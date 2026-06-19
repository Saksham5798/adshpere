import json
import logging
from typing import List

logger = logging.getLogger("adsphere.bidding.ranking")

def parse_interests(interest_field) -> set:
    """Safely parse interest tags to a python set."""
    if not interest_field:
        return set()
    if isinstance(interest_field, list):
        return set([i.lower() for i in interest_field])
    if isinstance(interest_field, str):
        try:
            parsed = json.loads(interest_field)
            if isinstance(parsed, list):
                return set([i.lower() for i in parsed])
        except Exception:
            # Fallback to string split if JSON parsing fails
            return set([i.strip().lower() for i in interest_field.replace("[", "").replace("]", "").replace('"', '').split(",") if i.strip()])
    return set()

def calculate_relevance_score(user_interests_raw, campaign_interests_raw) -> float:
    """
    Computes a relevance score [0.1 to 1.0] based on interest overlaps.
    Uses Jaccard Index: Overlap / Union
    """
    user_set = parse_interests(user_interests_raw)
    camp_set = parse_interests(campaign_interests_raw)

    if not camp_set:
        # If campaign has no interest targeting restrictions, it is general relevance
        return 0.5

    if not user_set:
        # User has no interests, low baseline relevance
        return 0.1

    intersection = user_set.intersection(camp_set)
    union = user_set.union(camp_set)

    if not union:
        return 0.1

    jaccard = len(intersection) / len(union)
    
    # Map [0, 1] Jaccard index to [0.1, 1.0] relevance score
    return 0.1 + (jaccard * 0.9)

def calculate_ctr(impressions: int, clicks: int) -> float:
    """Calculates Click-Through-Rate (CTR) with a Laplace smoothing to handle cold-starts."""
    if impressions <= 0:
        return 0.01  # Default baseline CTR (1%) for new campaigns
    
    # CTR calculation with smoothing to prevent 0 or extreme numbers
    ctr = clicks / impressions
    # Clip CTR between 0.001 and 0.2
    return max(0.001, min(0.2, ctr))

def calculate_score(bid_amount: float, ctr: float, relevance: float) -> float:
    """
    Calculates final auction ranking score.
    Higher is better.
    """
    return bid_amount * ctr * relevance