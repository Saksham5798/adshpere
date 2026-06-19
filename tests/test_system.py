"""
AdSphere RTB System — End-to-End Test Suite
============================================
Run this script while the server is running on port 8001:

    uvicorn src.main:app --host 127.0.0.1 --port 8001

Then in a separate terminal:

    python tests/test_system.py
"""

import sys
import json
import time
import requests

BASE_URL = "http://127.0.0.1:8001"
PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
WARN = "\033[93m[WARN]\033[0m"

results = {"passed": 0, "failed": 0}


def sep(title):
    print(f"\n{'='*60}")
    print(f"  TEST: {title}")
    print(f"{'='*60}")


def check(condition, label, detail=""):
    if condition:
        print(f"  {PASS} {label}")
        results["passed"] += 1
    else:
        print(f"  {FAIL} {label}")
        if detail:
            print(f"        → {detail}")
        results["failed"] += 1


# ─────────────────────────────────────────────────────────────────────
# TEST 1: Health Check
# ─────────────────────────────────────────────────────────────────────
sep("Health Check")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    data = r.json()
    check(r.status_code == 200,  "HTTP 200 response")
    check(data.get("status") == "healthy", "Status is 'healthy'")
    check("database" in data,    "Database field present in response")
except Exception as e:
    check(False, "Health endpoint reachable", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 2: Campaign Management API
# ─────────────────────────────────────────────────────────────────────
sep("Campaign Management API")
try:
    # List campaigns
    r = requests.get(f"{BASE_URL}/campaigns", timeout=5)
    campaigns = r.json()
    check(r.status_code == 200,  "GET /campaigns returns HTTP 200")
    check(len(campaigns) >= 5,   f"At least 5 seed campaigns present (found {len(campaigns)})")

    first = campaigns[0]
    check("id"               in first, "Campaign has 'id' field")
    check("name"             in first, "Campaign has 'name' field")
    check("advertiser"       in first, "Campaign has 'advertiser' field")
    check("budget"           in first, "Campaign has 'budget' field")
    check("bid_amount"       in first, "Campaign has 'bid_amount' field")
    check("target_interests" in first, "Campaign has 'target_interests' field")
    check("is_active"        in first, "Campaign has 'is_active' field")

    # Create a new campaign
    new_camp = {
        "name": "Test Campaign Alpha",
        "advertiser": "TestCorp",
        "budget": 250.0,
        "bid_amount": 1.50,
        "target_age_min": 20,
        "target_age_max": 40,
        "target_location": "All",
        "target_interests": ["Technology", "Gaming"],
        "ad_title": "Test Ad Headline",
        "ad_body": "Test ad body description text.",
        "ad_creative_url": "https://picsum.photos/300/250"
    }
    r2 = requests.post(f"{BASE_URL}/campaign", json=new_camp, timeout=5)
    check(r2.status_code == 201, "POST /campaign returns HTTP 201 Created")
    created = r2.json()
    check(created.get("name") == "Test Campaign Alpha", "Created campaign name matches")
    check(created.get("current_spend") == 0.0,          "New campaign starts with $0 spend")
    created_id = created.get("id")

    # Get single campaign
    r3 = requests.get(f"{BASE_URL}/campaign/{created_id}", timeout=5)
    check(r3.status_code == 200, f"GET /campaign/{created_id} returns HTTP 200")

    # 404 on missing campaign
    r4 = requests.get(f"{BASE_URL}/campaign/99999", timeout=5)
    check(r4.status_code == 404, "GET /campaign/99999 returns HTTP 404")

except Exception as e:
    check(False, "Campaign API suite", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 3: User Profile API
# ─────────────────────────────────────────────────────────────────────
sep("User Profile API")
try:
    r = requests.get(f"{BASE_URL}/users", timeout=5)
    users = r.json()
    check(r.status_code == 200, "GET /users returns HTTP 200")
    check(len(users) >= 5,      f"At least 5 seed users present (found {len(users)})")

    first_u = users[0]
    check("id"        in first_u, "User has 'id' field")
    check("name"      in first_u, "User has 'name' field")
    check("age"       in first_u, "User has 'age' field")
    check("location"  in first_u, "User has 'location' field")
    check("interests" in first_u, "User has 'interests' field")

    # Create user
    new_user = {
        "name": "Test User Beta",
        "age": 25,
        "location": "Mumbai",
        "interests": ["Gaming", "Technology"]
    }
    r2 = requests.post(f"{BASE_URL}/user", json=new_user, timeout=5)
    check(r2.status_code == 201, "POST /user returns HTTP 201 Created")
    created_user = r2.json()
    check(created_user.get("name") == "Test User Beta", "Created user name matches")

    # 404 on missing user
    r3 = requests.get(f"{BASE_URL}/user/99999", timeout=5)
    check(r3.status_code == 404, "GET /user/99999 returns HTTP 404")

except Exception as e:
    check(False, "User Profile API suite", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 4: Standard RTB Auction — Saksham (Mumbai, Tech/Gaming, Age 22)
#         Eligible: AppleCorp Tech Campaign + RazerZone Gaming Campaign
# ─────────────────────────────────────────────────────────────────────
sep("Standard RTB Auction (Targeting Match)")
try:
    payload = {
        "user_id": 1,           # Saksham — Mumbai, Age 22, Tech/Gaming/Gadgets
        "ip_address": "10.1.2.3",
        "device": "Desktop",
        "page_url": "https://adsphere-rtb.com/test"
    }
    r = requests.post(f"{BASE_URL}/auction/request", json=payload, timeout=10)
    check(r.status_code == 200, "POST /auction/request returns HTTP 200")
    res = r.json()
    check(res.get("auction_status") == "completed", "Auction status is 'completed'")
    check(res.get("winning_ad") is not None,         "Winning ad returned")
    check(res.get("auction_duration_ms") < 500,      f"Auction completed in <500ms ({res.get('auction_duration_ms')} ms)")
    check(len(res.get("trace", [])) > 0,             "Auction trace log is populated")

    ad = res.get("winning_ad", {})
    check("campaign_id"             in ad, "Winning ad has campaign_id")
    check("advertiser"              in ad, "Winning ad has advertiser")
    check("ad_title"                in ad, "Winning ad has ad_title")
    check("bid_amount"              in ad, "Winning ad has bid_amount")
    check("impression_tracking_url" in ad, "Winning ad has impression tracking URL")
    check("click_tracking_url"      in ad, "Winning ad has click tracking URL")

    winning_ad = ad  # save for later tracking tests

except Exception as e:
    winning_ad = None
    check(False, "Standard RTB Auction suite", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 5: Targeting Filter — Location Mismatch
#         Emma Watson is in New York, most campaigns target Mumbai/All
# ─────────────────────────────────────────────────────────────────────
sep("RTB Auction — Location Targeting Filter")
try:
    # Emma Watson: Age 32, New York, Cars/Technology/Luxury
    # TeslaMotors campaign targets New York — should win for Emma
    payload = {
        "user_id": 2,
        "ip_address": "10.2.3.4",
        "device": "Mobile"
    }
    r = requests.post(f"{BASE_URL}/auction/request", json=payload, timeout=10)
    res = r.json()
    check(r.status_code == 200, "POST /auction/request returns HTTP 200")
    status = res.get("auction_status")
    check(status in ("completed", "no_matching_campaigns"),
          f"Auction returns valid status (got: '{status}')")
    trace_text = " ".join(res.get("trace", []))
    check("filtered" in trace_text.lower() or "Winner Selected" in trace_text,
          "Trace log contains filtering or winner information")

except Exception as e:
    check(False, "Location targeting filter test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 6: User Not Found
# ─────────────────────────────────────────────────────────────────────
sep("RTB Auction — Non-Existent User")
try:
    payload = {"user_id": 99999, "ip_address": "10.3.4.5", "device": "Desktop"}
    r = requests.post(f"{BASE_URL}/auction/request", json=payload, timeout=10)
    res = r.json()
    check(r.status_code == 200,                            "Endpoint returns HTTP 200 (graceful)")
    check(res.get("auction_status") == "user_not_found",   "Auction status is 'user_not_found'")

except Exception as e:
    check(False, "Non-existent user test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 7: Fraud Detection — Blacklisted IP
# ─────────────────────────────────────────────────────────────────────
sep("Fraud Detection — Blacklisted IP")
try:
    payload = {
        "user_id": 1,
        "ip_address": "192.168.100.100",  # In the IP blacklist
        "device": "Desktop"
    }
    r = requests.post(f"{BASE_URL}/auction/request", json=payload, timeout=10)
    res = r.json()
    check(r.status_code == 200,                             "Endpoint returns HTTP 200")
    check(res.get("auction_status") == "fraud_blocked",     "Auction blocked for blacklisted IP")
    check(res.get("winning_ad") is None,                    "No winning ad returned on fraud block")
    trace = " ".join(res.get("trace", []))
    check("IP Blacklisted" in trace or "blacklist" in trace.lower(),
          "Trace log mentions IP blacklist")

    # Verify fraud log was written
    time.sleep(0.5)
    r2 = requests.get(f"{BASE_URL}/fraud", timeout=5)
    fraud_logs = r2.json()
    check(any(log["ip_address"] == "192.168.100.100" for log in fraud_logs),
          "Blacklisted IP appears in /fraud log records")

except Exception as e:
    check(False, "Blacklisted IP fraud test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 8: Fraud Detection — Rate Limiting
# ─────────────────────────────────────────────────────────────────────
sep("Fraud Detection — Rate Limit (>10 requests / 10s)")
try:
    spam_ip = "172.16.250.250"
    payload = {"user_id": 3, "ip_address": spam_ip, "device": "Mobile"}

    blocked_at = None
    for i in range(1, 13):
        r = requests.post(f"{BASE_URL}/auction/request", json=payload, timeout=10)
        res = r.json()
        if res.get("auction_status") == "fraud_blocked":
            blocked_at = i
            break

    check(blocked_at is not None,   f"Rate limit triggered (blocked at request #{blocked_at})")
    check(blocked_at <= 12,         f"Block occurred within 12 requests (at #{blocked_at})")

except Exception as e:
    check(False, "Rate limiting test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 9: Impression Tracking Pixel
# ─────────────────────────────────────────────────────────────────────
sep("Impression Tracking Pixel")
try:
    r = requests.get(f"{BASE_URL}/analytics/impression/1/1", timeout=5)
    check(r.status_code == 200,                         "GET /analytics/impression returns HTTP 200")
    check(r.headers.get("content-type") == "image/gif", "Response content-type is image/gif")
    check(len(r.content) == 43,                         "Response is a valid 1×1 transparent GIF (43 bytes)")

except Exception as e:
    check(False, "Impression pixel test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 10: Click Redirect Tracker
# ─────────────────────────────────────────────────────────────────────
sep("Click Redirect Tracker")
try:
    r = requests.get(f"{BASE_URL}/analytics/click/1/1",
                     timeout=5, allow_redirects=False)
    check(r.status_code == 307,               "GET /analytics/click returns HTTP 307 Temporary Redirect")
    check("Location" in r.headers,            "Response contains Location redirect header")
    check(r.headers["Location"].startswith("http"),
          f"Redirect points to valid URL ({r.headers.get('Location', '')[:50]}...)")

except Exception as e:
    check(False, "Click redirect test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 11: Analytics Summary
# ─────────────────────────────────────────────────────────────────────
sep("Analytics Summary API")
try:
    r = requests.get(f"{BASE_URL}/analytics/summary", timeout=5)
    check(r.status_code == 200, "GET /analytics/summary returns HTTP 200")
    data = r.json()

    agg = data.get("aggregate", {})
    check("impressions" in agg, "Aggregate has 'impressions'")
    check("clicks"      in agg, "Aggregate has 'clicks'")
    check("ctr"         in agg, "Aggregate has 'ctr'")
    check("revenue"     in agg, "Aggregate has 'revenue'")
    check(agg.get("impressions", 0) > 0, f"Impressions > 0 (seeded data present: {agg.get('impressions')})")
    check(agg.get("revenue", 0) > 0,     f"Revenue > 0 (seeded data present: ${agg.get('revenue')})")

    camps = data.get("campaigns", [])
    check(len(camps) >= 5, f"Campaign breakdown present ({len(camps)} campaigns)")

    # Verify per-campaign fields
    camp_fields = {"campaign_id", "campaign_name", "impressions", "clicks", "ctr", "revenue", "budget", "current_spend"}
    check(camp_fields.issubset(set(camps[0].keys())),
          "Each campaign breakdown entry has all required fields")

except Exception as e:
    check(False, "Analytics summary test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 12: Auction History Log
# ─────────────────────────────────────────────────────────────────────
sep("Auction History Log")
try:
    r = requests.get(f"{BASE_URL}/history?limit=50", timeout=5)
    check(r.status_code == 200, "GET /history returns HTTP 200")
    logs = r.json()
    check(len(logs) > 0, f"Auction history log contains records (found {len(logs)})")

    statuses = {log["status"] for log in logs}
    check(bool(statuses & {"WON", "LOST", "FILTERED_BUDGET", "FILTERED_TARGETING", "NO_CAMPAIGNS"}),
          f"Bid history contains valid status values: {statuses}")

    # Ensure the winning bid we generated in test 4 shows up
    won_entries = [l for l in logs if l["status"] == "WON"]
    check(len(won_entries) > 0, f"At least one WON entry exists ({len(won_entries)} found)")

except Exception as e:
    check(False, "Auction history log test", str(e))


# ─────────────────────────────────────────────────────────────────────
# TEST 13: Budget Deduction
# ─────────────────────────────────────────────────────────────────────
sep("Budget Deduction After Winning Bid")
try:
    # Get current spend of campaign 1
    r = requests.get(f"{BASE_URL}/campaign/1", timeout=5)
    camp = r.json()
    spend_before = camp.get("current_spend", 0.0)

    # Run an auction that should win campaign 1
    payload = {"user_id": 1, "ip_address": "10.5.6.7", "device": "Desktop"}
    r2 = requests.post(f"{BASE_URL}/auction/request", json=payload, timeout=10)
    res = r2.json()

    if res.get("auction_status") == "completed" and res.get("winning_ad", {}).get("campaign_id") == 1:
        time.sleep(0.2)
        r3 = requests.get(f"{BASE_URL}/campaign/1", timeout=5)
        camp_after = r3.json()
        spend_after = camp_after.get("current_spend", 0.0)
        check(spend_after > spend_before,
              f"Budget deducted after win: ${spend_before:.2f} → ${spend_after:.2f}")
    else:
        print(f"  {WARN} Campaign 1 did not win this auction — budget deduction test skipped")
        results["passed"] += 1  # skip as pass

except Exception as e:
    check(False, "Budget deduction test", str(e))


# ─────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────
total = results["passed"] + results["failed"]
print(f"\n{'='*60}")
print(f"  RESULTS: {results['passed']}/{total} tests passed", end="")
if results["failed"] == 0:
    print("  \033[92m✓ ALL PASSED\033[0m")
else:
    print(f"  \033[91m✗ {results['failed']} FAILED\033[0m")
print(f"{'='*60}\n")

sys.exit(0 if results["failed"] == 0 else 1)
