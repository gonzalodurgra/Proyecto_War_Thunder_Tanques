from pydantic import BaseModel, Field, field_validator
from bson.decimal128 import Decimal128
from typing import Optional, List, Dict, Any

# ====================================================================
# SECCIÓN 1: MODELOS BALÍSTICOS Y DE ARMAMENTO
# ====================================================================

# Paso 1: Definir el modelo para las municiones
class Municion(BaseModel):
    """
    Modelo que representa una munición individual del tanque.
    Define características balísticas como tablas de penetración a diferentes distancias,
    velocidad de salida y masa explosiva (incluyendo metadatos de estimación por IA).
    """
    nombre: str
    tipo: str
    penetracion_mm: List[int]  # Lista de valores de penetración a [0m, 100m, 500m, 1000m, 1500m, 2000m]
    masa_total: Optional[float] = None  # Masa total del proyectil en kg
    velocidad_bala: Optional[int] = None  # Velocidad inicial en boca (m/s)
    masa_explosivo: Optional[float] = None  # Masa del relleno explosivo en gramos
    datos_generados_por_ia: Optional[bool] = False  # Bandera para indicar si los datos fueron estimados por Gemini


# Paso 2: Definir el modelo para las armas
class Arma(BaseModel):
    """
    Modelo que representa un arma o cañón del tanque.
    Agrupa la lista de municiones disponibles para dicha pieza de artillería.
    """
    municiones: List[Municion]


# ====================================================================
# SECCIÓN 2: MODELO PRINCIPAL DEL TANQUE Y CONVERSIÓN DE TIPOS
# ====================================================================

# Paso 3: Definir el modelo principal del tanque
class Tanque(BaseModel):
    """
    Modelo principal que representa la ficha técnica completa de un tanque de War Thunder.
    Incluye estadísticas de blindaje, movilidad, ángulos de cañón, tiempos de recarga,
    rotaciones de torreta y configuraciones de armamento (setup_1 y setup_2).
    """
    nombre: str
    rol: str
    nacion: str
    rating_arcade: float | None
    rating_realista: float | None
    tripulacion: int
    visibilidad: int
    peso: float
    blindaje_chasis: int
    blindaje_torreta: int
    velocidad_adelante_arcade: int
    velocidad_adelante_realista: int
    velocidad_atras_arcade: int
    velocidad_atras_realista: int
    relacion_potencia_peso: float
    relacion_potencia_peso_realista: float
    angulo_depresion: int
    angulo_elevacion: int
    recarga: float
    cadencia: float
    cargador: int
    municion_total: int
    rotacion_torreta_horizontal_arcade: float
    rotacion_torreta_horizontal_realista: float
    rotacion_torreta_vertical_arcade: float
    rotacion_torreta_vertical_realista: float
    setup_1: Dict[str, Arma]  # Diccionario con las armas del setup principal
    setup_2: Dict[str, Arma]  # Diccionario con las armas del setup secundario/alternativo

    @field_validator('rating_arcade', 'rating_realista', mode='before')
    @classmethod
    def convertir_decimal128_a_float(cls, valor):
        """
        Validador que convierte tipos Decimal128 de MongoDB a float nativo de Python
        antes de validar los modelos, evitando errores de serialización JSON.
        """
        if isinstance(valor, Decimal128):
            return float(valor.to_decimal())
        return valor


# Paso 4: Modelo para respuestas con ID de persistencia
class TanqueDB(Tanque):
    """
    Extensión del modelo Tanque que mapea el identificador único `_id` de MongoDB
    al campo `id` accesible desde la API y el frontend.
    """
    id: Optional[str] = Field(alias="_id", default=None)
    
    class Config:
        # Permite que Pydantic serialice/deserialice usando tanto el alias `_id` como `id`
        populate_by_name = True


# ====================================================================
# SECCIÓN 3: MODELOS PARA SIMULACIÓN DE COMBATE CON IA (1v1 Y EQUIPOS)
# ====================================================================

class CombateIARequest(BaseModel):
    """
    Esquema de solicitud para simular un duelo 1 vs 1.
    Recibe los IDs de MongoDB de los dos vehículos enfrentados, la situación táctica y el modelo LLM a utilizar.
    """
    vehiculo1_id: str
    vehiculo2_id: str
    situacion: str
    modelo: Optional[str] = "gemini-3.1-flash-lite-preview"


class CombateIAResponse(BaseModel):
    """
    Esquema de respuesta tras la simulación de duelo 1 vs 1.
    Devuelve el ganador calculado por Monte Carlo/Red Neuronal, el análisis técnico generado por Gemini,
    puntos clave y el desglose de probabilidades y municiones óptimas empleadas.
    """
    ganador: str
    analisis: str
    puntos_clave: List[str]
    detalles_aliados: Optional[List[Dict[str, Any]]] = None
    detalles_enemigos: Optional[List[Dict[str, Any]]] = None
    datos_estimados_ia: Optional[bool] = False


class ElementoAnalisis(BaseModel):
    """
    Representa la clasificación táctica individual de un tanque en combate de escuadrones
    (por ejemplo: blanco prioritario, objetivo peligroso a evitar o mejor aliado de apoyo).
    """
    nombre: str
    nacion: str
    razon: str


class SimulacionEquiposIARequest(BaseModel):
    """
    Esquema de solicitud para batallas de escuadrones (hasta 16 vs 16).
    Contiene las listas completas de ambos equipos, el índice del tanque tripulado por el usuario,
    el escenario de combate y el modelo de IA seleccionado.
    """
    equipo_aliado: List[Dict]
    equipo_enemigo: List[Dict]
    tanque_usuario_index: int
    situacion: str
    modelo: Optional[str] = "gemini-3.1-flash-lite"


class SimulacionEquiposIAResponse(BaseModel):
    """
    Esquema de respuesta para la simulación de combate por equipos.
    Proporciona la probabilidad general de victoria aliada, la narrativa táctica del enfrentamiento
    y la categorización de amenazas y sinergias entre vehículos.
    """
    resultado_general: str
    probabilidad_victoria: float
    enemigos_prioritarios: List[ElementoAnalisis]
    enemigos_a_evitar: List[ElementoAnalisis]
    no_representan_amenaza: List[ElementoAnalisis]
    mas_daninos: List[ElementoAnalisis]
    mejores_companeros: List[ElementoAnalisis]
    detalles_aliados: Optional[List[Dict[str, Any]]] = None
    detalles_enemigos: Optional[List[Dict[str, Any]]] = None
    datos_estimados_ia: Optional[bool] = False