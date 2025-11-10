import sys
import io
import re
import json
from statistics import mean
# Configurar la salida estándar para UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
data = {}
ratings = {}

# Ahora cargar el archivo limpio
with open("tanques.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    
for tank in data:
    if(tank["rating_arcade"]):
        rating = float(tank["rating_arcade"])
    arm1 = tank.get("armamento_1", {})
    arm1_name = arm1.get("nombre", "")
    
    # Recarga segura - maneja diferentes tipos de flechas
    recarga_text = arm1.get("recarga", "")
    recarga = 0.0
    if recarga_text != None:
        match = re.search(r'[→\-—―➝]\s*(\d+\.?\d*)\s*s', recarga_text)
        if match:
            try:
                recarga = float(match.group(1))
            except ValueError:
                recarga = 0.0

    # Rotación
    rotacion = float(arm1.get("rotacion_torreta_arcade", 0))

    # Penetración (primer valor)
    penetracion = 0.0
    masa = 0.0
    velocidad = 0.0
    explosivo = 0.0
    if arm1_name in tank.get("armamento", {}):
        municiones = tank["armamento"][arm1_name].get("municiones", [])
        lista_penetraciones = []
        lista_masas = []
        lista_explosivos = []
        lista_velocidades = []
        if municiones:
            for municion in municiones:
                if municion and "penetracion_mm" in municion:
                    try:
                        lista_penetraciones.append(float(municion["penetracion_mm"][0]))
                        if municion["masa_total"]:
                            if "kg" in municion["masa_total"]:
                                masa_limpia = municion["masa_total"].replace("kg", "").strip()
                                lista_masas.append(float(masa_limpia) * 1000)
                            elif "g" in municion["masa_total"]:
                                # Limpiar: quitar "g" y espacios, luego convertir a float
                                masa_limpia = municion["masa_total"].replace("g", "").strip()
                                lista_masas.append(float(masa_limpia))

                        if municion["velocidad_bala"]:
                            # Limpiar: quitar "m/s" y espacios, luego convertir a float
                            velocidad_limpia = municion["velocidad_bala"].replace("m/s", "").strip()
                            lista_velocidades.append(float(velocidad_limpia))

                        if municion["masa_explosivo"]:
                            # Limpiar: quitar "g" y espacios, luego convertir a float
                            if "kg" in municion["masa_explosivo"]:
                                explosivo_limpio = municion["masa_explosivo"].replace("kg", "").strip()
                                lista_explosivos.append(float(explosivo_limpio) * 1000)
                            elif "g" in municion["masa_explosivo"]:
                                explosivo_limpio = municion["masa_explosivo"].replace("g", "").strip()
                                lista_explosivos.append(float(explosivo_limpio))
                    except (ValueError, IndexError):
                        pass
        penetracion = max(lista_penetraciones) if lista_penetraciones else 0
        masa = max(lista_masas) if lista_masas else 0
        velocidad = max(lista_velocidades) if lista_velocidades else 0
        explosivo = max(lista_explosivos) if lista_explosivos else 0
    # Convertir todos los valores a float limpios
    valores = {
        "tripulacion": float(tank["tripulacion"].split()[0]),
        "visibilidad": float(tank["visibilidad"].replace("%", "").strip()),
        "peso": float(tank["peso"]),
        "velocidad_adelante_arcade": float(tank["velocidad_adelante_arcade"]),
        "velocidad_atras_arcade": float(tank["velocidad_atras_arcade"]),
        "relacion_potencia_peso": float(tank["relacion_potencia_peso"]),
        "blindaje_chasis": float(tank["blindaje_chasis"].split("/")[0].strip()),
        "blindaje_torreta": float(tank["blindaje_torreta"].split("/")[0].strip()),
        "recarga": recarga,
        "rotacion_torreta_arcade": rotacion,
        "penetracion_mm": penetracion,
        "masa_total": masa,
        "masa_explosivo": explosivo,
        "velocidad": velocidad,
        "depresion": 0
    }
    if "armamento_1" in tank:
        if "angulo_elevacion" in tank["armamento_1"]:
            if tank["armamento_1"]["angulo_elevacion"] is not None:
                valores["depresion"] = abs(float(tank["armamento_1"]["angulo_elevacion"].split("/")[0].strip()))

    ratings.setdefault(rating, {k: [] for k in valores.keys()})
    for k, v in valores.items():
        ratings[rating][k].append(v)

maximos = {
    rating: {k: round(max(v), 2) for k, v in campos.items()}
    for rating, campos in ratings.items()
}
        

# --- Calcular medias ---
promedios = {
    rating: {k: round(mean(v), 2) for k, v in campos.items()}
    for rating, campos in ratings.items()
}

print("PROMEDIOS")

# --- Mostrar resultado ---
for rating, campos in promedios.items():
    print(f"\nRating {rating}:")
    for k, v in campos.items():
        print(f"  {k}: {v}") 
        
print("MAXIMOS:")
        
for rating, campos in maximos.items():
    print(f"\nRating {rating}:")
    for k, v in campos.items():
        print(f"  {k}: {v}") 