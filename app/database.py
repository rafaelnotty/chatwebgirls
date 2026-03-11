from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Crea un archivo chat.db en la raíz del proyecto
SQLALCHEMY_DATABASE_URL = "sqlite:///./chat.db"

# connect_args solo es necesario para SQLite en FastAPI para permitir múltiples hilos
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para inyectar la sesión de la BD en las rutas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
