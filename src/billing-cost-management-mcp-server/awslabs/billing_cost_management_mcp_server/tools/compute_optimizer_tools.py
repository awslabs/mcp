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

"""AWS Compute Optimizer tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

import botocore.session
import os
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from ..utilities.logging_utils import get_context_logger
from ..utilities.time_utils import timestamp_to_utc_iso_string
from botocore import xform_name
from botocore.exceptions import ClientError
from fastmcp import Context, FastMCP
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple


compute_optimizer_server = FastMCP(
    name='compute-optimizer-tools', instructions='Tools for working with AWS Compute Optimizer API'
)


@compute_optimizer_server.tool(
    name='compute-optimizer',
    description="""Retrieves recommendations from AWS Compute Optimizer.

IMPORTANT USAGE GUIDELINES:
- Focus on recommendations with the highest estimated savings first
- Include all relevant details when presenting specific recommendations

USE THIS TOOL FOR:
- **Performance optimization** (CPU, memory, network utilization analysis)
- **Performance-based rightsizing** (not cost-based)
- **Idle resource detection only when filtering by a specific Finding** — Idle, Unattached,
  or Unused (use get_idle_recommendations). For general idle detection or cost-savings
  recommendations, use cost-optimization instead.

**Note:** Compute Optimizer is a regional service. Specify a `region` to get recommendations for resources in that region. If omitted, defaults to AWS_REGION env var or us-east-1.

This tool supports the following operations:
1. get_ec2_instance_recommendations: Get recommendations for EC2 instances
2. get_auto_scaling_group_recommendations: Get recommendations for Auto Scaling groups
3. get_ebs_volume_recommendations: Get recommendations for EBS volumes
4. get_lambda_function_recommendations: Get recommendations for Lambda functions
5. get_rds_recommendations: Get recommendations for RDS and Aurora databases
6. get_ecs_service_recommendations: Get recommendations for ECS services
7. get_idle_recommendations: Get idle resource recommendations across supported resource types

Each call is scoped to one region (the `region` parameter) and optionally one account ID,
and can be narrowed with `filters`, a JSON array of {"name": ..., "values": [...]}.
Accepted filter names:
- get_ec2_instance_recommendations: Finding (Underprovisioned, Overprovisioned, Optimized),
  FindingReasonCodes (e.g. CPUOverprovisioned, MemoryUnderprovisioned),
  RecommendationSourceType (Ec2Instance, AutoScalingGroup), InferredWorkloadTypes (e.g. Redis)
- get_auto_scaling_group_recommendations: Finding (Optimized, NotOptimized),
  RecommendationSourceType, InferredWorkloadTypes (no FindingReasonCodes)
- get_ebs_volume_recommendations: Finding (Optimized, NotOptimized)
- get_lambda_function_recommendations: Finding (Optimized, NotOptimized, Unavailable),
  FindingReasonCode (MemoryOverprovisioned, MemoryUnderprovisioned, InsufficientData,
  Inconclusive). Unavailable functions are left out of unfiltered results; request them
  with Finding=Unavailable.
- get_rds_recommendations: InstanceFinding / StorageFinding (Optimized, Underprovisioned,
  Overprovisioned; storage also NotOptimized), InstanceFindingReasonCode,
  StorageFindingReasonCode, Idle (True, False). RDS has no plain `Finding` or
  `FindingReasonCode` filter: pick the instance or storage variant (a plain one is
  rejected with the choices listed).
- get_ecs_service_recommendations: Finding (Optimized, Underprovisioned, Overprovisioned),
  FindingReasonCode (CPU/Memory Overprovisioned/Underprovisioned)
- get_idle_recommendations: Finding (Idle, Unattached, Unused), ResourceType
Values are case-sensitive in the API; the tool folds near-misses (e.g.
`overprovisioned`, `OVER_PROVISIONED`, `finding`) onto the right spelling and echoes the
result as `applied_filters`. If the API still rejects a filter, the error lists
`valid_filters`.

To look up specific resources, pass `resource_arns` as a JSON array of ARNs (e.g.
'["arn:aws:ec2:us-east-1:123456789012:instance/i-0abc"]'). This is sent as the
operation's ARN parameter (instanceArns, autoScalingGroupArns, volumeArns, functionArns,
serviceArns, or resourceArns for RDS and idle) so only those resources are returned,
instead of paging the full list. All ARNs must be in one region; when `region` is
omitted it is taken from the ARNs, and an explicit `region` must match them.

Common finding values (Finding filter values are PascalCase):
- Underprovisioned: The resource doesn't have enough capacity
- Overprovisioned: The resource has excess capacity and could be downsized
- Optimized: The resource is already optimized
- NotOptimized: A better-performing or cheaper option exists (Auto Scaling groups, EBS,
  Lambda, and RDS storage; not EC2 instances)
The returned `finding` field does not always use that spelling: EC2 instance
recommendations return UPPER_SNAKE (OVER_PROVISIONED, UNDER_PROVISIONED, OPTIMIZED), and
other types may too. Match returned findings case- and underscore-insensitively.

For get_idle_recommendations, the `finding` field uses a distinct enum:
- Idle: Provisioned and running, but utilization is so low it is effectively doing nothing
- Unattached: Resource exists but isn't connected to anything
- Unused: Resource is provisioned but sees no meaningful activity
Its `filters` accept the filter names `Finding` (values: Idle, Unattached, Unused) and
`ResourceType`. Finding and ResourceType values are matched case-insensitively and
normalized to the idle enum spelling (e.g. ebsvolume is sent as EBSVolume, idle as Idle).
Idle results are sorted by estimated monthly savings after discounts, highest first, by
default. To change it, pass `order_by` as a JSON object, e.g.
'{"dimension": "SavingsValue", "order": "Asc"}' (dimension: SavingsValue or
SavingsValueAfterDiscount; order: Asc or Desc). Only get_idle_recommendations accepts
`order_by`.""",
)
async def compute_optimizer(
    ctx: Context,
    operation: str,
    region: Optional[str] = None,
    max_results: Optional[int] = None,
    filters: Optional[str] = None,
    account_ids: Optional[str] = None,
    next_token: Optional[str] = None,
    resource_arns: Optional[str] = None,
    order_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves recommendations from AWS Compute Optimizer.

    Args:
        ctx: The MCP context
        operation: The operation to perform (e.g., 'get_ec2_instance_recommendations')
        region: AWS region to query (e.g., 'us-west-2'). Defaults to AWS_REGION env var or us-east-1.
        max_results: Maximum number of results per page (up to 1000; up to 100 for
            get_idle_recommendations)
        filters: Optional filter expression as JSON string
        account_ids: Optional list of AWS account IDs as JSON array string
        next_token: Optional pagination token from a previous response
        resource_arns: Optional JSON array of resource ARNs to return recommendations for
        order_by: get_idle_recommendations only. Optional JSON object
            {"dimension": "SavingsValue"|"SavingsValueAfterDiscount", "order": "Asc"|"Desc"};
            defaults to SavingsValueAfterDiscount, Desc

    Returns:
        Dict containing the Compute Optimizer recommendations
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Log the request
        await ctx_logger.info(f'Compute Optimizer operation: {operation}')

        # Parse resource ARNs and resolve the region they live in
        arn_list = _parse_resource_arns(resource_arns)
        if arn_list:
            region = _resolve_region_for_arns(arn_list, region)

        # Only the idle API can sort; reject order_by elsewhere instead of ignoring it.
        if order_by and operation in _FILTER_SPECS and operation != 'get_idle_recommendations':
            return _error_response(
                operation,
                'validation_error',
                f'order_by is supported only by get_idle_recommendations, not {operation}.',
                {'provided_order_by': order_by},
            )

        # Initialize Compute Optimizer client using shared utility
        co_client = create_aws_client('compute-optimizer', region_name=region)

        # Check enrollment status first to provide better error messages
        try:
            enrollment_status = co_client.get_enrollment_status()
            status = enrollment_status.get('status', '')

            # Map operations to required resource types
            resource_type_mapping = {
                'get_ec2_instance_recommendations': 'ec2Instance',
                'get_auto_scaling_group_recommendations': 'autoScalingGroup',
                'get_ebs_volume_recommendations': 'ebsVolume',
                'get_lambda_function_recommendations': 'lambdaFunction',
                'get_rds_recommendations': 'rdsDBInstance',
                'get_ecs_service_recommendations': 'ecsService',
                # Idle recommendations span multiple resource types; a non-empty
                # value simply triggers the shared enrollment ACTIVE check below.
                'get_idle_recommendations': 'idle',
            }

            # Get required resource type for current operation
            required_resource_type = resource_type_mapping.get(operation)

            # If we have a valid operation, check enrollment
            if required_resource_type:
                # Check overall enrollment status
                if status.upper() != 'ACTIVE':
                    return format_response(
                        'error',
                        {
                            'error_type': 'enrollment_error',
                            'enrollment_status': status,
                            'operation': operation,
                            'aws_error_code': 'ComputeOptimizerNotActive',
                            'aws_region': region or os.environ.get('AWS_REGION', 'us-east-1'),
                        },
                        'Compute Optimizer is not active. Please activate the service in the AWS Console first.',
                    )

        except ClientError as e:
            # Specific error handling for enrollment status checking
            aws_error = e.response.get('Error', {})
            error_code = aws_error.get('Code', 'UnknownError')

            if error_code == 'AccessDeniedException' or error_code == 'AccessDenied':
                await ctx_logger.warning(f'Access denied for enrollment status check: {str(e)}')
                # Continue execution even if we can't check enrollment
            else:
                # For other enrollment checking errors, log but continue
                await ctx_logger.warning(f'Could not check Compute Optimizer enrollment: {str(e)}')

        # Process the operation
        if operation == 'get_ec2_instance_recommendations':
            return await get_ec2_instance_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token, arn_list
            )
        elif operation == 'get_auto_scaling_group_recommendations':
            return await get_auto_scaling_group_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token, arn_list
            )
        elif operation == 'get_ebs_volume_recommendations':
            return await get_ebs_volume_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token, arn_list
            )
        elif operation == 'get_lambda_function_recommendations':
            return await get_lambda_function_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token, arn_list
            )
        elif operation == 'get_rds_recommendations':
            return await get_rds_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token, arn_list
            )
        elif operation == 'get_ecs_service_recommendations':
            return await get_ecs_service_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token, arn_list
            )
        elif operation == 'get_idle_recommendations':
            return await get_idle_recommendations(
                ctx,
                co_client,
                max_results,
                filters,
                account_ids,
                next_token,
                arn_list,
                order_by=order_by,
            )
        else:
            return format_response(
                'error',
                {
                    'error_type': 'invalid_operation',
                    'provided_operation': operation,
                    'valid_operations': [
                        'get_ec2_instance_recommendations',
                        'get_auto_scaling_group_recommendations',
                        'get_ebs_volume_recommendations',
                        'get_lambda_function_recommendations',
                        'get_rds_recommendations',
                        'get_ecs_service_recommendations',
                        'get_idle_recommendations',
                    ],
                },
                f"Unsupported operation: {operation}. Use 'get_ec2_instance_recommendations', 'get_auto_scaling_group_recommendations', 'get_ebs_volume_recommendations', 'get_lambda_function_recommendations', 'get_rds_recommendations', 'get_ecs_service_recommendations' or 'get_idle_recommendations'.",
            )

    except ClientError as e:
        # Specific handling for AWS service errors
        aws_error = e.response.get('Error', {})
        error_code = aws_error.get('Code', 'UnknownError')
        aws_message = aws_error.get('Message', 'No error message provided')
        request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'Unknown')
        http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)

        # Create detailed error response
        error_response = {
            'status': 'error',
            'error_type': 'access_denied',  # Default, will be overridden
            'message': 'An error occurred',  # Default, will be overridden
            'data': {
                'service': 'Compute Optimizer',
                'operation': operation,
                'aws_error_code': error_code,
                'aws_error_message': aws_message,
                'request_id': request_id,
                'http_status': http_status,
            },
        }

        # Handle specific error codes with improved messages
        if error_code == 'AccessDeniedException' or error_code == 'AccessDenied':
            error_response['error_type'] = 'access_denied'
            error_response['message'] = (
                f'Access denied for Compute Optimizer {operation}. Ensure you have the compute-optimizer:{operation} permission.'
            )
            error_response['resolution'] = (
                'Check your IAM permissions and ensure your role has the ComputeOptimizerReadOnlyAccess policy or equivalent permissions.'
            )
            await ctx_logger.error(
                f'Access denied error for {operation}: {aws_message}', exc_info=True
            )

        elif error_code == 'OptInRequiredException':
            error_response['error_type'] = 'opt_in_required'
            error_response['message'] = (
                'Compute Optimizer requires opt-in before accessing recommendations.'
            )
            error_response['resolution'] = (
                'Enable Compute Optimizer in the AWS Console for your account/organization.'
            )
            await ctx_logger.error(f'Opt-in required: {aws_message}', exc_info=True)

        elif error_code == 'ValidationException':
            error_response['error_type'] = 'validation_error'
            error_response['message'] = f'Compute Optimizer validation error: {aws_message}'
            error_response['resolution'] = (
                'Check your request parameters and ensure resources are correctly configured.'
            )
            await ctx_logger.error(
                f'Validation error for {operation}: {aws_message}', exc_info=True
            )

        elif error_code == 'ThrottlingException' or error_code == 'Throttling':
            error_response['error_type'] = 'throttling_error'
            error_response['message'] = (
                'The Compute Optimizer API is throttling your requests. Please try again later.'
            )
            error_response['resolution'] = (
                'Implement backoff retry logic or reduce request frequency.'
            )
            await ctx_logger.error(f'API throttling for {operation}: {aws_message}', exc_info=True)

        elif error_code == 'ServiceUnavailableException':
            error_response['error_type'] = 'service_unavailable'
            error_response['message'] = (
                'Compute Optimizer service is temporarily unavailable. Please try again later.'
            )
            error_response['resolution'] = (
                'This is a temporary condition. Retry after a brief wait.'
            )
            await ctx_logger.error(f'Service unavailable: {aws_message}', exc_info=True)

        elif error_code == 'ResourceNotFoundException':
            error_response['error_type'] = 'resource_not_found'
            error_response['message'] = f'The requested resource was not found: {aws_message}'
            error_response['resolution'] = (
                'Verify resource identifiers and ensure resources exist.'
            )
            await ctx_logger.error(f'Resource not found: {aws_message}', exc_info=True)

        else:
            # For other AWS errors, use the generic handler
            return await handle_aws_error(ctx, e, operation, 'Compute Optimizer')

        return error_response

    except ValueError as e:
        # Specific handling for validation errors
        error_details = {
            'status': 'error',
            'error_type': 'validation_error',
            'service': 'Compute Optimizer',
            'operation': operation,
            'message': f'Invalid parameter: {str(e)}',
            'details': str(e),
        }
        await ctx_logger.warning(f'Validation error in {operation}: {str(e)}')
        return error_details

    except Exception as e:
        # Add detailed logging for troubleshooting
        await ctx_logger.error(
            f'Unhandled exception in compute_optimizer: {e.__class__.__name__}: {str(e)}',
            exc_info=True,
        )

        # Use shared error handler for other unexpected exceptions
        return await handle_aws_error(ctx, e, operation, 'Compute Optimizer')


def _parse_resource_arns(resource_arns: Optional[str]) -> Optional[List[str]]:
    """Parse the resource_arns JSON array into a list of ARN strings.

    A single unwrapped ARN is accepted too, since callers sometimes pass one bare.
    """
    if not resource_arns:
        return None
    if resource_arns.strip().startswith('arn:'):
        parsed: Any = [resource_arns.strip()]
    else:
        parsed = parse_json(resource_arns, 'resource_arns')
    if not isinstance(parsed, list) or not all(
        isinstance(arn, str) and arn.startswith('arn:') for arn in parsed
    ):
        raise ValueError('resource_arns must be a JSON array of ARN strings')
    return parsed or None


def _resolve_region_for_arns(arns: List[str], region: Optional[str]) -> Optional[str]:
    """Return the region to query for the given ARNs.

    Compute Optimizer is regional, so every ARN must be in the queried region. When no
    region is given, use the one the ARNs share.
    """
    arn_regions = {parts[3] for parts in (arn.split(':') for arn in arns) if len(parts) > 3}
    arn_regions.discard('')
    if len(arn_regions) > 1:
        raise ValueError(
            f'resource_arns span multiple regions ({", ".join(sorted(arn_regions))}); '
            'make one call per region'
        )
    if not arn_regions:
        return region
    arn_region = arn_regions.pop()
    if region and region.casefold() != arn_region.casefold():
        raise ValueError(
            f'resource_arns are in {arn_region} but region is {region}; '
            'Compute Optimizer only returns resources from the queried region'
        )
    return arn_region


_CO_SERVICE_NAME = 'Compute Optimizer'

# Filter name -> accepted values, per operation. A string names the botocore enum shape
# that holds the values; a tuple lists them directly where the filter accepts only a
# documented subset of the response enum (the EC2 Finding filter accepts only
# Underprovisioned/Overprovisioned/Optimized, the ASG one only Optimized/NotOptimized;
# the live API rejects the rest). The service's
# InvalidParameterValue message names neither the rejected value nor the valid set, so
# this table is what lets a caller self-correct.
_FILTER_SPECS: Dict[str, Dict[str, Any]] = {
    'get_ec2_instance_recommendations': {
        'Finding': ('Underprovisioned', 'Overprovisioned', 'Optimized'),
        'FindingReasonCodes': 'InstanceRecommendationFindingReasonCode',
        'RecommendationSourceType': ('Ec2Instance', 'AutoScalingGroup'),
        'InferredWorkloadTypes': 'InferredWorkloadType',
    },
    'get_auto_scaling_group_recommendations': {
        'Finding': ('Optimized', 'NotOptimized'),
        'RecommendationSourceType': ('Ec2Instance', 'AutoScalingGroup'),
        'InferredWorkloadTypes': 'InferredWorkloadType',
    },
    'get_ebs_volume_recommendations': {
        'Finding': 'EBSFinding',
    },
    'get_lambda_function_recommendations': {
        'Finding': 'LambdaFunctionRecommendationFinding',
        'FindingReasonCode': 'LambdaFunctionRecommendationFindingReasonCode',
    },
    'get_rds_recommendations': {
        'InstanceFinding': 'RDSInstanceFinding',
        'InstanceFindingReasonCode': 'RDSInstanceFindingReasonCode',
        'StorageFinding': 'RDSStorageFinding',
        'StorageFindingReasonCode': 'RDSStorageFindingReasonCode',
        'Idle': 'Idle',
    },
    'get_ecs_service_recommendations': {
        'Finding': 'ECSServiceRecommendationFinding',
        'FindingReasonCode': 'ECSServiceRecommendationFindingReasonCode',
    },
    'get_idle_recommendations': {
        'ResourceType': 'IdleRecommendationResourceType',
        'Finding': 'IdleFinding',
    },
}

# Tool operation -> boto3 client method, used to look up each operation's request model.
_API_METHODS = {
    'get_ec2_instance_recommendations': 'get_ec2_instance_recommendations',
    'get_auto_scaling_group_recommendations': 'get_auto_scaling_group_recommendations',
    'get_ebs_volume_recommendations': 'get_ebs_volume_recommendations',
    'get_lambda_function_recommendations': 'get_lambda_function_recommendations',
    'get_rds_recommendations': 'get_rds_database_recommendations',
    'get_ecs_service_recommendations': 'get_ecs_service_recommendations',
    'get_idle_recommendations': 'get_idle_recommendations',
}

_IDLE_ORDER_BY_DIMENSIONS = ('SavingsValue', 'SavingsValueAfterDiscount')
_IDLE_ORDER_BY_ORDERS = ('Asc', 'Desc')
_IDLE_DEFAULT_ORDER_BY = {'dimension': 'SavingsValueAfterDiscount', 'order': 'Desc'}

_DEFAULT_MAX_RESULTS_LIMIT = 1000
_MAX_RESULTS_LIMITS = {'get_idle_recommendations': 100}


def _error_response(
    operation: str, error_type: str, message: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build an error response with top-level service, operation, and error_type.

    Matches the shape handle_aws_error returns, so the failure is classifiable; the
    status/data/message payload is kept alongside.
    """
    return format_response(
        'error',
        data or {},
        message,
        error_type=error_type,
        operation=operation,
        service=_CO_SERVICE_NAME,
    )


def _filter_value_key(value: str) -> str:
    """Fold a filter value for matching: case- and underscore-insensitive.

    Lets the UPPER_SNAKE spelling EC2 returns in its `finding` field (OVER_PROVISIONED)
    be passed back as a filter value (Overprovisioned).
    """
    return value.casefold().replace('_', '')


def _filter_name_key(name: str) -> str:
    """Fold a filter name for matching: case-insensitive, singular/plural agnostic."""
    return name.casefold().removesuffix('s')


@lru_cache(maxsize=1)
def _model_filter_names() -> Dict[str, List[str]]:
    """Return {operation: filter names its API accepts}, read from the botocore model.

    Returns an empty map if the service model cannot be loaded.
    """
    try:
        service_model: Any = botocore.session.get_session().get_service_model('compute-optimizer')
        api_names = {xform_name(name): name for name in service_model.operation_names}
        return {
            operation: list(
                service_model.operation_model(api_names[method])
                .input_shape.members['filters']
                .member.members['name']
                .enum
            )
            for operation, method in _API_METHODS.items()
        }
    except Exception:
        return {}


def _ambiguous_filter_names(operation: str) -> Dict[str, List[str]]:
    """Return {folded name: real names} for filter names this operation splits in two.

    A name that is a filter on another operation (e.g. `Finding`) but not on this one,
    while two or more of this operation's filters end with it (RDS `InstanceFinding` and
    `StorageFinding`), is ambiguous: it gets a structured error rather than a guess.
    """
    all_names = _model_filter_names()
    own = all_names.get(operation, [])
    own_keys = {_filter_name_key(name) for name in own}
    other_keys = {_filter_name_key(name) for names in all_names.values() for name in names}
    ambiguous = {}
    for key in sorted(other_keys - own_keys):
        matches = [name for name in own if _filter_name_key(name).endswith(key)]
        if len(matches) > 1:
            ambiguous[key] = matches
    return ambiguous


def _spec_values(spec: Any) -> List[str]:
    """Resolve a _FILTER_SPECS entry (tuple or botocore enum shape name) to its values."""
    if isinstance(spec, tuple):
        return list(spec)
    return sorted(_idle_enum_canonical_map(spec).values())


def _valid_filter_values(operation: str) -> Dict[str, List[str]]:
    """Return {filter name: accepted values} for an operation."""
    return {name: _spec_values(spec) for name, spec in _FILTER_SPECS.get(operation, {}).items()}


def _normalize_filters(operation: str, filters: Any) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """Fold filter keys, names, and values onto the spelling the API expects.

    The API is case-sensitive on all three and rejects a near-miss with a bare
    "Invalid filter value/name". Values also fold underscores, so a returned EC2 finding
    (OVER_PROVISIONED) can be passed back as a filter. Tag filters (tag:<key>, tag-key)
    keep their key and values as given. Names and values that match nothing are passed
    through unchanged, so the service stays the authority on what is valid.

    Returns:
        (normalized filters, None), or (original filters, error response) when a name is
        ambiguous on this operation.
    """
    if not isinstance(filters, list):
        return filters, None

    spec = _FILTER_SPECS.get(operation, {})
    names_by_key = {_filter_name_key(name): name for name in spec}
    ambiguous = _ambiguous_filter_names(operation)

    normalized = []
    for f in filters:
        if not isinstance(f, dict):
            normalized.append(f)
            continue
        # Accept Name/Values as well as name/values.
        f = {
            (k.casefold() if isinstance(k, str) and k.casefold() in ('name', 'values') else k): v
            for k, v in f.items()
        }
        name = f.get('name')
        if not isinstance(name, str):
            normalized.append(f)
            continue

        folded = name.casefold()
        if folded == 'tag-key':
            normalized.append({**f, 'name': 'tag-key'})
            continue
        if folded.startswith('tag:'):
            normalized.append({**f, 'name': 'tag:' + name[4:]})
            continue

        key = _filter_name_key(name)
        if key in ambiguous and key not in names_by_key:
            choices = ambiguous[key]
            return filters, _error_response(
                operation,
                'validation_error',
                f'Filter name {name} is ambiguous for {operation}; use one of: '
                f'{", ".join(choices)}.',
                {
                    'submitted_filters': filters,
                    'filter_name_choices': choices,
                    'valid_filters': _valid_filter_values(operation),
                },
            )

        canonical_name = names_by_key.get(key, name)
        f = {**f, 'name': canonical_name}
        if canonical_name in spec and isinstance(f.get('values'), list):
            canonical = {
                _filter_value_key(value): value for value in _spec_values(spec[canonical_name])
            }
            f['values'] = [
                canonical.get(_filter_value_key(v), v) if isinstance(v, str) else v
                for v in f['values']
            ]
        normalized.append(f)
    return normalized, None


def _build_request_params(
    operation: str,
    max_results: Any,
    filters: Optional[str],
    account_ids: Optional[str],
    next_token: Optional[str],
    resource_arns: Optional[List[str]],
    arn_param: str,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Build the request for a get_*_recommendations call, validating locally first.

    Returns:
        (request params, None), or (partial params, error response) when a parameter is
        rejected before the call.
    """
    request_params: Dict[str, Any] = {}

    if max_results:
        max_results = int(max_results)
        limit = _MAX_RESULTS_LIMITS.get(operation, _DEFAULT_MAX_RESULTS_LIMIT)
        if max_results > limit:
            return request_params, _error_response(
                operation,
                'validation_error',
                f'max_results must be at most {limit} for {operation}; page through '
                'next_token for more.',
                {'provided_max_results': max_results, 'max_allowed': limit},
            )
        request_params['maxResults'] = max_results

    if filters:
        normalized, error = _normalize_filters(operation, parse_json(filters, 'filters'))
        if error:
            return request_params, error
        request_params['filters'] = normalized

    if account_ids:
        parsed_accounts = parse_json(account_ids, 'account_ids')
        if isinstance(parsed_accounts, list) and len(parsed_accounts) > 1:
            return request_params, _error_response(
                operation,
                'validation_error',
                'Compute Optimizer accepts one account ID per request; make one call per account.',
                {'provided_account_ids': parsed_accounts},
            )
        request_params['accountIds'] = parsed_accounts

    if next_token:
        request_params['nextToken'] = next_token

    # Restrict to specific resources if ARNs were provided
    if resource_arns:
        request_params[arn_param] = resource_arns

    return request_params, None


def _resolve_idle_order_by(
    order_by: Optional[str],
) -> Tuple[Dict[str, str], Optional[Dict[str, Any]]]:
    """Resolve the idle order_by input onto the API's orderBy, filling in the defaults.

    Keys and values fold case and underscores (the API rejects e.g. `desc`). A missing
    dimension or order takes the default (SavingsValueAfterDiscount, Desc).

    Returns:
        (orderBy, None), or (default orderBy, error response) for an invalid value.
    """
    operation = 'get_idle_recommendations'
    resolved = dict(_IDLE_DEFAULT_ORDER_BY)
    if not order_by:
        return resolved, None

    parsed = parse_json(order_by, 'order_by')
    valid = {'dimension': list(_IDLE_ORDER_BY_DIMENSIONS), 'order': list(_IDLE_ORDER_BY_ORDERS)}
    if not isinstance(parsed, dict):
        return resolved, _error_response(
            operation,
            'validation_error',
            'order_by must be a JSON object like {"dimension": "SavingsValueAfterDiscount", '
            '"order": "Desc"}.',
            {'provided_order_by': parsed, 'valid_order_by': valid},
        )

    for key, value in parsed.items():
        field = key.casefold() if isinstance(key, str) else key
        if field not in valid:
            return resolved, _error_response(
                operation,
                'validation_error',
                f'Unknown order_by key {key}; use dimension and/or order.',
                {'provided_order_by': parsed, 'valid_order_by': valid},
            )
        canonical = {_filter_value_key(v): v for v in valid[field]}
        match = canonical.get(_filter_value_key(value)) if isinstance(value, str) else None
        if match is None:
            return resolved, _error_response(
                operation,
                'validation_error',
                f'Invalid order_by {field}: {value}. Must be one of: {", ".join(valid[field])}.',
                {'provided_order_by': parsed, 'valid_order_by': valid},
            )
        resolved[field] = match
    return resolved, None


def _invalid_parameter_error(
    operation: str, error: ClientError, request_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Turn an InvalidParameterValueException into an actionable structured error."""
    aws_message = error.response.get('Error', {}).get('Message') or ''
    data: Dict[str, Any] = {
        'aws_error_code': 'InvalidParameterValueException',
        'aws_error_message': aws_message,
    }
    message = f'Compute Optimizer rejected the {operation} request: {aws_message}'
    if operation == 'get_idle_recommendations':
        # Keys this operation returned before the shared error shape; kept for compatibility.
        data.update(
            {
                'error_type': 'invalid_parameter_value',
                'operation': operation,
                'filters': request_params.get('filters'),
                'valid_resource_type_values': sorted(
                    _idle_enum_canonical_map(_IDLE_FILTER_ENUM_SHAPES['ResourceType']).values()
                ),
                'valid_finding_values': sorted(
                    _idle_enum_canonical_map(_IDLE_FILTER_ENUM_SHAPES['Finding']).values()
                ),
            }
        )
    # Point at the filters only when the service says a filter was the problem; the same
    # exception also covers e.g. an expired next_token or a malformed ARN.
    if 'filters' in request_params and 'filter' in aws_message.casefold():
        data['submitted_filters'] = request_params['filters']
        data['valid_filters'] = _valid_filter_values(operation)
        message += (
            ' The service does not say which filter or value it rejected: compare '
            'submitted_filters with valid_filters (names and values are case-sensitive) '
            'and retry.'
        )
    metadata = error.response.get('ResponseMetadata', {})
    return {
        **_error_response(operation, 'InvalidParameterValueException', message, data),
        # Request metadata handle_aws_error returned for this error before.
        'request_id': metadata.get('RequestId', 'Unknown'),
        'http_status': metadata.get('HTTPStatusCode', 0),
    }


def _call_recommendations_api(
    co_client: Any, method: str, operation: str, request_params: Dict[str, Any]
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Call a get_*_recommendations API, turning InvalidParameterValue into an error response.

    Returns (response, None), or ({}, error response). Other ClientErrors propagate to the
    dispatcher's error handling.
    """
    try:
        return getattr(co_client, method)(**request_params), None
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') != 'InvalidParameterValueException':
            raise
        return {}, _invalid_parameter_error(operation, e, request_params)


def _new_formatted_response(
    response: Dict[str, Any], request_params: Dict[str, Any], include_errors: bool = True
):
    """Start a formatted response with pagination, response-level errors, and filters.

    Set include_errors=False for APIs whose response has no `errors` member (Lambda), so
    the output doesn't imply "no errors" when the API cannot report any.
    """
    formatted_response: Dict[str, Any] = {'recommendations': []}
    if include_errors:
        formatted_response['errors'] = response.get('errors', [])
    formatted_response['next_token'] = response.get('nextToken')
    if 'filters' in request_params:
        # Echo what was actually queried (post-normalization), not what was typed.
        formatted_response['applied_filters'] = request_params['filters']
    return formatted_response


def _format_metrics(metrics: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Format utilization metrics as name/statistic/value entries."""
    return [
        {
            'name': metric.get('name'),
            'statistic': metric.get('statistic'),
            'value': metric.get('value'),
        }
        for metric in metrics or []
    ]


async def get_ec2_instance_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token, resource_arns=None
):
    """Get EC2 instance recommendations."""
    operation = 'get_ec2_instance_recommendations'
    request_params, error = _build_request_params(
        operation, max_results, filters, account_ids, next_token, resource_arns, 'instanceArns'
    )
    if error:
        return error

    response, error = _call_recommendations_api(
        co_client, 'get_ec2_instance_recommendations', operation, request_params
    )
    if error:
        return error

    formatted_response = _new_formatted_response(response, request_params)

    for recommendation in response.get('instanceRecommendations', []):
        current_instance = {
            'instance_type': recommendation.get('currentInstanceType'),
            'instance_name': recommendation.get('instanceName'),
            'instance_state': recommendation.get('instanceState'),
            'finding': recommendation.get('finding'),
            'finding_reason_codes': recommendation.get('findingReasonCodes', []),
            'current_performance_risk': recommendation.get('currentPerformanceRisk'),
            'inferred_workload_types': recommendation.get('inferredWorkloadTypes', []),
            'idle': recommendation.get('idle'),
            'gpu_info': recommendation.get('currentInstanceGpuInfo'),
        }

        instance_options = []
        for option in recommendation.get('recommendationOptions', []):
            instance_options.append(
                {
                    'instance_type': option.get('instanceType'),
                    'projected_utilization_metrics': option.get('projectedUtilizationMetrics'),
                    'performance_risk': option.get('performanceRisk'),
                    'rank': option.get('rank'),
                    'migration_effort': option.get('migrationEffort'),
                    'gpu_info': option.get('instanceGpuInfo'),
                    'platform_differences': option.get('platformDifferences', []),
                    'savings_opportunity': format_savings_opportunity(
                        option.get('savingsOpportunity', {})
                    ),
                    'savings_opportunity_after_discounts': format_savings_opportunity(
                        option.get('savingsOpportunityAfterDiscounts', {})
                    ),
                }
            )

        formatted_response['recommendations'].append(
            {
                'instance_arn': recommendation.get('instanceArn'),
                'account_id': recommendation.get('accountId'),
                'current_instance': current_instance,
                'recommendation_options': instance_options,
                'utilization_metrics': _format_metrics(recommendation.get('utilizationMetrics')),
                'lookback_period_in_days': recommendation.get('lookBackPeriodInDays'),
                'effective_recommendation_preferences': recommendation.get(
                    'effectiveRecommendationPreferences'
                ),
                'last_refresh_timestamp': format_timestamp(
                    recommendation.get('lastRefreshTimestamp')
                ),
                'external_metric_status': recommendation.get('externalMetricStatus'),
            }
        )

    return format_response('success', formatted_response)


def _format_asg_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Format an Auto Scaling group configuration (instance type and capacity)."""
    return {
        'instance_type': config.get('instanceType'),
        'desired_capacity': config.get('desiredCapacity'),
        'min_size': config.get('minSize'),
        'max_size': config.get('maxSize'),
        'allocation_strategy': config.get('allocationStrategy'),
        'type': config.get('type'),
        'mixed_instance_types': config.get('mixedInstanceTypes', []),
        'estimated_instance_hour_reduction_percentage': config.get(
            'estimatedInstanceHourReductionPercentage'
        ),
    }


async def get_auto_scaling_group_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token, resource_arns=None
):
    """Get Auto Scaling group recommendations."""
    operation = 'get_auto_scaling_group_recommendations'
    request_params, error = _build_request_params(
        operation,
        max_results,
        filters,
        account_ids,
        next_token,
        resource_arns,
        'autoScalingGroupArns',
    )
    if error:
        return error

    response, error = _call_recommendations_api(
        co_client, 'get_auto_scaling_group_recommendations', operation, request_params
    )
    if error:
        return error

    formatted_response = _new_formatted_response(response, request_params)

    for recommendation in response.get('autoScalingGroupRecommendations', []):
        current_config = {
            **_format_asg_configuration(recommendation.get('currentConfiguration', {})),
            'finding': recommendation.get('finding'),
            'current_performance_risk': recommendation.get('currentPerformanceRisk'),
            'inferred_workload_types': recommendation.get('inferredWorkloadTypes', []),
            'gpu_info': recommendation.get('currentInstanceGpuInfo'),
        }

        recommended_options = []
        for option in recommendation.get('recommendationOptions', []):
            recommended_options.append(
                {
                    **_format_asg_configuration(option.get('configuration', {})),
                    'projected_utilization_metrics': option.get('projectedUtilizationMetrics'),
                    'performance_risk': option.get('performanceRisk'),
                    'rank': option.get('rank'),
                    'migration_effort': option.get('migrationEffort'),
                    'gpu_info': option.get('instanceGpuInfo'),
                    'savings_opportunity': format_savings_opportunity(
                        option.get('savingsOpportunity', {})
                    ),
                    'savings_opportunity_after_discounts': format_savings_opportunity(
                        option.get('savingsOpportunityAfterDiscounts', {})
                    ),
                }
            )

        formatted_response['recommendations'].append(
            {
                'auto_scaling_group_arn': recommendation.get('autoScalingGroupArn'),
                'auto_scaling_group_name': recommendation.get('autoScalingGroupName'),
                'account_id': recommendation.get('accountId'),
                'current_configuration': current_config,
                'recommendation_options': recommended_options,
                'utilization_metrics': _format_metrics(recommendation.get('utilizationMetrics')),
                'lookback_period_in_days': recommendation.get('lookBackPeriodInDays'),
                'effective_recommendation_preferences': recommendation.get(
                    'effectiveRecommendationPreferences'
                ),
                'last_refresh_timestamp': format_timestamp(
                    recommendation.get('lastRefreshTimestamp')
                ),
            }
        )

    return format_response('success', formatted_response)


def _format_ebs_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Format an EBS volume configuration."""
    return {
        'volume_type': config.get('volumeType'),
        'volume_size': config.get('volumeSize'),
        'volume_baseline_iops': config.get('volumeBaselineIOPS'),
        'volume_burst_iops': config.get('volumeBurstIOPS'),
        'volume_baseline_throughput': config.get('volumeBaselineThroughput'),
        'volume_burst_throughput': config.get('volumeBurstThroughput'),
        'root_volume': config.get('rootVolume'),
    }


async def get_ebs_volume_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token, resource_arns=None
):
    """Get EBS volume recommendations."""
    operation = 'get_ebs_volume_recommendations'
    request_params, error = _build_request_params(
        operation, max_results, filters, account_ids, next_token, resource_arns, 'volumeArns'
    )
    if error:
        return error

    response, error = _call_recommendations_api(
        co_client, 'get_ebs_volume_recommendations', operation, request_params
    )
    if error:
        return error

    formatted_response = _new_formatted_response(response, request_params)

    for recommendation in response.get('volumeRecommendations', []):
        current_config = {
            **_format_ebs_configuration(recommendation.get('currentConfiguration', {})),
            'finding': recommendation.get('finding'),
            'current_performance_risk': recommendation.get('currentPerformanceRisk'),
        }

        recommended_options = []
        for option in recommendation.get('volumeRecommendationOptions', []):
            recommended_options.append(
                {
                    **_format_ebs_configuration(option.get('configuration', {})),
                    'performance_risk': option.get('performanceRisk'),
                    'rank': option.get('rank'),
                    'savings_opportunity': format_savings_opportunity(
                        option.get('savingsOpportunity', {})
                    ),
                    'savings_opportunity_after_discounts': format_savings_opportunity(
                        option.get('savingsOpportunityAfterDiscounts', {})
                    ),
                }
            )

        formatted_response['recommendations'].append(
            {
                'volume_arn': recommendation.get('volumeArn'),
                'account_id': recommendation.get('accountId'),
                'current_configuration': current_config,
                'recommendation_options': recommended_options,
                'utilization_metrics': _format_metrics(recommendation.get('utilizationMetrics')),
                'lookback_period_in_days': recommendation.get('lookBackPeriodInDays'),
                'effective_recommendation_preferences': recommendation.get(
                    'effectiveRecommendationPreferences'
                ),
                'last_refresh_timestamp': format_timestamp(
                    recommendation.get('lastRefreshTimestamp')
                ),
            }
        )

    return format_response('success', formatted_response)


async def get_lambda_function_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token, resource_arns=None
):
    """Get Lambda function recommendations."""
    operation = 'get_lambda_function_recommendations'
    request_params, error = _build_request_params(
        operation, max_results, filters, account_ids, next_token, resource_arns, 'functionArns'
    )
    if error:
        return error

    response, error = _call_recommendations_api(
        co_client, 'get_lambda_function_recommendations', operation, request_params
    )
    if error:
        return error

    # GetLambdaFunctionRecommendations has no response-level errors member.
    formatted_response = _new_formatted_response(response, request_params, include_errors=False)

    for recommendation in response.get('lambdaFunctionRecommendations', []):
        current_config = {
            'memory_size': recommendation.get('currentMemorySize'),
            'finding': recommendation.get('finding'),
            'finding_reason_codes': recommendation.get('findingReasonCodes', []),
            'current_performance_risk': recommendation.get('currentPerformanceRisk'),
        }

        recommended_options = []
        for option in recommendation.get('memorySizeRecommendationOptions', []):
            recommended_options.append(
                {
                    'memory_size': option.get('memorySize'),
                    'projected_utilization_metrics': option.get('projectedUtilizationMetrics'),
                    'rank': option.get('rank'),
                    'savings_opportunity': format_savings_opportunity(
                        option.get('savingsOpportunity', {})
                    ),
                    'savings_opportunity_after_discounts': format_savings_opportunity(
                        option.get('savingsOpportunityAfterDiscounts', {})
                    ),
                }
            )

        function_arn = recommendation.get('functionArn')
        function_name = (
            function_arn.split(':function:')[-1].split(':')[0] if function_arn else None
        )
        formatted_response['recommendations'].append(
            {
                'function_arn': function_arn,
                'function_name': function_name,
                'function_version': recommendation.get('functionVersion'),
                'account_id': recommendation.get('accountId'),
                'current_configuration': current_config,
                'recommendation_options': recommended_options,
                'number_of_invocations': recommendation.get('numberOfInvocations'),
                'utilization_metrics': _format_metrics(recommendation.get('utilizationMetrics')),
                'lookback_period_in_days': recommendation.get('lookbackPeriodInDays'),
                'effective_recommendation_preferences': recommendation.get(
                    'effectiveRecommendationPreferences'
                ),
                'last_refresh_timestamp': format_timestamp(
                    recommendation.get('lastRefreshTimestamp')
                ),
            }
        )

    return format_response('success', formatted_response)


async def get_rds_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token, resource_arns=None
):
    """Get Amazon RDS and Aurora database recommendations.

    Args:
        ctx: MCP context
        co_client: AWS Compute Optimizer client
        max_results: Maximum number of results to return
        filters: Optional filters as JSON string
        account_ids: Optional list of account IDs as JSON string
        next_token: Pagination token
        resource_arns: Optional list of RDS DB instance or cluster ARNs

    Returns:
        Dict containing RDS instance recommendations
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    operation = 'get_rds_recommendations'
    request_params, error = _build_request_params(
        operation, max_results, filters, account_ids, next_token, resource_arns, 'resourceArns'
    )
    if error:
        return error

    await ctx_logger.info(
        f'Calling get_rds_database_recommendations with parameters: {request_params}'
    )
    response, error = _call_recommendations_api(
        co_client, 'get_rds_database_recommendations', operation, request_params
    )
    if error:
        return error

    formatted_response = _new_formatted_response(response, request_params)

    for recommendation in response.get('rdsDBRecommendations', []):
        resource_arn = recommendation.get('resourceArn')

        current_config = {
            'instance_class': recommendation.get('currentDBInstanceClass'),
            'instance_finding': recommendation.get('instanceFinding'),
            'instance_finding_reason_codes': recommendation.get('instanceFindingReasonCodes', []),
            'current_instance_performance_risk': recommendation.get(
                'currentInstancePerformanceRisk'
            ),
            'idle': recommendation.get('idle'),
            'engine': recommendation.get('engine'),
            'engine_version': recommendation.get('engineVersion'),
            'db_cluster_identifier': recommendation.get('dbClusterIdentifier'),
            'promotion_tier': recommendation.get('promotionTier'),
            'storage_finding': recommendation.get('storageFinding'),
            'storage_finding_reason_codes': recommendation.get('storageFindingReasonCodes', []),
            'current_storage_configuration': recommendation.get('currentStorageConfiguration'),
            'current_storage_estimated_monthly_volume_iops_cost_variation': recommendation.get(
                'currentStorageEstimatedMonthlyVolumeIOPsCostVariation'
            ),
        }

        recommended_options = []
        for option in recommendation.get('instanceRecommendationOptions', []):
            recommended_options.append(
                {
                    'instance_class': option.get('dbInstanceClass'),
                    'projected_utilization_metrics': option.get('projectedUtilizationMetrics'),
                    'performance_risk': option.get('performanceRisk'),
                    'rank': option.get('rank'),
                    'savings_opportunity': format_savings_opportunity(
                        option.get('savingsOpportunity', {})
                    ),
                    'savings_opportunity_after_discounts': format_savings_opportunity(
                        option.get('savingsOpportunityAfterDiscounts', {})
                    ),
                }
            )

        storage_options = []
        for option in recommendation.get('storageRecommendationOptions', []):
            storage_options.append(
                {
                    'storage_configuration': option.get('storageConfiguration'),
                    'estimated_monthly_volume_iops_cost_variation': option.get(
                        'estimatedMonthlyVolumeIOPsCostVariation'
                    ),
                    'rank': option.get('rank'),
                    'savings_opportunity': format_savings_opportunity(
                        option.get('savingsOpportunity', {})
                    ),
                    'savings_opportunity_after_discounts': format_savings_opportunity(
                        option.get('savingsOpportunityAfterDiscounts', {})
                    ),
                }
            )

        formatted_response['recommendations'].append(
            {
                'instance_arn': resource_arn,
                'instance_name': resource_arn.split(':')[-1] if resource_arn else None,
                'account_id': recommendation.get('accountId'),
                'current_configuration': current_config,
                'recommendation_options': recommended_options,
                'storage_recommendation_options': storage_options,
                'utilization_metrics': recommendation.get('utilizationMetrics'),
                'lookback_period_in_days': recommendation.get('lookbackPeriodInDays'),
                'effective_recommendation_preferences': recommendation.get(
                    'effectiveRecommendationPreferences'
                ),
                'savings_estimation_mode': recommendation.get(
                    'effectiveRecommendationPreferences', {}
                ).get('savingsEstimationMode'),
                'last_refresh_timestamp': format_timestamp(
                    recommendation.get('lastRefreshTimestamp')
                ),
            }
        )

    return {'status': 'success', 'data': formatted_response}


async def get_ecs_service_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token, resource_arns=None
):
    """Get ECS service recommendations."""
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    operation = 'get_ecs_service_recommendations'
    request_params, error = _build_request_params(
        operation, max_results, filters, account_ids, next_token, resource_arns, 'serviceArns'
    )
    if error:
        return error

    await ctx_logger.info(
        f'Calling get_ecs_service_recommendations with parameters: {request_params}'
    )
    response, error = _call_recommendations_api(
        co_client, 'get_ecs_service_recommendations', operation, request_params
    )
    if error:
        return error

    formatted_response = _new_formatted_response(response, request_params)

    for recommendation in response.get('ecsServiceRecommendations', []):
        current_service_config = recommendation.get('currentServiceConfiguration', {})
        current_config = {
            'memory': current_service_config.get('memory'),
            'cpu': current_service_config.get('cpu'),
            'container_configurations': current_service_config.get('containerConfigurations', []),
            'auto_scaling_configuration': current_service_config.get('autoScalingConfiguration'),
            'task_definition_arn': current_service_config.get('taskDefinitionArn'),
            'finding': recommendation.get('finding'),
            'finding_reason_codes': recommendation.get('findingReasonCodes', []),
            'current_performance_risk': recommendation.get('currentPerformanceRisk'),
        }

        recommended_options = []
        for option in recommendation.get('serviceRecommendationOptions', []):
            recommended_options.append(
                {
                    'memory': option.get('memory'),
                    'cpu': option.get('cpu'),
                    'container_recommendations': option.get('containerRecommendations', []),
                    'projected_utilization_metrics': option.get('projectedUtilizationMetrics'),
                    'savings_opportunity': format_savings_opportunity(
                        option.get('savingsOpportunity', {})
                    ),
                    'savings_opportunity_after_discounts': format_savings_opportunity(
                        option.get('savingsOpportunityAfterDiscounts', {})
                    ),
                }
            )

        formatted_response['recommendations'].append(
            {
                'service_arn': recommendation.get('serviceArn'),
                'account_id': recommendation.get('accountId'),
                'current_service_configuration': current_config,
                'utilization_metrics': _format_metrics(recommendation.get('utilizationMetrics')),
                'lookback_period_in_days': recommendation.get('lookbackPeriodInDays'),
                'effective_recommendation_preferences': recommendation.get(
                    'effectiveRecommendationPreferences'
                ),
                'launch_type': recommendation.get('launchType'),
                'recommendation_options': recommended_options,
                'last_refresh_timestamp': format_timestamp(
                    recommendation.get('lastRefreshTimestamp')
                ),
                # Returned before the tag removal elsewhere; kept for compatibility.
                'tags': recommendation.get('tags', []),
            }
        )

    return format_response('success', formatted_response)


# Idle filter name -> botocore enum shape that holds its valid values.
_IDLE_FILTER_ENUM_SHAPES = {
    'ResourceType': 'IdleRecommendationResourceType',
    'Finding': 'IdleFinding',
}


@lru_cache(maxsize=None)
def _idle_enum_canonical_map(shape_name: str) -> Dict[str, str]:
    """Build a casefolded -> canonical map of a Compute Optimizer enum from the boto model.

    Used to normalize filter values onto the exact spelling the API expects (e.g.
    `EbsVolume` -> `EBSVolume`, `idle` -> `Idle`); every valid value is recoverable by
    case-folding alone. The enum is read from the installed botocore service model rather
    than hardcoded, so new values are supported automatically whenever boto3 is
    upgraded. The model is loaded offline (no AWS call).

    Returns:
        Mapping of casefolded value to canonical value. Returns an empty map if the
        service model or shape cannot be loaded (normalization is then skipped).
    """
    try:
        service_model: Any = botocore.session.get_session().get_service_model('compute-optimizer')
        enum_values = service_model.shape_for(shape_name).enum
    except Exception:
        # Older boto3 without this shape, or model load failure: skip normalization.
        return {}
    return {value.casefold(): value for value in enum_values or []}


def _normalize_idle_filters(filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fold idle `ResourceType` and `Finding` filters onto the canonical idle enum spelling."""
    normalized, _ = _normalize_filters('get_idle_recommendations', filters)
    return normalized


async def get_idle_recommendations(
    ctx,
    co_client,
    max_results,
    filters,
    account_ids,
    next_token,
    resource_arns=None,
    order_by=None,
):
    """Get idle resource recommendations.

    Idle recommendations cover multiple resource types, and the `finding` field uses
    the IdleFinding enum. For the authoritative list of supported resource types and
    finding values, see the IdleRecommendation API reference:
    https://docs.aws.amazon.com/compute-optimizer/latest/APIReference/API_IdleRecommendation.html
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    operation = 'get_idle_recommendations'
    request_params, error = _build_request_params(
        operation, max_results, filters, account_ids, next_token, resource_arns, 'resourceArns'
    )
    if error:
        return error
    # Sent on every page, including next_token follow-ups, so pagination stays consistent.
    request_params['orderBy'], error = _resolve_idle_order_by(order_by)
    if error:
        return error

    await ctx_logger.info(f'Calling get_idle_recommendations with parameters: {request_params}')
    response, error = _call_recommendations_api(
        co_client, 'get_idle_recommendations', operation, request_params
    )
    if error:
        return error

    formatted_response = _new_formatted_response(response, request_params)

    for recommendation in response.get('idleRecommendations', []):
        utilization_metrics = []
        for metric in recommendation.get('utilizationMetrics', []):
            utilization_metrics.append(
                {
                    'name': metric.get('name'),
                    'statistic': metric.get('statistic'),
                    'value': metric.get('value'),
                    'dimensions': metric.get('dimensions', []),
                }
            )

        formatted_response['recommendations'].append(
            {
                'resource_arn': recommendation.get('resourceArn'),
                'resource_id': recommendation.get('resourceId'),
                'resource_type': recommendation.get('resourceType'),
                'account_id': recommendation.get('accountId'),
                'finding': recommendation.get('finding'),
                'finding_description': recommendation.get('findingDescription'),
                'savings_opportunity': format_savings_opportunity(
                    recommendation.get('savingsOpportunity', {})
                ),
                'savings_opportunity_after_discounts': format_savings_opportunity(
                    recommendation.get('savingsOpportunityAfterDiscounts', {})
                ),
                'utilization_metrics': utilization_metrics,
                'lookback_period_in_days': recommendation.get('lookBackPeriodInDays'),
                'last_refresh_timestamp': format_timestamp(
                    recommendation.get('lastRefreshTimestamp')
                ),
                # Returned before the tag removal elsewhere; kept for compatibility.
                'tags': recommendation.get('tags', []),
            }
        )

    return format_response('success', formatted_response)


def format_savings_opportunity(savings_opportunity):
    """Format the savings opportunity for better readability."""
    if not savings_opportunity:
        return None

    return {
        'savings_percentage': savings_opportunity.get('savingsOpportunityPercentage'),
        'estimated_monthly_savings': {
            'currency': savings_opportunity.get('estimatedMonthlySavings', {}).get('currency'),
            'value': savings_opportunity.get('estimatedMonthlySavings', {}).get('value'),
        },
    }


def format_timestamp(timestamp):
    """Format a timestamp to an ISO 8601 UTC string."""
    if timestamp is None:
        return None

    return timestamp_to_utc_iso_string(timestamp)
