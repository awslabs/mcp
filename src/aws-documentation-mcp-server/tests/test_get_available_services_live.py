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
"""Live test for the get_available_services tool in the AWS Documentation MCP server."""

import pytest
from awslabs.aws_documentation_mcp_server.server_china import get_available_services


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_get_available_services_live():
    """Test that get_available_services can fetch real AWS China available services."""
    ctx = MockContext()

    # Call the tool
    result = await get_available_services(ctx)

    # Verify the result
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Check that the result contains the source URL
    source_url = 'https://docs.amazonaws.cn/en_us/aws/latest/userguide/services.html'
    assert source_url in result

    # Check for expected content in the AWS China services page
    expected_content_markers = [
        'Documentation by Service',
        'China',
        'Region',
        'services',
    ]

    for marker in expected_content_markers:
        assert marker.lower() in result.lower(), f"Expected to find '{marker}' in the result"

    # Check that the content is properly formatted
    assert 'AWS Documentation from' in result

    # Check that the result doesn't contain error messages
    error_indicators = ['<e>Error', 'Failed to fetch']
    for indicator in error_indicators:
        assert indicator not in result, f"Found error indicator '{indicator}' in the result"

    # Check for specific AWS services that should be available in China regions
    common_services = [
        'Amazon EC2',
        'Amazon S3',
        'Simple Storage Service',
        'Lambda',
    ]

    for service in common_services:
        assert service.lower() in result.lower(), (
            f"Expected to find '{service}' in the available services"
        )

    # Print a sample of the result for debugging (will show in pytest output with -v flag)
    print('\nReceived AWS China available services content (first 300 chars):')
    print(f'{result[:300]}...')


@pytest.mark.asyncio
@pytest.mark.live
async def test_get_available_services_content_structure():
    """Test that get_available_services returns properly structured content."""
    ctx = MockContext()

    # Call the tool
    result = await get_available_services(ctx)

    # Verify the result structure
    assert result is not None
    assert isinstance(result, str)

    # The result should contain markdown formatting elements
    markdown_elements = ['#', '##', '-', '*', '|']
    markdown_present = any(element in result for element in markdown_elements)
    assert markdown_present, 'Expected markdown formatting in the result'

    # The result should mention differences between global AWS and AWS China
    difference_indicators = ['difference', 'specific', 'region', 'availability']
    difference_mentioned = any(
        indicator.lower() in result.lower() for indicator in difference_indicators
    )
    assert difference_mentioned, (
        'Expected mentions of differences between global AWS and AWS China'
    )

    # Print the structure analysis for debugging
    print('\nContent structure analysis:')
    print(f'Total content length: {len(result)} characters')
    print(f'Number of lines: {result.count("\n")}')
    print(f'Number of paragraphs: {result.count("\n\n")}')
