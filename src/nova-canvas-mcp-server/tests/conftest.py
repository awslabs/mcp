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
"""Test fixtures for the nova-canvas-mcp-server tests."""

import base64
import json
import pytest
import tempfile
from typing import Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def temp_workspace_dir() -> Generator[str, None, None]:
    """Create a temporary directory for image output."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_bedrock_runtime_client() -> MagicMock:
    """Create a mock Bedrock runtime client for testing."""
    mock_client = MagicMock()

    # Mock the invoke_model method
    mock_response = {'body': MagicMock()}
    mock_response['body'].read.return_value = json.dumps(
        {
            'images': [
                base64.b64encode(b'mock_image_data_1').decode('utf-8'),
                base64.b64encode(b'mock_image_data_2').decode('utf-8'),
            ]
        }
    ).encode('utf-8')

    mock_client.invoke_model.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_text_prompt() -> str:
    """Return a sample text prompt for testing."""
    return 'A beautiful mountain landscape with a lake and trees'


@pytest.fixture
def sample_negative_prompt() -> str:
    """Return a sample negative prompt for testing."""
    return 'people, anatomy, hands, low quality, low resolution, low detail'


@pytest.fixture
def sample_colors() -> List[str]:
    """Return a sample list of colors for testing."""
    return ['#FF5733', '#33FF57', '#3357FF']


@pytest.fixture
def sample_base64_images() -> List[str]:
    """Return a list of sample base64-encoded images for testing."""
    return [
        base64.b64encode(b'mock_image_data_1').decode('utf-8'),
        base64.b64encode(b'mock_image_data_2').decode('utf-8'),
    ]


@pytest.fixture
def mock_successful_response() -> Dict:
    """Return a mock successful response from the Nova Canvas API."""
    return {
        'images': [
            base64.b64encode(b'mock_image_data_1').decode('utf-8'),
            base64.b64encode(b'mock_image_data_2').decode('utf-8'),
        ]
    }


@pytest.fixture
def mock_error_response() -> Dict:
    """Return a mock error response from the Nova Canvas API."""
    return {'error': 'An error occurred during image generation'}


@pytest.fixture
def mock_context() -> AsyncMock:
    """Create a mock MCP context for testing."""
    context = AsyncMock()
    context.error = AsyncMock()
    return context
