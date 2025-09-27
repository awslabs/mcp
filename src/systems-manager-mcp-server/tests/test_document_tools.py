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

"""Tests for document tools."""

import json
import os
import sys
from botocore.exceptions import ClientError
from mcp.types import CallToolResult
from unittest.mock import Mock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.systems_manager_mcp_server.tools.documents import register_tools


class TestDocumentTools:
    """Test document tools with direct AWS API calls."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_mcp = Mock()
        self.registered_functions = []

        def capture_function(func):
            self.registered_functions.append(func)
            return func

        self.mock_mcp.tool.return_value = capture_function

    def test_register_tools_creates_functions(self):
        """Test that register_tools creates all tool functions."""
        register_tools(self.mock_mcp)
        assert len(self.registered_functions) == 9

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_create_document_success(self, mock_readonly, mock_session):
        """Test create_document with AWS API documentation example."""
        mock_readonly.return_value = False

        # Mock SSM client and response from AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.create_document.return_value = {
            'DocumentDescription': {
                'Sha1': 'EXAMPLE6-90ab-cdef-fedc-ba987EXAMPLE',
                'Hash': 'EXAMPLE6-90ab-cdef-fedc-ba987EXAMPLE',
                'Name': 'Example',
                'Owner': '123456789012',
                'CreatedDate': '2017-06-23T06:56:49.672000+00:00',
                'Status': 'Creating',
                'DocumentVersion': '1',
                'Description': 'Document Example',
                'DocumentType': 'Command',
                'SchemaVersion': '2.0',
            }
        }

        # Sample document content from AWS API documentation
        document_content = {
            'schemaVersion': '2.0',
            'description': 'Document Example',
            'parameters': {
                'ExampleParameter': {
                    'type': 'String',
                    'description': 'Example parameter',
                    'default': 'ExampleParameterValue',
                }
            },
            'mainSteps': [
                {
                    'action': 'aws:runPowerShellScript',
                    'name': 'ExampleStep',
                    'inputs': {'runCommand': ['{{ ExampleParameter }}']},
                }
            ],
        }

        register_tools(self.mock_mcp)
        create_func = self.registered_functions[0]  # create_document is first

        result = create_func(
            content=json.dumps(document_content),
            name='Example',
            document_type='Command',
            document_format='JSON',
            target_type='/AWS::EC2::Instance',
            version_name='1.0',
            display_name='Document Example',
            requires='[{"Name": "AWS-ConfigureAWSPackage", "Version": "1.0"}]',
            attachments='[{"Key": "SourceUrl", "Values": ["https://example.com/script.ps1"]}]',
            tags='[{"Key": "Environment", "Value": "Test"}]',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Example' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.create_document.assert_called_once()
        call_args = mock_ssm_client.create_document.call_args[1]
        assert call_args['Name'] == 'Example'
        assert call_args['DocumentType'] == 'Command'
        assert call_args['TargetType'] == '/AWS::EC2::Instance'
        assert call_args['VersionName'] == '1.0'
        assert call_args['DisplayName'] == 'Document Example'
        assert 'Requires' in call_args
        assert 'Attachments' in call_args
        assert 'Tags' in call_args

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_create_document_readonly_mode(self, mock_readonly, mock_session):
        """Test create_document in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        create_func = self.registered_functions[0]

        result = create_func(
            content='{"schemaVersion": "2.0"}', name='TestDoc', document_type='Command'
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_create_document_invalid_json(self, mock_readonly, mock_session):
        """Test create_document with invalid JSON parameters."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        create_func = self.registered_functions[0]

        # Test invalid requires JSON
        result = create_func(
            content='{"schemaVersion": "2.0"}',
            name='TestDoc',
            document_type='Command',
            requires='{"invalid": json}',
            attachments='{"invalid: json}',
            tags='{"invalid: json}',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in requires' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_create_document_invalid_json_attachments(self, mock_readonly, mock_session):
        """Test create_document with invalid JSON attachments parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        create_func = self.registered_functions[0]

        # Test invalid attachments JSON
        result = create_func(
            content='{"schemaVersion": "2.0"}',
            name='TestDoc',
            document_type='Command',
            document_format='JSON',
            target_type=None,
            version_name=None,
            display_name=None,
            requires=None,
            attachments='{"invalid": json}',
            tags=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in attachments' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_create_document_invalid_json_tags(self, mock_readonly, mock_session):
        """Test create_document with invalid JSON tags parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        create_func = self.registered_functions[0]

        # Test invalid tags JSON
        result = create_func(
            content='{"schemaVersion": "2.0"}',
            name='TestDoc',
            document_type='Command',
            document_format='JSON',
            target_type=None,
            version_name=None,
            display_name=None,
            requires=None,
            attachments=None,
            tags='{"invalid": json}',
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in tags' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_create_document_client_error(self, mock_readonly, mock_session):
        """Test create_document with ClientError."""
        mock_readonly.return_value = False

        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.create_document.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'DocumentAlreadyExists',
                    'Message': 'The specified document already exists.',
                }
            },
            operation_name='CreateDocument',
        )

        register_tools(self.mock_mcp)
        create_func = self.registered_functions[0]

        result = create_func(
            content='{"schemaVersion": "2.0"}',
            name='ExistingDoc',
            document_type='Command',
            document_format='JSON',
            target_type=None,
            version_name=None,
            display_name=None,
            requires=None,
            attachments=None,
            tags=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'already exists' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_delete_document_success(self, mock_readonly, mock_session):
        """Test delete_document with AWS API documentation example."""
        mock_readonly.return_value = False

        # Mock SSM client - delete_document returns empty response on success
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.delete_document.return_value = {}

        register_tools(self.mock_mcp)
        delete_func = self.registered_functions[1]  # delete_document is second

        result = delete_func(
            name='ExampleDocument',
            document_version='1',
            version_name=None,
            force=True,
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'ExampleDocument' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.delete_document.assert_called_once_with(
            Name='ExampleDocument', DocumentVersion='1', Force=True
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_delete_document_readonly_mode(self, mock_readonly, mock_session):
        """Test delete_document in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        delete_func = self.registered_functions[1]

        result = delete_func(
            name='TestDoc',
            document_version=None,
            version_name=None,
            force=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_delete_document_client_error(self, mock_readonly, mock_session):
        """Test delete_document with ClientError."""
        mock_readonly.return_value = False

        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.delete_document.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidDocument',
                    'Message': 'The specified document does not exist.',
                }
            },
            operation_name='DeleteDocument',
        )

        register_tools(self.mock_mcp)
        delete_func = self.registered_functions[1]

        result = delete_func(
            name='NonExistentDoc',
            document_version=None,
            version_name=None,
            force=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'does not exist' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_describe_document_success(self, mock_session):
        """Test describe_document with AWS API documentation example."""
        # Mock SSM client and response from AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_document.return_value = {
            'Document': {
                'Sha1': 'EXAMPLE6-90ab-cdef-fedc-ba987EXAMPLE',
                'Hash': 'EXAMPLE6-90ab-cdef-fedc-ba987EXAMPLE',
                'Name': 'Example',
                'Owner': '123456789012',
                'CreatedDate': '2017-06-23T06:56:49.672000+00:00',
                'Status': 'Active',
                'DocumentVersion': '1',
                'Description': 'Document Example',
                'DocumentType': 'Command',
                'PlatformTypes': ['Windows'],
                'DocumentFormat': 'JSON',
                'SchemaVersion': '2.0',
                'DefaultVersion': '1',
                'LatestVersion': '1',
                'Requires': [
                    {
                        'Name': 'AWS-ConfigureAWSPackage',
                        'Version': '1.0',
                        'RequireType': 'Document',
                    }
                ],
                'Parameters': [
                    {
                        'Name': 'ExampleParameter',
                        'Type': 'String',
                        'Description': 'Example parameter for testing',
                        'DefaultValue': 'ExampleParameterValue',
                        'AllowedValues': ['Value1', 'Value2'],
                        'AllowedPattern': '^[a-zA-Z0-9]*$',
                    }
                ],
                'Tags': [
                    {'Key': 'Environment', 'Value': 'Test'},
                    {'Key': 'Owner', 'Value': 'TestUser'},
                    {'Key': 'Project', 'Value': 'ExampleProject'},
                ],
            }
        }

        register_tools(self.mock_mcp)
        describe_func = self.registered_functions[2]  # describe_document is third

        result = describe_func(
            name='Example',
            document_version='1',
            version_name='N/A',
            region='us-east-1',
            profile='default',
        )

        # Verify result includes enhanced fields
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Example' in result.content[0].text
        assert 'Command' in result.content[0].text
        assert 'Active' in result.content[0].text
        assert 'Schema Version: 2.0' in result.content[0].text
        assert 'Created Date:' in result.content[0].text
        assert 'Default Version: 1' in result.content[0].text
        assert 'Platform Types: Windows' in result.content[0].text

        # Verify Requires section
        assert 'Requires: 1 requirement(s)' in result.content[0].text
        assert 'Name: AWS-ConfigureAWSPackage' in result.content[0].text
        assert 'Version: 1.0' in result.content[0].text
        assert 'Type: Document' in result.content[0].text

        # Verify Parameters section with all fields
        assert 'Parameters: 1 parameter(s)' in result.content[0].text
        assert 'Name: ExampleParameter' in result.content[0].text
        assert 'Type: String' in result.content[0].text
        assert 'Description: Example parameter for testing' in result.content[0].text
        assert 'Default: ExampleParameterValue' in result.content[0].text
        assert 'Allowed Values: Value1, Value2' in result.content[0].text
        assert 'Pattern: ^[a-zA-Z0-9]*$' in result.content[0].text

        # Verify Tags section - all tags should be shown
        assert 'Tags: 3 tag(s)' in result.content[0].text
        assert 'Environment: Test' in result.content[0].text
        assert 'Owner: TestUser' in result.content[0].text
        assert 'Project: ExampleProject' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.describe_document.assert_called_once_with(
            Name='Example', DocumentVersion='1', VersionName='N/A'
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_describe_document_client_error(self, mock_session):
        """Test describe_document with ClientError."""
        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_document.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidDocument',
                    'Message': 'The specified document does not exist.',
                }
            },
            operation_name='DescribeDocument',
        )

        register_tools(self.mock_mcp)
        describe_func = self.registered_functions[2]

        result = describe_func(
            name='NonExistentDoc',
            document_version=None,
            version_name=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'does not exist' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_describe_document_permission_success(self, mock_session):
        """Test describe_document_permission with AWS API documentation example."""
        # Mock SSM client and response from AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_document_permission.return_value = {
            'AccountIds': ['123456789012', '123456789013'],
            'AccountSharingInfoList': [
                {'AccountId': '123456789012', 'SharedDocumentVersion': '$LATEST'},
                {'AccountId': '123456789013', 'SharedDocumentVersion': '1'},
            ],
            'NextToken': '1111111111111111111111111',
        }

        register_tools(self.mock_mcp)
        describe_perm_func = self.registered_functions[3]  # describe_document_permission is fourth

        result = describe_perm_func(
            name='ExampleDocument',
            permission_type='Share',
            max_results=10,
            next_token='1111111111111111111111111',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'ExampleDocument' in result.content[0].text
        assert '123456789012, 123456789013' in result.content[0].text
        assert 'Account: 123456789012' in result.content[0].text
        assert 'Account: 123456789013' in result.content[0].text
        assert 'Next Token: 1111111111111111111111111' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.describe_document_permission.assert_called_once_with(
            Name='ExampleDocument',
            PermissionType='Share',
            MaxResults=10,
            NextToken='1111111111111111111111111',
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_describe_document_permission_client_error(self, mock_session):
        """Test describe_document_permission with ClientError."""
        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_document_permission.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidDocument',
                    'Message': 'The specified document does not exist.',
                }
            },
            operation_name='DescribeDocumentPermission',
        )

        register_tools(self.mock_mcp)
        describe_perm_func = self.registered_functions[3]

        result = describe_perm_func(
            name='NonExistentDoc',
            permission_type='Share',
            max_results=None,
            next_token=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'does not exist' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_get_document_success(self, mock_session):
        """Test get_document with AWS API documentation example."""
        # Mock SSM client and response from AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_document.return_value = {
            'Document': {
                'Name': 'ExampleDocument',
                'DisplayName': 'Example Document Display Name',
                'VersionName': '1.0',
                'DocumentType': 'Command',
                'DocumentFormat': 'JSON',
                'Status': 'Active',
                'Requires': [
                    {
                        'Name': 'AWS-ConfigureAWSPackage',
                        'Version': '1.0',
                        'RequireType': 'Document',
                    },
                    {
                        'Name': 'AWS-UpdateSSMAgent',
                        'Version': '2.0',
                        'RequireType': 'Document',
                        'VersionName': 'Latest',
                    },
                ],
                'Content': '{\n  "schemaVersion": "2.2",\n  "description": "Example document content"\n}',
            }
        }

        register_tools(self.mock_mcp)
        get_func = self.registered_functions[4]  # get_document is fifth

        result = get_func(
            name='ExampleDocument',
            version_name='1.0',
            document_version=None,
            document_format='JSON',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'ExampleDocument' in result.content[0].text
        assert 'Example Document Display Name' in result.content[0].text
        assert 'Version: 1.0' in result.content[0].text
        assert 'Type: Command' in result.content[0].text
        assert 'Format: JSON' in result.content[0].text
        assert 'Status: Active' in result.content[0].text

        # Verify Requires section
        assert 'Requires: 2 requirement(s)' in result.content[0].text
        assert 'Name: AWS-ConfigureAWSPackage' in result.content[0].text
        assert 'Version: 1.0' in result.content[0].text
        assert 'Type: Document' in result.content[0].text
        assert 'Name: AWS-UpdateSSMAgent' in result.content[0].text
        assert 'Version: 2.0' in result.content[0].text
        assert 'Version Name: Latest' in result.content[0].text

        # Verify Content section
        assert '**Content:**' in result.content[0].text
        assert 'schemaVersion' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.get_document.assert_called_once_with(
            Name='ExampleDocument', VersionName='1.0', DocumentFormat='JSON'
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_get_document_client_error(self, mock_session):
        """Test get_document with ClientError."""
        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_document.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidDocument',
                    'Message': 'The specified document does not exist.',
                }
            },
            operation_name='GetDocument',
        )

        register_tools(self.mock_mcp)
        get_func = self.registered_functions[4]

        result = get_func(
            name='NonExistentDoc',
            version_name=None,
            document_version=None,
            document_format=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'does not exist' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_list_documents_success(self, mock_session):
        """Test list_documents with AWS API documentation example."""
        # Mock SSM client and response from AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_documents.return_value = {
            'DocumentIdentifiers': [
                {
                    'Name': 'ExampleDocument1',
                    'Owner': '123456789012',
                    'DocumentType': 'Command',
                    'DocumentFormat': 'JSON',
                    'DocumentVersion': '1',
                    'CreatedDate': '2017-06-23T06:56:49.672000+00:00',
                    'DisplayName': 'Example Document 1',
                    'SchemaVersion': '2.2',
                    'PlatformTypes': ['Windows', 'Linux'],
                    'Tags': [{'Key': 'Environment', 'Value': 'Test'}],
                    'TargetType': '/AWS::EC2::Instance',
                    'Requires': [{'Name': 'AWS-ConfigureAWSPackage', 'Version': '1.0'}],
                },
                {
                    'Name': 'ExampleDocument2',
                    'Owner': '123456789012',
                    'DocumentType': 'Automation',
                    'DocumentFormat': 'YAML',
                    'DocumentVersion': '2',
                    'CreatedDate': '2017-06-24T06:56:49.672000+00:00',
                    'SchemaVersion': '0.3',
                    'PlatformTypes': ['Linux'],
                },
            ],
            'NextToken': '1111111111111111111111111',
        }

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[5]  # list_documents is sixth

        result = list_func(
            document_filter_list='[{"key": "Owner", "value": "Self"}]',
            filters='[{"Key": "DocumentType", "Values": ["Command"]}]',
            max_results=10,
            next_token='1111111111111111111111111',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Found 2 documents' in result.content[0].text

        # Verify first document details
        assert 'ExampleDocument1' in result.content[0].text
        assert 'Type: Command' in result.content[0].text
        assert 'Owner: 123456789012' in result.content[0].text
        assert 'Format: JSON' in result.content[0].text
        assert 'Version: 1' in result.content[0].text
        assert 'Created: 2017-06-23T06:56:49.672000+00:00' in result.content[0].text
        assert 'Display Name: Example Document 1' in result.content[0].text
        assert 'Schema Version: 2.2' in result.content[0].text
        assert 'Platforms: Windows, Linux' in result.content[0].text
        assert 'Target Type: /AWS::EC2::Instance' in result.content[0].text

        # Verify second document details
        assert 'ExampleDocument2' in result.content[0].text
        assert 'Type: Automation' in result.content[0].text
        assert 'Format: YAML' in result.content[0].text
        assert 'Version: 2' in result.content[0].text
        assert 'Schema Version: 0.3' in result.content[0].text
        assert 'Platforms: Linux' in result.content[0].text

        # Verify NextToken
        assert 'Next Token: 1111111111111111111111111' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.list_documents.assert_called_once_with(
            DocumentFilterList=[{'key': 'Owner', 'value': 'Self'}],
            Filters=[{'Key': 'DocumentType', 'Values': ['Command']}],
            MaxResults=10,
            NextToken='1111111111111111111111111',
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_list_documents_no_results(self, mock_session):
        """Test list_documents with no results."""
        # Mock SSM client with empty response
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_documents.return_value = {'DocumentIdentifiers': []}

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[5]

        result = list_func(
            document_filter_list=None,
            filters=None,
            max_results=50,
            next_token=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'No documents found matching the criteria' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_list_documents_invalid_json(self, mock_session):
        """Test list_documents with invalid JSON filter."""
        register_tools(self.mock_mcp)
        list_func = self.registered_functions[5]

        result = list_func(
            document_filter_list='{"invalid": json}',
            filters=None,
            max_results=50,
            next_token=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in document_filter_list' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_list_documents_invalid_filters_json(self, mock_session):
        """Test list_documents with invalid JSON in filters parameter."""
        register_tools(self.mock_mcp)
        list_func = self.registered_functions[5]

        result = list_func(
            document_filter_list=None,
            filters='{"invalid": json}',
            max_results=50,
            next_token=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in filters' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_list_documents_client_error(self, mock_session):
        """Test list_documents with ClientError."""
        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_documents.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'User is not authorized to perform this operation.',
                }
            },
            operation_name='ListDocuments',
        )

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[5]

        result = list_func(
            document_filter_list=None,
            filters=None,
            max_results=50,
            next_token=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'not authorized' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_modify_document_permission_success(self, mock_readonly, mock_session):
        """Test modify_document_permission with AWS API documentation example."""
        mock_readonly.return_value = False

        # Mock SSM client - modify_document_permission returns empty response on success
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.modify_document_permission.return_value = {}

        register_tools(self.mock_mcp)
        modify_perm_func = self.registered_functions[6]  # modify_document_permission is seventh

        result = modify_perm_func(
            name='ExampleDocument',
            permission_type='Share',
            account_ids_to_add='123456789012,123456789013',
            account_ids_to_remove='123456789014',
            shared_document_version='1',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'ExampleDocument' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.modify_document_permission.assert_called_once_with(
            Name='ExampleDocument',
            PermissionType='Share',
            AccountIdsToAdd=['123456789012', '123456789013'],
            AccountIdsToRemove=['123456789014'],
            SharedDocumentVersion='1',
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_modify_document_permission_readonly_mode(self, mock_readonly, mock_session):
        """Test modify_document_permission in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        modify_perm_func = self.registered_functions[6]

        result = modify_perm_func(
            name='TestDoc',
            permission_type='Share',
            account_ids_to_add=None,
            account_ids_to_remove=None,
            shared_document_version=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_modify_document_permission_add_only(self, mock_readonly, mock_session):
        """Test modify_document_permission adding accounts only."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.modify_document_permission.return_value = {}

        register_tools(self.mock_mcp)
        modify_perm_func = self.registered_functions[6]

        result = modify_perm_func(
            name='TestDocument',
            permission_type='Share',
            account_ids_to_add='123456789012',
            account_ids_to_remove=None,
            shared_document_version=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'TestDocument' in result.content[0].text

        # Verify AWS API was called with only AccountIdsToAdd
        mock_ssm_client.modify_document_permission.assert_called_once_with(
            Name='TestDocument', PermissionType='Share', AccountIdsToAdd=['123456789012']
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_modify_document_permission_remove_only(self, mock_readonly, mock_session):
        """Test modify_document_permission removing accounts only."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.modify_document_permission.return_value = {}

        register_tools(self.mock_mcp)
        modify_perm_func = self.registered_functions[6]

        result = modify_perm_func(
            name='TestDocument',
            permission_type='Share',
            account_ids_to_add=None,
            account_ids_to_remove='123456789014,123456789015',
            shared_document_version=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'TestDocument' in result.content[0].text

        # Verify AWS API was called with only AccountIdsToRemove
        mock_ssm_client.modify_document_permission.assert_called_once_with(
            Name='TestDocument',
            PermissionType='Share',
            AccountIdsToRemove=['123456789014', '123456789015'],
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_modify_document_permission_client_error(self, mock_readonly, mock_session):
        """Test modify_document_permission with ClientError."""
        mock_readonly.return_value = False

        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.modify_document_permission.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidDocument',
                    'Message': 'The specified document does not exist.',
                }
            },
            operation_name='ModifyDocumentPermission',
        )

        register_tools(self.mock_mcp)
        modify_perm_func = self.registered_functions[6]

        result = modify_perm_func(
            name='NonExistentDoc',
            permission_type='Share',
            account_ids_to_add='123456789012',
            account_ids_to_remove=None,
            shared_document_version=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'does not exist' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_success(self, mock_readonly, mock_session):
        """Test update_document with AWS API documentation example."""
        mock_readonly.return_value = False

        # Mock SSM client and response from AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.update_document.return_value = {
            'DocumentDescription': {
                'Sha1': 'EXAMPLE6-90ab-cdef-fedc-ba987EXAMPLE',
                'Hash': 'EXAMPLE6-90ab-cdef-fedc-ba987EXAMPLE',
                'Name': 'ExampleDocument',
                'Owner': '123456789012',
                'CreatedDate': '2017-06-23T06:56:49.672000+00:00',
                'Status': 'Updating',
                'DocumentVersion': '2',
                'Description': 'Updated Document Example',
                'DocumentType': 'Command',
                'SchemaVersion': '2.0',
            }
        }

        # Updated document content
        updated_content = {
            'schemaVersion': '2.0',
            'description': 'Updated Document Example',
            'parameters': {
                'UpdatedParameter': {
                    'type': 'String',
                    'description': 'Updated parameter',
                    'default': 'UpdatedValue',
                }
            },
            'mainSteps': [
                {
                    'action': 'aws:runShellScript',
                    'name': 'UpdatedStep',
                    'inputs': {'runCommand': ['echo {{ UpdatedParameter }}']},
                }
            ],
        }

        register_tools(self.mock_mcp)
        update_func = self.registered_functions[7]  # update_document is eighth

        result = update_func(
            content=json.dumps(updated_content),
            name='ExampleDocument',
            document_version='1',
            document_format='JSON',
            target_type='/AWS::EC2::Instance',
            version_name='2.0',
            display_name='Updated Document Example',
            attachments='[{"Key": "SourceUrl", "Values": ["https://example.com/updated-script.sh"]}]',
            requires='[{"Name": "AWS-ConfigureAWSPackage", "Version": "2.0"}]',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'ExampleDocument' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.update_document.assert_called_once()
        call_args = mock_ssm_client.update_document.call_args[1]
        assert call_args['Name'] == 'ExampleDocument'
        assert call_args['DocumentVersion'] == '1'
        assert call_args['DocumentFormat'] == 'JSON'
        assert call_args['TargetType'] == '/AWS::EC2::Instance'
        assert call_args['VersionName'] == '2.0'
        assert call_args['DisplayName'] == 'Updated Document Example'
        assert 'Attachments' in call_args
        assert 'Requires' in call_args

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_readonly_mode(self, mock_readonly, mock_session):
        """Test update_document in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        update_func = self.registered_functions[7]

        result = update_func(
            content='{"schemaVersion": "2.0"}',
            name='TestDoc',
            document_version=None,
            document_format='JSON',
            target_type=None,
            version_name=None,
            display_name=None,
            attachments=None,
            requires=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_invalid_attachments_json(self, mock_readonly, mock_session):
        """Test update_document with invalid JSON attachments parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        update_func = self.registered_functions[7]

        result = update_func(
            content='{"schemaVersion": "2.0"}',
            name='TestDoc',
            document_version=None,
            document_format='JSON',
            target_type=None,
            version_name=None,
            display_name=None,
            attachments='{"invalid": json}',
            requires=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in attachments' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_invalid_requires_json(self, mock_readonly, mock_session):
        """Test update_document with invalid JSON requires parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        update_func = self.registered_functions[7]

        result = update_func(
            content='{"schemaVersion": "2.0"}',
            name='TestDoc',
            document_version=None,
            document_format='JSON',
            target_type=None,
            version_name=None,
            display_name=None,
            attachments=None,
            requires='{"invalid": json}',
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in requires' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_client_error(self, mock_readonly, mock_session):
        """Test update_document with ClientError."""
        mock_readonly.return_value = False

        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.update_document.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidDocument',
                    'Message': 'The specified document does not exist.',
                }
            },
            operation_name='UpdateDocument',
        )

        register_tools(self.mock_mcp)
        update_func = self.registered_functions[7]

        result = update_func(
            content='{"schemaVersion": "2.0"}',
            name='NonExistentDoc',
            document_version=None,
            document_format='JSON',
            target_type=None,
            version_name=None,
            display_name=None,
            attachments=None,
            requires=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'does not exist' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_default_version_success(self, mock_readonly, mock_session):
        """Test update_document_default_version with AWS API documentation example."""
        mock_readonly.return_value = False

        # Mock SSM client and response from AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.update_document_default_version.return_value = {
            'Description': {
                'Name': 'ExampleDocument',
                'DefaultVersion': '2',
                'DefaultVersionName': 'Version2.0',
            }
        }

        register_tools(self.mock_mcp)
        update_default_func = self.registered_functions[
            8
        ]  # update_document_default_version is ninth

        result = update_default_func(
            name='ExampleDocument', document_version='2', region='us-east-1', profile='default'
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'ExampleDocument' in result.content[0].text
        assert 'version 2' in result.content[0].text
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.update_document_default_version.assert_called_once_with(
            Name='ExampleDocument', DocumentVersion='2'
        )

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_default_version_readonly_mode(self, mock_readonly, mock_session):
        """Test update_document_default_version in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        update_default_func = self.registered_functions[8]

        result = update_default_func(
            name='TestDoc', document_version='1', region=None, profile=None
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_default_version_client_error(self, mock_readonly, mock_session):
        """Test update_document_default_version with ClientError."""
        mock_readonly.return_value = False

        # Mock SSM client to raise ClientError
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.update_document_default_version.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidDocumentVersion',
                    'Message': 'The specified document version is not valid or does not exist.',
                }
            },
            operation_name='UpdateDocumentDefaultVersion',
        )

        register_tools(self.mock_mcp)
        update_default_func = self.registered_functions[8]

        result = update_default_func(
            name='ExampleDocument', document_version='999', region=None, profile=None
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error' in result.content[0].text
        assert 'not valid or does not exist' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_create_document_exception(self, mock_readonly, mock_session, mock_log_error):
        """Test create_document with generic Exception."""
        mock_readonly.return_value = False
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.create_document.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        create_func = self.registered_functions[0]

        result = create_func(
            content='{"schemaVersion": "2.0"}', name='TestDoc', document_type='Command'
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_delete_document_exception(self, mock_readonly, mock_session, mock_log_error):
        """Test delete_document with generic Exception."""
        mock_readonly.return_value = False
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.delete_document.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        delete_func = self.registered_functions[1]

        result = delete_func(name='TestDoc')

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_describe_document_exception(self, mock_session, mock_log_error):
        """Test describe_document with generic Exception."""
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_document.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        describe_func = self.registered_functions[2]

        result = describe_func(name='TestDoc')

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_describe_document_permission_exception(self, mock_session, mock_log_error):
        """Test describe_document_permission with generic Exception."""
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_document_permission.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        describe_perm_func = self.registered_functions[3]

        result = describe_perm_func(name='TestDoc', permission_type='Share')

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_get_document_exception(self, mock_session, mock_log_error):
        """Test get_document with generic Exception."""
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_document.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        get_func = self.registered_functions[4]

        result = get_func(name='TestDoc')

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    def test_list_documents_exception(self, mock_session, mock_log_error):
        """Test list_documents with generic Exception."""
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_documents.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[5]

        result = list_func()

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_modify_document_permission_exception(
        self, mock_readonly, mock_session, mock_log_error
    ):
        """Test modify_document_permission with generic Exception."""
        mock_readonly.return_value = False
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.modify_document_permission.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        modify_perm_func = self.registered_functions[6]

        result = modify_perm_func(name='TestDoc', account_ids_to_add='123456789012')

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_exception(self, mock_readonly, mock_session, mock_log_error):
        """Test update_document with generic Exception."""
        mock_readonly.return_value = False
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.update_document.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        update_func = self.registered_functions[7]

        result = update_func(content='{"schemaVersion": "2.0"}', name='TestDoc')

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.documents.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.documents.Context.is_readonly')
    def test_update_document_default_version_exception(
        self, mock_readonly, mock_session, mock_log_error
    ):
        """Test update_document_default_version with generic Exception."""
        mock_readonly.return_value = False
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        # Mock SSM client to raise generic Exception
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.update_document_default_version.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        update_default_func = self.registered_functions[8]

        result = update_default_func(name='TestDoc', document_version='1')

        assert isinstance(result, CallToolResult)
        assert result.isError is True


def test_aws_api_example_data():
    """Test that AWS API documentation example data is valid JSON."""
    # Sample document content from AWS API documentation
    document_content = {
        'schemaVersion': '2.0',
        'description': 'Document Example',
        'parameters': {
            'ExampleParameter': {
                'type': 'String',
                'description': 'Example parameter',
                'default': 'ExampleParameterValue',
            }
        },
        'mainSteps': [
            {
                'action': 'aws:runPowerShellScript',
                'name': 'ExampleStep',
                'inputs': {'runCommand': ['{{ ExampleParameter }}']},
            }
        ],
    }

    # Verify it can be serialized to JSON
    json_content = json.dumps(document_content)
    assert json_content is not None
    assert len(json_content) > 0

    # Verify it can be parsed back
    parsed_content = json.loads(json_content)
    assert parsed_content['schemaVersion'] == '2.0'
    assert parsed_content['description'] == 'Document Example'
