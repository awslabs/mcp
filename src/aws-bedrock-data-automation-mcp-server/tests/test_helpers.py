"""Tests for the AWS Bedrock Data Automation MCP Server helpers."""

import json
import os
import pytest
from awslabs.aws_bedrock_data_automation_mcp_server.helpers import (
    download_from_s3,
    get_account_id,
    get_bedrock_data_automation_client,
    get_bedrock_data_automation_runtime_client,
    get_bucket_and_key_from_s3_uri,
    get_bucket_name,
    get_profile_arn,
    get_project,
    get_region,
    get_s3_client,
    invoke_data_automation_and_get_results,
    list_projects,
    upload_to_s3,
)
from unittest.mock import AsyncMock, MagicMock, mock_open, patch


def test_get_region():
    """Test the get_region function."""
    with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
        assert get_region() == 'us-west-2'

    with patch.dict(os.environ, {}, clear=True):
        assert get_region() == 'us-east-1'


def test_get_account_id():
    """Test the get_account_id function."""
    with patch.dict(os.environ, {'AWS_ACCOUNT_ID': '123456789012'}):
        assert get_account_id() == '123456789012'

    with patch.dict(os.environ, {}, clear=True):
        assert get_account_id() is None


def test_get_bucket_name():
    """Test the get_bucket_name function."""
    with patch.dict(os.environ, {'AWS_BUCKET_NAME': 'test-bucket'}):
        assert get_bucket_name() == 'test-bucket'

    with patch.dict(os.environ, {}, clear=True):
        assert get_bucket_name() is None


def test_get_profile_arn():
    """Test the get_profile_arn function."""
    with patch.dict(os.environ, {'AWS_REGION': 'us-west-2', 'AWS_ACCOUNT_ID': '123456789012'}):
        assert (
            get_profile_arn()
            == 'arn:aws:bedrock:us-west-2:123456789012:data-automation-profile/us.data-automation-v1'
        )

    with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}, clear=True):
        assert get_profile_arn() is None


def test_get_bedrock_data_automation_client():
    """Test the get_bedrock_data_automation_client function."""
    with patch('boto3.client') as mock_client:
        get_bedrock_data_automation_client()
        mock_client.assert_called_once_with('bedrock-data-automation', region_name=get_region())


def test_get_bedrock_data_automation_runtime_client():
    """Test the get_bedrock_data_automation_runtime_client function."""
    with patch('boto3.client') as mock_client:
        get_bedrock_data_automation_runtime_client()
        mock_client.assert_called_once_with(
            'bedrock-data-automation-runtime', region_name=get_region()
        )


def test_get_s3_client():
    """Test the get_s3_client function."""
    with patch('boto3.client') as mock_client:
        get_s3_client()
        mock_client.assert_called_once_with('s3', region_name=get_region())


@pytest.mark.asyncio
async def test_list_projects():
    """Test the list_projects function."""
    mock_client = MagicMock()
    mock_client.list_data_automation_projects.return_value = {
        'projects': [{'name': 'test-project'}]
    }

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_client',
        return_value=mock_client,
    ):
        result = await list_projects()
        assert result == [{'name': 'test-project'}]
        mock_client.list_data_automation_projects.assert_called_once()


@pytest.mark.asyncio
async def test_get_project():
    """Test the get_project function."""
    mock_client = MagicMock()
    mock_client.get_data_automation_project.return_value = {'project': {'name': 'test-project'}}

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_client',
        return_value=mock_client,
    ):
        result = await get_project('test-arn')
        assert result == {'name': 'test-project'}
        mock_client.get_data_automation_project.assert_called_once_with(projectArn='test-arn')


@pytest.mark.asyncio
async def test_upload_to_s3():
    """Test the upload_to_s3 function."""
    with patch.dict(os.environ, {'AWS_BUCKET_NAME': 'test-bucket'}):
        with patch(
            'awslabs.aws_bedrock_data_automation_mcp_server.helpers.Path.exists', return_value=True
        ):
            with patch('builtins.open', mock_open(read_data=b'test data')):
                with patch(
                    'awslabs.aws_bedrock_data_automation_mcp_server.helpers.uuid.uuid4',
                    return_value='test-uuid',
                ):
                    with patch(
                        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_s3_client'
                    ) as mock_get_client:
                        mock_client = MagicMock()
                        mock_get_client.return_value = mock_client

                        result = await upload_to_s3('/path/to/asset.pdf')

                        assert result == 's3://test-bucket/mcp/test-uuid.pdf'
                        mock_client.put_object.assert_called_once_with(
                            Bucket='test-bucket', Key='mcp/test-uuid.pdf', Body=b'test data'
                        )


@pytest.mark.asyncio
async def test_upload_to_s3_no_bucket():
    """Test the upload_to_s3 function when no bucket is set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match='AWS_BUCKET_NAME environment variable is not set'):
            await upload_to_s3('/path/to/asset.pdf')


@pytest.mark.asyncio
async def test_upload_to_s3_file_not_exists():
    """Test the upload_to_s3 function when the file does not exist."""
    with patch.dict(os.environ, {'AWS_BUCKET_NAME': 'test-bucket'}):
        with patch(
            'awslabs.aws_bedrock_data_automation_mcp_server.helpers.Path.exists',
            return_value=False,
        ):
            with pytest.raises(
                ValueError, match='Asset at path /path/to/asset.pdf does not exist'
            ):
                await upload_to_s3('/path/to/asset.pdf')


def test_get_bucket_and_key_from_s3_uri():
    """Test the get_bucket_and_key_from_s3_uri function."""
    bucket, key = get_bucket_and_key_from_s3_uri('s3://test-bucket/path/to/file.txt')
    assert bucket == 'test-bucket'
    assert key == 'path/to/file.txt'


@pytest.mark.asyncio
async def test_download_from_s3():
    """Test the download_from_s3 function."""
    mock_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({'key': 'value'}).encode('utf-8')
    mock_client.get_object.return_value = {'Body': mock_body}

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_s3_client',
        return_value=mock_client,
    ):
        result = await download_from_s3('s3://test-bucket/path/to/file.json')
        assert result == {'key': 'value'}
        mock_client.get_object.assert_called_once_with(
            Bucket='test-bucket', Key='path/to/file.json'
        )


@pytest.mark.asyncio
async def test_download_from_s3_error():
    """Test the download_from_s3 function when an error occurs."""
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception('Test error')

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_s3_client',
        return_value=mock_client,
    ):
        result = await download_from_s3('s3://test-bucket/path/to/file.json')
        assert result is None


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results():
    """Test the invoke_data_automation_and_get_results function."""
    # Mock all the necessary functions and responses
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses to simulate job completion
                mock_runtime.get_data_automation_status.side_effect = [
                    {'status': 'InProgress'},
                    {
                        'status': 'Success',
                        'outputConfiguration': {'s3Uri': 's3://test-bucket/mcp/test-output'},
                    },
                ]
                mock_get_runtime.return_value = mock_runtime

                # Mock the asyncio.sleep to avoid actual waiting
                with patch('asyncio.sleep', new=AsyncMock()):
                    # Mock the download_from_s3 function to return job metadata and outputs
                    with patch(
                        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.download_from_s3',
                        new=AsyncMock(
                            side_effect=[
                                # First call returns job metadata
                                {
                                    'output_metadata': [
                                        {
                                            'segment_metadata': [
                                                {
                                                    'standard_output_path': 's3://test-bucket/standard-output.json',
                                                    'custom_output_path': 's3://test-bucket/custom-output.json',
                                                }
                                            ]
                                        }
                                    ]
                                },
                                # Second call returns standard output
                                {'standard': 'output'},
                                # Third call returns custom output
                                {'custom': 'output'},
                            ]
                        ),
                    ):
                        result = await invoke_data_automation_and_get_results(
                            '/path/to/asset.pdf', 'test-project-arn'
                        )

                        assert result == {
                            'standardOutput': {'standard': 'output'},
                            'customOutput': {'custom': 'output'},
                        }

                        # Verify the invoke_data_automation_async call
                        mock_runtime.invoke_data_automation_async.assert_called_once_with(
                            inputConfiguration={'s3Uri': 's3://test-bucket/mcp/test-uuid.pdf'},
                            outputConfiguration={'s3Uri': 's3://test-bucket/mcp/test-output'},
                            dataAutomationConfiguration={
                                'dataAutomationProjectArn': 'test-project-arn'
                            },
                            dataAutomationProfileArn='arn:aws:bedrock:us-east-1:123456789012:data-automation-profile/us.data-automation-v1',
                        )


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_default_project():
    """Test the invoke_data_automation_and_get_results function with default project."""
    # Mock all the necessary functions and responses
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses to simulate job completion
                mock_runtime.get_data_automation_status.side_effect = [
                    {
                        'status': 'Success',
                        'outputConfiguration': {'s3Uri': 's3://test-bucket/mcp/test-output'},
                    }
                ]
                mock_get_runtime.return_value = mock_runtime

                # Mock the download_from_s3 function to return job metadata and outputs
                with patch(
                    'awslabs.aws_bedrock_data_automation_mcp_server.helpers.download_from_s3',
                    new=AsyncMock(
                        side_effect=[
                            # First call returns job metadata
                            {
                                'output_metadata': [
                                    {
                                        'segment_metadata': [
                                            {
                                                'standard_output_path': 's3://test-bucket/standard-output.json',
                                                'custom_output_path': 's3://test-bucket/custom-output.json',
                                            }
                                        ]
                                    }
                                ]
                            },
                            # Second call returns standard output
                            {'standard': 'output'},
                            # Third call returns custom output
                            {'custom': 'output'},
                        ]
                    ),
                ):
                    result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')

                    assert result == {
                        'standardOutput': {'standard': 'output'},
                        'customOutput': {'custom': 'output'},
                    }

                    # Verify the invoke_data_automation_async call with default project ARN
                    mock_runtime.invoke_data_automation_async.assert_called_once_with(
                        inputConfiguration={'s3Uri': 's3://test-bucket/mcp/test-uuid.pdf'},
                        outputConfiguration={'s3Uri': 's3://test-bucket/mcp/test-output'},
                        dataAutomationConfiguration={
                            'dataAutomationProjectArn': 'arn:aws:bedrock:us-east-1:aws:data-automation-project/public-default'
                        },
                        dataAutomationProfileArn='arn:aws:bedrock:us-east-1:123456789012:data-automation-profile/us.data-automation-v1',
                    )


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_no_profile_arn():
    """Test the invoke_data_automation_and_get_results function when profile ARN is not available."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(os.environ, {'AWS_BUCKET_NAME': 'test-bucket'}, clear=True):
            with pytest.raises(
                ValueError,
                match='Could not determine profile ARN. Make sure AWS_ACCOUNT_ID is set.',
            ):
                await invoke_data_automation_and_get_results('/path/to/asset.pdf')


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_no_bucket():
    """Test the invoke_data_automation_and_get_results function when bucket name is not set."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(os.environ, {'AWS_ACCOUNT_ID': '123456789012'}, clear=True):
            with pytest.raises(
                ValueError, match='AWS_BUCKET_NAME environment variable is not set'
            ):
                await invoke_data_automation_and_get_results('/path/to/asset.pdf')


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_job_failed():
    """Test the invoke_data_automation_and_get_results function when the job fails."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses to simulate job failure
                mock_runtime.get_data_automation_status.return_value = {'status': 'FAILED'}
                mock_get_runtime.return_value = mock_runtime

                result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')
                assert result is None


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_no_output_uri():
    """Test the invoke_data_automation_and_get_results function when there's no output URI."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses with missing output URI
                mock_runtime.get_data_automation_status.return_value = {
                    'status': 'Success',
                    'outputConfiguration': {},
                }
                mock_get_runtime.return_value = mock_runtime

                result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')
                assert result is None


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_no_job_metadata():
    """Test the invoke_data_automation_and_get_results function when job metadata is not available."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses
                mock_runtime.get_data_automation_status.return_value = {
                    'status': 'Success',
                    'outputConfiguration': {'s3Uri': 's3://test-bucket/mcp/test-output'},
                }
                mock_get_runtime.return_value = mock_runtime

                # Mock download_from_s3 to return None for job metadata
                with patch(
                    'awslabs.aws_bedrock_data_automation_mcp_server.helpers.download_from_s3',
                    new=AsyncMock(return_value=None),
                ):
                    result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')
                    assert result is None


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_invalid_metadata():
    """Test the invoke_data_automation_and_get_results function with invalid metadata structure."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses
                mock_runtime.get_data_automation_status.return_value = {
                    'status': 'Success',
                    'outputConfiguration': {'s3Uri': 's3://test-bucket/mcp/test-output'},
                }
                mock_get_runtime.return_value = mock_runtime

                # Mock download_from_s3 to return invalid metadata structure
                with patch(
                    'awslabs.aws_bedrock_data_automation_mcp_server.helpers.download_from_s3',
                    new=AsyncMock(return_value={'invalid': 'structure'}),
                ):
                    result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')
                    assert result is None


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_no_output_paths():
    """Test the invoke_data_automation_and_get_results function when no output paths are available."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses
                mock_runtime.get_data_automation_status.return_value = {
                    'status': 'Success',
                    'outputConfiguration': {'s3Uri': 's3://test-bucket/mcp/test-output'},
                }
                mock_get_runtime.return_value = mock_runtime

                # Mock download_from_s3 to return metadata with empty output paths
                with patch(
                    'awslabs.aws_bedrock_data_automation_mcp_server.helpers.download_from_s3',
                    new=AsyncMock(
                        return_value={
                            'output_metadata': [
                                {
                                    'segment_metadata': [
                                        {'standard_output_path': None, 'custom_output_path': None}
                                    ]
                                }
                            ]
                        }
                    ),
                ):
                    result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')
                    assert result is None


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_only_standard_output():
    """Test the invoke_data_automation_and_get_results function with only standard output."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses
                mock_runtime.get_data_automation_status.return_value = {
                    'status': 'Success',
                    'outputConfiguration': {'s3Uri': 's3://test-bucket/mcp/test-output'},
                }
                mock_get_runtime.return_value = mock_runtime

                # Mock download_from_s3 to return metadata with only standard output path
                with patch(
                    'awslabs.aws_bedrock_data_automation_mcp_server.helpers.download_from_s3',
                    new=AsyncMock(
                        side_effect=[
                            {
                                'output_metadata': [
                                    {
                                        'segment_metadata': [
                                            {
                                                'standard_output_path': 's3://test-bucket/standard-output.json',
                                                'custom_output_path': None,
                                            }
                                        ]
                                    }
                                ]
                            },
                            {'standard': 'output'},
                        ]
                    ),
                ):
                    result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')
                    assert result == {
                        'standardOutput': {'standard': 'output'},
                        'customOutput': None,
                    }


@pytest.mark.asyncio
async def test_invoke_data_automation_and_get_results_only_custom_output():
    """Test the invoke_data_automation_and_get_results function with only custom output."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.helpers.upload_to_s3',
        new=AsyncMock(return_value='s3://test-bucket/mcp/test-uuid.pdf'),
    ):
        with patch.dict(
            os.environ, {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCOUNT_ID': '123456789012'}
        ):
            with patch(
                'awslabs.aws_bedrock_data_automation_mcp_server.helpers.get_bedrock_data_automation_runtime_client'
            ) as mock_get_runtime:
                mock_runtime = MagicMock()
                mock_runtime.invoke_data_automation_async.return_value = {
                    'invocationArn': 'test-invocation-arn'
                }

                # Mock the get_data_automation_status responses
                mock_runtime.get_data_automation_status.return_value = {
                    'status': 'Success',
                    'outputConfiguration': {'s3Uri': 's3://test-bucket/mcp/test-output'},
                }
                mock_get_runtime.return_value = mock_runtime

                # Mock download_from_s3 to return metadata with only custom output path
                with patch(
                    'awslabs.aws_bedrock_data_automation_mcp_server.helpers.download_from_s3',
                    new=AsyncMock(
                        side_effect=[
                            {
                                'output_metadata': [
                                    {
                                        'segment_metadata': [
                                            {
                                                'standard_output_path': None,
                                                'custom_output_path': 's3://test-bucket/custom-output.json',
                                            }
                                        ]
                                    }
                                ]
                            },
                            {'custom': 'output'},
                        ]
                    ),
                ):
                    result = await invoke_data_automation_and_get_results('/path/to/asset.pdf')
                    assert result == {'standardOutput': None, 'customOutput': {'custom': 'output'}}
