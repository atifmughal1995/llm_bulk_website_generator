"""Service for AI content generation."""

import logging
from typing import Optional

from .ai_utils import generate_content
from .exceptions import AIContentError

logger = logging.getLogger(__name__)


class AIService:
    """Service for generating AI content."""

    def __init__(self, provider: Optional[str] = None) -> None:
        self._provider = provider

    def generate(
        self, prompt: str, temperature: float = 0.5, is_openai: bool = True
    ) -> str:
        """Generate content using the specified AI provider.

        Args:
            prompt: The prompt to send to the AI.
            temperature: The temperature for content generation.
            is_openai: Whether to use OpenAI (True) or Anthropic (False).

        Returns:
            The generated content as a string.

        Raises:
            AIContentError: If content generation fails.
        """
        logger.info('Generating AI content with temperature=%s', temperature)
        result = generate_content(prompt, temperature, is_openai)

        if result.startswith('Error:'):
            error_msg = result[6:]
            logger.error('AI content generation failed: %s', error_msg)
            raise AIContentError(error_msg)

        return result

    def generate_with_retry(
        self, prompt: str, temperature: float = 0.5, is_openai: bool = True, max_retries: int = 2
    ) -> str:
        """Generate content with retry logic for transient failures.

        Args:
            prompt: The prompt to send to the AI.
            temperature: The temperature for content generation.
            is_openai: Whether to use OpenAI (True) or Anthropic (False).
            max_retries: Maximum number of retry attempts.

        Returns:
            The generated content as a string.
        """
        last_error: Optional[str] = None
        for attempt in range(max_retries + 1):
            try:
                return self.generate(prompt, temperature, is_openai)
            except AIContentError as exc:
                last_error = str(exc)
                if attempt < max_retries:
                    logger.warning(
                        'AI generation attempt %d failed, retrying...', attempt + 1
                    )
                    import time
                    time.sleep(10)

        raise AIContentError(f'AI generation failed after {max_retries + 1} attempts: {last_error}')