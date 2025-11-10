import json
from playwright.sync_api import sync_playwright

def limpiar_texto(texto):
    return texto.replace("\n", " ").replace("\xa0", " ").strip()

def coger_texto(pagina, selector):
    elemento = pagina.locator(selector)
    return limpiar_texto(elemento.first.inner_text()) if elemento.count() > 0 else None

def fetch_data():
    url = "https://wiki.warthunder.com/unit/us_m2a4"
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome")
        pagina = navegador.new_page()
        pagina.goto(url, timeout=60000)

        datos = {}

        # === Datos generales ===
        datos["nombre"] = coger_texto(pagina, ".game-unit_title .game-unit_name")
        datos["rol"] = coger_texto(pagina, "div:has(+.game-unit_card-info_title:has-text('Main Role')) .text-truncate")
        datos["nacion"] = coger_texto(pagina, ".game-unit_card-info .text-truncate")
        rating_locator = pagina.locator(".game-unit_br-item", has_text="AB").locator(".value")
        datos["rating_arcade"] = limpiar_texto(rating_locator.first.inner_text()) if rating_locator.count() > 0 else None
        datos["tripulacion"] = coger_texto(pagina, ".game-unit_chars-line:has(.game-unit_chars-header:has-text('Crew')) .game-unit_chars-value")
        datos["visibilidad"] = coger_texto(pagina, ".game-unit_chars-header:has-text('Visibility') + .game-unit_chars-value")
        datos["peso"] = coger_texto(pagina, ".game-unit_chars-subline span:has-text('Weight') + .game-unit_chars-value span")
        datos["velocidad_max_arcade"] = coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .text-success") if pagina.locator(".game-unit_chars-subline span:has-text('Forward') + .game-unit_chars-value .text-success").count() > 0 else coger_texto(pagina, ".game-unit_chars-subline span:has-text('Forward') .game-unit_chars-value span")
        datos["marcha_atras_arcade"] = coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .text-success") if pagina.locator(".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value .text-success").count() > 0 else coger_texto(pagina, ".game-unit_chars-subline span:has-text('Backward') + .game-unit_chars-value span")
        datos["potencia_motor_arcade"] = coger_texto(pagina, ".game-unit_chars-subline span:has-text('Engine Power') + .game-unit_chars-value .text-success")

        # === Blindajes ===
        datos["blindaje_chasis"] = coger_texto(pagina, ".game-unit_chars-subline span:has-text('Hull') + .game-unit_chars-value")
        datos["blindaje_torreta"] = coger_texto(pagina, ".game-unit_chars-subline span:has-text('Turret') + .game-unit_chars-value")
        # === Armamento principal ===
        for indice, arma in enumerate(pagina.locator(".game-unit_weapon-title").all()):
            datos[f"armamento_{indice + 1}"] = {}
            datos[f"armamento_{indice + 1}"]["nombre"] = limpiar_texto(arma.first.inner_text())
        # Recogemos ángulos y rotaciones
        datos["armamento_1"]["angulo_elevacion"] = coger_texto(pagina, ".game-unit_chars-header:has-text('Vertical guidance') + .game-unit_chars-value")
        linea_torreta = pagina.locator(".game-unit_chars-line", has_text="Turret Rotation Speed")

        # Paso 2: desde ahí, subir un nivel y buscar el subline "Horizontal"
        valor_horizontal = (linea_torreta.locator("xpath=following-sibling::div[contains(@class,'game-unit_chars-subline') and span[text()='Horizontal']]//span[contains(@class,'text-success')]").all())[1]

        # Paso 3: obtener el primer valor
        rotacion_horizontal = float(valor_horizontal.first.inner_text())
        datos["armamento_1"]["rotacion_torreta_arcade"] = rotacion_horizontal

        # Tiempo de recarga
        datos["armamento_1"]["recarga"] = coger_texto(pagina, ".game-unit_chars-line:has(.game-unit_chars-header:has-text('Reload')) + .game-unit_chars-subline .game-unit_chars-value")

        # === Tipos de munición ===
        armamento = {}
        armas = pagina.locator("#weapon .game-unit_weapon")
        for indice in range(armas.count()):
            bloque_arma = armas.nth(indice)
            
            # Nombre del arma
            nombre_arma = limpiar_texto(bloque_arma.locator(".game-unit_weapon-title").first.inner_text())
            proyectiles = []

            # Expandir el acordeón del arma
            bloque_arma.locator(".accordion-button").click()

            # Iterar sobre las filas <tr> de la tabla de municiones
            for fila in bloque_arma.locator(".game-unit_belt-list tr").all():
                celdas = [limpiar_texto(t) for t in fila.locator("td").all_inner_texts() if t.strip()]
                if len(celdas) < 2:
                    continue  # saltar filas vacías o incompletas

                shell = {
                    "nombre": celdas[0],
                    "tipo": celdas[1],
                    "penetracion_mm": celdas[2:],  # el resto son valores numéricos
                }

                try:
                    # Abrir popover de la fila actual
                    boton_info = fila.locator("button").first
                    boton_info.click()

                    # Apuntar al último popover creado y esperar a que sea visible
                    popover = pagina.locator(".game-unit_popover").last
                    #popover.wait_for(state="visible", timeout=1000)

                    # Extraer datos dentro del popover
                    shell["masa_total"] = coger_texto(popover, ".game-unit_chars-header:has-text('Projectile Mass') + .game-unit_chars-value")
                    shell["velocidad_bala"] = coger_texto(popover, ".game-unit_chars-header:has-text('Muzzle Velocity') + .game-unit_chars-value")
                    shell["masa_explosivo"] = coger_texto(popover, ".game-unit_chars-header:has-text('Explosive Mass') + .game-unit_chars-value")

                    # Cerrar popover para evitar conflicto con la siguiente fila
                    try:
                        boton_info.click()
                    except:
                        pagina.keyboard.press("Escape")

                except:
                    shell["masa_total"] = None
                    shell["velocidad_bala"] = None
                    shell["masa_explosivo"] = None

                proyectiles.append(shell)

            armamento[nombre_arma] = {"municiones": proyectiles}

        datos["armamento"] = armamento



        navegador.close()
        return datos


if __name__ == "__main__":
    stats = fetch_data()
    with open("todos_los_tanques.json", "a", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)
        f.write(",\n")
    print("Datos guardados")

