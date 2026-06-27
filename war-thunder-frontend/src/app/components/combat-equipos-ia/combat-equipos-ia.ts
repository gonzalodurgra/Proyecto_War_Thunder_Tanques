import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TanksService, Tanque, SimulacionEquiposIAResponse, IAModelo } from '../../services/tanks';
import { Router } from '@angular/router';

@Component({
  selector: 'app-combat-equipos-ia',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './combat-equipos-ia.html',
  styleUrls: ['./combat-equipos-ia.css']
})
export class CombatEquiposIAComponent implements OnInit {
  tanques: Tanque[] = [];

  // Equipos
  equipoAliado: Tanque[] = [];
  equipoEnemigo: Tanque[] = [];
  tanqueUsuario: Tanque | null = null;

  situacion: string = 'Encuentro de escuadrones en terreno semiurbano a 800 metros con cobertura de colinas.';

  cargando: boolean = false;
  resultado: SimulacionEquiposIAResponse | null = null;
  error: string = '';

  // Buscadores
  filtroAliado: string = '';
  filtroEnemigo: string = '';
  mostrarListaAliado: boolean = false;
  mostrarListaEnemigo: boolean = false;

  // Modelos de IA
  modelos: IAModelo[] = [];
  modeloSeleccionado: string = 'gemini-3.1-flash-lite';

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

  get tanquesFiltradosAliado() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtroAliado.toLowerCase()) &&
      !this.equipoAliado.some(aliado => aliado._id === t._id)
    ).slice(0, 15);
  }

  get tanquesFiltradosEnemigo() {
    return this.tanques.filter(t =>
      t.nombre.toLowerCase().includes(this.filtroEnemigo.toLowerCase()) &&
      !this.equipoEnemigo.some(enemigo => enemigo._id === t._id)
    ).slice(0, 15);
  }

  agregarAliado(tanque: Tanque): void {
    if (this.equipoAliado.length >= 16) {
      this.error = 'El equipo aliado no puede superar los 16 tanques.';
      return;
    }
    this.equipoAliado.push(tanque);
    this.filtroAliado = '';
    this.mostrarListaAliado = false;
    this.error = '';

    // Si es el primer tanque, lo ponemos como el del usuario por defecto
    if (!this.tanqueUsuario) {
      this.tanqueUsuario = tanque;
    }
  }

  agregarEnemigo(tanque: Tanque): void {
    if (this.equipoEnemigo.length >= 16) {
      this.error = 'El equipo enemigo no puede superar los 16 tanques.';
      return;
    }
    this.equipoEnemigo.push(tanque);
    this.filtroEnemigo = '';
    this.mostrarListaEnemigo = false;
    this.error = '';
  }

  quitarAliado(index: number): void {
    const tanqueQuitado = this.equipoAliado[index];
    this.equipoAliado.splice(index, 1);

    // Si quitamos el tanque del usuario, asignamos otro o lo ponemos a null
    if (this.tanqueUsuario?._id === tanqueQuitado._id) {
      this.tanqueUsuario = this.equipoAliado.length > 0 ? this.equipoAliado[0] : null;
    }
  }

  quitarEnemigo(index: number): void {
    this.equipoEnemigo.splice(index, 1);
  }

  seleccionarComoUsuario(tanque: Tanque): void {
    this.tanqueUsuario = tanque;
  }

  get descripcionModeloSeleccionado(): string {
    const modelo = this.modelos.find(m => m.id === this.modeloSeleccionado);
    return modelo ? modelo.descripcion : '';
  }

  simular(): void {
    if (this.equipoAliado.length === 0 || this.equipoEnemigo.length === 0) {
      this.error = 'Ambos equipos deben tener al menos 1 vehículo.';
      return;
    }
    if (!this.tanqueUsuario) {
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

    const request = {
      equipo_aliado: this.equipoAliado.map(t => t._id!),
      equipo_enemigo: this.equipoEnemigo.map(t => t._id!),
      tanque_usuario_id: this.tanqueUsuario._id!,
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

  regresar(): void {
    this.router.navigate(['/tanques']);
  }

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

  aplicarModoOscuro(): void {
    document.body.classList.add('dark-mode');
  }

  aplicarModoClaro(): void {
    document.body.classList.remove('dark-mode');
  }
}
