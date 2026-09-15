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

"""Automatic pagination continuation hints for paginated MCP tool responses.

Paginated tools return a continuation token as a bare, easy-to-miss field, and
agents routinely answer as if one page were the complete result set. This
module wraps a tool's *return value* -- not the request/response lifecycle --
so every paginated response additionally carries a self-describing
``pagination`` status block, in both the incomplete and the complete case.
Wrapping the return value (rather than a server-side middleware hook) means
the same mutation reaches both the text content block and ``structuredContent``
that FastMCP derives from a tool's result, and lets the wrapper read the
wrapped function's real signature to name the right continuation parameter.

Three response idioms exist across this server's tools; all are handled here:

* A bare, camelCase ``nextToken`` in a ``Dict[str, Any]`` response, omitted
  entirely once there is no next page (~17 ``List*``/``Get*`` tools).
* A snake_case ``next_token`` in a ``Dict[str, Any]`` response that comes from
  a Pydantic model's ``model_dump()`` and so is always present, with value
  ``None`` on the last page rather than omitted (the two ECR list tools).
* A nested ``pagination`` dict already produced by the genomics file search
  tool, carrying its own ``has_more`` / ``continuation_token`` fields.

Non-paginated tools and error payloads (``handle_tool_error`` always returns
``{'error': ...}``) pass through byte-identical.
"""

import inspect
from functools import wraps
from typing import Any, Callable, Dict, Optional


# Parameter names recognized as a tool's continuation-token input, checked in
# this order. Every paginated tool in this server uses one of the two.
_CONTINUATION_PARAM_NAMES = ('next_token', 'continuation_token')

# Registered tool name -> the literal key its Dict[str, Any] response uses to
# carry the continuation token.
#
# This is an explicit allowlist rather than a "has a next_token parameter"
# signature check because signature alone is not a reliable signal: the
# CloudWatch-log tools in workflow_analysis.py (GetAHORunLogs, GetAHORunManifestLogs,
# GetAHORunEngineLogs, GetAHOTaskLogs) also accept next_token, but their responses
# carry nextForwardToken / nextBackwardToken instead, and CloudWatch always
# returns those tokens even when there is no more data -- presence can't signal
# completion the way it does for the tools below. list_run_metrics and friends in
# run_metrics.py have an internal next_token loop variable that fully drains
# CloudWatch pagination before returning, so it never reaches the client-facing
# response at all. Both families are deliberately excluded here.
_DICT_TOKEN_KEYS: Dict[str, str] = {
    'ListAHOWorkflows': 'nextToken',
    'ListAHOWorkflowVersions': 'nextToken',
    'ListAHORuns': 'nextToken',
    'ListAHORunTasks': 'nextToken',
    'ListAHORunGroups': 'nextToken',
    'ListAHORunCaches': 'nextToken',
    'ListAHOBatches': 'nextToken',
    'ListAHORunsInBatch': 'nextToken',
    'ListAHOSequenceStores': 'nextToken',
    'ListAHOReadSets': 'nextToken',
    'ListAHOReadSetImportJobs': 'nextToken',
    'ListAHOReadSetExportJobs': 'nextToken',
    'ListAHOReferenceStores': 'nextToken',
    'ListAHOReferences': 'nextToken',
    'ListAHOReferenceImportJobs': 'nextToken',
    'ListAHOConfigurations': 'nextToken',
    'ListCodeConnections': 'nextToken',
    'ListECRRepositories': 'next_token',
    'ListPullThroughCacheRules': 'next_token',
}


def _continuation_param_name(fn: Callable[..., Any]) -> str:
    """Derive the real parameter name a caller uses to pass a continuation token.

    Inspects the wrapped tool's own signature so the instruction text always
    names the parameter the tool actually accepts (``next_token`` vs.
    ``continuation_token``), rather than a name assumed by the caller.
    """
    params = inspect.signature(fn).parameters
    for name in _CONTINUATION_PARAM_NAMES:
        if name in params:
            return name
    return 'next_token'


def _first_list_length(values: Any) -> int:
    """Count of the (single) list-valued field in a paginated result.

    Every idiom handled here carries exactly one "items returned" list per
    response (workflows, runs, repositories, ...); the rest of the response is
    scalar metadata or the token itself.
    """
    for value in values:
        if isinstance(value, list):
            return len(value)
    return 0


def _instruction(
    is_complete: bool,
    tool_name: str,
    param_name: str,
    token: Optional[str],
    returned_count: int,
) -> str:
    if is_complete:
        return (
            f'COMPLETE -- all {returned_count} result(s) were returned for this '
            f'{tool_name} call. No further calls are needed to see the rest.'
        )
    if token is None:
        # More results exist (per the tool's own has_more/more-flag signal) but
        # this particular call did not come back with a usable token to advance
        # with -- echoing it anyway would tell an agent to call back with the
        # literal string "None". Flag the partial state honestly instead of
        # fabricating an actionable-looking call that isn't.
        return (
            f'PARTIAL RESULTS -- {tool_name} indicates more results exist, but this '
            f'call did not return a usable {param_name} to continue with. '
            f'{returned_count} item(s) returned so far. Do not answer questions about '
            "totals, counts, or 'all' items from this page alone; retrying with "
            'different parameters (for example a narrower filter, a smaller page '
            'size, or an alternate pagination mode) may yield a usable token.'
        )
    return (
        'PARTIAL RESULTS -- this is one page, not the full set. '
        f'{returned_count} item(s) returned and more exist. Call {tool_name} again '
        f'with {param_name}="{token}" plus the same other arguments, and repeat '
        'until pagination.isComplete is true. Do not answer questions about '
        "totals, counts, or 'all' items from this page alone."
    )


def _pagination_block(
    is_complete: bool,
    returned_count: int,
    tool_name: str,
    param_name: str,
    token: Optional[str],
) -> Dict[str, Any]:
    block: Dict[str, Any] = {'isComplete': is_complete, 'returnedCount': returned_count}
    if not is_complete and token is not None:
        block['nextToken'] = token
    block['instruction'] = _instruction(is_complete, tool_name, param_name, token, returned_count)
    return block


def paginating(tool_name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap *fn* so its returned paginated response carries an actionable pagination hint.

    Detects which pagination idiom (if any) the wrapped tool's response uses
    and injects an additive ``pagination`` status block -- always, whether the
    page is complete or not. Existing fields keep their exact names, values,
    and positions; nothing is renamed or removed. Non-paginated tools and
    error payloads (``{'error': ...}``) pass through unchanged.

    Args:
        tool_name: The literal name the tool is registered under (e.g.
            ``'ListAHOWorkflows'``), used verbatim in the instruction text so
            an agent can act on it directly.
        fn: The tool function being registered.

    Returns:
        An async wrapper suitable for passing to ``mcp.tool(name=tool_name)``.
    """
    param_name = _continuation_param_name(fn)
    token_key = _DICT_TOKEN_KEYS.get(tool_name)

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await fn(*args, **kwargs)

        if not isinstance(result, dict) or 'error' in result:
            return result

        nested = result.get('pagination')
        if isinstance(nested, dict) and 'has_more' in nested:
            token = nested.get('continuation_token')
            is_complete = not bool(nested['has_more'])
            returned_count = len(result.get('results', []))
            nested.update(
                _pagination_block(is_complete, returned_count, tool_name, param_name, token)
            )
            return result

        if token_key is not None:
            token = result.get(token_key)
            is_complete = token is None
            returned_count = _first_list_length(result.values())
            result['pagination'] = _pagination_block(
                is_complete, returned_count, tool_name, param_name, token
            )
            return result

        return result

    return wrapper
