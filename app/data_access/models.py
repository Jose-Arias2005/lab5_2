from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.data_access.database import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(150), nullable=False)
    industry = Column(String(100), nullable=False)
    original_photo_path = Column(String(300), nullable=True)
    selected_script_id = Column(Integer, ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True)
    video_path = Column(String(300), nullable=True)
    status = Column(String(50), default="CREATED", nullable=False)  # CREATED, SCRIPTS_GENERATED, MEDIA_GENERATED, PUBLISHED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    scripts = relationship("Script", back_populates="campaign", foreign_keys="Script.campaign_id", cascade="all, delete-orphan")
    selected_script = relationship("Script", foreign_keys=[selected_script_id], post_update=True)
    media_assets = relationship("MediaAsset", back_populates="campaign", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="campaign", cascade="all, delete-orphan")


class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    option_type = Column(String(10), nullable=False)  # 'A', 'B', 'C'
    title = Column(String(200), nullable=False)
    approach = Column(String(120), nullable=False)  # Dinámico/Viral, Profesional/Valor, Promocional/Urgencia
    hook = Column(String(300), nullable=False)
    narration = Column(Text, nullable=False)
    cta = Column(String(200), nullable=False)
    scene_prompts = Column(JSON, nullable=False)  # Lista de 3 prompts en inglés para Pollinations
    scene_subtitles = Column(JSON, nullable=False)  # Lista de 3 frases/subtítulos superpuestos
    is_selected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    campaign = relationship("Campaign", back_populates="scripts", foreign_keys=[campaign_id])


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String(50), nullable=False)  # ORIGINAL_PHOTO, GENERATED_IMAGE, GENERATED_VIDEO
    file_path = Column(String(300), nullable=False)
    scene_index = Column(Integer, nullable=True)  # 1, 2, 3 para las imágenes
    prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    campaign = relationship("Campaign", back_populates="media_assets")


class Publication(Base):
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), default="TIKTOK", nullable=False)
    publish_id = Column(String(150), nullable=False)
    status = Column(String(50), default="PUBLISHED", nullable=False)  # PUBLISHED, SIMULATED, FAILED
    response_payload = Column(JSON, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    campaign = relationship("Campaign", back_populates="publications")


class TikTokAuth(Base):
    __tablename__ = "tiktok_auth"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    open_id = Column(String(150), nullable=False)
    access_token = Column(String(500), nullable=False)
    refresh_token = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

