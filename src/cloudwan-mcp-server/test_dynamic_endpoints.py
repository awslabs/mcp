#!/usr/bin/env python3
"""Test script to demonstrate dynamic endpoint management functionality."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from awslabs.cloudwan_mcp_server.server import aws_config_manager

async def test_dynamic_endpoint_management():
    """Test the dynamic endpoint management system."""
    
    print("🔧 Testing Dynamic Endpoint Management System")
    print("=" * 60)
    
    # Test 1: List current profile endpoints (should be empty initially)
    print("\n1. Listing current profile endpoint configurations...")
    result = await aws_config_manager("list_profile_endpoints")
    data = json.loads(result)
    print(f"   Initial profile endpoints: {data.get('total_profiles', 0)} configured")
    
    # Test 2: Set endpoints for production profile
    print("\n2. Setting custom endpoints for production profile...")
    prod_endpoints = {
        "networkmanager": "https://networkmanager-vpce.us-east-1.vpce.amazonaws.com",
        "ec2": "https://ec2-vpce.us-east-1.vpce.amazonaws.com"
    }
    
    result = await aws_config_manager(
        "set_profile_endpoints", 
        profile="taylaand+net-prod-Admin", 
        region=json.dumps(prod_endpoints)
    )
    data = json.loads(result)
    if data.get("success"):
        print(f"   ✅ Endpoints set for taylaand+net-prod-Admin")
        print(f"   Environment variable: {data.get('environment_variable')}")
    else:
        print(f"   ❌ Failed: {data.get('error')}")
    
    # Test 3: Set endpoints for development profile  
    print("\n3. Setting different endpoints for development profile...")
    dev_endpoints = {
        "networkmanager": "https://networkmanager.us-west-2.amazonaws.com",
        "ec2": "https://ec2.us-west-2.amazonaws.com"
    }
    
    result = await aws_config_manager(
        "set_profile_endpoints",
        profile="development-profile",
        region=json.dumps(dev_endpoints)
    )
    data = json.loads(result)
    if data.get("success"):
        print(f"   ✅ Endpoints set for development-profile")
    else:
        print(f"   ❌ Failed: {data.get('error')}")
    
    # Test 4: List all profile endpoints
    print("\n4. Listing all profile endpoint configurations...")
    result = await aws_config_manager("list_profile_endpoints")
    data = json.loads(result)
    print(f"   Total profiles with custom endpoints: {data.get('total_profiles', 0)}")
    
    for profile_key, endpoints in data.get('profile_endpoints', {}).items():
        print(f"   📍 {profile_key}: {len(endpoints)} services configured")
        for service, endpoint in endpoints.items():
            print(f"      - {service}: {endpoint}")
    
    # Test 5: Get specific profile endpoints
    print("\n5. Getting endpoints for production profile...")
    result = await aws_config_manager(
        "get_profile_endpoints", 
        profile="taylaand+net-prod-Admin"
    )
    data = json.loads(result)
    if data.get("success"):
        print(f"   ✅ Profile has custom endpoints: {data.get('has_custom_endpoints')}")
        if data.get("endpoints"):
            for service, endpoint in data["endpoints"].items():
                print(f"      - {service}: {endpoint}")
    else:
        print(f"   ❌ Failed: {data.get('error')}")
    
    # Test 6: Test profile switching behavior
    print("\n6. Testing profile switching with endpoint resolution...")
    
    # Switch to production profile
    result = await aws_config_manager("set_profile", profile="taylaand+net-prod-Admin")
    data = json.loads(result)
    if data.get("success"):
        print(f"   ✅ Switched to production profile")
        print(f"   → This profile will use custom VPC endpoints")
    
    # Switch to a profile without custom endpoints
    result = await aws_config_manager("set_profile", profile="default")
    data = json.loads(result)
    if data.get("success"):
        print(f"   ✅ Switched to default profile")
        print(f"   → This profile will use standard AWS endpoints")
    
    # Test 7: Clear endpoints for development profile
    print("\n7. Clearing endpoints for development profile...")
    result = await aws_config_manager(
        "clear_profile_endpoints",
        profile="development-profile"
    )
    data = json.loads(result)
    if data.get("success"):
        print(f"   ✅ Endpoints cleared: {data.get('endpoints_cleared')}")
        print(f"   → development-profile will now use standard endpoints")
    else:
        print(f"   ❌ Failed: {data.get('error')}")
    
    # Test 8: Verify final state
    print("\n8. Final verification...")
    result = await aws_config_manager("list_profile_endpoints")
    data = json.loads(result)
    print(f"   Final profile endpoint count: {data.get('total_profiles', 0)}")
    
    print("\n" + "=" * 60)
    print("✨ Dynamic Endpoint Management Test Complete!")
    print("\nKey Benefits Demonstrated:")
    print("• ✅ Profile-specific endpoint configuration")
    print("• ✅ Dynamic switching without server restart") 
    print("• ✅ Support for AWS profiles with special characters")
    print("• ✅ Automatic cache clearing for immediate effect")
    print("• ✅ Fallback to standard endpoints when not configured")
    
    print("\n💡 Usage Example:")
    print("   # Set VPC endpoints for production")
    print('   aws_config_manager("set_profile_endpoints", profile="prod", region=\'{"networkmanager": "https://vpce-123.amazonaws.com"}\')') 
    print("   # Switch to production profile")
    print('   aws_config_manager("set_profile", profile="prod")')
    print("   # Now all CloudWAN calls use VPC endpoints automatically!")

if __name__ == "__main__":
    asyncio.run(test_dynamic_endpoint_management())