"""Test CRUD operations for new models."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.crud import (
    create_competitor_price,
    create_job_execution,
    create_price_history,
    delete_old_competitor_prices,
    get_competitor_prices,
    get_job_executions,
    get_price_history,
    update_job_execution,
)
from app.models import CompetitorPrice, JobExecution, Listing, PriceHistory
from app.schemas import ListingCreate


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def sample_listing(mock_db):
    """Create sample listing for tests."""
    listing_data = ListingCreate(
        platform="vinted",
        external_id="test123",
        url="https://vinted.pl/items/test123",
        title="Test Item",
        price=100.0,
    )
    listing = Listing(**listing_data.model_dump())
    listing.id = 1
    return listing


class TestPriceHistoryCRUD:
    """Test PriceHistory CRUD operations."""

    def test_create_price_history(self, mock_db):
        """Test creating price history entry."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda x: setattr(x, "id", 1)

        create_price_history(mock_db, listing_id=1, price=100.0)

        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called

    def test_get_price_history(self, mock_db):
        """Test getting price history for a listing."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        expected_history = [
            PriceHistory(id=1, listing_id=1, price=100.0, recorded_at=datetime.utcnow()),
            PriceHistory(
                id=2,
                listing_id=1,
                price=90.0,
                recorded_at=datetime.utcnow() - timedelta(days=1),
            ),
        ]
        mock_query.all.return_value = expected_history

        result = get_price_history(mock_db, listing_id=1, limit=100)

        assert len(result) == 2
        assert result[0].price == 100.0
        assert result[1].price == 90.0

    def test_get_price_history_default_limit(self, mock_db):
        """Test default limit of 100 for price history."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        get_price_history(mock_db, listing_id=1)

        mock_query.limit.assert_called_once_with(100)


class TestCompetitorPriceCRUD:
    """Test CompetitorPrice CRUD operations."""

    def test_create_competitor_price(self, mock_db):
        """Test creating competitor price entry."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda x: setattr(x, "id", 1)

        create_competitor_price(
            db=mock_db,
            listing_id=1,
            platform="olx",
            competitor_url="https://olx.pl/item/456",
            competitor_title="Similar Item",
            price=95.0,
            similarity_score=0.85,
        )

        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called

    def test_get_competitor_prices(self, mock_db):
        """Test getting competitor prices for a listing."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        expected_prices = [
            CompetitorPrice(
                id=1,
                listing_id=1,
                platform="olx",
                competitor_url="https://olx.pl/item/456",
                competitor_title="Similar Item",
                price=95.0,
                similarity_score=0.85,
                scraped_at=datetime.utcnow(),
            ),
        ]
        mock_query.all.return_value = expected_prices

        result = get_competitor_prices(mock_db, listing_id=1, limit=50)

        assert len(result) == 1
        assert result[0].platform == "olx"
        assert result[0].price == 95.0

    def test_get_competitor_prices_default_limit(self, mock_db):
        """Test default limit of 50 for competitor prices."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        get_competitor_prices(mock_db, listing_id=1)

        mock_query.limit.assert_called_once_with(50)

    def test_delete_old_competitor_prices(self, mock_db):
        """Test deleting old competitor prices."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = 10
        mock_db.commit.return_value = None

        result = delete_old_competitor_prices(mock_db, days=30)

        assert result == 10
        assert mock_db.commit.called

    def test_delete_old_competitor_prices_custom_days(self, mock_db):
        """Test deleting competitor prices with custom cutoff."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = 5
        mock_db.commit.return_value = None

        result = delete_old_competitor_prices(mock_db, days=7)

        assert result == 5


class TestJobExecutionCRUD:
    """Test JobExecution CRUD operations."""

    def test_create_job_execution(self, mock_db):
        """Test creating job execution entry."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda x: setattr(x, "id", 1)

        create_job_execution(
            mock_db, job_id="refresh_listings", job_name="Refresh active listings"
        )

        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called

    def test_update_job_execution_success(self, mock_db):
        """Test updating job execution with success status."""
        mock_execution = JobExecution(
            id=1,
            job_id="refresh_listings",
            job_name="Refresh active listings",
            status="running",
            started_at=datetime.utcnow(),
        )
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_execution
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = update_job_execution(
            mock_db,
            execution_id=1,
            status="success",
            result_data={"total_listings": 10, "updated": 10, "errors": 0},
        )

        assert result is not None
        assert result.status == "success"
        assert result.result_data == {"total_listings": 10, "updated": 10, "errors": 0}

    def test_update_job_execution_error(self, mock_db):
        """Test updating job execution with error status."""
        mock_execution = JobExecution(
            id=1,
            job_id="refresh_listings",
            job_name="Refresh active listings",
            status="running",
            started_at=datetime.utcnow(),
        )
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_execution
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = update_job_execution(
            mock_db, execution_id=1, status="error", error_message="Database connection failed"
        )

        assert result is not None
        assert result.status == "error"
        assert result.error_message == "Database connection failed"

    def test_update_job_execution_not_found(self, mock_db):
        """Test updating non-existent job execution."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = update_job_execution(mock_db, execution_id=999, status="success")

        assert result is None

    def test_get_job_executions_all(self, mock_db):
        """Test getting all job executions."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        expected_executions = [
            JobExecution(
                id=1,
                job_id="refresh_listings",
                job_name="Refresh active listings",
                status="success",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            ),
        ]
        mock_query.all.return_value = expected_executions

        result = get_job_executions(mock_db, limit=50)

        assert len(result) == 1
        assert result[0].job_id == "refresh_listings"

    def test_get_job_executions_by_job_id(self, mock_db):
        """Test getting executions for specific job."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        expected_executions = [
            JobExecution(
                id=1,
                job_id="cleanup",
                job_name="Cleanup old data",
                status="success",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            ),
        ]
        mock_query.all.return_value = expected_executions

        result = get_job_executions(mock_db, job_id="cleanup", limit=50)

        assert len(result) == 1
        assert result[0].job_id == "cleanup"

    def test_get_job_executions_default_limit(self, mock_db):
        """Test default limit of 50 for job executions."""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        get_job_executions(mock_db)

        mock_query.limit.assert_called_once_with(50)
