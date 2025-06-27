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
# ruff: noqa: D101, D102, D103
"""Tests for the Glue Interactive Sessions handler."""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from awslabs.dataprocessing_mcp_server.handlers.glue.glue_interactive_sessions_handler import GlueInteractiveSessionsHandler


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_glue_interactive_sessions_handler_initialization(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)

    # Verify that create_boto3_client was called with 'glue'
    mock_create_client.assert_called_once_with("glue")

    # Verify that all tools were registered
    assert mock_mcp.tool.call_count == 2

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]["name"] for call_args in call_args_list]

    # Verify that all expected tools were registered
    assert "manage_aws_glue_sessions" in tool_names
    assert "manage_aws_glue_statements" in tool_names


# Tests for manage_aws_glue_sessions method

@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags")
async def test_create_session_success(mock_prepare_tags, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the resource tags
    mock_prepare_tags.return_value = {"ManagedBy": "MCP"}
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the create_session response
    mock_glue_client.create_session.return_value = {
        "Session": {
            "Id": "test-session",
            "Status": "PROVISIONING"
        }
    }

    # Call the manage_aws_glue_sessions method with create-session operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="create-session",
        session_id="test-session",
        role="arn:aws:iam::123456789012:role/GlueInteractiveSessionRole",
        command={"Name": "glueetl", "PythonVersion": "3"},
        glue_version="3.0",
        description="Test session",
        timeout=60,
        idle_timeout=30,
        default_arguments={"--enable-glue-datacatalog": "true"},
        connections={"Connections": ["test-connection"]},
        max_capacity=5.0,
        number_of_workers=2,
        worker_type="G.1X",
        security_configuration="test-security-config",
        tags={"Environment": "Test"}
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully created session test-session" in result.content[0].text
    assert result.session_id == "test-session"
    assert result.session["Status"] == "PROVISIONING"

    # Verify that create_session was called with the correct parameters
    mock_glue_client.create_session.assert_called_once()
    args, kwargs = mock_glue_client.create_session.call_args
    assert kwargs["Id"] == "test-session"
    assert kwargs["Role"] == "arn:aws:iam::123456789012:role/GlueInteractiveSessionRole"
    assert kwargs["Command"] == {"Name": "glueetl", "PythonVersion": "3"}
    assert kwargs["GlueVersion"] == "3.0"
    assert kwargs["Description"] == "Test session"
    assert kwargs["Timeout"] == 60
    assert kwargs["IdleTimeout"] == 30
    assert kwargs["DefaultArguments"] == {"--enable-glue-datacatalog": "true"}
    assert kwargs["Connections"] == {"Connections": ["test-connection"]}
    assert kwargs["MaxCapacity"] == 5.0
    assert kwargs["NumberOfWorkers"] == 2
    assert kwargs["WorkerType"] == "G.1X"
    assert kwargs["SecurityConfiguration"] == "test-security-config"
    assert "Tags" in kwargs
    assert kwargs["Tags"]["Environment"] == "Test"
    assert kwargs["Tags"]["ManagedBy"] == "MCP"


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_create_session_no_write_access(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server without write access
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=False)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_sessions method with create-session operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="create-session",
        session_id="test-session",
        role="arn:aws:iam::123456789012:role/GlueInteractiveSessionRole",
        command={"Name": "glueetl", "PythonVersion": "3"}
    )

    # Verify the result indicates an error due to no write access
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Operation create-session is not allowed without write access" in result.content[0].text
    assert result.session_id == ""

    # Verify that create_session was NOT called
    mock_glue_client.create_session.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_delete_session_success(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return True
    mock_is_mcp_managed.return_value = True
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_session response
    mock_glue_client.get_session.return_value = {
        "Session": {
            "Id": "test-session",
            "Status": "READY",
            "Tags": {"ManagedBy": "MCP"}
        }
    }

    # Call the manage_aws_glue_sessions method with delete-session operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="delete-session",
        session_id="test-session"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully deleted session test-session" in result.content[0].text
    assert result.session_id == "test-session"

    # Verify that delete_session was called with the correct parameters
    mock_glue_client.delete_session.assert_called_once()
    args, kwargs = mock_glue_client.delete_session.call_args
    assert kwargs["Id"] == "test-session"


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_delete_session_not_mcp_managed(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return False
    mock_is_mcp_managed.return_value = False
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_session response
    mock_glue_client.get_session.return_value = {
        "Session": {
            "Id": "test-session",
            "Status": "READY",
            "Tags": {}  # No MCP tags
        }
    }

    # Call the manage_aws_glue_sessions method with delete-session operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="delete-session",
        session_id="test-session"
    )

    # Verify the result indicates an error because the session is not MCP managed
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Cannot delete session test-session - it is not managed by the MCP server" in result.content[0].text
    assert result.session_id == "test-session"

    # Verify that delete_session was NOT called
    mock_glue_client.delete_session.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_get_session_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_session response
    mock_session_details = {
        "Id": "test-session",
        "Status": "READY",
        "Command": {"Name": "glueetl", "PythonVersion": "3"},
        "GlueVersion": "3.0"
    }
    mock_glue_client.get_session.return_value = {
        "Session": mock_session_details
    }

    # Call the manage_aws_glue_sessions method with get-session operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="get-session",
        session_id="test-session"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved session test-session" in result.content[0].text
    assert result.session_id == "test-session"
    assert result.session == mock_session_details

    # Verify that get_session was called with the correct parameters
    mock_glue_client.get_session.assert_called()
    args, kwargs = mock_glue_client.get_session.call_args_list[-1]
    assert kwargs["Id"] == "test-session"


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_list_sessions_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the list_sessions response
    mock_glue_client.list_sessions.return_value = {
        "Sessions": [
            {
                "Id": "session1",
                "Status": "READY"
            },
            {
                "Id": "session2",
                "Status": "PROVISIONING"
            }
        ],
        "Ids": ["session1", "session2"],
        "NextToken": "next-token"
    }

    # Call the manage_aws_glue_sessions method with list-sessions operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="list-sessions",
        max_results=10,
        next_token="token",
        tags={"Environment": "Test"}
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved sessions" in result.content[0].text
    assert len(result.sessions) == 2
    assert result.sessions[0]["Id"] == "session1"
    assert result.sessions[1]["Id"] == "session2"
    assert result.ids == ["session1", "session2"]
    assert result.next_token == "next-token"
    assert result.count == 2

    # Verify that list_sessions was called with the correct parameters
    mock_glue_client.list_sessions.assert_called_once()
    args, kwargs = mock_glue_client.list_sessions.call_args
    assert "MaxResults" in kwargs
    # MaxResults is converted to string in the handler
    assert kwargs["MaxResults"] == "10"
    assert "NextToken" in kwargs
    assert kwargs["NextToken"] == "token"
    assert "Tags" in kwargs
    assert kwargs["Tags"] == {"Environment": "Test"}


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_stop_session_success(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return True
    mock_is_mcp_managed.return_value = True
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_session response
    mock_glue_client.get_session.return_value = {
        "Session": {
            "Id": "test-session",
            "Status": "READY",
            "Tags": {"ManagedBy": "MCP"}
        }
    }

    # Call the manage_aws_glue_sessions method with stop-session operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="stop-session",
        session_id="test-session"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully stopped session test-session" in result.content[0].text
    assert result.session_id == "test-session"

    # Verify that stop_session was called with the correct parameters
    mock_glue_client.stop_session.assert_called_once()
    args, kwargs = mock_glue_client.stop_session.call_args
    assert kwargs["Id"] == "test-session"


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_session_not_found(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_session to raise EntityNotFoundException
    mock_glue_client.exceptions.EntityNotFoundException = ClientError(
        {"Error": {"Code": "EntityNotFoundException", "Message": "Session not found"}},
        "get_session"
    )
    mock_glue_client.get_session.side_effect = mock_glue_client.exceptions.EntityNotFoundException

    # Call the manage_aws_glue_sessions method with delete-session operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="delete-session",
        session_id="test-session"
    )

    # Verify the result indicates an error because the session was not found
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Session test-session not found" in result.content[0].text
    assert result.session_id == "test-session"

    # Verify that delete_session was NOT called
    mock_glue_client.delete_session.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_session_invalid_operation(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_sessions method with an invalid operation
    result = await handler.manage_aws_glue_sessions(
        mock_ctx,
        operation="invalid-operation",
        session_id="test-session"
    )

    # Verify the result indicates an error due to invalid operation
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Invalid operation: invalid-operation" in result.content[0].text
    assert result.session_id == "test-session"


# Tests for manage_aws_glue_statements method

@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_run_statement_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the run_statement response
    mock_glue_client.run_statement.return_value = {
        "Id": 1
    }

    # Call the manage_aws_glue_statements method with run-statement operation
    result = await handler.manage_aws_glue_statements(
        mock_ctx,
        operation="run-statement",
        session_id="test-session",
        code="df = spark.read.csv('s3://bucket/data.csv')\ndf.show(5)"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully ran statement in session test-session" in result.content[0].text
    assert result.session_id == "test-session"
    assert result.statement_id == 1

    # Verify that run_statement was called with the correct parameters
    mock_glue_client.run_statement.assert_called_once()
    args, kwargs = mock_glue_client.run_statement.call_args
    assert kwargs["SessionId"] == "test-session"
    assert kwargs["Code"] == "df = spark.read.csv('s3://bucket/data.csv')\ndf.show(5)"


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_run_statement_no_write_access(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server without write access
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=False)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_statements method with run-statement operation
    result = await handler.manage_aws_glue_statements(
        mock_ctx,
        operation="run-statement",
        session_id="test-session",
        code="df = spark.read.csv('s3://bucket/data.csv')\ndf.show(5)"
    )

    # Verify the result indicates an error due to no write access
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Operation run-statement is not allowed without write access" in result.content[0].text
    assert result.session_id == ""

    # Verify that run_statement was NOT called
    mock_glue_client.run_statement.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_cancel_statement_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_statements method with cancel-statement operation
    result = await handler.manage_aws_glue_statements(
        mock_ctx,
        operation="cancel-statement",
        session_id="test-session",
        statement_id=1
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully canceled statement 1 in session test-session" in result.content[0].text
    assert result.session_id == "test-session"
    assert result.statement_id == 1

    # Verify that cancel_statement was called with the correct parameters
    mock_glue_client.cancel_statement.assert_called_once()
    args, kwargs = mock_glue_client.cancel_statement.call_args
    assert kwargs["SessionId"] == "test-session"
    assert kwargs["Id"] == 1


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_get_statement_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_statement response
    mock_statement_details = {
        "Id": 1,
        "Code": "df = spark.read.csv('s3://bucket/data.csv')\ndf.show(5)",
        "State": "AVAILABLE",
        "Output": {
            "Status": "ok",
            "Data": {"text/plain": "+---+----+\n|id |name|\n+---+----+\n|1  |Alice|\n|2  |Bob  |\n+---+----+"}
        }
    }
    mock_glue_client.get_statement.return_value = {
        "Statement": mock_statement_details
    }

    # Call the manage_aws_glue_statements method with get-statement operation
    result = await handler.manage_aws_glue_statements(
        mock_ctx,
        operation="get-statement",
        session_id="test-session",
        statement_id=1
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved statement 1 in session test-session" in result.content[0].text
    assert result.session_id == "test-session"
    assert result.statement_id == 1
    assert result.statement == mock_statement_details

    # Verify that get_statement was called with the correct parameters
    mock_glue_client.get_statement.assert_called_once()
    args, kwargs = mock_glue_client.get_statement.call_args
    assert kwargs["SessionId"] == "test-session"
    assert kwargs["Id"] == 1


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_list_statements_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the list_statements response
    mock_glue_client.list_statements.return_value = {
        "Statements": [
            {
                "Id": 1,
                "State": "AVAILABLE"
            },
            {
                "Id": 2,
                "State": "RUNNING"
            }
        ],
        "NextToken": "next-token"
    }

    # Call the manage_aws_glue_statements method with list-statements operation
    result = await handler.manage_aws_glue_statements(
        mock_ctx,
        operation="list-statements",
        session_id="test-session",
        max_results=10,
        next_token="token"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved statements for session test-session" in result.content[0].text
    assert result.session_id == "test-session"
    assert len(result.statements) == 2
    assert result.statements[0]["Id"] == 1
    assert result.statements[1]["Id"] == 2
    assert result.next_token == "next-token"
    assert result.count == 2

    # Verify that list_statements was called with the correct parameters
    mock_glue_client.list_statements.assert_called_once()
    args, kwargs = mock_glue_client.list_statements.call_args
    assert kwargs["SessionId"] == "test-session"
    assert "MaxResults" in kwargs
    assert "NextToken" in kwargs


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_statement_invalid_operation(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_statements method with an invalid operation
    result = await handler.manage_aws_glue_statements(
        mock_ctx,
        operation="invalid-operation",
        session_id="test-session",
        statement_id=1
    )

    # Verify the result indicates an error due to invalid operation
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Invalid operation: invalid-operation" in result.content[0].text
    assert result.session_id == "test-session"
    assert result.statement_id == 1


# Split the test_missing_required_parameters into individual tests for better isolation

@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_missing_role_and_command_for_create_session(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Test missing role and command for create-session
    # The handler checks for None values, not missing parameters
    with pytest.raises(ValueError) as excinfo:
        await handler.manage_aws_glue_sessions(
            mock_ctx,
            operation="create-session",
            session_id="test-session",
            role=None,
            command=None
        )
    assert "role and command are required" in str(excinfo.value)


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_missing_session_id_for_delete_session(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Test missing session_id for delete-session
    with pytest.raises(ValueError) as excinfo:
        await handler.manage_aws_glue_sessions(
            mock_ctx,
            operation="delete-session",
            session_id=None
        )
    assert "session_id is required" in str(excinfo.value)


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_missing_session_id_for_get_session(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Test missing session_id for get-session
    with pytest.raises(ValueError) as excinfo:
        await handler.manage_aws_glue_sessions(
            mock_ctx,
            operation="get-session",
            session_id=None
        )
    assert "session_id is required" in str(excinfo.value)


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_missing_session_id_for_stop_session(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Test missing session_id for stop-session
    with pytest.raises(ValueError) as excinfo:
        await handler.manage_aws_glue_sessions(
            mock_ctx,
            operation="stop-session",
            session_id=None
        )
    assert "session_id is required" in str(excinfo.value)


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_missing_code_for_run_statement(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Test missing code for run-statement
    with pytest.raises(ValueError) as excinfo:
        await handler.manage_aws_glue_statements(
            mock_ctx,
            operation="run-statement",
            session_id="test-session",
            code=None
        )
    assert "code is required" in str(excinfo.value)


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_missing_statement_id_for_cancel_statement(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Test missing statement_id for cancel-statement
    with pytest.raises(ValueError) as excinfo:
        await handler.manage_aws_glue_statements(
            mock_ctx,
            operation="cancel-statement",
            session_id="test-session",
            statement_id=None
        )
    assert "statement_id is required" in str(excinfo.value)


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_missing_statement_id_for_get_statement(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Interactive Sessions handler with the mock MCP server
    handler = GlueInteractiveSessionsHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Test missing statement_id for get-statement
    with pytest.raises(ValueError) as excinfo:
        await handler.manage_aws_glue_statements(
            mock_ctx,
            operation="get-statement",
            session_id="test-session",
            statement_id=None
        )
    assert "statement_id is required" in str(excinfo.value)
