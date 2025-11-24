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

"""Data models for CloudFormation template validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ValidationIssue:
    """Individual validation issue."""

    rule: str
    level: str
    message: str
    filename: str
    line_number: int
    column_number: int
    fix_suggestion: str


@dataclass
class ValidationResults:
    """Validation results summary."""

    is_valid: bool
    error_count: int
    warning_count: int
    info_count: int


@dataclass
class ValidationResponse:
    """Complete validation response."""

    validation_results: ValidationResults
    issues: List[ValidationIssue]
    message: str
