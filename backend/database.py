from pymongo import MongoClient
from pymongo.database import Database
import os
from dotenv import load_dotenv

# Paso 1: Definir la URI de conexión
# Para desarrollo local, usa: "mongodb://localhost:27017/"
# Para MongoDB Atlas (nube), usa la URI que te proporciona Atlas
load_dotenv()
MONGODB_URI = os.getenv("MONGO_URI")

# Paso 2: Nombre de la base de datos
DATABASE_NAME = "war_thunder_db"

# Paso 3: Crear el cliente de MongoDB
client = MongoClient(MONGODB_URI)

# Paso 4: Obtener la base de datos
database: Database = client[DATABASE_NAME]

# Paso 5: Función para obtener la colección de tanques
def get_tanks_collection():
    """
    Esta función devuelve la colección 'tanks' de MongoDB.
    Una colección es como una tabla en SQL.
    """
    return database["tanks"]

# Paso 5.5: Función para obtener la colección de usuarios
def get_users_collection():
    """
    Esta función devuelve la colección 'users' de MongoDB.
    Aquí se guardan los datos de los usuarios registrados.
    """
    return database["users"]

# Paso 6: Función para verificar la conexión
def verificar_conexion():
    """
    Verifica si la conexión a MongoDB funciona correctamente.
    """
    try:
        # Intenta hacer ping a la base de datos
        client.admin.command('ping')
        print("✓ Conexión exitosa a MongoDB")
        return True
    except Exception as e:
        print(f"✗ Error al conectar con MongoDB: {e}")
        return False