import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs';

// ====================================================================
// INTERFACES
// ====================================================================

export interface Usuario {
  username: string;
  email: string;
  password: string;
  nombre_completo?: string;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export interface UsuarioPerfil {
  username: string;
  email: string;
  nombre_completo?: string;
  disabled: boolean;
  created_at: string;
}

// ====================================================================
// SERVICIO DE AUTENTICACIÓN
// ====================================================================

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/auth';
  
  // BehaviorSubject para mantener el estado de autenticación
  // EXPLICACIÓN: BehaviorSubject es como una variable observable
  // Cualquier componente puede suscribirse y saber si el usuario está logueado
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.hasToken());
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();
  
  private currentUserSubject = new BehaviorSubject<string | null>(this.getUsername());
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) { }

  // ====================================================================
  // MÉTODO 1: REGISTRAR USUARIO
  // ====================================================================
  registrar(usuario: Usuario): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, usuario);
  }

  // ====================================================================
  // MÉTODO 2: LOGIN
  // ====================================================================
  login(loginData: LoginData): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.apiUrl}/login`, loginData).pipe(
      tap(response => {
        // Guardar el token en localStorage
        // EXPLICACIÓN: localStorage guarda datos en el navegador
        // Persisten aunque cierres la pestaña
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('username', response.username);
        
        // Actualizar el estado de autenticación
        this.isAuthenticatedSubject.next(true);
        this.currentUserSubject.next(response.username);
      })
    );
  }

  // ====================================================================
  // MÉTODO 3: LOGOUT
  // ====================================================================
  logout(): void {
    // Eliminar el token del localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    
    // Actualizar el estado
    this.isAuthenticatedSubject.next(false);
    this.currentUserSubject.next(null);
  }

  // ====================================================================
  // MÉTODO 4: OBTENER EL TOKEN
  // ====================================================================
  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  // ====================================================================
  // MÉTODO 5: VERIFICAR SI HAY TOKEN
  // ====================================================================
  hasToken(): boolean {
    return !!this.getToken();
  }

  // ====================================================================
  // MÉTODO 6: OBTENER NOMBRE DE USUARIO
  // ====================================================================
  getUsername(): string | null {
    return localStorage.getItem('username');
  }

  // ====================================================================
  // MÉTODO 7: VERIFICAR SI ESTÁ AUTENTICADO
  // ====================================================================
  isLoggedIn(): boolean {
    return this.hasToken();
  }

  // ====================================================================
  // MÉTODO 8: OBTENER PERFIL DEL USUARIO
  // ====================================================================
  obtenerPerfil(): Observable<UsuarioPerfil> {
    // IMPORTANTE: Esta petición requiere el token en el header
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`
    });
    
    return this.http.get<UsuarioPerfil>(`${this.apiUrl}/me`, { headers });
  }

  // ====================================================================
  // MÉTODO 9: OBTENER HEADERS CON AUTORIZACIÓN
  // ====================================================================
  getAuthHeaders(): HttpHeaders {
    const token = this.getToken();
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }
}
