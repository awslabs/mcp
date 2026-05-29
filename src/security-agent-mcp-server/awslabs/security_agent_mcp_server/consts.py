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

### Penetration Test and All Other Operations (via generic API)
Tools: `call_api`, `get_api_guide`

For pentests, target domains, integrations, and any operation beyond source code scanning:
1. `get_api_guide` → see all available operations
2. `call_api(operation, params)` → execute any SecurityAgent API

Example — pentest flow:
1. `call_api("CreateTargetDomain", {agentSpaceId, domain})` → register target
2. `call_api("VerifyTargetDomain", {agentSpaceId, targetDomainId})` → verify ownership
3. `call_api("CreatePentest", {agentSpaceId, title, assets: {endpoints: [...]}})` → create
4. `call_api("StartPentestJob", {agentSpaceId, pentestId})` → start
5. Poll with `call_api("BatchGetPentestJobs", ...)` until COMPLETED
6. `call_api("ListFindings", {agentSpaceId, pentestJobId})` → results
"""
