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

"""Tests for the fixed list_services_in_region function in resource_utils module."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.util.resource_utils import (
    list_services_in_region,
)


@pytest.mark.asyncio
async def test_list_services_in_region_search_exception(mock_ctx, mock_boto3_session):
    """Test handling when the search API raises an exception."""
    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock search to raise an exception that is not about Resource Explorer not being set up
    resource_explorer.search = mock.MagicMock(side_effect=Exception("Some other API error"))

    # Call the function
    result = await list_services_in_region("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["region"] == "us-east-1"
    assert result["services"] == []
    assert "error" in result
    assert "Some other API error" in result["error"]
    mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_list_services_in_region_resource_explorer_not_setup_specific(
    mock_ctx, mock_boto3_session
):
    """Test handling when Resource Explorer is not set up in the region with specific error message."""
    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock search to raise an exception indicating Resource Explorer is not set up
    resource_explorer.search = mock.MagicMock(
        side_effect=Exception("Resource Explorer has not been set up")
    )

    # Call the function
    result = await list_services_in_region("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["region"] == "us-east-1"
    assert result["services"] == []
    assert "error" in result
    assert "Resource Explorer has not been set up" in result["error"]
    mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_list_services_in_region_paginator_exception(mock_ctx, mock_boto3_session):
    """Test handling when the paginator raises an exception."""
    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock search to succeed but paginator to raise an exception
    resource_explorer.search = mock.MagicMock()

    # Mock get_paginator to return a paginator that raises an exception
    paginator = mock.MagicMock()
    resource_explorer.get_paginator.return_value = paginator
    paginator.paginate = mock.MagicMock(side_effect=Exception("Paginator error"))

    # Call the function
    result = await list_services_in_region("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["region"] == "us-east-1"
    assert result["services"] == []
    assert "error" in result
    assert "Paginator error" in result["error"]
    mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_list_services_in_region_page_iterator_exception(mock_ctx, mock_boto3_session):
    """Test handling when iterating through pages raises an exception."""
    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock search to succeed
    resource_explorer.search = mock.MagicMock()

    # Mock get_paginator to return a paginator
    paginator = mock.MagicMock()
    resource_explorer.get_paginator.return_value = paginator

    # Mock paginate to return a page iterator
    page_iterator = mock.MagicMock()
    paginator.paginate.return_value = page_iterator

    # Mock __iter__ to raise an exception
    page_iterator.__iter__ = mock.MagicMock(side_effect=Exception("Page iterator error"))

    # Call the function
    result = await list_services_in_region("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["region"] == "us-east-1"
    assert result["services"] == []
    assert "error" in result
    assert "Page iterator error" in result["error"]
    mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_list_services_in_region_datetime_serialization(mock_ctx, mock_boto3_session):
    """Test handling of datetime objects in the response."""
    import datetime

    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock search to succeed
    resource_explorer.search = mock.MagicMock()

    # Mock get_paginator to return a paginator
    paginator = mock.MagicMock()
    resource_explorer.get_paginator.return_value = paginator

    # Mock paginate to return a page iterator
    page_iterator = mock.MagicMock()
    paginator.paginate.return_value = page_iterator

    # Create a datetime object
    now = datetime.datetime.now()

    # Mock __iter__ to return a page with a datetime object
    page_iterator.__iter__.return_value = [
        {
            "Resources": [
                {
                    "Arn": "arn:aws:s3:::test-bucket",
                    "LastModified": now,  # This is a datetime object
                }
            ]
        }
    ]

    # Call the function
    result = await list_services_in_region("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["region"] == "us-east-1"
    assert "s3" in result["services"]
    assert result["service_counts"]["s3"] == 1
    assert result["total_resources"] == 1


@pytest.mark.asyncio
async def test_list_services_in_region_general_exception(mock_ctx, mock_boto3_session):
    """Test handling of a general exception in the function."""
    # Mock boto3_session.client to raise an exception
    mock_boto3_session.client = mock.MagicMock(side_effect=Exception("General error"))

    # Call the function
    result = await list_services_in_region("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["region"] == "us-east-1"
    assert result["services"] == []
    assert "error" in result
    assert "General error" in result["error"]

    # Check that either ctx.error or ctx.warning was called with a string containing "General error"
    # The implementation might use either one depending on where the exception is caught
    assert mock_ctx.error.called or mock_ctx.warning.called

    if mock_ctx.error.called:
        call_args = mock_ctx.error.call_args[0][0]
        assert isinstance(call_args, str)
        assert "General error" in call_args
    else:
        call_args = mock_ctx.warning.call_args[0][0]
        assert isinstance(call_args, str)
        assert "General error" in call_args
