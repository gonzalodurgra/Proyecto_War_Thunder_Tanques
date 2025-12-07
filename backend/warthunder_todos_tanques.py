import json
import time
from playwright.sync_api import sync_playwright
import os
import requests

def limpiar_texto(texto):
    """Limpia saltos de línea y espacios extraños del texto"""
    return texto.replace("\n", " ").replace("\xa0", " ").strip()

def coger_texto(pagina, selector):
    """Extrae texto de un elemento si existe, si no devuelve None"""
    elemento = pagina.locator(selector)
    return limpiar_texto(elemento.first.inner_text()) if elemento.count() > 0 else None

def descargar_imagen(url_img, nombre_tanque):
    """Descarga la imagen JPG del tanque en carpeta /imagenes."""
    if not url_img:
        return None

    # Crear carpeta si no existe
    os.makedirs("imagenes", exist_ok=True)

    # Quitar caracteres raros del nombre para convertirlo a archivo
    nombre_archivo = nombre_tanque.replace(" ", "_").replace("/", "_").replace("\"", "") + ".jpg"
    ruta_archivo = f"imagenes/{nombre_archivo}"

    try:
        # Descargar
        r = requests.get(url_img, timeout=20)
        if r.status_code == 200:
            with open(ruta_archivo, "wb") as f:
                f.write(r.content)
            return ruta_archivo
        else:
            print(f"Error descargando {url_img}: {r.status_code}")
            return None
    except Exception as e:
        print(f"Error al descargar imagen {url_img}: {e}")
        return None


def extraer_datos_municion(fila, pagina):
    """
    Extrae los datos de una fila de munición, incluyendo datos del popover. Devuelve el dict shell
    """
    # Leer datos básicos de la tabla
    celdas = [limpiar_texto(t) for t in fila.locator("td").all_inner_texts() if t.strip()]
    
    if len(celdas) < 2:
        return None  # Fila vacía o incompleta
    
    penetraciones = celdas[2:]
    
    penetraciones = [int(penetracion) for penetracion in penetraciones if penetracion != "—"]
    shell = {
        "nombre": celdas[0],
        "tipo": celdas[1],
        "penetracion_mm": penetraciones,
    }
    
    # Intentar extraer datos del popover, necesario para masa de bala, velocidad de bala y masa de explosivo
    try:
        boton_info = fila.locator("button").first
        boton_info.click()
        
        popover = pagina.locator(".game-unit_popover").last
        try:
            masa_total = coger_texto(popover, ".game-unit_chars-header:has-text('Projectile Mass') + .game-unit_chars-value")
            if "kg" in masa_total:
                masa_total = float(masa_total.replace("kg", "").strip()) * 1000
            elif "g" in masa_total:
                masa_total = float(masa_total.replace("g", "").strip())
        except Exception as e:
            shell["masa_total"] = None
        else:
            shell["masa_total"] = masa_total
        try:
            if coger_texto(popover, ".game-unit_chars-header:has-text('Muzzle Velocity') + .game-unit_chars-value").replace("m/s", "").strip():
                shell["velocidad_bala"] = int(coger_texto(popover, ".game-unit_chars-header:has-text('Muzzle Velocity') + .game-unit_chars-value").replace("m/s", "").replace(",", "").strip())
        except Exception as e:
            shell["velocidad_bala"] = None
        try:
            masa_explosivo = coger_texto(popover, ".game-unit_chars-header:has-text('Explosive Mass') + .game-unit_chars-value")
            if "kg" in masa_explosivo:
                masa_explosivo = float(masa_explosivo.replace("kg", "").strip()) * 1000
            elif "g" in masa_explosivo:
                masa_explosivo = float(masa_explosivo.replace("g", "").strip())
        except Exception as e:
            shell["masa_explosivo"] = None
        else:
            shell["masa_explosivo"] = masa_explosivo
        # Cerrar popover
        try:
            boton_info.click()
        except:
            pagina.keyboard.press("Escape")
            
    except Exception as e:
        print("No existen las características para el proyectil")
        shell["masa_explosivo"] = None
        shell["masa_total"] = None
        shell["velocidad_bala"] = None
    return shell


def extraer_municiones_arma(bloque_arma, pagina):
    """
    Extrae todas las municiones de un arma específica.
    """
    nombre_arma = limpiar_texto(bloque_arma.locator(".game-unit_weapon-title").first.inner_text())
    proyectiles = []
    
    # Expandir acordeón si existe
    if bloque_arma.locator(".accordion-button").count() > 0:
        bloque_arma.locator(".accordion-button").click()
    
    # Iterar sobre cada fila de munición
    for fila in bloque_arma.locator(".game-unit_belt-list tr").all():
        shell = extraer_datos_municion(fila, pagina)
        if shell:  # Solo agregar si no es None
            proyectiles.append(shell)
    
    return nombre_arma, proyectiles


def extraer_armamento(pagina):
    """
    Extrae todo el armamento del tanque, manejando setups múltiples o único.
    """
    setups = pagina.locator("#weapon .feed-filter")
    armamento_completo = {}
    
    # Determinar si hay múltiples setups o uno solo
    tiene_setups = setups.count() > 0
    num_iteraciones = setups.count() if tiene_setups else 1
    
    print(f"Setups encontrados: {num_iteraciones}")
    
    for indice_setup in range(num_iteraciones):
        # Si hay setups, hacer click en cada uno
        if tiene_setups:
            setups.nth(indice_setup).click()
            armas = pagina.locator("#weapon .game-unit_weapon").filter(has=pagina.locator(":visible"))
        else:
            armas = pagina.locator("#weapon .game-unit_weapon")
        
        armamento_setup = {}
        
        # Procesar cada arma en este setup
        for indice in range(armas.count()):
            bloque_arma = armas.nth(indice)
            nombre_arma, proyectiles = extraer_municiones_arma(bloque_arma, pagina)
            armamento_setup[nombre_arma] = {"municiones": proyectiles}
        
        # Guardar el setup
        if tiene_setups:
            armamento_completo[f"setup_{indice_setup + 1}"] = armamento_setup
        else:
            armamento_completo = armamento_setup
    
    return armamento_completo


def fetch_data(pagina):
    """
    Extrae todos los datos de un tanque individual.
    
    Organización:
    1. Datos básicos (nombre, rol, nación, rating)
    2. Características (tripulación, visibilidad, peso)
    3. Blindaje
    4. Armamento principal (ángulos, rotación, recarga)
    5. Municiones (usando la función extraer_armamento)
    """
    
    url_img = None

    selectores = [
        "img.game-unit_template-image",
        "img.game-unit_model-img",
        "img.game-unit_model_img",
        ".game-unit_model img",
        ".game-unit_page-header img"
    ]

    for sel in selectores:
        loc = pagina.locator(sel)
        if loc.count() > 0:
            src = loc.first.get_attribute("src")
            if src and src.startswith("http"):
                url_img = src
                break
    
    datos = {}
    
    # === DATOS BÁSICOS ===
    datos["nombre"] = coger_texto(pagina, ".game-unit_title .game-unit_name")
    
    if not url_img:
        print(f"⚠ No se encontró imagen del tanque en la página {pagina.url}")
    else:
        ruta_imagen = descargar_imagen(url_img, datos["nombre"])
        datos["imagen_local"] = ruta_imagen
    
    datos["rol"] = coger_texto(pagina, "div:has(+.game-unit_card-info_title:has-text('Main Role')) .text-truncate")
    datos["nacion"] = coger_texto(pagina, ".game-unit_card-info .text-truncate")
    
    rating_locator = pagina.locator(".game-unit_br-item", has_text="AB").locator(".value")
    datos["rating_arcade"] = limpiar_texto(rating_locator.first.inner_text()) if rating_locator.count() > 0 else None
    
    rating_locator = pagina.locator(".game-unit_br-item", has_text="RB").locator(".value")
    datos["rating_realista"] = limpiar_texto(rating_locator.first.inner_text()) if rating_locator.count() > 0 else None
    
    # === CARACTERÍSTICAS ===
    datos["tripulacion"] = int(coger_texto(pagina, ".game-unit_chars-line:has(.game-unit_chars-header:has-text('Crew')) .game-unit_chars-value").replace("persons", "").strip())
    datos["visibilidad"] = int(coger_texto(pagina, ".game-unit_chars-header:has-text('Visibility') + .game-unit_chars-value").replace("%", "").strip())
    datos["peso"] = float(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Weight') + .game-unit_chars-value span"))
    
    # === BLINDAJE ===
    datos["blindaje_chasis"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Hull') + .game-unit_chars-value").split("/")[0].strip())
    datos["blindaje_torreta"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Turret') + .game-unit_chars-value").split("/")[0].strip())
    
    # === MOVILIDAD (VELOCIDADES) ===
    # Buscar la sección de velocidad máxima
    # Opción 1: Buscar "Max Speed" y luego "Forward" / "Reverse"
    if pagina.locator(".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .text-success").count() > 0:
        datos["velocidad_adelante_arcade"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .text-success"))
    else:
        datos["velocidad_adelante_arcade"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value span"))
    if pagina.locator(".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .text-success").count() > 0:
        datos["velocidad_atras_arcade"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .text-success"))
    else:
        datos["velocidad_atras_arcade"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value span"))
    if pagina.locator(".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .text-success").count() > 0:
        datos["relacion_potencia_peso"] = float(coger_texto(pagina, ".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .text-success"))
    else:
        datos["relacion_potencia_peso"] = float(coger_texto(pagina, ".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value span"))
        
    if pagina.locator(".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .show-char-rb").count() > 0:
        datos["velocidad_adelante_realista"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .show-char-rb"))
    if pagina.locator(".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .show-char-rb").count() > 0:
        datos["velocidad_atras_realista"] = int(coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .show-char-rb"))
    if pagina.locator(".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .show-char-rb-mod-ref").count() > 0:
        datos["relacion_potencia_peso_realista"] = float(coger_texto(pagina, ".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .show-char-rb-mod-ref"))
    
    # === ARMAMENTO PRINCIPAL ===
    if pagina.locator(".game-unit_weapon-title").count() > 0:
        # Nombres de las armas
        if coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Vertical guidance') + .game-unit_chars-value"):
            datos["angulo_depresion"] = abs(int(coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Vertical guidance') + .game-unit_chars-value").split("/")[0].strip()))
            datos["angulo_elevacion"] = int(coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Vertical guidance') + .game-unit_chars-value").split("/")[0].strip())
        
        if coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-line:has(.game-unit_chars-header:has-text('Reload')) + .game-unit_chars-subline .game-unit_chars-value"):
            if "→" in coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-line:has(.game-unit_chars-header:has-text('Reload')) + .game-unit_chars-subline .game-unit_chars-value"):
                datos["recarga"] = float(coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-line:has(.game-unit_chars-header:has-text('Reload')) + .game-unit_chars-subline .game-unit_chars-value").split("→")[1].replace("s", "").strip())
            else:
                datos["recarga"] = float(coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-line:has(.game-unit_chars-header:has-text('Reload')) + .game-unit_chars-subline .game-unit_chars-value").replace("s", "").strip())
        
        if coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Fire Rate') + .game-unit_chars-value"):
            datos["cadencia"] = int(coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Fire Rate') + .game-unit_chars-value").replace("shots/min", "").replace(",","").strip())
        else:
            if "recarga" in datos:
                datos["cadencia"] = 1 / datos["recarga"] * 60
            else:
                datos["cadencia"] = None
        if coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-subline:has-text('Belt capacity') .game-unit_chars-value"):  
            datos["cargador"] = int(coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-subline:has-text('Belt capacity') .game-unit_chars-value").replace("rounds", "").replace("round", "").replace(",","").strip())
        else:
            datos["cargador"] = 1
        
        datos["municion_total"] = int(coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Ammunition') + .game-unit_chars-value").replace("rounds", "").replace(",","").strip())
            # Rotación de torreta (selector complejo)
        linea_torreta = pagina.locator(".game-unit_weapon:first-child .game-unit_chars-line", has_text="Turret Rotation Speed")
        selector_horizontal = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Horizontal']]//span[contains(@class,'text-success')]"
        selector_vertical = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Vertical']]//span[contains(@class,'text-success')]"
            
        if linea_torreta.locator(selector_horizontal).count() > 0:
            valores = linea_torreta.locator(selector_horizontal).all()
            if len(valores) > 1:
                rotacion_horizontal = float(valores[1].inner_text())
                datos["rotacion_torreta_horizontal_arcade"] = rotacion_horizontal
                
        if linea_torreta.locator(selector_vertical).count() > 0:
            valores = linea_torreta.locator(selector_vertical).all()
            if len(valores) > 1:
                rotacion_vertical = float(valores[1].inner_text())
                datos["rotacion_torreta_vertical_arcade"] = rotacion_vertical
                
        selector_horizontal = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Horizontal']]//span[contains(@class,'show-char-rb-mod-ref')]"
        selector_vertical = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Vertical']]//span[contains(@class,'show-char-rb-mod-ref')]"
        
        if linea_torreta.locator(selector_horizontal).count() > 0:
            valores = linea_torreta.locator(selector_horizontal).all()
            if len(valores) > 1:
                rotacion_horizontal = float(valores[1].inner_text())
                datos["rotacion_torreta_horizontal_realista"] = rotacion_horizontal
                
        if linea_torreta.locator(selector_vertical).count() > 0:
            valores = linea_torreta.locator(selector_vertical).all()
            if len(valores) > 1:
                rotacion_vertical = float(valores[1].inner_text())
                datos["rotacion_torreta_vertical_realista"] = rotacion_vertical
        
        # === MUNICIONES (código unificado) ===
        armamento = extraer_armamento(pagina)
        if armamento:
            # Si hay setups, ya viene con la estructura setup_1, setup_2, etc.
            # Si no hay setups, viene como diccionario directo
            if any(key.startswith("setup_") for key in armamento.keys()):
                # Hay setups múltiples
                for key, value in armamento.items():
                    datos[key] = value
            else:
                # Setup único
                datos["armamento"] = armamento
    
    return datos


def fetch_all_tanks():
    """
    Función principal que recorre todas las naciones y tanques.
    
    Flujo:
    1. Abre el navegador
    2. Va a la página de árboles tecnológicos
    3. Itera sobre cada nación, para depuración simplemente
    4. Para cada nación, obtiene todos los tanques
    5. Abre cada tanque en una nueva pestaña y extrae sus datos
    6. Guarda todo en una lista
    """
    base_url = "https://wiki.warthunder.com/"
    resultados = []
    
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome")
        pagina = navegador.new_page()
        pagina.goto(base_url, timeout=90000)
        
        # Ir a árboles tecnológicos
        pagina.goto("https://wiki.warthunder.com/ground?v=t&t_c=usa", timeout=90000)
        pagina.wait_for_selector("#wt-tree-tabs .navtabs_item", timeout=15000)
        
        naciones = pagina.locator("#wt-tree-tabs .navtabs_item")
        print(f"Encontradas {naciones.count()} naciones\n")
        
        for i in range(naciones.count()):
            nacion = naciones.nth(i)
            nombre_nacion = limpiar_texto(nacion.inner_text())
            print(f"=== Nación: {nombre_nacion} ===")
            nacion.click()
            
            # Obtener tanques de la nación actual
            arbol = pagina.locator(".unit-tree").filter(has=pagina.locator(":visible"))
            tanques = arbol.locator(".wt-tree_item-link")
            print(f"  {tanques.count()} tanques encontrados")
            
            for t in range(tanques.count()):
                enlace_tanque = tanques.nth(t)
                href = enlace_tanque.get_attribute("href")
                
                if not href or not href.startswith("/unit/"):
                    continue
                
                url_tanque = f"https://wiki.warthunder.com{href}"
                print(f"  Procesando {url_tanque}")
                
                # Abrir tanque en nueva pestaña
                subpagina = navegador.new_page()
                subpagina.goto(url_tanque, timeout=90000)
                
                try:
                    data_tanque = fetch_data(subpagina)
                    resultados.append(data_tanque)
                except Exception as e:
                    print(f"Error procesando {url_tanque}: {e}")
                
                subpagina.close()
            
            print()  # Línea en blanco entre naciones
        
        navegador.close()
    
    return resultados


if __name__ == "__main__":
    print("Iniciando scraping de War Thunder Wiki...\n")
    all_data = fetch_all_tanks()
    
    with open("tanques.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n Datos guardados: {len(all_data)} tanques procesados")