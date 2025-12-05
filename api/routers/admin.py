from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import admin_required
from .. import models, schemas

router = APIRouter()

@router.get("/pedidos", response_model=list[schemas.PedidoOut])
def listar(db: Session = Depends(get_db), user=Depends(admin_required)):
    return db.query(models.Pedido).all()

@router.post("/pedidos/{id}/despacho", response_model=schemas.PedidoOut)
def despachar(id: int, db: Session = Depends(get_db), user=Depends(admin_required)):
    p = db.query(models.Pedido).filter(models.Pedido.id == id).first()
    if not p:
        raise HTTPException(404, "Pedido no encontrado")
    p.estado = "en_camino"
    db.commit()
    db.refresh(p)
    return p

@router.post("/pedidos/{id}/reasignar", response_model=schemas.PedidoOut)
def reasignar(id: int, db: Session = Depends(get_db), user=Depends(admin_required)):
    p = db.query(models.Pedido).filter(models.Pedido.id == id).first()
    if not p:
        raise HTTPException(404, "Pedido no encontrado")

    return p
