"""AI service for description generation using multiple providers."""

import base64
import ipaddress
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def _validate_url(url: str) -> None:
    """Validate URL to prevent SSRF attacks.

    Args:
        url: URL to validate

    Raises:
        ValueError: If URL is invalid or targets private/internal network
    """
    parsed = urlparse(url)

    # Only allow HTTP/HTTPS
    if parsed.scheme not in ("http", "https"):
        msg = f"Invalid URL scheme: {parsed.scheme}"
        raise ValueError(msg)

    # Get hostname
    hostname = parsed.hostname
    if not hostname:
        msg = "Invalid URL: no hostname"
        raise ValueError(msg)

    # Block localhost
    if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
        msg = "Access to localhost is not allowed"
        raise ValueError(msg)

    # Try to check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        # If it's an IP, check if it's private/loopback/link-local
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            msg = f"Access to private IP address is not allowed: {ip}"
            raise ValueError(msg)
        # Valid public IP, allow it
        return
    except ValueError as e:
        # If the error is from our security check, re-raise it
        if "not allowed" in str(e):
            raise
        # Otherwise it's not a valid IP address, continue to domain checks

    # Not an IP address, check for cloud metadata endpoints
    blocked_domains = [
        "169.254.169.254",  # AWS/Azure/GCP metadata
        "metadata.google.internal",
        "metadata",
    ]
    hostname_lower = hostname.lower()
    is_blocked = any(
        hostname_lower == domain or hostname_lower.endswith(f".{domain}")
        for domain in blocked_domains
    )
    if is_blocked:
        msg = f"Access to metadata endpoint is not allowed: {hostname}"
        raise ValueError(msg)


class AIService:
    """Handles AI-powered description generation with multiple provider support."""

    def __init__(self) -> None:
        self.openai_client: AsyncOpenAI | None = None
        self.anthropic_api_key: str | None = None
        self.ollama_base_url: str | None = None

        # Initialize available providers
        if settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("OpenAI client initialized")

        if settings.anthropic_api_key:
            self.anthropic_api_key = settings.anthropic_api_key
            logger.info("Anthropic API key configured")

        if settings.ollama_base_url:
            self.ollama_base_url = settings.ollama_base_url
            logger.info("Ollama base URL configured: %s", self.ollama_base_url)

    async def suggest_category(self, image_paths: list[str], language: str = "pl") -> str:
        """Suggest an item category based on the provided images.

        This method builds a language-specific prompt and queries the configured
        AI providers in sequence (OpenAI → Anthropic → Ollama) until one
        successfully returns a response.

        Args:
            image_paths: List of file system paths to images that should be
                analyzed to infer the item category.
            language: Language code used to formulate the prompt. Currently
                "pl" generates a Polish prompt; any other value generates an
                English prompt. Defaults to "pl".

        Returns:
            A single category name (one word) that belongs to the configured
            set of supported categories (SUPPORTED_CATEGORIES). If no provider
            returns a valid category, or the response cannot be validated, the
            method falls back to returning "other".

        Raises:
            RuntimeError: If no AI provider is available or all providers fail.
        """
        categories_list = ", ".join(SUPPORTED_CATEGORIES)

        if language == "pl":
            prompt = f"""Przeanalizuj zdjęcia i określ kategorię przedmiotu.

Dostępne kategorie: {categories_list}

Odpowiedz TYLKO nazwą kategorii (jednym słowem), bez żadnych dodatkowych wyjaśnień."""
        else:
            prompt = f"""Analyze the images and determine the item category.

Available categories: {categories_list}

Respond with ONLY the category name (one word), without any additional explanations."""

        # Try providers in order: OpenAI -> Anthropic -> Ollama
        if self.openai_client:
            try:
                response = await self._generate_with_openai(prompt, image_paths)
                return self._extract_category(response)
            except Exception as e:
                logger.warning("OpenAI category suggestion failed: %s", e)

        if self.anthropic_api_key:
            try:
                response = await self._generate_with_anthropic(prompt, image_paths)
                return self._extract_category(response)
            except Exception as e:
                logger.warning("Anthropic category suggestion failed: %s", e)

        if self.ollama_base_url:
            try:
                response = await self._generate_with_ollama(prompt, image_paths)
                return self._extract_category(response)
            except Exception as e:
                logger.warning("Ollama category suggestion failed: %s", e)

        msg = "No AI provider available or all providers failed"
        raise RuntimeError(msg)

    def _extract_category(self, response: str) -> str:
        """Extract and validate category from AI response."""
        # Clean response and get first word
        cleaned = response.strip().lower()
        parts = cleaned.split()
        if not parts:
            # If response is empty or only whitespace, default to "other"
            return "other"
        category = parts[0]
        # Remove any punctuation
        category = "".join(c for c in category if c.isalnum() or c == "_")

        # Validate against supported categories
        if category in SUPPORTED_CATEGORIES:
            return category

        # If not found, return "other"
        return "other"

    async def extract_from_url(self, url: str, language: str = "pl") -> dict[str, Any]:
        """Extract product information from a product page URL.

        Args:
            url: Public HTTP/HTTPS URL of the product page to analyze.
            language: Two-letter language code (for example, "pl" or "en") that controls
                the language of the AI prompt and, where possible, the returned text.

        Returns:
            dict[str, Any]: A dictionary containing structured product data extracted
            from the page. The dictionary typically includes the following keys:

                - "title" (str | None): Human-readable product name.
                - "description" (str | None): Detailed or marketing description of the
                  product.
                - "category" (str | None): Predicted product category identifier.
                - "price" (float | int | None): Numeric price of the product, if it can
                  be determined.
                - "currency" (str | None): Currency code for the price (for example,
                  "PLN", "EUR"), if available.
                - "images" (list[str]): List of image URLs associated with the product.

            Additional provider-specific keys may be present depending on the AI
            response and extraction logic.

        Raises:
            ValueError: If the HTTP request to ``url`` fails or the response status is
                not successful, or if URL validation fails (SSRF protection).
            RuntimeError: If no AI provider is available to process the request or all
                configured providers fail.
        """
        # Validate URL to prevent SSRF
        _validate_url(url)

        try:
            # Fetch webpage content
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                response.raise_for_status()
                html_content = response.text

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text content
            text_content = soup.get_text(separator="\n", strip=True)
            # Limit content size
            text_content = text_content[:10000]

            # Extract images
            images = []
            for img in soup.find_all("img", src=True)[:10]:
                img_url = str(img["src"])
                if img_url.startswith("http"):
                    images.append(img_url)

            # Use AI to extract structured information
            if language == "pl":
                prompt = f"""Przeanalizuj treść strony produktu i wyodrębnij info w JSON.

Treść strony:
{text_content}

Wyodrębnij następujące informacje (jeśli dostępne):
- title: nazwa produktu
- brand: marka
- description: opis produktu (krótki, max 200 słów)
- price: cena (tylko liczba, bez waluty)
- currency: waluta (PLN, EUR, USD, etc.)
- category: kategoria z listy: {", ".join(SUPPORTED_CATEGORIES)}
- condition: stan (new, like_new, good, fair, poor)
- size: rozmiar
- specifications: kluczowe specyfikacje jako obiekt

Odpowiedz TYLKO poprawnym JSON-em bez dodatkowych wyjaśnień."""
            else:
                prompt = f"""Analyze product page content and extract information in JSON format.

Page content:
{text_content}

Extract the following information (if available):
- title: product name
- brand: brand name
- description: product description (brief, max 200 words)
- price: price (number only, no currency)
- currency: currency code (PLN, EUR, USD, etc.)
- category: category from: {", ".join(SUPPORTED_CATEGORIES)}
- condition: condition (new, like_new, good, fair, poor)
- size: size
- specifications: key specifications as object

Respond with ONLY valid JSON, no additional explanations."""

            # Try providers in order
            extracted_text = None
            if self.openai_client:
                try:
                    extracted_text = await self._generate_text_with_openai(prompt)
                except Exception as e:
                    logger.warning("OpenAI extraction failed: %s", e)

            if not extracted_text and self.anthropic_api_key:
                try:
                    extracted_text = await self._generate_text_with_anthropic(prompt)
                except Exception as e:
                    logger.warning("Anthropic extraction failed: %s", e)

            if not extracted_text and self.ollama_base_url:
                try:
                    extracted_text = await self._generate_text_with_ollama(prompt)
                except Exception as e:
                    logger.warning("Ollama extraction failed: %s", e)

            if not extracted_text:
                msg = "No AI provider available"
                raise RuntimeError(msg)

            # Parse JSON response
            extracted_data = self._parse_json_response(extracted_text)
            extracted_data["images"] = images

            return extracted_data

        except httpx.HTTPError as e:
            logger.error("Failed to fetch URL: %s", e)
            raise ValueError(f"Failed to fetch URL: {e}") from e
        except Exception as e:
            logger.error("URL extraction failed: %s", e)
            raise

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from AI response, handling markdown code blocks."""
        # Remove markdown code blocks
        response = response.strip()
        if response.startswith("```"):
            # Find the actual JSON content
            lines = response.split("\n")
            start_idx = 1  # Skip first ```
            end_idx = len(lines) - 1  # Skip last ```
            for i, line in enumerate(lines):
                if i > 0 and line.startswith("```"):
                    end_idx = i
                    break
            response = "\n".join(lines[start_idx:end_idx])

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON, returning empty dict")
            return {}

    async def _generate_text_with_openai(self, prompt: str) -> str:
        """Generate text using OpenAI.

        This is a thin wrapper around the more general `_generate_with_openai`
        helper, which centralizes the OpenAI provider logic (including
        optional image handling).
        """
        # Delegate to the unified OpenAI generation method with higher token limit for text-only
        return await self._generate_with_openai(prompt=prompt, image_paths=[], max_tokens=1000)

    async def _generate_text_with_anthropic(self, prompt: str) -> str:
        """Generate text using Anthropic Claude.

        Delegate to the shared Anthropic implementation to avoid duplicated logic.
        """
        return await self._generate_with_anthropic(prompt=prompt, image_paths=[], max_tokens=1000)

    async def _generate_text_with_ollama(self, prompt: str) -> str:
        """Generate text using local Ollama model.

        Delegate to the shared Ollama implementation to avoid duplicated logic.
        """
        return await self._generate_with_ollama(prompt=prompt, image_paths=[])

    async def generate_description(
        self,
        category: str,
        image_paths: list[str],
        brand: str | None = None,
        condition: str | None = None,
        size: str | None = None,
        additional_details: str | None = None,
        language: str = "pl",
        product_url: str | None = None,
    ) -> str:
        """Generate compelling description from images and item details."""
        # Fetch product details from URL if provided
        url_context = ""
        if product_url:
            try:
                url_context = await self._fetch_url_context(product_url)
            except Exception as e:
                logger.warning("Failed to fetch URL context: %s", e)
                # Continue without URL context

        prompt = self._build_prompt(
            category, brand, condition, size, additional_details, language, url_context
        )

        # Try providers in order: OpenAI -> Anthropic -> Ollama
        if self.openai_client:
            try:
                return await self._generate_with_openai(prompt, image_paths)
            except Exception as e:
                logger.warning("OpenAI generation failed: %s", e)

        if self.anthropic_api_key:
            try:
                return await self._generate_with_anthropic(prompt, image_paths)
            except Exception as e:
                logger.warning("Anthropic generation failed: %s", e)

        if self.ollama_base_url:
            try:
                return await self._generate_with_ollama(prompt, image_paths)
            except Exception as e:
                logger.warning("Ollama generation failed: %s", e)

        msg = "No AI provider available or all providers failed"
        raise RuntimeError(msg)

    async def _fetch_url_context(self, url: str) -> str:
        """Fetch and parse product page content for context."""
        # Validate URL to prevent SSRF
        _validate_url(url)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                response.raise_for_status()
                html_content = response.text

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text content
            text_content = soup.get_text(separator=" ", strip=True)
            # Limit context size to 3000 chars
            return text_content[:3000]

        except Exception as e:
            logger.warning("Failed to fetch URL context: %s", e)
            return ""

    def _build_prompt(
        self,
        category: str,
        brand: str | None,
        condition: str | None,
        size: str | None,
        additional_details: str | None,
        language: str = "pl",
        url_context: str = "",
    ) -> str:
        """Build category-specific prompt for description generation."""
        prompt_dict = CATEGORY_PROMPTS_PL if language == "pl" else CATEGORY_PROMPTS_EN
        base_prompt = prompt_dict.get(category, prompt_dict["default"]).format(
            brand=brand or "unknown",
            condition=condition or "good",
            size=size or "",
        )

        if additional_details:
            details_prefix = "Dodatkowe szczegóły:" if language == "pl" else "Additional details:"
            base_prompt += f"\n\n{details_prefix} {additional_details}"

        if url_context:
            if language == "pl":
                context_prefix = "Info z oryginalnej strony (użyj do wzbogacenia o szczegóły):"
            else:
                context_prefix = "Info from product page (use to enrich with details):"

            base_prompt += f"\n\n{context_prefix}\n{url_context}"

        return base_prompt

    async def _generate_with_openai(
        self,
        prompt: str,
        image_paths: list[str] | None = None,
        max_tokens: int = 500,
    ) -> str:
        """Generate text/description using OpenAI GPT-4V.

        Args:
            prompt: Text prompt for the AI
            image_paths: Optional list of image paths to include in request
            max_tokens: Maximum tokens for response (default 500)
        """
        if not self.openai_client:
            msg = "OpenAI client not initialized"
            raise RuntimeError(msg)

        if image_paths is None:
            image_paths = []

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        # Add images if provided
        for image_path in image_paths[:4]:  # Limit to 4 images
            image_data = self._load_image_base64(image_path)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                    },
                }
            )

        # pyrefly: ignore
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""

    async def _generate_with_anthropic(
        self,
        prompt: str,
        image_paths: list[str] | None = None,
        max_tokens: int = 500,
    ) -> str:
        """Generate text/description using Anthropic Claude.

        Args:
            prompt: Text prompt for the AI
            image_paths: Optional list of image paths to include in request
            max_tokens: Maximum tokens for response (default 500)
        """
        if not self.anthropic_api_key:
            msg = "Anthropic API key not configured"
            raise RuntimeError(msg)

        if image_paths is None:
            image_paths = []

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        # Add images if provided
        for image_path in image_paths[:4]:
            image_data = self._load_image_base64(image_path)
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data,
                    },
                }
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": content}],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def _generate_with_ollama(
        self,
        prompt: str,
        image_paths: list[str] | None = None,
    ) -> str:
        """Generate text/description using local Ollama model.

        Args:
            prompt: Text prompt for the AI
            image_paths: Optional list of image paths to include in request
        """
        if not self.ollama_base_url:
            msg = "Ollama base URL not configured"
            raise RuntimeError(msg)

        if image_paths is None:
            image_paths = []

        # Choose model based on whether images are provided
        model = "llama3.2-vision" if image_paths else "llama3.2"

        # Build payload with images if provided
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if image_paths:
            payload["images"] = [self._load_image_base64(path) for path in image_paths[:4]]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    def _load_image_base64(self, image_path: str) -> str:
        """Load image and convert to base64."""
        path = Path(image_path)
        if not path.exists():
            msg = f"Image not found: {image_path}"
            raise FileNotFoundError(msg)

        # Check file size (max 2MB)
        max_size = 2 * 1024 * 1024  # 2MB
        file_size = path.stat().st_size
        if file_size > max_size:
            msg = f"Image too large: {file_size} bytes (max {max_size} bytes)"
            raise ValueError(msg)

        with path.open("rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


# Category-specific prompt templates - English
CATEGORY_PROMPTS_EN = {
    "womens_fashion": """Generate an engaging listing description for women's fashion item.

Brand: {brand}
Condition: {condition}
Size: {size}

Focus on: Material, fit, style, brand reputation, condition details, care instructions.
Write in casual, friendly tone. SEO-friendly. Max 200 words.""",
    "mens_fashion": """Generate an engaging marketplace listing description for men's fashion item.

Brand: {brand}
Condition: {condition}
Size: {size}

Focus on: Material, fit, style, brand, condition, care instructions.
Write in casual, friendly tone. SEO-friendly. Max 200 words.""",
    "kids_clothing": """Generate an engaging marketplace listing description for kids' clothing.

Brand: {brand}
Condition: {condition}
Size: {size}

Focus on: Material, comfort, size/age, condition, safety, brand.
Warm, friendly tone. Mention safety. Max 200 words.""",
    "shoes": """Generate an engaging marketplace listing description for shoes.

Brand: {brand}
Condition: {condition}
Size: {size}

Focus on: Brand, size, condition (sole wear, material), style, comfort features.
Casual tone. Include specific measurements. Max 200 words.""",
    "bags_accessories": """Generate an engaging marketplace listing description for bag/accessory.

Brand: {brand}
Condition: {condition}

Focus on: Brand, material, dimensions, condition, features (pockets, compartments), style.
Descriptive, friendly tone. Max 200 words.""",
    "jewelry_watches": """Generate an engaging marketplace listing description for jewelry/watch.

Brand: {brand}
Condition: {condition}

Focus on: Material, brand, condition, features, style, authenticity markers.
Elegant, precise tone. Max 200 words.""",
    "electronics": """Generate an engaging marketplace listing description for electronics.

Brand: {brand}
Condition: {condition}

Focus on: Specifications, features, condition, included accessories, purchase date.
Clear, technical tone. Include keywords. Max 200 words.""",
    "home_garden": """Generate an engaging marketplace listing description for home & garden item.

Brand: {brand}
Condition: {condition}

Focus on: Functionality, materials, condition, usage instructions, benefits.
Practical tone. Emphasize features. Max 200 words.""",
    "sports_hobby": """Generate an engaging marketplace listing description for sports/hobby item.

Brand: {brand}
Condition: {condition}
Size: {size}

Focus on: Type, brand, condition, usage level, specifications, performance.
Enthusiastic tone. Sport-specific keywords. Max 200 words.""",
    "toys_games": """Generate an engaging marketplace listing description for toy/game.

Brand: {brand}
Condition: {condition}

Focus on: Age appropriateness, educational value, safety, condition, completeness.
Warm, clear tone. Mention safety. Max 200 words.""",
    "books_media": """Generate an engaging marketplace listing description for book/media.

Brand: {brand}
Condition: {condition}

Focus on: Title, author, edition, condition, language, format.
Informative tone. Specific about condition. Max 200 words.""",
    "beauty_health": """Generate an engaging listing description for beauty/health product.

Brand: {brand}
Condition: {condition}

Focus on: Brand, product type, usage, expiry date, quantity remaining, benefits.
Clean, honest tone. Safety info. Max 200 words.""",
    "vehicles_parts": """Generate an engaging marketplace listing description for vehicle/part.

Brand: {brand}
Condition: {condition}

Focus on: Make/model compatibility, condition, specifications, installation.
Technical, precise tone. Include details. Max 200 words.""",
    "animals_pet_supplies": """Generate an engaging listing description for pet supply/animal.

Brand: {brand}
Condition: {condition}

Focus on: Type, age appropriateness, safety, condition, size/capacity.
Caring, informative tone. Max 200 words.""",
    "music_instruments": """Generate an engaging listing description for musical instrument.

Brand: {brand}
Condition: {condition}

Focus on: Type, brand, condition, specifications, included accessories, sound quality.
Passionate, technical tone. Max 200 words.""",
    "collectibles_art": """Generate an engaging marketplace listing description for collectible/art.

Brand: {brand}
Condition: {condition}

Focus on: Rarity, condition, provenance, materials, dimensions, authenticity.
Elegant, detailed tone. Max 200 words.""",
    "default": """Generate an engaging marketplace listing description.

Brand: {brand}
Condition: {condition}

Focus on: Key features, condition, quality, brand, value.
Clear, engaging tone. Use keywords. Max 200 words.""",
}


# Category-specific prompt templates - Polish
CATEGORY_PROMPTS_PL = {
    "womens_fashion": """Wygeneruj angażujący opis ogłoszenia dla damskiej odzieży.

Marka: {brand}
Stan: {condition}
Rozmiar: {size}

Skup się na: Materiał, krój, styl, marka, stan, pielęgnacja.
Swobodny, przyjazny ton. SEO. Max 200 słów.""",
    "mens_fashion": """Wygeneruj angażujący opis ogłoszenia dla męskiej odzieży.

Marka: {brand}
Stan: {condition}
Rozmiar: {size}

Skup się na: Materiał, krój, styl, marka, stan, pielęgnacja.
Swobodny, przyjazny ton. SEO. Max 200 słów.""",
    "kids_clothing": """Wygeneruj angażujący opis ogłoszenia dla dziecięcej odzieży.

Marka: {brand}
Stan: {condition}
Rozmiar: {size}

Skup się na: Materiał, wygoda, rozmiar/wiek, stan, bezpieczeństwo, marka.
Ciepły, przyjazny ton. Bezpieczeństwo. Max 200 słów.""",
    "shoes": """Wygeneruj angażujący opis ogłoszenia dla obuwia.

Marka: {brand}
Stan: {condition}
Rozmiar: {size}

Skup się na: Marka, rozmiar, stan (podeszwa, materiał), styl, wygoda.
Swobodny ton. Dokładne wymiary. Max 200 słów.""",
    "bags_accessories": """Wygeneruj angażujący opis ogłoszenia dla torebki/akcesorium.

Marka: {brand}
Stan: {condition}

Skup się na: Marka, materiał, wymiary, stan, funkcje (kieszenie), styl.
Opisowy, przyjazny ton. Max 200 słów.""",
    "jewelry_watches": """Wygeneruj angażujący opis ogłoszenia dla biżuterii/zegarka.

Marka: {brand}
Stan: {condition}

Skup się na: Materiał, marka, stan, cechy, styl, autentyczność.
Elegancki, precyzyjny ton. Max 200 słów.""",
    "electronics": """Wygeneruj angażujący opis ogłoszenia dla elektroniki.

Marka: {brand}
Stan: {condition}

Skup się na: Specyfikacje, funkcje, stan, akcesoria, data zakupu.
Jasny, techniczny ton. Słowa kluczowe. Max 200 słów.""",
    "home_garden": """Wygeneruj angażujący opis ogłoszenia dla przedmiotu dom i ogród.

Marka: {brand}
Stan: {condition}

Skup się na: Funkcjonalność, materiały, stan, instrukcje, korzyści.
Praktyczny ton. Podkreśl cechy. Max 200 słów.""",
    "sports_hobby": """Wygeneruj angażujący opis ogłoszenia dla sprzętu sportowego/hobby.

Marka: {brand}
Stan: {condition}
Rozmiar: {size}

Skup się na: Typ, marka, stan, poziom użytkowania, specyfikacje, wydajność.
Entuzjastyczny ton. Słowa kluczowe. Max 200 słów.""",
    "toys_games": """Wygeneruj angażujący opis ogłoszenia dla zabawki/gry.

Marka: {brand}
Stan: {condition}

Skup się na: Wiek, wartość edukacyjna, bezpieczeństwo, stan, kompletność.
Ciepły, jasny ton. Bezpieczeństwo. Max 200 słów.""",
    "books_media": """Wygeneruj angażujący opis ogłoszenia dla książki/mediów.

Marka: {brand}
Stan: {condition}

Skup się na: Tytuł, autor, wydanie, stan, język, format.
Informacyjny ton. Dokładny stan. Max 200 słów.""",
    "beauty_health": """Wygeneruj angażujący opis ogłoszenia dla produktu beauty/zdrowie.

Marka: {brand}
Stan: {condition}

Skup się na: Marka, typ, użytkowanie, data ważności, ilość, korzyści.
Czysty, uczciwy ton. Bezpieczeństwo. Max 200 słów.""",
    "vehicles_parts": """Wygeneruj angażujący opis ogłoszenia dla pojazdu/części.

Marka: {brand}
Stan: {condition}

Skup się na: Kompatybilność, stan, specyfikacje, montaż.
Techniczny, precyzyjny ton. Szczegóły. Max 200 słów.""",
    "animals_pet_supplies": """Wygeneruj angażujący opis ogłoszenia dla akcesoriów zwierzęcych.

Marka: {brand}
Stan: {condition}

Skup się na: Typ, odpowiedniość, bezpieczeństwo, stan, rozmiar/pojemność.
Troskliwy, informacyjny ton. Max 200 słów.""",
    "music_instruments": """Wygeneruj angażujący opis ogłoszenia dla instrumentu muzycznego.

Marka: {brand}
Stan: {condition}

Skup się na: Typ, marka, stan, specyfikacje, akcesoria, jakość dźwięku.
Pasjonujący, techniczny ton. Max 200 słów.""",
    "collectibles_art": """Wygeneruj angażujący opis ogłoszenia dla kolekcji/sztuki.

Marka: {brand}
Stan: {condition}

Skup się na: Rzadkość, stan, pochodzenie, materiały, wymiary, autentyczność.
Elegancki, szczegółowy ton. Max 200 słów.""",
    "default": """Wygeneruj angażujący opis ogłoszenia.

Marka: {brand}
Stan: {condition}

Skup się na: Kluczowe cechy, stan, jakość, marka, wartość.
Jasny, angażujący ton. Słowa kluczowe. Max 200 słów.""",
}


# Supported categories (based on Vinted and OLX Poland)
SUPPORTED_CATEGORIES = [
    "womens_fashion",
    "mens_fashion",
    "kids_clothing",
    "shoes",
    "bags_accessories",
    "jewelry_watches",
    "electronics",
    "home_garden",
    "sports_hobby",
    "toys_games",
    "books_media",
    "beauty_health",
    "vehicles_parts",
    "animals_pet_supplies",
    "music_instruments",
    "collectibles_art",
    "other",
]
