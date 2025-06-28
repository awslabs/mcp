import pytest
from .fixtures import (
    CW_DESCRIBE_ALARMS,
    EC2_DESCRIBE_INSTANCES,
    EMPTY_EC2_DESCRIBE_INSTANCES,
    IAD_BUCKET,
    LIST_BUCKETS_PAYLOAD,
    PDX_BUCKET,
    T2_EC2_DESCRIBE_INSTANCES,
)
from awslabs.aws_mcp_server.core.aws.client_side_filtering import handle_client_side_query
from copy import deepcopy


@pytest.mark.parametrize(
    'response,client_side_query,expected_response,service,operation',
    [
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Testing passing None as a query
            None,
            EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Testing passing non-existing service name
            "Reservations[].Instances[?InstanceType=='t2.micro']",
            EC2_DESCRIBE_INSTANCES,
            'incorrect-service',
            'DescribeInstances',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Testing passing non-existing operation name
            "Reservations[].Instances[?InstanceType=='t2.micro']",
            EC2_DESCRIBE_INSTANCES,
            'ec2',
            'incorrect-operation',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Testing syntactically incorrect JMESPath query
            'incorrect-query-expression',
            EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Testing "field equals value" filter
            "Reservations[].Instances[?InstanceType=='t2.micro']",
            T2_EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Testing correct filter with no matching items
            "Reservations[].Instances[?InstanceType=='c1']",
            EMPTY_EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Testing accessing nested fields inside the filter
            "Reservations[].Instances[?Monitoring.State=='enabled']",
            T2_EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
        (
            deepcopy(CW_DESCRIBE_ALARMS),
            # Testing starts_with
            "MetricAlarms[?starts_with(AlarmName, 'fake')]",
            CW_DESCRIBE_ALARMS,
            'cloudwatch',
            'DescribeAlarms',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Trying to change output schema
            "{Rs: Reservations[].{Is: Instances[?starts_with(InstanceType, 't2')]}}",
            T2_EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Trying to extract instance ids only
            'Reservations[].Instances[].InstanceId',
            EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
        (
            deepcopy(CW_DESCRIBE_ALARMS),
            # Trying to access non-existent key inside function
            "MetricAlarms[?contains(NonExistentKey, 'value')]",
            CW_DESCRIBE_ALARMS,
            'cloudwatch',
            'DescribeAlarms',
        ),
        (
            deepcopy(EC2_DESCRIBE_INSTANCES),
            # Trying to access incorrect path
            'Buckets[].Functions[]',
            EC2_DESCRIBE_INSTANCES,
            'ec2',
            'DescribeInstances',
        ),
    ],
)
def test_handle_client_side_query(
    response, client_side_query, expected_response, service, operation
):
    """Test handle_client_side_query for various scenarios and queries."""
    filtered_response = handle_client_side_query(response, client_side_query, service, operation)
    assert filtered_response == expected_response


def test_non_present_key():
    """Test that filtering on a non-present key returns an empty result."""
    raw_response = deepcopy(CW_DESCRIBE_ALARMS)
    expected_response = deepcopy(raw_response)
    expected_response['MetricAlarms'] = []
    query = "MetricAlarms[?FakeKey=='fake-value']"
    filtered_response = handle_client_side_query(
        raw_response, query, 'cloudwatch', 'DescribeAlarms'
    )
    assert filtered_response == expected_response


def test_or_condition():
    """Test that OR conditions in queries are handled correctly."""
    raw_response = deepcopy(LIST_BUCKETS_PAYLOAD)
    expected_response = deepcopy(raw_response)
    expected_response['Buckets'] = [IAD_BUCKET, PDX_BUCKET]
    query = "Buckets[?Name=='IAD' || Name=='PDX']"
    filtered_response = handle_client_side_query(raw_response, query, 's3', 'ListBuckets')
    assert filtered_response == expected_response


def test_contains():
    """Test that contains function in queries is handled correctly."""
    raw_response = deepcopy(LIST_BUCKETS_PAYLOAD)
    expected_response = deepcopy(raw_response)
    expected_response['Buckets'] = [IAD_BUCKET]
    query = "Buckets[?contains(Name, 'A')]"
    filtered_response = handle_client_side_query(raw_response, query, 's3', 'ListBuckets')
    assert filtered_response == expected_response


def test_wrong_target_type():
    """Test that filtering does nothing if the target type is wrong."""
    raw_response = deepcopy(LIST_BUCKETS_PAYLOAD)
    # Using wrong output schema - filtering should do nothing
    raw_response['Buckets'] = 'some_string'
    query = "Buckets[?Name=='any_name']"
    filtered_response = handle_client_side_query(raw_response, query, 's3', 'ListBuckets')
    assert filtered_response == raw_response
