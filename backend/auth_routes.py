from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta, datetime
from database import get_users_collection
from user_models import Usuario, UsuarioDB, UsuarioEnDB, Token, LoginRequest
from passlib.hash import argon2
from auth import (
    autenticar_usuario,
    crear_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    obtener_usuario_activo_actual
)

# ====================================================================
# CREAR EL ROUTER
# ====================================================================
# EXPLICACIÓN: APIRouter agrupa rutas relacionadas
# Todas las rutas aquí empezarán con /auth

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

# ====================================================================
# RUTA 1: REGISTRAR USUARIO
# ====================================================================

@router.post("/register", response_model=UsuarioDB, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(usuario: Usuario):
    """
    Registra un nuevo usuario en el sistema.
    
    Proceso:
    1. Verifica que el username no exista
    2. Verifica que el email no exista
    3. Hashea la contraseña
    4. Guarda el usuario en la base de datos
    
    Args:
        usuario: Datos del nuevo usuario
        
    Returns:
        Datos del usuario creado (sin contraseña)
    """
    users_collection = get_users_collection()
    
    # PASO 1: Verificar si el username ya existe
    usuario_existente = users_collection.find_one({"username": usuario.username})
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está en uso"
        )
    
    # PASO 2: Verificar si el email ya existe
    email_existente = users_collection.find_one({"email": usuario.email})
    if email_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # PASO 3: Crear el usuario con la contraseña hasheada
    usuario_db = UsuarioEnDB(
        username=usuario.username,
        email=usuario.email,
        nombre_completo=usuario.nombre_completo,
        hashed_password=argon2.hash(usuario.password),  # Hashear la contraseña
        activo=True,
        fecha_registro=datetime.now().isoformat()
    )
    
    # PASO 4: Guardar en la base de datos
    usuario_dict = usuario_db.model_dump()
    users_collection.insert_one(usuario_dict)
    
    # PASO 5: Devolver los datos del usuario (sin la contraseña)
    return UsuarioDB(
        username=usuario_db.username,
        email=usuario_db.email,
        nombre_completo=usuario_db.nombre_completo,
        activo=usuario_db.activo,
        fecha_registro=usuario_db.fecha_registro
    )

# ====================================================================
# RUTA 2: LOGIN
# ====================================================================

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """
    Inicia sesión y devuelve un token JWT.
    
    Proceso:
    1. Verifica que el usuario y contraseña sean correctos
    2. Crea un token JWT
    3. Devuelve el token
    
    Args:
        login_data: Username y password
        
    Returns:
        Token JWT de acceso
    """
    # PASO 1: Autenticar al usuario
    usuario = autenticar_usuario(login_data.username, login_data.password)
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # PASO 2: Crear el token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_access_token(
        data={"sub": usuario.username},
        expires_delta=access_token_expires
    )
    
    # PASO 3: Devolver el token
    return Token(
        access_token=access_token,
        token_type="bearer",
        username=usuario.username
    )

# ====================================================================
# RUTA 3: OBTENER PERFIL DEL USUARIO ACTUAL
# ====================================================================

@router.get("/me", response_model=UsuarioDB)
async def obtener_perfil(
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Obtiene el perfil del usuario que está autenticado.
    
    Esta ruta está PROTEGIDA: solo funciona si envías un token válido.
    
    Args:
        usuario_actual: Usuario extraído del token JWT (automático)
        
    Returns:
        Datos del usuario actual
    """
    return UsuarioDB(
        username=usuario_actual.username,
        email=usuario_actual.email,
        nombre_completo=usuario_actual.nombre_completo,
        activo=usuario_actual.activo,
        fecha_registro=usuario_actual.fecha_registro
    )