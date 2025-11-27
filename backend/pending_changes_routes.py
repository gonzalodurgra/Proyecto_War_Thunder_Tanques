# pending_changes_routes.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from bson import ObjectId

from auth import obtener_usuario_activo_actual
from user_models import UsuarioEnDB
from pending_changes_models import CambioPendiente, RespuestaRevision
from database import get_db

router = APIRouter(prefix="/cambios-pendientes", tags=["Cambios Pendientes"])

# ====================================================================
# FUNCIÓN AUXILIAR: Verificar si es administrador
# ====================================================================

def verificar_admin(usuario: UsuarioEnDB) -> None:
    """
    Verifica que el usuario actual sea administrador.
    Si no lo es, lanza una excepción.
    """
    if not usuario.es_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden realizar esta acción"
        )


# ====================================================================
# 1. CREAR CAMBIO PENDIENTE (Para usuarios normales)
# ====================================================================

async def crear_cambio_pendiente(
    tipo_operacion: str,
    coleccion: str,
    usuario: UsuarioEnDB,
    tanque_id: str = None,
    datos_originales: dict = None,
    datos_nuevos: dict = None
) -> str:
    """
    Crea un cambio pendiente en lugar de aplicarlo directamente.
    
    EXPLICACIÓN:
    Esta función se llama automáticamente desde tus endpoints de CRUD
    cuando un usuario NO es admin.
    
    Args:
        tipo_operacion: "crear", "actualizar" o "eliminar"
        coleccion: Nombre de la colección ("tanques")
        usuario: Usuario que solicita el cambio
        tanque_id: ID del tanque (para actualizar/eliminar)
        datos_originales: Estado actual del tanque
        datos_nuevos: Estado propuesto del tanque
        
    Returns:
        ID del cambio pendiente creado
    """
    db = get_db()
    cambios_collection = db["cambios_pendientes"]
    
    cambio = CambioPendiente(
        tipo_operacion=tipo_operacion,
        coleccion=coleccion,
        usuario_id=str(usuario.id),
        usuario_email=usuario.email,
        tanque_id=tanque_id,
        datos_originales=datos_originales,
        datos_nuevos=datos_nuevos,
        estado="pendiente"
    )
    
    resultado = cambios_collection.insert_one(cambio.model_dump())
    
    return str(resultado.inserted_id)


# ====================================================================
# 2. OBTENER TODOS LOS CAMBIOS PENDIENTES (Solo admin)
# ====================================================================

@router.get("/", response_model=List[dict])
async def obtener_cambios_pendientes(
    estado: str = "pendiente",  # Puede ser: pendiente, aprobado, rechazado, todos
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Obtiene todos los cambios pendientes de aprobación.
    Solo accesible para administradores.
    
    EXPLICACIÓN:
    - El admin puede ver todos los cambios solicitados
    - Puede filtrar por estado (pendiente, aprobado, rechazado)
    - Cada cambio muestra quién lo solicitó y qué quiere cambiar
    """
    verificar_admin(usuario_actual)
    
    db = get_db()
    cambios_collection = db["cambios_pendientes"]
    
    # Construir filtro
    filtro = {}
    if estado != "todos":
        filtro["estado"] = estado
    
    cambios = []
    for cambio in cambios_collection.find(filtro).sort("fecha_solicitud", -1):
        cambio["_id"] = str(cambio["_id"])
        # Convertir fechas a string para serialización
        if "fecha_solicitud" in cambio:
            cambio["fecha_solicitud"] = cambio["fecha_solicitud"].isoformat()
        if "fecha_revision" in cambio and cambio["fecha_revision"]:
            cambio["fecha_revision"] = cambio["fecha_revision"].isoformat()
        cambios.append(cambio)
    
    return cambios


# ====================================================================
# 3. OBTENER UN CAMBIO ESPECÍFICO (Solo admin)
# ====================================================================

@router.get("/{cambio_id}", response_model=dict)
async def obtener_cambio_por_id(
    cambio_id: str,
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Obtiene los detalles de un cambio específico.
    """
    verificar_admin(usuario_actual)
    
    if not ObjectId.is_valid(cambio_id):
        raise HTTPException(status_code=400, detail="ID inválido")
    
    db = get_db()
    cambios_collection = db["cambios_pendientes"]
    
    cambio = cambios_collection.find_one({"_id": ObjectId(cambio_id)})
    
    if not cambio:
        raise HTTPException(status_code=404, detail="Cambio no encontrado")
    
    cambio["_id"] = str(cambio["_id"])
    if "fecha_solicitud" in cambio:
        cambio["fecha_solicitud"] = cambio["fecha_solicitud"].isoformat()
    if "fecha_revision" in cambio and cambio["fecha_revision"]:
        cambio["fecha_revision"] = cambio["fecha_revision"].isoformat()
    
    return cambio


# ====================================================================
# 4. APROBAR O RECHAZAR CAMBIO (Solo admin)
# ====================================================================

@router.post("/{cambio_id}/revisar", response_model=dict)
async def revisar_cambio(
    cambio_id: str,
    revision: RespuestaRevision,
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Aprueba o rechaza un cambio pendiente.
    
    EXPLICACIÓN PASO A PASO:
    1. Verifica que el usuario es admin
    2. Busca el cambio pendiente
    3. Si se aprueba, aplica el cambio a la colección de tanques
    4. Si se rechaza, solo marca el cambio como rechazado
    5. Actualiza el registro del cambio con la decisión del admin
    """
    verificar_admin(usuario_actual)
    
    if not ObjectId.is_valid(cambio_id):
        raise HTTPException(status_code=400, detail="ID inválido")
    
    db = get_db()
    cambios_collection = db["cambios_pendientes"]
    tanques_collection = db["tanques"]
    
    # PASO 1: Buscar el cambio
    cambio = cambios_collection.find_one({"_id": ObjectId(cambio_id)})
    
    if not cambio:
        raise HTTPException(status_code=404, detail="Cambio no encontrado")
    
    if cambio["estado"] != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"Este cambio ya fue {cambio['estado']}"
        )
    
    # PASO 2: Si se aprueba, aplicar el cambio
    if revision.aprobar:
        try:
            if cambio["tipo_operacion"] == "crear":
                # Crear nuevo tanque
                tanques_collection.insert_one(cambio["datos_nuevos"])
                
            elif cambio["tipo_operacion"] == "actualizar":
                # Actualizar tanque existente
                tanques_collection.update_one(
                    {"_id": ObjectId(cambio["tanque_id"])},
                    {"$set": cambio["datos_nuevos"]}
                )
                
            elif cambio["tipo_operacion"] == "eliminar":
                # Eliminar tanque
                tanques_collection.delete_one(
                    {"_id": ObjectId(cambio["tanque_id"])}
                )
            
            nuevo_estado = "aprobado"
            mensaje = "Cambio aprobado y aplicado exitosamente"
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al aplicar el cambio: {str(e)}"
            )
    else:
        # Si se rechaza, solo actualizar el estado
        nuevo_estado = "rechazado"
        mensaje = "Cambio rechazado"
    
    # PASO 3: Actualizar el registro del cambio
    cambios_collection.update_one(
        {"_id": ObjectId(cambio_id)},
        {
            "$set": {
                "estado": nuevo_estado,
                "fecha_revision": datetime.now(),
                "admin_revisor_id": str(usuario_actual.id),
                "admin_revisor_email": usuario_actual.email,
                "comentario_admin": revision.comentario
            }
        }
    )
    
    return {
        "mensaje": mensaje,
        "estado": nuevo_estado,
        "comentario": revision.comentario
    }


# ====================================================================
# 5. OBTENER CAMBIOS DEL USUARIO ACTUAL
# ====================================================================

@router.get("/mis-cambios/", response_model=List[dict])
async def obtener_mis_cambios(
    usuario_actual: UsuarioEnDB = Depends(obtener_usuario_activo_actual)
):
    """
    Permite a un usuario ver el estado de sus propios cambios solicitados.
    """
    db = get_db()
    cambios_collection = db["cambios_pendientes"]
    
    cambios = []
    for cambio in cambios_collection.find(
        {"usuario_id": str(usuario_actual.id)}
    ).sort("fecha_solicitud", -1):
        cambio["_id"] = str(cambio["_id"])
        if "fecha_solicitud" in cambio:
            cambio["fecha_solicitud"] = cambio["fecha_solicitud"].isoformat()
        if "fecha_revision" in cambio and cambio["fecha_revision"]:
            cambio["fecha_revision"] = cambio["fecha_revision"].isoformat()
        cambios.append(cambio)
    
    return cambios