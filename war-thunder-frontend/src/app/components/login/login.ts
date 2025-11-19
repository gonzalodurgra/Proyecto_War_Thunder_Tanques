import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService, LoginData } from '../../services/auth';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

// ====================================================================
// COMPONENTE DE LOGIN
// ====================================================================

@Component({
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrls: ['./login.css'],
  imports: [CommonModule, FormsModule]
})
export class LoginComponent {
  
  // ====================================================================
  // PROPIEDADES DEL COMPONENTE
  // ====================================================================
  
  // Datos del formulario
  loginData: LoginData = {
    username: '',
    password: ''
  };
  
  // Estados
  cargando: boolean = false;
  error: string = '';
  mostrarPassword: boolean = false;

  // ====================================================================
  // CONSTRUCTOR
  // ====================================================================
  // EXPLICACIÓN:
  // - AuthService: Para hacer login
  // - Router: Para redirigir después del login exitoso
  
  constructor(
    private authService: AuthService,
    private router: Router
  ) { }

  // ====================================================================
  // MÉTODO: HACER LOGIN
  // ====================================================================
  
  onSubmit(): void {
    // Validar que los campos no estén vacíos
    if (!this.loginData.username || !this.loginData.password) {
      this.error = 'Por favor completa todos los campos';
      return;
    }
    
    // Mostrar estado de carga
    this.cargando = true;
    this.error = '';
    
    // PASO 1: Llamar al servicio de autenticación
    this.authService.login(this.loginData).subscribe({
      next: (response) => {
        // SUCCESS: Login exitoso
        console.log('Login exitoso:');
        
        this.cargando = false;
        
        // PASO 2: Redirigir a la página de tanques
        this.router.navigate(['/tanques']);
      },
      error: (err) => {
        // ERROR: Credenciales incorrectas u otro error
        console.error('Error en login:', err);
        
        this.cargando = false;
        
        // Mostrar mensaje de error apropiado
        if (err.status === 401) {
          this.error = 'Usuario o contraseña incorrectos';
        } else {
          this.error = 'Error al iniciar sesión. Intenta de nuevo.';
        }
      }
    });
  }

  // ====================================================================
  // MÉTODO: TOGGLE MOSTRAR/OCULTAR PASSWORD
  // ====================================================================
  
  toggleMostrarPassword(): void {
    this.mostrarPassword = !this.mostrarPassword;
  }

  // ====================================================================
  // MÉTODO: IR A REGISTRO
  // ====================================================================
  
  irARegistro(): void {
    this.router.navigate(['/register']);
  }

  continuarComoInvitado() {
    if (this.cargando) return;
    this.router.navigate(['/tanques']);
  }
}
