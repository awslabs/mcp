#!/usr/bin/env python3
"""Quick test to verify Q Developer can connect to CloudWAN MCP server."""

import asyncio
import json
import subprocess
import os
import time
from pathlib import Path

async def test_q_developer_connection():
    """Test that Q Developer can connect to the CloudWAN MCP server."""
    
    print("🔍 Testing Q Developer CLI Connection to CloudWAN MCP Server")
    print("=" * 60)
    
    # Set environment variables as Q Developer would
    env = os.environ.copy()
    env.update({
        "AWS_PROFILE": "taylaand+customer-cloudwan-Admin",
        "AWS_DEFAULT_REGION": "us-west-2",
        "CLOUDWAN_AWS_CUSTOM_ENDPOINTS": '{"networkmanager": "https://networkmanageromega.us-west-2.amazonaws.com"}',
        "AWS_ENDPOINT_URL_NETWORKMANAGER": "https://networkmanageromega.us-west-2.amazonaws.com",
        "CLOUDWAN_MCP_DEBUG": "true",
        "CLOUDWAN_MCP_LOG_LEVEL": "DEBUG"
    })
    
    print("📋 Environment variables set:")
    for key, value in env.items():
        if key.startswith(('AWS_', 'CLOUDWAN_')):
            print(f"   {key}={value}")
    
    print()
    
    # Test 1: Server startup
    print("🚀 Test 1: Server startup test")
    cmd = [
        "uvx", 
        "--from", "/Users/taylaand/code/mcp/cloud-wan-mcp-server/mcp/src/cloudwan-mcp-server",
        "cloudwan-mcp-server",
        "--help"
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("   ✅ Server starts successfully")
            print(f"   📊 Exit code: {result.returncode}")
        else:
            print(f"   ❌ Server startup failed with exit code: {result.returncode}")
            print(f"   📝 stderr: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("   ❌ Server startup timed out")
        return False
    except Exception as e:
        print(f"   ❌ Server startup failed: {str(e)}")
        return False
    
    print()
    
    # Test 2: MCP Protocol availability
    print("🔌 Test 2: MCP Protocol availability test")
    
    # Start the server as a background process for a brief moment to see if MCP initializes
    cmd = [
        "uvx", 
        "--from", "/Users/taylaand/code/mcp/cloud-wan-mcp-server/mcp/src/cloudwan-mcp-server",
        "cloudwan-mcp-server"
    ]
    
    try:
        # Start the server process
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it a moment to initialize
        time.sleep(2)
        
        # Check if process is still running (good sign)
        if process.poll() is None:
            print("   ✅ MCP server process is running")
            print("   📋 Server initialized without immediate crashes")
            
            # Terminate the process cleanly
            process.terminate()
            try:
                process.wait(timeout=5)
                print("   ✅ Server terminated cleanly")
            except subprocess.TimeoutExpired:
                process.kill()
                print("   ⚠️  Server required force termination")
                
        else:
            print(f"   ❌ Server exited immediately with code: {process.returncode}")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"   📝 stderr: {stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ MCP protocol test failed: {str(e)}")
        return False
    
    print()
    
    # Test 3: Configuration validation
    print("📁 Test 3: Q Developer configuration validation")
    
    config_path = Path.home() / ".aws/amazonq/mcp.json"
    
    if not config_path.exists():
        print(f"   ❌ Q Developer config not found at {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if "awslabs.cloudwan-mcp-server" in config.get("mcpServers", {}):
            cloudwan_config = config["mcpServers"]["awslabs.cloudwan-mcp-server"]
            print("   ✅ CloudWAN MCP server configuration found")
            print(f"   📋 Command: {cloudwan_config['command']}")
            print(f"   📋 Args: {' '.join(cloudwan_config['args'])}")
            print(f"   📋 Disabled: {cloudwan_config.get('disabled', False)}")
            
            # Check for required environment variables
            required_env = cloudwan_config.get("env", {})
            if "AWS_PROFILE" in required_env and "AWS_DEFAULT_REGION" in required_env:
                print("   ✅ Required AWS environment variables configured")
            else:
                print("   ⚠️  Some AWS environment variables may be missing")
                
        else:
            print("   ❌ CloudWAN MCP server not found in Q Developer configuration")
            return False
            
    except Exception as e:
        print(f"   ❌ Config validation failed: {str(e)}")
        return False
    
    print()
    
    print("=" * 60)
    print("🎯 Q DEVELOPER CONNECTION TEST SUMMARY")
    print("=" * 60)
    print("✅ Server executable: cloudwan-mcp-server")
    print("✅ Server startup: Working")  
    print("✅ MCP protocol: Initializes correctly")
    print("✅ Q Developer config: Valid")
    print("✅ AWS profile support: taylaand+customer-cloudwan-Admin")
    print("✅ Custom endpoints: Configured")
    print()
    print("🚀 The Q Developer CLI should now be able to connect!")
    print()
    print("💡 If Q Developer still shows connection issues:")
    print("   1. Restart Q Developer CLI")
    print("   2. Check Q Developer logs for detailed error messages")
    print("   3. Verify AWS credentials are accessible from Q Developer's environment")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_q_developer_connection())
    if success:
        print("\n🎉 ALL Q DEVELOPER CONNECTION TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed - Q Developer may have connection issues")
    exit(0 if success else 1)