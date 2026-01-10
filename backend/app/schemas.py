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


class DescriptionLanguage(str, Enum):
    """Valid description language values."""

    POLISH = "pl"
    ENGLISH = "en"


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

    category: str
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


class ExtractFromURLRequest(BaseModel):
    """Schema for extracting product info from URL."""

    url: HttpUrl


class ExtractFromURLResponse(BaseModel):
    """Schema for extracted product information."""

    title: str | None = None
    brand: str | None = None
    description: str | None = None
    price: float | None = None
    currency: str | None = None
    category: str | None = None
    condition: str | None = None
    size: str | None = None
    images: list[str] = []
    specifications: dict | None = None


# Analytics Schemas
class AnalyticsSummaryResponse(BaseModel):
    """Schema for analytics summary response."""

    total_listings: int
    active_listings: int
    sold_listings: int
    total_revenue: float
    avg_sale_price: float
    total_profit: float
    inventory_value: float
    negative_profit_count: int


class SalesOverTimeItem(BaseModel):
    """Schema for sales over time item."""

    period: str
    sales_count: int
    revenue: float


class ListingsCreatedOverTimeItem(BaseModel):
    """Schema for listings created over time item."""

    period: str
    listings_count: int


class SalesOverTimeResponse(BaseModel):
    """Schema for sales over time response."""

    sales: list[SalesOverTimeItem]
    listings_created: list[ListingsCreatedOverTimeItem]


class CategoryStatsItem(BaseModel):
    """Schema for category stats item."""

    category: str
    sales_count: int
    total_revenue: float


class BrandStatsItem(BaseModel):
    """Schema for brand stats item."""

    brand: str
    sales_count: int
    total_revenue: float


class ProfitableItemStats(BaseModel):
    """Schema for profitable item stats."""

    id: int
    title: str | None
    category: str | None
    brand: str | None
    sale_price: float
    initial_cost: float
    profit: float


class FastSellingItemStats(BaseModel):
    """Schema for fast-selling item stats."""

    id: int
    title: str | None
    category: str | None
    brand: str | None
    posted_at: str | None
    sold_at: str | None
    days_to_sell: float | None


class BestSellersResponse(BaseModel):
    """Schema for best sellers response."""

    best_categories: list[CategoryStatsItem]
    best_brands: list[BrandStatsItem]
    most_profitable: list[ProfitableItemStats]
    fastest_selling: list[FastSellingItemStats]


class InventoryCategoryItem(BaseModel):
    """Schema for inventory category item."""

    category: str
    total_value: float
    items_count: int
    avg_price: float


class InventoryValueResponse(BaseModel):
    """Schema for inventory value response."""

    total_value: float
    total_items: int
    avg_time_to_sell_days: float | None
    by_category: list[InventoryCategoryItem]
