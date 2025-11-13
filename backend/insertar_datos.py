import json
from database import get_tanks_collection

# Paso 1: Leer el archivo JSON
with open('tanques.json', 'r', encoding='utf-8') as archivo:
    datos_tanque = json.load(archivo)

# Paso 2: Obtener la colección de tanques
tanks_collection = get_tanks_collection()

for tank in datos_tanque:
    # Paso 3: Insertar el tanque en la base de datos
    resultado = tanks_collection.insert_one(tank)

    # Paso 4: Mostrar el resultado
    print(f"✓ Tanque insertado exitosamente")
    print(f"ID en la base de datos: {resultado.inserted_id}")

    # Paso 5: Verificar que se insertó correctamente
    tanque_insertado = tanks_collection.find_one({"_id": resultado.inserted_id})
    print(f"Nombre del tanque: {tanque_insertado['nombre']}")
    print(f"Nación: {tanque_insertado['nacion']}")
    print(f"Rating: {tanque_insertado['rating_arcade']}")