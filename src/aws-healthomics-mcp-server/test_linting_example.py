#!/usr/bin/env python3
"""Simple test script to verify workflow linting functionality."""

import asyncio
from awslabs.aws_healthomics_mcp_server.tools.workflow_linting import (
    lint_workflow_definition,
    check_linting_dependencies,
)
from mcp.server.fastmcp import Context


async def test_linting():
    """Test the linting functionality with sample workflows."""
    ctx = Context()
    
    # Test dependency check
    print("=== Checking Linting Dependencies ===")
    deps_result = await check_linting_dependencies(ctx)
    print(f"Dependencies status: {deps_result['status']}")
    print(f"All available: {deps_result['summary']['all_available']}")
    for name, info in deps_result['dependencies'].items():
        print(f"  {name}: {info['version']} - {info['purpose']}")
    
    # Test WDL linting
    print("\n=== Testing WDL Linting ===")
    wdl_content = """version 1.0

workflow HelloWorld {
    input {
        String name = "World"
    }
    
    call SayHello { input: name = name }
    
    output {
        String greeting = SayHello.greeting
    }
}

task SayHello {
    input {
        String name
    }
    
    command <<<
        echo "Hello, ${name}!"
    >>>
    
    runtime {
        docker: "ubuntu:20.04"
        memory: "1 GB"
        cpu: 1
    }
    
    output {
        String greeting = stdout()
    }
}"""
    
    wdl_result = await lint_workflow_definition(
        ctx=ctx,
        workflow_content=wdl_content,
        workflow_format="wdl",
        filename="hello_world.wdl"
    )
    
    print(f"WDL linting status: {wdl_result['status']}")
    print(f"Valid: {wdl_result.get('valid', 'N/A')}")
    print(f"Errors: {wdl_result.get('summary', {}).get('errors', 0)}")
    print(f"Warnings: {wdl_result.get('summary', {}).get('warnings', 0)}")
    
    if wdl_result.get('findings'):
        print("Findings:")
        for finding in wdl_result['findings']:
            print(f"  - {finding['type']}: {finding['message']}")
    
    if wdl_result.get('warnings'):
        print("Warnings:")
        for warning in wdl_result['warnings']:
            print(f"  - {warning['type']}: {warning['message']}")
    
    # Test CWL linting
    print("\n=== Testing CWL Linting ===")
    cwl_content = """cwlVersion: v1.2
class: Workflow

inputs:
  name:
    type: string
    default: "World"

outputs:
  greeting:
    type: string
    outputSource: say_hello/greeting

steps:
  say_hello:
    run:
      class: CommandLineTool
      baseCommand: echo
      inputs:
        name:
          type: string
          inputBinding:
            prefix: "Hello,"
      outputs:
        greeting:
          type: stdout
      stdout: greeting.txt
    in:
      name: name
    out: [greeting]"""
    
    cwl_result = await lint_workflow_definition(
        ctx=ctx,
        workflow_content=cwl_content,
        workflow_format="cwl",
        filename="hello_world.cwl"
    )
    
    print(f"CWL linting status: {cwl_result['status']}")
    print(f"Valid: {cwl_result.get('valid', 'N/A')}")
    print(f"Errors: {cwl_result.get('summary', {}).get('errors', 0)}")
    print(f"Warnings: {cwl_result.get('summary', {}).get('warnings', 0)}")
    
    if cwl_result.get('findings'):
        print("Findings:")
        for finding in cwl_result['findings']:
            print(f"  - {finding['type']}: {finding['message']}")
    
    if cwl_result.get('warnings'):
        print("Warnings:")
        for warning in cwl_result['warnings']:
            print(f"  - {warning['type']}: {warning['message']}")


if __name__ == "__main__":
    asyncio.run(test_linting())