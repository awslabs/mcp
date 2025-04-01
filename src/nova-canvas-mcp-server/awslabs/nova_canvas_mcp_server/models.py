"""Pydantic models for Amazon Nova Canvas image generation."""

import random
import re
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Dict, List, Literal, Optional


class Quality(str, Enum):
    """Quality options for image generation.

    Attributes:
        STANDARD: Standard quality image generation.
        PREMIUM: Premium quality image generation with enhanced details.
    """

    STANDARD = "standard"
    PREMIUM = "premium"


class TaskType(str, Enum):
    """Task types for image generation.

    Attributes:
        TEXT_IMAGE: Generate an image from text description.
        COLOR_GUIDED_GENERATION: Generate an image guided by both text and color palette.
    """

    TEXT_IMAGE = "TEXT_IMAGE"
    COLOR_GUIDED_GENERATION = "COLOR_GUIDED_GENERATION"


class ImageGenerationConfig(BaseModel):
    """Configuration for image generation.

    This model defines the parameters that control the image generation process,
    including dimensions, quality, and generation settings.

    Attributes:
        width: Width of the generated image (320-4096, must be divisible by 16).
        height: Height of the generated image (320-4096, must be divisible by 16).
        quality: Quality level of the generated image (standard or premium).
        cfgScale: How strongly the image adheres to the prompt (1.1-10.0).
        seed: Seed for reproducible generation (0-858993459).
        numberOfImages: Number of images to generate (1-5).
    """

    width: int = Field(default=1024, ge=320, le=4096)
    height: int = Field(default=1024, ge=320, le=4096)
    quality: Quality = Quality.STANDARD
    cfgScale: float = Field(default=6.5, ge=1.1, le=10.0)
    seed: int = Field(
        default_factory=lambda: random.randint(0, 858993459), ge=0, le=858993459
    )
    numberOfImages: int = Field(default=1, ge=1, le=5)

    @field_validator("width", "height")
    @classmethod
    def must_be_divisible_by_16(cls, v: int) -> int:
        """Validate that width and height are divisible by 16.

        Args:
            v: The width or height value to validate.

        Returns:
            The validated value if it passes.

        Raises:
            ValueError: If the value is not divisible by 16.
        """
        if v % 16 != 0:
            raise ValueError("Value must be divisible by 16")
        return v

    @model_validator(mode="after")
    def validate_aspect_ratio_and_total_pixels(self):
        """Validate aspect ratio and total pixel count.

        Ensures that:
        1. The aspect ratio is between 1:4 and 4:1
        2. The total pixel count is less than 4,194,304

        Returns:
            The validated model if it passes.

        Raises:
            ValueError: If the aspect ratio or total pixel count is invalid.
        """
        width = self.width
        height = self.height

        # Check aspect ratio between 1:4 and 4:1
        aspect_ratio = width / height
        if aspect_ratio < 0.25 or aspect_ratio > 4.0:
            raise ValueError("Aspect ratio must be between 1:4 and 4:1")

        # Check total pixel count
        total_pixels = width * height
        if total_pixels >= 4194304:
            raise ValueError("Total pixel count must be less than 4,194,304")

        return self


class TextToImageParams(BaseModel):
    """Parameters for text-to-image generation.

    This model defines the text prompts used to generate images.

    Attributes:
        text: The text description of the image to generate (1-1024 characters).
        negativeText: Optional text to define what not to include in the image (1-1024 characters).
    """

    text: str = Field(..., min_length=1, max_length=1024)
    negativeText: Optional[str] = Field(default=None, min_length=1, max_length=1024)


class ColorGuidedGenerationParams(BaseModel):
    """Parameters for color-guided generation.

    This model defines the text prompts and color palette used to generate images.

    Attributes:
        colors: List of hexadecimal color values (e.g., "#FF9800") to guide the image generation.
        text: The text description of the image to generate (1-1024 characters).
        negativeText: Optional text to define what not to include in the image (1-1024 characters).
    """

    colors: List[str] = Field(..., max_length=10)
    text: str = Field(..., min_length=1, max_length=1024)
    negativeText: Optional[str] = Field(default=None, min_length=1, max_length=1024)

    @field_validator("colors")
    @classmethod
    def validate_hex_colors(cls, v: List[str]) -> List[str]:
        """Validate that colors are in the correct hexadecimal format.

        Args:
            v: List of color strings to validate.

        Returns:
            The validated list if all colors pass.

        Raises:
            ValueError: If any color is not a valid hexadecimal color in the format '#RRGGBB'.
        """
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for color in v:
            if not hex_pattern.match(color):
                raise ValueError(
                    f"Color '{color}' is not a valid hexadecimal color in the format '#RRGGBB'"
                )
        return v


class TextImageRequest(BaseModel):
    """Request model for text-to-image generation.

    This model combines the task type, text parameters, and generation configuration
    for a complete text-to-image request.

    Attributes:
        taskType: The type of task (TEXT_IMAGE).
        textToImageParams: Parameters for text-to-image generation.
        imageGenerationConfig: Configuration for image generation.
    """

    taskType: Literal[TaskType.TEXT_IMAGE] = TaskType.TEXT_IMAGE
    textToImageParams: TextToImageParams
    imageGenerationConfig: Optional[ImageGenerationConfig] = Field(
        default_factory=ImageGenerationConfig
    )

    # instead of overriding model_dump, we add a post-model_dump extension method
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary suitable for API requests.

        Returns:
            A dictionary representation of the model suitable for API requests.
        """
        text_to_image_params = self.textToImageParams.model_dump()
        # Remove negativeText if it's None
        if text_to_image_params.get("negativeText") is None:
            text_to_image_params.pop("negativeText", None)

        return {
            "taskType": self.taskType,
            "textToImageParams": text_to_image_params,
            "imageGenerationConfig": self.imageGenerationConfig.model_dump()
            if self.imageGenerationConfig
            else None,
        }


class ColorGuidedRequest(BaseModel):
    """Request model for color-guided generation.

    This model combines the task type, color-guided parameters, and generation configuration
    for a complete color-guided generation request.

    Attributes:
        taskType: The type of task (COLOR_GUIDED_GENERATION).
        colorGuidedGenerationParams: Parameters for color-guided generation.
        imageGenerationConfig: Configuration for image generation.
    """

    taskType: Literal[
        TaskType.COLOR_GUIDED_GENERATION
    ] = TaskType.COLOR_GUIDED_GENERATION
    colorGuidedGenerationParams: ColorGuidedGenerationParams
    imageGenerationConfig: Optional[ImageGenerationConfig] = Field(
        default_factory=ImageGenerationConfig
    )

    # instead of overriding model_dump, we add a post-model_dump extension method
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary suitable for API requests.

        Returns:
            A dictionary representation of the model suitable for API requests.
        """
        color_guided_params = self.colorGuidedGenerationParams.model_dump()
        # Remove negativeText if it's None
        if color_guided_params.get("negativeText") is None:
            color_guided_params.pop("negativeText", None)

        return {
            "taskType": self.taskType,
            "colorGuidedGenerationParams": color_guided_params,
            "imageGenerationConfig": self.imageGenerationConfig.model_dump()
            if self.imageGenerationConfig
            else None,
        }


class McpImageGenerationResponse(BaseModel):
    """Response from image generation API.

    This model represents the response from the Amazon Nova Canvas API
    for both text-to-image and color-guided image generation.
    """

    status: str
    paths: List[str]


class ImageGenerationResponse(BaseModel):
    """Response from image generation API.

    This model represents the response from the Amazon Nova Canvas API
    for both text-to-image and color-guided image generation.

    Attributes:
        status: Status of the image generation request ('success' or 'error').
        message: Message describing the result or error.
        paths: List of paths to the generated image files.
        images: List of PIL Image objects.
        prompt: The text prompt used to generate the images.
        negative_prompt: The negative prompt used to generate the images, if any.
        colors: The colors used to guide the image generation, if any.
    """

    status: str
    message: str
    paths: List[str]
    prompt: str
    negative_prompt: Optional[str] = None
    colors: Optional[List[str]] = None

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True  # Allow PIL.Image.Image type

    def __getitem__(self, key: str) -> Any:
        """Support dictionary-style access for backward compatibility.

        Args:
            key: The attribute name to access.

        Returns:
            The value of the attribute.

        Raises:
            KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}' not found in ImageGenerationResponse")
