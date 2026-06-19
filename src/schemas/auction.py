from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class BidRequest(BaseModel):
    user_id: int = Field(..., example=1)
    ip_address: str = Field(..., example="192.168.1.50")
    device: Optional[str] = Field(default="Desktop", example="Mobile")
    page_url: Optional[str] = Field(default="https://ad-network.com/demo", example="https://news.yahoo.com")

class AdCreativeResponse(BaseModel):
    campaign_id: int
    advertiser: str
    bid_amount: float
    ad_title: str
    ad_body: str
    ad_creative_url: str
    impression_tracking_url: str
    click_tracking_url: str

class BidResponse(BaseModel):
    auction_status: str = Field(..., example="completed")  # "completed", "no_matching_campaigns", "fraud_blocked"
    winning_ad: Optional[AdCreativeResponse] = None
    auction_duration_ms: float = Field(..., example=12.45)
    trace: List[str] = Field(default=[], description="Trace of auction campaign filtering and ranking details")
