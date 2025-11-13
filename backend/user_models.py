from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# ====================================================================
# MODELOS DE USUARIO
# ====================================================================

class Usuario(BaseModel):
    """
    Modelo para crear un usuario nuevo.
    EmailStr valida que sea un email válido.
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    nombre_completo: Optional[str] = None

class UsuarioDB(BaseModel):
    """
    Modelo del usuario como se guarda en la base de datos.
    NO incluye la contraseña en las respuestas.
    """
    username: str
    email: str
    nombre_completo: Optional[str] = None
    disabled: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

class UsuarioEnDB(UsuarioDB):
    """
    Modelo interno que SÍ incluye la contraseña hasheada.
    Solo se usa internamente, nunca se envía al cliente.
    """
    hashed_password: str

# ====================================================================
# MODELOS DE AUTENTICACIÓN
# ====================================================================

class Token(BaseModel):
    """
    Respuesta cuando el usuario hace login exitoso.
    """
    access_token: str
    token_type: str = "bearer"
    username: str

class TokenData(BaseModel):
    """
    Datos que se almacenan dentro del token JWT.
    """
    username: Optional[str] = None

class LoginRequest(BaseModel):
    """
    Datos que el usuario envía para hacer login.
    """
    username: str
    password: str