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
import fastmcp
import importlib
import pkgutil
import pytest
import re
from awslabs.billing_cost_management_mcp_server import tools as tools_package


# An operation name, as distinct from an ordinary word that happens to follow a
# tool name in prose ("the get-billing-view tools", "credits belong to"). Every
# operation in this server is snake_case or camelCase; no operation is a single
# all-lowercase word, and no English word carries an underscore or an internal
# capital.
_OPERATION_SHAPE = re.compile(r'^(?=.*(?:_|[a-z][A-Z]))[a-z][A-Za-z_]*$')


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


def _declared_operations(tool):
    """The operation names a tool's own schema names, if it enumerates them."""
    operation = (tool.inputSchema.get('properties', {}) or {}).get('operation') or {}
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
