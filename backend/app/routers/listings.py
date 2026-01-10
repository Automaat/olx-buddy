"""API routes for listing management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.post("/add-by-url", response_model=schemas.ListingResponse, status_code=201)
async def add_listing_by_url(
    listing_data: schemas.AddListingByURL,
    db: Session = Depends(get_db),
):
    """Add listing by pasting URL."""
    url_str = str(listing_data.url)

    # Extract external ID from URL path
    url_path = listing_data.url.path
    if not url_path:
        raise HTTPException(status_code=400, detail="Invalid URL: missing path")

    # External ID is assumed to be in the last path segment (e.g., "CID88-ID18PrbS.html")
    external_id = url_path.split("/")[-1].replace(".html", "")
    if not external_id:
        raise HTTPException(status_code=400, detail="Invalid URL: cannot extract listing ID")

    # Check if listing already exists
    existing = crud.get_listing_by_external_id(db, external_id)
    if existing:
        raise HTTPException(status_code=400, detail="Listing already exists")

    # Scrape listing data
    scraper = ScraperService()
    scraped_data = None

    try:
        if listing_data.platform == "olx":
            scraped_data = await scraper.scrape_olx_listing(url_str)
            if scraped_data:
                logger.info("Scraped OLX listing: %s", scraped_data.get("title"))
        else:
            # Vinted scraping not yet implemented
            logger.warning("Vinted scraping not implemented, creating minimal listing")

    except ValueError as e:
        logger.warning("Failed to scrape listing from %s: %s", url_str, e)
        raise HTTPException(status_code=400, detail=f"Failed to scrape listing: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error scraping listing from %s", url_str)
        raise HTTPException(status_code=500, detail="Failed to fetch listing data") from e

    # Build listing data
    listing_create_data = {
        "platform": listing_data.platform,
        "external_id": (scraped_data.get("external_id") if scraped_data else None) or external_id,
        "url": url_str,
        "initial_cost": listing_data.initial_cost,
    }

    # Add scraped data if available
    if scraped_data:
        listing_create_data.update(
            {
                "title": scraped_data.get("title"),
                "description": scraped_data.get("description"),
                "price": scraped_data.get("price"),
                "currency": scraped_data.get("currency", "PLN"),
                "category": scraped_data.get("category"),
                "condition": scraped_data.get("condition"),
                "images": scraped_data.get("images"),
            }
        )

    listing_create = schemas.ListingCreate(**listing_create_data)
    return crud.create_listing(db, listing_create)


@router.get("", response_model=list[schemas.ListingResponse])
async def list_listings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    platform: str | None = Query(default=None, pattern="^(vinted|olx)$"),
    status: str | None = Query(default=None, pattern="^(active|sold|removed)$"),
    db: Session = Depends(get_db),
):
    """List all listings with filters."""
    return crud.get_listings(db, skip=skip, limit=limit, platform=platform, status=status)


@router.get("/{listing_id}", response_model=schemas.ListingResponse)
async def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
):
    """Get listing details."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.patch("/{listing_id}", response_model=schemas.ListingResponse)
async def update_listing(
    listing_id: int,
    listing_update: schemas.ListingUpdate,
    db: Session = Depends(get_db),
):
    """Update listing."""
    listing = crud.update_listing(db, listing_id, listing_update)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("/{listing_id}/mark-sold", response_model=schemas.ListingResponse)
async def mark_listing_sold(
    listing_id: int,
    sold_data: schemas.ListingMarkSold,
    db: Session = Depends(get_db),
):
    """Mark listing as sold."""
    listing = crud.mark_listing_sold(db, listing_id, sold_data)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.delete("/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
):
    """Remove listing from tracking."""
    success = crud.delete_listing(db, listing_id)
    if not success:
        raise HTTPException(status_code=404, detail="Listing not found")
    return None
