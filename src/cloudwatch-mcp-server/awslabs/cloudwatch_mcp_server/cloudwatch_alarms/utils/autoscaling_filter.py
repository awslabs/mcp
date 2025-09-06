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

"""Utility class for detecting alarms with autoscaling actions."""

from typing import Any, Dict, List


class AutoscalingActionFilter:
    """Utility class for detecting alarms with autoscaling actions.

    This class provides instance methods to identify CloudWatch alarms that contain
    autoscaling actions in their action fields. Autoscaling actions are identified
    by their ARN prefix 'arn:aws:autoscaling:'.

    The filtering logic examines all three action fields of an alarm:
    - AlarmActions: Actions to execute when the alarm transitions to ALARM state
    - OKActions: Actions to execute when the alarm transitions to OK state
    - InsufficientDataActions: Actions to execute when the alarm transitions to INSUFFICIENT_DATA state

    An alarm is considered to have autoscaling actions if any of these fields
    contains at least one action ARN with the autoscaling prefix.
    """

    # ARN prefix for autoscaling actions
    AUTOSCALING_ARN_PREFIX = 'arn:aws:autoscaling:'

    def has_autoscaling_actions(self, alarm_data: Dict[str, Any]) -> bool:
        """Determine if an alarm has any autoscaling actions.

        This method examines all action fields of a CloudWatch alarm to determine
        if it contains any autoscaling-related actions. An alarm is considered to
        have autoscaling actions if any action ARN in any of the action fields
        starts with the autoscaling ARN prefix.

        Args:
            alarm_data: Raw alarm data from CloudWatch API response. Expected to
                       contain action fields like 'AlarmActions', 'OKActions',
                       and 'InsufficientDataActions'.

        Returns:
            bool: True if the alarm has at least one autoscaling action in any
                  action field, False otherwise.

        Examples:
            >>> filter_instance = AutoscalingActionFilter()
            >>> alarm_with_autoscaling = {
            ...     'AlarmName': 'test-alarm',
            ...     'AlarmActions': [
            ...         'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:...'
            ...     ],
            ... }
            >>> filter_instance.has_autoscaling_actions(alarm_with_autoscaling)
            True

            >>> alarm_without_autoscaling = {
            ...     'AlarmName': 'test-alarm',
            ...     'AlarmActions': ['arn:aws:sns:us-east-1:123456789012:alert-topic'],
            ... }
            >>> filter_instance.has_autoscaling_actions(alarm_without_autoscaling)
            False
        """
        # List of action fields to check in the alarm data
        action_fields = ['AlarmActions', 'OKActions', 'InsufficientDataActions']

        # Check each action field for autoscaling actions
        for field in action_fields:
            actions = alarm_data.get(field, [])
            if self._check_action_list(actions):
                return True

        return False

    def _check_action_list(self, actions: List[str]) -> bool:
        """Check if any action in the list is an autoscaling action.

        This helper method examines a list of action ARNs to determine if any
        of them are autoscaling-related. An action is considered autoscaling-related
        if it starts with the autoscaling ARN prefix.

        Args:
            actions: List of action ARNs to check. Each action should be a string
                    representing an AWS resource ARN.

        Returns:
            bool: True if any action in the list is autoscaling-related,
                  False otherwise.

        Note:
            This method includes type checking to handle cases where the actions
            list might contain non-string values, which could occur with malformed
            API responses.
        """
        return any(
            action.startswith(self.AUTOSCALING_ARN_PREFIX)
            for action in actions
            if isinstance(action, str)
        )
