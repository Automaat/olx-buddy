"""Test scraper service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.scraper import PriceSuggestionService, ScraperService, SimilarItem


@pytest.fixture
def scraper():
    """Create scraper service instance."""
    return ScraperService()


@pytest.fixture
def price_service(scraper):
    """Create price suggestion service instance."""
    return PriceSuggestionService(scraper)


class TestScraperService:
    """Test ScraperService class."""

    @pytest.mark.asyncio
    async def test_rate_limit(self, scraper):
        """Test rate limiting is applied."""
        scraper.rate_limit = 0.1
        scraper._last_request_time = 0.0

        start = asyncio.get_event_loop().time()
        await scraper._apply_rate_limit()
        await scraper._apply_rate_limit()
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_search_olx_success(self, scraper):
        """Test successful OLX search."""
        html_content = """
        <div data-cy="l-card">
            <h4>Test Item 1</h4>
            <a href="/item/1">Link</a>
            <p data-testid="ad-price">100 zł</p>
        </div>
        <div data-cy="l-card">
            <h4>Test Item 2</h4>
            <a href="/item/2">Link</a>
            <p data-testid="ad-price">200,50 zł</p>
        </div>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scraper._search_olx("test query", None, 10)

            assert len(results) == 2
            assert results[0].platform == "olx"
            assert results[0].title == "Test Item 1"
            assert results[0].price == 100.0
            assert results[0].url == "https://www.olx.pl/item/1"
            assert results[1].price == 200.5

    @pytest.mark.asyncio
    async def test_search_olx_no_results(self, scraper):
        """Test OLX search with no results."""
        html_content = "<html><body>No results</body></html>"

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scraper._search_olx("test", None, 10)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_olx_http_error(self, scraper):
        """Test OLX search with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )

            results = await scraper._search_olx("test", None, 10)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_olx_invalid_listing(self, scraper):
        """Test OLX search with invalid listing structure."""
        html_content = """
        <div data-cy="l-card">
            <h4>Valid Item</h4>
            <a href="/item/1">Link</a>
            <p data-testid="ad-price">100 zł</p>
        </div>
        <div data-cy="l-card">
            <h4>Invalid Item - No Price</h4>
            <a href="/item/2">Link</a>
        </div>
        <div data-cy="l-card">
            <p data-testid="ad-price">150 zł</p>
        </div>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scraper._search_olx("test", None, 10)
            assert len(results) == 1
            assert results[0].title == "Valid Item"

    @pytest.mark.asyncio
    async def test_search_vinted_success(self, scraper):
        """Test successful Vinted search."""
        html_content = """
        <div class="feed-grid__item">
            <a href="/item/1">
                <div class="ItemBox_title">Vinted Item 1</div>
                <div class="ItemBox_price">50 zł</div>
            </a>
        </div>
        <div class="feed-grid__item">
            <a href="/item/2">
                <div class="ItemBox_title">Vinted Item 2</div>
                <div class="ItemBox_price">75,50 zł</div>
            </a>
        </div>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scraper._search_vinted("test", None, "brand", 10)

            assert len(results) == 2
            assert results[0].platform == "vinted"
            assert results[0].title == "Vinted Item 1"
            assert results[0].price == 50.0
            assert results[1].price == 75.5

    @pytest.mark.asyncio
    async def test_search_vinted_no_results(self, scraper):
        """Test Vinted search with no results."""
        html_content = "<html><body>No items found</body></html>"

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scraper._search_vinted("test", None, None, 10)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_vinted_http_error(self, scraper):
        """Test Vinted search with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )

            results = await scraper._search_vinted("test", None, None, 10)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_vinted_invalid_listing(self, scraper):
        """Test Vinted search with invalid listing structure."""
        html_content = """
        <div class="feed-grid__item">
            <a href="/item/1">
                <div class="ItemBox_title">Valid Item</div>
                <div class="ItemBox_price">100 zł</div>
            </a>
        </div>
        <div class="feed-grid__item">
            <a href="/item/2">
                <div class="ItemBox_title">No Price Item</div>
            </a>
        </div>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scraper._search_vinted("test", None, None, 10)
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_similar_items_both_platforms(self, scraper):
        """Test finding similar items from both platforms."""
        with (
            patch.object(scraper, "_search_olx") as mock_olx,
            patch.object(scraper, "_search_vinted") as mock_vinted,
        ):
            mock_olx.return_value = [
                SimilarItem("olx", "Item 1", 100.0, "http://olx.pl/1"),
                SimilarItem("olx", "Item 2", 200.0, "http://olx.pl/2"),
            ]
            mock_vinted.return_value = [
                SimilarItem("vinted", "Item 3", 150.0, "http://vinted.pl/3"),
            ]

            results = await scraper.find_similar_items("test query", None, None, 10)

            assert len(results) == 3
            assert all(item.similarity_score >= 0 for item in results)

    @pytest.mark.asyncio
    async def test_find_similar_items_one_platform_fails(self, scraper):
        """Test finding items when one platform fails."""
        with (
            patch.object(scraper, "_search_olx") as mock_olx,
            patch.object(scraper, "_search_vinted") as mock_vinted,
        ):
            mock_olx.return_value = [
                SimilarItem("olx", "Item 1", 100.0, "http://olx.pl/1"),
            ]
            mock_vinted.side_effect = Exception("Vinted failed")

            results = await scraper.find_similar_items("test", None, None, 10)

            assert len(results) == 1
            assert results[0].platform == "olx"

    @pytest.mark.asyncio
    async def test_find_similar_items_sorted_by_similarity(self, scraper):
        """Test items are sorted by similarity score."""
        with (
            patch.object(scraper, "_search_olx") as mock_olx,
            patch.object(scraper, "_search_vinted") as mock_vinted,
        ):
            mock_olx.return_value = [
                SimilarItem("olx", "completely different", 100.0, "http://olx.pl/1"),
            ]
            mock_vinted.return_value = [
                SimilarItem("vinted", "laptop gaming", 150.0, "http://vinted.pl/2"),
            ]

            results = await scraper.find_similar_items("laptop", None, None, 10)

            assert results[0].similarity_score > results[1].similarity_score

    def test_parse_price_basic(self, scraper):
        """Test basic price parsing."""
        assert scraper._parse_price("100 zł") == 100.0
        assert scraper._parse_price("200,50 zł") == 200.5
        assert scraper._parse_price("1 234,56 zł") == 1234.56

    def test_parse_price_various_formats(self, scraper):
        """Test price parsing with various formats."""
        assert scraper._parse_price("1.234,56 zł") == 1234.56
        assert scraper._parse_price("PLN 50") == 50.0
        assert scraper._parse_price("25") == 25.0
        assert scraper._parse_price("99,99 €") == 99.99

    def test_parse_price_invalid(self, scraper):
        """Test invalid price returns 0."""
        assert scraper._parse_price("") == 0.0
        assert scraper._parse_price("abc") == 0.0
        assert scraper._parse_price("free") == 0.0

    def test_calculate_similarity_exact_match(self, scraper):
        """Test similarity calculation for exact match."""
        score = scraper._calculate_similarity("laptop gaming", "laptop gaming")
        assert score == 1.0

    def test_calculate_similarity_partial_match(self, scraper):
        """Test similarity calculation for partial match."""
        score = scraper._calculate_similarity("laptop gaming", "laptop for gaming setup")
        assert 0.4 < score < 1.0

    def test_calculate_similarity_no_match(self, scraper):
        """Test similarity calculation for no match."""
        score = scraper._calculate_similarity("laptop", "phone tablet")
        assert score == 0.0

    def test_calculate_similarity_empty(self, scraper):
        """Test similarity calculation with empty strings."""
        assert scraper._calculate_similarity("", "laptop") == 0.0
        assert scraper._calculate_similarity("laptop", "") == 0.0
        assert scraper._calculate_similarity("", "") == 0.0

    def test_calculate_similarity_case_insensitive(self, scraper):
        """Test similarity is case insensitive."""
        score1 = scraper._calculate_similarity("LAPTOP", "laptop")
        score2 = scraper._calculate_similarity("laptop", "laptop")
        assert score1 == score2 == 1.0

    @pytest.mark.asyncio
    async def test_scrape_olx_listing_success(self, scraper):
        """Test successful OLX listing scraping."""
        html_content = """
        <html>
        <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Lego minifigurki spiderman Spider-Man",
          "image": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
          ],
          "url": "https://www.olx.pl/d/oferta/lego-CID88-ID18PrbS.html",
          "description": "Lego minifigurki spiderman",
          "category": "https://www.olx.pl/dla-dzieci/zabawki/klocki/klocki-plastikowe/",
          "sku": "1046602772",
          "offers": {
            "@type": "Offer",
            "priceCurrency": "PLN",
            "price": 10,
            "itemCondition": "https://schema.org/UsedCondition"
          }
        }
        </script>
        </head>
        <body></body>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await scraper.scrape_olx_listing("https://www.olx.pl/d/oferta/lego-test.html")

            assert result["title"] == "Lego minifigurki spiderman Spider-Man"
            assert result["description"] == "Lego minifigurki spiderman"
            assert result["price"] == 10.0
            assert result["currency"] == "PLN"
            assert result["category"] == "Klocki Plastikowe"
            assert result["condition"] == "good"
            assert result["external_id"] == "1046602772"
            assert result["images"] is not None
            assert "image_0" in result["images"]
            assert "image_1" in result["images"]

    @pytest.mark.asyncio
    async def test_scrape_olx_listing_new_condition(self, scraper):
        """Test OLX scraping with new condition."""
        html_content = """
        <html>
        <head>
        <script type="application/ld+json">
        {
          "@type": "Product",
          "name": "Test Item",
          "offers": {
            "priceCurrency": "PLN",
            "price": 100,
            "itemCondition": "https://schema.org/NewCondition"
          }
        }
        </script>
        </head>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await scraper.scrape_olx_listing("https://www.olx.pl/test.html")

            assert result["condition"] == "new"

    @pytest.mark.asyncio
    async def test_scrape_olx_listing_no_json_ld(self, scraper):
        """Test OLX scraping with no JSON-LD data."""
        html_content = "<html><body>No JSON-LD data</body></html>"

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(ValueError, match="No JSON-LD data found"):
                await scraper.scrape_olx_listing("https://www.olx.pl/test.html")

    @pytest.mark.asyncio
    async def test_scrape_olx_listing_invalid_json(self, scraper):
        """Test OLX scraping with invalid JSON data."""
        html_content = """
        <html>
        <script type="application/ld+json">
        {invalid json}
        </script>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(ValueError, match="Invalid JSON data"):
                await scraper.scrape_olx_listing("https://www.olx.pl/test.html")

    @pytest.mark.asyncio
    async def test_scrape_olx_listing_missing_title(self, scraper):
        """Test OLX scraping with missing title."""
        html_content = """
        <html>
        <script type="application/ld+json">
        {
          "offers": {
            "price": 100,
            "priceCurrency": "PLN"
          }
        }
        </script>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(ValueError, match="Missing title"):
                await scraper.scrape_olx_listing("https://www.olx.pl/test.html")

    @pytest.mark.asyncio
    async def test_scrape_olx_listing_missing_offers(self, scraper):
        """Test OLX scraping with missing offers."""
        html_content = """
        <html>
        <script type="application/ld+json">
        {
          "name": "Test Item"
        }
        </script>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(ValueError, match="Missing or invalid offers"):
                await scraper.scrape_olx_listing("https://www.olx.pl/test.html")

    @pytest.mark.asyncio
    async def test_scrape_olx_listing_http_error(self, scraper):
        """Test OLX scraping with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )

            with pytest.raises(httpx.HTTPError):
                await scraper.scrape_olx_listing("https://www.olx.pl/test.html")


class TestPriceSuggestionService:
    """Test PriceSuggestionService class."""

    @pytest.mark.asyncio
    async def test_suggest_price_with_items(self, price_service, scraper):
        """Test price suggestion with similar items found."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            mock_find.return_value = [
                SimilarItem("olx", "Item 1", 100.0, "http://olx.pl/1"),
                SimilarItem("olx", "Item 2", 200.0, "http://olx.pl/2"),
                SimilarItem("vinted", "Item 3", 150.0, "http://vinted.pl/3"),
            ]

            result = await price_service.suggest_price("laptop", None, None, "good")

            assert result["suggested_price"] is not None
            assert result["min_price"] == 100.0
            assert result["max_price"] == 200.0
            assert result["median_price"] == 150.0
            assert result["sample_size"] == 3
            assert len(result["similar_items"]) == 3

    @pytest.mark.asyncio
    async def test_suggest_price_no_items(self, price_service, scraper):
        """Test price suggestion with no similar items found."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            mock_find.return_value = []

            result = await price_service.suggest_price("laptop", None, None, None)

            assert result["suggested_price"] is None
            assert result["min_price"] is None
            assert result["max_price"] is None
            assert result["median_price"] is None
            assert result["sample_size"] == 0
            assert result["similar_items"] == []

    @pytest.mark.asyncio
    async def test_suggest_price_condition_new(self, price_service, scraper):
        """Test price suggestion for new condition."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            mock_find.return_value = [
                SimilarItem("olx", f"Item {i}", float(i * 10), f"http://olx.pl/{i}")
                for i in range(1, 21)
            ]

            result = await price_service.suggest_price("laptop", None, None, "new")

            # New condition should suggest 90th percentile
            assert result["suggested_price"] >= result["median_price"]

    @pytest.mark.asyncio
    async def test_suggest_price_condition_poor(self, price_service, scraper):
        """Test price suggestion for poor condition."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            mock_find.return_value = [
                SimilarItem("olx", f"Item {i}", float(i * 10), f"http://olx.pl/{i}")
                for i in range(1, 21)
            ]

            result = await price_service.suggest_price("laptop", None, None, "poor")

            # Poor condition should suggest 20th percentile
            assert result["suggested_price"] <= result["median_price"]

    @pytest.mark.asyncio
    async def test_suggest_price_all_conditions(self, price_service, scraper):
        """Test price suggestions for all condition types."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            items = [
                SimilarItem("olx", f"Item {i}", float(i * 10), f"http://olx.pl/{i}")
                for i in range(1, 21)
            ]
            mock_find.return_value = items

            conditions = ["new", "like_new", "good", "fair", "poor"]
            results = []

            for condition in conditions:
                result = await price_service.suggest_price("laptop", None, None, condition)
                results.append(result["suggested_price"])

            # Prices should decrease from new to poor
            assert results == sorted(results, reverse=True)

    @pytest.mark.asyncio
    async def test_suggest_price_default_condition(self, price_service, scraper):
        """Test price suggestion with default condition (good)."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            mock_find.return_value = [
                SimilarItem("olx", f"Item {i}", float(i * 10), f"http://olx.pl/{i}")
                for i in range(1, 11)
            ]

            result = await price_service.suggest_price("laptop", None, None, None)

            # Default condition is "good" (60th percentile)
            assert result["suggested_price"] is not None

    @pytest.mark.asyncio
    async def test_suggest_price_with_category_and_brand(self, price_service, scraper):
        """Test price suggestion with category and brand filters."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            mock_find.return_value = [
                SimilarItem("olx", "Item 1", 100.0, "http://olx.pl/1"),
            ]

            await price_service.suggest_price("laptop", "electronics", "Dell", "good")

            mock_find.assert_called_once()
            call_args = mock_find.call_args
            assert call_args[0][0] == "laptop"
            assert call_args[0][1] == "electronics"
            assert call_args[0][2] == "Dell"

    @pytest.mark.asyncio
    async def test_suggest_price_top_5_similar_items(self, price_service, scraper):
        """Test that only top 5 similar items are returned."""
        with patch.object(scraper, "find_similar_items") as mock_find:
            mock_find.return_value = [
                SimilarItem("olx", f"Item {i}", float(i * 10), f"http://olx.pl/{i}")
                for i in range(1, 21)
            ]

            result = await price_service.suggest_price("laptop", None, None, "good")

            assert len(result["similar_items"]) == 5
            assert result["sample_size"] == 20
