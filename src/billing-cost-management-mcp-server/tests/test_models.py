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

"""Tests for models.py."""

import pytest
from awslabs.billing_cost_management_mcp_server.models import (
    APIStatus,
    BaseResponse,
    ColumnDefinition,
    CostMetric,
    DateGranularity,
    DateRange,
    ErrorResponse,
    SchemaFormat,
    SchemaInfo,
    StorageLensQueryRequest,
    SuccessResponse,
)


def test_api_status_enum():
    """Test APIStatus enum values."""
    assert APIStatus.SUCCESS == 'success'
    assert APIStatus.ERROR == 'error'


def test_cost_metric_enum():
    """Test CostMetric enum values."""
    assert CostMetric.UNBLENDED_COST == 'UnblendedCost'
    assert CostMetric.BLENDED_COST == 'BlendedCost'


def test_date_granularity_enum():
    """Test DateGranularity enum values."""
    assert DateGranularity.DAILY == 'DAILY'
    assert DateGranularity.MONTHLY == 'MONTHLY'


def test_schema_format_enum():
    """Test SchemaFormat enum values."""
    assert SchemaFormat.CSV == 'CSV'
    assert SchemaFormat.PARQUET == 'PARQUET'


def test_base_response():
    """Test BaseResponse model."""
    response = BaseResponse(status=APIStatus.SUCCESS, message='Test message')
    assert response.status == APIStatus.SUCCESS
    assert response.message == 'Test message'


def test_error_response():
    """Test ErrorResponse model."""
    response = ErrorResponse(error_code='TEST_ERROR')
    assert response.status == APIStatus.ERROR
    assert response.error_code == 'TEST_ERROR'


def test_success_response():
    """Test SuccessResponse model."""
    response = SuccessResponse(data={'test': 'data'})
    assert response.status == APIStatus.SUCCESS
    assert response.data == {'test': 'data'}


def test_date_range():
    """Test DateRange model."""
    date_range = DateRange(start_date='2023-01-01', end_date='2023-01-31')
    assert date_range.start_date == '2023-01-01'
    assert date_range.end_date == '2023-01-31'


def test_date_range_validation():
    """Test DateRange validation."""
    with pytest.raises(ValueError):
        DateRange(start_date='invalid-date', end_date='2023-01-31')


def test_column_definition():
    """Test ColumnDefinition model."""
    column = ColumnDefinition(name='test_column', type='string')
    assert column.name == 'test_column'
    assert column.type == 'string'
    assert column.nullable is True


def test_schema_info():
    """Test SchemaInfo model."""
    columns = [ColumnDefinition(name='col1', type='string')]
    schema = SchemaInfo(format=SchemaFormat.CSV, columns=columns)
    assert schema.format == SchemaFormat.CSV
    assert len(schema.columns) == 1


def test_storage_lens_query_request():
    """Test StorageLensQueryRequest model."""
    request = StorageLensQueryRequest(
        manifest_location='s3://bucket/manifest/', query='SELECT * FROM table'
    )
    assert request.manifest_location == 's3://bucket/manifest/'
    assert request.query == 'SELECT * FROM table'
