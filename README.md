![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

# Proyecto War Thunder Tanques

## 🧩 Descripción  
Este proyecto ofrece una **solución** para extraer, almacenar y visualizar información sobre tanques del videojuego War Thunder mediante web-scraping, API y frontend web.  
- El backend se encarga de la extracción de datos de la wiki de **War Thunder** (scraping), el almacenamiento en MongoDB, y la exposición de una API con FastAPI.  
- El frontend está construido con Angular y permite consultar y mostrar los tanques, así como gestionar usuarios (autenticación/autorizar).  
- Ideal para quienes quieran explorar datos de tanques de War Thunder, al mismo tiempo que aprende sobre scraping + API + frontend, o desarrollar una app de consulta.

## 📦 Estructura del proyecto  
/ (raíz del proyecto)<br>
└── docker-compose.dev.yaml #Arranca los contenedores para desarrollo<br>
└── docker-compose.yaml #Arranca los contenedores para producción<br>
└── backend #API en Python<br>
│<br>
│ ├── main.py # Punto de entrada de FastAPI<br>
│ ├── database.py # Configuración de MongoDB<br>
│ ├── models.py # Modelos de datos (tanques)<br>
│ ├── user_models.py # Modelos de usuario/autenticación<br>
│ ├── auth.py # Lógica de autenticación (hash, tokens)<br>
│ ├── auth_routes.py # Rutas de autenticación<br>
│ ├── warthunder_todos_tanques.py # Script de scraping<br>
│ ├── Dockerfile # Crea la imagen para el backend de producción<br>
│ ├── Dockerfile.dev # Crea la imagen para el backend de desarrollo<br>
│ ├── entrypoint.sh # Crea la base de datos en caso de que no exista cuando se ejecuta Dockerfile.dev<br>
│ ├── requirements.txt # Dependencias de Python<br>


│<br>
└── war-thunder-frontend/ # Aplicación Angular<br>
├── package.json<br>
├── package-lock.json<br>
├── angular.json<br>
├── Dockerfile<br>
├── Dockerfile.dev<br>
├── Dockerfile<br>
├── nginx.conf<br> #Configura el servidor nginx de la imagen obtenida en el Dockerfile
├── proxy.conf.json<br> #Evita errores de CORS (sólo usar para desarrollo)
├── src/<br>
│ ├── app/ # Components, servicios, rutas<br>
│ ├── index.html<br>
│ └── styles.css<br>


> Nota: Se omiten aquí los archivos temporales, dependencias compiladas y credenciales.

## 🚀 Instalación y uso
Requieres de Docker con imágenes que se encargan de Python, MongoDB y Angular para trabajar con este proyecto. Trabaja siempre con los .dev en lugar de los de producción a la hora de desarrollar más rápida y cómodamente
### 1. Levantando el proyecto  
1. Clona el repositorio:
  ```bash
   git clone https://github.com/usuario/Proyecto_War_Thunder_Tanques.git
   cd Proyecto_War_Thunder_Tanques
   ```
2. Ejecuta el [scrapper](backend/todos_los_tanques.py). Obtendrás un json de datos que luego utilizarás para MongoDB.
3. Ejecuta el archivo [para levantar el proyecto](docker-compose.dev.yaml). Creará todos los contenedores necesarios para poder desarrollar, con sus respectivas dependencias, inicializando además los datos.  
4. Crea un archivo .env, adaptando las variables de entorno de [.env.example](.env.example), en la raíz del proyecto.
**Ya deberías tener disponible el proyecto para probarlo y trabajar con él en caso de que quieras contribuir.**

## 📄 Licencia

Este proyecto es de **código abierto** bajo la licencia [MIT](./LICENSE).  
Puedes usarlo, modificarlo y distribuirlo libremente siempre que mantengas los créditos al autor original.

## 📝 Contribuir

Si deseas contribuir:
1. Haz un fork del repositorio.
2. Crea una rama (git checkout -b feature/nueva-funcionalidad).
3. Haz tus cambios y haz commit.
4. Envía un pull request.

## Contacto

Autor: [gonzalodurgra]
Puedes contactar por correo: [gonzalodurgra@gmail.com]
Repositorio original: https://github.com/gonzalodurgra/Proyecto_War_Thunder_Tanques
