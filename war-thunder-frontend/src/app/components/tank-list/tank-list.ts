import { Component, OnInit } from '@angular/core';
import { TanksService, Tanque } from '../../services/tanks';
import { AuthService } from '../../services/auth';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TanksStatsService, EstadisticasPorRating } from '../../services/tanks-stats.service.ts';

// ====================================================================
// Configuración del componente
// ====================================================================
@Component({
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

  // ⭐ NUEVO: Paginación
  tanquesPaginados: Tanque[] = [];
  paginaActual: number = 1;
  tanquesPorPagina: number = 24;
  totalPaginas: number = 0;
  paginasVisibles: number[] = [];
  
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

  // ⭐ NUEVO: Para usar Object.keys en el template
  Object = Object;

  //Comprueba si está autenticado
  isAuthenticated: boolean = localStorage.getItem("username") !== null;
  mostrarMenuUsuario: boolean = false;

  currentUsername: string | null = localStorage.getItem("username");

  isAdmin: boolean = localStorage.getItem("esAdmin") == "s";

  estadisticasPorRatingArcade: EstadisticasPorRating[] = [];
  estadisticasPorRatingRealista: EstadisticasPorRating[] = []
  coloresTanque: { [key: string]: string } = {};
  mostrarEstadisticasAvanzadas: boolean = false;
  // ====================================================================
  // PASO 2: Inyectar el servicio en el constructor
  // ====================================================================
  constructor(private tanksService: TanksService, private authService: AuthService, private statsService: TanksStatsService, private router: Router) {
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
        // NUEVO: Calcular estadísticas globales
        console.log('📊 Calculando estadísticas globales...');
        this.statsService.calcularRangosGlobales(this.tanques);

        // NUEVO: Calcular estadísticas por rating
        console.log('📊 Calculando estadísticas por rating...');
        this.estadisticasPorRatingArcade = this.statsService.calcularRangosPorRating(this.tanques, "rating_arcade");
        console.log('📊 Ratings procesados:', this.estadisticasPorRatingArcade.length);
        this.estadisticasPorRatingRealista = this.statsService.calcularRangosPorRating(this.tanques, "rating_realista");
        console.log('📊 Ratings procesados:', this.estadisticasPorRatingRealista.length);
        this.paginaActual = 1;
        this.calcularPaginacion();
        this.actualizarTanquesPaginados();
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

    // ⭐ NUEVO: Resetear a página 1 al filtrar
    this.paginaActual = 1;
    this.calcularPaginacion();
    this.actualizarTanquesPaginados();
  }

  // ====================================================================
  // MÉTODO: Buscar tanques por nombre
  // ====================================================================
  aplicarFiltroBusqueda(): void {
    if (this.filtroBusqueda.trim() === '') {
      if (this.filtroNacion === '') {
        this.tanquesFiltrados = [...this.tanques];
      } else {
        this.tanquesFiltrados = this.tanques.filter(
          tanque => tanque.nacion === this.filtroNacion
        );
      }
    } else {
      const busqueda = this.filtroBusqueda.toLowerCase();
      let tanquesBase = this.filtroNacion === '' 
        ? this.tanques 
        : this.tanques.filter(t => t.nacion === this.filtroNacion);
      
      this.tanquesFiltrados = tanquesBase.filter(tanque =>
        tanque.nombre.toLowerCase().includes(busqueda) ||
        tanque.rol.toLowerCase().includes(busqueda)
      );
    }
    
    // ⭐ NUEVO: Resetear a página 1 al buscar
    this.paginaActual = 1;
    this.calcularPaginacion();
    this.actualizarTanquesPaginados();
  }

  // ====================================================================
  // MÉTODO: Limpiar filtros
  // ====================================================================
  limpiarFiltros(): void {
    this.filtroNacion = '';
    this.filtroBusqueda = '';
    this.tanquesFiltrados = this.tanques;

    // ⭐ NUEVO: Resetear paginación
    this.paginaActual = 1;
    this.calcularPaginacion();
    this.actualizarTanquesPaginados();
  }

  // ====================================================================
  // ⭐ NUEVOS MÉTODOS DE PAGINACIÓN
  // ====================================================================

  /**
   * Calcula el número total de páginas
   */
  calcularPaginacion(): void {
    this.totalPaginas = Math.ceil(this.tanquesFiltrados.length / this.tanquesPorPagina);
    this.calcularPaginasVisibles();
  }

  /**
   * Actualiza el array de tanques a mostrar en la página actual
   */
  actualizarTanquesPaginados(): void {
    const inicio = (this.paginaActual - 1) * this.tanquesPorPagina;
    const fin = inicio + this.tanquesPorPagina;
    this.tanquesPaginados = this.tanquesFiltrados.slice(inicio, fin);
    
    // Scroll al inicio de la lista
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /**
   * Calcula qué números de página mostrar (max 5)
   */
  calcularPaginasVisibles(): void {
    const maxPaginasVisibles = 5;
    this.paginasVisibles = [];
    
    if (this.totalPaginas <= maxPaginasVisibles) {
      // Mostrar todas las páginas
      for (let i = 1; i <= this.totalPaginas; i++) {
        this.paginasVisibles.push(i);
      }
    } else {
      // Mostrar páginas alrededor de la actual
      let inicio = Math.max(1, this.paginaActual - 2);
      let fin = Math.min(this.totalPaginas, inicio + maxPaginasVisibles - 1);
      
      // Ajustar si estamos cerca del final
      if (fin - inicio < maxPaginasVisibles - 1) {
        inicio = Math.max(1, fin - maxPaginasVisibles + 1);
      }
      
      for (let i = inicio; i <= fin; i++) {
        this.paginasVisibles.push(i);
      }
    }
  }

  /**
   * Cambia a una página específica
   */
  irAPagina(pagina: number): void {
    if (pagina < 1 || pagina > this.totalPaginas) {
      return;
    }
    
    this.paginaActual = pagina;
    this.calcularPaginasVisibles();
    this.actualizarTanquesPaginados();
  }

  /**
   * Página anterior
   */
  paginaAnterior(): void {
    if (this.paginaActual > 1) {
      this.irAPagina(this.paginaActual - 1);
    }
  }

  /**
   * Página siguiente
   */
  paginaSiguiente(): void {
    if (this.paginaActual < this.totalPaginas) {
      this.irAPagina(this.paginaActual + 1);
    }
  }

  /**
   * Primera página
   */
  primeraPagina(): void {
    this.irAPagina(1);
  }

  /**
   * Última página
   */
  ultimaPagina(): void {
    this.irAPagina(this.totalPaginas);
  }

  /**
   * Obtiene el rango de tanques mostrados
   */
  getRangoTanques(): string {
    if (this.tanquesFiltrados.length === 0) {
      return '0 tanques';
    }
    
    const inicio = (this.paginaActual - 1) * this.tanquesPorPagina + 1;
    const fin = Math.min(this.paginaActual * this.tanquesPorPagina, this.tanquesFiltrados.length);
    
    return `${inicio}-${fin} de ${this.tanquesFiltrados.length} tanques`;
  }

  // ====================================================================
  // MÉTODO: Seleccionar un tanque para ver detalles
  // ====================================================================
  seleccionarTanque(tanque: Tanque): void {
    this.tanqueSeleccionado = tanque;
    // Calcular colores para este tanque usando su rating específico
    this.coloresTanque = this.statsService.obtenerColoresTanque(tanque, true);
    
    console.log('🎨 Colores calculados para:', tanque.nombre);
    console.log('Rating:', tanque.rating_arcade);
    console.log('Colores:', this.coloresTanque);
  }

  // ====================================================================
  // MÉTODO: Cerrar detalles del tanque
  // ====================================================================
  cerrarDetalles(): void {
    this.tanqueSeleccionado = null;
  }

  // ====================================================================
  // MÉTODO: Eliminar un tanque - REQUIERE AUTENTICACIÓN
  // ====================================================================
  eliminarTanque(id: string): void {
    // Verificar autenticación
    if (!this.isAuthenticated) {
      alert('Debes iniciar sesión para eliminar tanques');
      return;
    }
    
    if (!confirm('¿Estás seguro de que quieres eliminar este tanque?')) {
      return;
    }
    
    this.tanksService.eliminarTanque(id).subscribe({
      next: (response) => {
        console.log('Tanque eliminado:', response);
        this.cargarTanques();
        
        if (this.tanqueSeleccionado && this.tanqueSeleccionado._id === id) {
          this.cerrarDetalles();
        }
      },
      error: (err) => {
        console.error('Error al eliminar tanque:', err);
        
        if (err.status === 401) {
          alert('Tu sesión ha expirado. Por favor inicia sesión nuevamente.');
          this.logout();
        } else {
          alert('Error al eliminar el tanque');
        }
      }
    });
  }

  // ====================================================================
  // MÉTODO NUEVO: Logout
  // ====================================================================
  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  // ====================================================================
  // MÉTODO NUEVO: Toggle menú de usuario
  // ====================================================================
  toggleMenuUsuario(): void {
    this.mostrarMenuUsuario = !this.mostrarMenuUsuario;
  }

  // ====================================================================
  // MÉTODO NUEVO: Ir a login
  // ====================================================================
  irALogin(): void {
    this.router.navigate(['/login']);
  }

  // ====================================================================
  // MÉTODO NUEVO: Editar tanque
  // ====================================================================
  editarTanque(tanque: Tanque): void {
    if (!this.isAuthenticated) {
      alert('Debes iniciar sesión para editar tanques');
      return;
    }
    
    // Navegar a la ruta de edición con el ID del tanque
    this.router.navigate(['/tanques/editar', tanque._id]);
  }

  // ====================================================================
  // MÉTODO NUEVO: Crear nuevo tanque
  // ====================================================================
  crearNuevoTanque(): void {
    if (!this.isAuthenticated) {
      alert('Debes iniciar sesión para crear tanques');
      return;
    }
    
    // Navegar a la ruta de creación
    this.router.navigate(['/tanques/nuevo']);
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

  irAPanelAdmin(): void{
    this.router.navigate(["/admin"])
  }

  // ====================================================================
  // NUEVO MÉTODO: Obtener color de una estadística específica
  // ====================================================================
  obtenerColorEstadistica(
    tanque: Tanque, 
    nombreEstadistica: string,
    valor: number,
    invertir: boolean = false
  ): string {
    return this.statsService.obtenerColor(
      nombreEstadistica as any,
      valor,
      tanque.rating_arcade,
      invertir
    );
  }

  // ====================================================================
  // NUEVO MÉTODO: Obtener percentil de una estadística
  // ====================================================================
  obtenerPercentil(
    tanque: Tanque,
    nombreEstadistica: string,
    valor: number
  ): number {
    return this.statsService.obtenerPercentil(
      nombreEstadistica as any,
      valor,
      tanque.rating_arcade
    );
  }

  // ====================================================================
  // NUEVO MÉTODO: Obtener color de penetración
  // ====================================================================
  obtenerColorPenetracion(penetracionMm: number): string {
    return this.statsService.obtenerColorPenetracion(penetracionMm, this.tanques);
  }

  // ====================================================================
  // NUEVO MÉTODO: Formatear percentil para mostrar
  // ====================================================================
  formatearPercentil(percentil: number): string {
    if (percentil >= 90) return 'Top 10%';
    if (percentil >= 80) return 'Top 20%';
    if (percentil >= 70) return 'Top 30%';
    if (percentil >= 60) return 'Sobre promedio';
    if (percentil >= 40) return 'Promedio';
    if (percentil >= 30) return 'Bajo promedio';
    return 'Bottom 30%';
  }

  // ====================================================================
  // NUEVO MÉTODO: Toggle para mostrar/ocultar estadísticas avanzadas
  // ====================================================================
  toggleEstadisticasAvanzadas(): void {
    this.mostrarEstadisticasAvanzadas = !this.mostrarEstadisticasAvanzadas;
  }
}