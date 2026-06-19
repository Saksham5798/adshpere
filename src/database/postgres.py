import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load env variables
load_dotenv()

logger = logging.getLogger("adsphere.database")
logging.basicConfig(level=logging.INFO)

# Default to SQLite if Postgres is not specified
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///adsphere.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    logger.info(f"Connecting to database at: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    # Test connection
    with engine.connect() as conn:
        logger.info("Database connection established successfully.")
except Exception as e:
    logger.error(f"Failed to connect to database at {DATABASE_URL}. Error: {e}")
    # Fallback to sqlite if connection fails
    if not DATABASE_URL.startswith("sqlite"):
        logger.warning("Falling back to local SQLite database: sqlite:///adsphere.db")
        DATABASE_URL = "sqlite:///adsphere.db"
        connect_args = {"check_same_thread": False}
        engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    """Dependency injection helper for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
