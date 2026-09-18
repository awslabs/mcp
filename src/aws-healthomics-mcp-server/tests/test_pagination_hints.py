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

"""Tests for the automatic pagination continuation-hint wrapper.

Feature: pagination-continuation-hints

These are pure unit tests against small fake tool functions that mimic the
three real pagination idioms (bare ``nextToken`` in a dict, the ECR
``next_token`` dict variant, and the genomics search ``pagination.has_more``
block) plus the pass-through cases (errors, non-paginated tools). No AWS
client, session, or network call is touched anywhere in this file.

See ``test_pagination.py`` for the pre-existing, unrelated storage-level
pagination model tests (``StoragePaginationRequest``/``GlobalContinuationToken``
etc.); this module is intentionally separate to avoid colliding with those.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.utils.pagination import paginating
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Fake tool functions, one per idiom, shaped like the real ones they stand in
# for so that inspect.signature() sees the same parameter names.
# ---------------------------------------------------------------------------


async def _fake_list_workflows(
    ctx: Any = None,
    max_results: int = 10,
    next_token: Optional[str] = None,
    aws_profile: Optional[str] = None,
    aws_region: Optional[str] = None,
) -> Dict[str, Any]:
    if next_token == 'boom':
        return {'error': 'Error listing workflows: boom'}
    if next_token:
        return {'workflows': [{'id': 'wf-2'}], 'nextToken': 'page-3'}
    return {'workflows': [{'id': f'wf-{i}'} for i in range(25)], 'nextToken': 'page-2'}


async def _fake_list_workflows_complete(
    ctx: Any = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    return {'workflows': [{'id': f'wf-{i}'} for i in range(7)]}


async def _fake_list_ecr_repositories(
    ctx: Any = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    if next_token:
        return {'repositories': [], 'next_token': None, 'total_count': 0}
    return {
        'repositories': [{'repository_name': f'repo-{i}'} for i in range(3)],
        'next_token': 'ecr-page-2',
        'total_count': 3,
    }


async def _fake_search_genomics_files(
    ctx: Any = None,
    continuation_token: Optional[str] = None,
    offset: int = 0,
) -> Dict[str, Any]:
    if continuation_token:
        return {
            'results': [{'path': 's3://b/only.fastq'}],
            'pagination': {
                'offset': 0,
                'has_more': False,
                'continuation_token': None,
            },
        }
    return {
        'results': [{'path': f's3://b/f{i}.fastq'} for i in range(5)],
        'pagination': {
            'offset': 0,
            'has_more': True,
            'continuation_token': 'search-token-2',
        },
    }


async def _fake_search_genomics_files_offset_path(
    ctx: Any = None,
    continuation_token: Optional[str] = None,
    offset: int = 0,
) -> Dict[str, Any]:
    """Mimics the non-storage-pagination offset path's real quirk.

    genomics_search_orchestrator.py's plain search() sets has_more from the
    ranked-result count but passes the *input* continuation_token straight
    through unchanged (a pre-existing "pass through for now" behavior) --  so
    on a first call this is has_more=True with continuation_token still None.
    """
    return {
        'results': [{'path': f's3://b/f{i}.fastq'} for i in range(4)],
        'pagination': {
            'offset': 0,
            'has_more': True,
            'continuation_token': continuation_token,
        },
    }


async def _fake_list_with_no_list_field(
    ctx: Any = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Degenerate dict-idiom response with no list-valued field at all."""
    return {'count': 0}


async def _fake_non_paginated_tool(ctx: Any = None, workflow_id: str = '') -> Dict[str, Any]:
    return {'id': workflow_id, 'status': 'ACTIVE'}


async def _fake_error_only_tool(ctx: Any = None) -> Dict[str, Any]:
    return {'error': 'Something went wrong'}


# ---------------------------------------------------------------------------
# Dict / nextToken idiom
# ---------------------------------------------------------------------------


class TestDictNextTokenIdiom:
    """The ~17 list tools that carry a bare, camelCase ``nextToken``."""

    @pytest.mark.asyncio
    async def test_incomplete_page_gets_pagination_block(self):
        wrapped = paginating('ListAHOWorkflows', _fake_list_workflows)
        result = await wrapped(next_token=None)

        assert result['nextToken'] == 'page-2'  # existing field untouched
        assert len(result['workflows']) == 25  # existing field untouched
        assert result['pagination'] == {
            'isComplete': False,
            'returnedCount': 25,
            'nextToken': 'page-2',
            'instruction': (
                'PARTIAL RESULTS -- this is one page, not the full set. 25 item(s) '
                'returned and more exist. Call ListAHOWorkflows again with '
                'next_token="page-2" plus the same other arguments, and repeat '
                'until pagination.isComplete is true. Do not answer questions '
                "about totals, counts, or 'all' items from this page alone."
            ),
        }

    @pytest.mark.asyncio
    async def test_complete_page_still_gets_pagination_block(self):
        """Property 1: the block is emitted even when there is no next page."""
        wrapped = paginating('ListAHOWorkflows', _fake_list_workflows_complete)
        result = await wrapped(next_token=None)

        assert 'nextToken' not in result  # the tool never had one to begin with
        assert result['pagination']['isComplete'] is True
        assert result['pagination']['returnedCount'] == 7
        assert 'nextToken' not in result['pagination']
        assert 'no further' in result['pagination']['instruction'].lower()

    @pytest.mark.asyncio
    async def test_error_payload_passes_through_unchanged(self):
        wrapped = paginating('ListAHOWorkflows', _fake_list_workflows)
        result = await wrapped(next_token='boom')

        assert result == {'error': 'Error listing workflows: boom'}
        assert 'pagination' not in result

    @pytest.mark.asyncio
    async def test_non_paginated_tool_passes_through_unchanged(self):
        wrapped = paginating('GetAHOWorkflow', _fake_non_paginated_tool)
        result = await wrapped(workflow_id='wf-1')

        assert result == {'id': 'wf-1', 'status': 'ACTIVE'}

    @pytest.mark.asyncio
    async def test_unregistered_tool_with_error_only_passes_through(self):
        wrapped = paginating('SomeOtherTool', _fake_error_only_tool)
        result = await wrapped()

        assert result == {'error': 'Something went wrong'}

    @pytest.mark.asyncio
    async def test_no_list_field_defaults_returned_count_to_zero(self):
        """Degenerate response shape: still gets a block, with returnedCount 0."""
        wrapped = paginating('ListAHOWorkflows', _fake_list_with_no_list_field)
        result = await wrapped(next_token=None)

        assert result['pagination']['isComplete'] is True
        assert result['pagination']['returnedCount'] == 0


# ---------------------------------------------------------------------------
# ECR next_token (snake_case, always-present) idiom
# ---------------------------------------------------------------------------


class TestEcrNextTokenIdiom:
    """The two ECR list tools whose dicts come from a Pydantic ``model_dump()``."""

    @pytest.mark.asyncio
    async def test_incomplete_page(self):
        wrapped = paginating('ListECRRepositories', _fake_list_ecr_repositories)
        result = await wrapped(next_token=None)

        assert result['next_token'] == 'ecr-page-2'  # existing field, unchanged name/value
        assert result['total_count'] == 3  # existing field untouched
        assert result['pagination']['isComplete'] is False
        assert result['pagination']['nextToken'] == 'ecr-page-2'
        assert result['pagination']['returnedCount'] == 3
        assert 'next_token="ecr-page-2"' in result['pagination']['instruction']
        assert 'ListECRRepositories' in result['pagination']['instruction']

    @pytest.mark.asyncio
    async def test_complete_page_next_token_present_but_none(self):
        """ECR's model_dump() keeps the key with value None -- not omitted."""
        wrapped = paginating('ListECRRepositories', _fake_list_ecr_repositories)
        result = await wrapped(next_token='ecr-page-2')

        assert result['next_token'] is None
        assert result['pagination']['isComplete'] is True
        assert result['pagination']['returnedCount'] == 0
        assert 'nextToken' not in result['pagination']


# ---------------------------------------------------------------------------
# Search has_more_results idiom
# ---------------------------------------------------------------------------


class TestSearchHasMoreIdiom:
    """The genomics file search tool's existing nested ``pagination`` block."""

    @pytest.mark.asyncio
    async def test_incomplete_merges_into_existing_pagination_dict(self):
        wrapped = paginating('SearchGenomicsFiles', _fake_search_genomics_files)
        result = await wrapped(continuation_token=None)

        # Pre-existing fields of the *same* nested dict must survive untouched.
        assert result['pagination']['offset'] == 0
        assert result['pagination']['has_more'] is True
        assert result['pagination']['continuation_token'] == 'search-token-2'

        # New hint fields are merged in alongside them.
        assert result['pagination']['isComplete'] is False
        assert result['pagination']['returnedCount'] == 5
        assert result['pagination']['nextToken'] == 'search-token-2'
        assert 'SearchGenomicsFiles' in result['pagination']['instruction']
        # Property 3: the real parameter name for *this* tool, never next_token.
        assert 'continuation_token="search-token-2"' in result['pagination']['instruction']
        assert 'next_token=' not in result['pagination']['instruction']

    @pytest.mark.asyncio
    async def test_complete_case_still_emitted(self):
        wrapped = paginating('SearchGenomicsFiles', _fake_search_genomics_files)
        result = await wrapped(continuation_token='search-token-2')

        assert result['pagination']['has_more'] is False  # untouched existing field
        assert result['pagination']['isComplete'] is True
        assert result['pagination']['returnedCount'] == 1
        assert 'nextToken' not in result['pagination']

    @pytest.mark.asyncio
    async def test_has_more_with_no_usable_token_does_not_fabricate_one(self):
        """Regression test: has_more=True with a None token must not echo "None".

        The non-storage search path passes has_more independently of the
        token field, so it can legitimately report more results exist while
        the token itself is still None (e.g. the orchestrator's offset-based
        pass-through quirk). The instruction must flag this honestly rather
        than telling an agent to call back with continuation_token="None".
        """
        wrapped = paginating('SearchGenomicsFiles', _fake_search_genomics_files_offset_path)
        result = await wrapped(continuation_token=None)

        assert result['pagination']['has_more'] is True  # untouched existing field
        assert result['pagination']['isComplete'] is False
        assert result['pagination']['returnedCount'] == 4
        assert 'nextToken' not in result['pagination']
        assert 'None' not in result['pagination']['instruction']
        assert 'did not return a usable continuation_token' in result['pagination']['instruction']


# ---------------------------------------------------------------------------
# Property 3: continuation parameter name is derived from the real signature
# ---------------------------------------------------------------------------


class TestContinuationParamNameDerivation:
    """The instruction text always names the tool's real continuation parameter."""

    @pytest.mark.asyncio
    async def test_dict_idiom_uses_next_token_in_instruction(self):
        wrapped = paginating('ListAHOWorkflows', _fake_list_workflows)
        result = await wrapped(next_token=None)
        assert 'next_token=' in result['pagination']['instruction']

    @pytest.mark.asyncio
    async def test_search_idiom_uses_continuation_token_in_instruction(self):
        wrapped = paginating('SearchGenomicsFiles', _fake_search_genomics_files)
        result = await wrapped(continuation_token=None)
        assert 'continuation_token=' in result['pagination']['instruction']
        assert 'next_token=' not in result['pagination']['instruction']

    @pytest.mark.asyncio
    async def test_wrapper_preserves_wrapped_signature_for_schema_derivation(self):
        """Confirm functools.wraps preserves the original signature.

        FastMCP builds a tool's parameter schema from inspect.signature(fn);
        functools.wraps must keep that resolving to the original function so
        the registered tool's input schema is unaffected by the wrapper.
        """
        import inspect

        wrapped = paginating('ListAHOWorkflows', _fake_list_workflows)
        assert inspect.signature(wrapped) == inspect.signature(_fake_list_workflows)


# ---------------------------------------------------------------------------
# Registry integrity: every idiom-1/idiom-2 allowlist entry must name a tool
# that is actually registered, so a typo can't silently disable a hint.
# ---------------------------------------------------------------------------


class TestDictTokenKeysRegistryIntegrity:
    """Guards the ``_DICT_TOKEN_KEYS`` allowlist against silent drift.

    A typo'd or stale entry (a tool renamed in server.py without updating
    pagination.py, or vice versa) would not raise -- the wrapper would just
    quietly stop attaching a pagination block for that tool. This asserts the
    allowlist and the live, fully-registered server surface agree exactly.
    """

    async def test_every_allowlisted_tool_name_is_actually_registered(self):
        from awslabs.aws_healthomics_mcp_server.server import mcp
        from awslabs.aws_healthomics_mcp_server.utils.pagination import _DICT_TOKEN_KEYS

        registered = {tool.name for tool in await mcp.list_tools()}
        unregistered = set(_DICT_TOKEN_KEYS) - registered

        assert not unregistered, (
            f'_DICT_TOKEN_KEYS names tool(s) not registered in server.py: {unregistered}'
        )
