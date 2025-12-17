"""
LAUNCHER - Inicia API y Bot simultáneamente
=============================================
Este script ejecuta tanto la API de FastAPI como el Bot de Discord
en el mismo proceso, ideal para Render Free Tier.
"""

import subprocess
import sys
import os
import time
import signal

def iniciar_bot():
    """Inicia el bot de Discord en un proceso separado."""
    print("🤖 Iniciando bot de Discord...")
    bot_process = subprocess.Popen(
        [sys.executable, "discord_bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"✅ Bot iniciado con PID: {bot_process.pid}")
    return bot_process

def iniciar_api():
    """Inicia la API de FastAPI."""
    print("🌐 Iniciando API de FastAPI...")
    port = os.getenv("BACKEND_PORT", "8000")
    
    api_process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", port
        ],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    print(f"✅ API iniciada con PID: {api_process.pid}")
    return api_process

def manejar_señal(sig, frame):
    """Maneja señales de terminación."""
    print("\n⚠️ Señal de terminación recibida. Cerrando servicios...")
    sys.exit(0)

def main():
    """Función principal que inicia ambos servicios."""
    print("=" * 60)
    print("🚀 INICIANDO SERVICIOS DE WAR THUNDER")
    print("=" * 60)
    
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, manejar_señal)
    signal.signal(signal.SIGTERM, manejar_señal)
    
    try:
        # PASO 1: Iniciar el bot
        bot_process = iniciar_bot()
        time.sleep(3)  # Esperar a que el bot se inicialice
        
        # PASO 2: Iniciar la API
        api_process = iniciar_api()
        
        print("\n" + "=" * 60)
        print("✅ TODOS LOS SERVICIOS INICIADOS CORRECTAMENTE")
        print("=" * 60)
        print(f"📊 Bot PID: {bot_process.pid}")
        print(f"🌐 API PID: {api_process.pid}")
        print("=" * 60)
        
        # PASO 3: Mantener el script corriendo
        # Monitorear ambos procesos
        while True:
            # Verificar si el bot sigue corriendo
            bot_poll = bot_process.poll()
            if bot_poll is not None:
                print(f"⚠️ Bot se detuvo con código: {bot_poll}")
                # Capturar salida del bot para debugging
                stdout, stderr = bot_process.communicate()
                if stderr:
                    print(f"❌ Error del bot: {stderr}")
                # Reiniciar el bot
                print("🔄 Reiniciando bot...")
                bot_process = iniciar_bot()
            
            # Verificar si la API sigue corriendo
            api_poll = api_process.poll()
            if api_poll is not None:
                print(f"⚠️ API se detuvo con código: {api_poll}")
                break
            
            time.sleep(5)  # Verificar cada 5 segundos
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupción detectada. Cerrando servicios...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Limpiar procesos
        print("🧹 Limpiando procesos...")
        try:
            bot_process.terminate()
            api_process.terminate()
            bot_process.wait(timeout=5)
            api_process.wait(timeout=5)
        except:
            bot_process.kill()
            api_process.kill()
        print("✅ Servicios detenidos correctamente")

if __name__ == "__main__":
    main()