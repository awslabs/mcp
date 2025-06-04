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
"""Tests for the update_webapp_frontend module."""

import pytest
from awslabs.aws_serverless_mcp_server.tools.webapps.update_webapp_frontend import (
    UpdateFrontendTool,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, mock_open, patch


class TestUpdateWebappFrontend:
    """Tests for the update_webapp_frontend module."""

    @pytest.mark.asyncio
    async def test_get_all_files(self):
        """Test get_all_files function."""

        def mock_listdir(path):
            if path == '/dir/source':
                return ['file1.txt', 'file2.html', 'subdir']
            elif path == '/dir/source/subdir':
                return ['file3.js']
            return []

        def mock_isdir(path):
            return 'subdir' in path and not path.endswith(('.txt', '.html', '.js'))

        # Use a simple join function that doesn't call os.path.join recursively
        def mock_join(dir_path, file):
            if dir_path.endswith('/'):
                return f'{dir_path}{file}'
            return f'{dir_path}/{file}'

        with (
            patch('os.listdir', side_effect=mock_listdir),
            patch('os.path.isdir', side_effect=mock_isdir),
            patch('os.path.join', side_effect=mock_join),
        ):
            files = await UpdateFrontendTool(MagicMock())._get_all_files('/dir/source')

            # Check that all files were found
            assert len(files) == 3
            assert '/dir/source/file1.txt' in files
            assert '/dir/source/file2.html' in files
            assert '/dir/source/subdir/file3.js' in files

    @pytest.mark.asyncio
    async def test_get_all_files_empty_directory(self):
        """Test get_all_files with an empty directory."""
        with patch('os.listdir', return_value=[]):
            files = await UpdateFrontendTool(MagicMock())._get_all_files('/dir/empty')
            assert len(files) == 0

    @pytest.mark.asyncio
    async def test_get_all_files_with_exception(self):
        """Test get_all_files with an exception."""
        with patch('os.listdir', side_effect=Exception('Test error')):
            with pytest.raises(Exception, match='Test error'):
                await UpdateFrontendTool(MagicMock())._get_all_files('/dir/source')

    @pytest.mark.asyncio
    async def test_upload_file_to_s3(self):
        """Test upload_file_to_s3 function."""
        mock_s3_client = MagicMock()

        with (
            patch('builtins.open', mock_open(read_data=b'test content')),
            patch('mimetypes.guess_type', return_value=('text/plain', None)),
        ):
            await UpdateFrontendTool(MagicMock())._upload_file_to_s3(
                mock_s3_client, '/dir/source/file.txt', 'test-bucket', '/dir/source'
            )

            # Verify S3 client was called with correct parameters
            mock_s3_client.put_object.assert_called_once()
            call_args = mock_s3_client.put_object.call_args[1]
            assert call_args['Bucket'] == 'test-bucket'
            assert call_args['Key'] == 'file.txt'
            assert call_args['Body'] == b'test content'
            assert call_args['ContentType'] == 'text/plain'

    @pytest.mark.asyncio
    async def test_upload_file_to_s3_with_nested_path(self):
        """Test upload_file_to_s3 with a nested file path."""
        mock_s3_client = MagicMock()

        with (
            patch('builtins.open', mock_open(read_data=b'test content')),
            patch('mimetypes.guess_type', return_value=('application/javascript', None)),
        ):
            await UpdateFrontendTool(MagicMock())._upload_file_to_s3(
                mock_s3_client, '/dir/source/subdir/file.js', 'test-bucket', '/dir/source'
            )

            # Verify S3 client was called with correct parameters
            mock_s3_client.put_object.assert_called_once()
            call_args = mock_s3_client.put_object.call_args[1]
            assert call_args['Bucket'] == 'test-bucket'
            assert call_args['Key'] == 'subdir/file.js'
            assert call_args['Body'] == b'test content'
            assert call_args['ContentType'] == 'application/javascript'

    @pytest.mark.asyncio
    async def test_upload_file_to_s3_with_exception(self):
        """Test upload_file_to_s3 with an exception."""
        mock_s3_client = MagicMock()
        mock_s3_client.put_object.side_effect = Exception('Test error')

        with (
            patch('builtins.open', mock_open(read_data=b'test content')),
            patch('mimetypes.guess_type', return_value=('text/plain', None)),
            pytest.raises(Exception, match='Test error'),
        ):
            await UpdateFrontendTool(MagicMock())._upload_file_to_s3(
                mock_s3_client, '/dir/source/file.txt', 'test-bucket', '/dir/source'
            )

    @pytest.mark.asyncio
    async def test_sync_directory_to_s3(self):
        """Test sync_directory_to_s3 function."""
        mock_s3_client = MagicMock()

        # Mock S3 objects
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'file1.txt'},
                {'Key': 'file2.html'},
                {'Key': 'old-file.css'},  # This file should be deleted
            ],
            'IsTruncated': False,
        }

        # Mock local files
        local_files = [
            '/dir/source/file1.txt',
            '/dir/source/file2.html',
            '/dir/source/new-file.js',
        ]

        with (
            patch.object(UpdateFrontendTool, '_get_all_files', return_value=local_files),
            patch.object(UpdateFrontendTool, '_upload_file_to_s3') as mock_upload,
        ):
            await UpdateFrontendTool(MagicMock())._sync_directory_to_s3(
                mock_s3_client, '/dir/source', 'test-bucket'
            )

            # Verify all local files were uploaded
            assert mock_upload.call_count == 3

            # Verify old file was deleted
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket='test-bucket', Key='old-file.css'
            )

    @pytest.mark.asyncio
    async def test_sync_directory_to_s3_empty_s3(self):
        """Test sync_directory_to_s3 with an empty S3 bucket."""
        mock_s3_client = MagicMock()

        # Mock empty S3 bucket
        mock_s3_client.list_objects_v2.return_value = {}

        # Mock local files
        local_files = ['/dir/source/file1.txt', '/dir/source/file2.html']

        with (
            patch.object(UpdateFrontendTool, '_get_all_files', return_value=local_files),
            patch.object(UpdateFrontendTool, '_upload_file_to_s3') as mock_upload,
        ):
            await UpdateFrontendTool(MagicMock())._sync_directory_to_s3(
                mock_s3_client, '/dir/source', 'test-bucket'
            )

            # Verify all local files were uploaded
            assert mock_upload.call_count == 2

            # Verify no files were deleted
            mock_s3_client.delete_object.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_directory_to_s3_pagination(self):
        """Test sync_directory_to_s3 with S3 pagination."""
        mock_s3_client = MagicMock()

        # Mock paginated S3 responses
        mock_s3_client.list_objects_v2.side_effect = [
            {
                'Contents': [{'Key': 'file1.txt'}],
                'IsTruncated': True,
                'NextContinuationToken': 'token',
            },
            {
                'Contents': [{'Key': 'file2.html'}],
                'IsTruncated': False,
            },
        ]

        # Mock local files
        local_files = ['/dir/source/file1.txt', '/dir/source/new-file.js']

        with (
            patch.object(UpdateFrontendTool, '_get_all_files', return_value=local_files),
            patch.object(UpdateFrontendTool, '_upload_file_to_s3') as mock_upload,
        ):
            await UpdateFrontendTool(MagicMock())._sync_directory_to_s3(
                mock_s3_client, '/dir/source', 'test-bucket'
            )

            # Verify all local files were uploaded
            assert mock_upload.call_count == 2

            # Verify file2.html was deleted (not in local files)
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket='test-bucket', Key='file2.html'
            )

            # Verify pagination was handled correctly
            assert mock_s3_client.list_objects_v2.call_count == 2
            assert (
                mock_s3_client.list_objects_v2.call_args_list[1][1]['ContinuationToken'] == 'token'
            )

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_built_assets_not_found(self):
        """Test update_webapp_frontend with non-existent built assets path."""
        with patch('os.path.exists', return_value=False):
            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region='us-east-1',
            )

            assert result['status'] == 'error'
            assert 'Built assets path not found' in result['message']

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_stack_not_found(self):
        """Test update_webapp_frontend with non-existent CloudFormation stack."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.side_effect = ClientError(
            {'Error': {'Code': 'ValidationError', 'Message': 'Stack does not exist'}},
            'DescribeStacks',
        )

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
        }.get(service, MagicMock())

        with (
            patch('os.path.exists', return_value=True),
            patch('boto3.Session', return_value=mock_session),
        ):
            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region='us-east-1',
            )

            assert result['status'] == 'error'
            assert 'does not exist' in result['message']

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_no_website_bucket(self):
        """Test update_webapp_frontend with no WebsiteBucket output in stack."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {'Outputs': [{'OutputKey': 'ApiUrl', 'OutputValue': 'https://example.com'}]}
            ]
        }

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
        }.get(service, MagicMock())

        with (
            patch('os.path.exists', return_value=True),
            patch('boto3.Session', return_value=mock_session),
        ):
            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region='us-east-1',
            )
            assert result['status'] == 'error'
            assert 'Could not find WebsiteBucket output' in result['message']

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_success_no_cloudfront(self):
        """Test successful update_webapp_frontend without CloudFront."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [{'Outputs': [{'OutputKey': 'WebsiteBucket', 'OutputValue': 'test-bucket'}]}]
        }

        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client,
        }.get(service, MagicMock())

        with (
            patch('os.path.exists', return_value=True),
            patch('boto3.Session', return_value=mock_session),
            patch.object(UpdateFrontendTool, '_sync_directory_to_s3') as mock_sync,
        ):
            result = await UpdateFrontendTool(MagicMock()).update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region='us-east-1',
            )

            # Verify sync was called
            mock_sync.assert_called_once_with(mock_s3_client, '/dir/build', 'test-bucket')

            # Verify CloudFront invalidation was not created
            mock_cloudfront_client.create_invalidation.assert_not_called()

            # Verify success response
            assert result['status'] == 'success'
            assert 'Frontend assets updated successfully' in result['message']
            assert 'No CloudFront distribution found' in result['content'][2]['text']

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_success_with_cloudfront(self):
        """Test successful update_webapp_frontend with CloudFront."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'Outputs': [
                        {'OutputKey': 'WebsiteBucket', 'OutputValue': 'test-bucket'},
                        {
                            'OutputKey': 'CloudFrontDistributionId',
                            'OutputValue': 'ABCDEF12345',  # pragma: allowlist secret
                        },
                    ]
                }
            ]
        }

        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client,
        }.get(service, MagicMock())

        with (
            patch('os.path.exists', return_value=True),
            patch('boto3.Session', return_value=mock_session),
            patch.object(UpdateFrontendTool, '_sync_directory_to_s3') as mock_sync,
            patch('datetime.datetime') as mock_datetime,
        ):
            # Mock timestamp for invalidation
            mock_datetime.now.return_value.timestamp.return_value = 1234567890

            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region='us-east-1',
            )

            # Verify sync was called
            mock_sync.assert_called_once_with(mock_s3_client, '/dir/build', 'test-bucket')

            # Verify CloudFront invalidation was created
            mock_cloudfront_client.create_invalidation.assert_called_once()
            invalidation_args = mock_cloudfront_client.create_invalidation.call_args[1]
            assert invalidation_args['DistributionId'] == 'ABCDEF12345'  # pragma: allowlist secret
            assert invalidation_args['InvalidationBatch']['Paths']['Items'] == ['/*']
            assert invalidation_args['InvalidationBatch']['CallerReference'] == '1234567890'

            # Verify success response
            assert result['status'] == 'success'
            assert 'Frontend assets updated successfully' in result['message']
            assert (
                'CloudFront cache invalidation has been initiated' in result['content'][2]['text']
            )

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_success_with_cloudfront_url(self):
        """Test successful update_webapp_frontend with CloudFront URL but no ID."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'Outputs': [
                        {'OutputKey': 'WebsiteBucket', 'OutputValue': 'test-bucket'},
                        {
                            'OutputKey': 'CloudFrontURL',
                            'OutputValue': 'https://d123.cloudfront.net',
                        },
                    ]
                }
            ]
        }

        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client,
        }.get(service, MagicMock())

        with (
            patch('os.path.exists', return_value=True),
            patch('boto3.Session', return_value=mock_session),
            patch.object(UpdateFrontendTool, '_sync_directory_to_s3') as mock_sync,
        ):
            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region='us-east-1',
            )
            # Verify sync was called
            mock_sync.assert_called_once_with(mock_s3_client, '/dir/build', 'test-bucket')

            # Verify CloudFront invalidation was not created (no distribution ID)
            mock_cloudfront_client.create_invalidation.assert_not_called()

            # Verify success response
            assert result['status'] == 'success'
            assert 'Frontend assets updated successfully' in result['message']
            assert "couldn't create CloudFront invalidation" in result['message']

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_sync_error(self):
        """Test update_webapp_frontend with sync error."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [{'Outputs': [{'OutputKey': 'WebsiteBucket', 'OutputValue': 'test-bucket'}]}]
        }

        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client,
        }.get(service, MagicMock())

        with (
            patch('os.path.exists', return_value=True),
            patch('boto3.Session', return_value=mock_session),
            patch.object(
                UpdateFrontendTool, '_sync_directory_to_s3', side_effect=Exception('Sync error')
            ),
        ):
            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region='us-east-1',
            )
            # Verify error response
            assert result['status'] == 'error'
            assert 'Failed to update frontend assets' in result['message']
            assert 'Sync error' in result['message']

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_relative_path(self):
        """Test update_webapp_frontend with relative built assets path."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [{'Outputs': [{'OutputKey': 'WebsiteBucket', 'OutputValue': 'test-bucket'}]}]
        }

        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client,
        }.get(service, MagicMock())

        with (
            patch('os.path.exists', return_value=True),
            patch('os.path.isabs', return_value=False),
            patch('os.path.join', return_value='/dir/test-project/build'),
            patch('boto3.Session', return_value=mock_session),
            patch.object(UpdateFrontendTool, '_sync_directory_to_s3') as mock_sync,
        ):
            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='build',  # Relative path
                invalidate_cache=True,
                region='us-east-1',
            )

            # Verify sync was called with absolute path
            mock_sync.assert_called_once_with(
                mock_s3_client, '/dir/test-project/build', 'test-bucket'
            )

            # Verify success response
            assert result['status'] == 'success'
            assert 'Frontend assets updated successfully' in result['message']

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_no_region(self):
        """Test update_webapp_frontend without region."""
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [{'Outputs': [{'OutputKey': 'WebsiteBucket', 'OutputValue': 'test-bucket'}]}]
        }

        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            'cloudformation': mock_cfn_client,
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client,
        }[service]

        with (
            patch('os.path.exists', return_value=True),
            patch('boto3.Session', return_value=mock_session) as mock_session_constructor,
            patch.object(UpdateFrontendTool, '_sync_directory_to_s3') as mock_sync,
        ):
            tool = UpdateFrontendTool(MagicMock())
            result = await tool.update_webapp_frontend_tool(
                AsyncMock(),
                project_name='test-project',
                project_root='/dir/test-project',
                built_assets_path='/dir/build',
                invalidate_cache=True,
                region=None,  # No region
            )

            # Verify boto3.Session was called without region
            assert mock_session_constructor.call_count == 3

            # Verify sync was called
            mock_sync.assert_called_once_with(mock_s3_client, '/dir/build', 'test-bucket')

            # Verify success response
            assert result['status'] == 'success'
            assert 'Frontend assets updated successfully' in result['message']
