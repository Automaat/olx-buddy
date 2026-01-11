"""CRUD operations for database models."""

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import CompetitorPrice, JobExecution, Listing, PriceHistory
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


# PriceHistory CRUD
def create_price_history(db: Session, listing_id: int, price: float) -> PriceHistory:
    """Create price history entry."""
    db_price_history = PriceHistory(listing_id=listing_id, price=price)
    db.add(db_price_history)
    db.commit()
    db.refresh(db_price_history)
    return db_price_history


def get_price_history(db: Session, listing_id: int, limit: int = 100) -> list[PriceHistory]:
    """Get price history for a listing."""
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.listing_id == listing_id)
        .order_by(desc(PriceHistory.recorded_at))
        .limit(limit)
        .all()
    )


# CompetitorPrice CRUD
def create_competitor_price(
    db: Session,
    listing_id: int,
    platform: str,
    competitor_url: str,
    competitor_title: str,
    price: float,
    similarity_score: float,
) -> CompetitorPrice:
    """Create competitor price entry."""
    db_competitor_price = CompetitorPrice(
        listing_id=listing_id,
        platform=platform,
        competitor_url=competitor_url,
        competitor_title=competitor_title,
        price=price,
        similarity_score=similarity_score,
    )
    db.add(db_competitor_price)
    db.commit()
    db.refresh(db_competitor_price)
    return db_competitor_price


def get_competitor_prices(db: Session, listing_id: int, limit: int = 50) -> list[CompetitorPrice]:
    """Get competitor prices for a listing."""
    return (
        db.query(CompetitorPrice)
        .filter(CompetitorPrice.listing_id == listing_id)
        .order_by(desc(CompetitorPrice.scraped_at))
        .limit(limit)
        .all()
    )


def delete_old_competitor_prices(db: Session, days: int = 30) -> int:
    """Delete competitor prices older than specified days."""
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    deleted = (
        db.query(CompetitorPrice)
        .filter(CompetitorPrice.scraped_at < cutoff_date)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


def delete_competitor_prices_for_listing(db: Session, listing_id: int) -> int:
    """Delete all competitor prices for a specific listing."""
    deleted = (
        db.query(CompetitorPrice)
        .filter(CompetitorPrice.listing_id == listing_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


# JobExecution CRUD
def create_job_execution(db: Session, job_id: str, job_name: str) -> JobExecution:
    """Create job execution entry."""
    db_job_execution = JobExecution(
        job_id=job_id,
        job_name=job_name,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(db_job_execution)
    db.commit()
    db.refresh(db_job_execution)
    return db_job_execution


def update_job_execution(
    db: Session,
    execution_id: int,
    status: str,
    error_message: str | None = None,
    result_data: dict | None = None,
) -> JobExecution | None:
    """Update job execution status."""
    db_job_execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
    if not db_job_execution:
        return None

    db_job_execution.status = status
    db_job_execution.completed_at = datetime.utcnow()
    if error_message:
        db_job_execution.error_message = error_message
    if result_data:
        db_job_execution.result_data = result_data

    db.commit()
    db.refresh(db_job_execution)
    return db_job_execution


def get_job_executions(
    db: Session, job_id: str | None = None, limit: int = 50
) -> list[JobExecution]:
    """Get job execution history."""
    query = db.query(JobExecution)
    if job_id:
        query = query.filter(JobExecution.job_id == job_id)

    return query.order_by(desc(JobExecution.started_at)).limit(limit).all()
