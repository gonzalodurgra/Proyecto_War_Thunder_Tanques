"""
BOT DE DISCORD PARA WAR THUNDER
================================
Este bot se comunica con la API de War Thunder para proporcionar
estadísticas y comparaciones de tanques directamente en Discord.

REQUISITOS:
pip install discord.py requests python-dotenv aiohttp

CONFIGURACIÓN:
Crea un archivo .env con:
DISCORD_TOKEN=tu_token_de_discord
API_URL=http://localhost:8000
"""

import discord
from discord.ext import commands
from discord import app_commands
import requests
import statistics
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
import aiohttp
import asyncio

# ====================================================================
# PASO 1: Cargar variables de entorno
# ====================================================================
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

if not DISCORD_TOKEN:
    raise ValueError("⚠️ DISCORD_TOKEN no encontrado en .env")

print(f"🔗 Bot conectándose a API: {BACKEND_URL}")

# ====================================================================
# PASO 2: Configurar el bot
# ====================================================================
# Intents son los permisos que necesita el bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Crear el bot con prefijo ! para comandos tradicionales
bot = commands.Bot(command_prefix='!', intents=intents)

# ====================================================================
# PASO 3: Clase para manejar peticiones a la API
# ====================================================================
class WarThunderAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        timeout = aiohttp.ClientTimeout(
            total=None,
            sock_connect=8,
            sock_read=8
        )
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self.session:
            await self.session.close()

    async def _get(self, endpoint: str, retries: int = 3):
        if not self.session:
            raise RuntimeError("API session not started")

        url = f"{self.base_url}{endpoint}"

        for attempt in range(retries):
            try:
                async with asyncio.timeout(12):
                    async with self.session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.json()
            except (asyncio.TimeoutError, aiohttp.ClientError):
                if attempt < retries - 1:
                    await asyncio.sleep(3)

        return None

    async def obtener_todos_tanques(self):
        return await self._get("/tanques/") or []

    async def obtener_tanque_por_id(self, tanque_id: str):
        return await self._get(f"/tanques/{tanque_id}")

    async def obtener_tanques_por_nacion(self, nacion: str):
        return await self._get(f"/tanques/nacion/{nacion}") or []

    async def buscar_tanque_por_nombre(self, nombre: str):
        tanques = await self.obtener_todos_tanques()
        nombre = nombre.lower()

        for t in tanques:
            if t["nombre"].lower() == nombre:
                return t

        for t in tanques:
            if nombre in t["nombre"].lower():
                return t

        return None
    
    async def obtener_stats(self, br_min=None, br_max=None, modo="realista"):
        params = {"modo": modo}
        if br_min is not None:
            params["br_min"] = br_min
        if br_max is not None:
            params["br_max"] = br_max

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/stats", params=params) as r:
                return await r.json()



# Instancia de la API
api = WarThunderAPI(BACKEND_URL)

# ====================================================================
# PASO 4: Funciones auxiliares para cálculos estadísticos
# ====================================================================

def calcular_media_caracteristica(tanques: List[Dict], caracteristica: str) -> float:
    """Calcula la media de una característica numérica."""
    valores = []
    for tanque in tanques:
        valor = tanque.get(caracteristica)
        if valor is not None and isinstance(valor, (int, float)):
            valores.append(valor)
    
    return round(statistics.mean(valores), 2) if valores else 0

def calcular_estadisticas_completas(tanques: List[Dict], caracteristica: str) -> Dict:
    """Calcula estadísticas completas (media, min, max, mediana) de una característica."""
    valores = []
    for tanque in tanques:
        valor = tanque.get(caracteristica)
        if valor is not None and isinstance(valor, (int, float)):
            valores.append(valor)
    
    if not valores:
        return {'media': 0, 'min': 0, 'max': 0, 'mediana': 0}
    
    return {
        'media': round(statistics.mean(valores), 2),
        'min': min(valores),
        'max': max(valores),
        'mediana': round(statistics.median(valores), 2)
    }

def obtener_top_tanques(tanques: List[Dict], caracteristica: str, limite: int = 5) -> List[Dict]:
    """Obtiene los mejores tanques según una característica."""
    tanques_validos = [t for t in tanques if t.get(caracteristica) is not None]
    tanques_ordenados = sorted(
        tanques_validos, 
        key=lambda x: x.get(caracteristica, 0), 
        reverse=True
    )
    return tanques_ordenados[:limite]

def obtener_armamentos(tanque):
    """
    Devuelve un dict con:
    {
        "Armamento principal": {...}
        o
        "Setup 1": {...},
        "Setup 2": {...}
    }
    """
    if "armamento" in tanque:
        return {"Armamento principal": tanque["armamento"]}

    setups = {}
    for key, value in tanque.items():
        if key.startswith("setup_"):
            setups[key.replace("_", " ").title()] = value

    return setups

def formatear_armamento(armas):
    texto = ""

    for arma, datos in armas.items():
        texto += f"▶️ **{arma}**\n"

        for mun in datos.get("municiones", []):
            texto += f"• *{mun['nombre']}* ({mun['tipo']})\n"

            if mun["penetracion_mm"]:
                pen = " / ".join(map(str, mun["penetracion_mm"]))
                texto += f"  ↳ Pen: {pen} mm\n"

            if mun["velocidad_bala"]:
                texto += f"  ↳ Vel: {mun['velocidad_bala']} m/s\n"
                
            if mun["masa_total"]:
                texto += f"  ↳ Masa: {mun['masa_total']} g\n"

            if mun["masa_explosivo"]:
                texto += f"  ↳ Explosivo: {mun['masa_explosivo']} g\n"

        texto += "\n"

    return texto[:1024]  # límite Discord

# ===============================================
# FUNCIONES AUXILIARES PARA FILTRAR POR BR
# ===============================================

def filtrar_por_br(tanques, br_min=None, br_max=None, modo='realista'):
    """
    Filtra tanques según un rango de BR.
    
    Parámetros:
    - tanques: lista de tanques a filtrar
    - br_min: BR mínimo (None = sin límite inferior)
    - br_max: BR máximo (None = sin límite superior)
    - modo: 'realista' o 'arcade'
    
    Retorna: lista de tanques filtrados
    """
    # Decidir qué campo de BR usar según el modo
    campo_br = 'rating_realista' if modo == 'realista' else 'rating_arcade'
    
    # Lista para guardar los tanques que cumplan el filtro
    tanques_filtrados = []
    
    # Revisar cada tanque uno por uno
    for tanque in tanques:
        # Obtener el BR del tanque (si no existe, usar 0)
        br = tanque.get(campo_br, 0)
        
        # Verificar si el tanque cumple con el rango
        cumple_minimo = True if br_min is None else br >= br_min
        cumple_maximo = True if br_max is None else br <= br_max
        
        # Si cumple ambas condiciones, agregarlo a la lista
        if cumple_minimo and cumple_maximo:
            tanques_filtrados.append(tanque)
    
    return tanques_filtrados


def parsear_rango_br(texto_br):
    """
    Convierte un texto como "3-5" o "3.0-5.7" en números.
    
    Parámetros:
    - texto_br: string con el rango (ej: "3-5", "3.0-5.7")
    
    Retorna: tupla (br_min, br_max) o (None, None) si hay error
    """
    try:
        # Dividir el texto por el guión
        partes = texto_br.split('-')
        
        # Convertir a números flotantes
        br_min = float(partes[0])
        br_max = float(partes[1])
        
        return br_min, br_max
    except:
        # Si hay algún error, retornar None
        return None, None

# ====================================================================
# PASO 5: Eventos del bot
# ====================================================================

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    await api.start()

    try:
        synced = await bot.tree.sync()
        print(f'🔄 {len(synced)} comandos sincronizados')
    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')
        
@bot.event
async def on_close():
    await api.close()

@bot.event
async def on_message(message):
    """Se ejecuta cuando alguien envía un mensaje."""
    # Ignorar mensajes del propio bot
    if message.author == bot.user:
        return
    
    # Procesar comandos
    await bot.process_commands(message)

# ====================================================================
# PASO 6: Comandos del bot
# ====================================================================

# -------------------- COMANDO: !ping --------------------
@bot.command(name='ping')
async def ping(ctx):
    """Verifica que el bot esté funcionando."""
    await ctx.send(f'🏓 Pong! Latencia: {round(bot.latency * 1000)}ms')

# -------------------- COMANDO: !stats --------------------

@bot.command(name="stats")
async def stats(ctx, rango_br: str = None, modo: str = "realista"):
    await ctx.send("📊 Calculando estadísticas...")

    br_min, br_max = parsear_rango_br(rango_br) if rango_br else (None, None)
    data = await api.obtener_stats(br_min, br_max, modo)

    if data["total"] == 0:
        await ctx.send("❌ No hay tanques en ese rango")
        return

    embed = discord.Embed(
        title="📊 Estadísticas War Thunder",
        description=f"Tanques analizados: {data['total']}",
        color=discord.Color.blue()
    )

    embed.add_field(name="⭐ BR Medio", value=data["media_br"])
    embed.add_field(name="🛡 Blindaje Torreta", value=data["blindaje_torreta"])
    embed.add_field(name="🏎 Velocidad", value=data["velocidad"])

    await ctx.send(embed=embed)


# -------------------- COMANDO: !tanque --------------------
@bot.command(name='tanque')
async def tanque(ctx, *, nombre: str):
    """
    Busca información detallada de un tanque.
    Uso: !tanque nombre_del_tanque
    """
    await ctx.send(f'🔍 Buscando tanque: **{nombre}**...')
    
    tanque = await api.buscar_tanque_por_nombre(nombre)
    
    if not tanque:
        await ctx.send(f'❌ No se encontró el tanque: **{nombre}**')
        return
    
    # Crear embed con información del tanque
    embed = discord.Embed(
        title=f"🎮 {tanque['nombre']}",
        description=f"**Nación:** {tanque['nacion']} | **Rating:** {tanque['rating_arcade']}/{tanque['rating_realista']}",
        color=discord.Color.green()
    )
    
    # Información general
    embed.add_field(
        name="ℹ️ General",
        value=f"**Rol:** {tanque['rol']}\n**Tripulación:** {tanque['tripulacion']}\n**Peso:** {tanque['peso']} t\n**Visibilidad:** {tanque['visibilidad']} %",
        inline=True
    )
    
    # Blindaje
    embed.add_field(
        name="🛡️ Blindajes frontales",
        value=f"**Chasis:** {tanque['blindaje_chasis']} mm\n**Torreta:** {tanque['blindaje_torreta']} mm",
        inline=True
    )
    
    # Movilidad
    embed.add_field(
        name="🏎️ Movilidad",
        value=f"**Velocidad:** {tanque['velocidad_adelante_arcade']}/{tanque['velocidad_adelante_realista']} km/h\n**Marcha atrás:** {tanque['velocidad_atras_arcade']}/{tanque['velocidad_atras_realista']} km/h\n**Potencia/Peso:** {tanque['relacion_potencia_peso']}/{tanque['relacion_potencia_peso_realista']} hp/t",
        inline=True
    )
    
    # Armamento
    embed.add_field(
        name="🔫 Armamento",
        value=f"**Recarga:** {tanque['recarga']} s\n**Tamaño del cargador** {tanque['cargador']}\n**Cadencia:** {tanque['cadencia']:.1f} disp/min\n**Munición:** {tanque['municion_total']}\n**Rotación horizontal:** {tanque['rotacion_torreta_horizontal_arcade']}/{tanque['rotacion_torreta_horizontal_realista']} º/s\n**Rotación vertical:** {tanque['rotacion_torreta_vertical_arcade']}/{tanque['rotacion_torreta_vertical_realista']} º/s",
        inline=True
    )
    
    # Ángulos
    embed.add_field(
        name="📐 Ángulos",
        value=f"**Depresión:** {tanque['angulo_depresion']} °\n**Elevación:** {tanque['angulo_elevacion']} °",
        inline=True
    )
    
    armamentos = obtener_armamentos(tanque)

    for nombre_setup, armas in armamentos.items():
        embed.add_field(
            name=f"🔫 {nombre_setup}",
            value=formatear_armamento(armas),
            inline=False
        )
        
    embed.set_thumbnail(url=f"{BACKEND_URL}/imagenes/{tanque['imagen_local']}")

    await ctx.send(embed=embed)

# -------------------- COMANDO: !comparar --------------------
@bot.command(name='comparar')
async def comparar(ctx, tanque1: str, tanque2: str):
    """
    Compara dos tanques lado a lado.
    Uso: !comparar tanque1 tanque2
    """
    await ctx.send(f'⚖️ Comparando **{tanque1}** vs **{tanque2}**...')
    
    t1 = await api.buscar_tanque_por_nombre(tanque1)
    t2 = await api.buscar_tanque_por_nombre(tanque2)
    
    if not t1:
        await ctx.send(f'❌ No se encontró: **{tanque1}**')
        return
    if not t2:
        await ctx.send(f'❌ No se encontró: **{tanque2}**')
        return
    
    # Crear embed de comparación
    embed = discord.Embed(
        title="⚖️ Comparación de Tanques",
        description=f"**{t1['nombre']}** vs **{t2['nombre']}**",
        color=discord.Color.gold()
    )
    
    # Comparar características
    caracteristicas = [
        ('blindaje_chasis', '🛡️ Blindaje Chasis', 'mm'),
        ('blindaje_torreta', '🛡️ Blindaje Torreta', 'mm'),
        ('velocidad_adelante_arcade', '🏎️ Velocidad', 'km/h'),
        ('relacion_potencia_peso', '⚡ Potencia/Peso', 'hp/t'),
        ('recarga', '🔫 Recarga', 's'),
        ('cadencia', '🔫 Cadencia', 'disp/min')
    ]
    
    for campo, nombre, unidad in caracteristicas:
        valor1 = t1.get(campo, 0)
        valor2 = t2.get(campo, 0)
        
        # Determinar cuál es mejor (para recarga, menor es mejor)
        if campo == 'recarga':
            mejor = '🟢' if valor1 < valor2 else ('🔴' if valor1 > valor2 else '🟡')
            peor = '🔴' if valor1 < valor2 else ('🟢' if valor1 > valor2 else '🟡')
        else:
            mejor = '🟢' if valor1 > valor2 else ('🔴' if valor1 < valor2 else '🟡')
            peor = '🔴' if valor1 > valor2 else ('🟢' if valor1 < valor2 else '🟡')
        
        embed.add_field(
            name=nombre,
            value=f"{mejor} {valor1}{unidad}\n{peor} {valor2}{unidad}",
            inline=True
        )
    
    await ctx.send(embed=embed)

# -------------------- COMANDO: !nacion --------------------
@bot.command(name='nacion')
async def nacion(ctx, nombre_nacion: str, rango_br: str = None, modo: str = 'realista'):
    """
    Muestra estadísticas de una nación específica.
    
    Uso: 
    - !nacion USA                   (todos los tanques USA)
    - !nacion USA 3-5               (tanques USA BR 3.0-5.0 realista)
    - !nacion Germany 5-7 arcade    (tanques Germany BR 5.0-7.0 arcade)
    """
    await ctx.send(f'🌍 Obteniendo datos de **{nombre_nacion}**...')
    
    # PASO 1: Obtener tanques de la nación
    tanques = await api.obtener_tanques_por_nacion(nombre_nacion)
    
    if not tanques:
        await ctx.send(f'❌ No se encontraron tanques de: **{nombre_nacion}**')
        return
    
    # PASO 2: Filtrar por BR si se especificó
    br_min, br_max = None, None
    if rango_br:
        br_min, br_max = parsear_rango_br(rango_br)
        
        if br_min is None:
            await ctx.send('❌ Rango de BR inválido. Usa formato: `3-5` o `3.0-5.7`')
            return
        
        tanques = filtrar_por_br(tanques, br_min, br_max, modo)
        
        if not tanques:
            await ctx.send(f'❌ No hay tanques de {nombre_nacion} en BR {br_min}-{br_max} ({modo})')
            return
    
    # PASO 3: Calcular estadísticas
    total = len(tanques)
    stats_blindaje = calcular_estadisticas_completas(tanques, 'blindaje_torreta')
    if modo == "realista":
        stats_velocidad = calcular_estadisticas_completas(tanques, 'velocidad_adelante_realista')
    else:
        stats_velocidad = calcular_estadisticas_completas(tanques, 'velocidad_adelante_arcade')
    
    # NUEVO: Calcular estadísticas de BR
    campo_br = 'rating_realista' if modo == 'realista' else 'rating_arcade'
    stats_br = calcular_estadisticas_completas(tanques, campo_br)
    
    # Top 3 tanques por blindaje y velocidad
    top_blindaje = obtener_top_tanques(tanques, 'blindaje_torreta', 3)
    if modo == "realista":
        top_velocidad = obtener_top_tanques(tanques, 'velocidad_adelante_realista', 3)
    else:
        top_velocidad = obtener_top_tanques(tanques, 'velocidad_adelante_arcade', 3)
    
    # PASO 4: Crear embed
    titulo = f"🌍 Estadísticas de {nombre_nacion}"
    if rango_br:
        titulo += f" (BR {br_min}-{br_max} {modo})"
    
    embed = discord.Embed(
        title=titulo,
        description=f"Análisis de {total} tanques",
        color=discord.Color.purple()
    )
    
    # Mostrar rango de BR
    embed.add_field(
        name="⭐ Battle Rating",
        value=f"**Media:** {stats_br['media']}\n**Min:** {stats_br['min']}\n**Max:** {stats_br['max']}",
        inline=True
    )
    
    # Mostrar estadísticas de blindaje
    embed.add_field(
        name="🛡️ Blindaje (Torreta)",
        value=f"**Media:** {stats_blindaje['media']}mm\n**Min:** {stats_blindaje['min']}mm\n**Max:** {stats_blindaje['max']}mm",
        inline=True
    )
    
    # Mostrar estadísticas de velocidad
    embed.add_field(
        name="🏎️ Velocidad",
        value=f"**Media:** {stats_velocidad['media']}km/h\n**Min:** {stats_velocidad['min']}km/h\n**Max:** {stats_velocidad['max']}km/h",
        inline=True
    )
    
    # Top tanques por blindaje (ahora incluye BR)
    top_b_texto = '\n'.join([
        f"{i+1}. {t['nombre']} ({t['blindaje_torreta']}mm) [BR {t.get(campo_br, '?')}]" 
        for i, t in enumerate(top_blindaje)
    ])
    
    embed.add_field(
        name="🏆 Top Blindaje",
        value=top_b_texto,
        inline=False
    )
    
    await ctx.send(embed=embed)


# ===============================================
# COMANDO: !top (MODIFICADO CON BR)
# ===============================================

@bot.command(name='top')
async def top(ctx, caracteristica: str = 'blindaje_torreta', limite: int = 5, 
              rango_br: str = None, modo: str = 'realista'):
    """
    Muestra el top de tanques según una característica.
    
    Uso: 
    - !top blindaje_torreta 10
    - !top velocidad_adelante_arcade 5 3-5
    - !top blindaje_chasis 10 5-7 arcade
    """
    await ctx.send(f'🏆 Calculando top {limite} en **{caracteristica}**...')
    
    # PASO 1: Obtener todos los tanques
    tanques = await api.obtener_todos_tanques()
    
    if not tanques:
        await ctx.send('❌ No se pudieron obtener los tanques.')
        return
    
    # PASO 2: Filtrar por BR si se especificó
    br_min, br_max = None, None
    if rango_br:
        br_min, br_max = parsear_rango_br(rango_br)
        
        if br_min is None:
            await ctx.send('❌ Rango de BR inválido. Usa formato: `3-5` o `3.0-5.7`')
            return
        
        tanques = filtrar_por_br(tanques, br_min, br_max, modo)
        
        if not tanques:
            await ctx.send(f'❌ No hay tanques en BR {br_min}-{br_max} ({modo})')
            return
    
    # PASO 3: Obtener el top de tanques
    top = obtener_top_tanques(tanques, caracteristica, limite)
    
    if not top:
        await ctx.send(f'❌ No se encontraron datos para: **{caracteristica}**')
        return
    
    # PASO 4: Crear embed
    titulo = f"🏆 Top {limite} - {caracteristica.replace('_', ' ').title()}"
    if rango_br:
        titulo += f" (BR {br_min}-{br_max} {modo})"
    
    embed = discord.Embed(
        title=titulo,
        color=discord.Color.gold()
    )
    
    # Construir la descripción con cada tanque
    campo_br = 'rating_realista' if modo == 'realista' else 'rating_arcade'
    descripcion = ""
    
    for i, tanque in enumerate(top, 1):
        # Obtener el valor de la característica
        valor = tanque.get(caracteristica, 0)
        if isinstance(valor, float):
            valor = round(valor, 2)
        
        # Obtener el BR del tanque
        br = tanque.get(campo_br, '?')
        if isinstance(br, float):
            br = round(br, 1)
        
        # Asignar medalla según posición
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        
        # Agregar línea a la descripción
        descripcion += f"{medalla} **{i}.** {tanque['nombre']} - `{valor}` [BR {br}]\n"
    
    embed.description = descripcion
    
    await ctx.send(embed=embed)

# -------------------- COMANDO: !ayuda --------------------
@bot.command(name='ayuda')
async def ayuda(ctx):
    """Muestra todos los comandos disponibles."""
    embed = discord.Embed(
        title="📖 Comandos Disponibles - War Thunder Bot",
        description="Lista de todos los comandos que puedes usar",
        color=discord.Color.blue()
    )
    
    comandos = [
        ("!ping", "Verifica que el bot esté funcionando"),
        ("!stats <rating_minimo>-<rating_maximo> <modo>", "Muestra estadísticas generales de todos los tanques"),
        ("!tanque <nombre>", "Busca información detallada de un tanque"),
        ("!comparar <tanque1> <tanque2>", "Compara dos tanques lado a lado"),
        ("!nacion <nombre> [rating_minimo]-[rating_maximo] [modo]", "Muestra estadísticas de una nación"),
        ("!top [caracteristica] [limite] [rating_minimo]-[rating_maximo] [modo]", "Muestra los mejores tanques"),
        ("!ayuda", "Muestra este mensaje de ayuda")
    ]
    
    for comando, descripcion in comandos:
        embed.add_field(name=comando, value=descripcion, inline=False)
    
    embed.set_footer(text="Usa !comando para ejecutar cualquier comando")
    
    await ctx.send(embed=embed)

# ====================================================================
# PASO 7: Iniciar el bot
# ====================================================================

if __name__ == '__main__':
    print("🤖 Iniciando bot de Discord...")
    print(f"🔗 Conectando a API: {BACKEND_URL}")
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Error al iniciar el bot: {e}")