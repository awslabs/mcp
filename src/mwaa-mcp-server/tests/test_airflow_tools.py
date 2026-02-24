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
"""Tests for the Airflow REST API tools."""

import json
import pytest
from awslabs.mwaa_mcp_server.airflow_tools import AirflowTools
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture
def handler_readonly(mock_mcp):
    """Create AirflowTools handler in read-only mode."""
    return AirflowTools(mock_mcp, allow_write=False)


@pytest.fixture
def handler_writable(mock_mcp):
    """Create AirflowTools handler with write access."""
    return AirflowTools(mock_mcp, allow_write=True)


class TestInvokeAirflowApi:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_invoke_basic_get(self, mock_get_client, handler_readonly):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'dags': [], 'total_entries': 0},
            'RestApiStatusCode': 200,
        }
        mock_get_client.return_value = mock_client

        response = await handler_readonly._invoke_airflow_api(
            environment_name='test-env',
            method='GET',
            path='/dags',
        )

        assert response == {'dags': [], 'total_entries': 0}
        mock_client.invoke_rest_api.assert_called_once_with(
            Name='test-env',
            Method='GET',
            Path='/dags',
        )

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_invoke_with_body_and_query(self, mock_get_client, handler_readonly):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'dag_run_id': 'run-1'},
            'RestApiStatusCode': 200,
        }
        mock_get_client.return_value = mock_client

        response = await handler_readonly._invoke_airflow_api(
            environment_name='test-env',
            method='POST',
            path='/dags/my_dag/dagRuns',
            body={'conf': {'key': 'value'}},
            query_parameters={'limit': '10'},
        )

        assert response == {'dag_run_id': 'run-1'}
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['Body'] == {'conf': {'key': 'value'}}
        assert call_kwargs['QueryParameters'] == {'limit': '10'}

    @pytest.mark.asyncio
    async def test_invoke_invalid_environment_name(self, handler_readonly):
        with pytest.raises(ValueError, match='Invalid environment name'):
            await handler_readonly._invoke_airflow_api(
                environment_name='123-bad',
                method='GET',
                path='/dags',
            )


class TestListDags:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dags_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'dags': [{'dag_id': 'dag1'}, {'dag_id': 'dag2'}],
                'total_entries': 2,
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dags(mock_ctx, environment_name='test-env')

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert len(data['dags']) == 2

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dags_with_params(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'dags': [], 'total_entries': 0},
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dags(
            mock_ctx, environment_name='test-env', limit=10, offset=5, paused=True
        )

        assert not result.isError
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['QueryParameters'] == {
            'limit': '10',
            'offset': '5',
            'paused': 'true',
        }

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dags_client_error(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dags(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS API error' in result.content[0].text


class TestGetDag:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'dag_id': 'my_dag',
                'is_paused': False,
                'schedule_interval': '@daily',
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert data['dag_id'] == 'my_dag'

    @pytest.mark.asyncio
    async def test_get_dag_path_traversal(self, handler_readonly, mock_ctx):
        result = await handler_readonly.get_dag(
            mock_ctx, environment_name='test-env', dag_id='../../../etc/passwd'
        )

        assert result.isError
        assert 'path traversal' in result.content[0].text


class TestGetDagSource:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_source_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'content': 'from airflow import DAG\n...'},
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag_source(
            mock_ctx, environment_name='test-env', file_token='abc123'
        )

        assert not result.isError

    @pytest.mark.asyncio
    async def test_get_dag_source_path_traversal(self, handler_readonly, mock_ctx):
        result = await handler_readonly.get_dag_source(
            mock_ctx, environment_name='test-env', file_token='../bad'
        )

        assert result.isError
        assert 'path traversal' in result.content[0].text


class TestListDagRuns:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dag_runs_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'dag_runs': [{'dag_run_id': 'run-1', 'state': 'success'}],
                'total_entries': 1,
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dag_runs(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert len(data['dag_runs']) == 1

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dag_runs_with_filters(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'dag_runs': [], 'total_entries': 0},
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dag_runs(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            limit=5,
            offset=0,
            state='failed',
        )

        assert not result.isError
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['QueryParameters']['state'] == 'failed'


class TestGetDagRun:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_run_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'dag_run_id': 'run-1',
                'state': 'success',
                'execution_date': '2024-01-01T00:00:00+00:00',
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag_run(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
        )

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert data['dag_run_id'] == 'run-1'


class TestListTaskInstances:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_task_instances_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'task_instances': [
                    {'task_id': 'task1', 'state': 'success'},
                    {'task_id': 'task2', 'state': 'failed'},
                ],
                'total_entries': 2,
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_task_instances(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
        )

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert len(data['task_instances']) == 2


class TestGetTaskInstance:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_task_instance_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'task_id': 'my_task',
                'state': 'success',
                'try_number': 1,
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_task_instance(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
            task_id='my_task',
        )

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert data['task_id'] == 'my_task'

    @pytest.mark.asyncio
    async def test_get_task_instance_path_traversal(self, handler_readonly, mock_ctx):
        result = await handler_readonly.get_task_instance(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
            task_id='../../etc/passwd',
        )

        assert result.isError
        assert 'path traversal' in result.content[0].text


class TestGetTaskLogs:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_task_logs_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'content': 'Task log output here...'},
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_task_logs(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
            task_id='my_task',
            try_number=1,
        )

        assert not result.isError
        assert 'try 1' in result.content[0].text


class TestListConnections:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_connections_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'connections': [
                    {
                        'connection_id': 'aws_default',
                        'conn_type': 'aws',
                        'password': 'secret123',
                        'extra': '{"key": "value"}',
                    }
                ],
                'total_entries': 1,
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_connections(mock_ctx, environment_name='test-env')

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert data['connections'][0]['password'] == '***REDACTED***'
        assert data['connections'][0]['extra'] == '***REDACTED***'
        assert data['connections'][0]['connection_id'] == 'aws_default'


class TestListVariables:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_variables_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'variables': [{'key': 'my_var', 'value': 'my_value'}],
                'total_entries': 1,
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_variables(mock_ctx, environment_name='test-env')

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert len(data['variables']) == 1


class TestGetImportErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_import_errors_success(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'import_errors': [
                    {
                        'filename': '/usr/local/airflow/dags/broken_dag.py',
                        'stack_trace': 'SyntaxError: invalid syntax',
                    }
                ],
                'total_entries': 1,
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_import_errors(mock_ctx, environment_name='test-env')

        assert not result.isError
        data = json.loads(result.content[1].text)
        assert len(data['import_errors']) == 1


class TestTriggerDagRun:
    @pytest.mark.asyncio
    async def test_trigger_dag_run_blocked_readonly(self, handler_readonly, mock_ctx):
        result = await handler_readonly.trigger_dag_run(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert '--allow-write' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_trigger_dag_run_success(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {
                'dag_run_id': 'manual__2024-01-01T00:00:00+00:00',
                'state': 'queued',
            },
        }
        mock_get_client.return_value = mock_client

        result = await handler_writable.trigger_dag_run(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert not result.isError
        assert 'triggered' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_trigger_dag_run_with_conf(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'dag_run_id': 'run-1', 'state': 'queued'},
        }
        mock_get_client.return_value = mock_client

        result = await handler_writable.trigger_dag_run(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            conf={'key': 'value'},
            logical_date='2024-01-01T00:00:00+00:00',
        )

        assert not result.isError
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['Body'] == {
            'conf': {'key': 'value'},
            'logical_date': '2024-01-01T00:00:00+00:00',
        }


class TestPauseDag:
    @pytest.mark.asyncio
    async def test_pause_dag_blocked_readonly(self, handler_readonly, mock_ctx):
        result = await handler_readonly.pause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert '--allow-write' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_pause_dag_success(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'dag_id': 'my_dag', 'is_paused': True},
        }
        mock_get_client.return_value = mock_client

        result = await handler_writable.pause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert not result.isError
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['Body'] == {'is_paused': True}
        assert call_kwargs['Method'] == 'PATCH'


class TestUnpauseDag:
    @pytest.mark.asyncio
    async def test_unpause_dag_blocked_readonly(self, handler_readonly, mock_ctx):
        result = await handler_readonly.unpause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert '--allow-write' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_unpause_dag_success(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'dag_id': 'my_dag', 'is_paused': False},
        }
        mock_get_client.return_value = mock_client

        result = await handler_writable.unpause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert not result.isError
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['Body'] == {'is_paused': False}
        assert call_kwargs['Method'] == 'PATCH'


class TestListDagsBotoCoreError:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dags_botocore_error(self, mock_get_client, handler_readonly, mock_ctx):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dags(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestGetDagErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_client_error(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_botocore_error(self, mock_get_client, handler_readonly, mock_ctx):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestGetDagSourceErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_source_client_error(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag_source(
            mock_ctx, environment_name='test-env', file_token='abc123'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_source_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag_source(
            mock_ctx, environment_name='test-env', file_token='abc123'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestListDagRunsErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dag_runs_client_error(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dag_runs(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_dag_runs_botocore_error(self, mock_get_client, handler_readonly, mock_ctx):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dag_runs(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestGetDagRunErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_run_client_error(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag_run(
            mock_ctx, environment_name='test-env', dag_id='my_dag', dag_run_id='run-1'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_dag_run_botocore_error(self, mock_get_client, handler_readonly, mock_ctx):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_dag_run(
            mock_ctx, environment_name='test-env', dag_id='my_dag', dag_run_id='run-1'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestListTaskInstancesErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_task_instances_client_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_task_instances(
            mock_ctx, environment_name='test-env', dag_id='my_dag', dag_run_id='run-1'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_task_instances_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_task_instances(
            mock_ctx, environment_name='test-env', dag_id='my_dag', dag_run_id='run-1'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestGetTaskInstanceErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_task_instance_client_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_task_instance(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
            task_id='my_task',
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_task_instance_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_task_instance(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
            task_id='my_task',
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestGetTaskLogsErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_task_logs_client_error(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_task_logs(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
            task_id='my_task',
            try_number=1,
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_task_logs_botocore_error(self, mock_get_client, handler_readonly, mock_ctx):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_task_logs(
            mock_ctx,
            environment_name='test-env',
            dag_id='my_dag',
            dag_run_id='run-1',
            task_id='my_task',
            try_number=1,
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestListConnectionsErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_connections_client_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_connections(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_connections_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_connections(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_connections_with_params(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'connections': [], 'total_entries': 0},
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_connections(
            mock_ctx, environment_name='test-env', limit=10, offset=5
        )

        assert not result.isError
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['QueryParameters'] == {'limit': '10', 'offset': '5'}


class TestListVariablesErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_variables_client_error(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_variables(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_variables_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_variables(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_list_variables_with_params(self, mock_get_client, handler_readonly, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.return_value = {
            'RestApiResponse': {'variables': [], 'total_entries': 0},
        }
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_variables(
            mock_ctx, environment_name='test-env', limit=10, offset=5
        )

        assert not result.isError
        call_kwargs = mock_client.invoke_rest_api.call_args[1]
        assert call_kwargs['QueryParameters'] == {'limit': '10', 'offset': '5'}


class TestGetImportErrorsErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_import_errors_client_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_import_errors(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_get_import_errors_botocore_error(
        self, mock_get_client, handler_readonly, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_readonly.get_import_errors(mock_ctx, environment_name='test-env')

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text


class TestTriggerDagRunErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_trigger_dag_run_client_error(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_writable.trigger_dag_run(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_trigger_dag_run_botocore_error(
        self, mock_get_client, handler_writable, mock_ctx
    ):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_writable.trigger_dag_run(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_trigger_dag_run_path_traversal(self, handler_writable, mock_ctx):
        result = await handler_writable.trigger_dag_run(
            mock_ctx, environment_name='test-env', dag_id='../etc/passwd'
        )

        assert result.isError
        assert 'path traversal' in result.content[0].text


class TestPauseDagErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_pause_dag_client_error(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_writable.pause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_pause_dag_botocore_error(self, mock_get_client, handler_writable, mock_ctx):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_writable.pause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_pause_dag_path_traversal(self, handler_writable, mock_ctx):
        result = await handler_writable.pause_dag(
            mock_ctx, environment_name='test-env', dag_id='../etc/passwd'
        )

        assert result.isError
        assert 'path traversal' in result.content[0].text


class TestUnpauseDagErrors:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_unpause_dag_client_error(self, mock_get_client, handler_writable, mock_ctx):
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_writable.unpause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS API error' in result.content[0].text

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_unpause_dag_botocore_error(self, mock_get_client, handler_writable, mock_ctx):
        from botocore.exceptions import BotoCoreError

        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client

        result = await handler_writable.unpause_dag(
            mock_ctx, environment_name='test-env', dag_id='my_dag'
        )

        assert result.isError
        assert 'AWS SDK error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_unpause_dag_path_traversal(self, handler_writable, mock_ctx):
        result = await handler_writable.unpause_dag(
            mock_ctx, environment_name='test-env', dag_id='../etc/passwd'
        )

        assert result.isError
        assert 'path traversal' in result.content[0].text


class TestSanitizePathParam:
    def test_valid_params(self):
        assert AirflowTools._sanitize_path_param('my_dag', 'dag_id') == 'my_dag'
        assert AirflowTools._sanitize_path_param('run-123', 'dag_run_id') == 'run-123'

    def test_path_traversal_dots(self):
        with pytest.raises(ValueError, match='path traversal'):
            AirflowTools._sanitize_path_param('../etc/passwd', 'dag_id')

    def test_path_traversal_slash(self):
        with pytest.raises(ValueError, match='path traversal'):
            AirflowTools._sanitize_path_param('dag/id', 'dag_id')

    def test_path_traversal_backslash(self):
        with pytest.raises(ValueError, match='path traversal'):
            AirflowTools._sanitize_path_param('dag\\id', 'dag_id')


class TestRedactConnections:
    def test_redact_passwords(self):
        response = {
            'connections': [
                {
                    'connection_id': 'test',
                    'password': 'secret',
                    'extra': '{"token": "abc"}',
                    'host': 'localhost',
                }
            ]
        }
        result = AirflowTools._redact_connections(response)
        assert result['connections'][0]['password'] == '***REDACTED***'
        assert result['connections'][0]['extra'] == '***REDACTED***'
        assert result['connections'][0]['host'] == 'localhost'

    def test_redact_no_sensitive_fields(self):
        response = {'connections': [{'connection_id': 'test', 'host': 'localhost'}]}
        result = AirflowTools._redact_connections(response)
        assert result['connections'][0]['host'] == 'localhost'

    def test_redact_empty_connections(self):
        response = {'connections': []}
        result = AirflowTools._redact_connections(response)
        assert result['connections'] == []


class TestResolveEnvironment:
    def test_explicit_name_returned_as_is(self, mock_mcp):
        handler = AirflowTools(mock_mcp, allow_write=False)
        result = handler._resolve_environment('my-env')
        assert result == 'my-env'

    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    def test_single_env_auto_selected(self, mock_get_client, mock_mcp):
        mock_client = MagicMock()
        mock_client.list_environments.return_value = {
            'Environments': ['only-env'],
        }
        mock_get_client.return_value = mock_client

        handler = AirflowTools(mock_mcp, allow_write=False)
        result = handler._resolve_environment(None)

        assert result == 'only-env'

    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    def test_multiple_envs_raises_with_list(self, mock_get_client, mock_mcp):
        mock_client = MagicMock()
        mock_client.list_environments.return_value = {
            'Environments': ['env-a', 'env-b', 'env-c'],
        }
        mock_get_client.return_value = mock_client

        handler = AirflowTools(mock_mcp, allow_write=False)

        with pytest.raises(ValueError, match='Multiple MWAA environments found'):
            handler._resolve_environment(None)

    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    def test_no_envs_raises(self, mock_get_client, mock_mcp):
        mock_client = MagicMock()
        mock_client.list_environments.return_value = {
            'Environments': [],
        }
        mock_get_client.return_value = mock_client

        handler = AirflowTools(mock_mcp, allow_write=False)

        with pytest.raises(ValueError, match='No MWAA environments found'):
            handler._resolve_environment(None)

    def test_env_var_used_when_no_explicit_name(self, mock_mcp, monkeypatch):
        monkeypatch.setenv('MWAA_ENVIRONMENT', 'env-from-var')
        handler = AirflowTools(mock_mcp, allow_write=False)
        result = handler._resolve_environment(None)
        assert result == 'env-from-var'

    def test_explicit_name_takes_precedence_over_env_var(self, mock_mcp, monkeypatch):
        monkeypatch.setenv('MWAA_ENVIRONMENT', 'env-from-var')
        handler = AirflowTools(mock_mcp, allow_write=False)
        result = handler._resolve_environment('explicit-env')
        assert result == 'explicit-env'

    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    def test_env_var_ignored_when_empty(self, mock_get_client, mock_mcp, monkeypatch):
        monkeypatch.setenv('MWAA_ENVIRONMENT', '')
        mock_client = MagicMock()
        mock_client.list_environments.return_value = {
            'Environments': ['only-env'],
        }
        mock_get_client.return_value = mock_client

        handler = AirflowTools(mock_mcp, allow_write=False)
        result = handler._resolve_environment(None)
        assert result == 'only-env'


class TestRestApiClientExceptionEnrichment:
    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_enriched_error_message(self, mock_get_client, handler_readonly):
        """RestApiClientException should be re-raised with HTTP status and response body."""
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {
                'Error': {'Code': 'RestApiClientException', 'Message': ''},
                'RestApiStatusCode': 404,
                'RestApiResponse': {
                    'detail': 'DAG not found',
                    'status': 404,
                    'title': 'Not Found',
                },
            },
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ClientError) as exc_info:
            await handler_readonly._invoke_airflow_api(
                environment_name='test-env',
                method='GET',
                path='/dags/nonexistent/dagRuns',
            )

        error_message = str(exc_info.value)
        assert 'HTTP 404' in error_message
        assert 'DAG not found' in error_message

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_non_rest_api_error_passes_through(self, mock_get_client, handler_readonly):
        """Non-RestApiClientException errors should pass through unchanged."""
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ClientError) as exc_info:
            await handler_readonly._invoke_airflow_api(
                environment_name='test-env',
                method='GET',
                path='/dags',
            )

        assert 'AccessDeniedException' in str(exc_info.value)
        assert 'Access denied' in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('awslabs.mwaa_mcp_server.airflow_tools.get_mwaa_client')
    async def test_tool_surfaces_enriched_error(self, mock_get_client, handler_readonly, mock_ctx):
        """Tool method should surface the enriched RestApiClientException in CallToolResult."""
        mock_client = MagicMock()
        mock_client.invoke_rest_api.side_effect = ClientError(
            {
                'Error': {'Code': 'RestApiClientException', 'Message': ''},
                'RestApiStatusCode': 404,
                'RestApiResponse': {'detail': 'DAG not found', 'status': 404},
            },
            'InvokeRestApi',
        )
        mock_get_client.return_value = mock_client

        result = await handler_readonly.list_dag_runs(
            mock_ctx, environment_name='test-env', dag_id='nonexistent_dag'
        )

        assert result.isError
        assert 'HTTP 404' in result.content[0].text
        assert 'DAG not found' in result.content[0].text
