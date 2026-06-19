import json
import logging
import datetime
from sqlalchemy.orm import Session
from src.database.models import Analytics, Campaign
from src.cache.redis_cache import cache

logger = logging.getLogger("adsphere.analytics.processor")

def process_impression(campaign_id: int, db: Session):
    """
    Processes an impression event.
    Inserts/updates the Analytics table and syncs the cache.
    """
    logger.info(f"Processing IMPRESSION event for Campaign ID: {campaign_id}")
    
    # Simulate Kafka production (Publish event to system logs)
    mock_kafka_publish("impression", {"campaign_id": campaign_id, "timestamp": str(datetime.datetime.utcnow())})

    # Add transaction in Analytics table
    # We aggregate analytics by date to keep table size optimized
    today = datetime.date.today()
    start_of_day = datetime.datetime.combine(today, datetime.time.min)
    
    analytics_record = db.query(Analytics).filter(
        Analytics.campaign_id == campaign_id,
        Analytics.timestamp >= start_of_day
    ).first()
    
    if not analytics_record:
        analytics_record = Analytics(
            campaign_id=campaign_id,
            impressions=1,
            clicks=0,
            revenue=0.0
        )
        db.add(analytics_record)
    else:
        analytics_record.impressions += 1
        
    db.commit()

    # Update cache stats to ensure CTR calculations are updated instantly
    update_campaign_stats_cache(campaign_id, db)


def process_click(campaign_id: int, db: Session):
    """
    Processes a click event.
    Updates click count, logs revenue, and syncs the cache.
    """
    logger.info(f"Processing CLICK event for Campaign ID: {campaign_id}")
    
    # Simulate Kafka production
    mock_kafka_publish("click", {"campaign_id": campaign_id, "timestamp": str(datetime.datetime.utcnow())})

    # Find campaign to check bid_amount for revenue logging
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    revenue_increment = campaign.bid_amount if campaign else 0.0

    today = datetime.date.today()
    start_of_day = datetime.datetime.combine(today, datetime.time.min)
    
    analytics_record = db.query(Analytics).filter(
        Analytics.campaign_id == campaign_id,
        Analytics.timestamp >= start_of_day
    ).first()
    
    if not analytics_record:
        analytics_record = Analytics(
            campaign_id=campaign_id,
            impressions=1, # assume at least 1 impression if they clicked
            clicks=1,
            revenue=revenue_increment
        )
        db.add(analytics_record)
    else:
        analytics_record.clicks += 1
        analytics_record.revenue = float(analytics_record.revenue) + revenue_increment
        
    db.commit()

    # Update cache stats
    update_campaign_stats_cache(campaign_id, db)


def update_campaign_stats_cache(campaign_id: int, db: Session):
    """Recalculates impressions/clicks and updates cache."""
    analytics_records = db.query(Analytics).filter(Analytics.campaign_id == campaign_id).all()
    total_impressions = sum(r.impressions for r in analytics_records)
    total_clicks = sum(r.clicks for r in analytics_records)
    
    stats_key = f"campaign:stats:{campaign_id}"
    cache.set(
        stats_key,
        json.dumps({"impressions": total_impressions, "clicks": total_clicks}),
        expire_seconds=120
    )


def mock_kafka_publish(topic: str, message: dict):
    """Simulates publishing events to a high-throughput message streaming queue (like Kafka)"""
    logger.info(f"[MOCK KAFKA PRODUCER] Published to topic '{topic}': {json.dumps(message)}")
