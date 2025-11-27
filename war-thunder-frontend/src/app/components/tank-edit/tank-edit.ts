import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { TanksService, Tanque } from '../../services/tanks';
import { AuthService } from '../../services/auth';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef } from '@angular/core';
import { Municion } from '../../services/tanks';
import { Arma } from '../../services/tanks';
import { ImageUploadService } from '../../services/image-upload';

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

  // NUEVAS PROPIEDADES para la subida de imágenes
  archivoSeleccionado: File | null = null;
  subiendoImagen: boolean = false;
  mensajeImagen: string = '';
  
  // ====================================================================
  // CONSTRUCTOR
  // ====================================================================
  
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private tanksService: TanksService,
    private authService: AuthService,
    private cd: ChangeDetectorRef,
    // NUEVO: Inyectar el servicio de imágenes
    private imageUploadService: ImageUploadService
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
      // Crear tanque vacío
      this.tanque = this.crearTanqueVacio();

      // Preparar estructuras armamento/setup
      this.prepararEstructuraArmamento();
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
        this.prepararEstructuraArmamento();
        this.prepararMunicionesParaEdicion();
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
      rotacion_torreta_vertical_arcade: 0,
      armamento: {
        arma_principal: this.crearArmaVacia()
      },
      setup_1: {},
      setup_2: {}
    };
  }

  crearMunicionVacia(): Municion {
    return {
      nombre: '',
      tipo: '',
      penetracion_mm: [],
      masa_total: null,
      velocidad_bala: null,
      masa_explosivo: null
    };
  }

  crearArmaVacia(): Arma {
    return {
      municiones: [ this.crearMunicionVacia() ]
    };
  }

  agregarArma() {
    const key = 'arma_' + (Object.keys(this.tanque.armamento!).length + 1);

    this.tanque.armamento![key] = {
      municiones: [
        {
          nombre: '',
          tipo: '',
          penetracion_mm: [0, 0, 0, 0, 0, 0],
          masa_total: null,
          velocidad_bala: null,
          masa_explosivo: null
        }
      ]
    };
  }

  eliminarArma(key: string) {
    delete this.tanque.armamento![key];
  }

  agregarMunicion(key: string) {
    this.tanque.armamento![key].municiones.push({
      nombre: '',
      tipo: '',
      penetracion_mm: [],
      masa_total: null,
      velocidad_bala: null,
      masa_explosivo: null
    });
  }

  eliminarMunicion(key: string, index: number) {
    this.tanque.armamento![key].municiones.splice(index, 1);
  }

  convertirPenetracion(armaKey: string, index: number) {
    const texto = this.tanque.armamento![armaKey].municiones[index].penetracion_mm.toString() || '';

    this.tanque.armamento![armaKey].municiones[index].penetracion_mm =
      texto.split(',')
          .map(v => parseInt(v.trim(), 10))
          .filter(v => !isNaN(v));
  }

  prepararEstructuraArmamento() {
    if (!this.tanque.armamento) this.tanque.armamento = {};
    if (!this.tanque.setup_1) this.tanque.setup_1 = {};
    if (!this.tanque.setup_2) this.tanque.setup_2 = {};
  }

  private prepararMunicionesParaEdicion() {
    if (!this.tanque.armamento) return;

    for (const armaKey of Object.keys(this.tanque.armamento)) {
      const arma = this.tanque.armamento[armaKey];

      arma.municiones.forEach(m => {
        (m as any).penetracion_mmString = m.penetracion_mm.join(', ');
      });
    }
  }
  get armaKeys(): string[] {
    return this.tanque?.armamento ? Object.keys(this.tanque.armamento) : [];
  }

  // ... tu código existente (ngOnInit, cargarTanque, etc.) ...

  // ====================================================================
  // NUEVO MÉTODO: Cuando el usuario selecciona una imagen
  // ====================================================================
  
  /**
   * Se ejecuta cuando el usuario selecciona un archivo
   * 
   * EXPLICACIÓN:
   * 1. Obtiene el archivo del evento del input
   * 2. Verifica que sea una imagen
   * 3. Guarda el archivo temporalmente
   * 4. Muestra una vista previa (opcional)
   * 
   * @param event - Evento del input file
   */
  onImagenSeleccionada(event: any): void {
    // PASO 1: Obtener el archivo del input
    const archivo: File = event.target.files[0];
    
    // PASO 2: Verificar que se seleccionó algo
    if (!archivo) {
      return;
    }
    
    // PASO 3: Verificar que sea una imagen
    if (!archivo.type.startsWith('image/')) {
      this.mensajeImagen = '⚠️ Por favor selecciona una imagen válida';
      return;
    }
    
    // PASO 4: Guardar el archivo seleccionado
    this.archivoSeleccionado = archivo;
    this.mensajeImagen = `✅ Imagen seleccionada: ${archivo.name}`;
    
    console.log('Imagen seleccionada:', archivo.name, 'Tamaño:', archivo.size, 'bytes');
  }

  // ====================================================================
  // NUEVO MÉTODO: Subir la imagen al servidor
  // ====================================================================
  
  /**
   * Sube la imagen seleccionada al servidor
   * 
   * EXPLICACIÓN PASO A PASO:
   * 1. Verifica que haya una imagen seleccionada
   * 2. Muestra un indicador de carga
   * 3. Llama al servicio para subir la imagen
   * 4. Actualiza el campo imagen_local con la ruta
   * 5. Muestra un mensaje de confirmación
   */
  subirImagen(): void {
    // PASO 1: Verificar que hay un archivo seleccionado
    if (!this.archivoSeleccionado) {
      this.mensajeImagen = '⚠️ Por favor selecciona una imagen primero';
      return;
    }
    
    // PASO 2: Activar indicador de carga
    this.subiendoImagen = true;
    this.mensajeImagen = '⏳ Subiendo imagen...';
    
    // PASO 3: Llamar al servicio para subir la imagen
    this.imageUploadService.subirImagenTanque(this.archivoSeleccionado).subscribe({
      
      // Si la subida es EXITOSA
      next: (respuesta) => {
        console.log('Imagen subida:', respuesta);
        
        // PASO 4: Actualizar el campo imagen_local del tanque
        // Guardamos la ruta relativa que devuelve el servidor
        this.tanque.imagen_local = respuesta.ruta;
        
        // PASO 5: Mostrar mensaje de éxito
        this.mensajeImagen = `✅ ${respuesta.mensaje}`;
        this.subiendoImagen = false;
        
        // Limpiar la selección
        this.archivoSeleccionado = null;
        
        // Forzar detección de cambios para actualizar la vista previa
        this.cd.detectChanges();
      },
      
      // Si hay un ERROR
      error: (error) => {
        console.error('Error al subir imagen:', error);
        
        this.mensajeImagen = `❌ Error: ${error.error?.detail || 'No se pudo subir la imagen'}`;
        this.subiendoImagen = false;
      }
    });
  }

  // ====================================================================
  // NUEVO MÉTODO: Obtener URL completa de la imagen
  // ====================================================================
  
  /**
   * Obtiene la URL completa de la imagen para mostrarla
   * 
   * @returns URL completa de la imagen o null si no hay
   */
  obtenerUrlImagen(): string | null {
    if (!this.tanque.imagen_local) {
      return null;
    }
    
    return this.imageUploadService.obtenerUrlImagen(this.tanque.imagen_local);
  }
}
