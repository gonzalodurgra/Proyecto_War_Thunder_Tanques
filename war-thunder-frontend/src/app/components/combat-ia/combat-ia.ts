import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TanksService, Tanque, CombateIAResponse } from '../../services/tanks';
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

  // Filtros para la selección
  filtro1: string = '';
  filtro2: string = '';
  mostrarLista1: boolean = false;
  mostrarLista2: boolean = false;

  constructor(private tanksService: TanksService, private router: Router) {}

  ngOnInit(): void {
    this.cargarTanques();
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
    ).slice(0, 5);
  }

  get tanquesFiltrados2() {
    return this.tanques.filter(t => 
      t.nombre.toLowerCase().includes(this.filtro2.toLowerCase())
    ).slice(0, 5);
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
      situacion: this.situacion
    };

    this.tanksService.simularCombateIA(request).subscribe({
      next: (res) => {
        this.resultado = res;
        this.cargando = false;
      },
      error: (err) => {
        this.error = 'Error al simular el combate. Asegúrate de que la API Key de Gemini esté configurada.';
        this.cargando = false;
        console.error(err);
      }
    });
  }

  regresar(): void {
    this.router.navigate(['/tanques']);
  }
}
