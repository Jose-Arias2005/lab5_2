import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("marketing_app.database")

Base = declarative_base()

def get_engine():
    db_url = settings.DATABASE_URL
    max_retries = 5
    retry_delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=10,
                max_overflow=20
            )
            # Test connection
            with engine.connect() as conn:
                logger.info("Conexión exitosa a PostgreSQL: %s:%s/%s", settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)
                return engine
        except Exception as e:
            logger.warning("Intento %s/%s de conexión a PostgreSQL falló: %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error("No se pudo conectar a PostgreSQL tras %s intentos. Usando SQLite de respaldo local para desarrollo continuo.", max_retries)
                return create_engine("sqlite:///./fallback_marketing.db", connect_args={"check_same_thread": False})

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.data_access.models import Campaign, Script, MediaAsset, Publication, TikTokAuth
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas de base de datos inicializadas correctamente.")
    except Exception as e:
        logger.error("Error al inicializar tablas en la base de datos: %s", e)
        raise e

