import unittest
from awslabs.cfn_mcp_server.errors import ClientError
from awslabs.cfn_mcp_server.stack_analysis.cloudformation_utils import CloudFormationUtils
from unittest.mock import MagicMock, patch


class TestCloudFormationUtils(unittest.TestCase):
    """Tests for the CloudFormationUtils class."""

    @patch('awslabs.cfn_mcp_server.stack_analysis.cloudformation_utils.get_aws_client')
    def setUp(self, mock_get_aws_client):
        """Set up each test."""
        self.mock_cfn_client = MagicMock()
        mock_get_aws_client.return_value = self.mock_cfn_client
        self.cfn_utils = CloudFormationUtils(region='us-east-1')
        # Manually set the client since the property might be missing
        self.cfn_utils._cfn_client = self.mock_cfn_client

    def test_list_stacks(self):
        """Test listing CloudFormation stacks."""
        expected_stacks = [
            {'StackName': 'stack1', 'StackStatus': 'CREATE_COMPLETE'},
            {'StackName': 'stack2', 'StackStatus': 'UPDATE_COMPLETE'},
        ]
        self.mock_cfn_client.list_stacks.return_value = {'StackSummaries': expected_stacks}

        result = self.cfn_utils.list_stacks()

        self.assertEqual(result, expected_stacks)
        self.mock_cfn_client.list_stacks.assert_called_once()

    def test_describe_stack(self):
        """Test describing a CloudFormation stack."""
        stack_name = 'test-stack'
        expected_description = {
            'StackName': stack_name,
            'StackStatus': 'CREATE_COMPLETE',
            'Parameters': [{'ParameterKey': 'key1', 'ParameterValue': 'value1'}],
        }
        self.mock_cfn_client.describe_stacks.return_value = {'Stacks': [expected_description]}

        result = self.cfn_utils.describe_stack(stack_name)

        self.assertEqual(result, expected_description)
        self.mock_cfn_client.describe_stacks.assert_called_once_with(StackName=stack_name)

    def test_list_stack_resources(self):
        """Test listing resources in a CloudFormation stack."""
        stack_name = 'test-stack'
        expected_resources = [
            {
                'LogicalResourceId': 'resource1',
                'PhysicalResourceId': 'id1',
                'ResourceType': 'AWS::S3::Bucket',
            },
            {
                'LogicalResourceId': 'resource2',
                'PhysicalResourceId': 'id2',
                'ResourceType': 'AWS::Lambda::Function',
            },
        ]
        self.mock_cfn_client.list_stack_resources.return_value = {
            'StackResourceSummaries': expected_resources
        }

        result = self.cfn_utils.list_stack_resources(stack_name)

        self.assertEqual(result, expected_resources)
        self.mock_cfn_client.list_stack_resources.assert_called_once_with(StackName=stack_name)

    def test_get_stack_template(self):
        """Test getting a CloudFormation stack template."""
        stack_name = 'test-stack'
        expected_template_body = {'Resources': {'MyBucket': {'Type': 'AWS::S3::Bucket'}}}
        self.mock_cfn_client.get_template.return_value = {'TemplateBody': expected_template_body}

        result = self.cfn_utils.get_stack_template(stack_name)

        self.assertEqual(result, expected_template_body)
        self.mock_cfn_client.get_template.assert_called_once_with(StackName=stack_name)

    def test_start_resource_scan(self):
        """Test starting a resource scan."""
        expected_scan_id = 'scan-12345'
        self.mock_cfn_client.start_resource_scan.return_value = {
            'ResourceScanId': expected_scan_id
        }

        result = self.cfn_utils.start_resource_scan()

        self.assertEqual(result, expected_scan_id)
        self.assertEqual(self.cfn_utils.resource_scan_id, expected_scan_id)
        self.mock_cfn_client.start_resource_scan.assert_called_once()

    def test_get_resource_scan_status_with_scan_id(self):
        """Test getting resource scan status with provided scan ID."""
        scan_id = 'scan-12345'
        expected_status = {
            'ResourceScanId': scan_id,
            'Status': 'COMPLETE',
            'StatusReason': 'Scan completed successfully',
        }
        self.mock_cfn_client.describe_resource_scan.return_value = expected_status

        result = self.cfn_utils.get_resource_scan_status(scan_id)

        self.assertEqual(result, expected_status)
        self.mock_cfn_client.describe_resource_scan.assert_called_once_with(ResourceScanId=scan_id)

    def test_list_resource_scan_resources_with_scan_id(self):
        """Test listing resource scan resources with provided scan ID."""
        scan_id = 'scan-12345'
        expected_resources = [
            {'ResourceType': 'AWS::S3::Bucket', 'ResourceIdentifier': {'BucketName': 'bucket1'}},
            {
                'ResourceType': 'AWS::Lambda::Function',
                'ResourceIdentifier': {'FunctionName': 'func1'},
            },
        ]

        # Mock paginator
        mock_paginator = MagicMock()
        mock_page_iterator = [{'Resources': expected_resources}]
        mock_paginator.paginate.return_value = mock_page_iterator
        self.mock_cfn_client.get_paginator.return_value = mock_paginator

        result = self.cfn_utils.list_resource_scan_resources(scan_id)

        self.assertEqual(result, expected_resources)
        self.mock_cfn_client.get_paginator.assert_called_once_with('list_resource_scan_resources')
        mock_paginator.paginate.assert_called_once_with(ResourceScanId=scan_id)

    def test_list_resource_scan_resources_no_scan_id(self):
        """Test listing resource scan resources without scan ID raises error."""
        with self.assertRaises(ClientError) as context:
            self.cfn_utils.list_resource_scan_resources()

        self.assertEqual(str(context.exception), 'No resource scan ID available')
