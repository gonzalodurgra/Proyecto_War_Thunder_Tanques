#!/bin/bash
# entrypoint.sh

FLAG_FILE=/app/.db_initialized

# Ejecutar script de inicialización solo si no existe el flag
if [ ! -f "$FLAG_FILE" ]; then
    echo "🟢 Inicializando datos en MongoDB..."
    python3 /app/insertar_datos.py
    # Crear flag para que no se vuelva a ejecutar
    touch "$FLAG_FILE"
else
    echo "✅ Datos ya inicializados."
fi

# Ejecutar uvicorn con hot-reload
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app
