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
import re
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import index_exists
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


def _build_groupby(stage: Dict[str, Any]) -> list:
    fields = stage.get('fields', [])
    args = ['GROUPBY', str(len(fields))] + fields
    for reducer in stage.get('reducers', []):
        func = reducer.get('function', '').upper()
        if func not in VALID_REDUCE_FUNCTIONS:
            raise ValueError(
                f"Unknown REDUCE function '{func}'. Must be: {VALID_REDUCE_FUNCTIONS}"
            )
        args.append('REDUCE')
        args.append(func)
        field = reducer.get('field')
        if func == 'COUNT':
            args.append('0')
        elif func in ('QUANTILE', 'FIRST_VALUE'):
            extra = reducer.get('value')
            if field and extra is not None:
                args += ['2', field, str(extra)]
            elif field:
                args += ['1', field]
            else:
                args.append('0')
        elif func == 'RANDOM_SAMPLE':
            sample_size = reducer.get('size', 1)
            if field:
                args += ['2', field, str(sample_size)]
            else:
                args.append('0')
        elif field:
            args += ['1', field]
        else:
            args.append('0')
        alias = reducer.get('alias')
        if alias:
            args += ['AS', alias]
    return args


def _build_sortby(stage: Dict[str, Any]) -> list:
    fields = stage.get('fields', [])
    sort_args: list = []
    for f in fields:
        if isinstance(f, dict):
            sort_args.append(f.get('field', ''))
            sort_args.append(f.get('order', 'ASC').upper())
        else:
            sort_args += [f, 'ASC']
    args = ['SORTBY', str(len(sort_args))] + sort_args
    if stage.get('max'):
        args += ['MAX', str(stage['max'])]
    return args


def _build_apply(stage: Dict[str, Any]) -> list:
    expr = stage.get('expression', '')
    alias = stage.get('alias', '')
    if not expr or not alias:
        raise ValueError("APPLY stage requires 'expression' and 'alias'")
    return ['APPLY', expr, 'AS', alias]


def _build_filter(stage: Dict[str, Any]) -> list:
    expr = stage.get('expression', '')
    if not expr:
        raise ValueError("FILTER stage requires 'expression'")
    return ['FILTER', expr]


def _build_limit(stage: Dict[str, Any]) -> list:
    return ['LIMIT', str(stage.get('offset', 0)), str(stage.get('count', 10))]


_STAGE_BUILDERS = {
    'GROUPBY': _build_groupby,
    'SORTBY': _build_sortby,
    'APPLY': _build_apply,
    'FILTER': _build_filter,
    'LIMIT': _build_limit,
}


def _decode_aggregate_response(raw) -> List[Dict[str, Any]]:
    """Decode ft.aggregate response into list of dicts."""
    if not raw or len(raw) < 1:
        return []
    rows = []
    # ft.aggregate returns a list; each element after index 0 is a row dict or list
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
        query: Filter query (default: "*" for all documents)
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

        # Pre-validate: avoid GLIDE crashes on error responses
        if not await index_exists(client, index_name):
            return {'status': 'error', 'reason': f"Index '{index_name}' does not exist"}

        if query.strip() == '*':
            return {
                'status': 'error',
                'reason': "Wildcard '*' is not supported as an aggregate query. "
                "Use a field filter (e.g., '@price:[0 inf]', '@category:{Books}').",
            }

        # Build the pipeline args for custom_command.
        # TODO: Migrate to ft.aggregate() when GLIDE adds full pipeline stage support.
        cmd: list = ['FT.AGGREGATE', index_name, query]

        if pipeline:
            # Collect document fields that need LOAD and track pipeline aliases.
            load_fields: set = set()
            pipeline_aliases: set = set()

            def _extract_expr_fields(expr: str) -> None:
                """Add @field references from an expression, skipping pipeline aliases."""
                for match in re.findall(r'@(\w+)', expr):
                    if match not in pipeline_aliases:
                        load_fields.add(f'@{match}')

            for stage in pipeline:
                stype = stage.get('type', '').upper()
                if stype == 'GROUPBY':
                    for f in stage.get('fields', []):
                        load_fields.add(f)
                    for reducer in stage.get('reducers', []):
                        field = reducer.get('field')
                        if field and reducer.get('function', '').upper() != 'COUNT':
                            load_fields.add(field)
                        alias = reducer.get('alias')
                        if alias:
                            pipeline_aliases.add(alias)
                elif stype == 'SORTBY':
                    for f in stage.get('fields', []):
                        name = f.get('field', f) if isinstance(f, dict) else f
                        if isinstance(name, str) and name.startswith('@'):
                            field_name = name[1:]
                            if field_name not in pipeline_aliases:
                                load_fields.add(name)
                elif stype == 'APPLY':
                    _extract_expr_fields(stage.get('expression', ''))
                    alias = stage.get('alias')
                    if alias:
                        pipeline_aliases.add(alias)
                elif stype == 'FILTER':
                    _extract_expr_fields(stage.get('expression', ''))

            if load_fields:
                cmd += ['LOAD', str(len(load_fields))] + list(load_fields)

            for i, stage in enumerate(pipeline):
                stype = stage.get('type', '').upper()
                if stype not in VALID_STAGE_TYPES:
                    return {
                        'status': 'error',
                        'reason': f"Stage {i}: unknown type '{stype}'. Must be: {VALID_STAGE_TYPES}",
                    }
                builder = _STAGE_BUILDERS[stype]
                try:
                    cmd += builder(stage)
                except ValueError as e:
                    return {'status': 'error', 'reason': f'Stage {i} ({stype}): {e}'}

        logger.debug('aggregate command: %s', ' '.join(str(x) for x in cmd))
        raw = await client.custom_command(cmd)
        logger.debug('aggregate raw response type=%s value=%r', type(raw).__name__, raw)

        # GLIDE custom_command returns a list of row dicts for FT.AGGREGATE
        rows: List[Dict[str, Any]] = []
        if isinstance(raw, list):
            rows = _decode_aggregate_response(raw)

        return {'status': 'success', 'results': rows, 'total': len(rows)}

    except RequestError as e:
        return {'status': 'error', 'reason': str(e)}
    except Exception as e:
        logger.exception('aggregate failed: %s', e)
        return {'status': 'error', 'reason': str(e)}
