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

"""Red-first reproduction for the non-advancing continuation_token defect.

``GenomicsSearchOrchestrator.search()`` (the default, non-storage-paginated
path used by ``search_genomics_files`` whenever
``enable_storage_pagination`` is left at its default ``False``) builds
``pagination_info['continuation_token']`` by echoing ``request.continuation_token``
straight back (see ``genomics_search_orchestrator.py`` around line 202,
commented ``# Pass through for now``). It never decodes an incoming
``continuation_token`` to resume from, and it never mints a fresh one from
``next_offset``. An agent that follows the ``paginating()`` wrapper's own
instruction text -- which always says to retry with
``continuation_token="<token>"`` for this tool, per
``utils/pagination.py``'s ``_continuation_param_name`` resolution -- gets
back either the same token it sent (an infinite loop) or ``None`` (a dead
end), and either way never advances past the first page.

No AWS credentials, account, or network access: ``_execute_parallel_searches``
and ``_score_results`` are patched directly, and the real ``result_ranker``,
``association_engine`` and ``json_builder`` run against in-memory fixtures.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileResult,
    GenomicsFileSearchRequest,
    GenomicsFileType,
    GlobalContinuationToken,
    SearchConfig,
)
from awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator import (
    GenomicsSearchOrchestrator,
)
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_config():
    """Minimal SearchConfig for a single S3 bucket, no HealthOmics engine."""
    return SearchConfig(
        s3_bucket_paths=['s3://test-bucket/'],
        enable_healthomics_search=False,
    )


@pytest.fixture
def orchestrator(mock_config):
    """GenomicsSearchOrchestrator with a mocked S3 engine and no real AWS calls."""
    mock_s3_engine = MagicMock()
    mock_s3_engine.search_buckets = AsyncMock()
    mock_s3_engine.cleanup_expired_cache_entries = MagicMock()

    with patch(
        'awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine.HealthOmicsSearchEngine.__init__',
        return_value=None,
    ):
        return GenomicsSearchOrchestrator(mock_config, s3_engine=mock_s3_engine)


@pytest.fixture
def five_ranked_results():
    """Five GenomicsFileResult objects with distinct, already-descending scores.

    Distinct descending scores make ``result_ranker.rank_results`` (real,
    unmocked) a no-op reordering, so pagination slices land on predictable
    file paths: page 1 (offset 0) is file0/file1, page 2 (offset 2) is
    file2/file3, etc.
    """
    results = []
    for i in range(5):
        genomics_file = GenomicsFile(
            path=f's3://test-bucket/file{i}.fastq',
            file_type=GenomicsFileType.FASTQ,
            size_bytes=1000,
            storage_class='STANDARD',
            last_modified=datetime.now(),
            source_system='s3',
        )
        results.append(
            GenomicsFileResult(
                primary_file=genomics_file,
                associated_files=[],
                relevance_score=0.95 - i * 0.05,
                match_reasons=['test'],
            )
        )
    return results


def _paths(response) -> list:
    return [r['primary_file']['path'] for r in response.enhanced_response['results']]


class TestContinuationTokenAdvances:
    """Pins that a resumed search with the emitted continuation_token moves forward."""

    @pytest.mark.asyncio
    async def test_continuation_token_is_present_when_more_results_exist(
        self, orchestrator, five_ranked_results
    ):
        """Falsifier for a dead-end token.

        If has_more is True but continuation_token comes back None, the
        wrapper's instruction ("call again with continuation_token=...") is
        a dead end. This must not happen.
        """
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token=None,
        )

        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = [r.primary_file for r in five_ranked_results]
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = five_ranked_results
                response = await orchestrator.search(request)

        pagination = response.enhanced_response['pagination']
        assert pagination['has_more'] is True
        assert pagination['continuation_token'] is not None, (
            'has_more is True but continuation_token is None: the agent has '
            'no usable cursor to continue with, per the wrapper instruction.'
        )

    @pytest.mark.asyncio
    async def test_resuming_with_continuation_token_returns_next_page_not_same_page(
        self, orchestrator, five_ranked_results
    ):
        """The actual pagination defect.

        Resuming with the emitted token must return page 2, not page 1
        again.
        """
        first_request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token=None,
        )

        async def run_search(request):
            with patch.object(
                orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
            ) as mock_execute:
                mock_execute.return_value = [r.primary_file for r in five_ranked_results]
                with patch.object(
                    orchestrator, '_score_results', new_callable=AsyncMock
                ) as mock_score:
                    mock_score.return_value = five_ranked_results
                    return await orchestrator.search(request)

        first_response = await run_search(first_request)
        first_pagination = first_response.enhanced_response['pagination']
        assert _paths(first_response) == [
            's3://test-bucket/file0.fastq',
            's3://test-bucket/file1.fastq',
        ]

        token = first_pagination['continuation_token']
        assert token is not None, 'no continuation_token emitted despite has_more=True'

        # A real agent has no reason to also resend offset: the wrapper's
        # instruction only ever mentions continuation_token for this tool.
        second_request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token=token,
        )
        second_response = await run_search(second_request)

        assert _paths(second_response) == [
            's3://test-bucket/file2.fastq',
            's3://test-bucket/file3.fastq',
        ], (
            'Resuming with the emitted continuation_token returned the same '
            'page again instead of advancing -- the cursor does not work.'
        )


class TestContinuationTokenEdgeCases:
    """Regression tests for two findings from the HIGH-effort code review of this fix.

    1. A negative continuation_token must not desync pagination_info from
       what apply_pagination() actually slices (it clamps negative offsets
       to 0 internally; pagination_info must reflect that same clamp).
    2. Supplying both offset and a conflicting continuation_token must not
       silently override the offset -- it must log a warning (still
       preferring continuation_token, since that is the cursor this method
       itself hands back and the wrapper only ever asks the agent to resend
       it, not offset).
    """

    async def _run_search(self, orchestrator, five_ranked_results, request):
        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = [r.primary_file for r in five_ranked_results]
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = five_ranked_results
                return await orchestrator.search(request)

    @pytest.mark.asyncio
    async def test_negative_continuation_token_is_clamped_consistently(
        self, orchestrator, five_ranked_results
    ):
        """pagination_info must match the offset apply_pagination() actually used."""
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token='-3',
        )

        response = await self._run_search(orchestrator, five_ranked_results, request)

        pagination = response.enhanced_response['pagination']
        # apply_pagination() clamps a negative offset to 0, so results must
        # be page-1 (file0/file1), and pagination_info's own offset must
        # say 0 too -- not the unclamped -3 -- or has_more/next_offset would
        # describe a page that was never actually returned.
        assert _paths(response) == [
            's3://test-bucket/file0.fastq',
            's3://test-bucket/file1.fastq',
        ]
        assert pagination['offset'] == 0
        assert pagination['next_offset'] == 2
        assert pagination['continuation_token'] == '2'

    @pytest.mark.asyncio
    async def test_conflicting_offset_and_continuation_token_logs_warning(
        self, orchestrator, five_ranked_results
    ):
        """continuation_token still wins, but the override must not be silent."""
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=3,
            continuation_token='1',
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.logger'
        ) as mock_logger:
            response = await self._run_search(orchestrator, five_ranked_results, request)

        assert _paths(response) == [
            's3://test-bucket/file1.fastq',
            's3://test-bucket/file2.fastq',
        ]
        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any(
            'offset=3' in call and 'continuation_token' in call for call in warning_calls
        ), f'expected a warning that the explicit offset was overridden, got: {warning_calls}'

    @pytest.mark.asyncio
    async def test_unparseable_continuation_token_raises_actionable_error(
        self, orchestrator, five_ranked_results
    ):
        """An unparseable continuation_token must raise a visible, actionable error.

        Before this fix, `int(token)` raising ValueError was caught, logged
        server-side only (via loguru, never reaching the MCP response), and
        effective_offset silently fell back to request.offset. The agent
        would see a normal, successful-looking page 1 with no signal that
        its supplied cursor was rejected -- the same "confident wrong
        instruction" failure class this whole fix exists to eliminate, just
        reachable via a garbage/foreign token instead of the original echo
        bug. It must now raise instead of silently falling back.
        """
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token='not-a-valid-token',
        )

        with pytest.raises(ValueError) as exc_info:
            await self._run_search(orchestrator, five_ranked_results, request)

        message = str(exc_info.value)
        assert 'not-a-valid-token' in message
        assert 'invalid' in message.lower() or 'could not be parsed' in message.lower()
        # Actionable: the agent must be told both a safe default (start over)
        # and how to supply a token that will actually work.
        assert 'no continuation_token' in message
        assert 'pagination block' in message

    @pytest.mark.asyncio
    async def test_absent_continuation_token_still_starts_from_request_offset(
        self, orchestrator, five_ranked_results
    ):
        """continuation_token=None must keep meaning 'use request.offset as-is'.

        This must not regress: an absent token is not an error, and offset
        alone (no token at all) must still page normally.
        """
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=2,
            continuation_token=None,
        )

        response = await self._run_search(orchestrator, five_ranked_results, request)

        assert _paths(response) == [
            's3://test-bucket/file2.fastq',
            's3://test-bucket/file3.fastq',
        ]
        pagination = response.enhanced_response['pagination']
        assert pagination['offset'] == 2


class TestPaginatedContinuationTokenEdgeCases:
    """Sibling of TestContinuationTokenEdgeCases for search_paginated().

    search_paginated() decodes continuation_token as a base64-JSON
    GlobalContinuationToken (a different encoding from search()'s plain
    offset integer), but shares the same failure mode this whole fix
    targets: before this fix, a ValueError from GlobalContinuationToken.decode
    was caught, logged server-side only via loguru, and silently replaced
    with a fresh GlobalContinuationToken. The agent would see a normal,
    successful-looking page 1 with has_more=True and no signal that its
    supplied cursor was rejected -- it could iterate forever without
    knowing. It must now raise the same actionable, agent-visible error as
    search() does for its own unparseable-token case.
    """

    async def _run_paginated_search(self, orchestrator, five_ranked_results, request):
        with patch.object(
            orchestrator, '_execute_parallel_paginated_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = (
                [r.primary_file for r in five_ranked_results],
                GlobalContinuationToken(),
                len(five_ranked_results),
            )
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = five_ranked_results
                return await orchestrator.search_paginated(request)

    @pytest.mark.asyncio
    async def test_unparseable_continuation_token_raises_actionable_error(
        self, orchestrator, five_ranked_results
    ):
        """An unparseable continuation_token must raise a visible, actionable error.

        Before this fix, GlobalContinuationToken.decode's ValueError was
        caught, logged server-side only, and global_token silently reset to
        a fresh GlobalContinuationToken -- indistinguishable from a real
        first page. It must now raise instead of silently resetting.
        """
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token='not-a-valid-token',
            enable_storage_pagination=True,
        )

        with pytest.raises(ValueError) as exc_info:
            await self._run_paginated_search(orchestrator, five_ranked_results, request)

        message = str(exc_info.value)
        assert 'not-a-valid-token' in message
        assert 'invalid' in message.lower() or 'could not be parsed' in message.lower()
        # Actionable: the agent must be told both a safe default (start over)
        # and how to supply a token that will actually work.
        assert 'no continuation_token' in message
        assert 'pagination block' in message

    @pytest.mark.asyncio
    async def test_empty_string_continuation_token_raises_actionable_error(
        self, orchestrator, five_ranked_results
    ):
        """continuation_token='' must raise, not silently start a fresh search.

        The decode guard is `if request.continuation_token:` (truthiness),
        so an empty string is falsy and skips the try/except entirely --
        global_token stays a fresh GlobalContinuationToken with no error,
        indistinguishable from a real first page. This is the exact same
        silent-reset failure class the rest of this fix exists to
        eliminate, just reachable via '' instead of garbage text.
        GlobalContinuationToken.decode('') itself does raise ValueError
        (confirmed directly), so this is purely the guard skipping the
        decode call, not a decode gap.
        """
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token='',
            enable_storage_pagination=True,
        )

        with pytest.raises(ValueError) as exc_info:
            await self._run_paginated_search(orchestrator, five_ranked_results, request)

        message = str(exc_info.value)
        assert 'no continuation_token' in message
        assert 'pagination block' in message

    @pytest.mark.asyncio
    async def test_absent_continuation_token_still_starts_fresh_search(
        self, orchestrator, five_ranked_results
    ):
        """continuation_token=None must still start a fresh paginated search.

        This must not regress: an absent token is not an error.
        """
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token=None,
            enable_storage_pagination=True,
        )

        response = await self._run_paginated_search(orchestrator, five_ranked_results, request)

        assert _paths(response) == [
            's3://test-bucket/file0.fastq',
            's3://test-bucket/file1.fastq',
        ]

    @pytest.mark.asyncio
    async def test_valid_continuation_token_still_resumes(self, orchestrator, five_ranked_results):
        """A valid continuation_token's behavior must not change at all."""
        token = GlobalContinuationToken(
            s3_tokens={'s3://test-bucket/': 'next-page-marker'},
            page_number=1,
            total_results_seen=2,
        ).encode()
        request = GenomicsFileSearchRequest(
            search_terms=['sample'],
            max_results=2,
            offset=0,
            continuation_token=token,
            enable_storage_pagination=True,
        )

        with patch.object(
            orchestrator, '_execute_parallel_paginated_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = (
                [r.primary_file for r in five_ranked_results[2:4]],
                GlobalContinuationToken(),
                2,
            )
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = five_ranked_results[2:4]
                response = await orchestrator.search_paginated(request)

            # The decoded token (s3_tokens, page_number, total_results_seen)
            # must reach _execute_parallel_paginated_searches unchanged.
            called_global_token = mock_execute.call_args[0][2]
            assert called_global_token.s3_tokens == {'s3://test-bucket/': 'next-page-marker'}
            assert called_global_token.page_number == 1
            assert called_global_token.total_results_seen == 2

        assert _paths(response) == [
            's3://test-bucket/file2.fastq',
            's3://test-bucket/file3.fastq',
        ]
