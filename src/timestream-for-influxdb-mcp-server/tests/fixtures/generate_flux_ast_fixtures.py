# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Record Flux ASTs for tests/test_flux_query_guard.py from a real InfluxDB.

Usage, from the package directory, against a local InfluxDB 2.x:

    INFLUXDB_URL=http://127.0.0.1:8086 INFLUXDB_TOKEN=<token> \
        uv run python tests/fixtures/generate_flux_ast_fixtures.py

The script sends every query in BLOCKED_QUERIES and ALLOWED_QUERIES to
POST /api/v2/query/ast and writes the results to flux_ast.json. The `location`
fields are removed, because the guard does not read them.
"""

import json
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from awslabs.timestream_for_influxdb_mcp_server.server import parse_flux_query  # noqa: E402
from influxdb_client.client.influxdb_client import InfluxDBClient  # noqa: E402
from test_flux_query_guard import ALLOWED_QUERIES, BLOCKED_QUERIES  # noqa: E402


def strip_locations(node):
    """Remove `location` fields from an AST."""
    if isinstance(node, dict):
        return {k: strip_locations(v) for k, v in node.items() if k != 'location'}
    if isinstance(node, list):
        return [strip_locations(v) for v in node]
    return node


def main():
    """Record the ASTs and write flux_ast.json."""
    client = InfluxDBClient(url=os.environ['INFLUXDB_URL'], token=os.environ['INFLUXDB_TOKEN'])
    queries = [q for _, q, _ in BLOCKED_QUERIES] + [q for _, q in ALLOWED_QUERIES]
    fixtures = {query: strip_locations(parse_flux_query(client, query)) for query in queries}
    client.close()
    output = Path(__file__).parent / 'flux_ast.json'
    # Match the repository's pretty-format-json pre-commit hook.
    output.write_text(json.dumps(fixtures, indent=2, sort_keys=True) + '\n')
    print(f'Wrote {len(fixtures)} ASTs to {output}')


if __name__ == '__main__':
    main()
