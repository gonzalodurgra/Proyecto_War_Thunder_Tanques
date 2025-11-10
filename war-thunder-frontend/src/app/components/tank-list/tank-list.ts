import { Component, OnInit } from '@angular/core';
import { TanksService, Tanque } from '../../services/tanks';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';


// ====================================================================
// Configuración del componente
// ====================================================================
@Component({
  standalone: true,
  selector: 'app-tank-list',  // Nombre para usar en HTML: <app-tank-list>
  templateUrl: './tank-list.html',
  styleUrls: ['./tank-list.css'],
  imports: [CommonModule, FormsModule]
})
export class TankListComponent implements OnInit {
  
  // ====================================================================
  // PASO 1: Declarar las propiedades del componente
  // ====================================================================
  
  // Lista de tanques que se mostrará
  tanques: Tanque[] = [];
  
  // Tanques filtrados (para búsqueda y filtros)
  tanquesFiltrados: Tanque[] = [];
  
  // Lista de naciones disponibles
  naciones: string[] = [];
  
  // Estados de la aplicación
  cargando: boolean = false;
  error: string = '';
  
  // Filtros
  filtroNacion: string = '';
  filtroBusqueda: string = '';
  
  // Tanque seleccionado para ver detalles
  tanqueSeleccionado: Tanque | null = null;

  // ====================================================================
  // PASO 2: Inyectar el servicio en el constructor
  // ====================================================================
  constructor(private tanksService: TanksService) {
    // EXPLICACIÓN: Angular automáticamente crea una instancia de TanksService
    // y la inyecta aquí. Esto se llama "Inyección de Dependencias"
  }

  // ====================================================================
  // PASO 3: Cargar datos al iniciar el componente
  // ====================================================================
  ngOnInit(): void {
    // EXPLICACIÓN: ngOnInit se ejecuta cuando el componente se carga
    // Es el lugar ideal para cargar los datos iniciales
    
    this.cargarTanques();
    this.cargarNaciones();
  }

  // ====================================================================
  // MÉTODO: Cargar todos los tanques
  // ====================================================================
  cargarTanques(): void {
    this.cargando = true;
    this.error = '';
    
    // EXPLICACIÓN: subscribe() es como .then() en promesas
    // Se ejecuta cuando la petición HTTP termina
    this.tanksService.obtenerTodosLosTanques().subscribe({
      next: (data) => {
        // SUCCESS: Los datos llegaron correctamente
        console.log('Tanques cargados:', data);
        this.tanques = data;
        this.tanquesFiltrados = data;
        this.cargando = false;
      },
      error: (err) => {
        // ERROR: Algo salió mal
        console.error('Error al cargar tanques:', err);
        this.error = 'No se pudieron cargar los tanques. Verifica que la API esté corriendo.';
        this.cargando = false;
      }
    });
  }

  // ====================================================================
  // MÉTODO: Cargar las naciones disponibles
  // ====================================================================
  cargarNaciones(): void {
    this.tanksService.obtenerNacionesUnicas().subscribe({
      next: (naciones) => {
        this.naciones = naciones;
      },
      error: (err) => {
        console.error('Error al cargar naciones:', err);
      }
    });
  }

  // ====================================================================
  // MÉTODO: Filtrar tanques por nación
  // ====================================================================
  filtrarPorNacion(): void {
    if (this.filtroNacion === '') {
      // Si no hay filtro, mostrar todos
      this.tanquesFiltrados = this.tanques;
    } else {
      // Filtrar los tanques por la nación seleccionada
      this.tanquesFiltrados = this.tanques.filter(
        tanque => tanque.nacion === this.filtroNacion
      );
    }
    
    // Aplicar también el filtro de búsqueda si existe
    this.aplicarFiltroBusqueda();
  }

  // ====================================================================
  // MÉTODO: Buscar tanques por nombre
  // ====================================================================
  aplicarFiltroBusqueda(): void {
    if (this.filtroBusqueda === '') {
      return;
    }
    
    // Convertir a minúsculas para búsqueda case-insensitive
    const busqueda = this.filtroBusqueda.toLowerCase();
    
    this.tanquesFiltrados = this.tanquesFiltrados.filter(tanque =>
      tanque.nombre.toLowerCase().includes(busqueda)
    );
  }

  // ====================================================================
  // MÉTODO: Limpiar filtros
  // ====================================================================
  limpiarFiltros(): void {
    this.filtroNacion = '';
    this.filtroBusqueda = '';
    this.tanquesFiltrados = this.tanques;
  }

  // ====================================================================
  // MÉTODO: Seleccionar un tanque para ver detalles
  // ====================================================================
  seleccionarTanque(tanque: Tanque): void {
    this.tanqueSeleccionado = tanque;
  }

  // ====================================================================
  // MÉTODO: Cerrar detalles del tanque
  // ====================================================================
  cerrarDetalles(): void {
    this.tanqueSeleccionado = null;
  }

  // ====================================================================
  // MÉTODO: Eliminar un tanque
  // ====================================================================
  eliminarTanque(id: string): void {
    // EXPLICACIÓN: Pedimos confirmación antes de eliminar
    if (!confirm('¿Estás seguro de que quieres eliminar este tanque?')) {
      return;
    }
    
    this.tanksService.eliminarTanque(id).subscribe({
      next: (response) => {
        console.log('Tanque eliminado:', response);
        
        // Recargar la lista de tanques
        this.cargarTanques();
        
        // Cerrar detalles si estaba abierto
        if (this.tanqueSeleccionado && this.tanqueSeleccionado._id === id) {
          this.cerrarDetalles();
        }
      },
      error: (err) => {
        console.error('Error al eliminar tanque:', err);
        alert('Error al eliminar el tanque');
      }
    });
  }

  // ====================================================================
  // MÉTODO: Obtener color según la nación (para el UI)
  // ====================================================================
  obtenerColorNacion(nacion: string): string {
    // EXPLICACIÓN: Devuelve una clase CSS según la nación
    const colores: { [key: string]: string } = {
      'Great Britain': 'bg-red-500',
      'Germany': 'bg-gray-700',
      'USSR': 'bg-red-700',
      'USA': 'bg-blue-600',
      'Japan': 'bg-red-600',
      'France': 'bg-blue-500',
      'Italy': 'bg-green-600',
    };
    
    return colores[nacion] || 'bg-gray-500';
  }

  // ====================================================================
  // MÉTODO: Obtener armas del setup (para el modal de detalles)
  // ====================================================================
  obtenerArmasSetup(setup: { [key: string]: any }): any[] {
    // EXPLICACIÓN: Convierte el objeto de armas en un array
    // para poder iterarlo en el HTML con *ngFor
    
    return Object.keys(setup).map(nombreArma => ({
      nombre: nombreArma,
      municiones: setup[nombreArma].municiones
    }));
  }
}
