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

"""Data models for CloudFormation compliance checking."""

from dataclasses import dataclass
from typing import List


@dataclass
class ComplianceViolation:
    """Individual compliance violation."""

    rule_id: str
    severity: str
    resource: str
    resource_type: str
    message: str
    remediation: str


@dataclass
class ComplianceResults:
    """Compliance results summary."""

    overall_status: str
    total_violations: int
    error_count: int
    warning_count: int
    rule_sets_applied: List[str]


@dataclass
class ComplianceResponse:
    """Complete compliance response."""

    compliance_results: ComplianceResults
    violations: List[ComplianceViolation]
    message: str
