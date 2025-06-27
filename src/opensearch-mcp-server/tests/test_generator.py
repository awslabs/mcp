import unittest
from awslabs.opensearch_mcp_server.generator import AWSToolGenerator
from unittest.mock import MagicMock, patch


# Create mock classes to avoid importing boto3 and botocore
class MockClientError(Exception):
    """Mock class for boto3's ClientError exception."""

    def __init__(self, error_response, operation_name):
        """Initialize the mock ClientError.

        Args:
            error_response: The error response dictionary
            operation_name: The name of the operation that failed

        """
        self.response = error_response
        self.operation_name = operation_name
        super().__init__(f'{operation_name} failed: {error_response}')


class TestAWSToolGenerator(unittest.TestCase):
    """Test suite for AWSToolGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mcp_mock = MagicMock()
        self.mcp_mock.tool = MagicMock(return_value=lambda x: x)

        # Mock boto3 client
        self.boto3_client_mock = MagicMock()
        self.boto3_session_mock = MagicMock()
        self.boto3_session_mock.client.return_value = self.boto3_client_mock

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    def test_initialization(self, mock_session):
        """Test initialization of AWSToolGenerator."""
        mock_session.return_value = self.boto3_session_mock

        # Test with minimal parameters
        generator = AWSToolGenerator(
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='15.0.1',
        )

        self.assertEqual(generator.service_name, 'opensearch')
        self.assertEqual(generator.service_display_name, 'Amazon OpenSearch Service')
        self.assertEqual(generator.mcp, self.mcp_mock)
        self.assertEqual(generator.tool_configuration, {})
        self.assertEqual(generator.skip_param_documentation, False)  # Default value

        # Test with tool configuration
        tool_config = {'operation1': {'supported': True}}
        generator = AWSToolGenerator(
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
            tool_configuration=tool_config,
        )

        self.assertEqual(generator.tool_configuration, tool_config)

        # Test with skip_param_documentation set to True
        generator = AWSToolGenerator(
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
            skip_param_documentation=True,
        )

        self.assertEqual(generator.skip_param_documentation, True)

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    @patch('awslabs.opensearch_mcp_server.generator.botocore.session.get_session')
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
        self.boto3_client_mock.describe_domain = MagicMock()
        dir_mock = MagicMock(return_value=['describe_domain'])
        self.boto3_client_mock.__dir__ = dir_mock

        # Create generator and call generate
        generator = AWSToolGenerator(
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
        )

        generator.generate()

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
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
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
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

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    @patch('awslabs.opensearch_mcp_server.generator.botocore.session.get_session')
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
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
        )

        # Access private method for testing
        func = generator._AWSToolGenerator__create_operation_function('describe_domain')

        # Verify function was created with correct attributes
        self.assertEqual(func.__name__, 'describe_domain')
        self.assertTrue('Execute the AWS Amazon OpenSearch' in func.__doc__)
        self.assertTrue(hasattr(func, '__signature__'))

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    def test_tool_configuration_validation(self, mock_session):
        """Test validation of tool configuration."""
        mock_session.return_value = self.boto3_session_mock

        # Test invalid configuration: both ignore and func_override
        with self.assertRaises(ValueError):
            AWSToolGenerator(
                service_name='opensearch',
                service_display_name='Amazon OpenSearch Service',
                mcp=self.mcp_mock,
                mcp_server_version='10.15.99',
                tool_configuration={'operation1': {'supported': False}},
            )

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    @patch('awslabs.opensearch_mcp_server.generator.botocore.session.get_session')
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
        with patch('awslabs.opensearch_mcp_server.generator.ClientError', MockClientError):
            # Setup client mock with operations that raises ClientError
            error_response = {
                'Error': {
                    'Code': 'DomainDoesNotExist',
                    'Message': 'The specified domain does not exist',
                }
            }
            self.boto3_client_mock.describe_domain = MagicMock(
                side_effect=MockClientError(error_response, 'DescribeDomain')
            )
            dir_mock = MagicMock(return_value=['describe_domain'])
            self.boto3_client_mock.__dir__ = dir_mock

            # Create generator
            generator = AWSToolGenerator(
                service_name='opensearch',
                service_display_name='Amazon OpenSearch Service',
                mcp=self.mcp_mock,
                mcp_server_version='10.15.99',
            )

            # Create the operation function directly
            operation_func = generator._AWSToolGenerator__create_operation_function(
                'describe_domain'
            )

            # Test the created function with ClientError
            import asyncio

            result = asyncio.run(operation_func(region='us-east-1'))

            # Verify error handling
            self.assertEqual(result['error'], 'The specified domain does not exist')
            self.assertEqual(result['code'], 'DomainDoesNotExist')

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    def test_get_mcp(self, mock_session):
        """Test get_mcp method."""
        mock_session.return_value = self.boto3_session_mock

        generator = AWSToolGenerator(
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
        )

        self.assertEqual(generator.get_mcp(), self.mcp_mock)

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    @patch('awslabs.opensearch_mcp_server.generator.botocore.session.get_session')
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
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
        )

        # Create generator with skip_param_documentation=True
        generator_without_docs = AWSToolGenerator(
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
            skip_param_documentation=True,
        )

        # Get operation parameters for both generators
        params_with_docs = generator_with_docs._AWSToolGenerator__get_operation_input_parameters(
            'describe_domain'
        )
        params_without_docs = (
            generator_without_docs._AWSToolGenerator__get_operation_input_parameters(
                'describe_domain'
            )
        )

        # Verify that documentation is included when skip_param_documentation=False
        self.assertEqual(params_with_docs[0][3], 'Test documentation')

        # Verify that documentation is empty when skip_param_documentation=True
        self.assertEqual(params_without_docs[0][3], '')

    @patch('awslabs.opensearch_mcp_server.generator.boto3.Session')
    @patch('awslabs.opensearch_mcp_server.generator.botocore.session.get_session')
    def test_annotated_field_for_optional_params(self, mock_botocore_session, mock_boto3_session):
        """Test that optional parameters use Annotated with Field for documentation and have None as default."""
        from typing import Annotated, get_args, get_origin

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

        # Setup members for input shape - one required and one optional parameter
        required_param_shape = MagicMock()
        required_param_shape.type_name = 'string'
        required_param_shape.documentation = 'Required parameter documentation'

        optional_param_shape = MagicMock()
        optional_param_shape.type_name = 'string'
        optional_param_shape.documentation = 'Optional parameter documentation'

        input_shape_mock.members = {
            'required_param': required_param_shape,
            'optional_param': optional_param_shape,
        }
        input_shape_mock.required_members = ['required_param']

        # Create generator
        generator = AWSToolGenerator(
            service_name='opensearch',
            service_display_name='Amazon OpenSearch Service',
            mcp=self.mcp_mock,
            mcp_server_version='10.15.99',
        )

        # Create the operation function
        operation_func = generator._AWSToolGenerator__create_operation_function('test_operation')

        # Verify the function was created
        self.assertIsNotNone(operation_func)

        # Get the signature parameters
        params = operation_func.__signature__.parameters

        # Check required parameter (should not use Annotated)
        required_param = params.get('required_param')
        self.assertIsNotNone(required_param)
        self.assertEqual(required_param.annotation, str)

        # Check optional parameter (should use Annotated with Field)
        optional_param = params.get('optional_param')
        self.assertIsNotNone(optional_param)

        # Verify it uses Annotated
        self.assertEqual(get_origin(optional_param.annotation), Annotated)

        # Get the args of Annotated
        args = get_args(optional_param.annotation)
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0], str | None)  # First arg should be the type (str | None)

        # Check if the Field has the expected attributes
        self.assertTrue(hasattr(args[1], 'description'))

        # Check if the default value is None
        self.assertEqual(optional_param.default, None)


def test_hello_world():
    """Basic test to verify test setup is working."""
    assert True, 'Hello world test passes'


if __name__ == '__main__':
    unittest.main()
