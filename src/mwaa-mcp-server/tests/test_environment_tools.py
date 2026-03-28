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
# ruff: noqa: D101, D102, D103
"""Tests for the MWAA environment management tools."""

import json
import pytest
from awslabs.mwaa_mcp_server.environment_tools import EnvironmentTools
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture
def handler_readonly(mock_mcp):
    """Create EnvironmentTools handler in read-only mode."""
    return EnvironmentTools(mock_mcp, allow_write=False)


@pytest.fixture
def handler_writable(mock_mcp):
    """Create EnvironmentTools handler with write access."""
    return EnvironmentTools(mock_mcp, allow_write=True)


class TestListEnvironments:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_list_environments_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'Environments': ['env-1', 'env-2']},
            {'Environments': ['env-3']},
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_environments(mock_ctx)

        assert not result.isError
        assert len(result.content) == 2
        data = json.loads(result.content[1].text)
        assert data['environments'] == ['env-1', 'env-2', 'env-3']

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_list_environments_empty(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Environments': []}]
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_environments(mock_ctx)

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert data['environments'] == []

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_list_environments_client_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'ListEnvironments',
        )
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_environments(mock_ctx)

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_list_environments_with_region(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Environments': ['env-eu']}]
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_environments(
            mock_ctx, region='eu-west-1', profile_name='test-profile'
        )

        assert not result.isError
        mock_get_client.assert_called_once_with(
            region_name='eu-west-1', profile_name='test-profile'
        )


class TestGetEnvironment:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_get_environment_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.get_environment.return_value = {
            'Environment': {
                'Name': 'test-env',
                'Status': 'AVAILABLE',
                'AirflowVersion': '2.8.1',
            }
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_environment(mock_ctx, environment_name='test-env')

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert data['Name'] == 'test-env'
        assert data['Status'] == 'AVAILABLE'

    @pytest.mark.asyncio
    async def test_get_environment_invalid_name(self, handler_readonly, mock_ctx):
        result = await handler_readonly.get_environment(mock_ctx, environment_name='123-invalid')

        assert result.isError
        assert 'Invalid environment name' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_get_environment_not_found(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.get_environment.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetEnvironment',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_environment(mock_ctx, environment_name='nonexistent')

        assert result.isError
        assert 'AWS API error' in result.content[0].text


class TestCreateEnvironment:
    @pytest.mark.asyncio
    async def test_create_environment_blocked_readonly(self, handler_readonly, mock_ctx):
        result = await handler_readonly.create_environment(
            mock_ctx,
            environment_name='new-env',
            dag_s3_path='dags/',
            execution_role_arn='arn:aws:iam::123456789012:role/mwaa-role',
            source_bucket_arn='arn:aws:s3:::my-bucket',
            network_configuration={
                'SecurityGroupIds': ['sg-123'],
                'SubnetIds': ['subnet-1', 'subnet-2'],
            },
        )

        assert result.isError
        assert '--allow-write' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_create_environment_success(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.create_environment.return_value = {
            'Arn': 'arn:aws:airflow:us-east-1:123456789012:environment/new-env'
        }
        mock_get_client.return_value = mock_client

        result = await handler_writable.create_environment(
            mock_ctx,
            environment_name='new-env',
            dag_s3_path='dags/',
            execution_role_arn='arn:aws:iam::123456789012:role/mwaa-role',
            source_bucket_arn='arn:aws:s3:::my-bucket',
            network_configuration={
                'SecurityGroupIds': ['sg-123'],
                'SubnetIds': ['subnet-1', 'subnet-2'],
            },
        )

        assert not result.isError
        assert 'creation initiated' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_create_environment_with_optional_params(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.create_environment.return_value = {'Arn': 'arn:aws:airflow:...'}
        mock_get_client.return_value = mock_client

        result = await handler_writable.create_environment(
            mock_ctx,
            environment_name='new-env',
            dag_s3_path='dags/',
            execution_role_arn='arn:aws:iam::123456789012:role/mwaa-role',
            source_bucket_arn='arn:aws:s3:::my-bucket',
            network_configuration={
                'SecurityGroupIds': ['sg-123'],
                'SubnetIds': ['subnet-1', 'subnet-2'],
            },
            airflow_version='2.8.1',
            environment_class='mw1.medium',
            max_workers=10,
        )

        assert not result.isError
        call_kwargs = mock_client.create_environment.call_args[1]
        assert call_kwargs['AirflowVersion'] == '2.8.1'
        assert call_kwargs['EnvironmentClass'] == 'mw1.medium'
        assert call_kwargs['MaxWorkers'] == 10

    @pytest.mark.asyncio
    async def test_create_environment_invalid_name(self, handler_writable, mock_ctx):
        result = await handler_writable.create_environment(
            mock_ctx,
            environment_name='123-bad',
            dag_s3_path='dags/',
            execution_role_arn='arn:aws:iam::123456789012:role/mwaa-role',
            source_bucket_arn='arn:aws:s3:::my-bucket',
            network_configuration={
                'SecurityGroupIds': ['sg-123'],
                'SubnetIds': ['subnet-1', 'subnet-2'],
            },
        )

        assert result.isError
        assert 'Invalid environment name' in result.content[0].text


class TestUpdateEnvironment:
    @pytest.mark.asyncio
    async def test_update_environment_blocked_readonly(self, handler_readonly, mock_ctx):
        result = await handler_readonly.update_environment(
            mock_ctx,
            environment_name='test-env',
            max_workers=20,
        )

        assert result.isError
        assert '--allow-write' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_update_environment_success(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.update_environment.return_value = {
            'Arn': 'arn:aws:airflow:us-east-1:123456789012:environment/test-env'
        }
        mock_get_client.return_value = mock_client

        result = await handler_writable.update_environment(
            mock_ctx,
            environment_name='test-env',
            max_workers=20,
        )

        assert not result.isError
        assert 'update initiated' in result.content[0].text


class TestDeleteEnvironment:
    @pytest.mark.asyncio
    async def test_delete_environment_blocked_readonly(self, handler_readonly, mock_ctx):
        result = await handler_readonly.delete_environment(
            mock_ctx,
            environment_name='test-env',
        )

        assert result.isError
        assert '--allow-write' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_delete_environment_success(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = await handler_writable.delete_environment(
            mock_ctx,
            environment_name='test-env',
        )

        assert not result.isError
        assert 'deletion initiated' in result.content[0].text
        mock_client.delete_environment.assert_called_once_with(Name='test-env')

    @pytest.mark.asyncio
    async def test_delete_environment_invalid_name(self, handler_writable, mock_ctx):
        result = await handler_writable.delete_environment(
            mock_ctx,
            environment_name='123-bad',
        )

        assert result.isError
        assert 'Invalid environment name' in result.content[0].text


class TestGetEnvironmentBotoCoreError:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_get_environment_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.get_environment.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_environment(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestListEnvironmentsBotoCoreError:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_list_environments_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = BotoCoreError()
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_environments(mock_ctx)

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestCreateEnvironmentErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_create_environment_client_error(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.create_environment.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Bad input'}},
            'CreateEnvironment',
        )
        mock_get_client.return_value = mock_client

        result = await handler_writable.create_environment(
            mock_ctx,
            environment_name='new-env',
            dag_s3_path='dags/',
            execution_role_arn='arn:aws:iam::123456789012:role/mwaa-role',
            source_bucket_arn='arn:aws:s3:::my-bucket',
            network_configuration={
                'SecurityGroupIds': ['sg-123'],
                'SubnetIds': ['subnet-1', 'subnet-2'],
            },
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_create_environment_botocore_error(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.create_environment.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_writable.create_environment(
            mock_ctx,
            environment_name='new-env',
            dag_s3_path='dags/',
            execution_role_arn='arn:aws:iam::123456789012:role/mwaa-role',
            source_bucket_arn='arn:aws:s3:::my-bucket',
            network_configuration={
                'SecurityGroupIds': ['sg-123'],
                'SubnetIds': ['subnet-1', 'subnet-2'],
            },
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestUpdateEnvironmentErrors:
    @pytest.mark.asyncio
    async def test_update_environment_invalid_name(self, handler_writable, mock_ctx):
        result = await handler_writable.update_environment(
            mock_ctx, environment_name='123-bad', max_workers=10
        )

        assert result.isError
        assert 'Invalid environment name' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_update_environment_client_error(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.update_environment.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'UpdateEnvironment',
        )
        mock_get_client.return_value = mock_client

        result = await handler_writable.update_environment(
            mock_ctx, environment_name='test-env', max_workers=10
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_update_environment_botocore_error(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.update_environment.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_writable.update_environment(
            mock_ctx, environment_name='test-env', max_workers=10
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_update_environment_with_all_params(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.update_environment.return_value = {'Arn': 'arn:aws:airflow:...'}
        mock_get_client.return_value = mock_client

        result = await handler_writable.update_environment(
            mock_ctx,
            environment_name='test-env',
            airflow_version='2.9.0',
            environment_class='mw1.large',
            max_workers=20,
            dag_s3_path='new-dags/',
            execution_role_arn='arn:aws:iam::123456789012:role/new-role',
            source_bucket_arn='arn:aws:s3:::new-bucket',
        )

        assert not result.isError
        call_kwargs = mock_client.update_environment.call_args[1]
        assert call_kwargs['AirflowVersion'] == '2.9.0'
        assert call_kwargs['EnvironmentClass'] == 'mw1.large'
        assert call_kwargs['MaxWorkers'] == 20
        assert call_kwargs['DagS3Path'] == 'new-dags/'
        assert call_kwargs['ExecutionRoleArn'] == 'arn:aws:iam::123456789012:role/new-role'
        assert call_kwargs['SourceBucketArn'] == 'arn:aws:s3:::new-bucket'


class TestDeleteEnvironmentErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_delete_environment_client_error(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.delete_environment.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'DeleteEnvironment',
        )
        mock_get_client.return_value = mock_client

        result = await handler_writable.delete_environment(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.environment_tools.get_mwaa_client')
    async def test_delete_environment_botocore_error(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.delete_environment.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_writable.delete_environment(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestValidateEnvironmentName:
    def test_valid_names(self):
        EnvironmentTools._validate_environment_name('my-env')
        EnvironmentTools._validate_environment_name('MyEnv123')
        EnvironmentTools._validate_environment_name('a')
        EnvironmentTools._validate_environment_name('env_with_underscores')
        EnvironmentTools._validate_environment_name('E' * 80)

    def test_invalid_names(self):
        with pytest.raises(ValueError):
            EnvironmentTools._validate_environment_name('123-starts-with-digit')
        with pytest.raises(ValueError):
            EnvironmentTools._validate_environment_name('')
        with pytest.raises(ValueError):
            EnvironmentTools._validate_environment_name('-starts-with-hyphen')
        with pytest.raises(ValueError):
            EnvironmentTools._validate_environment_name('a' * 81)
        with pytest.raises(ValueError):
            EnvironmentTools._validate_environment_name('has spaces')
