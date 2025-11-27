# api/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext

# Usamos argon2 como definiste
pwd = CryptContext(schemes=["argon2"], deprecated="auto")

SECRET_KEY = "FORNACE_SECRET_123"
ALGORITHM = "HS256"
ACCESS_EXPIRE_MINUTES = 60 * 24  # 24 horas


def hash_password(password: str):
    return pwd.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd.verify(plain, hashed)


def crear_token(data: dict):
    """
    Esperamos que 'data' contenga al menos: {"id": <user_id>}.
    get_current_user usa 'id' del payload.
    """
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None

