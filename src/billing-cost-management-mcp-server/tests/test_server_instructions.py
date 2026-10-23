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
from awslabs.billing_cost_management_mcp_server.server_instructions import (
    GUIDANCE,
    TOOL_BLURBS,
    build_instructions,
    first_sentence,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_helpers import (
    list_recommendations,
)
from contextlib import asynccontextmanager
from fastmcp import Client, Context
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
    """The served instructions, tools and prompts, plus the startup log lines."""
    _mount_once()
    with patch.object(server.logger, 'info') as info:
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
                log=[str(c.args[0]) for c in info.call_args_list if c.args],
            )


def _section_entries(instructions, header):
    match = re.search(rf'^{header}:\n((?:- .+\n?)+)', instructions, re.M)
    assert match, f'no {header}: section'
    return re.findall(r'^- ([A-Za-z0-9_\-]+):', match.group(1), re.M)


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


# --- Item 1: the TOOLS and PROMPTS sections are generated from what is served ---


async def test_tool_entries_are_exactly_the_served_tools():
    """Every TOOLS entry is a served tool and every served tool is listed, in order."""
    async with _served() as served:
        assert _section_entries(served.instructions, 'TOOLS') == list(served.tools)


async def test_tool_blurbs_match_the_mounted_tools():
    """A curated blurb exists for every mounted tool, and none for a tool that is gone."""
    async with _served() as served:
        curated = set(TOOL_BLURBS)
        assert sorted(set(served.tools) - curated) == [], 'mounted tools without a blurb'
        assert sorted(curated - set(served.tools)) == [], 'blurbs for tools that are not mounted'


async def test_prompt_entries_are_exactly_the_registered_prompts():
    """Every PROMPTS entry is a registered prompt and every prompt is listed."""
    async with _served() as served:
        assert _section_entries(served.instructions, 'PROMPTS') == list(served.prompts)


async def test_startup_log_names_match_registered():
    """The startup log lists the served tools and the registered prompt names."""
    async with _served() as served:
        log = served.log
        tools_at, prompts_at = log.index('Available tools:'), log.index('Available prompts:')
        logged_tools = [
            line[2:] for line in log[tools_at + 1 : prompts_at] if line.startswith('- ')
        ]
        logged_prompts = [line[2:] for line in log[prompts_at + 1 :] if line.startswith('- ')]
        assert logged_tools == list(served.tools)
        assert logged_prompts == list(served.prompts)


async def test_billing_view_tools_are_marked_read_only():
    """The billing-view tools carry "(read-only)", not "managing"."""
    async with _served() as served:
        entries = dict(re.findall(r'^- ([a-z0-9-]+): (.*)$', served.instructions, re.M))
        for name in ('get-billing-view', 'list-billing-views', 'list-billing-view-segments'):
            assert '(read-only)' in entries[name], name


def test_build_instructions_falls_back_to_first_sentence_and_ignores_unserved_blurbs():
    """A tool with no blurb uses its first sentence; a blurb for an unserved tool is dropped."""
    tools = [
        SimpleNamespace(name='known', description='Ignored. Because a blurb exists.'),
        SimpleNamespace(name='new-tool', description='Does a new thing.  Second sentence.'),
    ]
    text = build_instructions(tools, [], blurbs={'known': 'Curated', 'gone': 'Stale'})
    assert '- known: Curated\n' in text
    assert '- new-tool: Does a new thing\n' in text
    assert 'gone' not in text and 'Stale' not in text
    assert 'PROMPTS:' not in text


@pytest.mark.parametrize(
    ('description', 'expected'),
    [
        ('One. Two.', 'One'),
        ('  Multi\n line   text! Next', 'Multi line text!'),
        ('No terminator', 'No terminator'),
        (None, ''),
    ],
)
def test_first_sentence(description, expected):
    """first_sentence collapses whitespace and stops at the first sentence end."""
    assert first_sentence(description) == expected


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
        assert qualifier < text.index('UnblendedCost') < text.index('Exclude Credits and Refunds')


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
    """Every tool name in the workflow guidance is a mounted tool."""
    async with _served() as served:
        named = (
            set(re.findall(r'\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b', GUIDANCE)) - _ENGLISH_COMPOUNDS
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
        pairs = re.findall(r'`([a-z][a-z0-9-]+)` `([a-z_]+)`', text)
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


def _graviton_text(*args):
    return graviton_migration_analysis(*args)[0].content.text


def test_graviton_prompt_requests_arm_options_and_tool_effort():
    """The Graviton prompt asks for ARM64 options and uses the tool-reported effort."""
    text = _graviton_text('111111111111, 222222222222', 'us-east-1')
    filters = json.loads(re.search(r"`filters` '([^']+)'", text).group(1))
    assert filters == {
        'actionTypes': ['MigrateToGraviton'],
        'accountIds': ['111111111111', '222222222222'],
        'regions': ['us-east-1'],
    }
    assert "`group_by` 'ResourceType'" in text
    order_by = json.loads(re.search(r"`order_by` '([^']+)'", text).group(1))
    assert order_by == {'dimension': 'EstimatedMonthlySavings', 'order': 'Desc'}
    assert json.loads(re.search(r"`cpu_vendor_architectures` '([^']+)'", text).group(1)) == [
        'AWS_ARM64'
    ]
    assert 'implementation_effort' in text and 'do not grade effort yourself' in text
    assert 'Easy, Medium, Complex' not in text
    assert 'Lookback' not in text


def test_graviton_prompt_without_region_or_accounts():
    """Empty account and region arguments are left out of the COH filter."""
    text = _graviton_text('', '')
    filters = json.loads(re.search(r"`filters` '([^']+)'", text).group(1))
    assert filters == {'actionTypes': ['MigrateToGraviton']}  # COH rejects empty lists
    assert 'Analyze all regions' in text


def _sp_text(*args):
    return savings_plans_analysis(*args)[0].content.text


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


def test_sp_prompt_account_filter_and_payment_option():
    """Accounts become a LINKED_ACCOUNT filter; payment_option passes through."""
    text = _sp_text('111111111111, 222222222222', 30, 1, 'ALL_UPFRONT')
    assert '`payment_option` ALL_UPFRONT' in text
    account_filter = json.loads(re.search(r'`filter` (\{.*\})\.', text).group(1))
    assert account_filter == {
        'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': ['111111111111', '222222222222']}
    }
    assert '`filter`' not in _sp_text('', 30)
    assert 'break-even' not in text
