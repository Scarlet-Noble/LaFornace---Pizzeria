# api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .auth import verificar_token
from . import models

bearer = HTTPBearer()

def get_current_user(
    credentials = Depends(bearer),
    db: Session = Depends(get_db)
):
    payload = verificar_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user = db.query(models.Usuario).filter(models.Usuario.id == payload["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return user

def admin_required(current = Depends(get_current_user)):
    if not current.es_admin:
        raise HTTPException(status_code=403, detail="Acceso solo administradores")
    # IMPORTANTE: sin coma, retorna el usuario, no una tupla
    return current
