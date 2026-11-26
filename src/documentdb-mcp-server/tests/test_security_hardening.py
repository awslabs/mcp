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
"""Tests for read-only enforcement, result bounds, logging and error hygiene."""

import pytest
import sys
from awslabs.documentdb_mcp_server import analytic_tools, db_management_tools, write_tools
from awslabs.documentdb_mcp_server.analytic_tools import (
    analyze_schema,
    explain_operation,
    get_field_type,
)
from awslabs.documentdb_mcp_server.config import (
    MAX_RESULTS,
    assert_pipeline_readonly,
    bounded_limit,
    is_database_allowed,
    is_namespace_allowed,
    parse_allowed_namespaces,
    pipeline_namespaces,
    serverConfig,
)
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.errors import (
    CONNECTION_ERROR_MESSAGE,
    SafeToolError,
    redact,
    tool_error,
)
from awslabs.documentdb_mcp_server.query_tools import aggregate, find
from awslabs.documentdb_mcp_server.server import main, mcp
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from pymongo.errors import AutoReconnect, OperationFailure, ServerSelectionTimeoutError
from unittest.mock import patch


HOST = 'internal-docdb-prod.cluster-abc123.us-west-2.docdb.amazonaws.com'
MARKER = 'MarkerPassw0rd'
SECRET_URI = f'mongodb://admin:{MARKER}@{HOST}:27017/?tls=true&retryWrites=false'


@pytest.fixture
def log_messages():
    """Capture loguru output (all levels) for the duration of a test."""
    messages = []
    handler_id = logger.add(lambda m: messages.append(str(m)), level='TRACE')
    yield messages
    logger.remove(handler_id)


def _stderr_sink(message) -> None:
    """Write to whatever sys.stderr is at call time (pytest swaps it per test)."""
    sys.stderr.write(message)


@pytest.fixture
def restore_logger():
    """Restore a stderr loguru sink after tests that call main(), which replaces sinks."""
    yield
    logger.remove()
    logger.add(_stderr_sink)


@pytest.fixture
def read_only(monkeypatch):
    """Run the test with the server in read-only mode."""
    monkeypatch.setattr(serverConfig, 'read_only_mode', True)


@pytest.fixture
def writable(monkeypatch):
    """Run the test with write operations allowed."""
    monkeypatch.setattr(serverConfig, 'read_only_mode', False)


def seed(mock_client, count, db='test_db', coll='test_collection'):
    """Insert ``count`` small documents into a mock collection and return it."""
    collection = mock_client[db][coll]
    for i in range(count):
        collection.insert_one({'_id': i, 'value': i})
    return collection


def spy_on(monkeypatch, obj, name):
    """Record the positional arguments of every call to ``obj.name``."""
    calls = []
    original = getattr(obj, name)

    def wrapper(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(obj, name, wrapper)
    return calls


class TestExplainReadOnly:
    """V2381754599: explainOperation must honour read-only mode."""

    @pytest.mark.parametrize('stage', [{'$out': 'other'}, {'$merge': {'into': 'other'}}])
    async def test_write_stage_rejected_in_read_only_mode(
        self, patch_client, read_only, monkeypatch, stage
    ):
        """An explained pipeline with $out/$merge never reaches the database."""
        db = patch_client()['test_db']
        commands = spy_on(monkeypatch, db, 'command')

        with pytest.raises(SafeToolError, match='read-only mode'):
            await explain_operation(
                'test_db', 'test_collection', 'aggregate', pipeline=[{'$match': {}}, stage]
            )
        assert commands == []

    async def test_execution_stats_forced_to_query_planner(
        self, patch_client, read_only, monkeypatch
    ):
        """In read-only mode an aggregate explain plans but does not execute."""
        db = patch_client()['test_db']
        commands = spy_on(monkeypatch, db, 'command')

        result = await explain_operation(
            'test_db',
            'test_collection',
            'aggregate',
            pipeline=[{'$match': {}}],
            verbosity='executionStats',
        )

        assert commands[0][0]['verbosity'] == 'queryPlanner'
        assert result['verbosity'] == 'queryPlanner'
        assert 'executionStats' not in result['explanation']

    async def test_find_explain_keeps_execution_stats(self, patch_client, read_only):
        """A find explain is a read; executionStats stays available in read-only mode."""
        patch_client()

        result = await explain_operation(
            'test_db', 'test_collection', 'find', query={}, verbosity='executionStats'
        )

        assert result['verbosity'] == 'executionStats'
        assert 'executionStats' in result['explanation']

    async def test_write_mode_passes_through(self, patch_client, writable, monkeypatch):
        """With --allow-write the pipeline and verbosity are sent unchanged."""
        db = patch_client()['test_db']
        commands = spy_on(monkeypatch, db, 'command')
        pipeline = [{'$match': {}}, {'$out': 'other'}]

        await explain_operation(
            'test_db',
            'test_collection',
            'aggregate',
            pipeline=pipeline,
            verbosity='executionStats',
        )

        assert commands[0][0]['explain']['pipeline'] == pipeline
        assert commands[0][0]['verbosity'] == 'executionStats'

    def test_shared_helper(self, monkeypatch):
        """assert_pipeline_readonly rejects write stages only in read-only mode."""
        monkeypatch.setattr(serverConfig, 'read_only_mode', True)
        assert_pipeline_readonly([{'$match': {}}, {'$group': {'_id': None}}])
        with pytest.raises(SafeToolError):
            assert_pipeline_readonly([{'$merge': {'into': 'x'}}])

        monkeypatch.setattr(serverConfig, 'read_only_mode', False)
        assert_pipeline_readonly([{'$merge': {'into': 'x'}}])


class TestResultBounds:
    """V2381766074: result counts are bounded by MAX_RESULTS."""

    def test_bounded_limit(self):
        """Limits are clamped to [1, MAX_RESULTS]."""
        assert bounded_limit(0) == 1
        assert bounded_limit(-5) == 1
        assert bounded_limit(10) == 10
        assert bounded_limit(10**9) == MAX_RESULTS

    @pytest.mark.parametrize(
        'tool,args',
        [
            ('find', {'database': 'd', 'collection': 'c', 'query': {}}),
            ('aggregate', {'database': 'd', 'collection': 'c', 'pipeline': []}),
        ],
    )
    @pytest.mark.parametrize('limit', [0, MAX_RESULTS + 1])
    async def test_out_of_range_limit_rejected_by_tool_validation(self, tool, args, limit):
        """limit=0 (formerly 'unlimited') and limit>MAX_RESULTS are rejected."""
        with pytest.raises(ToolError, match='validation error'):
            await mcp.call_tool(tool, {**args, 'limit': limit})

    async def test_input_schema_publishes_bounds(self):
        """Clients see the bounds in the tool schema."""
        tools = {tool.name: tool for tool in await mcp.list_tools()}
        for name, param in [
            ('find', 'limit'),
            ('aggregate', 'limit'),
            ('analyzeSchema', 'sample_size'),
        ]:
            schema = tools[name].input_schema['properties'][param]
            assert schema['minimum'] == 1
            assert schema['maximum'] == MAX_RESULTS

    async def test_find_clamps_limit(self, patch_client):
        """Find never returns more than MAX_RESULTS documents, even when called directly."""
        seed(patch_client(), MAX_RESULTS + 5)

        assert len(await find('test_db', 'test_collection', {}, None, 10**8)) == MAX_RESULTS
        assert len(await find('test_db', 'test_collection', {}, None, 0)) == 1

    async def test_aggregate_caps_caller_limit(self, patch_client, monkeypatch):
        """A caller-supplied $limit cannot lift the server cap."""
        collection = seed(patch_client(), MAX_RESULTS + 5)
        calls = spy_on(monkeypatch, collection, 'aggregate')
        pipeline = [{'$limit': 10**8}]

        result = await aggregate('test_db', 'test_collection', pipeline, 10**8)

        assert len(result) == MAX_RESULTS
        assert calls[0][0][-1] == {'$limit': MAX_RESULTS}
        # The caller's list is not modified.
        assert pipeline == [{'$limit': 10**8}]

    async def test_aggregate_appends_limit_after_caller_limit(self, patch_client, monkeypatch):
        """The requested limit applies even when the pipeline has a larger $limit."""
        collection = seed(patch_client(), 20)
        calls = spy_on(monkeypatch, collection, 'aggregate')

        result = await aggregate('test_db', 'test_collection', [{'$limit': 15}], 5)

        assert len(result) == 5
        assert calls[0][0] == [{'$limit': 15}, {'$limit': 5}]

    async def test_aggregate_keeps_write_stage_last(self, patch_client, writable, monkeypatch):
        """In write mode a pipeline ending in $out/$merge keeps that stage last."""
        collection = seed(patch_client(), 3)
        calls = spy_on(monkeypatch, collection, 'aggregate')

        await aggregate('test_db', 'test_collection', [{'$match': {}}, {'$out': 'copy'}], 10)

        assert calls[0][0][-1] == {'$out': 'copy'}

    async def test_analyze_schema_caps_sample_size(self, patch_client, monkeypatch):
        """AnalyzeSchema never samples more than MAX_RESULTS documents."""
        collection = seed(patch_client(), MAX_RESULTS + 5)
        calls = spy_on(monkeypatch, collection, 'aggregate')

        result = await analyze_schema('test_db', 'test_collection', 10**8)

        assert calls[0][0] == [{'$sample': {'size': MAX_RESULTS}}]
        assert result['sampled_documents'] == MAX_RESULTS


class TestLogging:
    """V2381766336: logs go to stderr and never contain document contents."""

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch(
        'sys.argv',
        [
            'awslabs.documentdb-mcp-server',
            '--connection-string',
            'mongodb://h:27017/?retryWrites=false',
        ],
    )
    def test_logs_do_not_reach_stdout(self, mock_run, capsys, restore_logger):
        """Stdout is reserved for the stdio JSON-RPC stream."""
        main()
        logger.warning('probe-after-main')

        captured = capsys.readouterr()
        assert captured.out == ''
        assert 'Starting DocumentDB MCP Server' in captured.err
        assert 'probe-after-main' in captured.err

    def test_get_field_type_does_not_log_document_values(self, log_messages):
        """A field-processing error logs the path and error type, not the document."""
        docs = [{'_id': 1, 'tags': ['SECRET-VALUE'], 'ssn': '123-45-6789'}]

        # 'tags[x]' makes int() fail on the index, which is a logged, skipped error.
        assert get_field_type(docs, 'tags[x]') == 'null'

        logged = ''.join(log_messages)
        assert "'tags[x]'" in logged
        assert 'ValueError' in logged
        assert 'SECRET-VALUE' not in logged
        assert '123-45-6789' not in logged


def _tool_calls():
    """One call per registered tool, with arguments that reach get_client()."""
    return [
        (find, ('d', 'c', {})),
        (aggregate, ('d', 'c', [{'$match': {}}])),
        (write_tools.insert, ('d', 'c', {'a': 1})),
        (write_tools.update, ('d', 'c', {'a': 1}, {'$set': {'a': 2}})),
        (write_tools.delete, ('d', 'c', {'a': 1})),
        (db_management_tools.list_databases, ()),
        (db_management_tools.create_collection, ('d', 'c')),
        (db_management_tools.list_collections, ('d',)),
        (db_management_tools.drop_collection, ('d', 'c')),
        (analytic_tools.count_documents, ('d', 'c')),
        (analytic_tools.get_database_stats, ('d',)),
        (analytic_tools.get_collection_stats, ('d', 'c')),
        (analytic_tools.analyze_schema, ('d', 'c')),
        (analytic_tools.explain_operation, ('d', 'c', 'find')),
    ]


class TestErrorMessages:
    """V2389565920: tool errors must not carry the cluster endpoint or credentials."""

    def test_every_registered_tool_is_covered(self):
        """Keep _tool_calls in step with the registered tools."""
        assert len(_tool_calls()) == 14

    @pytest.mark.parametrize('tool,args', _tool_calls(), ids=lambda v: getattr(v, '__name__', ''))
    async def test_connection_failure_message_is_fixed(
        self, patch_client, writable, log_messages, tool, args
    ):
        """Every tool returns the fixed message when the cluster is unreachable."""
        patch_client(
            raise_on_connect=ServerSelectionTimeoutError(
                f'{HOST}:27017: timed out, Topology Description: '
                f"<TopologyDescription servers: [<ServerDescription ('{HOST}', 27017)>]>"
            )
        )
        serverConfig.connection_string = SECRET_URI

        with pytest.raises(SafeToolError) as exc_info:
            await tool(*args)

        assert str(exc_info.value) == CONNECTION_ERROR_MESSAGE
        assert HOST not in str(exc_info.value)
        assert MARKER not in ''.join(log_messages)

    async def test_mcp_client_sees_only_the_fixed_message(self, patch_client, log_messages):
        """End to end through MCP call_tool: no endpoint or topology in the result."""
        patch_client(raise_on_connect=ServerSelectionTimeoutError(f'{HOST}:27017: timed out'))
        serverConfig.connection_string = SECRET_URI

        with pytest.raises(ToolError) as exc_info:
            await mcp.call_tool('find', {'database': 'd', 'collection': 'c', 'query': {}})

        assert CONNECTION_ERROR_MESSAGE in str(exc_info.value)
        assert HOST not in str(exc_info.value)
        assert MARKER not in str(exc_info.value)

    async def test_mcp_client_sees_deliberate_messages(self, read_only):
        """SafeToolError messages (e.g. read-only denials) reach the client verbatim."""
        with pytest.raises(ToolError, match='read-only mode') as exc_info:
            await mcp.call_tool('delete', {'database': 'd', 'collection': 'c', 'filter': {}})
        assert not isinstance(exc_info.value, UnexpectedToolError)

    async def test_unexpected_errors_are_hidden_from_the_client(
        self, patch_client, monkeypatch, log_messages
    ):
        """Errors that are not SafeToolError reach the client only as a generic message."""
        collection = patch_client()['d']['c']

        def failing_find(*args, **kwargs):
            raise RuntimeError(f'driver detail {HOST} {SECRET_URI}')

        monkeypatch.setattr(collection, 'find', failing_find)

        with pytest.raises(UnexpectedToolError) as exc_info:
            await mcp.call_tool('find', {'database': 'd', 'collection': 'c', 'query': {}})
        assert str(exc_info.value) == 'Error executing tool find'

        # Direct callers still get the (credential-redacted) detail.
        with pytest.raises(ValueError) as direct:
            await find('d', 'c', {})
        assert not isinstance(direct.value, SafeToolError)
        assert MARKER not in str(direct.value)
        assert MARKER not in ''.join(log_messages)

    async def test_client_constructor_error_is_contained(self, log_messages):
        """Pymongo errors raised by MongoClient() itself are also replaced."""
        # A non-numeric port makes the real MongoClient constructor raise ValueError.
        serverConfig.connection_string = f'mongodb://admin:{MARKER}@{HOST}:abc/?retryWrites=false'

        with pytest.raises(SafeToolError) as exc_info:
            await find('d', 'c', {})

        assert str(exc_info.value) == CONNECTION_ERROR_MESSAGE
        assert MARKER not in ''.join(log_messages)

    async def test_connection_lost_mid_operation_message_is_fixed(self, patch_client, monkeypatch):
        """A connection error after connecting (e.g. a failover) is also replaced."""
        collection = patch_client()['d']['c']

        def failing_find(*args, **kwargs):
            raise AutoReconnect(f'{HOST}:27017: connection closed')

        monkeypatch.setattr(collection, 'find', failing_find)

        with pytest.raises(SafeToolError) as exc_info:
            await find('d', 'c', {})
        assert str(exc_info.value) == CONNECTION_ERROR_MESSAGE

    async def test_operation_failure_relays_errmsg_and_code_only(self, patch_client, monkeypatch):
        """Query errors keep the server's errmsg and code, without the full reply."""
        collection = patch_client()['d']['c']

        def failing_find(*args, **kwargs):
            raise OperationFailure(
                'unknown operator: $foo',
                2,
                {'ok': 0, 'errmsg': 'unknown operator: $foo', 'code': 2, 'internal': HOST},
            )

        monkeypatch.setattr(collection, 'find', failing_find)

        with pytest.raises(SafeToolError) as exc_info:
            await find('d', 'c', {'a': {'$foo': 1}})

        assert str(exc_info.value) == 'Failed to query DocumentDB: unknown operator: $foo (code 2)'

    def test_operation_failure_without_details_keeps_message(self):
        """An OperationFailure with no server reply still relays its message."""
        converted = tool_error('query DocumentDB', OperationFailure('bad query', 2))
        assert str(converted) == 'Failed to query DocumentDB: bad query (code 2)'

    def test_tool_error_helper(self):
        """SafeToolError passes through; other errors have URI credentials redacted."""
        curated = SafeToolError('Operation not permitted')
        assert tool_error('x', curated) is curated

        converted = tool_error('x', RuntimeError(f'bad uri {SECRET_URI}'))
        assert MARKER not in str(converted)
        assert 'mongodb://<redacted>@' in str(converted)

    def test_redact(self):
        """redact() strips userinfo from mongodb and mongodb+srv URIs."""
        assert redact(SECRET_URI).startswith('mongodb://<redacted>@')
        assert MARKER not in redact(f'x mongodb+srv://u:{MARKER}@h/db y')
        assert redact('no uri here') == 'no uri here'


class TestStartupValidation:
    """V2389565921: a bad connection string is caught at startup, and on connect."""

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch(
        'sys.argv',
        [
            'awslabs.documentdb-mcp-server',
            '--connection-string',
            f'mongodb://admin:{MARKER}@{HOST}:abc/?retryWrites=false',
        ],
    )
    def test_unparseable_uri_exits_without_echoing_it(self, mock_run, capsys, restore_logger):
        """A malformed URI stops startup with a message that omits the credentials."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_run.assert_not_called()
        err = capsys.readouterr().err
        assert 'could not be parsed' in err
        assert MARKER not in err

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch(
        'sys.argv',
        [
            'awslabs.documentdb-mcp-server',
            '--connection-string',
            'notmongo://h/?retryWrites=false',
        ],
    )
    def test_wrong_scheme_exits(self, mock_run, restore_logger):
        """A non-MongoDB URI scheme stops startup."""
        with pytest.raises(SystemExit):
            main()
        mock_run.assert_not_called()

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch(
        'sys.argv',
        [
            'awslabs.documentdb-mcp-server',
            '--connection-string',
            'mongodb+srv://cluster.example.invalid/?retryWrites=false',
        ],
    )
    def test_srv_uri_is_not_resolved_at_startup(self, mock_run, restore_logger):
        """mongodb+srv:// is not parsed at startup, so no DNS lookup is needed to start."""
        main()
        mock_run.assert_called_once()

    def test_connect_enforces_retry_writes_when_main_is_bypassed(self, monkeypatch):
        """_connect() validates retryWrites itself, before building a client."""

        def no_client(*args, **kwargs):
            raise AssertionError('MongoClient must not be constructed')

        monkeypatch.setattr(
            'awslabs.documentdb_mcp_server.connection_tools.MongoClient', no_client
        )
        serverConfig.connection_string = 'mongodb://example.com:27017/'

        with pytest.raises(SafeToolError, match="missing 'retryWrites=false'"):
            DocumentDBConnection.get_client()


class TestWriteGuardrails:
    """V2381766516: destructive writes need explicit intent once --allow-write is on."""

    async def test_delete_with_empty_filter_is_rejected(self, patch_client, writable):
        """Delete with {} would empty the collection; it needs confirm_destructive."""
        collection = seed(patch_client(), 3)

        with pytest.raises(SafeToolError, match='confirm_destructive=True'):
            await write_tools.delete('test_db', 'test_collection', {}, True)
        assert collection.count_documents({}) == 3

    async def test_delete_with_empty_filter_and_confirmation(self, patch_client, writable):
        """confirm_destructive=True allows deleting every document."""
        collection = seed(patch_client(), 3)

        result = await write_tools.delete(
            'test_db', 'test_collection', {}, True, confirm_destructive=True
        )

        assert result['deleted_count'] == 3
        assert collection.count_documents({}) == 0

    async def test_update_with_empty_filter_is_rejected(self, patch_client, writable):
        """Update with {} needs confirm_destructive; with it, the update runs."""
        patch_client()

        with pytest.raises(SafeToolError, match='confirm_destructive=True'):
            await write_tools.update(
                'test_db', 'test_collection', {}, {'$set': {'x': 1}}, False, True
            )

        result = await write_tools.update(
            'test_db',
            'test_collection',
            {},
            {'$set': {'x': 1}},
            False,
            True,
            confirm_destructive=True,
        )
        assert result['success'] is True

    async def test_update_without_operators_needs_replace(self, patch_client, writable):
        """A $-free update document no longer silently replaces the document."""
        patch_client()['test_db']['test_collection'].insert_one(
            {'_id': 1, 'name': 'a', 'keep': 'me'}
        )

        with pytest.raises(SafeToolError, match='replace=True'):
            await write_tools.update('test_db', 'test_collection', {'_id': 1}, {'name': 'b'})

    @pytest.mark.parametrize(
        'update_doc,many,message',
        [
            ({'$set': {'name': 'b'}}, False, 'without \\$ operators'),
            ({'name': 'b'}, True, 'cannot be combined with many=True'),
        ],
    )
    async def test_replace_argument_errors(
        self, patch_client, writable, update_doc, many, message
    ):
        """replace=True takes a plain document and a single target."""
        patch_client()

        with pytest.raises(SafeToolError, match=message):
            await write_tools.update(
                'test_db', 'test_collection', {'_id': 1}, update_doc, False, many, replace=True
            )

    async def test_guardrail_parameters_default_to_off(self):
        """The tool schema publishes replace and confirm_destructive, both defaulting to False."""
        tools = {tool.name: tool for tool in await mcp.list_tools()}
        update_props = tools['update'].input_schema['properties']
        delete_props = tools['delete'].input_schema['properties']

        assert update_props['replace']['default'] is False
        assert update_props['confirm_destructive']['default'] is False
        assert delete_props['confirm_destructive']['default'] is False


@pytest.fixture
def allowlist(monkeypatch):
    """Restrict the server to the 'app' database and reports.daily_* collections."""
    monkeypatch.setattr(serverConfig, 'allowed_namespaces', ['app', 'reports.daily_*'])


class TestAllowedNamespaces:
    """V2381766516: --allowed-namespaces limits which namespaces any tool can touch."""

    def test_parse(self):
        """Patterns are comma-separated; an empty value allows everything."""
        assert parse_allowed_namespaces(None) is None
        assert parse_allowed_namespaces('  ') is None
        assert parse_allowed_namespaces('app, reports.daily_*') == ['app', 'reports.daily_*']
        with pytest.raises(ValueError, match='database part is empty'):
            parse_allowed_namespaces('.orphan')

    def test_matching(self, allowlist):
        """'db' covers every collection; 'db.pattern' covers matching collections only."""
        assert is_namespace_allowed('app', 'anything')
        assert is_namespace_allowed('reports', 'daily_2026')
        assert not is_namespace_allowed('reports', 'weekly')
        assert not is_namespace_allowed('other', 'x')
        assert is_database_allowed('reports')
        assert not is_database_allowed('other')

    def test_everything_allowed_by_default(self):
        """Without --allowed-namespaces, nothing changes."""
        assert serverConfig.allowed_namespaces is None
        assert is_namespace_allowed('any', 'thing')

    @pytest.mark.parametrize(
        'database,collection',
        [('other', 'c'), ('reports', 'weekly')],
    )
    async def test_find_outside_allowlist_is_rejected(
        self, patch_client, allowlist, database, collection
    ):
        """The check runs before the client is touched."""
        patch_client()

        with pytest.raises(SafeToolError, match='allowed namespaces'):
            await find(database, collection, {})

    async def test_find_inside_allowlist(self, patch_client, allowlist):
        """Allowed namespaces work as before."""
        seed(patch_client(), 2, db='reports', coll='daily_1')

        assert len(await find('reports', 'daily_1', {})) == 2

    def test_pipeline_namespaces_covers_every_stage(self):
        """Every stage that names another collection is found, including nested pipelines."""
        pipeline = [
            {'$lookup': {'from': 'a', 'pipeline': [{'$unionWith': {'coll': 'b'}}]}},
            {'$graphLookup': {'from': 'c'}},
            {'$unionWith': 'd'},
            {'$facet': {'x': [{'$lookup': {'from': 'e'}}]}},
            {'$merge': {'into': {'db': 'other', 'coll': 'f'}}},
        ]
        assert pipeline_namespaces('db', pipeline) == {
            ('db', 'a'),
            ('db', 'b'),
            ('db', 'c'),
            ('db', 'd'),
            ('db', 'e'),
            ('other', 'f'),
        }
        assert pipeline_namespaces('db', [{'$out': {'db': 'other', 'coll': 'g'}}]) == {
            ('other', 'g')
        }

    def test_pipeline_namespaces_edge_cases(self):
        """Sub-pipeline-only stages are walked; unresolvable targets fail closed."""
        assert pipeline_namespaces('db', None) == set()
        assert pipeline_namespaces(
            'db',
            [
                'not-a-stage',
                {'$match': {}},
                {'$lookup': {'pipeline': [{'$lookup': {'from': 'h'}}], 'as': 'x'}},
                {'$unionWith': {'pipeline': [{'$unionWith': 'i'}]}},
            ],
        ) == {('db', 'h'), ('db', 'i')}
        with pytest.raises(SafeToolError, match='cannot check'):
            pipeline_namespaces('db', [{'$out': {'db': 1, 'coll': 'x'}}])

    @pytest.mark.parametrize(
        'stage',
        [
            {'$lookup': {'from': 'weekly', 'localField': 'a', 'foreignField': 'b', 'as': 'c'}},
            {'$unionWith': {'coll': 'weekly'}},
            {'$facet': {'x': [{'$lookup': {'from': 'weekly', 'as': 'y'}}]}},
            {'$merge': {'into': {'db': 'other', 'coll': 'x'}}},
        ],
    )
    async def test_aggregate_cannot_reach_other_collections(
        self, patch_client, allowlist, writable, stage
    ):
        """A pipeline on an allowed collection cannot read or write a disallowed one."""
        patch_client()

        with pytest.raises(SafeToolError, match='allowed namespaces'):
            await aggregate('reports', 'daily_1', [stage], 10)

    async def test_unparseable_stage_target_fails_closed(self, patch_client, allowlist):
        """A stage target the server cannot resolve is rejected rather than allowed."""
        patch_client()

        with pytest.raises(SafeToolError, match='cannot check'):
            await aggregate('app', 'c', [{'$graphLookup': {'from': 123}}], 10)

    async def test_explain_pipeline_is_checked(self, patch_client, allowlist):
        """ExplainOperation applies the same pipeline check."""
        patch_client()

        with pytest.raises(SafeToolError, match='allowed namespaces'):
            await explain_operation(
                'reports',
                'daily_1',
                'aggregate',
                pipeline=[{'$lookup': {'from': 'weekly', 'as': 'w'}}],
            )

    async def test_write_outside_allowlist_is_rejected(self, patch_client, allowlist, writable):
        """Write tools check the namespace too."""
        patch_client()

        with pytest.raises(SafeToolError, match='allowed namespaces'):
            await write_tools.insert('other', 'c', {'a': 1})
        with pytest.raises(SafeToolError, match='allowed namespaces'):
            await db_management_tools.drop_collection('reports', 'weekly')

    async def test_listings_are_filtered(self, patch_client, allowlist):
        """ListDatabases and listCollections show only allowed namespaces."""
        client = patch_client()
        for db, coll in [
            ('app', 'a'),
            ('reports', 'daily_1'),
            ('reports', 'weekly'),
            ('other', 'x'),
        ]:
            client[db][coll].insert_one({'_id': 1})

        databases = (await db_management_tools.list_databases())['databases']
        assert sorted(databases) == ['app', 'reports']
        assert await db_management_tools.list_collections('reports') == ['daily_1']
        with pytest.raises(SafeToolError, match='allowed namespaces'):
            await db_management_tools.list_collections('other')

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch(
        'sys.argv',
        ['awslabs.documentdb-mcp-server', '--allowed-namespaces', 'app,reports.daily_*'],
    )
    def test_cli_flag(self, mock_run, restore_logger):
        """--allowed-namespaces configures the allowlist."""
        main()
        assert serverConfig.allowed_namespaces == ['app', 'reports.daily_*']

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.documentdb-mcp-server'])
    @patch.dict('os.environ', {'DOCUMENTDB_ALLOWED_NAMESPACES': 'app'})
    def test_env_var(self, mock_run, restore_logger):
        """DOCUMENTDB_ALLOWED_NAMESPACES configures the allowlist when the flag is absent."""
        main()
        assert serverConfig.allowed_namespaces == ['app']

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.documentdb-mcp-server', '--allowed-namespaces', '.bad'])
    def test_invalid_flag_exits(self, mock_run, restore_logger):
        """An invalid pattern stops startup."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        mock_run.assert_not_called()
