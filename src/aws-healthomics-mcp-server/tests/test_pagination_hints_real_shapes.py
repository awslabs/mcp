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

"""Regression guard: pin the pagination wrapper to REAL tool response shapes.

Feature: pagination-continuation-hints

``tests/test_pagination_hints.py`` only ever calls ``paginating()`` against
hand-written fake functions -- it proves the wrapper is internally
consistent, but nothing there fails if a real tool's response shape drifts
(a reordered field, a second list-valued field, an items list moved under a
new key). This file pins one representative real tool per idiom
(``list_workflows``, ``list_ecr_repositories``, ``search_genomics_files``) by
wrapping it with ``paginating()``, using the same client-mock seams as
``test_workflow_management.py`` / ``test_ecr_tools.py`` /
``test_genomics_file_search_integration_working.py``, and asserting on the
resulting ``pagination`` block against that tool's own real output. A future
change to any of these three functions that breaks the "exactly one list
field" or "token key" invariant the wrapper depends on will fail one of
these tests; verified directly by temporarily reproducing such a change
during development (see ``guard-DECISIONS.md`` in the task evidence). The
other ~16 registered tools sharing the dict/nextToken idiom are not
individually pinned here -- see ``guard-DECISIONS.md`` for why one
representative tool per idiom was judged sufficient for this task's scope.

No AWS credentials, account, or network access is used anywhere in this
file; all AWS-facing clients and the search orchestrator are mocked.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import list_ecr_repositories
from awslabs.aws_healthomics_mcp_server.tools.genomics_file_search import search_genomics_files
from awslabs.aws_healthomics_mcp_server.tools.workflow_management import list_workflows
from awslabs.aws_healthomics_mcp_server.utils.pagination import paginating

# Reusing test_ecr_tools.py's private mock-building helpers deliberately, per
# this task's brief, rather than duplicating a second copy of the ECR client
# mock scaffolding; if their signatures change, this file's ECR-idiom tests
# will fail loudly at import or call time.
from tests.test_ecr_tools import (
    _create_mock_ecr_client,
    _create_policy_not_found_exception,
    _create_sample_repository,
)
from tests.test_helpers import call_mcp_tool_directly
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Dict + nextToken idiom: ListAHOWorkflows.
#
# list_runs (workflow_execution.py) uses this idiom's response shape too, but
# is deliberately NOT pinned here: it has a separate, already-tracked
# false-completeness bug (client-side date filtering can truncate results
# without ever setting nextToken), and a guard test would either bake that
# bug in as "correct" or assert a fix that doesn't exist yet. list_workflows
# builds its response the same way (a single transformed list plus a
# conditionally-present nextToken key) without that complication, so it pins
# the idiom's shape invariant on its own.
# ---------------------------------------------------------------------------


class TestDictNextTokenIdiomAgainstRealListWorkflows:
    """Wraps the real ``list_workflows`` with a mocked ``get_omics_client``."""

    @pytest.mark.asyncio
    async def test_incomplete_page_pagination_block_matches_real_response(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_workflows.return_value = {
            'items': [
                {'id': 'wfl-1', 'name': 'wf-1', 'status': 'ACTIVE'},
                {'id': 'wfl-2', 'name': 'wf-2', 'status': 'ACTIVE'},
            ],
            'nextToken': 'real-next-token',
        }

        wrapped = paginating('ListAHOWorkflows', list_workflows)

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await wrapped(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                workflow_type=None,
                aws_profile=None,
                aws_region=None,
            )

        assert result['nextToken'] == 'real-next-token'
        assert len(result['workflows']) == 2

        pagination = result['pagination']
        assert pagination['isComplete'] is False
        assert pagination['returnedCount'] == len(result['workflows'])
        assert pagination['nextToken'] == 'real-next-token'
        assert 'ListAHOWorkflows' in pagination['instruction']
        assert 'next_token="real-next-token"' in pagination['instruction']

    @pytest.mark.asyncio
    async def test_complete_page_pagination_block_matches_real_response(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_workflows.return_value = {
            'items': [{'id': 'wfl-1', 'name': 'wf-1', 'status': 'ACTIVE'}],
            # No nextToken: this is the real function's own signal for the
            # last page (it only sets the key when AWS returns one).
        }

        wrapped = paginating('ListAHOWorkflows', list_workflows)

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ):
            result = await wrapped(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                workflow_type=None,
                aws_profile=None,
                aws_region=None,
            )

        assert 'nextToken' not in result
        assert len(result['workflows']) == 1

        pagination = result['pagination']
        assert pagination['isComplete'] is True
        assert pagination['returnedCount'] == len(result['workflows'])
        assert 'nextToken' not in pagination
        assert 'no further calls are needed' in pagination['instruction'].lower()


# ---------------------------------------------------------------------------
# Pydantic model_dump() + always-present next_token idiom: ListECRRepositories
# ---------------------------------------------------------------------------


class TestEcrNextTokenIdiomAgainstRealListEcrRepositories:
    """Wraps the real ``list_ecr_repositories`` with a mocked ``get_ecr_client``."""

    @pytest.mark.asyncio
    async def test_incomplete_page_pagination_block_matches_real_response(self):
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('repo-1')],
            'nextToken': 'real-ecr-next-token',
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()
        mock_ctx = AsyncMock()

        wrapped = paginating('ListECRRepositories', list_ecr_repositories)

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await wrapped(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
                aws_profile=None,
                aws_region=None,
            )

        assert result['next_token'] == 'real-ecr-next-token'
        assert result['total_count'] == len(result['repositories'])

        pagination = result['pagination']
        assert pagination['isComplete'] is False
        assert pagination['returnedCount'] == len(result['repositories'])
        assert pagination['nextToken'] == 'real-ecr-next-token'
        assert 'ListECRRepositories' in pagination['instruction']
        assert 'next_token="real-ecr-next-token"' in pagination['instruction']

    @pytest.mark.asyncio
    async def test_complete_page_pagination_block_matches_real_response(self):
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('repo-1')],
            # No nextToken key from AWS: the real function's model_dump()
            # still always emits the next_token *key*, but with value None.
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()
        mock_ctx = AsyncMock()

        wrapped = paginating('ListECRRepositories', list_ecr_repositories)

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await wrapped(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
                aws_profile=None,
                aws_region=None,
            )

        assert result['next_token'] is None

        pagination = result['pagination']
        assert pagination['isComplete'] is True
        assert pagination['returnedCount'] == len(result['repositories'])
        assert 'nextToken' not in pagination


# ---------------------------------------------------------------------------
# Search has_more / continuation_token idiom: SearchGenomicsFiles
# ---------------------------------------------------------------------------


class TestSearchIdiomAgainstRealSearchGenomicsFiles:
    """Wraps the real ``search_genomics_files`` with a mocked search orchestrator."""

    def _mock_response(
        self,
        has_more: bool,
        continuation_token,
        result_count: int,
        total_available: Optional[int] = None,
    ):
        results = [{'path': f's3://bucket/f{i}.bam'} for i in range(result_count)]
        enhanced_response = {
            'results': results,
            'total_found': result_count,
            'search_duration_ms': 42,
            'storage_systems_searched': ['s3'],
            'pagination': {
                'offset': 0,
                'limit': 100,
                'total_available': total_available
                if total_available is not None
                else result_count,
                'has_more': has_more,
                'continuation_token': continuation_token,
            },
        }
        mock_response = MagicMock()
        mock_response.results = results
        mock_response.total_found = result_count
        mock_response.search_duration_ms = 42
        mock_response.storage_systems_searched = ['s3']
        mock_response.enhanced_response = enhanced_response
        return mock_response

    @pytest.mark.asyncio
    async def test_incomplete_page_pagination_block_matches_real_response(self):
        """Exercises the storage-level pagination path (search_paginated()).

        Only this path can legitimately mint a fresh continuation_token
        (genomics_search_orchestrator.py's search_paginated() builds one from
        next_global_token.encode() when has_more_results is True); the plain
        search() path only ever passes the caller's own input token straight
        through (see genomics_search_orchestrator.py line ~202), so it can
        never produce this has_more=True + fresh-token shape. Using
        enable_storage_pagination=True here so the mocked method matches the
        real code path that can actually reach this state.
        """
        mock_ctx = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.search_paginated = AsyncMock(
            return_value=self._mock_response(
                has_more=True,
                continuation_token='real-search-token',
                result_count=3,
                total_available=10,
            )
        )

        wrapped = paginating('SearchGenomicsFiles', search_genomics_files)

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            return_value=mock_orchestrator,
        ):
            result = await call_mcp_tool_directly(
                wrapped,
                mock_ctx,
                file_type='bam',
                search_terms=['x'],
                enable_storage_pagination=True,
            )

        mock_orchestrator.search_paginated.assert_called_once()
        assert len(result['results']) == 3
        assert result['pagination']['has_more'] is True  # pre-existing field, untouched
        assert result['pagination']['continuation_token'] == 'real-search-token'

        pagination = result['pagination']
        assert pagination['isComplete'] is False
        assert pagination['returnedCount'] == len(result['results'])
        assert pagination['nextToken'] == 'real-search-token'
        assert 'SearchGenomicsFiles' in pagination['instruction']
        assert 'continuation_token="real-search-token"' in pagination['instruction']

    @pytest.mark.asyncio
    async def test_complete_page_pagination_block_matches_real_response(self):
        mock_ctx = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.search = AsyncMock(
            return_value=self._mock_response(
                has_more=False, continuation_token=None, result_count=1
            )
        )

        wrapped = paginating('SearchGenomicsFiles', search_genomics_files)

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            return_value=mock_orchestrator,
        ):
            result = await call_mcp_tool_directly(
                wrapped, mock_ctx, file_type='bam', search_terms=['x']
            )

        pagination = result['pagination']
        assert pagination['isComplete'] is True
        assert pagination['returnedCount'] == len(result['results'])
        assert 'nextToken' not in pagination
