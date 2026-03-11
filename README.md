# ChatWebGirls

Chat en tiempo real con WebSockets, mensajes de voz y selector de emojis.

## Stack

- **Backend**: FastAPI + Uvicorn/Gunicorn
- **Base de datos**: SQLite (mensajes) + JSON (usuarios)
- **Frontend**: HTML/CSS/JS vanilla
- **Tiempo real**: WebSockets nativos de FastAPI

## Características

- Mensajes de texto en tiempo real con broadcast a todos los conectados
- Grabación y envío de mensajes de voz (WebM) directamente desde el navegador
- Selector de emojis integrado
- Autenticación JWT (token en header para HTTP, query param para WebSocket)
- Dos roles: `user` y `admin`
  - El admin ve y escucha todos los mensajes incluso los eliminados
  - Los usuarios solo pueden borrar sus propios mensajes
  - Borrado lógico: los mensajes nunca se eliminan físicamente

## Instalación

```bash
git clone https://github.com/rafaelnotty/chatwebgirls.git
cd chatwebgirls
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Disponible en `http://localhost:8001`

## Producción (systemd)

```ini
[Unit]
Description=Aplicacion Web de Chat FastAPI
After=network.target

[Service]
User=orangepi
WorkingDirectory=/home/orangepi/chat_app
Environment="PATH=/home/orangepi/chat_app/venv/bin"
ExecStart=/home/orangepi/chat_app/venv/bin/gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
Restart=always

[Install]
WantedBy=multi-user.target
```

## Estructura

```
chat_app/
├── app/
│   ├── main.py       # Rutas, WebSocket, endpoint de audio
│   ├── auth.py       # JWT, dependencias de autenticación
│   ├── models.py     # Modelo SQLAlchemy (Message)
│   ├── schemas.py    # Modelos Pydantic
│   └── database.py   # Configuración SQLite
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── users.json        # Usuarios y contraseñas
└── run.py            # Arranque local con uvicorn
```
