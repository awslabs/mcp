#!/usr/bin/env python3
"""
True MCP server integration test that spawns server process and communicates via MCP protocol.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class MCPClient:
    """MCP client that communicates with server via stdin/stdout."""
    
    def __init__(self):
        self.process = None
        self.request_id = 0
    
    async def start_server(self):
        """Start MCP server process."""
        # Start the server using the entry point with debug logging
        env = {**os.environ, "FASTMCP_LOG_LEVEL": "DEBUG"}
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "awslabs.etl_replatforming_mcp_server.server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Initialize MCP connection
        init_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        await self._send_message(init_request)
        response = await self._read_message()
        
        if "error" in response:
            raise Exception(f"Failed to initialize: {response['error']}")
        
        # Send initialized notification (required by FastMCP)
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        await self._send_message(initialized_notification)
        
        return response
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """Call MCP tool using standard MCP tools/call method."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        print(f"DEBUG: Sending request: {json.dumps(request, indent=2)}")
        await self._send_message(request)
        response = await self._read_message()
        print(f"DEBUG: Received response: {json.dumps(response, indent=2)}")
        
        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
        
        return response.get("result", {})
    
    async def stop_server(self):
        """Stop MCP server process."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                print("⚠️ Server didn't terminate gracefully, force killing...")
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                print(f"⚠️ Error stopping server: {e}")
                try:
                    self.process.kill()
                    await self.process.wait()
                except:
                    pass
    
    def _next_id(self):
        self.request_id += 1
        return self.request_id
    
    async def _send_message(self, message):
        """Send JSON message to server."""
        json_str = json.dumps(message) + "\n"
        self.process.stdin.write(json_str.encode())
        await self.process.stdin.drain()
    
    async def _read_message(self):
        """Read JSON message from server."""
        line = await self.process.stdout.readline()
        if not line:
            raise Exception("Server closed connection")
        return json.loads(line.decode().strip())


async def test_mcp_server():
    """Test all 6 MCP server tools end-to-end."""
    print("🚀 Starting MCP Server Integration Test - All 6 Tools")
    print("=" * 60)
    
    client = MCPClient()
    
    try:
        # Start server
        print("🔌 Starting MCP server...")
        init_response = await client.start_server()
        print(f"✅ Server started: {init_response['result']['serverInfo']['name']}")
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent / "output" / f"mcp_integration_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        simple_workflow = {
            "StartAt": "HelloWorld",
            "States": {
                "HelloWorld": {
                    "Type": "Pass",
                    "Result": "Hello World!",
                    "End": True
                }
            }
        }
        
        results = []
        
        # Test 1: convert-single-etl-workflow
        print("\n🔧 Testing convert-single-etl-workflow...")
        try:
            result = await client.call_tool("convert-single-etl-workflow", {
                "workflow_content": json.dumps(simple_workflow),
                "source_framework": "step_functions",
                "target_framework": "airflow"
            })
            status = result.get('structuredContent', {}).get('status', 'unknown')
            print(f"  ✅ Status: {status}")
            results.append(f"convert-single-etl-workflow: ✅ {status}")
            
            with open(output_dir / "convert_single_result.json", 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            results.append(f"convert-single-etl-workflow: ❌ {str(e)}")
        
        # Test 2: parse-single-workflow-to-flex
        print("\n🔧 Testing parse-single-workflow-to-flex...")
        try:
            result = await client.call_tool("parse-single-workflow-to-flex", {
                "workflow_content": json.dumps(simple_workflow),
                "source_framework": "step_functions"
            })
            status = result.get('structuredContent', {}).get('status', 'unknown')
            print(f"  ✅ Status: {status}")
            results.append(f"parse-single-workflow-to-flex: ✅ {status}")
            
            with open(output_dir / "parse_single_result.json", 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            results.append(f"parse-single-workflow-to-flex: ❌ {str(e)}")
        
        # Test 3: generate-single-workflow-from-flex
        print("\n🔧 Testing generate-single-workflow-from-flex...")
        try:
            flex_workflow = {
                "name": "test_workflow",
                "description": "Test workflow",
                "tasks": [{
                    "id": "test_task",
                    "name": "Test Task",
                    "type": "bash",
                    "command": "echo 'Hello World'",
                    "depends_on": []
                }]
            }
            
            result = await client.call_tool("generate-single-workflow-from-flex", {
                "flex_workflow": flex_workflow,
                "target_framework": "airflow"
            })
            status = result.get('structuredContent', {}).get('status', 'unknown')
            print(f"  ✅ Status: {status}")
            results.append(f"generate-single-workflow-from-flex: ✅ {status}")
            
            with open(output_dir / "generate_single_result.json", 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            results.append(f"generate-single-workflow-from-flex: ❌ {str(e)}")
        
        # Test 4: convert-etl-workflow (directory-based)
        print("\n🔧 Testing convert-etl-workflow...")
        try:
            result = await client.call_tool("convert-etl-workflow", {
                "directory_path": "./samples/step_function_jobs",
                "target_framework": "airflow"
            })
            status = result.get('structuredContent', {}).get('status', 'unknown')
            print(f"  ✅ Status: {status}")
            results.append(f"convert-etl-workflow: ✅ {status}")
            
            with open(output_dir / "convert_directory_result.json", 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            results.append(f"convert-etl-workflow: ❌ {str(e)}")
        
        # Test 5: parse-to-flex (directory-based)
        print("\n🔧 Testing parse-to-flex...")
        try:
            result = await client.call_tool("parse-to-flex", {
                "directory_path": "./samples/step_function_jobs"
            })
            status = result.get('structuredContent', {}).get('status', 'unknown')
            print(f"  ✅ Status: {status}")
            results.append(f"parse-to-flex: ✅ {status}")
            
            with open(output_dir / "parse_directory_result.json", 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            results.append(f"parse-to-flex: ❌ {str(e)}")
        
        # Test 6: generate-from-flex (directory-based)
        print("\n🔧 Testing generate-from-flex...")
        try:
            # This test might fail if no FLEX files exist, but we'll try
            result = await client.call_tool("generate-from-flex", {
                "directory_path": "./samples",
                "target_framework": "airflow"
            })
            status = result.get('structuredContent', {}).get('status', 'unknown')
            print(f"  ✅ Status: {status}")
            results.append(f"generate-from-flex: ✅ {status}")
            
            with open(output_dir / "generate_directory_result.json", 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            results.append(f"generate-from-flex: ❌ {str(e)}")
        
        # Summary
        print("\n📈 Test Results Summary")
        print("=" * 40)
        for result in results:
            print(f"  {result}")
        
        successful = len([r for r in results if "✅" in r])
        total = len(results)
        print(f"\n📊 Success Rate: {successful}/{total} tools passed")
        print(f"📁 All results saved to: {output_dir}")
        print("\n✅ MCP integration test completed!")
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        raise
    
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
    finally:
        print("\n🔌 Stopping MCP server...")
        try:
            await client.stop_server()
            print("✅ Server stopped")
        except Exception as e:
            print(f"⚠️ Error during server shutdown: {e}")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())