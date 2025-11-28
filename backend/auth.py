from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database import get_users_collection
from user_models import TokenData, UsuarioEnDB
import os
from dotenv import load_dotenv

# ====================================================================
# CONFIGURACIÓN
# ====================================================================

# IMPORTANTE: En producción, usa una clave secreta segura y guárdala en variables de entorno
load_dotenv()
SECRET_KEY =  os.getenv("SECRET_KEY") # Cámbiala!
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # El token expira en 30 minutos

# ====================================================================
# PASO 1: Configurar el contexto de encriptación
# ====================================================================
# EXPLICACIÓN: CryptContext usa bcrypt para hashear contraseñas
# bcrypt es un algoritmo muy seguro que hace que sea prácticamente
# imposible descifrar las contraseñas

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# ====================================================================
# PASO 2: Configurar OAuth2
# ====================================================================
# EXPLICACIÓN: oauth2_scheme extrae el token del header "Authorization"
# El cliente enviará: Authorization: Bearer <token>

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ====================================================================
# FUNCIONES DE CONTRASEÑAS
# ====================================================================

def verificar_password(password_plano: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash.
    
    Args:
        password_plano: La contraseña que el usuario escribe
        hashed_password: El hash guardado en la base de datos
        
    Returns:
        True si coinciden, False si no
    """
    return pwd_context.verify(password_plano, hashed_password)

#def hash_password(password: str) -> str:
    """
    Convierte una contraseña en texto plano a un hash seguro.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash de la contraseña (string largo y aleatorio)
    """
    #return pwd_context.hash(password)

# ====================================================================
# FUNCIONES DE JWT (TOKENS)
# ====================================================================

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    print("SECRET_KEY:", os.getenv("SECRET_KEY"))
    print("JWT_ALGORITHM:", os.getenv("JWT_ALGORITHM"))
    """
    Crea un token JWT con los datos del usuario.
    
    Args:
        data: Diccionario con los datos a incluir en el token (ej: username)
        expires_delta: Tiempo hasta que expire el token
        
    Returns:
        String con el token JWT
    """
    # Copiar los datos para no modificar el original
    to_encode = data.copy()
    
    # Calcular la fecha de expiración
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Añadir la fecha de expiración al token
    to_encode.update({"exp": expire})
    
    # Crear el token JWT
    encoded_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("JWT_ALGORITHM"))
    return encoded_jwt

# ====================================================================
# FUNCIONES DE BASE DE DATOS
# ====================================================================

def obtener_usuario(username: str) -> Optional[UsuarioEnDB]:
    """
    Busca un usuario en la base de datos por su username.
    
    Args:
        username: Nombre de usuario
        
    Returns:
        Usuario si existe, None si no
    """
    users_collection = get_users_collection()
    usuario_dict = users_collection.find_one({"username": username})
    
    if usuario_dict:
        return UsuarioEnDB(**usuario_dict)
    return None

def autenticar_usuario(username: str, password: str) -> Optional[UsuarioEnDB]:
    """
    Verifica que el usuario y contraseña sean correctos.
    
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
        
    Returns:
        Usuario si las credenciales son correctas, None si no
    """
    usuario = obtener_usuario(username)
    
    if not usuario:
        return None
    
    if not verificar_password(password, usuario.hashed_password):
        return None
    
    return usuario

# ====================================================================
# DEPENDENCIAS DE FASTAPI
# ====================================================================

async def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> UsuarioEnDB:
    """
    Extrae y valida el usuario actual desde el token JWT.
    Esta función se usa como dependencia en las rutas protegidas.
    
    Args:
        token: Token JWT extraído del header Authorization
        
    Returns:
        Usuario actual
        
    Raises:
        HTTPException si el token es inválido o expiró
    """
    # Definir la excepción para credenciales inválidas
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el token JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username)
        
    except JWTError:
        raise credentials_exception
    
    # Buscar el usuario en la base de datos
    usuario = obtener_usuario(username=token_data.username)
    
    if usuario is None:
        raise credentials_exception
    
    return usuario

async def obtener_usuario_activo_actual(
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_actual)
) -> UsuarioEnDB:
    """
    Verifica que el usuario actual esté activo (no deshabilitado).
    
    Args:
        usuario_actual: Usuario obtenido del token
        
    Returns:
        Usuario si está activo
        
    Raises:
        HTTPException si el usuario está deshabilitado
    """
    if not usuario_actual.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario deshabilitado"
        )
    
    return usuario_actual