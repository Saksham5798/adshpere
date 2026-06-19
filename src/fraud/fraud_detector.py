import logging
from src.cache.redis_cache import cache

logger = logging.getLogger("adsphere.fraud")

# Simple mock blacklist of IPs
IP_BLACKLIST = {
    "192.168.100.100",
    "10.0.0.99",
    "66.66.66.66"
}

def is_fraud(ip_address: str, user_id: int = None) -> tuple[bool, float, str]:
    """
    Checks if a bid request is fraudulent.
    Returns: (is_fraud_detected, fraud_score, reason)
    """
    # 1. Blacklist Check
    if ip_address in IP_BLACKLIST:
        logger.warning(f"Fraud detected: IP {ip_address} is blacklisted.")
        return True, 1.0, "IP Blacklisted"

    # 2. Rate-Limiting Check (e.g., maximum 10 requests per 10 seconds per IP)
    rate_key = f"rate_limit:{ip_address}"
    current_requests = cache.incr(rate_key)
    
    if current_requests == 1:
        # Key was just created, set TTL of 10 seconds
        # Using cache.set with expiration
        cache.set(rate_key, 1, expire_seconds=10)
    
    if current_requests > 10:
        logger.warning(f"Fraud detected: Rate limit exceeded for IP {ip_address} ({current_requests} req/10s).")
        return True, 0.9, f"Rate Limit Exceeded ({current_requests} requests/10s)"

    # 3. User ID validation (if provided)
    if user_id is not None and user_id <= 0:
        return True, 0.95, "Invalid User ID"

    # No fraud detected
    return False, 0.0, ""
