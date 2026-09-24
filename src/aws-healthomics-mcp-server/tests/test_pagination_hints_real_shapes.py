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
from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import list_runs
from awslabs.aws_healthomics_mcp_server.tools.workflow_management import list_workflows
from awslabs.aws_healthomics_mcp_server.utils.pagination import paginating
from datetime import datetime, timedelta, timezone

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
# list_runs (workflow_execution.py) uses this idiom's response shape too;
# its own date-filter truncation cases are pinned separately below in
# TestDictNextTokenIdiomAgainstRealListRunsDateFilterTruncation. list_workflows
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


class TestDictNextTokenIdiomAgainstRealListRunsDateFilterTruncation:
    """Wraps the real ``list_runs`` with a mocked ``get_omics_client``.

    Pins the two false-completeness cases in ListAHORuns' client-side
    date-filter truncation path: the ``== max_results`` boundary, and the
    falsy-token case where upstream is exhausted at the moment of
    truncation.
    """

    def _run_items(self, count: int):
        base_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        return [
            {
                'id': f'run-{i}',
                'name': f'run-{i}',
                'status': 'COMPLETED',
                'workflowId': f'wfl-{i}',
                'workflowType': 'WDL',
                'creationTime': base_time + timedelta(days=i),
            }
            for i in range(count)
        ]

    @pytest.mark.asyncio
    async def test_boundary_exact_max_results_with_upstream_token_is_incomplete(self):
        """Filtered set == max_results and an upstream current_token exists.

        Before the fix, the truncation check was strictly
        ``len(filtered_runs) > max_results``, so an exact match emitted no
        nextToken even though more matching runs might exist upstream, and
        the wrapper reported this page as COMPLETE.
        """
        mock_response = {
            'items': self._run_items(10),  # exactly max_results
            'nextToken': 'upstream-token-boundary',
        }

        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs.return_value = mock_response

        wrapped = paginating('ListAHORuns', list_runs)

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await wrapped(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after='2023-06-10T00:00:00Z',
                created_before=None,
                run_group_id=None,
            )

        assert len(result['runs']) == 10
        assert result.get('nextToken') == 'upstream-token-boundary'

        pagination = result['pagination']
        assert pagination['isComplete'] is False
        assert pagination['nextToken'] == 'upstream-token-boundary'
        assert 'no further calls are needed' not in pagination['instruction'].lower()

    @pytest.mark.asyncio
    async def test_truncation_with_no_upstream_token_reports_partial_not_complete(self):
        """Filtered set > max_results but upstream is exhausted (no current_token).

        Matching runs were discarded by the max_results slice and there is no
        token to hand back. Before the fix, list_runs emitted nothing extra,
        so the wrapper's dict/nextToken branch saw no token key and reported
        the page as COMPLETE -- fabricating certainty that no runs were
        dropped. The fix raises the pagination.has_more flag pagination.py's
        nested idiom already recognizes, routing into its honest
        is_complete=False / token=None path instead.
        """
        # No nextToken: upstream is exhausted on this single batch.
        mock_response = {'items': self._run_items(15)}

        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs.return_value = mock_response

        wrapped = paginating('ListAHORuns', list_runs)

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await wrapped(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after='2023-06-10T00:00:00Z',
                created_before=None,
                run_group_id=None,
            )

        assert len(result['runs']) == 10
        assert 'nextToken' not in result

        pagination = result['pagination']
        assert pagination['isComplete'] is False
        assert 'nextToken' not in pagination
        instruction = pagination['instruction'].lower()
        assert 'partial results' in instruction
        assert 'no further calls are needed' not in instruction
        # returnedCount must reflect the true number of runs actually
        # returned (10, in result['runs']), not the 'results' key this
        # idiom was originally written for -- list_runs' response uses
        # 'runs', not 'results'.
        assert pagination['returnedCount'] == 10

    @pytest.mark.asyncio
    async def test_boundary_exact_max_results_with_no_upstream_token_is_genuinely_complete(self):
        """Filtered set == max_results and upstream is exhausted (no current_token).

        No runs were discarded (the slice at max_results kept everything) and
        there are no further upstream pages, so this page really is complete:
        neither nextToken nor the pagination.has_more flag should be raised.
        """
        mock_response = {'items': self._run_items(10)}  # exactly max_results, no nextToken

        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs.return_value = mock_response

        wrapped = paginating('ListAHORuns', list_runs)

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await wrapped(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after='2023-06-10T00:00:00Z',
                created_before=None,
                run_group_id=None,
            )

        assert len(result['runs']) == 10
        assert 'nextToken' not in result

        pagination = result['pagination']
        assert pagination['isComplete'] is True
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

        search_paginated() mints a fresh continuation_token from
        next_global_token.encode() when has_more_results is True (see
        genomics_search_orchestrator.py's search_paginated()). The plain
        search() path also mints a fresh token now (str(next_offset), see
        that method's pagination_info construction), but this test targets
        search_paginated()'s own base64-JSON token shape specifically, so it
        still needs enable_storage_pagination=True to route to that method
        rather than search().
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
