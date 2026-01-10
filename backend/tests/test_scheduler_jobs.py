"""Test scheduler job functions."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models import JobExecution, Listing, PriceHistory
from app.scheduler import cleanup_old_data, refresh_active_listings, scrape_competitor_prices


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.commit = MagicMock()
    db.close = MagicMock()
    db.query = MagicMock()
    return db


@pytest.fixture
def mock_session_local(mock_db):
    """Mock SessionLocal."""
    with patch("app.scheduler.SessionLocal") as mock:
        mock.return_value = mock_db
        yield mock


class TestRefreshActiveListings:
    """Test refresh_active_listings job function."""

    def test_refresh_success(self, mock_session_local, mock_db):
        """Test successful refresh of active listings."""
        # Setup
        mock_execution = JobExecution(
            id=1,
            job_id="refresh_listings",
            job_name="Refresh active listings",
            status="running",
            started_at=datetime.utcnow(),
        )
        mock_listings = [
            Listing(id=1, platform="olx", url="http://olx.pl/test1", title="Test 1"),
            Listing(id=2, platform="vinted", url="http://vinted.com/test2", title="Test 2"),
        ]

        with (
            patch("app.scheduler.create_job_execution") as mock_create,
            patch("app.scheduler.get_listings") as mock_get,
            patch("app.scheduler.update_job_execution") as mock_update,
        ):
            mock_create.return_value = mock_execution
            mock_get.return_value = mock_listings

            # Execute
            refresh_active_listings()

            # Verify
            mock_create.assert_called_once_with(
                mock_db, "refresh_listings", "Refresh active listings"
            )
            mock_get.assert_called_once()
            mock_update.assert_called_once()

            # Check result data
            call_args = mock_update.call_args
            assert call_args[0][0] == mock_db
            assert call_args[0][1] == 1  # execution.id
            assert call_args[0][2] == "success"
            result_data = call_args[1]["result_data"]
            assert result_data["total_listings"] == 2
            assert result_data["updated"] == 2
            assert result_data["errors"] == 0

            mock_db.close.assert_called_once()

    def test_refresh_error_handling(self, mock_session_local, mock_db):
        """Test error handling in refresh job."""
        mock_execution = JobExecution(
            id=1,
            job_id="refresh_listings",
            job_name="Refresh active listings",
            status="running",
            started_at=datetime.utcnow(),
        )

        with (
            patch("app.scheduler.create_job_execution") as mock_create,
            patch("app.scheduler.get_listings") as mock_get,
            patch("app.scheduler.update_job_execution") as mock_update,
        ):
            mock_create.return_value = mock_execution
            mock_get.side_effect = Exception("Database error")

            # Execute
            refresh_active_listings()

            # Verify error handling
            mock_update.assert_called_once_with(mock_db, 1, "error", error_message="Database error")
            mock_db.close.assert_called_once()


class TestScrapeCompetitorPrices:
    """Test scrape_competitor_prices job function."""

    def test_scrape_success(self, mock_session_local, mock_db):
        """Test successful competitor price scraping."""
        mock_execution = JobExecution(
            id=2,
            job_id="competitor_prices",
            job_name="Scrape competitor prices",
            status="running",
            started_at=datetime.utcnow(),
        )
        mock_listing = Listing(
            id=1,
            platform="olx",
            url="http://olx.pl/test",
            title="iPhone 13",
            brand="Apple",
            category="electronics",
        )

        class MockSimilarItem:
            platform = "vinted"
            url = "http://vinted.com/item"
            title = "iPhone 13 Pro"
            price = 2000.0
            similarity_score = 0.85

        with (
            patch("app.scheduler.create_job_execution") as mock_create,
            patch("app.scheduler.get_listings") as mock_get,
            patch("app.scheduler.ScraperService") as mock_scraper_cls,
            patch("app.scheduler.create_competitor_price") as mock_create_price,
            patch("app.scheduler.update_job_execution") as mock_update,
        ):
            mock_create.return_value = mock_execution
            mock_get.return_value = [mock_listing]

            mock_scraper = MagicMock()
            mock_scraper_cls.return_value = mock_scraper

            # Mock async method properly
            async def mock_find_similar(*args, **kwargs):
                return [MockSimilarItem()]

            mock_scraper.find_similar_items.side_effect = mock_find_similar

            # Execute
            scrape_competitor_prices()

            # Verify
            mock_create.assert_called_once_with(
                mock_db, "competitor_prices", "Scrape competitor prices"
            )
            mock_get.assert_called_once()
            mock_create_price.assert_called_once()
            mock_update.assert_called_once()

            # Check result data
            call_args = mock_update.call_args
            result_data = call_args[1]["result_data"]
            assert result_data["total_listings"] == 1
            assert result_data["total_competitors_found"] == 1
            assert result_data["errors"] == 0

            mock_db.close.assert_called_once()

    def test_scrape_skips_listing_without_title(self, mock_session_local, mock_db):
        """Test scraping skips listings without title/brand."""
        mock_execution = JobExecution(
            id=2,
            job_id="competitor_prices",
            job_name="Scrape competitor prices",
            status="running",
            started_at=datetime.utcnow(),
        )
        mock_listing = Listing(
            id=1,
            platform="olx",
            url="http://olx.pl/test",
            title=None,
            brand=None,
        )

        with (
            patch("app.scheduler.create_job_execution") as mock_create,
            patch("app.scheduler.get_listings") as mock_get,
            patch("app.scheduler.ScraperService"),
            patch("app.scheduler.create_competitor_price") as mock_create_price,
            patch("app.scheduler.update_job_execution") as mock_update,
        ):
            mock_create.return_value = mock_execution
            mock_get.return_value = [mock_listing]

            # Execute
            scrape_competitor_prices()

            # Verify no competitors were created
            mock_create_price.assert_not_called()

            # Check result data shows listing was skipped
            call_args = mock_update.call_args
            result_data = call_args[1]["result_data"]
            assert result_data["total_competitors_found"] == 0


class TestCleanupOldData:
    """Test cleanup_old_data job function."""

    def test_cleanup_success(self, mock_session_local, mock_db):
        """Test successful cleanup of old data."""
        mock_execution = JobExecution(
            id=3,
            job_id="cleanup",
            job_name="Cleanup old data",
            status="running",
            started_at=datetime.utcnow(),
        )

        # Mock query chains
        mock_price_history_query = MagicMock()
        mock_price_history_query.filter.return_value = mock_price_history_query
        mock_price_history_query.delete.return_value = 50

        mock_listing_query = MagicMock()
        mock_listing_query.filter.return_value = mock_listing_query
        mock_listing_query.delete.return_value = 10

        def query_side_effect(model):
            if model == PriceHistory:
                return mock_price_history_query
            elif model == Listing:
                return mock_listing_query
            return MagicMock()

        mock_db.query.side_effect = query_side_effect

        with (
            patch("app.scheduler.create_job_execution") as mock_create,
            patch("app.scheduler.delete_old_competitor_prices") as mock_delete_comp,
            patch("app.scheduler.update_job_execution") as mock_update,
        ):
            mock_create.return_value = mock_execution
            mock_delete_comp.return_value = 100

            # Execute
            cleanup_old_data()

            # Verify
            mock_create.assert_called_once_with(mock_db, "cleanup", "Cleanup old data")
            mock_delete_comp.assert_called_once_with(mock_db, days=30)

            # Verify price history cleanup
            assert mock_price_history_query.delete.call_count == 1
            mock_db.commit.assert_called()

            # Verify listings cleanup
            assert mock_listing_query.delete.call_count == 1

            # Check result data
            call_args = mock_update.call_args
            result_data = call_args[1]["result_data"]
            assert result_data["competitor_prices_deleted"] == 100
            assert result_data["price_history_deleted"] == 50
            assert result_data["listings_deleted"] == 10

            mock_db.close.assert_called_once()

    def test_cleanup_error_handling(self, mock_session_local, mock_db):
        """Test error handling in cleanup job."""
        mock_execution = JobExecution(
            id=3,
            job_id="cleanup",
            job_name="Cleanup old data",
            status="running",
            started_at=datetime.utcnow(),
        )

        with (
            patch("app.scheduler.create_job_execution") as mock_create,
            patch("app.scheduler.delete_old_competitor_prices") as mock_delete,
            patch("app.scheduler.update_job_execution") as mock_update,
        ):
            mock_create.return_value = mock_execution
            mock_delete.side_effect = Exception("Cleanup failed")

            # Execute
            cleanup_old_data()

            # Verify error handling
            mock_update.assert_called_once_with(mock_db, 3, "error", error_message="Cleanup failed")
            mock_db.close.assert_called_once()
