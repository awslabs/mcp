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

"""Tests for the Glue Interactive Sessions models."""

import pytest
from awslabs.dataprocessing_mcp_server.models.glue_models import (
    # Session response models
    CreateSessionResponse,
    DeleteSessionResponse,
    GetSessionResponse,
    ListSessionsResponse,
    StopSessionResponse,
    # Statement response models
    RunStatementResponse,
    CancelStatementResponse,
    GetStatementResponse,
    ListStatementsResponse,
)
from mcp.types import TextContent
from pydantic import ValidationError


class TestSessionResponseModels:
    """Tests for the session response models."""

    def test_create_session_response(self):
        """Test creating a CreateSessionResponse."""
        session_details = {
            "Id": "test-session",
            "Status": "PROVISIONING",
            "Command": {"Name": "glueetl", "PythonVersion": "3"},
            "GlueVersion": "3.0",
        }
        
        response = CreateSessionResponse(
            isError=False,
            session_id="test-session",
            session=session_details,
            content=[TextContent(type="text", text="Successfully created session")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert response.session == session_details
        assert response.operation == "create-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully created session"

    def test_create_session_response_with_error(self):
        """Test creating a CreateSessionResponse with error."""
        response = CreateSessionResponse(
            isError=True,
            session_id="",
            session=None,
            content=[TextContent(type="text", text="Failed to create session")],
        )
        
        assert response.isError is True
        assert response.session_id == ""
        assert response.session is None
        assert response.operation == "create-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to create session"

    def test_delete_session_response(self):
        """Test creating a DeleteSessionResponse."""
        response = DeleteSessionResponse(
            isError=False,
            session_id="test-session",
            content=[TextContent(type="text", text="Successfully deleted session")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert response.operation == "delete-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully deleted session"

    def test_delete_session_response_with_error(self):
        """Test creating a DeleteSessionResponse with error."""
        response = DeleteSessionResponse(
            isError=True,
            session_id="test-session",
            content=[TextContent(type="text", text="Failed to delete session")],
        )
        
        assert response.isError is True
        assert response.session_id == "test-session"
        assert response.operation == "delete-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to delete session"

    def test_get_session_response(self):
        """Test creating a GetSessionResponse."""
        session_details = {
            "Id": "test-session",
            "Status": "READY",
            "Command": {"Name": "glueetl", "PythonVersion": "3"},
            "GlueVersion": "3.0",
            "CreatedOn": "2023-01-01T00:00:00Z",
        }
        
        response = GetSessionResponse(
            isError=False,
            session_id="test-session",
            session=session_details,
            content=[TextContent(type="text", text="Successfully retrieved session")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert response.session == session_details
        assert response.operation == "get-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully retrieved session"

    def test_get_session_response_with_error(self):
        """Test creating a GetSessionResponse with error."""
        response = GetSessionResponse(
            isError=True,
            session_id="test-session",
            session={},
            content=[TextContent(type="text", text="Failed to retrieve session")],
        )
        
        assert response.isError is True
        assert response.session_id == "test-session"
        assert response.session == {}
        assert response.operation == "get-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to retrieve session"

    def test_list_sessions_response(self):
        """Test creating a ListSessionsResponse."""
        sessions = [
            {
                "Id": "session1",
                "Status": "READY",
                "Command": {"Name": "glueetl", "PythonVersion": "3"},
            },
            {
                "Id": "session2",
                "Status": "PROVISIONING",
                "Command": {"Name": "glueetl", "PythonVersion": "3"},
            },
        ]
        
        response = ListSessionsResponse(
            isError=False,
            sessions=sessions,
            ids=["session1", "session2"],
            count=2,
            next_token="next-token",
            content=[TextContent(type="text", text="Successfully listed sessions")],
        )
        
        assert response.isError is False
        assert len(response.sessions) == 2
        assert response.sessions[0]["Id"] == "session1"
        assert response.sessions[1]["Id"] == "session2"
        assert response.ids == ["session1", "session2"]
        assert response.count == 2
        assert response.next_token == "next-token"
        assert response.operation == "list-sessions"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully listed sessions"

    def test_list_sessions_response_with_error(self):
        """Test creating a ListSessionsResponse with error."""
        response = ListSessionsResponse(
            isError=True,
            sessions=[],
            count=0,
            content=[TextContent(type="text", text="Failed to list sessions")],
        )
        
        assert response.isError is True
        assert len(response.sessions) == 0
        assert response.count == 0
        assert response.next_token is None  # Default value
        assert response.operation == "list-sessions"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to list sessions"

    def test_stop_session_response(self):
        """Test creating a StopSessionResponse."""
        response = StopSessionResponse(
            isError=False,
            session_id="test-session",
            content=[TextContent(type="text", text="Successfully stopped session")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert response.operation == "stop-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully stopped session"

    def test_stop_session_response_with_error(self):
        """Test creating a StopSessionResponse with error."""
        response = StopSessionResponse(
            isError=True,
            session_id="test-session",
            content=[TextContent(type="text", text="Failed to stop session")],
        )
        
        assert response.isError is True
        assert response.session_id == "test-session"
        assert response.operation == "stop-session"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to stop session"


class TestStatementResponseModels:
    """Tests for the statement response models."""

    def test_run_statement_response(self):
        """Test creating a RunStatementResponse."""
        response = RunStatementResponse(
            isError=False,
            session_id="test-session",
            statement_id=1,
            content=[TextContent(type="text", text="Successfully ran statement")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert response.statement_id == 1
        assert response.operation == "run-statement"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully ran statement"

    def test_run_statement_response_with_error(self):
        """Test creating a RunStatementResponse with error."""
        response = RunStatementResponse(
            isError=True,
            session_id="test-session",
            statement_id=0,
            content=[TextContent(type="text", text="Failed to run statement")],
        )
        
        assert response.isError is True
        assert response.session_id == "test-session"
        assert response.statement_id == 0
        assert response.operation == "run-statement"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to run statement"

    def test_cancel_statement_response(self):
        """Test creating a CancelStatementResponse."""
        response = CancelStatementResponse(
            isError=False,
            session_id="test-session",
            statement_id=1,
            content=[TextContent(type="text", text="Successfully canceled statement")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert response.statement_id == 1
        assert response.operation == "cancel-statement"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully canceled statement"

    def test_cancel_statement_response_with_error(self):
        """Test creating a CancelStatementResponse with error."""
        response = CancelStatementResponse(
            isError=True,
            session_id="test-session",
            statement_id=1,
            content=[TextContent(type="text", text="Failed to cancel statement")],
        )
        
        assert response.isError is True
        assert response.session_id == "test-session"
        assert response.statement_id == 1
        assert response.operation == "cancel-statement"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to cancel statement"

    def test_get_statement_response(self):
        """Test creating a GetStatementResponse."""
        statement_details = {
            "Id": 1,
            "Code": "df = spark.read.csv('s3://bucket/data.csv')\ndf.show(5)",
            "State": "AVAILABLE",
            "Output": {
                "Status": "ok",
                "Data": {"text/plain": "+---+----+\n|id |name|\n+---+----+\n|1  |Alice|\n|2  |Bob  |\n+---+----+"}
            }
        }
        
        response = GetStatementResponse(
            isError=False,
            session_id="test-session",
            statement_id=1,
            statement=statement_details,
            content=[TextContent(type="text", text="Successfully retrieved statement")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert response.statement_id == 1
        assert response.statement == statement_details
        assert response.operation == "get-statement"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully retrieved statement"

    def test_get_statement_response_with_error(self):
        """Test creating a GetStatementResponse with error."""
        response = GetStatementResponse(
            isError=True,
            session_id="test-session",
            statement_id=1,
            statement={},
            content=[TextContent(type="text", text="Failed to retrieve statement")],
        )
        
        assert response.isError is True
        assert response.session_id == "test-session"
        assert response.statement_id == 1
        assert response.statement == {}
        assert response.operation == "get-statement"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to retrieve statement"

    def test_list_statements_response(self):
        """Test creating a ListStatementsResponse."""
        statements = [
            {
                "Id": 1,
                "State": "AVAILABLE",
                "Code": "df = spark.read.csv('s3://bucket/data.csv')"
            },
            {
                "Id": 2,
                "State": "RUNNING",
                "Code": "df.show(5)"
            }
        ]
        
        response = ListStatementsResponse(
            isError=False,
            session_id="test-session",
            statements=statements,
            count=2,
            next_token="next-token",
            content=[TextContent(type="text", text="Successfully listed statements")],
        )
        
        assert response.isError is False
        assert response.session_id == "test-session"
        assert len(response.statements) == 2
        assert response.statements[0]["Id"] == 1
        assert response.statements[1]["Id"] == 2
        assert response.count == 2
        assert response.next_token == "next-token"
        assert response.operation == "list-statements"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully listed statements"

    def test_list_statements_response_with_error(self):
        """Test creating a ListStatementsResponse with error."""
        response = ListStatementsResponse(
            isError=True,
            session_id="test-session",
            statements=[],
            count=0,
            content=[TextContent(type="text", text="Failed to list statements")],
        )
        
        assert response.isError is True
        assert response.session_id == "test-session"
        assert len(response.statements) == 0
        assert response.count == 0
        assert response.next_token is None  # Default value
        assert response.operation == "list-statements"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to list statements"


class TestValidationErrors:
    """Tests for validation errors in the models."""

    def test_create_session_response_missing_required_fields(self):
        """Test that creating a CreateSessionResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            CreateSessionResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id")]
            )

    def test_delete_session_response_missing_required_fields(self):
        """Test that creating a DeleteSessionResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            DeleteSessionResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id")]
            )

    def test_get_session_response_missing_required_fields(self):
        """Test that creating a GetSessionResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            GetSessionResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id")]
            )

    def test_list_sessions_response_missing_required_fields(self):
        """Test that creating a ListSessionsResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            ListSessionsResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing sessions and count")]
            )

    def test_stop_session_response_missing_required_fields(self):
        """Test that creating a StopSessionResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            StopSessionResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id")]
            )

    def test_run_statement_response_missing_required_fields(self):
        """Test that creating a RunStatementResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            RunStatementResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id and statement_id")]
            )

        with pytest.raises(ValidationError):
            RunStatementResponse(
                isError=False,
                session_id="test-session",
                content=[TextContent(type="text", text="Missing statement_id")]
            )

    def test_cancel_statement_response_missing_required_fields(self):
        """Test that creating a CancelStatementResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            CancelStatementResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id and statement_id")]
            )

        with pytest.raises(ValidationError):
            CancelStatementResponse(
                isError=False,
                session_id="test-session",
                content=[TextContent(type="text", text="Missing statement_id")]
            )

    def test_get_statement_response_missing_required_fields(self):
        """Test that creating a GetStatementResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            GetStatementResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id and statement_id")]
            )

        with pytest.raises(ValidationError):
            GetStatementResponse(
                isError=False,
                session_id="test-session",
                content=[TextContent(type="text", text="Missing statement_id")]
            )

    def test_list_statements_response_missing_required_fields(self):
        """Test that creating a ListStatementsResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            ListStatementsResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing session_id, statements, and count")]
            )

        with pytest.raises(ValidationError):
            ListStatementsResponse(
                isError=False,
                session_id="test-session",
                content=[TextContent(type="text", text="Missing statements and count")]
            )
