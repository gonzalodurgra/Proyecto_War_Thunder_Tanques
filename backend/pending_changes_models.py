# pending_changes_models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime

class CambioPendiente(BaseModel):
    """
    Modelo para representar un cambio pendiente de aprobación.
    
    EXPLICACIÓN:
    - Cada vez que un usuario no-admin hace un cambio, 
      se guarda aquí en lugar de aplicarse directamente
    - El admin puede revisar y aprobar/rechazar estos cambios
    """
    tipo_operacion: Literal["crear", "actualizar", "eliminar"]
    coleccion: str  # "tanques" en este caso
    usuario_id: str
    usuario_email: str
    
    # Datos del cambio
    tanque_id: Optional[str] = None  # ID del tanque (para actualizar/eliminar)
    datos_originales: Optional[Dict[str, Any]] = None  # Estado antes del cambio
    datos_nuevos: Optional[Dict[str, Any]] = None  # Estado después del cambio
    
    # Estado del cambio
    estado: Literal["pendiente", "aprobado", "rechazado"] = "pendiente"
    fecha_solicitud: datetime = Field(default_factory=datetime.now)
    fecha_revision: Optional[datetime] = None
    admin_revisor_id: Optional[str] = None
    admin_revisor_email: Optional[str] = None
    comentario_admin: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "tipo_operacion": "actualizar",
                "coleccion": "tanques",
                "usuario_id": "123",
                "usuario_email": "usuario@example.com",
                "tanque_id": "507f1f77bcf86cd799439011",
                "datos_originales": {"nombre": "Tiger I", "rating_arcade": "5.7"},
                "datos_nuevos": {"nombre": "Tiger I", "rating_arcade": "6.0"},
                "estado": "pendiente"
            }
        }


class RespuestaRevision(BaseModel):
    """
    Modelo para la respuesta del admin al revisar un cambio.
    """
    aprobar: bool  # True = aprobar, False = rechazar
    comentario: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "aprobar": True,
                "comentario": "Cambio válido y bien documentado"
            }
        }