# api/routers/pizzas.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..dependencies import admin_required

router = APIRouter()

@router.get("/", response_model=list[schemas.PizzaOut])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Pizza).all()

@router.post("/", response_model=schemas.PizzaOut)
def crear(data: schemas.PizzaCreate, db: Session = Depends(get_db), user=Depends(admin_required)):
    nuevo = models.Pizza(**data.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{id}/disponible", response_model=schemas.PizzaOut)
def toggle(id: int, body: schemas.PizzaUpdate, db: Session = Depends(get_db), user=Depends(admin_required)):
    pizza = db.query(models.Pizza).filter(models.Pizza.id == id).first()
    if not pizza:
        raise HTTPException(404, "Pizza no encontrada")

    if body.disponible is not None:
        pizza.disponible = body.disponible

    db.commit()
    db.refresh(pizza)
    return pizza
