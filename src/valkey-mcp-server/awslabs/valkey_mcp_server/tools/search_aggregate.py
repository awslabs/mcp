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

"""FT.AGGREGATE structured pipeline builder for Valkey Search (GLIDE)."""

import logging
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import index_exists
from glide import ft
from glide_shared.commands.server_modules.ft_options.ft_aggregate_options import (
    FtAggregateApply,
    FtAggregateClause,
    FtAggregateFilter,
    FtAggregateGroupBy,
    FtAggregateLimit,
    FtAggregateOptions,
    FtAggregateReducer,
    FtAggregateSortBy,
    FtAggregateSortProperty,
    OrderBy,
)
from glide_shared.exceptions import RequestError
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

VALID_REDUCE_FUNCTIONS = {
    'COUNT',
    'COUNT_DISTINCT',
    'COUNT_DISTINCTISH',
    'SUM',
    'MIN',
    'MAX',
    'AVG',
    'STDDEV',
    'QUANTILE',
    'TOLIST',
    'FIRST_VALUE',
    'RANDOM_SAMPLE',
}

VALID_STAGE_TYPES = {'GROUPBY', 'SORTBY', 'APPLY', 'FILTER', 'LIMIT'}


def _build_reducer(r: Dict[str, Any]) -> FtAggregateReducer:
    """Translate a reducer dict into a GLIDE FtAggregateReducer."""
    func = r.get('function', '').upper()
    if func not in VALID_REDUCE_FUNCTIONS:
        raise ValueError(f"Unknown REDUCE function '{func}'. Must be: {VALID_REDUCE_FUNCTIONS}")
    field = r.get('field')
    args: list = [field] if field else []
    if func in ('QUANTILE', 'FIRST_VALUE') and r.get('value') is not None:
        args.append(str(r['value']))
    if func == 'RANDOM_SAMPLE' and r.get('size') is not None:
        args.append(str(r['size']))
    return FtAggregateReducer(func, args, name=r.get('alias'))


def _build_clause(stage: Dict[str, Any]) -> FtAggregateClause:
    """Translate a pipeline stage dict into a GLIDE FtAggregateClause."""
    stype = stage.get('type', '').upper()

    if stype == 'GROUPBY':
        fields = stage.get('fields', [])
        reducers = [_build_reducer(r) for r in stage.get('reducers', [])]
        return FtAggregateGroupBy(fields, reducers)

    if stype == 'SORTBY':
        props = []
        for f in stage.get('fields', []):
            if isinstance(f, dict):
                order = OrderBy.DESC if f.get('order', 'ASC').upper() == 'DESC' else OrderBy.ASC
                props.append(FtAggregateSortProperty(f.get('field', ''), order))
            else:
                props.append(FtAggregateSortProperty(f, OrderBy.ASC))
        return FtAggregateSortBy(props)

    if stype == 'APPLY':
        expr = stage.get('expression', '')
        alias = stage.get('alias', '')
        if not expr or not alias:
            raise ValueError("APPLY stage requires 'expression' and 'alias'")
        return FtAggregateApply(expr, alias)

    if stype == 'FILTER':
        expr = stage.get('expression', '')
        if not expr:
            raise ValueError("FILTER stage requires 'expression'")
        return FtAggregateFilter(expr)

    if stype == 'LIMIT':
        return FtAggregateLimit(stage.get('offset', 0), stage.get('count', 10))

    raise ValueError(f"Unknown stage type '{stype}'. Must be: {VALID_STAGE_TYPES}")


def _decode_aggregate_response(raw: Any) -> List[Dict[str, Any]]:
    """Decode ft.aggregate response into list of dicts.

    Handles two response formats: GLIDE may return rows as dicts (bytes keys/values)
    or as flat lists of alternating key-value pairs, depending on the Valkey version
    and GLIDE client version.
    """
    if not raw or not isinstance(raw, list):
        return []
    rows = []
    for row in raw:
        if isinstance(row, dict):
            d: Dict[str, Any] = {}
            for k, v in row.items():
                str_k = k.decode() if isinstance(k, bytes) else str(k)
                str_v = v.decode() if isinstance(v, bytes) else v
                d[str_k] = str_v
            rows.append(d)
        elif isinstance(row, list):
            d = {}
            for i in range(0, len(row) - 1, 2):
                key = row[i].decode() if isinstance(row[i], bytes) else str(row[i])
                val = row[i + 1]
                if isinstance(val, bytes):
                    val = val.decode()
                d[key] = val
            rows.append(d)
    return rows


@mcp.tool()
async def aggregate(
    index_name: str,
    query: str = '*',
    pipeline: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run an FT.AGGREGATE pipeline on a Valkey Search index.

    Translates structured JSON pipeline stages into FT.AGGREGATE syntax,
    eliminating the need to know the complex ordered DSL.

    Args:
        index_name: Valkey Search index name
        query: Filter query (e.g., "@price:[0 inf]", "@category:{Books}")
        pipeline: Ordered list of pipeline stages. Each stage is a dict
            with a "type" key. Supported types:

            GROUPBY — group and aggregate:
              {"type": "GROUPBY", "fields": ["@category"],
               "reducers": [{"function": "COUNT", "alias": "cnt"},
                            {"function": "AVG", "field": "@price", "alias": "avg"}]}

            SORTBY — sort results:
              {"type": "SORTBY",
               "fields": [{"field": "@cnt", "order": "DESC"}]}

            APPLY — computed expression:
              {"type": "APPLY", "expression": "@price * 1.1",
               "alias": "adjusted"}

            FILTER — post-aggregation filter:
              {"type": "FILTER", "expression": "@cnt > 5"}

            LIMIT — pagination:
              {"type": "LIMIT", "offset": 0, "count": 10}

    Returns:
        Dict with "status" and "results" (list of row dicts).
    """
    try:
        client = await get_client()

        # Pre-validate on every call: GLIDE errors are catchable RequestErrors,
        # but FastMCP's stdio transport crashes on exceptions during concurrent
        # tool calls. Pre-validating avoids the error path.
        if not await index_exists(client, index_name):
            return {'status': 'error', 'reason': f"Index '{index_name}' does not exist"}

        # Reject wildcard '*' — some Valkey versions reject it with "Invalid: query string
        # syntax". The resulting RequestError is catchable, but FastMCP's stdio transport
        # crashes when exceptions occur during concurrent tool calls.
        if query.strip() == '*':
            return {
                'status': 'error',
                'reason': "Wildcard '*' is not supported as an aggregate query. "
                "Use a field filter (e.g., '@price:[0 inf]', '@category:{Books}').",
            }

        # Build typed GLIDE clauses from pipeline stages
        clauses: list[FtAggregateClause] = []
        if pipeline:
            for i, stage in enumerate(pipeline):
                try:
                    clauses.append(_build_clause(stage))
                except ValueError as e:
                    return {'status': 'error', 'reason': f'Stage {i}: {e}'}

        options = FtAggregateOptions(loadAll=True, clauses=clauses)

        logger.debug('aggregate: index=%s query=%s clauses=%d', index_name, query, len(clauses))
        raw = await ft.aggregate(
            client=client, index_name=index_name, query=query, options=options
        )
        logger.debug('aggregate raw response type=%s', type(raw).__name__)

        rows = _decode_aggregate_response(raw)
        return {'status': 'success', 'results': rows, 'total': len(rows)}

    except RequestError as e:
        return {'status': 'error', 'reason': str(e)}
    except Exception as e:
        logger.exception('aggregate failed: %s', e)
        return {'status': 'error', 'reason': str(e)}
