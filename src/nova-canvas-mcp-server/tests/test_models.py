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
"""Tests for the models module of the nova-canvas-mcp-server."""

import pytest
from awslabs.nova_canvas_mcp_server.models import (
    ColorGuidedGenerationParams,
    ColorGuidedRequest,
    ImageGenerationConfig,
    ImageGenerationResponse,
    McpImageGenerationResponse,
    Quality,
    TaskType,
    TextImageRequest,
    TextToImageParams,
)
from pydantic import ValidationError


class TestEnums:
    """Tests for the enum classes."""

    def test_quality_enum(self):
        """Test that Quality enum has the expected values."""
        assert Quality.STANDARD == 'standard'
        assert Quality.PREMIUM == 'premium'

    def test_task_type_enum(self):
        """Test that TaskType enum has the expected values."""
        assert TaskType.TEXT_IMAGE == 'TEXT_IMAGE'
        assert TaskType.COLOR_GUIDED_GENERATION == 'COLOR_GUIDED_GENERATION'


class TestImageGenerationConfig:
    """Tests for the ImageGenerationConfig model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ImageGenerationConfig()
        assert config.width == 1024
        assert config.height == 1024
        assert config.quality == Quality.STANDARD
        assert config.cfgScale == 6.5
        assert 0 <= config.seed <= 858993459
        assert config.numberOfImages == 1

    def test_custom_values(self):
        """Test that custom values are accepted."""
        config = ImageGenerationConfig(
            width=512,
            height=768,
            quality=Quality.PREMIUM,
            cfgScale=8.0,
            seed=12345,
            numberOfImages=3,
        )
        assert config.width == 512
        assert config.height == 768
        assert config.quality == Quality.PREMIUM
        assert config.cfgScale == 8.0
        assert config.seed == 12345
        assert config.numberOfImages == 3

    def test_width_height_divisible_by_16(self):
        """Test that width and height must be divisible by 16."""
        # Valid values
        ImageGenerationConfig(width=512, height=768)

        # Invalid width
        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=513, height=768)

        # Invalid height
        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=512, height=769)

    def test_width_height_bounds(self):
        """Test that width and height must be within bounds."""
        # Valid values
        ImageGenerationConfig(width=320, height=320)
        ImageGenerationConfig(width=2000, height=2000)  # Just under the 4,194,304 pixel limit

        # Below minimum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=304, height=320)

        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=320, height=304)

        # Above maximum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=4112, height=320)

        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=320, height=4112)

    def test_cfg_scale_bounds(self):
        """Test that cfgScale must be within bounds."""
        # Valid values
        ImageGenerationConfig(cfgScale=1.1)
        ImageGenerationConfig(cfgScale=10.0)

        # Below minimum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(cfgScale=1.0)

        # Above maximum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(cfgScale=10.1)

    def test_seed_bounds(self):
        """Test that seed must be within bounds."""
        # Valid values
        ImageGenerationConfig(seed=0)
        ImageGenerationConfig(seed=858993459)

        # Below minimum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(seed=-1)

        # Above maximum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(seed=858993460)

    def test_number_of_images_bounds(self):
        """Test that numberOfImages must be within bounds."""
        # Valid values
        ImageGenerationConfig(numberOfImages=1)
        ImageGenerationConfig(numberOfImages=5)

        # Below minimum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(numberOfImages=0)

        # Above maximum
        with pytest.raises(ValidationError):
            ImageGenerationConfig(numberOfImages=6)

    def test_aspect_ratio_validation(self):
        """Test that aspect ratio must be between 1:4 and 4:1."""
        # Valid aspect ratios
        ImageGenerationConfig(width=1024, height=1024)  # 1:1
        ImageGenerationConfig(width=512, height=2048)  # 1:4
        ImageGenerationConfig(width=2048, height=512)  # 4:1

        # Invalid aspect ratios
        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=320, height=1600)  # > 1:4

        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=1600, height=320)  # > 4:1

    def test_total_pixels_validation(self):
        """Test that total pixel count must be less than 4,194,304."""
        # Valid pixel count
        ImageGenerationConfig(width=2000, height=2000)  # 4,000,000 pixels

        # Invalid pixel count
        with pytest.raises(ValidationError):
            ImageGenerationConfig(width=2048, height=2048)  # 4,194,304 pixels (equal to limit)


class TestTextToImageParams:
    """Tests for the TextToImageParams model."""

    def test_valid_params(self):
        """Test that valid parameters are accepted."""
        params = TextToImageParams(text='A beautiful mountain landscape')
        assert params.text == 'A beautiful mountain landscape'
        assert params.negativeText is None

    def test_with_negative_text(self):
        """Test with negative text parameter."""
        params = TextToImageParams(
            text='A beautiful mountain landscape', negativeText='people, clouds'
        )
        assert params.text == 'A beautiful mountain landscape'
        assert params.negativeText == 'people, clouds'

    def test_text_length_validation(self):
        """Test that text length is validated."""
        # Empty text
        with pytest.raises(ValidationError):
            TextToImageParams(text='')

        # Text too long (> 1024 characters)
        with pytest.raises(ValidationError):
            TextToImageParams(text='a' * 1025)

    def test_negative_text_length_validation(self):
        """Test that negative text length is validated."""
        # Empty negative text
        with pytest.raises(ValidationError):
            TextToImageParams(text='A beautiful mountain landscape', negativeText='')

        # Negative text too long (> 1024 characters)
        with pytest.raises(ValidationError):
            TextToImageParams(text='A beautiful mountain landscape', negativeText='a' * 1025)


class TestColorGuidedGenerationParams:
    """Tests for the ColorGuidedGenerationParams model."""

    def test_valid_params(self):
        """Test that valid parameters are accepted."""
        params = ColorGuidedGenerationParams(
            text='A beautiful mountain landscape', colors=['#FF5733', '#33FF57', '#3357FF']
        )
        assert params.text == 'A beautiful mountain landscape'
        assert params.colors == ['#FF5733', '#33FF57', '#3357FF']
        assert params.negativeText is None

    def test_with_negative_text(self):
        """Test with negative text parameter."""
        params = ColorGuidedGenerationParams(
            text='A beautiful mountain landscape',
            colors=['#FF5733', '#33FF57', '#3357FF'],
            negativeText='people, clouds',
        )
        assert params.text == 'A beautiful mountain landscape'
        assert params.colors == ['#FF5733', '#33FF57', '#3357FF']
        assert params.negativeText == 'people, clouds'

    def test_hex_color_validation(self):
        """Test that hex colors are validated."""
        # Valid hex colors
        ColorGuidedGenerationParams(
            text='A beautiful mountain landscape', colors=['#FF5733', '#33FF57', '#3357FF']
        )

        # Invalid hex colors
        with pytest.raises(ValidationError):
            ColorGuidedGenerationParams(
                text='A beautiful mountain landscape',
                colors=['FF5733', '#33FF57', '#3357FF'],  # Missing #
            )

        with pytest.raises(ValidationError):
            ColorGuidedGenerationParams(
                text='A beautiful mountain landscape',
                colors=['#FF573', '#33FF57', '#3357FF'],  # Too short
            )

        with pytest.raises(ValidationError):
            ColorGuidedGenerationParams(
                text='A beautiful mountain landscape',
                colors=['#FF5733', '#33FF57G', '#3357FF'],  # Invalid character
            )

    def test_colors_max_length(self):
        """Test that colors list has a maximum length of 10."""
        # Valid length
        ColorGuidedGenerationParams(text='A beautiful mountain landscape', colors=['#FF5733'] * 10)

        # Invalid length
        with pytest.raises(ValidationError):
            ColorGuidedGenerationParams(
                text='A beautiful mountain landscape', colors=['#FF5733'] * 11
            )


class TestTextImageRequest:
    """Tests for the TextImageRequest model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        request = TextImageRequest(
            textToImageParams=TextToImageParams(text='A beautiful mountain landscape')
        )
        assert request.taskType == TaskType.TEXT_IMAGE
        assert request.textToImageParams.text == 'A beautiful mountain landscape'
        assert request.textToImageParams.negativeText is None
        assert isinstance(request.imageGenerationConfig, ImageGenerationConfig)

    def test_custom_values(self):
        """Test that custom values are accepted."""
        request = TextImageRequest(
            textToImageParams=TextToImageParams(
                text='A beautiful mountain landscape', negativeText='people, clouds'
            ),
            imageGenerationConfig=ImageGenerationConfig(
                width=512,
                height=768,
                quality=Quality.PREMIUM,
                cfgScale=8.0,
                seed=12345,
                numberOfImages=3,
            ),
        )
        assert request.taskType == TaskType.TEXT_IMAGE
        assert request.textToImageParams.text == 'A beautiful mountain landscape'
        assert request.textToImageParams.negativeText == 'people, clouds'
        assert request.imageGenerationConfig.width == 512
        assert request.imageGenerationConfig.height == 768
        assert request.imageGenerationConfig.quality == Quality.PREMIUM
        assert request.imageGenerationConfig.cfgScale == 8.0
        assert request.imageGenerationConfig.seed == 12345
        assert request.imageGenerationConfig.numberOfImages == 3

    def test_to_api_dict(self):
        """Test the to_api_dict method."""
        # Without negative text
        request = TextImageRequest(
            textToImageParams=TextToImageParams(text='A beautiful mountain landscape')
        )
        api_dict = request.to_api_dict()
        assert api_dict['taskType'] == TaskType.TEXT_IMAGE
        assert api_dict['textToImageParams']['text'] == 'A beautiful mountain landscape'
        assert 'negativeText' not in api_dict['textToImageParams']
        assert api_dict['imageGenerationConfig'] is not None

        # With negative text
        request = TextImageRequest(
            textToImageParams=TextToImageParams(
                text='A beautiful mountain landscape', negativeText='people, clouds'
            )
        )
        api_dict = request.to_api_dict()
        assert api_dict['taskType'] == TaskType.TEXT_IMAGE
        assert api_dict['textToImageParams']['text'] == 'A beautiful mountain landscape'
        assert api_dict['textToImageParams']['negativeText'] == 'people, clouds'
        assert api_dict['imageGenerationConfig'] is not None


class TestColorGuidedRequest:
    """Tests for the ColorGuidedRequest model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        request = ColorGuidedRequest(
            colorGuidedGenerationParams=ColorGuidedGenerationParams(
                text='A beautiful mountain landscape', colors=['#FF5733', '#33FF57', '#3357FF']
            )
        )
        assert request.taskType == TaskType.COLOR_GUIDED_GENERATION
        assert request.colorGuidedGenerationParams.text == 'A beautiful mountain landscape'
        assert request.colorGuidedGenerationParams.colors == ['#FF5733', '#33FF57', '#3357FF']
        assert request.colorGuidedGenerationParams.negativeText is None
        assert isinstance(request.imageGenerationConfig, ImageGenerationConfig)

    def test_custom_values(self):
        """Test that custom values are accepted."""
        request = ColorGuidedRequest(
            colorGuidedGenerationParams=ColorGuidedGenerationParams(
                text='A beautiful mountain landscape',
                colors=['#FF5733', '#33FF57', '#3357FF'],
                negativeText='people, clouds',
            ),
            imageGenerationConfig=ImageGenerationConfig(
                width=512,
                height=768,
                quality=Quality.PREMIUM,
                cfgScale=8.0,
                seed=12345,
                numberOfImages=3,
            ),
        )
        assert request.taskType == TaskType.COLOR_GUIDED_GENERATION
        assert request.colorGuidedGenerationParams.text == 'A beautiful mountain landscape'
        assert request.colorGuidedGenerationParams.colors == ['#FF5733', '#33FF57', '#3357FF']
        assert request.colorGuidedGenerationParams.negativeText == 'people, clouds'
        assert request.imageGenerationConfig.width == 512
        assert request.imageGenerationConfig.height == 768
        assert request.imageGenerationConfig.quality == Quality.PREMIUM
        assert request.imageGenerationConfig.cfgScale == 8.0
        assert request.imageGenerationConfig.seed == 12345
        assert request.imageGenerationConfig.numberOfImages == 3

    def test_to_api_dict(self):
        """Test the to_api_dict method."""
        # Without negative text
        request = ColorGuidedRequest(
            colorGuidedGenerationParams=ColorGuidedGenerationParams(
                text='A beautiful mountain landscape', colors=['#FF5733', '#33FF57', '#3357FF']
            )
        )
        api_dict = request.to_api_dict()
        assert api_dict['taskType'] == TaskType.COLOR_GUIDED_GENERATION
        assert api_dict['colorGuidedGenerationParams']['text'] == 'A beautiful mountain landscape'
        assert api_dict['colorGuidedGenerationParams']['colors'] == [
            '#FF5733',
            '#33FF57',
            '#3357FF',
        ]
        assert 'negativeText' not in api_dict['colorGuidedGenerationParams']
        assert api_dict['imageGenerationConfig'] is not None

        # With negative text
        request = ColorGuidedRequest(
            colorGuidedGenerationParams=ColorGuidedGenerationParams(
                text='A beautiful mountain landscape',
                colors=['#FF5733', '#33FF57', '#3357FF'],
                negativeText='people, clouds',
            )
        )
        api_dict = request.to_api_dict()
        assert api_dict['taskType'] == TaskType.COLOR_GUIDED_GENERATION
        assert api_dict['colorGuidedGenerationParams']['text'] == 'A beautiful mountain landscape'
        assert api_dict['colorGuidedGenerationParams']['colors'] == [
            '#FF5733',
            '#33FF57',
            '#3357FF',
        ]
        assert api_dict['colorGuidedGenerationParams']['negativeText'] == 'people, clouds'
        assert api_dict['imageGenerationConfig'] is not None


class TestMcpImageGenerationResponse:
    """Tests for the McpImageGenerationResponse model."""

    def test_success_response(self):
        """Test that a success response is created correctly."""
        response = McpImageGenerationResponse(
            status='success', paths=['file:///path/to/image1.png', 'file:///path/to/image2.png']
        )
        assert response.status == 'success'
        assert response.paths == ['file:///path/to/image1.png', 'file:///path/to/image2.png']


class TestImageGenerationResponse:
    """Tests for the ImageGenerationResponse model."""

    def test_success_response(self):
        """Test that a success response is created correctly."""
        response = ImageGenerationResponse(
            status='success',
            message='Generated 2 image(s)',
            paths=['/path/to/image1.png', '/path/to/image2.png'],
            prompt='A beautiful mountain landscape',
        )
        assert response.status == 'success'
        assert response.message == 'Generated 2 image(s)'
        assert response.paths == ['/path/to/image1.png', '/path/to/image2.png']
        assert response.prompt == 'A beautiful mountain landscape'
        assert response.negative_prompt is None
        assert response.colors is None

    def test_error_response(self):
        """Test that an error response is created correctly."""
        response = ImageGenerationResponse(
            status='error',
            message='An error occurred during image generation',
            paths=[],
            prompt='A beautiful mountain landscape',
        )
        assert response.status == 'error'
        assert response.message == 'An error occurred during image generation'
        assert response.paths == []
        assert response.prompt == 'A beautiful mountain landscape'
        assert response.negative_prompt is None
        assert response.colors is None

    def test_with_optional_fields(self):
        """Test with optional fields."""
        response = ImageGenerationResponse(
            status='success',
            message='Generated 2 image(s)',
            paths=['/path/to/image1.png', '/path/to/image2.png'],
            prompt='A beautiful mountain landscape',
            negative_prompt='people, clouds',
            colors=['#FF5733', '#33FF57', '#3357FF'],
        )
        assert response.status == 'success'
        assert response.message == 'Generated 2 image(s)'
        assert response.paths == ['/path/to/image1.png', '/path/to/image2.png']
        assert response.prompt == 'A beautiful mountain landscape'
        assert response.negative_prompt == 'people, clouds'
        assert response.colors == ['#FF5733', '#33FF57', '#3357FF']

    def test_dictionary_access(self):
        """Test dictionary-style access."""
        response = ImageGenerationResponse(
            status='success',
            message='Generated 2 image(s)',
            paths=['/path/to/image1.png', '/path/to/image2.png'],
            prompt='A beautiful mountain landscape',
        )
        assert response['status'] == 'success'
        assert response['message'] == 'Generated 2 image(s)'
        assert response['paths'] == ['/path/to/image1.png', '/path/to/image2.png']
        assert response['prompt'] == 'A beautiful mountain landscape'

        # Test accessing non-existent key
        with pytest.raises(KeyError):
            response['non_existent_key']
