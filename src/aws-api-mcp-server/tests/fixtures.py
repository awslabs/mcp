import botocore.client
import botocore.exceptions
import contextlib
import datetime
from .history_handler import history
from awslabs.aws_api_mcp_server.core.common.models import Credentials
from copy import deepcopy
from unittest.mock import patch


S3_CLI_NO_REGION = 'aws s3api list-buckets'

CLOUD9_PARAMS_CLI_MISSING_CONTEXT = (
    'aws cloud9 create-environment-ec2 --name test --instance-type t3.large'
)
CLOUD9_PARAMS_MISSING_CONTEXT_FAILURES = {
    'validation_failures': None,
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

T2_EC2_DESCRIBE_INSTANCES_FILTERED = {
    'Result': [
        EMPTY_EC2_RESERVATION.get('Instances'),
        T2_EC2_INSTANCE_RESERVATION.get('Instances'),
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

IAD_BUCKET = {'Name': 'IAD', 'CreationDate': '2022-07-13T15:20:58+00:00'}
DUB_BUCKET = {'Name': 'DUB', 'CreationDate': '2022-07-13T15:20:58+00:00'}
PDX_BUCKET = {'Name': 'PDX', 'CreationDate': '2022-07-13T15:20:58+00:00'}

LIST_BUCKETS_PAYLOAD = {
    'ResponseMetadata': {'HTTPStatusCode': 200},
    'Buckets': [
        IAD_BUCKET,
        DUB_BUCKET,
        PDX_BUCKET,
    ],
    'Owner': {'DisplayName': 'clpo', 'ID': '***'},
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


def raise_(ex):
    """Raise the given exception."""
    raise ex


_patched_operations = {
    'ListEnvironments': lambda *args, **kwargs: CLOUD9_LIST_ENVIRONMENTS,
    'DescribeInstances': lambda *args, **kwargs: deepcopy(EC2_DESCRIBE_INSTANCES),
    'ListFunctions': lambda *args, **kwargs: CLOUDFRONT_FUNCTIONS,
    'DescribeEnvironments': lambda *args, **kwargs: CLOUD9_DESCRIBE_ENVIRONMENTS,
    'GetCallerIdentity': lambda *args, **kwargs: GET_CALLER_IDENTITY_PAYLOAD,
    'ListBuckets': lambda *args, **kwargs: LIST_BUCKETS_PAYLOAD,
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

    with patch(
        'awslabs.aws_api_mcp_server.core.aws.driver.get_local_credentials',
        return_value=Credentials(**TEST_CREDENTIALS),
    ):
        with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
            with patch('botocore.client.BaseClient.can_paginate', new=mock_can_paginate):
                yield


class DummyCtx:
    """Mock implementation of MCP context for testing purposes."""

    async def error(self, message):
        """Mock MCP ctx.error with the given message.

        Args:
            message: The error message
        """
        # Do nothing because MCP ctx.error doesn't throw exception
        pass
