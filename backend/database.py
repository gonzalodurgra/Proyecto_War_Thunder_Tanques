# mongo_client.py
from pymongo import MongoClient
from pymongo.database import Database
import os
from dotenv import load_dotenv
# ==========================
# Configuración de entorno
# ==========================
load_dotenv()
MONGODB_URI = os.getenv(
    "MONGODB_URI",
)
DATABASE_NAME = os.getenv(
    "DATABASE_NAME",
)

print(MONGODB_URI)
print(DATABASE_NAME)

# ==========================
# Inicialización del cliente
# ==========================
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    database: Database = client[DATABASE_NAME]

    # Verificación de conexión
    client.admin.command('ping')
    print(f"✓ Conexión exitosa a MongoDB: {MONGODB_URI}")
except Exception as e:
    print(f"✗ Error al conectar con MongoDB: {e}")
    raise e

# ==========================
# Funciones para colecciones y base de datos
# ==========================
def get_db():
    return database

def get_tanks_collection():
    """
    Devuelve la colección 'tanks' de la base de datos.
    """
    return database["tanks"]

def get_users_collection():
    """
    Devuelve la colección 'users' de la base de datos.
    """
    return database["users"]

# ==========================
# Función de verificación opcional
# ==========================
def verificar_conexion() -> bool:
    """
    Intenta hacer ping a la base de datos y devuelve True si está conectada.
    """
    try:
        client.admin.command('ping')
        print("✓ Conexión verificada con éxito")
        return True
    except Exception as e:
        print(f"✗ Error al verificar conexión: {e}")
        return False

