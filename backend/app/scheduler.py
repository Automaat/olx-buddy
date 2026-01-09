"""APScheduler configuration and jobs."""

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def refresh_active_listings():
    """Refresh data for all active listings."""
    # TODO: Implement
    pass


def scrape_competitor_prices():
    """Scrape competitor prices for market analysis."""
    # TODO: Implement
    pass


def cleanup_old_data():
    """Cleanup old competitor prices and history."""
    # TODO: Implement
    pass


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
