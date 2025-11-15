# ====================================================================
# DOCKERFILE MULTI-STAGE PARA FRONTEND ANGULAR
# ====================================================================

# EXPLICACIÓN DE MULTI-STAGE:
# - Stage 1 (build): Compila la aplicación Angular
# - Stage 2 (production): Sirve los archivos estáticos con Nginx
# - Resultado: Imagen final muy ligera (solo archivos compilados + Nginx)

# ====================================================================
# STAGE 1: BUILD DE LA APLICACIÓN ANGULAR
# ====================================================================

FROM node:current-alpine AS build

# EXPLICACIÓN:
# - node:20-alpine: Node.js 20 en Alpine Linux (muy ligero)
# - AS build: nombre del stage para referenciar después

WORKDIR /app

# Copiar archivos de dependencias
COPY package*.json ./

# EXPLICACIÓN:
# - package*.json copia tanto package.json como package-lock.json
# - Los copiamos primero para aprovechar el cache de Docker

# Instalar dependencias
RUN npm ci --silent

# EXPLICACIÓN:
# - npm ci es más rápido y determinista que npm install
# - --silent reduce el output en la consola
# - Instala exactamente las versiones de package-lock.json

# Copiar el código fuente
COPY . .

# Build de producción de Angular
RUN npm run build --configuration war-thunder-frontend

# EXPLICACIÓN:
# - npm run build ejecuta "ng build"
# - --configuration production: optimiza para producción
# - Genera archivos en dist/war-thunder-frontend/

# ====================================================================
# STAGE 2: SERVIDOR NGINX PARA PRODUCCIÓN
# ====================================================================

FROM nginx:alpine

# EXPLICACIÓN:
# - nginx:alpine: servidor web Nginx en Alpine Linux
# - Solo ~23MB de tamaño
# - Perfecto para servir archivos estáticos

# Copiar la configuración personalizada de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# EXPLICACIÓN:
# - Copiamos nuestra configuración personalizada
# - Reemplaza la configuración por defecto de Nginx

# Copiar los archivos compilados desde el stage de build
COPY --from=build /app/dist/war-thunder-frontend/browser /usr/share/nginx/html

# EXPLICACIÓN:
# - --from=build: copia desde el stage anterior
# - /war-thunder-frontend/dist/war-thunder-frontend/browser: archivos compilados de Angular 18+
# - /usr/share/nginx/html: directorio por defecto de Nginx

# Exponer el puerto 80
EXPOSE 80

# EXPLICACIÓN:
# - Nginx sirve por defecto en el puerto 80
# - Este será el puerto del frontend

# El comando por defecto de nginx:alpine ya inicia Nginx
# No necesitamos especificar CMD

# ====================================================================
# RESULTADO FINAL
# ====================================================================
# - Stage 1 se descarta después del build
# - Imagen final solo contiene: Nginx + archivos HTML/CSS/JS compilados
# - Tamaño final: ~50MB (vs ~1GB si incluyéramos Node.js)