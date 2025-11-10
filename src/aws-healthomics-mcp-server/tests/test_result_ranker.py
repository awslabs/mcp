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

"""Tests for result ranker."""

import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileResult,
    GenomicsFileType,
)
from awslabs.aws_healthomics_mcp_server.search.result_ranker import ResultRanker
from datetime import datetime, timezone


class TestResultRanker:
    """Test cases for result ranker."""

    @pytest.fixture
    def ranker(self):
        """Create a test result ranker."""
        return ResultRanker()

    @pytest.fixture
    def sample_results(self):
        """Create sample genomics file results with different relevance scores."""
        results = []

        # Create sample GenomicsFile objects
        files = [
            GenomicsFile(
                path=f's3://bucket/file{i}.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000000 + i * 100000,
                storage_class='STANDARD',
                last_modified=datetime(2023, 1, i + 1, tzinfo=timezone.utc),
                tags={'sample_id': f'sample_{i}'},
                source_system='s3',
                metadata={'description': f'Sample file {i}'},
            )
            for i in range(5)
        ]

        # Create GenomicsFileResult objects with different relevance scores
        scores = [0.95, 0.75, 0.85, 0.65, 0.55]  # Intentionally not sorted
        for i, (file, score) in enumerate(zip(files, scores)):
            result = GenomicsFileResult(
                primary_file=file,
                associated_files=[],
                relevance_score=score,
                match_reasons=[f'Matched search term in file {i}'],
            )
            results.append(result)

        return results

    def test_init(self, ranker):
        """Test ResultRanker initialization."""
        assert isinstance(ranker, ResultRanker)

    def test_rank_results_by_relevance_score(self, ranker, sample_results):
        """Test ranking results by relevance score."""
        ranked = ranker.rank_results(sample_results, 'relevance_score')

        # Should be sorted by relevance score in descending order
        assert len(ranked) == 5
        assert ranked[0].relevance_score == 0.95  # Highest score first
        assert ranked[1].relevance_score == 0.85
        assert ranked[2].relevance_score == 0.75
        assert ranked[3].relevance_score == 0.65
        assert ranked[4].relevance_score == 0.55  # Lowest score last

        # Verify all results are present
        original_scores = {r.relevance_score for r in sample_results}
        ranked_scores = {r.relevance_score for r in ranked}
        assert original_scores == ranked_scores

    def test_rank_results_empty_list(self, ranker):
        """Test ranking empty results list."""
        ranked = ranker.rank_results([])
        assert ranked == []

    def test_rank_results_single_result(self, ranker, sample_results):
        """Test ranking single result."""
        single_result = [sample_results[0]]
        ranked = ranker.rank_results(single_result)

        assert len(ranked) == 1
        assert ranked[0] == sample_results[0]

    def test_rank_results_unsupported_sort_by(self, ranker, sample_results):
        """Test ranking with unsupported sort_by parameter."""
        # Should default to relevance_score and log warning
        ranked = ranker.rank_results(sample_results, 'unsupported_field')

        # Should still be sorted by relevance score
        assert len(ranked) == 5
        assert ranked[0].relevance_score == 0.95
        assert ranked[4].relevance_score == 0.55

    def test_rank_results_identical_scores(self, ranker):
        """Test ranking results with identical relevance scores."""
        # Create results with same scores
        files = [
            GenomicsFile(
                path=f's3://bucket/file{i}.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000000,
                storage_class='STANDARD',
                last_modified=datetime.now(timezone.utc),
                tags={},
                source_system='s3',
                metadata={},
            )
            for i in range(3)
        ]

        results = [
            GenomicsFileResult(
                primary_file=file,
                associated_files=[],
                relevance_score=0.8,  # Same score for all
                match_reasons=['test'],
            )
            for file in files
        ]

        ranked = ranker.rank_results(results)

        assert len(ranked) == 3
        # All should have same score
        for result in ranked:
            assert result.relevance_score == 0.8

    def test_apply_pagination_basic(self, ranker, sample_results):
        """Test basic pagination functionality."""
        # First page: offset=0, max_results=2
        page1 = ranker.apply_pagination(sample_results, max_results=2, offset=0)
        assert len(page1) == 2
        assert page1[0] == sample_results[0]
        assert page1[1] == sample_results[1]

        # Second page: offset=2, max_results=2
        page2 = ranker.apply_pagination(sample_results, max_results=2, offset=2)
        assert len(page2) == 2
        assert page2[0] == sample_results[2]
        assert page2[1] == sample_results[3]

        # Third page: offset=4, max_results=2 (only 1 result left)
        page3 = ranker.apply_pagination(sample_results, max_results=2, offset=4)
        assert len(page3) == 1
        assert page3[0] == sample_results[4]

    def test_apply_pagination_empty_list(self, ranker):
        """Test pagination with empty results list."""
        paginated = ranker.apply_pagination([], max_results=10, offset=0)
        assert paginated == []

    def test_apply_pagination_invalid_offset(self, ranker, sample_results):
        """Test pagination with invalid offset."""
        # Negative offset should be corrected to 0
        paginated = ranker.apply_pagination(sample_results, max_results=2, offset=-5)
        assert len(paginated) == 2
        assert paginated[0] == sample_results[0]

        # Offset beyond results should return empty list
        paginated = ranker.apply_pagination(sample_results, max_results=2, offset=10)
        assert paginated == []

    def test_apply_pagination_invalid_max_results(self, ranker, sample_results):
        """Test pagination with invalid max_results."""
        # Zero max_results should be corrected to 100
        paginated = ranker.apply_pagination(sample_results, max_results=0, offset=0)
        assert len(paginated) == 5  # All results since we have only 5

        # Negative max_results should be corrected to 100
        paginated = ranker.apply_pagination(sample_results, max_results=-10, offset=0)
        assert len(paginated) == 5  # All results since we have only 5

    def test_apply_pagination_large_max_results(self, ranker, sample_results):
        """Test pagination with max_results larger than available results."""
        paginated = ranker.apply_pagination(sample_results, max_results=100, offset=0)
        assert len(paginated) == 5  # All available results
        assert paginated == sample_results

    def test_get_ranking_statistics_basic(self, ranker, sample_results):
        """Test basic ranking statistics."""
        stats = ranker.get_ranking_statistics(sample_results)

        assert stats['total_results'] == 5
        assert 'score_statistics' in stats
        assert 'score_distribution' in stats

        score_stats = stats['score_statistics']
        assert score_stats['min_score'] == 0.55
        assert score_stats['max_score'] == 0.95
        assert score_stats['mean_score'] == (0.95 + 0.75 + 0.85 + 0.65 + 0.55) / 5
        assert score_stats['score_range'] == 0.95 - 0.55

        # Check score distribution
        distribution = stats['score_distribution']
        assert 'high' in distribution
        assert 'medium' in distribution
        assert 'low' in distribution
        assert distribution['high'] + distribution['medium'] + distribution['low'] == 5

    def test_get_ranking_statistics_empty_list(self, ranker):
        """Test ranking statistics with empty results list."""
        stats = ranker.get_ranking_statistics([])

        assert stats['total_results'] == 0
        assert stats['score_statistics'] == {}

    def test_get_ranking_statistics_single_result(self, ranker, sample_results):
        """Test ranking statistics with single result."""
        single_result = [sample_results[0]]
        stats = ranker.get_ranking_statistics(single_result)

        assert stats['total_results'] == 1
        score_stats = stats['score_statistics']
        assert score_stats['min_score'] == sample_results[0].relevance_score
        assert score_stats['max_score'] == sample_results[0].relevance_score
        assert score_stats['mean_score'] == sample_results[0].relevance_score
        assert score_stats['score_range'] == 0.0

        # With zero range, all results should be in 'high' bucket
        distribution = stats['score_distribution']
        assert distribution['high'] == 1
        assert distribution['medium'] == 0
        assert distribution['low'] == 0

    def test_get_ranking_statistics_identical_scores(self, ranker):
        """Test ranking statistics with identical scores."""
        # Create results with identical scores
        files = [
            GenomicsFile(
                path=f's3://bucket/file{i}.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000000,
                storage_class='STANDARD',
                last_modified=datetime.now(timezone.utc),
                tags={},
                source_system='s3',
                metadata={},
            )
            for i in range(3)
        ]

        results = [
            GenomicsFileResult(
                primary_file=file,
                associated_files=[],
                relevance_score=0.7,  # Same score for all
                match_reasons=['test'],
            )
            for file in files
        ]

        stats = ranker.get_ranking_statistics(results)

        assert stats['total_results'] == 3
        score_stats = stats['score_statistics']
        assert score_stats['min_score'] == 0.7
        assert score_stats['max_score'] == 0.7
        assert score_stats['mean_score'] == pytest.approx(0.7)
        assert score_stats['score_range'] == 0.0

        # With zero range, all results should be in 'high' bucket
        distribution = stats['score_distribution']
        assert distribution['high'] == 3
        assert distribution['medium'] == 0
        assert distribution['low'] == 0

    def test_full_workflow(self, ranker, sample_results):
        """Test complete workflow: rank, paginate, and get statistics."""
        # Step 1: Rank results
        ranked = ranker.rank_results(sample_results)
        assert ranked[0].relevance_score == 0.95  # Highest first

        # Step 2: Apply pagination
        page1 = ranker.apply_pagination(ranked, max_results=3, offset=0)
        assert len(page1) == 3
        assert page1[0].relevance_score == 0.95
        assert page1[1].relevance_score == 0.85
        assert page1[2].relevance_score == 0.75

        # Step 3: Get statistics
        stats = ranker.get_ranking_statistics(ranked)
        assert stats['total_results'] == 5
        assert stats['score_statistics']['max_score'] == 0.95
        assert stats['score_statistics']['min_score'] == 0.55

    def test_edge_cases_with_extreme_scores(self, ranker):
        """Test edge cases with extreme relevance scores."""
        # Create results with extreme scores
        files = [
            GenomicsFile(
                path=f's3://bucket/file{i}.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000000,
                storage_class='STANDARD',
                last_modified=datetime.now(timezone.utc),
                tags={},
                source_system='s3',
                metadata={},
            )
            for i in range(3)
        ]

        results = [
            GenomicsFileResult(
                primary_file=files[0],
                associated_files=[],
                relevance_score=0.0,  # Minimum score
                match_reasons=['test'],
            ),
            GenomicsFileResult(
                primary_file=files[1],
                associated_files=[],
                relevance_score=1.0,  # Maximum score
                match_reasons=['test'],
            ),
            GenomicsFileResult(
                primary_file=files[2],
                associated_files=[],
                relevance_score=0.5,  # Middle score
                match_reasons=['test'],
            ),
        ]

        # Test ranking
        ranked = ranker.rank_results(results)
        assert ranked[0].relevance_score == 1.0
        assert ranked[1].relevance_score == 0.5
        assert ranked[2].relevance_score == 0.0

        # Test statistics
        stats = ranker.get_ranking_statistics(ranked)
        assert stats['score_statistics']['min_score'] == 0.0
        assert stats['score_statistics']['max_score'] == 1.0
        assert stats['score_statistics']['score_range'] == 1.0
        assert stats['score_statistics']['mean_score'] == 0.5
