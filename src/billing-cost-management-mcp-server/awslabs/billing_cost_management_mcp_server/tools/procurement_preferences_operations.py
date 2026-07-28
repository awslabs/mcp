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

"""AWS Procurement Portal Preference operations for the BCM MCP server.

This module contains the read-only operation handlers for the
``procurement-preferences`` tool (AWS Procurement Portal Preferences: SAP
Business Network / Coupa connections and e-invoice delivery settings). Each
operation performs the AWS API call, normalizes ``datetime`` timestamps to
ISO 8601 strings for the agent, and returns a standardized response envelope.

Note: procurement portal preference records may include portal connection
details. Ensure IAM read-only policies are scoped appropriately.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from ..utilities.time_utils import normalize_datetimes_to_iso
from fastmcp import Context
from typing import Any, Dict, Optional


# ``ProcurementPortalSharedSecret`` is a shared secret / authentication
# credential for the procurement portal. The tool must not expose it to the
# LLM, so it is dropped from the response after the SDK call returns, before the
# response is returned to the agent. The field is still returned by the AWS API
# and remains accessible via a direct SDK call; we simply do not propagate it out
# of this tool. Other preference attributes are intentionally retained.
_SENSITIVE_FIELD_NAMES = frozenset({'ProcurementPortalSharedSecret'})


def drop_sensitive_fields(value: Any) -> Any:
    """Recursively drop known secret fields from an AWS response structure.

    Walks nested dicts and lists and removes any key named in
    ``_SENSITIVE_FIELD_NAMES``. Recursion makes the redaction robust against the
    secret appearing at any depth (for example nested under
    ``TestEnvPreference``) and against every item in a list, not just the first.

    Args:
        value: An arbitrary JSON-like structure (dict, list, or scalar).

    Returns:
        The same structure with sensitive keys removed. Dicts and lists are
        mutated in place and also returned for convenience.
    """
    if isinstance(value, dict):
        for key in [k for k in value if k in _SENSITIVE_FIELD_NAMES]:
            del value[key]
        for inner in value.values():
            drop_sensitive_fields(inner)
    elif isinstance(value, list):
        for item in value:
            drop_sensitive_fields(item)
    return value


def _create_invoicing_client() -> Any:
    """Create an AWS Invoicing client.

    The Region is intentionally not hard-coded. ``create_aws_client`` resolves
    it from the ``AWS_REGION`` environment variable and falls back to
    ``us-east-1`` (the home Region of the global Invoicing service).

    Returns:
        boto3.client: AWS Invoicing client.
    """
    return create_aws_client('invoicing')


async def list_procurement_portal_preferences(
    ctx: Context,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """List procurement portal preference configurations for the caller.

    Retrieves the procurement portal connections and e-invoice delivery
    settings (for example SAP Business Network or Coupa) configured for the
    account.

    Args:
        ctx: The MCP context object.
        max_results: Maximum number of results per page (1-100).
        next_token: Pagination token from a previous response to resume from.
        max_pages: Maximum number of pages to auto-paginate through. Defaults to
            all pages.

    Returns:
        Dict containing ``procurement_portal_preferences`` (with ISO 8601
        timestamps) and a ``pagination`` metadata block, or a standardized error
        response.
    """
    try:
        request_params: Dict[str, Any] = {}
        if max_results is not None:
            request_params['MaxResults'] = max_results
        if next_token:
            request_params['NextToken'] = next_token

        client = _create_invoicing_client()

        preferences, pagination = await paginate_aws_response(
            ctx,
            'ListProcurementPortalPreferences',
            client.list_procurement_portal_preferences,
            request_params,
            'ProcurementPortalPreferences',
            token_param='NextToken',
            token_key='NextToken',
            max_pages=max_pages,
        )

        normalized = normalize_datetimes_to_iso(preferences)
        # Drop procurement portal secrets before returning so they never reach
        # the agent/LLM context (see drop_sensitive_fields / _SENSITIVE_FIELD_NAMES).
        drop_sensitive_fields(normalized)

        await ctx.info(f'Successfully listed {len(normalized)} procurement portal preferences')

        return format_response(
            'success',
            {'procurement_portal_preferences': normalized, 'pagination': pagination},
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListProcurementPortalPreferences', 'Invoicing')


async def get_procurement_portal_preference(
    ctx: Context,
    procurement_portal_preference_arn: str,
) -> Dict[str, Any]:
    """Retrieve a single procurement portal preference configuration.

    Args:
        ctx: The MCP context object.
        procurement_portal_preference_arn: The ARN of the procurement portal
            preference to retrieve (required).

    Returns:
        Dict containing the ``procurement_portal_preference`` (with ISO 8601
        timestamps), or a standardized error response.
    """
    try:
        if not procurement_portal_preference_arn:
            return format_response(
                'error',
                {
                    'message': (
                        'procurement_portal_preference_arn is required for '
                        'get_procurement_portal_preference.'
                    )
                },
            )

        client = _create_invoicing_client()
        response = client.get_procurement_portal_preference(
            ProcurementPortalPreferenceArn=procurement_portal_preference_arn
        )
        response.pop('ResponseMetadata', None)

        await ctx.info(
            f'Successfully retrieved procurement portal preference: '
            f'{procurement_portal_preference_arn}'
        )

        # Drop procurement portal secrets before returning so they never reach
        # the agent/LLM context (see drop_sensitive_fields / _SENSITIVE_FIELD_NAMES).
        preference = drop_sensitive_fields(
            normalize_datetimes_to_iso(response.get('ProcurementPortalPreference', {}))
        )

        return format_response(
            'success',
            {'procurement_portal_preference': preference},
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'GetProcurementPortalPreference', 'Invoicing')
