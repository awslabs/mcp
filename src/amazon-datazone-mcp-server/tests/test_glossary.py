"""
Unit tests for glossary tools.
"""

from unittest.mock import Mock

import pytest


class TestGlossary:
    """Test cases for glossary tools."""

    @pytest.mark.asyncio
    async def test_create_glossary_success(
        self, mcp_server_with_tools, tool_extractor, sample_glossary_data
    ):
        """Test successful glossary creation."""
        # Get the tool function from the MCP server
        create_glossary = tool_extractor(mcp_server_with_tools, "create_glossary")

        # Arrange
        expected_response = {
            "id": "glossary_new123",
            "name": sample_glossary_data["name"],
            "description": sample_glossary_data["description"],
            "domainId": sample_glossary_data["domain_identifier"],
            "owningProjectId": sample_glossary_data["owning_project_identifier"],
            "status": "ENABLED",
        }
        mcp_server_with_tools._mock_client.create_glossary.return_value = expected_response

        # Act
        result = await create_glossary(
            domain_identifier=sample_glossary_data["domain_identifier"],
            name=sample_glossary_data["name"],
            owning_project_identifier=sample_glossary_data["owning_project_identifier"],
            description=sample_glossary_data["description"],
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_glossary.assert_called_once_with(
            domainIdentifier=sample_glossary_data["domain_identifier"],
            name=sample_glossary_data["name"],
            owningProjectIdentifier=sample_glossary_data["owning_project_identifier"],
            status="ENABLED",
            description=sample_glossary_data["description"],
        )

    @pytest.mark.asyncio
    async def test_create_glossary_term_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful glossary term creation."""
        # Get the tool function from the MCP server
        create_glossary_term = tool_extractor(mcp_server_with_tools, "create_glossary_term")

        # Arrange
        domain_id = "dzd_test123"
        glossary_id = "glossary_test123"
        term_name = "Customer"
        short_description = "A person who purchases products"
        long_description = "A detailed description of a customer entity"

        expected_response = {
            "id": "term_new123",
            "name": term_name,
            "shortDescription": short_description,
            "longDescription": long_description,
            "domainId": domain_id,
            "glossaryId": glossary_id,
            "status": "ENABLED",
        }
        mcp_server_with_tools._mock_client.create_glossary_term.return_value = expected_response

        # Act
        result = await create_glossary_term(
            domain_identifier=domain_id,
            glossary_identifier=glossary_id,
            name=term_name,
            short_description=short_description,
            long_description=long_description,
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_glossary_term.assert_called_once_with(
            domainIdentifier=domain_id,
            glossaryIdentifier=glossary_id,
            name=term_name,
            status="ENABLED",
            shortDescription=short_description,
            longDescription=long_description,
        )

    @pytest.mark.asyncio
    async def test_get_glossary_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful glossary retrieval."""
        # Get the tool function from the MCP server
        get_glossary = tool_extractor(mcp_server_with_tools, "get_glossary")

        # Arrange
        domain_id = "dzd_test123"
        glossary_id = "glossary_test123"
        expected_response = {
            "id": glossary_id,
            "name": "Test Glossary",
            "description": "Test glossary description",
            "domainId": domain_id,
            "status": "ENABLED",
            "createdAt": 1234567890,
        }
        mcp_server_with_tools._mock_client.get_glossary.return_value = expected_response

        # Act
        result = await get_glossary(domain_id, glossary_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_glossary.assert_called_once_with(
            domainIdentifier=domain_id, identifier=glossary_id
        )

    @pytest.mark.asyncio
    async def test_get_glossary_term_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful glossary term retrieval."""
        # Get the tool function from the MCP server
        get_glossary_term = tool_extractor(mcp_server_with_tools, "get_glossary_term")

        # Arrange
        domain_id = "dzd_test123"
        term_id = "term_test123"
        expected_response = {
            "id": term_id,
            "name": "Customer",
            "shortDescription": "A person who purchases products",
            "domainId": domain_id,
            "glossaryId": "glossary_test123",
            "status": "ENABLED",
        }
        mcp_server_with_tools._mock_client.get_glossary_term.return_value = expected_response

        # Act
        result = await get_glossary_term(domain_id, term_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_glossary_term.assert_called_once_with(
            domainIdentifier=domain_id, identifier=term_id
        )

    @pytest.mark.asyncio
    async def test_create_glossary_access_denied(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test glossary creation with access denied error."""
        # Get the tool function from the MCP server
        create_glossary = tool_extractor(mcp_server_with_tools, "create_glossary")

        # Arrange
        domain_id = "dzd_test123"
        glossary_name = "Denied Glossary"
        mcp_server_with_tools._mock_client.create_glossary.side_effect = mock_client_error(
            "AccessDeniedException", "Insufficient permissions"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_glossary(
                domain_identifier=domain_id,
                name=glossary_name,
                owning_project_identifier="prj_test123",
            )

        assert f"Error creating glossary in domain {domain_id}" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_glossary_not_found(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test glossary retrieval when glossary doesn't exist."""
        # Get the tool function from the MCP server
        get_glossary = tool_extractor(mcp_server_with_tools, "get_glossary")

        # Arrange
        domain_id = "dzd_test123"
        glossary_id = "glossary_nonexistent"
        mcp_server_with_tools._mock_client.get_glossary.side_effect = mock_client_error(
            "ResourceNotFoundException", "Glossary not found"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await get_glossary(domain_id, glossary_id)

        assert f"Error getting glossary {glossary_id} in domain {domain_id}" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_glossary_term_conflict(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test glossary term creation when term already exists."""
        # Get the tool function from the MCP server
        create_glossary_term = tool_extractor(mcp_server_with_tools, "create_glossary_term")

        # Arrange
        domain_id = "dzd_test123"
        glossary_id = "glossary_test123"
        term_name = "Existing Term"
        mcp_server_with_tools._mock_client.create_glossary_term.side_effect = mock_client_error(
            "ConflictException", "Term already exists"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_glossary_term(
                domain_identifier=domain_id,
                glossary_identifier=glossary_id,
                name=term_name,
                short_description="Short desc",
            )

        assert f"Error creating glossary term in domain {domain_id}" in str(exc_info.value)

    def test_register_tools(self, mock_fastmcp):
        """Test that tools are properly registered with FastMCP."""
        # Import here to avoid circular import issues
        from awslabs.datazone_mcp_server.tools import glossary

        # Act
        glossary.register_tools(mock_fastmcp)

        # Assert
        assert mock_fastmcp.tool.call_count > 0


class TestGlossaryParameterValidation:
    """Test parameter validation for glossary tools."""

    @pytest.mark.asyncio
    async def test_create_glossary_with_optional_params(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_glossary with optional parameters."""
        # Get the tool function from the MCP server
        create_glossary = tool_extractor(mcp_server_with_tools, "create_glossary")

        # Arrange
        mcp_server_with_tools._mock_client.create_glossary.return_value = {
            "id": "glossary_full123",
            "name": "Full Glossary",
            "status": "ENABLED",
        }

        # Act
        await create_glossary(
            domain_identifier="dzd_test123",
            name="Full Glossary",
            owning_project_identifier="prj_test123",
            description="Full description",
            status="ENABLED",
            client_token="token_123",
        )

        # Assert
        mcp_server_with_tools._mock_client.create_glossary.assert_called_once_with(
            domainIdentifier="dzd_test123",
            name="Full Glossary",
            owningProjectIdentifier="prj_test123",
            description="Full description",
            status="ENABLED",
            clientToken="token_123",
        )

    @pytest.mark.asyncio
    async def test_create_glossary_term_with_optional_params(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_glossary_term with optional parameters."""
        # Get the tool function from the MCP server
        create_glossary_term = tool_extractor(mcp_server_with_tools, "create_glossary_term")

        # Arrange
        mcp_server_with_tools._mock_client.create_glossary_term.return_value = {
            "id": "term_full123",
            "name": "Full Term",
            "status": "ENABLED",
        }

        # Act
        await create_glossary_term(
            domain_identifier="dzd_test123",
            glossary_identifier="glossary_test123",
            name="Full Term",
            short_description="Short description",
            long_description="Long description",
            term_relations=[{"classifies": ["asset_123"]}],
            status="ENABLED",
            client_token="token_123",
        )

        # Assert
        mcp_server_with_tools._mock_client.create_glossary_term.assert_called_once_with(
            domainIdentifier="dzd_test123",
            glossaryIdentifier="glossary_test123",
            name="Full Term",
            status="ENABLED",
            shortDescription="Short description",
            longDescription="Long description",
            termRelations=[{"classifies": ["asset_123"]}],
            clientToken="token_123",
        )
