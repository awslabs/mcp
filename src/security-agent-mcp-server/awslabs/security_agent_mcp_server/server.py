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

"""AWS Security Agent MCP Server implementation."""

import json
import os
import sys
from awslabs.security_agent_mcp_server.aws_client import SecurityAgentClient
from awslabs.security_agent_mcp_server.consts import (
    DEFAULT_REGION,
    SERVER_INSTRUCTIONS,
)
from awslabs.security_agent_mcp_server.scanner import Scanner
from awslabs.security_agent_mcp_server.state import StateManager
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Optional


def _json_serial(obj):
    """JSON serializer for objects not serializable by default (e.g., datetime)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f'Type {type(obj)} not serializable')


# Map AWS error codes to short, user-actionable remediation strings.
# Default fallback when the code isn't in the map is provided by _translate_client_error.
_REMEDIATION = {
    'AccessDeniedException': 'Check your IAM permissions for this operation.',
    'AccessDenied': 'Check your IAM permissions for this operation.',
    'EntityAlreadyExists': 'The resource already exists; reuse it or pick a different name.',
    'EntityAlreadyExistsException': 'The resource already exists; reuse it or pick a different name.',
    'ResourceNotFoundException': 'The resource does not exist or was deleted; run setup again.',
    'NoSuchEntity': 'The IAM resource does not exist; run setup again.',
    'BucketAlreadyExists': 'The S3 bucket name is taken globally; pick a different name.',
    'BucketAlreadyOwnedByYou': 'You already own this bucket; reuse it.',
    'ValidationException': 'Request parameters were invalid; check the operation inputs.',
    'ThrottlingException': 'Request was throttled; retry with backoff.',
    'TooManyRequestsException': 'Request was throttled; retry with backoff.',
    'ConflictException': 'The resource is in a conflicting state; retry after the current operation finishes.',
}


def _translate_client_error(e: ClientError) -> dict:
    """Translate a boto3 ClientError into the {error, error_code, remediation} contract.

    The MCP server's pattern A (`{'error': '...'}`) returns are kept as-is for known
    application-level cases. This helper is the structured shape for AWS-side failures
    so callers (including LLMs) can branch on `error_code` and surface `remediation`
    instead of parsing free-text boto3 messages.
    """
    err = e.response.get('Error', {}) if hasattr(e, 'response') else {}
    code = err.get('Code', 'UnknownError')
    message = err.get('Message') or str(e)
    return {
        'error': message,
        'error_code': code,
        'remediation': _REMEDIATION.get(code, 'See error message; consult AWS docs for details.'),
    }


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize MCP server
mcp = FastMCP(
    'awslabs.security-agent-mcp-server',
    instructions=SERVER_INSTRUCTIONS,
    dependencies=['boto3', 'filelock', 'gitignorefile', 'pydantic', 'loguru'],
)

# Initialize components
_region = os.environ.get('AWS_REGION', DEFAULT_REGION)

_client = SecurityAgentClient(region=_region)
_state = StateManager(region=_region)
_scanner = Scanner(client=_client, state=_state)


_ALLOWED_ROOT: str | None = os.environ.get('WORKSPACE_ROOT')


async def _validate_path(ctx: Context, path: str, must_be_dir: bool = True) -> str:
    """Resolve path and verify it's within the configured workspace root.

    Prevents scanning arbitrary directories (e.g. ~/.aws, /etc) which would
    upload their contents to S3. The allowed root is determined by:
    1. WORKSPACE_ROOT env var (set by IDE/power config)
    2. Server process cwd (fallback)
    """
    resolved = os.path.realpath(os.path.abspath(path))
    root = os.path.realpath(_ALLOWED_ROOT) if _ALLOWED_ROOT else os.path.realpath(os.getcwd())

    if root != os.sep and not (resolved == root or resolved.startswith(root + os.sep)):
        raise ValueError(
            f'Path "{path}" resolves to "{resolved}" which is outside the allowed workspace '
            f'root "{root}". Set the WORKSPACE_ROOT environment variable to the directory '
            f'you want to allow scanning.'
        )

    if must_be_dir and not os.path.isdir(resolved):
        raise ValueError(f'Path "{resolved}" does not exist or is not a directory.')
    if not must_be_dir and not os.path.isfile(resolved):
        raise ValueError(f'Path "{resolved}" does not exist or is not a file.')

    return resolved


def _client_prefix(ctx: Context) -> str:
    """Extract a kebab-case prefix from the MCP client name, or 'ide' as fallback."""
    try:
        session = ctx.session
        if session is None:
            return 'ide'
        client_params = session.client_params
        if client_params is None:
            return 'ide'
        name = client_params.clientInfo.name  # type: ignore[union-attr]
        if not isinstance(name, str):
            return 'ide'
        return name.lower().replace(' ', '-')
    except (AttributeError, TypeError):
        return 'ide'


def _ensure_s3_bucket(config: dict, kind: str = 'scans') -> None:
    """Lazily create and register the per-account S3 bucket for the given kind.

    kind 'scans' -> security-agent-scans-... (full/diff scans);
    'threat-model' -> security-agent-threat-model-... (threat model reviews).
    """
    config_key = 's3_bucket' if kind == 'scans' else 'threat_model_s3_bucket'
    if config.get(config_key):
        return
    account_id = _client.get_caller_identity()['Account']
    bucket = f'security-agent-{kind}-{account_id}-{_region}'
    try:
        _client.create_s3_bucket(bucket)
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') != 'BucketAlreadyOwnedByYou':
            raise

    # Register bucket on agent space so the service can access it
    agent_space_id = config['agent_space_id']
    space = _client.get_agent_space(agent_space_id)
    aws_resources = dict(space.get('awsResources', {}))
    existing_buckets = list(aws_resources.get('s3Buckets', []))
    if bucket not in existing_buckets:
        existing_buckets.append(bucket)
        aws_resources['s3Buckets'] = existing_buckets
        _client.update_agent_space(
            agent_space_id,
            space.get('name', 'security-scans'),
            aws_resources,
        )

    _state.update_config(**{config_key: bucket})


@mcp.tool()
async def setup_check(ctx: Context) -> str:
    """Check if AWS Security Agent prerequisites are configured.

    Verifies agent space and service role are available.
    If not ready, lists existing agent spaces to help with setup.
    """
    try:
        config = _state.get_config()
        missing = []

        if not config.get('agent_space_id'):
            missing.append('agent_space_id')
        if not config.get('service_role'):
            missing.append('service_role')

        try:
            _client.get_caller_identity()
        except Exception as e:
            missing.append(f'aws_credentials ({e})')

        result: dict = {'ready': len(missing) == 0, 'missing': missing, 'config': config}

        # If not ready, list existing spaces for user to choose from
        if not result['ready'] and 'aws_credentials' not in str(missing):
            try:
                spaces = _client.list_agent_spaces()
                if spaces:
                    result['existing_agent_spaces'] = [
                        {'id': s.get('agentSpaceId'), 'name': s.get('name')} for s in spaces
                    ]
                    result['next_step'] = (
                        'Show these agent spaces to the user and ask which one to use '
                        'or whether to create a new one. Wait for their response before calling setup.'
                    )
            except Exception as list_err:
                logger.warning(f'Could not list existing agent spaces: {list_err}')
                result['list_agent_spaces_error'] = str(list_err)

        logger.info(f'Setup check: ready={result["ready"]}')
        return json.dumps(result, default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in setup_check: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in setup_check: {e}')
        await ctx.error(f'Error checking setup: {e}')
        raise


@mcp.tool()
async def setup(
    ctx: Context,
    name: Optional[str] = Field(
        default=None,
        description='Name for new agent space. If not provided and no agent_space_id, defaults to "security-scans".',
    ),
    agent_space_id: Optional[str] = Field(
        default=None,
        description='Existing agent space ID to use. Omit to create new.',
    ),
    service_role_arn: Optional[str] = Field(
        default=None,
        description='Existing IAM service role ARN. Omit to create a minimal role automatically.',
    ),
) -> str:
    """One-time setup: provision or reuse agent space and IAM service role.

    NOTE: This creates a minimal role for code scanning and basic pentesting (S3 read + CloudWatch Logs).
    For advanced use cases (VPC-based pentests, custom networking, broader AWS resource access),
    configure the agent space and role via the AWS Security Agent console instead.

    IMPORTANT: Before calling, ask the user:
    1. "Do you have an existing agent space, or should I create a new one?"
       (setup_check returns existing_agent_spaces if any exist — show them)
    2. "Do you have an existing IAM service role, or should I create one?"
       If using an existing role, it MUST have a trust policy allowing securityagent.amazonaws.com to assume it.
       For pentesting AWS resources, the role needs broader permissions (ec2:Describe*, iam:Get*).
       For code scanning only, a minimal role with S3 read is sufficient.
       See: https://docs.aws.amazon.com/securityagent/latest/userguide/create-iam-role.html

    Then call with the appropriate params:
    - New space + new role: setup(name='my-space')
    - New space + existing role: setup(name='my-space', service_role_arn='arn:...')
    - Existing space + new role: setup(agent_space_id='as-xxx')
    - Existing space + existing role: setup(agent_space_id='as-xxx', service_role_arn='arn:...')
    """
    try:
        identity = _client.get_caller_identity()
        account_id = identity['Account']
        config = _state.get_config()

        # Resolve service role
        service_role = config.get('service_role')
        if not service_role:
            if service_role_arn:
                service_role = service_role_arn
            else:
                role_name = 'SecurityAgentScanRole'
                service_role = _client.create_service_role(role_name, account_id, '')
                logger.info(f'Created or updated service role: {service_role}')
            _state.update_config(service_role=service_role)

        # Resolve agent space
        if not agent_space_id:
            agent_space_id = config.get('agent_space_id')

        if not agent_space_id:
            result = _client.create_agent_space(
                name=name or 'security-scans', service_role=service_role
            )
            agent_space_id = result['agentSpaceId']
            logger.info(f'Created agent space: {agent_space_id}')
        else:
            # Ensure role is registered on existing space
            space_details = _client.get_agent_space(agent_space_id)
            space_name = space_details.get('name', name or 'security-scans')
            aws_resources = dict(space_details.get('awsResources', {}))
            existing_roles = list(aws_resources.get('iamRoles', []))

            if service_role not in existing_roles:
                existing_roles.append(service_role)
                aws_resources['iamRoles'] = existing_roles
                _client.update_agent_space(agent_space_id, space_name, aws_resources)

        _state.update_config(agent_space_id=agent_space_id)

        return json.dumps(
            {
                'status': 'ready',
                'agent_space_id': agent_space_id,
                'service_role': service_role,
                'account_id': account_id,
            }
        )
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in setup: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in setup: {e}')
        await ctx.error(f'Setup failed: {e}')
        raise


@mcp.tool()
async def start_security_scan(
    ctx: Context,
    path: str = Field(
        default='.',
        description='Path to the code directory to scan. CRITICAL: Assistant must provide the current workspace directory.',
    ),
    title: Optional[str] = Field(
        default=None,
        description='Title for the scan. Must not contain spaces (use hyphens instead). Defaults to auto-generated name with timestamp.',
    ),
) -> str:
    """Start a security code review scan. Zips code, uploads to S3, starts scan, returns immediately.

    Returns scan_id for polling with get_scan_status. The scan runs server-side.
    Use get_scan_status to check progress and get_scan_findings to retrieve results when complete.
    """
    try:
        config = _state.get_config()
        if not config.get('agent_space_id') or not config.get('service_role'):
            return json.dumps({'error': 'Not configured. Run setup first.'}, default=_json_serial)

        # Lazy S3 bucket creation on first scan
        _ensure_s3_bucket(config)

        path = await _validate_path(ctx, path)
        prefix = _client_prefix(ctx)
        title = (
            f'{prefix}-{title}'
            if title
            else f'{prefix}-pre-cr-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'
        )
        logger.info(f'Starting security scan on path: {path}')
        result = await _scanner.start_scan(path=path, title=title)
        return json.dumps(result, default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in start_security_scan: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except ValueError as e:
        logger.error(f'Error in start_security_scan: {e}')
        return json.dumps({'error': str(e)}, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in start_security_scan: {e}')
        await ctx.error(f'Scan failed: {e}')
        raise


@mcp.tool()
async def start_diff_scan(
    ctx: Context,
    path: str = Field(
        default='.',
        description='Absolute path to the code directory to scan. CRITICAL: Assistant must provide the user\'s current workspace absolute path, NOT ".". The MCP server runs as a subprocess and "." resolves to its own directory, not the user\'s workspace.',
    ),
    base_ref: str = Field(
        default='HEAD',
        description='Git ref to diff against. "HEAD" for uncommitted changes, or a branch/commit like "main".',
    ),
    title: Optional[str] = Field(
        default=None,
        description='Title for the diff scan. Auto-generated if not provided.',
    ),
) -> str:
    """Start a diff security scan — analyzes only changed code with full repo as context.

    Faster than a full scan (10-15 min vs ~45 min). Uploads the current repo and
    the diff patch; the agent focuses on changes while having full source for context.
    No prior scan required.
    """
    try:
        config = _state.get_config()
        if not config.get('agent_space_id') or not config.get('service_role'):
            return json.dumps({'error': 'Not configured. Run setup first.'}, default=_json_serial)

        _ensure_s3_bucket(config)

        path = await _validate_path(ctx, path)
        prefix = _client_prefix(ctx)
        title = (
            f'{prefix}-{title}'
            if title
            else f'{prefix}-diff-{base_ref}-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'
        )
        logger.info(f'Starting diff scan on path: {path}, base_ref: {base_ref}')
        result = await _scanner.start_diff_scan(path=path, base_ref=base_ref, title=title)
        return json.dumps(result, default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in start_diff_scan: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except ValueError as e:
        logger.error(f'Error in start_diff_scan: {e}')
        return json.dumps({'error': str(e)}, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in start_diff_scan: {e}')
        await ctx.error(f'Diff scan failed: {e}')
        raise


@mcp.tool()
async def start_threat_model_review(
    ctx: Context,
    path: str = Field(
        default='.',
        description='Absolute path to the source code directory to threat model. CRITICAL: Assistant must provide the user\'s current workspace absolute path, NOT ".". The MCP server runs as a subprocess and "." resolves to its own directory, not the user\'s workspace.',
    ),
    specs: list[str] = Field(
        default_factory=list,
        description='Absolute paths to spec documents (e.g., Kiro design.md and requirements.md) for the agent to focus on during threat modeling. At least one is required.',
    ),
    title: Optional[str] = Field(
        default=None,
        description='Title for the threat model review. Auto-generated if not provided.',
    ),
) -> str:
    """Start a threat model review — analyzes source code guided by design/requirement specs.

    Uploads the source directory and the provided spec documents, creates a threat
    model with the source as an asset and the specs as scope documents, and starts
    a threat model job. Returns a scan_id for polling with get_scan_status; retrieve
    identified threats with get_scan_findings. No prior scan required.
    """
    try:
        config = _state.get_config()
        if not config.get('agent_space_id') or not config.get('service_role'):
            return json.dumps({'error': 'Not configured. Run setup first.'}, default=_json_serial)

        _ensure_s3_bucket(config, 'threat-model')

        path = await _validate_path(ctx, path)
        specs = [await _validate_path(ctx, s, must_be_dir=False) for s in specs]
        prefix = _client_prefix(ctx)
        title = (
            f'{prefix}-{title}'
            if title
            else f'{prefix}-threatmodel-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'
        )
        logger.info(f'Starting threat model review on path: {path}, specs: {len(specs)}')
        result = await _scanner.start_threat_model_review(path=path, specs=specs, title=title)
        return json.dumps(result, default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in start_threat_model_review: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except ValueError as e:
        logger.error(f'Error in start_threat_model_review: {e}')
        return json.dumps({'error': str(e)}, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in start_threat_model_review: {e}')
        await ctx.error(f'Threat model review failed: {e}')
        raise


@mcp.tool()
async def get_scan_status(
    ctx: Context,
    scan_id: Optional[str] = Field(
        default=None,
        description='Scan ID to check. Uses the most recent scan if not provided.',
    ),
) -> str:
    """Check the status of a security scan.

    Useful for checking a previous scan from an earlier session, or verifying
    a scan completed after session recovery.
    """
    try:
        return json.dumps(await _scanner.get_status(scan_id=scan_id), default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in get_scan_status: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in get_scan_status: {e}')
        await ctx.error(f'Error checking status: {e}')
        raise


@mcp.tool()
async def get_scan_findings(
    ctx: Context,
    scan_id: Optional[str] = Field(
        default=None,
        description='Scan ID to get findings for. Uses the most recent scan if not provided.',
    ),
    severity: Optional[str] = Field(
        default=None,
        description='Filter findings by minimum severity: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL.',
    ),
) -> str:
    """Get findings from a completed security scan.

    Returns findings with title, severity, confidence, file location, and description.
    """
    try:
        return json.dumps(
            await _scanner.get_findings(scan_id=scan_id, severity=severity), default=_json_serial
        )
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in get_scan_findings: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in get_scan_findings: {e}')
        await ctx.error(f'Error getting findings: {e}')
        raise


@mcp.tool()
async def list_scans(ctx: Context) -> str:
    """List all recent security scans tracked locally with their status."""
    try:
        return json.dumps({'scans': _state.list_scans()}, default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in list_scans: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in list_scans: {e}')
        await ctx.error(f'Error listing scans: {e}')
        raise


@mcp.tool()
async def stop_scan(
    ctx: Context,
    scan_id: str = Field(..., description='The scan ID to stop.'),
) -> str:
    """Stop a running security scan."""
    try:
        logger.info(f'Stopping scan: {scan_id}')
        return json.dumps(await _scanner.stop_scan(scan_id=scan_id), default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in stop_scan: {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in stop_scan: {e}')
        await ctx.error(f'Error stopping scan: {e}')
        raise


@mcp.tool()
async def call_api(
    ctx: Context,
    operation: str = Field(
        ...,
        description='SecurityAgent API operation name (e.g., CreatePentest, ListTargetDomains). Call get_api_guide for available operations.',
    ),
    params: dict = Field(
        default_factory=dict,
        description='Operation parameters as JSON object.',
    ),
) -> str:
    """Call any AWS Security Agent API operation directly.

    Use get_api_guide to discover available operations and their parameters.
    """
    try:
        import re

        if not re.match(r'^[A-Za-z][A-Za-z0-9]*$', operation):
            return json.dumps(
                {'error': f'Invalid operation name: {operation}'}, default=_json_serial
            )
        logger.info(f'call_api: {operation}')
        result = _client.call(operation, params)
        return json.dumps(result, default=_json_serial)
    except ClientError as e:
        err = _translate_client_error(e)
        logger.error(f'Error in call_api ({operation}): {e}')
        await ctx.error(err['error'])
        return json.dumps(err, default=_json_serial)
    except Exception as e:
        logger.error(f'Error in call_api ({operation}): {e}')
        await ctx.error(f'{operation} failed: {e}')
        raise


_cached_operations = None


@mcp.tool()
async def get_api_guide(ctx: Context) -> str:
    """Get all available SecurityAgent API operations.

    Returns operation names dynamically from the service model,
    plus a link to full API documentation with parameter details.
    """
    global _cached_operations
    if _cached_operations is None:
        try:
            import boto3

            session = boto3.Session(region_name=_region)
            client = session.client('securityagent')
            _cached_operations = sorted(client.meta.service_model.operation_names)
        except Exception as load_err:
            logger.warning(f'Could not load SecurityAgent service model: {load_err}')

    operations = _cached_operations or ['(Could not load service model — use documentation link)']

    return json.dumps(
        {
            'documentation': 'https://docs.aws.amazon.com/securityagent/latest/APIReference/API_Operations.html',
            'operations': operations,
            'usage': 'Call call_api(operation="OperationName", params={...}). See documentation link for parameter details.',
            'examples': {
                'ListAgentSpaces': {},
                'CreatePentest': {
                    'agentSpaceId': '...',
                    'title': '...',
                    'assets': {'endpoints': [{'uri': 'https://example.com/api'}]},
                    'serviceRole': 'arn:aws:iam::...:role/...',
                },
                'StartPentestJob': {'agentSpaceId': '...', 'pentestId': '...'},
                'ListFindings': {
                    'agentSpaceId': '...',
                    '_note': 'Pass exactly ONE of codeReviewJobId or pentestJobId.',
                    'codeReviewJobId': '... (for code review findings)',
                    'pentestJobId': '... (for pentest findings)',
                },
                'CreateTargetDomain': {
                    'targetDomainName': 'example.com',
                    'verificationMethod': 'HTTP_ROUTE',
                },
                'VerifyTargetDomain': {'targetDomainId': '...'},
            },
        }
    )


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
