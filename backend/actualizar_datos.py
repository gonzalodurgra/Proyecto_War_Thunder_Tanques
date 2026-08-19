import json
import asyncio
from pathlib import Path
from database import get_tanks_collection
from warthunder_todos_tanques import fetch_all_tanks

BASE_DIR = Path(__file__).resolve().parent
TANQUES_JSON = BASE_DIR / "tanques.json"

async def actualizar_tanques_semanal():
    print("Iniciando actualización semanal de tanques...")
    
    # 1. Scraping de los datos nuevos
    nuevos_tanques = await fetch_all_tanks()
    print(f"Scraping completado. {len(nuevos_tanques)} tanques encontrados.")
    
    # 2. Guardar el JSON localmente (como caché/backup)
    with open(TANQUES_JSON, "w", encoding="utf-8") as f:
        json.dump(nuevos_tanques, f, indent=4, ensure_ascii=False)
        
    # 3. Fusión (Merge) con MongoDB
    tanks_collection = get_tanks_collection()
    tanques_actualizados = 0
    tanques_nuevos = 0
    
    for tanque_nuevo in nuevos_tanques:
        nombre = tanque_nuevo.get("nombre")
        nacion = tanque_nuevo.get("nacion")
        
        # Buscar si el tanque ya existe en MongoDB
        tanque_existente = tanks_collection.find_one({"nombre": nombre, "nacion": nacion})
        
        if tanque_existente:
            # Preservar slope_factor_ia
            if "slope_factor_ia" in tanque_existente:
                tanque_nuevo["slope_factor_ia"] = tanque_existente["slope_factor_ia"]
                
            # Preservar datos de municiones generados por IA
            for armamento_key in ["armamento", "setup_1", "setup_2"]:
                if armamento_key in tanque_existente and armamento_key in tanque_nuevo:
                    arm_existente = tanque_existente[armamento_key]
                    arm_nuevo = tanque_nuevo[armamento_key]
                    
                    if isinstance(arm_existente, dict) and isinstance(arm_nuevo, dict):
                        for arma_nombre, arma_datos in arm_existente.items():
                            if arma_nombre in arm_nuevo and "municiones" in arma_datos:
                                municiones_existentes = arma_datos["municiones"]
                                municiones_nuevas = arm_nuevo[arma_nombre].get("municiones", [])
                                
                                # Crear un diccionario para búsqueda rápida de municiones existentes
                                dict_mun_existentes = {m["nombre"]: m for m in municiones_existentes if "nombre" in m}
                                
                                for mun_nueva in municiones_nuevas:
                                    nombre_mun = mun_nueva.get("nombre")
                                    if nombre_mun and nombre_mun in dict_mun_existentes:
                                        mun_antigua = dict_mun_existentes[nombre_mun]
                                        if mun_antigua.get("datos_generados_por_ia"):
                                            mun_nueva["masa_total"] = mun_antigua.get("masa_total")
                                            mun_nueva["velocidad_bala"] = mun_antigua.get("velocidad_bala")
                                            mun_nueva["masa_explosivo"] = mun_antigua.get("masa_explosivo")
                                            mun_nueva["datos_generados_por_ia"] = True
            
            # Actualizar en base de datos
            tanks_collection.update_one({"_id": tanque_existente["_id"]}, {"$set": tanque_nuevo})
            tanques_actualizados += 1
        else:
            # Insertar como nuevo
            tanks_collection.insert_one(tanque_nuevo)
            tanques_nuevos += 1
            
    print(f"Actualización completada: {tanques_actualizados} actualizados, {tanques_nuevos} nuevos insertados.")

if __name__ == "__main__":
    asyncio.run(actualizar_tanques_semanal())
