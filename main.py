
from fastapi import FastAPI, HTTPException, Depends
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from database import get_tanks_collection, verificar_conexion
from models import Tanque, TanqueDB
from bson import ObjectId
from auth_routes import router as auth_router
from auth import obtener_usuario_activo_actual
from user_models import UsuarioEnDB

# Paso 1: Crear la aplicación FastAPI
app = FastAPI(
    title="API de Tanques War Thunder",
    description="API para gestionar información de tanques del juego War Thunder",
    version="1.0.0"
)

# Paso 1.5: Configurar CORS para permitir peticiones desde Angular
# EXPLICACIÓN: Angular corre en http://localhost:4200 por defecto
# FastAPI corre en http://localhost:8000
# Sin CORS, el navegador bloquea las peticiones entre diferentes puertos
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",  # Angular development server
        "http://127.0.0.1:4200",  # Alternativa de localhost
        # Añade aquí la URL de producción cuando la tengas
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permite todos los headers
)

# Paso 1.7: Incluir el router de autenticación
# EXPLICACIÓN: Todas las rutas de auth_router estarán bajo /auth
app.include_router(auth_router)

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
@app.get("/tanques/{tanque_nombre}", response_model=dict)
async def obtener_tanque_por_nombre(tanque_nombre: str):
    """
    Obtiene un tanque específico por su nombre.
    
    Args:
        tanque_nombre: Nombre del tanque en MongoDB
        
    Returns:
        Información del tanque
    """
    try:
        # Buscar el tanque por ID
        tanque = tanks_collection.find_one({"nombre": tanque_nombre})
        
        if tanque is None:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")
        
        # Convertir ObjectId a string
        tanque["_id"] = str(tanque["_id"])
        return tanque
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Nombre inválido: {str(e)}")

# Paso 8: Obtener tanques por nación (GET)
@app.get("/tanques/nacion/{nacion}", response_model=List[dict])
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
@app.put("/tanques/{tanque_nombre}", response_model=dict)
async def actualizar_tanque(tanque_nombre: str, tanque: Tanque):
    """
    Actualiza la información de un tanque existente.
    
    Args:
        tanque_nombre: Nombre del tanque a actualizar
        tanque: Nueva información del tanque
        
    Returns:
        Mensaje de confirmación
    """
    try:
        # Convertir el modelo a diccionario
        tanque_dict = tanque.model_dump()
        
        # Actualizar el documento
        resultado = tanks_collection.update_one(
            {"nombre": tanque_nombre},
            {"$set": tanque_dict}
        )
        
        if resultado.matched_count == 0:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")
        
        return {"mensaje": "Tanque actualizado exitosamente"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

# Paso 10: Eliminar un tanque (DELETE)
@app.delete("/tanques/{tanque_nombre}", response_model=dict)
async def eliminar_tanque(tanque_nombre: str):
    """
    Elimina un tanque de la base de datos.
    
    Args:
        tanque_nombre: Nombre del tanque a eliminar
        
    Returns:
        Mensaje de confirmación
    """
    try:
        # Eliminar el documento
        resultado = tanks_collection.delete_one({"nombre": tanque_nombre})
        
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Tanque no encontrado")
        
        return {"mensaje": "Tanque eliminado exitosamente"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

# Para ejecutar la aplicación, usa en la terminal:
# uvicorn main:app --reload