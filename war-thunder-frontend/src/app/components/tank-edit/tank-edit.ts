import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { TanksService, Tanque } from '../../services/tanks';
import { AuthService } from '../../services/auth';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef } from '@angular/core';

// ====================================================================
// COMPONENTE DE EDICIÓN DE TANQUES
// ====================================================================

@Component({
  selector: 'app-tank-edit',
  templateUrl: './tank-edit.html',
  styleUrls: ['./tank-edit.css'],
  imports: [CommonModule, FormsModule]
})
export class TankEditComponent implements OnInit {
  
  // ====================================================================
  // PROPIEDADES
  // ====================================================================
  
  tanque: Tanque = this.crearTanqueVacio();
  tanqueId: string | null = null;
  modoEdicion: boolean = false; // false = crear, true = editar
  
  cargando: boolean = false;
  guardando: boolean = false;
  error: string = '';
  
  // ====================================================================
  // CONSTRUCTOR
  // ====================================================================
  
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private tanksService: TanksService,
    private authService: AuthService,
    private cd: ChangeDetectorRef
  ) { }

  // ====================================================================
  // INICIALIZACIÓN
  // ====================================================================
  
  ngOnInit(): void {
    // Verificar autenticación
    if (!this.authService.isLoggedIn()) {
      alert('Debes iniciar sesión para editar tanques');
      this.router.navigate(['/login']);
      return;
    }
    
    // Obtener el ID del tanque de la URL (si existe)
    this.tanqueId = this.route.snapshot.paramMap.get('id');
    if (this.tanqueId) {
      // Modo edición: cargar el tanque existente
      this.modoEdicion = true;
      this.cargarTanque();
    } else {
      // Modo creación: usar tanque vacío
      this.modoEdicion = false;
    }
  }

  // ====================================================================
  // MÉTODO: Cargar tanque existente
  // ====================================================================
  
  cargarTanque(): void {
    if (!this.tanqueId) return;
    
    this.cargando = true;
    this.error = '';
    
    this.tanksService.obtenerTanquePorId(this.tanqueId).subscribe({
      next: (data) => {
        console.log(data)
        Object.assign(this.tanque, data);
        this.cargando = false;
        this.cd.detectChanges();
      },
      error: (err) => {
        console.error('Error al cargar tanque:', err);
        this.error = 'No se pudo cargar el tanque';
        this.cargando = false;
      }
    });
  }

  // ====================================================================
  // MÉTODO: Guardar tanque (crear o actualizar)
  // ====================================================================
  
  guardarTanque(): void {
    // Validar campos obligatorios
    if (!this.validarTanque()) {
      return;
    }
    
    this.guardando = true;
    this.error = '';
    
    if (this.modoEdicion && this.tanqueId) {
      // Actualizar tanque existente
      this.actualizarTanque();
    } else {
      // Crear nuevo tanque
      this.crearTanque();
    }
  }

  // ====================================================================
  // MÉTODO: Crear nuevo tanque
  // ====================================================================
  
  crearTanque(): void {
    this.tanksService.crearTanque(this.tanque).subscribe({
      next: (response) => {
        console.log('Tanque creado:', response);
        alert('Tanque creado exitosamente');
        this.router.navigate(['/tanques']);
      },
      error: (err) => {
        console.error('Error al crear tanque:', err);
        this.guardando = false;
        
        if (err.status === 401) {
          this.error = 'Tu sesión ha expirado. Por favor inicia sesión nuevamente.';
          setTimeout(() => this.router.navigate(['/login']), 2000);
        } else {
          this.error = 'Error al crear el tanque. Verifica los datos.';
        }
      }
    });
  }

  // ====================================================================
  // MÉTODO: Actualizar tanque existente
  // ====================================================================
  
  actualizarTanque(): void {
    if (!this.tanqueId) return;
    
    this.tanksService.actualizarTanque(this.tanqueId, this.tanque).subscribe({
      next: (response) => {
        console.log('Tanque actualizado:', response);
        alert('Tanque actualizado exitosamente');
        this.router.navigate(['/tanques']);
      },
      error: (err) => {
        console.error('Error al actualizar tanque:', err);
        this.guardando = false;
        
        if (err.status === 401) {
          this.error = 'Tu sesión ha expirado. Por favor inicia sesión nuevamente.';
          setTimeout(() => this.router.navigate(['/login']), 2000);
        } else {
          this.error = 'Error al actualizar el tanque. Verifica los datos.';
        }
      }
    });
  }

  // ====================================================================
  // MÉTODO: Validar tanque
  // ====================================================================
  
  validarTanque(): boolean {
    if (!this.tanque.nombre || this.tanque.nombre.trim() === '') {
      this.error = 'El nombre del tanque es obligatorio';
      return false;
    }
    
    if (!this.tanque.nacion || this.tanque.nacion.trim() === '') {
      this.error = 'La nación es obligatoria';
      return false;
    }
    
    if (!this.tanque.rol || this.tanque.rol.trim() === '') {
      this.error = 'El rol es obligatorio';
      return false;
    }
    if (!this.tanque.tripulacion || this.tanque.rol.trim() === '') {
      this.error = 'La tripulación es obligatoria';
      return false;
    }
    if (!this.tanque.peso || this.tanque.peso === null) {
      this.error = 'El peso es obligatorio';
      return false;
    }
    if (this.tanque.blindaje_chasis === null) {
      this.error = 'El blindaje frontal del chasis es obligatorio';
      return false;
    }
    if (this.tanque.blindaje_torreta === null) {
      this.error = 'El blindaje frontal de la torreta es obligatorio';
      return false;
    }
    if(!this.tanque.velocidad_adelante_arcade || this.tanque.velocidad_adelante_arcade === null){
      this.error = "La velocidad punta es obligatoria"
    }
    if(!this.tanque.velocidad_atras_arcade || this.tanque.velocidad_atras_arcade === null){
      this.error = "La velocidad marcha atrás es obligatoria"
    }
    return true;
  }

  // ====================================================================
  // MÉTODO: Cancelar y volver
  // ====================================================================
  
  cancelar(): void {
    if (confirm('¿Estás seguro? Los cambios no guardados se perderán.')) {
      this.router.navigate(['/tanques']);
    }
  }

  // ====================================================================
  // MÉTODO: Crear tanque vacío con valores por defecto
  // ====================================================================
  
  crearTanqueVacio(): Tanque {
    return {
      nombre: '',
      imagen_local: '',
      rol: '',
      nacion: '',
      rating_arcade: '1.0',
      tripulacion: 0,
      visibilidad: 0,
      peso: 0,
      blindaje_chasis: 0,
      blindaje_torreta: 0,
      velocidad_adelante_arcade: 0,
      velocidad_atras_arcade: 0,
      relacion_potencia_peso: 0,
      angulo_depresion: 0,
      angulo_elevacion: 0,
      recarga: 0,
      cadencia: 0,
      cargador: 0,
      municion_total: 0,
      rotacion_torreta_horizontal_arcade: 0,
      rotacion_torreta_vertical_arcade: 0
    };
  }
}
