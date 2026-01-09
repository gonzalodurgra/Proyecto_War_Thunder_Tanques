![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

# Proyecto War Thunder Tanques

## 🧩 Descripción  
Este proyecto ofrece una **solución** para extraer, almacenar y visualizar información sobre tanques del videojuego War Thunder mediante web-scraping, API y frontend web. Adicionalmente, la API trabaja en conjunto con un bot de Discord. 
- El backend se encarga de la extracción de datos de la wiki de **War Thunder** (scraping), el almacenamiento en MongoDB, la exposición de una API con FastAPI y un bot de Discord con discord.py.  
- El frontend está construido con Angular y permite consultar y mostrar los tanques, así como gestionar usuarios (autenticación/autorizar) y todos los cambios que se produzcan. 
- Ideal para quienes quieran explorar datos de tanques de War Thunder, al mismo tiempo que aprende sobre scraping + API + frontend + creación de bots, o desarrollar una app de consulta.

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
│ ├── pending_models.py # Lógica para cambios pendientes<br>
│ ├── pending_routes.py # Rutas de cambios pendientes<br>
│ ├── warthunder_todos_tanques.py # Script de scraping<br>
│ ├── discord_bot.py # Crea el bot que se comunica con la API<br>
│ ├── launcher.py # Permite la ejecución al mismo tiempo de la API y del bot de Discord<br>
│ ├── Dockerfile # Crea la imagen para el backend de producción<br>
│ ├── Dockerfile.bot # Crea la imagen para el backend del bot en producción<br>
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
│ ├── app/ # Components (admin, login, registro, listar y editar tanques), servicios (tanques, estadísticas de tanques, autorización, subida de imágenes y cambios pendientes), rutas<br>
│ ├── index.html<br>
│ └── styles.css (estilos globales)<br>


> Nota: Se omiten aquí los archivos temporales, dependencias compiladas y credenciales.

## 🚀 ¿Qué necesitas para ejecutar mi proyecto en local?
Requieres de Docker con imágenes que se encargan de Python, MongoDB y Angular para trabajar con este proyecto. Trabaja siempre con los .dev en lugar de los de producción a la hora del desarrollo inicial para ser más rápido, eficiente y por temas de comodidad
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
### 2. ¿Cuál es la funcionalidad de mi proyecto?
1. Cómo ya he mencionado, todo comienza en base a mi scrapper para traer los datos de la wiki, para la cual uso la librería playwright. Decir que el proceso es un poco largo, puede durar entre 1 hora y media o 3 horas normalmente.
2. La API se encarga de la parte CRUD generalmente en base a los tanques, con endpoints adicionales para monitorizar tanto API como frontend, procesado de imágenes y funciones adicionales en cuanto al bot de Discord.
3. A su vez, el bot de Discord se inicia, el cual contiene los comandos *!ping* para comprobar su funcionamiento, *!stats* que extrae las medias de todas las características según rating del tanque, *!tanque* que muestra información detallada de un vehículo terrestre, *!comparar* compara dos tanques a grandes rasgos, !nacion tiene una función muy similar a stats, pero divide según país, *!top* muestra según rango de ratings los mejores tanques en cierta característica; y *!ayuda* que muestra todos los comandos y una guía de como utilizarlos.
4. En cuanto al frontend, toda variable estadística útil se muestra con un color indicativo del valor de dicha característica, permitiendo al usuario saber según si está en verde, amarillo o rojo (variando de tonos) si es un pro o contra, con una badge para indicar su posición en percentiles respecto a otros vehículos. Además, se introduce un panel de administración, donde se registran los cambios realizados por el usuario que pueden ser aceptados o rechazados. (Tened en cuenta que el administrador ejecuta operaciones de forma directa, y que el usuario habitual puede ver también sus cambios).

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
