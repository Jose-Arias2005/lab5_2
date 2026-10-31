from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.data_access.models import Campaign, Script, MediaAsset, Publication, TikTokAuth

class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, company_name: str, industry: str, original_photo_path: Optional[str] = None) -> Campaign:
        campaign = Campaign(
            company_name=company_name,
            industry=industry,
            original_photo_path=original_photo_path,
            status="CREATED"
        )
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def get_by_id(self, campaign_id: int) -> Optional[Campaign]:
        return self.db.query(Campaign).filter(Campaign.id == campaign_id).first()

    def list_all(self) -> List[Campaign]:
        return self.db.query(Campaign).order_by(Campaign.created_at.desc()).all()

    def update_status(self, campaign_id: int, status: str) -> Optional[Campaign]:
        campaign = self.get_by_id(campaign_id)
        if campaign:
            campaign.status = status
            self.db.commit()
            self.db.refresh(campaign)
        return campaign

    def set_selected_script(self, campaign_id: int, script_id: int) -> Optional[Campaign]:
        campaign = self.get_by_id(campaign_id)
        if campaign:
            campaign.selected_script_id = script_id
            self.db.commit()
            self.db.refresh(campaign)
        return campaign

    def update_video_path(self, campaign_id: int, video_path: str) -> Optional[Campaign]:
        campaign = self.get_by_id(campaign_id)
        if campaign:
            campaign.video_path = video_path
            campaign.status = "MEDIA_GENERATED"
            self.db.commit()
            self.db.refresh(campaign)
        return campaign


class ScriptRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_batch(self, campaign_id: int, scripts_data: List[Dict[str, Any]]) -> List[Script]:
        scripts = []
        for item in scripts_data:
            script = Script(
                campaign_id=campaign_id,
                option_type=item.get("option_type", "A"),
                title=item.get("title", ""),
                approach=item.get("approach", ""),
                hook=item.get("hook", ""),
                narration=item.get("narration", ""),
                cta=item.get("cta", ""),
                scene_prompts=item.get("scene_prompts", []),
                scene_subtitles=item.get("scene_subtitles", []),
                is_selected=False
            )
            self.db.add(script)
            scripts.append(script)
        self.db.commit()
        for s in scripts:
            self.db.refresh(s)
        return scripts

    def get_by_id(self, script_id: int) -> Optional[Script]:
        return self.db.query(Script).filter(Script.id == script_id).first()

    def get_by_campaign(self, campaign_id: int) -> List[Script]:
        return self.db.query(Script).filter(Script.campaign_id == campaign_id).order_by(Script.option_type.asc()).all()

    def mark_selected(self, campaign_id: int, script_id: int) -> Optional[Script]:
        # Reset previous selections for the campaign
        self.db.query(Script).filter(Script.campaign_id == campaign_id).update({"is_selected": False})
        selected = self.get_by_id(script_id)
        if selected and selected.campaign_id == campaign_id:
            selected.is_selected = True
            self.db.commit()
            self.db.refresh(selected)
            return selected
        return None


class MediaAssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_asset(self, campaign_id: int, asset_type: str, file_path: str,
                  scene_index: Optional[int] = None, prompt: Optional[str] = None) -> MediaAsset:
        asset = MediaAsset(
            campaign_id=campaign_id,
            asset_type=asset_type,
            file_path=file_path,
            scene_index=scene_index,
            prompt=prompt
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def get_by_campaign(self, campaign_id: int) -> List[MediaAsset]:
        return self.db.query(MediaAsset).filter(MediaAsset.campaign_id == campaign_id).order_by(MediaAsset.scene_index.asc().nullsfirst()).all()


class PublicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_publication(self, campaign_id: int, platform: str, publish_id: str,
                           status: str, response_payload: Optional[Dict[str, Any]] = None) -> Publication:
        publication = Publication(
            campaign_id=campaign_id,
            platform=platform,
            publish_id=publish_id,
            status=status,
            response_payload=response_payload
        )
        self.db.add(publication)
        self.db.commit()
        self.db.refresh(publication)
        return publication

    def get_by_campaign(self, campaign_id: int) -> List[Publication]:
        return self.db.query(Publication).filter(Publication.campaign_id == campaign_id).order_by(Publication.published_at.desc()).all()

    def get_latest_by_campaign(self, campaign_id: int) -> Optional[Publication]:
        return self.db.query(Publication).filter(Publication.campaign_id == campaign_id).order_by(Publication.published_at.desc()).first()


class TikTokAuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_auth(self, open_id: str, access_token: str, refresh_token: Optional[str] = None, expires_at: Optional[Any] = None) -> TikTokAuth:
        auth = TikTokAuth(
            open_id=open_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        self.db.add(auth)
        self.db.commit()
        self.db.refresh(auth)
        return auth

    def get_latest(self) -> Optional[TikTokAuth]:
        return self.db.query(TikTokAuth).order_by(TikTokAuth.created_at.desc()).first()

