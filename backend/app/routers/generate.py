"""API endpoints for AI-powered description and price generation."""

import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import (
    CategoryResponse,
    GenerateDescriptionResponse,
    ImageUploadResponse,
)
from app.services.ai import SUPPORTED_CATEGORIES, AIService
from app.services.scraper import PriceSuggestionService, ScraperService
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generate"])

# Initialize services
storage_service = StorageService()
ai_service = AIService()
scraper_service = ScraperService()
price_service = PriceSuggestionService(scraper_service)


@router.post("/upload-images", response_model=ImageUploadResponse)
async def upload_images(
    files: Annotated[list[UploadFile], File(description="Images to upload (max 10)")],
) -> ImageUploadResponse:
    """Upload item photos for description generation."""
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 images allowed",
        )

    try:
        image_paths = await storage_service.save_images(files)

        if not image_paths:
            raise HTTPException(
                status_code=400,
                detail="Failed to save any images",
            )

        return ImageUploadResponse(
            image_paths=image_paths,
            count=len(image_paths),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Image upload failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to upload images",
        ) from e


@router.post("/description", response_model=GenerateDescriptionResponse)
async def generate_description(
    category: Annotated[str, Form()],
    image_paths: Annotated[str, Form(description="Comma-separated image paths")],
    brand: Annotated[str | None, Form()] = None,
    condition: Annotated[str | None, Form()] = None,
    size: Annotated[str | None, Form()] = None,
    additional_details: Annotated[str | None, Form()] = None,
    include_price_suggestion: Annotated[bool, Form()] = True,
) -> GenerateDescriptionResponse:
    """Generate description and price suggestion from images and details."""
    # Validate category
    if category not in SUPPORTED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Supported: {', '.join(SUPPORTED_CATEGORIES)}",
        )

    # Parse image paths
    paths = [p.strip() for p in image_paths.split(",") if p.strip()]
    if not paths:
        raise HTTPException(
            status_code=400,
            detail="At least one image path required",
        )

    try:
        # Generate description
        description = await ai_service.generate_description(
            category=category,
            image_paths=paths,
            brand=brand,
            condition=condition,
            size=size,
            additional_details=additional_details,
        )

        # Generate price suggestion if requested
        price_data = {}
        if include_price_suggestion:
            try:
                # Build search query from brand and category
                search_query = " ".join(filter(None, [brand, category.replace("_", " ")]))
                if additional_details:
                    search_query += f" {additional_details[:50]}"

                price_data = await price_service.suggest_price(
                    search_query=search_query,
                    category=category,
                    brand=brand,
                    condition=condition,
                )
            except Exception as e:
                logger.warning("Price suggestion failed: %s", e)
                # Continue without price suggestion

        return GenerateDescriptionResponse(
            description=description,
            suggested_price=price_data.get("suggested_price"),
            min_price=price_data.get("min_price"),
            max_price=price_data.get("max_price"),
            median_price=price_data.get("median_price"),
            sample_size=price_data.get("sample_size", 0),
            similar_items=price_data.get("similar_items", []),
        )

    except RuntimeError as e:
        logger.error("AI generation failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable. Please configure at least one AI provider.",
        ) from e
    except Exception as e:
        logger.error("Description generation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate description",
        ) from e


@router.get("/categories", response_model=CategoryResponse)
async def get_categories() -> CategoryResponse:
    """Get list of supported categories."""
    return CategoryResponse(categories=SUPPORTED_CATEGORIES)
