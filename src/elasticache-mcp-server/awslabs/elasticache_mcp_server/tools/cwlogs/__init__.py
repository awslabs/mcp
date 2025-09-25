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

"""CloudWatch Logs tools."""

from .get_log_events import get_log_events
from .create_log_group import create_log_group
from .describe_log_groups import describe_log_groups
from .describe_log_streams import describe_log_streams
from .filter_log_events import filter_log_events

__all__ = [
    'get_log_events',
    'create_log_group',
    'describe_log_groups',
    'describe_log_streams',
    'filter_log_events',
]
