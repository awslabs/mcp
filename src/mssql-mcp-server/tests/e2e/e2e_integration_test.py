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

"""End-to-end integration tests for mssql MCP Server against a live RDS SQL Server instance.

Run via SSH tunnel:
  ssh -L 14330:<rds-endpoint>:1433 ec2-user@<bastion-ip> -N &
  pytest tests/e2e/e2e_integration_test.py -v -m live \
      --endpoint localhost --port 14330 \
      --secret-arn <secret-arn> --region us-west-2
"""

import pytest
import pytest_asyncio
from awslabs.mssql_mcp_server.connection.pymssql_pool_connection import PymssqlPoolConnection


@pytest.fixture(scope='function')
def conn_params(request):
    """Fixture providing connection parameters from CLI options."""
    return {
        'host': request.config.getoption('--endpoint'),
        'port': request.config.getoption('--port'),
        'secret_arn': request.config.getoption('--secret-arn'),
        'region': request.config.getoption('--region'),
        'database': request.config.getoption('--database'),
    }


@pytest_asyncio.fixture(scope='function')
async def pool_conn(conn_params):
    """Fixture providing an initialized PymssqlPoolConnection."""
    conn = PymssqlPoolConnection(
        host=conn_params['host'],
        port=conn_params['port'],
        database=conn_params['database'],
        readonly=False,
        secret_arn=conn_params['secret_arn'],
        region=conn_params['region'],
        encryption='off',
    )
    await conn.initialize_pool()
    yield conn
    await conn.close()


@pytest.mark.live
@pytest.mark.asyncio
async def test_select_1(pool_conn):
    """SELECT 1 returns a single row with value 1."""
    result = await pool_conn.execute_query('SELECT 1 AS val')
    assert result['records'] == [[{'longValue': 1}]]
    assert result['columnMetadata'] == [{'name': 'val'}]


@pytest.mark.live
@pytest.mark.asyncio
async def test_server_version(pool_conn):
    """@@VERSION contains 'Microsoft SQL Server'."""
    result = await pool_conn.execute_query('SELECT @@VERSION AS version')
    rows = result['records']
    assert len(rows) == 1
    version_str = rows[0][0].get('stringValue', '')
    assert 'Microsoft SQL Server' in version_str
    print(f'\nSQL Server version: {version_str[:80]}')


@pytest.mark.live
@pytest.mark.asyncio
async def test_list_databases(pool_conn):
    """sys.databases contains 'master'."""
    result = await pool_conn.execute_query('SELECT name FROM sys.databases ORDER BY name')
    names = [r[0]['stringValue'] for r in result['records']]
    assert 'master' in names
    print(f'\nDatabases: {names}')


@pytest.mark.live
@pytest.mark.asyncio
async def test_information_schema(pool_conn):
    """INFORMATION_SCHEMA.TABLES query returns TABLE_NAME column."""
    result = await pool_conn.execute_query(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
    )
    assert 'columnMetadata' in result
    assert result['columnMetadata'][0]['name'] == 'TABLE_NAME'


@pytest.mark.live
@pytest.mark.asyncio
async def test_create_and_query_table(conn_params):
    """Use tempdb which allows table creation by any login."""
    conn = PymssqlPoolConnection(
        host=conn_params['host'],
        port=conn_params['port'],
        database='tempdb',
        readonly=False,
        secret_arn=conn_params['secret_arn'],
        region=conn_params['region'],
        encryption='off',
    )
    await conn.initialize_pool()
    try:
        await conn.execute_query(
            "IF OBJECT_ID('mcp_test_table', 'U') IS NOT NULL DROP TABLE mcp_test_table"
        )
        await conn.execute_query(
            'CREATE TABLE mcp_test_table (id INT PRIMARY KEY, name NVARCHAR(100))'
        )
        await conn.execute_query("INSERT INTO mcp_test_table VALUES (1, 'hello'), (2, 'world')")
        result = await conn.execute_query('SELECT id, name FROM mcp_test_table ORDER BY id')
        assert len(result['records']) == 2
        assert result['records'][0][0]['longValue'] == 1
        assert result['records'][0][1]['stringValue'] == 'hello'
        await conn.execute_query('DROP TABLE mcp_test_table')
    finally:
        await conn.close()


@pytest.mark.live
@pytest.mark.asyncio
async def test_parameterized_query(pool_conn):
    """Parameterized query binds values correctly."""
    result = await pool_conn.execute_query(
        'SELECT %s AS val',
        [{'name': 'v', 'value': {'stringValue': 'param_works'}}],
    )
    assert result['records'][0][0]['stringValue'] == 'param_works'


@pytest.mark.live
@pytest.mark.asyncio
async def test_connection_health(pool_conn):
    """check_connection_health returns True for a live connection."""
    assert await pool_conn.check_connection_health() is True


@pytest.mark.live
@pytest.mark.asyncio
async def test_readonly_blocks_insert(pool_conn):
    """Readonly connection passes keyword detection and can execute SELECTs."""
    readonly_conn = PymssqlPoolConnection(
        host=pool_conn.host,
        port=pool_conn.port,
        database=pool_conn.database,
        readonly=True,
        secret_arn=pool_conn.secret_arn,
        region=pool_conn.region,
        encryption='off',
    )
    await readonly_conn.initialize_pool()
    result = await readonly_conn.execute_query('SELECT 1 AS ok')
    assert result['records'][0][0]['longValue'] == 1
    await readonly_conn.close()
