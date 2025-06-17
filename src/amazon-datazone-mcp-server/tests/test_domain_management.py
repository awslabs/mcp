"""Tests for domain management tools."""

from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError


class TestDomainManagement:
    """Test domain management functionality."""

    @pytest.mark.asyncio
    async def test_get_domain_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain retrieval."""
        # Get the tool function from the MCP server
        get_domain = tool_extractor(mcp_server_with_tools, "get_domain")

        domain_id = test_data_helper.get_domain_id()
        result = await get_domain(domain_id)

        # Verify the result
        assert result is not None
        assert result["id"] == domain_id
        assert result["name"] == "Test Domain"
        assert result["status"] == "AVAILABLE"

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.get_domain.assert_called_once_with(identifier=domain_id)

    @pytest.mark.asyncio
    async def test_get_domain_not_found(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test domain not found error handling."""
        # Configure mock to raise ResourceNotFoundException
        error = client_error_helper("ResourceNotFoundException", "Domain not found")
        mcp_server_with_tools._mock_client.get_domain.side_effect = error

        get_domain = tool_extractor(mcp_server_with_tools, "get_domain")

        domain_id = "dzd_nonexistent"
        with pytest.raises(Exception) as exc_info:
            await get_domain(domain_id)

        assert "Error getting domain dzd_nonexistent" in str(exc_info.value)

    # @pytest.mark.asyncio
    # async def test_create_domain_success(
    #     self, mcp_server_with_tools, tool_extractor, sample_domain_data
    # ):
    #     """Test successful domain creation."""
    #     create_domain = tool_extractor(mcp_server_with_tools, "create_domain")

    #     result = await create_domain(
    #         name=sample_domain_data["name"],
    #         domain_execution_role=sample_domain_data["domain_execution_role"],
    #         service_role=sample_domain_data["service_role"],
    #         domain_version=sample_domain_data["domain_version"],
    #         description=sample_domain_data["description"],
    #     )

    #     # Verify the result
    #     assert result is not None
    #     assert result["name"] == "New Test Domain"
    #     assert result["status"] == "CREATING"
    #     assert "id" in result
    #     assert "arn" in result

    #     # Verify the mock was called correctly
    #     mcp_server_with_tools._mock_client.create_domain.assert_called_once()
    #     call_args = mcp_server_with_tools._mock_client.create_domain.call_args[1]
    #     assert call_args["name"] == sample_domain_data["name"]
    #     assert call_args["domainExecutionRole"] == sample_domain_data["domain_execution_role"]
    #     assert call_args["serviceRole"] == sample_domain_data["service_role"]

    @pytest.mark.asyncio
    async def test_create_domain_conflict(
        self, mcp_server_with_tools, tool_extractor, sample_domain_data, client_error_helper
    ):
        """Test domain creation conflict error."""
        # Configure mock to raise ConflictException
        error = client_error_helper("ConflictException", "Domain already exists")
        mcp_server_with_tools._mock_client.create_domain.side_effect = error

        create_domain = tool_extractor(mcp_server_with_tools, "create_domain")

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name=sample_domain_data["name"],
                domain_execution_role=sample_domain_data["domain_execution_role"],
                service_role=sample_domain_data["service_role"],
            )

        assert f"Domain {sample_domain_data['name']} already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_access_denied(
        self, mcp_server_with_tools, tool_extractor, sample_domain_data, client_error_helper
    ):
        """Test domain creation access denied error."""
        # Configure mock to raise AccessDeniedException
        error = client_error_helper("AccessDeniedException", "Access denied")
        mcp_server_with_tools._mock_client.create_domain.side_effect = error

        create_domain = tool_extractor(mcp_server_with_tools, "create_domain")

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name=sample_domain_data["name"],
                domain_execution_role=sample_domain_data["domain_execution_role"],
                service_role=sample_domain_data["service_role"],
            )

        assert f"Access denied while creating domain {sample_domain_data['name']}" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_list_domain_units_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain units listing."""
        # Configure mock response
        mcp_server_with_tools._mock_client.list_domain_units_for_parent.return_value = {
            "items": [
                {
                    "id": "unit_123",
                    "name": "Test Unit",
                    "description": "Test domain unit",
                    "domainId": "dzd_test123",
                    "parentDomainUnitId": "parent_unit_123",
                }
            ]
        }

        list_domain_units = tool_extractor(mcp_server_with_tools, "list_domain_units")

        domain_id = test_data_helper.get_domain_id()
        parent_unit_id = "parent_unit_123"
        result = await list_domain_units(domain_id, parent_unit_id)

        # Verify the result
        assert result is not None
        assert "items" in result
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == "unit_123"

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.list_domain_units_for_parent.assert_called_once_with(
            domainIdentifier=domain_id, parentDomainUnitIdentifier=parent_unit_id
        )

    @pytest.mark.asyncio
    async def test_create_domain_unit_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain unit creation."""
        # Configure mock response
        mcp_server_with_tools._mock_client.create_domain_unit.return_value = {
            "id": "unit_new123",
            "name": "New Test Unit",
            "description": "New test domain unit",
            "domainId": "dzd_test123",
            "parentDomainUnitId": "parent_unit_123",
        }

        create_domain_unit = tool_extractor(mcp_server_with_tools, "create_domain_unit")

        domain_id = test_data_helper.get_domain_id()
        unit_name = "New Test Unit"
        parent_unit_id = "parent_unit_123"
        description = "New test domain unit"

        result = await create_domain_unit(
            domain_identifier=domain_id,
            name=unit_name,
            parent_domain_unit_identifier=parent_unit_id,
            description=description,
        )

        # Verify the result
        assert result is not None
        assert result["name"] == unit_name
        assert result["description"] == description
        assert "id" in result

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.create_domain_unit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_domain_unit_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain unit retrieval."""
        # Configure mock response
        mcp_server_with_tools._mock_client.get_domain_unit.return_value = {
            "id": "unit_test123",
            "name": "Test Unit",
            "description": "Test domain unit",
            "domainId": "dzd_test123",
            "parentDomainUnitId": "parent_unit_123",
        }

        get_domain_unit = tool_extractor(mcp_server_with_tools, "get_domain_unit")

        domain_id = test_data_helper.get_domain_id()
        unit_id = "unit_test123"
        result = await get_domain_unit(domain_id, unit_id)

        # Verify the result
        assert result is not None
        assert result["id"] == unit_id
        assert result["name"] == "Test Unit"

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.get_domain_unit.assert_called_once_with(
            domainIdentifier=domain_id, identifier=unit_id
        )

    @pytest.mark.asyncio
    async def test_search_success(self, mcp_server_with_tools, tool_extractor, test_data_helper):
        """Test successful search operation."""
        # Configure mock response
        mcp_server_with_tools._mock_client.search.return_value = {
            "items": [
                {
                    "id": "search_result_123",
                    "name": "Search Result",
                    "description": "Test search result",
                    "assetType": "amazon.datazone.S3Asset",
                }
            ],
            "totalMatchCount": 1,
        }

        search = tool_extractor(mcp_server_with_tools, "search")

        domain_id = test_data_helper.get_domain_id()
        search_scope = "ASSET"
        search_text = "test"

        result = await search(
            domain_identifier=domain_id, search_scope=search_scope, search_text=search_text
        )

        # Verify the result
        assert result is not None
        assert "items" in result
        assert len(result["items"]) == 1
        assert result["totalMatchCount"] == 1

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_policy_grant_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful policy grant addition."""
        # Configure mock response
        mcp_server_with_tools._mock_client.add_policy_grant.return_value = {
            "policyType": "OVERRIDE_DOMAIN_UNIT_OWNERS",
            "principal": {"domainUnitId": "unit_123", "domainUnitDesignation": "OWNER"},
        }

        add_policy_grant = tool_extractor(mcp_server_with_tools, "add_policy_grant")

        domain_id = test_data_helper.get_domain_id()
        entity_id = "unit_123"
        entity_type = "DOMAIN_UNIT"
        policy_type = "OVERRIDE_DOMAIN_UNIT_OWNERS"
        principal_id = "user_123"

        result = await add_policy_grant(
            domain_identifier=domain_id,
            entity_identifier=entity_id,
            entity_type=entity_type,
            policy_type=policy_type,
            principal_identifier=principal_id,
        )

        # Verify the result
        assert result is not None
        assert result["policyType"] == policy_type

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.add_policy_grant.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_generic_error(
        self, mcp_server_with_tools, tool_extractor, test_data_helper, client_error_helper
    ):
        """Test generic error handling."""
        # Configure mock to raise a generic error
        error = client_error_helper("InternalServerException", "Internal server error")
        mcp_server_with_tools._mock_client.get_domain.side_effect = error

        get_domain = tool_extractor(mcp_server_with_tools, "get_domain")

        domain_id = test_data_helper.get_domain_id()
        with pytest.raises(Exception) as exc_info:
            await get_domain(domain_id)

        assert "Error getting domain dzd_test123" in str(exc_info.value)


class TestDomainManagementParameterValidation:
    """Test parameter validation for domain management tools."""

    @pytest.mark.asyncio
    async def test_search_with_all_parameters(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test search with all optional parameters."""
        # Configure mock response
        mcp_server_with_tools._mock_client.search.return_value = {"items": [], "totalMatchCount": 0}

        search = tool_extractor(mcp_server_with_tools, "search")

        domain_id = test_data_helper.get_domain_id()

        # Test with all parameters
        await search(
            domain_identifier=domain_id,
            search_scope="ASSET",
            additional_attributes=["BUSINESS_NAME"],
            filters={"assetType": "amazon.datazone.S3Asset"},
            max_results=25,
            next_token="token123",
            owning_project_identifier="prj_test123",
            search_in=[{"attribute": "name"}],
            search_text="test query",
            sort={"attribute": "name", "order": "asc"},
        )

        # Verify the mock was called with all parameters
        mcp_server_with_tools._mock_client.search.assert_called_once()
        call_args = mcp_server_with_tools._mock_client.search.call_args[1]
        assert call_args["domainIdentifier"] == domain_id
        assert call_args["searchScope"] == "ASSET"
        assert call_args["additionalAttributes"] == ["BUSINESS_NAME"]
        assert call_args["maxResults"] == 25
