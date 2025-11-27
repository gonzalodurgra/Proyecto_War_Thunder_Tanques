// src/app/services/pending-changes.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth';
import { environment } from '../../environments/environment';

// Interfaz para un cambio pendiente
export interface CambioPendiente {
  _id?: string;
  tipo_operacion: 'crear' | 'actualizar' | 'eliminar';
  coleccion: string;
  usuario_id: string;
  usuario_email: string;
  tanque_id?: string;
  datos_originales?: any;
  datos_nuevos?: any;
  estado: 'pendiente' | 'aprobado' | 'rechazado';
  fecha_solicitud: string;
  fecha_revision?: string;
  admin_revisor_id?: string;
  admin_revisor_email?: string;
  comentario_admin?: string;
}

// Interfaz para revisar un cambio
export interface RevisionCambio {
  aprobar: boolean;
  comentario?: string;
}

@Injectable({
  providedIn: 'root'
})
export class PendingChangesService {
  
  private apiUrl = environment.apiUrl;

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) { }

  /**
   * Obtiene los headers con el token de autenticación
   */
  private getHeaders(): HttpHeaders {
    const token = this.authService.getToken();
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  /**
   * Obtiene todos los cambios pendientes (solo admin)
   * 
   * @param estado - Filtrar por estado: 'pendiente', 'aprobado', 'rechazado', 'todos'
   */
  obtenerCambiosPendientes(estado: string = 'pendiente'): Observable<CambioPendiente[]> {
    return this.http.get<CambioPendiente[]>(
      `${this.apiUrl}/?estado=${estado}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Obtiene un cambio específico por ID
   */
  obtenerCambioPorId(cambioId: string): Observable<CambioPendiente> {
    return this.http.get<CambioPendiente>(
      `${this.apiUrl}/${cambioId}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Aprueba o rechaza un cambio pendiente (solo admin)
   * 
   * @param cambioId - ID del cambio a revisar
   * @param revision - Objeto con la decisión (aprobar/rechazar) y comentario opcional
   */
  revisarCambio(cambioId: string, revision: RevisionCambio): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/${cambioId}/revisar`,
      revision,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Obtiene los cambios del usuario actual
   */
  obtenerMisCambios(): Observable<CambioPendiente[]> {
    return this.http.get<CambioPendiente[]>(
      `${this.apiUrl}/mis-cambios/`,
      { headers: this.getHeaders() }
    );
  }
}
