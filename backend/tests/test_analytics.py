"""Test analytics service and API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.crud import create_listing
from app.main import app
from app.models import CompetitorPrice, Listing, PriceHistory
from app.schemas import ListingCreate
from app.services.analytics import (
    get_analytics_summary,
    get_best_sellers,
    get_inventory_value,
    get_listings_created_over_time,
    get_sales_over_time,
)

client = TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def sample_listings():
    """Create sample listings for tests."""
    now = datetime.now(UTC)

    # Active listings
    active1 = Listing(
        id=1,
        platform="vinted",
        external_id="active1",
        url="https://vinted.pl/items/active1",
        title="Active Item 1",
        price=100.0,
        status="active",
        category="electronics",
        brand="Apple",
        initial_cost=50.0,
        created_at=now - timedelta(days=5),
    )

    active2 = Listing(
        id=2,
        platform="vinted",
        external_id="active2",
        url="https://vinted.pl/items/active2",
        title="Active Item 2",
        price=200.0,
        status="active",
        category="clothing",
        brand="Nike",
        initial_cost=100.0,
        created_at=now - timedelta(days=3),
    )

    # Sold listings
    sold1 = Listing(
        id=3,
        platform="vinted",
        external_id="sold1",
        url="https://vinted.pl/items/sold1",
        title="Sold Item 1",
        price=150.0,
        sale_price=150.0,
        status="sold",
        category="electronics",
        brand="Samsung",
        initial_cost=80.0,
        created_at=now - timedelta(days=30),
        posted_at=now - timedelta(days=28),
        sold_at=now - timedelta(days=5),
    )

    sold2 = Listing(
        id=4,
        platform="vinted",
        external_id="sold2",
        url="https://vinted.pl/items/sold2",
        title="Sold Item 2",
        price=300.0,
        sale_price=250.0,
        status="sold",
        category="clothing",
        brand="Adidas",
        initial_cost=150.0,
        created_at=now - timedelta(days=25),
        posted_at=now - timedelta(days=23),
        sold_at=now - timedelta(days=2),
    )

    # Sold with negative profit
    sold3 = Listing(
        id=5,
        platform="vinted",
        external_id="sold3",
        url="https://vinted.pl/items/sold3",
        title="Sold Item 3 (Loss)",
        price=100.0,
        sale_price=80.0,
        status="sold",
        category="furniture",
        brand="IKEA",
        initial_cost=120.0,
        created_at=now - timedelta(days=20),
        posted_at=now - timedelta(days=18),
        sold_at=now - timedelta(days=10),
    )

    # Fast selling item
    sold4 = Listing(
        id=6,
        platform="vinted",
        external_id="sold4",
        url="https://vinted.pl/items/sold4",
        title="Fast Sell Item",
        price=500.0,
        sale_price=450.0,
        status="sold",
        category="electronics",
        brand="Apple",
        initial_cost=300.0,
        created_at=now - timedelta(days=15),
        posted_at=now - timedelta(days=14),
        sold_at=now - timedelta(days=13),
    )

    return [active1, active2, sold1, sold2, sold3, sold4]


class TestAnalyticsSummary:
    """Test get_analytics_summary service function."""

    def test_analytics_summary_with_data(self, mock_db, sample_listings):
        """Test analytics summary with various listings."""
        # Setup mock query responses
        active_listings = [l for l in sample_listings if l.status == "active"]
        sold_listings = [l for l in sample_listings if l.status == "sold"]

        # Mock count queries
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock

        # Track call sequence for different queries
        call_count = [0]

        def count_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:  # active count
                return len(active_listings)
            else:  # sold count
                return len(sold_listings)

        filter_mock.count.side_effect = count_side_effect

        # Mock sold items revenue query
        sold_items_mock = MagicMock()
        sold_items_mock.total_revenue = 930.0  # 150 + 250 + 80 + 450
        sold_items_mock.avg_sale_price = 232.5

        # Mock profit query
        profit_mock = MagicMock()
        profit_mock.total_profit = 200.0  # (150-80) + (250-150) + (80-120) + (450-300)

        # Mock inventory value query
        inventory_mock = MagicMock()
        inventory_mock.total_value = 300.0  # 100 + 200

        # Configure first() to return different values based on call order
        first_calls = [sold_items_mock, profit_mock, inventory_mock]
        first_call_index = [0]

        def first_side_effect():
            result = first_calls[first_call_index[0]]
            first_call_index[0] += 1
            return result

        filter_mock.first.side_effect = first_side_effect

        # Mock negative profit count (scalar)
        filter_mock.scalar.return_value = 1

        result = get_analytics_summary(mock_db)

        assert result["total_listings"] == 6
        assert result["active_listings"] == 2
        assert result["sold_listings"] == 4
        assert result["total_revenue"] == 930.0
        assert result["avg_sale_price"] == 232.5
        assert result["total_profit"] == 200.0
        assert result["inventory_value"] == 300.0
        assert result["negative_profit_count"] == 1

    def test_analytics_summary_empty_db(self, mock_db):
        """Test analytics summary with no listings."""
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock

        # Mock all counts as 0
        filter_mock.count.return_value = 0

        # Mock empty results
        sold_items_mock = MagicMock()
        sold_items_mock.total_revenue = None
        sold_items_mock.avg_sale_price = None

        profit_mock = MagicMock()
        profit_mock.total_profit = None

        inventory_mock = MagicMock()
        inventory_mock.total_value = None

        first_calls = [sold_items_mock, profit_mock, inventory_mock]
        first_call_index = [0]

        def first_side_effect():
            result = first_calls[first_call_index[0]]
            first_call_index[0] += 1
            return result

        filter_mock.first.side_effect = first_side_effect
        filter_mock.scalar.return_value = 0

        result = get_analytics_summary(mock_db)

        assert result["total_listings"] == 0
        assert result["active_listings"] == 0
        assert result["sold_listings"] == 0
        assert result["total_revenue"] == 0.0
        assert result["avg_sale_price"] == 0.0
        assert result["total_profit"] == 0.0
        assert result["inventory_value"] == 0.0
        assert result["negative_profit_count"] == 0


class TestSalesOverTime:
    """Test get_sales_over_time service function."""

    def test_sales_over_time_daily(self, mock_db):
        """Test sales over time with daily grouping."""
        mock_result1 = MagicMock()
        mock_result1.period = datetime(2026, 1, 5, 0, 0, 0)
        mock_result1.sales_count = 2
        mock_result1.revenue = 400.0

        mock_result2 = MagicMock()
        mock_result2.period = datetime(2026, 1, 8, 0, 0, 0)
        mock_result2.sales_count = 1
        mock_result2.revenue = 150.0

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = [mock_result1, mock_result2]

        result = get_sales_over_time(mock_db, period="daily", days=30)

        assert len(result) == 2
        assert result[0]["sales_count"] == 2
        assert result[0]["revenue"] == 400.0
        assert result[1]["sales_count"] == 1
        assert result[1]["revenue"] == 150.0

    def test_sales_over_time_weekly(self, mock_db):
        """Test sales over time with weekly grouping."""
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = []

        result = get_sales_over_time(mock_db, period="weekly", days=90)

        assert result == []

    def test_sales_over_time_monthly(self, mock_db):
        """Test sales over time with monthly grouping."""
        mock_result = MagicMock()
        mock_result.period = datetime(2026, 1, 1, 0, 0, 0)
        mock_result.sales_count = 5
        mock_result.revenue = 1000.0

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = [mock_result]

        result = get_sales_over_time(mock_db, period="monthly", days=365)

        assert len(result) == 1
        assert result[0]["sales_count"] == 5
        assert result[0]["revenue"] == 1000.0


class TestListingsCreatedOverTime:
    """Test get_listings_created_over_time service function."""

    def test_listings_created_daily(self, mock_db):
        """Test listings created over time with daily grouping."""
        mock_result = MagicMock()
        mock_result.period = datetime(2026, 1, 10, 0, 0, 0)
        mock_result.listings_count = 3

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = [mock_result]

        result = get_listings_created_over_time(mock_db, period="daily", days=7)

        assert len(result) == 1
        assert result[0]["listings_count"] == 3

    def test_listings_created_monthly(self, mock_db):
        """Test listings created with monthly grouping."""
        mock_result = MagicMock()
        mock_result.period = datetime(2026, 1, 1, 0, 0, 0)
        mock_result.listings_count = 15

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = [mock_result]

        result = get_listings_created_over_time(mock_db, period="monthly", days=365)

        assert len(result) == 1
        assert result[0]["listings_count"] == 15

    def test_listings_created_empty(self, mock_db):
        """Test listings created with no results."""
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = []

        result = get_listings_created_over_time(mock_db, period="weekly", days=30)

        assert result == []


class TestBestSellers:
    """Test get_best_sellers service function."""

    def test_best_sellers_with_data(self, mock_db):
        """Test best sellers with various data."""
        # Mock categories
        cat1 = MagicMock()
        cat1.category = "electronics"
        cat1.sales_count = 10
        cat1.total_revenue = 2000.0

        # Mock brands
        brand1 = MagicMock()
        brand1.brand = "Apple"
        brand1.sales_count = 5
        brand1.total_revenue = 1500.0

        # Mock profitable items
        item1 = MagicMock()
        item1.id = 1
        item1.title = "iPhone"
        item1.category = "electronics"
        item1.brand = "Apple"
        item1.sale_price = 500.0
        item1.initial_cost = 300.0
        item1.profit = 200.0

        # Mock fast selling items
        fast1 = MagicMock()
        fast1.id = 2
        fast1.title = "Fast Item"
        fast1.category = "clothing"
        fast1.brand = "Nike"
        fast1.posted_at = datetime(2026, 1, 1, 0, 0, 0)
        fast1.sold_at = datetime(2026, 1, 2, 0, 0, 0)
        fast1.days_to_sell = 1.0

        # Setup mocks for categories and brands (with group_by)
        query_mock_grouped = MagicMock()
        filter_mock_grouped = MagicMock()
        group_mock = MagicMock()
        order_mock_grouped = MagicMock()
        limit_mock_grouped = MagicMock()

        query_mock_grouped.filter.return_value = filter_mock_grouped
        filter_mock_grouped.group_by.return_value = group_mock
        group_mock.order_by.return_value = order_mock_grouped
        order_mock_grouped.limit.return_value = limit_mock_grouped

        # Setup mocks for profitable and fastest (without group_by)
        query_mock_direct = MagicMock()
        filter_mock_direct = MagicMock()
        order_mock_direct = MagicMock()
        limit_mock_direct = MagicMock()

        query_mock_direct.filter.return_value = filter_mock_direct
        filter_mock_direct.order_by.return_value = order_mock_direct
        order_mock_direct.limit.return_value = limit_mock_direct

        # Return different query mocks based on call count
        query_call_count = [0]

        def query_side_effect(*args):
            query_call_count[0] += 1
            if query_call_count[0] <= 2:  # categories and brands
                return query_mock_grouped
            else:  # profitable and fastest items
                return query_mock_direct

        mock_db.query.side_effect = query_side_effect

        # Setup results
        grouped_call_count = [0]

        def grouped_all_side_effect():
            grouped_call_count[0] += 1
            if grouped_call_count[0] == 1:  # categories
                return [cat1]
            else:  # brands
                return [brand1]

        limit_mock_grouped.all.side_effect = grouped_all_side_effect

        direct_call_count = [0]

        def direct_all_side_effect():
            direct_call_count[0] += 1
            if direct_call_count[0] == 1:  # profitable items
                return [item1]
            else:  # fastest selling
                return [fast1]

        limit_mock_direct.all.side_effect = direct_all_side_effect

        result = get_best_sellers(mock_db, limit=10)

        assert len(result["best_categories"]) == 1
        assert result["best_categories"][0]["category"] == "electronics"
        assert result["best_categories"][0]["sales_count"] == 10

        assert len(result["best_brands"]) == 1
        assert result["best_brands"][0]["brand"] == "Apple"

        assert len(result["most_profitable"]) == 1
        assert result["most_profitable"][0]["profit"] == 200.0

        assert len(result["fastest_selling"]) == 1
        assert result["fastest_selling"][0]["days_to_sell"] == 1.0

    def test_best_sellers_empty(self, mock_db):
        """Test best sellers with no data."""
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        limit_mock = MagicMock()
        order_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = []

        result = get_best_sellers(mock_db, limit=5)

        assert result["best_categories"] == []
        assert result["best_brands"] == []
        assert result["most_profitable"] == []
        assert result["fastest_selling"] == []


class TestInventoryValue:
    """Test get_inventory_value service function."""

    def test_inventory_value_with_data(self, mock_db):
        """Test inventory value calculation."""
        # Mock total value
        total_mock = MagicMock()
        total_mock.total_value = 1000.0
        total_mock.total_items = 10

        # Mock category breakdown
        cat1 = MagicMock()
        cat1.category = "electronics"
        cat1.total_value = 600.0
        cat1.items_count = 6
        cat1.avg_price = 100.0

        # Mock avg time to sell
        avg_time_mock = MagicMock()
        avg_time_mock.avg_days = 15.5

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock

        # Setup first() to return different values
        first_calls = [total_mock, avg_time_mock]
        first_call_index = [0]

        def first_side_effect():
            result = first_calls[first_call_index[0]]
            first_call_index[0] += 1
            return result

        filter_mock.first.side_effect = first_side_effect

        # Setup category breakdown
        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = [cat1]

        result = get_inventory_value(mock_db)

        assert result["total_value"] == 1000.0
        assert result["total_items"] == 10
        assert result["avg_time_to_sell_days"] == 15.5
        assert len(result["by_category"]) == 1
        assert result["by_category"][0]["category"] == "electronics"

    def test_inventory_value_no_avg_time(self, mock_db):
        """Test inventory value when avg time to sell is None."""
        total_mock = MagicMock()
        total_mock.total_value = 500.0
        total_mock.total_items = 5

        avg_time_mock = MagicMock()
        avg_time_mock.avg_days = None

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock

        first_calls = [total_mock, avg_time_mock]
        first_call_index = [0]

        def first_side_effect():
            result = first_calls[first_call_index[0]]
            first_call_index[0] += 1
            return result

        filter_mock.first.side_effect = first_side_effect

        group_mock = MagicMock()
        filter_mock.group_by.return_value = group_mock
        order_mock = MagicMock()
        group_mock.order_by.return_value = order_mock
        order_mock.all.return_value = []

        result = get_inventory_value(mock_db)

        assert result["avg_time_to_sell_days"] is None


class TestAnalyticsEndpoints:
    """Test analytics API endpoints."""

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.get_analytics_summary")
    def test_analytics_summary_endpoint(self, mock_summary, mock_get_db):
        """Test GET /api/analytics/summary endpoint."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_summary.return_value = {
            "total_listings": 10,
            "active_listings": 6,
            "sold_listings": 4,
            "total_revenue": 1000.0,
            "avg_sale_price": 250.0,
            "total_profit": 400.0,
            "inventory_value": 600.0,
            "negative_profit_count": 1,
        }

        response = client.get("/api/analytics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_listings"] == 10
        assert data["total_revenue"] == 1000.0

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.get_sales_over_time")
    @patch("app.routers.analytics.get_listings_created_over_time")
    def test_sales_over_time_endpoint(
        self, mock_listings_created, mock_sales, mock_get_db
    ):
        """Test GET /api/analytics/sales-over-time endpoint."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_sales.return_value = [
            {"period": "2026-01-10", "sales_count": 5, "revenue": 500.0}
        ]
        mock_listings_created.return_value = [
            {"period": "2026-01-10", "listings_count": 3}
        ]

        response = client.get("/api/analytics/sales-over-time?period=daily&days=7")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sales"]) == 1
        assert len(data["listings_created"]) == 1
        assert data["sales"][0]["sales_count"] == 5

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.get_sales_over_time")
    @patch("app.routers.analytics.get_listings_created_over_time")
    def test_sales_over_time_invalid_period(
        self, mock_listings_created, mock_sales, mock_get_db
    ):
        """Test sales over time with invalid period parameter."""
        response = client.get("/api/analytics/sales-over-time?period=invalid")

        assert response.status_code == 422  # Validation error

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.get_best_sellers")
    def test_best_sellers_endpoint(self, mock_best_sellers, mock_get_db):
        """Test GET /api/analytics/best-sellers endpoint."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_best_sellers.return_value = {
            "best_categories": [
                {"category": "electronics", "sales_count": 10, "total_revenue": 2000.0}
            ],
            "best_brands": [
                {"brand": "Apple", "sales_count": 5, "total_revenue": 1500.0}
            ],
            "most_profitable": [],
            "fastest_selling": [],
        }

        response = client.get("/api/analytics/best-sellers?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["best_categories"]) == 1
        assert data["best_categories"][0]["category"] == "electronics"

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.get_inventory_value")
    def test_inventory_value_endpoint(self, mock_inventory, mock_get_db):
        """Test GET /api/analytics/inventory-value endpoint."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_inventory.return_value = {
            "total_value": 1000.0,
            "total_items": 10,
            "avg_time_to_sell_days": 15.5,
            "by_category": [
                {
                    "category": "electronics",
                    "total_value": 600.0,
                    "items_count": 6,
                    "avg_price": 100.0,
                }
            ],
        }

        response = client.get("/api/analytics/inventory-value")

        assert response.status_code == 200
        data = response.json()
        assert data["total_value"] == 1000.0
        assert data["total_items"] == 10

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.crud.get_listing")
    @patch("app.routers.analytics.crud.get_competitor_prices")
    def test_price_monitoring_endpoint(
        self, mock_get_prices, mock_get_listing, mock_get_db
    ):
        """Test GET /api/analytics/price-monitoring/{listing_id} endpoint."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock listing exists
        mock_listing = MagicMock()
        mock_listing.id = 1
        mock_get_listing.return_value = mock_listing

        # Mock competitor prices
        mock_price = MagicMock()
        mock_price.id = 1
        mock_price.platform = "olx"
        mock_price.competitor_url = "https://olx.pl/item/123"
        mock_price.competitor_title = "Similar Item"
        mock_price.price = 120.0
        mock_price.similarity_score = 0.85
        mock_price.scraped_at = datetime(2026, 1, 10, 12, 0, 0)

        mock_get_prices.return_value = [mock_price]

        response = client.get("/api/analytics/price-monitoring/1")

        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == 1
        assert len(data["competitor_prices"]) == 1
        assert data["competitor_prices"][0]["price"] == 120.0
        assert data["competitor_prices"][0]["similarity_score"] == 0.85

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.crud.get_listing")
    def test_price_monitoring_listing_not_found(self, mock_get_listing, mock_get_db):
        """Test price monitoring with non-existent listing."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_get_listing.return_value = None

        response = client.get("/api/analytics/price-monitoring/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Listing not found"

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.crud.get_listing")
    @patch("app.routers.analytics.crud.get_price_history")
    def test_price_history_endpoint(
        self, mock_get_history, mock_get_listing, mock_get_db
    ):
        """Test GET /api/analytics/price-monitoring/{listing_id}/history endpoint."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock listing exists
        mock_listing = MagicMock()
        mock_listing.id = 1
        mock_get_listing.return_value = mock_listing

        # Mock price history
        mock_history = MagicMock()
        mock_history.id = 1
        mock_history.price = 150.0
        mock_history.recorded_at = datetime(2026, 1, 9, 12, 0, 0)

        mock_get_history.return_value = [mock_history]

        response = client.get("/api/analytics/price-monitoring/1/history")

        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == 1
        assert len(data["price_history"]) == 1
        assert data["price_history"][0]["price"] == 150.0

    @patch("app.routers.analytics.get_db")
    @patch("app.routers.analytics.crud.get_listing")
    def test_price_history_listing_not_found(self, mock_get_listing, mock_get_db):
        """Test price history with non-existent listing."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_get_listing.return_value = None

        response = client.get("/api/analytics/price-monitoring/999/history")

        assert response.status_code == 404
        assert response.json()["detail"] == "Listing not found"
