# api/main.py
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from uuid import uuid4

from .database import engine, get_db
from . import models, schemas
from .auth import hash_password, verify_password, crear_token, verificar_token
from .dependencies import get_current_user, admin_required

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API La Fornace",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "msg": "API lista"}


# =========================================================
#   USUARIOS
# =========================================================
@app.post("/api/usuarios/registro", response_model=schemas.UsuarioOut)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):

    existente = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    nuevo = models.Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        password_hash=hash_password(usuario.password),
        direccion=usuario.direccion,
        telefono=usuario.telefono,
        es_admin=False
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.post("/api/usuarios/login")
def login_usuario(credenciales: schemas.UsuarioLogin, db: Session = Depends(get_db)):

    user = db.query(models.Usuario).filter(models.Usuario.email == credenciales.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not verify_password(credenciales.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # IMPORTANTE: el payload lleva "id", que lee get_current_user
    token = crear_token({"id": user.id})

    usuario_data = jsonable_encoder(user)

    return {
        "token": token,
        "usuario": usuario_data
    }


# =========================================================
#   PIZZAS
# =========================================================
@app.get("/api/pizzas", response_model=List[schemas.PizzaOut])
def listar_pizzas(db: Session = Depends(get_db)):
    return db.query(models.Pizza).all()


@app.post("/api/pizzas", response_model=schemas.PizzaOut)
def crear_pizza(
    pizza: schemas.PizzaCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(admin_required)
):
    nueva = models.Pizza(
        nombre=pizza.nombre,
        descripcion=pizza.descripcion,
        precio=pizza.precio,
        disponible=pizza.disponible
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.put("/api/pizzas/{pizza_id}", response_model=schemas.PizzaOut)
def actualizar_pizza(
    pizza_id: int,
    datos: schemas.PizzaUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(admin_required)
):
    pizza = db.query(models.Pizza).filter(models.Pizza.id == pizza_id).first()
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza no encontrada")

    for campo, valor in datos.dict(exclude_unset=True).items():
        setattr(pizza, campo, valor)

    db.commit()
    db.refresh(pizza)
    return pizza


# =========================================================
#   PEDIDOS (CLIENTE)
# =========================================================
@app.post("/api/pedidos", response_model=schemas.PedidoOut)
def crear_pedido(
    pedido_data: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    if not pedido_data.items:
        raise HTTPException(status_code=400, detail="El pedido debe tener items")

    total = 0
    for item in pedido_data.items:
        pizza = db.query(models.Pizza).filter(models.Pizza.id == item.pizza_id).first()
        if not pizza or not pizza.disponible:
            raise HTTPException(status_code=400, detail="Pizza no disponible")
        total += pizza.precio * item.cantidad

    codigo = f"LF-{uuid4().hex[:8].upper()}"

    nuevo = models.Pedido(
        usuario_id=current_user.id,
        total=total,
        estado="pagado",
        codigo_seguimiento=codigo
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # Guardar items
    for item in pedido_data.items:
        pizza = db.query(models.Pizza).filter(models.Pizza.id == item.pizza_id).first()
        detalle = models.PedidoItem(
            pedido_id=nuevo.id,
            pizza_id=item.pizza_id,
            cantidad=item.cantidad,
            precio_unitario=pizza.precio
        )
        db.add(detalle)

    db.commit()
    db.refresh(nuevo)

    return nuevo


@app.get("/api/pedidos/seguimiento/{codigo}", response_model=schemas.PedidoOut)
def seguimiento(codigo: str, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.codigo_seguimiento == codigo).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido


# =========================================================
#   PEDIDOS (ADMIN) – para US08
# =========================================================
@app.get("/api/pedidos", response_model=List[schemas.PedidoOut])
def listar_pedidos_admin(
    db: Session = Depends(get_db),
    current_admin = Depends(admin_required)
):
    return db.query(models.Pedido).all()


@app.put("/api/admin/pedidos/{pedido_id}/estado", response_model=schemas.PedidoOut)
def actualizar_estado_pedido(
    pedido_id: int,
    data: schemas.PedidoEstadoUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(admin_required)
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    pedido.estado = data.estado
    db.commit()
    db.refresh(pedido)
    return pedido
