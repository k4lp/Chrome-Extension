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
        self._configure()

    def _configure(self) -> None:
        """Configure Gemini API with current settings."""
        if not self.settings.api.gemini_api_key:
            logger.warning("Gemini API key not set")
            return

        genai.configure(api_key=self.settings.api.gemini_api_key)

        # Configure model
        self._model = genai.GenerativeModel(
            model_name=self.settings.api.default_model,
            generation_config={
                "temperature": self.settings.api.temperature,
                "max_output_tokens": self.settings.api.max_output_tokens,
            },
        )
        logger.info(f"Configured Gemini model: {self.settings.api.default_model}")

    def reconfigure(self, settings: Settings) -> None:
        """Reconfigure client with new settings.

        Args:
            settings: New settings
        """
        self.settings = settings
        self._configure()

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_blocks: Optional[List[str]] = None,
    ) -> str:
        """Generate response from Gemini.

        Args:
            system_prompt: System prompt/instructions
            user_message: User's message
            context_blocks: Optional context blocks to include

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
            logger.error(f"Error generating response: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    def generate_streaming(
        self,
        system_prompt: str,
        user_message: str,
        context_blocks: Optional[List[str]] = None,
    ):
        """Generate streaming response from Gemini.

        Args:
            system_prompt: System prompt/instructions
            user_message: User's message
            context_blocks: Optional context blocks to include

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
            logger.error(f"Error in streaming generation: {e}")
            raise RuntimeError(f"Failed to generate streaming response: {e}")

    def is_configured(self) -> bool:
        """Check if client is properly configured.

        Returns:
            True if configured
        """
        return self._model is not None and bool(self.settings.api.gemini_api_key)
