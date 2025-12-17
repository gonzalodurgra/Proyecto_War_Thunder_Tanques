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
    """
    Clase que maneja todas las comunicaciones con la API de War Thunder.
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    async def obtener_todos_tanques(self) -> List[Dict]:
        """Obtiene todos los tanques de la API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.base_url}/tanques/') as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ Error al obtener tanques: {response.status}")
                    return []
    
    async def obtener_tanque_por_id(self, tanque_id: str) -> Optional[Dict]:
        """Obtiene un tanque específico por ID."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.base_url}/tanques/{tanque_id}') as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    async def buscar_tanque_por_nombre(self, nombre: str) -> Optional[Dict]:
        """Busca un tanque por nombre (coincidencia parcial)."""
        tanques = await self.obtener_todos_tanques()
        nombre_lower = nombre.lower()
        
        # Búsqueda exacta primero
        for tanque in tanques:
            if tanque['nombre'].lower() == nombre_lower:
                return tanque
        
        # Búsqueda parcial
        for tanque in tanques:
            if nombre_lower in tanque['nombre'].lower():
                return tanque
        
        return None
    
    async def obtener_tanques_por_nacion(self, nacion: str) -> List[Dict]:
        """Obtiene todos los tanques de una nación."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.base_url}/tanques/nacion/{nacion}') as response:
                if response.status == 200:
                    return await response.json()
                return []

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


# ====================================================================
# PASO 5: Eventos del bot
# ====================================================================

@bot.event
async def on_ready():
    """Se ejecuta cuando el bot está listo."""
    print(f'✅ Bot conectado como {bot.user}')
    print(f'📊 Servidores: {len(bot.guilds)}')
    
    # Sincronizar comandos slash
    try:
        synced = await bot.tree.sync()
        print(f'🔄 {len(synced)} comandos slash sincronizados')
    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')

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
@bot.command(name='stats')
async def stats(ctx):
    """Muestra estadísticas generales de todos los tanques."""
    await ctx.send('📊 Calculando estadísticas...')
    
    tanques = await api.obtener_todos_tanques()
    
    if not tanques:
        await ctx.send('❌ No se pudieron obtener los tanques.')
        return
    
    # Calcular estadísticas
    total = len(tanques)
    
    # Contar tanques por nación
    naciones = {}
    for tanque in tanques:
        nacion = tanque.get('nacion', 'Desconocida')
        naciones[nacion] = naciones.get(nacion, 0) + 1
    
    # Calcular medias
    media_blindaje_chasis = calcular_media_caracteristica(tanques, 'blindaje_chasis')
    media_blindaje_torreta = calcular_media_caracteristica(tanques, 'blindaje_torreta')
    media_velocidad = calcular_media_caracteristica(tanques, 'velocidad_adelante_arcade')
    media_potencia = calcular_media_caracteristica(tanques, 'relacion_potencia_peso')
    
    # Crear embed
    embed = discord.Embed(
        title="📊 Estadísticas Generales - War Thunder",
        description=f"Análisis de {total} tanques",
        color=discord.Color.blue()
    )
    
    # Agregar campos
    embed.add_field(
        name="🛡️ Blindaje Promedio",
        value=f"Chasis: {media_blindaje_chasis}mm\nTorreta: {media_blindaje_torreta}mm",
        inline=True
    )
    
    embed.add_field(
        name="🏎️ Movilidad Promedio",
        value=f"Velocidad: {media_velocidad}km/h\nPotencia/Peso: {media_potencia}hp/t",
        inline=True
    )
    
    # Top 3 naciones con más tanques
    top_naciones = sorted(naciones.items(), key=lambda x: x[1], reverse=True)[:3]
    naciones_texto = '\n'.join([f"{nacion}: {cantidad}" for nacion, cantidad in top_naciones])
    
    embed.add_field(
        name="🌍 Top Naciones",
        value=naciones_texto,
        inline=False
    )
    
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
        value=f"**Recarga:** {tanque['recarga']} s\n**Cadencia:** {tanque['cadencia']:.1f} disp/min\n**Munición:** {tanque['municion_total']}\n**Rotación horizontal:** {tanque['rotacion_torreta_horizontal_arcade']}/{tanque['rotacion_torreta_horizontal_realista']} º/s\n**Rotación vertical:** {tanque['rotacion_torreta_vertical_arcade']}/{tanque['rotacion_torreta_vertical_realista']} º/s",
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
async def nacion(ctx, *, nombre_nacion: str):
    """
    Muestra estadísticas de una nación específica.
    Uso: !nacion nombre_nacion
    """
    await ctx.send(f'🌍 Obteniendo datos de **{nombre_nacion}**...')
    
    tanques = await api.obtener_tanques_por_nacion(nombre_nacion)
    
    if not tanques:
        await ctx.send(f'❌ No se encontraron tanques de: **{nombre_nacion}**')
        return
    
    # Calcular estadísticas
    total = len(tanques)
    stats_blindaje = calcular_estadisticas_completas(tanques, 'blindaje_torreta')
    stats_velocidad = calcular_estadisticas_completas(tanques, 'velocidad_adelante_arcade')
    
    # Top 3 tanques por blindaje
    top_blindaje = obtener_top_tanques(tanques, 'blindaje_torreta', 3)
    top_velocidad = obtener_top_tanques(tanques, 'velocidad_adelante_arcade', 3)
    
    # Crear embed
    embed = discord.Embed(
        title=f"🌍 Estadísticas de {nombre_nacion}",
        description=f"Análisis de {total} tanques",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🛡️ Blindaje (Torreta)",
        value=f"**Media:** {stats_blindaje['media']}mm\n**Min:** {stats_blindaje['min']}mm\n**Max:** {stats_blindaje['max']}mm",
        inline=True
    )
    
    embed.add_field(
        name="🏎️ Velocidad",
        value=f"**Media:** {stats_velocidad['media']}km/h\n**Min:** {stats_velocidad['min']}km/h\n**Max:** {stats_velocidad['max']}km/h",
        inline=True
    )
    
    # Top tanques
    top_b_texto = '\n'.join([
        f"{i+1}. {t['nombre']} ({t['blindaje_torreta']}mm)" 
        for i, t in enumerate(top_blindaje)
    ])
    
    embed.add_field(
        name="🏆 Top Blindaje",
        value=top_b_texto,
        inline=False
    )
    
    await ctx.send(embed=embed)

# -------------------- COMANDO: !top --------------------
@bot.command(name='top')
async def top(ctx, caracteristica: str = 'blindaje_torreta', limite: int = 5):
    """
    Muestra el top de tanques según una característica.
    Uso: !top [caracteristica] [limite]
    Ejemplo: !top blindaje_torreta 10
    """
    await ctx.send(f'🏆 Calculando top {limite} en **{caracteristica}**...')
    
    tanques = await api.obtener_todos_tanques()
    
    if not tanques:
        await ctx.send('❌ No se pudieron obtener los tanques.')
        return
    
    # Obtener top
    top = obtener_top_tanques(tanques, caracteristica, limite)
    
    if not top:
        await ctx.send(f'❌ No se encontraron datos para: **{caracteristica}**')
        return
    
    # Crear embed
    embed = discord.Embed(
        title=f"🏆 Top {limite} - {caracteristica.replace('_', ' ').title()}",
        color=discord.Color.gold()
    )
    
    descripcion = ""
    for i, tanque in enumerate(top, 1):
        valor = tanque.get(caracteristica, 0)
        if isinstance(valor, float):
            valor = round(valor, 2)
        
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        descripcion += f"{medalla} **{i}.** {tanque['nombre']} - `{valor}`\n"
    
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
        ("!stats", "Muestra estadísticas generales de todos los tanques"),
        ("!tanque <nombre>", "Busca información detallada de un tanque"),
        ("!comparar <tanque1> <tanque2>", "Compara dos tanques lado a lado"),
        ("!nacion <nombre>", "Muestra estadísticas de una nación"),
        ("!top [caracteristica] [limite]", "Muestra los mejores tanques"),
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