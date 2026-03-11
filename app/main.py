import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import datetime, timezone
from fastapi.responses import RedirectResponse

from app import models, schemas, database, auth
from app.auth import get_current_user, get_current_admin, create_access_token, load_users, save_users
from jose import jwt, JWTError

# Crear las tablas en la base de datos (si no existen)
models.Base.metadata.create_all(bind=database.engine)

# Migración: añadir columna message_type si no existe (para DBs existentes)
with database.engine.connect() as _conn:
    try:
        _conn.execute(text("ALTER TABLE messages ADD COLUMN message_type VARCHAR DEFAULT 'text'"))
        _conn.commit()
    except Exception:
        pass  # La columna ya existe

# Directorio para audios
os.makedirs("static/audio", exist_ok=True)

app = FastAPI(title="Chat en Tiempo Real")

# Montar los archivos estáticos (Frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    # Redirige automáticamente la raíz hacia nuestro frontend
    return RedirectResponse(url="/static/index.html")

# --- Gestor de Conexiones WebSocket ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# --- Rutas de Autenticación y Usuarios ---

@app.post("/login", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    users = load_users()
    user = users.get(form_data.username)
    
    # Validación simple (en producción usar hashes)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer", "type_user": user["type_user"]}

@app.post("/users/")
async def create_user(user_data: schemas.UserData, current_admin: dict = Depends(get_current_admin)):
    users = load_users()
    if user_data.username in users:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    
    users[user_data.username] = {"password": user_data.password, "type_user": user_data.type_user}
    save_users(users)
    return {"msg": f"Usuario {user_data.username} creado exitosamente"}

@app.delete("/users/{username}")
async def delete_user(username: str, current_admin: dict = Depends(get_current_admin)):
    users = load_users()
    if username not in users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if username == current_admin["username"]:
        raise HTTPException(status_code=400, detail="No puedes borrarte a ti mismo")
        
    del users[username]
    save_users(users)
    return {"msg": f"Usuario {username} eliminado"}

# --- Rutas de Mensajes ---

@app.get("/messages/", response_model=List[schemas.MessageResponse])
async def get_messages(db: Session = Depends(database.get_db), current_user: dict = Depends(get_current_user)):
    # El admin ve todo, el usuario normal solo ve los no borrados
    if current_user.get("type_user") == "admin":
        messages = db.query(models.Message).all()
    else:
        messages = db.query(models.Message).filter(models.Message.is_deleted == False).all()
    return messages

@app.delete("/messages/{message_id}")
async def delete_message(message_id: int, db: Session = Depends(database.get_db), current_user: dict = Depends(get_current_user)):
    msg = db.query(models.Message).filter(models.Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    
    # Solo el creador o el admin pueden borrar
    if msg.user_id != current_user["username"] and current_user.get("type_user") != "admin":
        raise HTTPException(status_code=403, detail="No tienes permiso para borrar este mensaje")
    
    msg.is_deleted = True
    db.commit()
    # Notificar a los clientes que recarguen el chat
    await manager.broadcast({"type": "delete", "message_id": message_id})
    return {"msg": "Mensaje borrado lógicamente"}

# --- Audio ---

@app.post("/messages/audio")
async def upload_audio(
    audio: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: dict = Depends(get_current_user)
):
    filename = f"{uuid.uuid4()}.webm"
    filepath = f"static/audio/{filename}"
    content = await audio.read()
    with open(filepath, "wb") as f:
        f.write(content)

    new_msg = models.Message(
        user_id=current_user["username"],
        content=f"/static/audio/{filename}",
        message_type="audio",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    await manager.broadcast({
        "type": "message",
        "id": new_msg.id,
        "user_id": current_user["username"],
        "content": f"/static/audio/{filename}",
        "message_type": "audio",
        "timestamp": new_msg.timestamp.isoformat(),
        "is_deleted": False
    })
    return {"msg": "Audio enviado"}

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...), db: Session = Depends(database.get_db)):
    # Autenticación del WebSocket mediante el token en la URL
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            # Guardar en base de datos
            new_msg = models.Message(user_id=username, content=data, timestamp=datetime.now(timezone.utc))
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)
            
            # Formatear y emitir el mensaje a todos
            msg_data = {
                "type": "message",
                "id": new_msg.id,
                "user_id": username,
                "content": data,
                "message_type": "text",
                "timestamp": new_msg.timestamp.isoformat(),
                "is_deleted": False
            }
            await manager.broadcast(msg_data)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)