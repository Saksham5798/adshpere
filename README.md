# AdSphere — Real-Time Bidding (RTB) Advertising System

> **College System Design Capstone Project**  
> *Demonstrating RTB concepts analogous to large digital advertising platforms such as Google Ads, Meta Audience Network, and The Trade Desk.*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Source Code Structure](#3-source-code-structure)
4. [Dependencies](#4-dependencies)
5. [Setup Instructions](#5-setup-instructions)
6. [Execution Steps](#6-execution-steps)
7. [API Reference](#7-api-reference)
8. [Additional Project Details](#8-additional-project-details)

---

## 1. Project Overview

**AdSphere** is a high-throughput, production-style Real-Time Bidding (RTB) advertising platform built using:

| Layer | Technology |
|-------|-----------|
| Backend API | **FastAPI** (Python 3.x) |
| Database ORM | **SQLAlchemy 2.0** |
| Database Storage | **PostgreSQL** (production) / **SQLite** (fallback) |
| Caching Layer | **Redis** (production) / Thread-safe In-Memory Cache (fallback) |
| Data Validation | **Pydantic v2** |
| Frontend Dashboard | Vanilla **HTML / CSS / JavaScript** (Chart.js) |

### What is RTB?

Real-Time Bidding is a mechanism in which digital advertising inventory is bought and sold in automated, instantaneous auctions — triggered every time a user loads a webpage. These auctions must complete in under **100 milliseconds** (between the HTTP request and the ad being rendered on-screen).

### What AdSphere Implements

| Feature | Implementation |
|--------|---------------|
| Campaign Management | Create / Read / Update campaigns with budget, bids, and targeting |
| User Demographics | Create user profiles with age, location, and interest tags |
| Real-Time Auction | Sub-15ms auction engine with targeting filters and scoring |
| Interest Matching | Jaccard Similarity Index for computing relevance overlap |
| Dynamic CTR | Laplace-smoothed Click-Through-Rate from live analytics |
| Budget Enforcement | Atomic cache-based budget checks + DB write-back sync |
| Fraud Detection | IP blacklist matching + sliding-window rate limiting |
| Impression Tracking | Returns a 1×1 transparent tracking GIF pixel |
| Click Tracking | Issues an HTTP 307 redirect and records click/revenue metrics |
| Analytics Dashboard | Impressions, clicks, CTR, and revenue aggregated per campaign |
| Event Streaming | Simulated Kafka producer/consumer pipeline for telemetry events |

---

## 2. System Architecture Diagram

![AdSphere RTB System Architecture](docs/architecture_diagram.png)

### Flow Description (Step-by-Step)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP  │  COMPONENT                     │  ACTION                        │
├────────┼────────────────────────────────┼────────────────────────────────┤
│   1    │  Client Browser                │  Page loads, bid request sent  │
│   2    │  FastAPI API Gateway           │  Routes POST /auction/request  │
│   3    │  Fraud Guard                   │  Checks IP blacklist + rate    │
│  3a    │  Redis / In-Memory Cache       │  Reads rate-limit counter      │
│  3b    │  Fraud Logs DB                 │  Writes suspicious event log   │
│   4    │  Bidding Engine Orchestrator   │  Loads user profile from cache │
│  4a    │  Redis Cache                   │  Campaign budget cache hit     │
│  4b    │  PostgreSQL / SQLite           │  Fallback DB query on miss     │
│   5    │  Campaign Targeting Matcher    │  Age / Location / Interests    │
│   6    │  Ranking Engine                │  Jaccard relevance + CTR score │
│   7    │  Budget Manager                │  Verifies remaining budget     │
│  7a    │  Redis Cache                   │  Atomic spend increment        │
│  7b    │  PostgreSQL / SQLite           │  Persist spend, mark inactive  │
│   8    │  Bid History DB                │  Log WON / LOST / FILTERED     │
│   9    │  FastAPI Response              │  Return winning ad + trackers  │
│  10    │  Impression Pixel API          │  Ad loads, GIF pixel fires     │
│  11    │  Click Redirect Tracker        │  User clicks, 307 redirect     │
│  12    │  Analytics Processor           │  Async: update CTR + revenue   │
│  12a   │  Analytics DB                  │  Persist impressions/clicks    │
│  12b   │  Redis Cache                   │  Evict stale CTR stats cache   │
└────────┴────────────────────────────────┴────────────────────────────────┘
```

### Component Descriptions

- **FastAPI API Gateway** (`src/api/`) — HTTP entrypoint exposing campaign CRUD, user profiles, auction execution, and telemetry tracking endpoints.
- **Fraud Guard** (`src/fraud/fraud_detector.py`) — Inline IP blacklist lookup and sliding-window rate-limiting using the cache layer.
- **Bidding Engine** (`src/bidding/bidding_engine.py`) — Orchestrates the full auction lifecycle: user loading, targeting filters, scoring, budget checks, winner selection, and outcome logging.
- **Ranking Engine** (`src/bidding/ranking_engine.py`) — Implements interest overlap scoring (Jaccard Index) and Laplace-smoothed CTR to compute the final bid ranking score.
- **Budget Manager** (`src/bidding/budget_manager.py`) — Handles atomic budget checks and deductions via the cache, with synchronization back to the database.
- **Cache Manager** (`src/cache/redis_cache.py`) — Redis client with automatic thread-safe in-memory fallback for budget tracking, user profiles, CTR stats, and rate-limiting counters.
- **Analytics Processor** (`src/analytics/analytics_processor.py`) — Processes impression and click events asynchronously via FastAPI `BackgroundTasks`, updates DB counters, and evicts stale cache entries.

---

## 3. Source Code Structure

```
AdSphere-RTB-System/
│
├── README.md                       ← This file
├── requirements.txt                ← Python package dependencies
├── adsphere.db                     ← SQLite database (auto-created on first run)
│
├── docs/
│   └── architecture_diagram.png   ← System Architecture visual diagram
│
├── tests/
│   └── test_system.py              ← End-to-end test suite (13 test groups)
│
└── src/
    ├── __init__.py
    ├── main.py                     ← FastAPI app entrypoint, router wiring,
    │                                  startup seeding, static file mounting
    │
    ├── api/                        ← REST API route handlers
    │   ├── __init__.py
    │   ├── campaign_api.py         ← Campaign CRUD endpoints
    │   ├── user_api.py             ← User Profile CRUD endpoints
    │   └── auction_api.py          ← Auction, tracking pixels, analytics & logs
    │
    ├── database/                   ← Data access layer
    │   ├── __init__.py
    │   ├── postgres.py             ← SQLAlchemy engine (Postgres → SQLite fallback)
    │   ├── models.py               ← ORM table definitions (5 tables)
    │   └── seed.py                 ← Startup data seeder (5 campaigns, 5 users)
    │
    ├── schemas/                    ← Pydantic request/response validation
    │   ├── __init__.py
    │   ├── campaign.py             ← CampaignCreate / CampaignResponse
    │   ├── user.py                 ← UserCreate / UserResponse
    │   └── auction.py              ← BidRequest / BidResponse / AdCreativeResponse
    │
    ├── bidding/                    ← RTB auction engine
    │   ├── __init__.py
    │   ├── bidding_engine.py       ← Full auction lifecycle orchestrator
    │   ├── ranking_engine.py       ← Jaccard + CTR scoring functions
    │   └── budget_manager.py       ← Atomic spend checks and deductions
    │
    ├── cache/                      ← Caching abstraction
    │   ├── __init__.py
    │   └── redis_cache.py          ← Redis client + LocalCache fallback
    │
    ├── fraud/                      ← Fraud and safety layer
    │   ├── __init__.py
    │   └── fraud_detector.py       ← IP blacklist + sliding-window rate limiter
    │
    ├── analytics/                  ← Event telemetry and metrics
    │   ├── __init__.py
    │   ├── analytics_processor.py  ← Impression/click event handlers
    │   ├── kafka_producer.py       ← Mock Kafka producer (event streaming)
    │   └── kafka_consumer.py       ← Mock Kafka consumer (event processing)
    │
    └── dashboard/
        ├── __init__.py
        └── static/
            ├── index.html          ← Dark glassmorphic dashboard UI
            ├── style.css           ← Responsive CSS (dark mode, glass cards)
            └── app.js              ← Fetch API, Chart.js, RTB Simulator logic
```

### Database Tables (SQLAlchemy Models)

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `campaigns` | id, name, advertiser, budget, current_spend, bid_amount, target_age_min/max, target_location, target_interests, ad_title, ad_body, is_active | Stores all advertiser campaigns |
| `users` | id, name, age, location, interests | Stores publisher audience demographic profiles |
| `bid_history` | id, campaign_id, user_id, bid_amount, score, status, reason, timestamp | Full win/loss/filtered auction audit trail |
| `analytics` | id, campaign_id, impressions, clicks, revenue, timestamp | Daily aggregated performance metrics |
| `fraud_logs` | id, ip_address, user_id, reason, score, request_data, timestamp | Security anomaly and rate-limit event records |

---

## 4. Dependencies

Install all dependencies using:
```bash
pip install -r requirements.txt
```

### Core Dependencies

| Package | Version | Role |
|---------|---------|------|
| `fastapi` | ≥0.100 | Web framework — async REST APIs |
| `uvicorn` | ≥0.20 | ASGI server for running FastAPI |
| `sqlalchemy` | ≥2.0 | Database ORM for table definitions and queries |
| `psycopg2-binary` | ≥2.9 | PostgreSQL database adapter |
| `pydantic` | ≥2.0 | Request/response payload validation and serialization |
| `python-dotenv` | ≥1.0 | Loads environment variables from `.env` files |
| `redis` | ≥4.0 | Redis client for high-speed caching and rate limiting |
| `jinja2` | ≥3.0 | Template rendering (used internally by FastAPI) |
| `python-multipart` | ≥0.0.5 | Form data parsing support |

### Frontend (CDN — no install required)
| Library | Purpose |
|---------|---------|
| **Chart.js** | Interactive campaign spend and performance charts |
| **Lucide Icons** | Sidebar and UI icon set |
| **Google Fonts** — Outfit, Plus Jakarta Sans, Fira Code | Typography |

---

## 5. Setup Instructions

> The system uses a **Dual-Mode Fallback Policy**:  
> If PostgreSQL or Redis are not configured, it automatically falls back to **SQLite** for the database and a **thread-safe in-memory cache** for Redis operations — so the system runs immediately with zero extra infrastructure.

### Option A — Quickstart (SQLite + In-Memory, no extra services required)

```bash
# Step 1: Navigate to the project directory
cd AdSphere-RTB-System

# Step 2: Activate the virtual environment
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# Step 3: Install dependencies (if not already installed)
pip install -r requirements.txt

# Step 4 (Optional): Delete any stale database to start fresh
rm -f adsphere.db
```

That's it — the server will auto-create tables and seed sample data on first boot.

---

### Option B — Production Mode (PostgreSQL + Redis)

**Prerequisites:** PostgreSQL server running with a database named `adsphere`, and a Redis server.

1. Create a `.env` file in the project root:

```ini
# .env
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/adsphere
REDIS_URL=redis://localhost:6379/0
```

2. Create the database in PostgreSQL:
```sql
CREATE DATABASE adsphere;
```

3. The application will automatically run `CREATE TABLE IF NOT EXISTS` on startup — no manual migrations needed.

---

## 6. Execution Steps

### Step 1 — Start the Server

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8001
```

**Expected startup output:**
```
INFO:adsphere.database: Connecting to database at: sqlite:///adsphere.db
INFO:adsphere.database: Database connection established successfully.
INFO:adsphere.cache:    Falling back to In-Memory Cache.
INFO:adsphere.main:     Database tables initialized successfully.
INFO:adsphere.database.seed: Seeding default campaigns...
INFO:adsphere.database.seed: Successfully seeded 5 campaigns.
INFO:adsphere.database.seed: Successfully seeded 5 user profiles.
INFO:adsphere.database.seed: Successfully seeded baseline analytics metrics.
INFO:     Uvicorn running on http://127.0.0.1:8001
```

---

### Step 2 — Open the Dashboard

Open your browser and navigate to:

```
http://127.0.0.1:8001/
```

You will see the **AdSphere Dashboard** with:

| Tab | Contents |
|-----|---------|
| **Overview** | KPI cards (Revenue, Impressions, Clicks, CTR) + campaign spend bar chart |
| **Campaigns** | Live campaign cards with budget progress bars + create/edit form |
| **User Profiles** | Demographics table + add user form |
| **RTB Simulator** | Pick a user, choose IP and device, run a live auction, view hacker-terminal trace and rendered ad |
| **Logs & Fraud** | Bid history table (WON/LOST/FILTERED) + fraud security log |

---

### Step 3 — Browse the API Documentation

FastAPI auto-generates interactive Swagger documentation:

```
http://127.0.0.1:8001/docs
```

All endpoints are documented with request schemas, response models, and example payloads.

---

### Step 4 — Run the End-to-End Test Suite

With the server running, open a new terminal and run:

```bash
python tests/test_system.py
```

This covers **13 test groups** including:

| # | Test Area |
|---|-----------|
| 1 | Health check |
| 2 | Campaign CRUD (create, list, get, 404) |
| 3 | User Profile CRUD (create, list, get, 404) |
| 4 | Standard RTB auction (targeting match + scoring) |
| 5 | Location targeting filter |
| 6 | Non-existent user graceful handling |
| 7 | Fraud detection — blacklisted IP |
| 8 | Fraud detection — rate limiting (>10 req/10s) |
| 9 | Impression tracking pixel (1×1 GIF) |
| 10 | Click redirect tracker (HTTP 307) |
| 11 | Analytics summary (aggregate + per-campaign) |
| 12 | Auction history log entries |
| 13 | Budget deduction after winning bid |

**Example output:**
```
============================================================
  TEST: Standard RTB Auction (Targeting Match)
============================================================
  [PASS] POST /auction/request returns HTTP 200
  [PASS] Auction status is 'completed'
  [PASS] Winning ad returned
  [PASS] Auction completed in <500ms (8.98 ms)
  [PASS] Winning ad has impression tracking URL
  [PASS] Winning ad has click tracking URL
```

---

## 7. API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the HTML dashboard |
| `GET` | `/health` | Health check |
| `POST` | `/campaign` | Create a new campaign |
| `GET` | `/campaigns` | List all campaigns |
| `GET` | `/campaign/{id}` | Get a single campaign |
| `PUT` | `/campaign/{id}` | Update a campaign |
| `POST` | `/user` | Create a user profile |
| `GET` | `/users` | List all user profiles |
| `GET` | `/user/{id}` | Get a single user profile |
| `POST` | `/auction/request` | **Run a real-time bid auction** |
| `GET` | `/analytics/impression/{campaign_id}/{user_id}` | Impression tracking pixel |
| `GET` | `/analytics/click/{campaign_id}/{user_id}` | Click redirect tracker |
| `GET` | `/analytics/summary` | Aggregate + per-campaign analytics |
| `GET` | `/history` | Bid history log |
| `GET` | `/fraud` | Fraud and security event log |
| `GET` | `/docs` | Interactive Swagger API documentation |

---

## 8. Additional Project Details

### A. Auction Scoring Formula

The final **Ranking Score** that determines the auction winner is:

$$\text{Score} = \text{Bid Amount} \times \text{CTR} \times \text{Relevance Score}$$

Higher score wins. All three components are computed dynamically per auction.

---

### B. Relevance Score — Jaccard Similarity Index

Interest overlap between a user and a campaign is measured using the Jaccard Similarity Index:

$$\text{Jaccard Index} = \frac{|\text{User Interests} \cap \text{Campaign Interests}|}{|\text{User Interests} \cup \text{Campaign Interests}|}$$

The Jaccard range [0, 1] is then mapped to a relevance score [0.1, 1.0] to ensure no campaign is completely penalized:

$$\text{Relevance Score} = 0.1 + (\text{Jaccard Index} \times 0.9)$$

**Example:**
```
User interests:     {Technology, Gaming, Gadgets}
Campaign interests: {Technology, Gadgets}

Intersection: {Technology, Gadgets} → size = 2
Union:        {Technology, Gaming, Gadgets} → size = 3
Jaccard Index = 2/3 = 0.667
Relevance Score = 0.1 + (0.667 × 0.9) = 0.70
```

---

### C. Dynamic CTR — Laplace Smoothing

Rather than using a static CTR, AdSphere computes CTR dynamically from live analytics:

$$\text{CTR} = \frac{\text{Clicks}}{\text{Impressions}} \quad \text{(standard)}$$

To prevent division-by-zero for new campaigns with no impressions (the **cold-start problem**), a baseline CTR of 1% is used:

```python
if impressions <= 0:
    return 0.01  # 1% baseline CTR for new campaigns

ctr = clicks / impressions
return max(0.001, min(0.2, ctr))  # Clipped to [0.1%, 20%]
```

---

### D. Targeting Filter Pipeline

Before scoring, each campaign goes through a three-stage filter:

```
Campaign Pool
     │
     ▼
[1] Budget Filter ──── current_spend + bid_amount > budget? ─── FILTERED_BUDGET ──→ Skip
     │
     ▼
[2] Age Filter ───────  target_age_min ≤ user.age ≤ target_age_max? ── NO ──→ FILTERED_TARGETING
     │
     ▼
[3] Location Filter ── target_location == "All" OR matches user.location? ── NO ──→ FILTERED_TARGETING
     │
     ▼
[4] Interest Filter ── user_interests ∩ campaign_interests ≠ ∅? ── NO ──→ FILTERED_TARGETING
     │
     ▼
  ELIGIBLE → Proceed to scoring
```

All filtered campaigns are logged to `bid_history` with their filter reason for auditing.

---

### E. Fraud Detection Mechanisms

| Mechanism | Threshold | Action |
|-----------|-----------|--------|
| IP Blacklist | Exact match in blacklist set | Immediate block, score = 1.0 |
| Rate Limiting | > 10 requests per 10-second window | Block, score = 0.9 |
| Invalid User | user_id ≤ 0 | Block, score = 0.95 |

All blocked requests write a `FraudLog` record with IP, reason, severity score, and the raw request payload.

---

### F. Caching Architecture

| Cache Key Pattern | Data Cached | TTL |
|------------------|-------------|-----|
| `user:profile:{user_id}` | Full user profile JSON | 10 minutes |
| `campaign:budget:{campaign_id}` | Campaign total budget (float) | 1 hour |
| `campaign:spend:{campaign_id}` | Campaign current spend (float) | 1 hour |
| `campaign:stats:{campaign_id}` | `{impressions, clicks}` JSON | 2 minutes |
| `rate_limit:{ip_address}` | Request counter (int) | 10 seconds |

---

### G. Seed Data

On first boot, the system automatically populates:

**5 Campaigns:**

| Name | Advertiser | Budget | Bid | Target |
|------|-----------|--------|-----|--------|
| AdSphere Premium Tech Launch | AppleCorp | $1,500 | $3.50 | Mumbai, Age 18-45, Tech/Gaming |
| Fitness Fanatics Summer Sale | NikeFit | $800 | $1.80 | All, Age 15-40, Fitness/Sports |
| Luxury Auto Showcase | TeslaMotors | $3,000 | $5.00 | New York, Age 25-65, Cars/Luxury |
| Gamer Elite Pro Gear | RazerZone | $1,000 | $2.20 | All, Age 12-35, Gaming/Tech |
| Gourmet Espresso Promo | Starbucks | $500 | $1.20 | All, Age 18-60, Food/Lifestyle |

**5 User Profiles:**

| Name | Age | Location | Interests |
|------|-----|----------|-----------|
| Saksham | 22 | Mumbai | Technology, Gaming, Gadgets |
| Emma Watson | 32 | New York | Cars, Technology, Luxury |
| Virat Kohli | 37 | Mumbai | Sports, Fitness, Lifestyle |
| Sarah Jenkins | 19 | All | Gaming, Fitness |
| Rajesh Kumar | 48 | Mumbai | Food, Lifestyle, Coffee |
# adshpere
