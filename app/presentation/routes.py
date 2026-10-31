import os
import shutil
import time
from pathlib import Path
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.data_access.database import get_db
from app.data_access.repositories import (
    CampaignRepository,
    ScriptRepository,
    MediaAssetRepository,
    PublicationRepository,
    TikTokAuthRepository
)
from app.business_logic.script_service import ScriptService
from app.business_logic.media_service import MediaService
from app.business_logic.tiktok_service import TikTokService

router = APIRouter()

# Configuración del motor de plantillas Jinja2
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Función auxiliar para convertir rutas absolutas de archivo a URLs relativas del navegador
def get_media_url(file_path: str) -> str:
    if not file_path:
        return ""
    p = Path(file_path)
    try:
        # Extraer la ruta relativa respecto a MEDIA_DIR
        rel = p.relative_to(settings.MEDIA_DIR)
        return f"/media/{rel.as_posix()}"
    except ValueError:
        # Si no es relativo directo, buscar nombre de carpeta contenedora
        parts = p.parts
        if "media" in parts:
            idx = parts.index("media")
            return "/" + "/".join(parts[idx:])
        return f"/media/{p.name}"

templates.env.filters["media_url"] = get_media_url


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Página principal: formulario de recepción de foto, empresa y rubro."""
    campaign_repo = CampaignRepository(db)
    recent_campaigns = campaign_repo.list_all()[:4]
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"recent_campaigns": recent_campaigns, "settings": settings}
    )


@router.post("/campaigns/create")
async def create_campaign(
    request: Request,
    company_name: str = Form(...),
    industry: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    1. Recepción de fotografía, nombre y rubro.
    2. Almacenamiento en /app/media/uploads/.
    3. Generación de las 3 propuestas de guiones con Gemini (o fallback).
    """
    campaign_repo = CampaignRepository(db)
    script_repo = ScriptRepository(db)
    asset_repo = MediaAssetRepository(db)

    # 1. Guardar la fotografía subida
    filename = f"original_{int(time.time())}_{photo.filename}"
    upload_path = settings.UPLOADS_DIR / filename
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    # 2. Crear registro de campaña
    campaign = campaign_repo.create(
        company_name=company_name.strip(),
        industry=industry.strip(),
        original_photo_path=str(upload_path)
    )

    asset_repo.add_asset(
        campaign_id=campaign.id,
        asset_type="ORIGINAL_PHOTO",
        file_path=str(upload_path)
    )

    # 3. Generar 3 guiones con IA Gemini (con fallback local automático)
    scripts_data = ScriptService.generate_scripts(company_name.strip(), industry.strip())
    script_repo.create_batch(campaign.id, scripts_data)
    campaign_repo.update_status(campaign.id, "SCRIPTS_GENERATED")

    # Redirigir a la pantalla de selección de guion
    return RedirectResponse(
        url=f"/campaigns/{campaign.id}/select-script",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/campaigns/{campaign_id}/select-script", response_class=HTMLResponse)
def select_script_view(campaign_id: int, request: Request, db: Session = Depends(get_db)):
    """Muestra las 3 opciones de guiones (A, B y C) para selección interactiva del usuario."""
    campaign_repo = CampaignRepository(db)
    script_repo = ScriptRepository(db)

    campaign = campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    scripts = script_repo.get_by_campaign(campaign_id)
    return templates.TemplateResponse(
        request=request,
        name="select_script.html",
        context={"campaign": campaign, "scripts": scripts}
    )


@router.post("/campaigns/{campaign_id}/select-script")
def select_script_action(
    campaign_id: int,
    script_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Procesa la selección del guion e inicia la generación multimedia:
    - 3 imágenes verticales con Pollinations.ai.
    - 1 video MP4 vertical (9:16) con MoviePy/FFmpeg y subtítulos superpuestos.
    """
    campaign_repo = CampaignRepository(db)
    script_repo = ScriptRepository(db)
    asset_repo = MediaAssetRepository(db)

    campaign = campaign_repo.get_by_id(campaign_id)
    script = script_repo.get_by_id(script_id)
    if not campaign or not script:
        raise HTTPException(status_code=404, detail="Campaña o guion no encontrado")

    # Marcar guion seleccionado
    script_repo.mark_selected(campaign_id, script_id)
    campaign_repo.set_selected_script(campaign_id, script_id)

    # Generación multimedia
    script_dict = {
        "scene_prompts": script.scene_prompts,
        "scene_subtitles": script.scene_subtitles,
        "title": script.title,
        "narration": script.narration
    }

    image_paths, video_path = MediaService.generate_campaign_media(
        campaign_id=campaign.id,
        script_data=script_dict,
        company_name=campaign.company_name
    )

    # Registrar assets multimedia en BD
    for idx, img_path in enumerate(image_paths):
        prompt_used = script.scene_prompts[idx] if idx < len(script.scene_prompts) else ""
        asset_repo.add_asset(
            campaign_id=campaign.id,
            asset_type="GENERATED_IMAGE",
            file_path=img_path,
            scene_index=idx + 1,
            prompt=prompt_used
        )

    asset_repo.add_asset(
        campaign_id=campaign.id,
        asset_type="GENERATED_VIDEO",
        file_path=video_path
    )

    campaign_repo.update_video_path(campaign.id, video_path)

    return RedirectResponse(
        url=f"/campaigns/{campaign.id}/view",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/campaigns/{campaign_id}/view", response_class=HTMLResponse)
def view_campaign(campaign_id: int, request: Request, published: bool = False, db: Session = Depends(get_db)):
    """Vista detallada de la campaña: guion elegido, 3 imágenes, video vertical y panel de TikTok."""
    campaign_repo = CampaignRepository(db)
    asset_repo = MediaAssetRepository(db)
    pub_repo = PublicationRepository(db)

    campaign = campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    assets = asset_repo.get_by_campaign(campaign_id)
    generated_images = [a for a in assets if a.asset_type == "GENERATED_IMAGE"]
    publication = pub_repo.get_latest_by_campaign(campaign_id)

    return templates.TemplateResponse(
        request=request,
        name="view_campaign.html",
        context={
            "campaign": campaign,
            "selected_script": campaign.selected_script,
            "generated_images": generated_images,
            "publication": publication,
            "published_just_now": published,
            "settings": settings
        }
    )


@router.post("/campaigns/{campaign_id}/publish/tiktok")
def publish_to_tiktok(campaign_id: int, db: Session = Depends(get_db)):
    """
    Publica el video en TikTok Content Posting API v2.
    Soporta TIKTOK_SANDBOX_MODE=true o fallback automático con guardado en PostgreSQL.
    """
    campaign_repo = CampaignRepository(db)
    pub_repo = PublicationRepository(db)
    auth_repo = TikTokAuthRepository(db)

    campaign = campaign_repo.get_by_id(campaign_id)
    if not campaign or not campaign.video_path:
        raise HTTPException(status_code=400, detail="La campaña no posee un video generado válido")

    latest_auth = auth_repo.get_latest()
    access_token = latest_auth.access_token if latest_auth else None

    # Publicación
    title = f"{campaign.company_name} - {campaign.selected_script.title if campaign.selected_script else 'Campaña Viral'}"
    result = TikTokService.publish_video(
        video_path=campaign.video_path,
        title=title,
        access_token=access_token
    )

    # Persistir registro de publicación en PostgreSQL
    pub = pub_repo.create_publication(
        campaign_id=campaign.id,
        platform="TIKTOK",
        publish_id=result.get("publish_id", "pub_unknown"),
        status=result.get("status", "PUBLISHED"),
        response_payload=result
    )

    campaign_repo.update_status(campaign.id, "PUBLISHED")

    return RedirectResponse(
        url=f"/campaigns/{campaign.id}/view?published=true",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/campaigns/history", response_class=HTMLResponse)
def history_view(request: Request, auth_success: bool = False, db: Session = Depends(get_db)):
    """Historial completo de campañas, videos y estado en redes sociales."""
    campaign_repo = CampaignRepository(db)
    campaigns = campaign_repo.list_all()
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"campaigns": campaigns, "auth_success": auth_success, "settings": settings}
    )


@router.get("/auth/tiktok/login")
def tiktok_login():
    """Inicia el flujo de autenticación OAuth 2.0 con TikTok."""
    auth_url = TikTokService.get_authorization_url()
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/auth/tiktok/callback")
def tiktok_callback(code: str = "demo_code", state: str = "", db: Session = Depends(get_db)):
    """Callback OAuth 2.0 de TikTok: intercambia el code y persiste en BD."""
    auth_repo = TikTokAuthRepository(db)
    token_data = TikTokService.exchange_code_for_token(code)

    auth_repo.save_auth(
        open_id=token_data.get("open_id", "demo_open_id"),
        access_token=token_data.get("access_token", "demo_token"),
        refresh_token=token_data.get("refresh_token")
    )

    return RedirectResponse(url="/campaigns/history?auth_success=true", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/media/{subpath:path}")
def serve_media_file(subpath: str):
    """Sirve archivos multimedia locales (imágenes y videos MP4) con cabeceras de streaming."""
    target_file = (settings.MEDIA_DIR / subpath).resolve()
    if not target_file.exists() or not str(target_file).startswith(str(settings.MEDIA_DIR)):
        raise HTTPException(status_code=404, detail="Archivo multimedia no encontrado")

    media_type = "video/mp4" if target_file.suffix == ".mp4" else "image/jpeg"
    return FileResponse(path=str(target_file), media_type=media_type)

