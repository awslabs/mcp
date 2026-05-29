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
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.security_agent_mcp_server.scanner import Scanner
from awslabs.security_agent_mcp_server.state import StateManager


@pytest.fixture
def mock_client():
    """Create a mock SecurityAgentClient."""
    client = MagicMock()
    client.upload_to_s3 = MagicMock(return_value='s3://bucket/key.zip')
    client.create_code_review = MagicMock(return_value={'codeReviewId': 'cr-123'})
    client.start_code_review_job = MagicMock(return_value={'codeReviewJobId': 'cj-456'})
    client.batch_get_code_review_jobs = MagicMock(return_value={
        'codeReviewJobs': [{'status': 'COMPLETED', 'steps': []}]
    })
    client.list_findings = MagicMock(return_value={
        'findingsSummaries': [
            {'findingId': 'f-1', 'title': 'SQL Injection', 'riskLevel': 'CRITICAL'}
        ]
    })
    client.batch_get_findings = MagicMock(return_value={
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
    })
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
        mock_state.save_scan('scan-test', {
            'scan_id': 'scan-test',
            'job_id': 'cj-456',
            'code_review_id': 'cr-123',
            'started_at': '2026-01-01T00:00:00+00:00', 'agent_space_id': 'as-test',
        })
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
        mock_state.save_scan('scan-test', {
            'scan_id': 'scan-test',
            'job_id': 'cj-missing',
            'code_review_id': 'cr-123',
            'started_at': '2026-01-01T00:00:00+00:00', 'agent_space_id': 'as-test',
        })
        status = await scanner.get_status('scan-test')
        assert 'error' in status

    @pytest.mark.asyncio
    async def test_get_findings(self, mock_client, mock_state):
        """Gets findings from completed scan."""
        scanner = Scanner(client=mock_client, state=mock_state)
        mock_state.save_scan('scan-test', {
            'scan_id': 'scan-test',
            'job_id': 'cj-456',
            'code_review_id': 'cr-123',
            'started_at': '2026-01-01T00:00:00+00:00', 'agent_space_id': 'as-test',
        })
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
        mock_state.save_scan('scan-test', {
            'scan_id': 'scan-test',
            'job_id': 'cj-456',
            'code_review_id': 'cr-123',
            'started_at': '2026-01-01T00:00:00+00:00', 'agent_space_id': 'as-test',
        })
        result = await scanner.stop_scan('scan-test')
        assert result['status'] == 'STOPPED'
        mock_client.stop_code_review_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_scan_no_scan(self, mock_client, mock_state):
        """Returns error when scan not found."""
        scanner = Scanner(client=mock_client, state=mock_state)
        result = await scanner.stop_scan('nonexistent')
        assert 'error' in result
