import logging
from fastapi import APIRouter, Depends, BackgroundTasks, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from src.database.postgres import get_db
from src.database.models import Campaign, User, BidHistory, FraudLog, Analytics
from src.schemas.auction import BidRequest, BidResponse
from src.bidding.bidding_engine import run_auction as execute_auction
from src.analytics.analytics_processor import process_impression, process_click

router = APIRouter(tags=["RTB Auction & Analytics"])
logger = logging.getLogger("adsphere.api.auction")

# 1x1 pixel transparent GIF binary content
TRANSPARENT_1X1_GIF = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'


@router.post("/auction/request", response_model=BidResponse)
def auction_request(request: BidRequest, db: Session = Depends(get_db)):
    """
    Receives a real-time bid request from a publisher webpage.
    Executes the auction and returns the winning ad.
    """
    logger.info(f"Incoming bid request from IP {request.ip_address} for user {request.user_id}")
    response = execute_auction(request, db)
    return response


@router.get("/analytics/impression/{campaign_id}/{user_id}")
def track_impression_pixel(campaign_id: int, user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Asynchronous tracking pixel endpoint for impressions.
    Fires on ad load and returns a transparent 1x1 tracking GIF.
    """
    background_tasks.add_task(process_impression, campaign_id, db)
    return Response(content=TRANSPARENT_1X1_GIF, media_type="image/gif")


@router.get("/analytics/click/{campaign_id}/{user_id}")
def track_click_redirect(campaign_id: int, user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Asynchronous tracker endpoint for clicks.
    Fires when a user clicks the ad, logs analytics, and redirects to the creative landing page.
    """
    background_tasks.add_task(process_click, campaign_id, db)
    
    # Fetch campaign to redirect to its creative landing page, or default fallback
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    destination_url = "https://www.google.com" # default fallback
    
    if campaign:
        # If it's a mock url, redirect to a mock destination, otherwise use the url
        if campaign.ad_creative_url and campaign.ad_creative_url.startswith("http"):
            # Redirect to the creative or a placeholder
            destination_url = campaign.ad_creative_url
            
    # Redirect with temporary redirect code
    return RedirectResponse(url=destination_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/analytics/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    """
    Returns high-level aggregate analytics: impressions, clicks, CTR, and revenue.
    Includes campaign-specific metrics.
    """
    # 1. Total Metrics
    totals = db.query(
        func.sum(Analytics.impressions).label("total_impressions"),
        func.sum(Analytics.clicks).label("total_clicks"),
        func.sum(Analytics.revenue).label("total_revenue")
    ).first()

    total_impressions = totals.total_impressions or 0
    total_clicks = totals.total_clicks or 0
    total_revenue = totals.total_revenue or 0.0
    
    ctr = (total_clicks / total_impressions) if total_impressions > 0 else 0.0

    # 2. Campaign breakdown
    campaigns = db.query(Campaign).all()
    campaign_breakdown = []
    
    for camp in campaigns:
        # Sum analytics records for this campaign
        camp_stats = db.query(
            func.sum(Analytics.impressions).label("impressions"),
            func.sum(Analytics.clicks).label("clicks"),
            func.sum(Analytics.revenue).label("revenue")
        ).filter(Analytics.campaign_id == camp.id).first()

        camp_impressions = camp_stats.impressions or 0
        camp_clicks = camp_stats.clicks or 0
        camp_revenue = camp_stats.revenue or 0.0
        camp_ctr = (camp_clicks / camp_impressions) if camp_impressions > 0 else 0.0

        campaign_breakdown.append({
            "campaign_id": camp.id,
            "campaign_name": camp.name,
            "advertiser": camp.advertiser,
            "budget": camp.budget,
            "current_spend": camp.current_spend,
            "bid_amount": camp.bid_amount,
            "is_active": camp.is_active,
            "impressions": camp_impressions,
            "clicks": camp_clicks,
            "ctr": round(camp_ctr, 4),
            "revenue": round(camp_revenue, 2)
        })

    return {
        "aggregate": {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": round(ctr, 4),
            "revenue": round(total_revenue, 2)
        },
        "campaigns": campaign_breakdown
    }


@router.get("/history")
def get_auction_history(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieves the recent auction history log."""
    history = db.query(BidHistory).order_by(BidHistory.timestamp.desc()).limit(limit).all()
    
    result = []
    for log in history:
        # Fetch name details
        camp_name = "N/A"
        advertiser = "N/A"
        if log.campaign_id:
            camp = db.query(Campaign).filter(Campaign.id == log.campaign_id).first()
            if camp:
                camp_name = camp.name
                advertiser = camp.advertiser
                
        user_name = "N/A"
        if log.user_id:
            usr = db.query(User).filter(User.id == log.user_id).first()
            if usr:
                user_name = usr.name

        result.append({
            "id": log.id,
            "campaign_id": log.campaign_id,
            "campaign_name": camp_name,
            "advertiser": advertiser,
            "user_id": log.user_id,
            "user_name": user_name,
            "bid_amount": log.bid_amount,
            "score": round(log.score, 4),
            "status": log.status,
            "reason": log.reason,
            "timestamp": log.timestamp.isoformat()
        })
    return result


@router.get("/fraud")
def get_fraud_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieves recent fraud attempts and rate-limit violations."""
    logs = db.query(FraudLog).order_by(FraudLog.timestamp.desc()).limit(limit).all()
    
    result = []
    for log in logs:
        user_name = "N/A"
        if log.user_id:
            usr = db.query(User).filter(User.id == log.user_id).first()
            if usr:
                user_name = usr.name
                
        result.append({
            "id": log.id,
            "ip_address": log.ip_address,
            "user_id": log.user_id,
            "user_name": user_name,
            "reason": log.reason,
            "score": log.score,
            "timestamp": log.timestamp.isoformat()
        })
    return result
