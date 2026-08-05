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
import hashlib
import os
import subprocess
import tempfile
import uuid
import zipfile
from awslabs.security_agent_mcp_server.aws_client import SecurityAgentClient
from awslabs.security_agent_mcp_server.state import StateManager
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


MAX_ZIP_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

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

    @staticmethod
    def _workspace_id(abs_path: str) -> str:
        """Stable short identifier for a workspace path, used as the S3 key prefix."""
        return hashlib.md5(abs_path.encode(), usedforsecurity=False).hexdigest()[:12]

    def _zip_and_upload_source(self, path: str, abs_path: str, s3_bucket: str) -> tuple[str, int]:
        """Zip the workspace and upload to a stable per-workspace S3 key, overwriting any prior upload.

        Returns (s3_url, zip_size_bytes).
        """
        zip_path = self._zip_code(path)
        zip_size = os.path.getsize(zip_path)
        if zip_size > MAX_ZIP_SIZE:
            os.unlink(zip_path)
            raise ValueError(
                f'Code too large ({zip_size // 1024 // 1024}MB). Max {MAX_ZIP_SIZE // 1024 // 1024}MB.'
            )
        try:
            s3_key = f'security-scans/source/{self._workspace_id(abs_path)}/source.zip'
            s3_url = self._client.upload_to_s3(s3_bucket, s3_key, zip_path)
        finally:
            if os.path.exists(zip_path):
                os.unlink(zip_path)
        return s3_url, zip_size

    def _zip_committed_and_upload(
        self, abs_path: str, base_ref: str, s3_bucket: str
    ) -> tuple[str, int]:
        """Zip the committed state at base_ref using git archive and upload.

        Returns (s3_url, zip_size_bytes).
        """
        tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        tmp.close()
        try:
            result = subprocess.run(
                ['git', 'archive', '--format=zip', '-o', tmp.name, '--', base_ref],
                cwd=abs_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise ValueError(f'git archive failed: {result.stderr.strip()}')

            zip_size = os.path.getsize(tmp.name)
            if zip_size > MAX_ZIP_SIZE:
                raise ValueError(
                    f'Code too large ({zip_size // 1024 // 1024}MB). '
                    f'Max {MAX_ZIP_SIZE // 1024 // 1024}MB.'
                )
            s3_key = f'security-scans/source/{self._workspace_id(abs_path)}/source.zip'
            s3_url = self._client.upload_to_s3(s3_bucket, s3_key, tmp.name)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
        return s3_url, zip_size

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
        if not s3_bucket:
            return {'error': 'No S3 bucket configured. Run setup first.'}

        # Verify agent space still exists
        space = self._client.get_agent_space(agent_space_id)
        if not space:
            self._state.clear_config_keys('agent_space_id')
            return {'error': f'Agent space {agent_space_id} no longer exists. Run setup again.'}

        abs_path = os.path.abspath(path)
        scan_id = f'scan-{uuid.uuid4().hex[:8]}'
        title = title or f'pre-cr-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'

        # 1+2. Zip code and upload to stable per-workspace S3 key (overwrites prior uploads)
        try:
            s3_url, zip_size = self._zip_and_upload_source(path, abs_path, s3_bucket)
        except ValueError as e:
            return {'error': str(e)}

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
                'scan_type': 'FULL',
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
            'scan_type': 'FULL',
            'title': title,
            'message': 'Security scan started. Ask the user if they want you to poll for status periodically, or if they prefer to check back later.',
        }

    async def start_diff_scan(
        self, path: str = '.', base_ref: str = 'HEAD', title: Optional[str] = None
    ) -> dict:
        """Run a diff scan — analyzes only changed code with full repo context.

        Uploads the committed state at base_ref as the baseline source, and the
        diff (base_ref vs working tree) as the changes to focus on.
        """
        config = self._state.get_config()
        agent_space_id = config.get('agent_space_id')
        service_role = config.get('service_role')
        s3_bucket = config.get('s3_bucket')

        if not agent_space_id or not service_role:
            return {'error': 'Not configured. Run setup_check and setup first.'}
        if not s3_bucket:
            return {'error': 'No S3 bucket configured. Run setup first.'}

        # Verify agent space still exists
        space = self._client.get_agent_space(agent_space_id)
        if not space:
            self._state.clear_config_keys('agent_space_id')
            return {'error': f'Agent space {agent_space_id} no longer exists. Run setup again.'}

        abs_path = os.path.abspath(path)

        # 1. Generate diff: base_ref vs working tree (fail fast if no changes)
        diff_cmd = ['git', 'diff', base_ref, '--']

        try:
            diff_result = subprocess.run(
                diff_cmd,
                cwd=abs_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            return {'error': 'git is not installed or not in PATH.'}
        except subprocess.TimeoutExpired:
            return {'error': 'git diff timed out (>60s). Try a narrower base_ref.'}

        if diff_result.returncode != 0:
            return {
                'error': f'git diff failed: {diff_result.stderr.strip()}. '
                f'Verify that "{base_ref}" is a valid ref in this repo.'
            }

        diff_content = diff_result.stdout
        if not diff_content.strip():
            return {'error': f'No diff found for {" ".join(diff_cmd)}. Nothing to scan.'}

        scan_id = f'scan-{uuid.uuid4().hex[:8]}'
        title = title or f'diff-{base_ref}-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'

        # 2. Zip committed state at base_ref (baseline) and upload
        try:
            s3_url, zip_size = self._zip_committed_and_upload(abs_path, base_ref, s3_bucket)
        except ValueError as e:
            return {'error': str(e)}

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

        # 4. Upload diff patch to a scan-specific S3 key
        diff_tmp = tempfile.NamedTemporaryFile(suffix='.patch', delete=False, mode='w')
        diff_tmp.write(diff_content)
        diff_tmp.close()
        try:
            s3_key_diff = f'security-scans/diffs/{scan_id}/diff.patch'
            self._client.upload_to_s3(s3_bucket, s3_key_diff, diff_tmp.name)
            diff_s3_uri = f's3://{s3_bucket}/{s3_key_diff}'
        finally:
            if os.path.exists(diff_tmp.name):
                os.unlink(diff_tmp.name)

        # 5. Start code review job with diffSource (recreate CodeReview if deleted externally)
        try:
            job_result = self._client.start_code_review_job_with_diff(
                agent_space_id=agent_space_id,
                code_review_id=code_review_id,
                diff_s3_uri=diff_s3_uri,
            )
        except (RuntimeError, ClientError) as e:
            is_not_found = (
                isinstance(e, ClientError)
                and e.response['Error']['Code'] == 'ResourceNotFoundException'
            ) or (isinstance(e, RuntimeError) and 'ResourceNotFoundException' in str(e))
            if is_not_found:
                cr_result = self._client.create_code_review(
                    agent_space_id=agent_space_id,
                    title=title,
                    service_role=service_role,
                    s3_url=s3_url,
                )
                code_review_id = cr_result['codeReviewId']
                self._state.set_code_review_id(abs_path, code_review_id)
                job_result = self._client.start_code_review_job_with_diff(
                    agent_space_id=agent_space_id,
                    code_review_id=code_review_id,
                    diff_s3_uri=diff_s3_uri,
                )
            else:
                raise

        job_id = job_result['codeReviewJobId']

        self._state.save_scan(
            scan_id,
            {
                'scan_id': scan_id,
                'code_review_id': code_review_id,
                'job_id': job_id,
                'agent_space_id': agent_space_id,
                'status': 'IN_PROGRESS',
                'scan_type': 'DIFF',
                'base_ref': base_ref,
                'title': title,
                'path': abs_path,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'zip_size_bytes': zip_size,
                'diff_size_bytes': len(diff_content.encode('utf-8')),
            },
        )

        return {
            'scan_id': scan_id,
            'code_review_id': code_review_id,
            'job_id': job_id,
            'status': 'STARTED',
            'scan_type': 'DIFF',
            'base_ref': base_ref,
            'title': title,
            'message': 'Diff scan started. Should complete in 10-15 minutes. '
            'Use get_scan_status to check progress.',
        }

    async def start_threat_model_review(
        self,
        path: str = '.',
        specs: Optional[list[str]] = None,
        title: Optional[str] = None,
    ) -> dict:
        """Run a threat model review — analyzes source code guided by design/requirement specs.

        Uploads the current repo (overwriting prior uploads) and the provided spec
        documents (e.g., Kiro design.md / requirements.md), creates a threat model
        with the source as an asset and the specs as scope docs, then starts a job.
        """
        config = self._state.get_config()
        agent_space_id = config.get('agent_space_id')
        service_role = config.get('service_role')
        s3_bucket = config.get('threat_model_s3_bucket')

        if not agent_space_id or not service_role:
            return {'error': 'Not configured. Run setup_check and setup first.'}
        if not s3_bucket:
            return {'error': 'No threat-model S3 bucket configured. Run setup first.'}
        if not specs:
            return {
                'error': 'No specs provided. Provide at least one design/requirements doc path.'
            }

        missing = [s for s in specs if not os.path.isfile(s)]
        if missing:
            return {'error': f'Spec files not found: {", ".join(missing)}'}

        # Verify agent space still exists
        space = self._client.get_agent_space(agent_space_id)
        if not space:
            self._state.clear_config_keys('agent_space_id')
            return {'error': f'Agent space {agent_space_id} no longer exists. Run setup again.'}

        abs_path = os.path.abspath(path)
        scan_id = f'scan-{uuid.uuid4().hex[:8]}'
        title = title or f'threatmodel-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'

        # 1. Zip and upload current repo to stable per-workspace S3 key (overwrites prior)
        try:
            s3_url, zip_size = self._zip_and_upload_source(path, abs_path, s3_bucket)
        except ValueError as e:
            return {'error': str(e)}

        # 2. Upload each spec doc to a scan-specific S3 key -> scope docs
        scope_docs = []
        for i, spec in enumerate(specs):
            s3_key_spec = (
                f'security-scans/threat-models/{scan_id}/specs/{i}_{os.path.basename(spec)}'
            )
            self._client.upload_to_s3(s3_bucket, s3_key_spec, spec)
            scope_docs.append({'s3Location': f's3://{s3_bucket}/{s3_key_spec}'})

        # 3. Create threat model (source as asset, specs as scope docs)
        tm_result = self._client.create_threat_model(
            agent_space_id=agent_space_id,
            title=title,
            service_role=service_role,
            assets={'sourceCode': [{'s3Location': s3_url}]},
            scope_docs=scope_docs,
        )
        threat_model_id = tm_result['threatModelId']

        # 4. Start threat model job
        job_result = self._client.start_threat_model_job(
            agent_space_id=agent_space_id,
            threat_model_id=threat_model_id,
        )
        job_id = job_result['threatModelJobId']

        self._state.save_scan(
            scan_id,
            {
                'scan_id': scan_id,
                'threat_model_id': threat_model_id,
                'job_id': job_id,
                'agent_space_id': agent_space_id,
                'status': 'IN_PROGRESS',
                'scan_type': 'THREAT_MODEL',
                'title': title,
                'path': abs_path,
                'specs': specs,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'zip_size_bytes': zip_size,
            },
        )

        return {
            'scan_id': scan_id,
            'threat_model_id': threat_model_id,
            'job_id': job_id,
            'status': 'STARTED',
            'scan_type': 'THREAT_MODEL',
            'title': title,
            'spec_count': len(specs),
            'message': 'Threat model review started. Use get_scan_status to check progress '
            'and get_scan_findings to retrieve identified threats.',
        }

    async def get_status(self, scan_id: Optional[str] = None) -> dict:
        """Get the current status of a scan."""
        scan = self._state.get_scan(scan_id)
        if not scan:
            return {'error': 'No scan found. Start one with start_security_scan.'}

        if scan.get('scan_type') == 'THREAT_MODEL':
            result = self._client.batch_get_threat_model_jobs(
                agent_space_id=scan['agent_space_id'],
                job_ids=[scan['job_id']],
            )
            jobs = result.get('threatModelJobs', [])
        else:
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

        if scan.get('scan_type') == 'THREAT_MODEL':
            return self._get_threat_findings(scan, scan_status, severity)

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
                    f for f in findings_summaries if (f.get('riskLevel') or '').upper() in allowed
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

    def _get_threat_findings(self, scan: dict, scan_status: str, severity: Optional[str]) -> dict:
        """Get threats (findings) for a threat model scan."""
        summaries = self._client.list_threats(
            agent_space_id=scan['agent_space_id'],
            threat_job_id=scan['job_id'],
        ).get('threats', [])

        if severity:
            severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']
            severity_upper = severity.upper()
            if severity_upper in severity_order:
                allowed = set(severity_order[: severity_order.index(severity_upper) + 1])
                summaries = [t for t in summaries if (t.get('severity') or '').upper() in allowed]

        threat_ids = [t.get('threatId') for t in summaries if t.get('threatId')]
        threats = []
        if threat_ids:
            batch_result = self._client.batch_get_threats(
                agent_space_id=scan['agent_space_id'],
                threat_ids=threat_ids,
            )
            threats = [
                {
                    'threatId': t.get('threatId'),
                    'statement': t.get('statement'),
                    'severity': t.get('severity'),
                    'status': t.get('status'),
                    'stride': t.get('stride'),
                    'threatImpact': t.get('threatImpact'),
                    'recommendation': t.get('recommendation'),
                    'impactedAssets': t.get('impactedAssets'),
                }
                for t in batch_result.get('threats', [])
            ]

        result = {
            'scan_id': scan['scan_id'],
            'title': scan.get('title'),
            'scan_status': scan_status,
            'total_findings': len(threats),
            'findings': threats,
        }
        if scan_status not in ('COMPLETED', 'PARTIALLY_COMPLETED'):
            result['note'] = 'Scan still in progress. More threats may appear. Check again later.'
        return result

    async def stop_scan(self, scan_id: str) -> dict:
        """Stop a running scan."""
        scan = self._state.get_scan(scan_id)
        if not scan:
            return {'error': 'No scan found.'}

        if scan.get('scan_type') == 'THREAT_MODEL':
            self._client.call(
                'StopThreatModelJob',
                {
                    'agentSpaceId': scan['agent_space_id'],
                    'threatModelJobId': scan['job_id'],
                },
            )
        else:
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
