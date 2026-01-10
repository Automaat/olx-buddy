"""Test generate router endpoints."""

import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.ai import SUPPORTED_CATEGORIES

client = TestClient(app)


@pytest.fixture
def mock_storage_service():
    """Mock storage service."""
    with patch("app.routers.generate.storage_service") as mock:
        yield mock


@pytest.fixture
def mock_ai_service():
    """Mock AI service."""
    with patch("app.routers.generate.ai_service") as mock:
        yield mock


@pytest.fixture
def mock_price_service():
    """Mock price suggestion service."""
    with patch("app.routers.generate.price_service") as mock:
        yield mock


@pytest.fixture
def temp_image_file():
    """Create temporary image file."""

    def _create_image(filename: str = "test.jpg"):
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return (filename, buf, "image/jpeg")

    return _create_image


class TestUploadImagesEndpoint:
    """Test /api/generate/upload-images endpoint."""

    def test_upload_images_success(self, mock_storage_service, temp_image_file):
        """Test successful image upload."""
        mock_storage_service.save_images = AsyncMock(
            return_value=["uploads/image1.jpg", "uploads/image2.jpg"]
        )

        response = client.post(
            "/api/generate/upload-images",
            files=[
                ("files", temp_image_file("test1.jpg")),
                ("files", temp_image_file("test2.jpg")),
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["image_paths"]) == 2

    def test_upload_images_too_many_files(self, temp_image_file):
        """Test uploading more than 10 images."""
        files = [("files", temp_image_file(f"test{i}.jpg")) for i in range(11)]

        response = client.post("/api/generate/upload-images", files=files)

        assert response.status_code == 400
        assert "Maximum 10 images" in response.json()["detail"]

    def test_upload_images_no_files_saved(self, mock_storage_service, temp_image_file):
        """Test when no images are saved successfully."""
        mock_storage_service.save_images = AsyncMock(return_value=[])

        response = client.post(
            "/api/generate/upload-images", files=[("files", temp_image_file("test.jpg"))]
        )

        assert response.status_code == 400
        assert "Failed to save any images" in response.json()["detail"]

    def test_upload_images_invalid_file_type(self, mock_storage_service, temp_image_file):
        """Test uploading invalid file type."""
        mock_storage_service.save_images = AsyncMock(side_effect=ValueError("Invalid file type"))

        response = client.post(
            "/api/generate/upload-images", files=[("files", temp_image_file("test.jpg"))]
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_images_server_error(self, mock_storage_service, temp_image_file):
        """Test server error during upload."""
        mock_storage_service.save_images = AsyncMock(side_effect=Exception("Server error"))

        response = client.post(
            "/api/generate/upload-images", files=[("files", temp_image_file("test.jpg"))]
        )

        assert response.status_code == 500
        assert "Failed to upload images" in response.json()["detail"]


class TestGenerateDescriptionEndpoint:
    """Test /api/generate/description endpoint."""

    def test_generate_description_success(
        self, mock_ai_service, mock_price_service, mock_storage_service, tmp_path
    ):
        """Test successful description generation."""
        # Create test image
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(return_value="Generated description")
        mock_price_service.suggest_price = AsyncMock(
            return_value={
                "suggested_price": 100.0,
                "min_price": 80.0,
                "max_price": 120.0,
                "median_price": 100.0,
                "sample_size": 5,
                "similar_items": [],
            }
        )

        response = client.post(
            "/api/generate/description",
            data={
                "category": "womens_fashion",
                "image_paths": str(test_image),
                "brand": "Nike",
                "condition": "good",
                "size": "M",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "womens_fashion"
        assert data["description"] == "Generated description"
        assert data["suggested_price"] == 100.0

    def test_generate_description_invalid_category(self, mock_storage_service, tmp_path):
        """Test with invalid category."""
        # Create test image
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path

        response = client.post(
            "/api/generate/description",
            data={"category": "invalid_category", "image_paths": str(test_image)},
        )

        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]

    def test_generate_description_no_image_paths(self):
        """Test with no image paths."""
        response = client.post(
            "/api/generate/description",
            data={"category": "womens_fashion", "image_paths": " "},
        )

        assert response.status_code == 400
        assert "At least one image path required" in response.json()["detail"]

    def test_generate_description_image_outside_upload_dir(self, mock_storage_service, tmp_path):
        """Test with image path outside upload directory."""
        mock_storage_service.upload_dir = tmp_path / "uploads"
        mock_storage_service.upload_dir.mkdir()

        outside_file = tmp_path / "outside.jpg"
        outside_file.write_bytes(b"test")

        response = client.post(
            "/api/generate/description",
            data={"category": "womens_fashion", "image_paths": str(outside_file)},
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    def test_generate_description_image_not_found(self, mock_storage_service, tmp_path):
        """Test with non-existent image."""
        mock_storage_service.upload_dir = tmp_path

        response = client.post(
            "/api/generate/description",
            data={"category": "womens_fashion", "image_paths": str(tmp_path / "nonexistent.jpg")},
        )

        assert response.status_code == 404
        assert "Image not found" in response.json()["detail"]

    def test_generate_description_invalid_image_path(self, mock_storage_service, tmp_path):
        """Test with invalid image path."""
        mock_storage_service.upload_dir = tmp_path

        response = client.post(
            "/api/generate/description",
            data={"category": "womens_fashion", "image_paths": "\x00invalid"},
        )

        assert response.status_code == 400
        assert "Invalid image path" in response.json()["detail"]

    def test_generate_description_without_price_suggestion(
        self, mock_ai_service, mock_storage_service, tmp_path
    ):
        """Test description generation without price suggestion."""
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(return_value="Generated description")

        response = client.post(
            "/api/generate/description",
            data={
                "category": "womens_fashion",
                "image_paths": str(test_image),
                "include_price_suggestion": "false",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Generated description"
        assert data["suggested_price"] is None

    def test_generate_description_price_suggestion_fails(
        self, mock_ai_service, mock_price_service, mock_storage_service, tmp_path
    ):
        """Test when price suggestion fails but description succeeds."""
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(return_value="Generated description")
        mock_price_service.suggest_price = AsyncMock(side_effect=Exception("Price service failed"))

        response = client.post(
            "/api/generate/description",
            data={"category": "womens_fashion", "image_paths": str(test_image)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Generated description"
        assert data["suggested_price"] is None

    def test_generate_description_ai_service_unavailable(
        self, mock_ai_service, mock_storage_service, tmp_path
    ):
        """Test when AI service is unavailable."""
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(
            side_effect=RuntimeError("No AI provider available")
        )

        response = client.post(
            "/api/generate/description",
            data={"category": "womens_fashion", "image_paths": str(test_image)},
        )

        assert response.status_code == 503
        assert "AI service unavailable" in response.json()["detail"]

    def test_generate_description_server_error(
        self, mock_ai_service, mock_storage_service, tmp_path
    ):
        """Test server error during description generation."""
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(side_effect=Exception("Server error"))

        response = client.post(
            "/api/generate/description",
            data={"category": "womens_fashion", "image_paths": str(test_image)},
        )

        assert response.status_code == 500
        assert "Failed to generate description" in response.json()["detail"]

    def test_generate_description_multiple_images(
        self, mock_ai_service, mock_price_service, mock_storage_service, tmp_path
    ):
        """Test with multiple image paths."""
        test_image1 = tmp_path / "test1.jpg"
        test_image2 = tmp_path / "test2.jpg"
        test_image1.write_bytes(b"test1")
        test_image2.write_bytes(b"test2")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(return_value="Generated description")
        mock_price_service.suggest_price = AsyncMock(
            return_value={
                "suggested_price": 100.0,
                "min_price": 80.0,
                "max_price": 120.0,
                "median_price": 100.0,
                "sample_size": 5,
                "similar_items": [],
            }
        )

        response = client.post(
            "/api/generate/description",
            data={
                "category": "womens_fashion",
                "image_paths": f"{test_image1},{test_image2}",
            },
        )

        assert response.status_code == 200
        mock_ai_service.generate_description.assert_called_once()
        call_args = mock_ai_service.generate_description.call_args
        assert len(call_args[1]["image_paths"]) == 2

    def test_generate_description_with_all_parameters(
        self, mock_ai_service, mock_price_service, mock_storage_service, tmp_path
    ):
        """Test with all optional parameters."""
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(return_value="Generated description")
        mock_price_service.suggest_price = AsyncMock(
            return_value={
                "suggested_price": 100.0,
                "min_price": 80.0,
                "max_price": 120.0,
                "median_price": 100.0,
                "sample_size": 5,
                "similar_items": [],
            }
        )

        response = client.post(
            "/api/generate/description",
            data={
                "category": "womens_fashion",
                "image_paths": str(test_image),
                "brand": "Nike",
                "condition": "like_new",
                "size": "L",
                "additional_details": "Limited edition sneakers from 2020",
                "include_price_suggestion": "true",
            },
        )

        assert response.status_code == 200
        mock_ai_service.generate_description.assert_called_once()
        call_args = mock_ai_service.generate_description.call_args
        assert call_args[1]["brand"] == "Nike"
        assert call_args[1]["condition"] == "like_new"
        assert call_args[1]["size"] == "L"
        assert call_args[1]["additional_details"] == "Limited edition sneakers from 2020"

    def test_generate_description_truncates_long_additional_details(
        self, mock_ai_service, mock_price_service, mock_storage_service, tmp_path
    ):
        """Test that long additional details are truncated for price search."""
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"test")

        mock_storage_service.upload_dir = tmp_path
        mock_ai_service.generate_description = AsyncMock(return_value="Generated description")
        mock_price_service.suggest_price = AsyncMock(
            return_value={
                "suggested_price": 100.0,
                "min_price": 80.0,
                "max_price": 120.0,
                "median_price": 100.0,
                "sample_size": 5,
                "similar_items": [],
            }
        )

        long_details = "word " * 50  # More than 100 characters

        response = client.post(
            "/api/generate/description",
            data={
                "category": "womens_fashion",
                "image_paths": str(test_image),
                "additional_details": long_details,
            },
        )

        assert response.status_code == 200
        mock_price_service.suggest_price.assert_called_once()
        call_args = mock_price_service.suggest_price.call_args
        search_query = call_args[1]["search_query"]
        # Should be truncated
        assert len(search_query) < len(long_details) + len("womens_fashion")


class TestGetCategoriesEndpoint:
    """Test /api/generate/categories endpoint."""

    def test_get_categories_success(self):
        """Test successful retrieval of categories."""
        response = client.get("/api/generate/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0
        assert data["categories"] == SUPPORTED_CATEGORIES

    def test_get_categories_returns_all_expected_categories(self):
        """Test that all expected categories are returned."""
        response = client.get("/api/generate/categories")

        data = response.json()
        # Verify we get all supported categories
        assert set(data["categories"]) == set(SUPPORTED_CATEGORIES)
