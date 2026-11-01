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

"""Class guards over every mounted tool description.

A tool description is the only thing that tells a model what an operation's
result covers, so an ambiguity in one is a defect in the result the model
produces from it. These two rules generalize a defect found in `sp-explorer`,
whose `describe_savings_plans` entry said "the plans the account owns" without
naming which account: the API is scoped to the calling account, so from a
management account the operation returns an empty list, and a caller reading
that as "owns none" recommends a commitment over usage existing plans already
cover.

Tools are discovered by walking the `tools` package for FastMCP servers, so a
tool added later is covered without being registered here.
"""

import asyncio
import botocore.session
import fastmcp
import importlib
import pkgutil
import pytest
import re
from awslabs.billing_cost_management_mcp_server import tools as tools_package
from typing import Dict, NamedTuple, Tuple


# An operation name, as distinct from an ordinary word that happens to follow a
# tool name in prose ("the get-billing-view tools", "credits belong to"). Every
# operation in this server is snake_case or camelCase; no operation is a single
# all-lowercase word, and no English word carries an underscore or an internal
# capital.
_OPERATION_SHAPE = re.compile(r'^(?=.*(?:_|[a-z][A-Z]))[a-z][A-Za-z_]*$')


class _ApiSurface(NamedTuple):
    """How one tool's schema and description line up with the API it wraps.

    ``filter_params`` maps each member of the API's filter shape to the tool
    parameters that together supply it, so a member reachable through more than
    one parameter (a time interval built from two dates) still counts as
    exposed. An empty tuple records a member deliberately left out, and
    ``unexposed_reasons`` must then say why.
    """

    service: str
    filter_shape: str
    response_shapes: Tuple[str, ...]
    filter_params: Dict[str, Tuple[str, ...]]
    unexposed_reasons: Dict[str, str] = {}
    undocumented_ok: Tuple[str, ...] = ()


# Tools whose API surface is pinned against botocore. A tool absent from this
# table is not checked, so adding a row is how a tool joins the guard; the two
# rules below then hold for it without further wiring.
_API_SURFACES = {
    'invoicing': _ApiSurface(
        service='invoicing',
        filter_shape='InvoiceSummariesFilter',
        response_shapes=('InvoiceSummary', 'Entity'),
        filter_params={
            'TimeInterval': ('start_date', 'end_date'),
            'BillingPeriod': ('billing_period',),
            'InvoicingEntity': ('invoicing_entity',),
            'ReceiverRole': ('receiver_role',),
        },
    ),
    'invoice-units': _ApiSurface(
        service='invoicing',
        filter_shape='Filters',
        response_shapes=('InvoiceUnit', 'InvoiceUnitRule'),
        filter_params={
            'Names': ('names',),
            'InvoiceReceivers': ('invoice_receivers',),
            'Accounts': ('accounts',),
            'BillSourceAccounts': ('bill_source_accounts',),
        },
    ),
}


def _documented(name, description):
    """Whether a field or enum name appears in its own right.

    A plain substring test passes on a name contained in another documented
    one -- `InvoiceId` inside `OriginalInvoiceId` -- which would hide exactly
    the omission these guards exist to catch.
    """
    return re.search(rf'\b{re.escape(name)}\b', description) is not None


def _shape(surface, name):
    """A shape from the live botocore model for a surface's service."""
    return botocore.session.get_session().get_service_model(surface.service).shape_for(name)


async def _collect_tools():
    """Every tool published by every FastMCP server under the tools package."""
    collected = {}
    for module_info in pkgutil.iter_modules(tools_package.__path__):
        try:
            module = importlib.import_module(f'{tools_package.__name__}.{module_info.name}')
        except Exception:
            # A tool module whose optional client package is absent does not
            # register a server; the installs that lack it do not serve it either.
            continue
        for value in vars(module).values():
            if isinstance(value, fastmcp.FastMCP):
                async with fastmcp.Client(value) as client:
                    for tool in await client.list_tools():
                        collected[tool.name] = tool
    return collected


@pytest.fixture(scope='module')
def mounted_tools():
    """Tools as published to MCP clients, keyed by name."""
    return asyncio.run(_collect_tools())


def _input_schema(tool):
    """The served input schema, under whichever field name this FastMCP uses.

    MCP SDK v2 renamed ``inputSchema`` to ``input_schema``, and this package is
    built against both.
    """
    schema = getattr(tool, 'input_schema', None)
    return tool.inputSchema if schema is None else schema


def _declared_operations(tool):
    """The operation names a tool's own schema names, if it enumerates them."""
    operation = (_input_schema(tool).get('properties', {}) or {}).get('operation') or {}
    return set(re.findall(r"'([a-zA-Z][A-Za-z_]*)'", operation.get('description') or ''))


def test_tools_are_discovered(mounted_tools):
    """Guard the guards: a discovery that finds nothing would pass both rules."""
    assert len(mounted_tools) > 40


def test_no_description_says_the_account_owns_without_naming_which(mounted_tools):
    """A description claiming "the account owns" must name which account.

    Every one of these APIs is scoped to the calling account unless it documents
    otherwise, and the difference decides whether an empty result means "owns
    none" or "bought none here".
    """
    offenders = sorted(
        name
        for name, tool in mounted_tools.items()
        if re.search(r'\bthe account owns\b', tool.description or '', re.I)
    )

    assert offenders == [], (
        'These descriptions say "the account owns" without naming the account. '
        'Say whose plans, resources or charges the operation returns — for an '
        f'account-scoped API, "the calling account only": {offenders}'
    )


def test_every_tool_operation_cross_reference_resolves(mounted_tools):
    """A description that points at `<tool> <operation>` must name a real one.

    A description is the only place these pointers exist, so a renamed operation
    leaves a dangling instruction that a model will follow anyway.
    """
    names = '|'.join(sorted(map(re.escape, mounted_tools), key=len, reverse=True))
    reference = re.compile(rf'\b({names})\s+`?([a-z][A-Za-z_]*)`?')

    unresolved = []
    for name, tool in mounted_tools.items():
        for referenced_tool, operation in reference.findall(tool.description or ''):
            if not _OPERATION_SHAPE.match(operation):
                continue
            target = mounted_tools[referenced_tool]
            # Not every tool enumerates its operations in the schema, so fall
            # back to its description: a renamed operation leaves both.
            if operation in _declared_operations(target):
                continue
            if operation in (target.description or ''):
                continue
            unresolved.append(f'{name} -> {referenced_tool} {operation}')

    assert unresolved == [], (
        f'These descriptions point at an operation the named tool does not have: {unresolved}'
    )


@pytest.mark.parametrize('tool_name', sorted(_API_SURFACES))
def test_tool_schema_exposes_every_api_filter_member(mounted_tools, tool_name):
    """A filter member the API accepts must be reachable, or deliberately not.

    This is the class behind `ReceiverRole`: the member was never exposed, so
    the tool enforced a one-month cap the API only applies without it, and
    estimated invoices were unreachable. Dropping a filter member on onboarding
    is invisible — nothing fails, the data is simply never returned.
    """
    surface = _API_SURFACES[tool_name]
    served = set(_input_schema(mounted_tools[tool_name]).get('properties', {}))

    problems = []
    for member in _shape(surface, surface.filter_shape).members:
        if member not in surface.filter_params:
            problems.append(f'{member}: not in filter_params; expose it or record a reason')
            continue
        params = surface.filter_params[member]
        if not params:
            if member not in surface.unexposed_reasons:
                problems.append(f'{member}: left unexposed with no reason given')
            continue
        missing = [param for param in params if param not in served]
        if missing:
            problems.append(f'{member}: maps to parameters the schema lacks: {missing}')

    assert problems == [], f'{tool_name} filter surface: {problems}'


@pytest.mark.parametrize('tool_name', sorted(_API_SURFACES))
def test_description_names_every_response_member(mounted_tools, tool_name):
    """Every field a result can carry, and every enum value, must be named.

    A tool passes unlisted fields through unchanged, so an omission does not
    lose data — it loses the reader's knowledge that the data is there, and the
    reader deflects a question the result already answers.
    """
    surface = _API_SURFACES[tool_name]
    description = mounted_tools[tool_name].description or ''

    missing = []
    for shape_name in surface.response_shapes:
        shape = _shape(surface, shape_name)
        for member, member_shape in shape.members.items():
            if not _documented(member, description) and member not in surface.undocumented_ok:
                missing.append(f'{shape_name}.{member}')
            for value in getattr(member_shape, 'enum', None) or ():
                if not _documented(value, description):
                    missing.append(f'{shape_name}.{member} = {value}')

    assert missing == [], f'{tool_name} description does not name: {missing}'
