from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Esquema para el Token de respuesta
class Token(BaseModel):
    access_token: str
    token_type: str
    type_user: str

# Esquema para crear o validar un usuario en el JSON
class UserData(BaseModel):
    username: str
    password: str
    type_user: str  # 'admin' o 'user'

# Esquema para la respuesta de los mensajes del chat
class MessageResponse(BaseModel):
    id: int
    user_id: str
    content: str
    message_type: str = "text"
    timestamp: datetime
    is_deleted: bool

    class Config:
        from_attributes = True  # Permite a Pydantic leer modelos de SQLAlchemy
