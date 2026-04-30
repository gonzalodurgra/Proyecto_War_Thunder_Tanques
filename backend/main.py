
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import markdown
from database import get_tanks_collection, verificar_conexion
from models import Tanque, TanqueDB, CombateIARequest, CombateIAResponse
from google import genai
import json
from bson import ObjectId
from auth_routes import router as auth_router
from auth import obtener_usuario_activo_actual
from user_models import UsuarioEnDB
import os
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
from pending_changes_routes import router as pending_changes_router
from pending_changes_routes import crear_cambio_pendiente
from contextlib import asynccontextmanager
from fastapi import APIRouter, Query
from typing import Optional
from statistics import mean
from bson.decimal128 import Decimal128

def convertir_decimal128_recursivo(dato):
    """
    Convierte todos los Decimal128 a float de forma recursiva.
    Funciona con diccionarios, listas y valores individuales.
    """
    if isinstance(dato, Decimal128):
        # Convertir Decimal128 a float
        return float(dato.to_decimal())
    elif isinstance(dato, dict):
        # Si es un diccionario, convertir cada valor
        return {clave: convertir_decimal128_recursivo(valor) for clave, valor in dato.items()}
    elif isinstance(dato, list):
        # Si es una lista, convertir cada elemento
        return [convertir_decimal128_recursivo(elemento) for elemento in dato]
    else:
        # Si es otro tipo, dejarlo como está
        return dato
    
# Paso 3: Evento que se ejecuta al iniciar la aplicación
#@app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Esta función se ejecuta cuando la aplicación inicia.
    Verifica que la conexión a MongoDB funcione.
    """
    print("Iniciando aplicación...")
    verificar_conexion()
    yield
    print("Deteniendo aplicación.")

# Paso 1: Crear la aplicación FastAPI
app = FastAPI(
    title="API de Tanques War Thunder",
    description="API para gestionar información de tanques del juego War Thunder",
    version="1.0.0",
    lifespan=lifespan
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:4200"
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Configurar Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_ai = None
if GEMINI_API_KEY:
    client_ai = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("⚠️ ADVERTENCIA: GEMINI_API_KEY no configurada. El endpoint de IA no funcionará.")

allowed_origins = [
    "http://localhost:4200",  # Desarrollo local Angular
    "http://localhost:3000",  # Desarrollo local alternativo
    "http://localhost",       # Localhost genérico
    FRONTEND_URL,             # URL del frontend en producción
    "https://war-thunder-frontend.onrender.com"
]
if BACKEND_URL and BACKEND_URL not in allowed_origins:
    allowed_origins.append(BACKEND_URL)
    
if FRONTEND_URL.startswith("https://"):
    http_version = FRONTEND_URL.replace("https://", "http://")
    if http_version not in allowed_origins:
        allowed_origins.append(http_version)
elif FRONTEND_URL.startswith("http://"):
    https_version = FRONTEND_URL.replace("http://", "https://")
    if https_version not in allowed_origins:
        allowed_origins.append(https_version)

print(f"🌐 CORS configurado para: {allowed_origins}")

# Paso 1.5: Configurar CORS para permitir peticiones desde Angular
# EXPLICACIÓN: Angular corre en http://localhost:4200 por defecto
# FastAPI corre en http://localhost:8000
# Sin CORS, el navegador bloquea las peticiones entre diferentes puertos
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permite todos los headers
)
# Paso 1.7: Incluir el router de autenticación
# EXPLICACIÓN: Todas las rutas de auth_router estarán bajo /auth
app.include_router(auth_router)
# Incluir el router de cambios pendientes
app.include_router(pending_changes_router)

app.mount("/imagenes", StaticFiles(directory="imagenes"), name="imagenes")

# Definir la carpeta donde se guardarán las imágenes
IMAGENES_DIR = Path("imagenes")

# Crear la carpeta al iniciar la aplicación (si no existe)
IMAGENES_DIR.mkdir(exist_ok=True)

# Paso 2: Obtener la colección de tanques
tanks_collection = get_tanks_collection()

def media(tanques, campo):
    valores = [t[campo] for t in tanques if isinstance(t.get(campo), (int, float))]
    return round(sum(valores) / len(valores), 2) if valores else 0


def contar_por_nacion(tanques):
    naciones = {}
    for t in tanques:
        naciones[t["nacion"]] = naciones.get(t["nacion"], 0) + 1
    return naciones

def filtrar_por_br(tanques, br_min, br_max, modo):
    campo_br = "rating_realista" if modo == "realista" else "rating_arcade"
    
    tanques_filtrados = []
    
    for t in tanques:
        # Verificar que el campo existe
        if campo_br not in t:
            continue
        
        try:
            # Intentar convertir a float
            rating = float(t[campo_br])
            
            # Verificar los rangos
            if br_min is not None and rating < br_min:
                continue
            if br_max is not None and rating > br_max:
                continue
            
            # Si pasó todas las verificaciones, agregarlo
            tanques_filtrados.append(t)
            
        except (ValueError, TypeError):
            # Si no se puede convertir a float, ignorar este tanque
            continue
    
    return tanques_filtrados

def extraer_penetraciones(tanque):
    """
    Extrae todas las penetraciones a 0m de un tanque.
    Maneja tanto 'armamento' como 'setup_1/setup_2'.
    
    Retorna: lista de números (penetraciones en mm)
    """
    penetraciones = []
    
    # CASO 1: El tanque tiene campo "armamento"
    if "armamento" in tanque:
        armamento = tanque["armamento"]
        
        # Recorrer cada arma (ej: "37 mm M5 cannon")
        for nombre_arma, datos_arma in armamento.items():
            municiones = datos_arma.get("municiones", [])
            
            # Recorrer cada munición
            for municion in municiones:
                penetracion = municion.get("penetracion_mm", [])
                
                # Si hay datos de penetración, tomar el primero [0]
                if penetracion and len(penetracion) > 0:
                    penetraciones.append(penetracion[0])
    
    # CASO 2: El tanque tiene "setup_1", "setup_2", etc.
    else:
        # Buscar todos los setups (setup_1, setup_2, ...)
        for key in tanque.keys():
            if key.startswith("setup_"):
                setup = tanque[key]
                
                # Recorrer cada arma en el setup
                for nombre_arma, datos_arma in setup.items():
                    municiones = datos_arma.get("municiones", [])
                    
                    # Recorrer cada munición
                    for municion in municiones:
                        penetracion = municion.get("penetracion_mm", [])
                        
                        if penetracion and len(penetracion) > 0:
                            penetraciones.append(penetracion[0])
    
    return penetraciones

def media_penetracion(tanques):
    """
    Calcula la media de penetración a 0m de todos los tanques.
    
    Parámetros:
    - tanques: lista de diccionarios (tanques)
    
    Retorna: promedio de penetración (float)
    """
    todas_penetraciones = []
    
    # Extraer penetraciones de cada tanque
    for tanque in tanques:
        penetraciones = extraer_penetraciones(tanque)
        todas_penetraciones.extend(penetraciones)  # Agregar todas a la lista
    
    # Si no hay datos, retornar 0
    if not todas_penetraciones:
        return 0
    
    # Calcular promedio
    return sum(todas_penetraciones) / len(todas_penetraciones)

def obtener_penetracion_maxima(tanque):
    """
    Obtiene la munición con mayor penetración a 0m de un tanque.
    
    Parámetros:
    - tanque: diccionario con datos del tanque
    
    Retorna: diccionario con información de la mejor munición
    """
    mejor_municion = {
        "penetracion_0m": 0,
        "penetraciones_completas": [],
        "nombre_municion": "N/A",
        "tipo_municion": "N/A"
    }
    
    # CASO 1: Tanque con campo "armamento"
    if "armamento" in tanque:
        armamento = tanque["armamento"]
        
        # Recorrer cada arma del tanque
        for nombre_arma, datos_arma in armamento.items():
            municiones = datos_arma.get("municiones", [])
            
            # Recorrer cada munición del arma
            for municion in municiones:
                penetracion = municion.get("penetracion_mm", [])
                
                # Si tiene datos de penetración
                if penetracion and len(penetracion) > 0:
                    penetracion_0m = penetracion[0]  # Primer valor = 0 metros
                    
                    # Si esta munición es mejor que la guardada
                    if penetracion_0m > mejor_municion["penetracion_0m"]:
                        mejor_municion = {
                            "penetracion_0m": penetracion_0m,
                            "penetraciones_completas": penetracion,
                            "nombre_municion": municion.get("nombre", "N/A"),
                            "tipo_municion": municion.get("tipo", "N/A")
                        }
    
    # CASO 2: Tanque con "setup_1", "setup_2", etc.
    else:
        # Buscar todos los setups del tanque
        for key in tanque.keys():
            if key.startswith("setup_"):
                setup = tanque[key]
                
                # Recorrer cada arma del setup
                for nombre_arma, datos_arma in setup.items():
                    municiones = datos_arma.get("municiones", [])
                    
                    # Recorrer cada munición
                    for municion in municiones:
                        penetracion = municion.get("penetracion_mm", [])
                        
                        if penetracion and len(penetracion) > 0:
                            penetracion_0m = penetracion[0]
                            
                            if penetracion_0m > mejor_municion["penetracion_0m"]:
                                mejor_municion = {
                                    "penetracion_0m": penetracion_0m,
                                    "penetraciones_completas": penetracion,
                                    "nombre_municion": municion.get("nombre", "N/A"),
                                    "tipo_municion": municion.get("tipo", "N/A")
                                }
    
    return mejor_municion

# Paso 4: Ruta principal (raíz)
@app.get("/")
async def root():
    """
    Ruta de bienvenida. Prueba con: http://localhost:8000/
    """
    return {
        "mensaje": "Bienvenido a la API de War Thunder",
        "documentacion": "/docs",
        "version": "1.0.0",
        "cors_enabled": True,
        "allowed_origins": len(allowed_origins)
    }
    
@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    try:
        verificar_conexion()
        return {"status": "ok", "db": "connected"}
    except Exception:
        return {"status": "degraded", "db": "error"}


# Paso 5: Crear un nuevo tanque (POST)
@app.post("/tanques/", response_model=dict, status_code=201)
async def crear_tanque(
    tanque: Tanque,
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Crea un nuevo tanque en la base de datos.
    
    NUEVO COMPORTAMIENTO:
    - Si el usuario ES ADMIN: crea el tanque inmediatamente
    - Si el usuario NO ES ADMIN: crea un cambio pendiente de aprobación
    
    Args:
        tanque: Objeto Tanque con toda la información
        usuario_actual: Usuario autenticado actual
        
    Returns:
        Diccionario con el ID del tanque creado o ID del cambio pendiente
    """
    tanque_dict = tanque.model_dump()
    
    # VERIFICAR SI ES ADMIN
    if usuario_actual.es_admin:
        # ADMIN: Crear inmediatamente
        resultado = tanks_collection.insert_one(tanque_dict)
        return {
            "mensaje": "Tanque creado exitosamente",
            "id": str(resultado.inserted_id)
        }
    else:
        # NO ADMIN: Crear cambio pendiente
        cambio_id = await crear_cambio_pendiente(
            tipo_operacion="crear",
            coleccion="tanques",
            usuario=usuario_actual,
            datos_nuevos=tanque_dict
        )
        return {
            "mensaje": "Solicitud de creación enviada. Pendiente de aprobación del administrador",
            "cambio_id": cambio_id,
            "estado": "pendiente"
        }
    
# NUEVO ENDPOINT: Subir imagen de tanque
@app.post("/upload-tank-image/")
async def upload_tank_image(file: UploadFile = File(...)):
    """
    Endpoint para subir una imagen de tanque.
    
    EXPLICACIÓN PASO A PASO:
    1. Recibe el archivo desde Angular
    2. Verifica que sea una imagen válida
    3. Guarda el archivo en la carpeta 'imagenes'
    4. Retorna confirmación con el nombre del archivo
    
    Args:
        file: Archivo de imagen enviado desde Angular (UploadFile)
        
    Returns:
        Diccionario con mensaje de éxito y nombre del archivo
    """
    
    # PASO 1: Verificar que sea una imagen
    # content_type es algo como "image/jpeg", "image/png", etc.
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen (JPG, PNG, etc.)"
        )
    
    # PASO 2: Limpiar el nombre del archivo
    # Esto previene problemas con caracteres especiales
    nombre_seguro = file.filename.replace(" ", "_")
    
    # PASO 3: Crear la ruta completa donde guardar
    file_path = IMAGENES_DIR / nombre_seguro
    
    try:
        # PASO 4: Guardar el archivo
        # Abrimos el archivo en modo escritura binaria ('wb')
        with file_path.open("wb") as buffer:
            # Leemos todo el contenido del archivo subido
            content = await file.read()
            # Lo escribimos en el nuevo archivo
            buffer.write(content)
        
        # PASO 5: Retornar confirmación
        return {
            "mensaje": "Imagen subida exitosamente",
            "nombre_archivo": nombre_seguro,
            "ruta": f"imagenes/{nombre_seguro}"
        }
    
    except Exception as e:
        # Si algo sale mal, retornar error
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar la imagen: {str(e)}"
        )

# Paso 6: Obtener todos los tanques (GET)
@app.get("/tanques/", response_model=List[dict])  # ← Cambiar de nuevo a dict
async def obtener_tanques():
    """
    Obtiene todos los tanques de la base de datos.
    Prueba con: http://localhost:8000/tanques/
    
    Returns:
        Lista de todos los tanques
    """
    tanques = []
    
    # Buscar todos los documentos en la colección
    for tanque_dict in tanks_collection.find().sort([("rating_realista", 1), ("nacion", 1)]):
        # Convertir ObjectId a string
        tanque_dict["_id"] = str(tanque_dict["_id"])
        
        # Convertir todos los Decimal128 a float (recursivamente)
        tanque_dict = convertir_decimal128_recursivo(tanque_dict)
        
        tanques.append(tanque_dict)
    
    return tanques

# Paso 7: Obtener un tanque específico por ID (GET)
@app.get("/tanques/{id}", response_model=dict)
async def obtener_tanque_por_id(id: str):
    """
    Obtiene un tanque específico por su ID.
    
    Args:
        id: Id del tanque en MongoDB
        
    Returns:
        Información del tanque
    """
    try:
        # Validar formato
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID de MongoDB inválido")

        # Buscar el tanque por _id (ObjectId, no string)
        tanque_dict = tanks_collection.find_one({"_id": ObjectId(id)})

        if tanque_dict is None:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")

        # Convertir ObjectId a string
        tanque_dict["_id"] = str(tanque_dict["_id"])
        
        # Convertir todos los Decimal128 a float (recursivamente)
        tanque_dict = convertir_decimal128_recursivo(tanque_dict)
        
        return tanque_dict

    except HTTPException:
        # Re-lanzar las excepciones HTTP sin modificar
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener tanque: {str(e)}")


# Paso 8: Obtener tanques por nación (GET)
@app.get("/tanques/nacion/{nacion}", response_model=dict)
async def obtener_tanques_por_nacion(nacion: str):
    """
    Obtiene todos los tanques de una nación específica.
    Ejemplo: http://localhost:8000/tanques/nacion/Great Britain
    
    Args:
        nacion: Nombre de la nación
        
    Returns:
        Lista de tanques de esa nación
    """
    tanques = []
    
    # Buscar tanques de la nación especificada
    for tanque_dict in tanks_collection.find({"nacion": nacion}):
        # Convertir ObjectId a string
        tanque_dict["_id"] = str(tanque_dict["_id"])
        
        # Convertir todos los Decimal128 a float (recursivamente)
        tanque_dict = convertir_decimal128_recursivo(tanque_dict)
        
        tanques.append(tanque_dict)
    
    if not tanques:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontraron tanques de la nación: {nacion}"
        )
    
    return tanques

# Paso 9: Actualizar un tanque (PUT)
@app.put("/tanques/{id}", response_model=dict)
async def actualizar_tanque(
    id: str,
    tanque: Tanque,
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Actualiza la información de un tanque existente.
    
    NUEVO COMPORTAMIENTO:
    - Si el usuario ES ADMIN: actualiza el tanque inmediatamente
    - Si el usuario NO ES ADMIN: crea un cambio pendiente de aprobación
    """
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID de MongoDB inválido")

        tanque_dict = tanque.model_dump()
        
        # Obtener datos originales
        tanque_original = tanks_collection.find_one({"_id": ObjectId(id)})
        
        if not tanque_original:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")
        
        # Convertir ObjectId a string para el cambio pendiente
        tanque_original["_id"] = str(tanque_original["_id"])

        # VERIFICAR SI ES ADMIN
        if usuario_actual.es_admin:
            # ADMIN: Actualizar inmediatamente
            resultado = tanks_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": tanque_dict}
            )
            return {"mensaje": "Tanque actualizado exitosamente"}
        else:
            # NO ADMIN: Crear cambio pendiente
            cambio_id = await crear_cambio_pendiente(
                tipo_operacion="actualizar",
                coleccion="tanques",
                usuario=usuario_actual,
                tanque_id=id,
                datos_originales=tanque_original,
                datos_nuevos=tanque_dict
            )
            return {
                "mensaje": "Solicitud de actualización enviada. Pendiente de aprobación del administrador",
                "cambio_id": cambio_id,
                "estado": "pendiente"
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

# Paso 10: Eliminar un tanque (DELETE)
@app.delete("/tanques/{id}", response_model=dict)
async def eliminar_tanque(
    id: str,
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Elimina un tanque de la base de datos.
    
    NUEVO COMPORTAMIENTO:
    - Si el usuario ES ADMIN: elimina el tanque inmediatamente
    - Si el usuario NO ES ADMIN: crea un cambio pendiente de aprobación
    """
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID de MongoDB inválido")

        # Obtener datos originales
        tanque_original = tanks_collection.find_one({"_id": ObjectId(id)})
        
        if not tanque_original:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")
        
        # Convertir ObjectId a string
        tanque_original["_id"] = str(tanque_original["_id"])

        # VERIFICAR SI ES ADMIN
        if usuario_actual.es_admin:
            # ADMIN: Eliminar inmediatamente
            resultado = tanks_collection.delete_one({"_id": ObjectId(id)})
            return {"mensaje": "Tanque eliminado exitosamente"}
        else:
            # NO ADMIN: Crear cambio pendiente
            cambio_id = await crear_cambio_pendiente(
                tipo_operacion="eliminar",
                coleccion="tanques",
                usuario=usuario_actual,
                tanque_id=id,
                datos_originales=tanque_original
            )
            return {
                "mensaje": "Solicitud de eliminación enviada. Pendiente de aprobación del administrador",
                "cambio_id": cambio_id,
                "estado": "pendiente"
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
    
@app.get("/stats")
async def obtener_stats(
    br_min: Optional[float] = Query(None, ge=0),
    br_max: Optional[float] = Query(None, ge=0),
    modo: str = Query("realista", regex="^(realista|arcade)$")
):
    tanques = await obtener_tanques()  # Mongo o lo que uses

    if br_min is not None or br_max is not None:
        tanques = filtrar_por_br(tanques, br_min, br_max, modo)

    if not tanques:
        return {
            "total": 0,
            "mensaje": "No hay tanques en ese rango"
        }
    campo_potencia = "relacion_potencia_peso_realista" if modo == "realista" else "relacion_potencia_peso"
    return {
        "total": len(tanques),
        "naciones": contar_por_nacion(tanques),
        "blindaje_chasis": round(media(tanques, "blindaje_chasis")),
        "blindaje_torreta": round(media(tanques, "blindaje_torreta")),
        "velocidad_adelante": round(media(tanques, f"velocidad_adelante_{modo}")),
        "velocidad_atras": round(media(tanques, f"velocidad_atras_{modo}")),
        "depresion": round(media(tanques, "angulo_depresion")),
        "elevacion": round(media(tanques, "angulo_elevacion")),
        "recarga": round(media(tanques, "recarga"), 2),
        "cadencia": round(media(tanques, "cadencia"), 2),
        "potencia_peso": round(media(tanques, campo_potencia), 2),
        "tripulacion": round(media(tanques, "tripulacion")),
        "visibilidad": round(media(tanques, "visibilidad")),
        "rotacion_horizontal": round(media(tanques, f"rotacion_torreta_horizontal_{modo}"), 2),
        "rotacion_vertical": round(media(tanques, f"rotacion_torreta_vertical_{modo}"), 2),
        "penetracion": round(media_penetracion(tanques))
    }
    
@app.get("/stats/nacion")
async def obtener_stats_nacion(
    nacion: str,
    br_min: Optional[float] = Query(None, ge=0),
    br_max: Optional[float] = Query(None, ge=0),
    modo: str = Query("realista", regex="^(realista|arcade)$")
):
    """
    Obtiene estadísticas de tanques de una nación específica.
    
    Parámetros:
    - nacion: Nombre de la nación (USA, Germany, USSR, etc.)
    - br_min: Battle Rating mínimo (opcional)
    - br_max: Battle Rating máximo (opcional)
    - modo: realista o arcade (por defecto: realista)
    """
    # PASO 1: Obtener todos los tanques de la nación
    tanques = await obtener_tanques_por_nacion(nacion)
    
    # PASO 3: Filtrar por BR si se especificó
    if br_min is not None or br_max is not None:
        tanques = filtrar_por_br(tanques, br_min, br_max, modo)
    
    # PASO 4: Si no hay tanques, devolver mensaje
    if not tanques:
        return {
            "total": 0,
            "mensaje": f"No hay tanques de {nacion} en ese rango"
        }
    
    # PASO 5: Calcular el campo correcto según el modo
    campo_potencia = "relacion_potencia_peso_realista" if modo == "realista" else "relacion_potencia_peso"
    
    # PASO 6: Calcular y devolver estadísticas
    return {
        "total": len(tanques),
        "naciones": contar_por_nacion(tanques),
        "blindaje_chasis": round(media(tanques, "blindaje_chasis")),
        "blindaje_torreta": round(media(tanques, "blindaje_torreta")),
        "velocidad_adelante": round(media(tanques, f"velocidad_adelante_{modo}")),
        "velocidad_atras": round(media(tanques, f"velocidad_atras_{modo}")),
        "depresion": round(media(tanques, "angulo_depresion")),
        "elevacion": round(media(tanques, "angulo_elevacion")),
        "recarga": round(media(tanques, "recarga"), 2),
        "cadencia": round(media(tanques, "cadencia"), 2),
        "potencia_peso": round(media(tanques, campo_potencia), 2),
        "tripulacion": round(media(tanques, "tripulacion")),
        "visibilidad": round(media(tanques, "visibilidad")),
        "rotacion_horizontal": round(media(tanques, f"rotacion_torreta_horizontal_{modo}"), 2),
        "rotacion_vertical": round(media(tanques, f"rotacion_torreta_vertical_{modo}"), 2),
        "penetracion": round(media_penetracion(tanques))
    }


@app.get("/top")
async def obtener_top(
    caracteristica: str,
    limite: int = Query(5, ge=1, le=50),
    br_min: Optional[float] = Query(None, ge=0),
    br_max: Optional[float] = Query(None, ge=0),
    modo: str = Query("realista", regex="^(realista|arcade)$")
):
    """
    Obtiene el top de tanques según una característica.
    
    Parámetros:
    - caracteristica: Campo a ordenar (blindaje_torreta, velocidad_adelante_realista, etc.)
    - limite: Número de tanques a devolver (1-50, por defecto: 5)
    - br_min: Battle Rating mínimo (opcional)
    - br_max: Battle Rating máximo (opcional)
    - modo: realista o arcade (por defecto: realista)
    """
    # PASO 1: Obtener todos los tanques
    tanques = await obtener_tanques()
    
    # PASO 2: Filtrar por BR si se especificó
    if br_min is not None or br_max is not None:
        tanques = filtrar_por_br(tanques, br_min, br_max, modo)
        
        # ===== NUEVA LÓGICA PARA PENETRACIÓN =====
    if caracteristica == "penetracion":
        # PASO 3a: Procesar tanques para obtener penetraciones
        tanques_con_penetracion = []
        
        for tanque in tanques:
            mejor_municion = obtener_penetracion_maxima(tanque)
            
            # Solo incluir tanques que tengan munición
            if mejor_municion["penetracion_0m"] > 0:
                # Crear objeto combinando datos del tanque + munición
                tanque_procesado = {
                    "nombre": tanque.get("nombre", "Desconocido"),
                    "nacion": tanque.get("nacion", "Desconocido"),
                    "rating_realista": tanque.get("rating_realista", "?"),
                    "rating_arcade": tanque.get("rating_arcade", "?"),
                    "penetracion": mejor_municion["penetracion_0m"],  # Para ordenar
                    "penetracion_0m": mejor_municion["penetracion_0m"],
                    "penetraciones_completas": mejor_municion["penetraciones_completas"],
                    "nombre_municion": mejor_municion["nombre_municion"],
                    "tipo_municion": mejor_municion["tipo_municion"]
                }
                tanques_con_penetracion.append(tanque_procesado)
        
        # PASO 4a: Verificar si hay resultados
        if not tanques_con_penetracion:
            return {
                "tanques": [],
                "mensaje": "No hay tanques con datos de penetración"
            }
        
        # PASO 5a: Ordenar por penetración a 0m (mayor a menor)
        tanques_ordenados = sorted(
            tanques_con_penetracion,
            key=lambda t: t["penetracion_0m"],
            reverse=True
        )
        
        # PASO 6a: Tomar solo los primeros 'limite'
        top_tanques = tanques_ordenados[:limite]
        
        # PASO 7a: Devolver resultado
        return {
            "tanques": top_tanques,
            "total": len(top_tanques),
            "caracteristica": "penetracion",
            "es_penetracion": True  # Bandera para el bot
        }
    else:
        # PASO 3: Filtrar tanques que tienen la característica
        tanques_con_valor = []
        for t in tanques:
            valor = t.get(caracteristica)
            
            # Solo incluir si el valor es un número válido
            if isinstance(valor, (int, float)):
                tanques_con_valor.append(t)
            elif isinstance(valor, str):
                try:
                    float(valor)  # Intentar convertir
                    tanques_con_valor.append(t)
                except (ValueError, TypeError):
                    continue
        
        # PASO 4: Si no hay tanques con esa característica
        if not tanques_con_valor:
            return {
                "tanques": [],
                "mensaje": f"No hay tanques con datos de {caracteristica}"
            }
        
        # PASO 5: Ordenar de mayor a menor
        tanques_ordenados = sorted(
            tanques_con_valor,
            key=lambda t: float(t.get(caracteristica, 0)),
            reverse=True
        )
        
        # PASO 6: Tomar solo los primeros 'limite' tanques
        top_tanques = tanques_ordenados[:limite]
        
        # PASO 7: Devolver el resultado
        return {
            "tanques": top_tanques,
            "total": len(top_tanques),
            "caracteristica": caracteristica
        }

@app.get("/ia/modelos/")
async def listar_modelos_ia():
    """
    Retorna la lista de modelos de Gemini disponibles para la API Key actual.
    """
    if not client_ai:
        return []
    
    try:
        modelos = []
        # Obtenemos todos los modelos de la API
        for m in client_ai.models.list():
            nombre_id = m.name.lower()
            
            # FILTRO: Debe permitir generar contenido
            # En la nueva SDK, podemos checkear m.supported_generation_methods o simplemente filtrar
            if 'generatecontent' not in [method.lower() for method in (m.supported_generation_methods or [])]:
                continue
                
            # LISTA NEGRA: Palabras clave de modelos que NO son para chat/texto general
            palabras_bloqueadas = [
                'embedding', 'aqa', 'search', 'image', 'vision-only', 
                'banana', 'nano-experimental', 'internal'
            ]
            
            es_modelo_especializado = any(p in nombre_id for p in palabras_bloqueadas)
            
            # Solo incluimos modelos de la familia Gemini que no sean especializados
            if nombre_id.startswith('gemini-') and not es_modelo_especializado:
                modelos.append({
                    "id": nombre_id,
                    "nombre": m.display_name,
                    "descripcion": m.description
                })
        
        # Ordenamos la lista para que los más nuevos (2.0, 1.5) salgan primero
        modelos.sort(key=lambda x: x['id'], reverse=True)
        
        return modelos
    except Exception as e:
        print(f"Error al listar modelos: {e}")
        return []

@app.post("/combate-ia/", response_model=CombateIAResponse)
async def simular_combate_ia(request: CombateIARequest):
    """
    Simula un combate entre dos vehículos de War Thunder usando IA Gemini.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="La funcionalidad de IA no está configurada (falta API Key)"
        )

    try:
        # 1. Obtener datos de ambos vehículos
        v1 = tanks_collection.find_one({"_id": ObjectId(request.vehiculo1_id)})
        v2 = tanks_collection.find_one({"_id": ObjectId(request.vehiculo2_id)})

        if not v1 or not v2:
            raise HTTPException(status_code=404, detail="Uno o ambos vehículos no fueron encontrados")

        # Limpiar datos para el prompt
        v1 = convertir_decimal128_recursivo(v1)
        v2 = convertir_decimal128_recursivo(v2)
        v1["_id"] = str(v1["_id"])
        v2["_id"] = str(v2["_id"])

        # 2. Construir el prompt
        prompt = f"""
        Como experto analista militar de War Thunder, simula un enfrentamiento entre estos dos vehículos:

        VEHÍCULO 1: {v1['nombre']} ({v1['nacion']})
        - BR: {v1.get('rating_realista', 'N/A')}
        - Blindaje (Chasis/Torreta): {v1.get('blindaje_chasis', 0)}/{v1.get('blindaje_torreta', 0)} mm
        - Velocidad Máx: {v1.get('velocidad_adelante_realista', 0)} km/h
        - Recarga: {v1.get('recarga', 0)} s
        - Cargador: {v1.get('cargador', 1)} disparos
        - Cadencia: {v1.get('cadencia', 0)} disparos/min
        - Datos técnicos completos: {json.dumps(v1, default=str)}

        VEHÍCULO 2: {v2['nombre']} ({v2['nacion']})
        - BR: {v2.get('rating_realista', 'N/A')}
        - Blindaje (Chasis/Torreta): {v2.get('blindaje_chasis', 0)}/{v2.get('blindaje_torreta', 0)} mm
        - Velocidad Máx: {v2.get('velocidad_adelante_realista', 0)} km/h
        - Recarga: {v2.get('recarga', 0)} s
        - Cargador: {v2.get('cargador', 1)} disparos
        - Cadencia: {v2.get('cadencia', 0)} disparos/min
        - Datos técnicos completos: {json.dumps(v2, default=str)}

        SITUACIÓN DE COMBATE:
        {request.situacion}

        REFERENCIA TÉCNICA DE BALÍSTICA:
        - El campo 'penetracion_mm' es una lista de 6 valores. Estos corresponden a la capacidad de penetración a las siguientes distancias: [0m, 100m, 500m, 1000m, 1500m, 2000m]. Úsalos para evaluar la efectividad real según la distancia de la SITUACIÓN DE COMBATE.

        INSTRUCCIONES DE ANÁLISIS:
        1. Analiza TODAS las armas disponibles en cada vehículo (cañones principales, secundarios y ametralladoras).
        2. Para cada arma, evalúa todas sus municiones disponibles.
        3. Identifica la munición que, siendo capaz de penetrar el blindaje del oponente a la distancia de la situación dada, genere el mayor daño post-penetración (considerando tipo de proyectil, masa de explosivo y calibre).
        4. Evalúa la capacidad de fuego para decidir el ganador:
           - Si el vehículo tiene un 'cargador' mayor a 1, ten en cuenta la 'cadencia' de disparo para evaluar su capacidad de saturar al enemigo con varios disparos rápidos en poco tiempo.
           - Si el 'cargador' es 1, básate simplemente en el tiempo de 'recarga' para disparos individuales.
        5. Determina el ganador basándote en la ventaja táctica, supervivencia, arsenal y la lógica de cadencia/recarga analizada.
        
        Responde estrictamente en formato JSON con la siguiente estructura:
        {{
            "ganador": "Nombre del vehículo ganador",
            "analisis": "Explicación técnica detallada: indica qué arma y munición específica se usó, por qué es la más letal y cómo influyó la cadencia/recarga en el resultado",
            "puntos_clave": ["Punto 1", "Punto 2", "Punto 3"]
        }}
        """

        # 3. Llamar a Gemini (Usar el modelo seleccionado o el default 1.5 Flash)
        modelo_a_usar = request.modelo if hasattr(request, 'modelo') and request.modelo else 'gemini-2.0-flash-exp'
        
        if not client_ai:
            raise HTTPException(status_code=500, detail="El cliente de IA no está inicializado")

        response = client_ai.models.generate_content(
            model=modelo_a_usar,
            contents=prompt
        )
        
        # 4. Parsear respuesta
        # Limpiar posibles bloques de código markdown si los hay
        texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
        resultado_ia = json.loads(texto_limpio)

        # Convertir el análisis de Markdown a HTML para que el frontend lo muestre bien
        if 'analisis' in resultado_ia:
            resultado_ia['analisis'] = markdown.markdown(resultado_ia['analisis'])

        return CombateIAResponse(**resultado_ia)

    except Exception as e:
        print(f"Error en combate IA: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la simulación: {str(e)}")


# Para ejecutar la aplicación, usa en la terminal:
# uvicorn main:app --reload