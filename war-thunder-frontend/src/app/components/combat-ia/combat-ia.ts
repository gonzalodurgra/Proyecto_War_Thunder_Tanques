import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TanksService, Tanque, CombateIAResponse, IAModelo } from '../../services/tanks';
import { Router } from '@angular/router';

/**
 * COMPONENTE DE COMBATE 1 VS 1 CON IA (DUELOS TÁCTICOS)
 * =======================================================
 * Este componente permite al usuario:
 * 1. Seleccionar dos tanques para enfrentarse cara a cara.
 * 2. Elegir dinámicamente el modelo de IA (Google Gemini) para el informe táctico.
 * 3. Describir la situación táctica (distancia, terreno, ángulos de tiro).
 * 4. Invocar el motor híbrido (Monte Carlo + PyTorch/ONNX + Gemini) y visualizar
 *    probabilidades de victoria, municiones óptimas y desglose balístico.
 */
@Component({
  selector: 'app-combat-ia',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './combat-ia.html',
  styleUrls: ['./combat-ia.css']
})
export class CombatIAComponent implements OnInit {
  // ====================================================================
  // ESTADO Y PROPIEDADES DEL COMPONENTE
  // ====================================================================
  tanques: Tanque[] = [];
  vehiculo1: Tanque | null = null;
  vehiculo2: Tanque | null = null;
  situacion: string = 'Encuentro frontal en campo abierto a 500 metros.';

  // Estados de interfaz y feedback
  cargando: boolean = false;
  resultado: CombateIAResponse | null = null;
  error: string = '';

  // Modelos de lenguaje disponibles obtenidos dinámicamente desde el backend
  modelos: IAModelo[] = [];
  modeloSeleccionado: string = 'gemini-3.1-flash-lite';

  // Filtros de búsqueda para autocompletado en selectores de vehículos
  filtro1: string = '';
  filtro2: string = '';
  mostrarLista1: boolean = false;
  mostrarLista2: boolean = false;

  // Estado del tema visual
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
   * Carga la lista de modelos de Gemini disponibles en la API Key configurada.
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
   * Carga el catálogo completo de tanques para permitir la selección de combatientes.
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
  // FILTRADO Y SELECCIÓN DE VEHÍCULOS
  // ====================================================================

  /**
   * Filtra los primeros 70 tanques que coinciden con el texto de búsqueda para el vehículo 1.
   */
  get tanquesFiltrados1() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtro1.toLowerCase())
    ).slice(0, 70);
  }

  /**
   * Filtra los primeros 70 tanques que coinciden con el texto de búsqueda para el vehículo 2.
   */
  get tanquesFiltrados2() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtro2.toLowerCase())
    ).slice(0, 70);
  }

  /**
   * Asigna el primer combatiente y oculta el desplegable.
   */
  seleccionarVehiculo1(tanque: Tanque): void {
    this.vehiculo1 = tanque;
    this.filtro1 = tanque.nombre;
    this.mostrarLista1 = false;
  }

  /**
   * Asigna el segundo combatiente y oculta el desplegable.
   */
  seleccionarVehiculo2(tanque: Tanque): void {
    this.vehiculo2 = tanque;
    this.filtro2 = tanque.nombre;
    this.mostrarLista2 = false;
  }

  /**
   * Obtiene la descripción explicativa del modelo de IA actualmente seleccionado.
   */
  get descripcionModeloSeleccionado(): string {
    const modelo = this.modelos.find(m => m.id === this.modeloSeleccionado);
    return modelo ? modelo.descripcion : '';
  }

  // ====================================================================
  // EJECUCIÓN DE LA SIMULACIÓN
  // ====================================================================

  /**
   * Valida los datos y envía la petición de simulación 1v1 al backend.
   */
  simular(): void {
    if (!this.vehiculo1 || !this.vehiculo2 || !this.situacion) {
      this.error = 'Por favor, selecciona ambos vehículos y describe la situación.';
      return;
    }

    this.cargando = true;
    this.resultado = null;
    this.error = '';

    const request = {
      vehiculo1_id: this.vehiculo1._id!,
      vehiculo2_id: this.vehiculo2._id!,
      situacion: this.situacion,
      modelo: this.modeloSeleccionado
    };

    this.tanksService.simularCombateIA(request).subscribe({
      next: (res) => {
        this.resultado = res;
        this.cargando = false;
      },
      error: (err) => {
        this.error = 'Error al simular el combate. Si el error persiste, por favor, inténtalo más tarde o cambia el modelo de IA.';
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

