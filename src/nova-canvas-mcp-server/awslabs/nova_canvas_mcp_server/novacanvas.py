# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Amazon Nova Canvas API interaction module.

This module provides functions for generating images using Amazon Nova Canvas
through the AWS Bedrock service. It handles the API requests, response processing,
and image saving functionality.
"""

import base64
import json
import os
import random
from .models import (
    ColorGuidedGenerationParams,
    ColorGuidedRequest,
    ImageGenerationConfig,
    ImageGenerationResponse,
    Quality,
    TextImageRequest,
    TextToImageParams,
)
from awslabs.nova_canvas_mcp_server.consts import (
    DEFAULT_CFG_SCALE,
    DEFAULT_HEIGHT,
    DEFAULT_NUMBER_OF_IMAGES,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_QUALITY,
    DEFAULT_WIDTH,
    NOVA_CANVAS_MODEL_ID,
)
from loguru import logger
from typing import TYPE_CHECKING, Any, Dict, List, Optional


if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
else:
    BedrockRuntimeClient = object


def save_generated_images(
    base64_images: List[str],
    filename: Optional[str] = None,
    number_of_images: int = DEFAULT_NUMBER_OF_IMAGES,
    prefix: str = 'nova_canvas',
    workspace_dir: Optional[str] = None,
) -> Dict[str, List]:
    """Save base64-encoded images to files.

    Args:
        base64_images: List of base64-encoded image data.
        filename: Base filename to use (without extension). If None, a random name is generated.
        number_of_images: Number of images being saved.
        prefix: Prefix to use for randomly generated filenames.
        workspace_dir: Directory where the images should be saved. If None, uses current directory.

    Returns:
        Dictionary with lists of paths to the saved image files and PIL Image objects.
    """
    logger.debug(f'Saving {len(base64_images)} images')
    # Determine the output directory
    if workspace_dir:
        output_dir = os.path.join(workspace_dir, DEFAULT_OUTPUT_DIR)
    else:
        output_dir = DEFAULT_OUTPUT_DIR

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the generated images
    saved_paths: List[str] = []
    for i, base64_image_data in enumerate(base64_images):
        # Generate filename if not provided
        if filename:
            image_filename = (
                f'{filename}_{i + 1}.png' if number_of_images > 1 else f'{filename}.png'
            )
        else:
            # Generate a random filename
            random_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
            image_filename = f'{prefix}_{random_id}_{i + 1}.png'

        # Decode the base64 image data
        image_data = base64.b64decode(base64_image_data)

        # Save the image
        image_path = os.path.join(output_dir, image_filename)
        with open(image_path, 'wb') as file:
            file.write(image_data)
        # Convert to absolute path
        abs_image_path = os.path.abspath(image_path)
        saved_paths.append(abs_image_path)

    return {'paths': saved_paths}


async def invoke_nova_canvas(
    request_model_dict: Dict[str, Any],
    bedrock_runtime_client: BedrockRuntimeClient,
) -> Dict[str, Any]:
    """Invoke the Nova Canvas API with the given request.

    Args:
        request_model_dict: Dictionary representation of the request model.
        bedrock_runtime_client: BedrockRuntimeClient object.

    Returns:
        Dictionary containing the API response.

    Raises:
        Exception: If the API call fails.
    """
    logger.debug('Invoking Nova Canvas API')

    # Convert the request payload to JSON
    request = json.dumps(request_model_dict)

    try:
        # Invoke the model
        logger.info(f'Sending request to Nova Canvas model: {NOVA_CANVAS_MODEL_ID}')
        response = bedrock_runtime_client.invoke_model(modelId=NOVA_CANVAS_MODEL_ID, body=request)

        # Decode the response body
        result = json.loads(response['body'].read().decode('utf-8'))
        logger.info('Nova Canvas API call successful')
        return result
    except Exception as e:
        logger.error(f'Nova Canvas API call failed: {str(e)}')
        raise


async def generate_image_with_text(
    prompt: str,
    bedrock_runtime_client: BedrockRuntimeClient,
    negative_prompt: Optional[str] = None,
    filename: Optional[str] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    quality: str = DEFAULT_QUALITY,
    cfg_scale: float = DEFAULT_CFG_SCALE,
    seed: Optional[int] = None,
    number_of_images: int = DEFAULT_NUMBER_OF_IMAGES,
    workspace_dir: Optional[str] = None,
) -> ImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with text prompt.

    This function uses Amazon Nova Canvas to generate images based on a text prompt.
    The generated image will be saved to a file and the path will be returned.

    Args:
        prompt: The text description of the image to generate (1-1024 characters).
        bedrock_runtime_client: BedrockRuntimeClient object.
        negative_prompt: Text to define what not to include in the image (1-1024 characters).
        filename: The name of the file to save the image to (without extension).
            If not provided, a random name will be generated.
        width: The width of the generated image (320-4096, divisible by 16).
        height: The height of the generated image (320-4096, divisible by 16).
        quality: The quality of the generated image ("standard" or "premium").
        cfg_scale: How strongly the image adheres to the prompt (1.1-10.0).
        seed: Seed for generation (0-858,993,459). Random if not provided.
        number_of_images: The number of images to generate (1-5).
        workspace_dir: Directory where the images should be saved. If None, uses current directory.

    Returns:
        ImageGenerationResponse: An object containing the paths to the generated images,
        PIL Image objects, and status information.
    """
    logger.debug(f"Generating text-to-image with prompt: '{prompt[:30]}...' ({width}x{height})")

    try:
        # Validate input parameters using Pydantic
        try:
            logger.debug('Validating parameters and creating request model')

            # Create image generation config
            config = ImageGenerationConfig(
                width=width,
                height=height,
                quality=Quality.STANDARD if quality == DEFAULT_QUALITY else Quality.PREMIUM,
                cfgScale=cfg_scale,
                seed=seed if seed is not None else random.randint(0, 858993459),
                numberOfImages=number_of_images,
            )

            # Create text-to-image params
            # The Nova Canvas API doesn't accept null for negativeText
            if negative_prompt is not None:
                text_params = TextToImageParams(text=prompt, negativeText=negative_prompt)
            else:
                text_params = TextToImageParams(text=prompt)

            # Create the full request
            request_model = TextImageRequest(
                textToImageParams=text_params, imageGenerationConfig=config
            )

            # Convert model to dictionary
            request_model_dict = request_model.to_api_dict()
            logger.info('Request validation successful')

        except Exception as e:
            logger.error(f'Parameter validation failed: {str(e)}')
            return ImageGenerationResponse(
                status='error',
                message=f'Validation error: {str(e)}',
                paths=[],
                prompt=prompt,
                negative_prompt=negative_prompt,
            )

        try:
            # Invoke the Nova Canvas API
            logger.debug('Sending request to Nova Canvas API')
            model_response = await invoke_nova_canvas(request_model_dict, bedrock_runtime_client)

            # Extract the image data
            base64_images = model_response['images']
            logger.info(f'Received {len(base64_images)} images from Nova Canvas API')

            # Save the generated images
            result = save_generated_images(
                base64_images,
                filename,
                number_of_images,
                prefix='nova_canvas',
                workspace_dir=workspace_dir,
            )

            logger.info(f'Successfully generated {len(result["paths"])} image(s)')
            return ImageGenerationResponse(
                status='success',
                message=f'Generated {len(result["paths"])} image(s)',
                paths=result['paths'],
                prompt=prompt,
                negative_prompt=negative_prompt,
            )
        except Exception as e:
            logger.error(f'Image generation failed: {str(e)}')
            return ImageGenerationResponse(
                status='error',
                message=str(e),
                paths=[],
                prompt=prompt,
                negative_prompt=negative_prompt,
            )

    except Exception as e:
        logger.error(f'Unexpected error in generate_image_with_text: {str(e)}')
        return ImageGenerationResponse(
            status='error',
            message=str(e),
            paths=[],
            prompt=prompt,
            negative_prompt=negative_prompt,
        )


async def generate_image_with_colors(
    prompt: str,
    colors: List[str],
    bedrock_runtime_client: BedrockRuntimeClient,
    negative_prompt: Optional[str] = None,
    filename: Optional[str] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    quality: str = DEFAULT_QUALITY,
    cfg_scale: float = DEFAULT_CFG_SCALE,
    seed: Optional[int] = None,
    number_of_images: int = DEFAULT_NUMBER_OF_IMAGES,
    workspace_dir: Optional[str] = None,
) -> ImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with color guidance.

    This function uses Amazon Nova Canvas to generate images based on a text prompt and color palette.
    The generated image will be saved to a file and the path will be returned.

    Args:
        prompt: The text description of the image to generate (1-1024 characters).
        colors: List of up to 10 hexadecimal color values (e.g., "#FF9800").
        bedrock_runtime_client: BedrockRuntimeClient object.
        negative_prompt: Text to define what not to include in the image (1-1024 characters).
        filename: The name of the file to save the image to (without extension).
            If not provided, a random name will be generated.
        width: The width of the generated image (320-4096, divisible by 16).
        height: The height of the generated image (320-4096, divisible by 16).
        quality: The quality of the generated image ("standard" or "premium").
        cfg_scale: How strongly the image adheres to the prompt (1.1-10.0).
        seed: Seed for generation (0-858,993,459). Random if not provided.
        number_of_images: The number of images to generate (1-5).
        workspace_dir: Directory where the images should be saved. If None, uses current directory.

    Returns:
        ImageGenerationResponse: An object containing the paths to the generated images,
        PIL Image objects, and status information.
    """
    logger.debug(
        f"Generating color-guided image with prompt: '{prompt[:30]}...' and {len(colors)} colors"
    )

    try:
        # Validate input parameters using Pydantic
        try:
            logger.debug('Validating parameters and creating color-guided request model')

            # Create image generation config
            config = ImageGenerationConfig(
                width=width,
                height=height,
                quality=Quality.STANDARD if quality == DEFAULT_QUALITY else Quality.PREMIUM,
                cfgScale=cfg_scale,
                seed=seed if seed is not None else random.randint(0, 858993459),
                numberOfImages=number_of_images,
            )

            # Create color-guided params
            # The Nova Canvas API doesn't accept null for negativeText
            if negative_prompt is not None:
                color_params = ColorGuidedGenerationParams(
                    colors=colors,
                    text=prompt,
                    negativeText=negative_prompt,
                )
            else:
                color_params = ColorGuidedGenerationParams(
                    colors=colors,
                    text=prompt,
                )

            # Create the full request
            request_model = ColorGuidedRequest(
                colorGuidedGenerationParams=color_params, imageGenerationConfig=config
            )

            # Convert model to dictionary
            request_model_dict = request_model.to_api_dict()
            logger.info('Color-guided request validation successful')

        except Exception as e:
            logger.error(f'Color-guided parameter validation failed: {str(e)}')
            return ImageGenerationResponse(
                status='error',
                message=f'Validation error: {str(e)}',
                paths=[],
                prompt=prompt,
                negative_prompt=negative_prompt,
                colors=colors,
            )

        try:
            # Invoke the Nova Canvas API
            logger.debug('Sending color-guided request to Nova Canvas API')
            model_response = await invoke_nova_canvas(request_model_dict, bedrock_runtime_client)

            # Extract the image data
            base64_images = model_response['images']
            logger.info(f'Received {len(base64_images)} images from Nova Canvas API')

            # Save the generated images
            result = save_generated_images(
                base64_images,
                filename,
                number_of_images,
                prefix='nova_canvas_color',
                workspace_dir=workspace_dir,
            )

            logger.info(f'Successfully generated {len(result["paths"])} color-guided image(s)')
            return ImageGenerationResponse(
                status='success',
                message=f'Generated {len(result["paths"])} image(s)',
                paths=result['paths'],
                prompt=prompt,
                negative_prompt=negative_prompt,
                colors=colors,
            )
        except Exception as e:
            logger.error(f'Color-guided image generation failed: {str(e)}')
            return ImageGenerationResponse(
                status='error',
                message=str(e),
                paths=[],
                prompt=prompt,
                negative_prompt=negative_prompt,
                colors=colors,
            )

    except Exception as e:
        logger.error(f'Unexpected error in generate_image_with_colors: {str(e)}')
        return ImageGenerationResponse(
            status='error',
            message=str(e),
            paths=[],
            prompt=prompt,
            negative_prompt=negative_prompt,
            colors=colors,
        )
