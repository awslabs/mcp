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
"""Tests for the novacanvas module of the nova-canvas-mcp-server."""

import base64
import json
import os
import pytest
from awslabs.nova_canvas_mcp_server.consts import (
    DEFAULT_CFG_SCALE,
    DEFAULT_HEIGHT,
    DEFAULT_NUMBER_OF_IMAGES,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_QUALITY,
    DEFAULT_WIDTH,
    NOVA_CANVAS_MODEL_ID,
)
from awslabs.nova_canvas_mcp_server.novacanvas import (
    generate_image_with_colors,
    generate_image_with_text,
    invoke_nova_canvas,
    save_generated_images,
)
from unittest.mock import patch


class TestSaveGeneratedImages:
    """Tests for the save_generated_images function."""

    def test_save_images_with_filename(self, temp_workspace_dir, sample_base64_images):
        """Test saving images with a specified filename."""
        result = save_generated_images(
            base64_images=sample_base64_images,
            filename='test_image',
            number_of_images=2,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the paths are returned correctly
        assert len(result['paths']) == 2
        assert all(os.path.exists(path) for path in result['paths'])
        assert all(os.path.basename(path).startswith('test_image_') for path in result['paths'])
        assert all(path.endswith('.png') for path in result['paths'])

        # Check that the images were saved with the correct content
        for i, path in enumerate(result['paths']):
            with open(path, 'rb') as f:
                content = f.read()
                assert content == b'mock_image_data_' + str(i + 1).encode()

    def test_save_images_without_filename(self, temp_workspace_dir, sample_base64_images):
        """Test saving images without a specified filename."""
        result = save_generated_images(
            base64_images=sample_base64_images,
            filename=None,
            number_of_images=2,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the paths are returned correctly
        assert len(result['paths']) == 2
        assert all(os.path.exists(path) for path in result['paths'])
        assert all(os.path.basename(path).startswith('nova_canvas_') for path in result['paths'])
        assert all(path.endswith('.png') for path in result['paths'])

        # Check that the images were saved with the correct content
        for i, path in enumerate(result['paths']):
            with open(path, 'rb') as f:
                content = f.read()
                assert content == b'mock_image_data_' + str(i + 1).encode()

    def test_save_single_image(self, temp_workspace_dir):
        """Test saving a single image."""
        base64_image = base64.b64encode(b'mock_single_image_data').decode('utf-8')

        result = save_generated_images(
            base64_images=[base64_image],
            filename='single_image',
            number_of_images=1,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the path is returned correctly
        assert len(result['paths']) == 1
        assert os.path.exists(result['paths'][0])
        assert os.path.basename(result['paths'][0]) == 'single_image.png'

        # Check that the image was saved with the correct content
        with open(result['paths'][0], 'rb') as f:
            content = f.read()
            assert content == b'mock_single_image_data'

    def test_save_images_creates_output_dir(self, temp_workspace_dir, sample_base64_images):
        """Test that the output directory is created if it doesn't exist."""
        # Create a nested directory path that doesn't exist
        nested_dir = os.path.join(temp_workspace_dir, 'nested', 'dir')

        # Use only one base64 image for this test
        result = save_generated_images(
            base64_images=[sample_base64_images[0]],
            filename='test_image',
            number_of_images=1,
            workspace_dir=nested_dir,
        )

        # Check that the output directory was created
        output_dir = os.path.join(nested_dir, DEFAULT_OUTPUT_DIR)
        assert os.path.exists(output_dir)

        # Check that the image was saved in the correct location
        assert len(result['paths']) == 1
        assert os.path.exists(result['paths'][0])
        assert os.path.dirname(result['paths'][0]) == os.path.abspath(output_dir)


class TestInvokeNovaCanvas:
    """Tests for the invoke_nova_canvas function."""

    @pytest.mark.asyncio
    async def test_successful_invocation(
        self, mock_bedrock_runtime_client, mock_successful_response
    ):
        """Test successful invocation of the Nova Canvas API."""
        request_dict = {
            'taskType': 'TEXT_IMAGE',
            'textToImageParams': {'text': 'A beautiful mountain landscape'},
            'imageGenerationConfig': {
                'width': 1024,
                'height': 1024,
                'quality': 'standard',
                'cfgScale': 6.5,
                'seed': 12345,
                'numberOfImages': 1,
            },
        }

        result = await invoke_nova_canvas(request_dict, mock_bedrock_runtime_client)

        # Check that the API was called with the correct parameters
        mock_bedrock_runtime_client.invoke_model.assert_called_once_with(
            modelId=NOVA_CANVAS_MODEL_ID, body=json.dumps(request_dict)
        )

        # Check that the result is correct
        assert 'images' in result
        assert len(result['images']) == 2
        assert all(isinstance(img, str) for img in result['images'])

    @pytest.mark.asyncio
    async def test_api_error(self, mock_bedrock_runtime_client):
        """Test handling of API errors."""
        # Set up the mock to raise an exception
        mock_bedrock_runtime_client.invoke_model.side_effect = Exception('API error')

        request_dict = {
            'taskType': 'TEXT_IMAGE',
            'textToImageParams': {'text': 'A beautiful mountain landscape'},
        }

        # Check that the exception is propagated
        with pytest.raises(Exception, match='API error'):
            await invoke_nova_canvas(request_dict, mock_bedrock_runtime_client)


class TestGenerateImageWithText:
    """Tests for the generate_image_with_text function."""

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.save_generated_images')
    async def test_successful_generation(
        self,
        mock_save_images,
        mock_invoke_nova_canvas,
        mock_bedrock_runtime_client,
        sample_text_prompt,
        temp_workspace_dir,
    ):
        """Test successful image generation with text."""
        # Set up mocks
        mock_invoke_nova_canvas.return_value = {'images': ['base64_image_1', 'base64_image_2']}
        mock_save_images.return_value = {'paths': ['/path/to/image1.png', '/path/to/image2.png']}

        # Call the function
        result = await generate_image_with_text(
            prompt=sample_text_prompt,
            bedrock_runtime_client=mock_bedrock_runtime_client,
            filename='test_image',
            width=512,
            height=768,
            quality='premium',
            cfg_scale=8.0,
            seed=12345,
            number_of_images=2,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.message == 'Generated 2 image(s)'
        assert result.paths == ['/path/to/image1.png', '/path/to/image2.png']
        assert result.prompt == sample_text_prompt
        assert result.negative_prompt is None

        # Check that invoke_nova_canvas was called with the correct parameters
        mock_invoke_nova_canvas.assert_called_once()
        call_args = mock_invoke_nova_canvas.call_args[0][0]
        assert call_args['taskType'] == 'TEXT_IMAGE'
        assert call_args['textToImageParams']['text'] == sample_text_prompt
        assert call_args['imageGenerationConfig']['width'] == 512
        assert call_args['imageGenerationConfig']['height'] == 768
        assert call_args['imageGenerationConfig']['quality'] == 'premium'
        assert call_args['imageGenerationConfig']['cfgScale'] == 8.0
        assert call_args['imageGenerationConfig']['seed'] == 12345
        assert call_args['imageGenerationConfig']['numberOfImages'] == 2

        # Check that save_generated_images was called with the correct parameters
        mock_save_images.assert_called_once_with(
            ['base64_image_1', 'base64_image_2'],
            'test_image',
            2,
            prefix='nova_canvas',
            workspace_dir=temp_workspace_dir,
        )

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.save_generated_images')
    async def test_generation_with_negative_prompt(
        self,
        mock_save_images,
        mock_invoke_nova_canvas,
        mock_bedrock_runtime_client,
        sample_text_prompt,
        sample_negative_prompt,
        temp_workspace_dir,
    ):
        """Test image generation with a negative prompt."""
        # Set up mocks
        mock_invoke_nova_canvas.return_value = {'images': ['base64_image_1']}
        mock_save_images.return_value = {'paths': ['/path/to/image1.png']}

        # Call the function
        result = await generate_image_with_text(
            prompt=sample_text_prompt,
            bedrock_runtime_client=mock_bedrock_runtime_client,
            negative_prompt=sample_negative_prompt,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['/path/to/image1.png']
        assert result.prompt == sample_text_prompt
        assert result.negative_prompt == sample_negative_prompt

        # Check that invoke_nova_canvas was called with the correct parameters
        mock_invoke_nova_canvas.assert_called_once()
        call_args = mock_invoke_nova_canvas.call_args[0][0]
        assert call_args['textToImageParams']['text'] == sample_text_prompt
        assert call_args['textToImageParams']['negativeText'] == sample_negative_prompt

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    async def test_validation_error(self, mock_invoke_nova_canvas, mock_bedrock_runtime_client):
        """Test handling of validation errors."""
        # Call the function with invalid parameters
        result = await generate_image_with_text(
            prompt='',  # Empty prompt is invalid
            bedrock_runtime_client=mock_bedrock_runtime_client,
        )

        # Check that the result indicates an error
        assert result.status == 'error'
        assert 'Validation error' in result.message
        assert result.paths == []
        assert result.prompt == ''
        assert result.negative_prompt is None

        # Check that invoke_nova_canvas was not called
        mock_invoke_nova_canvas.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    async def test_api_error(
        self, mock_invoke_nova_canvas, mock_bedrock_runtime_client, sample_text_prompt
    ):
        """Test handling of API errors."""
        # Set up the mock to raise an exception
        mock_invoke_nova_canvas.side_effect = Exception('API error')

        # Call the function
        result = await generate_image_with_text(
            prompt=sample_text_prompt, bedrock_runtime_client=mock_bedrock_runtime_client
        )

        # Check that the result indicates an error
        assert result.status == 'error'
        assert result.message == 'API error'
        assert result.paths == []
        assert result.prompt == sample_text_prompt
        assert result.negative_prompt is None

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.save_generated_images')
    async def test_default_parameters(
        self,
        mock_save_images,
        mock_invoke_nova_canvas,
        mock_bedrock_runtime_client,
        sample_text_prompt,
    ):
        """Test image generation with default parameters."""
        # Set up mocks
        mock_invoke_nova_canvas.return_value = {'images': ['base64_image_1']}
        mock_save_images.return_value = {'paths': ['/path/to/image1.png']}

        # Call the function with minimal parameters
        result = await generate_image_with_text(
            prompt=sample_text_prompt, bedrock_runtime_client=mock_bedrock_runtime_client
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['/path/to/image1.png']

        # Check that invoke_nova_canvas was called with default parameters
        mock_invoke_nova_canvas.assert_called_once()
        call_args = mock_invoke_nova_canvas.call_args[0][0]
        assert call_args['imageGenerationConfig']['width'] == DEFAULT_WIDTH
        assert call_args['imageGenerationConfig']['height'] == DEFAULT_HEIGHT
        assert call_args['imageGenerationConfig']['quality'] == DEFAULT_QUALITY
        assert call_args['imageGenerationConfig']['cfgScale'] == DEFAULT_CFG_SCALE
        assert call_args['imageGenerationConfig']['numberOfImages'] == DEFAULT_NUMBER_OF_IMAGES


class TestGenerateImageWithColors:
    """Tests for the generate_image_with_colors function."""

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.save_generated_images')
    async def test_successful_generation(
        self,
        mock_save_images,
        mock_invoke_nova_canvas,
        mock_bedrock_runtime_client,
        sample_text_prompt,
        sample_colors,
        temp_workspace_dir,
    ):
        """Test successful image generation with colors."""
        # Set up mocks
        mock_invoke_nova_canvas.return_value = {'images': ['base64_image_1', 'base64_image_2']}
        mock_save_images.return_value = {'paths': ['/path/to/image1.png', '/path/to/image2.png']}

        # Call the function
        result = await generate_image_with_colors(
            prompt=sample_text_prompt,
            colors=sample_colors,
            bedrock_runtime_client=mock_bedrock_runtime_client,
            filename='test_image',
            width=512,
            height=768,
            quality='premium',
            cfg_scale=8.0,
            seed=12345,
            number_of_images=2,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.message == 'Generated 2 image(s)'
        assert result.paths == ['/path/to/image1.png', '/path/to/image2.png']
        assert result.prompt == sample_text_prompt
        assert result.negative_prompt is None
        assert result.colors == sample_colors

        # Check that invoke_nova_canvas was called with the correct parameters
        mock_invoke_nova_canvas.assert_called_once()
        call_args = mock_invoke_nova_canvas.call_args[0][0]
        assert call_args['taskType'] == 'COLOR_GUIDED_GENERATION'
        assert call_args['colorGuidedGenerationParams']['text'] == sample_text_prompt
        assert call_args['colorGuidedGenerationParams']['colors'] == sample_colors
        assert call_args['imageGenerationConfig']['width'] == 512
        assert call_args['imageGenerationConfig']['height'] == 768
        assert call_args['imageGenerationConfig']['quality'] == 'premium'
        assert call_args['imageGenerationConfig']['cfgScale'] == 8.0
        assert call_args['imageGenerationConfig']['seed'] == 12345
        assert call_args['imageGenerationConfig']['numberOfImages'] == 2

        # Check that save_generated_images was called with the correct parameters
        mock_save_images.assert_called_once_with(
            ['base64_image_1', 'base64_image_2'],
            'test_image',
            2,
            prefix='nova_canvas_color',
            workspace_dir=temp_workspace_dir,
        )

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.save_generated_images')
    async def test_generation_with_negative_prompt(
        self,
        mock_save_images,
        mock_invoke_nova_canvas,
        mock_bedrock_runtime_client,
        sample_text_prompt,
        sample_colors,
        sample_negative_prompt,
        temp_workspace_dir,
    ):
        """Test image generation with colors and a negative prompt."""
        # Set up mocks
        mock_invoke_nova_canvas.return_value = {'images': ['base64_image_1']}
        mock_save_images.return_value = {'paths': ['/path/to/image1.png']}

        # Call the function
        result = await generate_image_with_colors(
            prompt=sample_text_prompt,
            colors=sample_colors,
            bedrock_runtime_client=mock_bedrock_runtime_client,
            negative_prompt=sample_negative_prompt,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['/path/to/image1.png']
        assert result.prompt == sample_text_prompt
        assert result.negative_prompt == sample_negative_prompt
        assert result.colors == sample_colors

        # Check that invoke_nova_canvas was called with the correct parameters
        mock_invoke_nova_canvas.assert_called_once()
        call_args = mock_invoke_nova_canvas.call_args[0][0]
        assert call_args['colorGuidedGenerationParams']['text'] == sample_text_prompt
        assert call_args['colorGuidedGenerationParams']['colors'] == sample_colors
        assert call_args['colorGuidedGenerationParams']['negativeText'] == sample_negative_prompt

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    async def test_validation_error(
        self, mock_invoke_nova_canvas, mock_bedrock_runtime_client, sample_text_prompt
    ):
        """Test handling of validation errors."""
        # Call the function with invalid parameters
        result = await generate_image_with_colors(
            prompt=sample_text_prompt,
            colors=['invalid_color'],  # Invalid color format
            bedrock_runtime_client=mock_bedrock_runtime_client,
        )

        # Check that the result indicates an error
        assert result.status == 'error'
        assert 'Validation error' in result.message
        assert result.paths == []
        assert result.prompt == sample_text_prompt
        assert result.colors == ['invalid_color']

        # Check that invoke_nova_canvas was not called
        mock_invoke_nova_canvas.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    async def test_api_error(
        self,
        mock_invoke_nova_canvas,
        mock_bedrock_runtime_client,
        sample_text_prompt,
        sample_colors,
    ):
        """Test handling of API errors."""
        # Set up the mock to raise an exception
        mock_invoke_nova_canvas.side_effect = Exception('API error')

        # Call the function
        result = await generate_image_with_colors(
            prompt=sample_text_prompt,
            colors=sample_colors,
            bedrock_runtime_client=mock_bedrock_runtime_client,
        )

        # Check that the result indicates an error
        assert result.status == 'error'
        assert result.message == 'API error'
        assert result.paths == []
        assert result.prompt == sample_text_prompt
        assert result.colors == sample_colors

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.invoke_nova_canvas')
    @patch('awslabs.nova_canvas_mcp_server.novacanvas.save_generated_images')
    async def test_default_parameters(
        self,
        mock_save_images,
        mock_invoke_nova_canvas,
        mock_bedrock_runtime_client,
        sample_text_prompt,
        sample_colors,
    ):
        """Test image generation with default parameters."""
        # Set up mocks
        mock_invoke_nova_canvas.return_value = {'images': ['base64_image_1']}
        mock_save_images.return_value = {'paths': ['/path/to/image1.png']}

        # Call the function with minimal parameters
        result = await generate_image_with_colors(
            prompt=sample_text_prompt,
            colors=sample_colors,
            bedrock_runtime_client=mock_bedrock_runtime_client,
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['/path/to/image1.png']

        # Check that invoke_nova_canvas was called with default parameters
        mock_invoke_nova_canvas.assert_called_once()
        call_args = mock_invoke_nova_canvas.call_args[0][0]
        assert call_args['imageGenerationConfig']['width'] == DEFAULT_WIDTH
        assert call_args['imageGenerationConfig']['height'] == DEFAULT_HEIGHT
        assert call_args['imageGenerationConfig']['quality'] == DEFAULT_QUALITY
        assert call_args['imageGenerationConfig']['cfgScale'] == DEFAULT_CFG_SCALE
        assert call_args['imageGenerationConfig']['numberOfImages'] == DEFAULT_NUMBER_OF_IMAGES
