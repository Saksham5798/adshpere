import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Database and seed utilities
from src.database.models import Base, engine, SessionLocal
from src.database.seed import seed_data

# Router API modules
from src.api.campaign_api import router as campaign_router
from src.api.user_api import router as user_router
from src.api.auction_api import router as auction_router

logger = logging.getLogger("adsphere.main")
logging.basicConfig(level=logging.INFO)

# Make sure tables are created (especially on first boot)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database tables: {e}")

app = FastAPI(
    title="AdSphere RTB System",
    description="Real-Time Advertising Bidding & Auction Platform",
    version="1.0"
)

# CORS middleware for local frontend development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed database with sample campaigns/users on startup
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        seed_data(db)
    except Exception as e:
        logger.error(f"Error seeding database on startup: {e}")
    finally:
        db.close()

# Include REST endpoints
app.include_router(campaign_router)
app.include_router(user_router)
app.include_router(auction_router)

# Mount frontend static files
# Ensure static directory exists
STATIC_DIR = os.path.join("src", "dashboard", "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount the static directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def home():
    """Serves the HTML dashboard at the root URL."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "project": "AdSphere",
        "status": "Running",
        "message": "To view the dashboard, index.html must be placed in src/dashboard/static"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected"
    }