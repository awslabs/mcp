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

"""Pre-run validation tools for the AWS HealthOmics MCP server."""

import json
import re
from awslabs.aws_healthomics_mcp_server.consts import HEALTHOMICS_PRINCIPAL
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import check_container_availability
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_aws_session,
    get_iam_client,
    get_omics_client,
)
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import parse_s3_path
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional, Tuple


# Check result statuses
STATUS_PASS = 'pass'
STATUS_WARN = 'warn'
STATUS_FAIL = 'fail'

# Matches an ECR image URI, capturing the repository name and the tag or digest.
# e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-prefix/my-repo:1.0
_ECR_URI_PATTERN = re.compile(
    r'^(?P<account>\d{12})\.dkr\.ecr\.(?P<region>[a-z0-9-]+)\.amazonaws\.com/'
    r'(?P<repository>[^:@]+)(?::(?P<tag>[^@]+))?(?:@(?P<digest>sha256:[a-f0-9]+))?$'
)


def _check(name: str, status: str, detail: Optional[str] = None) -> Dict[str, Any]:
    """Build a single check result entry.

    Args:
        name: Identifier for the check
        status: One of 'pass', 'warn', or 'fail'
        detail: Optional human-readable explanation

    Returns:
        Dictionary describing the check result
    """
    result: Dict[str, Any] = {'name': name, 'status': status}
    if detail:
        result['detail'] = detail
    return result


def parse_ecr_image_uri(image_uri: str) -> Optional[Dict[str, str]]:
    """Parse an ECR image URI into its component parts.

    Args:
        image_uri: Full ECR image URI, optionally with a tag or digest

    Returns:
        Dictionary with 'account', 'region', 'repository', and either 'tag' or
        'digest' keys, or None if the URI is not a recognizable ECR URI.
    """
    match = _ECR_URI_PATTERN.match(image_uri.strip())
    if not match:
        return None

    parts = {
        'account': match.group('account'),
        'region': match.group('region'),
        'repository': match.group('repository'),
    }
    if match.group('digest'):
        parts['digest'] = match.group('digest')
    if match.group('tag'):
        parts['tag'] = match.group('tag')
    if 'tag' not in parts and 'digest' not in parts:
        parts['tag'] = 'latest'
    return parts


def _as_list(value: Any) -> List[Any]:
    """Normalize a policy value that may be a scalar or a list into a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _statement_condition_verdict(
    condition: Dict[str, Any],
    region: Optional[str],
    account_id: Optional[str],
) -> Tuple[str, Optional[str]]:
    """Decide whether a trust statement's conditions permit this run.

    Only the condition keys AWS documents for confused-deputy protection on the
    HealthOmics trust policy are evaluated: ``aws:SourceArn`` and
    ``aws:SourceAccount``. Anything else is reported as not evaluable rather than
    assumed to permit the run.

    Args:
        condition: The statement's Condition block
        region: Region the run will start in
        account_id: Account the run will start in

    Returns:
        Tuple of (verdict, reason) where verdict is 'permits', 'excludes' or
        'unknown'. reason is populated for 'excludes' and 'unknown'.
    """
    unevaluated: List[str] = []

    for operator, entries in condition.items():
        if not isinstance(entries, dict):
            unevaluated.append(operator)
            continue

        for key, raw_values in entries.items():
            key_lower = key.lower()
            values = [str(v) for v in _as_list(raw_values)]

            if key_lower == 'aws:sourcearn':
                # Values are run ARN patterns: arn:aws:omics:<region>:<account>:run/*
                arn_regions = set()
                arn_accounts = set()
                for value in values:
                    parts = value.split(':')
                    if len(parts) < 5:
                        unevaluated.append(f'{operator}/{key}')
                        continue
                    arn_regions.add(parts[3])
                    arn_accounts.add(parts[4])

                concrete_regions = {r for r in arn_regions if r and '*' not in r and '?' not in r}
                if region and concrete_regions and region not in concrete_regions:
                    return (
                        'excludes',
                        f'{key} restricts this role to runs in '
                        f'{", ".join(sorted(concrete_regions))}, but the run region is {region}',
                    )

                concrete_accounts = {
                    a for a in arn_accounts if a and '*' not in a and '?' not in a
                }
                if account_id and concrete_accounts and account_id not in concrete_accounts:
                    return (
                        'excludes',
                        f'{key} restricts this role to account '
                        f'{", ".join(sorted(concrete_accounts))}, but the run account is '
                        f'{account_id}',
                    )

            elif key_lower == 'aws:sourceaccount':
                concrete = {v for v in values if '*' not in v and '?' not in v}
                if account_id and concrete and account_id not in concrete:
                    return (
                        'excludes',
                        f'{key} restricts this role to account '
                        f'{", ".join(sorted(concrete))}, but the run account is {account_id}',
                    )

            else:
                unevaluated.append(f'{operator}/{key}')

    if unevaluated:
        return (
            'unknown',
            f'trust policy carries conditions this check does not evaluate '
            f'({", ".join(sorted(set(unevaluated)))}); HealthOmics may still be unable to '
            f'assume the role',
        )
    return ('permits', None)


def evaluate_healthomics_trust(
    assume_role_policy: Any,
    region: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Tuple[str, str]:
    """Evaluate whether HealthOmics can assume a role for a run in this region.

    Naming ``omics.amazonaws.com`` as a trusted principal is necessary but not
    sufficient. AWS documents a confused-deputy guard for this trust policy that
    scopes it with ``aws:SourceArn`` and ``aws:SourceAccount``, and a role scoped to
    another region is rejected by StartRun with ``IAM role is invalid or
    inaccessible`` even though the principal is present.

    Args:
        assume_role_policy: AssumeRolePolicyDocument, as a dict or a JSON string
        region: Region the run will start in
        account_id: Account the run will start in

    Returns:
        Tuple of (status, detail) where status is one of the module's STATUS_ values
    """
    if isinstance(assume_role_policy, str):
        try:
            assume_role_policy = json.loads(assume_role_policy)
        except json.JSONDecodeError:
            return (STATUS_FAIL, 'Trust policy could not be parsed as JSON')

    if not isinstance(assume_role_policy, dict):
        return (STATUS_FAIL, 'Trust policy is missing or not an object')

    exclusions: List[str] = []
    unknowns: List[str] = []

    for statement in assume_role_policy.get('Statement', []):
        if not isinstance(statement, dict) or statement.get('Effect') != 'Allow':
            continue
        services = [str(s) for s in _as_list(statement.get('Principal', {}).get('Service'))]
        if HEALTHOMICS_PRINCIPAL not in services:
            continue

        condition = statement.get('Condition') or {}
        if not condition:
            return (
                STATUS_PASS,
                f'{HEALTHOMICS_PRINCIPAL} is allowed to assume this role without conditions',
            )

        verdict, reason = _statement_condition_verdict(condition, region, account_id)
        if verdict == 'permits':
            return (
                STATUS_PASS,
                f'{HEALTHOMICS_PRINCIPAL} is allowed to assume this role, and its trust '
                f'conditions permit a run in {region} / {account_id}',
            )
        if verdict == 'excludes' and reason:
            exclusions.append(reason)
        elif reason:
            unknowns.append(reason)

    if exclusions:
        return (
            STATUS_FAIL,
            f'{HEALTHOMICS_PRINCIPAL} is named in the trust policy, but no statement permits '
            f'this run: {"; ".join(exclusions)}. StartRun reports this as '
            f'"IAM role is invalid or inaccessible".',
        )
    if unknowns:
        return (STATUS_WARN, '; '.join(unknowns))
    return (
        STATUS_FAIL,
        f'Trust policy does not allow {HEALTHOMICS_PRINCIPAL} to assume this role. '
        f'HealthOmics cannot use it to start runs.',
    )


def extract_s3_uris(parameters: Any) -> List[str]:
    """Recursively collect S3 URIs from a run parameters structure.

    Walks nested dicts and lists so that File inputs inside Structs, Arrays and
    Maps are all discovered.

    Args:
        parameters: Run parameters (dict, list, or scalar)

    Returns:
        Sorted list of unique S3 URIs found
    """
    found: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, str):
            if node.startswith('s3://'):
                found.add(node)
        elif isinstance(node, dict):
            for value in node.values():
                _walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                _walk(value)

    _walk(parameters)
    return sorted(found)


async def validate_run_readiness(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow the run will use',
    ),
    role_arn: str = Field(
        ...,
        description='ARN of the IAM service role intended for the run',
    ),
    output_uri: str = Field(
        ...,
        description='S3 URI where run outputs will be written (e.g. s3://bucket/prefix/)',
    ),
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description='Run parameters. Any S3 URIs found in the values (including inside '
        'nested Structs, Arrays and Maps) are checked for existence.',
    ),
    container_images: Optional[List[str]] = Field(
        None,
        description='Optional list of ECR container image URIs used by the workflow. '
        'Each is checked for availability and HealthOmics accessibility. Extract these '
        'from the runtime/container directives in the workflow definition.',
    ),
    workflow_version_name: Optional[str] = Field(
        None,
        description='Optional workflow version name. Only used for reporting context.',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Run pre-flight checks before starting a HealthOmics workflow run.

    Validates the prerequisites that most commonly cause runs to fail, without
    starting a run or incurring compute cost. All checks are attempted so that a
    single call reports every problem found, rather than stopping at the first one.

    Checks performed:
    1. Workflow exists and is ACTIVE
    2. IAM role exists
    3. IAM role trust policy allows the HealthOmics service principal
    4. Output S3 bucket exists
    5. Output S3 bucket region matches the workflow region
    6. IAM role can write to the output location (best-effort, via policy simulation)
    7. Container images are available and accessible by HealthOmics (if provided)
    8. Input S3 objects referenced in parameters exist (if provided)

    Check 6 requires the caller to hold iam:SimulatePrincipalPolicy. When that
    permission is missing the check reports 'warn' rather than 'fail', because the
    run may still succeed.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow the run will use
        role_arn: ARN of the IAM service role intended for the run
        output_uri: S3 URI where run outputs will be written
        parameters: Optional run parameters; S3 URIs in values are checked
        container_images: Optional list of ECR image URIs to verify
        workflow_version_name: Optional version name, for reporting context only
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing:
        - ready: True only when no check failed
        - summary: Human-readable counts of pass/warn/fail
        - checks: List of individual check results, each with name, status and detail
    """
    try:
        # Handle Field objects for optional parameters (FastMCP compatibility)
        for _name, _value in (
            ('parameters', parameters),
            ('container_images', container_images),
            ('workflow_version_name', workflow_version_name),
        ):
            if hasattr(_value, 'default'):
                if _name == 'parameters':
                    parameters = getattr(_value, 'default', None)
                elif _name == 'container_images':
                    container_images = getattr(_value, 'default', None)
                else:
                    workflow_version_name = getattr(_value, 'default', None)

        checks: List[Dict[str, Any]] = []

        session = get_aws_session(region_name=aws_region, profile_name=aws_profile)
        effective_region = session.region_name
        omics_client = get_omics_client(region_name=aws_region, profile_name=aws_profile)
        iam_client = get_iam_client(region_name=aws_region, profile_name=aws_profile)
        s3_client = session.client('s3')

        # --- Check 1: workflow exists and is ACTIVE ---
        workflow_status = None
        try:
            workflow = omics_client.get_workflow(id=workflow_id)
            workflow_status = workflow.get('status')
            if workflow_status == 'ACTIVE':
                checks.append(
                    _check(
                        'workflow_active',
                        STATUS_PASS,
                        f'Workflow {workflow_id} is ACTIVE',
                    )
                )
            else:
                checks.append(
                    _check(
                        'workflow_active',
                        STATUS_FAIL,
                        f'Workflow {workflow_id} status is {workflow_status}; '
                        f'a run can only start from an ACTIVE workflow. '
                        f'statusMessage: {workflow.get("statusMessage")}',
                    )
                )
        except ClientError as e:
            checks.append(
                _check(
                    'workflow_active',
                    STATUS_FAIL,
                    f'Could not retrieve workflow {workflow_id}: '
                    f'{e.response["Error"].get("Message", str(e))}',
                )
            )

        # --- Checks 2 and 3: IAM role exists and trusts HealthOmics ---
        role_name = role_arn.split('/')[-1] if '/' in role_arn else None
        # The account the run will be attributed to, taken from the role ARN
        arn_parts = role_arn.split(':')
        role_account_id = arn_parts[4] if len(arn_parts) > 4 else None
        if not role_name:
            checks.append(
                _check(
                    'role_exists',
                    STATUS_FAIL,
                    f'Could not parse a role name from ARN: {role_arn}',
                )
            )
        else:
            try:
                role = iam_client.get_role(RoleName=role_name)['Role']
                checks.append(_check('role_exists', STATUS_PASS, f'Role {role_name} exists'))

                trust_status, trust_detail = evaluate_healthomics_trust(
                    role.get('AssumeRolePolicyDocument'),
                    region=effective_region,
                    account_id=role_account_id,
                )
                checks.append(_check('role_trust_policy', trust_status, trust_detail))
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ('NoSuchEntity', 'AccessDenied'):
                    status = STATUS_FAIL if error_code == 'NoSuchEntity' else STATUS_WARN
                    checks.append(
                        _check(
                            'role_exists',
                            status,
                            f'Could not read role {role_name}: '
                            f'{e.response["Error"].get("Message", str(e))}',
                        )
                    )
                else:
                    checks.append(
                        _check('role_exists', STATUS_WARN, f'Could not read role: {str(e)}')
                    )

        # --- Checks 4, 5 and 6: output location ---
        output_bucket: Optional[str] = None
        output_prefix = ''
        try:
            output_bucket, output_prefix = parse_s3_path(output_uri)
        except ValueError as e:
            checks.append(_check('output_uri_format', STATUS_FAIL, str(e)))

        if output_bucket:
            bucket_region: Optional[str] = None
            try:
                s3_client.head_bucket(Bucket=output_bucket)
                checks.append(
                    _check('output_bucket_exists', STATUS_PASS, f'Bucket {output_bucket} exists')
                )

                location = s3_client.get_bucket_location(Bucket=output_bucket)
                # us-east-1 is reported as None by the S3 API
                bucket_region = location.get('LocationConstraint') or 'us-east-1'
                if bucket_region == effective_region:
                    checks.append(
                        _check(
                            'output_bucket_region',
                            STATUS_PASS,
                            f'Bucket is in {bucket_region}, matching the run region',
                        )
                    )
                else:
                    checks.append(
                        _check(
                            'output_bucket_region',
                            STATUS_FAIL,
                            f'Bucket {output_bucket} is in {bucket_region} but the run region '
                            f'is {effective_region}. HealthOmics requires the output bucket to '
                            f'be in the same region as the run.',
                        )
                    )
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ('404', 'NoSuchBucket'):
                    detail = f'Bucket {output_bucket} does not exist'
                elif error_code in ('403', 'AccessDenied'):
                    detail = (
                        f'Access denied reading bucket {output_bucket}. The bucket may exist '
                        f'but the current caller cannot inspect it.'
                    )
                else:
                    detail = f'Could not inspect bucket {output_bucket}: {str(e)}'
                status = STATUS_WARN if error_code in ('403', 'AccessDenied') else STATUS_FAIL
                checks.append(_check('output_bucket_exists', status, detail))

            # Best-effort permission simulation for the service role
            if role_arn:
                resource_arn = f'arn:aws:s3:::{output_bucket}/{output_prefix.rstrip("/")}/*'
                try:
                    simulation = iam_client.simulate_principal_policy(
                        PolicySourceArn=role_arn,
                        ActionNames=['s3:PutObject'],
                        ResourceArns=[resource_arn],
                    )
                    decisions = [
                        r.get('EvalDecision') for r in simulation.get('EvaluationResults', [])
                    ]
                    if decisions and all(d == 'allowed' for d in decisions):
                        checks.append(
                            _check(
                                'role_s3_write',
                                STATUS_PASS,
                                f'Role is allowed s3:PutObject on {resource_arn}',
                            )
                        )
                    else:
                        checks.append(
                            _check(
                                'role_s3_write',
                                STATUS_FAIL,
                                f'Policy simulation returned {decisions} for s3:PutObject on '
                                f'{resource_arn}. The run will not be able to write outputs.',
                            )
                        )
                except ClientError as e:
                    checks.append(
                        _check(
                            'role_s3_write',
                            STATUS_WARN,
                            f'Could not simulate role permissions ({e.response["Error"]["Code"]}). '
                            f'This check needs iam:SimulatePrincipalPolicy; the run may still '
                            f'succeed.',
                        )
                    )

        # --- Check 7: container images ---
        if container_images:
            for image_uri in container_images:
                parts = parse_ecr_image_uri(image_uri)
                if parts is None:
                    checks.append(
                        _check(
                            f'container:{image_uri}',
                            STATUS_FAIL,
                            'Not a private ECR image URI. HealthOmics can only pull images from '
                            'ECR repositories it has access to. Use a registry map or replace '
                            'the URI with a private ECR URI.',
                        )
                    )
                    continue

                availability = await check_container_availability(
                    ctx,
                    repository_name=parts['repository'],
                    image_tag=parts.get('tag', 'latest'),
                    image_digest=parts.get('digest'),
                    initiate_pull_through=False,
                    aws_profile=aws_profile,
                    aws_region=aws_region,
                )

                available = availability.get('available')
                accessible = availability.get('healthomics_accessible')
                if available and accessible == 'accessible':
                    checks.append(
                        _check(f'container:{image_uri}', STATUS_PASS, availability.get('message'))
                    )
                elif available:
                    checks.append(
                        _check(
                            f'container:{image_uri}',
                            STATUS_FAIL,
                            f'Image exists but HealthOmics accessibility is "{accessible}". '
                            f'{availability.get("message")}',
                        )
                    )
                else:
                    checks.append(
                        _check(
                            f'container:{image_uri}',
                            STATUS_FAIL,
                            availability.get('message', 'Image not available'),
                        )
                    )

        # --- Check 8: input S3 objects ---
        if parameters:
            for uri in extract_s3_uris(parameters):
                try:
                    bucket, key = parse_s3_path(uri)
                except ValueError as e:
                    checks.append(_check(f'input:{uri}', STATUS_FAIL, str(e)))
                    continue

                if not key:
                    # A bucket-only URI cannot be checked as an object
                    checks.append(
                        _check(
                            f'input:{uri}',
                            STATUS_WARN,
                            'URI has no key; skipped object existence check',
                        )
                    )
                    continue

                try:
                    s3_client.head_object(Bucket=bucket, Key=key)
                    checks.append(_check(f'input:{uri}', STATUS_PASS, 'Object exists'))
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code in ('404', 'NoSuchKey'):
                        checks.append(_check(f'input:{uri}', STATUS_FAIL, 'Object not found'))
                    elif error_code in ('403', 'AccessDenied'):
                        checks.append(
                            _check(
                                f'input:{uri}',
                                STATUS_WARN,
                                'Access denied to the current caller; the run role may still '
                                'have access',
                            )
                        )
                    else:
                        checks.append(
                            _check(f'input:{uri}', STATUS_WARN, f'Could not check: {str(e)}')
                        )

        pass_count = sum(1 for c in checks if c['status'] == STATUS_PASS)
        warn_count = sum(1 for c in checks if c['status'] == STATUS_WARN)
        fail_count = sum(1 for c in checks if c['status'] == STATUS_FAIL)

        result = {
            'ready': fail_count == 0,
            'summary': (
                f'{fail_count} failed, {warn_count} warnings, {pass_count} passed '
                f'({len(checks)} checks)'
            ),
            'checks': checks,
        }
        if workflow_version_name:
            result['workflowVersionName'] = workflow_version_name

        logger.info(
            f'validate_run_readiness for workflow {workflow_id}: '
            f'ready={result["ready"]} ({result["summary"]})'
        )
        return result

    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error validating run readiness')
