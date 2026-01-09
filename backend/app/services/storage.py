"""Storage service for handling file uploads."""

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Max image size
MAX_IMAGE_SIZE = (1920, 1920)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class StorageService:
    """Handles file uploads and storage."""

    def __init__(self, upload_dir: Path = UPLOAD_DIR) -> None:
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(exist_ok=True)

    async def save_image(self, file: UploadFile) -> str:
        """Save uploaded image, optimize and resize if needed."""
        # Validate extension
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            msg = f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            raise ValueError(msg)

        # Generate unique filename
        unique_name = f"{uuid.uuid4()}{file_ext}"
        file_path = self.upload_dir / unique_name

        # Read and process image
        content = await file.read()

        try:
            # Open with Pillow
            img = Image.open(file.file)

            # Convert RGBA to RGB if needed
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = background

            # Resize if too large
            if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
                img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
                logger.info("Resized image from original size to %s", img.size)

            # Save optimized
            img.save(
                file_path,
                format="JPEG",
                quality=85,
                optimize=True,
            )

            logger.info("Saved image: %s", unique_name)
            return str(file_path)

        except Exception as e:
            logger.error("Failed to process image: %s", e)
            # Save original if processing fails
            with file_path.open("wb") as f:
                f.write(content)
            return str(file_path)

    async def save_images(self, files: list[UploadFile]) -> list[str]:
        """Save multiple images."""
        paths = []
        for file in files:
            try:
                path = await self.save_image(file)
                paths.append(path)
            except Exception as e:
                logger.error("Failed to save image %s: %s", file.filename, e)
                continue
        return paths

    def delete_image(self, file_path: str) -> bool:
        """Delete an image file."""
        try:
            path = Path(file_path)
            if path.exists() and path.is_relative_to(self.upload_dir):
                path.unlink()
                logger.info("Deleted image: %s", file_path)
                return True
            return False
        except Exception as e:
            logger.error("Failed to delete image %s: %s", file_path, e)
            return False
