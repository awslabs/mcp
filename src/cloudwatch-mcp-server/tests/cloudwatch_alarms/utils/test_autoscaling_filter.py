"""Unit tests for AutoscalingActionFilter utility class.

This module contains comprehensive tests for the AutoscalingActionFilter class,
covering all scenarios for detecting autoscaling actions in CloudWatch alarms.
Tests cover various action field combinations, edge cases, and error conditions.
"""

from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.utils.autoscaling_filter import (
    AutoscalingActionFilter,
)
from tests.cloudwatch_alarms.fixtures import (
    AUTOSCALING_SCALE_DOWN_ARN,
    AUTOSCALING_SCALE_UP_ARN,
    LAMBDA_HANDLER_ARN,
    SNS_ALERT_ARN,
    SQS_QUEUE_ARN,
    AlarmFixtures,
    EdgeCaseFixtures,
)


class TestAutoscalingActionFilter:
    """Test class for AutoscalingActionFilter functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.filter = AutoscalingActionFilter()

        # Use shared fixture ARNs for consistency
        self.autoscaling_arn_1 = AUTOSCALING_SCALE_UP_ARN
        self.autoscaling_arn_2 = AUTOSCALING_SCALE_DOWN_ARN
        self.sns_arn = SNS_ALERT_ARN
        self.lambda_arn = LAMBDA_HANDLER_ARN
        self.sqs_arn = SQS_QUEUE_ARN

    def test_alarm_with_autoscaling_alarm_actions(self):
        """Test detection of autoscaling actions in AlarmActions field."""
        alarm_data = {
            'AlarmName': 'test-autoscaling-alarm-actions',
            'AlarmActions': [self.autoscaling_arn_1],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, 'Should detect autoscaling action in AlarmActions field'

    def test_alarm_with_autoscaling_ok_actions(self):
        """Test detection of autoscaling actions in OKActions field."""
        alarm_data = {
            'AlarmName': 'test-autoscaling-ok-actions',
            'OKActions': [self.autoscaling_arn_1],
            'StateValue': 'OK',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, 'Should detect autoscaling action in OKActions field'

    def test_alarm_with_autoscaling_insufficient_data_actions(self):
        """Test detection of autoscaling actions in InsufficientDataActions field."""
        alarm_data = {
            'AlarmName': 'test-autoscaling-insufficient-data-actions',
            'InsufficientDataActions': [self.autoscaling_arn_1],
            'StateValue': 'INSUFFICIENT_DATA',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, 'Should detect autoscaling action in InsufficientDataActions field'

    def test_alarm_with_autoscaling_actions_in_multiple_fields(self):
        """Test detection of autoscaling actions across multiple action fields."""
        alarm_data = {
            'AlarmName': 'test-autoscaling-multiple-fields',
            'AlarmActions': [self.autoscaling_arn_1],
            'OKActions': [self.autoscaling_arn_2],
            'InsufficientDataActions': [self.autoscaling_arn_1],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, 'Should detect autoscaling actions in multiple fields'

    def test_alarm_with_mixed_autoscaling_and_non_autoscaling_actions(self):
        """Test detection when alarm has both autoscaling and non-autoscaling actions."""
        alarm_data = {
            'AlarmName': 'test-mixed-actions',
            'AlarmActions': [self.autoscaling_arn_1, self.sns_arn, self.lambda_arn],
            'OKActions': [self.sqs_arn],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, (
            'Should identify as autoscaling alarm when mixed actions include autoscaling'
        )

    def test_alarm_with_no_autoscaling_actions(self):
        """Test that alarms with only non-autoscaling actions are not detected."""
        alarm_data = {
            'AlarmName': 'test-no-autoscaling-actions',
            'AlarmActions': [self.sns_arn, self.lambda_arn],
            'OKActions': [self.sqs_arn],
            'InsufficientDataActions': [self.sns_arn],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is False, (
            'Should identify as non-autoscaling alarm when no autoscaling actions present'
        )

    def test_alarm_with_empty_action_fields(self):
        """Test handling of alarms with empty action fields."""
        alarm_data = {
            'AlarmName': 'test-empty-actions',
            'AlarmActions': [],
            'OKActions': [],
            'InsufficientDataActions': [],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is False, (
            'Should identify as non-autoscaling alarm when all action fields are empty'
        )

    def test_alarm_with_missing_action_fields(self):
        """Test handling of alarms with missing action fields."""
        alarm_data = {'AlarmName': 'test-missing-actions', 'StateValue': 'ALARM'}

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is False, (
            'Should identify as non-autoscaling alarm when action fields are missing'
        )

    def test_alarm_with_some_missing_action_fields(self):
        """Test handling of alarms with partially missing action fields."""
        alarm_data = {
            'AlarmName': 'test-partial-missing-actions',
            'AlarmActions': [self.autoscaling_arn_1],
            # OKActions field is missing
            'InsufficientDataActions': [self.sns_arn],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, (
            'Should detect autoscaling actions even when some fields are missing'
        )

    def test_handling_of_malformed_action_arns(self):
        """Test graceful handling of malformed action ARNs."""
        # Use fixture for malformed actions alarm
        alarm_data = EdgeCaseFixtures.create_alarm_with_malformed_actions()

        # Should not raise an exception and should detect the valid autoscaling ARN
        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, (
            'Should handle malformed ARNs gracefully and detect valid autoscaling ARN'
        )

    def test_handling_of_all_malformed_action_arns(self):
        """Test handling when all action ARNs are malformed."""
        alarm_data = {
            'AlarmName': 'test-all-malformed-arns',
            'AlarmActions': [None, 123, '', 'not-an-arn', {'invalid': 'dict'}],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is False, 'Should return False when all ARNs are malformed'

    def test_autoscaling_arn_prefix_variations(self):
        """Test detection of various valid autoscaling ARN formats."""
        test_cases = [
            # Standard scaling policy ARN
            'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:policy-id:autoScalingGroupName/asg-name:policyName/policy-name',
            # Minimal autoscaling ARN
            'arn:aws:autoscaling:region:account:resource',
            # Different region
            'arn:aws:autoscaling:eu-west-1:123456789012:scalingPolicy:policy-id',
            # Different account
            'arn:aws:autoscaling:us-east-1:999999999999:scalingPolicy:policy-id',
        ]

        for arn in test_cases:
            alarm_data = {
                'AlarmName': f'test-arn-variation-{hash(arn)}',
                'AlarmActions': [arn],
                'StateValue': 'ALARM',
            }

            result = self.filter.has_autoscaling_actions(alarm_data)
            assert result is True, f'Should detect autoscaling action for ARN: {arn}'

    def test_non_autoscaling_arn_variations(self):
        """Test that non-autoscaling ARNs with 'autoscaling' in names are not detected."""
        test_cases = [
            # SNS topic with 'autoscaling' in name
            'arn:aws:sns:us-east-1:123456789012:autoscaling-alerts',
            # Lambda function with 'autoscaling' in name
            'arn:aws:lambda:us-east-1:123456789012:function:autoscaling-handler',
            # SQS queue with 'autoscaling' in name
            'arn:aws:sqs:us-east-1:123456789012:autoscaling-queue',
            # CloudWatch alarm with 'autoscaling' in name
            'arn:aws:cloudwatch:us-east-1:123456789012:alarm:autoscaling-cpu-high',
            # ARN that starts similarly but is not autoscaling
            'arn:aws:autoscaling-plans:us-east-1:123456789012:scaling-plan:plan-id',
        ]

        for arn in test_cases:
            alarm_data = {
                'AlarmName': f'test-non-autoscaling-{hash(arn)}',
                'AlarmActions': [arn],
                'StateValue': 'ALARM',
            }

            result = self.filter.has_autoscaling_actions(alarm_data)
            assert result is False, f'Should not detect as autoscaling action for ARN: {arn}'

    def test_autoscaling_like_arns_comprehensive(self):
        """Test comprehensive autoscaling-like ARNs using fixture."""
        # Use fixture for autoscaling-like ARNs
        alarm_data = EdgeCaseFixtures.create_alarm_with_autoscaling_like_arns()

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is False, (
            "Should not detect autoscaling actions in ARNs that only contain 'autoscaling' in names"
        )

    def test_case_sensitivity_of_autoscaling_prefix(self):
        """Test that autoscaling prefix matching is case-sensitive."""
        test_cases = [
            'ARN:AWS:AUTOSCALING:us-east-1:123456789012:scalingPolicy:policy-id',  # Uppercase
            'arn:aws:AutoScaling:us-east-1:123456789012:scalingPolicy:policy-id',  # Mixed case
            'arn:aws:AUTOSCALING:us-east-1:123456789012:scalingPolicy:policy-id',  # Uppercase service
        ]

        for arn in test_cases:
            alarm_data = {
                'AlarmName': f'test-case-sensitivity-{hash(arn)}',
                'AlarmActions': [arn],
                'StateValue': 'ALARM',
            }

            result = self.filter.has_autoscaling_actions(alarm_data)
            assert result is False, f'Should not detect case-insensitive match for ARN: {arn}'

    def test_multiple_autoscaling_actions_in_same_field(self):
        """Test detection when multiple autoscaling actions exist in same field."""
        alarm_data = {
            'AlarmName': 'test-multiple-autoscaling-same-field',
            'AlarmActions': [
                self.autoscaling_arn_1,
                self.autoscaling_arn_2,
                self.sns_arn,  # Mixed with non-autoscaling
            ],
            'StateValue': 'ALARM',
        }

        result = self.filter.has_autoscaling_actions(alarm_data)
        assert result is True, (
            'Should detect autoscaling actions when multiple exist in same field'
        )

    def test_check_action_list_method_directly(self):
        """Test the _check_action_list helper method directly."""
        # Test with autoscaling actions
        autoscaling_actions = [self.autoscaling_arn_1, self.sns_arn]
        result = self.filter._check_action_list(autoscaling_actions)
        assert result is True, 'Should detect autoscaling action in mixed list'

        # Test with no autoscaling actions
        non_autoscaling_actions = [self.sns_arn, self.lambda_arn, self.sqs_arn]
        result = self.filter._check_action_list(non_autoscaling_actions)
        assert result is False, 'Should not detect autoscaling actions in non-autoscaling list'

        # Test with empty list
        empty_actions = []
        result = self.filter._check_action_list(empty_actions)
        assert result is False, 'Should return False for empty action list'

        # Test with malformed actions
        malformed_actions = [None, 123, '', {'invalid': 'dict'}]
        result = self.filter._check_action_list(malformed_actions)
        assert result is False, 'Should return False for list with only malformed actions'

    def test_autoscaling_arn_prefix_constant(self):
        """Test that the autoscaling ARN prefix constant is correct."""
        expected_prefix = 'arn:aws:autoscaling:'
        assert self.filter.AUTOSCALING_ARN_PREFIX == expected_prefix, (
            f"AUTOSCALING_ARN_PREFIX should be '{expected_prefix}'"
        )

    def test_filter_instance_reusability(self):
        """Test that filter instances can be reused across multiple calls."""
        # First call
        alarm_data_1 = {
            'AlarmName': 'test-reusability-1',
            'AlarmActions': [self.autoscaling_arn_1],
            'StateValue': 'ALARM',
        }
        result_1 = self.filter.has_autoscaling_actions(alarm_data_1)

        # Second call with different data
        alarm_data_2 = {
            'AlarmName': 'test-reusability-2',
            'AlarmActions': [self.sns_arn],
            'StateValue': 'ALARM',
        }
        result_2 = self.filter.has_autoscaling_actions(alarm_data_2)

        # Third call back to autoscaling
        alarm_data_3 = {
            'AlarmName': 'test-reusability-3',
            'OKActions': [self.autoscaling_arn_2],
            'StateValue': 'OK',
        }
        result_3 = self.filter.has_autoscaling_actions(alarm_data_3)

        assert result_1 is True, 'First call should detect autoscaling action'
        assert result_2 is False, 'Second call should not detect autoscaling action'
        assert result_3 is True, 'Third call should detect autoscaling action'


# Additional test fixtures and utilities for integration testing
class TestAutoscalingActionFilterIntegration:
    """Integration tests for AutoscalingActionFilter with realistic data."""

    def setup_method(self):
        """Set up test fixtures for integration tests."""
        self.filter = AutoscalingActionFilter()

    def test_realistic_metric_alarm_with_autoscaling(self):
        """Test filtering with realistic autoscaling alarm data."""
        # Use fixture for realistic target tracking alarm
        realistic_alarm = EdgeCaseFixtures.create_realistic_target_tracking_alarm()

        result = self.filter.has_autoscaling_actions(realistic_alarm)
        assert result is True, 'Should detect autoscaling action in realistic metric alarm'

    def test_realistic_composite_alarm_without_autoscaling(self):
        """Test filtering with realistic composite alarm without autoscaling actions."""
        # Use fixture for realistic composite alarm without autoscaling
        realistic_composite_alarm = (
            AlarmFixtures.create_composite_alarm_without_autoscaling_actions()
        )

        result = self.filter.has_autoscaling_actions(realistic_composite_alarm)
        assert result is False, (
            'Should not detect autoscaling actions in realistic composite alarm'
        )
