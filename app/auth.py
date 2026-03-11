import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# Configuración JWT (En producción, el SECRET_KEY debe ir en variables de entorno)
SECRET_KEY = "clave_secreta_super_segura_para_el_chat_reemplazar_luego"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # El token durará 1 día

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
USERS_FILE = "users.json"

# --- Funciones para manejar el JSON ---

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# --- Funciones de JWT ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependencias de FastAPI ---

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    users = load_users()
    if username not in users:
        raise credentials_exception
    
    # Retornamos un diccionario con los datos útiles del usuario
    return {"username": username, "type_user": users[username].get("type_user")}

async def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("type_user") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Privilegios insuficientes. Se requiere rol de administrador."
        )
    return current_user
