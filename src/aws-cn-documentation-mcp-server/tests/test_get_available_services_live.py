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
"""Live test for the get_available_services tool in the AWS China Documentation MCP server."""

import pytest
from awslabs.aws_cn_documentation_mcp_server.server import get_available_services


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

    # Check that the result contains the URL
    expected_url = 'https://docs.amazonaws.cn/en_us/aws/latest/userguide/services.html'
    assert expected_url in result

    # Check for expected content in the AWS China available services page
    expected_content_markers = [
        'China',
        'Amazon',
        'services',
    ]

    for marker in expected_content_markers:
        assert marker.lower() in result.lower(), f"Expected to find '{marker}' in the result"

    # Check for some specific AWS services that should be available in China
    expected_services = [
        'S3',
        'EC2',
        'Lambda',
        'CloudFront',
    ]

    for service in expected_services:
        assert service in result, f"Expected to find '{service}' in the list of available services"

    # Check that the content is properly formatted
    assert 'AWS China Documentation from' in result

    # Check that the result doesn't contain error messages
    error_indicators = ['<e>Error', 'Failed to fetch']
    for indicator in error_indicators:
        assert indicator not in result, f"Found error indicator '{indicator}' in the result"

    # Print a sample of the result for debugging (will show in pytest output with -v flag)
    print('\nReceived available services content (first 300 chars):')
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

    # The result should have a header line with the URL
    lines = result.split('\n')
    assert lines[0].startswith('AWS China Documentation from')

    # The content should have at least one heading
    heading_found = False
    for line in lines:
        if line.startswith('#'):
            heading_found = True
            break
    assert heading_found, 'Expected to find at least one heading in the result'

    # The content should have a table or list of services
    list_indicators = ['- ', '* ', '1. ', '|']
    list_found = False
    for line in lines:
        if any(indicator in line for indicator in list_indicators):
            list_found = True
            break
    assert list_found, 'Expected to find a list or table of services in the result'

    # Check for links to service documentation
    link_found = False
    for line in lines:
        if 'https://' in line and 'docs.amazonaws.cn' in line:
            link_found = True
            break
    assert link_found, 'Expected to find links to service documentation in the result'

    print('\nContent structure test successful')
