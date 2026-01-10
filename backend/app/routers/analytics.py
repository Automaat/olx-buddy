"""API routes for analytics and reporting."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.analytics import (
    get_analytics_summary,
    get_best_sellers,
    get_inventory_value,
    get_listings_created_over_time,
    get_sales_over_time,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=schemas.AnalyticsSummaryResponse)
async def analytics_summary(db: Session = Depends(get_db)):
    """Get overall analytics summary.

    Returns:
    - Total revenue
    - Total listings (active/sold)
    - Avg sale price
    - Total profit
    - Inventory value
    """
    return get_analytics_summary(db)


@router.get("/sales-over-time", response_model=schemas.SalesOverTimeResponse)
async def sales_over_time(
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get time series data for sales and listings created.

    Args:
    - period: Grouping period (daily/weekly/monthly)
    - days: Number of days to look back

    Returns:
    - Sales over time
    - Revenue over time
    - Listings created over time
    """
    sales = get_sales_over_time(db, period=period, days=days)
    listings_created = get_listings_created_over_time(db, period=period, days=days)

    return {
        "sales": sales,
        "listings_created": listings_created,
    }


@router.get("/best-sellers", response_model=schemas.BestSellersResponse)
async def best_sellers(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get best-selling categories, brands, and items.

    Args:
    - limit: Number of items per category

    Returns:
    - Best-selling categories
    - Best-selling brands
    - Fastest-selling items
    - Most profitable items
    """
    return get_best_sellers(db, limit=limit)


@router.get("/inventory-value", response_model=schemas.InventoryValueResponse)
async def inventory_value(db: Session = Depends(get_db)):
    """Get current inventory value breakdown.

    Returns:
    - Total value of active listings
    - Breakdown by category
    - Average time to sell
    """
    return get_inventory_value(db)


@router.get("/price-monitoring/{listing_id}")
async def price_monitoring(
    listing_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get competitor prices for a specific listing.

    Args:
    - listing_id: ID of the listing
    - limit: Number of competitor prices to return

    Returns competitor prices sorted by scraped_at (most recent first).
    """
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    competitor_prices = crud.get_competitor_prices(db, listing_id, limit=limit)

    prices_list = []
    for cp in competitor_prices:
        price_val = 0.0
        price = cast(float | None, cp.price)
        if price is not None:
            price_val = float(price)

        similarity_val = 0.0
        similarity = cast(float | None, cp.similarity_score)
        if similarity is not None:
            similarity_val = float(similarity)

        prices_list.append(
            {
                "id": cp.id,
                "platform": cp.platform,
                "competitor_url": cp.competitor_url,
                "competitor_title": cp.competitor_title,
                "price": price_val,
                "similarity_score": similarity_val,
                "scraped_at": cp.scraped_at.isoformat(),
            }
        )

    return {
        "listing_id": listing_id,
        "competitor_prices": prices_list,
    }


@router.get("/price-monitoring/{listing_id}/history")
async def price_history(
    listing_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get price history for a specific listing.

    Args:
    - listing_id: ID of the listing
    - limit: Number of price history entries to return

    Returns price history sorted by recorded_at (most recent first).
    """
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    price_history = crud.get_price_history(db, listing_id, limit=limit)

    history_list = []
    for ph in price_history:
        price = cast(float, ph.price)
        history_list.append(
            {
                "id": ph.id,
                "price": float(price),
                "recorded_at": ph.recorded_at.isoformat(),
            }
        )

    return {
        "listing_id": listing_id,
        "price_history": history_list,
    }
