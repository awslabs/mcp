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

"""Tests that Field() defaults resolve to real values when handlers are called directly.

When a handler uses ``param = Field('default', ...)`` and a test omits that param,
Python passes the raw FieldInfo sentinel instead of the intended default. These tests
call every handler with ONLY required params, verifying that optional defaults resolve
correctly and don't cause Pydantic validation errors or wrong branch execution.
"""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mcp():
    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return mcp


def _parse(result: dict) -> dict:
    return json.loads(result['content'][0]['text'])


# ── artifact.py: upload_artifact ────────────────────────────────────────
# HIGH-RISK defaults: encoding='utf-8', categoryType='CUSTOMER_INPUT', fileType='JSON'
# MEDIUM-RISK defaults: fileName=None, planStepId=None


class TestArtifactFieldDefaults:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available', return_value=True)
    async def test_upload_with_only_required_params(self, _, mock_fes, mock_httpx):
        """Omit encoding, categoryType, fileType, fileName, planStepId — all should default."""
        from awslabs.aws_transform_mcp_server.tools.artifact import ArtifactHandler

        handler = ArtifactHandler(_mcp())
        ctx = AsyncMock()

        mock_fes.side_effect = [
            {'artifactId': 'a-1', 's3PreSignedUrl': 'https://s3.example.com/upload'},
            None,
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='j-1',
            content='{"key": "val"}',
        )
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'
        assert parsed['data']['artifactId'] == 'a-1'

        # Verify the Pydantic model received correct string defaults
        create_req = mock_fes.call_args_list[0][0][1]
        assert create_req.artifactReference.artifactType.categoryType == 'CUSTOMER_INPUT'
        assert create_req.artifactReference.artifactType.fileType == 'JSON'
        # fileName=None means no fileMetadata
        assert create_req.fileMetadata is None
        # planStepId=None means not set
        assert create_req.planStepId is None


# ── configure.py: configure ─────────────────────────────────────────────
# HIGH-RISK defaults: region='us-east-1'
# MEDIUM-RISK defaults: sessionCookie=None, origin=None, startUrl=None, profileName=None


class TestConfigureFieldDefaults:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.persist_config')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.set_config')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.build_cookie_config')
    async def test_cookie_with_only_required_params(
        self, mock_build, mock_set, mock_persist, mock_fes
    ):
        """Omit region — should default to 'us-east-1'."""
        from awslabs.aws_transform_mcp_server.tools.configure import ConfigureHandler

        handler = ConfigureHandler(_mcp())
        ctx = AsyncMock()

        mock_config = MagicMock()
        mock_config.fes_endpoint = 'https://fes.example.com'
        mock_config.origin = 'https://abc123.transform.us-east-1.on.aws'
        mock_config.session_cookie = 'cookie-val'
        mock_config.region = 'us-east-1'
        mock_build.return_value = mock_config
        mock_fes.return_value = {'userId': 'u-1'}

        result = await handler.configure(
            ctx,
            authMode='cookie',
            sessionCookie='cookie-val',
            origin='https://abc123.transform.us-east-1.on.aws',
        )
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'

        # Verify region='us-east-1' was passed (not FieldInfo)
        mock_build.assert_called_once_with(
            'https://abc123.transform.us-east-1.on.aws', 'cookie-val', 'us-east-1'
        )

    @pytest.mark.asyncio
    async def test_sso_missing_startUrl_defaults_to_none(self):
        """Omit startUrl — should be None, not a truthy FieldInfo."""
        from awslabs.aws_transform_mcp_server.tools.configure import ConfigureHandler

        handler = ConfigureHandler(_mcp())
        ctx = AsyncMock()

        result = await handler.configure(ctx, authMode='sso')
        parsed = _parse(result)
        # Should hit the "startUrl is required" validation, not a FieldInfo error
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'startUrl' in parsed['error']['message']

    @pytest.mark.asyncio
    async def test_cookie_missing_sessionCookie_defaults_to_none(self):
        """Omit sessionCookie — should be None, not a truthy FieldInfo."""
        from awslabs.aws_transform_mcp_server.tools.configure import ConfigureHandler

        handler = ConfigureHandler(_mcp())
        ctx = AsyncMock()

        result = await handler.configure(ctx, authMode='cookie')
        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'sessionCookie' in parsed['error']['message']


# ── hitl.py: complete_task ──────────────────────────────────────────────
# HIGH-RISK default: action='APPROVE'
# MEDIUM-RISK defaults: content=None, filePath=None, fileType=None


class TestHitlFieldDefaults:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact', new_callable=AsyncMock
    )
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.format_and_validate')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api', new_callable=AsyncMock
    )
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available', return_value=True)
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.job_needs_check', return_value=None)
    async def test_complete_task_with_only_required_params(
        self, _nudge, _cfg, mock_fes, mock_fmt, mock_upload
    ):
        """Omit content, filePath, fileType, action — action should default to 'APPROVE'."""
        from awslabs.aws_transform_mcp_server.tools.hitl import HitlHandler

        handler = HitlHandler(_mcp())
        ctx = AsyncMock()

        mock_fes.side_effect = [
            # GetHitlTask
            {'task': {'uxComponentId': 'comp-1', 'severity': 'STANDARD'}},
            # SubmitStandardHitlTask
            None,
            # GetHitlTask (final)
            {'task': {'taskId': 't-1', 'status': 'SUBMITTED'}},
        ]
        mock_fmt.return_value = MagicMock(ok=True, content='{}')
        mock_upload.return_value = 'art-resp-1'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='j-1',
            taskId='t-1',
        )
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'

        # Verify action='APPROVE' was used (not FieldInfo)
        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][0] == 'SubmitStandardHitlTask'
        assert submit_call[0][1].action == 'APPROVE'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact', new_callable=AsyncMock
    )
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.format_and_validate')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api', new_callable=AsyncMock
    )
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available', return_value=True)
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.job_needs_check', return_value=None)
    async def test_filePath_defaults_to_none_not_truthy(
        self, _nudge, _cfg, mock_fes, mock_fmt, mock_upload
    ):
        """Omit filePath — should be None so file upload is skipped."""
        from awslabs.aws_transform_mcp_server.tools.hitl import HitlHandler

        handler = HitlHandler(_mcp())
        ctx = AsyncMock()

        mock_fes.side_effect = [
            {'task': {'uxComponentId': 'comp-1', 'severity': 'STANDARD'}},
            None,
            {'task': {'taskId': 't-1', 'status': 'SUBMITTED'}},
        ]
        mock_fmt.return_value = MagicMock(ok=True, content='{}')
        mock_upload.return_value = 'art-resp-1'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='j-1',
            taskId='t-1',
        )
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'
        # No uploadedArtifactId means filePath was correctly None
        assert 'uploadedArtifactId' not in parsed['data']


# ── job.py: create_job ──────────────────────────────────────────────────
# MEDIUM-RISK defaults: jobType=None, orchestratorAgent=None


class TestJobFieldDefaults:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.job.call_transform_api', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.job.is_fes_available', return_value=True)
    async def test_create_job_with_only_required_params(self, _, mock_fes):
        """Omit jobType and orchestratorAgent — should be None, not FieldInfo."""
        from awslabs.aws_transform_mcp_server.tools.job import JobHandler

        handler = JobHandler(_mcp())
        ctx = AsyncMock()

        mock_fes.side_effect = [
            {'jobId': 'j-1'},
            None,
            {'jobId': 'j-1', 'status': 'RUNNING'},
        ]

        result = await handler.create_job(
            ctx,
            workspaceId='ws-1',
            jobName='test',
            objective='obj',
            intent='intent',
        )
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'

        # Verify jobType and orchestratorAgent are None (not FieldInfo)
        create_req = mock_fes.call_args_list[0][0][1]
        assert create_req.jobType is None
        assert create_req.orchestratorAgent is None


# ── collaborator.py: manage_collaborator ────────────────────────────────
# MEDIUM-RISK defaults: userId=None, confirm=None


class TestCollaboratorFieldDefaults:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.collaborator.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.collaborator.is_fes_available', return_value=True
    )
    async def test_leave_with_userId_defaulting_to_none(self, _, mock_fes):
        """Omit userId for 'leave' — should be None so the 'userId must not be provided' check passes."""
        from awslabs.aws_transform_mcp_server.tools.collaborator import CollaboratorHandler

        handler = CollaboratorHandler(_mcp())
        ctx = AsyncMock()

        mock_fes.return_value = {}

        result = await handler.manage_collaborator(
            ctx,
            workspaceId='ws-1',
            action='leave',
            confirm=True,
        )
        parsed = _parse(result)
        # Should succeed (not hit "userId must not be provided" error)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'
        assert parsed['data']['left'] is True

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.collaborator.is_fes_available', return_value=True
    )
    async def test_leave_without_confirm_defaults_to_none(self, _):
        """Omit confirm for 'leave' — should be None (falsy), triggering validation error."""
        from awslabs.aws_transform_mcp_server.tools.collaborator import CollaboratorHandler

        handler = CollaboratorHandler(_mcp())
        ctx = AsyncMock()

        result = await handler.manage_collaborator(
            ctx,
            workspaceId='ws-1',
            action='leave',
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        # Must be the "confirm required" error, not the "userId must not be provided" error
        assert 'confirm' in parsed['error']['message']


# ── connector.py: create_connector ──────────────────────────────────────
# MEDIUM-RISK defaults: description=None, targetRegions=None


class TestConnectorFieldDefaults:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_fes_available', return_value=True)
    async def test_create_connector_with_only_required_params(self, _, mock_fes, mock_config):
        """Omit description and targetRegions — should be None, not FieldInfo."""
        from awslabs.aws_transform_mcp_server.tools.connector import ConnectorHandler

        handler = ConnectorHandler(_mcp())
        ctx = AsyncMock()

        mock_fes.side_effect = [
            {'connectorId': 'c-1'},
            {'connectorId': 'c-1', 'status': 'PENDING'},
        ]
        mock_cfg = MagicMock()
        mock_cfg.region = 'us-east-1'
        mock_config.return_value = mock_cfg

        result = await handler.create_connector(
            ctx,
            workspaceId='ws-1',
            connectorName='test',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket'},
            awsAccountId='123456789012',
        )
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'

        # Verify description and targetRegions are None in the request
        create_req = mock_fes.call_args_list[0][0][1]
        assert create_req.description is None
        assert create_req.targetRegions is None


# ── workspace.py: create_workspace ──────────────────────────────────────
# MEDIUM-RISK default: description=None


class TestWorkspaceFieldDefaults:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.workspace.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.workspace.is_fes_available', return_value=True)
    async def test_create_workspace_with_only_required_params(self, _, mock_fes):
        """Omit description — should be None, not FieldInfo."""
        from awslabs.aws_transform_mcp_server.tools.workspace import WorkspaceHandler

        handler = WorkspaceHandler(_mcp())
        ctx = AsyncMock()

        mock_fes.return_value = {'workspace': {'workspaceId': 'ws-1', 'name': 'test'}}

        result = await handler.create_workspace(ctx, name='test')
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'

        # Verify description is None in the request
        create_req = mock_fes.call_args_list[0][0][1]
        assert create_req.description is None


# ── chat/send_message.py: send_message ──────────────────────────────────
# MEDIUM-RISK defaults: jobId=None, skipPolling=None


class TestSendMessageFieldDefaults:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.chat.send_message.poll_for_response',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.chat.send_message.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.chat.send_message.is_fes_available',
        return_value=True,
    )
    async def test_send_message_with_only_required_params(self, _, mock_fes, mock_poll):
        """Omit jobId and skipPolling — should be None, not FieldInfo."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        ctx = AsyncMock()

        mock_fes.return_value = {'message': {'messageId': 'm-1', 'text': 'hello'}}
        mock_poll.return_value = {
            'terminal': {'messageId': 'm-2', 'text': 'response', 'sender': 'ASSISTANT'},
            'is_error': False,
            'last_thinking': None,
        }

        result = await send_message(ctx, workspaceId='ws-1', text='hello')
        parsed = _parse(result)
        assert parsed['success'] is True, f'Expected success, got: {parsed}'
        # No hint field means jobId was correctly None
        assert 'hint' not in parsed['data']
