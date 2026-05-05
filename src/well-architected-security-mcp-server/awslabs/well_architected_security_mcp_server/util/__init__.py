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

"""Utility functions for AWS Security Pillar MCP Server."""

from .resource_utils import list_services_in_region
from .security_services import (
    check_access_analyzer,
    check_guard_duty,
    check_inspector,
    check_security_hub,
    get_access_analyzer_findings,
    get_guardduty_findings,
    get_inspector_findings,
    get_securityhub_findings,
)

# Export all imported functions
__all__ = [
    # Security service functions
    "check_access_analyzer",
    "check_security_hub",
    "check_guard_duty",
    "check_inspector",
    "get_guardduty_findings",
    "get_securityhub_findings",
    "get_inspector_findings",
    "get_access_analyzer_findings",
    # Resource utility functions
    "list_services_in_region",
]
