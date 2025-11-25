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

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class StackEvent:
    """CloudFormation stack event."""

    timestamp: datetime
    resource_type: str
    logical_resource_id: str
    resource_status: str
    resource_status_reason: Optional[str] = None


@dataclass
class FailedResource:
    """Failed CloudFormation resource."""

    logical_id: str
    resource_type: str
    status: str
    status_reason: str
    timestamp: datetime
    cloudtrail_link: Optional[str] = None


@dataclass
class DeploymentResponse:
    """Complete deployment troubleshooting response."""

    stack_name: str
    stack_status: str
    failed_resources: List[FailedResource]
    events: List[StackEvent]
    root_cause_analysis: str
    remediation_steps: List[str]
    console_deeplink: str
