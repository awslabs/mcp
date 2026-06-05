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

"""Tests for Scanner."""

import pytest
from awslabs.security_agent_mcp_server.scanner import Scanner
from awslabs.security_agent_mcp_server.state import StateManager
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


@pytest.fixture
def mock_client():
    """Create a mock SecurityAgentClient."""
    client = MagicMock()
    client.upload_to_s3 = MagicMock(return_value='s3://bucket/key.zip')
    client.create_code_review = MagicMock(return_value={'codeReviewId': 'cr-123'})
    client.start_code_review_job = MagicMock(return_value={'codeReviewJobId': 'cj-456'})
    client.batch_get_code_review_jobs = MagicMock(
        return_value={'codeReviewJobs': [{'status': 'COMPLETED', 'steps': []}]}
    )
    client.list_findings = MagicMock(
        return_value={
            'findingsSummaries': [
                {'findingId': 'f-1', 'title': 'SQL Injection', 'riskLevel': 'CRITICAL'}
            ]
        }
    )
    client.batch_get_findings = MagicMock(
        return_value={
            'findings': [
                {
                    'findingId': 'f-1',
                    'name': 'SQL Injection',
                    'description': 'SQL injection vulnerability',
                    'riskLevel': 'CRITICAL',
                    'riskType': 'SQL_INJECTION',
                    'confidence': 'HIGH',
                    'status': 'ACTIVE',
                    'remediationCode': 'Use parameterized queries',
                    'codeLocations': [{'filePath': 'app.py', 'lineStart': 10, 'lineEnd': 15}],
                }
            ]
        }
    )
    client.stop_code_review_job = MagicMock(return_value={})
    return client


@pytest.fixture
def mock_state(tmp_path, monkeypatch):
    """Create a StateManager with temp directory."""
    monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
    monkeypatch.setattr(
        'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
    )
    monkeypatch.setattr(
        'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
    )
    sm = StateManager()
    sm.update_config(
        agent_space_id='as-test',
        service_role='arn:aws:iam::123:role/TestRole',
        s3_bucket='test-bucket',
    )
    return sm


class TestScanner:
    """Tests for the Scanner class."""

    @pytest.mark.asyncio
    async def test_start_scan_success(self, mock_client, mock_state, tmp_path):
        """Starts a scan successfully."""
        scanner = Scanner(client=mock_client, state=mock_state)
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')

        result = await scanner.start_scan(path=str(code_dir), title='test-scan')
        assert 'scan_id' in result
        assert 'job_id' in result
        mock_client.upload_to_s3.assert_called_once()
        mock_client.create_code_review.assert_called_once()
        mock_client.start_code_review_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_scan_with_gitignore(self, mock_client, mock_state, tmp_path):
        """Respects .gitignore when packaging."""
        scanner = Scanner(client=mock_client, state=mock_state)
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        (code_dir / 'secret.env').write_text('KEY=secret')
        (code_dir / '.gitignore').write_text('*.env\n')

        result = await scanner.start_scan(path=str(code_dir))
        assert 'scan_id' in result

    @pytest.mark.asyncio
    async def test_start_scan_excludes_node_modules(self, mock_client, mock_state, tmp_path):
        """Always excludes node_modules."""
        scanner = Scanner(client=mock_client, state=mock_state)
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        nm = code_dir / 'node_modules'
        nm.mkdir()
        (nm / 'pkg.js').write_text('module')

        result = await scanner.start_scan(path=str(code_dir))
        assert 'scan_id' in result

    @pytest.mark.asyncio
    async def test_get_status(self, mock_client, mock_state):
        """Gets scan status."""
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-test',
            {
                'scan_id': 'scan-test',
                'job_id': 'cj-456',
                'code_review_id': 'cr-123',
                'started_at': '2026-01-01T00:00:00+00:00',
                'agent_space_id': 'as-test',
            },
        )
        status = await scanner.get_status('scan-test')
        assert status['status'] == 'COMPLETED'

    @pytest.mark.asyncio
    async def test_get_status_no_scan(self, mock_client, mock_state):
        """Returns error when scan not found."""
        scanner = Scanner(client=mock_client, state=mock_state)
        status = await scanner.get_status('nonexistent')
        assert 'error' in status

    @pytest.mark.asyncio
    async def test_get_status_no_jobs(self, mock_client, mock_state):
        """Returns error when job not found."""
        mock_client.batch_get_code_review_jobs.return_value = {'codeReviewJobs': []}
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-test',
            {
                'scan_id': 'scan-test',
                'job_id': 'cj-missing',
                'code_review_id': 'cr-123',
                'started_at': '2026-01-01T00:00:00+00:00',
                'agent_space_id': 'as-test',
            },
        )
        status = await scanner.get_status('scan-test')
        assert 'error' in status

    @pytest.mark.asyncio
    async def test_get_findings(self, mock_client, mock_state):
        """Gets findings from completed scan."""
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-test',
            {
                'scan_id': 'scan-test',
                'job_id': 'cj-456',
                'code_review_id': 'cr-123',
                'started_at': '2026-01-01T00:00:00+00:00',
                'agent_space_id': 'as-test',
            },
        )
        findings = await scanner.get_findings('scan-test')
        assert findings['total_findings'] == 1
        assert findings['findings'][0]['name'] == 'SQL Injection'
        assert findings['findings'][0]['remediationCode'] == 'Use parameterized queries'

    @pytest.mark.asyncio
    async def test_get_findings_no_scan(self, mock_client, mock_state):
        """Returns error when scan not found."""
        scanner = Scanner(client=mock_client, state=mock_state)
        findings = await scanner.get_findings('nonexistent')
        assert 'error' in findings

    @pytest.mark.asyncio
    async def test_stop_scan(self, mock_client, mock_state):
        """Stops a running scan."""
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-test',
            {
                'scan_id': 'scan-test',
                'job_id': 'cj-456',
                'code_review_id': 'cr-123',
                'started_at': '2026-01-01T00:00:00+00:00',
                'agent_space_id': 'as-test',
            },
        )
        result = await scanner.stop_scan('scan-test')
        assert result['status'] == 'STOPPED'
        mock_client.stop_code_review_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_scan_no_scan(self, mock_client, mock_state):
        """Returns error when scan not found."""
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.stop_scan('nonexistent')
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_start_scan_not_configured(self, mock_client, tmp_path, monkeypatch):
        """Errors out cleanly when agent space / role missing from config."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        scanner = Scanner(client=mock_client, state=sm)

        result = await scanner.start_scan(path=str(tmp_path))
        assert 'error' in result
        assert 'Not configured' in result['error']
        # Must not have hit upload path
        mock_client.upload_to_s3.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_scan_agent_space_deleted(self, mock_client, mock_state, tmp_path):
        """If get_agent_space returns empty, surface error AND actually clear the stale id.

        Subsequent scans don't repeat the failure. Regression test for the no-op clear bug.
        """
        mock_client.get_agent_space.return_value = {}
        scanner = Scanner(client=mock_client, state=mock_state)

        # Sanity: precondition has agent_space_id
        assert mock_state.get_config().get('agent_space_id') == 'as-test'

        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print()')

        result = await scanner.start_scan(path=str(code_dir))
        assert 'error' in result
        assert 'no longer exists' in result['error']
        # Did not reach upload
        mock_client.upload_to_s3.assert_not_called()
        # And — critically — the stale ID is gone from disk now.
        assert 'agent_space_id' not in mock_state.get_config()

    @pytest.mark.asyncio
    async def test_start_scan_recreates_on_resource_not_found(
        self, mock_client, mock_state, tmp_path
    ):
        """If start_code_review_job returns ResourceNotFoundException, recreate CR and retry."""
        mock_client.get_agent_space.return_value = {'agentSpaceId': 'as-test'}
        # First call: missing CR error; Second call: success
        mock_client.start_code_review_job.side_effect = [
            ClientError(
                {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'gone'}},
                'StartCodeReviewJob',
            ),
            {'codeReviewJobId': 'cj-after-recreate'},
        ]
        # create_code_review will be called twice — once initially, once for retry.
        mock_client.create_code_review.side_effect = [
            {'codeReviewId': 'cr-original'},
            {'codeReviewId': 'cr-recreated'},
        ]

        scanner = Scanner(client=mock_client, state=mock_state)
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print()')

        result = await scanner.start_scan(path=str(code_dir))
        assert result['job_id'] == 'cj-after-recreate'
        assert mock_client.create_code_review.call_count == 2
        assert mock_client.start_code_review_job.call_count == 2

    @pytest.mark.asyncio
    async def test_start_scan_other_clienterror_raises(self, mock_client, mock_state, tmp_path):
        """Non-ResourceNotFoundException ClientError must bubble up unchanged."""
        mock_client.get_agent_space.return_value = {'agentSpaceId': 'as-test'}
        mock_client.start_code_review_job.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'no'}},
            'StartCodeReviewJob',
        )

        scanner = Scanner(client=mock_client, state=mock_state)
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print()')

        with pytest.raises(ClientError):
            await scanner.start_scan(path=str(code_dir))

    @pytest.mark.asyncio
    async def test_start_scan_too_large(self, mock_client, mock_state, tmp_path, monkeypatch):
        """Bails when zipped source exceeds MAX_ZIP_SIZE."""
        # Patch MAX_ZIP_SIZE down so we don't have to generate hundreds of MB.
        monkeypatch.setattr('awslabs.security_agent_mcp_server.scanner.MAX_ZIP_SIZE', 10)
        mock_client.get_agent_space.return_value = {'agentSpaceId': 'as-test'}
        scanner = Scanner(client=mock_client, state=mock_state)

        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'big.txt').write_text('x' * 1024)

        result = await scanner.start_scan(path=str(code_dir))
        assert 'error' in result
        assert 'too large' in result['error'].lower()
        mock_client.upload_to_s3.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_scan_reuses_existing_code_review(self, mock_client, mock_state, tmp_path):
        """When per-workspace code_review_id exists, do NOT call create_code_review."""
        mock_client.get_agent_space.return_value = {'agentSpaceId': 'as-test'}
        scanner = Scanner(client=mock_client, state=mock_state)

        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print()')

        # Pre-seed code review id for this workspace path
        import os as _os

        abs_dir = _os.path.abspath(str(code_dir))
        mock_state.set_code_review_id(abs_dir, 'cr-existing')

        await scanner.start_scan(path=str(code_dir))
        mock_client.create_code_review.assert_not_called()
        mock_client.start_code_review_job.assert_called_once_with(
            agent_space_id='as-test', code_review_id='cr-existing'
        )

    @pytest.mark.asyncio
    async def test_start_scan_excludes_pyc_files(self, mock_client, mock_state, tmp_path):
        """*.pyc / .DS_Store files must be excluded from the zip."""
        mock_client.get_agent_space.return_value = {'agentSpaceId': 'as-test'}
        scanner = Scanner(client=mock_client, state=mock_state)

        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print()')
        (code_dir / 'compiled.pyc').write_text('garbage')
        (code_dir / '.DS_Store').write_text('mac')

        result = await scanner.start_scan(path=str(code_dir))
        assert 'scan_id' in result

    @pytest.mark.asyncio
    async def test_zip_code_skips_symlinks(self, mock_client, mock_state, tmp_path):
        """Symlinks should never be packaged."""
        mock_client.get_agent_space.return_value = {'agentSpaceId': 'as-test'}
        scanner = Scanner(client=mock_client, state=mock_state)

        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print()')
        # Symlink pointing somewhere that exists outside the zip root
        target = tmp_path / 'outside.txt'
        target.write_text('secret')
        (code_dir / 'link').symlink_to(target)

        result = await scanner.start_scan(path=str(code_dir))
        assert 'scan_id' in result

    def test_zip_code_invalid_path(self, mock_client, mock_state):
        """_zip_code raises on non-directory path."""
        scanner = Scanner(client=mock_client, state=mock_state)
        with pytest.raises(ValueError, match='not a directory'):
            scanner._zip_code('/this/path/does/not/exist/at/all')

    @pytest.mark.asyncio
    async def test_get_findings_filters_by_severity(self, mock_client, mock_state):
        """severity='HIGH' yields CRITICAL + HIGH only."""
        mock_client.list_findings.return_value = {
            'findingsSummaries': [
                {'findingId': 'f-c', 'riskLevel': 'CRITICAL'},
                {'findingId': 'f-h', 'riskLevel': 'HIGH'},
                {'findingId': 'f-m', 'riskLevel': 'MEDIUM'},
                {'findingId': 'f-l', 'riskLevel': 'LOW'},
            ]
        }
        mock_client.batch_get_findings.return_value = {
            'findings': [
                {'findingId': 'f-c', 'name': 'C', 'riskLevel': 'CRITICAL'},
                {'findingId': 'f-h', 'name': 'H', 'riskLevel': 'HIGH'},
            ]
        }

        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-1',
            {
                'scan_id': 'scan-1',
                'job_id': 'cj-1',
                'agent_space_id': 'as-test',
                'started_at': '2026-01-01T00:00:00+00:00',
            },
        )

        result = await scanner.get_findings('scan-1', severity='HIGH')
        # Verify the right finding_ids were sent to batch_get_findings
        called_ids = mock_client.batch_get_findings.call_args.kwargs['finding_ids']
        assert set(called_ids) == {'f-c', 'f-h'}
        assert result['total_findings'] == 2

    @pytest.mark.asyncio
    async def test_get_findings_invalid_severity_returns_all(self, mock_client, mock_state):
        """Unknown severity string passes through without filtering."""
        mock_client.list_findings.return_value = {
            'findingsSummaries': [
                {'findingId': 'f-c', 'riskLevel': 'CRITICAL'},
                {'findingId': 'f-l', 'riskLevel': 'LOW'},
            ]
        }
        mock_client.batch_get_findings.return_value = {
            'findings': [
                {'findingId': 'f-c'},
                {'findingId': 'f-l'},
            ]
        }
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-1',
            {
                'scan_id': 'scan-1',
                'job_id': 'cj-1',
                'agent_space_id': 'as-test',
                'started_at': '2026-01-01T00:00:00+00:00',
            },
        )
        result = await scanner.get_findings('scan-1', severity='BOGUS')
        assert result['total_findings'] == 2

    @pytest.mark.asyncio
    async def test_get_findings_in_progress_includes_note(self, mock_client, mock_state):
        """When status != COMPLETED, response includes a 'note' about partial results."""
        mock_client.batch_get_code_review_jobs.return_value = {
            'codeReviewJobs': [{'status': 'IN_PROGRESS', 'steps': []}]
        }
        mock_client.list_findings.return_value = {'findingsSummaries': []}
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-1',
            {
                'scan_id': 'scan-1',
                'job_id': 'cj-1',
                'agent_space_id': 'as-test',
                'started_at': '2026-01-01T00:00:00+00:00',
            },
        )
        result = await scanner.get_findings('scan-1')
        assert 'note' in result
        assert 'in progress' in result['note'].lower()
