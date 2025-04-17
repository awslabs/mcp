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
"""Tests for the server module of the nova-canvas-mcp-server."""

import pytest
from unittest.mock import MagicMock, patch
from awslabs.nova_canvas_mcp_server.server import (
    mcp_generate_image,
    mcp_generate_image_with_colors,
)


class TestMcpGenerateImage:
    """Tests for the mcp_generate_image function."""

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_text')
    async def test_generate_image_success(
        self, mock_generate_image, mock_context, sample_text_prompt, temp_workspace_dir
    ):
        """Test successful image generation."""
        # Set up the mock
        mock_generate_image.return_value = MagicMock(
            status='success',
            paths=['/path/to/image1.png', '/path/to/image2.png'],
            message='Generated 2 image(s)',
        )

        # Call the function
        result = await mcp_generate_image(
            ctx=mock_context,
            prompt=sample_text_prompt,
            negative_prompt='people, clouds',
            filename='test_image',
            width=512,
            height=768,
            quality='premium',
            cfg_scale=8.0,
            seed=12345,
            number_of_images=2,
            workspace_dir=temp_workspace_dir,
        )

        # Check that generate_image_with_text was called with the correct parameters
        mock_generate_image.assert_called_once()
        call_args = mock_generate_image.call_args[1]
        assert call_args['prompt'] == sample_text_prompt
        assert call_args['negative_prompt'] == 'people, clouds'
        assert call_args['filename'] == 'test_image'
        assert call_args['width'] == 512
        assert call_args['height'] == 768
        assert call_args['quality'] == 'premium'
        assert call_args['cfg_scale'] == 8.0
        assert call_args['seed'] == 12345
        assert call_args['number_of_images'] == 2
        assert call_args['workspace_dir'] == temp_workspace_dir
        # We can't directly compare the bedrock_runtime_client object
        assert 'bedrock_runtime_client' in call_args

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['file:///path/to/image1.png', 'file:///path/to/image2.png']

        # Check that ctx.error was not called
        mock_context.error.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_text')
    async def test_generate_image_error(
        self, mock_generate_image, mock_context, sample_text_prompt
    ):
        """Test error handling in image generation."""
        # Set up the mock to return an error
        mock_generate_image.return_value = MagicMock(
            status='error', message='Failed to generate image: API error', paths=[]
        )

        # Call the function and check that it raises an exception
        with pytest.raises(Exception, match='Failed to generate image: API error'):
            await mcp_generate_image(ctx=mock_context, prompt=sample_text_prompt)

        # Check that ctx.error was called with the expected error message
        assert mock_context.error.call_count == 2
        assert 'Failed to generate image: API error' in str(mock_context.error.call_args_list)

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_text')
    async def test_generate_image_with_defaults(
        self, mock_generate_image, mock_context, sample_text_prompt
    ):
        """Test image generation with default parameters."""
        # Set up the mock
        mock_generate_image.return_value = MagicMock(
            status='success', paths=['/path/to/image.png'], message='Generated 1 image(s)'
        )

        # Call the function with minimal parameters
        result = await mcp_generate_image(ctx=mock_context, prompt=sample_text_prompt)

        # Check that generate_image_with_text was called with the correct parameters
        mock_generate_image.assert_called_once()
        call_args = mock_generate_image.call_args[1]
        assert call_args['prompt'] == sample_text_prompt
        assert 'negative_prompt' in call_args
        assert hasattr(call_args['filename'], 'default') and call_args['filename'].default is None
        assert (
            hasattr(call_args['workspace_dir'], 'default')
            and call_args['workspace_dir'].default is None
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['file:///path/to/image.png']

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_text')
    async def test_generate_image_exception(
        self, mock_generate_image, mock_context, sample_text_prompt
    ):
        """Test handling of exceptions during image generation."""
        # Set up the mock to raise an exception
        mock_generate_image.side_effect = Exception('Unexpected error')

        # Call the function and check that it raises an exception
        with pytest.raises(Exception, match='Unexpected error'):
            await mcp_generate_image(ctx=mock_context, prompt=sample_text_prompt)

        # Check that ctx.error was called with the expected error message
        assert mock_context.error.call_count == 1
        assert 'Error generating image: Unexpected error' in str(mock_context.error.call_args_list)


class TestMcpGenerateImageWithColors:
    """Tests for the mcp_generate_image_with_colors function."""

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_colors')
    async def test_generate_image_with_colors_success(
        self,
        mock_generate_image,
        mock_context,
        sample_text_prompt,
        sample_colors,
        temp_workspace_dir,
    ):
        """Test successful image generation with colors."""
        # Set up the mock
        mock_generate_image.return_value = MagicMock(
            status='success',
            paths=['/path/to/image1.png', '/path/to/image2.png'],
            message='Generated 2 image(s)',
        )

        # Call the function
        result = await mcp_generate_image_with_colors(
            ctx=mock_context,
            prompt=sample_text_prompt,
            colors=sample_colors,
            negative_prompt='people, clouds',
            filename='test_image',
            width=512,
            height=768,
            quality='premium',
            cfg_scale=8.0,
            seed=12345,
            number_of_images=2,
            workspace_dir=temp_workspace_dir,
        )

        # Check that generate_image_with_colors was called with the correct parameters
        mock_generate_image.assert_called_once()
        call_args = mock_generate_image.call_args[1]
        assert call_args['prompt'] == sample_text_prompt
        assert call_args['colors'] == sample_colors
        assert call_args['negative_prompt'] == 'people, clouds'
        assert call_args['filename'] == 'test_image'
        assert call_args['width'] == 512
        assert call_args['height'] == 768
        assert call_args['quality'] == 'premium'
        assert call_args['cfg_scale'] == 8.0
        assert call_args['seed'] == 12345
        assert call_args['number_of_images'] == 2
        assert call_args['workspace_dir'] == temp_workspace_dir
        # We can't directly compare the bedrock_runtime_client object
        assert 'bedrock_runtime_client' in call_args

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['file:///path/to/image1.png', 'file:///path/to/image2.png']

        # Check that ctx.error was not called
        mock_context.error.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_colors')
    async def test_generate_image_with_colors_error(
        self, mock_generate_image, mock_context, sample_text_prompt, sample_colors
    ):
        """Test error handling in image generation with colors."""
        # Set up the mock to return an error
        mock_generate_image.return_value = MagicMock(
            status='error', message='Failed to generate color-guided image: API error', paths=[]
        )

        # Call the function and check that it raises an exception
        with pytest.raises(Exception, match='Failed to generate color-guided image: API error'):
            await mcp_generate_image_with_colors(
                ctx=mock_context, prompt=sample_text_prompt, colors=sample_colors
            )

        # Check that ctx.error was called with the expected error message
        assert mock_context.error.call_count == 2
        assert 'Failed to generate color-guided image: API error' in str(
            mock_context.error.call_args_list
        )

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_colors')
    async def test_generate_image_with_colors_defaults(
        self, mock_generate_image, mock_context, sample_text_prompt, sample_colors
    ):
        """Test image generation with colors using default parameters."""
        # Set up the mock
        mock_generate_image.return_value = MagicMock(
            status='success', paths=['/path/to/image.png'], message='Generated 1 image(s)'
        )

        # Call the function with minimal parameters
        result = await mcp_generate_image_with_colors(
            ctx=mock_context, prompt=sample_text_prompt, colors=sample_colors
        )

        # Check that generate_image_with_colors was called with the correct parameters
        mock_generate_image.assert_called_once()
        call_args = mock_generate_image.call_args[1]
        assert call_args['prompt'] == sample_text_prompt
        assert call_args['colors'] == sample_colors
        assert 'negative_prompt' in call_args
        assert hasattr(call_args['filename'], 'default') and call_args['filename'].default is None
        assert (
            hasattr(call_args['workspace_dir'], 'default')
            and call_args['workspace_dir'].default is None
        )

        # Check that the result is correct
        assert result.status == 'success'
        assert result.paths == ['file:///path/to/image.png']

    @pytest.mark.asyncio
    @patch('awslabs.nova_canvas_mcp_server.server.generate_image_with_colors')
    async def test_generate_image_with_colors_exception(
        self, mock_generate_image, mock_context, sample_text_prompt, sample_colors
    ):
        """Test handling of exceptions during image generation with colors."""
        # Set up the mock to raise an exception
        mock_generate_image.side_effect = Exception('Unexpected error')

        # Call the function and check that it raises an exception
        with pytest.raises(Exception, match='Unexpected error'):
            await mcp_generate_image_with_colors(
                ctx=mock_context, prompt=sample_text_prompt, colors=sample_colors
            )

        # Check that ctx.error was called with the expected error message
        assert mock_context.error.call_count == 1
        assert 'Error generating color-guided image: Unexpected error' in str(
            mock_context.error.call_args_list
        )


class TestServerIntegration:
    """Integration tests for the server module."""

    def test_server_tool_registration(self):
        """Test that the server tools are registered correctly."""
        # Check that the tools are registered
        assert hasattr(mcp_generate_image, '__name__')
        assert hasattr(mcp_generate_image_with_colors, '__name__')

        # Check that the functions have the correct docstrings
        assert (
            mcp_generate_image.__doc__ is not None
            and 'Generate an image using Amazon Nova Canvas with text prompt'
            in mcp_generate_image.__doc__
        )
        assert (
            mcp_generate_image_with_colors.__doc__ is not None
            and 'Generate an image using Amazon Nova Canvas with color guidance'
            in mcp_generate_image_with_colors.__doc__
        )
