# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

import boto3
import json
import logging
import os
import sys
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Bedrock client
try:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
    )
    logger.info('Successfully initialized Bedrock client')
except Exception as e:
    logger.error(f'Failed to initialize Bedrock client: {str(e)}')
    bedrock_runtime = None

# Initialize FastAPI app
app = FastAPI(title='Nova Canvas Image Generator API')


# Add exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions in the FastAPI application."""
    logger.error(f'Global exception: {str(exc)}')
    logger.error(traceback.format_exc())
    return JSONResponse(status_code=500, content={'detail': f'An error occurred: {str(exc)}'})


# Define request/response models
class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""

    prompt: str = Field(..., description='Text description of the image to generate')
    negative_prompt: Optional[str] = Field(
        '', description='Text to define what not to include in the image'
    )
    width: int = Field(
        1024, description='Width of the generated image (320-4096, divisible by 16)'
    )
    height: int = Field(
        1024, description='Height of the generated image (320-4096, divisible by 16)'
    )
    quality: str = Field(
        'standard', description="Quality of the generated image ('standard' or 'premium')"
    )
    cfg_scale: float = Field(
        6.5, description='How strongly the image adheres to the prompt (1.1-10.0)'
    )
    seed: Optional[int] = Field(None, description='Seed for generation (0-858,993,459)')
    number_of_images: int = Field(1, description='Number of images to generate (1-5)')
    use_improved_prompt: Optional[bool] = Field(
        False, description='Use improved prompt for image generation'
    )
    colors: Optional[List[str]] = Field(
        None, description='List of hexadecimal color values for color-guided generation'
    )


class ImageGenerationResponse(BaseModel):
    """Response model for image generation."""

    status: str
    message: str
    image_paths: List[str]
    improved_prompt: Optional[str] = ''


# Function to improve prompts with Nova Text Model
async def improve_prompt_with_nova_text(prompt: str) -> str:
    """Improve the image generation prompt using Nova Text Model.

    Args:
        prompt: Original prompt from the user

    Returns:
        str: Improved prompt for image generation
    """
    try:
        if not bedrock_runtime:
            logger.warning('Bedrock client not initialized, returning original prompt')
            return prompt

        # Define system prompt
        system_list = [
            {
                'text': 'You are an expert at improving image generation prompts by adding specific details about composition, lighting, style, and technical aspects.',
                'cachePoint': {'type': 'default'},
            }
        ]

        # Define message
        message_list = [
            {
                'role': 'user',
                'content': [
                    {
                        'text': f"""Enhance prompt with specific details:
                        - Composition: layout, perspective, focal point
                        - Lighting: direction, intensity, shadows
                        - Style: artistic technique, medium, texture
                        - Mood: atmosphere, emotion, time of day
                        - Technical: resolution, aspect ratio

                        Provide concise output (<1000 chars): {prompt}"""
                    }
                ],
            }
        ]

        # Configure inference parameters
        inf_params = {'max_new_tokens': 500}

        # Construct the request body
        request_body = {
            'schemaVersion': 'messages-v1',
            'messages': message_list,
            'system': system_list,
            'inferenceConfig': inf_params,
        }

        # Call Nova Text Model through Bedrock
        response = bedrock_runtime.invoke_model(
            modelId='amazon.nova-micro-v1:0', body=json.dumps(request_body)
        )

        # Parse response
        response_body = json.loads(response['body'].read())
        logger.info(f'Response body: {response_body}')
        improved_prompt = response_body['output']['message']['content'][0]['text'].strip()

        logger.info(f"Original prompt: '{prompt}'")
        logger.info(f"Improved prompt: '{improved_prompt}'")

        return improved_prompt

    except Exception as e:
        logger.error(f'Error improving prompt with Nova Text Model: {str(e)}')
        # Return original prompt if improvement fails
        return prompt


# Connect to the MCP server and generate images
async def generate_image(request: ImageGenerationRequest) -> Dict[str, Any]:
    """Generate an image using the Nova Canvas MCP server.

    Args:
        request: The image generation request parameters

    Returns:
        A dictionary with the generation results
    """
    logger.info(f"Processing image generation request with prompt: '{request.prompt}'")

    try:
        # Check if use_improved_prompt is True
        if request.use_improved_prompt:
            logger.info('Improving prompt with Nova Text Model')
            # Improve prompt using Nova Text Model
            improved_prompt = await improve_prompt_with_nova_text(request.prompt)
            # Update the request with improved prompt
            request.prompt = improved_prompt

        # Initialize MCP client using the awslabs.nova-canvas-mcp-server
        logger.info('Initializing MCP client with awslabs.nova-canvas-mcp-server')
        mcp_client = MultiServerMCPClient(
            {
                'nova_canvas': {
                    'transport': 'stdio',
                    'command': 'uvx',
                    'args': ['awslabs.nova-canvas-mcp-server@latest'],
                    'env': {
                        'AWS_PROFILE': os.getenv('AWS_PROFILE', 'default'),
                        'AWS_REGION': os.getenv('AWS_REGION', 'us-east-1'),
                    },
                }
            }
        )

        # Process with MCP client
        logger.info('Connecting to MCP server')
        async with mcp_client as client:
            # Get tools from the MCP server
            logger.info('Getting tools from MCP server')
            tools = client.get_tools()
            tool_names = [tool.name for tool in tools]
            logger.info(f'Retrieved {len(tools)} tools from MCP server: {tool_names}')

            if not tools:
                logger.warning('No tools were returned from the MCP server')
                return {
                    'status': 'error',
                    'message': 'No tools available from the Nova Canvas server.',
                    'image_paths': [],
                }

            # Determine which tool to use based on whether colors are provided
            logger.info('Determining which tool to use based on request parameters')
            if request.colors:
                # Use color-guided generation
                logger.info(f'Using color-guided generation with {len(request.colors)} colors')
                tool_name = 'generate_image_with_colors'
                tool_args = {
                    'prompt': request.prompt,
                    'colors': request.colors,
                    'negative_prompt': request.negative_prompt,
                    'width': request.width,
                    'height': request.height,
                    'quality': request.quality,
                    'cfg_scale': request.cfg_scale,
                    'seed': request.seed,
                    'number_of_images': request.number_of_images,
                    'workspace_dir': os.getcwd(),
                }
            else:
                # Use standard text-to-image generation
                logger.info('Using standard text-to-image generation')
                tool_name = 'generate_image'
                tool_args = {
                    'prompt': request.prompt,
                    'negative_prompt': request.negative_prompt,
                    'width': request.width,
                    'height': request.height,
                    'quality': request.quality,
                    'cfg_scale': request.cfg_scale,
                    'seed': request.seed,
                    'number_of_images': request.number_of_images,
                    'workspace_dir': os.getcwd(),
                }

            # Find the requested tool
            requested_tool = None
            for tool in tools:
                if tool.name == tool_name:
                    requested_tool = tool
                    break

            if not requested_tool:
                logger.warning(f'Requested tool {tool_name} not found')
                return {
                    'status': 'error',
                    'message': f'Tool {tool_name} not found',
                    'image_paths': [],
                }

            # Execute the tool
            logger.info(f'Executing tool {tool_name}')
            logger.info(f'Tool arguments: {tool_args}')
            tool_result = await requested_tool.ainvoke(tool_args)
            logger.info(f'Tool result: {tool_result}')

            try:
                # If tool_result is a string, try to parse it as JSON
                if isinstance(tool_result, str):
                    tool_result = json.loads(tool_result)

                # Access paths from the dictionary
                if isinstance(tool_result, dict) and 'paths' in tool_result:
                    logger.info(f'Image paths: {tool_result["paths"]}')
                else:
                    logger.error(f'No paths found in tool result: {tool_result}')
            except Exception as e:
                logger.error(f'Error processing tool result: {e}')

            # Extract image paths from the result
            if isinstance(tool_result, dict) and 'paths' in tool_result and tool_result['paths']:
                # Convert file:// URLs to relative paths
                image_paths = []
                for path in tool_result['paths']:
                    if path.startswith('file://'):
                        path = path[7:]  # Remove file:// prefix
                    image_paths.append(path)

                return {
                    'status': 'success',
                    'message': f'Generated {len(image_paths)} image(s)',
                    'image_paths': image_paths,
                    'improved_prompt': request.prompt,
                }
            else:
                logger.error('No image paths found in tool result')
                return {
                    'status': 'error',
                    'message': 'No images were generated',
                    'image_paths': [],
                    'improved_prompt': request.prompt,
                }

    except Exception as e:
        logger.error(f'Error in generate_image: {str(e)}')
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f'Error generating image: {str(e)}')


# Define API endpoints
@app.post('/generate', response_model=ImageGenerationResponse)
async def generate(request: ImageGenerationRequest):
    """Generate an image using Nova Canvas."""
    logger.info(f'Received image generation request with prompt: {request.prompt}')
    try:
        result = await generate_image(request)
        logger.info('Image generation processed successfully')
        return result
    except Exception as e:
        logger.error(f'Error processing image generation: {str(e)}')
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/health')
def health_check():
    """Health check endpoint."""
    return {'status': 'healthy'}


# Run the FastAPI app with uvicorn
if __name__ == '__main__':
    import json
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)
