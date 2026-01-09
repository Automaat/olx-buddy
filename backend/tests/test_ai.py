"""Test AI service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.ai import CATEGORY_PROMPTS, SUPPORTED_CATEGORIES, AIService


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
        """Test prompt building for clothing category."""
        prompt = ai_service._build_prompt("clothing", "Nike", "like_new", "M", None)

        assert "clothing" in prompt.lower()
        assert "Nike" in prompt
        assert "like_new" in prompt
        assert "M" in prompt

    def test_build_prompt_electronics_category(self, ai_service):
        """Test prompt building for electronics category."""
        prompt = ai_service._build_prompt("electronics", "Apple", "good", None, None)

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
            assert category in CATEGORY_PROMPTS

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
        expected_categories = [
            "clothing",
            "electronics",
            "furniture",
            "home_garden",
            "sports",
            "toys_kids",
            "books_media",
            "other",
        ]
        assert SUPPORTED_CATEGORIES == expected_categories

    def test_category_prompts_structure(self):
        """Test that category prompts have proper structure."""
        for category, prompt in CATEGORY_PROMPTS.items():
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Check for template variables
            assert "{condition}" in prompt or category == "furniture"
