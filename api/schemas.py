# api/schemas.py
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    direccion: Optional[str] = None
    telefono: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(UsuarioBase):
    id: int
    es_admin: bool

    class Config:
        orm_mode = True
        from_attributes = True


class PizzaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    disponible: bool = True


class PizzaCreate(PizzaBase):
    pass


class PizzaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    disponible: Optional[bool] = None


class PizzaOut(PizzaBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True


class PedidoItemCreate(BaseModel):
    pizza_id: int
    cantidad: int


class PedidoCreate(BaseModel):
    usuario_id: Optional[int] = None
    items: List[PedidoItemCreate]


class PedidoItemOut(BaseModel):
    id: int
    pizza_id: int
    cantidad: int
    precio_unitario: float

    class Config:
        orm_mode = True
        from_attributes = True


class PedidoOut(BaseModel):
    id: int
    usuario_id: Optional[int]
    total: float
    estado: str
    codigo_seguimiento: str
    fecha_creacion: datetime
    items: List[PedidoItemOut]

    class Config:
        orm_mode = True
        from_attributes = True


class PedidoEstadoUpdate(BaseModel):
    estado: str
