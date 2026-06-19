import logging
from sqlalchemy.orm import Session
from src.database.models import Campaign
from src.cache.redis_cache import cache

logger = logging.getLogger("adsphere.bidding.budget")

BUDGET_KEY_PREFIX = "campaign:budget"
SPEND_KEY_PREFIX = "campaign:spend"

def get_campaign_budget_and_spend(campaign_id: int, db: Session) -> tuple[float, float]:
    """
    Retrieves total budget and current spend for a campaign.
    Checks cache first, queries DB and caches if cache miss.
    """
    budget_key = f"{BUDGET_KEY_PREFIX}:{campaign_id}"
    spend_key = f"{SPEND_KEY_PREFIX}:{campaign_id}"
    
    budget_cached = cache.get(budget_key)
    spend_cached = cache.get(spend_key)
    
    if budget_cached is not None and spend_cached is not None:
        return float(budget_cached), float(spend_cached)
        
    # Cache miss - fetch from DB
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return 0.0, 0.0
        
    # Sync back to cache (keep for 1 hour/3600s or until updated)
    cache.set(budget_key, campaign.budget, expire_seconds=3600)
    cache.set(spend_key, campaign.current_spend, expire_seconds=3600)
    
    return campaign.budget, campaign.current_spend

def has_budget(campaign_id: int, bid_amount: float, db: Session) -> bool:
    """Checks if a campaign has sufficient remaining budget to place a bid."""
    budget, spend = get_campaign_budget_and_spend(campaign_id, db)
    return (spend + bid_amount) <= budget

def deduct_budget(campaign_id: int, bid_amount: float, db: Session) -> bool:
    """
    Atomically records and deducts the winning bid amount from the campaign budget.
    Updates the cache and database.
    """
    budget_key = f"{BUDGET_KEY_PREFIX}:{campaign_id}"
    spend_key = f"{SPEND_KEY_PREFIX}:{campaign_id}"
    
    # 1. Increment spend in cache atomically
    new_spend = cache.incr_by_float(spend_key, bid_amount)
    
    # Get budget from cache/DB to verify safety limits
    budget, _ = get_campaign_budget_and_spend(campaign_id, db)
    
    # 2. Update Database Campaign object
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign:
        campaign.current_spend = float(campaign.current_spend) + bid_amount
        if campaign.current_spend >= campaign.budget:
            campaign.is_active = False
            # Clear or update cache active status
            cache.delete(f"campaign:active:{campaign_id}")
            logger.info(f"Campaign {campaign_id} has exhausted its budget. Marked inactive.")
        
        db.commit()
        db.refresh(campaign)
        
        # Keep cache updated with DB actual value to prevent drift
        cache.set(spend_key, campaign.current_spend, expire_seconds=3600)
        return True
    
    # If campaign was not found in DB, roll back cache increment
    cache.incr_by_float(spend_key, -bid_amount)
    return False

def reset_campaign_cache(campaign_id: int, budget: float, spend: float):
    """Resets cache parameters when campaign is edited/created."""
    cache.set(f"{BUDGET_KEY_PREFIX}:{campaign_id}", budget, expire_seconds=3600)
    cache.set(f"{SPEND_KEY_PREFIX}:{campaign_id}", spend, expire_seconds=3600)
    cache.delete(f"campaign:active:{campaign_id}")
