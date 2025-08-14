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

"""Tests for the fixed check_access_analyzer function."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.util.security_services import (
    check_access_analyzer,
)


@pytest.mark.asyncio
async def test_check_access_analyzer_api_error_handling(mock_ctx, mock_boto3_session):
    """Test that the check_access_analyzer function handles API errors correctly."""
    # Create a mock Access Analyzer client that raises an exception
    mock_client = mock.MagicMock()
    mock_client.list_analyzers = mock.MagicMock(side_effect=Exception("API Error"))
    mock_boto3_session.client.return_value = mock_client

    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert "enabled" in result
    assert result["enabled"] is False
    assert "error" in result
    assert "API Error" in result["error"]
    assert "message" in result
    assert "Error checking IAM Access Analyzer status" in result["message"]
    mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_check_access_analyzer_with_active_analyzers(mock_ctx, mock_boto3_session):
    """Test the check_access_analyzer function when there are active analyzers."""
    # Create a mock Access Analyzer client
    mock_client = mock.MagicMock()

    # Mock the list_analyzers response with an active analyzer
    mock_client.list_analyzers.return_value = {
        "analyzers": [
            {
                "arn": "arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-analyzer",
                "name": "account-analyzer",
                "type": "ACCOUNT",
                "status": "ACTIVE",
                "createdAt": "2023-01-01T00:00:00Z",
            }
        ]
    }

    # Mock the list_findings response
    mock_client.list_findings.return_value = {"findings": ["finding1", "finding2"]}

    mock_boto3_session.client.return_value = mock_client

    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert "enabled" in result
    assert result["enabled"] is True
    assert "analyzers" in result
    assert len(result["analyzers"]) == 1
    assert result["analyzers"][0]["name"] == "account-analyzer"
    assert result["analyzers"][0]["status"] == "ACTIVE"
    assert "message" in result
    assert "IAM Access Analyzer is enabled" in result["message"]
    assert "1 analyzer(s) (1 active)" in result["message"]


@pytest.mark.asyncio
async def test_check_access_analyzer_with_inactive_analyzers(mock_ctx, mock_boto3_session):
    """Test the check_access_analyzer function when there are inactive analyzers."""
    # Create a mock Access Analyzer client
    mock_client = mock.MagicMock()

    # Mock the list_analyzers response with an inactive analyzer
    mock_client.list_analyzers.return_value = {
        "analyzers": [
            {
                "arn": "arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-analyzer",
                "name": "account-analyzer",
                "type": "ACCOUNT",
                "status": "INACTIVE",
                "createdAt": "2023-01-01T00:00:00Z",
            }
        ]
    }

    # Mock the list_findings response
    mock_client.list_findings.return_value = {"findings": []}

    mock_boto3_session.client.return_value = mock_client

    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert "enabled" in result
    assert result["enabled"] is True  # Should still be True even with inactive analyzers
    assert "analyzers" in result
    assert len(result["analyzers"]) == 1
    assert result["analyzers"][0]["name"] == "account-analyzer"
    assert result["analyzers"][0]["status"] == "INACTIVE"
    assert "message" in result
    assert "IAM Access Analyzer is enabled" in result["message"]
    assert "1 analyzer(s) (0 active)" in result["message"]


@pytest.mark.asyncio
async def test_check_access_analyzer_with_no_analyzers(mock_ctx, mock_boto3_session):
    """Test the check_access_analyzer function when there are no analyzers."""
    # Create a mock Access Analyzer client
    mock_client = mock.MagicMock()

    # Mock the list_analyzers response with no analyzers
    mock_client.list_analyzers.return_value = {"analyzers": []}

    mock_boto3_session.client.return_value = mock_client

    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert "enabled" in result
    assert result["enabled"] is False
    assert "analyzers" in result
    assert len(result["analyzers"]) == 0
    assert "setup_instructions" in result
    assert "message" in result
    assert "IAM Access Analyzer is not enabled" in result["message"]


@pytest.mark.asyncio
async def test_check_access_analyzer_with_real_world_response(mock_ctx, mock_boto3_session):
    """Test the check_access_analyzer function with a real-world response."""
    # Create a mock Access Analyzer client
    mock_client = mock.MagicMock()

    # Mock the list_analyzers response with a real-world response
    mock_client.list_analyzers.return_value = {
        "analyzers": [
            {
                "arn": "arn:aws:access-analyzer:us-east-1:384612698411:analyzer/account-external-access-analyzer",
                "name": "account-external-access-analyzer",
                "type": "ACCOUNT",
                "createdAt": "2025-06-06T15:39:48Z",
                "lastResourceAnalyzed": "arn:aws:ec2:us-east-1::snapshot/snap-0fb157b70e288e14b",
                "lastResourceAnalyzedAt": "2025-06-20T07:18:46.557Z",
                "tags": {},
                "status": "ACTIVE",
            }
        ]
    }

    # Mock the list_findings response
    mock_client.list_findings.return_value = {"findings": ["finding1", "finding2", "finding3"]}

    mock_boto3_session.client.return_value = mock_client

    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert "enabled" in result
    assert result["enabled"] is True
    assert "analyzers" in result
    assert len(result["analyzers"]) == 1
    assert result["analyzers"][0]["name"] == "account-external-access-analyzer"
    assert result["analyzers"][0]["status"] == "ACTIVE"
    assert result["analyzers"][0]["findings_count"] == "3"
    assert "message" in result
    assert "IAM Access Analyzer is enabled" in result["message"]
    assert "1 analyzer(s) (1 active)" in result["message"]


@pytest.mark.asyncio
async def test_check_access_analyzer_with_missing_analyzers_field(mock_ctx, mock_boto3_session):
    """Test the check_access_analyzer function when the analyzers field is missing."""
    # Create a mock Access Analyzer client
    mock_client = mock.MagicMock()

    # Mock the list_analyzers response with a missing analyzers field
    mock_client.list_analyzers.return_value = {}

    mock_boto3_session.client.return_value = mock_client

    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert "enabled" in result
    assert result["enabled"] is False
    assert "analyzers" in result
    assert len(result["analyzers"]) == 0
    assert "debug_info" in result
    assert "raw_response" in result["debug_info"]
    assert "setup_instructions" in result
    assert "message" in result
    assert "IAM Access Analyzer is not enabled" in result["message"]
