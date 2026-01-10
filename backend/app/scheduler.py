"""APScheduler configuration and jobs."""

import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.crud import (
    create_competitor_price,
    create_job_execution,
    delete_old_competitor_prices,
    get_listings,
    update_job_execution,
)
from app.database import SessionLocal
from app.models import Listing, PriceHistory
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def refresh_active_listings():
    """Refresh data for all active listings.

    This job fetches current data for active listings from their platforms.
    Updates: price, views, status (if sold/removed).
    Records price history when price changes.

    Note: Currently placeholder - full implementation requires platform API integration
    or advanced scraping of individual listing pages.
    """
    db = SessionLocal()
    execution = None

    try:
        execution = create_job_execution(db, "refresh_listings", "Refresh active listings")
        logger.info("Starting refresh_active_listings job (execution_id=%d)", execution.id)

        # Get all active listings
        active_listings = get_listings(
            db, status="active", limit=settings.scheduler_job_listing_limit
        )
        logger.info("Found %d active listings to refresh", len(active_listings))

        updated_count = 0
        error_count = 0

        for listing in active_listings:
            try:
                # Placeholder: In production, scrape listing detail page
                # For now, just log that we would refresh it
                logger.debug(
                    "Would refresh listing %d (%s): %s",
                    listing.id,
                    listing.platform,
                    listing.url,
                )
                # Example update (placeholder):
                # new_data = await scrape_listing_detail(listing.url)
                # if new_data.price != listing.price:
                #     create_price_history(db, listing.id, new_data.price)
                # update_listing(db, listing.id, ListingUpdate(**new_data))
                updated_count += 1

            except Exception as e:
                logger.error("Failed to refresh listing %d: %s", listing.id, e)
                error_count += 1
                continue

        result = {
            "total_listings": len(active_listings),
            "updated": updated_count,
            "errors": error_count,
        }

        update_job_execution(db, execution.id, "success", result_data=result)
        logger.info("Refresh job completed: %s", result)

    except Exception as e:
        logger.exception("refresh_active_listings job failed")
        if execution:
            update_job_execution(db, execution.id, "error", error_message=str(e))
    finally:
        db.close()


def scrape_competitor_prices():
    """Scrape competitor prices for market analysis.

    For each active listing:
    - Extract search keywords (brand + category)
    - Search both platforms for similar items
    - Store competitor prices with similarity scores
    - Rate limit: handled by ScraperService
    """
    db = SessionLocal()
    execution = None

    try:
        execution = create_job_execution(db, "competitor_prices", "Scrape competitor prices")
        logger.info("Starting scrape_competitor_prices job (execution_id=%d)", execution.id)

        # Get all active listings
        active_listings = get_listings(
            db, status="active", limit=settings.scheduler_job_listing_limit
        )
        logger.info("Found %d active listings to scrape competitors for", len(active_listings))

        scraper = ScraperService()

        async def process_listings() -> tuple[int, int]:
            total_competitors_inner = 0
            error_count_inner = 0

            for listing in active_listings:
                try:
                    # Build search query from listing data
                    search_query = listing.title or ""
                    if listing.brand:
                        search_query = f"{listing.brand} {search_query}".strip()

                    if not search_query:
                        logger.warning("Listing %d has no title/brand, skipping", listing.id)
                        continue

                    logger.info(
                        "Searching competitors for listing %d: %s", listing.id, search_query
                    )

                    # Find similar items
                    similar_items = await scraper.find_similar_items(
                        search_query=search_query,
                        category=listing.category,
                        brand=listing.brand,
                        max_results=10,
                    )

                    # Store competitor prices
                    for item in similar_items:
                        create_competitor_price(
                            db=db,
                            listing_id=listing.id,
                            platform=item.platform,
                            competitor_url=item.url,
                            competitor_title=item.title,
                            price=item.price,
                            similarity_score=item.similarity_score,
                        )
                        total_competitors_inner += 1

                    logger.info(
                        "Found %d competitors for listing %d", len(similar_items), listing.id
                    )

                except Exception as e:
                    logger.error("Failed to scrape competitors for listing %d: %s", listing.id, e)
                    error_count_inner += 1
                    continue

            return total_competitors_inner, error_count_inner

        total_competitors, error_count = asyncio.run(process_listings())

        result = {
            "total_listings": len(active_listings),
            "total_competitors_found": total_competitors,
            "errors": error_count,
        }

        update_job_execution(db, execution.id, "success", result_data=result)
        logger.info("Competitor scraping job completed: %s", result)

    except Exception as e:
        logger.exception("scrape_competitor_prices job failed")
        if execution:
            update_job_execution(db, execution.id, "error", error_message=str(e))
    finally:
        db.close()


def cleanup_old_data():
    """Cleanup old competitor prices and history.

    - Delete competitor prices >30 days old
    - Delete price history >90 days old
    - Clean up removed listings >30 days old
    """
    db = SessionLocal()
    execution = None

    try:
        execution = create_job_execution(db, "cleanup", "Cleanup old data")
        logger.info("Starting cleanup_old_data job (execution_id=%d)", execution.id)

        # Delete old competitor prices (>30 days)
        competitor_deleted = delete_old_competitor_prices(db, days=30)
        logger.info("Deleted %d old competitor prices", competitor_deleted)

        # Delete old price history (>90 days)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        price_history_deleted = (
            db.query(PriceHistory)
            .filter(PriceHistory.recorded_at < cutoff_date)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Deleted %d old price history entries", price_history_deleted)

        # Delete removed listings (>30 days)
        removed_cutoff = datetime.utcnow() - timedelta(days=30)
        listings_deleted = (
            db.query(Listing)
            .filter(Listing.status == "removed")
            .filter(Listing.updated_at < removed_cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Deleted %d old removed listings", listings_deleted)

        result = {
            "competitor_prices_deleted": competitor_deleted,
            "price_history_deleted": price_history_deleted,
            "listings_deleted": listings_deleted,
        }

        update_job_execution(db, execution.id, "success", result_data=result)
        logger.info("Cleanup job completed: %s", result)

    except Exception as e:
        logger.exception("cleanup_old_data job failed")
        if execution:
            update_job_execution(db, execution.id, "error", error_message=str(e))
    finally:
        db.close()


# Schedule jobs
scheduler.add_job(
    func=refresh_active_listings,
    trigger="interval",
    minutes=30,
    id="refresh_listings",
    name="Refresh active listings",
)

scheduler.add_job(
    func=scrape_competitor_prices,
    trigger="cron",
    hour=3,
    id="competitor_prices",
    name="Scrape competitor prices",
)

scheduler.add_job(
    func=cleanup_old_data,
    trigger="cron",
    day_of_week="sun",
    hour=4,
    id="cleanup",
    name="Cleanup old data",
)
