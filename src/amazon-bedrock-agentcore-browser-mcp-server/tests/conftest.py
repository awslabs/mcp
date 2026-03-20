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

"""Test fixtures for Amazon Bedrock AgentCore Browser MCP Server."""

import pytest
from awslabs.amazon_bedrock_agentcore_browser_mcp_server import aws_client
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def _clear_client_cache():
    """Clear cached boto3 clients between tests."""
    aws_client._clients.clear()
    yield
    aws_client._clients.clear()


@pytest.fixture
def mock_dp_client():
    """Mock boto3 data plane client for browser session operations."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_cp_client():
    """Mock boto3 control plane client for browser management operations."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_start_browser_session_response():
    """Standard mock response for start_browser_session API."""
    return {
        'sessionId': 'test-session-123',
        'createdAt': '2024-01-01T00:00:00Z',
        'streams': {
            'automationStream': {'streamEndpoint': 'wss://automation.example.com/session-123'},
            'liveViewStream': {'streamEndpoint': 'wss://liveview.example.com/session-123'},
        },
    }


@pytest.fixture
def mock_get_browser_session_response():
    """Standard mock response for get_browser_session API."""
    return {
        'sessionId': 'test-session-123',
        'browserIdentifier': 'aws.browser.v1',
        'status': 'READY',
        'createdAt': '2024-01-01T00:00:00Z',
        'lastUpdatedAt': '2024-01-01T00:05:00Z',
        'sessionTimeoutSeconds': 900,
        'viewPort': {'width': 1456, 'height': 819},
        'streams': {
            'automationStream': {'streamEndpoint': 'wss://automation.example.com/session-123'},
            'liveViewStream': {'streamEndpoint': 'wss://liveview.example.com/session-123'},
        },
    }


@pytest.fixture
def mock_list_browser_sessions_response():
    """Standard mock response for list_browser_sessions API."""
    return {
        'sessionSummaries': [
            {
                'sessionId': 'session-1',
                'name': 'test-session-1',
                'status': 'ACTIVE',
                'createdAt': '2024-01-01T00:00:00Z',
            },
            {
                'sessionId': 'session-2',
                'name': 'test-session-2',
                'status': 'ACTIVE',
                'createdAt': '2024-01-01T00:01:00Z',
            },
        ],
        'nextToken': 'next-page-token',
    }


@pytest.fixture
def mock_stop_browser_session_response():
    """Standard mock response for stop_browser_session API."""
    return {
        'sessionId': 'test-session-123',
        'browserIdentifier': 'aws.browser.v1',
        'lastUpdatedAt': '2024-01-01T00:10:00Z',
    }


@pytest.fixture
def mock_save_browser_session_profile_response():
    """Standard mock response for save_browser_session_profile API."""
    return {
        'profileIdentifier': 'test-profile',
        'browserIdentifier': 'aws.browser.v1',
        'sessionId': 'test-session-123',
        'lastUpdatedAt': '2024-01-01T00:10:00Z',
    }


@pytest.fixture
def mock_list_browsers_response():
    """Standard mock response for list_browsers API."""
    return {
        'browsers': [
            {
                'browserId': 'aws.browser.v1',
                'name': 'AWS Browser v1',
                'status': 'ACTIVE',
                'type': 'SYSTEM',
            },
            {
                'browserId': 'custom-browser-1',
                'name': 'Custom VPC Browser',
                'status': 'ACTIVE',
                'type': 'CUSTOM',
            },
        ],
        'nextToken': 'next-page-token',
    }


@pytest.fixture
def mock_get_browser_response():
    """Standard mock response for get_browser API."""
    return {
        'browserId': 'aws.browser.v1',
        'name': 'AWS Browser v1',
        'description': 'AWS-managed browser instance',
        'status': 'ACTIVE',
        'type': 'SYSTEM',
        'networkConfiguration': None,
        'createdAt': '2024-01-01T00:00:00Z',
    }


@pytest.fixture
def client_error_resource_not_found():
    """ClientError for ResourceNotFoundException."""
    error_response = {
        'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Session not found'}
    }
    return ClientError(error_response, 'GetBrowserSession')


@pytest.fixture
def client_error_access_denied():
    """ClientError for AccessDeniedException."""
    error_response = {
        'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied to resource'}
    }
    return ClientError(error_response, 'StartBrowserSession')
