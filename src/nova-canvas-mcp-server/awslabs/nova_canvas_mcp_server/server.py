"""Nova Canvas MCP Server implementation."""

import argparse
import boto3
import os
import sys
from awslabs.nova_canvas_mcp_server.consts import (
    DEFAULT_CFG_SCALE,
    DEFAULT_HEIGHT,
    DEFAULT_NUMBER_OF_IMAGES,
    DEFAULT_QUALITY,
    DEFAULT_WIDTH,
    PROMPT_INSTRUCTIONS,
)
from awslabs.nova_canvas_mcp_server.models import McpImageGenerationResponse
from awslabs.nova_canvas_mcp_server.novacanvas import (
    generate_image_with_colors,
    generate_image_with_text,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import TYPE_CHECKING, List, Optional


# Logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Bedrock Runtime Client typing
if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
else:
    BedrockRuntimeClient = object


# Bedrock Runtime Client
bedrock_runtime_client: BedrockRuntimeClient
aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')

try:
    if aws_profile := os.environ.get('AWS_PROFILE'):
        bedrock_runtime_client = boto3.Session(
            profile_name=aws_profile, region_name=aws_region
        ).client('bedrock-runtime')
    else:
        bedrock_runtime_client = boto3.Session(region_name=aws_region).client('bedrock-runtime')
except Exception as e:
    logger.error(f'Error creating bedrock runtime client: {str(e)}')
    raise


# Create the MCP server Pwith detailed instructions
mcp = FastMCP(
    'awslabs-nova-canvas-mcp-server',
    instructions=f"""
# Amazon Nova Canvas Image Generation

This MCP server provides tools for generating images using Amazon Nova Canvas through Amazon Bedrock.

## Available Tools

### generate_image
Generate an image from a text prompt using Amazon Nova Canvas.

### generate_image_with_colors
Generate an image from a text prompt and color palette using Amazon Nova Canvas.

## Prompt Best Practices

{PROMPT_INSTRUCTIONS}
""",
    dependencies=[
        'pydantic',
        'boto3',
    ],
)


@mcp.tool(name='generate_image')
async def mcp_generate_image(
    ctx: Context,
    prompt: str = Field(
        description='The text description of the image to generate (1-1024 characters)'
    ),
    negative_prompt: Optional[str] = Field(
        default=None,
        description='Text to define what not to include in the image (1-1024 characters)',
    ),
    filename: Optional[str] = Field(
        default=None, description='The name of the file to save the image to (without extension)'
    ),
    width: int = Field(
        default=DEFAULT_WIDTH,
        description='The width of the generated image (320-4096, divisible by 16)',
    ),
    height: int = Field(
        default=DEFAULT_HEIGHT,
        description='The height of the generated image (320-4096, divisible by 16)',
    ),
    quality: str = Field(
        default=DEFAULT_QUALITY,
        description='The quality of the generated image ("standard" or "premium")',
    ),
    cfg_scale: float = Field(
        default=DEFAULT_CFG_SCALE,
        description='How strongly the image adheres to the prompt (1.1-10.0)',
    ),
    seed: Optional[int] = Field(default=None, description='Seed for generation (0-858,993,459)'),
    number_of_images: int = Field(
        default=DEFAULT_NUMBER_OF_IMAGES, description='The number of images to generate (1-5)'
    ),
    workspace_dir: Optional[str] = Field(
        default=None,
        description="""The current workspace directory where the image should be saved.
        CRITICAL: Assistant must always provide the current IDE workspace directory parameter to save images to the user's current project.""",
    ),
) -> McpImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with text prompt.

    This tool uses Amazon Nova Canvas to generate images based on a text prompt.
    The generated image will be saved to a file and the path will be returned.

    IMPORTANT FOR ASSISTANT: Always send the current workspace directory when calling this tool!
    The workspace_dir parameter should be set to the directory where the user is currently working
    so that images are saved to a location accessible to the user.

    ## Prompt Best Practices

    An effective prompt often includes short descriptions of:
    1. The subject
    2. The environment
    3. (optional) The position or pose of the subject
    4. (optional) Lighting description
    5. (optional) Camera position/framing
    6. (optional) The visual style or medium ("photo", "illustration", "painting", etc.)

    Do not use negation words like "no", "not", "without" in your prompt. Instead, use the
    negative_prompt parameter to specify what you don't want in the image.

    You should always include "people, anatomy, hands, low quality, low resolution, low detail" in your negative_prompt

    ## Example Prompts

    - "realistic editorial photo of female teacher standing at a blackboard with a warm smile"
    - "whimsical and ethereal soft-shaded story illustration: A woman in a large hat stands at the ship's railing looking out across the ocean"
    - "drone view of a dark river winding through a stark Iceland landscape, cinematic quality"

    Returns:
        McpImageGenerationResponse: A response containing the generated image paths.
    """
    logger.debug(
        f"MCP tool generate_image called with prompt: '{prompt[:30]}...', dims: {width}x{height}"
    )

    try:
        logger.info(
            f'Generating image with text prompt, quality: {quality}, cfg_scale: {cfg_scale}'
        )
        response = await generate_image_with_text(
            prompt=prompt,
            bedrock_runtime_client=bedrock_runtime_client,
            negative_prompt=negative_prompt,
            filename=filename,
            width=width,
            height=height,
            quality=quality,
            cfg_scale=cfg_scale,
            seed=seed,
            number_of_images=number_of_images,
            workspace_dir=workspace_dir,
        )

        if response.status == 'success':
            # return response.paths
            return McpImageGenerationResponse(
                status='success',
                paths=[f'file://{path}' for path in response.paths],
            )
        else:
            logger.error(f'Image generation returned error status: {response.message}')
            await ctx.error(f'Failed to generate image: {response.message}')  # type: ignore
            # Return empty image or raise exception based on requirements
            raise Exception(f'Failed to generate image: {response.message}')
    except Exception as e:
        logger.error(f'Error in mcp_generate_image: {str(e)}')
        await ctx.error(f'Error generating image: {str(e)}')  # type: ignore
        raise


@mcp.tool(name='generate_image_with_colors')
async def mcp_generate_image_with_colors(
    ctx: Context,
    prompt: str = Field(
        description='The text description of the image to generate (1-1024 characters)'
    ),
    colors: List[str] = Field(
        description='List of up to 10 hexadecimal color values (e.g., "#FF9800")'
    ),
    negative_prompt: Optional[str] = Field(
        default=None,
        description='Text to define what not to include in the image (1-1024 characters)',
    ),
    filename: Optional[str] = Field(
        default=None, description='The name of the file to save the image to (without extension)'
    ),
    width: int = Field(
        default=1024, description='The width of the generated image (320-4096, divisible by 16)'
    ),
    height: int = Field(
        default=1024, description='The height of the generated image (320-4096, divisible by 16)'
    ),
    quality: str = Field(
        default='standard',
        description='The quality of the generated image ("standard" or "premium")',
    ),
    cfg_scale: float = Field(
        default=6.5, description='How strongly the image adheres to the prompt (1.1-10.0)'
    ),
    seed: Optional[int] = Field(default=None, description='Seed for generation (0-858,993,459)'),
    number_of_images: int = Field(default=1, description='The number of images to generate (1-5)'),
    workspace_dir: Optional[str] = Field(
        default=None,
        description="The current workspace directory where the image should be saved. CRITICAL: Assistant must always provide this parameter to save images to the user's current project.",
    ),
) -> McpImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with color guidance.

    This tool uses Amazon Nova Canvas to generate images based on a text prompt and color palette.
    The generated image will be saved to a file and the path will be returned.

    IMPORTANT FOR Assistant: Always send the current workspace directory when calling this tool!
    The workspace_dir parameter should be set to the directory where the user is currently working
    so that images are saved to a location accessible to the user.

    ## Prompt Best Practices

    An effective prompt often includes short descriptions of:
    1. The subject
    2. The environment
    3. (optional) The position or pose of the subject
    4. (optional) Lighting description
    5. (optional) Camera position/framing
    6. (optional) The visual style or medium ("photo", "illustration", "painting", etc.)

    Do not use negation words like "no", "not", "without" in your prompt. Instead, use the
    negative_prompt parameter to specify what you don't want in the image.

    ## Example Colors

    - ["#FF5733", "#33FF57", "#3357FF"] - A vibrant color scheme with red, green, and blue
    - ["#000000", "#FFFFFF"] - A high contrast black and white scheme
    - ["#FFD700", "#B87333"] - A gold and bronze color scheme

    Returns:
        McpImageGenerationResponse: A response containing the generated image paths.
    """
    logger.debug(
        f"MCP tool generate_image_with_colors called with prompt: '{prompt[:30]}...', {len(colors)} colors"
    )

    try:
        color_hex_list = ', '.join(colors[:3]) + (', ...' if len(colors) > 3 else '')
        logger.info(
            f'Generating color-guided image with colors: [{color_hex_list}], quality: {quality}'
        )

        response = await generate_image_with_colors(
            prompt=prompt,
            colors=colors,
            bedrock_runtime_client=bedrock_runtime_client,
            negative_prompt=negative_prompt,
            filename=filename,
            width=width,
            height=height,
            quality=quality,
            cfg_scale=cfg_scale,
            seed=seed,
            number_of_images=number_of_images,
            workspace_dir=workspace_dir,
        )

        if response.status == 'success':
            return McpImageGenerationResponse(
                status='success',
                paths=[f'file://{path}' for path in response.paths],
            )
        else:
            logger.error(
                f'Color-guided image generation returned error status: {response.message}'
            )
            await ctx.error(f'Failed to generate color-guided image: {response.message}')
            raise Exception(f'Failed to generate color-guided image: {response.message}')
    except Exception as e:
        logger.error(f'Error in mcp_generate_image_with_colors: {str(e)}')
        await ctx.error(f'Error generating color-guided image: {str(e)}')
        raise


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting nova-canvas-mcp-server MCP server')

    parser = argparse.ArgumentParser(
        description='MCP server for generating images using Amazon Nova Canvas'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()
    logger.debug(f'Parsed arguments: sse={args.sse}, port={args.port}')

    # Run server with appropriate transport
    if args.sse:
        logger.info(f'Using SSE transport on port {args.port}')
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        logger.info('Using standard stdio transport')
        mcp.run()


if __name__ == '__main__':
    main()
