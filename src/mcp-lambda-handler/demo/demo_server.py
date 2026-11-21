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

"""Demo MCP Lambda server illustrating required vs optional parameter behaviour.

Run directly to inspect the tool schemas that would be sent to MCP clients:

    uv run python demo/demo_server.py
"""

from awslabs.mcp_lambda_handler import MCPLambdaHandler
from typing import Optional


mcp = MCPLambdaHandler(name='demo-server', version='1.0.0')


@mcp.tool()
def search_products(
    query: str,
    category: str,
    max_results: Optional[int] = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    include_out_of_stock: bool = False,
) -> list:
    """Search the product catalogue.

    Args:
        query: The search term (required)
        category: Product category to filter by (required)
        max_results: Maximum number of results to return
        min_price: Minimum price filter in USD
        max_price: Maximum price filter in USD
        include_out_of_stock: Whether to include out-of-stock items
    """
    return []


@mcp.tool()
def get_product(product_id: str) -> dict:
    """Fetch a single product by ID.

    Args:
        product_id: The unique product identifier (required)
    """
    return {}


@mcp.tool()
def add_to_cart(
    product_id: str,
    quantity: int,
    note: Optional[str] = None,
) -> dict:
    """Add a product to the shopping cart.

    Args:
        product_id: Product to add (required)
        quantity: Number of units (required)
        note: Optional note for the item
    """
    return {}


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    return mcp.handle_request(event, context)


if __name__ == '__main__':
    import json

    print('=== MCP Tool Schemas ===\n')
    for name, schema in mcp.tools.items():
        input_schema = schema['inputSchema']
        required = input_schema.get('required', [])
        optional = [p for p in input_schema['properties'] if p not in required]

        print(f'Tool: {name}')
        print(f'  Required params : {required}')
        print(f'  Optional params : {optional}')
        print('  Full inputSchema:')
        print(json.dumps(input_schema, indent=4))
        print()
