import asyncio
import os
import traceback
from diagrams_mcp_server.diagrams import generate_diagram

async def main():
    try:
        code = """with Diagram("Test AWS Diagram", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""
        print("Starting diagram generation...")
        result = await generate_diagram(code, filename="test_diagram", workspace_dir=os.getcwd())
        print(f"Status: {result.status}")
        print(f"Path: {result.path}")
        print(f"Message: {result.message}")
        
        if result.status == "success" and result.path and os.path.exists(result.path):
            print(f"Diagram generated successfully at {result.path}")
            print(f"File size: {os.path.getsize(result.path)} bytes")
        else:
            print("Failed to generate diagram")
            if result.path:
                print(f"Path exists: {os.path.exists(result.path)}")
    except Exception as e:
        print(f"Exception occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
