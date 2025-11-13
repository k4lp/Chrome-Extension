"""Gemini API client wrapper."""

from typing import Optional, List, Dict, Any
import google.generativeai as genai
from loguru import logger

from ..config.models import Settings


class GeminiClient:
    """Client for interacting with Gemini API."""

    def __init__(self, settings: Settings):
        """Initialize Gemini client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._model = None
        self._api_keys = []
        self._current_key_index = 0
        self._configure()

    def _parse_api_keys(self) -> list[str]:
        """Parse newline-delimited API keys from settings.

        Returns:
            List of API keys
        """
        if not self.settings.api.gemini_api_key:
            return []

        keys_text = self.settings.api.gemini_api_key.strip()
        keys = [k.strip() for k in keys_text.split('\n') if k.strip()]
        return keys

    def _configure(self) -> None:
        """Configure Gemini API with current settings."""
        # Parse all available API keys
        self._api_keys = self._parse_api_keys()

        if not self._api_keys:
            logger.warning("Gemini API key not set")
            self._model = None
            return

        # Use the current key (default to first key)
        current_key = self._api_keys[self._current_key_index]
        genai.configure(api_key=current_key)

        # Configure model
        self._model = genai.GenerativeModel(
            model_name=self.settings.api.default_model,
            generation_config={
                "temperature": self.settings.api.temperature,
                "max_output_tokens": self.settings.api.max_output_tokens,
            },
        )
        logger.info(
            f"Configured Gemini model: {self.settings.api.default_model} "
            f"with API key #{self._current_key_index + 1}/{len(self._api_keys)}"
        )

    def _rotate_api_key(self) -> bool:
        """Rotate to the next available API key.

        Returns:
            True if rotation successful, False if no more keys
        """
        if len(self._api_keys) <= 1:
            logger.warning("No additional API keys available for rotation")
            return False

        # Move to next key
        self._current_key_index = (self._current_key_index + 1) % len(self._api_keys)

        logger.warning(
            f"🔄 Rotating to API key #{self._current_key_index + 1}/{len(self._api_keys)}"
        )

        # Reconfigure with new key
        try:
            current_key = self._api_keys[self._current_key_index]
            genai.configure(api_key=current_key)

            # Recreate model with new key
            self._model = genai.GenerativeModel(
                model_name=self.settings.api.default_model,
                generation_config={
                    "temperature": self.settings.api.temperature,
                    "max_output_tokens": self.settings.api.max_output_tokens,
                },
            )
            logger.info(f"✓ Successfully rotated to new API key")
            return True
        except Exception as e:
            logger.error(f"Failed to rotate API key: {e}")
            return False

    def reconfigure(self, settings: Settings) -> None:
        """Reconfigure client with new settings.

        Args:
            settings: New settings
        """
        self.settings = settings
        self._current_key_index = 0  # Reset to first key
        self._configure()

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_blocks: Optional[List[str]] = None,
        _retry_count: int = 0,
    ) -> str:
        """Generate response from Gemini with automatic key rotation on rate limits.

        Args:
            system_prompt: System prompt/instructions
            user_message: User's message
            context_blocks: Optional context blocks to include
            _retry_count: Internal retry counter

        Returns:
            Generated response text

        Raises:
            RuntimeError: If API key not configured or generation fails
        """
        if not self._model:
            raise RuntimeError("Gemini API not configured. Please set API key in settings.")

        try:
            # Build full prompt
            parts = [system_prompt, ""]

            # Add context blocks if provided
            if context_blocks:
                parts.append("=== CONTEXT ===")
                for i, block in enumerate(context_blocks, 1):
                    parts.append(f"\n--- Context Block {i} ---")
                    parts.append(block)
                parts.append("\n=== END CONTEXT ===\n")

            # Add user message
            parts.append(f"User: {user_message}")

            full_prompt = "\n".join(parts)

            # Generate response
            logger.debug(f"Generating with prompt length: {len(full_prompt)} chars")
            response = self._model.generate_content(full_prompt)

            if not response or not response.text:
                raise RuntimeError("Empty response from Gemini")

            logger.info("Successfully generated response")
            return response.text

        except Exception as e:
            error_str = str(e).lower()

            # Check for rate limit errors
            is_rate_limit = any(
                phrase in error_str
                for phrase in [
                    "rate limit",
                    "quota",
                    "429",
                    "resource exhausted",
                    "resource_exhausted",
                    "too many requests",
                ]
            )

            # Retry with key rotation if we have more keys to try
            if is_rate_limit and _retry_count < len(self._api_keys):
                logger.warning(f"⚠️ Rate limit hit on key #{self._current_key_index + 1}: {e}")

                # Try rotating to next key
                if self._rotate_api_key():
                    logger.info(
                        f"♻️ Retrying with new API key (attempt {_retry_count + 1}/{len(self._api_keys)})"
                    )
                    return self.generate(
                        system_prompt, user_message, context_blocks, _retry_count + 1
                    )
                else:
                    logger.error("Failed to rotate to new API key")

            # If all keys exhausted or other error
            if is_rate_limit:
                logger.error(
                    f"❌ Rate limit exhausted on all {len(self._api_keys)} API key(s)"
                )
                raise RuntimeError(
                    f"Rate limit exceeded on all available API keys. "
                    f"Please wait or add more API keys. Error: {e}"
                )

            logger.error(f"Error generating response: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    def generate_streaming(
        self,
        system_prompt: str,
        user_message: str,
        context_blocks: Optional[List[str]] = None,
        _retry_count: int = 0,
    ):
        """Generate streaming response from Gemini with automatic key rotation.

        Args:
            system_prompt: System prompt/instructions
            user_message: User's message
            context_blocks: Optional context blocks to include
            _retry_count: Internal retry counter

        Yields:
            Response chunks

        Raises:
            RuntimeError: If API key not configured or generation fails
        """
        if not self._model:
            raise RuntimeError("Gemini API not configured. Please set API key in settings.")

        try:
            # Build full prompt (same as generate)
            parts = [system_prompt, ""]

            if context_blocks:
                parts.append("=== CONTEXT ===")
                for i, block in enumerate(context_blocks, 1):
                    parts.append(f"\n--- Context Block {i} ---")
                    parts.append(block)
                parts.append("\n=== END CONTEXT ===\n")

            parts.append(f"User: {user_message}")
            full_prompt = "\n".join(parts)

            # Generate streaming response
            logger.debug(f"Generating streaming with prompt length: {len(full_prompt)} chars")
            response = self._model.generate_content(full_prompt, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text

            logger.info("Successfully completed streaming response")

        except Exception as e:
            error_str = str(e).lower()

            # Check for rate limit errors
            is_rate_limit = any(
                phrase in error_str
                for phrase in [
                    "rate limit",
                    "quota",
                    "429",
                    "resource exhausted",
                    "resource_exhausted",
                    "too many requests",
                ]
            )

            # Retry with key rotation if we have more keys to try
            if is_rate_limit and _retry_count < len(self._api_keys):
                logger.warning(
                    f"⚠️ Streaming rate limit hit on key #{self._current_key_index + 1}: {e}"
                )

                # Try rotating to next key
                if self._rotate_api_key():
                    logger.info(
                        f"♻️ Retrying streaming with new API key "
                        f"(attempt {_retry_count + 1}/{len(self._api_keys)})"
                    )
                    # Recursively retry with new key
                    yield from self.generate_streaming(
                        system_prompt, user_message, context_blocks, _retry_count + 1
                    )
                    return
                else:
                    logger.error("Failed to rotate to new API key")

            # If all keys exhausted or other error
            if is_rate_limit:
                logger.error(
                    f"❌ Streaming rate limit exhausted on all {len(self._api_keys)} API key(s)"
                )
                raise RuntimeError(
                    f"Rate limit exceeded on all available API keys. "
                    f"Please wait or add more API keys. Error: {e}"
                )

            logger.error(f"Error in streaming generation: {e}")
            raise RuntimeError(f"Failed to generate streaming response: {e}")

    def is_configured(self) -> bool:
        """Check if client is properly configured.

        Returns:
            True if configured
        """
        return self._model is not None and bool(self.settings.api.gemini_api_key)
