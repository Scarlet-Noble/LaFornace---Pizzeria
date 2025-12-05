from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from ..database import get_db
from .. import models, schemas
from ..dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=schemas.PedidoOut)
def crear(data: schemas.PedidoCreate, 
          db: Session = Depends(get_db), 
          user = Depends(get_current_user)):

    total = 0
    for item in data.items:
        p = db.query(models.Pizza).filter(models.Pizza.id == item.pizza_id).first()
        if not p or not p.disponible:
            raise HTTPException(400, "Producto no disponible")
        total += p.precio * item.cantidad

    codigo = f"LF-{uuid4().hex[:8].upper()}"

    pedido = models.Pedido(
        usuario_id=user.id,
        total=total,
        estado="pagado",
        codigo_seguimiento=codigo
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    for item in data.items:
        p = db.query(models.Pizza).filter(models.Pizza.id == item.pizza_id).first()
        detalle = models.PedidoItem(
            pedido_id=pedido.id,
            pizza_id=p.id,
            cantidad=item.cantidad,
            precio_unitario=p.precio
        )
        db.add(detalle)

    db.commit()
    db.refresh(pedido)
    return pedido

@router.get("/seguimiento/{codigo}", response_model=schemas.PedidoOut)
def seguimiento(codigo: str, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.codigo_seguimiento == codigo).first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    return pedido
