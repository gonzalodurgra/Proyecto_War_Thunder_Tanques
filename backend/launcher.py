"""
LAUNCHER - Inicia API y Bot simultáneamente
=============================================
Este script ejecuta tanto la API de FastAPI como el Bot de Discord
en el mismo entorno/contenedor, gestionando el ciclo de vida de ambos subprocesos,
captura de señales de apagado (SIGINT/SIGTERM) y reinicio automático en caso de fallo.
"""

import subprocess
import sys
import os
import time
import signal

# ====================================================================
# SECCIÓN 1: INICIALIZACIÓN DE SUBPROCESOS
# ====================================================================

def iniciar_bot():
    """
    Inicia el bot de Discord en un subproceso independiente.
    Redirige stdout y stderr a tuberías (PIPE) para permitir supervisión y captura de logs.
    """
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
    """
    Inicia el servidor web FastAPI mediante Uvicorn en un subproceso.
    Conecta stdout y stderr a los flujos estándar del sistema para visibilidad en consola.
    """
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


# ====================================================================
# SECCIÓN 2: CONTROL DE SEÑALES Y PARADA ORDENADA
# ====================================================================

def manejar_señal(sig, frame):
    """
    Manejador de señales del sistema operativo (Ctrl+C o SIGTERM).
    Permite una detención ordenada de los procesos hijos antes de salir.
    """
    print("\n⚠️ Señal de terminación recibida. Cerrando servicios...")
    sys.exit(0)


# ====================================================================
# SECCIÓN 3: BUCLE PRINCIPAL DE MONITORIZACIÓN Y RECUPERACIÓN
# ====================================================================

def main():
    """
    Función principal de supervisión:
    1. Registra los manejadores de interrupción.
    2. Arranca el bot de Discord y espera su conexión inicial.
    3. Arranca el servidor FastAPI.
    4. Mantiene un bucle activo comprobando el estado de salud de ambos procesos,
       reiniciando el bot si finaliza inesperadamente.
    5. Gestiona la limpieza y liberación de recursos en el bloque finally.
    """
    print("=" * 60)
    print("🚀 INICIANDO SERVICIOS DE WAR THUNDER")
    print("=" * 60)
    
    # Registrar manejadores de señales para captura de interrupciones
    signal.signal(signal.SIGINT, manejar_señal)
    signal.signal(signal.SIGTERM, manejar_señal)
    
    try:
        # PASO 1: Iniciar el bot de Discord primero
        bot_process = iniciar_bot()
        time.sleep(3)  # Tiempo de cortesía para inicializar sesión y conexión
        
        # PASO 2: Iniciar la API de FastAPI
        api_process = iniciar_api()
        
        print("\n" + "=" * 60)
        print("✅ TODOS LOS SERVICIOS INICIADOS CORRECTAMENTE")
        print("=" * 60)
        print(f"📊 Bot PID: {bot_process.pid}")
        print(f"🌐 API PID: {api_process.pid}")
        print("=" * 60)
        
        # PASO 3: Bucle de supervisión periódica
        while True:
            # Comprobar si el bot de Discord sigue activo
            bot_poll = bot_process.poll()
            if bot_poll is not None:
                print(f"⚠️ Bot se detuvo con código: {bot_poll}")
                # Capturar errores del stderr para diagnóstico
                stdout, stderr = bot_process.communicate()
                if stderr:
                    print(f"❌ Error del bot: {stderr}")
                # Auto-recuperación: reintentar levantar el bot
                print("🔄 Reiniciando bot...")
                bot_process = iniciar_bot()
            
            # Comprobar si el servidor de API sigue activo
            api_poll = api_process.poll()
            if api_poll is not None:
                print(f"⚠️ API se detuvo con código: {api_poll}")
                break
            
            time.sleep(5)  # Intervalo de sondeo de 5 segundos
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupción detectada. Cerrando servicios...")
    except Exception as e:
        print(f"❌ Error durante la ejecución del supervisor: {e}")
    finally:
        # Limpieza ordenada de procesos hijos (SIGTERM con fallback a SIGKILL)
        print("🧹 Limpiando procesos...")
        try:
            bot_process.terminate()
            api_process.terminate()
            bot_process.wait(timeout=5)
            api_process.wait(timeout=5)
        except Exception:
            bot_process.kill()
            api_process.kill()
        print("✅ Servicios detenidos correctamente")


if __name__ == "__main__":
    main()