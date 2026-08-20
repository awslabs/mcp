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

"""Constants for the AWS Security Agent MCP Server."""

# Default configuration
DEFAULT_REGION = 'us-east-1'

# MCP Server instructions
SERVER_INSTRUCTIONS = """
# AWS Security Agent MCP Server

Comprehensive MCP server for AWS Security Agent — security scanning and penetration testing.

## Workflows

### Setup (one-time)
Tools: `setup_check`, `setup`

1. `setup_check` → verify credentials, agent space, service role
2. `setup` → create or reuse agent space and IAM role

### Source Code Security Scan (orchestrated end-to-end)
Tools: `start_security_scan`, `get_scan_status`, `get_scan_findings`, `list_scans`, `stop_scan`

1. `start_security_scan(path=".")` → zips code, uploads to S3, starts scan. Returns scan_id.
2. Poll with `get_scan_status` until COMPLETED (or call `get_scan_findings` anytime for partial results)
3. `get_scan_findings` → vulnerabilities with remediation guidance and code locations

### Diff Scan (fast incremental scan)
Tools: `start_diff_scan`, `get_scan_status`, `get_scan_findings`

For scanning only changed code with full repo as context. No prior scan required.

1. `start_diff_scan(path=".", base_ref="HEAD")` → generates git diff, uploads current repo + diff patch, starts diff scan
2. Poll with `get_scan_status` until COMPLETED (10-15 min vs ~45 min for full scan)
3. `get_scan_findings` → vulnerabilities focused on changed code

base_ref options:
- "HEAD" (default) — scan uncommitted workspace changes (staged + unstaged)
- "main" or any ref — scan all changes on branch vs that ref

### Threat Model Review (design/spec-guided)
Tools: `start_threat_model_review`, `get_scan_status`, `get_scan_findings`

Analyzes source code guided by design/requirement specs (e.g., Kiro design.md and
requirements.md). The specs are used as scope documents the agent focuses on, prioritized
over general source code analysis. No prior scan required.

1. `start_threat_model_review(path=".", specs=["/abs/design.md", "/abs/requirements.md"])`
   → zips + uploads the source dir, uploads the specs as scope docs, creates a threat model, starts a job
2. Poll with `get_scan_status` until COMPLETED
3. `get_scan_findings` → identified threats (severity, STRIDE, impact, recommendation)

### Penetration Test and All Other Operations (via generic API)
Tools: `call_api`, `get_api_guide`

For pentests, target domains, integrations, and any operation beyond source code scanning:
1. `get_api_guide` → see all available operations
2. `call_api(operation, params)` → execute any SecurityAgent API

Example — pentest flow:
1. `call_api("CreateTargetDomain", {targetDomainName, verificationMethod})` → register target
2. `call_api("VerifyTargetDomain", {targetDomainId})` → verify ownership
3. `call_api("CreatePentest", {agentSpaceId, title, assets: {endpoints: [...]}, serviceRole})` → create
4. `call_api("StartPentestJob", {agentSpaceId, pentestId})` → start
5. Poll with `call_api("BatchGetPentestJobs", {agentSpaceId, pentestJobIds: [...]})` until COMPLETED
6. `call_api("ListFindings", {agentSpaceId, pentestJobId})` → results
"""
