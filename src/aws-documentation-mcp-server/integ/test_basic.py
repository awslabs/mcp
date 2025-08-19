"""
Basic integration test for aws-documentation-mcp-server using the official MCP SDK.
"""

import os
import sys
import pytest
import asyncio
import logging

# Add the testing framework to the path
testing_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'testing')
sys.path.insert(0, testing_path)

# Also add the parent directory to handle relative imports
parent_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, parent_path)

# setup constants
DOCUMENTATION_SERVER_PY = "awslabs/aws_documentation_mcp_server/server.py"
READ_DOCUMENTATION_TOOL_NAME = "read_documentation"
SEARCH_DOCUMENTATION_TOOL_NAME = "search_documentation"
RECOMMEND_TOOL_NAME = "recommend"
NUMBER_OF_TOOLS = 3

from testing.pytest_utils import (
    MCPTestBase, 
    create_test_config, 
    create_validation_rule,
    create_tool_test_config,
    assert_test_results,
    setup_logging,
)

# Setup logging
setup_logging("INFO")
logger = logging.getLogger(__name__)


class TestAWSDocumentationMCPServer:
    """Basic integration tests for AWS Documentation MCP Server."""
    
    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup test environment."""
        self.server_path = os.path.join(os.path.dirname(__file__), '..')
        self.test_instance = None
        yield
        if self.test_instance:
            asyncio.run(self.test_instance.teardown())
    
    @pytest.mark.asyncio
    async def test_basic_protocol(self):
        """Test basic MCP protocol functionality."""
        
        # Create test instance
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command="uv",
            args=["run", "--frozen", DOCUMENTATION_SERVER_PY],
            env={
                "FASTMCP_LOG_LEVEL": "ERROR"
            }
        )
        
        await self.test_instance.setup()
        
        # Define expected configuration
        expected_config = create_test_config(
            expected_tools={
                "count": NUMBER_OF_TOOLS,  # read_documentation, search_documentation, and recommend
                "names": [READ_DOCUMENTATION_TOOL_NAME, SEARCH_DOCUMENTATION_TOOL_NAME, RECOMMEND_TOOL_NAME]
            },
            expected_resources={
                "count": 0  # This server doesn't provide resources
            },
            expected_prompts={
                "count": 0  # This server doesn't provide prompts
            }
        )
        
        # Run basic tests
        results = await self.test_instance.run_basic_tests(expected_config)
        
        # Assert results
        assert_test_results(results, expected_success_count=6)  # 6 basic protocol tests
    
    @pytest.mark.asyncio
    async def test_search_documentation_tool(self):
        """Test the search documentation tool."""
        
        # Create test instance
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command="uv",
            args=["run", "--frozen", DOCUMENTATION_SERVER_PY],
            env={
                "FASTMCP_LOG_LEVEL": "ERROR"
            }
        )
        
        await self.test_instance.setup()
        
        validation_rules = [
            create_validation_rule("contains", "url", "content"),
            create_validation_rule("contains", "title", "content")
        ]
        
        test_config = create_tool_test_config(
            tool_name=SEARCH_DOCUMENTATION_TOOL_NAME,
            arguments={
                "search_phrase": "S3 bucket",
                "limit": 1
            },
            validation_rules=validation_rules
        )
        
        result = await self.test_instance.run_custom_test(test_config)
        
        assert result.success, f"Search documentation test failed: {result.error_message}"
        assert "result" in result.details, "Response should contain result field"
    
    @pytest.mark.asyncio
    async def test_read_documentation_tool(self):
        """Test the read documentation tool."""
        
        # Create test instance
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command="uv",
            args=["run", "--frozen", DOCUMENTATION_SERVER_PY],
            env={
                "FASTMCP_LOG_LEVEL": "ERROR"
            }
        )
        
        await self.test_instance.setup()
        
        validation_rules = [
            create_validation_rule("contains", "bucket", "content"),
            create_validation_rule("contains", "naming", "content"),
            create_validation_rule("contains", "rules", "content")
        ]
        
        test_config = create_tool_test_config(
            tool_name=READ_DOCUMENTATION_TOOL_NAME,
            arguments={
                "url": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html"
            },
            validation_rules=validation_rules
        )
        
        result = await self.test_instance.run_custom_test(test_config)
        
        assert result.success, f"Read documentation test failed: {result.error_message}"
        assert "result" in result.details, "Response should contain result field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
