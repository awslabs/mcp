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
# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.

# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
# because boto3 client doesn't have any type hinting
import unittest
from awslabs.amazon_mq_mcp_server.aws_service_mcp_generator import AWSToolGenerator
from unittest.mock import MagicMock, patch


# Create mock classes to avoid importing boto3 and botocore
class MockClientError(Exception):
    """Create mock classes to avoid importing boto3 and botocore."""

    def __init__(self, error_response, operation_name):
        """Initiate mock client."""
        self.response = error_response
        self.operation_name = operation_name
        super().__init__(f'{operation_name} failed: {error_response}')


class TestAWSToolGenerator(unittest.TestCase):
    """Test suite for AWSToolGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mcp_mock = MagicMock()
        self.mcp_mock.tool = MagicMock(return_value=lambda x: x)  # Decorator mock

        # Mock boto3 client
        self.boto3_client_mock = MagicMock()
        self.boto3_session_mock = MagicMock()
        self.boto3_session_mock.client.return_value = self.boto3_client_mock

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    def test_initialization(self, mock_session):
        """Test initialization of AWSToolGenerator."""
        mock_session.return_value = self.boto3_session_mock

        # Test with minimal parameters
        generator = AWSToolGenerator(
            service_name='sqs', service_display_name='SQS', mcp=self.mcp_mock
        )

        self.assertEqual(generator.service_name, 'sqs')
        self.assertEqual(generator.service_display_name, 'SQS')
        self.assertEqual(generator.mcp, self.mcp_mock)
        self.assertEqual(generator.tool_configuration, {})
        self.assertEqual(generator.skip_param_documentation, False)  # Default value

        # Test with tool configuration
        tool_config = {'operation1': {'ignore': True}}
        generator = AWSToolGenerator(
            service_name='sns',
            service_display_name='SNS',
            mcp=self.mcp_mock,
            tool_configuration=tool_config,
        )

        self.assertEqual(generator.tool_configuration, tool_config)

        # Test with skip_param_documentation set to True
        generator = AWSToolGenerator(
            service_name='sns',
            service_display_name='SNS',
            mcp=self.mcp_mock,
            skip_param_documentation=True,
        )

        self.assertEqual(generator.skip_param_documentation, True)

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.botocore.session.get_session')
    def test_generate(self, mock_botocore_session, mock_boto3_session):
        """Test generate method registers operations as tools."""
        mock_boto3_session.return_value = self.boto3_session_mock

        # Setup mock for botocore session
        botocore_session_mock = MagicMock()
        mock_botocore_session.return_value = botocore_session_mock

        # Setup service model mock
        service_model_mock = MagicMock()
        botocore_session_mock.get_service_model.return_value = service_model_mock

        # Setup operation model mock
        operation_model_mock = MagicMock()
        service_model_mock.operation_model.return_value = operation_model_mock

        # Setup input shape mock
        input_shape_mock = MagicMock()
        operation_model_mock.input_shape = input_shape_mock

        # Setup members for input shape
        member_shape_mock = MagicMock()
        member_shape_mock.type_name = 'string'
        member_shape_mock.documentation = 'Test documentation'

        input_shape_mock.members = {'param1': member_shape_mock}
        input_shape_mock.required_members = ['param1']

        # Setup client mock with operations
        self.boto3_client_mock.get_queue_url = MagicMock()
        dir_mock = MagicMock(return_value=['get_queue_url'])
        self.boto3_client_mock.__dir__ = dir_mock

        # Create generator and call generate
        generator = AWSToolGenerator(
            service_name='sqs', service_display_name='SQS', mcp=self.mcp_mock
        )

        generator.generate()

        # Verify tool was registered
        self.mcp_mock.tool.assert_called()

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    def test_get_client(self, mock_session):
        """Test client creation and caching."""
        # Create different mock clients for different regions
        us_west_client = MagicMock(name='us_west_client')
        us_east_client = MagicMock(name='us_east_client')

        # Configure the session mock to return different clients based on region
        session_instances = {}

        def get_session(profile_name, region_name):
            if region_name not in session_instances:
                session_mock = MagicMock()
                if region_name == 'us-west-2':
                    session_mock.client.return_value = us_west_client
                else:
                    session_mock.client.return_value = us_east_client
                session_instances[region_name] = session_mock
            return session_instances[region_name]

        mock_session.side_effect = get_session

        generator = AWSToolGenerator(
            service_name='sqs', service_display_name='SQS', mcp=self.mcp_mock
        )

        # Access private method for testing
        client1 = generator._AWSToolGenerator__get_client('us-west-2')
        client2 = generator._AWSToolGenerator__get_client('us-west-2')
        client3 = generator._AWSToolGenerator__get_client('us-east-1')

        # Verify client caching works
        self.assertEqual(client1, client2)
        self.assertNotEqual(client1, client3)

        # Verify boto3 Session was called with correct parameters
        mock_session.assert_any_call(profile_name='default', region_name='us-west-2')
        mock_session.assert_any_call(profile_name='default', region_name='us-east-1')

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.botocore.session.get_session')
    def test_create_operation_function(self, mock_botocore_session, mock_boto3_session):
        """Test creation of operation functions."""
        mock_boto3_session.return_value = self.boto3_session_mock

        # Setup mock for botocore session
        botocore_session_mock = MagicMock()
        mock_botocore_session.return_value = botocore_session_mock

        # Setup service model mock
        service_model_mock = MagicMock()
        botocore_session_mock.get_service_model.return_value = service_model_mock

        # Setup operation model mock
        operation_model_mock = MagicMock()
        service_model_mock.operation_model.return_value = operation_model_mock

        # Setup input shape mock
        input_shape_mock = MagicMock()
        operation_model_mock.input_shape = input_shape_mock

        # Setup members for input shape
        member_shape_mock = MagicMock()
        member_shape_mock.type_name = 'string'
        member_shape_mock.documentation = 'Test documentation'

        input_shape_mock.members = {'param1': member_shape_mock}
        input_shape_mock.required_members = ['param1']

        generator = AWSToolGenerator(
            service_name='sqs', service_display_name='SQS', mcp=self.mcp_mock
        )

        # Access private method for testing
        func = generator._AWSToolGenerator__create_operation_function('get_queue_url')

        # Verify function was created with correct attributes
        self.assertEqual(func.__name__, 'get_queue_url')
        self.assertTrue('Execute the AWS SQS' in func.__doc__)
        self.assertTrue(hasattr(func, '__signature__'))

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    def test_tool_configuration_validation(self, mock_session):
        """Test validation of tool configuration."""
        mock_session.return_value = self.boto3_session_mock

        # Test invalid configuration: both ignore and func_override
        with self.assertRaises(ValueError):
            AWSToolGenerator(
                service_name='sqs',
                service_display_name='SQS',
                mcp=self.mcp_mock,
                tool_configuration={
                    'operation1': {
                        'ignore': True,
                        'func_override': lambda mcp, client_getter, op: None,
                    }
                },
            )

        # Test invalid configuration: both ignore and documentation_override
        with self.assertRaises(ValueError):
            AWSToolGenerator(
                service_name='sqs',
                service_display_name='SQS',
                mcp=self.mcp_mock,
                tool_configuration={
                    'operation1': {'ignore': True, 'documentation_override': 'Custom docs'}
                },
            )

        # Test invalid configuration: both func_override and documentation_override
        with self.assertRaises(ValueError):
            AWSToolGenerator(
                service_name='sqs',
                service_display_name='SQS',
                mcp=self.mcp_mock,
                tool_configuration={
                    'operation1': {
                        'func_override': lambda mcp, client_getter, op: None,
                        'documentation_override': 'Custom docs',
                    }
                },
            )

        # Test invalid configuration: empty override
        with self.assertRaises(ValueError):
            AWSToolGenerator(
                service_name='sqs',
                service_display_name='SQS',
                mcp=self.mcp_mock,
                tool_configuration={'operation1': {}},
            )

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.botocore.session.get_session')
    def test_function_override(self, mock_botocore_session, mock_boto3_session):
        """Test function override in tool configuration."""
        mock_boto3_session.return_value = self.boto3_session_mock

        # Setup mock for botocore session
        botocore_session_mock = MagicMock()
        mock_botocore_session.return_value = botocore_session_mock

        # Setup service model mock
        service_model_mock = MagicMock()
        botocore_session_mock.get_service_model.return_value = service_model_mock

        # Create a mock for the override function
        override_func_mock = MagicMock()

        # Setup client mock with operations
        self.boto3_client_mock.get_queue_url = MagicMock()
        dir_mock = MagicMock(return_value=['get_queue_url'])
        self.boto3_client_mock.__dir__ = dir_mock

        # Create generator with override
        generator = AWSToolGenerator(
            service_name='sqs',
            service_display_name='SQS',
            mcp=self.mcp_mock,
            tool_configuration={'get_queue_url': {'func_override': override_func_mock}},
        )

        generator.generate()

        # Verify override function was called
        override_func_mock.assert_called_once()
        args = override_func_mock.call_args[0]
        self.assertEqual(args[0], self.mcp_mock)
        self.assertTrue(callable(args[1]))  # client_getter is callable
        self.assertEqual(args[2], 'get_queue_url')

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.botocore.session.get_session')
    def test_validator(self, mock_botocore_session, mock_boto3_session):
        """Test validator in tool configuration."""
        mock_boto3_session.return_value = self.boto3_session_mock

        # Setup mock for botocore session
        botocore_session_mock = MagicMock()
        mock_botocore_session.return_value = botocore_session_mock

        # Setup service model mock
        service_model_mock = MagicMock()
        botocore_session_mock.get_service_model.return_value = service_model_mock

        # Setup operation model mock
        operation_model_mock = MagicMock()
        service_model_mock.operation_model.return_value = operation_model_mock

        # Setup input shape mock with no members
        input_shape_mock = MagicMock()
        input_shape_mock.members = {}
        input_shape_mock.required_members = []
        operation_model_mock.input_shape = input_shape_mock

        # Create a mock for the validator function
        validator_mock = MagicMock(return_value=(True, None))

        # Setup client mock with operations
        self.boto3_client_mock.get_queue_url = MagicMock(return_value={'QueueUrl': 'test-url'})
        dir_mock = MagicMock(return_value=['get_queue_url'])
        self.boto3_client_mock.__dir__ = dir_mock

        # Create generator with validator
        generator = AWSToolGenerator(
            service_name='sqs',
            service_display_name='SQS',
            mcp=self.mcp_mock,
            tool_configuration={'get_queue_url': {'validator': validator_mock}},
        )

        # Create the operation function directly
        operation_func = generator._AWSToolGenerator__create_operation_function(
            'get_queue_url', validator=validator_mock
        )

        # Test the created function with validator
        import asyncio

        result = asyncio.run(operation_func(region='us-east-1'))

        # Verify validator was called
        validator_mock.assert_called_once()
        self.assertEqual(result, {'QueueUrl': 'test-url'})

        # Test with validator returning False
        validator_mock.reset_mock()
        validator_mock.return_value = (False, 'Validation failed')
        result = asyncio.run(operation_func(region='us-east-1'))
        self.assertEqual(result, {'error': 'Validation failed'})

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.botocore.session.get_session')
    def test_client_error_handling(self, mock_botocore_session, mock_boto3_session):
        """Test handling of ClientError in operation functions."""
        mock_boto3_session.return_value = self.boto3_session_mock

        # Setup mock for botocore session
        botocore_session_mock = MagicMock()
        mock_botocore_session.return_value = botocore_session_mock

        # Setup service model mock
        service_model_mock = MagicMock()
        botocore_session_mock.get_service_model.return_value = service_model_mock

        # Setup operation model mock
        operation_model_mock = MagicMock()
        service_model_mock.operation_model.return_value = operation_model_mock

        # Setup input shape mock with no members
        input_shape_mock = MagicMock()
        input_shape_mock.members = {}
        input_shape_mock.required_members = []
        operation_model_mock.input_shape = input_shape_mock

        # Setup a function that will be returned by the decorator mock
        test_func = MagicMock()
        self.mcp_mock.tool.return_value = test_func

        # Patch ClientError in the module
        with patch(
            'awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.ClientError', MockClientError
        ):
            # Setup client mock with operations that raises ClientError
            error_response = {
                'Error': {
                    'Code': 'QueueDoesNotExist',
                    'Message': 'The specified queue does not exist',
                }
            }
            self.boto3_client_mock.get_queue_url = MagicMock(
                side_effect=MockClientError(error_response, 'GetQueueUrl')
            )
            dir_mock = MagicMock(return_value=['get_queue_url'])
            self.boto3_client_mock.__dir__ = dir_mock

            # Create generator
            generator = AWSToolGenerator(
                service_name='sqs', service_display_name='SQS', mcp=self.mcp_mock
            )

            # Create the operation function directly
            operation_func = generator._AWSToolGenerator__create_operation_function(
                'get_queue_url'
            )

            # Test the created function with ClientError
            import asyncio

            result = asyncio.run(operation_func(region='us-east-1'))

            # Verify error handling
            self.assertEqual(result['error'], 'The specified queue does not exist')
            self.assertEqual(result['code'], 'QueueDoesNotExist')

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    def test_get_mcp(self, mock_session):
        """Test get_mcp method."""
        mock_session.return_value = self.boto3_session_mock

        generator = AWSToolGenerator(
            service_name='sqs', service_display_name='SQS', mcp=self.mcp_mock
        )

        self.assertEqual(generator.get_mcp(), self.mcp_mock)

    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.aws_service_mcp_generator.botocore.session.get_session')
    def test_skip_param_documentation(self, mock_botocore_session, mock_boto3_session):
        """Test skip_param_documentation flag."""
        mock_boto3_session.return_value = self.boto3_session_mock

        # Setup mock for botocore session
        botocore_session_mock = MagicMock()
        mock_botocore_session.return_value = botocore_session_mock

        # Setup service model mock
        service_model_mock = MagicMock()
        botocore_session_mock.get_service_model.return_value = service_model_mock

        # Setup operation model mock
        operation_model_mock = MagicMock()
        service_model_mock.operation_model.return_value = operation_model_mock

        # Setup input shape mock
        input_shape_mock = MagicMock()
        operation_model_mock.input_shape = input_shape_mock

        # Setup members for input shape
        member_shape_mock = MagicMock()
        member_shape_mock.type_name = 'string'
        member_shape_mock.documentation = 'Test documentation'

        input_shape_mock.members = {'param1': member_shape_mock}
        input_shape_mock.required_members = ['param1']

        # Create generator with skip_param_documentation=False (default)
        generator_with_docs = AWSToolGenerator(
            service_name='sqs', service_display_name='SQS', mcp=self.mcp_mock
        )

        # Create generator with skip_param_documentation=True
        generator_without_docs = AWSToolGenerator(
            service_name='sqs',
            service_display_name='SQS',
            mcp=self.mcp_mock,
            skip_param_documentation=True,
        )

        # Get operation parameters for both generators
        params_with_docs = generator_with_docs._AWSToolGenerator__get_operation_input_parameters(
            'get_queue_url'
        )
        params_without_docs = (
            generator_without_docs._AWSToolGenerator__get_operation_input_parameters(
                'get_queue_url'
            )
        )

        # Verify that documentation is included when skip_param_documentation=False
        self.assertEqual(params_with_docs[0][3], 'Test documentation')

        # Verify that documentation is empty when skip_param_documentation=True
        self.assertEqual(params_without_docs[0][3], '')


def test_hello_world():
    """Basic test to verify test setup is working."""
    assert True, 'Hello world test passes'


if __name__ == '__main__':
    unittest.main()
