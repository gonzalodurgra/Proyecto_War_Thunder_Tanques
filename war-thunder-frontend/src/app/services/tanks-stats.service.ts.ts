import { Injectable } from '@angular/core';
import * as aq from 'arquero';
import { Tanque, Municion } from './tanks';

// ====================================================================
// PASO 1: Definir interfaces para las estadísticas con DECILES
// ====================================================================

// Esta interfaz guarda los valores mínimo, máximo y DECILES de una estadística
export interface RangoEstadistica {
  min: number;      // Valor mínimo
  max: number;      // Valor máximo
  d1: number;       // Decil 1 (10%)
  d2: number;       // Decil 2 (20%)
  d3: number;       // Decil 3 (30%)
  d4: number;       // Decil 4 (40%)
  d5: number;       // Decil 5 (50% - mediana)
  d6: number;       // Decil 6 (60%)
  d7: number;       // Decil 7 (70%)
  d8: number;       // Decil 8 (80%)
  d9: number;       // Decil 9 (90%)
}

// Esta interfaz guarda todos los rangos de todas las estadísticas
export interface RangosEstadisticas {
  tripulacion: RangoEstadistica;
  visibilidad: RangoEstadistica;
  blindaje_chasis: RangoEstadistica;
  blindaje_torreta: RangoEstadistica;

  velocidad_adelante_arcade: RangoEstadistica;
  velocidad_adelante_realista: RangoEstadistica;

  velocidad_atras_arcade: RangoEstadistica;
  velocidad_atras_realista: RangoEstadistica;

  relacion_potencia_peso: RangoEstadistica;
  relacion_potencia_peso_realista: RangoEstadistica;

  angulo_depresion: RangoEstadistica;
  angulo_elevacion: RangoEstadistica;

  recarga: RangoEstadistica;
  cadencia: RangoEstadistica;

  rotacion_torreta_horizontal_arcade: RangoEstadistica;
  rotacion_torreta_horizontal_realista: RangoEstadistica;

  rotacion_torreta_vertical_arcade: RangoEstadistica;
  rotacion_torreta_vertical_realista: RangoEstadistica;
}

// Interfaz para estadísticas agrupadas por rating
export interface EstadisticasPorRating {
  rating: number;
  rangos: RangosEstadisticas;
  cantidad_tanques: number;
}

@Injectable({
  providedIn: 'root'
})
export class TanksStatsService {

  // Variables para almacenar los rangos calculados
  private rangosGlobales: RangosEstadisticas | null = null;
  private rangosPorRating: Map<number, RangosEstadisticas> = new Map();

  // NUEVO: Variables para almacenar rangos de penetración por rating
  private rangosPenetracionPorRating: Map<number, RangoEstadistica> = new Map();

  constructor() { }

  // ====================================================================
  // MÉTODO: Calcular rangos GLOBALES (todos los tanques)
  // ====================================================================

  calcularRangosGlobales(tanques: Tanque[]): RangosEstadisticas {
    tanques = this.limpiarTanques(tanques)
    const tabla = aq.from(tanques);

    const columnasEstadisticas = [
      'tripulacion',
      'visibilidad',
      'blindaje_chasis',
      'blindaje_torreta',
      'velocidad_adelante_arcade',
      'velocidad_adelante_realista',
      'velocidad_atras_arcade',
      'velocidad_atras_realista',
      'relacion_potencia_peso',
      'relacion_potencia_peso_realista',
      'angulo_depresion',
      'angulo_elevacion',
      'recarga',
      'cadencia',
      'rotacion_torreta_horizontal_arcade',
      'rotacion_torreta_horizontal_realista',
      'rotacion_torreta_vertical_arcade',
      'rotacion_torreta_vertical_realista'
    ];

    const rangos: any = {};

    columnasEstadisticas.forEach(columna => {
      // Calcular estadísticas con DECILES (10 partes)
      const stats = tabla
        .rollup({
          min: aq.op.min(columna),
          max: aq.op.max(columna),
          d1: aq.op.quantile(columna, 0.10),  // Decil 1 (10%)
          d2: aq.op.quantile(columna, 0.20),  // Decil 2 (20%)
          d3: aq.op.quantile(columna, 0.30),  // Decil 3 (30%)
          d4: aq.op.quantile(columna, 0.40),  // Decil 4 (40%)
          d5: aq.op.quantile(columna, 0.50),  // Decil 5 (50% - mediana)
          d6: aq.op.quantile(columna, 0.60),  // Decil 6 (60%)
          d7: aq.op.quantile(columna, 0.70),  // Decil 7 (70%)
          d8: aq.op.quantile(columna, 0.80),  // Decil 8 (80%)
          d9: aq.op.quantile(columna, 0.90)   // Decil 9 (90%)
        })
        .object();

      rangos[columna] = stats;
    });

    this.rangosGlobales = rangos as RangosEstadisticas;
    return this.rangosGlobales;
  }

  // ====================================================================
  // MÉTODO: Calcular rangos POR RATING (con ventana de Matchmaking: ±1.0 BR / ±3 niveles)
  // ====================================================================
  // EXPLICACIÓN: Para cada rating, se evalúa contra todos los vehículos que puede enfrentar:
  // desde downtier total (rating - 1.0, 3 niveles) hasta uptier total (rating + 1.0, 3 niveles),
  // respetando el mínimo (1.0) y máximo de War Thunder.

  calcularRangosPorRating(tanques: Tanque[], modo: string): EstadisticasPorRating[] {
    // PASO 1: Agrupar tanques por rating usando Arquero
    const tabla = aq.from(tanques);

    // Obtener ratings únicos
    const ratingsUnicos = tabla
      .groupby(modo)
      .count()
      .orderby(modo)
      .array(modo);

    // PASO 2: Para cada rating, calcular sus propios rangos considerando el rango de matchmaking
    const estadisticasPorRating: EstadisticasPorRating[] = [];

    ratingsUnicos.forEach(rating => {
      // Filtrar tanques dentro de la ventana de matchmaking [rating - 1.0, rating + 1.0] (±3 pasos de BR)
      const tanquesDelRango = this.obtenerTanquesRangoMatchmaking(tanques, rating, modo);

      if (tanquesDelRango.length > 0) {
        // Calcular rangos para el grupo completo de combate de este rating
        const rangos = this.calcularRangosParaGrupo(tanquesDelRango);

        // Guardar en el Map para acceso rápido
        this.rangosPorRating.set(rating, rangos);

        // Agregar a la lista de resultados
        estadisticasPorRating.push({
          rating: rating,
          rangos: rangos,
          cantidad_tanques: tanquesDelRango.length
        });
      }
    });

    return estadisticasPorRating;
  }

  // ====================================================================
  // MÉTODO AUXILIAR: Calcular rangos para un grupo específico de tanques
  // ====================================================================

  private calcularRangosParaGrupo(tanques: Tanque[]): RangosEstadisticas {
    tanques = this.limpiarTanques(tanques)
    const tabla = aq.from(tanques);

    const columnasEstadisticas = [
      'tripulacion',
      'visibilidad',
      'blindaje_chasis',
      'blindaje_torreta',
      'velocidad_adelante_arcade',
      'velocidad_adelante_realista',
      'velocidad_atras_arcade',
      'velocidad_atras_realista',
      'relacion_potencia_peso',
      'relacion_potencia_peso_realista',
      'angulo_depresion',
      'angulo_elevacion',
      'recarga',
      'cadencia',
      'rotacion_torreta_horizontal_arcade',
      'rotacion_torreta_horizontal_realista',
      'rotacion_torreta_vertical_arcade',
      'rotacion_torreta_vertical_realista'
    ];

    const rangos: any = {};

    columnasEstadisticas.forEach(columna => {
      const stats = tabla
        .rollup({
          min: aq.op.min(columna),
          max: aq.op.max(columna),
          d1: aq.op.quantile(columna, 0.10),
          d2: aq.op.quantile(columna, 0.20),
          d3: aq.op.quantile(columna, 0.30),
          d4: aq.op.quantile(columna, 0.40),
          d5: aq.op.quantile(columna, 0.50),
          d6: aq.op.quantile(columna, 0.60),
          d7: aq.op.quantile(columna, 0.70),
          d8: aq.op.quantile(columna, 0.80),
          d9: aq.op.quantile(columna, 0.90)
        })
        .object();

      rangos[columna] = stats;
    });

    return rangos as RangosEstadisticas;
  }

  // ====================================================================
  // MÉTODO: Obtener color según el valor (10 niveles de color)
  // ====================================================================

  obtenerColor(
    nombreEstadistica: keyof RangosEstadisticas,
    valor: number,
    rating: number | null = null,
    invertir: boolean = false
  ): string {

    // Decidir qué rangos usar: por rating o globales
    let rango: RangoEstadistica | undefined;

    if (rating && this.rangosPorRating.has(rating)) {
      rango = this.rangosPorRating.get(rating)![nombreEstadistica];
    } else if (this.rangosGlobales) {
      rango = this.rangosGlobales[nombreEstadistica];
    }

    if (!rango) {
      console.warn('Rangos no calculados. Llama primero a calcularRangos()');
      return '#808080'; // Gris por defecto
    }

    // PASO 1: Determinar en qué DECIL está el valor
    // Tenemos 10 colores diferentes: desde rojo (malo) hasta verde brillante (excelente)
    let color: string;

    // Colores en gradiente de 10 niveles
    const coloresAscendentes = [
      '#ef4444', // Rojo oscuro (0-10%)
      '#f87171', // Rojo (10-20%)
      '#fb923c', // Naranja oscuro (20-30%)
      '#fbbf24', // Naranja (30-40%)
      '#facc15', // Amarillo oscuro (40-50%)
      '#a3e635', // Amarillo-verde (50-60%)
      '#84cc16', // Verde limón (60-70%)
      '#4ade80', // Verde claro (70-80%)
      '#22c55e', // Verde (80-90%)
      '#16a34a'  // Verde oscuro (90-100%)
    ];

    // Para estadísticas invertidas (menor es mejor)
    const coloresDescendentes = [...coloresAscendentes].reverse();

    const colores = invertir ? coloresDescendentes : coloresAscendentes;

    // Determinar el índice de color según el decil
    if (valor <= rango.d1) {
      color = colores[0];
    } else if (valor <= rango.d2) {
      color = colores[1];
    } else if (valor <= rango.d3) {
      color = colores[2];
    } else if (valor <= rango.d4) {
      color = colores[3];
    } else if (valor <= rango.d5) {
      color = colores[4];
    } else if (valor <= rango.d6) {
      color = colores[5];
    } else if (valor <= rango.d7) {
      color = colores[6];
    } else if (valor <= rango.d8) {
      color = colores[7];
    } else if (valor <= rango.d9) {
      color = colores[8];
    } else {
      color = colores[9];
    }

    return color;
  }

  // ====================================================================
  // MÉTODO: Obtener colores para todas las estadísticas de un tanque
  // ====================================================================

  obtenerColoresTanque(
    tanque: Tanque,
    usarRatingEspecifico: boolean = true,
    ratingCustomArcade: number | null = null,
    ratingCustomRealista: number | null = null
  ): { [key: string]: string } {
    const rating_arcade = ratingCustomArcade !== null
      ? ratingCustomArcade
      : (usarRatingEspecifico ? tanque.rating_arcade : null);

    const rating_realista = ratingCustomRealista !== null
      ? ratingCustomRealista
      : (usarRatingEspecifico ? tanque.rating_realista : null);

    return {
      tripulacion_arcade: this.obtenerColor('tripulacion', tanque.tripulacion, rating_arcade),
      visibilidad_arcade: this.obtenerColor('visibilidad', tanque.visibilidad, rating_arcade, true),
      blindaje_chasis_arcade: this.obtenerColor('blindaje_chasis', tanque.blindaje_chasis, rating_arcade),
      blindaje_torreta_arcade: this.obtenerColor('blindaje_torreta', tanque.blindaje_torreta, rating_arcade),
      velocidad_adelante_arcade: this.obtenerColor('velocidad_adelante_arcade', tanque.velocidad_adelante_arcade, rating_arcade),
      velocidad_atras_arcade: this.obtenerColor('velocidad_atras_arcade', tanque.velocidad_atras_arcade, rating_arcade),
      potencia_peso_arcade: this.obtenerColor('relacion_potencia_peso', tanque.relacion_potencia_peso, rating_arcade),
      depresion_arcade: this.obtenerColor('angulo_depresion', tanque.angulo_depresion, rating_arcade),
      elevacion_arcade: this.obtenerColor('angulo_elevacion', tanque.angulo_elevacion, rating_arcade),
      recarga_arcade: this.obtenerColor('recarga', tanque.recarga, rating_arcade, true),
      cadencia_arcade: this.obtenerColor('cadencia', tanque.cadencia, rating_arcade),
      rotacion_horizontal_arcade: this.obtenerColor('rotacion_torreta_horizontal_arcade', tanque.rotacion_torreta_horizontal_arcade, rating_arcade),
      rotacion_vertical_arcade: this.obtenerColor('rotacion_torreta_vertical_arcade', tanque.rotacion_torreta_vertical_arcade, rating_arcade),
      tripulacion_realista: this.obtenerColor('tripulacion', tanque.tripulacion, rating_realista),
      visibilidad_realista: this.obtenerColor('visibilidad', tanque.visibilidad, rating_realista, true),
      blindaje_chasis_realista: this.obtenerColor('blindaje_chasis', tanque.blindaje_chasis, rating_realista),
      blindaje_torreta_realista: this.obtenerColor('blindaje_torreta', tanque.blindaje_torreta, rating_realista),
      velocidad_adelante_realista: this.obtenerColor('velocidad_adelante_realista', tanque.velocidad_adelante_realista, rating_realista),
      velocidad_atras_realista: this.obtenerColor('velocidad_atras_realista', tanque.velocidad_atras_realista, rating_realista),
      potencia_peso_realista: this.obtenerColor('relacion_potencia_peso_realista', tanque.relacion_potencia_peso_realista, rating_realista),
      depresion_realista: this.obtenerColor('angulo_depresion', tanque.angulo_depresion, rating_realista),
      elevacion_realista: this.obtenerColor('angulo_elevacion', tanque.angulo_elevacion, rating_realista),
      recarga_realista: this.obtenerColor('recarga', tanque.recarga, rating_realista, true),
      cadencia_realista: this.obtenerColor('cadencia', tanque.cadencia, rating_realista),
      rotacion_horizontal_realista: this.obtenerColor('rotacion_torreta_horizontal_realista', tanque.rotacion_torreta_horizontal_realista, rating_realista),
      rotacion_vertical_realista: this.obtenerColor('rotacion_torreta_vertical_realista', tanque.rotacion_torreta_vertical_realista, rating_realista)
    };
  }

  // ====================================================================
  // MÉTODO: Obtener percentil exacto de un valor
  // ====================================================================
  // EXPLICACIÓN: Este método devuelve en qué percentil está un valor
  // Por ejemplo: si devuelve 85, significa que el tanque es mejor que el 85% de los tanques

  obtenerPercentil(
    nombreEstadistica: keyof RangosEstadisticas,
    valor: number,
    rating: number | null = null
  ): number {

    let rango: RangoEstadistica | undefined;

    if (rating && this.rangosPorRating.has(rating)) {
      rango = this.rangosPorRating.get(rating)![nombreEstadistica];
    } else if (this.rangosGlobales) {
      rango = this.rangosGlobales[nombreEstadistica];
    }

    if (!rango) {
      return 50; // Valor medio por defecto
    }

    // Interpolar entre deciles
    if (valor <= rango.d1) return 5;
    if (valor <= rango.d2) return 15;
    if (valor <= rango.d3) return 25;
    if (valor <= rango.d4) return 35;
    if (valor <= rango.d5) return 45;
    if (valor <= rango.d6) return 55;
    if (valor <= rango.d7) return 65;
    if (valor <= rango.d8) return 75;
    if (valor <= rango.d9) return 85;
    return 95;
  }

  // ====================================================================
  // LISTA DE BATTLE RATINGS OFICIALES DE WAR THUNDER (Pasos de 0.3 / 0.4)
  // ====================================================================
  private readonly BATTLE_RATINGS_OFICIALES = [
    1.0, 1.3, 1.7, 2.0, 2.3, 2.7, 3.0, 3.3, 3.7, 4.0, 4.3, 4.7, 5.0, 5.3, 5.7, 6.0,
    6.3, 6.7, 7.0, 7.3, 7.7, 8.0, 8.3, 8.7, 9.0, 9.3, 9.7, 10.0, 10.3, 10.7, 11.0,
    11.3, 11.7, 12.0, 12.3, 12.7, 13.0, 13.3
  ];

  /**
   * Obtiene los niveles disponibles de downtier / uptier relativos para un rating dado.
   * Retorna una lista con la diferencia de pasos (-3 a +3), la diferencia numérica y el BR de destino.
   * Por ejemplo: [{ paso: -3, delta: -1.0, brDestino: 2.7, label: '-1.0 (Downtier total)' }, ...]
   */
  obtenerOpcionesNivelesMatchmaking(rating: number): { paso: number; delta: number; brDestino: number; label: string }[] {
    const brRedondeado = Math.round(rating * 10) / 10;
    const index = this.BATTLE_RATINGS_OFICIALES.findIndex(
      br => Math.abs(br - brRedondeado) < 0.05
    );

    if (index === -1) {
      return [{ paso: 0, delta: 0, brDestino: brRedondeado, label: 'BR Base (0.0)' }];
    }

    const opciones: { paso: number; delta: number; brDestino: number; label: string }[] = [];
    const minIndex = Math.max(0, index - 3);
    const maxIndex = Math.min(this.BATTLE_RATINGS_OFICIALES.length - 1, index + 3);

    for (let i = minIndex; i <= maxIndex; i++) {
      const paso = i - index; // -3, -2, -1, 0, +1, +2, +3
      const brDestino = this.BATTLE_RATINGS_OFICIALES[i];
      const delta = Math.round((brDestino - brRedondeado) * 10) / 10;

      let label = '';
      if (paso === -3) label = `Downtier total (${delta > 0 ? '+' : ''}${delta.toFixed(1)})`;
      else if (paso === -2) label = `Downtier -2 (${delta.toFixed(1)})`;
      else if (paso === -1) label = `Downtier -1 (${delta.toFixed(1)})`;
      else if (paso === 0) label = `BR Base (${brDestino.toFixed(1)})`;
      else if (paso === 1) label = `Uptier +1 (+${delta.toFixed(1)})`;
      else if (paso === 2) label = `Uptier +2 (+${delta.toFixed(1)})`;
      else if (paso === 3) label = `Uptier total (+${delta.toFixed(1)})`;

      opciones.push({
        paso,
        delta,
        brDestino,
        label
      });
    }

    return opciones;
  }

  /**
   * Obtiene la lista de Battle Ratings que forman el rango de matchmaking [BR - 1.0, BR + 1.0]
   * (3 niveles de downtier, BR actual, y 3 niveles de uptier, hasta ±1.0 BR).
   * Respeta los límites mínimos (1.0) y máximos de War Thunder.
   */
  obtenerBrsEmparejamiento(rating: number): number[] {
    const brRedondeado = Math.round(rating * 10) / 10;
    const index = this.BATTLE_RATINGS_OFICIALES.findIndex(
      br => Math.abs(br - brRedondeado) < 0.05
    );

    // Si el rating está en la lista oficial, tomar ±3 pasos (downtier 3 niveles a uptier 3 niveles)
    if (index !== -1) {
      const minIndex = Math.max(0, index - 3);
      const maxIndex = Math.min(this.BATTLE_RATINGS_OFICIALES.length - 1, index + 3);
      return this.BATTLE_RATINGS_OFICIALES.slice(minIndex, maxIndex + 1);
    }

    // Si es un valor no estándar, filtrar por rango numérico [rating - 1.05, rating + 1.05]
    return this.BATTLE_RATINGS_OFICIALES.filter(
      br => br >= rating - 1.05 && br <= rating + 1.05
    );
  }

  /**
   * Filtra los tanques que entran en el rango de matchmaking (±1.0 BR / ±3 niveles) de un rating dado.
   */
  obtenerTanquesRangoMatchmaking(tanques: Tanque[], rating: number, modo: string): Tanque[] {
    const brsValidos = new Set(this.obtenerBrsEmparejamiento(rating));

    return tanques.filter(t => {
      const r = modo === 'rating_arcade' ? t.rating_arcade : t.rating_realista;
      if (r === null || r === undefined) return false;
      const rRedondeado = Math.round(r * 10) / 10;
      return brsValidos.has(rRedondeado);
    });
  }
  // Prioridad (menor número = mayor prioridad):
  // 1: APHE y variantes (APHEBC, APHECBC); APCBC con explosivo
  // 2: APFSDS
  // 3: ATGM
  // 4: HEATFS
  // 5: APDS
  // 6: AP y variantes sólidas (APC, APBC, APCBC) sin explosivo
  // 7: HEAT
  // 8: HESH
  // 9: APCR
  // 10: HE
  // 99: Otros
  obtenerPrioridadTipoMunicion(municion: Municion): number {
    const rawTipo = (municion.tipo || '').toUpperCase().trim();
    const nombre = (municion.nombre || '').toUpperCase().trim();
    const tieneExplosivo = (municion.masa_explosivo !== null && municion.masa_explosivo !== undefined && municion.masa_explosivo > 0);

    // 1. APHE y sus variantes (APHEBC, APHECBC); APCBC con explosivo
    if (
      rawTipo.includes('APHE') ||
      rawTipo.includes('SAPHE') ||
      rawTipo.includes('SAPCBC') ||
      (rawTipo.includes('APCBC') && tieneExplosivo) ||
      (rawTipo.includes('APBC') && tieneExplosivo) ||
      (rawTipo.includes('APC') && tieneExplosivo)
    ) {
      return 1;
    }

    // 2. APFSDS
    if (rawTipo.includes('APFSDS')) {
      return 2;
    }

    // 3. ATGM
    if (rawTipo.includes('ATGM') || nombre.includes('ATGM')) {
      return 3;
    }

    // 4. HEATFS
    if (rawTipo.includes('HEATFS') || rawTipo.includes('HEAT-FS')) {
      return 4;
    }

    // 5. APDS
    if (rawTipo.includes('APDS')) {
      return 5;
    }

    // 6. AP y variantes (APC, APBC, APCBC) sin explosivo (sólidas)
    if (
      rawTipo.includes('APCBC') ||
      rawTipo.includes('APBC') ||
      rawTipo.includes('APC') ||
      rawTipo.includes('AP-T') ||
      rawTipo.includes('AP/T') ||
      rawTipo.startsWith('AP') ||
      rawTipo.includes('/AP')
    ) {
      return 6;
    }

    // 7. HEAT
    if (rawTipo.includes('HEAT')) {
      return 7;
    }

    // 8. HESH
    if (rawTipo.includes('HESH')) {
      return 8;
    }

    // 9. APCR / HVAP
    if (rawTipo.includes('APCR') || rawTipo.includes('HVAP')) {
      return 9;
    }

    // 10. HE y sus variantes (HE-VT, HE-TF, HE-OR, etc.)
    if (rawTipo.startsWith('HE') || rawTipo.includes('/HE') || rawTipo.includes('-HE')) {
      return 10;
    }

    return 99;
  }

  /**
   * Selecciona la mejor munición de un tanque según la jerarquía de tipos de munición.
   * A igual prioridad de tipo, desempata la que tenga mayor penetración a 0m.
   */
  obtenerPenetracionPriorizadaTanque(tanque: Tanque): number | null {
    let mejorMunicion: Municion | null = null;
    let mejorPrioridad = 999;
    let mejorPenetracion0m = -1;

    [tanque.armamento, tanque.setup_1, tanque.setup_2].forEach(setup => {
      if (setup) {
        Object.values(setup).forEach(arma => {
          arma.municiones.forEach(municion => {
            if (municion.penetracion_mm && municion.penetracion_mm.length > 0) {
              const pen0 = municion.penetracion_mm[0];
              if (typeof pen0 === 'number' && !isNaN(pen0)) {
                const prioridad = this.obtenerPrioridadTipoMunicion(municion);

                // Si encontramos un tipo de bala con mayor prioridad (menor número)
                if (prioridad < mejorPrioridad) {
                  mejorPrioridad = prioridad;
                  mejorPenetracion0m = pen0;
                  mejorMunicion = municion;
                } else if (prioridad === mejorPrioridad) {
                  // Mismo tipo o categoría: desempata la mayor penetración a 0m
                  if (pen0 > mejorPenetracion0m) {
                    mejorPenetracion0m = pen0;
                    mejorMunicion = municion;
                  }
                }
              }
            }
          });
        });
      }
    });

    return mejorPenetracion0m >= 0 ? mejorPenetracion0m : null;
  }

  // ====================================================================
  // NUEVO MÉTODO: Calcular rangos de penetración por rating
  // ====================================================================
  // EXPLICACIÓN: Este método agrupa las penetraciones por rating del tanque
  // y calcula los deciles para cada grupo

  calcularRangosPenetracionPorRating(tanques: Tanque[], modo: string): void {
    console.log('📊 Calculando rangos de penetración por rating...');

    // Limpiar rangos anteriores
    this.rangosPenetracionPorRating.clear();

    // Obtener ratings únicos
    const ratingsUnicos = new Set<number>();
    tanques.forEach(tanque => {
      const rating = modo === 'rating_arcade' ? tanque.rating_arcade : tanque.rating_realista;
      if (rating) ratingsUnicos.add(rating);
    });

    // Para cada rating, calcular rangos de penetración considerando la ventana de matchmaking (±1.0 BR / ±3 niveles)
    ratingsUnicos.forEach(rating => {
      // Filtrar tanques en el rango de matchmaking [rating - 1.0, rating + 1.0]
      const tanquesDelRango = this.obtenerTanquesRangoMatchmaking(tanques, rating, modo);

      // Extraer la munición priorizada de cada tanque de este rango
      const penetracionesDelRango: any[] = [];

      tanquesDelRango.forEach(tanque => {
        const penTanque = this.obtenerPenetracionPriorizadaTanque(tanque);
        if (penTanque !== null) {
          penetracionesDelRango.push(penTanque);
        }
      });

      // Limpiar y calcular estadísticas
      const penetracionesLimpias = this.limpiarPenetraciones(penetracionesDelRango);

      if (penetracionesLimpias.length > 0) {
        const tablaPenetraciones = aq.from(
          penetracionesLimpias.map(p => ({ penetracion: p }))
        );

        const stats = tablaPenetraciones
          .rollup({
            min: aq.op.min('penetracion'),
            max: aq.op.max('penetracion'),
            d1: aq.op.quantile('penetracion', 0.10),
            d2: aq.op.quantile('penetracion', 0.20),
            d3: aq.op.quantile('penetracion', 0.30),
            d4: aq.op.quantile('penetracion', 0.40),
            d5: aq.op.quantile('penetracion', 0.50),
            d6: aq.op.quantile('penetracion', 0.60),
            d7: aq.op.quantile('penetracion', 0.70),
            d8: aq.op.quantile('penetracion', 0.80),
            d9: aq.op.quantile('penetracion', 0.90)
          })
          .object() as RangoEstadistica;

        // Guardar en el Map
        this.rangosPenetracionPorRating.set(rating, stats);

        console.log(`✅ Rating ${rating}: ${penetracionesLimpias.length} penetraciones procesadas`);
      }
    })
  }
  // ====================================================================
  // MÉTODO: Obtener color para penetración de munición
  // ====================================================================

  obtenerColorPenetracion(
    penetracionMm: number,
    todosLosTanques: Tanque[],
    rating: number | null = null
  ): string {

    let stats: RangoEstadistica | undefined;

    // PASO 1: Intentar usar rangos específicos del rating
    if (rating && this.rangosPenetracionPorRating.has(rating)) {
      stats = this.rangosPenetracionPorRating.get(rating);
    }
    // PASO 2: Si no hay rangos por rating, calcular globales
    else {
      const todasLasPenetraciones: any[] = [];

      todosLosTanques.forEach(tanque => {
        const penTanque = this.obtenerPenetracionPriorizadaTanque(tanque);
        if (penTanque !== null) {
          todasLasPenetraciones.push(penTanque);
        }
      });

      const penetracionesLimpias = this.limpiarPenetraciones(todasLasPenetraciones);

      if (penetracionesLimpias.length === 0) return '#999999';

      const tablaPenetraciones = aq.from(
        penetracionesLimpias.map(p => ({ penetracion: p }))
      );

      stats = tablaPenetraciones
        .rollup({
          min: aq.op.min('penetracion'),
          max: aq.op.max('penetracion'),
          d1: aq.op.quantile('penetracion', 0.10),
          d2: aq.op.quantile('penetracion', 0.20),
          d3: aq.op.quantile('penetracion', 0.30),
          d4: aq.op.quantile('penetracion', 0.40),
          d5: aq.op.quantile('penetracion', 0.50),
          d6: aq.op.quantile('penetracion', 0.60),
          d7: aq.op.quantile('penetracion', 0.70),
          d8: aq.op.quantile('penetracion', 0.80),
          d9: aq.op.quantile('penetracion', 0.90)
        })
        .object() as RangoEstadistica;
    }

    if (!stats) return '#999999';

    // PASO 3: Asignar color según decil
    if (penetracionMm <= stats.d1) return '#ef4444';
    if (penetracionMm <= stats.d2) return '#f87171';
    if (penetracionMm <= stats.d3) return '#fb923c';
    if (penetracionMm <= stats.d4) return '#fbbf24';
    if (penetracionMm <= stats.d5) return '#facc15';
    if (penetracionMm <= stats.d6) return '#a3e635';
    if (penetracionMm <= stats.d7) return '#84cc16';
    if (penetracionMm <= stats.d8) return '#4ade80';
    if (penetracionMm <= stats.d9) return '#22c55e';
    return '#16a34a';
  }

  // ====================================================================
  // NUEVO MÉTODO: Obtener percentil de penetración
  // ====================================================================

  obtenerPercentilPenetracion(
    penetracionMm: number,
    rating: number | null = null
  ): number {

    let stats: RangoEstadistica | undefined;

    if (rating && this.rangosPenetracionPorRating.has(rating)) {
      stats = this.rangosPenetracionPorRating.get(rating);
    }

    if (!stats) return 50;

    // Interpolar entre deciles
    if (penetracionMm <= stats.d1) return 5;
    if (penetracionMm <= stats.d2) return 15;
    if (penetracionMm <= stats.d3) return 25;
    if (penetracionMm <= stats.d4) return 35;
    if (penetracionMm <= stats.d5) return 45;
    if (penetracionMm <= stats.d6) return 55;
    if (penetracionMm <= stats.d7) return 65;
    if (penetracionMm <= stats.d8) return 75;
    if (penetracionMm <= stats.d9) return 85;
    return 95;
  }


  private limpiarTanques(tanques: Tanque[]): Tanque[] {
    const columnasNumericas = [
      'tripulacion',
      'visibilidad',
      'blindaje_chasis',
      'blindaje_torreta',
      'velocidad_adelante_arcade',
      'velocidad_adelante_realista',
      'velocidad_atras_arcade',
      'velocidad_atras_realista',
      'relacion_potencia_peso',
      'relacion_potencia_peso_realista',
      'angulo_depresion',
      'angulo_elevacion',
      'recarga',
      'cadencia',
      'rotacion_torreta_horizontal_arcade',
      'rotacion_torreta_horizontal_realista',
      'rotacion_torreta_vertical_arcade',
      'rotacion_torreta_vertical_realista'
    ];

    return tanques.map(t => {
      const copia = { ...t };

      columnasNumericas.forEach(col => {
        const valor = (copia as any)[col];

        // Convertir string a número, o dejar 0 si no se puede convertir
        (copia as any)[col] = typeof valor === 'number' ? valor : Number(valor) || 0;
      });

      return copia;
    });
  }
  private limpiarPenetraciones(valores: any[]): number[] {
    return valores
      .map((v): number | null => {

        if (typeof v === 'string') {
          const limpio = v.replace(/[^\d.]/g, '');
          const num = Number(limpio);
          return isNaN(num) ? null : num;
        }

        if (typeof v === 'number') return v;

        return null;
      })
      .filter((v): v is number => typeof v === 'number' && !isNaN(v) && v > 0);
  }
}
