# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the read-only Flux query guard used by InfluxDBQuery.

The guard parses each query with InfluxDB's own parser (POST /api/v2/query/ast)
and checks the AST. The ASTs used here were recorded from InfluxDB OSS v2.7.11
and are stored in fixtures/flux_ast.json, keyed by query text. To add a query,
add it to BLOCKED_QUERIES or ALLOWED_QUERIES and regenerate the fixture file
with fixtures/generate_flux_ast_fixtures.py.
"""

import json
import pytest
from awslabs.timestream_for_influxdb_mcp_server.server import (
    check_flux_ast,
    influxdb_query,
    parse_flux_query,
    validate_flux_query,
)
from influxdb_client.rest import ApiException
from pathlib import Path
from unittest.mock import MagicMock, patch


WRITE = 'write-producing Flux operation'
PACKAGE = 'imports a Flux package that is not permitted'
HOST = 'host argument'
SYNTAX = 'syntax that the read-only validation does not support'

# (test id, query, expected error message fragment)
BLOCKED_QUERIES = [
    ('pipe_to', 'from(bucket: "src") |> range(start: -1h) |> to(bucket: "dst")', WRITE),
    (
        'to_assignment',
        'data = from(bucket: "src")\nresult = to(bucket: "dst", tables: data)',
        WRITE,
    ),
    ('to_alias', 'writer = to\nfrom(bucket: "src") |> writer(bucket: "dst")', WRITE),
    ('to_in_record', 'w = {f: to}\nfrom(bucket: "src") |> w.f(bucket: "dst")', WRITE),
    (
        'to_in_user_function',
        'f = (tables=<-) => tables |> to(bucket: "dst")\nfrom(bucket: "src") |> f()',
        WRITE,
    ),
    ('to_split_across_lines', 'from(bucket: "src") |> to\n(bucket: "dst")', WRITE),
    ('wideTo_unqualified', 'from(bucket: "src") |> wideTo(bucket: "dst")', WRITE),
    (
        'experimental_to',
        'import "experimental"\nfrom(bucket: "src") |> experimental.to(bucket: "dst")',
        WRITE,
    ),
    (
        'experimental_to_aliased_import',
        'import e "experimental"\nfrom(bucket: "src") |> e.to(bucket: "dst")',
        WRITE,
    ),
    (
        'experimental_to_bracket_access',
        'import "experimental"\nfrom(bucket: "src") |> experimental["to"](bucket: "dst")',
        WRITE,
    ),
    (
        'influxdb_wideTo_bracket_access',
        'import "influxdata/influxdb"\nfrom(bucket: "src") |> influxdb["wideTo"](bucket: "dst")',
        WRITE,
    ),
    ('to_behind_regex_with_quote', 'r = /"/\nfrom(bucket: "src") |> to(bucket: "dst")', WRITE),
    (
        'to_behind_regex_with_slashes',
        'r = /\\/\\// from(bucket: "src") |> to(bucket: "dst")',
        WRITE,
    ),
    (
        'to_behind_url_in_string',
        'from(bucket: "src") |> map(fn: (r) => ({r with u: "http://example"})) |> to(bucket: "dst")',
        WRITE,
    ),
    (
        'to_behind_escaped_quote',
        'from(bucket: "src") |> filter(fn: (r) => r.m == "a\\"b") |> to(bucket: "dst")',
        WRITE,
    ),
    (
        'to_in_interpolation',
        'x = "${to}"\nfrom(bucket: "src") |> range(start: -1h)',
        WRITE,
    ),
    (
        'to_with_remote_host',
        'from(bucket: "src") |> to(bucket: "dst", host: "https://other.example.com", token: "t")',
        WRITE,
    ),
    (
        'http_post',
        'import "http"\nhttp.post(url: "https://other.example.com", data: bytes(v: "x"))',
        PACKAGE,
    ),
    (
        'http_post_behind_regex',
        'import "http"\nr = /"/\nhttp.post(url: "https://other.example.com", data: bytes(v: "x"))',
        PACKAGE,
    ),
    (
        'requests_get',
        'import "experimental/http/requests"\nrequests.get(url: "https://other.example.com")',
        PACKAGE,
    ),
    ('secrets_get', 'import "influxdata/influxdb/secrets"\nx = secrets.get(key: "k")', PACKAGE),
    (
        'package_bound_to_variable',
        'import "experimental"\ne = experimental\nfrom(bucket: "src") |> e.to(bucket: "dst")',
        PACKAGE,
    ),
    (
        'from_remote_host',
        'from(bucket: "src", host: "https://other.example.com") |> range(start: -1h)',
        HOST,
    ),
    (
        'from_remote_host_string_key',
        'from(bucket: "src", "host": "https://other.example.com") |> range(start: -1h)',
        HOST,
    ),
    (
        'from_alias_remote_host',
        'f = from\nf(bucket: "src", host: "https://other.example.com") |> range(start: -1h)',
        HOST,
    ),
    ('buckets_remote_host', 'buckets(host: "https://other.example.com")', HOST),
    ('builtin_statement', 'builtin x : int', SYNTAX),
    ('testcase_statement', 'testcase t { x = 1 }', SYNTAX),
]

# (test id, query)
ALLOWED_QUERIES = [
    (
        'range_filter',
        'from(bucket: "src") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "cpu")',
    ),
    (
        'bracket_field_access',
        'from(bucket: "src") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "cpu")',
    ),
    (
        'regex_filter',
        'from(bucket: "src") |> range(start: -1h) |> filter(fn: (r) => r.host =~ /^web-[0-9]+$/)',
    ),
    (
        'regex_with_quote_and_slashes',
        'from(bucket: "src") |> range(start: -1h) |> filter(fn: (r) => r.path !~ /"|\\/\\//)',
    ),
    (
        'commented_out_to',
        'from(bucket: "src") |> range(start: -1h)\n// |> to(bucket: "dst")\n|> yield()',
    ),
    (
        'to_in_string_literal',
        'from(bucket: "src") |> filter(fn: (r) => r.message == "experimental.to(")',
    ),
    (
        'url_in_string',
        'from(bucket: "src") |> range(start: -1h) |> map(fn: (r) => ({r with u: "http://a//b"}))',
    ),
    (
        'string_interpolation',
        'm = "cpu"\nfrom(bucket: "src") |> range(start: -1h) |> map(fn: (r) => ({r with s: "m=${m}"}))',
    ),
    (
        'to_prefixed_conversions',
        'from(bucket: "src") |> range(start: -1h) |> map(fn: (r) => ({r with s: string(v: r._value)})) |> toFloat()',
    ),
    (
        'record_field_named_to',
        'from(bucket: "src") |> range(start: -1h) |> map(fn: (r) => ({r with to: 1, x: r.to}))',
    ),
    (
        'record_field_named_host',
        'from(bucket: "src") |> range(start: -1h) |> map(fn: (r) => ({r with host: "a"}))',
    ),
    (
        'aggregate_window',
        'from(bucket: "src") |> range(start: -1h) |> aggregateWindow(every: 5m, fn: mean, createEmpty: false) |> yield(name: "mean")',
    ),
    (
        'pivot',
        'from(bucket: "src") |> range(start: -1h) |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")',
    ),
    (
        'allowed_packages',
        'import "strings"\nimport "date"\nimport "math"\nimport "influxdata/influxdb/schema"\n'
        'from(bucket: "src") |> range(start: -1h) |> map(fn: (r) => ({r with u: strings.toUpper(v: r.host), h: date.hour(t: r._time), m: math.abs(x: r._value)}))',
    ),
    (
        'join_package',
        'import "join"\na = from(bucket: "src") |> range(start: -1h)\nb = from(bucket: "src") |> range(start: -1h)\n'
        'join.inner(left: a, right: b, on: (l, r) => l._time == r._time, as: (l, r) => ({l with v2: r._value}))',
    ),
    (
        'schema_measurements',
        'import "influxdata/influxdb/schema"\nschema.measurements(bucket: "src")',
    ),
    (
        'array_from',
        'import "array"\narray.from(rows: [{_measurement: "m", _field: "f", _value: 1.0}])',
    ),
    ('buckets_local', 'buckets()'),
    (
        'option_and_function',
        'option now = () => 2030-01-01T00:00:00Z\nf = (tables=<-) => tables |> limit(n: 1)\nfrom(bucket: "src") |> range(start: -1h) |> f()',
    ),
    (
        'conditional_dict_index',
        'import "dict"\nd = ["a": 1]\nl = [1, 2]\nfrom(bucket: "src") |> range(start: -1h) |> map(fn: (r) => ({r with x: if r._value > 0.0 then dict.get(dict: d, key: "a", default: l[0]) else -1}))',
    ),
]

FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'flux_ast.json'


@pytest.fixture(scope='module')
def flux_ast_fixtures():
    """Load the recorded InfluxDB ASTs, keyed by query text."""
    return json.loads(FIXTURE_PATH.read_text())


def _ast_for(fixtures, query):
    if query not in fixtures:
        pytest.fail(
            'No recorded AST for this query. Regenerate tests/fixtures/flux_ast.json with '
            'tests/fixtures/generate_flux_ast_fixtures.py.'
        )
    return fixtures[query]


def _package(*body, imports=None):
    """Build a minimal Flux AST Package node for synthetic tests."""
    return {
        'type': 'Package',
        'package': 'main',
        'files': [{'type': 'File', 'imports': imports, 'body': list(body)}],
    }


class TestCheckFluxAst:
    """Tests for check_flux_ast with ASTs recorded from InfluxDB."""

    @pytest.mark.parametrize(
        'query,expected',
        [(q, e) for _, q, e in BLOCKED_QUERIES],
        ids=[i for i, _, _ in BLOCKED_QUERIES],
    )
    def test_rejects_query(self, flux_ast_fixtures, query, expected):
        """Test that queries that can write or reach the network are rejected."""
        with pytest.raises(ValueError, match=expected):
            check_flux_ast(_ast_for(flux_ast_fixtures, query))

    @pytest.mark.parametrize(
        'query', [q for _, q in ALLOWED_QUERIES], ids=[i for i, _ in ALLOWED_QUERIES]
    )
    def test_allows_query(self, flux_ast_fixtures, query):
        """Test that read queries are allowed."""
        check_flux_ast(_ast_for(flux_ast_fixtures, query))

    def test_rejects_unknown_node_type(self):
        """Test that a node type the guard does not know is rejected."""
        ast = _package({'type': 'ExpressionStatement', 'expression': {'type': 'FutureExpression'}})
        with pytest.raises(ValueError, match='FutureExpression'):
            check_flux_ast(ast)

    def test_rejects_node_with_parse_errors(self):
        """Test that a node carrying parser errors is rejected."""
        ast = _package(
            {
                'type': 'ExpressionStatement',
                'expression': {'type': 'Identifier', 'name': 'x', 'errors': [{'msg': 'bad'}]},
            }
        )
        with pytest.raises(ValueError, match='parse errors'):
            check_flux_ast(ast)

    def test_rejects_import_without_path(self):
        """Test that an import declaration with no path is rejected."""
        ast = _package(imports=[{'type': 'ImportDeclaration', 'path': None}])
        with pytest.raises(ValueError, match=PACKAGE):
            check_flux_ast(ast)

    def test_does_not_scan_location_source_text(self):
        """Test that the raw source text in `location` is not treated as code."""
        ast = _package(
            {
                'type': 'ExpressionStatement',
                'location': {'source': 'to(bucket: "dst")'},
                'expression': {'type': 'Identifier', 'name': 'x'},
            }
        )
        check_flux_ast(ast)

    def test_ignores_scalar_list_items(self):
        """Test that scalar values inside AST lists are skipped."""
        check_flux_ast(_package({'type': 'ExpressionStatement', 'expression': None}, 'x', 1))

    def test_ignores_property_key_that_is_not_identifier_or_string(self):
        """Test that an unexpected call-argument key shape is not a host argument."""
        call = {
            'type': 'CallExpression',
            'callee': {'type': 'Identifier', 'name': 'f'},
            'arguments': [
                {
                    'type': 'ObjectExpression',
                    'properties': [
                        {
                            'type': 'Property',
                            'key': {'type': 'IntegerLiteral', 'value': '1'},
                            'value': {'type': 'IntegerLiteral', 'value': '1'},
                        },
                        {'type': 'Property', 'key': None, 'value': None},
                    ],
                }
            ],
        }
        check_flux_ast(_package({'type': 'ExpressionStatement', 'expression': call}))


class TestParseFluxQuery:
    """Tests for parse_flux_query, with the InfluxDB endpoint mocked."""

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.QueryService')
    def test_returns_ast(self, mock_query_service):
        """Test that the AST is returned from a successful response."""
        response = MagicMock()
        response.data = json.dumps({'ast': _package()}).encode()
        mock_query_service.return_value.post_query_ast.return_value = response
        client = MagicMock()

        assert parse_flux_query(client, 'buckets()') == _package()

        mock_query_service.assert_called_once_with(client.api_client)
        kwargs = mock_query_service.return_value.post_query_ast.call_args.kwargs
        assert kwargs['language_request'].query == 'buckets()'
        assert kwargs['_preload_content'] is False

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.QueryService')
    def test_raises_on_syntax_error(self, mock_query_service):
        """Test that an InfluxDB parse error is a rejection that includes the reason."""
        error = ApiException(status=400, reason='Bad Request')
        error.body = b'{"code":"invalid","message":"expected RPAREN, got EOF"}'
        mock_query_service.return_value.post_query_ast.side_effect = error

        with pytest.raises(ValueError, match='expected RPAREN, got EOF'):
            parse_flux_query(MagicMock(), 'from(')

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.QueryService')
    def test_raises_on_api_error_without_body(self, mock_query_service):
        """Test that an API error without a body still fails closed."""
        mock_query_service.return_value.post_query_ast.side_effect = ApiException(
            status=404, reason='Not Found'
        )

        with pytest.raises(ValueError, match='Not Found'):
            parse_flux_query(MagicMock(), 'buckets()')

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.QueryService')
    def test_raises_on_connection_error(self, mock_query_service):
        """Test that a network failure fails closed."""
        mock_query_service.return_value.post_query_ast.side_effect = OSError('refused')

        with pytest.raises(ValueError, match='refused'):
            parse_flux_query(MagicMock(), 'buckets()')

    @pytest.mark.parametrize(
        'payload', [b'not json', b'[]', b'{}', b'{"ast": {"type": "File"}}'], ids=str
    )
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.QueryService')
    def test_raises_on_unexpected_response(self, mock_query_service, payload):
        """Test that a response without a Package AST fails closed."""
        response = MagicMock()
        response.data = payload
        mock_query_service.return_value.post_query_ast.return_value = response

        with pytest.raises(ValueError, match='could not be parsed'):
            parse_flux_query(MagicMock(), 'buckets()')


class TestValidateFluxQuery:
    """Tests for validate_flux_query."""

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.INFLUXDB_WRITE_MODE', True)
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.parse_flux_query')
    def test_skips_validation_in_write_mode(self, mock_parse):
        """Test that no AST request is made when INFLUXDB_WRITE_MODE is enabled."""
        validate_flux_query('from(bucket: "src") |> to(bucket: "dst")', MagicMock())
        mock_parse.assert_not_called()

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.INFLUXDB_WRITE_MODE', False)
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.parse_flux_query')
    def test_checks_parsed_query_in_read_only_mode(self, mock_parse, flux_ast_fixtures):
        """Test that the parsed AST is checked when INFLUXDB_WRITE_MODE is disabled."""
        query = BLOCKED_QUERIES[0][1]
        mock_parse.return_value = _ast_for(flux_ast_fixtures, query)
        client = MagicMock()

        with pytest.raises(ValueError, match=WRITE):
            validate_flux_query(query, client)

        mock_parse.assert_called_once_with(client, query)


@patch(
    'awslabs.timestream_for_influxdb_mcp_server.server.INFLUXDB_ALLOWED_URLS',
    'https://influxdb-example.aws:8086',
)
class TestInfluxDBQueryGuard:
    """Tests that InfluxDBQuery validates a query before running it."""

    @staticmethod
    def _mock_client(mock_get_client):
        client = MagicMock()
        client.query_api.return_value.query.return_value = []
        mock_get_client.return_value = client
        return client

    @staticmethod
    async def _query(query):
        return await influxdb_query(
            url='https://influxdb-example.aws:8086',
            token='test-token',
            org='test-org',
            query=query,
            verify_ssl=True,
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.INFLUXDB_WRITE_MODE', False)
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.parse_flux_query')
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_rejected_query_is_not_run(self, mock_get_client, mock_parse, flux_ast_fixtures):
        """Test that a rejected query is never sent to the query API."""
        query = 'import "experimental"\nfrom(bucket: "src") |> experimental["to"](bucket: "dst")'
        mock_parse.return_value = _ast_for(flux_ast_fixtures, query)
        client = self._mock_client(mock_get_client)

        with pytest.raises(ValueError, match=WRITE):
            await self._query(query)

        mock_parse.assert_called_once_with(client, query)
        client.query_api.assert_not_called()
        client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.INFLUXDB_WRITE_MODE', False)
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.parse_flux_query')
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_unparseable_query_is_not_run(self, mock_get_client, mock_parse):
        """Test that a query InfluxDB cannot parse is rejected before it runs."""
        mock_parse.side_effect = ValueError('Flux query could not be parsed')
        client = self._mock_client(mock_get_client)

        with pytest.raises(ValueError, match='could not be parsed'):
            await self._query('from(')

        client.query_api.assert_not_called()
        client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.INFLUXDB_WRITE_MODE', False)
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.parse_flux_query')
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_allowed_query_is_run(self, mock_get_client, mock_parse, flux_ast_fixtures):
        """Test that an allowed query is sent to the query API."""
        query = ALLOWED_QUERIES[0][1]
        mock_parse.return_value = _ast_for(flux_ast_fixtures, query)
        client = self._mock_client(mock_get_client)

        result = await self._query(query)

        assert result['status'] == 'success'
        client.query_api.return_value.query.assert_called_once_with(org='test-org', query=query)

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.INFLUXDB_WRITE_MODE', True)
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.parse_flux_query')
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_write_query_runs_in_write_mode(self, mock_get_client, mock_parse):
        """Test that to() runs without an AST request when INFLUXDB_WRITE_MODE is enabled."""
        client = self._mock_client(mock_get_client)

        result = await self._query('from(bucket: "src") |> to(bucket: "dst")')

        assert result['status'] == 'success'
        mock_parse.assert_not_called()
        client.query_api.return_value.query.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_client_creation_error_is_returned(self, mock_get_client):
        """Test that a client creation failure is returned as an error result."""
        mock_get_client.side_effect = ValueError('Token must be provided')

        result = await self._query('buckets()')

        assert result == {'status': 'error', 'message': 'Token must be provided'}
