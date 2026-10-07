![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![Angular](https://img.shields.io/badge/Angular-18+-DD0031?logo=angular&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248?logo=mongodb&logoColor=white)
![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-5865F2?logo=discord&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-AI%20Simulator-EE4C2C?logo=pytorch&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-GenAI-4285F4?logo=google&logoColor=white)

# 🛡️ Proyecto War Thunder Tanques

Una plataforma integral y full-stack diseñada para la **extracción, análisis estadístico, gestión comunitaria y simulación avanzada de combate con IA** de vehículos blindados del videojuego **War Thunder**.

El ecosistema combina **Web Scraping automatizado**, una **API REST con FastAPI**, persistencia en **MongoDB**, un **Simulador de Combate Balístico (Monte Carlo + PyTorch/ONNX + Google Gemini)**, un **Bot interactivo de Discord** y un **Frontend moderno en Angular** con soporte de roles, temas y analítica visual.

---

## 📑 Tabla de Contenidos

1. [✨ Características Principales](#-características-principales)
2. [🏗️ Arquitectura y Tecnologías](#️-arquitectura-y-tecnologías)
3. [🤖 Motor de Simulación de Combate (IA & Balística)](#-motor-de-simulación-de-combate-ia--balística)
4. [🤖 Bot de Discord](#-bot-de-discord)
5. [📦 Estructura del Proyecto](#-estructura-del-proyecto)
6. [🚀 Guía de Instalación y Ejecución](#-guía-de-instalación-y-ejecución)
   - [Requisitos Previos](#requisitos-previos)
   - [Variables de Entorno (.env)](#variables-de-entorno-env)
   - [Ejecución con Docker Compose (Recomendado)](#ejecución-con-docker-compose-recomendado)
   - [Ejecución Local Manual (Desarrollo)](#ejecución-local-manual-desarrollo)
7. [📡 Referencia de la API REST](#-referencia-de-la-api-rest)
8. [👥 Sistema de Roles y Aprobación de Cambios](#-sistema-de-roles-y-aprobación-de-cambios)
9. [📄 Licencia y Contribución](#-licencia-y-contribución)

---

## ✨ Características Principales

- **🕷️ Web Scraping Automatizado (Playwright & BeautifulSoup):**
  - Extracción masiva y periódica de todos los tanques terrestres directamente de la wiki oficial de War Thunder.
  - Captura datos balísticos detallados (tablas de penetración a 0m–2000m, velocidad en boca, masa de proyectil/explosivo), blindajes, velocidades (arcade/realista), rotaciones de torreta y setups de armas.
  - Descarga y almacenamiento local de imágenes de cada tanque.
  - Sincronización inteligente (`actualizar_datos.py`) que actualiza la base de datos preservando estimaciones y mejoras de IA previas.

- **⚔️ Simulador de Combate Táctico con IA:**
  - **Duelos 1 vs 1 (`/combate-ia`):** Simulación Monte Carlo de cientos de iteraciones basada en reglas de balística y física de War Thunder, refinada con una red neuronal PyTorch / ONNX Runtime.
  - **Combates por Equipos (`/combate-equipos-ia`):** Simulación de enfrentamientos de escuadrones (hasta 16 vs 16), calculando probabilidad de victoria, desglose de amenazas prioritarias, objetivos a evitar, blancos fáciles y mejores aliados de apoyo.
  - **Integración con Google Gemini (GenAI SDK):** Selección dinámica de modelos (Gemini 2.0 / 1.5), estimación inteligente de datos balísticos faltantes (factor de inclinación de blindaje / masa y velocidad de munición) y generación de análisis tácticos detallados en Markdown.

- **🌐 Frontend en Angular (SPA):**
  - **Catálogo Interactivo de Tanques:** Búsqueda en tiempo real, filtros por nación, Battle Rating (BR) y rol.
  - **Analítica Visual:** Indicadores cromáticos (verde/amarillo/rojo) y percentiles relativos frente al resto de vehículos según su BR.
  - **Modo Claro / Modo Oscuro** persistente en toda la interfaz.
  - **Panel de Administración:** Revisión, aprobación y rechazo en tiempo real de cambios o creaciones propuestas por la comunidad.
  - **Gestión y Edición:** Creación y modificación de tanques con subida de imágenes locales.

- **🤖 Bot de Discord (`discord.py` & `aiohttp`):**
  - Consultas estadísticas generales, comparativas lado a lado entre dos tanques con visualización de munición y penetraciones a diferentes distancias, rankings (`!top`) por características o penetración balística, y desglose por naciones.

- **🔐 Seguridad y Autenticación:**
  - Autenticación mediante tokens JWT (JSON Web Tokens) y contraseñas hasheadas con `bcrypt`.
  - Control de acceso basado en roles (Admin vs Usuario estándar).

---

## 🏗️ Arquitectura y Tecnologías

```mermaid
flowchart TD
    Wiki[Wiki War Thunder] -->|Playwright / Scraping| Scraper[warthunder_todos_tanques.py / actualizar_datos.py]
    Scraper -->|JSON / Inserción| DB[(MongoDB)]
    
    subgraph Backend [FastAPI Backend]
        API[FastAPI Endpoints]
        Auth[JWT & Bcrypt Auth]
        Pending[Sistema de Cambios Pendientes]
        SimEngine[Simulador Balístico Monte Carlo]
        NeuralNet[Red Neuronal PyTorch / ONNX]
        Gemini[Google Gemini API]
    end
    
    DB <--> API
    API --> SimEngine
    SimEngine <--> NeuralNet
    SimEngine <--> Gemini
    
    Frontend[Angular Frontend SPA] <-->|HTTP / REST API| API
    DiscordBot[Bot de Discord] <-->|Async HTTP / aiohttp| API
    DiscordBot <--> DiscordUsers[Usuarios en Discord]
```

### Stack Tecnológico:
- **Backend:** Python 3.11+, FastAPI, Uvicorn, PyMongo, Pydantic, PyTorch, ONNX Runtime, Google GenAI SDK (`google-genai`), python-jose, passlib, Playwright.
- **Frontend:** Angular 18+, TypeScript, HTML5/CSS3 moderno (Dark/Light mode, Responsive, Glassmorphism).
- **Base de Datos:** MongoDB 7.0.
- **Bot:** discord.py, aiohttp.
- **Infraestructura:** Docker, Docker Compose, Nginx.

---

## 🤖 Motor de Simulación de Combate (IA & Balística)

El simulador (`combat_simulator.py`) calcula el resultado de los combates combinando tres capas:

1. **Física y Balística Realista:**
   - Cálculo de probabilidad de penetración según distancia ($0\text{ m} - 2000\text{ m}$), blindaje efectivo con factor de inclinación (*slope factor*), cadencia y tiempo de recarga.
   - Efecto post-penetración considerando masa del proyectil, carga explosiva y número de tripulantes.
   - Influencia de la movilidad, velocidades de guiado, visibilidad y terreno/situación táctica.
2. **Refinamiento Neuronal (PyTorch & ONNX):**
   - Una red neuronal entrenada procesa los vectores de atributos de ambos vehículos para ajustar dinámicamente las probabilidades de victoria.
   - Compatible tanto con PyTorch nativo (`combat_model.pt`) como con ONNX Runtime optimizado (`combat_model.onnx`).
3. **Completado y Narrativa con Google Gemini:**
   - Si a un tanque le faltan parámetros balísticos o multiplicadores de blindaje inclinado, Gemini los estima inteligentemente y los persiste.
   - Redacción de informes tácticos post-combate explicando las causas técnicas de la victoria/derrota.

---

## 🤖 Bot de Discord

El bot permite acceder a toda la potencia de la API directamente desde servidores de Discord:

| Comando | Parámetros | Descripción |
| :--- | :--- | :--- |
| `!ping` | Ninguno | Comprueba la latencia del bot. |
| `!stats` | `[rango_br]` `[modo]` | Muestra medias estadísticas globales de blindaje, movilidad, armamento y penetración (ej: `!stats 3.0-5.7 realista`). |
| `!tanque` | `<nombre>` | Muestra ficha técnica detallada, blindajes, movilidad, setups de armamento, munición y foto. |
| `!comparar` | `<tanque1>` `<tanque2>` | Comparativa directa lado a lado entre dos tanques con balance de pros y contras e informe balístico. |
| `!nacion` | `<nombre>` `[rango_br]` `[modo]` | Estadísticas medias de todos los tanques de un país (ej: `!nacion Germany 5.7-7.7 arcade`). |
| `!top` | `[caracteristica]` `[limite]` `[rango_br]` `[modo]` | Ranking de mejores vehículos (ej: `!top penetracion 5 5.0-6.7`, `!top velocidad_adelante_realista 10`). |
| `!ayuda` | Ninguno | Guía visual de ayuda con todos los comandos disponibles. |

---

## 📦 Estructura del Proyecto

```text
├── .env.example                       # Plantilla de variables de entorno
├── docker-compose.dev.yaml            # Docker Compose para entorno de desarrollo (con hot-reload)
├── docker-compose.yaml                # Docker Compose para producción (Nginx + FastAPI + MongoDB)
├── backend/                           # Backend en FastAPI y módulos de IA
│   ├── main.py                        # Punto de entrada de FastAPI y rutas principales
│   ├── database.py                    # Conexión y gestión de cliente MongoDB
│   ├── models.py                      # Esquemas Pydantic para tanques y combate IA
│   ├── user_models.py                 # Modelos de usuarios y autenticación
│   ├── auth.py                        # Lógica JWT, hashing de contraseñas y dependencias
│   ├── auth_routes.py                 # Endpoints de login, registro y perfil (/auth)
│   ├── pending_changes_models.py      # Modelos de control de cambios pendientes
│   ├── pending_changes_routes.py      # Endpoints para aprobar/rechazar propuestas
│   ├── combat_simulator.py            # Motor de simulación balística Monte Carlo + PyTorch/ONNX
│   ├── combat_model.pt                # Pesos del modelo neuronal PyTorch
│   ├── combat_model.onnx              # Modelo exportado para ONNX Runtime
│   ├── export_model_onnx.py           # Script para exportar PyTorch a ONNX
│   ├── discord_bot.py                 # Bot de Discord interactivo
│   ├── launcher.py                    # Ejecutor concurrente de API + Bot
│   ├── warthunder_todos_tanques.py    # Script de Web Scraping con Playwright
│   ├── actualizar_datos.py            # Sincronización y actualización incremental de datos
│   ├── insertar_datos.py              # Script para poblar MongoDB desde JSON
│   ├── tanques.json                   # Base de datos local en JSON de vehículos
│   ├── imagenes/                      # Almacén de imágenes de tanques
│   ├── Dockerfile                     # Imagen Docker de producción para backend
│   ├── Dockerfile.dev                 # Imagen Docker de desarrollo
│   ├── Dockerfile.bot                 # Imagen Docker para el bot de Discord
│   ├── entrypoint.sh                  # Script de inicialización de BD en contenedor
│   └── requirements.txt               # Dependencias Python
└── war-thunder-frontend/              # Aplicación Angular (Frontend)
    ├── src/
    │   ├── app/
    │   │   ├── components/
    │   │   │   ├── tank-list/         # Catálogo de tanques con filtros y percentiles
    │   │   │   ├── tank-edit/         # Formulario de creación/edición de tanques
    │   │   │   ├── combat-ia/         # Vista de Simulación 1v1 con IA
    │   │   │   ├── combat-equipos-ia/ # Vista de Simulación de Equipos con IA
    │   │   │   ├── admin-panel/       # Panel de moderación de cambios pendientes
    │   │   │   ├── login/             # Inicio de sesión
    │   │   │   └── register/          # Registro de nuevos usuarios
    │   │   ├── services/              # Servicios Angular (tanks, auth, stats, pending-changes)
    │   │   ├── app.routes.ts          # Configuración de rutas de la SPA
    │   │   └── app.config.ts          # Proveedores globales de Angular
    │   ├── styles.css                 # Estilos globales y variables de tema
    │   └── index.html
    ├── Dockerfile                     # Multi-stage build con Nginx para producción
    ├── Dockerfile.dev                 # Configuración de desarrollo Angular
    ├── nginx.conf                     # Servidor web Nginx para la SPA
    └── proxy.conf.json                # Proxy inverso de desarrollo
```

---

## 🚀 Guía de Instalación y Ejecución

### Requisitos Previos

- [Docker](https://www.docker.com/) y [Docker Compose](https://docs.docker.com/compose/) (Recomendado).
- O en su defecto para ejecución manual:
  - **Python 3.11+**
  - **Node.js 18+** y **npm**
  - **MongoDB 7.0+**

### Variables de Entorno (.env)

Copia el archivo `.env.example` en la raíz como `.env` y configura tus valores:

```bash
cp .env.example .env
```

Ejemplo de contenido:
```ini
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/admin
SECRET_KEY=tu_clave_secreta_jwt_muy_segura
JWT_ALGORITHM=HS256
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=admin123
DATABASE_NAME=war_thunder
BACKEND_PORT=8000
FRONTEND_PORT=4200
DISCORD_TOKEN=tu_token_de_discord_aqui
BACKEND_URL=http://localhost:8000
GEMINI_API_KEY=tu_api_key_de_google_gemini
```

---

### Ejecución con Docker Compose (Recomendado)

#### Modo Desarrollo (con Hot-Reload)
```bash
# Levantar Backend, Frontend y MongoDB con recarga en caliente:
docker compose -f docker-compose.dev.yaml up --build
```
- **Frontend:** `http://localhost:4200`
- **Backend API Docs:** `http://localhost:8000/docs`
- **MongoDB:** `localhost:27017`

#### Modo Producción
```bash
docker compose up -d --build
```

---

### Ejecución Local Manual (Desarrollo)

Si prefieres ejecutar los servicios en terminales independientes sin Docker:

#### 1. Backend y Bot (Python)
```bash
cd backend
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt

# (Opcional) Instalar navegadores de Playwright si vas a scrapear:
playwright install

# Poblar la base de datos inicial si es necesario:
python insertar_datos.py

# Opción A: Iniciar solo la API de FastAPI
uvicorn main:app --reload --port 8000

# Opción B: Iniciar la API y el Bot de Discord simultáneamente
python launcher.py
```

#### 2. Frontend (Angular)
```bash
cd war-thunder-frontend
npm install
npm start
```
Accede a `http://localhost:4200` en tu navegador.

---

## 📡 Referencia de la API REST

La API cuenta con documentación Swagger interactiva disponible en `/docs` y Redoc en `/redoc`.

### Endpoints Principales:

- **Autenticación (`/auth`)**
  - `POST /auth/register`: Registro de usuario.
  - `POST /auth/token`: Inicio de sesión (obtiene token Bearer JWT).
  - `GET /auth/me`: Perfil del usuario autenticado.
- **Tanques (`/tanques`)**
  - `GET /tanques/`: Lista todos los tanques con ordenamiento por BR y nación.
  - `GET /tanques/{id}`: Obtiene un tanque por su ID.
  - `GET /tanques/nacion/{nacion}`: Filtra vehículos por país.
  - `POST /tanques/`: Crea un nuevo tanque (directo si es admin, genera solicitud si es usuario).
  - `PUT /tanques/{id}`: Actualiza datos de un tanque.
  - `DELETE /tanques/{id}`: Elimina un tanque.
- **Estadísticas y Análisis**
  - `GET /stats`: Medias estadísticas globales con filtro por BR y modo (`arcade`/`realista`).
  - `GET /stats/nacion`: Medias estadísticas filtradas por país y BR.
  - `GET /top`: Rankings ordenados por cualquier característica o penetración balística.
- **Simulación de Combate e IA**
  - `GET /ia/modelos/`: Lista los modelos de Gemini disponibles.
  - `POST /combate-ia/`: Ejecuta duelo 1v1 con simulación Monte Carlo, red neuronal y análisis táctico de IA.
  - `POST /simulacion-equipos-ia/`: Simulación de batallas de escuadrones (hasta 16 vs 16) con priorización de amenazas.
- **Cambios Pendientes (`/cambios-pendientes`)**
  - `GET /cambios-pendientes/`: Lista cambios pendientes (solo administradores).
  - `GET /cambios-pendientes/mis-cambios`: Lista solicitudes del usuario autenticado.
  - `POST /cambios-pendientes/{id}/aprobar`: Aplica los cambios a la base de datos.
  - `POST /cambios-pendientes/{id}/rechazar`: Descarta la solicitud con motivo.
- **Utilidades e Imágenes**
  - `POST /upload-tank-image/`: Subida de imágenes de vehículos.
  - `GET /imagenes/{archivo}`: Servidor estático de imágenes.
  - `GET /health`: Comprobación de estado y conexión a la base de datos.

---

## 👥 Sistema de Roles y Aprobación de Cambios

Para mantener la integridad de los datos balísticos y estadísticos:
1. **Administradores:** Pueden crear, modificar o eliminar tanques con efecto inmediato en MongoDB, además de moderar solicitudes.
2. **Usuarios Registrados:** Pueden proponer nuevos tanques o sugerir correcciones en vehículos existentes. Estas peticiones quedan en estado `pendiente` y son auditadas desde el **Panel de Administración** antes de consolidarse.

---

## 📄 Licencia

Este proyecto es de **código abierto** bajo la licencia [MIT](./LICENSE).  
Puedes usarlo, modificarlo y distribuirlo libremente manteniendo los créditos al autor original.

---

## 📝 Contribuir

¡Las contribuciones son bienvenidas!
1. Haz un fork del repositorio.
2. Crea tu rama de características (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus cambios y haz commit (`git commit -m 'Añadir nueva funcionalidad'`).
4. Haz push a la rama (`git push origin feature/nueva-funcionalidad`).
5. Abre un **Pull Request**.

---

## 📬 Contacto

- **Autor:** Gonzalo Durán ([gonzalodurgra](https://github.com/gonzalodurgra))
- **Correo:** [gonzalodurgra@gmail.com](mailto:gonzalodurgra@gmail.com)
- **Repositorio:** [Proyecto_Scrapping_FastAPI_Angular_War_Thunder_Tanques](https://github.com/gonzalodurgra/Proyecto_Scrapping_FastAPI_Angular_War_Thunder_Tanques)

