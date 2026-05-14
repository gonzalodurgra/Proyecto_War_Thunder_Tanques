from aiohttp.web import head
import json
import time
import asyncio
from playwright.async_api import async_playwright
import os
import httpx
from pathlib import Path

def limpiar_texto(texto):
    """Limpia saltos de línea y espacios extraños del texto"""
    return texto.replace("\n", " ").replace("\xa0", " ").strip()

async def coger_texto(pagina, selector):
    """Extrae texto de un elemento si existe, si no devuelve None"""
    elemento = pagina.locator(selector)
    if await elemento.count() > 0:
        texto = await elemento.first.inner_text()
        return limpiar_texto(texto)
    return None

async def descargar_imagen(url_img, nombre_tanque):
    """Descarga la imagen JPG del tanque en carpeta /imagenes usando httpx."""
    if not url_img:
        return None
    
    BASE_DIR = Path(__file__).resolve().parent
    IMAGENES = BASE_DIR / "imagenes"

    # Crear carpeta si no existe
    os.makedirs(IMAGENES, exist_ok=True)

    # Quitar caracteres raros del nombre para convertirlo a archivo
    nombre_archivo = nombre_tanque.replace(" ", "_").replace("/", "_").replace("\"", "") + ".jpg"
    ruta_archivo: Path = IMAGENES / nombre_archivo

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url_img, timeout=20.0)
            if r.status_code == 200:
                with open(ruta_archivo, "wb") as f:
                    f.write(r.content)
                    print(f"Descargada: {nombre_archivo}")
                return str(ruta_archivo.relative_to(Path(__file__).resolve().parent)).replace("\\", "/")
            else:
                print(f"Error descargando {url_img}: {r.status_code}")
                return None
    except Exception as e:
        print(f"Error al descargar imagen {url_img}: {e}")
        return None


async def extraer_datos_municion(fila, pagina):
    """
    Extrae los datos de una fila de munición, incluyendo datos del popover. Devuelve el dict shell
    """
    # Leer datos básicos de la tabla
    textos_celdas = await fila.locator("td").all_inner_texts()
    celdas = [limpiar_texto(t) for t in textos_celdas if t.strip()]
    
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
        await boton_info.click()
        
        popover = pagina.locator(".game-unit_popover").last
        try:
            masa_total = await coger_texto(popover, ".game-unit_chars-header:has-text('Projectile Mass') + .game-unit_chars-value")
            if masa_total and "kg" in masa_total:
                masa_total = float(masa_total.replace("kg", "").strip()) * 1000
            elif masa_total and "g" in masa_total:
                masa_total = float(masa_total.replace("g", "").strip())
        except:
            shell["masa_total"] = None
        else:
            shell["masa_total"] = masa_total

        try:
            velocidad_texto = await coger_texto(popover, ".game-unit_chars-header:has-text('Muzzle Velocity') + .game-unit_chars-value")
            if velocidad_texto and velocidad_texto.replace("m/s", "").strip():
                shell["velocidad_bala"] = int(velocidad_texto.replace("m/s", "").replace(",", "").strip())
        except:
            shell["velocidad_bala"] = None

        try:
            masa_explosivo = await coger_texto(popover, ".game-unit_chars-header:has-text('Explosive Mass') + .game-unit_chars-value")
            if masa_explosivo and "kg" in masa_explosivo:
                masa_explosivo = float(masa_explosivo.replace("kg", "").strip()) * 1000
            elif masa_explosivo and "g" in masa_explosivo:
                masa_explosivo = float(masa_explosivo.replace("g", "").strip())
        except:
            shell["masa_explosivo"] = None
        else:
            shell["masa_explosivo"] = masa_explosivo

        # Cerrar popover
        try:
            await boton_info.click()
        except:
            if not pagina.is_closed():
                await pagina.keyboard.press("Escape")
            
    except Exception:
        # print("No existen las características para el proyectil")
        shell["masa_explosivo"] = None
        shell["masa_total"] = None
        shell["velocidad_bala"] = None
    return shell


async def extraer_municiones_arma(bloque_arma, pagina):
    """
    Extrae todas las municiones de un arma específica.
    """
    nombre_arma_texto = await bloque_arma.locator(".game-unit_weapon-title").first.inner_text()
    nombre_arma = limpiar_texto(nombre_arma_texto)
    proyectiles = []
    
    # Expandir acordeón si existe
    if await bloque_arma.locator(".accordion-button").count() > 0:
        await bloque_arma.locator(".accordion-button").click()
    
    # Iterar sobre cada fila de munición
    filas = await bloque_arma.locator(".game-unit_belt-list tr").all()
    for fila in filas:
        shell = await extraer_datos_municion(fila, pagina)
        if shell:  # Solo agregar si no es None
            proyectiles.append(shell)
    
    return nombre_arma, proyectiles


async def extraer_armamento(pagina):
    """
    Extrae todo el armamento del tanque, manejando setups múltiples o único.
    """
    setups = pagina.locator("#weapon .feed-filter")
    armamento_completo = {}
    
    # Determinar si hay múltiples setups o uno solo
    num_setups = await setups.count()
    tiene_setups = num_setups > 0
    num_iteraciones = num_setups if tiene_setups else 1
    
    print(f"Setups encontrados: {num_iteraciones}")
    
    for indice_setup in range(num_iteraciones):
        # Si hay setups, hacer click en cada uno
        if tiene_setups:
            await setups.nth(indice_setup).click()
            armas = pagina.locator("#weapon .game-unit_weapon").filter(has=pagina.locator(":visible"))
        else:
            armas = pagina.locator("#weapon .game-unit_weapon")
        
        armamento_setup = {}
        
        # Procesar cada arma en este setup
        num_armas = await armas.count()
        for indice in range(num_armas):
            bloque_arma = armas.nth(indice)
            nombre_arma, proyectiles = await extraer_municiones_arma(bloque_arma, pagina)
            armamento_setup[nombre_arma] = {"municiones": proyectiles}
        
        # Guardar el setup
        if tiene_setups:
            armamento_completo[f"setup_{indice_setup + 1}"] = armamento_setup
        else:
            armamento_completo = armamento_setup
    
    return armamento_completo


async def fetch_data(pagina):
    """
    Extrae todos los datos de un tanque individual.
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
        try:
            # Esperar un poco a que la imagen aparezca (lazy loading)
            await loc.first.wait_for(state="attached", timeout=2000)
        except:
            pass

        if await loc.count() > 0:
            src = await loc.first.get_attribute("src")
            if src and src.startswith("http"):
                url_img = src
                break
    
    datos = {}
    
    # === DATOS BÁSICOS ===
    datos["nombre"] = await coger_texto(pagina, ".game-unit_title .game-unit_name")
    
    if not url_img:
        print(f"⚠ No se encontró imagen del tanque en la página {pagina.url}")
    else:
        ruta_imagen = await descargar_imagen(url_img, datos["nombre"])
        datos["imagen_local"] = ruta_imagen
    
    datos["rol"] = await coger_texto(pagina, "div:has(+.game-unit_card-info_title:has-text('Main Role')) .text-truncate")
    datos["nacion"] = await coger_texto(pagina, ".game-unit_card-info .text-truncate")
    
    rating_locator = pagina.locator(".game-unit_br-item", has_text="AB").locator(".value")
    if await rating_locator.count() > 0:
        texto_rating = await rating_locator.first.inner_text()
        datos["rating_arcade"] = float(limpiar_texto(texto_rating))
    else:
        datos["rating_arcade"] = None
    
    rating_locator = pagina.locator(".game-unit_br-item", has_text="RB").locator(".value")
    if await rating_locator.count() > 0:
        texto_rating = await rating_locator.first.inner_text()
        datos["rating_realista"] = float(limpiar_texto(texto_rating))
    else:
        datos["rating_realista"] = None
    
    # === CARACTERÍSTICAS ===
    crew_text = await coger_texto(pagina, ".game-unit_chars-line:has(.game-unit_chars-header:has-text('Crew')) .game-unit_chars-value")
    if crew_text:
        datos["tripulacion"] = int(crew_text.replace("persons", "").strip())
    
    vis_text = await coger_texto(pagina, ".game-unit_chars-header:has-text('Visibility') + .game-unit_chars-value")
    if vis_text:
        datos["visibilidad"] = int(vis_text.replace("%", "").strip())
        
    peso_text = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Weight') + .game-unit_chars-value span")
    if peso_text:
        datos["peso"] = float(peso_text)
    
    # === BLINDAJE ===
    blindaje_chasis_text = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Hull') + .game-unit_chars-value")
    if blindaje_chasis_text:
        datos["blindaje_chasis"] = int(blindaje_chasis_text.split("/")[0].strip())
        
    blindaje_torreta_text = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Turret') + .game-unit_chars-value")
    if blindaje_torreta_text:
        datos["blindaje_torreta"] = int(blindaje_torreta_text.split("/")[0].strip())
    
    # === MOVILIDAD (VELOCIDADES) ===
    if await pagina.locator(".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .text-success").count() > 0:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .text-success")
        datos["velocidad_adelante_arcade"] = int(texto_vel)
    else:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value span")
        if texto_vel:
            datos["velocidad_adelante_arcade"] = int(texto_vel)
    
    if await pagina.locator(".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .text-success").count() > 0:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .text-success")
        datos["velocidad_atras_arcade"] = int(texto_vel)
    else:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value span")
        if texto_vel:
            datos["velocidad_atras_arcade"] = int(texto_vel)
    
    if await pagina.locator(".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .text-success").count() > 0:
        texto_pwr = await coger_texto(pagina, ".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .text-success")
        datos["relacion_potencia_peso"] = float(texto_pwr)
    else:
        texto_pwr = await coger_texto(pagina, ".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value span")
        if texto_pwr:
            datos["relacion_potencia_peso"] = float(texto_pwr)
        
    if await pagina.locator(".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .show-char-rb").count() > 0:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .show-char-rb")
        datos["velocidad_adelante_realista"] = int(texto_vel)
    else:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value span")
        if texto_vel:
            datos["velocidad_adelante_realista"] = int(texto_vel)
        
    if await pagina.locator(".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .show-char-rb").count() > 0:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .show-char-rb")
        datos["velocidad_atras_realista"] = int(texto_vel)
    else:
        texto_vel = await coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value span")
        if texto_vel:
            datos["velocidad_atras_realista"] = int(texto_vel)
        
    if await pagina.locator(".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .show-char-rb-mod-ref").count() > 0:
        texto_pwr = await coger_texto(pagina, ".game-unit_chars-line span:has-text('Power-to-weight ratio') + .game-unit_chars-value .show-char-rb-mod-ref")
        datos["relacion_potencia_peso_realista"] = float(texto_pwr)
    
    # === ARMAMENTO PRINCIPAL ===
    if await pagina.locator(".game-unit_weapon-title").count() > 0:
        # Nombres de las armas
        vert_guidance = await coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Vertical guidance') + .game-unit_chars-value")
        if vert_guidance:
            datos["angulo_depresion"] = abs(int(vert_guidance.split("/")[0].strip()))
            datos["angulo_elevacion"] = int(vert_guidance.split("/")[1].replace("°", "").strip())
        
        reload_text = await coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-line:has(.game-unit_chars-header:has-text('Reload')) + .game-unit_chars-subline .game-unit_chars-value")
        if reload_text:
            datos["recarga"] = float(reload_text.split("→")[1].replace("s", "").strip())
        
        reload_text_base = await coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-line:has(.game-unit_chars-header:has-text('Reload')) .game-unit_chars-value")
        if reload_text_base:
            datos["recarga"] = float(reload_text_base.replace("s", "").strip())
        
        fire_rate = await coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Fire Rate') + .game-unit_chars-value")
        if fire_rate:
            datos["cadencia"] = int(fire_rate.replace("shots/min", "").replace(",","").strip())
        else:
            if "recarga" in datos:
                datos["cadencia"] = 1 / datos["recarga"] * 60
            else:
                datos["cadencia"] = None
        
        belt_cap = await coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-subline:has-text('Belt capacity') .game-unit_chars-value")
        if belt_cap:  
            datos["cargador"] = int(belt_cap.replace("rounds", "").replace("round", "").replace(",","").strip())
        else:
            datos["cargador"] = 1
        
        ammunition = await coger_texto(pagina, ".game-unit_weapon:first-child .game-unit_chars-header:has-text('Ammunition') + .game-unit_chars-value")
        if ammunition:
            datos["municion_total"] = int(ammunition.replace("rounds", "").replace(",","").strip())
            
        # Rotación de torreta (selector complejo)
        linea_torreta = pagina.locator(".game-unit_weapon:first-child .game-unit_chars-line", has_text="Turret Rotation Speed")
        selector_horizontal = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Horizontal']]//span[contains(@class,'text-success')]"
        selector_vertical = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Vertical']]//span[contains(@class,'text-success')]"
            
        if await linea_torreta.locator(selector_horizontal).count() > 0:
            valores = await linea_torreta.locator(selector_horizontal).all()
            if len(valores) > 1:
                rotacion_horizontal = float(await valores[1].inner_text())
                datos["rotacion_torreta_horizontal_arcade"] = rotacion_horizontal
                
        if await linea_torreta.locator(selector_vertical).count() > 0:
            valores = await linea_torreta.locator(selector_vertical).all()
            if len(valores) > 1:
                rotacion_vertical = float(await valores[1].inner_text())
                datos["rotacion_torreta_vertical_arcade"] = rotacion_vertical
                
        selector_horizontal_rb = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Horizontal']]//span[contains(@class,'show-char-rb-mod-ref')]"
        selector_vertical_rb = "xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Vertical']]//span[contains(@class,'show-char-rb-mod-ref')]"
        
        if await linea_torreta.locator(selector_horizontal_rb).count() > 0:
            valores = await linea_torreta.locator(selector_horizontal_rb).all()
            if len(valores) > 1:
                rotacion_horizontal = float(await valores[1].inner_text())
                datos["rotacion_torreta_horizontal_realista"] = rotacion_horizontal
                
        if await linea_torreta.locator(selector_vertical_rb).count() > 0:
            valores = await linea_torreta.locator(selector_vertical_rb).all()
            if len(valores) > 1:
                rotacion_vertical = float(await valores[1].inner_text())
                datos["rotacion_torreta_vertical_realista"] = rotacion_vertical
        
        # === MUNICIONES (código unificado) ===
        armamento = await extraer_armamento(pagina)
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


async def procesar_tanque(navegador, url_tanque, semaforo):
    """Procesa un tanque individual con control de concurrencia."""
    async with semaforo:
        subpagina = await navegador.new_page()
        try:
            # Añadir un delay aleatorio pequeño para evitar detección
            await asyncio.sleep(1) 
            await subpagina.goto(url_tanque, timeout=90000, wait_until="domcontentloaded")
            # Esperar a que la red esté tranquila para asegurar carga de imágenes
            await subpagina.wait_for_load_state("networkidle", timeout=15000)
            return await fetch_data(subpagina)
        except Exception as e:
            print(f"Error procesando {url_tanque}: {e}")
            return None
        finally:
            if not subpagina.is_closed():
                await subpagina.close()

async def fetch_all_tanks():
    """
    Función principal que recorre todas las naciones y tanques.
    """
    base_url = "https://wiki.warthunder.com/"
    resultados = []
    semaforo = asyncio.Semaphore(3)  # Reducido a 3 para evitar bloqueos por exceso de peticiones
    
    async with async_playwright() as p:
        # Añadir User-Agent para parecer un navegador real
        navegador = await p.chromium.launch(
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            headless=True
        )
        contexto = await navegador.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        pagina = await contexto.new_page()
        await pagina.goto(base_url, timeout=90000)
        
        # Ir a árboles tecnológicos
        await pagina.goto("https://wiki.warthunder.com/ground?v=t&t_c=usa", timeout=90000)
        await pagina.wait_for_selector("#wt-tree-tabs .navtabs_item", timeout=15000)
        
        naciones = pagina.locator("#wt-tree-tabs .navtabs_item")
        num_naciones = await naciones.count()
        print(f"Encontradas {num_naciones} naciones\n")
        
        for i in range(num_naciones):
            nacion = naciones.nth(i)
            nombre_nacion = limpiar_texto(await nacion.inner_text())
            print(f"=== Nación: {nombre_nacion} ===")
            await nacion.click()
            
            # Obtener tanques de la nación actual
            arbol = pagina.locator(".unit-tree").filter(has=pagina.locator(":visible"))
            tanques = arbol.locator(".wt-tree_item-link")
            num_tanques = await tanques.count()
            print(f"  {num_tanques} tanques encontrados")
            
            tasks = []
            for t in range(num_tanques):
                enlace_tanque = tanques.nth(t)
                href = await enlace_tanque.get_attribute("href")
                
                if not href or not href.startswith("/unit/"):
                    continue
                
                url_tanque = f"https://wiki.warthunder.com{href}"
                tasks.append(procesar_tanque(contexto, url_tanque, semaforo))
                # Pequeña pausa entre lanzamientos de tareas para no saturar
                # await asyncio.sleep(0.2)
            
            # Ejecutar descargas y scraping en paralelo
            resultados_nacion = await asyncio.gather(*tasks)
            # Filtrar resultados None (errores)
            resultados.extend([r for r in resultados_nacion if r])
            
            print()  # Línea en blanco entre naciones
        
        await navegador.close()
    
    return resultados


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    TANQUES_JSON = BASE_DIR / "tanques.json"
    print("Iniciando scraping de War Thunder Wiki...\n")
    all_data = asyncio.run(fetch_all_tanks())
    
    with open(TANQUES_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n Datos guardados: {len(all_data)} tanques procesados")