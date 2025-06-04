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

import pytest
from awslabs.cdk_mcp_server.data.cdk_nag_parser import (
    check_cdk_nag_suppressions,
    extract_rule_info,
    extract_rule_pack_section,
    extract_section_by_marker,
    fetch_cdk_nag_content,
    format_rule_info,
    get_errors,
    get_rule,
    get_rule_pack,
    get_warnings,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_fetch_cdk_nag_content():
    """Test fetching CDK Nag content."""
    mock_content = """
# CDK Nag Rules

## AWS Solutions
### Warnings
- W1: Warning 1
- W2: Warning 2

### Errors
- E1: Error 1
- E2: Error 2

## HIPAA Security
### Warnings
- W3: Warning 3
"""

    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = MagicMock()
        mock_response.text = mock_content
        mock_get.return_value = mock_response

        content = await fetch_cdk_nag_content()
        assert content == mock_content
        mock_get.assert_called_once()


def test_extract_rule_pack_section():
    """Test extracting rule pack section."""
    content = """
# CDK Nag Rules

## AWS Solutions
### Warnings
- W1: Warning 1

## HIPAA Security
### Warnings
- W2: Warning 2
"""

    # Test valid rule pack
    section = extract_rule_pack_section(content, 'AWS Solutions')
    assert 'AWS Solutions' in section
    assert 'W1: Warning 1' in section
    assert 'HIPAA Security' not in section

    # Test invalid rule pack
    section = extract_rule_pack_section(content, 'Invalid Pack')
    assert 'not found' in section


def test_extract_section_by_marker():
    """Test extracting section by marker."""
    section = """
## AWS Solutions
### Warnings
- W1: Warning 1
- W2: Warning 2

### Errors
- E1: Error 1
"""

    # Test valid marker
    found, result = extract_section_by_marker(section, '### Warnings')
    assert found
    assert 'W1: Warning 1' in result
    assert 'W2: Warning 2' in result
    assert 'Errors' not in result

    # Test invalid marker
    found, result = extract_section_by_marker(section, '### Invalid')
    assert not found
    assert 'No Invalid found' in result


def test_extract_rule_info():
    """Test extracting rule information."""
    content = """
| Rule ID | Cause | Explanation | Control ID |
|---------|--------|-------------|------------|
| W1 | Cause 1 | Explanation 1 | Control 1 |
| W2 | Cause 2 | Explanation 2 | Control 2 |
"""

    # Test valid rule
    rule_info = extract_rule_info(content, 'W1')
    assert rule_info is not None
    assert rule_info['rule_id'] == 'W1'
    assert rule_info['cause'] == 'Cause 1'
    assert rule_info['explanation'] == 'Explanation 1'
    assert rule_info['control_ids'] == 'Control 1'

    # Test invalid rule
    rule_info = extract_rule_info(content, 'Invalid')
    assert rule_info is None


def test_format_rule_info():
    """Test formatting rule information."""
    rule_info = {
        'rule_id': 'W1',
        'cause': 'Cause 1',
        'explanation': 'Explanation 1',
        'control_ids': 'Control 1',
    }

    formatted = format_rule_info(rule_info)
    assert '# W1' in formatted
    assert 'Cause 1' in formatted
    assert 'Explanation 1' in formatted
    assert 'Control 1' in formatted

    # Test with None
    formatted = format_rule_info(None)
    assert 'not found' in formatted


@pytest.mark.asyncio
async def test_get_rule_pack():
    """Test getting rule pack."""
    mock_content = """
# CDK Nag Rules

## AWS Solutions
### Warnings
- W1: Warning 1

## HIPAA Security
### Warnings
- W2: Warning 2
"""

    with patch('awslabs.cdk_mcp_server.data.cdk_nag_parser.fetch_cdk_nag_content') as mock_fetch:
        mock_fetch.return_value = mock_content

        # Test valid rule pack
        result = await get_rule_pack('AWS Solutions')
        assert 'AWS Solutions' in result
        assert 'W1: Warning 1' in result

        # Test invalid rule pack
        result = await get_rule_pack('Invalid Pack')
        assert 'not found' in result


@pytest.mark.asyncio
async def test_get_warnings():
    """Test getting warnings."""
    mock_content = """
# CDK Nag Rules

## AWS Solutions
### Warnings
- W1: Warning 1
- W2: Warning 2

### Errors
- E1: Error 1
"""

    with patch('awslabs.cdk_mcp_server.data.cdk_nag_parser.fetch_cdk_nag_content') as mock_fetch:
        mock_fetch.return_value = mock_content

        # Test valid rule pack
        result = await get_warnings('AWS Solutions')
        assert 'W1: Warning 1' in result
        assert 'W2: Warning 2' in result
        assert 'E1: Error 1' not in result

        # Test invalid rule pack
        result = await get_warnings('Invalid Pack')
        assert 'not found' in result


@pytest.mark.asyncio
async def test_get_errors():
    """Test getting errors."""
    mock_content = """
# CDK Nag Rules

## AWS Solutions
### Warnings
- W1: Warning 1

### Errors
- E1: Error 1
- E2: Error 2
"""

    with patch('awslabs.cdk_mcp_server.data.cdk_nag_parser.fetch_cdk_nag_content') as mock_fetch:
        mock_fetch.return_value = mock_content

        # Test valid rule pack
        result = await get_errors('AWS Solutions')
        assert 'E1: Error 1' in result
        assert 'E2: Error 2' in result
        assert 'W1: Warning 1' not in result

        # Test invalid rule pack
        result = await get_errors('Invalid Pack')
        assert 'not found' in result


@pytest.mark.asyncio
async def test_get_rule():
    """Test getting rule information."""
    mock_content = """
| Rule ID | Cause | Explanation | Control ID |
|---------|--------|-------------|------------|
| W1 | Cause 1 | Explanation 1 | Control 1 |
"""

    with patch('awslabs.cdk_mcp_server.data.cdk_nag_parser.fetch_cdk_nag_content') as mock_fetch:
        mock_fetch.return_value = mock_content

        # Test valid rule
        result = await get_rule('W1')
        assert '# W1' in result
        assert 'Cause 1' in result
        assert 'Explanation 1' in result
        assert 'Control 1' in result

        # Test invalid rule
        result = await get_rule('Invalid')
        assert 'not found' in result


def test_check_cdk_nag_suppressions():
    """Test checking CDK Nag suppressions."""
    # Test with code containing suppressions
    code = """
    import { NagSuppressions } from 'cdk-nag';
    NagSuppressions.addStackSuppressions(stack, [
        { id: 'W1', reason: 'Test' }
    ]);
    """

    result = check_cdk_nag_suppressions(code=code)
    assert result['has_suppressions'] is True
    assert len(result['suppressions']) > 0
    assert 'W1' in str(result['suppressions'])

    # Test with code without suppressions
    code = """
    const stack = new Stack();
    """

    result = check_cdk_nag_suppressions(code=code)
    assert result['has_suppressions'] is False

    # Test with invalid input
    result = check_cdk_nag_suppressions()
    assert 'error' in result
    assert result['status'] == 'error'

    # Test with both code and file_path
    result = check_cdk_nag_suppressions(code='test', file_path='test.ts')
    assert 'error' in result
    assert result['status'] == 'error'
