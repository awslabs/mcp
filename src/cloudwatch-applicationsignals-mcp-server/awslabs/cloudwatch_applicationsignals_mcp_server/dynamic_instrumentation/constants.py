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
"""Shared constants for dynamic instrumentation support."""

SNAPSHOT_SIGNAL_TYPE = 'SNAPSHOT'

# Dynamic instrumentation snapshots are written to a per-service CloudWatch Logs
# group. ``{service_name}`` is substituted with the target service name at query
# time via ``resolve_snapshot_log_group``.
SNAPSHOT_LOG_GROUP_TEMPLATE = '/aws/service-events/{service_name}'


def resolve_snapshot_log_group(service_name: str) -> str:
    """Resolve the per-service snapshot log group name."""
    return SNAPSHOT_LOG_GROUP_TEMPLATE.format(service_name=service_name)
