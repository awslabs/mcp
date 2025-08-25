# CloudWatch Alarms Test Fixtures

This directory contains comprehensive test fixtures for testing CloudWatch alarms filtering functionality. The fixtures are designed to provide consistent, reusable test data for various testing scenarios.

## Overview

The `fixtures.py` module provides:

1. **Factory Classes**: Create test data programmatically
2. **Pytest Fixtures**: Ready-to-use fixtures for common test scenarios
3. **Constants**: Shared ARN constants for consistency across tests
4. **Edge Cases**: Special fixtures for error handling and edge case testing

## Factory Classes

### AlarmFixtures

Creates various types of alarm data:

- `create_metric_alarm_with_autoscaling_alarm_actions()` - Metric alarm with autoscaling actions in AlarmActions field
- `create_metric_alarm_with_autoscaling_ok_actions()` - Metric alarm with autoscaling actions in OKActions field
- `create_metric_alarm_with_autoscaling_insufficient_data_actions()` - Metric alarm with autoscaling actions in InsufficientDataActions field
- `create_metric_alarm_with_mixed_actions()` - Metric alarm with both autoscaling and non-autoscaling actions
- `create_metric_alarm_without_autoscaling_actions()` - Metric alarm with only non-autoscaling actions
- `create_metric_alarm_with_empty_actions()` - Metric alarm with empty action fields
- `create_metric_alarm_with_missing_action_fields()` - Metric alarm with missing action fields
- `create_composite_alarm_with_autoscaling_actions()` - Composite alarm with autoscaling actions
- `create_composite_alarm_without_autoscaling_actions()` - Composite alarm without autoscaling actions
- `create_composite_alarm_with_mixed_actions()` - Composite alarm with mixed action types

### PaginationFixtures

Creates paginated response data for testing pagination scenarios:

- `create_single_page_response_all_autoscaling()` - Single page with all autoscaling alarms
- `create_single_page_response_all_non_autoscaling()` - Single page with all non-autoscaling alarms
- `create_single_page_response_mixed_alarms()` - Single page with mixed alarm types
- `create_multi_page_response_for_filtering()` - Multi-page response designed for filtering tests
- `create_large_dataset_response(num_autoscaling, num_non_autoscaling)` - Large dataset for performance testing
- `create_empty_response()` - Empty response for no-alarms scenarios

### EdgeCaseFixtures

Creates edge case test data:

- `create_alarm_with_malformed_actions()` - Alarm with malformed action ARNs
- `create_alarm_with_autoscaling_like_arns()` - Alarm with ARNs containing 'autoscaling' but not autoscaling service ARNs
- `create_realistic_target_tracking_alarm()` - Realistic target tracking alarm as created by AWS Auto Scaling

## Pytest Fixtures

Ready-to-use fixtures that can be injected into test methods:

```python
def test_my_feature(autoscaling_metric_alarm, non_autoscaling_metric_alarm):
    # Use the fixtures directly
    assert autoscaling_metric_alarm['AlarmName'] == 'autoscaling-cpu-high-alarm'
    assert non_autoscaling_metric_alarm['AlarmName'] == 'application-cpu-high-alarm'
```

Available fixtures:
- `autoscaling_metric_alarm`
- `non_autoscaling_metric_alarm`
- `mixed_actions_metric_alarm`
- `autoscaling_composite_alarm`
- `non_autoscaling_composite_alarm`
- `empty_actions_alarm`
- `missing_actions_alarm`
- `malformed_actions_alarm`
- `autoscaling_like_arns_alarm`
- `realistic_target_tracking_alarm`
- `single_page_mixed_response`
- `multi_page_filtering_response`
- `large_dataset_response`
- `empty_response`

## Constants

Shared ARN constants for consistency:

- `AUTOSCALING_SCALE_UP_ARN` - Standard scale-up policy ARN
- `AUTOSCALING_SCALE_DOWN_ARN` - Standard scale-down policy ARN
- `AUTOSCALING_TARGET_TRACKING_ARN` - Target tracking policy ARN
- `SNS_ALERT_ARN` - SNS topic ARN for alerts
- `SNS_CRITICAL_ARN` - SNS topic ARN for critical alerts
- `LAMBDA_HANDLER_ARN` - Lambda function ARN
- `SQS_QUEUE_ARN` - SQS queue ARN

## Usage Examples

### Using Factory Methods

```python
from tests.cloudwatch_alarms.fixtures import AlarmFixtures

def test_autoscaling_detection():
    alarm = AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions()
    # Test your filtering logic with the alarm data
```

### Using Pytest Fixtures

```python
def test_filtering_behavior(autoscaling_metric_alarm, non_autoscaling_metric_alarm):
    # Fixtures are automatically injected
    mock_response = [
        {
            'MetricAlarms': [autoscaling_metric_alarm, non_autoscaling_metric_alarm],
            'CompositeAlarms': []
        }
    ]
    # Test your filtering logic
```

### Using Pagination Fixtures

```python
def test_pagination_with_filtering(multi_page_filtering_response):
    # Use the multi-page response for pagination testing
    mock_paginator.paginate.return_value = multi_page_filtering_response
    # Test your pagination logic
```

### Creating Custom Test Data

```python
from tests.cloudwatch_alarms.fixtures import PaginationFixtures

def test_performance():
    # Create a large dataset for performance testing
    large_response = PaginationFixtures.create_large_dataset_response(
        num_autoscaling=100,
        num_non_autoscaling=20
    )
    # Test performance with large dataset
```

## Best Practices

1. **Use Fixtures for Common Scenarios**: Use the provided pytest fixtures for standard test cases
2. **Use Factory Methods for Custom Data**: Use factory methods when you need to customize the test data
3. **Reuse Constants**: Use the shared ARN constants to maintain consistency across tests
4. **Test Edge Cases**: Use EdgeCaseFixtures to test error handling and malformed data scenarios
5. **Performance Testing**: Use large dataset fixtures for performance and stress testing
