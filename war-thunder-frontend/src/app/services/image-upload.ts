// src/app/services/image-upload.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// Interfaz para la respuesta del servidor
interface RespuestaSubida {
  mensaje: string;
  nombre_archivo: string;
  ruta: string;
}

@Injectable({
  providedIn: 'root'
})
export class ImageUploadService {
  
  // URL base de tu API FastAPI
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  /**
   * Sube una imagen de tanque al servidor
   * 
   * EXPLICACIÓN PASO A PASO:
   * 1. Recibe un archivo File desde el componente
   * 2. Crea un FormData (estructura especial para enviar archivos)
   * 3. Añade el archivo al FormData
   * 4. Envía la petición POST al backend
   * 5. Retorna un Observable que el componente puede suscribirse
   * 
   * @param file - Archivo de imagen seleccionado por el usuario
   * @returns Observable con la respuesta del servidor
   */
  subirImagenTanque(file: File): Observable<RespuestaSubida> {
    // PASO 1: Crear FormData
    // FormData es necesario para enviar archivos desde el navegador
    const formData = new FormData();
    
    // PASO 2: Añadir el archivo
    // 'file' es el nombre del parámetro que espera FastAPI
    // file es el objeto File
    // file.name es el nombre original del archivo
    formData.append('file', file, file.name);
    
    // PASO 3: Enviar la petición POST
    // El HttpClient automáticamente establece los headers correctos para FormData
    return this.http.post<RespuestaSubida>(
      `${this.apiUrl}/upload-tank-image/`, 
      formData
    );
  }

  /**
   * Construye la URL completa de una imagen
   * Para mostrar la imagen en el template
   * 
   * @param rutaImagen - Ruta relativa de la imagen (ej: "imagenes/tanque.jpg")
   * @returns URL completa (ej: "http://localhost:8000/imagenes/tanque.jpg")
   */
  obtenerUrlImagen(rutaImagen: string): string {
    // Si la ruta ya es completa (empieza con http), devolverla tal cual
    if (rutaImagen.startsWith('http')) {
      return rutaImagen;
    }
    
    // Si es una ruta relativa, construir la URL completa
    return `${this.apiUrl}/${rutaImagen}`;
  }
}
