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

"""Comprehensive test data fixtures for CloudWatch alarms filtering tests.

This module provides reusable test fixtures for testing autoscaling alarm filtering
functionality. It includes mock alarm data with various action configurations,
paginated response fixtures, and utilities for creating test scenarios.
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List


# Sample autoscaling action ARNs
AUTOSCALING_SCALE_UP_ARN = 'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:12345678-1234-1234-1234-123456789012:autoScalingGroupName/my-asg:policyName/scale-up'
AUTOSCALING_SCALE_DOWN_ARN = 'arn:aws:autoscaling:us-west-2:987654321098:scalingPolicy:87654321-4321-4321-4321-210987654321:autoScalingGroupName/another-asg:policyName/scale-down'
AUTOSCALING_TARGET_TRACKING_ARN = 'arn:aws:autoscaling:eu-west-1:555666777888:scalingPolicy:target-tracking-policy:autoScalingGroupName/web-tier-asg:policyName/target-tracking-cpu'

# Sample non-autoscaling action ARNs
SNS_ALERT_ARN = 'arn:aws:sns:us-east-1:123456789012:alert-topic'
SNS_CRITICAL_ARN = 'arn:aws:sns:us-east-1:123456789012:critical-alerts'
LAMBDA_HANDLER_ARN = 'arn:aws:lambda:us-east-1:123456789012:function:alert-handler'
SQS_QUEUE_ARN = 'arn:aws:sqs:us-east-1:123456789012:alert-queue'


class AlarmFixtures:
    """Factory class for creating test alarm data fixtures."""

    @staticmethod
    def create_metric_alarm_with_autoscaling_alarm_actions() -> Dict[str, Any]:
        """Create metric alarm with autoscaling actions in AlarmActions field."""
        return {
            'AlarmName': 'autoscaling-cpu-high-alarm',
            'AlarmDescription': 'CPU utilization high - triggers scale up',
            'StateValue': 'ALARM',
            'StateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [85.0] was greater than the threshold (80.0)',
            'StateReasonData': '{"version":"1.0","queryDate":"2024-01-01T12:01:00.000+0000","statistic":"Average","period":300,"recentDatapoints":[85.0],"threshold":80.0}',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [{'Name': 'AutoScalingGroupName', 'Value': 'web-tier-asg'}],
            'Period': 300,
            'EvaluationPeriods': 1,
            'Threshold': 80.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [AUTOSCALING_SCALE_UP_ARN],
            'OKActions': [],
            'InsufficientDataActions': [],
        }

    @staticmethod
    def create_metric_alarm_with_autoscaling_ok_actions() -> Dict[str, Any]:
        """Create metric alarm with autoscaling actions in OKActions field."""
        return {
            'AlarmName': 'autoscaling-cpu-low-alarm',
            'AlarmDescription': 'CPU utilization low - triggers scale down when OK',
            'StateValue': 'OK',
            'StateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [30.0] was not greater than the threshold (40.0)',
            'StateReasonData': '{"version":"1.0","queryDate":"2024-01-01T12:01:00.000+0000","statistic":"Average","period":300,"recentDatapoints":[30.0],"threshold":40.0}',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [{'Name': 'AutoScalingGroupName', 'Value': 'web-tier-asg'}],
            'Period': 300,
            'EvaluationPeriods': 2,
            'Threshold': 40.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [],
            'OKActions': [AUTOSCALING_SCALE_DOWN_ARN],
            'InsufficientDataActions': [],
        }

    @staticmethod
    def create_metric_alarm_with_autoscaling_insufficient_data_actions() -> Dict[str, Any]:
        """Create metric alarm with autoscaling actions in InsufficientDataActions field."""
        return {
            'AlarmName': 'autoscaling-memory-insufficient-data-alarm',
            'AlarmDescription': 'Memory utilization insufficient data - triggers scaling policy',
            'StateValue': 'INSUFFICIENT_DATA',
            'StateReason': 'Insufficient Data: The alarm has insufficient data to determine the alarm state',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'MemoryUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [{'Name': 'AutoScalingGroupName', 'Value': 'app-tier-asg'}],
            'Period': 300,
            'EvaluationPeriods': 1,
            'Threshold': 75.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'breaching',
            'AlarmActions': [],
            'OKActions': [],
            'InsufficientDataActions': [AUTOSCALING_TARGET_TRACKING_ARN],
        }

    @staticmethod
    def create_metric_alarm_with_mixed_actions() -> Dict[str, Any]:
        """Create metric alarm with both autoscaling and non-autoscaling actions."""
        return {
            'AlarmName': 'mixed-actions-cpu-alarm',
            'AlarmDescription': 'CPU alarm with both autoscaling and notification actions',
            'StateValue': 'ALARM',
            'StateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [90.0] was greater than the threshold (85.0)',
            'StateReasonData': '{"version":"1.0","queryDate":"2024-01-01T12:01:00.000+0000","statistic":"Average","period":300,"recentDatapoints":[90.0],"threshold":85.0}',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [
                {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'},
                {'Name': 'AutoScalingGroupName', 'Value': 'mixed-tier-asg'},
            ],
            'Period': 300,
            'EvaluationPeriods': 1,
            'Threshold': 85.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [AUTOSCALING_SCALE_UP_ARN, SNS_ALERT_ARN, LAMBDA_HANDLER_ARN],
            'OKActions': [SNS_ALERT_ARN],
            'InsufficientDataActions': [SQS_QUEUE_ARN],
        }

    @staticmethod
    def create_metric_alarm_without_autoscaling_actions() -> Dict[str, Any]:
        """Create metric alarm with no autoscaling actions."""
        return {
            'AlarmName': 'application-cpu-high-alarm',
            'AlarmDescription': 'Application CPU utilization monitoring',
            'StateValue': 'ALARM',
            'StateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [95.0] was greater than the threshold (90.0)',
            'StateReasonData': '{"version":"1.0","queryDate":"2024-01-01T12:01:00.000+0000","statistic":"Average","period":300,"recentDatapoints":[95.0],"threshold":90.0}',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-abcdef1234567890'}],
            'Period': 300,
            'EvaluationPeriods': 2,
            'Threshold': 90.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [SNS_CRITICAL_ARN, LAMBDA_HANDLER_ARN],
            'OKActions': [SNS_ALERT_ARN],
            'InsufficientDataActions': [SQS_QUEUE_ARN],
        }

    @staticmethod
    def create_metric_alarm_with_empty_actions() -> Dict[str, Any]:
        """Create metric alarm with empty action fields."""
        return {
            'AlarmName': 'empty-actions-alarm',
            'AlarmDescription': 'Alarm with no actions configured',
            'StateValue': 'ALARM',
            'StateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [50.0] was greater than the threshold (45.0)',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'NetworkIn',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Sum',
            'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-empty123456789'}],
            'Period': 300,
            'EvaluationPeriods': 1,
            'Threshold': 45.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [],
            'OKActions': [],
            'InsufficientDataActions': [],
        }

    @staticmethod
    def create_metric_alarm_with_missing_action_fields() -> Dict[str, Any]:
        """Create metric alarm with missing action fields."""
        return {
            'AlarmName': 'missing-actions-alarm',
            'AlarmDescription': 'Alarm with missing action fields',
            'StateValue': 'ALARM',
            'StateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [60.0] was greater than the threshold (55.0)',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'DiskReadOps',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Sum',
            'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-missing123456789'}],
            'Period': 300,
            'EvaluationPeriods': 1,
            'Threshold': 55.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            # Action fields intentionally missing
        }

    @staticmethod
    def create_composite_alarm_with_autoscaling_actions() -> Dict[str, Any]:
        """Create composite alarm with autoscaling actions."""
        return {
            'AlarmName': 'autoscaling-composite-alarm',
            'AlarmDescription': 'Composite alarm for autoscaling based on multiple metrics',
            'StateValue': 'ALARM',
            'StateReason': 'Composite alarm triggered: CPU and Memory thresholds exceeded',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'AlarmRule': 'ALARM("cpu-high-alarm") AND ALARM("memory-high-alarm")',
            'AlarmConfigurationUpdatedTimestamp': datetime(2024, 1, 1, 10, 0, 0),
            'ActionsEnabled': True,
            'AlarmActions': [AUTOSCALING_SCALE_UP_ARN],
            'OKActions': [AUTOSCALING_SCALE_DOWN_ARN],
            'InsufficientDataActions': [],
        }

    @staticmethod
    def create_composite_alarm_without_autoscaling_actions() -> Dict[str, Any]:
        """Create composite alarm without autoscaling actions."""
        return {
            'AlarmName': 'application-health-composite-alarm',
            'AlarmDescription': 'Composite alarm for overall application health monitoring',
            'StateValue': 'ALARM',
            'StateReason': 'Application health degraded: Multiple component failures detected',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'AlarmRule': '(ALARM("database-connection-alarm") OR ALARM("high-error-rate-alarm")) AND NOT ALARM("maintenance-mode-alarm")',
            'AlarmConfigurationUpdatedTimestamp': datetime(2024, 1, 1, 10, 0, 0),
            'ActionsEnabled': True,
            'AlarmActions': [SNS_CRITICAL_ARN, LAMBDA_HANDLER_ARN],
            'OKActions': [SNS_ALERT_ARN],
            'InsufficientDataActions': [SQS_QUEUE_ARN],
        }

    @staticmethod
    def create_composite_alarm_with_mixed_actions() -> Dict[str, Any]:
        """Create composite alarm with both autoscaling and non-autoscaling actions."""
        return {
            'AlarmName': 'mixed-composite-alarm',
            'AlarmDescription': 'Composite alarm with mixed action types',
            'StateValue': 'ALARM',
            'StateReason': 'Mixed composite alarm triggered',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'AlarmRule': 'ALARM("resource-alarm-1") OR ALARM("resource-alarm-2")',
            'AlarmConfigurationUpdatedTimestamp': datetime(2024, 1, 1, 10, 0, 0),
            'ActionsEnabled': True,
            'AlarmActions': [AUTOSCALING_TARGET_TRACKING_ARN, SNS_CRITICAL_ARN],
            'OKActions': [SNS_ALERT_ARN],
            'InsufficientDataActions': [LAMBDA_HANDLER_ARN],
        }


class PaginationFixtures:
    """Factory class for creating paginated response fixtures."""

    @staticmethod
    def create_single_page_response_all_autoscaling() -> List[Dict[str, Any]]:
        """Create single page response with all autoscaling alarms."""
        return [
            {
                'MetricAlarms': [
                    AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions(),
                    AlarmFixtures.create_metric_alarm_with_autoscaling_ok_actions(),
                ],
                'CompositeAlarms': [
                    AlarmFixtures.create_composite_alarm_with_autoscaling_actions()
                ],
            }
        ]

    @staticmethod
    def create_single_page_response_all_non_autoscaling() -> List[Dict[str, Any]]:
        """Create single page response with all non-autoscaling alarms."""
        return [
            {
                'MetricAlarms': [
                    AlarmFixtures.create_metric_alarm_without_autoscaling_actions(),
                    AlarmFixtures.create_metric_alarm_with_empty_actions(),
                ],
                'CompositeAlarms': [
                    AlarmFixtures.create_composite_alarm_without_autoscaling_actions()
                ],
            }
        ]

    @staticmethod
    def create_single_page_response_mixed_alarms() -> List[Dict[str, Any]]:
        """Create single page response with mixed autoscaling and non-autoscaling alarms."""
        return [
            {
                'MetricAlarms': [
                    AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions(),
                    AlarmFixtures.create_metric_alarm_without_autoscaling_actions(),
                    AlarmFixtures.create_metric_alarm_with_mixed_actions(),
                ],
                'CompositeAlarms': [
                    AlarmFixtures.create_composite_alarm_with_autoscaling_actions(),
                    AlarmFixtures.create_composite_alarm_without_autoscaling_actions(),
                ],
            }
        ]

    @staticmethod
    def create_multi_page_response_for_filtering() -> List[Dict[str, Any]]:
        """Create multi-page response designed for testing pagination with filtering."""
        return [
            # Page 1: Mostly autoscaling alarms
            {
                'MetricAlarms': [
                    AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions(),
                    AlarmFixtures.create_metric_alarm_with_autoscaling_ok_actions(),
                    AlarmFixtures.create_metric_alarm_without_autoscaling_actions(),  # 1 non-autoscaling
                ],
                'CompositeAlarms': [
                    AlarmFixtures.create_composite_alarm_with_autoscaling_actions()
                ],
            },
            # Page 2: Mix of alarm types
            {
                'MetricAlarms': [
                    AlarmFixtures.create_metric_alarm_with_mixed_actions(),  # Autoscaling (mixed)
                    AlarmFixtures.create_metric_alarm_with_empty_actions(),  # Non-autoscaling
                ],
                'CompositeAlarms': [
                    AlarmFixtures.create_composite_alarm_without_autoscaling_actions()  # Non-autoscaling
                ],
            },
            # Page 3: More non-autoscaling alarms
            {
                'MetricAlarms': [
                    {
                        **AlarmFixtures.create_metric_alarm_without_autoscaling_actions(),
                        'AlarmName': 'additional-app-alarm-1',
                    },
                    {
                        **AlarmFixtures.create_metric_alarm_without_autoscaling_actions(),
                        'AlarmName': 'additional-app-alarm-2',
                    },
                ],
                'CompositeAlarms': [],
            },
        ]

    @staticmethod
    def create_large_dataset_response(
        num_autoscaling: int = 50, num_non_autoscaling: int = 10
    ) -> List[Dict[str, Any]]:
        """Create large dataset response for performance testing."""
        pages = []
        alarms_per_page = 10

        # Create autoscaling alarms
        autoscaling_alarms = []
        for i in range(num_autoscaling):
            alarm = AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions()
            alarm['AlarmName'] = f'autoscaling-alarm-{i:03d}'
            alarm['Dimensions'] = [{'Name': 'AutoScalingGroupName', 'Value': f'asg-{i:03d}'}]
            autoscaling_alarms.append(alarm)

        # Create non-autoscaling alarms
        non_autoscaling_alarms = []
        for i in range(num_non_autoscaling):
            alarm = AlarmFixtures.create_metric_alarm_without_autoscaling_actions()
            alarm['AlarmName'] = f'application-alarm-{i:03d}'
            alarm['Dimensions'] = [{'Name': 'InstanceId', 'Value': f'i-{i:016x}'}]
            non_autoscaling_alarms.append(alarm)

        # Combine and distribute across pages
        all_alarms = autoscaling_alarms + non_autoscaling_alarms
        for i in range(0, len(all_alarms), alarms_per_page):
            page_alarms = all_alarms[i : i + alarms_per_page]
            pages.append({'MetricAlarms': page_alarms, 'CompositeAlarms': []})

        return pages

    @staticmethod
    def create_empty_response() -> List[Dict[str, Any]]:
        """Create empty response for testing no alarms scenario."""
        return [{'MetricAlarms': [], 'CompositeAlarms': []}]


class EdgeCaseFixtures:
    """Factory class for creating edge case test fixtures."""

    @staticmethod
    def create_alarm_with_malformed_actions() -> Dict[str, Any]:
        """Create alarm with malformed action ARNs for error handling tests."""
        return {
            'AlarmName': 'malformed-actions-alarm',
            'AlarmDescription': 'Alarm with malformed action ARNs',
            'StateValue': 'ALARM',
            'StateReason': 'Test alarm with malformed actions',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-malformed123456'}],
            'Period': 300,
            'EvaluationPeriods': 1,
            'Threshold': 80.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'AlarmActions': [
                None,  # None value
                123,  # Integer value
                '',  # Empty string
                'not-an-arn',  # Malformed ARN
                AUTOSCALING_SCALE_UP_ARN,  # Valid autoscaling ARN
                {'invalid': 'dict'},  # Dictionary value
                'arn:aws:sns:us-east-1:123456789012:valid-topic',  # Valid non-autoscaling ARN
            ],
            'OKActions': [],
            'InsufficientDataActions': [],
        }

    @staticmethod
    def create_alarm_with_autoscaling_like_arns() -> Dict[str, Any]:
        """Create alarm with ARNs that contain 'autoscaling' but are not autoscaling service ARNs."""
        return {
            'AlarmName': 'autoscaling-like-arns-alarm',
            'AlarmDescription': 'Alarm with ARNs containing autoscaling in name but not autoscaling service',
            'StateValue': 'ALARM',
            'StateReason': 'Test alarm with autoscaling-like ARNs',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-autoscalinglike123'}],
            'Period': 300,
            'EvaluationPeriods': 1,
            'Threshold': 80.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'AlarmActions': [
                'arn:aws:sns:us-east-1:123456789012:autoscaling-alerts',  # SNS with autoscaling in name
                'arn:aws:lambda:us-east-1:123456789012:function:autoscaling-handler',  # Lambda with autoscaling in name
                'arn:aws:autoscaling-plans:us-east-1:123456789012:scaling-plan:plan-id',  # Similar but different service
            ],
            'OKActions': [
                'arn:aws:sqs:us-east-1:123456789012:autoscaling-queue'  # SQS with autoscaling in name
            ],
            'InsufficientDataActions': [
                'arn:aws:cloudwatch:us-east-1:123456789012:alarm:autoscaling-cpu-high'  # CloudWatch alarm with autoscaling in name
            ],
        }

    @staticmethod
    def create_realistic_target_tracking_alarm() -> Dict[str, Any]:
        """Create realistic target tracking alarm as created by AWS Auto Scaling."""
        return {
            'AlarmName': 'TargetTracking-my-web-asg-AlarmHigh-12345678-1234-1234-1234-123456789012',
            'AlarmDescription': 'DO NOT EDIT OR DELETE. For TargetTrackingScaling policy arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:12345678-1234-1234-1234-123456789012:autoScalingGroupName/my-web-asg:policyName/my-target-tracking-policy.',
            'ActionsEnabled': True,
            'OKActions': [],
            'AlarmActions': [
                'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:12345678-1234-1234-1234-123456789012:autoScalingGroupName/my-web-asg:policyName/my-target-tracking-policy'
            ],
            'InsufficientDataActions': [],
            'StateValue': 'OK',
            'StateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [45.0 (01/01/24 12:00:00)] was not greater than the threshold (70.0) (minimum 1 datapoint for OK -> ALARM transition).',
            'StateReasonData': '{"version":"1.0","queryDate":"2024-01-01T12:01:00.000+0000","statistic":"Average","period":300,"recentDatapoints":[45.0],"threshold":70.0}',
            'StateUpdatedTimestamp': datetime(2024, 1, 1, 12, 1, 0),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Statistic': 'Average',
            'Dimensions': [{'Name': 'AutoScalingGroupName', 'Value': 'my-web-asg'}],
            'Period': 300,
            'EvaluationPeriods': 1,
            'DatapointsToAlarm': 1,
            'Threshold': 70.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            'EvaluateLowSampleCountPercentile': '',
            'AlarmArn': 'arn:aws:cloudwatch:us-east-1:123456789012:alarm:TargetTracking-my-web-asg-AlarmHigh-12345678-1234-1234-1234-123456789012',
            'AlarmConfigurationUpdatedTimestamp': datetime(2024, 1, 1, 10, 0, 0),
        }


# Pytest fixtures for easy use in test files
@pytest.fixture
def autoscaling_metric_alarm():
    """Fixture for metric alarm with autoscaling actions."""
    return AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions()


@pytest.fixture
def non_autoscaling_metric_alarm():
    """Fixture for metric alarm without autoscaling actions."""
    return AlarmFixtures.create_metric_alarm_without_autoscaling_actions()


@pytest.fixture
def mixed_actions_metric_alarm():
    """Fixture for metric alarm with mixed action types."""
    return AlarmFixtures.create_metric_alarm_with_mixed_actions()


@pytest.fixture
def autoscaling_composite_alarm():
    """Fixture for composite alarm with autoscaling actions."""
    return AlarmFixtures.create_composite_alarm_with_autoscaling_actions()


@pytest.fixture
def non_autoscaling_composite_alarm():
    """Fixture for composite alarm without autoscaling actions."""
    return AlarmFixtures.create_composite_alarm_without_autoscaling_actions()


@pytest.fixture
def empty_actions_alarm():
    """Fixture for alarm with empty action fields."""
    return AlarmFixtures.create_metric_alarm_with_empty_actions()


@pytest.fixture
def missing_actions_alarm():
    """Fixture for alarm with missing action fields."""
    return AlarmFixtures.create_metric_alarm_with_missing_action_fields()


@pytest.fixture
def malformed_actions_alarm():
    """Fixture for alarm with malformed action ARNs."""
    return EdgeCaseFixtures.create_alarm_with_malformed_actions()


@pytest.fixture
def autoscaling_like_arns_alarm():
    """Fixture for alarm with autoscaling-like but non-autoscaling ARNs."""
    return EdgeCaseFixtures.create_alarm_with_autoscaling_like_arns()


@pytest.fixture
def realistic_target_tracking_alarm():
    """Fixture for realistic target tracking alarm."""
    return EdgeCaseFixtures.create_realistic_target_tracking_alarm()


@pytest.fixture
def single_page_mixed_response():
    """Fixture for single page response with mixed alarm types."""
    return PaginationFixtures.create_single_page_response_mixed_alarms()


@pytest.fixture
def multi_page_filtering_response():
    """Fixture for multi-page response designed for filtering tests."""
    return PaginationFixtures.create_multi_page_response_for_filtering()


@pytest.fixture
def large_dataset_response():
    """Fixture for large dataset response for performance testing."""
    return PaginationFixtures.create_large_dataset_response()


@pytest.fixture
def empty_response():
    """Fixture for empty response."""
    return PaginationFixtures.create_empty_response()
