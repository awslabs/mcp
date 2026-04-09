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
"""Tests for FastMCP 3.x features: tag filtering, enriched descriptions, validate_output, multi-spec."""

import json
import pytest
from awslabs.openapi_mcp_server.api.config import Config, load_config
from awslabs.openapi_mcp_server.server import create_mcp_server_async
from unittest.mock import MagicMock, patch


PETSTORE_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 'Petstore', 'version': '1.0.0'},
    'servers': [{'url': 'https://example.com'}],
    'paths': {
        '/pets': {
            'get': {
                'operationId': 'listPets',
                'summary': 'List all pets',
                'tags': ['pet'],
                'parameters': [
                    {
                        'name': 'status',
                        'in': 'query',
                        'schema': {'type': 'string', 'enum': ['available', 'sold']},
                    }
                ],
                'responses': {'200': {'description': 'OK'}, '400': {'description': 'Bad request'}},
            },
            'post': {
                'operationId': 'createPet',
                'summary': 'Create a pet',
                'tags': ['pet'],
                'responses': {'201': {'description': 'Created'}},
            },
        },
        '/store/inventory': {
            'get': {
                'operationId': 'getInventory',
                'summary': 'Returns inventories',
                'tags': ['store'],
                'responses': {'200': {'description': 'OK'}},
            },
        },
        '/users': {
            'get': {
                'operationId': 'listUsers',
                'summary': 'List users',
                'tags': ['user'],
                'parameters': [
                    {
                        'name': 'limit',
                        'in': 'query',
                        'schema': {'type': 'integer', 'example': 10},
                    }
                ],
                'responses': {'200': {'description': 'OK'}},
            },
        },
    },
}

EXTRA_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 'Payments', 'version': '1.0.0'},
    'servers': [{'url': 'https://payments.example.com'}],
    'paths': {
        '/payments': {
            'post': {
                'operationId': 'createPayment',
                'summary': 'Create payment',
                'tags': ['payment'],
                'responses': {'201': {'description': 'Created'}},
            },
        },
    },
}


def _base_config(**overrides):
    defaults = {
        'api_name': 'Test',
        'api_base_url': 'https://example.com',
        'api_spec_url': 'https://example.com/spec.json',
    }
    defaults.update(overrides)
    return Config(**defaults)


async def _create_server(config, spec=None, extra_spec=None):
    spec = spec or PETSTORE_SPEC
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
    ):

        def load_side_effect(url='', path=''):
            if extra_spec and url != config.api_spec_url:
                return extra_spec
            return spec

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()
        return await create_mcp_server_async(config)


# --- Tag filtering ---


@pytest.mark.asyncio
async def test_include_tags_filters_to_matching():
    """Only operations with matching tags are exposed."""
    server = await _create_server(_base_config(include_tags='pet'))
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert 'listPets' in names
    assert 'createPet' in names
    assert 'getInventory' not in names
    assert 'listUsers' not in names


@pytest.mark.asyncio
async def test_exclude_tags_hides_matching():
    """Operations with excluded tags are hidden."""
    server = await _create_server(_base_config(exclude_tags='store,user'))
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert 'listPets' in names
    assert 'createPet' in names
    assert 'getInventory' not in names
    assert 'listUsers' not in names


@pytest.mark.asyncio
async def test_no_tag_filters_exposes_all():
    """Without tag filters, all operations are exposed."""
    server = await _create_server(_base_config())
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert 'listPets' in names
    assert 'getInventory' in names
    assert 'listUsers' in names


# --- Enriched descriptions ---


@pytest.mark.asyncio
async def test_enriched_descriptions_include_response_codes():
    """Tool descriptions include response codes from the spec."""
    server = await _create_server(_base_config())
    tools = await server.list_tools()
    list_pets = next(t for t in tools if t.name == 'listPets')
    assert 'Returns:' in list_pets.description
    assert '200' in list_pets.description


@pytest.mark.asyncio
async def test_enriched_descriptions_include_enum_examples():
    """Tool descriptions include enum examples from parameters."""
    server = await _create_server(_base_config())
    tools = await server.list_tools()
    list_pets = next(t for t in tools if t.name == 'listPets')
    assert 'status=available' in list_pets.description


@pytest.mark.asyncio
async def test_enriched_descriptions_include_explicit_examples():
    """Tool descriptions include explicit example values from parameters."""
    server = await _create_server(_base_config())
    tools = await server.list_tools()
    list_users = next(t for t in tools if t.name == 'listUsers')
    assert 'limit=10' in list_users.description


# --- Validate output toggle ---


@pytest.mark.asyncio
async def test_validate_output_default_true():
    """validate_output defaults to True."""
    config = _base_config()
    assert config.validate_output is True


@pytest.mark.asyncio
async def test_validate_output_false_creates_server():
    """Server starts successfully with validate_output=False."""
    server = await _create_server(_base_config(validate_output=False))
    tools = await server.list_tools()
    assert len(tools) > 0


# --- Multi-spec composition ---


@pytest.mark.asyncio
async def test_additional_specs_adds_tools():
    """Additional specs add their tools to the server."""
    extra = json.dumps(
        [
            {
                'name': 'payments',
                'spec_url': 'https://payments.example.com/spec.json',
                'base_url': 'https://payments.example.com',
            }
        ]
    )
    server = await _create_server(_base_config(additional_specs=extra), extra_spec=EXTRA_SPEC)
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert 'listPets' in names
    assert 'createPayment' in names


@pytest.mark.asyncio
async def test_additional_specs_invalid_json_continues():
    """Invalid additional_specs JSON logs warning but server still starts."""
    server = await _create_server(_base_config(additional_specs='not-json'))
    tools = await server.list_tools()
    # Primary spec tools still work
    names = {t.name for t in tools}
    assert 'listPets' in names


# --- Config loading ---


def test_config_tag_fields_from_env():
    """Tag filter config loads from environment variables."""
    with patch.dict('os.environ', {'INCLUDE_TAGS': 'pet,store', 'EXCLUDE_TAGS': 'admin'}):
        config = load_config()
    assert config.include_tags == 'pet,store'
    assert config.exclude_tags == 'admin'


def test_config_validate_output_from_env():
    """validate_output loads from VALIDATE_OUTPUT env var."""
    with patch.dict('os.environ', {'VALIDATE_OUTPUT': 'false'}):
        config = load_config()
    assert config.validate_output is False


def test_config_additional_specs_from_env():
    """additional_specs loads from ADDITIONAL_SPECS env var."""
    specs = '[{"name":"x","spec_url":"http://x"}]'
    with patch.dict('os.environ', {'ADDITIONAL_SPECS': specs}):
        config = load_config()
    assert config.additional_specs == specs


def test_config_defaults():
    """New config fields have correct defaults."""
    config = Config()
    assert config.include_tags == ''
    assert config.exclude_tags == ''
    assert config.validate_output is True
    assert config.additional_specs == ''


@pytest.mark.asyncio
async def test_enriched_descriptions_no_params():
    """Tool descriptions still enriched when operation has no parameters."""
    server = await _create_server(_base_config())
    tools = await server.list_tools()
    inventory = next(t for t in tools if t.name == 'getInventory')
    # Should have Returns even without params
    assert 'Returns:' in inventory.description


@pytest.mark.asyncio
async def test_additional_specs_with_spec_path():
    """Additional specs can use spec_path instead of spec_url."""
    extra = json.dumps(
        [
            {
                'name': 'payments',
                'spec_path': 'fake.json',
                'base_url': 'https://payments.example.com',
            }
        ]
    )
    server = await _create_server(_base_config(additional_specs=extra), extra_spec=EXTRA_SPEC)
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert 'createPayment' in names


@pytest.mark.asyncio
async def test_additional_specs_empty_array():
    """Empty additional_specs array is handled gracefully."""
    server = await _create_server(_base_config(additional_specs='[]'))
    tools = await server.list_tools()
    assert len(tools) == 4  # Only primary spec tools


@pytest.mark.asyncio
async def test_include_and_exclude_tags_combined():
    """Include and exclude can be used together."""
    server = await _create_server(_base_config(include_tags='pet,store', exclude_tags='store'))
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert 'listPets' in names
    assert 'getInventory' not in names


def test_config_no_validate_output_from_args():
    """no_validate_output CLI arg sets validate_output to False."""
    from unittest.mock import MagicMock as M

    args = M()
    args.no_validate_output = True
    args.include_tags = None
    args.exclude_tags = None
    args.additional_specs = None
    # Set all other expected attrs to None
    for attr in [
        'api_name',
        'api_url',
        'spec_url',
        'spec_path',
        'port',
        'debug',
        'auth_type',
        'auth_username',
        'auth_password',
        'auth_token',
        'auth_api_key',
        'auth_api_key_name',
        'auth_api_key_in',
        'auth_cognito_client_id',
        'auth_cognito_username',
        'auth_cognito_password',
        'auth_cognito_client_secret',
        'auth_cognito_domain',
        'auth_cognito_scopes',
        'auth_cognito_user_pool_id',
        'auth_cognito_region',
    ]:
        setattr(args, attr, None)
    config = load_config(args)
    assert config.validate_output is False


@pytest.mark.asyncio
async def test_server_logs_tool_and_prompt_counts():
    """Server logs registered tools and prompts after creation."""
    with patch('awslabs.openapi_mcp_server.server.logger') as mock_logger:
        server = await _create_server(_base_config())
        tools = await server.list_tools()
        prompts = await server.list_prompts()
        # Verify logging happened
        assert len(tools) > 0
        assert len(prompts) > 0
        # The server should have logged tool/prompt info
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any('Registered tools' in c for c in info_calls)


@pytest.mark.asyncio
async def test_validate_output_true_creates_server():
    """Server starts successfully with validate_output=True (default)."""
    server = await _create_server(_base_config(validate_output=True))
    tools = await server.list_tools()
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_prompt_generation_failure_handled():
    """Server continues when prompt generation fails."""
    with patch('awslabs.openapi_mcp_server.server.MCPPromptManager') as mock_pm:
        mock_pm.return_value.generate_prompts.side_effect = RuntimeError('prompt gen failed')
        server = await _create_server(_base_config())
        # Server should still be created despite prompt failure
        tools = await server.list_tools()
        assert len(tools) > 0
