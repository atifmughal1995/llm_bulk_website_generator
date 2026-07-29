"""Service for image-related operations."""

import logging
from typing import Optional

from .image_utils import get_image, get_placeholder, get_images

logger = logging.getLogger(__name__)


class ImageService:
    """Service for fetching and managing images."""

    def __init__(self) -> None:
        self._placeholder = get_placeholder()

    def get_image(self, query: str) -> str:
        """Fetch a single image URL from Unsplash.

        Args:
            query: The search query.

        Returns:
            The image URL or placeholder if failed.
        """
        try:
            url = get_image(query)
            if not url:
                logger.warning('No image found for query: %s', query)
                return self._placeholder
            return url
        except Exception as exc:
            logger.error('Failed to fetch image for query "%s": %s', query, exc)
            return self._placeholder

    def get_images(self, query: str, count: int = 10) -> list[str]:
        """Fetch multiple image URLs from Unsplash.

        Args:
            query: The search query.
            count: Number of images to fetch.

        Returns:
            List of image URLs.
        """
        try:
            urls = get_images(query, count)
            if not urls:
                logger.warning('No images found for query: %s', query)
                return [self._placeholder]
            return urls
        except Exception as exc:
            logger.error('Failed to fetch images for query "%s": %s', query, exc)
            return [self._placeholder]

    def get_placeholder(self) -> str:
        """Return the placeholder image URL."""
        return self._placeholder

    def regenerate_broken_images(
        self, html: str, project_id: int
    ) -> str:
        """Regenerate broken images in HTML using OpenAI's image API."""
        from .image_utils import html_regenerate_broken_img
        return html_regenerate_broken_img(html, project_id)