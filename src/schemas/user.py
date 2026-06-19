from pydantic import BaseModel, Field, field_validator
from typing import List
import json

class UserBase(BaseModel):
    name: str = Field(..., example="Alice Johnson")
    age: int = Field(..., ge=0, le=120, example=28)
    location: str = Field(..., example="Mumbai")
    interests: List[str] = Field(default=[], example=["Technology", "Cars"])

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

    # Validator to parse database JSON-string format back to Pydantic List[str]
    @field_validator("interests", mode="before")
    @classmethod
    def parse_interests(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return [i.strip() for i in value.replace("[", "").replace("]", "").replace('"', '').split(",") if i.strip()]
        return value
