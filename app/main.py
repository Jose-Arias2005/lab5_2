import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.data_access.database import init_db
from app.presentation.routes import router

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("marketing_app.main")

# Inicialización de FastAPI
app = FastAPI(
    title="Marketing Automatizado con IA & TikTok",
    description="Generador automatizado de campañas de marketing multimedia con Gemini, Pollinations.ai y TikTok API",
    version="1.0.0"
)

# Montar archivos estáticos
STATIC_DIR = Path(__file__).resolve().parent / "presentation" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Incluir rutas de la aplicación
app.include_router(router)

@app.on_event("startup")
def startup_event():
    logger.info("Iniciando aplicación de Marketing Automatizado en el puerto %s...", settings.PORT)
    settings.ensure_directories()
    try:
        init_db()
        logger.info("Base de datos conectada e inicializada correctamente.")
    except Exception as e:
        logger.error("Error al inicializar la base de datos durante el inicio: %s", e)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "marketing-ai-tiktok",
        "sandbox_mode": settings.TIKTOK_SANDBOX_MODE,
        "gemini_model": settings.GEMINI_MODEL
    }

