# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar la aplicación
python run.py
# Escucha en http://0.0.0.0:8001 con reload automático
```

## Arquitectura

Aplicación de chat en tiempo real con FastAPI + WebSockets. Frontend vanilla HTML/JS servido como archivos estáticos por el propio FastAPI.

### Almacenamiento dual

- **Usuarios**: `users.json` en la raíz del proyecto (no en la base de datos). Gestionado con `load_users()`/`save_users()` en `app/auth.py`. Contiene username, password en texto plano, y `type_user` (`admin` o `user`).
- **Mensajes**: SQLite en `chat.db` vía SQLAlchemy. El modelo `Message` (`app/models.py`) usa borrado lógico: el campo `is_deleted` se pone a `True` en lugar de eliminar la fila. Campo `message_type` indica `"text"` o `"audio"`.
- **Audios**: archivos `.webm` guardados en `static/audio/` (generados con UUID). El campo `content` del mensaje contiene la URL `/static/audio/<uuid>.webm`. Al arrancar, `main.py` crea el directorio si no existe.

### Autenticación

JWT con `python-jose`. El token se genera en `/login` y se usa de dos formas:
- HTTP: cabecera `Authorization: Bearer <token>` via `OAuth2PasswordBearer`
- WebSocket: parámetro de query `?token=<token>` (el WebSocket no soporta cabeceras personalizadas)

Las dependencias `get_current_user` y `get_current_admin` están en `app/auth.py` y se inyectan en las rutas.

### WebSocket y broadcast

`ConnectionManager` en `app/main.py` mantiene la lista de conexiones activas. Al recibir un mensaje por WebSocket, lo persiste en SQLite y hace broadcast a todos los clientes conectados como JSON con `type: "message"`. Los borrados se notifican con `type: "delete"`.

### Roles

- `user`: ve solo mensajes no borrados, puede borrar sus propios mensajes
- `admin`: ve todos los mensajes (incluyendo borrados), puede borrar cualquier mensaje, puede crear/eliminar usuarios (via panel en el frontend)
