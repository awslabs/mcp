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

"""The served instructions and prompts name only what the server serves.

Everything is read from the real server over an in-memory FastMCP Client, so the
checks hold for any tool or prompt added later.
"""

import json
import pytest
import re
from awslabs.billing_cost_management_mcp_server import server
from awslabs.billing_cost_management_mcp_server.prompts.graviton_migration import (
    graviton_migration_analysis,
)
from awslabs.billing_cost_management_mcp_server.prompts.savings_plans import (
    savings_plans_analysis,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_helpers import (
    list_recommendations,
)
from contextlib import asynccontextmanager
from fastmcp import Client, Context
from fastmcp.exceptions import McpError
from mcp.types import TextContent
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


_MOUNTED = []

GRAVITON_ARGS = {'account_ids': '111111111111, 222222222222', 'region': 'us-east-1'}
SP_ARGS = {'account_ids': '111111111111', 'lookback_days': '30', 'term_in_years': '1'}
PROMPT_ARGS = {
    'analyze_graviton_opportunities': GRAVITON_ARGS,
    'analyze_savings_plans_opportunities': SP_ARGS,
}

# Fields of tool responses (not parameters) the instructions and prompts name.
# The COH ones are checked against the list_recommendations formatter below.
COH_RECOMMENDATION_FIELDS = {
    'current_resource_type',
    'recommended_resource_type',
    'estimated_monthly_savings',
    'implementation_effort',
}
RESPONSE_FIELDS = COH_RECOMMENDATION_FIELDS | {
    'complete_dataset',
    'data_stored',
    'table_name',
    'query_tool',
    'sample_queries',
}

# Hyphenated English words in the guidance that are not tool names.
_ENGLISH_COMPOUNDS = {
    'high-level',
    'multi-account',
    'performance-based',
    'highest-impact',
    'top-level',
}


def _mount_once():
    """Mount the real tool servers once per process (setup() is not idempotent)."""
    if not _MOUNTED:
        server.setup()
        _MOUNTED.append(True)


@asynccontextmanager
async def _served():
    """The served instructions, tools and prompts."""
    _mount_once()
    async with Client(server.mcp) as client:
        # FastMCP 4 may negotiate server/discover, which has no InitializeResult.
        init = client.initialize_result
        yield SimpleNamespace(
            client=client,
            instructions=getattr(client, 'instructions', None)
            or (init and init.instructions)
            or '',
            tools={t.name: t for t in await client.list_tools()},
            prompts={p.name: p for p in await client.list_prompts()},
        )


async def _rendered(served, name):
    result = await served.client.get_prompt(name, PROMPT_ARGS[name])
    return '\n'.join(getattr(m.content, 'text', str(m.content)) for m in result.messages)


def _tool_text(tool):
    return (tool.description or '') + json.dumps(tool.inputSchema)


def _schema_properties(tools):
    return {name for t in tools.values() for name in (t.inputSchema or {}).get('properties', {})}


def _unknown_identifiers(text, tools):
    """Backticked bare identifiers that name no tool, parameter, operation or response field."""
    properties = _schema_properties(tools)
    all_tool_text = ' '.join(_tool_text(t) for t in tools.values())
    unknown = []
    for token in re.findall(r'`([^`\s]+)`', text):
        if re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)+', token):
            if token not in tools:
                unknown.append(token)
        elif re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)+', token):
            is_operation = re.search(rf'\b{token}\b', all_tool_text)
            if token not in properties | RESPONSE_FIELDS and not is_operation:
                unknown.append(token)
    return unknown


# --- Item 1: no hand-maintained tool or prompt list ---


async def test_instructions_list_no_tools_or_prompts():
    """Hosts get tools and prompts from tools/list and prompts/list; a copy here drifts."""
    async with _served() as served:
        assert 'TOOLS:' not in served.instructions
        assert 'PROMPTS:' not in served.instructions
        assert 'Available components' not in served.instructions


async def test_instructions_are_short_enough_to_be_shown_whole():
    """Some hosts cut long instructions (Claude Code at about 4 KB); keep the guidance in."""
    async with _served() as served:
        assert len(served.instructions) < 4000


# --- Items 2-4: stale guidance removed, defaults scoped ---


@pytest.mark.parametrize(
    'banned',
    [
        'top 2-3',
        'managing and querying',
        'accountIds parameter',
        'Use rec-details for enhanced',
        'athena-cur',
        '- pricing:',
        '- budget:',
        'graviton_migration',
        'savings_plans_analysis',
        'graviton_analysis',
        'Exclude Credits and Refunds',
    ],
)
async def test_stale_guidance_removed(banned):
    """Stale or wrong guidance from the hand-maintained text is gone."""
    async with _served() as served:
        assert banned not in served.instructions


async def test_truncation_guidance_states_what_was_omitted():
    """Optimization guidance no longer truncates silently to the top 2-3."""
    async with _served() as served:
        assert 'lead with the highest-impact recommendations' in served.instructions
        assert 'state how many were omitted and their combined savings' in served.instructions


async def test_defaults_yield_to_user_and_host_instructions():
    """The metric and credit defaults apply unless the user or the host's instructions say otherwise."""
    async with _served() as served:
        text = served.instructions
        qualifier = text.index("Unless the user or the host's instructions specify otherwise")
        assert (
            qualifier
            < text.index('UnblendedCost')
            < text.index('Report net cost, with credits and refunds included')
        )


async def test_rec_details_routing():
    """One COH recommendation routes to get_recommendation, enrichment to rec-details."""
    async with _served() as served:
        assert (
            'Use cost-optimization `get_recommendation` for one Cost Optimization Hub recommendation; '
            'use rec-details only when Compute Optimizer and Cost Explorer enrichment is wanted'
        ) in served.instructions
        assert 'get_recommendation' in served.tools['cost-optimization'].description


async def test_multi_account_parameters_exist_in_the_served_schemas():
    """The multi-account guidance names the parameters each tool really takes."""
    async with _served() as served:
        co = served.tools['compute-optimizer'].inputSchema['properties']
        coh = served.tools['cost-optimization'].inputSchema['properties']
        assert 'accountIds' not in co and 'accountIds' not in coh
        assert 'account_ids' in co and 'single' in co['account_ids']['description']
        assert 'filters' in coh and 'accountIds' in served.tools['cost-optimization'].description
        assert 'list_enrollment_statuses only' in coh['account_id']['description']
        text = served.instructions
        assert (
            'compute-optimizer takes `account_ids` as a JSON array with one account ID per call'
            in text
        )
        assert '{"accountIds": ["123456789012"]}' in text
        assert 'top-level `account_id` applies only to `list_enrollment_statuses`' in text


async def test_identifiers_in_instructions_exist():
    """Class guard: every backticked identifier is a tool, parameter, operation or field."""
    async with _served() as served:
        assert _unknown_identifiers(served.instructions, served.tools) == []


async def test_guidance_names_only_mounted_tools():
    """Every tool name in the instructions is a mounted tool."""
    async with _served() as served:
        named = (
            set(re.findall(r'\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b', served.instructions))
            - _ENGLISH_COMPOUNDS
        )
        assert named, 'guidance names no tool'
        assert sorted(named - set(served.tools)) == []


async def test_coh_response_fields_named_by_the_prompts_exist():
    """The list_recommendations fields the Graviton prompt names are the formatter's keys."""
    coh_client = MagicMock()
    coh_client.list_recommendations.return_value = {'items': [{'recommendationId': 'r'}]}
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    with patch(
        'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
        lambda _size: False,
    ):
        result = await list_recommendations(context, coh_client)
    assert COH_RECOMMENDATION_FIELDS <= set(result['data']['recommendations'][0])


# --- Item 5: prompts name real tools and operations ---


@pytest.mark.parametrize('prompt', sorted(PROMPT_ARGS))
async def test_prompt_names_only_served_tools_and_operations(prompt):
    """Each `tool` `operation` pair in a rendered prompt exists on the server."""
    async with _served() as served:
        text = await _rendered(served, prompt)
        pairs = re.findall(r'`([a-z][a-z0-9-]+)` `([a-z0-9_]+)`', text)
        assert pairs, 'prompt names no tool operation'
        for tool, operation in pairs:
            assert tool in served.tools, f'{prompt} references unknown tool {tool!r}'
            assert re.search(rf'\b{operation}\b', _tool_text(served.tools[tool])), (
                f'{prompt}: {tool} has no operation {operation!r}'
            )
        assert _unknown_identifiers(text, served.tools) == []
        for stale in (
            'compute_optimizer_get_ec2_instance_recommendations',
            'cost_explorer_get_savings_plans_purchase_recommendation',
        ):
            assert stale not in text


async def test_registered_prompt_arguments():
    """The prompts take only arguments their steps use."""
    async with _served() as served:
        graviton = {a.name for a in served.prompts['analyze_graviton_opportunities'].arguments}
        assert graviton == {'account_ids', 'region'}  # lookback_days dropped: no tool takes it
        sp = {a.name for a in served.prompts['analyze_savings_plans_opportunities'].arguments}
        assert sp == {'account_ids', 'lookback_days', 'term_in_years', 'payment_option'}


def _group(pattern, text):
    """The first group of ``pattern`` in ``text``; fails the test if it does not match."""
    match = re.search(pattern, text)
    assert match, f'{pattern!r} not found'
    return match.group(1)


def _message_text(messages):
    content = messages[0].content
    assert isinstance(content, TextContent)
    return content.text


def _graviton_text(*args):
    return _message_text(graviton_migration_analysis(*args))


def test_graviton_prompt_requests_arm_options_and_tool_effort():
    """The Graviton prompt asks for ARM64 options and uses the tool-reported effort."""
    text = _graviton_text('111111111111, 222222222222', 'us-east-1')
    filters = json.loads(_group(r"`filters` '([^']+)'", text))
    assert filters == {
        'actionTypes': ['MigrateToGraviton'],
        'accountIds': ['111111111111', '222222222222'],
        'regions': ['us-east-1'],
    }
    assert "`group_by` 'ResourceType'" in text
    order_by = json.loads(_group(r"`order_by` '([^']+)'", text))
    assert order_by == {'dimension': 'EstimatedMonthlySavings', 'order': 'Desc'}
    assert json.loads(_group(r"`cpu_vendor_architectures` '([^']+)'", text)) == ['AWS_ARM64']
    assert 'implementation_effort' in text and 'do not grade effort yourself' in text
    assert 'Easy, Medium, Complex' not in text
    assert 'Lookback' not in text


def test_graviton_prompt_without_region_or_accounts():
    """Empty account and region arguments are left out of the COH filter."""
    text = _graviton_text('', '')
    filters = json.loads(_group(r"`filters` '([^']+)'", text))
    assert filters == {'actionTypes': ['MigrateToGraviton']}  # COH rejects empty lists
    assert 'Analyze all regions' in text


def _sp_text(*args):
    return _message_text(savings_plans_analysis(*args))


@pytest.mark.parametrize(
    ('days', 'period', 'note'),
    [
        (7, 'SEVEN_DAYS', False),
        (30, 'THIRTY_DAYS', False),
        (60, 'SIXTY_DAYS', False),
        (14, 'SEVEN_DAYS', True),
        (90, 'SIXTY_DAYS', True),
    ],
)
def test_sp_prompt_maps_lookback_to_supported_period(days, period, note):
    """lookback_days maps to the closest lookback period the API accepts."""
    text = _sp_text('111111111111', days)
    assert f'`lookback_period_in_days` {period}' in text
    assert ('recommendations support 7, 30 or 60 days' in text) is note


@pytest.mark.parametrize(
    ('years', 'term', 'label'),
    [
        (1, 'ONE_YEAR', '1 year\n'),
        ('1', 'ONE_YEAR', '1 year\n'),
        ('3', 'THREE_YEARS', '3 years\n'),
    ],
)
def test_sp_prompt_term(years, term, label):
    """term_in_years maps to the API term value; MCP passes prompt arguments as strings."""
    text = _sp_text('111111111111', 30, years)
    assert f'`term_in_years` {term}' in text
    assert f'Savings Plans term length: {label}' in text


@pytest.mark.parametrize('years', [2, 5, '2', 0])
def test_sp_prompt_rejects_unsupported_term(years):
    """Savings Plans terms are 1 or 3 years; any other term is rejected, not sent as ONE_YEAR."""
    with pytest.raises(ValueError, match='term_in_years must be 1 or 3'):
        _sp_text('111111111111', 30, years)


async def test_served_sp_prompt_rejects_unsupported_term():
    """Over MCP (string arguments), an unsupported term reaches the client as an error."""
    async with _served() as served:
        with pytest.raises(McpError, match='term_in_years must be 1 or 3, got 2'):
            await served.client.get_prompt(
                'analyze_savings_plans_opportunities', {**SP_ARGS, 'term_in_years': '2'}
            )


@pytest.mark.parametrize(
    ('given', 'sent'),
    [
        ('NO_UPFRONT', 'NO_UPFRONT'),
        ('all_upfront', 'ALL_UPFRONT'),
        (' Partial_Upfront ', 'PARTIAL_UPFRONT'),
    ],
)
def test_sp_prompt_normalizes_payment_option(given, sent):
    """payment_option is upper-cased to the API value."""
    assert f'`payment_option` {sent} ' in _sp_text('111111111111', 30, 1, given)


@pytest.mark.parametrize('given', ['all upfront', 'HEAVY_UTILIZATION', ''])
def test_sp_prompt_rejects_unsupported_payment_option(given):
    """Only the three Savings Plans payment options are accepted (the RI utilization values are not)."""
    with pytest.raises(
        ValueError,
        match=re.escape(
            f'payment_option must be NO_UPFRONT, PARTIAL_UPFRONT or ALL_UPFRONT, got {given!r}'
        ),
    ):
        _sp_text('111111111111', 30, 1, given)


def test_sp_prompt_account_filter_and_payment_option():
    """Accounts become a LINKED_ACCOUNT filter; payment_option ALL_UPFRONT is sent unchanged."""
    text = _sp_text('111111111111, 222222222222', 30, 1, 'ALL_UPFRONT')
    assert '`payment_option` ALL_UPFRONT' in text
    account_filter = json.loads(_group(r'`filter` (\{.*\})\.', text))
    assert account_filter == {
        'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': ['111111111111', '222222222222']}
    }
    assert '`filter`' not in _sp_text('', 30)
    assert 'break-even' not in text
