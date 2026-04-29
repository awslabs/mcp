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

"""Data models for SSM for SAP configuration check tools."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ConfigCheckDefinition(BaseModel):
    """A configuration check definition."""

    id: str = Field(..., description='Configuration check ID')
    name: Optional[str] = Field(default=None, description='Check name')
    description: Optional[str] = Field(default=None, description='Check description')


class ConfigCheckOperation(BaseModel):
    """A configuration check operation result."""

    check_id: str = Field(..., description='Configuration check ID')
    operation_id: Optional[str] = Field(default=None, description='Operation ID')
    status: str = Field(..., description='Operation status')
    result: Optional[str] = Field(default=None, description='Check result')
    last_updated: Optional[str] = Field(default=None, description='Last updated timestamp')
    subchecks: Optional[List['SubCheckResult']] = Field(
        default=None, description='Sub-check results when include_subchecks is True'
    )


class SubCheckResult(BaseModel):
    """A sub-check result within a configuration check."""

    id: str = Field(..., description='Sub-check result ID')
    name: str = Field(..., description='Sub-check name')
    result: str = Field(..., description='Sub-check result')
    description: Optional[str] = Field(default=None, description='Sub-check description')
    rule_results: Optional[List[Dict[str, Any]]] = Field(
        default=None, description='Rule-level results'
    )


class ConfigCheckSummary(BaseModel):
    """Summary of configuration check results for an application."""

    application_id: str = Field(..., description='Application ID')
    total_checks: int = Field(default=0, description='Total number of checks')
    by_status: Dict[str, int] = Field(default_factory=dict, description='Counts by status')
    by_result: Dict[str, int] = Field(default_factory=dict, description='Counts by result')
    checks: List[ConfigCheckOperation] = Field(
        default_factory=list, description='Individual check results'
    )


class StartConfigChecksResponse(BaseModel):
    """Response from starting configuration checks."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Status message')
    operations: Optional[List[Dict[str, Any]]] = Field(
        default=None, description='Initiated operations'
    )
