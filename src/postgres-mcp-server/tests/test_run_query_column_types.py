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
"""run_query result shapes for bytea, json/jsonb and array columns.

Both connection methods must hand the caller the same JSON-safe value for the
same column: bytea as a hex string, json/jsonb as JSON text and arrays
as JSON lists. The PG wire path is driven through ``PsycopgPoolConnection.execute_query``
with a mocked cursor; the RDS Data API path uses the response shapes the Data
API returns. Both go through the real ``parse_execute_response``.
"""

import boto3
import json
import pytest
from awslabs.postgres_mcp_server.connection.db_connection_map import ConnectionMethod
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import PsycopgPoolConnection
from awslabs.postgres_mcp_server.server import DummyCtx, parse_execute_response, run_query
from botocore.stub import Stubber
from unittest.mock import AsyncMock, MagicMock, patch


# PostgreSQL type OIDs (pg_type.oid)
OID_BOOL = 16
OID_BYTEA = 17
OID_INT4 = 23
OID_TEXT = 25
OID_JSON = 114
OID_JSONB = 3802
OID_BOOL_ARRAY = 1000
OID_INT4_ARRAY = 1007
OID_TEXT_ARRAY = 1009
OID_FLOAT8_ARRAY = 1022

PNG_HEADER = b'\x89PNG\r\n\x1a\n\x00\xff'  # not valid UTF-8

# (case id, value psycopg returns, type OID, cell the RDS Data API returns, expected result)
CASES = [
    pytest.param(
        PNG_HEADER,
        OID_BYTEA,
        {'blobValue': PNG_HEADER},
        '\\x89504e470d0a1a0a00ff',
        id='bytea-binary',
    ),
    pytest.param(b'hi', OID_BYTEA, {'blobValue': b'hi'}, '\\x6869', id='bytea-valid-utf8'),
    pytest.param(b'', OID_BYTEA, {'blobValue': b''}, '\\x', id='bytea-empty'),
    pytest.param(
        {'a': True, 'b': None, 'c': 'x'},
        OID_JSONB,
        {'stringValue': '{"a": true, "b": null, "c": "x"}'},
        '{"a": true, "b": null, "c": "x"}',
        id='jsonb-object',
    ),
    pytest.param(
        [1, 'a', None],
        OID_JSON,
        {'stringValue': '[1, "a", null]'},
        '[1, "a", null]',
        id='json-list',
    ),
    pytest.param('x', OID_JSONB, {'stringValue': '"x"'}, '"x"', id='jsonb-string-scalar'),
    pytest.param(7, OID_JSONB, {'stringValue': '7'}, '7', id='jsonb-number-scalar'),
    pytest.param(
        ['red', 'blue'],
        OID_TEXT_ARRAY,
        {'arrayValue': {'stringValues': ['red', 'blue']}},
        ['red', 'blue'],
        id='text-array',
    ),
    pytest.param(
        [1, 2, 3],
        OID_INT4_ARRAY,
        {'arrayValue': {'longValues': [1, 2, 3]}},
        [1, 2, 3],
        id='int-array',
    ),
    pytest.param(
        [1.5, 2.5],
        OID_FLOAT8_ARRAY,
        {'arrayValue': {'doubleValues': [1.5, 2.5]}},
        [1.5, 2.5],
        id='double-array',
    ),
    pytest.param(
        [True, False],
        OID_BOOL_ARRAY,
        {'arrayValue': {'booleanValues': [True, False]}},
        [True, False],
        id='bool-array',
    ),
    pytest.param(
        [[1, 2], [3, 4]],
        OID_INT4_ARRAY,
        {'arrayValue': {'arrayValues': [{'longValues': [1, 2]}, {'longValues': [3, 4]}]}},
        [[1, 2], [3, 4]],
        id='nested-int-array',
    ),
    pytest.param('plain', OID_TEXT, {'stringValue': 'plain'}, 'plain', id='text-unchanged'),
    pytest.param(5, OID_INT4, {'longValue': 5}, 5, id='int-unchanged'),
]


def _psycopg_connection_returning(rows, description):
    """A real PsycopgPoolConnection whose cursor yields ``rows`` / ``description``."""
    connection = PsycopgPoolConnection(
        host='localhost',
        port=5432,
        database='db',
        readonly=True,
        secret_arn='arn',  # pragma: allowlist secret
        db_user='user',
        region='us-east-1',
        is_test=True,
    )

    cursor = MagicMock()
    cursor.description = description
    cursor.execute = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=rows)
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=None)

    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)

    conn = MagicMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    conn.transaction.return_value = transaction
    conn.cursor.return_value = cursor
    conn.execute = AsyncMock()

    connection._get_connection = AsyncMock(return_value=conn)
    return connection


@pytest.mark.asyncio
@pytest.mark.parametrize('pg_value, oid, rds_cell, expected', CASES)
async def test_pg_wire_column_type(pg_value, oid, rds_cell, expected):
    """PG wire: each column type comes back JSON-safe and in the expected shape."""
    connection = _psycopg_connection_returning([(pg_value,)], [('col', oid)])

    response = await connection.execute_query('SELECT col FROM t')
    rows = parse_execute_response(response)

    assert rows == [{'col': expected}]
    json.dumps(rows)  # must not raise


@pytest.mark.parametrize('pg_value, oid, rds_cell, expected', CASES)
def test_rds_api_column_type(pg_value, oid, rds_cell, expected):
    """RDS Data API: each column type comes back JSON-safe and in the expected shape."""
    response = {'columnMetadata': [{'name': 'col'}], 'records': [[rds_cell]]}

    rows = parse_execute_response(response)

    assert rows == [{'col': expected}]
    json.dumps(rows)  # must not raise


@pytest.mark.asyncio
@pytest.mark.parametrize('pg_value, oid, rds_cell, expected', CASES)
async def test_both_paths_return_the_same_value(pg_value, oid, rds_cell, expected):
    """The same column must not change shape with the connection method."""
    pg_connection = _psycopg_connection_returning([(pg_value,)], [('col', oid)])
    pg_rows = parse_execute_response(await pg_connection.execute_query('SELECT col FROM t'))
    rds_rows = parse_execute_response(
        {'columnMetadata': [{'name': 'col'}], 'records': [[rds_cell]]}
    )

    assert pg_rows == rds_rows


@pytest.mark.asyncio
@pytest.mark.parametrize('pg_value, oid, rds_cell, expected', CASES)
async def test_pg_wire_cells_are_valid_data_api_cells(pg_value, oid, rds_cell, expected):
    """The cells the PG wire path builds must be valid RDS Data API ``Field`` values."""
    connection = _psycopg_connection_returning([(pg_value,)], [('col', oid)])
    response = await connection.execute_query('SELECT col FROM t')

    client = boto3.client(
        'rds-data',
        region_name='us-east-1',
        aws_access_key_id='test',  # pragma: allowlist secret
        aws_secret_access_key='test',  # pragma: allowlist secret
    )
    with Stubber(client) as stubber:
        stubber.add_response('execute_statement', response)
        returned = client.execute_statement(
            resourceArn='arn:aws:rds:us-east-1:123456789012:cluster:c',
            secretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:s',  # pragma: allowlist secret
            sql='SELECT 1',
        )

    assert returned['records'] == response['records']


@pytest.mark.asyncio
async def test_pg_wire_mixed_row_with_nulls():
    """All three problem types in one row (the table from the bug report), plus NULLs."""
    description = [
        ('id', OID_INT4),
        ('payload', OID_BYTEA),
        ('meta', OID_JSONB),
        ('tags', OID_TEXT_ARRAY),
        ('missing_blob', OID_BYTEA),
        ('missing_json', OID_JSONB),
        ('missing_array', OID_TEXT_ARRAY),
    ]
    row = (
        1,
        PNG_HEADER,
        {'a': True, 'b': None, 'c': 'x'},
        ['red', 'blue'],
        None,
        None,
        None,
    )
    connection = _psycopg_connection_returning([row], description)

    rows = parse_execute_response(await connection.execute_query('SELECT * FROM docs'))

    assert rows == [
        {
            'id': 1,
            'payload': '\\x89504e470d0a1a0a00ff',
            'meta': '{"a": true, "b": null, "c": "x"}',
            'tags': ['red', 'blue'],
            'missing_blob': None,
            'missing_json': None,
            'missing_array': None,
        }
    ]
    json.dumps(rows)


@pytest.mark.asyncio
async def test_pg_wire_array_with_null_elements_and_empty_array():
    """NULL elements stay null and an empty array is an empty list."""
    connection = _psycopg_connection_returning(
        [(['a', None], [1, None], [])],
        [('t', OID_TEXT_ARRAY), ('i', OID_INT4_ARRAY), ('e', OID_TEXT_ARRAY)],
    )

    rows = parse_execute_response(await connection.execute_query('SELECT 1'))

    assert rows == [{'t': ['a', None], 'i': [1, None], 'e': []}]


@pytest.mark.asyncio
async def test_pg_wire_json_array_column_elements_are_json_text():
    """jsonb[] elements are JSON text, not Python reprs."""
    connection = _psycopg_connection_returning(
        [([{'k': 1}, {'k': None}],)],
        [('col', 3807)],  # 3807 = jsonb[]
    )

    rows = parse_execute_response(await connection.execute_query('SELECT 1'))

    assert rows == [{'col': ['{"k": 1}', '{"k": null}']}]


@pytest.mark.asyncio
async def test_pg_wire_description_without_type_code_still_works():
    """A description entry that carries only a name falls back to value-based mapping."""
    connection = _psycopg_connection_returning([(1, 'x')], [('a',), ('b',)])

    rows = parse_execute_response(await connection.execute_query('SELECT 1'))

    assert rows == [{'a': 1, 'b': 'x'}]


@pytest.mark.asyncio
async def test_run_query_returns_serializable_rows_for_bytea():
    """run_query hands back rows that serialize, where raw bytes used to break the call."""
    connection = AsyncMock()
    connection.readonly_query = True
    connection.execute_query.return_value = {
        'columnMetadata': [{'name': 'id'}, {'name': 'payload'}, {'name': 'tags'}],
        'records': [
            [
                {'longValue': 1},
                {'blobValue': PNG_HEADER},
                {'arrayValue': {'stringValues': ['red', 'blue']}},
            ]
        ],
    }
    with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
        mock_map.get.return_value = connection
        result = await run_query(
            sql='SELECT * FROM docs',
            ctx=DummyCtx(),
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='c',
            db_endpoint='e',
            database='d',
        )

    assert result == [{'id': 1, 'payload': '\\x89504e470d0a1a0a00ff', 'tags': ['red', 'blue']}]
    json.dumps(result)
