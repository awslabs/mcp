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

"""Pydantic-based cost models for DynamoDB Cost & Performance Calculator."""

from pydantic import BaseModel, Field
from typing import List


class GSIWriteAmplification(BaseModel):
    """Write amplification metrics for a single GSI affected by a write operation."""

    gsi_name: str
    wcus: float
    cost: float


class AccessPatternResult(BaseModel):
    """Calculated performance and cost metrics for a single access pattern.

    References the input access pattern by pattern ID. All input fields
    (description, table, rps, item_size_bytes, etc.) can be retrieved from
    the original input using the pattern field.
    """

    pattern: str  # References AccessPattern.pattern from input
    rcus: float = 0.0
    wcus: float = 0.0  # Base table only
    cost: float = 0.0  # Base table only
    gsi_write_amplification: List[GSIWriteAmplification] = Field(default_factory=list)


class TableResult(BaseModel):
    """Calculated storage metrics for a table.

    References the input table by name. All input fields (item_count,
    item_size_bytes, gsi_list) can be retrieved from the original input.
    """

    table_name: str  # References Table.name from input
    storage_gb: float
    storage_cost: float


class GSIResult(BaseModel):
    """Calculated storage metrics for a GSI.

    References the input GSI by name and parent table.
    """

    gsi_name: str  # References GSI.name from input
    table_name: str  # Parent table name
    storage_gb: float
    storage_cost: float


class CostModel(BaseModel):
    """Output from CostCalculator with capacity and cost metrics."""

    access_patterns: List[AccessPatternResult]
    tables: List[TableResult] = Field(default_factory=list)
    gsis: List[GSIResult] = Field(default_factory=list)
