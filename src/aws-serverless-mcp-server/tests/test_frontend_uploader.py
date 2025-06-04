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
"""Tests for the frontend_uploader module."""

import os
import pytest
from awslabs.aws_serverless_mcp_server.models import (
    DeployWebAppRequest,
    FrontendConfiguration,
)
from awslabs.aws_serverless_mcp_server.tools.webapps.utils.frontend_uploader import (
    upload_frontend_assets,
    upload_to_s3,
)
from botocore.exceptions import BotoCoreError, ClientError
from unittest.mock import MagicMock, patch


class TestFrontendUploader:
    """Tests for the frontend_uploader module."""

    @pytest.mark.asyncio
    async def test_upload_frontend_assets_no_frontend_config(self):
        """Test upload_frontend_assets with no frontend configuration."""
        # Create a mock request without frontend configuration
        request = DeployWebAppRequest(
            region='us-east-1',
            backend_configuration=None,
            deployment_type='backend',
            project_name='test-project',
            project_root='/dir/test-project',
            frontend_configuration=None,
        )

        deploy_result = {'outputs': {'WebsiteBucket': 'test-bucket'}}

        # Should return without error when no frontend config
        await upload_frontend_assets(request, deploy_result)

    @pytest.mark.asyncio
    async def test_upload_frontend_assets_no_built_assets_path(self):
        """Test upload_frontend_assets with no built assets path."""
        frontend_config = FrontendConfiguration(
            built_assets_path='',
            framework='react',
            index_document='index.html',
            error_document='error.html',
            custom_domain='example.com',
            certificate_arn='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        )

        request = DeployWebAppRequest(
            region='us-east-1',
            backend_configuration=None,
            deployment_type='frontend',
            project_name='test-project',
            project_root='/dir/test-project',
            frontend_configuration=frontend_config,
        )

        deploy_result = {'outputs': {'WebsiteBucket': 'test-bucket'}}

        # Should return without error when no built assets path
        await upload_frontend_assets(request, deploy_result)

    @pytest.mark.asyncio
    async def test_upload_frontend_assets_no_bucket_name(self):
        """Test upload_frontend_assets with no bucket name in deploy result."""
        frontend_config = FrontendConfiguration(
            built_assets_path='/dir/build',
            framework='react',
            index_document='index.html',
            error_document='error.html',
            custom_domain='example.com',
            certificate_arn='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        )

        request = DeployWebAppRequest(
            region='us-east-1',
            backend_configuration=None,
            deployment_type='frontend',
            project_name='test-project',
            project_root='/dir/test-project',
            frontend_configuration=frontend_config,
        )

        deploy_result = {'outputs': {}}

        with pytest.raises(Exception, match='S3 bucket name not found in deployment outputs'):
            await upload_frontend_assets(request, deploy_result)

    @pytest.mark.asyncio
    async def test_upload_frontend_assets_path_not_exists(self):
        """Test upload_frontend_assets with non-existent built assets path."""
        frontend_config = FrontendConfiguration(
            built_assets_path='/dir/nonexistent',
            framework='react',
            index_document='index.html',
            error_document='error.html',
            custom_domain='example.com',
            certificate_arn='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        )

        request = DeployWebAppRequest(
            deployment_type='frontend',
            project_name='test-project',
            project_root='/dir/test-project',
            frontend_configuration=frontend_config,
            region='us-east-1',
            backend_configuration=None,
        )

        deploy_result = {'outputs': {'WebsiteBucket': 'test-bucket'}}

        with patch('os.path.exists', return_value=False):
            with pytest.raises(Exception, match='Built assets path not found: /dir/nonexistent'):
                await upload_frontend_assets(request, deploy_result)

    @pytest.mark.asyncio
    async def test_upload_frontend_assets_success(self):
        """Test successful upload_frontend_assets."""
        frontend_config = FrontendConfiguration(
            built_assets_path='/dir/build',
            framework='react',
            index_document='index.html',
            error_document='error.html',
            custom_domain='example.com',
            certificate_arn='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        )

        request = DeployWebAppRequest(
            deployment_type='frontend',
            project_name='test-project',
            project_root='/dir/test-project',
            region='us-east-1',
            frontend_configuration=frontend_config,
            backend_configuration=None,
        )

        deploy_result = {'outputs': {'WebsiteBucket': 'test-bucket'}}

        with (
            patch('os.path.exists', return_value=True),
            patch(
                'awslabs.aws_serverless_mcp_server.tools.webapps.utils.frontend_uploader.upload_to_s3'
            ) as mock_upload,
        ):
            await upload_frontend_assets(request, deploy_result)
            mock_upload.assert_called_once_with('/dir/build', 'test-bucket', 'us-east-1')

    @pytest.mark.asyncio
    async def test_upload_frontend_assets_upload_failure(self):
        """Test upload_frontend_assets with upload failure."""
        frontend_config = FrontendConfiguration(
            built_assets_path='/dir/build',
            framework='react',
            index_document='index.html',
            error_document='error.html',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/abcd1234',
            custom_domain='example.com',
        )

        request = DeployWebAppRequest(
            region='us-east-1',
            deployment_type='frontend',
            project_name='test-project',
            project_root='/dir/test-project',
            frontend_configuration=frontend_config,
            backend_configuration=None,
        )

        deploy_result = {'outputs': {'WebsiteBucket': 'test-bucket'}}

        with (
            patch('os.path.exists', return_value=True),
            patch(
                'awslabs.aws_serverless_mcp_server.tools.webapps.utils.frontend_uploader.upload_to_s3',
                side_effect=Exception('Upload failed'),
            ),
        ):
            with pytest.raises(Exception, match='Upload failed'):
                await upload_frontend_assets(request, deploy_result)

    @pytest.mark.asyncio
    async def test_upload_to_s3_success(self):
        """Test successful upload_to_s3."""
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client

        # Mock file system
        test_files = [
            ('/dir/source', ['subdir'], ['file1.txt', 'file2.html']),
            ('/dir/source/subdir', [], ['file3.js']),
        ]

        def mock_relpath(path, start):
            """Mock os.path.relpath to return relative paths correctly."""
            if path.startswith(start):
                return path[len(start) :].lstrip('/')
            return path

        with (
            patch('boto3.Session', return_value=mock_session),
            patch('os.walk', return_value=test_files),
            patch('os.path.join', side_effect=os.path.join),
            patch('os.path.relpath', side_effect=mock_relpath),
        ):
            await upload_to_s3('/dir/source', 'test-bucket', 'us-east-1')

            # Verify S3 client was created with correct region
            mock_session.client.assert_called_once_with('s3')

            # Verify files were uploaded
            expected_calls = [
                ('/dir/source/file1.txt', 'test-bucket', 'file1.txt'),
                ('/dir/source/file2.html', 'test-bucket', 'file2.html'),
                ('/dir/source/subdir/file3.js', 'test-bucket', 'subdir/file3.js'),
            ]

            assert mock_s3_client.upload_file.call_count == 3
            for i, call in enumerate(mock_s3_client.upload_file.call_args_list):
                args = call[0]
                assert args == expected_calls[i]

    @pytest.mark.asyncio
    async def test_upload_to_s3_no_region(self):
        """Test upload_to_s3 without region."""
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client

        test_files = [('root', [], ['file1.txt'])]

        with (
            patch('boto3.Session', return_value=mock_session),
            patch('os.walk', return_value=test_files),
            patch('os.path.join', side_effect=lambda *args: '/'.join(args)),
            patch(
                'os.path.relpath', side_effect=lambda path, start: path.replace(start + '/', '')
            ),
        ):
            await upload_to_s3('/dir/source', 'test-bucket')

            # Verify Session was created without region
            mock_session.client.assert_called_once_with('s3')

    @pytest.mark.asyncio
    async def test_upload_to_s3_client_error(self):
        """Test upload_to_s3 with ClientError."""
        mock_s3_client = MagicMock()
        mock_s3_client.upload_file.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}}, 'upload_file'
        )
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client

        test_files = [('root', [], ['file1.txt'])]

        with (
            patch('boto3.Session', return_value=mock_session),
            patch('os.walk', return_value=test_files),
            patch('os.path.join', side_effect=lambda *args: '/'.join(args)),
            patch(
                'os.path.relpath', side_effect=lambda path, start: path.replace(start + '/', '')
            ),
        ):
            with pytest.raises(ClientError):
                await upload_to_s3('/dir/source', 'test-bucket', 'us-east-1')

    @pytest.mark.asyncio
    async def test_upload_to_s3_botocore_error(self):
        """Test upload_to_s3 with BotoCoreError."""
        mock_s3_client = MagicMock()
        mock_s3_client.upload_file.side_effect = BotoCoreError()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client

        test_files = [('root', [], ['file1.txt'])]

        with (
            patch('boto3.Session', return_value=mock_session),
            patch('os.walk', return_value=test_files),
            patch('os.path.join', side_effect=lambda *args: '/'.join(args)),
            patch(
                'os.path.relpath', side_effect=lambda path, start: path.replace(start + '/', '')
            ),
        ):
            with pytest.raises(BotoCoreError):
                await upload_to_s3('/dir/source', 'test-bucket', 'us-east-1')

    @pytest.mark.asyncio
    async def test_upload_to_s3_empty_directory(self):
        """Test upload_to_s3 with empty directory."""
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client

        # Empty directory
        test_files = [('root', [], [])]

        with (
            patch('boto3.Session', return_value=mock_session),
            patch('os.walk', return_value=test_files),
        ):
            await upload_to_s3('/dir/source', 'test-bucket', 'us-east-1')

            # No files should be uploaded
            mock_s3_client.upload_file.assert_not_called()
