![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

# Proyecto War Thunder Tanques

## 🧩 Descripción  
Este proyecto ofrece una **solución completa** para extraer, almacenar y visualizar información sobre tanques del videojuego War Thunder mediante web-scraping, API y frontend web.  
- El backend se encarga de la extracción de datos de la wiki de **War Thunder** (scraping), el almacenamiento en MongoDB, y la exposición de una API con FastAPI.  
- El frontend está construido con Angular y permite consultar y mostrar los tanques, así como gestionar usuarios (autenticación/autorizar).  
- Ideal para quienes quieran explorar datos de tanques de War Thunder, al mismo tiempo que aprende sobre scraping + API + frontend, o desarrollar una app de consulta.

## 📦 Estructura del proyecto  
/ (raíz del proyecto)<br>
│<br>
├── main.py # Punto de entrada de FastAPI<br>
├── database.py # Configuración de MongoDB<br>
├── models.py # Modelos de datos (tanques)<br>
├── user_models.py # Modelos de usuario/autenticación<br>
├── auth.py # Lógica de autenticación (hash, tokens)<br>
├── auth_routes.py # Rutas de autenticación<br>
├── warthunder_todos_tanques.py # Script de scraping<br>
├── insertar_datos.py # Módulo para insertar datos en MongoDB<br>
└── requirements.txt # Dependencias de Python<br>
│<br>
└── war-thunder-frontend/ # Aplicación Angular<br>
├── package.json<br>
├── src/<br>
│ ├── app/ # Components, servicios, rutas<br>
│ ├── index.html<br>
│ └── styles.css<br>


> Nota: Se omiten aquí los archivos temporales, dependencias compiladas y credenciales.

## 🚀 Instalación y uso
Requieres de Python, MongoDB y Angular para trabajar con este proyecto
### 1. Backend  
1. Clona el repositorio, crea el entorno, actívalo e instala las dependencias:
  ```bash
   git clone https://github.com/usuario/Proyecto_War_Thunder_Tanques.git
   cd Proyecto_War_Thunder_Tanques
   python3 -m venv venv
   source venv/bin/activate
   # en Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Ejecuta el archivo [scrapper de todos los tanques](warthunder_todos_tanques.py) para obtener los datos. Una vez con ellos sigue con el proceso. Estos datos serán insertados en MongoDB, y vendrán en formato JSON.  
3. Crea un archivo .env, adaptando las variables de entorno de [.env.example](.env.example), en la raíz del proyecto
4. Ejecuta FastAPI con uvicorn main:app --reload. Abre otra terminal y ejecuta también [el fichero de inserción de datos](insertar_datos.py)
5. Sitúate en la terminal en la carpeta del [frontend](war-thunder-frontend/)
6. Ejecuta npm install y acto seguido ng serve
7. Listo, ya puedes probar mi proyecto

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
