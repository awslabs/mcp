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

"""Credential-parameter preservation tests for the registered MCP tool surface.

Routing every tool's ``boto3.Session`` construction through the
``CredentialResolver`` seam in ``utils/aws_utils.py`` touches the credential path
of every AWS-calling tool at once. The regression that refactor could plausibly
introduce is a change to how callers select an identity: dropping the
``aws_profile``/``aws_region`` parameters from a tool, making one required, or
changing a default.

These tests pin exactly that invariant rather than snapshotting the whole tool
surface. A frozen full-surface snapshot fails on any unrelated tool change made
anywhere in the server (for example adding a new filter parameter to a single
tool), which makes it a shared-fate assertion that reports drift having nothing to
do with the credential seam. Asserting the credential contract directly keeps the
guard that matters and stays stable as tools gain unrelated parameters.

Validates: Requirements Behavior preservation in single-tenant mode (identical
credential-selection parameters, types, and defaults after the resolver seam).
"""

from awslabs.aws_healthomics_mcp_server.server import mcp


# Both credential-override parameters must be optional strings defaulting to None
# on every AWS-calling tool, so identity selection is uniform across the surface.
_CREDENTIAL_PARAMS = ('aws_profile', 'aws_region')

# Tools that legitimately expose no credential parameters because they never
# construct a boto3 session: they return static data or operate purely on local
# files. A tool joining this set is a signal that the credential parameters were
# dropped, so the set is asserted exactly.
_TOOLS_WITHOUT_CREDENTIAL_PARAMS = frozenset(
    {
        'GetAHOSupportedRegions',
        'GetSupportedFileTypes',
        'LintAHOWorkflowBundle',
        'LintAHOWorkflowDefinition',
        'PackageAHOWorkflow',
    }
)


def _assert_credential_param(tool_name: str, param_name: str, schema: dict) -> None:
    """Assert one credential parameter is an optional string defaulting to None."""
    assert 'default' in schema, (
        f"Tool '{tool_name}' parameter '{param_name}' declares no default; it must "
        'default to None so callers can omit it.'
    )
    assert schema['default'] is None, (
        f"Tool '{tool_name}' parameter '{param_name}' defaults to "
        f'{schema["default"]!r}, expected None.'
    )

    # Compare the optional-string union order-independently: Pydantic's branch
    # order is an implementation detail, the nullable-string contract is not.
    assert 'anyOf' in schema, (
        f"Tool '{tool_name}' parameter '{param_name}' is not an optional string "
        f'(no anyOf); got {schema!r}.'
    )
    actual_types = sorted(
        sub['type'] for sub in schema['anyOf'] if isinstance(sub, dict) and 'type' in sub
    )
    assert actual_types == ['null', 'string'], (
        f"Tool '{tool_name}' parameter '{param_name}' must be an optional string; "
        f'got type branches {actual_types}.'
    )


async def test_aws_calling_tools_expose_credential_parameters():
    """Every AWS-calling tool exposes aws_profile and aws_region, optional and None.

    Guards against the credential-resolver seam dropping a tool's identity
    selection parameters or altering their type or default.

    Validates: Requirements Behavior preservation in single-tenant mode.
    """
    tools = await mcp.list_tools()
    assert tools, 'No tools were registered; the server surface is empty.'

    for tool in sorted(tools, key=lambda t: t.name):
        if tool.name in _TOOLS_WITHOUT_CREDENTIAL_PARAMS:
            continue

        properties = (tool.input_schema or {}).get('properties', {})
        for param_name in _CREDENTIAL_PARAMS:
            assert param_name in properties, (
                f"Tool '{tool.name}' is missing the '{param_name}' parameter. Every "
                'AWS-calling tool must accept both credential overrides.'
            )
            _assert_credential_param(tool.name, param_name, properties[param_name])


async def test_credential_parameters_are_never_required():
    """The credential overrides are always optional.

    Making either parameter required would break every existing caller that omits
    it and relies on the default credential chain.

    Validates: Requirements Behavior preservation in single-tenant mode.
    """
    tools = await mcp.list_tools()

    for tool in sorted(tools, key=lambda t: t.name):
        required = set((tool.input_schema or {}).get('required', []))
        offending = sorted(required.intersection(_CREDENTIAL_PARAMS))
        assert not offending, (
            f"Tool '{tool.name}' marks {offending} as required; the credential "
            'overrides must always be optional.'
        )


async def test_tools_without_credential_parameters_are_exactly_the_local_tools():
    """Only the known static/local tools may omit the credential parameters.

    Asserted as an exact set so a tool silently losing its credential parameters
    surfaces here instead of being skipped by the exemption above. A newly added
    tool that genuinely makes no AWS calls should be added to
    ``_TOOLS_WITHOUT_CREDENTIAL_PARAMS`` deliberately.

    Validates: Requirements Behavior preservation in single-tenant mode.
    """
    tools = await mcp.list_tools()

    actual = {
        tool.name
        for tool in tools
        if not set(_CREDENTIAL_PARAMS).issubset((tool.input_schema or {}).get('properties', {}))
    }

    assert actual == set(_TOOLS_WITHOUT_CREDENTIAL_PARAMS), (
        'The set of tools without credential parameters changed.\n'
        f'Unexpectedly missing them: {sorted(actual - set(_TOOLS_WITHOUT_CREDENTIAL_PARAMS))}\n'
        f'Now have them: {sorted(set(_TOOLS_WITHOUT_CREDENTIAL_PARAMS) - actual)}'
    )
