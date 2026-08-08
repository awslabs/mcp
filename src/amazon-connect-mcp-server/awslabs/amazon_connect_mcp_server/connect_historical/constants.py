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

"""Constants for Amazon Connect historical metric tools.

These cover the GetMetricDataV2 API used for historical reporting. See the API
reference for the complete metric catalog and threshold/grouping rules:
https://docs.aws.amazon.com/connect/latest/APIReference/API_GetMetricDataV2.html
"""

# A commonly used subset of GetMetricDataV2 metric names. The API accepts many
# more; this list is what the tool defaults to and validates loose input against.
COMMON_HISTORICAL_METRICS = [
    'CONTACTS_HANDLED',
    'CONTACTS_ABANDONED',
    'CONTACTS_QUEUED',
    'CONTACTS_CREATED',
    'AVG_HANDLE_TIME',
    'AVG_ABANDON_TIME',
    'AVG_QUEUE_ANSWER_TIME',
    'AVG_HOLD_TIME',
    'AVG_AGENT_INTERACTION_TIME',
    'AVG_AFTER_CONTACT_WORK_TIME',
    'SERVICE_LEVEL',
    'ABANDONMENT_RATE',
    'AGENT_OCCUPANCY',
    'MAX_QUEUED_TIME',
    'CONTACTS_TRANSFERRED_OUT',
]

# Valid grouping dimensions for GetMetricDataV2.
VALID_HISTORICAL_GROUPINGS = {
    'QUEUE',
    'CHANNEL',
    'ROUTING_PROFILE',
    'AGENT',
    'AGENT_HIERARCHY_LEVEL_ONE',
    'AGENT_HIERARCHY_LEVEL_TWO',
    'AGENT_HIERARCHY_LEVEL_THREE',
    'AGENT_HIERARCHY_LEVEL_FOUR',
    'AGENT_HIERARCHY_LEVEL_FIVE',
    'CONTACT_REASON',
    'ROUTING_STEP_EXPRESSION',
}

# Metrics that require a Threshold definition (e.g., service level). For these we
# default to a 120-second 'less than or equal to' comparison if none is supplied.
THRESHOLD_METRICS = {'SERVICE_LEVEL', 'CONTACTS_QUEUED_BY_ENQUEUE'}

DEFAULT_SERVICE_LEVEL_THRESHOLD_SECONDS = 120

# GetMetricDataV2 retains historical data for the last 90 days (3 months).
MAX_LOOKBACK_DAYS = 90

# GetMetricDataV2 requires the StartTime->EndTime window of a single request to be
# at most 24 hours. Wider requested ranges are split into chunks of this size.
MAX_INTERVAL_HOURS = 24

# Safety cap on the number of 24-hour chunks fetched for one report (90 days).
MAX_INTERVAL_CHUNKS = 90

# Wall-clock budget (seconds) for the multi-interval fetch loop. MCP hosts such
# as Amazon Quick enforce a fixed 60-second per-operation timeout, so we stop
# early and return partial results rather than exceeding the host limit.
INTERVAL_FETCH_BUDGET_SECONDS = 45
