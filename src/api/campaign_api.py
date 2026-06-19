import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database.postgres import get_db
from src.database.models import Campaign
from src.schemas.campaign import CampaignCreate, CampaignResponse
from src.bidding.budget_manager import reset_campaign_cache

router = APIRouter(prefix="/campaign", tags=["Campaigns"])

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(request: CampaignCreate, db: Session = Depends(get_db)):
    """Creates a new advertising campaign and initializes its cache settings."""
    campaign = Campaign(
        name=request.name,
        advertiser=request.advertiser,
        budget=request.budget,
        current_spend=0.0,
        bid_amount=request.bid_amount,
        target_age_min=request.target_age_min,
        target_age_max=request.target_age_max,
        target_location=request.target_location,
        target_interests=json.dumps(request.target_interests),
        ad_title=request.ad_title,
        ad_body=request.ad_body,
        ad_creative_url=request.ad_creative_url,
        is_active=True
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Initialize budget and spend parameters in cache
    reset_campaign_cache(campaign.id, campaign.budget, campaign.current_spend)

    return campaign

@router.get("s", response_model=List[CampaignResponse])
def get_campaigns(db: Session = Depends(get_db)):
    """Retrieves all advertising campaigns in the system."""
    return db.query(Campaign).all()

@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Retrieves a single campaign by its ID."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign ID {campaign_id} not found")
    return campaign

@router.put("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(campaign_id: int, request: CampaignCreate, db: Session = Depends(get_db)):
    """Updates campaign parameters and resets cached values."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign ID {campaign_id} not found")

    campaign.name = request.name
    campaign.advertiser = request.advertiser
    campaign.budget = request.budget
    campaign.bid_amount = request.bid_amount
    campaign.target_age_min = request.target_age_min
    campaign.target_age_max = request.target_age_max
    campaign.target_location = request.target_location
    campaign.target_interests = json.dumps(request.target_interests)
    campaign.ad_title = request.ad_title
    campaign.ad_body = request.ad_body
    campaign.ad_creative_url = request.ad_creative_url
    
    # Reactivate if budget is increased above spend
    if campaign.current_spend < campaign.budget:
        campaign.is_active = True

    db.commit()
    db.refresh(campaign)

    # Refresh cached budget configuration
    reset_campaign_cache(campaign.id, campaign.budget, campaign.current_spend)

    return campaign