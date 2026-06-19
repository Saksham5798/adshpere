from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import json

class CampaignBase(BaseModel):
    name: str = Field(..., example="Tech Enthusiasts Ad")
    advertiser: str = Field(..., example="GadgetCorp")
    budget: float = Field(..., gt=0, example=1000.0)
    bid_amount: float = Field(..., gt=0, example=2.50)
    target_age_min: int = Field(default=0, ge=0, le=120)
    target_age_max: int = Field(default=100, ge=0, le=120)
    target_location: str = Field(default="All", example="Mumbai")
    target_interests: List[str] = Field(default=[], example=["Technology", "Gaming"])
    ad_title: str = Field(default="Great Gadgets Sale", example="Latest Smartwatches 50% Off!")
    ad_body: str = Field(default="Buy the best smartwatches on the market today.", example="Shop our premium smartwatch collection with real-time health trackers and 7-day battery life.")
    ad_creative_url: str = Field(default="https://picsum.photos/300/250", example="https://picsum.photos/300/250")

class CampaignCreate(CampaignBase):
    pass

class CampaignResponse(CampaignBase):
    id: int
    current_spend: float
    is_active: bool

    class Config:
        from_attributes = True

    # Validator to parse database JSON-string format back to Pydantic List[str]
    @field_validator("target_interests", mode="before")
    @classmethod
    def parse_interests(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return [i.strip() for i in value.replace("[", "").replace("]", "").replace('"', '').split(",") if i.strip()]
        return value
