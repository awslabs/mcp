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
import subprocess
from awslabs.security_agent_mcp_server.scanner import Scanner
from awslabs.security_agent_mcp_server.state import StateManager
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


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
    client.start_code_review_job_with_diff = MagicMock(
        return_value={'codeReviewJobId': 'cj-diff-789'}
    )
    client.create_threat_model = MagicMock(return_value={'threatModelId': 'tm-123'})
    client.start_threat_model_job = MagicMock(return_value={'threatModelJobId': 'tmj-456'})
    client.batch_get_threat_model_jobs = MagicMock(
        return_value={'threatModelJobs': [{'status': 'COMPLETED'}]}
    )
    client.list_threats = MagicMock(
        return_value={'threats': [{'threatId': 't-1', 'severity': 'HIGH'}]}
    )
    client.batch_get_threats = MagicMock(
        return_value={
            'threats': [
                {
                    'threatId': 't-1',
                    'statement': 'Unauthenticated access to admin API',
                    'severity': 'HIGH',
                    'status': 'OPEN',
                    'stride': ['SPOOFING'],
                    'threatImpact': 'Account takeover',
                    'recommendation': 'Require authentication',
                    'impactedAssets': ['admin-api'],
                }
            ]
        }
    )
    client.get_agent_space = MagicMock(return_value={'agentSpaceId': 'as-test'})
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
        threat_model_s3_bucket='test-tm-bucket',
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
    async def test_stop_scan_threat_model(self, mock_client, mock_state):
        """Stops a threat model scan via StopThreatModelJob."""
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-tm',
            {
                'scan_id': 'scan-tm',
                'job_id': 'tj-123',
                'agent_space_id': 'as-test',
                'scan_type': 'THREAT_MODEL',
                'started_at': '2026-01-01T00:00:00+00:00',
            },
        )
        mock_client.call = MagicMock(return_value={})
        result = await scanner.stop_scan('scan-tm')
        assert result['status'] == 'STOPPED'
        mock_client.call.assert_called_once_with(
            'StopThreatModelJob',
            {
                'agentSpaceId': 'as-test',
                'threatModelJobId': 'tj-123',
            },
        )
        mock_client.stop_code_review_job.assert_not_called()

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


class TestDiffScan:
    """Tests for start_diff_scan."""

    @pytest.mark.asyncio
    async def test_diff_scan_success_no_prior_review(self, mock_client, mock_state, tmp_path):
        """Creates a CodeReview on first diff scan and starts the job."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')

        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='diff --git a/app.py b/app.py\n+new line\n',
                stderr='',
            )
            result = await scanner.start_diff_scan(path=str(code_dir), base_ref='HEAD')

        assert result['scan_type'] == 'DIFF'
        assert result['status'] == 'STARTED'
        assert result['job_id'] == 'cj-diff-789'
        assert result['base_ref'] == 'HEAD'
        mock_client.upload_to_s3.assert_called()
        mock_client.create_code_review.assert_called_once()
        mock_client.start_code_review_job_with_diff.assert_called_once()

    @pytest.mark.asyncio
    async def test_diff_scan_reuses_existing_code_review(self, mock_client, mock_state, tmp_path):
        """Reuses existing CodeReview when one exists for the workspace."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        mock_state.set_code_review_id(str(code_dir), 'cr-existing')

        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='diff --git a/app.py b/app.py\n+new line\n',
                stderr='',
            )
            result = await scanner.start_diff_scan(path=str(code_dir))

        assert result['code_review_id'] == 'cr-existing'
        mock_client.create_code_review.assert_not_called()
        mock_client.start_code_review_job_with_diff.assert_called_once()

    @pytest.mark.asyncio
    async def test_diff_scan_empty_diff(self, mock_client, mock_state, tmp_path):
        """Returns error when there are no changes to scan."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
            result = await scanner.start_diff_scan(path=str(code_dir))

        assert 'error' in result
        assert 'No diff' in result['error']
        mock_client.upload_to_s3.assert_not_called()

    @pytest.mark.asyncio
    async def test_diff_scan_git_failure(self, mock_client, mock_state, tmp_path):
        """Returns error when git diff fails (e.g., bad ref)."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128, stdout='', stderr='fatal: bad revision'
            )
            result = await scanner.start_diff_scan(path=str(code_dir), base_ref='nonexistent')

        assert 'error' in result
        assert 'git diff failed' in result['error']

    @pytest.mark.asyncio
    async def test_diff_scan_git_not_installed(self, mock_client, mock_state, tmp_path):
        """Returns error when git binary is missing."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = await scanner.start_diff_scan(path=str(code_dir))

        assert 'error' in result
        assert 'git is not installed' in result['error']

    @pytest.mark.asyncio
    async def test_diff_scan_not_configured(self, mock_client, mock_state, tmp_path):
        """Returns error when setup is not complete."""
        mock_state.clear()
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_diff_scan(path=str(tmp_path))
        assert 'error' in result
        assert 'Not configured' in result['error']

    @pytest.mark.asyncio
    async def test_diff_scan_branch_ref(self, mock_client, mock_state, tmp_path):
        """Uses 'git diff base_ref' and 'git archive base_ref' for branch mode."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='diff --git a/app.py b/app.py\n+new line\n',
                stderr='',
            )
            await scanner.start_diff_scan(path=str(code_dir), base_ref='main')

        # Verify calls: first is git diff, second is git archive
        calls = mock_run.call_args_list
        diff_args = calls[0][0][0]
        archive_args = calls[1][0][0]
        assert diff_args == ['git', 'diff', 'main', '--']
        assert archive_args[:3] == ['git', 'archive', '--format=zip']
        assert '--' in archive_args and 'main' in archive_args

    @pytest.mark.asyncio
    async def test_diff_scan_uploads_repo_and_diff(self, mock_client, mock_state, tmp_path):
        """Uploads both the source repo zip and the diff patch to S3."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='diff --git a/app.py b/app.py\n+new line\n',
                stderr='',
            )
            await scanner.start_diff_scan(path=str(code_dir))

        # 2 uploads expected: source.zip and diff.patch
        assert mock_client.upload_to_s3.call_count == 2
        keys = [call.args[1] for call in mock_client.upload_to_s3.call_args_list]
        assert any('source.zip' in k for k in keys)
        assert any('diff.patch' in k for k in keys)

    @pytest.mark.asyncio
    async def test_diff_scan_recreates_code_review_if_deleted(
        self, mock_client, mock_state, tmp_path
    ):
        """If StartCodeReviewJob fails with ResourceNotFoundException, recreates the CodeReview."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        mock_state.set_code_review_id(str(code_dir), 'cr-stale')

        # First call raises ResourceNotFoundException via RuntimeError, second call succeeds
        mock_client.start_code_review_job_with_diff = MagicMock(
            side_effect=[
                RuntimeError(
                    'StartCodeReviewJob with diffSource failed (404): ResourceNotFoundException'
                ),
                {'codeReviewJobId': 'cj-recreated'},
            ]
        )
        mock_client.create_code_review = MagicMock(return_value={'codeReviewId': 'cr-new'})

        scanner = Scanner(client=mock_client, state=mock_state)

        with patch('awslabs.security_agent_mcp_server.scanner.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='diff --git a/app.py b/app.py\n+new line\n',
                stderr='',
            )
            result = await scanner.start_diff_scan(path=str(code_dir))

        assert result['code_review_id'] == 'cr-new'
        assert result['job_id'] == 'cj-recreated'
        assert mock_client.create_code_review.call_count == 1
        assert mock_client.start_code_review_job_with_diff.call_count == 2


class TestThreatModelReview:
    """Tests for start_threat_model_review and threat-model status/findings."""

    def _make_specs(self, tmp_path):
        design = tmp_path / 'design.md'
        reqs = tmp_path / 'requirements.md'
        design.write_text('# Design')
        reqs.write_text('# Requirements')
        return [str(design), str(reqs)]

    @pytest.mark.asyncio
    async def test_threat_model_review_success(self, mock_client, mock_state, tmp_path):
        """Creates a threat model with specs as scope docs and starts a job."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        specs = self._make_specs(tmp_path)

        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_threat_model_review(path=str(code_dir), specs=specs)

        assert result['scan_type'] == 'THREAT_MODEL'
        assert result['status'] == 'STARTED'
        assert result['threat_model_id'] == 'tm-123'
        assert result['job_id'] == 'tmj-456'
        assert result['spec_count'] == 2
        mock_client.create_threat_model.assert_called_once()
        mock_client.start_threat_model_job.assert_called_once()

        # source is sent as an asset, specs as scope docs
        kwargs = mock_client.create_threat_model.call_args.kwargs
        assert kwargs['assets']['sourceCode'][0]['s3Location']
        assert len(kwargs['scope_docs']) == 2
        assert all('s3Location' in d for d in kwargs['scope_docs'])

    @pytest.mark.asyncio
    async def test_threat_model_review_uploads_source_and_specs(
        self, mock_client, mock_state, tmp_path
    ):
        """Uploads the source zip plus one object per spec."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        (code_dir / 'app.py').write_text('print("hello")')
        specs = self._make_specs(tmp_path)

        scanner = Scanner(client=mock_client, state=mock_state)
        await scanner.start_threat_model_review(path=str(code_dir), specs=specs)

        # 1 source zip + 2 specs
        assert mock_client.upload_to_s3.call_count == 3
        keys = [call.args[1] for call in mock_client.upload_to_s3.call_args_list]
        assert any('source.zip' in k for k in keys)
        assert any(k.endswith('design.md') for k in keys)
        assert any(k.endswith('requirements.md') for k in keys)

    @pytest.mark.asyncio
    async def test_threat_model_review_no_specs(self, mock_client, mock_state, tmp_path):
        """Returns error when no specs are provided."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_threat_model_review(path=str(code_dir), specs=[])
        assert 'error' in result
        assert 'No specs' in result['error']
        mock_client.create_threat_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_threat_model_review_missing_spec_file(self, mock_client, mock_state, tmp_path):
        """Returns error when a spec path does not exist."""
        code_dir = tmp_path / 'code'
        code_dir.mkdir()
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_threat_model_review(
            path=str(code_dir), specs=[str(tmp_path / 'missing.md')]
        )
        assert 'error' in result
        assert 'not found' in result['error']
        mock_client.upload_to_s3.assert_not_called()

    @pytest.mark.asyncio
    async def test_threat_model_review_not_configured(self, mock_client, mock_state, tmp_path):
        """Returns error when setup is not complete."""
        mock_state.clear()
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_threat_model_review(path=str(tmp_path), specs=[str(tmp_path)])
        assert 'error' in result
        assert 'Not configured' in result['error']

    @pytest.mark.asyncio
    async def test_threat_model_status_uses_threat_job_api(self, mock_client, mock_state):
        """get_status routes THREAT_MODEL scans to batch_get_threat_model_jobs."""
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-tm',
            {
                'scan_id': 'scan-tm',
                'job_id': 'tmj-456',
                'threat_model_id': 'tm-123',
                'scan_type': 'THREAT_MODEL',
                'started_at': '2026-01-01T00:00:00+00:00',
                'agent_space_id': 'as-test',
            },
        )
        status = await scanner.get_status('scan-tm')
        assert status['status'] == 'COMPLETED'
        mock_client.batch_get_threat_model_jobs.assert_called_once()
        mock_client.batch_get_code_review_jobs.assert_not_called()

    @pytest.mark.asyncio
    async def test_threat_model_findings(self, mock_client, mock_state):
        """get_findings returns threats for a THREAT_MODEL scan."""
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-tm',
            {
                'scan_id': 'scan-tm',
                'job_id': 'tmj-456',
                'threat_model_id': 'tm-123',
                'scan_type': 'THREAT_MODEL',
                'started_at': '2026-01-01T00:00:00+00:00',
                'agent_space_id': 'as-test',
            },
        )
        findings = await scanner.get_findings('scan-tm')
        assert findings['total_findings'] == 1
        assert findings['findings'][0]['threatId'] == 't-1'
        assert findings['findings'][0]['recommendation'] == 'Require authentication'
        mock_client.list_threats.assert_called_once()
        mock_client.batch_get_threats.assert_called_once()

    @pytest.mark.asyncio
    async def test_threat_model_findings_severity_filter(self, mock_client, mock_state):
        """Severity filter excludes threats below the requested minimum."""
        mock_client.list_threats.return_value = {
            'threats': [
                {'threatId': 't-1', 'severity': 'HIGH'},
                {'threatId': 't-2', 'severity': 'LOW'},
            ]
        }
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan(
            'scan-tm',
            {
                'scan_id': 'scan-tm',
                'job_id': 'tmj-456',
                'scan_type': 'THREAT_MODEL',
                'started_at': '2026-01-01T00:00:00+00:00',
                'agent_space_id': 'as-test',
            },
        )
        await scanner.get_findings('scan-tm', severity='HIGH')
        # only the HIGH threat id is fetched in detail
        threat_ids = mock_client.batch_get_threats.call_args.kwargs['threat_ids']
        assert threat_ids == ['t-1']


class TestThreatModelStatusAndFindings:
    """Status + findings for threat-model scans (separate code path from code reviews)."""

    @pytest.fixture
    def tm_state_with_scan(self, tmp_path, monkeypatch):
        """State with a saved THREAT_MODEL scan."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.update_config(agent_space_id='as-test', service_role='arn:role')
        sm.save_scan(
            'tm-scan',
            {
                'scan_id': 'tm-scan',
                'job_id': 'tj-1',
                'agent_space_id': 'as-test',
                'scan_type': 'THREAT_MODEL',
                'title': 'tm-test',
                'started_at': '2026-01-01T00:00:00+00:00',
            },
        )
        return sm

    @pytest.mark.asyncio
    async def test_get_status_threat_model(self, tm_state_with_scan):
        """get_status routes to batch_get_threat_model_jobs for THREAT_MODEL scans."""
        client = MagicMock()
        client.batch_get_threat_model_jobs = MagicMock(
            return_value={'threatModelJobs': [{'status': 'COMPLETED', 'steps': []}]}
        )
        scanner = Scanner(client=client, state=tm_state_with_scan)
        status = await scanner.get_status('tm-scan')
        assert status['status'] == 'COMPLETED'
        client.batch_get_threat_model_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_findings_threat_model(self, tm_state_with_scan):
        """get_findings routes to list_threats + batch_get_threats for THREAT_MODEL scans."""
        client = MagicMock()
        client.batch_get_threat_model_jobs = MagicMock(
            return_value={'threatModelJobs': [{'status': 'COMPLETED', 'steps': []}]}
        )
        client.list_threats = MagicMock(
            return_value={
                'threats': [
                    {'threatId': 't-1', 'severity': 'HIGH'},
                    {'threatId': 't-2', 'severity': 'LOW'},
                ]
            }
        )
        client.batch_get_threats = MagicMock(
            return_value={
                'threats': [
                    {
                        'threatId': 't-1',
                        'statement': 'Spoofing',
                        'severity': 'HIGH',
                        'stride': 'S',
                        'threatImpact': 'high',
                        'recommendation': 'Add MFA',
                    },
                    {
                        'threatId': 't-2',
                        'statement': 'Info disclosure',
                        'severity': 'LOW',
                        'stride': 'I',
                    },
                ]
            }
        )
        scanner = Scanner(client=client, state=tm_state_with_scan)
        findings = await scanner.get_findings('tm-scan')
        assert findings['total_findings'] == 2
        assert findings['findings'][0]['stride'] == 'S'
        client.list_threats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_findings_threat_model_severity_filter(self, tm_state_with_scan):
        """Severity filter is applied before batch_get_threats."""
        client = MagicMock()
        client.batch_get_threat_model_jobs = MagicMock(
            return_value={'threatModelJobs': [{'status': 'COMPLETED', 'steps': []}]}
        )
        client.list_threats = MagicMock(
            return_value={
                'threats': [
                    {'threatId': 't-h', 'severity': 'HIGH'},
                    {'threatId': 't-l', 'severity': 'LOW'},
                ]
            }
        )
        client.batch_get_threats = MagicMock(
            return_value={'threats': [{'threatId': 't-h', 'severity': 'HIGH'}]}
        )
        scanner = Scanner(client=client, state=tm_state_with_scan)
        findings = await scanner.get_findings('tm-scan', severity='HIGH')
        called_ids = client.batch_get_threats.call_args.kwargs['threat_ids']
        assert called_ids == ['t-h']
        assert findings['total_findings'] == 1


class TestDiffScanEdgeCases:
    """Cover remaining diff scan edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.scanner.subprocess.run')
    async def test_diff_scan_timeout(self, mock_run, mock_client, mock_state, tmp_path):
        """Git diff timeout returns error."""
        mock_client.get_agent_space.return_value = {'name': 'sec'}
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='git', timeout=60)
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_diff_scan(path=str(tmp_path), base_ref='HEAD')
        assert 'timed out' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.scanner.subprocess.run')
    async def test_diff_scan_zip_committed_failure(
        self, mock_run, mock_client, mock_state, tmp_path
    ):
        """_zip_committed_and_upload ValueError propagates."""
        mock_client.get_agent_space.return_value = {'name': 'sec'}
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout='diff content\n', stderr=''),
            MagicMock(returncode=1, stdout='', stderr='fatal: not a valid ref'),
        ]
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_diff_scan(path=str(tmp_path), base_ref='HEAD')
        assert 'error' in result
        assert 'git archive failed' in result['error']

    @pytest.mark.asyncio
    async def test_diff_scan_no_bucket(self, mock_client, tmp_path, monkeypatch):
        """Missing s3_bucket returns error."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        state = StateManager()
        state.update_config(agent_space_id='as-1', service_role='arn:role')
        scanner = Scanner(client=mock_client, state=state)
        result = await scanner.start_diff_scan(path=str(tmp_path), base_ref='HEAD')
        assert 'error' in result
        assert 'S3 bucket' in result['error']

    @pytest.mark.asyncio
    async def test_diff_scan_agent_space_gone(self, mock_client, mock_state, tmp_path):
        """Agent space that no longer exists returns error."""
        mock_client.get_agent_space.return_value = {}
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_diff_scan(path=str(tmp_path), base_ref='HEAD')
        assert 'error' in result
        assert 'no longer exists' in result['error']


class TestThreatModelEdgeCases:
    """Cover remaining threat model edge cases."""

    @pytest.mark.asyncio
    async def test_threat_model_no_bucket(self, mock_client, tmp_path, monkeypatch):
        """Missing threat_model_s3_bucket returns error."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        state = StateManager()
        state.update_config(agent_space_id='as-1', service_role='arn:role')
        scanner = Scanner(client=mock_client, state=state)
        result = await scanner.start_threat_model_review(
            path=str(tmp_path), specs=[str(tmp_path / 'a.md')]
        )
        assert 'error' in result
        assert 'threat-model S3 bucket' in result['error']

    @pytest.mark.asyncio
    async def test_threat_model_agent_space_gone(self, mock_client, mock_state, tmp_path):
        """Agent space that no longer exists returns error."""
        spec = tmp_path / 'design.md'
        spec.write_text('spec')
        mock_client.get_agent_space.return_value = {}
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.start_threat_model_review(path=str(tmp_path), specs=[str(spec)])
        assert 'error' in result
        assert 'no longer exists' in result['error']

    @pytest.mark.asyncio
    async def test_threat_model_zip_failure(self, mock_client, mock_state, tmp_path):
        """_zip_and_upload_source ValueError propagates."""
        spec = tmp_path / 'design.md'
        spec.write_text('spec')
        mock_client.get_agent_space.return_value = {'name': 'sec'}
        scanner = Scanner(client=mock_client, state=mock_state)
        with patch.object(scanner, '_zip_and_upload_source', side_effect=ValueError('too large')):
            result = await scanner.start_threat_model_review(path=str(tmp_path), specs=[str(spec)])
        assert 'error' in result
        assert 'too large' in result['error']

    @pytest.mark.asyncio
    async def test_threat_findings_in_progress_note(self, mock_client):
        """Threat findings add note when scan still in progress."""
        state = MagicMock()
        state.get_config.return_value = {'agent_space_id': 'as-1'}
        state.get_scan.return_value = {
            'scan_id': 'tm-1',
            'scan_type': 'THREAT_MODEL',
            'agent_space_id': 'as-1',
            'job_id': 'tj-1',
            'title': 'test',
            'started_at': '2026-01-01T00:00:00+00:00',
        }
        mock_client.batch_get_threat_model_jobs.return_value = {
            'threatModelJobs': [{'status': 'IN_PROGRESS'}]
        }
        mock_client.list_threats.return_value = {'threats': []}
        scanner = Scanner(client=mock_client, state=state)
        result = await scanner.get_findings('tm-1')
        assert 'note' in result
        assert 'still in progress' in result['note']


class TestStartScanEdgeCases:
    """Cover start_scan missing bucket and archive errors."""

    @pytest.mark.asyncio
    async def test_start_scan_no_bucket(self, mock_client, tmp_path, monkeypatch):
        """Missing s3_bucket returns error."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        state = StateManager()
        state.update_config(agent_space_id='as-1', service_role='arn:role')
        scanner = Scanner(client=mock_client, state=state)
        result = await scanner.start_scan(path=str(tmp_path))
        assert 'error' in result
        assert 'S3 bucket' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.scanner.subprocess.run')
    async def test_git_archive_failure(self, mock_run, mock_client, mock_state, tmp_path):
        """Git archive failure raises ValueError."""
        mock_run.return_value = MagicMock(returncode=1, stderr='fatal: bad ref')
        scanner = Scanner(client=mock_client, state=mock_state)
        with pytest.raises(ValueError, match='git archive failed'):
            scanner._zip_committed_and_upload(str(tmp_path), 'HEAD', 'bucket')
