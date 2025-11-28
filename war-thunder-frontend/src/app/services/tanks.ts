import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { map } from 'rxjs';

// ====================================================================
// PASO 1: Definir las interfaces (tipos de datos)
// ====================================================================
// EXPLICACIÓN: Las interfaces en TypeScript son como los modelos de Pydantic
// Definen la estructura de los datos que esperamos recibir

export interface Municion {
  nombre: string;
  tipo: string;
  penetracion_mm: number[];
  masa_total?: number | null;
  velocidad_bala?: number | null;
  masa_explosivo?: number | null;
}

export interface Arma {
  municiones: Municion[];
}

export interface Tanque {
  _id?: string;  // El signo ? significa que es opcional
  nombre: string;
  rol: string;
  imagen_local: string;
  nacion: string;
  rating_arcade: string;
  tripulacion: number;
  visibilidad: number;
  peso: number;
  blindaje_chasis: number;
  blindaje_torreta: number;
  velocidad_adelante_arcade: number;
  velocidad_atras_arcade: number;
  relacion_potencia_peso: number;
  angulo_depresion: number;
  angulo_elevacion: number;
  recarga: number;
  cadencia: number;
  cargador: number;
  municion_total: number;
  rotacion_torreta_horizontal_arcade: number;
  rotacion_torreta_vertical_arcade: number;
  armamento?: { [key: string]: Arma }
  setup_1?: { [key: string]: Arma };
  setup_2?: { [key: string]: Arma };
}

const URL_IMAGENES = 'https://proyecto-war-thunder-tanques.onrender.com/';

// ====================================================================
// PASO 2: Crear el servicio
// ====================================================================
// EXPLICACIÓN: @Injectable significa que este servicio puede ser
// inyectado en componentes y otros servicios

@Injectable({
  providedIn: 'root'  // Hace el servicio disponible en toda la aplicación
})
export class TanksService {
  // URL base de tu API FastAPI
  private apiUrl = environment.apiUrl;
  
  // Headers HTTP opcionales (por si necesitas añadir autenticación después)
  // private httpOptions = {
  //   headers: new HttpHeaders({
  //     'Content-Type': 'application/json'
  //   })
  // };

  // EXPLICACIÓN: HttpClient es el módulo de Angular para hacer peticiones HTTP
  // Lo inyectamos en el constructor
  constructor(private http: HttpClient) { }

  // ====================================================================
  // MÉTODO 1: Obtener todos los tanques (GET)
  // ====================================================================
  obtenerTodosLosTanques(): Observable<Tanque[]> {
    return this.http.get<Tanque[]>(`${this.apiUrl}/tanques/`).pipe(
      map(tanques =>
        tanques.map(tanque => ({
          ...tanque,
          imagen_local: `${URL_IMAGENES}${tanque.imagen_local}`
        }))
      )
    );
  }

  // ====================================================================
  // MÉTODO 2: Obtener un tanque por ID (GET)
  // ====================================================================
  obtenerTanquePorId(id: string): Observable<Tanque> {
    return this.http.get<Tanque>(`${this.apiUrl}/tanques/${id}`).pipe(
      map(tanque => ({
        ...tanque,
        imagen_local: `${URL_IMAGENES}${tanque.imagen_local}`
      }))
    );
  }

  // ====================================================================
  // MÉTODO 3: Obtener tanques por nación (GET)
  // ====================================================================
  obtenerTanquesPorNacion(nacion: string): Observable<Tanque[]> {
    const nacionCodificada = encodeURIComponent(nacion);
    return this.http.get<Tanque[]>(`${this.apiUrl}/tanques/nacion/${nacionCodificada}`).pipe(
      map(tanques =>
        tanques.map(tanque => ({
          ...tanque,
          imagen_local: `${URL_IMAGENES}${tanque.imagen_local}`
        }))
      )
    );
  }

  // ====================================================================
  // MÉTODO 4: Crear un nuevo tanque (POST)
  // ====================================================================
  crearTanque(tanque: Tanque): Observable<any> {
    // EXPLICACIÓN:
    // - Omitimos el _id porque MongoDB lo genera automáticamente
    // - Enviamos el tanque en el body de la petición
    const { _id, ...tanqueSinId } = tanque;
    
    return this.http.post<any>(
      `${this.apiUrl}/tanques/`,
      tanqueSinId,
      this.getAuthHeaders()
    );
  }

  // ====================================================================
  // MÉTODO 5: Actualizar un tanque (PUT)
  // ====================================================================
  actualizarTanque(id: string, tanque: Tanque): Observable<any> {
    const { _id, ...tanqueSinId } = tanque;
    
    return this.http.put<any>(
      `${this.apiUrl}/tanques/${id}`,
      tanqueSinId,
      this.getAuthHeaders()
    );
  }

  // ====================================================================
  // MÉTODO 6: Eliminar un tanque (DELETE)
  // ====================================================================
  eliminarTanque(id: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/tanques/${id}`, this.getAuthHeaders());
  }

  // ====================================================================
  // MÉTODO 7: Obtener naciones únicas (útil para filtros)
  // ====================================================================
  obtenerNacionesUnicas(): Observable<string[]> {
    // EXPLICACIÓN: Este método procesa los tanques para obtener
    // una lista única de naciones
    
    return new Observable(observer => {
      this.obtenerTodosLosTanques().subscribe({
        next: (tanques) => {
          // Extraer todas las naciones
          const naciones = tanques.map(t => t.nacion);
          
          // Obtener valores únicos usando Set
          const nacionesUnicas = Array.from(new Set(naciones));
          
          // Ordenar alfabéticamente
          nacionesUnicas.sort();
          
          observer.next(nacionesUnicas);
          observer.complete();
        },
        error: (error) => {
          observer.error(error);
        }
      });
    });
  }

  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    
    return {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      })
    };
  }
}
