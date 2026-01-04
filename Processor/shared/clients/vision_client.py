"""
Vision Model Client for Image Description

Supports both Ollama (LLaVA) and OpenAI (GPT-4 Vision) for image analysis.
"""

import os
import base64
import logging
from typing import Optional, Union
from pathlib import Path
from io import BytesIO
from PIL import Image
from config import config

logger = logging.getLogger(__name__)


class VisionModelClient:
    """Client for vision language models to describe images."""

    def __init__(self):
        # Get vision configuration from config.py
        vision_config = config.get_vision_config()

        self.enabled = vision_config.get('enabled', True)
        self.provider = vision_config.get('provider', 'ollama').lower()

        # Model configuration
        if self.provider == "ollama":
            self.model = vision_config.get('ollama_model', 'llava:13b')
            self.api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            logger.info(f"🖼️ Vision Model: Ollama {self.model}")
        else:
            self.model = vision_config.get('openai_model', 'gpt-4-vision-preview')
            self.api_key = os.getenv("OPENAI_API_KEY")
            logger.info(f"🖼️ Vision Model: OpenAI {self.model}")

        # Image processing settings
        self.resize_images = vision_config.get('resize_for_vision', True)
        self.max_dimension = vision_config.get('max_dimension', 1024)
        self.min_width = vision_config.get('min_width', 100)
        self.min_height = vision_config.get('min_height', 100)

        # Description prompt from config.py
        self.description_prompt = config.get_vision_prompt('default')

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds max dimensions."""
        if not self.resize_images:
            return image

        width, height = image.size

        if width <= self.max_dimension and height <= self.max_dimension:
            return image

        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = self.max_dimension
            new_height = int(height * (self.max_dimension / width))
        else:
            new_height = self.max_dimension
            new_width = int(width * (self.max_dimension / height))

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _image_to_base64(self, image: Union[Image.Image, bytes, str, Path]) -> str:
        """Convert image to base64 string."""
        if isinstance(image, (str, Path)):
            with open(image, "rb") as f:
                image_bytes = f.read()
        elif isinstance(image, bytes):
            image_bytes = image
        elif isinstance(image, Image.Image):
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

        return base64.b64encode(image_bytes).decode("utf-8")

    async def describe_image_ollama(self, image: Union[Image.Image, bytes, str, Path]) -> str:
        """Describe image using Ollama LLaVA model."""
        import httpx

        # Process image
        if isinstance(image, Image.Image):
            pil_image = image
        else:
            if isinstance(image, (str, Path)):
                pil_image = Image.open(image)
            elif isinstance(image, bytes):
                pil_image = Image.open(BytesIO(image))
            else:
                raise ValueError(f"Unsupported image type: {type(image)}")

        # Resize if needed
        pil_image = self._resize_image(pil_image)

        # Convert to base64
        image_base64 = self._image_to_base64(pil_image)

        # Call Ollama API
        payload = {
            "model": self.model,
            "prompt": self.description_prompt,
            "images": [image_base64],
            "stream": False
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.api_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

    async def describe_image_openai(self, image: Union[Image.Image, bytes, str, Path]) -> str:
        """Describe image using OpenAI GPT-4 Vision."""
        from openai import AsyncOpenAI

        # Process image
        if isinstance(image, Image.Image):
            pil_image = image
        else:
            if isinstance(image, (str, Path)):
                pil_image = Image.open(image)
            elif isinstance(image, bytes):
                pil_image = Image.open(BytesIO(image))
            else:
                raise ValueError(f"Unsupported image type: {type(image)}")

        # Resize if needed
        pil_image = self._resize_image(pil_image)

        # Convert to base64
        image_base64 = self._image_to_base64(pil_image)

        # Call OpenAI API
        client = AsyncOpenAI(api_key=self.api_key)

        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.description_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )

        return response.choices[0].message.content

    async def describe_image(self, image: Union[Image.Image, bytes, str, Path]) -> Optional[str]:
        """
        Describe image using configured vision model.

        Args:
            image: PIL Image, bytes, or path to image file

        Returns:
            str: Image description or None if disabled

        """
        if not self.enabled:
            logger.debug("Image extraction disabled")
            return None

        try:
            # Validate image size
            if isinstance(image, Image.Image):
                pil_image = image
            elif isinstance(image, (str, Path)):
                pil_image = Image.open(image)
            elif isinstance(image, bytes):
                pil_image = Image.open(BytesIO(image))
            else:
                raise ValueError(f"Unsupported image type: {type(image)}")

            width, height = pil_image.size
            if width < self.min_width or height < self.min_height:
                logger.debug(f"Image too small: {width}x{height}")
                return None

            # Call appropriate provider
            if self.provider == "ollama":
                description = await self.describe_image_ollama(image)
            else:  # openai
                description = await self.describe_image_openai(image)

            logger.info(f"✅ Generated image description ({len(description)} chars)")
            return description

        except Exception as e:
            logger.error(f"❌ Failed to describe image: {e}")
            return None

    def is_enabled(self) -> bool:
        """Check if image extraction is enabled."""
        return self.enabled


# Global instance
_vision_client: Optional[VisionModelClient] = None


def get_vision_client() -> VisionModelClient:
    """Get or create global vision client instance."""
    global _vision_client

    if _vision_client is None:
        _vision_client = VisionModelClient()

    return _vision_client
