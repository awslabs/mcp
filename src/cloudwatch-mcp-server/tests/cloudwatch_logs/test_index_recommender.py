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

"""Tests for the CWL field index recommender tool."""

import json
import pytest
import time
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender import (
    _build_field_usage,
    _extract_log_group_name,
    recommend_indexes_account,
    recommend_indexes_loggroup,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.query_parser import (
    detect_language as _detect_language,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.query_parser import (
    parse_query_fields,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.scoring import (
    AccountIndexRecommenderResult,
    IndexRecommenderResult,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def ctx():
    """Mock MCP context."""
    mock = AsyncMock()
    mock.info = AsyncMock()
    mock.warning = AsyncMock()
    mock.error = AsyncMock()
    return mock


def _epoch_ms(days_ago=0):
    """Return epoch milliseconds for N days ago."""
    return int((time.time() - days_ago * 86400) * 1000)


class TestParseQueryFields:
    """Tests for parse_query_fields."""

    def test_filter_equality(self):
        """Equality filter should be detected."""
        result = parse_query_fields('filter requestId = "abc123"')
        assert result.get('requestId') == 'filter_equality'

    def test_filter_index_equality(self):
        """FilterIndex equality should be detected."""
        result = parse_query_fields('filterIndex IPaddress = "198.51.100.0"')
        assert result.get('IPaddress') == 'filter_equality'

    def test_filter_in(self):
        """IN operator should be treated as equality filter."""
        result = parse_query_fields('filterIndex status IN ["200", "201"]')
        assert result.get('status') == 'filter_equality'

    def test_filter_like(self):
        """Like operator should be detected as non-equality filter."""
        result = parse_query_fields('filter @message like /ERROR/')
        # @message is a system field, but the regex should still match
        # Test with a non-system field
        result = parse_query_fields('filter errorCode like /Access/')
        assert result.get('errorCode') == 'filter_non_equality'

    def test_fields_clause(self):
        """Fields clause should extract display fields."""
        result = parse_query_fields('fields @timestamp, requestId, statusCode | limit 10')
        assert result.get('requestId') == 'display'
        assert result.get('statusCode') == 'display'

    def test_stats_by(self):
        """Stats by clause should extract display fields."""
        result = parse_query_fields('stats count(*) by eventSource, eventName')
        assert result.get('eventSource') == 'display'
        assert result.get('eventName') == 'display'

    def test_sort(self):
        """Sort clause should extract display fields."""
        result = parse_query_fields('sort duration desc')
        assert result.get('duration') == 'display'

    def test_equality_takes_priority_over_display(self):
        """If a field is used in both filter= and fields, filter_equality wins."""
        result = parse_query_fields('fields requestId, statusCode | filter requestId = "abc"')
        assert result.get('requestId') == 'filter_equality'

    def test_filter_and_condition(self):
        """Fields in 'filter a = x and b = y' should both be equality filters."""
        result = parse_query_fields('filter level = "ERROR" and requestId = "abc" | limit 10')
        assert result.get('level') == 'filter_equality'
        assert result.get('requestId') == 'filter_equality'

    def test_field_name_in_regex_value_not_extracted(self):
        """Field names inside regex patterns should not be extracted."""
        result = parse_query_fields('filter @message like /filter level = x/')
        # level is inside a regex value, should not be extracted
        assert 'level' not in result

    def test_numeric_prefixed_tokens_excluded(self):
        """Tokens starting with digits (5m, 1h, 30s) should not be extracted."""
        result = parse_query_fields('stats count(*) by 5m')
        assert '5m' not in result

    def test_complex_query(self):
        """Complex multi-clause query should classify all fields correctly."""
        query = (
            'fields @timestamp, @message '
            '| filter level = "ERROR" '
            '| filter path like /api/ '
            '| stats count(*) by statusCode '
            '| sort statusCode desc'
        )
        result = parse_query_fields(query)
        assert result.get('level') == 'filter_equality'
        assert result.get('path') == 'filter_non_equality'
        assert result.get('statusCode') == 'display'

    def test_empty_query(self):
        """Empty query should return no fields."""
        result = parse_query_fields('')
        assert result == {}

    def test_stats_alias_excluded(self):
        """Aliases created by 'as' should not be treated as fields."""
        result = parse_query_fields('stats count(*) as cnt by region')
        assert 'cnt' not in result
        assert result.get('region') == 'display'

    def test_parse_as_aliases_excluded(self):
        """Aliases from 'parse ... as var1, var2' should not be treated as fields."""
        result = parse_query_fields(
            'parse queryText "*@message like \'*\'*" as before, preval, after'
        )
        assert 'before' not in result
        assert 'preval' not in result
        assert 'after' not in result


class TestDetectLanguage:
    """Tests for _detect_language."""

    def test_cwli(self):
        """CWLI queries should be detected."""
        assert _detect_language('fields @timestamp | filter level = "ERROR"') == 'cwli'

    def test_sql(self):
        """SQL queries starting with SELECT should be detected."""
        assert _detect_language('SELECT * FROM `LogGroup` WHERE status = 200') == 'sql'

    def test_ppl(self):
        """PPL queries using where (not filter) should be detected."""
        assert _detect_language('SOURCE `lg` | where status = 200 | fields status') == 'ppl'

    def test_source_without_where_is_cwli(self):
        """SOURCE query without |where should be cwli."""
        assert _detect_language('SOURCE `lg` | stats count(*) by y') == 'cwli'

    def test_where_with_filter_is_cwli(self):
        """Query with both |where and |filter should be cwli."""
        assert _detect_language('fields @timestamp | filter x = 1 | where y = 2') == 'cwli'

    def test_where_without_filter_is_ppl(self):
        """Query with |where but no |filter and no SOURCE should be ppl."""
        assert _detect_language('fields @timestamp | where x = 1') == 'ppl'


class TestParseSqlFields:
    """Tests for SQL query parsing."""

    def test_where_equality(self):
        """SQL WHERE = should be detected as equality filter."""
        result = parse_query_fields("SELECT * FROM `lg` WHERE Operation = 'PutLogEvents'")
        assert result.get('Operation') == 'filter_equality'

    def test_where_in(self):
        """SQL WHERE IN should be detected as equality filter."""
        result = parse_query_fields('SELECT * FROM `lg` WHERE status IN (200, 201)')
        assert result.get('status') == 'filter_equality'

    def test_where_like(self):
        """SQL WHERE LIKE should be non-equality filter."""
        result = parse_query_fields("SELECT * FROM `lg` WHERE message LIKE '%error%'")
        assert result.get('message') == 'filter_non_equality'

    def test_select_fields(self):
        """SQL SELECT fields should be display."""
        result = parse_query_fields('SELECT Operation, RequestId FROM `lg`')
        assert result.get('Operation') == 'display'
        assert result.get('RequestId') == 'display'

    def test_group_by(self):
        """SQL GROUP BY fields should be display."""
        result = parse_query_fields('SELECT Operation, COUNT(*) FROM `lg` GROUP BY Operation')
        assert result.get('Operation') == 'display'

    def test_order_by(self):
        """SQL ORDER BY fields should be display."""
        result = parse_query_fields('SELECT * FROM `lg` ORDER BY duration DESC')
        assert result.get('duration') == 'display'

    def test_backtick_fields(self):
        """SQL backtick-quoted fields should be extracted."""
        result = parse_query_fields(
            "SELECT `@logStream`, Operation FROM `lg` WHERE `@logStream` = 'x'"
        )
        assert result.get('Operation') == 'display'

    def test_filterindex_sql(self):
        """SQL filterIndex should be detected."""
        result = parse_query_fields(
            "SELECT * FROM filterIndex('region' = 'us-east-1') WHERE status = 200"
        )
        assert result.get('region') == 'filter_equality'
        assert result.get('status') == 'filter_equality'

    def test_multi_condition_where(self):
        """Multiple WHERE conditions should all be detected."""
        result = parse_query_fields("SELECT * FROM `lg` WHERE a = 1 AND b = 2 AND c LIKE '%x%'")
        assert result.get('a') == 'filter_equality'
        assert result.get('b') == 'filter_equality'
        assert result.get('c') == 'filter_non_equality'


class TestParsePplFields:
    """Tests for PPL query parsing."""

    def test_where_equality(self):
        """PPL where = should be detected as equality filter."""
        result = parse_query_fields('SOURCE `lg` | where status = 200')
        assert result.get('status') == 'filter_equality'

    def test_where_like(self):
        """PPL where like should be non-equality filter."""
        result = parse_query_fields("SOURCE `lg` | where message like '%error%'")
        assert result.get('message') == 'filter_non_equality'

    def test_fields_command(self):
        """PPL fields command should extract display fields."""
        result = parse_query_fields('SOURCE `lg` | where x = 1 | fields Operation, RequestId')
        assert result.get('Operation') == 'display'
        assert result.get('RequestId') == 'display'

    def test_stats_by(self):
        """PPL stats by should extract display fields."""
        result = parse_query_fields('SOURCE `lg` | where x = 1 | stats count() by Operation')
        assert result.get('Operation') == 'display'

    def test_sort(self):
        """PPL sort should extract display fields."""
        result = parse_query_fields('SOURCE `lg` | where x = 1 | sort duration')
        assert result.get('duration') == 'display'

    def test_filterindex_ppl(self):
        """PPL filterIndex should be detected."""
        result = parse_query_fields(
            'SOURCE `lg` | filterIndex region = "us-east-1" | where status = 200'
        )
        assert result.get('region') == 'filter_equality'
        assert result.get('status') == 'filter_equality'

    def test_where_in_ppl(self):
        """PPL where IN should be equality filter."""
        result = parse_query_fields('SOURCE `lg` | where status IN ["200", "201"]')
        assert result.get('status') == 'filter_equality'


class TestExtractLogGroupName:
    """Tests for _extract_log_group_name."""

    def test_plain_name(self):
        """Plain log group name should be returned as-is."""
        assert _extract_log_group_name('/aws/lambda/my-func') == '/aws/lambda/my-func'

    def test_arn(self):
        """ARN should have the name extracted."""
        arn = 'arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/my-func'
        assert _extract_log_group_name(arn) == '/aws/lambda/my-func'

    def test_arn_govcloud(self):
        """GovCloud ARN should work too."""
        arn = 'arn:aws-us-gov:logs:us-gov-west-1:123456789012:log-group:/my/log'
        assert _extract_log_group_name(arn) == '/my/log'

    def test_arn_with_star_suffix(self):
        """ARN with :* resource suffix should strip it."""
        arn = 'arn:aws:logs:us-east-1:123456789012:log-group:/my/log:*'
        assert _extract_log_group_name(arn) == '/my/log'

    def test_none_query_string_handled(self):
        """None queryString in query history should not crash."""
        import time

        # Should not raise
        fu, uq = _build_field_usage(
            [{'queryString': None, 'createTime': int(time.time() * 1000)}],
            time.time(),
        )
        assert fu == {}
        assert len(uq) == 1  # None is still counted as a unique query string


@pytest.mark.asyncio
class TestRecommendIndexes:
    """Tests for recommend_indexes_loggroup."""

    async def test_no_queries_found(self, ctx):
        """No query history should return empty result with warning."""
        client = MagicMock()
        client.describe_queries.return_value = {'queries': []}

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert isinstance(result, IndexRecommenderResult)
        assert result.queries_analyzed == 0
        assert len(result.warnings) > 0

    async def test_only_system_fields(self, ctx):
        """Queries using only system fields should return no recommendations."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'fields @timestamp, @message | limit 10',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert result.queries_analyzed == 1
        assert len(result.recommendations) == 0
        assert 'system fields' in result.warnings[0].lower()

    async def test_already_indexed_field(self, ctx):
        """Fields already indexed should appear in already_indexed bucket."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter customField = "abc"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {
            'indexPolicies': [
                {
                    'policyDocument': json.dumps({'Fields': ['customField']}),
                    'source': 'LOG_GROUP',
                }
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert len(result.already_indexed) == 1
        assert result.already_indexed[0].field_name == 'customField'
        assert result.already_indexed[0].source == 'LOG_GROUP'
        assert len(result.recommendations) == 0

    async def test_field_not_found_in_log_data(self, ctx):
        """Fields not found in log data should appear in fields_not_found bucket."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter nonExistentField = "val"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}
        # Field existence query returns empty
        client.start_query.return_value = {'queryId': 'qid-1'}
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert len(result.fields_not_found) == 1
        assert result.fields_not_found[0].field_name == 'nonExistentField'

    async def test_full_recommendation_flow(self, ctx):
        """End-to-end: field exists, not indexed, gets scored."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1" | fields userId, action',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                },
                {
                    'queryString': 'filter userId = "u2"',
                    'createTime': _epoch_ms(3),
                    'status': 'Complete',
                },
                {
                    'queryString': 'fields action | limit 10',
                    'createTime': _epoch_ms(5),
                    'status': 'Complete',
                },
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        # Field existence: both userId and action exist
        call_count = 0

        def mock_start_query(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start_query

        def mock_get_results(**kwargs):
            qid = kwargs.get('queryId', '')
            if 'qid-1' in qid:
                # Field existence check
                return {
                    'status': 'Complete',
                    'results': [
                        [
                            {'field': 'userId', 'value': 'u1'},
                            {'field': 'action', 'value': 'login'},
                        ]
                    ],
                }
            # Cardinality checks
            return {
                'status': 'Complete',
                'results': [[{'field': 'cardinality', 'value': '500'}]],
            }

        client.get_query_results.side_effect = mock_get_results
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 1000000}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert result.queries_analyzed == 3
        assert len(result.recommendations) >= 1
        # userId should score higher (2 equality filters vs action with 0)
        user_rec = next((r for r in result.recommendations if r.field_name == 'userId'), None)
        assert user_rec is not None
        assert user_rec.score > 0
        assert user_rec.filter_equality_count == 2
        assert user_rec.action == 'CREATE_INDEX'

    async def test_old_queries_filtered_out(self, ctx):
        """Queries older than 30 days should be excluded."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter oldField = "val"',
                    'createTime': _epoch_ms(45),  # 45 days ago
                    'status': 'Complete',
                }
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert result.queries_analyzed == 0

    async def test_describe_queries_error_handled(self, ctx):
        """API errors should be caught and reported as warnings."""
        client = MagicMock()
        client.describe_queries.side_effect = Exception('AccessDenied')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert result.queries_analyzed == 0
        assert any('Error fetching' in w for w in result.warnings)

    async def test_scoring_recency_matters(self, ctx):
        """More recent queries should produce higher recency scores."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter recentField = "val"',
                    'createTime': _epoch_ms(1),  # 1 day ago
                    'status': 'Complete',
                },
                {
                    'queryString': 'filter oldField = "val"',
                    'createTime': _epoch_ms(25),  # 25 days ago
                    'status': 'Complete',
                },
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [
                [
                    {'field': 'recentField', 'value': 'v1'},
                    {'field': 'oldField', 'value': 'v2'},
                ]
            ],
        }
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        recent = next((r for r in result.recommendations if r.field_name == 'recentField'), None)
        old = next((r for r in result.recommendations if r.field_name == 'oldField'), None)
        assert recent is not None and old is not None
        assert recent.score_breakdown.recency_score > old.score_breakdown.recency_score

    async def test_arn_input_extracts_name_for_describe_queries(self, ctx):
        """ARN input should use name for DescribeQueries and ARN for DescribeIndexPolicies."""
        arn = 'arn:aws:logs:us-east-1:123456789012:log-group:/aws/test/lg1'
        client = MagicMock()
        client.describe_queries.return_value = {'queries': []}

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(ctx, log_group_identifier=arn)

        # DescribeQueries should be called with the extracted name
        call_kwargs = client.describe_queries.call_args[1]
        assert call_kwargs['logGroupName'] == '/aws/test/lg1'
        # Result should show the original ARN
        assert result.log_group == arn


@pytest.mark.asyncio
class TestRecommendIndexesAccount:
    """Tests for recommend_indexes_account."""

    async def test_no_queries(self, ctx):
        """No query history should return empty result."""
        client = MagicMock()
        client.describe_queries.return_value = {'queries': []}

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx)

        assert isinstance(result, AccountIndexRecommenderResult)
        assert result.total_queries_analyzed == 0
        assert result.log_group_results == []

    async def test_groups_by_log_group(self, ctx):
        """Queries from different log groups should produce separate results."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg1',
                    'status': 'Complete',
                },
                {
                    'queryString': 'filter orderId = "o1"',
                    'createTime': _epoch_ms(2),
                    'logGroupName': '/aws/lg2',
                    'status': 'Complete',
                },
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'field': 'userId', 'value': 'u1'}, {'field': 'orderId', 'value': 'o1'}]],
        }
        client.describe_log_groups.return_value = {
            'logGroups': [
                {'logGroupName': '/aws/lg1', 'storedBytes': 100},
                {'logGroupName': '/aws/lg2', 'storedBytes': 200},
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx)

        assert result.total_log_groups_analyzed == 2
        assert result.total_queries_analyzed == 2
        assert len(result.log_group_results) == 2

    async def test_api_error_handled(self, ctx):
        """API errors should be caught and reported."""
        client = MagicMock()
        client.describe_queries.side_effect = Exception('AccessDenied')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx)

        assert result.total_queries_analyzed == 0
        assert any('Error fetching' in w for w in result.warnings)

    async def test_system_fields_only_log_groups_excluded(self, ctx):
        """Log groups with only system field queries should not appear in results."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'fields @timestamp, @message | limit 10',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg-system-only',
                    'status': 'Complete',
                },
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg-with-fields',
                    'status': 'Complete',
                },
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx)

        # Only the log group with non-system fields should appear
        assert result.total_log_groups_analyzed == 2
        assert len(result.log_group_results) == 1
        assert result.log_group_results[0].log_group == '/aws/lg-with-fields'

    async def test_already_indexed_log_group_included(self, ctx):
        """Log groups where all fields are already indexed should still appear."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter Operation = "Put"',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg-indexed',
                    'status': 'Complete',
                }
            ],
        }
        # Account-level index policies (used by account tool)
        client.describe_account_policies.return_value = {
            'accountPolicies': [
                {
                    'policyDocument': json.dumps({'Fields': ['Operation']}),
                }
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx)

        assert len(result.log_group_results) == 1
        assert len(result.log_group_results[0].already_indexed) == 1


@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases and error paths."""

    async def test_non_equality_filter_penalty(self, ctx):
        """Fields used only with like/!= should get penalized eq_ratio."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter customError like /Access/',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'field': 'customError', 'value': 'AccessDenied'}]],
        }
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        rec = result.recommendations[0]
        # Non-equality filter gets 0.5x penalty on eq_ratio, so score should be low
        assert rec.filter_equality_count == 0
        assert rec.score_breakdown.filter_equality_score == 0.0

    async def test_display_only_field(self, ctx):
        """Fields used only in fields/stats (not filter) should still be recommended."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'stats count(*) by serviceName',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'field': 'serviceName', 'value': 'lambda'}]],
        }
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert len(result.recommendations) == 1
        assert result.recommendations[0].field_name == 'serviceName'
        assert result.recommendations[0].filter_equality_count == 0

    async def test_index_policy_api_failure(self, ctx):
        """DescribeIndexPolicies failure should warn but continue analysis."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.side_effect = Exception('AccessDenied')

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'field': 'userId', 'value': 'u1'}]],
        }
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        # Should still produce recommendations despite policy check failure
        assert len(result.recommendations) >= 1
        assert any('Could not fetch index policies' in w for w in result.warnings)

    async def test_describe_log_groups_failure(self, ctx):
        """DescribeLogGroups failure should warn but continue with 0 scan volume."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'field': 'userId', 'value': 'u1'}]],
        }
        client.describe_log_groups.side_effect = Exception('Throttled')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert len(result.recommendations) >= 1
        # scan_volume_score should be 0 since we couldn't fetch metadata
        assert result.recommendations[0].score_breakdown.scan_volume_score == 0.0

    async def test_malformed_cardinality_result(self, ctx):
        """Non-numeric cardinality result should default to 0."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start

        def mock_get_results(**kwargs):
            qid = kwargs.get('queryId', '')
            if 'qid-1' in qid:
                return {
                    'status': 'Complete',
                    'results': [[{'field': 'userId', 'value': 'u1'}]],
                }
            # Cardinality query returns non-numeric
            return {
                'status': 'Complete',
                'results': [[{'field': 'cardinality', 'value': 'not-a-number'}]],
            }

        client.get_query_results.side_effect = mock_get_results
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert len(result.recommendations) == 1
        assert result.recommendations[0].score_breakdown.cardinality_score == 0.0

    async def test_quick_query_exception(self, ctx):
        """start_query failure in _run_quick_query should return empty, not crash."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}
        client.start_query.side_effect = Exception('LimitExceeded')
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        # Field existence check failed, so field goes to not_found
        assert len(result.fields_not_found) == 1
        assert result.fields_not_found[0].field_name == 'userId'

    async def test_lightweight_non_equality_penalty(self, ctx):
        """Account-level lightweight analysis should penalize non-equality fields."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter customField like /pattern/',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg1',
                    'status': 'Complete',
                }
            ],
        }
        client.describe_account_policies.return_value = {'accountPolicies': []}

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx)

        assert len(result.log_group_results) == 1
        rec = result.log_group_results[0].recommendations[0]
        assert rec.filter_equality_count == 0

    async def test_account_policy_fetch_error(self, ctx):
        """Account-level index policy fetch failure should not crash."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg1',
                    'status': 'Complete',
                }
            ],
        }
        client.describe_account_policies.side_effect = Exception('AccessDenied')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx)

        assert len(result.log_group_results) == 1

    async def test_max_queries_cap_warning(self, ctx):
        """When query history hits max_queries cap, a warning should be emitted."""
        client = MagicMock()
        # Return exactly max_queries results to trigger the cap warning
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': f'filter field{i} = "val"',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg1',
                    'status': 'Complete',
                }
                for i in range(2)
            ],
        }
        client.describe_account_policies.return_value = {'accountPolicies': []}

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx, max_queries=2)

        assert any('capped' in w.lower() for w in result.warnings)

    async def test_parse_error_skipped(self, ctx):
        """Queries that fail to parse should be skipped, not crash."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'logGroupName': '/aws/lg1',
                    'status': 'Complete',
                },
            ],
        }
        client.describe_account_policies.return_value = {'accountPolicies': []}

        with (
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.parse_query_fields',
                side_effect=Exception('Parse boom'),
            ),
        ):
            result = await recommend_indexes_account(ctx)

        # Parse failed for all queries, so no recommendations
        assert result.total_queries_analyzed == 1

    async def test_ppl_detection_with_filter_and_where(self):
        """Query with both filter and where should detect as cwli, not ppl."""
        assert _detect_language('fields @timestamp | filter x = 1 | where y = 2') == 'cwli'

    async def test_pagination_cap_reached(self, ctx):
        """Pagination should stop when max_total is reached."""
        client = MagicMock()
        # Return exactly max_queries results with a nextToken
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter a = "1"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                },
                {
                    'queryString': 'filter b = "2"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                },
            ],
            'nextToken': 'more',
        }
        client.describe_account_policies.return_value = {'accountPolicies': []}

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_account(ctx, max_queries=2)

        # Should have analyzed exactly 2 queries (pagination stopped at cap)
        assert result.total_queries_analyzed == 2
        # describe_queries should only be called once (cap reached on first page)
        assert client.describe_queries.call_count == 1

    async def test_sql_order_by_display(self, ctx):
        """SQL ORDER BY fields should be classified as display."""
        result = parse_query_fields('SELECT * FROM `lg` ORDER BY duration DESC LIMIT 10')
        assert result.get('duration') == 'display'

    async def test_ppl_compound_and_equality(self, ctx):
        """PPL compound 'and field = val' should detect both fields as equality."""
        result = parse_query_fields(
            'SOURCE `lg` | filterIndex region = "us-east-1" and env = "prod"'
        )
        assert result.get('region') == 'filter_equality'
        assert result.get('env') == 'filter_equality'

    async def test_quick_query_timeout(self, ctx):
        """Quick query that never completes should return empty list."""
        client = MagicMock()
        client.describe_queries.return_value = {
            'queries': [
                {
                    'queryString': 'filter userId = "u1"',
                    'createTime': _epoch_ms(1),
                    'status': 'Complete',
                }
            ],
        }
        client.describe_index_policies.return_value = {'indexPolicies': []}
        client.start_query.return_value = {'queryId': 'qid-1'}
        # Always return Running — never completes
        client.get_query_results.return_value = {'status': 'Running', 'results': []}
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with (
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.QUERY_TIMEOUT', 1
            ),
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.asyncio.sleep',
                new_callable=AsyncMock,
            ),
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        # Field existence timed out, so field goes to not_found
        assert len(result.fields_not_found) == 1

    async def test_many_candidates_beyond_cardinality_top_n(self, ctx):
        """Fields beyond TOP_N_FOR_CARDINALITY should use base_score (no cardinality)."""
        client = MagicMock()
        # Create 12 queries with different fields to exceed TOP_N_FOR_CARDINALITY (10)
        queries = [
            {
                'queryString': f'filter field{i} = "val"',
                'createTime': _epoch_ms(1),
                'status': 'Complete',
            }
            for i in range(12)
        ]
        client.describe_queries.return_value = {'queries': queries}
        client.describe_index_policies.return_value = {'indexPolicies': []}

        call_count = 0

        def mock_start(**kwargs):
            nonlocal call_count
            call_count += 1
            return {'queryId': f'qid-{call_count}'}

        client.start_query.side_effect = mock_start

        def mock_get_results(**kwargs):
            qid = kwargs.get('queryId', '')
            if 'qid-1' in qid:
                # Field existence: all 12 fields exist
                return {
                    'status': 'Complete',
                    'results': [[{'field': f'field{i}', 'value': f'v{i}'} for i in range(12)]],
                }
            # Cardinality query for top 10
            return {
                'status': 'Complete',
                'results': [[{f'card_{i}': '100'} for i in range(10)]],
            }

        client.get_query_results.side_effect = mock_get_results
        client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/test/lg1', 'storedBytes': 100}],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender.get_aws_client',
            return_value=client,
        ):
            result = await recommend_indexes_loggroup(
                ctx,
                log_group_identifier='/aws/test/lg1',
            )

        assert len(result.recommendations) == 12
        # Fields beyond top 10 should have no cardinality_score
        no_card = [
            r for r in result.recommendations if r.score_breakdown.cardinality_score is None
        ]
        assert len(no_card) >= 2

    async def test_pagination_page_size_zero(self, ctx):
        """When max_total equals results already fetched, page_size becomes 0 and loop breaks."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_logs.index_recommender import (
            _paginate_describe_queries,
        )

        client = MagicMock()
        # First call returns 1 query with nextToken, max_total=1 should stop
        client.describe_queries.return_value = {
            'queries': [{'queryString': 'filter a = "1"', 'status': 'Complete'}],
            'nextToken': 'page2',
        }

        result = _paginate_describe_queries(client, max_total=1, status='Complete')
        assert len(result) == 1
        assert client.describe_queries.call_count == 1
