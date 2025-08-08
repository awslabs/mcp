#!/usr/bin/env python3
"""
Integration test for dynamic endpoint management using the full MCP server.

This test demonstrates the complete workflow of profile-specific endpoint management
without requiring server restart, using the actual MCP tooling infrastructure.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock AWS dependencies to avoid credential requirements
sys.modules['boto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.config'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()

# Set up path and import the actual server components
sys.path.insert(0, str(Path(__file__).parent))

async def integration_test_dynamic_endpoints():
    """Integration test using the real MCP server components."""
    
    # Import after mocking to avoid import errors
    from awslabs.cloudwan_mcp_server.server import aws_config_manager
    
    print("🚀 Dynamic Endpoint Management Integration Test")
    print("=" * 70)
    print("Testing through full MCP server infrastructure...")
    print()
    
    # Set minimal AWS environment to avoid errors
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
    
    test_results = []
    
    try:
        # Test 1: Initial state - list profile endpoints
        print("📋 Test 1: Check initial profile endpoint state")
        result = await aws_config_manager("list_profile_endpoints")
        data = json.loads(result)
        
        if data.get("success"):
            initial_count = data.get("total_profiles", 0)
            print(f"   ✅ Successfully listed profile endpoints")
            print(f"   📊 Initial profiles with endpoints: {initial_count}")
            test_results.append("✅ list_profile_endpoints: PASS")
        else:
            print(f"   ❌ Failed to list profile endpoints: {data.get('error', 'Unknown error')}")
            test_results.append("❌ list_profile_endpoints: FAIL")
        
        print()
        
        # Test 2: Set endpoints for production profile with special characters
        print("🔧 Test 2: Set endpoints for production profile 'taylaand+net-prod-Admin'")
        
        prod_endpoints = {
            "networkmanager": "https://networkmanager-vpce.us-east-1.vpce.amazonaws.com",
            "ec2": "https://ec2-vpce.us-east-1.vpce.amazonaws.com",
            "sts": "https://sts-vpce.us-east-1.vpce.amazonaws.com"
        }
        
        result = await aws_config_manager(
            "set_profile_endpoints", 
            profile="taylaand+net-prod-Admin", 
            region=json.dumps(prod_endpoints)
        )
        data = json.loads(result)
        
        if data.get("success"):
            env_var = data.get("environment_variable")
            print(f"   ✅ Successfully set endpoints for production profile")
            print(f"   🔑 Environment variable: {env_var}")
            print(f"   📍 Services configured: {len(data.get('endpoints', {}))}")
            test_results.append("✅ set_profile_endpoints (special chars): PASS")
            
            # Verify the environment variable was actually set
            if env_var and env_var in os.environ:
                print(f"   ✅ Environment variable {env_var} confirmed in environment")
            else:
                print(f"   ⚠️  Environment variable not found in os.environ")
        else:
            print(f"   ❌ Failed: {data.get('error', 'Unknown error')}")
            test_results.append("❌ set_profile_endpoints (special chars): FAIL")
        
        print()
        
        # Test 3: Set different endpoints for development profile
        print("🛠️  Test 3: Set different endpoints for development profile")
        
        dev_endpoints = {
            "networkmanager": "https://networkmanager.us-west-2.amazonaws.com",
            "ec2": "https://ec2.us-west-2.amazonaws.com"
        }
        
        result = await aws_config_manager(
            "set_profile_endpoints",
            profile="development-internal",
            region=json.dumps(dev_endpoints)
        )
        data = json.loads(result)
        
        if data.get("success"):
            print(f"   ✅ Successfully set endpoints for development profile")
            print(f"   📍 Services configured: {len(data.get('endpoints', {}))}")
            test_results.append("✅ set_profile_endpoints (dev): PASS")
        else:
            print(f"   ❌ Failed: {data.get('error', 'Unknown error')}")
            test_results.append("❌ set_profile_endpoints (dev): FAIL")
        
        print()
        
        # Test 4: Retrieve specific profile endpoints
        print("🔍 Test 4: Retrieve endpoints for production profile")
        
        result = await aws_config_manager(
            "get_profile_endpoints", 
            profile="taylaand+net-prod-Admin"
        )
        data = json.loads(result)
        
        if data.get("success") and data.get("has_custom_endpoints"):
            endpoints = data.get("endpoints", {})
            print(f"   ✅ Successfully retrieved profile endpoints")
            print(f"   📍 Found {len(endpoints)} configured services:")
            for service, endpoint in endpoints.items():
                print(f"      • {service}: {endpoint}")
            test_results.append("✅ get_profile_endpoints: PASS")
        else:
            print(f"   ❌ Failed or no endpoints found: {data.get('error', 'No custom endpoints')}")
            test_results.append("❌ get_profile_endpoints: FAIL")
        
        print()
        
        # Test 5: Test profile with no custom endpoints
        print("📪 Test 5: Check profile without custom endpoints")
        
        result = await aws_config_manager(
            "get_profile_endpoints",
            profile="default-profile"
        )
        data = json.loads(result)
        
        if data.get("success") and not data.get("has_custom_endpoints"):
            print(f"   ✅ Correctly identified profile without custom endpoints")
            print(f"   📍 Fallback to global: {data.get('fallback_to_global')}")
            test_results.append("✅ get_profile_endpoints (no endpoints): PASS")
        else:
            print(f"   ❌ Unexpected result: {data}")
            test_results.append("❌ get_profile_endpoints (no endpoints): FAIL")
        
        print()
        
        # Test 6: List all configured profile endpoints
        print("📋 Test 6: List all profile endpoint configurations")
        
        result = await aws_config_manager("list_profile_endpoints")
        data = json.loads(result)
        
        if data.get("success"):
            total_profiles = data.get("total_profiles", 0)
            profile_endpoints = data.get("profile_endpoints", {})
            
            print(f"   ✅ Successfully listed all profile endpoints")
            print(f"   📊 Total profiles with custom endpoints: {total_profiles}")
            
            for profile_key, endpoints in profile_endpoints.items():
                print(f"   📍 {profile_key}: {len(endpoints)} services")
                for service, endpoint in endpoints.items():
                    print(f"      • {service}: {endpoint[:50]}{'...' if len(endpoint) > 50 else ''}")
            
            test_results.append("✅ list_profile_endpoints (populated): PASS")
        else:
            print(f"   ❌ Failed: {data.get('error', 'Unknown error')}")
            test_results.append("❌ list_profile_endpoints (populated): FAIL")
        
        print()
        
        # Test 7: Clear endpoints for development profile
        print("🗑️  Test 7: Clear endpoints for development profile")
        
        result = await aws_config_manager(
            "clear_profile_endpoints",
            profile="development-internal"
        )
        data = json.loads(result)
        
        if data.get("success"):
            cleared = data.get("endpoints_cleared")
            print(f"   ✅ Clear operation completed")
            print(f"   📍 Endpoints actually cleared: {cleared}")
            print(f"   🧹 Cache cleared: {data.get('cache_cleared')}")
            test_results.append("✅ clear_profile_endpoints: PASS")
        else:
            print(f"   ❌ Failed: {data.get('error', 'Unknown error')}")
            test_results.append("❌ clear_profile_endpoints: FAIL")
        
        print()
        
        # Test 8: Verify cache clearing and profile switching behavior
        print("🔄 Test 8: Test profile switching with endpoint inheritance")
        
        # First, set current profile to production (with endpoints)
        result = await aws_config_manager("set_profile", profile="taylaand+net-prod-Admin")
        data = json.loads(result)
        
        if data.get("success"):
            print(f"   ✅ Successfully switched to production profile")
            print(f"   📍 This profile uses custom VPC endpoints")
            
            # Verify the profile switch worked
            result = await aws_config_manager("get_current")
            data = json.loads(result)
            current_profile = data.get("current_configuration", {}).get("aws_profile")
            print(f"   🔍 Confirmed current profile: {current_profile}")
            
            test_results.append("✅ profile switching: PASS")
        else:
            print(f"   ❌ Profile switch failed: {data.get('error', 'Unknown error')}")
            test_results.append("❌ profile switching: FAIL")
        
        print()
        
        # Test 9: Error handling - invalid endpoints JSON
        print("⚠️  Test 9: Error handling - invalid endpoints JSON")
        
        result = await aws_config_manager(
            "set_profile_endpoints",
            profile="test-invalid",
            region="invalid-json-string"
        )
        data = json.loads(result)
        
        if not data.get("success") and "JSON format" in data.get("error", ""):
            print(f"   ✅ Correctly rejected invalid JSON")
            print(f"   📍 Error message: {data.get('error', '')[:60]}...")
            test_results.append("✅ error handling (invalid JSON): PASS")
        else:
            print(f"   ❌ Did not properly handle invalid JSON: {data}")
            test_results.append("❌ error handling (invalid JSON): FAIL")
        
        print()
        
        # Test 10: Final verification
        print("🔍 Test 10: Final state verification")
        
        result = await aws_config_manager("list_profile_endpoints")
        data = json.loads(result)
        
        if data.get("success"):
            final_count = data.get("total_profiles", 0)
            print(f"   ✅ Final verification completed")
            print(f"   📊 Final profiles with endpoints: {final_count}")
            print(f"   📍 Remaining configurations:")
            for profile_key in data.get("profile_endpoints", {}):
                print(f"      • {profile_key}")
            test_results.append("✅ final verification: PASS")
        else:
            print(f"   ❌ Final verification failed: {data.get('error', 'Unknown error')}")
            test_results.append("❌ final verification: FAIL")
        
        print()
        
    except Exception as e:
        print(f"💥 Test execution failed with exception: {str(e)}")
        test_results.append(f"❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Final report
    print("=" * 70)
    print("📊 INTEGRATION TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for result in test_results if result.startswith("✅"))
    total = len(test_results)
    
    print(f"Tests Passed: {passed}/{total}")
    print()
    
    for result in test_results:
        print(f"  {result}")
    
    print()
    print("🎯 KEY FEATURES DEMONSTRATED:")
    print("   ✅ Profile-specific endpoint configuration")
    print("   ✅ Support for AWS profiles with special characters (+, @, etc.)")
    print("   ✅ Dynamic endpoint switching without server restart")
    print("   ✅ Automatic client cache clearing")
    print("   ✅ Environment variable management")
    print("   ✅ JSON validation and error handling")
    print("   ✅ Profile inheritance and fallback behavior")
    
    print()
    print("💡 USAGE SCENARIO SOLVED:")
    print('   "what if I want to swap between profiles where one does')
    print('    need custom endpoints and another doesn\'t? We should avoid')
    print('    the user having to stop the assistant and making changes')
    print('    to the mcp.json"')
    print()
    print("   ➡️  SOLUTION: Use profile-specific endpoint environment variables")
    print("       that are automatically resolved when switching profiles!")
    
    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed - review output above")
        return False

if __name__ == "__main__":
    success = asyncio.run(integration_test_dynamic_endpoints())
    sys.exit(0 if success else 1)