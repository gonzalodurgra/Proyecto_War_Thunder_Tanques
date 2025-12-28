from pydantic import BaseModel, Field
from typing import Optional, List, Dict

# Paso 1: Definir el modelo para las municiones
class Municion(BaseModel):
    """
    Modelo que representa una munición del tanque.
    BaseModel de Pydantic nos ayuda a validar los datos automáticamente.
    """
    nombre: str
    tipo: str
    penetracion_mm: List[int]  # Lista de valores de penetración
    masa_total: Optional[float] = None  # Optional significa que puede ser None
    velocidad_bala: Optional[int] = None
    masa_explosivo: Optional[float] = None

# Paso 2: Definir el modelo para las armas
class Arma(BaseModel):
    """
    Modelo que representa un arma del tanque.
    Contiene una lista de municiones disponibles.
    """
    municiones: List[Municion]

# Paso 3: Definir el modelo principal del tanque
class Tanque(BaseModel):
    """
    Modelo principal que representa un tanque completo.
    Incluye todas las características y estadísticas del tanque.
    """
    nombre: str
    rol: str
    nacion: str
    rating_arcade: float
    rating_realista: float
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
    setup_1: Dict[str, Arma]  # Diccionario con las armas del setup 1
    setup_2: Dict[str, Arma]  # Diccionario con las armas del setup 2

# Paso 4: Modelo para respuestas (incluye el ID de MongoDB)
class TanqueDB(Tanque):
    """
    Este modelo extiende Tanque y añade el campo 'id' que MongoDB genera.
    Field(alias="_id") significa que MongoDB usa "_id" pero nosotros lo llamamos "id"
    """
    id: Optional[str] = Field(alias="_id", default=None)
    
    class Config:
        # Permite que Pydantic trabaje con el campo "_id" de MongoDB
        populate_by_name = True