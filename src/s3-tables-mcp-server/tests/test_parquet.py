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

"""Tests for Parquet file processor (import_parquet_to_table)."""

import pytest
from awslabs.s3_tables_mcp_server.file_processor import parquet
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_import_parquet_to_table_success():
    """Test successful import_parquet_to_table."""
    # Arrange
    warehouse = 'test-warehouse'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/test.parquet'
    uri = 'http://localhost:8181'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    preserve_case = False

    # Patch import_file_to_table to simulate a successful import
    success_result = {
        'status': 'success',
        'message': 'Successfully imported 2 rows',
        'rows_processed': 2,
        'file_processed': 'test.parquet',
        'table_created': True,
        'table_uuid': 'fake-uuid',
        'columns': ['col1', 'col2'],
    }
    with patch(
        'awslabs.s3_tables_mcp_server.file_processor.parquet.import_file_to_table',
        new=AsyncMock(return_value=success_result),
    ):
        # Act
        result = await parquet.import_parquet_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
            preserve_case=preserve_case,
        )

    # Assert
    assert result['status'] == 'success'
    assert result['rows_processed'] == 2
    assert result['file_processed'] == 'test.parquet'
    assert result['table_created'] is True
    assert result['columns'] == ['col1', 'col2']
