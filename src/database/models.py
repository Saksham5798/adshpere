import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship
from src.database.postgres import Base, engine, SessionLocal

# Re-exporting for backward compatibility with existing main.py structure
__all__ = ["Base", "engine", "SessionLocal", "Campaign", "User", "BidHistory", "Analytics", "FraudLog"]

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Unnamed Campaign")
    advertiser = Column(String, nullable=False)
    budget = Column(Float, nullable=False)
    current_spend = Column(Float, default=0.0, nullable=False)
    bid_amount = Column(Float, nullable=False)
    
    # Targeting preferences
    target_age_min = Column(Integer, default=0, nullable=False)
    target_age_max = Column(Integer, default=100, nullable=False)
    target_location = Column(String, default="All", nullable=False)  # "All" or a specific country/city e.g., "Mumbai"
    target_interests = Column(String, default="[]", nullable=False)   # JSON string list of interest tags, e.g., '["Tech", "Cars"]'
    
    # Creative assets
    ad_title = Column(String, nullable=False, default="Sample Ad Title")
    ad_body = Column(String, nullable=False, default="Sample Ad Description Body")
    ad_creative_url = Column(String, nullable=False, default="https://picsum.photos/300/250")  # placeholder URL
    
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    bids = relationship("BidHistory", back_populates="campaign", cascade="all, delete-orphan")
    analytics_records = relationship("Analytics", back_populates="campaign", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    location = Column(String, nullable=False)
    interests = Column(String, default="[]", nullable=False)  # JSON string list of interest tags, e.g., '["Tech", "Cars"]'

    # Relationships
    bids = relationship("BidHistory", back_populates="user", cascade="all, delete-orphan")


class BidHistory(Base):
    __tablename__ = "bid_history"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bid_amount = Column(Float, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    status = Column(String, nullable=False)  # "WON", "LOST", "FILTERED_BUDGET", "FILTERED_TARGETING", "NO_CAMPAIGNS"
    reason = Column(String, nullable=True)    # reason for being filtered out, e.g. "Location mismatch"
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="bids")
    user = relationship("User", back_populates="bids")


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    revenue = Column(Float, default=0.0, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="analytics_records")


class FraudLog(Base):
    __tablename__ = "fraud_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String, nullable=False)
    request_data = Column(String, nullable=False)  # Raw JSON request data
    score = Column(Float, default=0.0, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


# Initialize tables
Base.metadata.create_all(bind=engine)