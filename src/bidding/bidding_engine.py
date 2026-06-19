import time
import json
import logging
from sqlalchemy.orm import Session
from src.database.models import Campaign, User, BidHistory, FraudLog, Analytics
from src.schemas.auction import BidRequest, BidResponse, AdCreativeResponse
from src.bidding import ranking_engine, budget_manager
from src.fraud import fraud_detector
from src.cache.redis_cache import cache

logger = logging.getLogger("adsphere.bidding.engine")

def run_auction(request: BidRequest, db: Session) -> BidResponse:
    """
    Executes a real-time auction for a bid request.
    Filters campaigns by targeting/budget, ranks using scoring,
    registers transactions, logs history, and returns the winning creative.
    """
    start_time = time.time()
    trace = []
    
    trace.append(f"Starting auction for User ID: {request.user_id} | IP: {request.ip_address}")
    
    # 1. Fraud Check
    is_fraudulent, fraud_score, fraud_reason = fraud_detector.is_fraud(request.ip_address, request.user_id)
    if is_fraudulent:
        duration_ms = (time.time() - start_time) * 1000.0
        trace.append(f"Auction blocked: Fraud detected! Reason: {fraud_reason}")
        
        # Log fraud to DB
        fraud_log = FraudLog(
            ip_address=request.ip_address,
            user_id=request.user_id if request.user_id > 0 else None,
            reason=fraud_reason,
            request_data=request.model_dump_json(),
            score=fraud_score
        )
        db.add(fraud_log)
        db.commit()
        
        return BidResponse(
            auction_status="fraud_blocked",
            winning_ad=None,
            auction_duration_ms=round(duration_ms, 2),
            trace=trace
        )

    # 2. Get User Profile
    user_key = f"user:profile:{request.user_id}"
    user_cached = cache.get(user_key)
    user = None
    
    if user_cached:
        try:
            user_dict = json.loads(user_cached)
            user = User(
                id=user_dict["id"],
                name=user_dict["name"],
                age=user_dict["age"],
                location=user_dict["location"],
                interests=json.dumps(user_dict["interests"])
            )
            trace.append(f"Loaded User profile from cache: {user_dict['name']}")
        except Exception:
            pass

    if not user:
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            duration_ms = (time.time() - start_time) * 1000.0
            trace.append(f"User profile {request.user_id} not found in DB.")
            return BidResponse(
                auction_status="user_not_found",
                winning_ad=None,
                auction_duration_ms=round(duration_ms, 2),
                trace=trace
            )
        # Cache user profile
        user_data = {
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "location": user.location,
            "interests": ranking_engine.parse_interests(user.interests)
        }
        # Convert set to list for JSON serialization
        user_data["interests"] = list(user_data["interests"])
        cache.set(user_key, json.dumps(user_data), expire_seconds=600)
        trace.append(f"Loaded User profile from DB and cached: {user.name}")

    # 3. Fetch Active Campaigns
    active_campaigns = db.query(Campaign).filter(Campaign.is_active == True).all()
    if not active_campaigns:
        duration_ms = (time.time() - start_time) * 1000.0
        trace.append("No active campaigns found in database.")
        
        # Log a bid history entry representing no bid
        bid_history = BidHistory(
            user_id=user.id,
            bid_amount=0.0,
            score=0.0,
            status="NO_CAMPAIGNS",
            reason="No active campaigns in system"
        )
        db.add(bid_history)
        db.commit()
        
        return BidResponse(
            auction_status="no_matching_campaigns",
            winning_ad=None,
            auction_duration_ms=round(duration_ms, 2),
            trace=trace
        )

    # 4. Filter Campaigns (Targeting & Budget constraints)
    eligible_campaigns = []
    user_interests = ranking_engine.parse_interests(user.interests)
    
    for campaign in active_campaigns:
        camp_desc = f"Campaign '{campaign.name}' (ID: {campaign.id})"
        
        # Check Budget
        if not budget_manager.has_budget(campaign.id, campaign.bid_amount, db):
            trace.append(f"{camp_desc} filtered: Budget exhausted.")
            # Log filtered status
            bid_hist = BidHistory(
                campaign_id=campaign.id,
                user_id=user.id,
                bid_amount=campaign.bid_amount,
                score=0.0,
                status="FILTERED_BUDGET",
                reason="Budget exhausted"
            )
            db.add(bid_hist)
            continue

        # Check Age targeting
        if not (campaign.target_age_min <= user.age <= campaign.target_age_max):
            trace.append(f"{camp_desc} filtered: Age mismatch. Target: {campaign.target_age_min}-{campaign.target_age_max}, User: {user.age}")
            bid_hist = BidHistory(
                campaign_id=campaign.id,
                user_id=user.id,
                bid_amount=campaign.bid_amount,
                score=0.0,
                status="FILTERED_TARGETING",
                reason=f"Age mismatch: {user.age} not in {campaign.target_age_min}-{campaign.target_age_max}"
            )
            db.add(bid_hist)
            continue

        # Check Location targeting
        if campaign.target_location != "All" and campaign.target_location.lower() != user.location.lower():
            trace.append(f"{camp_desc} filtered: Location mismatch. Target: {campaign.target_location}, User: {user.location}")
            bid_hist = BidHistory(
                campaign_id=campaign.id,
                user_id=user.id,
                bid_amount=campaign.bid_amount,
                score=0.0,
                status="FILTERED_TARGETING",
                reason=f"Location mismatch: User is in {user.location}, target: {campaign.target_location}"
            )
            db.add(bid_hist)
            continue

        # Check Interest targeting (if campaign lists target interests, user must have at least one overlap)
        campaign_interests = ranking_engine.parse_interests(campaign.target_interests)
        if campaign_interests and not user_interests.intersection(campaign_interests):
            trace.append(f"{camp_desc} filtered: Interest mismatch. Target: {list(campaign_interests)}, User: {list(user_interests)}")
            bid_hist = BidHistory(
                campaign_id=campaign.id,
                user_id=user.id,
                bid_amount=campaign.bid_amount,
                score=0.0,
                status="FILTERED_TARGETING",
                reason="Interest mismatch"
            )
            db.add(bid_hist)
            continue

        # Campaign passed all filters!
        eligible_campaigns.append(campaign)
        trace.append(f"{camp_desc} passed targeting and budget checks.")

    # Commit any filtered logs recorded so far
    db.commit()

    if not eligible_campaigns:
        duration_ms = (time.time() - start_time) * 1000.0
        trace.append("No active campaigns passed the targeting and budget matching rules.")
        return BidResponse(
            auction_status="no_matching_campaigns",
            winning_ad=None,
            auction_duration_ms=round(duration_ms, 2),
            trace=trace
        )

    # 5. Run Ranking & Scoring
    scored_candidates = []
    
    for campaign in eligible_campaigns:
        # Calculate relevance
        relevance = ranking_engine.calculate_relevance_score(user.interests, campaign.target_interests)
        
        # Calculate CTR from dynamic DB stats
        # Check cache for campaign stats first
        stats_key = f"campaign:stats:{campaign.id}"
        stats_cached = cache.get(stats_key)
        impressions = 0
        clicks = 0
        
        if stats_cached:
            try:
                stats = json.loads(stats_cached)
                impressions = stats["impressions"]
                clicks = stats["clicks"]
            except Exception:
                pass
        else:
            # Query DB
            analytics_records = db.query(Analytics).filter(Analytics.campaign_id == campaign.id).all()
            impressions = sum(r.impressions for r in analytics_records)
            clicks = sum(r.clicks for r in analytics_records)
            # Cache it for 2 minutes
            cache.set(stats_key, json.dumps({"impressions": impressions, "clicks": clicks}), expire_seconds=120)

        ctr = ranking_engine.calculate_ctr(impressions, clicks)
        score = ranking_engine.calculate_score(campaign.bid_amount, ctr, relevance)
        
        scored_candidates.append({
            "campaign": campaign,
            "bid": campaign.bid_amount,
            "ctr": ctr,
            "relevance": relevance,
            "score": score
        })
        
        trace.append(
            f"Campaign '{campaign.name}' Scored: {score:.5f} (Bid: ${campaign.bid_amount:.2f}, CTR: {ctr*100:.3f}%, Relevance: {relevance:.2f})"
        )

    # Sort candidates by score descending
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    winner_pkg = scored_candidates[0]
    winner_camp = winner_pkg["campaign"]
    
    trace.append(f"Winner Selected: Campaign '{winner_camp.name}' (Score: {winner_pkg['score']:.5f})")

    # 6. Deduct win bid & log transactions
    # Deduct spend
    budget_manager.deduct_budget(winner_camp.id, winner_pkg["bid"], db)
    
    # Save winner to history
    win_history = BidHistory(
        campaign_id=winner_camp.id,
        user_id=user.id,
        bid_amount=winner_pkg["bid"],
        score=winner_pkg["score"],
        status="WON"
    )
    db.add(win_history)
    
    # Save other participants as lost
    for candidate in scored_candidates[1:]:
        lost_camp = candidate["campaign"]
        lost_history = BidHistory(
            campaign_id=lost_camp.id,
            user_id=user.id,
            bid_amount=candidate["bid"],
            score=candidate["score"],
            status="LOST"
        )
        db.add(lost_history)
    
    db.commit()
    db.refresh(win_history)

    # Create Tracking URLs
    impression_url = f"/analytics/impression/{winner_camp.id}/{user.id}"
    click_url = f"/analytics/click/{winner_camp.id}/{user.id}"

    duration_ms = (time.time() - start_time) * 1000.0
    trace.append(f"Auction complete in {duration_ms:.2f} ms")

    winning_ad = AdCreativeResponse(
        campaign_id=winner_camp.id,
        advertiser=winner_camp.advertiser,
        bid_amount=winner_pkg["bid"],
        ad_title=winner_camp.ad_title,
        ad_body=winner_camp.ad_body,
        ad_creative_url=winner_camp.ad_creative_url,
        impression_tracking_url=impression_url,
        click_tracking_url=click_url
    )

    return BidResponse(
        auction_status="completed",
        winning_ad=winning_ad,
        auction_duration_ms=round(duration_ms, 2),
        trace=trace
    )