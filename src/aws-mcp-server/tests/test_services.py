import awscli.clidriver
import pytest
from awslabs.aws_mcp_server.core.aws.services import (
    GET_METRIC_DATA_MAX_RESULTS_OVERRIDE,
    driver,
    extract_pagination_config,
    update_parameters_with_max_results,
)


MAX_RESULTS = 6


@pytest.mark.parametrize(
    'service_name,operation_name,max_results_key,max_results_type',
    [
        ('lambda', 'ListFunctions', 'MaxItems', int),
        ('route53', 'ListHostedZones', 'MaxItems', str),
    ],
)
def test_max_results_type(service_name, operation_name, max_results_key, max_results_type):
    """Test that max results type is set correctly for each service and operation."""
    parameters = {
        'PaginationConfig': {'MaxItems': MAX_RESULTS},
        'Foo': 'Bar',
    }
    updated_parameters, pagination_config = extract_pagination_config(
        parameters, service_name, operation_name, MAX_RESULTS
    )
    max_results = pagination_config.get('MaxItems')
    updated_parameters = update_parameters_with_max_results(
        updated_parameters,
        service_name,
        operation_name,
        max_results,
    )
    assert updated_parameters.get('Foo') == 'Bar'  # Other parameters are unchanged
    assert isinstance(
        updated_parameters.get(max_results_key), max_results_type
    )  # MaxResults are rewritten


@pytest.mark.parametrize(
    'max_result_config, max_result_param, expected_max_result',
    [
        (None, None, None),  # max result is not defined
        (10, None, 10),  # max result is defined in config but not as param
        (None, 6, 6),  # max result is defined as parameter and not in config
        (6, 10, 6),  # max result is defined in both places. In this case we take config param
    ],
)
def test_max_results(max_result_config, max_result_param, expected_max_result):
    """Test that max results are set correctly based on config and parameters."""
    parameters = {
        'PaginationConfig': {'MaxItems': max_result_config},
        'Foo': 'Bar',
    }
    service_name = 'lambda'
    operation_name = 'ListFunctions'
    updated_parameters, pagination_config = extract_pagination_config(
        parameters, service_name, operation_name, max_result_param
    )
    max_results = pagination_config.get('MaxItems')
    updated_parameters = update_parameters_with_max_results(
        updated_parameters,
        service_name,
        operation_name,
        max_results,
    )
    assert updated_parameters.get('MaxItems') == expected_max_result


@pytest.mark.parametrize(
    'service_name, operation_name, limit_key, max_result_param, expected_max_result',
    [
        ('athena', 'ListTagsForResource', 'MaxResults', 6, 75),  # min: 75, max: None
        ('ec2', 'ListSnapshotsInRecycleBin', 'MaxResults', 4, 5),  # min: 5, max: 1000
        (
            'ec2',
            'ListSnapshotsInRecycleBin',
            'MaxResults',
            1500,
            1000,
        ),  # min: 5, max: 1000
        ('sagemaker', 'ListDevices', 'MaxResults', 120, 100),  # min: None, max: 100
        ('ecs', 'ListClusters', 'maxResults', 25, 25),  # min: None, max: None
        ('rds', 'DescribeDBInstances', 'MaxRecords', 10, 20),  # Override, min: 20, max: 100
        ('rds', 'DescribeDBClusters', 'MaxRecords', 110, 100),  # Override, min: 20, max: 100
    ],
)
def test_max_results_outside_of_model_bounds(
    service_name, operation_name, limit_key, max_result_param, expected_max_result
):
    """Test that max results are capped within model bounds for each operation."""
    parameters = {'Foo': 'Bar'}
    updated_parameters, pagination_config = extract_pagination_config(
        parameters, service_name, operation_name, max_result_param
    )
    max_results = pagination_config.get('MaxItems')
    updated_parameters = update_parameters_with_max_results(
        updated_parameters,
        service_name,
        operation_name,
        max_results,
    )
    assert updated_parameters.get(limit_key) == expected_max_result


@pytest.mark.parametrize(
    'max_results, expected_max_datapoints',
    [
        (10, 10),
        (4500, GET_METRIC_DATA_MAX_RESULTS_OVERRIDE),
        (3900, GET_METRIC_DATA_MAX_RESULTS_OVERRIDE),
    ],
)
def test_update_operation_max_results_key_for_get_metric_data(
    max_results, expected_max_datapoints
):
    """Test that GetMetricData max results are overridden as expected."""
    service_name = 'cloudwatch'
    operation_name = 'GetMetricData'
    updated_parameters, pagination_config = extract_pagination_config(
        {}, service_name, operation_name, max_results
    )
    max_results = pagination_config.get('MaxItems')
    updated_parameters = update_parameters_with_max_results(
        updated_parameters,
        service_name,
        operation_name,
        max_results,
    )

    assert updated_parameters.get('MaxDatapoints') == expected_max_datapoints


def test_update_operation_max_results_key_does_not_raise_exceptions():
    """Test that update_operation_max_results_key does not raise exceptions for any service/operation."""
    command_table = driver._get_command_table()
    # Testing update_operation_max_results_key against all services and operations
    for service_name, command in command_table.items():
        if not isinstance(command, awscli.clidriver.ServiceCommand):
            continue
        service_command_table = command._get_command_table()
        for operation_name, operation in service_command_table.items():
            if hasattr(operation, '_operation_model'):
                camel_case_name = operation._operation_model.name
            else:
                # Operations without model include operations like `ec2 wait`, `emr ssh`,
                # `cloudtrail validate-logs` which should not reach update_operation_max_results_key
                # but testing them just in case
                # convert kebab-case to CamelCase
                camel_case_name = ''.join(word.capitalize() for word in operation_name.split('-'))
            extract_pagination_config({}, service_name, camel_case_name, max_results=25)
