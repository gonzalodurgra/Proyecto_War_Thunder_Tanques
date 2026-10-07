import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TanksService, Tanque, SimulacionEquiposIAResponse, SimulacionEquiposIARequest, IAModelo } from '../../services/tanks';
import { Router } from '@angular/router';

/**
 * COMPONENTE DE COMBATE POR EQUIPOS CON IA (BATALLAS DE ESCUADRONES)
 * ====================================================================
 * Este componente permite al usuario:
 * 1. Armar dos alineaciones tácticas completas (hasta 16 vehículos aliados vs 16 enemigos).
 * 2. Seleccionar cuál de los vehículos aliados es tripulado por el propio jugador.
 * 3. Configurar el escenario de batalla y elegir el modelo LLM (Gemini).
 * 4. Simular la batalla global con Monte Carlo + Red Neuronal y obtener un desglose
 *    estratégico: probabilidad de victoria, blancos prioritarios, tanques a evitar
 *    y sinergias con compañeros de escuadrón.
 */
@Component({
  selector: 'app-combat-equipos-ia',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './combat-equipos-ia.html',
  styleUrls: ['./combat-equipos-ia.css']
})
export class CombatEquiposIAComponent implements OnInit {
  // ====================================================================
  // ESTADO Y PROPIEDADES DEL COMPONENTE
  // ====================================================================
  tanques: Tanque[] = [];

  // Alineaciones de escuadrón
  equipoAliado: Tanque[] = [];
  equipoEnemigo: Tanque[] = [];
  tanqueUsuarioIndex: number | null = null; // Índice del tanque del jugador en equipoAliado

  situacion: string = 'Encuentro de escuadrones en terreno semiurbano a 800 metros con cobertura de colinas.';

  // Estados de carga y respuesta
  cargando: boolean = false;
  resultado: SimulacionEquiposIAResponse | null = null;
  error: string = '';

  // Filtros de búsqueda para selectores de aliados y enemigos
  filtroAliado: string = '';
  filtroEnemigo: string = '';
  mostrarListaAliado: boolean = false;
  mostrarListaEnemigo: boolean = false;

  // Modelos de IA disponibles
  modelos: IAModelo[] = [];
  modeloSeleccionado: string = 'gemini-3.1-flash-lite';

  // Tema visual
  modoOscuro: boolean = false;

  constructor(private tanksService: TanksService, private router: Router) { }

  // ====================================================================
  // CICLO DE VIDA (INICIALIZACIÓN)
  // ====================================================================
  ngOnInit(): void {
    this.cargarPreferenciaTema();
    this.cargarTanques();
    this.cargarModelos();
  }

  /**
   * Carga los modelos de Gemini disponibles desde el backend.
   */
  cargarModelos(): void {
    this.tanksService.obtenerModelosIA().subscribe({
      next: (modelos) => {
        this.modelos = modelos;
        if (modelos.length > 0 && !modelos.find(m => m.id === this.modeloSeleccionado)) {
          this.modeloSeleccionado = modelos[0].id;
        }
      },
      error: (err) => console.error('Error al cargar modelos:', err)
    });
  }

  /**
   * Carga la base de datos de tanques para poblar los selectores de búsqueda.
   */
  cargarTanques(): void {
    this.tanksService.obtenerTodosLosTanques().subscribe({
      next: (tanques) => {
        this.tanques = tanques;
      },
      error: (err) => {
        this.error = 'No se pudieron cargar los vehículos.';
        console.error(err);
      }
    });
  }

  // ====================================================================
  // FILTRADO Y BÚSQUEDA DE VEHÍCULOS
  // ====================================================================

  /**
   * Filtra los tanques para sugerencias del equipo aliado (máximo 15 resultados).
   */
  get tanquesFiltradosAliado() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtroAliado.toLowerCase())
    ).slice(0, 15);
  }

  /**
   * Filtra los tanques para sugerencias del equipo enemigo (máximo 15 resultados).
   */
  get tanquesFiltradosEnemigo() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtroEnemigo.toLowerCase())
    ).slice(0, 15);
  }

  // ====================================================================
  // GESTIÓN DE ALINEACIONES Y ESCUADRONES
  // ====================================================================

  /**
   * Añade un tanque al equipo aliado (límite máximo de 16 tanques).
   * Si es el primer tanque aliado, se asigna como el vehículo del usuario por defecto.
   */
  agregarAliado(tanque: Tanque): void {
    if (this.equipoAliado.length >= 16) {
      this.error = 'El equipo aliado no puede superar los 16 tanques.';
      return;
    }
    // Clonar para evitar mutación de referencias
    this.equipoAliado.push({ ...tanque });
    this.filtroAliado = '';
    this.mostrarListaAliado = false;
    this.error = '';

    // Si es el primer tanque, ponemos su índice (0) como el del usuario por defecto
    if (this.tanqueUsuarioIndex === null || this.tanqueUsuarioIndex === -1) {
      this.tanqueUsuarioIndex = 0;
    }
  }

  /**
   * Añade un tanque al equipo enemigo (límite máximo de 16 tanques).
   */
  agregarEnemigo(tanque: Tanque): void {
    if (this.equipoEnemigo.length >= 16) {
      this.error = 'El equipo enemigo no puede superar los 16 tanques.';
      return;
    }
    this.equipoEnemigo.push({ ...tanque });
    this.filtroEnemigo = '';
    this.mostrarListaEnemigo = false;
    this.error = '';
  }

  /**
   * Elimina un tanque del equipo aliado y reajusta el índice del tanque del usuario.
   */
  quitarAliado(index: number): void {
    this.equipoAliado.splice(index, 1);

    // Ajustar el índice del tanque de usuario
    if (this.tanqueUsuarioIndex === index) {
      this.tanqueUsuarioIndex = this.equipoAliado.length > 0 ? 0 : null;
    } else if (this.tanqueUsuarioIndex !== null && this.tanqueUsuarioIndex > index) {
      this.tanqueUsuarioIndex--;
    }
  }

  /**
   * Elimina un tanque del equipo enemigo.
   */
  quitarEnemigo(index: number): void {
    this.equipoEnemigo.splice(index, 1);
  }

  /**
   * Marca el tanque aliado en la posición indicada como el vehículo del jugador.
   */
  seleccionarComoUsuario(index: number): void {
    this.tanqueUsuarioIndex = index;
  }

  /**
   * Retorna el objeto Tanque correspondiente al vehículo del usuario.
   */
  get tanqueUsuario(): Tanque | null {
    if (this.tanqueUsuarioIndex !== null && this.tanqueUsuarioIndex >= 0 && this.tanqueUsuarioIndex < this.equipoAliado.length) {
      return this.equipoAliado[this.tanqueUsuarioIndex];
    }
    return null;
  }

  /**
   * Retorna la descripción del modelo de Gemini seleccionado.
   */
  get descripcionModeloSeleccionado(): string {
    const modelo = this.modelos.find(m => m.id === this.modeloSeleccionado);
    return modelo ? modelo.descripcion : '';
  }

  // ====================================================================
  // EJECUCIÓN DE LA SIMULACIÓN DE EQUIPOS
  // ====================================================================

  /**
   * Valida la composición de escuadrones y solicita la simulación por equipos al backend.
   */
  simular(): void {
    if (this.equipoAliado.length === 0 || this.equipoEnemigo.length === 0) {
      this.error = 'Ambos equipos deben tener al menos 1 vehículo.';
      return;
    }
    if (this.tanqueUsuarioIndex === null || this.tanqueUsuarioIndex === -1) {
      this.error = 'Debes elegir cuál de los tanques aliados manejas.';
      return;
    }
    if (!this.situacion.trim()) {
      this.error = 'Describe la situación táctica de combate.';
      return;
    }

    this.cargando = true;
    this.resultado = null;
    this.error = '';

    const request: SimulacionEquiposIARequest = {
      equipo_aliado: this.equipoAliado,
      equipo_enemigo: this.equipoEnemigo,
      tanque_usuario_index: this.tanqueUsuarioIndex,
      situacion: this.situacion,
      modelo: this.modeloSeleccionado
    };

    this.tanksService.simularCombateEquiposIA(request).subscribe({
      next: (res) => {
        this.resultado = res;
        this.cargando = false;
      },
      error: (err) => {
        this.error = 'Error al simular la batalla de equipos. Por favor, inténtalo de nuevo.';
        this.cargando = false;
        console.error(err);
      }
    });
  }

  /**
   * Navega de vuelta a la lista principal de tanques.
   */
  regresar(): void {
    this.router.navigate(['/tanques']);
  }

  // ====================================================================
  // GESTIÓN DE TEMA (CLARO / OSCURO)
  // ====================================================================

  /**
   * Carga la preferencia de tema guardada en localStorage.
   */
  cargarPreferenciaTema(): void {
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
   * Alterna entre modo claro y oscuro y persiste la elección.
   */
  toggleModoOscuro(): void {
    this.modoOscuro = !this.modoOscuro;
    if (this.modoOscuro) {
      this.aplicarModoOscuro();
      localStorage.setItem('tema', 'oscuro');
    } else {
      this.aplicarModoClaro();
      localStorage.setItem('tema', 'claro');
    }
  }

  /**
   * Aplica la clase CSS de modo oscuro en el elemento raíz body.
   */
  aplicarModoOscuro(): void {
    document.body.classList.add('dark-mode');
  }

  /**
   * Elimina la clase CSS de modo oscuro del body.
   */
  aplicarModoClaro(): void {
    document.body.classList.remove('dark-mode');
  }
}

