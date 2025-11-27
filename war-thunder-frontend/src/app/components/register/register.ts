import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService, Usuario } from '../../services/auth';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

// ====================================================================
// COMPONENTE DE REGISTRO
// ====================================================================

@Component({
  selector: 'app-register',
  templateUrl: './register.html',
  styleUrls: ['./register.css'],
  imports: [CommonModule, FormsModule]
})
export class RegisterComponent {
  
  // ====================================================================
  // PROPIEDADES DEL COMPONENTE
  // ====================================================================
  
  // Datos del formulario
  usuario: Usuario = {
    username: '',
    email: '',
    password: '',
    nombre_completo: '',
    es_admin: false
  };
  
  // Confirmación de contraseña
  confirmarPassword: string = '';
  
  // Estados
  cargando: boolean = false;
  error: string = '';
  exito: boolean = false;
  mostrarPassword: boolean = false;
  mostrarConfirmarPassword: boolean = false;

  // ====================================================================
  // CONSTRUCTOR
  // ====================================================================
  
  constructor(
    private authService: AuthService,
    private router: Router
  ) { }

  // ====================================================================
  // MÉTODO: VALIDAR FORMULARIO
  // ====================================================================
  
  validarFormulario(): boolean {
    // Validar que todos los campos estén completos
    if (!this.usuario.username || !this.usuario.email || 
        !this.usuario.password || !this.confirmarPassword) {
      this.error = 'Por favor completa todos los campos obligatorios';
      return false;
    }
    
    // Validar longitud del username
    if (this.usuario.username.length < 3) {
      this.error = 'El nombre de usuario debe tener al menos 3 caracteres';
      return false;
    }
    
    // Validar formato de email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.usuario.email)) {
      this.error = 'Por favor ingresa un email válido';
      return false;
    }
    
    // Validar longitud de contraseña
    if (this.usuario.password.length < 6) {
      this.error = 'La contraseña debe tener al menos 6 caracteres';
      return false;
    }
    
    // Validar que las contraseñas coincidan
    if (this.usuario.password !== this.confirmarPassword) {
      this.error = 'Las contraseñas no coinciden';
      return false;
    }
    
    return true;
  }

  // ====================================================================
  // MÉTODO: REGISTRAR USUARIO
  // ====================================================================
  
  onSubmit(): void {
    // Limpiar mensajes anteriores
    this.error = '';
    this.exito = false;
    
    // Validar formulario
    if (!this.validarFormulario()) {
      return;
    }
    
    // Mostrar estado de carga
    this.cargando = true;
    
    // PASO 1: Llamar al servicio de registro
    this.authService.registrar(this.usuario).subscribe({
      next: (response) => {
        // SUCCESS: Registro exitoso
        console.log('Usuario registrado:', response);
        
        this.cargando = false;
        this.exito = true;
        
        // PASO 2: Esperar 2 segundos y redirigir al login
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 2000);
      },
      error: (err) => {
        // ERROR: El usuario/email ya existe u otro error
        console.error('Error en registro:', err);
        
        this.cargando = false;
        
        // Mostrar mensaje de error apropiado
        if (err.error && err.error.detail) {
          this.error = err.error.detail;
        } else {
          this.error = 'Error al registrar usuario. Intenta de nuevo.';
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
  
  toggleMostrarConfirmarPassword(): void {
    this.mostrarConfirmarPassword = !this.mostrarConfirmarPassword;
  }

  // ====================================================================
  // MÉTODO: VOLVER AL LOGIN
  // ====================================================================
  
  volverAlLogin(): void {
    this.router.navigate(['/login']);
  }

  // ====================================================================
  // MÉTODO: VERIFICAR FORTALEZA DE LA CONTRASEÑA
  // ====================================================================
  
  obtenerFortalezaPassword(): string {
    const password = this.usuario.password;
    
    if (password.length === 0) return '';
    if (password.length < 6) return 'débil';
    if (password.length < 10) return 'media';
    
    // Verificar si tiene números, mayúsculas y minúsculas
    const tieneNumeros = /\d/.test(password);
    const tieneMayusculas = /[A-Z]/.test(password);
    const tieneMinusculas = /[a-z]/.test(password);
    const tieneEspeciales = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    const criterios = [tieneNumeros, tieneMayusculas, tieneMinusculas, tieneEspeciales]
      .filter(Boolean).length;
    
    if (criterios >= 3) return 'fuerte';
    return 'media';
  }
  
  obtenerColorFortaleza(): string {
    const fortaleza = this.obtenerFortalezaPassword();
    
    switch (fortaleza) {
      case 'débil': return '#f44336';
      case 'media': return '#ff9800';
      case 'fuerte': return '#4caf50';
      default: return '#ddd';
    }
  }
}