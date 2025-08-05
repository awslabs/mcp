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


"""Test simple AWS client async wrapper"""

import asyncio
import os
import sys

sys.path.append(".")


async def test_simple_client() -> None:
    """Test AWS client wrapper directly"""
    # Set correct environment
    os.environ["AWS_PROFILE"] = "taylaand+net-dev-Admin"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_REGION"] = "us-west-2"

    try:
        from awslabs.cloudwan_mcp_server.aws.client_manager import AWSClientManager
        from awslabs.cloudwan_mcp_server.config import CloudWANConfig

        print("🔄 Initializing AWS Client Manager...")

        config = CloudWANConfig()
        aws_manager = AWSClientManager(config)

        print("✅ Components initialized successfully")

        # Test direct client creation first
        print("\n🔍 Testing direct sync client...")
        sync_client = aws_manager.get_client("networkmanager", "us-west-2")
        print(f"Sync client type: {type(sync_client)}")

        # Test sync operation
        print("\n🔍 Testing sync operation...")
        response = sync_client.describe_global_networks()
        print(f"Sync response success: {response is not None}")
        print(f"Number of global networks: {len(response.get('GlobalNetworks', []))}")

        # Test async context manager
        print("\n🔍 Testing async client context...")
        async with aws_manager.client_context("networkmanager", "us-west-2") as nm:
            print(f"Async client type: {type(nm)}")
            print(f"Client has describe_global_networks: {hasattr(nm, 'describe_global_networks')}")

            # Test if we can call the method
            describe_method = getattr(nm, "describe_global_networks")
            print(f"Method type: {type(describe_method)}")
            print(f"Method is callable: {callable(describe_method)}")

            # Try the actual async call
            print("\n🔍 Testing async method call...")
            result = await nm.describe_global_networks()
            print(f"Async response success: {result is not None}")
            print(f"Number of global networks: {len(result.get('GlobalNetworks', []))}")

    except Exception as e:
        print(f"❌ Error testing client: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_client())
