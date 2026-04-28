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

  estadisticasPorRating: EstadisticasPorRating[] = [];
  coloresTanque: { [key: string]: string } = {};
  mostrarEstadisticasAvanzadas: boolean = false;

  // ====================================================================
  // Variables para modo de juego
  // ====================================================================
  modoActual: string = 'rating_arcade'; // Por defecto Arcade

  modoOscuro: boolean = false

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
    this.cargarPreferenciaTema();
    this.cargarTanques();
    this.cargarNaciones();
    if(!this.authService.isLoggedIn()){
      this.authService.logout()
    }
  }


  // ====================================================================
  // MÉTODO: Cargar todos los tanques
  // ====================================================================
  cargarTanques(): void {
    this.cargando = true;
    this.error = '';

    this.tanksService.obtenerTodosLosTanques().subscribe({
      next: (tanques) => {
        console.log('✅ Tanques cargados:', tanques.length);
        this.tanques = tanques;
        this.tanquesFiltrados = tanques;

        // NUEVO: Calcular estadísticas globales
        console.log('📊 Calculando estadísticas globales...');
        this.statsService.calcularRangosGlobales(tanques);

        // NUEVO: Calcular estadísticas por rating
        console.log('📊 Calculando estadísticas por rating...');
        this.estadisticasPorRating = this.statsService.calcularRangosPorRating(tanques, this.modoActual);
        console.log('📊 Ratings procesados:', this.estadisticasPorRating.length);

        // NUEVO: Calcular rangos de penetración por rating
        console.log('🎯 Calculando penetraciones por rating...');
        this.statsService.calcularRangosPenetracionPorRating(tanques, this.modoActual);

        // Cargar naciones únicas
        this.cargarNaciones();
        
        // Actualizar paginación
        this.calcularPaginacion();
        this.actualizarTanquesPaginados();
        
        this.cargando = false;
      },
      error: (error) => {
        console.error('❌ Error al cargar tanques:', error);
        this.error = 'Error al cargar los tanques. Por favor, intenta de nuevo.';
        this.cargando = false;
      }
    });
  }

  // ====================================================================
  // NUEVO MÉTODO: Cambiar modo de juego
  // ====================================================================
  cambiarModo(modo: string): void {
    this.modoActual = modo;
    console.log(`🎮 Cambiando a modo: ${modo}`);
    
    // Recalcular estadísticas con el nuevo modo
    this.estadisticasPorRating = this.statsService.calcularRangosPorRating(this.tanques, modo);
    this.statsService.calcularRangosPenetracionPorRating(this.tanques, modo);
    
    // Si hay un tanque seleccionado, recalcular sus colores
    if (this.tanqueSeleccionado) {
      this.seleccionarTanque(this.tanqueSeleccionado);
    }
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
    console.log('Rating Arcade:', tanque.rating_arcade);
    console.log('Rating Realista:', tanque.rating_realista);
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
  // MÉTODO NUEVO: Ir al simulador de IA
  // ====================================================================
  irASimuladorIA(): void {
    this.router.navigate(['/combate-ia']);
  }

  // ====================================================================
  // MÉTODO: Obtener color según la nación (para el UI)
  // ====================================================================
  obtenerColorNacion(nacion: string): string {
    // EXPLICACIÓN: Devuelve una clase CSS según la nación
    const colores: { [key: string]: string } = {
      'Gran Bretaña': 'bg-red-500',
      'Alemania': 'bg-gray-700',
      'URSS': 'bg-red-700',
      'Estados Unidos': 'bg-blue-600',
      'Japón': 'bg-red-600',
      'Francia': 'bg-blue-500',
      'Italia': 'bg-green-600',
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
    if (!this.tanqueSeleccionado) {
      return this.statsService.obtenerColorPenetracion(penetracionMm, this.tanques);
    }
    
    // Usar el rating del tanque seleccionado según el modo actual
    const rating = this.modoActual === 'rating_arcade' 
      ? this.tanqueSeleccionado.rating_arcade 
      : this.tanqueSeleccionado.rating_realista;
    
    return this.statsService.obtenerColorPenetracion(penetracionMm, this.tanques, rating);
  }

  // ====================================================================
  // NUEVO MÉTODO: Formatear percentil para mostrar
  // ====================================================================
  obtenerPercentilPenetracion(penetracionMm: number): number {
    if (!this.tanqueSeleccionado) return 50;
    
    const rating = this.modoActual === 'rating_arcade'
      ? this.tanqueSeleccionado.rating_arcade
      : this.tanqueSeleccionado.rating_realista;
    
    return this.statsService.obtenerPercentilPenetracion(penetracionMm, rating);
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
  obtenerColorPorPercentil(percentil: number): string {
    if (percentil <= 10) return '#ef4444';
    if (percentil <= 20) return '#f87171';
    if (percentil <= 30) return '#fb923c';
    if (percentil <= 40) return '#fbbf24';
    if (percentil <= 50) return '#facc15';
    if (percentil <= 60) return '#a3e635';
    if (percentil <= 70) return '#84cc16';
    if (percentil <= 80) return '#4ade80';
    if (percentil <= 90) return '#22c55e';
    return '#16a34a';
  }
  obtenerColorPorPercentilInvertido(percentil: number): string {
    return this.obtenerColorPorPercentil(100 - percentil);
  }

  /**
   * Carga la preferencia de tema guardada en localStorage
   */
  cargarPreferenciaTema(): void {
    // EXPLICACIÓN: localStorage permite guardar datos en el navegador
    // que persisten incluso después de cerrar la página
    
    const temaGuardado = localStorage.getItem('tema');
    
    if (temaGuardado === 'oscuro') {
      this.modoOscuro = true;
      this.aplicarModoOscuro();
    } else {
      this.modoOscuro = false;
      this.aplicarModoClaro();
    }
  }

  /**
   * Alterna entre modo claro y oscuro
   */
  toggleModoOscuro(): void {
    // EXPLICACIÓN: Este método se ejecuta cuando el usuario hace clic
    // en el botón de modo oscuro
    
    this.modoOscuro = !this.modoOscuro;
    
    if (this.modoOscuro) {
      this.aplicarModoOscuro();
      // Guardar preferencia
      localStorage.setItem('tema', 'oscuro');
    } else {
      this.aplicarModoClaro();
      // Guardar preferencia
      localStorage.setItem('tema', 'claro');
    }
  }

  /**
   * Aplica el modo oscuro al documento
   */
  aplicarModoOscuro(): void {
    // EXPLICACIÓN: Agregamos la clase 'dark-mode' al body
    // Esto activa las variables CSS del tema oscuro
    
    document.body.classList.add('dark-mode');
  }

  /**
   * Aplica el modo claro al documento
   */
  aplicarModoClaro(): void {
    // EXPLICACIÓN: Removemos la clase 'dark-mode' del body
    // Esto vuelve a las variables CSS del tema claro
    
    document.body.classList.remove('dark-mode');
  }

  // ====================================================================
  // PASO 4: OPCIONAL - Limpiar al destruir el componente
  // ====================================================================
  
  ngOnDestroy(): void {
    // EXPLICACIÓN: Este método se ejecuta cuando el componente se destruye
    // Es una buena práctica limpiar las modificaciones al DOM
    
    // Si quieres mantener el tema en otras páginas, comenta esta línea:
    // document.body.classList.remove('dark-mode');
  }
}