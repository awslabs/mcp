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

"""Pytest configuration and fixtures for CloudWatch alarms tests."""

# Import all fixtures from fixtures.py to make them available to all test files
from fixtures import (
    autoscaling_composite_alarm,
    autoscaling_like_arns_alarm,
    autoscaling_metric_alarm,
    empty_actions_alarm,
    empty_response,
    large_dataset_response,
    malformed_actions_alarm,
    missing_actions_alarm,
    mixed_actions_metric_alarm,
    multi_page_filtering_response,
    non_autoscaling_composite_alarm,
    non_autoscaling_metric_alarm,
    realistic_target_tracking_alarm,
    single_page_mixed_response,
)


# Re-export all fixtures so they're available to test files
__all__ = [
    'autoscaling_metric_alarm',
    'non_autoscaling_metric_alarm',
    'mixed_actions_metric_alarm',
    'autoscaling_composite_alarm',
    'non_autoscaling_composite_alarm',
    'empty_actions_alarm',
    'missing_actions_alarm',
    'malformed_actions_alarm',
    'autoscaling_like_arns_alarm',
    'realistic_target_tracking_alarm',
    'single_page_mixed_response',
    'multi_page_filtering_response',
    'large_dataset_response',
    'empty_response',
]
