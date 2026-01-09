"""API routes for listing management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.post("/add-by-url", response_model=schemas.ListingResponse, status_code=201)
async def add_listing_by_url(
    listing_data: schemas.AddListingByURL,
    db: Session = Depends(get_db),
):
    """Add listing by pasting URL."""
    # Extract external ID from URL path
    url_path = listing_data.url.path
    if not url_path:
        raise HTTPException(status_code=400, detail="Invalid URL: missing path")

    external_id = url_path.split("/")[-1]
    if not external_id:
        raise HTTPException(status_code=400, detail="Invalid URL: cannot extract listing ID")

    # Check if listing already exists
    existing = crud.get_listing_by_external_id(db, external_id)
    if existing:
        raise HTTPException(status_code=400, detail="Listing already exists")

    # TODO: Implement scraping logic in Phase 2
    # For now, create minimal listing
    listing_create = schemas.ListingCreate(
        platform=listing_data.platform,
        external_id=external_id,
        url=str(listing_data.url),
        initial_cost=listing_data.initial_cost,
    )

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
