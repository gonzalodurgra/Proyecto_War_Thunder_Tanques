import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TanksService, Tanque, CombateIAResponse, IAModelo } from '../../services/tanks';
import { Router } from '@angular/router';

@Component({
  selector: 'app-combat-ia',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './combat-ia.html',
  styleUrls: ['./combat-ia.css']
})
export class CombatIAComponent implements OnInit {
  tanques: Tanque[] = [];
  vehiculo1: Tanque | null = null;
  vehiculo2: Tanque | null = null;
  situacion: string = 'Encuentro frontal en campo abierto a 500 metros.';

  cargando: boolean = false;
  resultado: CombateIAResponse | null = null;
  error: string = '';

  // Modelos disponibles
  modelos: IAModelo[] = [];
  modeloSeleccionado: string = 'gemini-3.1-flash-lite-preview';

  filtro1: string = '';
  filtro2: string = '';
  mostrarLista1: boolean = false;
  mostrarLista2: boolean = false;

  modoOscuro: boolean = false;

  constructor(private tanksService: TanksService, private router: Router) { }

  ngOnInit(): void {
    this.cargarPreferenciaTema();
    this.cargarTanques();
    this.cargarModelos();
  }

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

  get tanquesFiltrados1() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtro1.toLowerCase())
    ).slice(0, 70);
  }

  get tanquesFiltrados2() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtro2.toLowerCase())
    ).slice(0, 70);
  }

  seleccionarVehiculo1(tanque: Tanque): void {
    this.vehiculo1 = tanque;
    this.filtro1 = tanque.nombre;
    this.mostrarLista1 = false;
  }

  seleccionarVehiculo2(tanque: Tanque): void {
    this.vehiculo2 = tanque;
    this.filtro2 = tanque.nombre;
    this.mostrarLista2 = false;
  }

  get descripcionModeloSeleccionado(): string {
    const modelo = this.modelos.find(m => m.id === this.modeloSeleccionado);
    return modelo ? modelo.descripcion : '';
  }

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

  regresar(): void {
    this.router.navigate(['/tanques']);
  }

  /**
   * Carga la preferencia de tema guardada en localStorage
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
   * Alterna entre modo claro y oscuro
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
   * Aplica el modo oscuro al documento
   */
  aplicarModoOscuro(): void {
    document.body.classList.add('dark-mode');
  }

  /**
   * Aplica el modo claro al documento
   */
  aplicarModoClaro(): void {
    document.body.classList.remove('dark-mode');
  }
}
