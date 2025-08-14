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

"""Comprehensive model validation tests following AWS Labs patterns."""

import json
from datetime import datetime

import pytest

from awslabs.cloudwan_mcp_server.server import (
    ContentItem,
    DateTimeEncoder,
    McpResponse,
    safe_json_dumps,
)


class TestContentItemModel:
    """Test ContentItem TypedDict model validation following AWS Labs patterns."""

    @pytest.mark.unit
    def test_content_item_valid_creation(self) -> None:
        """Test valid ContentItem creation with required fields."""
        content_item = ContentItem(type="text", text="Test content")

        assert content_item["type"] == "text"
        assert content_item["text"] == "Test content"
        assert len(content_item) == 2

    @pytest.mark.unit
    def test_content_item_types(self) -> None:
        """Test ContentItem with different valid types."""
        valid_types = ["text", "error", "warning", "info", "json"]

        for content_type in valid_types:
            content_item = ContentItem(type=content_type, text=f"Content for {content_type}")
            assert content_item["type"] == content_type
            assert isinstance(content_item["text"], str)

    @pytest.mark.unit
    def test_content_item_empty_text(self) -> None:
        """Test ContentItem with empty text (should be valid)."""
        content_item = ContentItem(type="text", text="")
        assert content_item["type"] == "text"
        assert content_item["text"] == ""

    @pytest.mark.unit
    def test_content_item_with_json_text(self) -> None:
        """Test ContentItem with JSON string text."""
        json_text = json.dumps({"key": "value", "number": 42})
        content_item = ContentItem(type="json", text=json_text)

        assert content_item["type"] == "json"
        assert content_item["text"] == json_text
        # Verify text is valid JSON
        parsed = json.loads(content_item["text"])
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    @pytest.mark.unit
    def test_content_item_with_multiline_text(self) -> None:
        """Test ContentItem with multiline text content."""
        multiline_text = """This is line 1
This is line 2
This is line 3 with special chars: !@#$%^&*()"""

        content_item = ContentItem(type="text", text=multiline_text)
        assert content_item["type"] == "text"
        assert content_item["text"] == multiline_text
        assert "\n" in content_item["text"]


class TestMcpResponseModel:
    """Test McpResponse TypedDict model validation following AWS Labs patterns."""

    @pytest.mark.unit
    def test_mcp_response_required_content(self) -> None:
        """Test McpResponse with required content field."""
        content = [ContentItem(type="text", text="Response content")]
        response = McpResponse(content=content)

        assert "content" in response
        assert len(response["content"]) == 1
        assert response["content"][0]["type"] == "text"
        assert response["content"][0]["text"] == "Response content"

    @pytest.mark.unit
    def test_mcp_response_with_error_flag(self) -> None:
        """Test McpResponse with optional isError field."""
        content = [ContentItem(type="error", text="Error occurred")]
        response = McpResponse(content=content, isError=True)

        assert response["content"][0]["type"] == "error"
        assert response["isError"] is True

    @pytest.mark.unit
    def test_mcp_response_without_error_flag(self) -> None:
        """Test McpResponse without optional isError field (total=False)."""
        content = [ContentItem(type="text", text="Success response")]
        response = McpResponse(content=content)

        # isError should not be present when not specified
        assert "content" in response
        assert "isError" not in response or response.get("isError") is False

    @pytest.mark.unit
    def test_mcp_response_multiple_content_items(self) -> None:
        """Test McpResponse with multiple content items."""
        content = [
            ContentItem(type="text", text="First item"),
            ContentItem(type="json", text='{"key": "value"}'),
            ContentItem(type="warning", text="Warning message"),
        ]
        response = McpResponse(content=content)

        assert len(response["content"]) == 3
        assert response["content"][0]["type"] == "text"
        assert response["content"][1]["type"] == "json"
        assert response["content"][2]["type"] == "warning"

    @pytest.mark.unit
    def test_mcp_response_empty_content_list(self) -> None:
        """Test McpResponse with empty content list."""
        response = McpResponse(content=[])
        assert "content" in response
        assert len(response["content"]) == 0

    @pytest.mark.unit
    def test_mcp_response_error_scenario(self) -> None:
        """Test McpResponse for error scenarios following AWS Labs patterns."""
        error_content = [
            ContentItem(type="error", text="AWS API call failed"),
            ContentItem(type="text", text="Additional error details"),
        ]
        response = McpResponse(content=error_content, isError=True)

        assert response["isError"] is True
        assert len(response["content"]) == 2
        assert response["content"][0]["type"] == "error"

    @pytest.mark.unit
    def test_mcp_response_datetime_serialization(self) -> None:
        """Test McpResponse handles datetime objects in content items."""
        dt_content = ContentItem(type="text", text=datetime(2024, 1, 1).isoformat())
        response = McpResponse(content=[dt_content])
        result = safe_json_dumps(response)
        assert '"text": "2024-01-01T00:00:00"' in result


class TestDateTimeEncoder:
    """Test DateTimeEncoder for JSON serialization following AWS Labs patterns."""

    @pytest.mark.unit
    def test_datetime_encoding(self) -> None:
        """Test DateTimeEncoder handles datetime objects correctly."""
        encoder = DateTimeEncoder()
        test_datetime = datetime(2024, 1, 15, 10, 30, 45)

        result = encoder.default(test_datetime)
        assert result == "2024-01-15T10:30:45"
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_datetime_encoding_with_microseconds(self) -> None:
        """Test DateTimeEncoder handles datetime with microseconds."""
        encoder = DateTimeEncoder()
        test_datetime = datetime(2024, 1, 15, 10, 30, 45, 123456)

        result = encoder.default(test_datetime)
        assert result == "2024-01-15T10:30:45.123456"
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_non_datetime_objects(self) -> None:
        """Test DateTimeEncoder passes non-datetime objects to parent."""
        encoder = DateTimeEncoder()

        # Should raise TypeError for unsupported types
        with pytest.raises(TypeError):
            encoder.default(object())

    @pytest.mark.unit
    def test_datetime_encoder_in_json_dumps(self) -> None:
        """Test DateTimeEncoder integration with json.dumps."""
        test_data = {"timestamp": datetime(2024, 1, 15, 10, 30, 45), "message": "Test message", "count": 42}

        result = json.dumps(test_data, cls=DateTimeEncoder)
        parsed = json.loads(result)

        assert parsed["timestamp"] == "2024-01-15T10:30:45"
        assert parsed["message"] == "Test message"
        assert parsed["count"] == 42


class TestSafeJsonDumps:
    """Test safe_json_dumps function following AWS Labs patterns."""

    @pytest.mark.unit
    def test_safe_json_dumps_with_datetime(self) -> None:
        """Test safe_json_dumps handles datetime objects correctly."""
        test_data = {"created_at": datetime(2024, 1, 15, 10, 30, 45), "name": "Test Resource", "active": True}

        result = safe_json_dumps(test_data)
        parsed = json.loads(result)

        assert parsed["created_at"] == "2024-01-15T10:30:45"
        assert parsed["name"] == "Test Resource"
        assert parsed["active"] is True

    @pytest.mark.unit
    def test_safe_json_dumps_with_indent(self) -> None:
        """Test safe_json_dumps with formatting options."""
        test_data = {"key": "value", "timestamp": datetime(2024, 1, 15, 10, 30, 45)}

        result = safe_json_dumps(test_data, indent=2)

        # Verify formatting
        assert "\n" in result
        assert '  "key": "value"' in result
        assert '  "timestamp": "2024-01-15T10:30:45"' in result

    @pytest.mark.unit
    def test_safe_json_dumps_complex_structure(self) -> None:
        """Test safe_json_dumps with complex nested structure."""
        test_data = {
            "core_networks": [
                {
                    "id": "core-network-123",
                    "created_at": datetime(2024, 1, 15, 10, 30, 45),
                    "segments": ["prod", "dev"],
                },
                {"id": "core-network-456", "created_at": datetime(2024, 1, 16, 11, 45, 30), "segments": ["staging"]},
            ],
            "total_count": 2,
        }

        result = safe_json_dumps(test_data)
        parsed = json.loads(result)

        assert len(parsed["core_networks"]) == 2
        assert parsed["core_networks"][0]["created_at"] == "2024-01-15T10:30:45"
        assert parsed["core_networks"][1]["created_at"] == "2024-01-16T11:45:30"
        assert parsed["total_count"] == 2

    @pytest.mark.unit
    def test_safe_json_dumps_empty_objects(self) -> None:
        """Test safe_json_dumps with empty objects and lists."""
        test_data = {
            "empty_dict": {},
            "empty_list": [],
            "null_value": None,
            "timestamp": datetime(2024, 1, 15, 10, 30, 45),
        }

        result = safe_json_dumps(test_data)
        parsed = json.loads(result)

        assert parsed["empty_dict"] == {}
        assert parsed["empty_list"] == []
        assert parsed["null_value"] is None
        assert parsed["timestamp"] == "2024-01-15T10:30:45"


class TestAWSLabsResponseFormats:
    """Test AWS Labs standard response format patterns."""

    @pytest.mark.unit
    def test_success_response_format(self) -> None:
        """Test standard AWS Labs success response format."""
        success_data = {
            "success": True,
            "data": {"resource_id": "test-123", "status": "active"},
            "timestamp": datetime(2024, 1, 15, 10, 30, 45),
        }

        json_result = safe_json_dumps(success_data, indent=2)
        parsed = json.loads(json_result)

        assert parsed["success"] is True
        assert "data" in parsed
        assert parsed["data"]["resource_id"] == "test-123"
        assert parsed["timestamp"] == "2024-01-15T10:30:45"

    @pytest.mark.unit
    def test_error_response_format(self) -> None:
        """Test standard AWS Labs error response format."""
        error_data = {
            "success": False,
            "error": "Resource not found",
            "error_code": "ResourceNotFound",
            "timestamp": datetime(2024, 1, 15, 10, 30, 45),
        }

        json_result = safe_json_dumps(error_data, indent=2)
        parsed = json.loads(json_result)

        assert parsed["success"] is False
        assert parsed["error"] == "Resource not found"
        assert parsed["error_code"] == "ResourceNotFound"
        assert parsed["timestamp"] == "2024-01-15T10:30:45"

    @pytest.mark.unit
    def test_mcp_content_response_integration(self) -> None:
        """Test integration between MCP response models and JSON serialization."""
        # Create AWS Labs style data
        aws_data = {
            "CoreNetworks": [
                {
                    "CoreNetworkId": "core-network-123",
                    "CreatedAt": datetime(2024, 1, 15, 10, 30, 45),
                    "State": "AVAILABLE",
                }
            ]
        }

        # Convert to JSON string for ContentItem
        json_content = safe_json_dumps(aws_data, indent=2)

        # Create MCP response
        content_item = ContentItem(type="json", text=json_content)
        mcp_response = McpResponse(content=[content_item])

        # Verify structure
        assert len(mcp_response["content"]) == 1
        assert mcp_response["content"][0]["type"] == "json"

        # Verify JSON content can be parsed
        parsed_content = json.loads(mcp_response["content"][0]["text"])
        assert len(parsed_content["CoreNetworks"]) == 1
        assert parsed_content["CoreNetworks"][0]["CoreNetworkId"] == "core-network-123"
        assert parsed_content["CoreNetworks"][0]["CreatedAt"] == "2024-01-15T10:30:45"

    @pytest.mark.unit
    def test_validation_error_patterns(self) -> None:
        """Test validation error response patterns following AWS Labs standards."""
        validation_errors = ["Missing required field", "Invalid CIDR format"]
        error_response = {
            "success": False,
            "error": "Validation failed",
            "error_code": "ValidationError",  # Ensure present
            "validation_errors": validation_errors,
        }
        json_result = safe_json_dumps(error_response, indent=2)
        parsed = json.loads(json_result)

        assert parsed["error_code"] == "ValidationError"
        assert len(parsed["validation_errors"]) == 2
