"""Scraper service for fetching similar items from OLX and Vinted."""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SimilarItem:
    """Similar item found on marketplace."""

    platform: str
    title: str
    price: float
    url: str
    similarity_score: float = 0.0


class ScraperService:
    """Scrapes OLX and Vinted for similar items."""

    def __init__(self) -> None:
        self.rate_limit = settings.scrape_rate_limit
        self._last_request_time: float = 0.0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        import time

        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        self._last_request_time = time.time()

    async def find_similar_items(
        self,
        search_query: str,
        category: str | None = None,
        brand: str | None = None,
        max_results: int = 10,
    ) -> list[SimilarItem]:
        """Find similar items on both platforms."""
        olx_task = self._search_olx(search_query, category, max_results // 2)
        vinted_task = self._search_vinted(search_query, category, brand, max_results // 2)

        olx_items, vinted_items = await asyncio.gather(
            olx_task, vinted_task, return_exceptions=True
        )

        results: list[SimilarItem] = []
        if not isinstance(olx_items, BaseException):
            results.extend(olx_items)
        else:
            logger.error("OLX search failed: %s", olx_items)

        if not isinstance(vinted_items, BaseException):
            results.extend(vinted_items)
        else:
            logger.error("Vinted search failed: %s", vinted_items)

        # Calculate similarity scores
        for item in results:
            item.similarity_score = self._calculate_similarity(search_query, item.title)

        # Sort by similarity
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:max_results]

    async def _search_olx(
        self,
        query: str,
        category: str | None,
        max_results: int,
    ) -> list[SimilarItem]:
        """Search OLX for similar items."""
        await self._apply_rate_limit()

        search_url = f"https://www.olx.pl/oferty/q-{quote_plus(query)}/"

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                response = await client.get(search_url, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                items = []

                # OLX listing structure: div[data-cy="l-card"]
                listings = soup.find_all("div", {"data-cy": "l-card"})[:max_results]

                for listing in listings:
                    try:
                        # Title and URL
                        title_elem = listing.find("h6")
                        if not title_elem:
                            continue

                        link_elem = listing.find("a", href=True)
                        if not link_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        url = urljoin("https://www.olx.pl", str(link_elem["href"]))

                        # Price
                        price_elem = listing.find("p", {"data-testid": "ad-price"})
                        if not price_elem:
                            continue

                        price_text = price_elem.get_text(strip=True)
                        price = self._parse_price(price_text)

                        if price > 0:
                            items.append(
                                SimilarItem(
                                    platform="olx",
                                    title=title,
                                    price=price,
                                    url=url,
                                )
                            )

                    except Exception as e:
                        logger.warning("Failed to parse OLX listing: %s", e)
                        continue

                logger.info("Found %d items on OLX", len(items))
                return items

        except Exception as e:
            logger.error("OLX search failed: %s", e)
            return []

    async def _search_vinted(
        self,
        query: str,
        category: str | None,
        brand: str | None,
        max_results: int,
    ) -> list[SimilarItem]:
        """Search Vinted for similar items."""
        await self._apply_rate_limit()

        # Build search query
        search_params = {"search_text": query}
        if brand:
            search_params["brand_ids[]"] = brand

        # Use catalog endpoint
        search_url = "https://www.vinted.pl/catalog"

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                response = await client.get(search_url, params=search_params, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                items = []

                # Vinted uses feed-grid__item class
                listings = soup.find_all("div", class_=lambda x: x and "feed-grid__item" in x)[
                    :max_results
                ]

                for listing in listings:
                    try:
                        # Find link
                        link_elem = listing.find("a", href=True)
                        if not link_elem:
                            continue

                        url = urljoin("https://www.vinted.pl", str(link_elem["href"]))

                        # Title
                        title_elem = listing.find(class_=lambda x: x and "ItemBox_title" in str(x))
                        if not title_elem:
                            continue
                        title = title_elem.get_text(strip=True)

                        # Price
                        price_elem = listing.find(class_=lambda x: x and "ItemBox_price" in str(x))
                        if not price_elem:
                            continue

                        price_text = price_elem.get_text(strip=True)
                        price = self._parse_price(price_text)

                        if price > 0:
                            items.append(
                                SimilarItem(
                                    platform="vinted",
                                    title=title,
                                    price=price,
                                    url=url,
                                )
                            )

                    except Exception as e:
                        logger.warning("Failed to parse Vinted listing: %s", e)
                        continue

                logger.info("Found %d items on Vinted", len(items))
                return items

        except Exception as e:
            logger.error("Vinted search failed: %s", e)
            return []

    def _parse_price(self, price_text: str) -> float:
        """Parse price from text."""
        # Remove currency symbols while keeping digits, commas, dots and spaces
        cleaned = re.sub(r"[^\d,.\s]", "", price_text)
        # Handle Polish format (1 234,56 or 1.234,56) by removing thousand separators
        cleaned = cleaned.replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _calculate_similarity(self, query: str, title: str) -> float:
        """Calculate basic similarity score between query and title."""
        query_lower = query.lower()
        title_lower = title.lower()

        # Split into words
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())

        # Calculate Jaccard similarity
        if not query_words or not title_words:
            return 0.0

        intersection = query_words & title_words
        union = query_words | title_words

        return len(intersection) / len(union)


class PriceSuggestionService:
    """Calculates price suggestions based on similar items."""

    def __init__(self, scraper: ScraperService) -> None:
        self.scraper = scraper

    async def suggest_price(
        self,
        search_query: str,
        category: str | None = None,
        brand: str | None = None,
        condition: str | None = None,
    ) -> dict[str, Any]:
        """Suggest price based on similar items.

        Args:
            search_query: Text to search for similar items
            category: Optional category filter
            brand: Optional brand filter
            condition: Item condition - one of: new, like_new, good, fair, poor
                      Determines price percentile (new=90th, like_new=80th, good=60th,
                      fair=40th, poor=20th). Defaults to 'good' if not provided.

        Returns:
            Dict containing suggested_price, min/max/median prices, sample_size,
            and list of similar_items with similarity scores.
        """
        similar_items = await self.scraper.find_similar_items(
            search_query, category, brand, max_results=20
        )

        if not similar_items:
            return {
                "suggested_price": None,
                "min_price": None,
                "max_price": None,
                "median_price": None,
                "sample_size": 0,
                "similar_items": [],
            }

        prices = [item.price for item in similar_items]
        prices.sort()

        # Calculate statistics
        min_price = min(prices)
        max_price = max(prices)
        median_price = prices[len(prices) // 2]

        # Suggest price based on condition using array indexing approximation of percentiles
        # Note: This uses simplified percentile calculation via array position
        # For N sorted prices: idx = int(N * percentile_fraction)
        condition_multiplier = {
            "new": 0.9,  # Approximates 90th percentile
            "like_new": 0.8,  # Approximates 80th percentile
            "good": 0.6,  # Approximates 60th percentile
            "fair": 0.4,  # Approximates 40th percentile
            "poor": 0.2,  # Approximates 20th percentile
        }.get(condition or "good", 0.6)

        percentile_idx = int(condition_multiplier * (len(prices) - 1))
        suggested_price = prices[percentile_idx]

        return {
            "suggested_price": round(suggested_price, 2),
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "median_price": round(median_price, 2),
            "sample_size": len(similar_items),
            "similar_items": [
                {
                    "platform": item.platform,
                    "title": item.title,
                    "price": item.price,
                    "url": item.url,
                    "similarity_score": round(item.similarity_score, 2),
                }
                for item in similar_items[:5]  # Top 5 most similar
            ],
        }
