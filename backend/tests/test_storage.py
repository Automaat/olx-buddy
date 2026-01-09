"""Test storage service."""

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from PIL import Image

from app.services.storage import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE, StorageService


@pytest.fixture
def storage_service(tmp_path):
    """Create storage service with temporary directory."""
    return StorageService(upload_dir=tmp_path)


@pytest.fixture
def mock_upload_file():
    """Create a mock upload file."""

    def _create_upload(filename: str, content: bytes, content_type: str = "image/jpeg"):
        file = MagicMock(spec=UploadFile)
        file.filename = filename
        file.content_type = content_type
        file.read = AsyncMock(return_value=content)
        return file

    return _create_upload


@pytest.fixture
def valid_jpeg_bytes():
    """Create valid JPEG image bytes."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def valid_png_bytes():
    """Create valid PNG image bytes."""
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def large_image_bytes():
    """Create large image that exceeds MAX_IMAGE_SIZE."""
    img = Image.new("RGB", (3000, 3000), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def rgba_image_bytes():
    """Create RGBA image bytes."""
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestStorageService:
    """Test StorageService class."""

    def test_init_creates_directory(self, tmp_path):
        """Test that initialization creates upload directory."""
        upload_dir = tmp_path / "uploads"
        assert not upload_dir.exists()

        StorageService(upload_dir=upload_dir)

        assert upload_dir.exists()
        assert upload_dir.is_dir()

    def test_init_existing_directory(self, tmp_path):
        """Test initialization with existing directory."""
        tmp_path.mkdir(exist_ok=True)
        service = StorageService(upload_dir=tmp_path)

        assert service.upload_dir == tmp_path

    @pytest.mark.asyncio
    async def test_save_image_jpeg(
        self, storage_service, mock_upload_file, valid_jpeg_bytes, tmp_path
    ):
        """Test saving valid JPEG image."""
        file = mock_upload_file("test.jpg", valid_jpeg_bytes)

        result = await storage_service.save_image(file)

        assert result.startswith(str(tmp_path))
        assert Path(result).exists()
        assert Path(result).suffix == ".jpg"

    @pytest.mark.asyncio
    async def test_save_image_png(
        self, storage_service, mock_upload_file, valid_png_bytes, tmp_path
    ):
        """Test saving valid PNG image."""
        file = mock_upload_file("test.png", valid_png_bytes)

        result = await storage_service.save_image(file)

        assert result.startswith(str(tmp_path))
        assert Path(result).exists()

    @pytest.mark.asyncio
    async def test_save_image_webp(self, storage_service, mock_upload_file, tmp_path):
        """Test saving WebP image."""
        img = Image.new("RGB", (100, 100), color="yellow")
        buf = io.BytesIO()
        img.save(buf, format="WEBP")

        file = mock_upload_file("test.webp", buf.getvalue())

        result = await storage_service.save_image(file)

        assert result.startswith(str(tmp_path))
        assert Path(result).exists()

    @pytest.mark.asyncio
    async def test_save_image_invalid_extension(
        self, storage_service, mock_upload_file, valid_jpeg_bytes
    ):
        """Test saving file with invalid extension."""
        file = mock_upload_file("test.txt", valid_jpeg_bytes)

        with pytest.raises(ValueError, match="Invalid file type"):
            await storage_service.save_image(file)

    @pytest.mark.asyncio
    async def test_save_image_no_filename(
        self, storage_service, mock_upload_file, valid_jpeg_bytes
    ):
        """Test saving file with no filename."""
        file = mock_upload_file(None, valid_jpeg_bytes)

        with pytest.raises(ValueError, match="Invalid file type"):
            await storage_service.save_image(file)

    @pytest.mark.asyncio
    async def test_save_image_unique_filenames(
        self, storage_service, mock_upload_file, valid_jpeg_bytes
    ):
        """Test that saved images get unique filenames."""
        file1 = mock_upload_file("test.jpg", valid_jpeg_bytes)
        file2 = mock_upload_file("test.jpg", valid_jpeg_bytes)

        result1 = await storage_service.save_image(file1)
        result2 = await storage_service.save_image(file2)

        assert result1 != result2
        assert Path(result1).name != Path(result2).name

    @pytest.mark.asyncio
    async def test_save_image_resizes_large_image(
        self, storage_service, mock_upload_file, large_image_bytes, tmp_path
    ):
        """Test that large images are resized."""
        file = mock_upload_file("large.jpg", large_image_bytes)

        result = await storage_service.save_image(file)

        # Check that image was saved and resized
        saved_img = Image.open(result)
        assert saved_img.size[0] <= MAX_IMAGE_SIZE[0]
        assert saved_img.size[1] <= MAX_IMAGE_SIZE[1]

    @pytest.mark.asyncio
    async def test_save_image_converts_rgba_to_rgb(
        self, storage_service, mock_upload_file, rgba_image_bytes, tmp_path
    ):
        """Test that RGBA images are converted to RGB."""
        file = mock_upload_file("test.png", rgba_image_bytes)

        result = await storage_service.save_image(file)

        # Saved as JPEG which doesn't support transparency
        saved_img = Image.open(result)
        assert saved_img.mode == "RGB"

    @pytest.mark.asyncio
    async def test_save_image_converts_palette_mode(self, storage_service, mock_upload_file):
        """Test that palette mode images are converted to RGB."""
        img = Image.new("P", (100, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        file = mock_upload_file("test.png", buf.getvalue())

        result = await storage_service.save_image(file)

        saved_img = Image.open(result)
        assert saved_img.mode == "RGB"

    @pytest.mark.asyncio
    async def test_save_image_invalid_image_data(self, storage_service, mock_upload_file, tmp_path):
        """Test saving invalid image data falls back to raw save."""
        file = mock_upload_file("test.jpg", b"not an image")

        result = await storage_service.save_image(file)

        # Should still save the file even if processing fails
        assert Path(result).exists()

    @pytest.mark.asyncio
    async def test_save_image_case_insensitive_extension(
        self, storage_service, mock_upload_file, valid_jpeg_bytes
    ):
        """Test that file extensions are case insensitive."""
        file = mock_upload_file("test.JPG", valid_jpeg_bytes)

        result = await storage_service.save_image(file)

        assert Path(result).exists()

    @pytest.mark.asyncio
    async def test_save_images_multiple_files(
        self, storage_service, mock_upload_file, valid_jpeg_bytes, valid_png_bytes
    ):
        """Test saving multiple images."""
        files = [
            mock_upload_file("test1.jpg", valid_jpeg_bytes),
            mock_upload_file("test2.png", valid_png_bytes),
            mock_upload_file("test3.jpg", valid_jpeg_bytes),
        ]

        results = await storage_service.save_images(files)

        assert len(results) == 3
        assert all(Path(path).exists() for path in results)

    @pytest.mark.asyncio
    async def test_save_images_some_fail(self, storage_service, mock_upload_file, valid_jpeg_bytes):
        """Test saving multiple images where some fail."""
        files = [
            mock_upload_file("test1.jpg", valid_jpeg_bytes),
            mock_upload_file("test2.txt", b"not valid"),
            mock_upload_file("test3.jpg", valid_jpeg_bytes),
        ]

        results = await storage_service.save_images(files)

        # Should have 2 successful saves
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_save_images_empty_list(self, storage_service):
        """Test saving empty list of images."""
        results = await storage_service.save_images([])

        assert results == []

    def test_delete_image_success(self, storage_service, tmp_path):
        """Test deleting an image file."""
        # Create a test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test content")

        result = storage_service.delete_image(str(test_file))

        assert result is True
        assert not test_file.exists()

    def test_delete_image_not_found(self, storage_service, tmp_path):
        """Test deleting non-existent file."""
        result = storage_service.delete_image(str(tmp_path / "nonexistent.jpg"))

        assert result is False

    def test_delete_image_outside_upload_dir(self, storage_service, tmp_path):
        """Test deleting file outside upload directory."""
        # Create file outside upload dir
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "test.jpg"
        outside_file.write_bytes(b"test")

        result = storage_service.delete_image(str(outside_file))

        assert result is False
        assert outside_file.exists()  # File should not be deleted

    def test_delete_image_path_traversal_attempt(self, storage_service, tmp_path):
        """Test that path traversal attempts are blocked."""
        # Create a file outside the upload directory
        parent_dir = tmp_path.parent
        external_file = parent_dir / "external.jpg"
        external_file.write_bytes(b"external content")

        # Attempt to delete using path traversal
        traversal_path = str(tmp_path / ".." / "external.jpg")
        result = storage_service.delete_image(traversal_path)

        assert result is False
        assert external_file.exists()

    def test_delete_image_error_handling(self, storage_service, tmp_path):
        """Test error handling during deletion."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")

        with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
            result = storage_service.delete_image(str(test_file))

            assert result is False

    def test_allowed_extensions_constant(self):
        """Test that allowed extensions constant is correct."""
        expected = {".jpg", ".jpeg", ".png", ".webp"}
        assert ALLOWED_EXTENSIONS == expected

    def test_max_image_size_constant(self):
        """Test that max image size constant is correct."""
        assert MAX_IMAGE_SIZE == (1920, 1920)

    @pytest.mark.asyncio
    async def test_save_image_optimizes_quality(
        self, storage_service, mock_upload_file, valid_jpeg_bytes, tmp_path
    ):
        """Test that saved images are optimized."""
        file = mock_upload_file("test.jpg", valid_jpeg_bytes)

        result = await storage_service.save_image(file)

        # Check that file was saved (optimization is implicit in Pillow save with quality=85)
        assert Path(result).exists()
        saved_size = Path(result).stat().st_size

        # Optimized file should exist and have reasonable size
        assert saved_size > 0

    @pytest.mark.asyncio
    async def test_save_image_preserves_aspect_ratio(
        self, storage_service, mock_upload_file, tmp_path
    ):
        """Test that aspect ratio is preserved when resizing."""
        # Create image with known aspect ratio (2:1)
        img = Image.new("RGB", (2400, 1200), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        file = mock_upload_file("test.jpg", buf.getvalue())

        result = await storage_service.save_image(file)

        saved_img = Image.open(result)
        # Should maintain 2:1 aspect ratio
        assert abs(saved_img.size[0] / saved_img.size[1] - 2.0) < 0.01
