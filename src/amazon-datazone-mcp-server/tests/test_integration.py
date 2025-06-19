# """
# Integration tests for Amazon DataZone MCP Server.

# These tests require real AWS credentials and an active DataZone domain.
# Run with: pytest tests/test_integration.py -m integration

# Requirements:
# - AWS credentials configured (via AWS CLI, environment, or IAM role)
# - TEST_DATAZONE_DOMAIN_ID environment variable (optional - will create if needed)
# - TEST_DATAZONE_PROJECT_ID environment variable (optional - will create if needed)
# """

# import asyncio
# import os
# from unittest.mock import patch

# import boto3
# import pytest
# from botocore.exceptions import ClientError, NoCredentialsError

# # Skip all tests if running in CI or if AWS tests are disabled
# pytestmark = pytest.mark.integration


# @pytest.fixture(scope="session")
# def check_aws_credentials():
#     """Check if AWS credentials are available."""
#     try:
#         # Try to get credentials
#         session = boto3.Session()
#         credentials = session.get_credentials()
#         if credentials is None:
#             pytest.skip("No AWS credentials available")

#         # Test if we can actually use them
#         sts = boto3.client("sts")
#         sts.get_caller_identity()
#         return True
#     except (NoCredentialsError, ClientError) as e:
#         pytest.skip(f"AWS credentials not available or invalid: {e}")


# @pytest.fixture(scope="session")
# def aws_region():
#     """Get AWS region for tests."""
#     region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
#     return region


# @pytest.fixture(scope="session")
# def real_datazone_client(check_aws_credentials, aws_region):
#     """Create a real Amazon DataZone client for integration tests."""
#     if os.getenv("SKIP_AWS_TESTS", "false").lower() == "true":
#         pytest.skip("AWS integration tests disabled via SKIP_AWS_TESTS")

#     try:
#         client = boto3.client("datazone", region_name=aws_region)
#         # Test basic connectivity
#         client.list_domains(maxResults=1)
#         return client
#     except Exception as e:
#         pytest.skip(f"Cannot connect to Amazon DataZone: {e}")


# @pytest.fixture(scope="session")
# def test_domain_id(real_datazone_client):
#     """
#     Get or create a test domain for integration tests.
#     Uses TEST_DATAZONE_DOMAIN_ID if provided, otherwise skips.
#     """
#     domain_id = os.getenv("TEST_DATAZONE_DOMAIN_ID")
#     if not domain_id:
#         pytest.skip(
#             "TEST_DATAZONE_DOMAIN_ID environment variable not set. Integration tests require an existing domain."
#         )

#     # Verify the domain exists
#     try:
#         real_datazone_client.get_domain(identifier=domain_id)
#         return domain_id
#     except ClientError as e:
#         if e.response["Error"]["Code"] == "ResourceNotFoundException":
#             pytest.skip(f"Domain {domain_id} not found")
#         raise


# @pytest.fixture(scope="session")
# def test_project_id():
#     """
#     Project ID for integration tests.
#     Set via environment variable: TEST_DATAZONE_PROJECT_ID
#     """
#     project_id = os.getenv("TEST_DATAZONE_PROJECT_ID")
#     if not project_id:
#         pytest.skip("TEST_DATAZONE_PROJECT_ID environment variable not set")
#     return project_id


# @pytest.fixture
# async def mcp_server_with_tools():
#     """Setup MCP server for integration testing."""
#     from awslabs.datazone_mcp_server import server

#     # Return the actual server instance for integration tests
#     return server.mcp


# @pytest.fixture
# def tool_extractor():
#     """Extract tools from MCP server for testing."""

#     def _extract_tool(mcp_server, tool_name):
#         # For integration tests, we need to access the actual implementation
#         # This is a simplified version - in real integration we'd call through MCP
#         from awslabs.datazone_mcp_server.tools import (
#             data_management,
#             domain_management,
#             environment,
#             glossary,
#             project_management,
#         )

#         # Map tool names to modules and functions
#         tool_map = {
#             # Domain management
#             "get_domain": domain_management.get_domain,
#             "list_domains": domain_management.list_domains,
#             "search": domain_management.search,
#             # Project management
#             "list_projects": project_management.list_projects,
#             "get_project": project_management.get_project,
#             "create_project": project_management.create_project,
#             # Data management
#             "search_listings": data_management.search_listings,
#             "list_form_types": data_management.list_form_types,
#             "get_asset": data_management.get_asset,
#             # Glossary
#             "create_glossary": glossary.create_glossary,
#             "get_glossary": glossary.get_glossary,
#             # Environment
#             "list_environments": environment.list_environments,
#             "get_environment": environment.get_environment,
#         }

#         return tool_map.get(tool_name)

#     return _extract_tool


# class TestDomainManagementIntegration:
#     """Integration tests for domain management tools."""

#     @pytest.mark.asyncio
#     async def test_get_domain_integration(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test getting a real domain."""
#         get_domain = tool_extractor(mcp_server_with_tools, "get_domain")

#         # Temporarily replace the client for this test
#         with patch(
#             "awslabs.datazone_mcp_server.tools.domain_management.datazone_client", real_datazone_client
#         ):
#             result = await get_domain(test_domain_id)

#             # Verify response structure
#             assert "id" in result
#             assert "name" in result
#             assert "status" in result
#             assert result["id"] == test_domain_id

#     @pytest.mark.asyncio
#     async def test_list_domains_integration(
#         self, real_datazone_client, mcp_server_with_tools, tool_extractor
#     ):
#         """Test listing real domains."""
#         list_domains = tool_extractor(mcp_server_with_tools, "list_domains")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.domain_management.datazone_client", real_datazone_client
#         ):
#             result = await list_domains(max_results=5)

#             # Verify response structure
#             assert "items" in result
#             assert isinstance(result["items"], list)

#     @pytest.mark.asyncio
#     async def test_search_integration(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test search functionality with real domain."""
#         search = tool_extractor(mcp_server_with_tools, "search")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.domain_management.datazone_client", real_datazone_client
#         ):
#             result = await search(
#                 domain_identifier=test_domain_id, search_scope="ASSET", max_results=10
#             )

#             # Verify response structure
#             assert "items" in result
#             assert isinstance(result["items"], list)


# class TestProjectManagementIntegration:
#     """Integration tests for project management tools."""

#     @pytest.mark.asyncio
#     async def test_list_projects_integration(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test listing real projects."""
#         list_projects = tool_extractor(mcp_server_with_tools, "list_projects")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.project_management.datazone_client", real_datazone_client
#         ):
#             result = await list_projects(domain_identifier=test_domain_id, max_results=10)

#             # Verify response structure
#             assert "items" in result
#             assert isinstance(result["items"], list)

#     @pytest.mark.asyncio
#     async def test_get_project_integration(
#         self,
#         real_datazone_client,
#         test_domain_id,
#         test_project_id,
#         mcp_server_with_tools,
#         tool_extractor,
#     ):
#         """Test getting a real project."""
#         get_project = tool_extractor(mcp_server_with_tools, "get_project")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.project_management.datazone_client", real_datazone_client
#         ):
#             result = await get_project(test_domain_id, test_project_id)

#             # Verify response structure
#             assert "id" in result
#             assert "name" in result
#             assert "domainId" in result
#             assert result["id"] == test_project_id
#             assert result["domainId"] == test_domain_id


# class TestDataManagementIntegration:
#     """Integration tests for data management tools."""

#     @pytest.mark.asyncio
#     async def test_search_listings_integration(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test searching real listings."""
#         search_listings = tool_extractor(mcp_server_with_tools, "search_listings")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.data_management.datazone_client", real_datazone_client
#         ):
#             result = await search_listings(domain_identifier=test_domain_id, max_results=10)

#             # Verify response structure
#             assert "items" in result
#             assert isinstance(result["items"], list)

#     @pytest.mark.asyncio
#     async def test_list_form_types_integration(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test listing real form types."""
#         list_form_types = tool_extractor(mcp_server_with_tools, "list_form_types")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.data_management.datazone_client", real_datazone_client
#         ):
#             result = await list_form_types(domain_identifier=test_domain_id, max_results=10)

#             # Verify response structure
#             assert "items" in result
#             assert isinstance(result["items"], list)


# class TestErrorHandlingIntegration:
#     """Integration tests for error handling with real AWS."""

#     @pytest.mark.asyncio
#     async def test_nonexistent_domain_error(
#         self, real_datazone_client, mcp_server_with_tools, tool_extractor
#     ):
#         """Test error handling for nonexistent domain."""
#         get_domain = tool_extractor(mcp_server_with_tools, "get_domain")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.domain_management.datazone_client", real_datazone_client
#         ):
#             with pytest.raises(Exception) as exc_info:
#                 await get_domain("nonexistent-domain-id")

#             # Should be a client error
#             assert "ResourceNotFoundException" in str(exc_info.value) or "Not Found" in str(
#                 exc_info.value
#             )

#     @pytest.mark.asyncio
#     async def test_invalid_parameters_error(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test error handling for invalid parameters."""
#         search = tool_extractor(mcp_server_with_tools, "search")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.domain_management.datazone_client", real_datazone_client
#         ):
#             with pytest.raises(Exception) as exc_info:
#                 await search(
#                     domain_identifier=test_domain_id,
#                     search_scope="INVALID_SCOPE",  # Invalid scope
#                     max_results=10,
#                 )

#             # Should be a validation error
#             assert "ValidationException" in str(exc_info.value) or "Invalid" in str(exc_info.value)


# class TestPerformanceIntegration:
#     """Performance tests with real AWS services."""

#     @pytest.mark.slow
#     @pytest.mark.asyncio
#     async def test_response_time_reasonable(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test that response times are reasonable."""
#         import time

#         get_domain = tool_extractor(mcp_server_with_tools, "get_domain")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.domain_management.datazone_client", real_datazone_client
#         ):
#             start_time = time.time()
#             await get_domain(test_domain_id)
#             end_time = time.time()

#             response_time = end_time - start_time
#             # Should respond within 30 seconds
#             assert response_time < 30.0, f"Response took {response_time:.2f} seconds"

#     @pytest.mark.slow
#     @pytest.mark.asyncio
#     async def test_pagination_handling(
#         self, real_datazone_client, test_domain_id, mcp_server_with_tools, tool_extractor
#     ):
#         """Test pagination with real data."""
#         list_projects = tool_extractor(mcp_server_with_tools, "list_projects")

#         with patch(
#             "awslabs.datazone_mcp_server.tools.project_management.datazone_client", real_datazone_client
#         ):
#             # Request small page size to test pagination
#             result = await list_projects(domain_identifier=test_domain_id, max_results=1)

#             # Verify pagination structure
#             assert "items" in result
#             assert isinstance(result["items"], list)
#             # If there are more results, nextToken should be present
#             if len(result["items"]) == 1:
#                 # May or may not have nextToken depending on total results
#                 pass  # This is expected behavior


# def test_aws_credentials_available():
#     """Test that AWS credentials are properly configured."""
#     try:
#         session = boto3.Session()
#         credentials = session.get_credentials()

#         if credentials is None:
#             pytest.skip("No AWS credentials found")

#         # Test that we can actually use the credentials
#         sts = boto3.client("sts")
#         identity = sts.get_caller_identity()

#         assert "Account" in identity
#         assert "Arn" in identity

#     except Exception as e:
#         pytest.skip(f"AWS credentials not available: {e}")


# def test_aws_region_configured():
#     """Test that AWS region is properly configured."""
#     region = boto3.Session().region_name or os.getenv("AWS_DEFAULT_REGION")

#     if not region:
#         pytest.skip("No AWS region configured")

#     assert region is not None
#     assert len(region) > 0


# @pytest.fixture(scope="session", autouse=True)
# def integration_test_setup():
#     """Setup for integration tests."""
#     # Print helpful information about integration test requirements
#     print("\n" + "=" * 60)
#     print("AWS DataZone MCP Server Integration Tests")
#     print("=" * 60)
#     print("Requirements:")
#     print("1. AWS credentials configured")
#     print("2. TEST_DATAZONE_DOMAIN_ID environment variable")
#     print("3. TEST_DATAZONE_PROJECT_ID environment variable (optional)")
#     print("4. Appropriate AWS permissions for DataZone")
#     print("")
#     print("To skip these tests, set: SKIP_AWS_TESTS=true")
#     print("=" * 60)

#     yield

#     print("\nIntegration tests completed.")


# # Configuration for pytest markers
# def pytest_configure(config):
#     """Configure pytest markers."""
#     config.addinivalue_line("markers", "integration: mark test as integration test requiring AWS")
#     config.addinivalue_line("markers", "slow: mark test as slow running")
