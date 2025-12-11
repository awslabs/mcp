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

"""Result ranking system for genomics file search results."""

from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_RESULT_RANKER_FALLBACK_SIZE
from awslabs.aws_healthomics_mcp_server.models import GenomicsFileResult
from loguru import logger
from typing import List


class ResultRanker:
    """Handles ranking and pagination of genomics file search results."""

    def __init__(self):
        """Initialize the result ranker."""
        pass

    def rank_results(
        self, results: List[GenomicsFileResult], sort_by: str = 'relevance_score'
    ) -> List[GenomicsFileResult]:
        """Sort results by relevance score in descending order.

        Args:
            results: List of GenomicsFileResult objects to rank
            sort_by: Field to sort by (default: "relevance_score")

        Returns:
            List of GenomicsFileResult objects sorted by relevance score in descending order
        """
        if not results:
            logger.info('No results to rank')
            return results

        # Sort by relevance score in descending order (highest scores first)
        if sort_by == 'relevance_score':
            ranked_results = sorted(results, key=lambda x: x.relevance_score, reverse=True)
        else:
            # Future extensibility for other sorting criteria
            logger.warning(
                f'Unsupported sort_by parameter: {sort_by}, defaulting to relevance_score'
            )
            ranked_results = sorted(results, key=lambda x: x.relevance_score, reverse=True)

        logger.info(f'Ranked {len(ranked_results)} results by {sort_by}')

        # Log top results for debugging (always log since logger.debug will handle level filtering)
        if ranked_results:
            top_scores = [f'{r.relevance_score:.3f}' for r in ranked_results[:5]]
            logger.debug(f'Top 5 relevance scores: {top_scores}')

        return ranked_results

    def apply_pagination(
        self, results: List[GenomicsFileResult], max_results: int, offset: int = 0
    ) -> List[GenomicsFileResult]:
        """Apply result limits and pagination to the ranked results.

        Args:
            results: List of ranked GenomicsFileResult objects
            max_results: Maximum number of results to return
            offset: Starting offset for pagination (default: 0)

        Returns:
            Paginated list of GenomicsFileResult objects
        """
        if not results:
            logger.info('No results to paginate')
            return results

        total_results = len(results)

        # Validate pagination parameters
        if offset < 0:
            logger.warning(f'Invalid offset {offset}, setting to 0')
            offset = 0

        if max_results <= 0:
            logger.warning(
                f'Invalid max_results {max_results}, setting to {DEFAULT_RESULT_RANKER_FALLBACK_SIZE}'
            )
            max_results = DEFAULT_RESULT_RANKER_FALLBACK_SIZE

        # Apply offset and limit
        start_index = offset
        end_index = min(offset + max_results, total_results)

        if start_index >= total_results:
            logger.info(
                f'Offset {offset} exceeds total results {total_results}, returning empty list'
            )
            return []

        paginated_results = results[start_index:end_index]

        logger.info(
            f'Applied pagination: offset={offset}, max_results={max_results}, '
            f'returning {len(paginated_results)} of {total_results} total results'
        )

        return paginated_results

    def get_ranking_statistics(self, results: List[GenomicsFileResult]) -> dict:
        """Get statistics about the ranking distribution.

        Args:
            results: List of GenomicsFileResult objects

        Returns:
            Dictionary containing ranking statistics
        """
        if not results:
            return {'total_results': 0, 'score_statistics': {}}

        scores = [result.relevance_score for result in results]

        statistics = {
            'total_results': len(results),
            'score_statistics': {
                'min_score': min(scores),
                'max_score': max(scores),
                'mean_score': sum(scores) / len(scores),
                'score_range': max(scores) - min(scores),
            },
        }

        # Add score distribution buckets
        if statistics['score_statistics']['score_range'] > 0:
            buckets = {'high': 0, 'medium': 0, 'low': 0}
            max_score = statistics['score_statistics']['max_score']
            min_score = statistics['score_statistics']['min_score']
            range_size = (max_score - min_score) / 3

            for score in scores:
                if score >= max_score - range_size:
                    buckets['high'] += 1
                elif score >= min_score + range_size:
                    buckets['medium'] += 1
                else:
                    buckets['low'] += 1

            statistics['score_distribution'] = buckets
        else:
            statistics['score_distribution'] = {'high': len(results), 'medium': 0, 'low': 0}

        return statistics
