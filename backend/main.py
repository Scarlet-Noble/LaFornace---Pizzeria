from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict
from jose import jwt, JWTError
from passlib.hash import bcrypt
from datetime import datetime, timedelta
from uuid import uuid4

# ===================== APP & CORS =====================
app = FastAPI(title="La Fornace API", version="1.0")

# CORS simple para desarrollo (permite llamadas desde tus HTML locales o Live Server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # en producción restringe; para demo dejamos abierto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = "super-secret-fornace"  # cambia en prod
JWT_ALG = "HS256"
ACCESS_MIN = 24 * 60  # 24 horas sesión

def create_token(sub: str, is_admin: bool = False):
    payload = {
        "sub": sub,
        "adm": is_admin,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_MIN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def get_current(auth: Optional[str] = Header(None, alias="Authorization")):
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Falta token")
    token = auth.split()[1]
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return {"email": data["sub"], "is_admin": bool(data.get("adm", False))}
    except JWTError:
        raise HTTPException(401, "Token inválido")

# ===================== MODELOS =====================
class User(BaseModel):
    email: EmailStr
    password_hash: str
    is_admin: bool = False
    verified: bool = True
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None

class Product(BaseModel):
    id: str
    name: str
    price: int
    available: bool = True

class CartItem(BaseModel):
    product_id: str
    quantity: int

class OrderItem(BaseModel):
    product_id: str
    name: str
    unit_price: int
    quantity: int
    subtotal: int

class Order(BaseModel):
    id: str
    user: EmailStr
    items: List[OrderItem]
    total: int
    status: str = "PAID"  # PAID, SHIPPED, DELIVERED

class Invoice(BaseModel):
    id: str
    order_id: str
    to: EmailStr
    total: int
    issued_at: datetime

class Dispatch(BaseModel):
    order_id: str
    courier: str
    status: str = "PREP"   # PREP, ON_ROUTE, DELIVERED

class Track(BaseModel):
    order_id: str
    status: str            # PREP, ON_ROUTE, DELIVERED
    updated_at: datetime

# ===================== STORAGE EN MEMORIA =====================
USERS: Dict[str, User] = {}
PRODUCTS: Dict[str, Product] = {
    "p1": Product(id="p1", name="Margherita", price=8990),
    "p2": Product(id="p2", name="Pepperoni",  price=9990),
    "p3": Product(id="p3", name="Cuatro Quesos", price=12990),
}
CARTS: Dict[str, List[CartItem]] = {}
ORDERS: Dict[str, Order] = {}
INVOICES: Dict[str, Invoice] = {}
DISPATCHES: Dict[str, Dispatch] = {}
TRACKS: Dict[str, Track] = {}

# ===================== SCHEMAS I/O =====================
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AddCartIn(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)

class PayIn(BaseModel):
    card_number: str
    name: str
    cvv: str
    expiry: str

class AvailabilityIn(BaseModel):
    product_id: str
    available: bool

class ReassignIn(BaseModel):
    order_id: str
    courier: str

# ===================== HEALTH =====================
@app.get("/")
def root():
    return {"ok": True, "svc": "LaFornace API"}

# ===================== AUTH (US-01, US-02, US-03 parcial) =====================
@app.post("/auth/register")
def register(body: RegisterIn):
    if body.email in USERS:
        raise HTTPException(400, "El email ya está en uso")
    USERS[body.email] = User(email=body.email, password_hash=bcrypt.hash(body.password))
    # Primer usuario registrado es admin (demo)
    if sum(1 for _ in USERS.values()) == 1:
        USERS[body.email].is_admin = True
    return {"ok": True}

@app.post("/auth/login")
def login(body: LoginIn):
    u = USERS.get(body.email)
    if not u or not bcrypt.verify(body.password, u.password_hash):
        if u:
            u.failed_attempts += 1
            if u.failed_attempts >= 5:
                u.locked_until = datetime.utcnow() + timedelta(minutes=10)
                raise HTTPException(423, "Cuenta bloqueada 10 min")
        raise HTTPException(401, "Credenciales inválidas")
    if u.locked_until and datetime.utcnow() < u.locked_until:
        raise HTTPException(423, "Cuenta temporalmente bloqueada")
    if not u.verified:
        raise HTTPException(401, "Verifica tu correo para continuar")
    u.failed_attempts = 0
    token = create_token(u.email, u.is_admin)
    return {"token": token, "is_admin": u.is_admin}

# ===================== MENÚ (US-04) =====================
@app.get("/menu", response_model=List[Product])
def menu():
    return list(PRODUCTS.values())

# ===================== CARRITO (US-05) =====================
@app.get("/cart", response_model=List[CartItem])
def get_cart(user=Depends(get_current)):
    return CARTS.get(user["email"], [])

@app.post("/cart/add")
def add_cart(item: AddCartIn, user=Depends(get_current)):
    p = PRODUCTS.get(item.product_id)
    if not p or not p.available:
        raise HTTPException(400, "Producto no disponible")
    cart = CARTS.setdefault(user["email"], [])
    for c in cart:
        if c.product_id == item.product_id:
            c.quantity += item.quantity
            break
    else:
        cart.append(CartItem(product_id=item.product_id, quantity=item.quantity))
    return {"ok": True}

@app.post("/cart/clear")
def clear_cart(user=Depends(get_current)):
    CARTS[user["email"]] = []
    return {"ok": True}

# ===================== CHECKOUT / PAGO / ORDEN / BOLETA (US-06, US-07) =====================
@app.post("/checkout/pay")
def pay(body: PayIn, user=Depends(get_current)):
    cart = CARTS.get(user["email"], [])
    if not cart:
        raise HTTPException(400, "Carrito vacío")

    # Regla de demo: si la tarjeta termina en 0 → rechazo (cumple Gherkin de pago rechazado)
    if body.card_number.strip()[-1] == "0":
        return {"approved": False, "message": "Pago rechazado, inténtalo de nuevo"}

    # Construir orden
    items: List[OrderItem] = []
    total = 0
    for c in cart:
        p = PRODUCTS[c.product_id]
        if not p.available:
            raise HTTPException(400, f"{p.name} no disponible")
        sub = p.price * c.quantity
        items.append(OrderItem(
            product_id=p.id, name=p.name,
            unit_price=p.price, quantity=c.quantity, subtotal=sub
        ))
        total += sub

    order_id = uuid4().hex[:8]
    order = Order(id=order_id, user=user["email"], items=items, total=total, status="PAID")
    ORDERS[order_id] = order

    # Boleta
    inv_id = uuid4().hex[:8]
    invoice = Invoice(id=inv_id, order_id=order_id, to=user["email"], total=total, issued_at=datetime.utcnow())
    INVOICES[inv_id] = invoice

    # “Enviar” boleta (demo: log a consola)
    print(f"[EMAIL] Boleta #{inv_id} enviada a {user['email']} total ${total}")

    # Crear despacho + tracking inicial
    DISPATCHES[order_id] = Dispatch(order_id=order_id, courier="Repartidor A")
    TRACKS[order_id] = Track(order_id=order_id, status="PREP", updated_at=datetime.utcnow())

    # limpiar carrito
    CARTS[user["email"]] = []

    return {"approved": True, "order_id": order_id, "invoice_id": inv_id, "total": total}

@app.get("/invoice/{order_id}", response_model=Invoice)
def get_invoice(order_id: str, user=Depends(get_current)):
    inv = next((i for i in INVOICES.values() if i.order_id == order_id), None)
    if not inv: raise HTTPException(404, "Boleta no encontrada")
    if inv.to != user["email"] and not user["is_admin"]:
        raise HTTPException(403, "Sin permiso")
    return inv

@app.post("/invoice/resend/{order_id}")
def resend_invoice(order_id: str, user=Depends(get_current)):
    inv = next((i for i in INVOICES.values() if i.order_id == order_id), None)
    if not inv: raise HTTPException(404, "Boleta no encontrada")
    if inv.to != user["email"] and not user["is_admin"]:
        raise HTTPException(403, "Sin permiso")
    print(f"[EMAIL] Reenvío de boleta #{inv.id} a {inv.to}")
    return {"ok": True}

# ===================== DESPACHO / TRACKING (US-08, US-09) =====================
@app.post("/dispatch/reassign")
def reassign(body: ReassignIn, user=Depends(get_current)):
    if not user["is_admin"]:
        raise HTTPException(403, "Solo admin")
    d = DISPATCHES.get(body.order_id)
    if not d: raise HTTPException(404, "Orden no existe")
    d.courier = body.courier
    print(f"[DISPATCH] Orden {body.order_id} reasignada a {body.courier}")
    return {"ok": True}

@app.post("/dispatch/advance/{order_id}")
def advance(order_id: str, user=Depends(get_current)):
    o = ORDERS.get(order_id)
    if not o: raise HTTPException(404, "Orden no existe")
    if o.user != user["email"] and not user["is_admin"]:
        raise HTTPException(403, "Sin permiso")

    t = TRACKS[order_id]
    if t.status == "PREP":
        t.status = "ON_ROUTE"; ORDERS[order_id].status = "SHIPPED"
    elif t.status == "ON_ROUTE":
        t.status = "DELIVERED"; ORDERS[order_id].status = "DELIVERED"
    t.updated_at = datetime.utcnow()
    return {"status": t.status}

@app.get("/tracking/{order_id}", response_model=Track)
def tracking(order_id: str, user=Depends(get_current)):
    tr = TRACKS.get(order_id)
    if not tr: raise HTTPException(404, "Sin tracking")
    o = ORDERS[order_id]
    if o.user != user["email"] and not user["is_admin"]:
        raise HTTPException(403, "Sin permiso")
    return tr

# ===================== ADMIN DISPONIBILIDAD (US-10) =====================
@app.post("/admin/availability")
def availability(body: AvailabilityIn, user=Depends(get_current)):
    if not user["is_admin"]:
        raise HTTPException(403, "Solo admin")
    p = PRODUCTS.get(body.product_id)
    if not p: raise HTTPException(404, "Producto no existe")
    p.available = body.available
    return {"ok": True, "product": p}
