import botocore.client
import botocore.exceptions
import contextlib
import datetime
from .history_handler import history
from awscli.compat import BytesIO
from awslabs.aws_mcp_server.core.common.models import ActionType
from botocore.response import StreamingBody
from copy import deepcopy
from unittest.mock import MagicMock, patch


S3_CLI_NO_REGION = 'aws s3api list-buckets'

EC2_WAIT_COMMAND_CLI = 'aws ec2 wait volume-available --volume-ids vol-1234567890abcdef0'
EC2_WAIT_COMMAND_VALIDATION_FAILURES = {
    'classification': None,
    'failed_constraints': [],
    'validation_failures': [
        {
            'reason': "The operation 'wait' for service 'ec2' is currently unsupported.",
            'context': {
                'service': 'ec2',
                'operation': 'wait',
                'parameters': None,
                'args': None,
                'region': None,
                'operators': None,
            },
        }
    ],
    'missing_context_failures': None,
}

CLOUD9_PARAMS_CLI_MISSING_CONTEXT = (
    'aws cloud9 create-environment-ec2 --name test --instance-type t3.large'
)
CLOUD9_PARAMS_MISSING_CONTEXT_FAILURES = {
    'validation_failures': None,
    'classification': {
        'api_type': 'management',
        'action_types': [ActionType.UNKNOWN.value],
    },
    'failed_constraints': [],
    'missing_context_failures': [
        {
            'reason': "The following parameters are missing for service 'cloud9' and operation 'create-environment-ec2': '--image-id'",
            'context': {
                'service': 'cloud9',
                'operation': 'create-environment-ec2',
                'parameters': ['--image-id'],
                'args': None,
                'region': None,
                'operators': None,
            },
        }
    ],
}

CLOUD9_PARAMS_CLI_NON_EXISTING_OPERATION = 'aws cloud9 list-environments-1'
CLOUD9_PARAMS_CLI_VALIDATION_FAILURES = {
    'classification': None,
    'failed_constraints': [],
    'validation_failures': [
        {
            'reason': "The operation 'list-environments-1' for service 'cloud9' does not exist.",
            'context': {
                'service': 'cloud9',
                'operation': 'list-environments-1',
                'parameters': None,
                'args': None,
                'region': None,
                'operators': None,
            },
        }
    ],
    'missing_context_failures': None,
}


TEST_CREDENTIALS = {'access_key_id': 'test', 'secret_access_key': 'test', 'session_token': 'test'}


# Original botocore _make_api_call function
orig = botocore.client.BaseClient._make_api_call

CLOUD9_LIST_ENVIRONMENTS = {
    'environmentIds': [
        'dc7ec5068da34567b72376837becd583',  # pragma: allowlist secret
        'bfdc3c72123b4b918de2004b6d6e78ab',  # pragma: allowlist secret
    ],  # pragma: allowlist secret
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

T3_EC2_INSTANCE_RESERVATION = {
    'Groups': [],
    'Instances': [
        {
            'AmiLaunchIndex': 0,
            'ImageId': 'ami-0a5fbecff26409d48',
            'InstanceId': 'i-0487c758efa644ff4',
            'InstanceType': 't3.small',
            'LaunchTime': datetime.datetime.now(datetime.timezone.utc),
            'Monitoring': {'State': 'disabled'},
        }
    ],
}
T2_EC2_INSTANCE_RESERVATION = {
    'Groups': [],
    'Instances': [
        {
            'AmiLaunchIndex': 1,
            'ImageId': 'ami-0a5fbecff26409d48',
            'InstanceId': 'i-0487c758efa644ff4',
            'InstanceType': 't2.micro',
            'LaunchTime': datetime.datetime.now(datetime.timezone.utc),
            'Monitoring': {'State': 'enabled'},
        }
    ],
}

EMPTY_EC2_RESERVATION = {'Groups': [], 'Instances': []}

EMPTY_EC2_DESCRIBE_INSTANCES = {
    'Reservations': [
        EMPTY_EC2_RESERVATION,
        EMPTY_EC2_RESERVATION,
    ],
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

T2_EC2_DESCRIBE_INSTANCES = {
    'Reservations': [
        EMPTY_EC2_RESERVATION,
        T2_EC2_INSTANCE_RESERVATION,
    ],
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

EC2_DESCRIBE_INSTANCES = {
    'Reservations': [
        T3_EC2_INSTANCE_RESERVATION,
        T2_EC2_INSTANCE_RESERVATION,
    ],
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

CLOUDFORMATION_LIST_STACKS_FIRST_PAGE = {
    'StackSummaries': [
        {
            'StackId': 'arn:aws:cloudformation:region:account-id:stack/stack-name/stack-id',
            'StackName': 'stack-name',
            'StackStatus': 'CREATE_COMPLETE',
            'CreationTime': 'timestamp',
            'LastUpdatedTime': 'timestamp',
            'DeletionTime': 'timestamp',
        },
    ],
    'pagination_token': 'token',
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

CLOUDFORMATION_LIST_STACKS_SECOND_PAGE = {
    'StackSummaries': [
        {
            'StackId': 'arn:aws:cloudformation:region:account-id:stack/stack-name/stack-id',
            'StackName': 'stack-name',
            'StackStatus': 'CREATE_COMPLETE',
            'CreationTime': 'timestamp',
            'LastUpdatedTime': 'timestamp',
            'DeletionTime': 'timestamp',
        },
    ],
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

REDSHIFT_FIRST_PAGE = {
    'DefaultClusterParameters': {
        'Parameters': [
            {
                'ParameterName': 'enable_user_activity_logging',
            },
            {
                'ParameterName': 'query_group',
            },
        ]
    },
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'pagination_token': 'nexttoken',
}

REDSHIFT_SECOND_PAGE = {
    'DefaultClusterParameters': {
        'Parameters': [
            {
                'ParameterName': 'enable_user_activity_logging_2',
            },
            {
                'ParameterName': 'query_group_2',
            },
        ]
    },
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

CW_DESCRIBE_ALARMS = {
    'MetricAlarms': [{'AlarmName': 'fake-alarm'}],
    'CompositeAlarms': [],
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

CLOUD9_DESCRIBE_ENVIRONMENTS = {
    'environments': [
        {'id': '7d61007bd98b4d589f1504af84c168de'},  # pragma: allowlist secret
        {'id': 'b181ffd35fe2457c8c5ae9d75edc068a'},  # pragma: allowlist secret
    ],
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

GET_CALLER_IDENTITY_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

LIST_INVESTIGATIONS_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
}

IAD_BUCKET = {'Name': 'IAD', 'CreationDate': '2022-07-13T15:20:58+00:00'}
DUB_BUCKET = {'Name': 'DUB', 'CreationDate': '2022-07-13T15:20:58+00:00'}
PDX_BUCKET = {'Name': 'PDX', 'CreationDate': '2022-07-13T15:20:58+00:00'}

BucketsPerRegion = {
    'us-east-1': IAD_BUCKET,
    None: IAD_BUCKET,
    'us-west-2': PDX_BUCKET,
    'eu-west-1': DUB_BUCKET,
    'Global': [IAD_BUCKET, DUB_BUCKET, PDX_BUCKET],
}


LIST_BUCKETS_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'Buckets': [
        IAD_BUCKET,
        DUB_BUCKET,
        PDX_BUCKET,
    ],
    'Owner': {'DisplayName': 'clpo', 'ID': '***'},
}

LIST_OBJECTS_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'IsTruncated': False,
    'Marker': '',
    'Contents': [
        {
            'Key': 'example-file-1.txt',
            'LastModified': '2025-01-08T15:30:15.000Z',
            'ETag': '"d41d8cd98f00b204e9800998ecf8427e"',  # pragma: allowlist secret
            'Size': 1024,
            'StorageClass': 'STANDARD',
            'Owner': {'DisplayName': 'example-owner', 'ID': 'exampleownerid12345678'},
        },
        {
            'Key': 'example-folder/example-file-2.jpg',
            'LastModified': '2025-01-09T10:15:30.000Z',
            'ETag': '"6d0bb00954ceb7fbee436bb55a8397ab"',  # pragma: allowlist secret
            'Size': 2048576,
            'StorageClass': 'STANDARD',
            'Owner': {'DisplayName': 'example-owner', 'ID': 'exampleownerid12345678'},
        },
    ],
    'Name': 'example-bucket',
    'Prefix': '',
    'MaxKeys': 1000,
    'EncodingType': 'url',
}

GET_METRIC_DATA_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'Messages': [],
    'MetricDataResults': [
        {
            'Id': 'm1',
            'Label': 'Unhealthy Behind Load Balancer',
            'StatusCode': 'Complete',
            'Timestamps': [1637074200, 1637073900, 1637073600],
            'Values': [0, 0, 0],
        },
        {
            'Id': 'q1',
            'Label': 'Cluster CpuUtilization',
            'StatusCode': 'Complete',
            'Timestamps': [1637074245, 1637073945, 1637073645],
            'Values': [1.2158469945359334, 0.8678863271635757, 0.7201860957623283],
        },
    ],
}

GET_METRIC_STATISTICS_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'Label': 'CPUUtilization',
    'Datapoints': [
        {
            'Timestamp': '2025-02-20T10:00:00Z',
            'Average': 45.6,
            'Unit': 'Percent',
            'SampleCount': 5.0,
            'Maximum': 51.2,
            'Minimum': 41.3,
            'Sum': 228.0,
        },
        {
            'Timestamp': '2025-02-20T10:05:00Z',
            'Average': 47.2,
            'Unit': 'Percent',
            'SampleCount': 5.0,
            'Maximum': 53.1,
            'Minimum': 42.8,
            'Sum': 236.0,
        },
    ],
}

GET_BATCH_TRACES_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'NextToken': 'NEXT_TOKEN_STRING',
    'Traces': [
        {
            'Duration': 0.532,
            'Id': '1-5e3d83d7-826f745d84226d5e7f689f72',
            'LimitExceeded': False,
            'Segments': [
                {'Document': 'doc1', 'Id': '3b58ef65f8a799a9'},  # pragma: allowlist secret
                {'Document': 'doc2', 'Id': '1c2e5d67f9b8a0b1'},  # pragma: allowlist secret
            ],
        },
        {
            'Duration': 0.328,
            'Id': '1-5e3d83d8-a9b8c7d6e5f4a3b2c1d0e9f8',
            'LimitExceeded': False,
            'Segments': [{'Document': 'doc3', 'Id': '4a3b2c1d0e9f8g7h'}],
        },
    ],
    'UnprocessedTraceIds': ['1-5e3d83d9-f1e2d3c4b5a6978685746352'],
}


LAMBDA_INVOKE_FUNCTION_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'StatusCode': 200,
    'ExecutedVersion': '$LATEST',
    'Payload': '"Hello from Lambda!"',
}

DYNAMODB_GET_ITEM_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'Item': {
        'id': {'S': 'foo'},
        'name': {'S': 'John Doe'},
    },
}

DYNAMODB_SCAN_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'Items': ['foo', 'bar'],
    'Count': 2,
    'ScannedCount': 2,
    'LastEvaluatedKey': {'id': {'S': '2'}},
}

DESCRIBE_ALARMS_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 403},
    'Error': {'Code': 'AccessDenied'},
}


LIST_MANAGED_INSIGHT_RULES_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'ManagedRules': [],
}

SSM_LIST_NODES_PAYLOAD = {
    'Nodes': [
        {
            'CaptureTime': '1970-01-01T00:00:00',
            'Id': 'abc',
            'NodeType': {
                'Instance': {
                    'AgentType': 'AgentType',
                    'AgentVersion': 'AgentVersion',
                    'ComputerName': 'ComputerName',
                    'InstanceStatus': 'InstanceStatus',
                    'IpAddress': 'IpAddress',
                    'ManagedStatus': 'ManagedStatus',
                    'PlatformType': 'PlatformType',
                    'PlatformName': 'PlatformName',
                    'PlatformVersion': 'PlatformVersion',
                    'ResourceType': 'ResourceType',
                }
            },
        }
    ],
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'estimated_resources_processed': 20,
}

S3_GET_OBJECT_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'Body': StreamingBody(raw_stream=BytesIO(b'this is a stream'), content_length=16),
}

CLOUDFRONT_FUNCTIONS = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'FunctionList': {
        'Items': [
            {
                'Name': 'my-function-1',
            },
            {
                'Name': 'my-function-2',
            },
        ],
        'MaxItems': 10,
    },
}


def _get_bucket_location_mock(kwarg):
    metadata = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    requested = kwarg.get('Bucket')
    for region, bucket in BucketsPerRegion.items():
        if bucket['Name'] == requested:
            return {'LocationConstraint': region, **metadata}
    return {'LocationConstraint': None, **metadata}


def raise_(ex):
    """Raise the given exception."""
    raise ex


_patched_operations = {
    'ListEnvironments': lambda *args, **kwargs: CLOUD9_LIST_ENVIRONMENTS,
    'DescribeInstances': lambda *args, **kwargs: deepcopy(EC2_DESCRIBE_INSTANCES),
    'ListFunctions': lambda *args, **kwargs: CLOUDFRONT_FUNCTIONS,
    'DescribeDefaultClusterParameters': lambda *args, **kwargs: deepcopy(REDSHIFT_FIRST_PAGE),
    'ListStacks': lambda *args, **kwargs: deepcopy(CLOUDFORMATION_LIST_STACKS_FIRST_PAGE),
    'DescribeEnvironments': lambda *args, **kwargs: CLOUD9_DESCRIBE_ENVIRONMENTS,
    'GetCallerIdentity': lambda *args, **kwargs: GET_CALLER_IDENTITY_PAYLOAD,
    'ListInvestigations': lambda *args, **kwargs: LIST_INVESTIGATIONS_PAYLOAD,
    'ListBuckets': lambda *args, **kwargs: LIST_BUCKETS_PAYLOAD,
    'ListObjects': lambda *args, **kwargs: LIST_OBJECTS_PAYLOAD,
    'GetMetricData': lambda *args, **kwargs: GET_METRIC_DATA_PAYLOAD,
    'GetMetricStatistics': lambda *args, **kwargs: GET_METRIC_STATISTICS_PAYLOAD,
    'BatchGetTraces': lambda *args, **kwargs: GET_BATCH_TRACES_PAYLOAD,
    'Invoke': lambda *args, **kwargs: LAMBDA_INVOKE_FUNCTION_PAYLOAD,
    'GetItem': lambda *args, **kwargs: DYNAMODB_GET_ITEM_PAYLOAD,
    'Scan': lambda *args, **kwargs: DYNAMODB_SCAN_PAYLOAD,
    'GetObject': lambda *args, **kwargs: S3_GET_OBJECT_PAYLOAD,
    'GetBucketLocation': _get_bucket_location_mock,
    'DescribeAlarms': lambda *args, **kwargs: raise_(
        botocore.exceptions.ClientError(DESCRIBE_ALARMS_PAYLOAD, 'DescribeAlarms')
    ),
    'DescribeCapacityReservationFleets': lambda *args, **kwargs: {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    },
    'ListManagedInsightRules': lambda *args, **kwargs: LIST_MANAGED_INSIGHT_RULES_PAYLOAD,
    'ListNodes': lambda *args, **kwargs: SSM_LIST_NODES_PAYLOAD,
}


def mock_make_api_call(self, operation_name, kwarg):
    """Mock the _make_api_call method for boto3 clients."""
    op = _patched_operations.get(operation_name)
    if op:
        history.emit(
            operation_name,
            kwarg,
            self._client_config.region_name,
            self._client_config.read_timeout,
            self.meta.endpoint_url,
        )
        return op(kwarg)

    # If we don't want to patch the API call; these will fail
    # as credentials are invalid
    return orig(self, operation_name, kwarg)


@contextlib.contextmanager
def patch_boto3():
    """Context manager to patch boto3 for non-paginated API calls."""

    def mock_can_paginate(self, operation_name):
        return False

    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with patch('botocore.client.BaseClient.can_paginate', new=mock_can_paginate):
            yield


@contextlib.contextmanager
def patch_boto3_paginated_cloudformation():
    """Context manager to patch boto3 for paginated CloudFormation API calls."""
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with patch('botocore.client.BaseClient.get_paginator') as mock_get_paginator:
            mock_paginator = MagicMock()

            mock_paginator.paginate.return_value = iter([CLOUDFORMATION_LIST_STACKS_SECOND_PAGE])

            mock_get_paginator.return_value = mock_paginator

            yield


@contextlib.contextmanager
def patch_boto3_paginated_redshift():
    """Context manager to patch boto3 for paginated Redshift API calls."""
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with patch('botocore.client.BaseClient.get_paginator') as mock_get_paginator:
            mock_paginator = MagicMock()

            mock_paginator.paginate.return_value = iter([REDSHIFT_SECOND_PAGE])

            mock_get_paginator.return_value = mock_paginator

            yield


@contextlib.contextmanager
def patch_boto3_paginated_cloudformation_for_max_limit():
    """Context manager to patch boto3 for paginated CloudFormation API calls with max limit."""
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with patch('botocore.client.BaseClient.get_paginator') as mock_get_paginator:
            mock_paginator = MagicMock()

            mock_paginator.paginate.return_value = iter(
                [CLOUDFORMATION_LIST_STACKS_FIRST_PAGE, CLOUDFORMATION_LIST_STACKS_FIRST_PAGE]
            )

            mock_get_paginator.return_value = mock_paginator

            yield
