
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
import pytest
from unittest.mock import MagicMock
from awslabs.cdk_mcp_server.core.tools import (
    cdk_guidance,
    explain_cdk_nag_rule,
    check_cdk_nag_suppressions_tool,
    bedrock_schema_generator_from_file,
    get_aws_solutions_construct_pattern,
    search_genai_cdk_constructs,
    lambda_layer_documentation_provider
)

@pytest.fixture
def mock_context():
    """Fixture that provides a mocked MCP context."""
    context = MagicMock()
    context.settings = MagicMock()
    return context

@pytest.mark.asyncio
async def test_cdk_guidance(mock_context):
    """Test CDK guidance tool."""
    result = await cdk_guidance(mock_context)
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_explain_cdk_nag_rule(mock_context):
    """Test CDK Nag rule explanation tool."""
    result = await explain_cdk_nag_rule(mock_context, rule_id="AwsSolutions-APIG3")
    assert isinstance(result, dict)
    assert 'rule_id' in result
    assert 'content' in result
    assert 'source' in result
    assert 'status' in result
    assert result['rule_id'] == "AwsSolutions-APIG3"
    assert result['source'] == 'https://github.com/cdklabs/cdk-nag/blob/main/RULES.md'
    assert result['status'] == 'success'

@pytest.mark.asyncio
async def test_check_cdk_nag_suppressions_tool(mock_context):
    """Test CDK Nag suppressions check tool."""
    result = await check_cdk_nag_suppressions_tool(mock_context, code="test code")
    assert isinstance(result, dict)
    assert 'has_suppressions' in result
    assert 'message' in result
    assert 'status' in result


@pytest.mark.asyncio
async def test_bedrock_schema_generator_from_file_throws_error(mock_context):
    """Test Bedrock schema generator tool."""
    with pytest.raises(Exception):
        await bedrock_schema_generator_from_file(
            mock_context,
            lambda_code_path="test.py", #non existing path
            output_path="test.json" #non existing path
        )

@pytest.mark.asyncio
async def test_get_aws_solutions_construct_pattern(mock_context):
    """Test AWS Solutions Construct pattern tool."""
    result = await get_aws_solutions_construct_pattern(mock_context, pattern_name="aws-alb-lambda")
    assert isinstance(result, dict)
    assert 'description' in result
    assert 'use_cases' in result
    assert 'services' in result
    assert 'documentation_uri' in result
    assert result['pattern_name'] == "aws-alb-lambda"
    assert result['services'] == ["Application Load Balancer", 'Lambda']
    assert result['description'] == 'This AWS Solutions Construct implements an an Application Load Balancer to an AWS Lambda function'
    assert result['documentation_uri'] == "aws-solutions-constructs://aws-alb-lambda"

@pytest.mark.asyncio
async def test_search_genai_cdk_constructs(mock_context):
    """Test GenAI CDK constructs search tool."""
    result = await search_genai_cdk_constructs(mock_context, query="knowledge base")
    assert isinstance(result, dict)
    assert 'count' in result
    assert 'results' in result
    assert 'status' in result
    assert 'installation_required' in result
    assert result['status'] == 'success'
    assert result['installation_required']['package_name'] == '@cdklabs/generative-ai-cdk-constructs'
    assert result['installation_required']['message'] == 'This construct requires the @cdklabs/generative-ai-cdk-constructs package to be installed'

@pytest.mark.asyncio
async def test_lambda_layer_documentation_provider_generic(mock_context):
    """Test Lambda layer documentation provider tool."""
    result = await lambda_layer_documentation_provider(mock_context, layer_type="generic")
    assert isinstance(result, dict)
    assert 'code_examples' in result
    assert 'directory_structure' in result
    assert 'source_url' in result
    assert 'layer_type' in result
    assert result['layer_type'] == 'generic'

@pytest.mark.asyncio
async def test_lambda_layer_documentation_provider_python(mock_context):
    """Test Lambda layer documentation provider tool."""
    result = await lambda_layer_documentation_provider(mock_context, layer_type="python")
    assert isinstance(result, dict)
    assert 'layer_type' in result
    assert 'documentation_source' in result
    assert 'documentation_usage_guide' in result
    assert 'code_generation_guidance' in result
    assert result['layer_type'] == 'python'
    assert result['documentation_source']['server'] == 'awslabs.aws-documentation-mcp-server'
    assert result['documentation_source']['tool'] == 'read_documentation'
    assert result['documentation_source']['parameters']['max_length'] == 10000
    assert result['documentation_usage_guide']['when_to_fetch_full_docs'] == 'Fetch full documentation to view detailed property definitions, learn about optional parameters, and find additional code examples'
    assert result['documentation_usage_guide']['contains_sample_code'] == True
    assert result['documentation_usage_guide']['contains_props_documentation'] == True
    assert result['code_generation_guidance']['imports'] == ["import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha'"]
    assert result['code_generation_guidance']['construct_types'] == {'python': 'PythonLayerVersion'}
    assert result['code_generation_guidance']['required_properties'] == {'python': ['entry']}
    assert result['code_generation_guidance']['sample_code'] == "new python.PythonLayerVersion(this, 'MyLayer', {\n  entry: '/path/to/my/layer', // point this to your library's directory\n})"
