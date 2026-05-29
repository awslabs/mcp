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

"""Scanner — orchestrates zip, upload, create code review, start job, poll status, fetch findings."""

import gitignorefile
import os
import tempfile
import uuid
import zipfile
from awslabs.security_agent_mcp_server.aws_client import SecurityAgentClient
from awslabs.security_agent_mcp_server.state import StateManager
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


MAX_ZIP_SIZE = 512 * 1024 * 1024  # 512MB

EXCLUDE_DIRS = {
    '.git',
    'node_modules',
    '__pycache__',
    '.venv',
    'venv',
    'dist',
    'build',
    'target',
    '.mypy_cache',
    '.pytest_cache',
    '.tox',
    '.next',
    'cdk.out',
}

EXCLUDE_FILES = {
    '.DS_Store',
    'Thumbs.db',
    '*.pyc',
    '*.pyo',
}


class Scanner:
    """Orchestrates code packaging, scan execution, and findings retrieval."""

    def __init__(self, client: SecurityAgentClient, state: StateManager):
        """Initialize Scanner with API client and state manager."""
        self._client = client
        self._state = state

    async def start_scan(self, path: str = '.', title: Optional[str] = None) -> dict:
        """Package code, upload to S3, and start a security scan.

        Reuses an existing CodeReview for the same workspace path if one exists.
        Only creates a new CodeReview on first scan of a workspace.
        """
        config = self._state.get_config()
        agent_space_id = config.get('agent_space_id')
        service_role = config.get('service_role')
        s3_bucket = config.get('s3_bucket')

        if not agent_space_id or not service_role:
            return {'error': 'Not configured. Run setup_check and setup first.'}

        # Verify agent space still exists
        space = self._client.get_agent_space(agent_space_id)
        if not space:
            self._state.update_config(agent_space_id=None)
            return {'error': f'Agent space {agent_space_id} no longer exists. Run setup again.'}

        abs_path = os.path.abspath(path)
        scan_id = f'scan-{uuid.uuid4().hex[:8]}'
        title = title or f'pre-cr-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'

        # 1. Zip code
        zip_path = self._zip_code(path)
        zip_size = os.path.getsize(zip_path)
        if zip_size > MAX_ZIP_SIZE:
            os.unlink(zip_path)
            return {
                'error': f'Code too large ({zip_size // 1024 // 1024}MB). Max {MAX_ZIP_SIZE // 1024 // 1024}MB.'
            }

        # 2. Upload to S3
        try:
            s3_key = f'security-scans/{scan_id}/source.zip'
            s3_url = self._client.upload_to_s3(s3_bucket, s3_key, zip_path)
        finally:
            if os.path.exists(zip_path):
                os.unlink(zip_path)

        # 3. Get or create code review for this workspace
        code_review_id = self._state.get_code_review_id(abs_path)
        if not code_review_id:
            cr_result = self._client.create_code_review(
                agent_space_id=agent_space_id,
                title=title,
                service_role=service_role,
                s3_url=s3_url,
            )
            code_review_id = cr_result['codeReviewId']
            self._state.set_code_review_id(abs_path, code_review_id)

        # 4. Start code review job (recreate if code review was deleted externally)
        try:
            job_result = self._client.start_code_review_job(
                agent_space_id=agent_space_id,
                code_review_id=code_review_id,
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                cr_result = self._client.create_code_review(
                    agent_space_id=agent_space_id,
                    title=title,
                    service_role=service_role,
                    s3_url=s3_url,
                )
                code_review_id = cr_result['codeReviewId']
                self._state.set_code_review_id(abs_path, code_review_id)
                job_result = self._client.start_code_review_job(
                    agent_space_id=agent_space_id,
                    code_review_id=code_review_id,
                )
            else:
                raise
        job_id = job_result['codeReviewJobId']

        # 5. Save state
        self._state.save_scan(
            scan_id,
            {
                'scan_id': scan_id,
                'code_review_id': code_review_id,
                'job_id': job_id,
                'agent_space_id': agent_space_id,
                'status': 'IN_PROGRESS',
                'title': title,
                'path': abs_path,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'zip_size_bytes': zip_size,
            },
        )

        return {
            'scan_id': scan_id,
            'code_review_id': code_review_id,
            'job_id': job_id,
            'status': 'STARTED',
            'title': title,
            'message': 'Security scan started. Ask the user if they want you to poll for status periodically, or if they prefer to check back later.',
        }

    async def get_status(self, scan_id: Optional[str] = None) -> dict:
        """Get the current status of a scan."""
        scan = self._state.get_scan(scan_id)
        if not scan:
            return {'error': 'No scan found. Start one with start_security_scan.'}

        result = self._client.batch_get_code_review_jobs(
            agent_space_id=scan['agent_space_id'],
            job_ids=[scan['job_id']],
        )
        jobs = result.get('codeReviewJobs', [])
        if not jobs:
            return {'error': f'Job {scan["job_id"]} not found.'}

        job = jobs[0]
        status = job.get('status', 'UNKNOWN')
        if scan.get('status') != status:
            scan['status'] = status
            self._state.save_scan(scan['scan_id'], scan)

        elapsed = ''
        if scan.get('started_at'):
            start = datetime.fromisoformat(scan['started_at'])
            elapsed = f'{int((datetime.now(timezone.utc) - start).total_seconds())}s'

        return {
            'scan_id': scan['scan_id'],
            'status': status,
            'title': scan.get('title'),
            'elapsed': elapsed,
            'steps': job.get('steps', []),
        }

    async def get_findings(
        self, scan_id: Optional[str] = None, severity: Optional[str] = None
    ) -> dict:
        """Get findings from a scan. Works during IN_PROGRESS (partial) or after COMPLETED."""
        scan = self._state.get_scan(scan_id)
        if not scan:
            return {'error': 'No scan found.'}

        # Get current status for context
        status_result = await self.get_status(scan_id=scan['scan_id'])
        scan_status = status_result.get('status', 'UNKNOWN')

        result = self._client.list_findings(
            agent_space_id=scan['agent_space_id'],
            code_review_job_id=scan['job_id'],
        )
        findings_summaries = result.get('findingsSummaries', [])

        if severity:
            severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']
            severity_upper = severity.upper()
            if severity_upper in severity_order:
                min_idx = severity_order.index(severity_upper)
                allowed = set(severity_order[: min_idx + 1])
                findings_summaries = [
                    f for f in findings_summaries if f.get('riskLevel', '').upper() in allowed
                ]

        # Batch get full details (including remediationCode and codeLocations)
        finding_ids = [f['findingId'] for f in findings_summaries]
        findings = []
        if finding_ids:
            batch_result = self._client.batch_get_findings(
                agent_space_id=scan['agent_space_id'],
                finding_ids=finding_ids,
            )
            findings = [
                {
                    'findingId': f.get('findingId'),
                    'name': f.get('name'),
                    'description': f.get('description'),
                    'riskLevel': f.get('riskLevel'),
                    'riskType': f.get('riskType'),
                    'confidence': f.get('confidence'),
                    'status': f.get('status'),
                    'remediationCode': f.get('remediationCode'),
                    'codeLocations': f.get('codeLocations'),
                }
                for f in batch_result.get('findings', [])
            ]

        result = {
            'scan_id': scan['scan_id'],
            'title': scan.get('title'),
            'scan_status': scan_status,
            'total_findings': len(findings),
            'findings': findings,
        }
        if scan_status not in ('COMPLETED', 'PARTIALLY_COMPLETED'):
            result['note'] = 'Scan still in progress. More findings may appear. Check again later.'
        return result

    async def stop_scan(self, scan_id: str) -> dict:
        """Stop a running scan."""
        scan = self._state.get_scan(scan_id)
        if not scan:
            return {'error': 'No scan found.'}

        self._client.stop_code_review_job(
            agent_space_id=scan['agent_space_id'],
            code_review_job_id=scan['job_id'],
        )
        scan['status'] = 'STOPPED'
        self._state.save_scan(scan['scan_id'], scan)
        return {'scan_id': scan['scan_id'], 'status': 'STOPPED'}

    def _zip_code(self, path: str) -> str:
        root = Path(path).resolve()
        if not root.is_dir():
            raise ValueError(f'Path does not exist or is not a directory: {root}')
        gitignore_path = root / '.gitignore'
        matches = (
            gitignorefile.parse(str(gitignore_path))
            if gitignore_path.exists()
            else lambda _: False
        )

        tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        try:
            with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                for dirpath, dirnames, filenames in os.walk(root):
                    dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
                    for filename in filenames:
                        filepath = Path(dirpath) / filename
                        if filepath.is_symlink():
                            continue
                        rel_path = filepath.relative_to(root)
                        if not matches(str(filepath)) and not any(
                            filepath.match(p) for p in EXCLUDE_FILES
                        ):
                            zf.write(filepath, rel_path)
        except Exception:
            os.unlink(tmp.name)
            raise
        return tmp.name
