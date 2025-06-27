#!/usr/bin/env python3
"""Test script to isolate Direct PostgreSQL query execution issues."""

import asyncio
import os
import sys


sys.path.insert(0, '/Users/reachrk/Downloads/awslabs/aws-mcp-servers/src/postgres-mcp-server')

# from awslabs.postgres_mcp_server.unified_connection import UnifiedDBConnectionSingleton  # Module doesn't exist
from awslabs.postgres_mcp_server.connection.connection_factory import ConnectionFactory


async def test_direct_postgres_query():
    """Test Direct PostgreSQL query execution directly."""
    print("🧪 Testing Direct PostgreSQL Query Execution")
    print("=" * 50)

    try:
        # Create connection using ConnectionFactory
        db_connection = ConnectionFactory.create_connection(
            hostname="pg-clone-db-cluster.cluster-cjvgkx7iusm0.us-west-2.rds.amazonaws.com",
            port=5432,
            secret_arn="arn:aws:secretsmanager:us-west-2:288947426911:secret:rds!cluster-7d957e88-d967-46f3-a21e-7db88c36bdf9-NEq9xL",
            database="devdb",
            region="us-west-2",
            readonly=True
        )

        print("✅ Connection created")
        print(f"✅ Connection type: {type(db_connection).__name__}")

        # Test simple query
        print("\n🔍 Testing simple query: SELECT 1")
        result = await db_connection.execute_query("SELECT 1 as test")
        print(f"✅ Query result: {result}")

        # Test version query
        print("\n🔍 Testing version query")
        result = await db_connection.execute_query("SELECT version() as postgresql_version")
        print(f"✅ Version result: {result}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    # Set AWS profile
    os.environ['AWS_PROFILE'] = 'mcp_profile'
    os.environ['AWS_REGION'] = 'us-west-2'

    success = await test_direct_postgres_query()

    if success:
        print("\n🎉 Direct PostgreSQL query execution is working!")
    else:
        print("\n❌ Direct PostgreSQL query execution has issues")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
