# user_models.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from bson import ObjectId

# ====================================================================
# MODELOS DE USUARIO
# ====================================================================

class Usuario(BaseModel):
    """Modelo para crear un usuario nuevo"""
    email: EmailStr
    nombre_completo: str
    password: str
    username: str

class UsuarioDB(BaseModel):
    """Modelo de usuario en la base de datos (sin password)"""
    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr
    nombre_completo: str
    es_admin: bool = False
    activo: bool = True
    fecha_registro: Optional[str] = None
    @field_validator("id", mode="before")
    def convertir_objectid(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v
    class Config:
        populate_by_name = True

class UsuarioEnDB(BaseModel):
    """Modelo de usuario en la base de datos (con password hasheado)"""
    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr
    nombre_completo: str
    hashed_password: str
    es_admin: bool = False
    activo: bool = True
    fecha_registro: Optional[str] = None
    username: str
    @field_validator("id", mode="before")
    def convertir_objectid(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v

    class Config:
        populate_by_name = True

# ====================================================================
# MODELOS DE AUTENTICACIÓN
# ====================================================================

class Token(BaseModel):
    """Modelo para el token JWT"""
    access_token: str
    token_type: str
    username: str  # Info del usuario logueado

class TokenData(BaseModel):
    """Datos almacenados en el token JWT"""
    username: Optional[str] = None

class LoginRequest(BaseModel):
    """Modelo para la solicitud de login"""
    username: str
    password: str