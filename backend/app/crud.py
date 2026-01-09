"""CRUD operations for database models."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Listing
from app.schemas import ListingCreate, ListingMarkSold, ListingUpdate


def get_listing(db: Session, listing_id: int) -> Listing | None:
    """Get listing by ID."""
    return db.query(Listing).filter(Listing.id == listing_id).first()


def get_listing_by_external_id(db: Session, external_id: str) -> Listing | None:
    """Get listing by external ID."""
    return db.query(Listing).filter(Listing.external_id == external_id).first()


def get_listings(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    platform: str | None = None,
    status: str | None = None,
) -> list[Listing]:
    """Get all listings with optional filters."""
    query = db.query(Listing)

    if platform:
        query = query.filter(Listing.platform == platform)
    if status:
        query = query.filter(Listing.status == status)

    return query.offset(skip).limit(limit).all()


def create_listing(db: Session, listing: ListingCreate) -> Listing:
    """Create a new listing."""
    db_listing = Listing(**listing.model_dump())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing


def update_listing(db: Session, listing_id: int, listing: ListingUpdate) -> Listing | None:
    """Update an existing listing."""
    db_listing = get_listing(db, listing_id)
    if not db_listing:
        return None

    update_data = listing.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_listing, field, value)

    db_listing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_listing)
    return db_listing


def mark_listing_sold(db: Session, listing_id: int, sold_data: ListingMarkSold) -> Listing | None:
    """Mark listing as sold."""
    db_listing = get_listing(db, listing_id)
    if not db_listing:
        return None

    db_listing.status = "sold"
    db_listing.sale_price = sold_data.sale_price
    db_listing.sold_at = sold_data.sold_at or datetime.utcnow()
    db_listing.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_listing)
    return db_listing


def delete_listing(db: Session, listing_id: int) -> bool:
    """Delete a listing."""
    db_listing = get_listing(db, listing_id)
    if not db_listing:
        return False

    db.delete(db_listing)
    db.commit()
    return True
