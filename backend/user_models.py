from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from pymongo import MongoClient
from getpass import getpass
from fastapi import Depends, HTTPException, status,APIRouter
from database import get_db
from auth import pwd_context


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
    es_admin: bool = False

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
    es_admin: bool = False
    class Config:
        populate_by_name = True

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

def hacer_admin(email: str):
    """
    Script para convertir un usuario existente en administrador.
    
    EXPLICACIÓN:
    - Busca un usuario por su email
    - Actualiza el campo es_admin a True
    - Esto te permite hacer admin a tu usuario después de registrarte
    
    Uso:
        python crear_admin.py
    """
    # Conectar a MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client["war_thunder_db"]
    usuarios_collection = db["usuarios"]
    
    # Buscar el usuario
    usuario = usuarios_collection.find_one({"email": email})
    
    if not usuario:
        print(f"❌ No se encontró el usuario con email: {email}")
        return
    
    # Actualizar a admin
    resultado = usuarios_collection.update_one(
        {"email": email},
        {"$set": {"es_admin": True}}
    )
    
    if resultado.modified_count > 0:
        print(f"✅ Usuario {email} ahora es ADMINISTRADOR")
    else:
        print(f"⚠️ El usuario {email} ya era administrador")

if __name__ == "__main__":
    print("=" * 50)
    print("CONVERTIR USUARIO EN ADMINISTRADOR")
    print("=" * 50)
    
    email = input("Email del usuario: ")
    
    confirmacion = input(f"¿Hacer admin a {email}? (s/n): ")
    
    if confirmacion.lower() == 's':
        hacer_admin(email)
    else:
        print("Operación cancelada")

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

@router.post("/registro", response_model=dict)
async def registrar_usuario(usuario: Usuario):
    """
    Registra un nuevo usuario.
    
    NUEVO: El primer usuario que se registre será automáticamente admin.
    """
    db = get_db()
    usuarios_collection = db["usuarios"]
    
    # Verificar si el email ya existe
    if usuarios_collection.find_one({"email": usuario.email}):
        raise HTTPException(
            status_code=400,
            detail="El email ya está registrado"
        )
    
    # Hash de la contraseña
    hashed_password = pwd_context.hash(usuario.password)
    
    # Contar usuarios existentes
    total_usuarios = usuarios_collection.count_documents({})
    
    # Si es el primer usuario, hacerlo admin automáticamente
    es_primer_usuario = (total_usuarios == 0)
    
    # Crear el usuario
    usuario_dict = {
        "email": usuario.email,
        "nombre_completo": usuario.nombre_completo,
        "hashed_password": hashed_password,
        "es_admin": es_primer_usuario or usuario.es_admin,  # ⭐ Primer usuario = admin
        "activo": True,
        "fecha_registro": datetime.now().isoformat()
    }
    
    resultado = usuarios_collection.insert_one(usuario_dict)
    
    mensaje = "Usuario registrado exitosamente"
    if es_primer_usuario:
        mensaje += " como ADMINISTRADOR (primer usuario del sistema)"
    
    return {
        "mensaje": mensaje,
        "id": str(resultado.inserted_id),
        "es_admin": usuario_dict["es_admin"]
    }