import argparse
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_sql_injection(args):
    """Main entry point End-to-end SQL injection test.

    Args:
        args: list of args
    """
    server_params = StdioServerParameters(
        command='uv',
        args=[
            'run',
            '--directory',
            args.directory,
            'awslabs.postgres-mcp-server',
            '--allow_write_query',
        ],
        env={
            'AWS_PROFILE': 'default',
            'AWS_REGION': args.region,
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print('Available tools:')
            for tool in tools.tools:
                print(f'  - {tool.name}')

            # Step 1: Connect to database
            print('--- Connecting to database ---')
            connect_result = await session.call_tool(
                'connect_to_database',
                {
                    'region': args.region,
                    'database_type': args.database_type,
                    'connection_method': args.connection_method,
                    'cluster_identifier': args.cluster_identifier,
                    'db_endpoint': args.db_endpoint,
                    'port': args.port,
                    'database': args.database,
                },
            )
            print(f'Connection: {connect_result}')

            # Test 1: Normal request (should work)
            print('\n--- Test 1: Normal table name ---')
            result = await session.call_tool(
                'get_table_schema',
                {
                    'connection_method': args.connection_method,
                    'cluster_identifier': args.cluster_identifier,
                    'db_endpoint': args.db_endpoint,
                    'database': args.database,
                    'table_name': 'contacts',
                },
            )
            print(f'Result: {result}')

            # Test 2: SQL injection attempt (should be safe with parameterization)
            print('\n--- Test 2: SQL injection attempt ---')
            malicious_name = "public.users') UNION SELECT usename, passwd, null FROM pg_shadow--"
            result = await session.call_tool(
                'get_table_schema',
                {
                    'connection_method': args.connection_method,
                    'cluster_identifier': args.cluster_identifier,
                    'db_endpoint': args.db_endpoint,
                    'database': args.database,
                    'table_name': malicious_name,
                },
            )
            print(f'Result: {result}')
            # With parameterization: should return empty/null (no such table)
            # Without parameterization: would return pg_shadow data


def parse_args():
    """Helper function to parse the args."""
    parser = argparse.ArgumentParser(
        description='End-to-end SQL injection test for postgres-mcp-server'
    )
    parser.add_argument(
        '--directory',
        required=True,
        help='Path to the postgres-mcp-server project directory',
    )
    parser.add_argument(
        '--region',
        required=True,
        help='AWS region (e.g. us-west-2)',
    )
    parser.add_argument(
        '--database-type',
        dest='database_type',
        required=True,
        choices=['APG', 'RDS'],
        help='Database type (e.g. APG, RDS)',
    )
    parser.add_argument(
        '--connection-method',
        dest='connection_method',
        required=True,
        choices=['pgwire', 'RDS_API'],
        help='Connection method (e.g. pgwire, RDS_API)',
    )
    parser.add_argument(
        '--cluster-identifier',
        dest='cluster_identifier',
        required=True,
        help='Aurora cluster identifier (e.g. ken-apg17)',
    )
    parser.add_argument(
        '--db-endpoint',
        dest='db_endpoint',
        required=True,
        help='Database instance endpoint (e.g. ken-apg17-instance-1.xxx.us-west-2.rds.amazonaws.com)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5432,
        help='Database port (default: 5432)',
    )
    parser.add_argument(
        '--database',
        required=True,
        help='Database name (e.g. postgres)',
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    asyncio.run(test_sql_injection(args))
