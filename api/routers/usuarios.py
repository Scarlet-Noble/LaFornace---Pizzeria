# api/routers/usuarios.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..auth import hash_password, verify_password, crear_token

router = APIRouter()

@router.post("/registro", response_model=schemas.UsuarioOut)
def registro(data: schemas.UsuarioCreate, db: Session = Depends(get_db)):

    existe = db.query(models.Usuario).filter(models.Usuario.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Correo ya registrado")

    nuevo = models.Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        direccion=data.direccion,
        telefono=data.telefono,
        es_admin=False
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return nuevo


@router.post("/login")
def login(data: schemas.UsuarioLogin, db: Session = Depends(get_db)):

    user = db.query(models.Usuario).filter(models.Usuario.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = crear_token({"id": user.id})

    return {
        "token": token,
        "usuario": {
            "id": user.id,
            "nombre": user.nombre,
            "email": user.email,
            "es_admin": user.es_admin,
            "direccion": user.direccion,
            "telefono": user.telefono,
        }
    }
