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

"""Static checks that tool error paths can be classified by the error contract.

ErrorSignalingMiddleware derives retry_strategy from the top-level error_type
(utilities/error_contract.py), so an error whose type is unmapped, nested in data, or
hidden by a wrapping exception silently gets do_not_retry. These checks scan the
package source so such paths fail here rather than in production.
"""

import ast
import pathlib
import pytest
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
    _ERROR_TYPE_GUIDANCE,
    _ERROR_TYPE_PREFIX_GUIDANCE,
)
from typing import Iterator, List, Tuple


PACKAGE_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / 'awslabs'
    / 'billing_cost_management_mcp_server'
)

# error_type literals deliberately left unmapped, so they get the do_not_retry default
UNMAPPED_BY_DESIGN = {
    # bcm-pricing-calc: the account has no pricing preferences; the user must set them
    'PREFERENCES_NOT_CONFIGURED': 'account state, cannot be fixed during the run',
    # Fallback when an upstream error carries no error_type
    'unknown_error': 'unclassified',
    # cost-explorer: the boto3 client could not be created (credentials, region)
    'client_creation_error': 'local configuration, cannot be fixed during the run',
    # compute-optimizer-automation: retry_strategy is combined from the per-region
    # errors at the call site (combine_guidance)
    'multi_region_error': 'retry_strategy set at the call site',
}

# Exceptions too generic to carry an AWS error code or a classification
_GENERIC_EXCEPTIONS = {'Exception', 'RuntimeError'}


def _modules() -> Iterator[Tuple[pathlib.Path, ast.Module]]:
    for path in sorted(PACKAGE_DIR.rglob('*.py')):
        yield path.relative_to(PACKAGE_DIR), ast.parse(path.read_text())


def _is_error_format_response(node: ast.Call) -> bool:
    func = node.func
    name = func.id if isinstance(func, ast.Name) else getattr(func, 'attr', None)
    return (
        name == 'format_response'
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == 'error'
    )


def _error_type_literals(node: ast.AST) -> List[str]:
    """Return the string error_type values a node sets."""
    values: List[ast.AST] = []
    if isinstance(node, ast.keyword) and node.arg == 'error_type':
        values.append(node.value)
    elif isinstance(node, ast.Dict):
        values.extend(
            value
            for key, value in zip(node.keys, node.values)
            if isinstance(key, ast.Constant) and key.value == 'error_type'
        )
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            is_subscript = (
                isinstance(target, ast.Subscript)
                and isinstance(target.slice, ast.Constant)
                and target.slice.value == 'error_type'
            )
            is_constant = isinstance(target, ast.Name) and target.id.endswith('ERROR_TYPE')
            if is_subscript or is_constant:
                values.append(node.value)
    return [v.value for v in values if isinstance(v, ast.Constant) and isinstance(v.value, str)]


def _is_mapped(error_type: str) -> bool:
    return error_type in _ERROR_TYPE_GUIDANCE or any(
        error_type.startswith(prefix) for prefix, _ in _ERROR_TYPE_PREFIX_GUIDANCE
    )


def test_package_dir_exists():
    """Guard against the scans below silently passing on an empty tree."""
    assert any(PACKAGE_DIR.rglob('tools/*.py'))


def test_error_type_literals_are_mapped():
    """Every literal error_type is mapped in error_contract.py or unmapped by design."""
    unmapped = [
        f'{path}:{getattr(node, "lineno", "?")}: {value!r}'
        for path, module in _modules()
        for node in ast.walk(module)
        for value in _error_type_literals(node)
        if not _is_mapped(value) and value not in UNMAPPED_BY_DESIGN
    ]

    assert not unmapped, (
        'Unmapped error_type values get retry_strategy=do_not_retry. Add them to '
        '_ERROR_TYPE_GUIDANCE in utilities/error_contract.py (and the README table), or to '
        'UNMAPPED_BY_DESIGN with the reason:\n' + '\n'.join(unmapped)
    )


@pytest.mark.parametrize('error_type', sorted(UNMAPPED_BY_DESIGN))
def test_unmapped_by_design_is_still_unmapped(error_type):
    """Drop an allowlist entry once its error_type gains a mapping."""
    assert not _is_mapped(error_type)


def test_error_type_is_not_only_nested_in_data():
    """An error_type inside data is invisible to the retry mapping; it must be top level."""
    nested_only = []
    for path, module in _modules():
        for node in ast.walk(module):
            if (
                not isinstance(node, ast.Call)
                or not _is_error_format_response(node)
                or len(node.args) < 2
            ):
                continue
            data = node.args[1]
            has_top_level = any(k.arg == 'error_type' for k in node.keywords)
            if isinstance(data, ast.Dict) and _error_type_literals(data) and not has_top_level:
                nested_only.append(f'{path}:{node.lineno}')

    assert not nested_only, (
        "Pass error_type= to format_response; data['error_type'] is not read:\n"
        + '\n'.join(nested_only)
    )


def test_except_blocks_do_not_wrap_in_generic_exceptions():
    """Raising Exception(...) in an except block hides the AWS error code from handle_aws_error.

    Re-raise the original (`raise`), or raise ValueError / TimeoutError when the failure is
    the caller's input or a timeout, so it is classified.
    """
    wrapping = [
        f'{path}:{raise_node.lineno}'
        for path, module in _modules()
        for handler in ast.walk(module)
        if isinstance(handler, ast.ExceptHandler)
        for raise_node in ast.walk(handler)
        if isinstance(raise_node, ast.Raise)
        and isinstance(raise_node.exc, ast.Call)
        and isinstance(raise_node.exc.func, ast.Name)
        and raise_node.exc.func.id in _GENERIC_EXCEPTIONS
    ]

    assert not wrapping, 'Generic exception raised in an except block:\n' + '\n'.join(wrapping)
