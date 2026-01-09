"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class ItemCondition(str, Enum):
    """Valid item condition values."""

    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class ListingBase(BaseModel):
    """Base schema for listing data."""

    platform: str = Field(..., max_length=20)
    external_id: str = Field(..., max_length=100)
    url: str
    title: str | None = None
    description: str | None = None
    price: float | None = None
    currency: str = Field(default="PLN", max_length=3)
    category: str | None = Field(None, max_length=100)
    brand: str | None = Field(None, max_length=100)
    condition: str | None = Field(None, max_length=50)
    size: str | None = Field(None, max_length=50)
    views: int = Field(default=0)
    images: dict | None = None
    platform_metadata: dict | None = None
    status: str = Field(default="active", max_length=20)
    posted_at: datetime | None = None
    initial_cost: float | None = None


class ListingCreate(ListingBase):
    """Schema for creating a new listing."""

    pass


class ListingUpdate(BaseModel):
    """Schema for updating a listing."""

    title: str | None = None
    description: str | None = None
    price: float | None = None
    currency: str | None = Field(None, max_length=3)
    category: str | None = Field(None, max_length=100)
    brand: str | None = Field(None, max_length=100)
    condition: str | None = Field(None, max_length=50)
    size: str | None = Field(None, max_length=50)
    views: int | None = None
    status: str | None = Field(None, max_length=20)
    initial_cost: float | None = None


class ListingResponse(ListingBase):
    """Schema for listing response."""

    id: int
    sale_price: float | None = None
    sold_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListingMarkSold(BaseModel):
    """Schema for marking listing as sold."""

    sale_price: float = Field(..., gt=0)
    sold_at: datetime | None = None


class AddListingByURL(BaseModel):
    """Schema for adding listing by URL."""

    url: HttpUrl
    platform: str = Field(..., pattern="^(vinted|olx)$")
    initial_cost: float | None = Field(None, gt=0)


class GenerateDescriptionRequest(BaseModel):
    """Schema for description generation request."""

    category: str = Field(..., max_length=50)
    brand: str | None = Field(None, max_length=100)
    condition: str | None = Field(None, max_length=50)
    size: str | None = Field(None, max_length=50)
    additional_details: str | None = None


class GenerateDescriptionResponse(BaseModel):
    """Schema for description generation response."""

    description: str
    suggested_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    median_price: float | None = None
    sample_size: int = 0
    similar_items: list[dict] = []


class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""

    image_paths: list[str]
    count: int


class CategoryResponse(BaseModel):
    """Schema for category list response."""

    categories: list[str]
