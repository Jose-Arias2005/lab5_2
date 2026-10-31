import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server Configuration
    PORT: int = int(os.getenv("PORT", "8001"))
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # TikTok Integration Configuration
    TIKTOK_CLIENT_KEY: str = os.getenv("TIKTOK_CLIENT_KEY", "")
    TIKTOK_CLIENT_SECRET: str = os.getenv("TIKTOK_CLIENT_SECRET", "")
    TIKTOK_REDIRECT_URI: str = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8001/auth/tiktok/callback")
    TIKTOK_SANDBOX_MODE: bool = os.getenv("TIKTOK_SANDBOX_MODE", "true").lower() in ("true", "1", "yes")
    
    # Database Configuration
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_NAME: str = os.getenv("DB_NAME", "marketing_db")
    DB_HOST: str = os.getenv("DB_HOST", "db")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    
    # Base Media Directory Path (supports container /app/media or local development)
    MEDIA_DIR: Path = Path(os.getenv("MEDIA_DIR", "/app/media" if os.path.exists("/app") else "./app/media")).resolve()

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def UPLOADS_DIR(self) -> Path:
        return self.MEDIA_DIR / "uploads"

    @property
    def GENERATED_IMAGES_DIR(self) -> Path:
        return self.MEDIA_DIR / "generated_images"

    @property
    def VIDEOS_DIR(self) -> Path:
        return self.MEDIA_DIR / "videos"

    def ensure_directories(self):
        """Asegura que los directorios de almacenamiento multimedia existan con permisos adecuados."""
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        self.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
settings.ensure_directories()

