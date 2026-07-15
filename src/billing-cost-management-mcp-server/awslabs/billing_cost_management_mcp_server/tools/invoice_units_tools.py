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

"""AWS Invoice Unit tools for the AWS Billing and Cost Management MCP server.

Exposes a single read-only ``invoice-units`` tool that routes by ``operation``
across the AWS Invoice Configuration read APIs (mirroring the ``invoicing``
tool). The rich tool description is the primary vehicle that gives the agent
semantic context about every request parameter and response field.
"""

from ..utilities.aws_service_base import format_response
from .invoice_units_operations import (
    batch_get_invoice_profile as _batch_get_invoice_profile,
)
from .invoice_units_operations import (
    get_invoice_unit as _get_invoice_unit,
)
from .invoice_units_operations import (
    list_invoice_units as _list_invoice_units,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


invoice_units_server = FastMCP(
    name='invoice-units-tools',
    instructions='Read-only tools for working with AWS Invoice Configuration (invoice units)',
)


async def _invoice_units(
    ctx: Context,
    operation: str,
    invoice_unit_arn: Optional[str] = None,
    names: Optional[List[str]] = None,
    invoice_receivers: Optional[List[str]] = None,
    accounts: Optional[List[str]] = None,
    bill_source_accounts: Optional[List[str]] = None,
    account_ids: Optional[List[str]] = None,
    as_of: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Route an AWS Invoice Unit ``operation`` to its handler.

    Kept separate from the FastMCP-decorated wrapper so the routing can be unit
    tested directly (decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The invoice unit operation (``"list_invoice_units"``,
            ``"get_invoice_unit"``, or ``"batch_get_invoice_profile"``).
        invoice_unit_arn: ARN of a single invoice unit (get_invoice_unit).
        names: Filter invoice units by name (list_invoice_units).
        invoice_receivers: Filter by receiver account ID (list_invoice_units).
        accounts: Filter by member account ID (list_invoice_units).
        bill_source_accounts: Filter by bill source account ID
            (list_invoice_units).
        account_ids: Account IDs to fetch profiles for
            (batch_get_invoice_profile).
        as_of: Point-in-time UTC instant for list/get operations.
        max_results: Maximum results per page (1-100).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        The operation's response, or a standardized error for an unknown
        operation.
    """
    await ctx.info(f'Invoice unit operation: {operation}')

    if operation == 'list_invoice_units':
        return await _list_invoice_units(
            ctx,
            names=names,
            invoice_receivers=invoice_receivers,
            accounts=accounts,
            bill_source_accounts=bill_source_accounts,
            as_of=as_of,
            max_results=max_results,
            next_token=next_token,
            max_pages=max_pages,
        )

    if operation == 'get_invoice_unit':
        if invoice_unit_arn is None:
            return format_response(
                'error',
                {'message': 'invoice_unit_arn is required for get_invoice_unit.'},
            )
        return await _get_invoice_unit(ctx, invoice_unit_arn=invoice_unit_arn, as_of=as_of)

    if operation == 'batch_get_invoice_profile':
        if account_ids is None:
            return format_response(
                'error',
                {'message': 'account_ids is required for batch_get_invoice_profile.'},
            )
        return await _batch_get_invoice_profile(ctx, account_ids=account_ids)

    return format_response(
        'error',
        {
            'message': (
                f"Unsupported operation: '{operation}'. Supported operations: "
                'list_invoice_units, get_invoice_unit, batch_get_invoice_profile.'
            )
        },
    )


@invoice_units_server.tool(
    name='invoice-units',
    description="""Access AWS Invoice Configuration (invoice units) — read-only. Invoice units are groups of AWS accounts that represent business entities and receive a separate invoice, each with a designated receiver account. Choose an action with the required `operation` parameter; the remaining parameters apply to specific operations.

## OPERATIONS

1) list_invoice_units - list invoice unit definitions visible to the management account
   Required: operation="list_invoice_units"
   Optional filters (AND across types; OR within a list):
     - names: match invoice unit names
     - invoice_receivers: match receiver account IDs (12-digit)
     - accounts: match member account IDs
     - bill_source_accounts: match bill source account IDs
     - as_of: point-in-time UTC "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS" (definitions as of that instant; defaults to current)
   Pagination: max_results caps items per page (1-100); max_pages caps pages fetched (default: all). The `pagination` block reports total_results, pages_fetched, has_more, and next_token.
   Returns: `data.invoice_units`, each with InvoiceUnitArn, Name, Description, InvoiceReceiver, TaxInheritanceDisabled, Rule {LinkedAccounts}, and LastModified (ISO 8601 UTC).

2) get_invoice_unit - retrieve one invoice unit definition
   Required: operation="get_invoice_unit", invoice_unit_arn
   Optional: as_of (point-in-time UTC, as above)
   Returns: `data.invoice_unit` with the fields above.

3) batch_get_invoice_profile - fetch invoice receiver profiles for accounts
   Required: operation="batch_get_invoice_profile", account_ids (12-digit account IDs, linked under the management account)
   Returns: `data.profiles`, each with AccountId, ReceiverName, ReceiverAddress, ReceiverEmail, Issuer, TaxRegistrationNumber.

EXAMPLES
- {"operation": "list_invoice_units"}
- {"operation": "list_invoice_units", "invoice_receivers": ["123456789012"]}
- {"operation": "get_invoice_unit", "invoice_unit_arn": "arn:aws:invoicing::123456789012:invoice-unit/abc123"}
- {"operation": "batch_get_invoice_profile", "account_ids": ["123456789012", "210987654321"]}""",
)
async def invoice_units(
    ctx: Context,
    operation: str,
    invoice_unit_arn: Optional[str] = None,
    names: Optional[List[str]] = None,
    invoice_receivers: Optional[List[str]] = None,
    accounts: Optional[List[str]] = None,
    bill_source_accounts: Optional[List[str]] = None,
    account_ids: Optional[List[str]] = None,
    as_of: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """FastMCP wrapper for AWS Invoice Unit operations.

    Thin wrapper so the routing logic in ``_invoice_units`` can be unit tested
    directly (FastMCP-decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The invoice unit operation to perform.
        invoice_unit_arn: ARN of a single invoice unit (get_invoice_unit).
        names: Filter invoice units by name (list_invoice_units).
        invoice_receivers: Filter by receiver account ID (list_invoice_units).
        accounts: Filter by member account ID (list_invoice_units).
        bill_source_accounts: Filter by bill source account ID
            (list_invoice_units).
        account_ids: Account IDs to fetch profiles for
            (batch_get_invoice_profile).
        as_of: Point-in-time UTC instant for list/get operations.
        max_results: Maximum results per page (1-100).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        Dict containing the operation result.
    """
    return await _invoice_units(
        ctx,
        operation,
        invoice_unit_arn=invoice_unit_arn,
        names=names,
        invoice_receivers=invoice_receivers,
        accounts=accounts,
        bill_source_accounts=bill_source_accounts,
        account_ids=account_ids,
        as_of=as_of,
        max_results=max_results,
        next_token=next_token,
        max_pages=max_pages,
    )
