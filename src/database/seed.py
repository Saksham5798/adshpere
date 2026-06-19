import json
import logging
from sqlalchemy.orm import Session
from src.database.models import Campaign, User, Analytics
from src.bidding.budget_manager import reset_campaign_cache
from src.cache.redis_cache import cache

logger = logging.getLogger("adsphere.database.seed")

def seed_data(db: Session):
    """
    Populates the database with initial mock campaigns and user profiles
    if the database is currently empty.
    """
    # 1. Seed campaigns
    if db.query(Campaign).count() == 0:
        logger.info("Database is empty of campaigns. Seeding default campaigns...")
        campaigns = [
            Campaign(
                name="AdSphere Premium Tech Launch",
                advertiser="AppleCorp",
                budget=1500.0,
                current_spend=0.0,
                bid_amount=3.50,
                target_age_min=18,
                target_age_max=45,
                target_location="Mumbai",
                target_interests=json.dumps(["Technology", "Gaming", "Gadgets"]),
                ad_title="iPhone 18 Pro Max - Pre-Order Now",
                ad_body="Experience the future of mobile with the revolutionary A20 Bionic chip and holographic screen.",
                ad_creative_url="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&h=250&fit=crop",
                is_active=True
            ),
            Campaign(
                name="Fitness Fanatics Summer Sale",
                advertiser="NikeFit",
                budget=800.0,
                current_spend=0.0,
                bid_amount=1.80,
                target_age_min=15,
                target_age_max=40,
                target_location="All",
                target_interests=json.dumps(["Fitness", "Sports", "Lifestyle"]),
                ad_title="Just Do It - 30% Off Running Gear",
                ad_body="Level up your summer workout routine with breathable, ultra-light apparel engineered for speed.",
                ad_creative_url="https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=300&h=250&fit=crop",
                is_active=True
            ),
            Campaign(
                name="Luxury Auto Showcase",
                advertiser="TeslaMotors",
                budget=3000.0,
                current_spend=0.0,
                bid_amount=5.00,
                target_age_min=25,
                target_age_max=65,
                target_location="New York",
                target_interests=json.dumps(["Cars", "Technology", "Luxury"]),
                ad_title="Model S Plaid - Re-imagine Speed",
                ad_body="0-60 mph in 1.99s. Dual-motor all-wheel drive, autopilot enabled, and 400+ miles range.",
                ad_creative_url="https://images.unsplash.com/photo-1563720223185-11003d516935?w=300&h=250&fit=crop",
                is_active=True
            ),
            Campaign(
                name="Gamer Elite Pro Gear",
                advertiser="RazerZone",
                budget=1000.0,
                current_spend=0.0,
                bid_amount=2.20,
                target_age_min=12,
                target_age_max=35,
                target_location="All",
                target_interests=json.dumps(["Gaming", "Technology", "Gadgets"]),
                ad_title="Chroma Pro Gaming Keyboard",
                ad_body="Mechanical green switches with customizable RGB lighting and 1ms actuation latency.",
                ad_creative_url="https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=300&h=250&fit=crop",
                is_active=True
            ),
            Campaign(
                name="Gourmet Espresso Promo",
                advertiser="Starbucks",
                budget=500.0,
                current_spend=0.0,
                bid_amount=1.20,
                target_age_min=18,
                target_age_max=60,
                target_location="All",
                target_interests=json.dumps(["Food", "Lifestyle", "Coffee"]),
                ad_title="Cold Brew Nitro - Real Energy",
                ad_body="Slow-steeped for 20 hours and infused with nitrogen for a smooth, velvety texture.",
                ad_creative_url="https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=300&h=250&fit=crop",
                is_active=True
            )
        ]
        
        for camp in campaigns:
            db.add(camp)
        db.commit()

        # Seed caches
        for camp in campaigns:
            db.refresh(camp)
            reset_campaign_cache(camp.id, camp.budget, camp.current_spend)
            
        logger.info(f"Successfully seeded {len(campaigns)} campaigns.")

    # 2. Seed users
    if db.query(User).count() == 0:
        logger.info("Database is empty of users. Seeding default user profiles...")
        users = [
            User(
                name="Saksham (You)",
                age=22,
                location="Mumbai",
                interests=json.dumps(["Technology", "Gaming", "Gadgets"])
            ),
            User(
                name="Emma Watson",
                age=32,
                location="New York",
                interests=json.dumps(["Cars", "Technology", "Luxury", "Lifestyle"])
            ),
            User(
                name="Virat Kohli",
                age=37,
                location="Mumbai",
                interests=json.dumps(["Sports", "Fitness", "Lifestyle"])
            ),
            User(
                name="Sarah Jenkins",
                age=19,
                location="All",
                interests=json.dumps(["Gaming", "Fitness"])
            ),
            User(
                name="Rajesh Kumar",
                age=48,
                location="Mumbai",
                interests=json.dumps(["Food", "Lifestyle", "Coffee"])
            )
        ]
        
        for usr in users:
            db.add(usr)
        db.commit()
        logger.info(f"Successfully seeded {len(users)} user profiles.")

    # 3. Seed baseline Analytics for seed data (to prevent 0 CTR metrics)
    if db.query(Analytics).count() == 0:
        logger.info("Seeding baseline analytics metrics...")
        # Get campaigns
        camps = db.query(Campaign).all()
        for c in camps:
            # Seed varying impressions and clicks
            if c.id == 1:
                impressions, clicks, revenue = 150, 12, 12 * 3.50
            elif c.id == 2:
                impressions, clicks, revenue = 80, 5, 5 * 1.80
            elif c.id == 3:
                impressions, clicks, revenue = 200, 18, 18 * 5.00
            elif c.id == 4:
                impressions, clicks, revenue = 110, 8, 8 * 2.20
            else:
                impressions, clicks, revenue = 50, 3, 3 * 1.20
                
            analytics = Analytics(
                campaign_id=c.id,
                impressions=impressions,
                clicks=clicks,
                revenue=revenue
            )
            db.add(analytics)
            
            # Sync cache stats
            stats_key = f"campaign:stats:{c.id}"
            cache.set(
                stats_key,
                json.dumps({"impressions": impressions, "clicks": clicks}),
                expire_seconds=120
            )
            
        db.commit()
        logger.info("Successfully seeded baseline analytics metrics.")
