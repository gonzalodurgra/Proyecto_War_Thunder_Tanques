// src/app/components/admin-panel/admin-panel.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PendingChangesService, CambioPendiente } from '../../services/pending-changes';
import { AuthService } from '../../services/auth';
import { Router } from '@angular/router';

@Component({
  selector: 'app-admin-panel',
  templateUrl: './admin-panel.html',
  styleUrls: ['./admin-panel.css'],
  standalone: true,
  imports: [CommonModule, FormsModule]
})
export class AdminPanelComponent implements OnInit {
  
  // Lista de cambios pendientes
  cambiosPendientes: CambioPendiente[] = [];
  
  // Cambio seleccionado para ver detalles
  cambioSeleccionado: CambioPendiente | null = null;
  
  // Estados de carga
  cargando: boolean = false;
  procesando: boolean = false;
  
  // Filtro de estado
  filtroEstado: string = 'pendiente';
  
  // Comentario del admin
  comentarioAdmin: string = '';
  
  // Mensajes
  mensaje: string = '';
  tipoMensaje: 'success' | 'error' | 'info' = 'info';

  constructor(
    private pendingChangesService: PendingChangesService,
    private authService: AuthService,
    private router: Router
  ) { }

  ngOnInit(): void {
    // Verificar que el usuario es admin
    if (!this.authService.isAdmin()) {
      alert('No tienes permisos para acceder a esta página');
      this.router.navigate(['/tanques']);
      return;
    }
    
    this.cargarCambiosPendientes();
  }

  /**
   * Carga los cambios pendientes del servidor
   */
  cargarCambiosPendientes(): void {
    this.cargando = true;
    this.mensaje = '';
    
    this.pendingChangesService.obtenerCambiosPendientes(this.filtroEstado).subscribe({
      next: (cambios) => {
        this.cambiosPendientes = cambios;
        this.cargando = false;
        
        if (cambios.length === 0) {
          this.mensaje = 'No hay cambios con este estado';
          this.tipoMensaje = 'info';
        }
      },
      error: (error) => {
        console.error('Error al cargar cambios:', error);
        this.mensaje = 'Error al cargar los cambios pendientes';
        this.tipoMensaje = 'error';
        this.cargando = false;
      }
    });
  }

  /**
   * Cambia el filtro de estado y recarga
   */
  cambiarFiltro(estado: string): void {
    this.filtroEstado = estado;
    this.cargarCambiosPendientes();
  }

  /**
   * Selecciona un cambio para ver detalles
   */
  verDetalles(cambio: CambioPendiente): void {
    this.cambioSeleccionado = cambio;
    this.comentarioAdmin = '';
  }

  /**
   * Cierra el modal de detalles
   */
  cerrarDetalles(): void {
    this.cambioSeleccionado = null;
    this.comentarioAdmin = '';
  }

  /**
   * Aprueba un cambio
   */
  aprobarCambio(cambio: CambioPendiente): void {
    if (!confirm('¿Estás seguro de aprobar este cambio?')) {
      return;
    }
    
    this.procesarCambio(cambio._id!, true);
  }

  /**
   * Rechaza un cambio
   */
  rechazarCambio(cambio: CambioPendiente): void {
    if (!this.comentarioAdmin || this.comentarioAdmin.trim() === '') {
      alert('Por favor proporciona un comentario explicando por qué rechazas este cambio');
      return;
    }
    
    if (!confirm('¿Estás seguro de rechazar este cambio?')) {
      return;
    }
    
    this.procesarCambio(cambio._id!, false);
  }

  /**
   * Procesa la aprobación o rechazo de un cambio
   */
  private procesarCambio(cambioId: string, aprobar: boolean): void {
    this.procesando = true;
    this.mensaje = '';
    
    const revision = {
      aprobar: aprobar,
      comentario: this.comentarioAdmin || undefined
    };
    
    this.pendingChangesService.revisarCambio(cambioId, revision).subscribe({
      next: (response) => {
        this.mensaje = response.mensaje;
        this.tipoMensaje = 'success';
        this.procesando = false;
        
        // Cerrar modal
        this.cerrarDetalles();
        
        // Recargar lista
        this.cargarCambiosPendientes();
      },
      error: (error) => {
        console.error('Error al revisar cambio:', error);
        this.mensaje = error.error?.detail || 'Error al procesar el cambio';
        this.tipoMensaje = 'error';
        this.procesando = false;
      }
    });
  }

  /**
   * Obtiene un label descriptivo del tipo de operación
   */
  getOperacionLabel(tipo: string): string {
    const labels: { [key: string]: string } = {
      'crear': '➕ Crear',
      'actualizar': '✏️ Actualizar',
      'eliminar': '🗑️ Eliminar'
    };
    return labels[tipo] || tipo;
  }

  /**
   * Obtiene la clase CSS según el tipo de operación
   */
  getOperacionClass(tipo: string): string {
    const classes: { [key: string]: string } = {
      'crear': 'operacion-crear',
      'actualizar': 'operacion-actualizar',
      'eliminar': 'operacion-eliminar'
    };
    return classes[tipo] || '';
  }

  /**
   * Obtiene la clase CSS según el estado
   */
  getEstadoClass(estado: string): string {
    const classes: { [key: string]: string } = {
      'pendiente': 'estado-pendiente',
      'aprobado': 'estado-aprobado',
      'rechazado': 'estado-rechazado'
    };
    return classes[estado] || '';
  }

  /**
   * Formatea una fecha ISO a formato legible
   */
  formatearFecha(fechaISO: string): string {
    const fecha = new Date(fechaISO);
    return fecha.toLocaleString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Obtiene las diferencias entre datos originales y nuevos
   */
  getDiferencias(cambio: CambioPendiente): string[] {
    if (!cambio.datos_originales || !cambio.datos_nuevos) {
      return [];
    }

    const diferencias: string[] = [];
    const keys = new Set([
      ...Object.keys(cambio.datos_originales),
      ...Object.keys(cambio.datos_nuevos)
    ]);

    keys.forEach(key => {
      if (key === '_id') return; // Ignorar el ID
      
      const valorOriginal = cambio.datos_originales![key];
      const valorNuevo = cambio.datos_nuevos![key];

      if (JSON.stringify(valorOriginal) !== JSON.stringify(valorNuevo)) {
        diferencias.push(
          `${key}: "${valorOriginal}" → "${valorNuevo}"`
        );
      }
    });

    return diferencias;
  }
}
