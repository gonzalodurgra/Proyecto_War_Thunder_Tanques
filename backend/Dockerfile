# ====================================================================
# DOCKERFILE PARA BACKEND FASTAPI
# ====================================================================

# Usar Python 3.11 como imagen base
FROM python:3.11-slim

# EXPLICACIÓN:
# - python:3.11-slim es una versión ligera de Python
# - "slim" significa que no tiene paquetes innecesarios, reduciendo el tamaño

WORKDIR /app

# EXPLICACIÓN:
# - Todos los comandos siguientes se ejecutarán en /app
# - Es como hacer "cd /app" en la terminal

# ====================================================================
# COPIAR ARCHIVOS DE DEPENDENCIAS
# ====================================================================

# Copiar el archivo de requisitos primero (para aprovechar el cache de Docker)
COPY requirements.txt .

# EXPLICACIÓN:
# - Copiamos solo requirements.txt primero
# - Si no cambia, Docker reutiliza la capa cacheada
# - Esto acelera las builds posteriores

# ====================================================================
# INSTALAR DEPENDENCIAS
# ====================================================================

# Instalar las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# EXPLICACIÓN:
# - --no-cache-dir: No guarda cache de pip (reduce tamaño)
# - --upgrade pip: Actualiza pip a la última versión
# - RUN ejecuta comandos durante la build
# - && encadena comandos (si el primero falla, el segundo no se ejecuta)

# ====================================================================
# COPIAR EL CÓDIGO DE LA APLICACIÓN
# ====================================================================

# Copiar todo el código de la aplicación
COPY . .

# EXPLICACIÓN:
# - Primer punto: directorio actual (tu máquina)
# - Segundo punto: directorio de trabajo en el contenedor (/app)
# - Copia todos los archivos .py, excepto los que están en .dockerignore

# ====================================================================
# EXPONER EL PUERTO
# ====================================================================

# Exponer el puerto 8000 (donde corre FastAPI)
EXPOSE 10000

# EXPLICACIÓN:
# - EXPOSE documenta qué puerto usa la aplicación
# - No publica el puerto automáticamente, solo lo documenta
# - La publicación real se hace en docker-compose.yml

# Healthcheck para Render
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
CMD curl -f http://localhost:${PORT:-10000}/ || exit 1

# ====================================================================
# COMANDO PARA EJECUTAR LA APLICACIÓN
# ====================================================================

# Comando para iniciar el servidor uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-10000}"]

# EXPLICACIÓN:
# - CMD define el comando que se ejecuta cuando inicia el contenedor
# - uvicorn main:app: ejecuta la app de main.py
# - --host 0.0.0.0: escucha en todas las interfaces (necesario para Docker)
# - --port 8000: puerto donde corre la API
# - NO usamos --reload en producción (solo desarrollo)