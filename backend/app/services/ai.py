"""AI service for description generation using multiple providers."""

import base64
import logging
from pathlib import Path
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


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

    async def generate_description(
        self,
        category: str,
        image_paths: list[str],
        brand: str | None = None,
        condition: str | None = None,
        size: str | None = None,
        additional_details: str | None = None,
    ) -> str:
        """Generate compelling description from images and item details."""
        prompt = self._build_prompt(category, brand, condition, size, additional_details)

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

    def _build_prompt(
        self,
        category: str,
        brand: str | None,
        condition: str | None,
        size: str | None,
        additional_details: str | None,
    ) -> str:
        """Build category-specific prompt for description generation."""
        base_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["default"]).format(
            brand=brand or "unknown",
            condition=condition or "good",
            size=size or "",
        )

        if additional_details:
            base_prompt += f"\n\nAdditional details: {additional_details}"

        return base_prompt

    async def _generate_with_openai(self, prompt: str, image_paths: list[str]) -> str:
        """Generate description using OpenAI GPT-4V."""
        if not self.openai_client:
            msg = "OpenAI client not initialized"
            raise RuntimeError(msg)

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        # Add images
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

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],  # pyrefly: ignore
            max_tokens=500,
        )

        return response.choices[0].message.content or ""

    async def _generate_with_anthropic(self, prompt: str, image_paths: list[str]) -> str:
        """Generate description using Anthropic Claude."""
        if not self.anthropic_api_key:
            msg = "Anthropic API key not configured"
            raise RuntimeError(msg)

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        # Add images
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
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": content}],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def _generate_with_ollama(self, prompt: str, image_paths: list[str]) -> str:
        """Generate description using local Ollama model."""
        if not self.ollama_base_url:
            msg = "Ollama base URL not configured"
            raise RuntimeError(msg)

        # Ollama vision models (llama3.2-vision)
        images = [self._load_image_base64(path) for path in image_paths[:4]]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": "llama3.2-vision",
                    "prompt": prompt,
                    "images": images,
                    "stream": False,
                },
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

        with path.open("rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


# Category-specific prompt templates
CATEGORY_PROMPTS = {
    "clothing": """Generate an engaging marketplace listing description for clothing item.

Brand: {brand}
Condition: {condition}
Size: {size}

Focus on:
- Material and fabric quality
- Fit and style
- Brand reputation
- Condition details
- Care instructions if visible

Write in casual, friendly tone. Make it SEO-friendly with relevant keywords. Max 200 words.""",
    "electronics": """Generate an engaging marketplace listing description for electronics.

Brand: {brand}
Condition: {condition}

Focus on:
- Technical specifications
- Features and capabilities
- Condition (scratches, battery health, etc.)
- What's included (accessories, box, charger)
- Original purchase date if known

Write clearly and precisely. Include relevant technical keywords. Max 200 words.""",
    "furniture": """Generate an engaging marketplace listing description for furniture.

Condition: {condition}
Dimensions: {size}

Focus on:
- Materials and construction
- Dimensions and measurements
- Condition (scratches, stains, wear)
- Style and design
- Assembly requirements

Write descriptively. Mention dimensions prominently. Max 200 words.""",
    "home_garden": """Generate an engaging marketplace listing description for home & garden item.

Brand: {brand}
Condition: {condition}

Focus on:
- Functionality and features
- Materials and quality
- Condition and wear
- Usage instructions
- Brand if notable

Write clearly. Emphasize practical benefits. Max 200 words.""",
    "sports": """Generate an engaging marketplace listing description for sports equipment.

Brand: {brand}
Condition: {condition}
Size: {size}

Focus on:
- Type and specifications
- Brand and quality
- Condition and usage level
- Size/fit information
- Performance features

Write enthusiastically. Include sport-specific keywords. Max 200 words.""",
    "toys_kids": """Generate an engaging marketplace listing description for toys/kids items.

Brand: {brand}
Condition: {condition}

Focus on:
- Age appropriateness
- Educational/entertainment value
- Safety and condition
- Brand and quality
- What's included

Write warmly and clearly. Mention safety. Max 200 words.""",
    "books_media": """Generate an engaging marketplace listing description for books/media.

Brand: {brand}
Condition: {condition}

Focus on:
- Title, author, edition
- Condition (pages, cover, marks)
- Content overview (no spoilers)
- Language
- Format (hardcover, paperback, etc.)

Write informatively. Be specific about condition. Max 200 words.""",
    "default": """Generate an engaging marketplace listing description.

Brand: {brand}
Condition: {condition}

Focus on:
- Key features and benefits
- Condition and quality
- Brand reputation
- What makes it valuable
- Any notable characteristics

Write clearly and engagingly. Use relevant keywords. Max 200 words.""",
}


# Supported categories
SUPPORTED_CATEGORIES = [
    "clothing",
    "electronics",
    "furniture",
    "home_garden",
    "sports",
    "toys_kids",
    "books_media",
    "other",
]
