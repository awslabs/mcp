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

"""DynamoDB Cost & Performance Calculator - Core calculation logic."""

from awslabs.dynamodb_mcp_server.cost_performance_calculator.cost_model import (
    AccessPatternResult,
    CostModel,
    GSIResult,
    GSIWriteAmplification,
    TableResult,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import DataModel


SECONDS_PER_MONTH = 2_635_200  # 30.5 days

# us-east-1 - Jan 2026 - https://aws.amazon.com/dynamodb/pricing/on-demand/
RCU_PRICE = 0.125 / 1_000_000  # $0.125 per million RRU
WCU_PRICE = 0.625 / 1_000_000  # $0.625 per million WRU
STORAGE_PRICE = 0.25  # $0.25 per GB-month


def calculate_cost(input_data: DataModel) -> CostModel:
    """Calculate cost and performance metrics from input data."""
    table_map = {table.name: table for table in input_data.table_list}

    access_patterns = [
        _calculate_access_pattern(ap, table_map) for ap in input_data.access_pattern_list
    ]
    tables = [_calculate_table_storage(table) for table in input_data.table_list]
    gsis = [
        _calculate_gsi_storage(gsi, table.name)
        for table in input_data.table_list
        for gsi in table.gsi_list
    ]

    return CostModel(access_patterns=access_patterns, tables=tables, gsis=gsis)


def _calculate_access_pattern(ap, table_map) -> AccessPatternResult:
    """Calculate metrics for a single access pattern."""
    rcus = ap.calculate_rcus() if hasattr(ap, 'calculate_rcus') else 0.0
    wcus = ap.calculate_wcus() if hasattr(ap, 'calculate_wcus') else 0.0
    cost = (rcus * RCU_PRICE * ap.rps * SECONDS_PER_MONTH) + (
        wcus * WCU_PRICE * ap.rps * SECONDS_PER_MONTH
    )

    gsi_write_amp = []
    if hasattr(ap, 'gsi_list') and ap.gsi_list:
        table = table_map.get(ap.table)
        if table:
            gsi_write_amp = _calculate_gsi_write_amplification(ap, table)

    return AccessPatternResult(
        pattern=ap.pattern,
        rcus=rcus,
        wcus=wcus,
        cost=cost,
        gsi_write_amplification=gsi_write_amp,
    )


def _calculate_gsi_write_amplification(ap, table) -> list[GSIWriteAmplification]:
    """Calculate write amplification for GSIs."""
    gsi_write_amp = []

    for gsi_name, wcus in ap.calculate_gsi_wcus(table):
        cost = wcus * WCU_PRICE * ap.rps * SECONDS_PER_MONTH
        gsi_write_amp.append(GSIWriteAmplification(gsi_name=gsi_name, wcus=wcus, cost=cost))

    return gsi_write_amp


def _calculate_table_storage(table) -> TableResult:
    """Calculate storage metrics for a table."""
    storage_gb = table.storage_gb()
    storage_cost = storage_gb * STORAGE_PRICE
    return TableResult(table_name=table.name, storage_gb=storage_gb, storage_cost=storage_cost)


def _calculate_gsi_storage(gsi, table_name: str) -> GSIResult:
    """Calculate storage metrics for a GSI."""
    storage_gb = gsi.storage_gb()
    storage_cost = storage_gb * STORAGE_PRICE
    return GSIResult(
        gsi_name=gsi.name,
        table_name=table_name,
        storage_gb=storage_gb,
        storage_cost=storage_cost,
    )
