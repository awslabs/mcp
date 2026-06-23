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

"""Tests for the MCP server tools."""

import pytest
from awslabs.security_agent_mcp_server.server import mcp
from unittest.mock import AsyncMock, MagicMock, patch


def test_server_has_expected_tools():
    """Verify all expected tools are registered."""
    tools = mcp._tool_manager._tools
    expected = {
        'setup_check',
        'setup',
        'start_security_scan',
        'start_diff_scan',
        'start_threat_model_review',
        'get_scan_status',
        'get_scan_findings',
        'list_scans',
        'stop_scan',
        'call_api',
        'get_api_guide',
    }
    assert set(tools.keys()) == expected


def test_server_name():
    """Verify server name is correct."""
    assert mcp.name == 'awslabs.security-agent-mcp-server'


def test_server_has_instructions():
    """Verify server has instructions set."""
    assert mcp.instructions is not None
    assert 'AWS Security Agent' in mcp.instructions


def test_server_tool_count():
    """Verify correct number of tools."""
    assert len(mcp._tool_manager._tools) == 11


class TestSetupCheck:
    """Tests for setup_check tool."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_ready(self, mock_client, mock_state):
        """Returns ready when all configured."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'bucket',
        }
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'true' in result or '"ready": true' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_not_ready(self, mock_client, mock_state):
        """Returns missing items when not configured."""
        mock_state.get_config.return_value = {}
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'false' in result or '"ready": false' in result
        assert 'agent_space_id' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_creds_error(self, mock_client, mock_state):
        """Reports credential error."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'bucket',
        }
        mock_client.get_caller_identity.side_effect = Exception('no creds')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'aws_credentials' in result


class TestSetup:
    """Tests for setup tool."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_creates_new_space_and_role(self, mock_client, mock_state):
        """Creates agent space and role when nothing provided."""
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_client.create_service_role.return_value = (
            'arn:aws:iam::123456789012:role/SecurityAgentScanRole'
        )
        mock_client.create_agent_space.return_value = {'agentSpaceId': 'as-new'}
        mock_state.get_config.return_value = {}
        mock_state.update_config = MagicMock()
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup

        result = await setup(ctx, name='test', agent_space_id=None, service_role_arn=None)
        assert 'ready' in result
        assert 'as-new' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_uses_existing_space_and_role(self, mock_client, mock_state):
        """Uses existing space and role when provided."""
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_client.get_agent_space.return_value = {
            'name': 'existing',
            'awsResources': {'iamRoles': ['arn:existing'], 's3Buckets': []},
        }
        mock_client.update_agent_space.return_value = {}
        mock_state.get_config.return_value = {}
        mock_state.update_config = MagicMock()
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup

        result = await setup(
            ctx, name=None, agent_space_id='as-exist', service_role_arn='arn:my-role'
        )
        assert 'ready' in result
        assert 'arn:my-role' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_preserves_existing_resources_when_adding_role(self, mock_client, mock_state):
        """All existing awsResources are preserved when registering a new role on the space."""
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_client.get_agent_space.return_value = {
            'name': 'existing',
            'awsResources': {
                'iamRoles': ['arn:other-role'],
                's3Buckets': ['pentest-bucket', 'code-review-bucket'],
            },
        }
        mock_client.update_agent_space.return_value = {}
        mock_state.get_config.return_value = {}
        mock_state.update_config = MagicMock()
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup

        await setup(ctx, name=None, agent_space_id='as-exist', service_role_arn='arn:my-role')

        # Verify the update call preserved buckets AND merged the new role
        aws_resources_arg = mock_client.update_agent_space.call_args[0][2]
        assert aws_resources_arg['s3Buckets'] == ['pentest-bucket', 'code-review-bucket']
        assert 'arn:other-role' in aws_resources_arg['iamRoles']
        assert 'arn:my-role' in aws_resources_arg['iamRoles']


class TestCallApi:
    """Tests for call_api tool."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_call_api_success(self, mock_client):
        """Calls API successfully."""
        mock_client.call.return_value = {'result': 'ok'}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import call_api

        result = await call_api(ctx, operation='ListAgentSpaces', params={})
        assert 'ok' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_call_api_invalid_operation(self, mock_client):
        """Rejects invalid operation names."""
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import call_api

        result = await call_api(ctx, operation='../evil', params={})
        assert 'Invalid operation' in result


class TestGetApiGuide:
    """Tests for get_api_guide tool."""

    @pytest.mark.asyncio
    async def test_returns_guide(self):
        """Returns operations list."""
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_api_guide

        result = await get_api_guide(ctx)
        assert 'documentation' in result
        assert 'operations' in result


class TestSetupCheckNotReady:
    """Tests for setup_check listing spaces."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_lists_existing_spaces(self, mock_state, mock_client):
        """Returns existing spaces when not ready."""
        mock_state.get_config.return_value = {}
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.list_agent_spaces.return_value = [{'agentSpaceId': 'as-1', 'name': 'test'}]
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'existing_agent_spaces' in result
        assert 'as-1' in result


class TestStartSecurityScan:
    """Tests for start_security_scan lazy bucket creation."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path', new=AsyncMock(return_value='.')
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_creates_bucket_when_missing(self, mock_client, mock_state, mock_scanner):
        """Creates S3 bucket on first scan when not in config."""
        mock_state.get_config.return_value = {'agent_space_id': 'as-1', 'service_role': 'arn:role'}
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_client.create_s3_bucket.return_value = 'bucket'
        mock_state.update_config = MagicMock()
        mock_scanner.start_scan = AsyncMock(return_value={'scan_id': 'scan-1'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        result = await start_security_scan(ctx, path='.', title='test')
        mock_client.create_s3_bucket.assert_called_once()
        assert 'scan-1' in result

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path', new=AsyncMock(return_value='.')
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_handles_bucket_already_exists(self, mock_client, mock_state, mock_scanner):
        """Handles BucketAlreadyOwnedByYou gracefully."""
        from botocore.exceptions import ClientError

        mock_state.get_config.return_value = {'agent_space_id': 'as-1', 'service_role': 'arn:role'}
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}

        mock_client.create_s3_bucket.side_effect = ClientError(
            {'Error': {'Code': 'BucketAlreadyOwnedByYou', 'Message': 'owned'}},
            'CreateBucket',
        )
        mock_client.get_agent_space.return_value = {
            'name': 'sec',
            'awsResources': {'iamRoles': ['arn:role'], 's3Buckets': []},
        }
        mock_state.update_config = MagicMock()
        mock_scanner.start_scan = AsyncMock(return_value={'scan_id': 'scan-1'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        result = await start_security_scan(ctx, path='.', title='test')
        assert 'scan-1' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_not_configured(self, mock_state):
        """Returns error when not configured."""
        mock_state.get_config.return_value = {}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        result = await start_security_scan(ctx, path='.', title='test')
        assert 'error' in result
        assert 'Not configured' in result


def test_json_serial_unsupported_type():
    """_json_serial raises TypeError for non-datetime objects (default branch)."""
    from awslabs.security_agent_mcp_server.server import _json_serial

    class Weird:
        """Weird."""

        pass

    with pytest.raises(TypeError):
        _json_serial(Weird())


def test_json_serial_datetime():
    """_json_serial returns ISO string for datetime."""
    from awslabs.security_agent_mcp_server.server import _json_serial
    from datetime import datetime, timezone

    out = _json_serial(datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert out.startswith('2026-01-01')


class TestSetupCheckListSpacesError:
    """Covers the list_agent_spaces failure branch in setup_check."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_list_spaces_error(self, mock_state, mock_client):
        """If list_agent_spaces throws, do not crash — error is silently swallowed."""
        mock_state.get_config.return_value = {}
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.list_agent_spaces.side_effect = Exception('AccessDenied')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        # Tool must still return a successful response (no existing_agent_spaces).
        assert '"ready": false' in result
        assert 'existing_agent_spaces' not in result


class TestSetupErrorPaths:
    """Setup tool error / fallback paths."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_role_create_unrelated_error_propagates(self, mock_client, mock_state):
        """Any other exception from create_service_role surfaces via ctx.error."""
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.create_service_role.side_effect = RuntimeError('boom')
        mock_state.get_config.return_value = {}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup

        with pytest.raises(RuntimeError):
            await setup(ctx, name='n', agent_space_id=None, service_role_arn=None)
        ctx.error.assert_awaited()

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_setup_check_top_level_exception(self, mock_state):
        """If get_config itself throws, error path is hit."""
        mock_state.get_config.side_effect = RuntimeError('disk gone')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        with pytest.raises(RuntimeError):
            await setup_check(ctx)
        ctx.error.assert_awaited()


class TestStartSecurityScanBucketRegistration:
    """Covers bucket-registration path in start_security_scan."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path', new=AsyncMock(return_value='.')
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_registers_bucket_on_agent_space(self, mock_client, mock_state, mock_scanner):
        """Newly-created bucket gets added to the agent space's awsResources."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
        }
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.create_s3_bucket.return_value = 'bucket'
        mock_client.get_agent_space.return_value = {
            'name': 'sec',
            'awsResources': {'iamRoles': ['arn:role'], 's3Buckets': []},
        }
        mock_state.update_config = MagicMock()
        mock_scanner.start_scan = AsyncMock(return_value={'scan_id': 'scan-1'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        await start_security_scan(ctx, path='.', title='t')
        mock_client.update_agent_space.assert_called_once()
        # Existing iamRoles preserved when the new bucket is registered
        aws_resources_arg = mock_client.update_agent_space.call_args[0][2]
        assert aws_resources_arg['iamRoles'] == ['arn:role']
        assert any('security-agent-scans-' in b for b in aws_resources_arg['s3Buckets'])

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_bucket_create_unrelated_error_raises(
        self, mock_client, mock_state, mock_scanner
    ):
        """Any error other than BucketAlreadyOwnedByYou must surface."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
        }
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.create_s3_bucket.side_effect = RuntimeError('access denied')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        with pytest.raises(RuntimeError):
            await start_security_scan(ctx, path='.', title='t')
        ctx.error.assert_awaited()


class TestGetScanStatusAndFindings:
    """Coverage for get_scan_status, get_scan_findings, list_scans, stop_scan."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_get_scan_status(self, mock_scanner):
        """Test get scan status."""
        mock_scanner.get_status = AsyncMock(return_value={'status': 'COMPLETED'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_scan_status

        result = await get_scan_status(ctx, scan_id='scan-1')
        assert 'COMPLETED' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_get_scan_status_error(self, mock_scanner):
        """Test get scan status error."""
        mock_scanner.get_status = AsyncMock(side_effect=RuntimeError('no scan'))
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_scan_status

        with pytest.raises(RuntimeError):
            await get_scan_status(ctx, scan_id='x')
        ctx.error.assert_awaited()

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_get_scan_findings(self, mock_scanner):
        """Test get scan findings."""
        mock_scanner.get_findings = AsyncMock(return_value={'total_findings': 2, 'findings': []})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_scan_findings

        result = await get_scan_findings(ctx, scan_id='scan-1', severity='HIGH')
        assert 'total_findings' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_get_scan_findings_error(self, mock_scanner):
        """Test get scan findings error."""
        mock_scanner.get_findings = AsyncMock(side_effect=RuntimeError('boom'))
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_scan_findings

        with pytest.raises(RuntimeError):
            await get_scan_findings(ctx, scan_id='x', severity=None)
        ctx.error.assert_awaited()

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_list_scans(self, mock_state):
        """Test list scans."""
        mock_state.list_scans.return_value = [{'scan_id': 'scan-1'}]
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import list_scans

        result = await list_scans(ctx)
        assert 'scan-1' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_list_scans_error(self, mock_state):
        """Test list scans error."""
        mock_state.list_scans.side_effect = RuntimeError('disk')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import list_scans

        with pytest.raises(RuntimeError):
            await list_scans(ctx)
        ctx.error.assert_awaited()

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_stop_scan(self, mock_scanner):
        """Test stop scan."""
        mock_scanner.stop_scan = AsyncMock(return_value={'status': 'STOPPED'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import stop_scan

        result = await stop_scan(ctx, scan_id='scan-1')
        assert 'STOPPED' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_stop_scan_error(self, mock_scanner):
        """Test stop scan error."""
        mock_scanner.stop_scan = AsyncMock(side_effect=RuntimeError('boom'))
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import stop_scan

        with pytest.raises(RuntimeError):
            await stop_scan(ctx, scan_id='x')
        ctx.error.assert_awaited()


class TestCallApiErrors:
    """TestCallApiErrors."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_call_api_underlying_error(self, mock_client):
        """Underlying client error rethrows via ctx.error."""
        mock_client.call.side_effect = RuntimeError('AccessDenied')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import call_api

        with pytest.raises(RuntimeError):
            await call_api(ctx, operation='ListAgentSpaces', params={})
        ctx.error.assert_awaited()


class TestGetApiGuideFallback:
    """Cover the boto3 fallback path in get_api_guide."""

    @pytest.mark.asyncio
    async def test_returns_fallback_when_boto3_fails(self, monkeypatch):
        """If boto3 service-model load fails, returns fallback string."""
        import awslabs.security_agent_mcp_server.server as srv

        monkeypatch.setattr(srv, '_cached_operations', None)

        # Replace the boto3 module in sys.modules so `import boto3` inside the
        # tool gets our broken stub.
        import sys

        class _BrokenBoto3:
            """BrokenBoto3."""

            class Session:
                """Session."""

                def __init__(self, *a, **kw):
                    """Init."""
                    raise RuntimeError('no creds')

        monkeypatch.setitem(sys.modules, 'boto3', _BrokenBoto3)

        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_api_guide

        result = await get_api_guide(ctx)
        assert 'Could not load service model' in result


def test_main_runs_mcp(monkeypatch):
    """main() invokes mcp.run()."""
    from awslabs.security_agent_mcp_server import server

    called = {}

    def fake_run():
        """Fake run."""
        called['ran'] = True

    monkeypatch.setattr(server.mcp, 'run', fake_run)
    server.main()
    assert called.get('ran') is True


class TestErrorContract:
    """ClientError -> {error, error_code, remediation} translation."""

    def test_translate_known_code(self):
        """Test translate known code."""
        from awslabs.security_agent_mcp_server.server import _translate_client_error
        from botocore.exceptions import ClientError

        e = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'no perms'}},
            'CreateRole',
        )
        out = _translate_client_error(e)
        assert out['error'] == 'no perms'
        assert out['error_code'] == 'AccessDeniedException'
        assert out['remediation']  # non-empty

    def test_translate_unknown_code_uses_fallback(self):
        """Test translate unknown code uses fallback."""
        from awslabs.security_agent_mcp_server.server import _translate_client_error
        from botocore.exceptions import ClientError

        e = ClientError(
            {'Error': {'Code': 'WeirdNewException', 'Message': 'odd'}},
            'SomeOp',
        )
        out = _translate_client_error(e)
        assert out['error_code'] == 'WeirdNewException'
        assert 'AWS docs' in out['remediation']

    def test_translate_missing_response_shape(self):
        """Test translate missing response shape."""
        from awslabs.security_agent_mcp_server.server import _translate_client_error
        from botocore.exceptions import ClientError

        # Some boto3 errors lack a populated 'Error' dict.
        e = ClientError({}, 'Op')
        out = _translate_client_error(e)
        assert out['error_code'] == 'UnknownError'
        assert out['error']  # non-empty fallback

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_call_api_clienterror_returns_structured_dict(self, mock_client):
        """ClientError from boto3 should now return structured JSON, not re-raise."""
        from botocore.exceptions import ClientError

        mock_client.call.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}},
            'ListAgentSpaces',
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import call_api

        result = await call_api(ctx, operation='ListAgentSpaces', params={})
        # Structured payload — no exception, just JSON.
        import json as _json

        payload = _json.loads(result)
        assert payload['error'] == 'denied'
        assert payload['error_code'] == 'AccessDeniedException'
        assert 'remediation' in payload
        ctx.error.assert_awaited_with('denied')

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_call_api_non_clienterror_still_raises(self, mock_client):
        """RuntimeError (non-ClientError) must still bubble up — only ClientError is caught."""
        mock_client.call.side_effect = RuntimeError('boom')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import call_api

        with pytest.raises(RuntimeError):
            await call_api(ctx, operation='ListAgentSpaces', params={})

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_get_scan_status_clienterror_returns_structured(self, mock_scanner):
        """Test get scan status clienterror returns structured."""
        from botocore.exceptions import ClientError

        mock_scanner.get_status = AsyncMock(
            side_effect=ClientError(
                {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'gone'}},
                'BatchGetCodeReviewJobs',
            )
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_scan_status

        result = await get_scan_status(ctx, scan_id='scan-1')
        import json as _json

        payload = _json.loads(result)
        assert payload['error_code'] == 'ResourceNotFoundException'

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_get_scan_findings_clienterror_returns_structured(self, mock_scanner):
        """Test get scan findings clienterror returns structured."""
        from botocore.exceptions import ClientError

        mock_scanner.get_findings = AsyncMock(
            side_effect=ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'slow down'}},
                'ListFindings',
            )
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_scan_findings

        result = await get_scan_findings(ctx, scan_id='scan-1', severity=None)
        import json as _json

        assert _json.loads(result)['error_code'] == 'ThrottlingException'

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_list_scans_clienterror_returns_structured(self, mock_state):
        """Test list scans clienterror returns structured."""
        from botocore.exceptions import ClientError

        mock_state.list_scans.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'no'}},
            'ListScans',
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import list_scans

        result = await list_scans(ctx)
        import json as _json

        assert _json.loads(result)['error_code'] == 'AccessDeniedException'

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_stop_scan_clienterror_returns_structured(self, mock_scanner):
        """Test stop scan clienterror returns structured."""
        from botocore.exceptions import ClientError

        mock_scanner.stop_scan = AsyncMock(
            side_effect=ClientError(
                {'Error': {'Code': 'ConflictException', 'Message': 'conflict'}},
                'StopCodeReviewJob',
            )
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import stop_scan

        result = await stop_scan(ctx, scan_id='scan-1')
        import json as _json

        assert _json.loads(result)['error_code'] == 'ConflictException'

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_setup_check_clienterror_returns_structured(self, mock_client, mock_state):
        """Test setup check clienterror returns structured."""
        from botocore.exceptions import ClientError

        mock_state.get_config.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}},
            'GetConfig',
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        import json as _json

        assert _json.loads(result)['error_code'] == 'AccessDeniedException'

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_setup_clienterror_returns_structured(self, mock_client, mock_state):
        """Test setup clienterror returns structured."""
        from botocore.exceptions import ClientError

        mock_client.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'no sts'}},
            'GetCallerIdentity',
        )
        mock_state.get_config.return_value = {}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup

        result = await setup(ctx, name='n', agent_space_id=None, service_role_arn=None)
        import json as _json

        assert _json.loads(result)['error_code'] == 'AccessDeniedException'

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path', new=AsyncMock(return_value='.')
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_start_security_scan_clienterror_returns_structured(
        self, mock_state, mock_scanner
    ):
        """ClientError surfaced from start_security_scan returns structured payload."""
        from botocore.exceptions import ClientError

        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'b',
        }
        mock_scanner.start_scan = AsyncMock(
            side_effect=ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'bad input'}},
                'StartCodeReviewJob',
            )
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        result = await start_security_scan(ctx, path='.', title='t')
        import json as _json

        assert _json.loads(result)['error_code'] == 'ValidationException'


class TestStartDiffScan:
    """Tests for start_diff_scan tool."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path', new=AsyncMock(return_value='.')
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_success(self, mock_state, mock_scanner):
        """Delegates to scanner.start_diff_scan when configured."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'bucket',
        }
        mock_scanner.start_diff_scan = AsyncMock(
            return_value={'scan_id': 'scan-diff-1', 'scan_type': 'DIFF'}
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_diff_scan

        result = await start_diff_scan(ctx, path='.', base_ref='HEAD', title='diff-test')
        assert 'scan-diff-1' in result
        assert 'DIFF' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_not_configured(self, mock_state):
        """Returns error when agent_space_id missing."""
        mock_state.get_config.return_value = {}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_diff_scan

        result = await start_diff_scan(ctx, path='.', base_ref='HEAD', title=None)
        assert 'Not configured' in result

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path',
        new=AsyncMock(return_value='/tmp/test'),
    )
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._ensure_s3_bucket')
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    async def test_lazily_creates_bucket(self, mock_scanner, mock_ensure_bucket, mock_state):
        """Calls _ensure_s3_bucket when bucket not yet configured."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
        }
        mock_scanner.start_diff_scan = AsyncMock(return_value={'scan_id': 'scan-123'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_diff_scan

        result = await start_diff_scan(ctx, path='/tmp/test', base_ref='HEAD', title=None)
        mock_ensure_bucket.assert_called_once_with(mock_state.get_config.return_value)
        assert 'scan-123' in result


class TestStartThreatModelReview:
    """Tests for the start_threat_model_review tool."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path',
        new=AsyncMock(side_effect=lambda ctx, p, **kw: p),
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_success(self, mock_state, mock_client, mock_scanner):
        """Delegates to scanner.start_threat_model_review when configured."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            'threat_model_s3_bucket': 'tm-bucket',
        }
        mock_scanner.start_threat_model_review = AsyncMock(
            return_value={'scan_id': 'tm-scan-1', 'scan_type': 'THREAT_MODEL'}
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_threat_model_review

        result = await start_threat_model_review(
            ctx, path='/abs/path', specs=['/abs/path/design.md'], title='tm-test'
        )
        assert 'tm-scan-1' in result
        mock_scanner.start_threat_model_review.assert_called_once_with(
            path='/abs/path', specs=['/abs/path/design.md'], title='ide-tm-test'
        )

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_not_configured(self, mock_state):
        """Returns error when agent_space_id/service_role missing."""
        mock_state.get_config.return_value = {}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_threat_model_review

        result = await start_threat_model_review(ctx, path='.', specs=[], title=None)
        assert 'Not configured' in result

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path',
        new=AsyncMock(side_effect=lambda ctx, p, **kw: p),
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_lazy_creates_threat_model_bucket(self, mock_state, mock_client, mock_scanner):
        """When threat_model_s3_bucket missing, _ensure_s3_bucket creates+registers it."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
        }
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.create_s3_bucket.return_value = 'security-agent-threat-model-123-us-east-1'
        mock_client.get_agent_space.return_value = {
            'name': 'sec',
            'awsResources': {'iamRoles': ['arn:role'], 's3Buckets': []},
        }
        mock_state.update_config = MagicMock()
        mock_scanner.start_threat_model_review = AsyncMock(return_value={'scan_id': 'tm-scan-1'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_threat_model_review

        await start_threat_model_review(ctx, path='/abs', specs=['/abs/design.md'], title='t')
        # Bucket creation called with the threat-model name
        mock_client.create_s3_bucket.assert_called_once()
        bucket_arg = mock_client.create_s3_bucket.call_args.args[0]
        assert bucket_arg.startswith('security-agent-threat-model-')
        # Registered on agent space
        mock_client.update_agent_space.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        'awslabs.security_agent_mcp_server.server._validate_path',
        new=AsyncMock(side_effect=lambda ctx, p, **kw: p),
    )
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_unexpected_error_propagates(self, mock_state, mock_scanner):
        """Non-ClientError surfaces via ctx.error and re-raises."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            'threat_model_s3_bucket': 'tm-bucket',
        }
        mock_scanner.start_threat_model_review = AsyncMock(side_effect=RuntimeError('boom'))
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_threat_model_review

        with pytest.raises(RuntimeError):
            await start_threat_model_review(ctx, path='.', specs=['/x'], title=None)
        ctx.error.assert_awaited()


class TestEnsureS3BucketHelper:
    """Tests for the _ensure_s3_bucket helper used by both scan tools."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_skips_when_already_configured(self, mock_state, mock_client):
        """If bucket already in config, helper returns immediately without API calls."""
        from awslabs.security_agent_mcp_server.server import _ensure_s3_bucket

        config = {'s3_bucket': 'already-set', 'agent_space_id': 'as-1'}
        _ensure_s3_bucket(config, 'scans')
        mock_client.get_caller_identity.assert_not_called()
        mock_client.create_s3_bucket.assert_not_called()

    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    def test_handles_bucket_already_owned(self, mock_state, mock_client):
        """BucketAlreadyOwnedByYou is swallowed (idempotent setup)."""
        from awslabs.security_agent_mcp_server.server import _ensure_s3_bucket
        from botocore.exceptions import ClientError

        config = {'agent_space_id': 'as-1'}
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.create_s3_bucket.side_effect = ClientError(
            {'Error': {'Code': 'BucketAlreadyOwnedByYou', 'Message': 'owned'}},
            'CreateBucket',
        )
        mock_client.get_agent_space.return_value = {
            'name': 'sec',
            'awsResources': {'iamRoles': [], 's3Buckets': []},
        }
        # Should not raise
        _ensure_s3_bucket(config, 'scans')
        # Despite create error, bucket still gets registered with the agent space
        mock_client.update_agent_space.assert_called_once()

    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    def test_unexpected_create_error_raises(self, mock_state, mock_client):
        """Non-BucketAlreadyOwnedByYou ClientError surfaces."""
        from awslabs.security_agent_mcp_server.server import _ensure_s3_bucket
        from botocore.exceptions import ClientError

        config = {'agent_space_id': 'as-1'}
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.create_s3_bucket.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'no'}}, 'CreateBucket'
        )
        with pytest.raises(ClientError):
            _ensure_s3_bucket(config, 'scans')


class TestValidatePath:
    """Tests for _validate_path workspace boundary enforcement."""

    @pytest.mark.asyncio
    async def test_valid_path_within_workspace(self, tmp_path):
        """Valid path within WORKSPACE_ROOT resolves successfully."""
        import awslabs.security_agent_mcp_server.server as srv

        subdir = tmp_path / 'project'
        subdir.mkdir()
        original = srv._ALLOWED_ROOT
        srv._ALLOWED_ROOT = str(tmp_path)
        try:
            ctx = MagicMock()
            result = await srv._validate_path(ctx, str(subdir))
            assert result == str(subdir.resolve())
        finally:
            srv._ALLOWED_ROOT = original

    @pytest.mark.asyncio
    async def test_path_outside_workspace_raises(self, tmp_path):
        """Path outside WORKSPACE_ROOT raises ValueError."""
        import awslabs.security_agent_mcp_server.server as srv

        original = srv._ALLOWED_ROOT
        srv._ALLOWED_ROOT = str(tmp_path / 'workspace')
        (tmp_path / 'workspace').mkdir()
        try:
            ctx = MagicMock()
            with pytest.raises(ValueError, match='outside the allowed workspace'):
                await srv._validate_path(ctx, '/etc')
        finally:
            srv._ALLOWED_ROOT = original

    @pytest.mark.asyncio
    async def test_nonexistent_dir_raises(self, tmp_path):
        """Non-existent directory raises ValueError."""
        import awslabs.security_agent_mcp_server.server as srv

        original = srv._ALLOWED_ROOT
        srv._ALLOWED_ROOT = str(tmp_path)
        try:
            ctx = MagicMock()
            with pytest.raises(ValueError, match='does not exist'):
                await srv._validate_path(ctx, str(tmp_path / 'nonexistent'))
        finally:
            srv._ALLOWED_ROOT = original

    @pytest.mark.asyncio
    async def test_file_validation(self, tmp_path):
        """File path validates with must_be_dir=False."""
        import awslabs.security_agent_mcp_server.server as srv

        f = tmp_path / 'spec.md'
        f.write_text('hello')
        original = srv._ALLOWED_ROOT
        srv._ALLOWED_ROOT = str(tmp_path)
        try:
            ctx = MagicMock()
            result = await srv._validate_path(ctx, str(f), must_be_dir=False)
            assert result == str(f.resolve())
        finally:
            srv._ALLOWED_ROOT = original

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises(self, tmp_path):
        """Non-existent file raises ValueError with must_be_dir=False."""
        import awslabs.security_agent_mcp_server.server as srv

        original = srv._ALLOWED_ROOT
        srv._ALLOWED_ROOT = str(tmp_path)
        try:
            ctx = MagicMock()
            with pytest.raises(ValueError, match='does not exist'):
                await srv._validate_path(ctx, str(tmp_path / 'nofile.md'), must_be_dir=False)
        finally:
            srv._ALLOWED_ROOT = original


class TestClientPrefix:
    """Tests for _client_prefix."""

    def test_extracts_client_name(self):
        """Extracts and kebab-cases client name from session."""
        from awslabs.security_agent_mcp_server.server import _client_prefix

        ctx = MagicMock()
        ctx.session.client_params.clientInfo.name = 'Kiro IDE'
        assert _client_prefix(ctx) == 'kiro-ide'

    def test_none_session_returns_fallback(self):
        """Returns 'ide' when session is None."""
        from awslabs.security_agent_mcp_server.server import _client_prefix

        ctx = MagicMock()
        ctx.session = None
        assert _client_prefix(ctx) == 'ide'

    def test_non_string_name_returns_fallback(self):
        """Returns 'ide' when name is not a string."""
        from awslabs.security_agent_mcp_server.server import _client_prefix

        ctx = MagicMock()
        ctx.session.client_params.clientInfo.name = 123
        assert _client_prefix(ctx) == 'ide'

    def test_attribute_error_returns_fallback(self):
        """Returns 'ide' on AttributeError."""
        from awslabs.security_agent_mcp_server.server import _client_prefix

        ctx = MagicMock()
        type(ctx.session.client_params).clientInfo = property(
            lambda self: (_ for _ in ()).throw(AttributeError)
        )
        assert _client_prefix(ctx) == 'ide'


class TestStartDiffScanErrors:
    """Tests for start_diff_scan error paths."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._validate_path')
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_client_error_returns_structured(
        self, mock_client, mock_state, mock_scanner, mock_validate
    ):
        """ClientError returns structured error JSON."""
        from awslabs.security_agent_mcp_server.server import start_diff_scan
        from botocore.exceptions import ClientError

        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'bucket',
        }
        mock_validate.return_value = '.'
        mock_scanner.start_diff_scan = AsyncMock(
            side_effect=ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'no'}}, 'Op')
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await start_diff_scan(ctx, path='.', base_ref='HEAD')
        assert 'error' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_value_error_returns_message(self, mock_state):
        """ValueError from _validate_path returns error message."""
        from awslabs.security_agent_mcp_server.server import start_diff_scan

        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'bucket',
        }
        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await start_diff_scan(ctx, path='/etc/passwd', base_ref='HEAD')
        assert 'error' in result


class TestStartThreatModelErrors:
    """Tests for start_threat_model_review error paths."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._validate_path')
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_client_error_returns_structured(
        self, mock_client, mock_state, mock_scanner, mock_validate
    ):
        """ClientError returns structured error JSON."""
        from awslabs.security_agent_mcp_server.server import start_threat_model_review
        from botocore.exceptions import ClientError

        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            'threat_model_s3_bucket': 'bucket',
        }
        mock_validate.return_value = '.'
        mock_scanner.start_threat_model_review = AsyncMock(
            side_effect=ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'no'}}, 'Op')
        )
        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await start_threat_model_review(ctx, path='.', specs=[])
        assert 'error' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_value_error_returns_message(self, mock_state):
        """ValueError from _validate_path returns error message."""
        from awslabs.security_agent_mcp_server.server import start_threat_model_review

        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            'threat_model_s3_bucket': 'bucket',
        }
        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await start_threat_model_review(ctx, path='/etc/passwd', specs=[])
        assert 'error' in result
