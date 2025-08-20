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

"""Tests for the prompt functions in server.py module."""

import pytest

from awslabs.well_architected_security_mcp_server.server import (
    check_network_security_prompt,
    check_storage_security_prompt,
    security_assessment_precheck,
)


@pytest.mark.asyncio
async def test_security_assessment_precheck(mock_ctx):
    """Test the security_assessment_precheck prompt function."""
    # Call the function
    result = await security_assessment_precheck(mock_ctx)

    # Verify the result is a non-empty string
    assert isinstance(result, str)
    assert len(result) > 0

    # Check for expected content in the prompt
    assert "AWS Security Assessment Workflow Guide" in result
    assert "CheckSecurityServices" in result
    assert "GetSecurityFindings" in result
    assert "Step 1: Check Security Services Status" in result
    assert "Step 2: Analyze the Results" in result
    assert "Step 3: Retrieve Findings from Enabled Services" in result
    assert "Step 4: Summarize Security Posture" in result
    assert "Best Practices" in result

    # Check for code examples
    assert "```python" in result
    assert "await use_mcp_tool" in result
    assert 'server_name="well-architected-security-mcp-server"' in result
    assert 'tool_name="CheckSecurityServices"' in result
    assert 'tool_name="GetSecurityFindings"' in result


@pytest.mark.asyncio
async def test_check_storage_security_prompt(mock_ctx):
    """Test the check_storage_security_prompt function."""
    # Call the function
    result = await check_storage_security_prompt(mock_ctx)

    # Verify the result is a non-empty string
    assert isinstance(result, str)
    assert len(result) > 0

    # Check for expected content in the prompt
    assert "AWS Storage Security Assessment Guide" in result
    assert "Step 1: Identify Available Storage Services" in result
    assert "Step 2: Filter for Storage Services" in result
    assert "Step 3: Check Storage Encryption" in result
    assert "Step 4: Analyze the Results" in result
    assert "Step 5: Review Non-Compliant Resources" in result
    assert "Step 6: Implement Recommendations" in result
    assert "Best Practices for Storage Security" in result
    assert "CheckStorageEncryption" in result

    # Check for code examples and specific storage services
    assert "```python" in result
    assert "await use_mcp_tool" in result
    assert 'tool_name="CheckStorageEncryption"' in result
    assert 'tool_name="ListServicesInRegion"' in result
    assert "storage_services = ['s3', 'ebs', 'rds', 'dynamodb', 'efs', 'elasticache']" in result
    assert "include_unencrypted_only" in result


@pytest.mark.asyncio
async def test_check_network_security_prompt(mock_ctx):
    """Test the check_network_security_prompt function."""
    # Call the function
    result = await check_network_security_prompt(mock_ctx)

    # Verify the result is a non-empty string
    assert isinstance(result, str)
    assert len(result) > 0

    # Check for expected content in the prompt
    assert "AWS Network Security Assessment Guide" in result
    assert "Step 1: Identify Available Network Services" in result
    assert "Step 2: Filter for Network Services" in result
    assert "Step 3: Check Network Security" in result
    assert "Step 4: Analyze the Results" in result
    assert "Step 5: Review Non-Compliant Resources" in result
    assert "Step 6: Implement Recommendations" in result
    assert "Best Practices for Network Security" in result
    assert "CheckNetworkSecurity" in result

    # Check for code examples and specific network services
    assert "```python" in result
    assert "await use_mcp_tool" in result
    assert 'tool_name="CheckNetworkSecurity"' in result
    assert 'tool_name="ListServicesInRegion"' in result
    assert "network_services = ['elb', 'vpc', 'apigateway', 'cloudfront']" in result
    assert "include_non_compliant_only" in result

    # Check for best practices
    assert "Use HTTPS/TLS" in result
    assert "Configure security policies" in result
    assert "Implement strict security headers" in result
    assert "Use AWS Certificate Manager" in result
