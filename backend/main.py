
from fastapi import FastAPI, HTTPException, Depend, File, UploadFile
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from database import get_tanks_collection, verificar_conexion
from models import Tanque, TanqueDB
from bson import ObjectId
from auth_routes import router as auth_router
from auth import obtener_usuario_activo_actual
from user_models import UsuarioEnDB
import os
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil

# Paso 1: Crear la aplicación FastAPI
app = FastAPI(
    title="API de Tanques War Thunder",
    description="API para gestionar información de tanques del juego War Thunder",
    version="1.0.0"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:4200"
)

# Paso 1.5: Configurar CORS para permitir peticiones desde Angular
# EXPLICACIÓN: Angular corre en http://localhost:4200 por defecto
# FastAPI corre en http://localhost:8000
# Sin CORS, el navegador bloquea las peticiones entre diferentes puertos
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",  # Desarrollo local
        "http://localhost",
        FRONTEND_URL,  # Producción
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permite todos los headers
)

# Paso 1.7: Incluir el router de autenticación
# EXPLICACIÓN: Todas las rutas de auth_router estarán bajo /auth
app.include_router(auth_router)

app.mount("/imagenes", StaticFiles(directory="imagenes"), name="imagenes")

# Definir la carpeta donde se guardarán las imágenes
IMAGENES_DIR = Path("imagenes")

# Crear la carpeta al iniciar la aplicación (si no existe)
IMAGENES_DIR.mkdir(exist_ok=True)

# Paso 2: Obtener la colección de tanques
tanks_collection = get_tanks_collection()

# Paso 3: Evento que se ejecuta al iniciar la aplicación
#@app.on_event("startup")
@asynccontextmanager
async def startup_event():
    """
    Esta función se ejecuta cuando la aplicación inicia.
    Verifica que la conexión a MongoDB funcione.
    """
    print("Iniciando aplicación...")
    verificar_conexion()

# Paso 4: Ruta principal (raíz)
@app.get("/")
async def root():
    """
    Ruta de bienvenida. Prueba con: http://localhost:8000/
    """
    return {
        "mensaje": "Bienvenido a la API de War Thunder",
        "documentacion": "/docs"
    }

# Paso 5: Crear un nuevo tanque (POST)
@app.post("/tanques/", response_model=dict, status_code=201)
async def crear_tanque(tanque: Tanque):
    """
    Crea un nuevo tanque en la base de datos.
    
    Args:
        tanque: Objeto Tanque con toda la información
        
    Returns:
        Diccionario con el ID del tanque creado
    """
    # Convertir el modelo Pydantic a diccionario
    tanque_dict = tanque.model_dump()
    
    # Insertar en MongoDB
    resultado = tanks_collection.insert_one(tanque_dict)
    
    return {
        "mensaje": "Tanque creado exitosamente",
        "id": str(resultado.inserted_id)
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
@app.get("/tanques/", response_model=List[dict])
async def obtener_tanques():
    """
    Obtiene todos los tanques de la base de datos.
    Prueba con: http://localhost:8000/tanques/
    
    Returns:
        Lista de todos los tanques
    """
    tanques = []
    
    # Buscar todos los documentos en la colección
    for tanque in tanks_collection.find():
        # Convertir ObjectId a string para que sea serializable
        tanque["_id"] = str(tanque["_id"])
        tanques.append(tanque)
    
    return tanques

# Paso 7: Obtener un tanque específico por ID (GET)
@app.get("/tanques/{id}", response_model=dict)
async def obtener_tanque_por_id(id: str):
    """
    Obtiene un tanque específico por su nombre.
    
    Args:
        tanque_id: Id del tanque en MongoDB
        
    Returns:
        Información del tanque
    """
    try:
        # Validar formato
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID de MongoDB inválido")

        # Buscar el tanque por _id (ObjectId, no string)
        tanque = tanks_collection.find_one({"_id": ObjectId(id)})

        if tanque is None:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")

        # Convertir ObjectId a string para devolverlo
        tanque["_id"] = str(tanque["_id"])
        return tanque

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener tanque: {str(e)}")

# Paso 8: Obtener tanques por nación (GET)
@app.get("/tanques/nacion/{nacion}", response_model=List[dict])
async def obtener_tanques_por_nacion(nacion: str):
    """
    Obtiene todos los tanques de una nación específica.
    Ejemplo: http://localhost:8000/tanques/nacion/Great Britain
    
    Args:
        nacion: Id de la nación
        
    Returns:
        Lista de tanques de esa nación
    """
    tanques = []
    
    # Buscar tanques de la nación especificada
    for tanque in tanks_collection.find({"nacion": nacion}):
        tanque["_id"] = str(tanque["_id"])
        tanques.append(tanque)
    
    if not tanques:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontraron tanques de la nación: {nacion}"
        )
    
    return tanques

# Paso 9: Actualizar un tanque (PUT)
@app.put("/tanques/{id}", response_model=dict)
async def actualizar_tanque(id: str, tanque: Tanque):
    """
    Actualiza la información de un tanque existente.
    
    Args:
        tanque_id: Id del tanque a actualizar
        tanque: Nueva información del tanque
        
    Returns:
        Mensaje de confirmación
    """
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID de MongoDB inválido")

        tanque_dict = tanque.model_dump()

        resultado = tanks_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": tanque_dict}
        )

        if resultado.matched_count == 0:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")

        return {"mensaje": "Tanque actualizado exitosamente"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

# Paso 10: Eliminar un tanque (DELETE)
@app.delete("/tanques/{id}", response_model=dict)
async def eliminar_tanque(id: str):
    """
    Elimina un tanque de la base de datos.
    
    Args:
        tanque_id: Id del tanque a eliminar
        
    Returns:
        Mensaje de confirmación
    """
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="ID de MongoDB inválido")

        resultado = tanks_collection.delete_one({"_id": ObjectId(id)})

        if resultado.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")

        return {"mensaje": "Tanque eliminado exitosamente"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

# Para ejecutar la aplicación, usa en la terminal:
# uvicorn main:app --reload