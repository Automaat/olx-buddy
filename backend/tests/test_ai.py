"""Test AI service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.ai import (
    CATEGORY_PROMPTS_EN,
    CATEGORY_PROMPTS_PL,
    SUPPORTED_CATEGORIES,
    AIService,
    _validate_url,
)


@pytest.fixture
def ai_service():
    """Create AI service with no providers configured."""
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.ollama_base_url = None
        return AIService()


@pytest.fixture
def ai_service_with_openai():
    """Create AI service with OpenAI configured."""
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        mock_settings.anthropic_api_key = None
        mock_settings.ollama_base_url = None
        with patch("app.services.ai.AsyncOpenAI"):
            return AIService()


@pytest.fixture
def ai_service_with_anthropic():
    """Create AI service with Anthropic configured."""
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.ollama_base_url = None
        return AIService()


@pytest.fixture
def ai_service_with_ollama():
    """Create AI service with Ollama configured."""
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None
        mock_settings.ollama_base_url = "http://localhost:11434"
        return AIService()


@pytest.fixture
def test_image_path(tmp_path):
    """Create a temporary test image."""
    image_path = tmp_path / "test.jpg"
    image_path.write_bytes(b"fake image data")
    return str(image_path)


class TestAIService:
    """Test AIService class."""

    def test_init_no_providers(self, ai_service):
        """Test initialization with no providers."""
        assert ai_service.openai_client is None
        assert ai_service.anthropic_api_key is None
        assert ai_service.ollama_base_url is None

    def test_init_with_openai(self):
        """Test initialization with OpenAI."""
        with (
            patch("app.services.ai.settings") as mock_settings,
            patch("app.services.ai.AsyncOpenAI") as mock_openai,
        ):
            mock_settings.openai_api_key = "test-key"
            mock_settings.anthropic_api_key = None
            mock_settings.ollama_base_url = None

            service = AIService()

            assert service.openai_client is not None
            mock_openai.assert_called_once_with(api_key="test-key")

    def test_init_with_anthropic(self, ai_service_with_anthropic):
        """Test initialization with Anthropic."""
        assert ai_service_with_anthropic.anthropic_api_key == "test-key"

    def test_init_with_ollama(self, ai_service_with_ollama):
        """Test initialization with Ollama."""
        assert ai_service_with_ollama.ollama_base_url == "http://localhost:11434"

    def test_build_prompt_default_category(self, ai_service):
        """Test prompt building with default category."""
        prompt = ai_service._build_prompt("unknown_category", "Nike", "good", "L", None)

        assert "Nike" in prompt
        assert "good" in prompt

    def test_build_prompt_clothing_category(self, ai_service):
        """Test prompt building for womens_fashion category."""
        prompt = ai_service._build_prompt("womens_fashion", "Nike", "like_new", "M", None, "en")

        assert "fashion" in prompt.lower()
        assert "Nike" in prompt
        assert "like_new" in prompt
        assert "M" in prompt

    def test_build_prompt_electronics_category(self, ai_service):
        """Test prompt building for electronics category."""
        prompt = ai_service._build_prompt("electronics", "Apple", "good", None, None, "en")

        assert "electronics" in prompt.lower()
        assert "Apple" in prompt

    def test_build_prompt_with_additional_details(self, ai_service):
        """Test prompt building with additional details."""
        prompt = ai_service._build_prompt(
            "clothing", "Nike", "good", "L", "Limited edition sneakers"
        )

        assert "Limited edition sneakers" in prompt

    def test_build_prompt_all_categories_exist(self, ai_service):
        """Test that all supported categories have prompts."""
        for category in SUPPORTED_CATEGORIES:
            if category == "other":
                # "other" uses default prompt
                continue
            assert category in CATEGORY_PROMPTS_EN
            assert category in CATEGORY_PROMPTS_PL

    @pytest.mark.asyncio
    async def test_generate_description_no_providers(self, ai_service, test_image_path):
        """Test description generation with no providers available."""
        with pytest.raises(RuntimeError, match="No AI provider available"):
            await ai_service.generate_description("clothing", [test_image_path])

    @pytest.mark.asyncio
    async def test_generate_with_openai_success(self, ai_service_with_openai, test_image_path):
        """Test successful generation with OpenAI."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated description"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(ai_service_with_openai, "_load_image_base64", return_value="base64data"):
            result = await ai_service_with_openai._generate_with_openai(
                "Test prompt", [test_image_path]
            )

            assert result == "Generated description"

    @pytest.mark.asyncio
    async def test_generate_with_openai_no_client(self, ai_service):
        """Test OpenAI generation with no client initialized."""
        with pytest.raises(RuntimeError, match="OpenAI client not initialized"):
            await ai_service._generate_with_openai("prompt", [])

    @pytest.mark.asyncio
    async def test_generate_with_openai_multiple_images(
        self, ai_service_with_openai, test_image_path
    ):
        """Test OpenAI generation with multiple images."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated description"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(ai_service_with_openai, "_load_image_base64", return_value="base64data"):
            await ai_service_with_openai._generate_with_openai("Test prompt", [test_image_path] * 5)

            # Should only use first 4 images
            call_args = ai_service_with_openai.openai_client.chat.completions.create.call_args
            content = call_args[1]["messages"][0]["content"]
            image_items = [item for item in content if item["type"] == "image_url"]
            assert len(image_items) == 4

    @pytest.mark.asyncio
    async def test_generate_with_anthropic_success(
        self, ai_service_with_anthropic, test_image_path
    ):
        """Test successful generation with Anthropic."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "Generated description"}]}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(
                ai_service_with_anthropic, "_load_image_base64", return_value="base64data"
            ),
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_anthropic._generate_with_anthropic(
                "Test prompt", [test_image_path]
            )

            assert result == "Generated description"

    @pytest.mark.asyncio
    async def test_generate_with_anthropic_no_key(self, ai_service):
        """Test Anthropic generation with no API key."""
        with pytest.raises(RuntimeError, match="Anthropic API key not configured"):
            await ai_service._generate_with_anthropic("prompt", [])

    @pytest.mark.asyncio
    async def test_generate_with_anthropic_http_error(
        self, ai_service_with_anthropic, test_image_path
    ):
        """Test Anthropic generation with HTTP error."""
        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(
                ai_service_with_anthropic, "_load_image_base64", return_value="base64data"
            ),
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("API error")
            )

            with pytest.raises(httpx.HTTPError):
                await ai_service_with_anthropic._generate_with_anthropic(
                    "Test prompt", [test_image_path]
                )

    @pytest.mark.asyncio
    async def test_generate_with_ollama_success(self, ai_service_with_ollama, test_image_path):
        """Test successful generation with Ollama."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Generated description"}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(ai_service_with_ollama, "_load_image_base64", return_value="base64data"),
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_ollama._generate_with_ollama(
                "Test prompt", [test_image_path]
            )

            assert result == "Generated description"

    @pytest.mark.asyncio
    async def test_generate_with_ollama_no_url(self, ai_service):
        """Test Ollama generation with no base URL."""
        with pytest.raises(RuntimeError, match="Ollama base URL not configured"):
            await ai_service._generate_with_ollama("prompt", [])

    @pytest.mark.asyncio
    async def test_generate_with_ollama_empty_response(
        self, ai_service_with_ollama, test_image_path
    ):
        """Test Ollama generation with empty response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(ai_service_with_ollama, "_load_image_base64", return_value="base64data"),
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_ollama._generate_with_ollama(
                "Test prompt", [test_image_path]
            )

            assert result == ""

    @pytest.mark.asyncio
    async def test_generate_description_fallback_to_anthropic(
        self, ai_service_with_anthropic, test_image_path
    ):
        """Test fallback from OpenAI to Anthropic."""
        # Add both providers
        ai_service_with_anthropic.openai_client = MagicMock()

        # OpenAI fails
        ai_service_with_anthropic.openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI failed")
        )

        # Anthropic succeeds
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "Anthropic description"}]}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(
                ai_service_with_anthropic, "_load_image_base64", return_value="base64data"
            ),
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_anthropic.generate_description(
                "clothing", [test_image_path]
            )

            assert result == "Anthropic description"

    @pytest.mark.asyncio
    async def test_generate_description_fallback_to_ollama(
        self, ai_service_with_ollama, test_image_path
    ):
        """Test fallback to Ollama after other providers fail."""
        ai_service_with_ollama.openai_client = MagicMock()
        ai_service_with_ollama.anthropic_api_key = "test-key"

        # OpenAI and Anthropic fail
        ai_service_with_ollama.openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI failed")
        )

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(ai_service_with_ollama, "_load_image_base64", return_value="base64data"),
        ):
            # First call (Anthropic) fails, second call (Ollama) succeeds
            anthropic_response = AsyncMock(side_effect=Exception("Anthropic failed"))
            ollama_response = MagicMock()
            ollama_response.json.return_value = {"response": "Ollama description"}
            ollama_response.raise_for_status = MagicMock()

            mock_post = AsyncMock(side_effect=[anthropic_response, ollama_response])
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await ai_service_with_ollama.generate_description(
                "clothing", [test_image_path]
            )

            assert result == "Ollama description"

    def test_load_image_base64_success(self, ai_service, test_image_path):
        """Test loading image and converting to base64."""
        result = ai_service._load_image_base64(test_image_path)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_load_image_base64_file_not_found(self, ai_service):
        """Test loading non-existent image."""
        with pytest.raises(FileNotFoundError, match="Image not found"):
            ai_service._load_image_base64("/nonexistent/image.jpg")

    def test_load_image_base64_file_too_large(self, ai_service, tmp_path):
        """Test loading image that exceeds size limit."""
        large_image = tmp_path / "large.jpg"
        large_image.write_bytes(b"x" * (3 * 1024 * 1024))  # 3MB

        with pytest.raises(ValueError, match="Image too large"):
            ai_service._load_image_base64(str(large_image))

    def test_supported_categories_list(self):
        """Test that supported categories list is correct."""
        # Verify key categories are present
        assert "womens_fashion" in SUPPORTED_CATEGORIES
        assert "mens_fashion" in SUPPORTED_CATEGORIES
        assert "electronics" in SUPPORTED_CATEGORIES
        assert "home_garden" in SUPPORTED_CATEGORIES
        assert "other" in SUPPORTED_CATEGORIES
        # Verify list is not empty
        assert len(SUPPORTED_CATEGORIES) > 0

    def test_category_prompts_structure(self):
        """Test that category prompts have proper structure."""
        for category, prompt in CATEGORY_PROMPTS_EN.items():
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Check for template variables
            assert "{condition}" in prompt or category == "furniture"

        for category, prompt in CATEGORY_PROMPTS_PL.items():
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Check for template variables
            assert "{condition}" in prompt or category == "furniture"


class TestSuggestCategory:
    """Test category suggestion functionality."""

    @pytest.mark.asyncio
    async def test_suggest_category_with_openai(self, ai_service_with_openai, test_image_path):
        """Test category suggestion with OpenAI."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "electronics"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(ai_service_with_openai, "_load_image_base64", return_value="base64data"):
            result = await ai_service_with_openai.suggest_category([test_image_path], "en")

            assert result == "electronics"

    @pytest.mark.asyncio
    async def test_suggest_category_polish_language(self, ai_service_with_openai, test_image_path):
        """Test category suggestion with Polish language."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "womens_fashion"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(ai_service_with_openai, "_load_image_base64", return_value="base64data"):
            result = await ai_service_with_openai.suggest_category([test_image_path], "pl")

            assert result == "womens_fashion"
            # Verify prompt contains Polish text
            call_args = ai_service_with_openai.openai_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            prompt_text = messages[0]["content"][0]["text"]
            assert "kategori" in prompt_text.lower() or "przeanalizuj" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_suggest_category_fallback_to_anthropic(
        self, ai_service_with_anthropic, test_image_path
    ):
        """Test category suggestion fallback to Anthropic."""
        ai_service_with_anthropic.openai_client = MagicMock()
        ai_service_with_anthropic.openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI failed")
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "toys_games"}]}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(
                ai_service_with_anthropic, "_load_image_base64", return_value="base64data"
            ),
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_anthropic.suggest_category([test_image_path], "en")

            assert result == "toys_games"

    @pytest.mark.asyncio
    async def test_suggest_category_no_providers(self, ai_service, test_image_path):
        """Test category suggestion with no providers."""
        with pytest.raises(RuntimeError, match="No AI provider available"):
            await ai_service.suggest_category([test_image_path], "en")

    @pytest.mark.asyncio
    async def test_suggest_category_invalid_response_returns_other(
        self, ai_service_with_openai, test_image_path
    ):
        """Test category suggestion with invalid category returns 'other'."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "invalid_category"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(ai_service_with_openai, "_load_image_base64", return_value="base64data"):
            result = await ai_service_with_openai.suggest_category([test_image_path], "en")

            assert result == "other"


class TestExtractCategory:
    """Test category extraction from AI response."""

    def test_extract_category_valid(self, ai_service):
        """Test extracting valid category."""
        result = ai_service._extract_category("electronics")
        assert result == "electronics"

    def test_extract_category_with_extra_text(self, ai_service):
        """Test extracting category from response with extra text."""
        result = ai_service._extract_category("womens_fashion is the category")
        assert result == "womens_fashion"

    def test_extract_category_with_punctuation(self, ai_service):
        """Test extracting category with punctuation."""
        result = ai_service._extract_category("electronics.")
        assert result == "electronics"

    def test_extract_category_invalid_returns_other(self, ai_service):
        """Test invalid category returns 'other'."""
        result = ai_service._extract_category("invalid_category")
        assert result == "other"

    def test_extract_category_uppercase(self, ai_service):
        """Test extracting uppercase category."""
        result = ai_service._extract_category("ELECTRONICS")
        assert result == "electronics"

    def test_extract_category_empty_response(self, ai_service):
        """Test extracting category from empty response returns 'other'."""
        result = ai_service._extract_category("")
        assert result == "other"

    def test_extract_category_whitespace_only(self, ai_service):
        """Test extracting category from whitespace-only response returns 'other'."""
        result = ai_service._extract_category("   \n\t  ")
        assert result == "other"


class TestExtractFromURL:
    """Test URL extraction functionality."""

    @pytest.mark.asyncio
    async def test_extract_from_url_success(self, ai_service_with_openai):
        """Test successful URL extraction."""
        mock_http_response = MagicMock()
        mock_http_response.text = """
        <html>
            <body>
                <h1>Product Title</h1>
                <div class="price">99.99 PLN</div>
                <div class="description">Great product</div>
                <img src="https://example.com/img1.jpg"/>
            </body>
        </html>
        """
        mock_http_response.raise_for_status = MagicMock()

        mock_ai_response = MagicMock()
        mock_ai_response.choices = [MagicMock()]
        mock_ai_response.choices[0].message.content = """{
            "title": "Product Title",
            "price": 99.99,
            "currency": "PLN"
        }"""

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_ai_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_http_response
            )

            result = await ai_service_with_openai.extract_from_url("https://example.com/product")

            assert result["title"] == "Product Title"
            assert result["price"] == 99.99
            assert result["currency"] == "PLN"
            assert "https://example.com/img1.jpg" in result["images"]

    @pytest.mark.asyncio
    async def test_extract_from_url_polish_language(self, ai_service_with_openai):
        """Test URL extraction with Polish language."""
        mock_http_response = MagicMock()
        mock_http_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_http_response.raise_for_status = MagicMock()

        mock_ai_response = MagicMock()
        mock_ai_response.choices = [MagicMock()]
        mock_ai_response.choices[0].message.content = '{"title": "Test"}'

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_ai_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_http_response
            )

            await ai_service_with_openai.extract_from_url("https://example.com/product", "pl")

            call_args = ai_service_with_openai.openai_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            content = messages[0]["content"]
            # Content is now a list with text/image objects
            prompt = content[0]["text"] if isinstance(content, list) else content
            assert "przeanalizuj" in prompt.lower() or "wyodrębnij" in prompt.lower()

    @pytest.mark.asyncio
    async def test_extract_from_url_http_error(self, ai_service_with_openai):
        """Test URL extraction with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("404 Not Found")
            )

            with pytest.raises(ValueError, match="Failed to fetch URL"):
                await ai_service_with_openai.extract_from_url("https://example.com/product")

    @pytest.mark.asyncio
    async def test_extract_from_url_no_provider(self, ai_service):
        """Test URL extraction with no AI provider."""
        mock_http_response = MagicMock()
        mock_http_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_http_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_http_response
            )

            with pytest.raises(RuntimeError, match="No AI provider available"):
                await ai_service.extract_from_url("https://example.com/product")

    @pytest.mark.asyncio
    async def test_extract_from_url_filters_images(self, ai_service_with_openai):
        """Test that URL extraction filters images correctly."""
        mock_http_response = MagicMock()
        mock_http_response.text = """
        <html>
            <body>
                <img src="https://example.com/img1.jpg"/>
                <img src="https://example.com/img2.jpg"/>
                <img src="/relative/img.jpg"/>
                <img src="data:image/png;base64,abc"/>
            </body>
        </html>
        """
        mock_http_response.raise_for_status = MagicMock()

        mock_ai_response = MagicMock()
        mock_ai_response.choices = [MagicMock()]
        mock_ai_response.choices[0].message.content = '{"title": "Test"}'

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_ai_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_http_response
            )

            result = await ai_service_with_openai.extract_from_url("https://example.com/product")

            # Should only include absolute HTTP URLs
            assert len(result["images"]) == 2
            assert "https://example.com/img1.jpg" in result["images"]
            assert "https://example.com/img2.jpg" in result["images"]


class TestFetchURLContext:
    """Test URL context fetching."""

    @pytest.mark.asyncio
    async def test_fetch_url_context_success(self, ai_service_with_openai):
        """Test successful URL context fetching."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head><script>alert('test')</script></head>
            <body>
                <nav>Menu</nav>
                <h1>Product Title</h1>
                <p>Product description</p>
                <footer>Footer</footer>
            </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_openai._fetch_url_context("https://example.com/product")

            assert "Product Title" in result
            assert "Product description" in result
            # Should remove script, nav, footer
            assert "alert" not in result
            assert "Menu" not in result
            assert "Footer" not in result
            # Should be limited to 3000 chars
            assert len(result) <= 3000

    @pytest.mark.asyncio
    async def test_fetch_url_context_long_content(self, ai_service_with_openai):
        """Test that long content is truncated."""
        long_text = "word " * 2000  # Create very long text
        mock_response = MagicMock()
        mock_response.text = f"<html><body>{long_text}</body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_openai._fetch_url_context("https://example.com/product")

            assert len(result) <= 3000

    @pytest.mark.asyncio
    async def test_fetch_url_context_http_error(self, ai_service_with_openai):
        """Test URL context fetching with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )

            result = await ai_service_with_openai._fetch_url_context("https://example.com/product")

            # Should return empty string on error
            assert result == ""


class TestParseJSONResponse:
    """Test JSON response parsing."""

    def test_parse_json_response_plain_json(self, ai_service):
        """Test parsing plain JSON."""
        response = '{"title": "Test", "price": 99.99}'
        result = ai_service._parse_json_response(response)

        assert result["title"] == "Test"
        assert result["price"] == 99.99

    def test_parse_json_response_markdown_code_block(self, ai_service):
        """Test parsing JSON in markdown code block."""
        response = """```json
{"title": "Test", "price": 99.99}
```"""
        result = ai_service._parse_json_response(response)

        assert result["title"] == "Test"
        assert result["price"] == 99.99

    def test_parse_json_response_code_block_without_language(self, ai_service):
        """Test parsing JSON in code block without language specifier."""
        response = """```
{"title": "Test"}
```"""
        result = ai_service._parse_json_response(response)

        assert result["title"] == "Test"

    def test_parse_json_response_invalid_json(self, ai_service):
        """Test parsing invalid JSON returns empty dict."""
        response = "not valid json"
        result = ai_service._parse_json_response(response)

        assert result == {}

    def test_parse_json_response_with_extra_text(self, ai_service):
        """Test parsing JSON with extra text in code block."""
        response = """```json
Some explanation text
{"title": "Test"}
More text after
```"""
        result = ai_service._parse_json_response(response)

        # Should handle extra text gracefully
        assert isinstance(result, dict)


class TestTextGenerationHelpers:
    """Test text generation helper methods."""

    @pytest.mark.asyncio
    async def test_generate_text_with_openai(self, ai_service_with_openai):
        """Test text generation with OpenAI."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated text"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await ai_service_with_openai._generate_text_with_openai("Test prompt")

        assert result == "Generated text"

    @pytest.mark.asyncio
    async def test_generate_text_with_openai_no_client(self, ai_service):
        """Test text generation with no OpenAI client."""
        with pytest.raises(RuntimeError, match="OpenAI client not initialized"):
            await ai_service._generate_text_with_openai("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_text_with_anthropic(self, ai_service_with_anthropic):
        """Test text generation with Anthropic."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "Generated text"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_anthropic._generate_text_with_anthropic("Test prompt")

            assert result == "Generated text"

    @pytest.mark.asyncio
    async def test_generate_text_with_anthropic_no_key(self, ai_service):
        """Test text generation with no Anthropic key."""
        with pytest.raises(RuntimeError, match="Anthropic API key not configured"):
            await ai_service._generate_text_with_anthropic("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_text_with_ollama(self, ai_service_with_ollama):
        """Test text generation with Ollama."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Generated text"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_ollama._generate_text_with_ollama("Test prompt")

            assert result == "Generated text"

    @pytest.mark.asyncio
    async def test_generate_text_with_ollama_no_url(self, ai_service):
        """Test text generation with no Ollama URL."""
        with pytest.raises(RuntimeError, match="Ollama base URL not configured"):
            await ai_service._generate_text_with_ollama("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_text_with_ollama_empty_response(self, ai_service_with_ollama):
        """Test text generation with empty Ollama response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await ai_service_with_ollama._generate_text_with_ollama("Test prompt")

            assert result == ""


class TestGenerateDescriptionWithURLContext:
    """Test description generation with URL context."""

    @pytest.mark.asyncio
    async def test_generate_description_with_url_context(
        self, ai_service_with_openai, test_image_path
    ):
        """Test that URL context is fetched and used in description generation."""
        mock_http_response = MagicMock()
        mock_http_response.text = "<html><body>Product specs: RAM 16GB</body></html>"
        mock_http_response.raise_for_status = MagicMock()

        mock_ai_response = MagicMock()
        mock_ai_response.choices = [MagicMock()]
        mock_ai_response.choices[0].message.content = "Description with specs"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_ai_response
        )

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(ai_service_with_openai, "_load_image_base64", return_value="base64data"),
        ):
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_http_response
            )

            result = await ai_service_with_openai.generate_description(
                category="electronics",
                image_paths=[test_image_path],
                product_url="https://example.com/product",
            )

            assert result == "Description with specs"
            # Verify URL was fetched
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_description_url_fetch_fails_continues(
        self, ai_service_with_openai, test_image_path
    ):
        """Test that description generation continues if URL fetch fails."""
        mock_ai_response = MagicMock()
        mock_ai_response.choices = [MagicMock()]
        mock_ai_response.choices[0].message.content = "Description without URL context"

        ai_service_with_openai.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_ai_response
        )

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch.object(ai_service_with_openai, "_load_image_base64", return_value="base64data"),
        ):
            # URL fetch fails
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Failed")
            )

            # Should still generate description
            result = await ai_service_with_openai.generate_description(
                category="electronics",
                image_paths=[test_image_path],
                product_url="https://example.com/product",
            )

            assert result == "Description without URL context"


class TestURLValidation:
    """Test SSRF protection in URL validation."""

    def test_validate_url_valid_http(self):
        """Test validation of valid HTTP URL."""
        _validate_url("http://example.com/product")
        # Should not raise

    def test_validate_url_valid_https(self):
        """Test validation of valid HTTPS URL."""
        _validate_url("https://example.com/product")
        # Should not raise

    def test_validate_url_invalid_scheme(self):
        """Test that non-HTTP schemes are rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            _validate_url("ftp://example.com/file")

    def test_validate_url_file_scheme(self):
        """Test that file:// URLs are rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            _validate_url("file:///etc/passwd")

    def test_validate_url_no_hostname(self):
        """Test that URLs without hostname are rejected."""
        with pytest.raises(ValueError, match="no hostname"):
            _validate_url("http://")

    def test_validate_url_localhost(self):
        """Test that localhost is blocked."""
        with pytest.raises(ValueError, match="localhost"):
            _validate_url("http://localhost:8080/admin")

    def test_validate_url_127_0_0_1(self):
        """Test that 127.0.0.1 is blocked."""
        with pytest.raises(ValueError, match="localhost"):
            _validate_url("http://127.0.0.1:8000")

    def test_validate_url_private_ip_10(self):
        """Test that private 10.x.x.x IPs are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            _validate_url("http://10.0.0.1/api")

    def test_validate_url_private_ip_192_168(self):
        """Test that private 192.168.x.x IPs are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            _validate_url("http://192.168.1.1/admin")

    def test_validate_url_private_ip_172(self):
        """Test that private 172.16-31.x.x IPs are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            _validate_url("http://172.16.0.1/admin")

    def test_validate_url_link_local(self):
        """Test that link-local 169.254.x.x IPs are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            _validate_url("http://169.254.1.1/api")

    def test_validate_url_aws_metadata(self):
        """Test that AWS metadata endpoint is blocked."""
        with pytest.raises(ValueError, match="metadata"):
            _validate_url("http://169.254.169.254/latest/meta-data/")

    def test_validate_url_gcp_metadata(self):
        """Test that GCP metadata endpoint is blocked."""
        with pytest.raises(ValueError, match="metadata"):
            _validate_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_validate_url_metadata_subdomain(self):
        """Test that subdomains of metadata are blocked."""
        with pytest.raises(ValueError, match="metadata"):
            _validate_url("http://api.metadata/data")

    def test_validate_url_valid_public_ip(self):
        """Test that public IPs are allowed."""
        _validate_url("http://8.8.8.8/")
        # Should not raise

    def test_validate_url_valid_domain(self):
        """Test that valid public domains are allowed."""
        _validate_url("https://www.google.com/search")
        _validate_url("https://api.github.com/repos")
        # Should not raise
