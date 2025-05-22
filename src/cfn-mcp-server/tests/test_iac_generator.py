# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the CloudFormation IaC Generator tool."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from awslabs.cfn_mcp_server.iac_generator import create_template
from awslabs.cfn_mcp_server.errors import ClientError


@pytest.fixture
def mock_cfn_client():
    """Create a mock CloudFormation client."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def mock_get_aws_client():
    """Mock the get_aws_client function."""
    with patch('awslabs.cfn_mcp_server.iac_generator.get_aws_client') as mock:
        yield mock


@pytest.mark.asyncio
async def test_create_template_validation_error_no_name_or_id():
    """Test validation error when neither template_name nor template_id is provided."""
    with pytest.raises(ClientError, match="Either template_name or template_id must be provided"):
        await create_template(template_name=None, template_id=None)


@pytest.mark.asyncio
async def test_create_template_validation_error_invalid_output_format():
    """Test validation error when output_format is invalid."""
    with pytest.raises(ClientError, match="output_format must be either 'JSON' or 'YAML'"):
        await create_template(template_name="test", output_format="XML")


@pytest.mark.asyncio
async def test_create_template_validation_error_invalid_deletion_policy():
    """Test validation error when deletion_policy is invalid."""
    with pytest.raises(ClientError, match="deletion_policy must be one of 'RETAIN', 'DELETE', or 'SNAPSHOT'"):
        await create_template(template_name="test", deletion_policy="INVALID")


@pytest.mark.asyncio
async def test_create_template_validation_error_invalid_update_replace_policy():
    """Test validation error when update_replace_policy is invalid."""
    with pytest.raises(ClientError, match="update_replace_policy must be one of 'RETAIN', 'DELETE', or 'SNAPSHOT'"):
        await create_template(template_name="test", update_replace_policy="INVALID")


@pytest.mark.asyncio
async def test_create_template_start_generation(mock_get_aws_client, mock_cfn_client):
    """Test starting a new template generation process."""
    mock_get_aws_client.return_value = mock_cfn_client
    mock_cfn_client.create_generated_template.return_value = {
        'GeneratedTemplateId': 'test-template-id'
    }

    result = await create_template(
        template_name="test-template",
        resources=[{"ResourceType": "AWS::S3::Bucket", "ResourceIdentifier": "test-bucket"}],
        output_format="YAML",
        deletion_policy="RETAIN",
        update_replace_policy="RETAIN"
    )

    mock_cfn_client.create_generated_template.assert_called_once_with(
        GeneratedTemplateName="test-template",
        TemplateConfiguration={
            'DeletionPolicy': "RETAIN",
            'UpdateReplacePolicy': "RETAIN"
        },
        Resources=[
            {"ResourceType": "AWS::S3::Bucket", "ResourceIdentifier": "test-bucket"}
        ]
    )

    assert result["status"] == "INITIATED"
    assert result["template_id"] == "test-template-id"
    assert "message" in result


@pytest.mark.asyncio
async def test_create_template_check_status_in_progress(mock_get_aws_client, mock_cfn_client):
    """Test checking the status of a template generation process that is in progress."""
    mock_get_aws_client.return_value = mock_cfn_client
    mock_cfn_client.describe_generated_template.return_value = {
        'Status': 'IN_PROGRESS'
    }

    result = await create_template(template_id="test-template-id")

    mock_cfn_client.describe_generated_template.assert_called_once_with(
        GeneratedTemplateName="test-template-id"
    )
    mock_cfn_client.get_generated_template.assert_not_called()

    assert result["status"] == "IN_PROGRESS"
    assert result["template_id"] == "test-template-id"
    assert "message" in result


@pytest.mark.asyncio
async def test_create_template_retrieve_template(mock_get_aws_client, mock_cfn_client):
    """Test retrieving a generated template."""
    mock_get_aws_client.return_value = mock_cfn_client
    mock_cfn_client.describe_generated_template.return_value = {
        'Status': 'COMPLETE',
        'ResourceIdentifiers': [
            {"ResourceType": "AWS::S3::Bucket", "ResourceIdentifier": "test-bucket"}
        ]
    }
    mock_cfn_client.get_generated_template.return_value = {
        'TemplateBody': 'template-content'
    }

    result = await create_template(template_id="test-template-id")

    mock_cfn_client.describe_generated_template.assert_called_once_with(
        GeneratedTemplateName="test-template-id"
    )
    mock_cfn_client.get_generated_template.assert_called_once_with(
        GeneratedTemplateName="test-template-id",
        Format="YAML"
    )

    assert result["status"] == "COMPLETED"
    assert result["template_id"] == "test-template-id"
    assert result["template"] == "template-content"
    assert "resources" in result
    assert "message" in result


@pytest.mark.asyncio
async def test_create_template_save_to_file(mock_get_aws_client, mock_cfn_client, tmpdir):
    """Test saving a generated template to a file."""
    mock_get_aws_client.return_value = mock_cfn_client
    mock_cfn_client.describe_generated_template.return_value = {
        'Status': 'COMPLETE',
        'ResourceIdentifiers': []
    }
    mock_cfn_client.get_generated_template.return_value = {
        'TemplateBody': 'template-content'
    }

    file_path = os.path.join(tmpdir, "template.yaml")

    result = await create_template(template_id="test-template-id", save_to_file=file_path)

    assert os.path.exists(file_path)
    with open(file_path, 'r') as f:
        assert f.read() == 'template-content'

    mock_cfn_client.get_generated_template.assert_called_once_with(
        GeneratedTemplateName="test-template-id",
        Format="YAML"
    )

    assert result["status"] == "COMPLETED"
    assert result["file_path"] == file_path


@pytest.mark.asyncio
async def test_create_template_resource_validation_error(mock_get_aws_client, mock_cfn_client):
    """Test validation error when resources are invalid."""
    mock_get_aws_client.return_value = mock_cfn_client

    with pytest.raises(ClientError, match="Each resource must have 'ResourceType' and 'ResourceIdentifier'"):
        await create_template(
            template_name="test-template",
            resources=[{"ResourceType": "AWS::S3::Bucket"}]  # Missing ResourceIdentifier
        )


@pytest.mark.asyncio
async def test_create_template_api_error(mock_get_aws_client, mock_cfn_client):
    """Test handling of API errors."""
    mock_get_aws_client.return_value = mock_cfn_client
    mock_cfn_client.create_generated_template.side_effect = Exception("API Error")

    with patch('awslabs.cfn_mcp_server.iac_generator.handle_aws_api_error') as mock_handle_error:
        mock_handle_error.side_effect = ClientError("Handled API Error")

        with pytest.raises(ClientError, match="Handled API Error"):
            await create_template(
                template_name="test-template",
                resources=[{"ResourceType": "AWS::S3::Bucket", "ResourceIdentifier": "test-bucket"}]
            )

        mock_handle_error.assert_called_once()
