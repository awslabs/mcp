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

"""Live integration tests for the RDS for Db2 MCP server.

These run only against a real RDS for Db2 instance and are deselected by
default. Provide connection details via environment variables and run with
``uv run --frozen pytest -m live`` after exporting RDS_DB2_ENDPOINT,
RDS_DB2_REGION, RDS_DB2_DATABASE, and RDS_DB2_SECRET_ARN.

Requirements: network reachability to the instance (VPC/SG on 50443), a valid
master-user secret, and the RDS regional SSL certificate bundle when SSL is on.
"""

import os
import pytest
from awslabs.db2_mcp_server.connection.ibm_db_connection import IbmDbConnection


pytestmark = pytest.mark.live

_REQUIRED = ('RDS_DB2_ENDPOINT', 'RDS_DB2_REGION', 'RDS_DB2_DATABASE', 'RDS_DB2_SECRET_ARN')


def _require_env():
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        pytest.skip(f'Missing env for live test: {", ".join(missing)}')


@pytest.mark.asyncio
async def test_live_health_check():
    """A read-only connection can run SELECT 1 FROM SYSIBM.SYSDUMMY1."""
    _require_env()
    conn = IbmDbConnection(
        host=os.environ['RDS_DB2_ENDPOINT'],
        port=int(os.environ.get('RDS_DB2_PORT', '50443')),
        database=os.environ['RDS_DB2_DATABASE'],
        readonly=True,
        secret_arn=os.environ['RDS_DB2_SECRET_ARN'],
        region=os.environ['RDS_DB2_REGION'],
        ssl_encryption=os.environ.get('RDS_DB2_SSL', 'require'),
        ssl_server_certificate=os.environ.get('RDS_DB2_SSL_CERT'),
        ssl_hostname_validation=os.environ.get('RDS_DB2_SSL_HOSTNAME_VALIDATION', 'basic')
        != 'off',
    )
    try:
        assert await conn.check_connection_health() is True
    finally:
        await conn.close()
