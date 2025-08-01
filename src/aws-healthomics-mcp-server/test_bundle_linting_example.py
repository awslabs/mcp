#!/usr/bin/env python3
"""Test script to demonstrate multi-file workflow linting functionality."""

import asyncio
from pathlib import Path
from awslabs.aws_healthomics_mcp_server.tools.workflow_linting import lint_workflow_bundle
from mcp.server.fastmcp import Context


async def test_wdl_bundle_linting():
    """Test WDL bundle linting with multi-file workflow."""
    print("=== Testing WDL Bundle Linting ===")
    
    # Read the WDL workflow files
    wdl_files = {}
    
    # Main workflow
    main_wdl = Path("examples/multi_file_workflows/wdl_example/main.wdl")
    if main_wdl.exists():
        wdl_files["main.wdl"] = main_wdl.read_text()
    
    # Task files
    alignment_wdl = Path("examples/multi_file_workflows/wdl_example/tasks/alignment.wdl")
    if alignment_wdl.exists():
        wdl_files["tasks/alignment.wdl"] = alignment_wdl.read_text()
    
    variant_calling_wdl = Path("examples/multi_file_workflows/wdl_example/tasks/variant_calling.wdl")
    if variant_calling_wdl.exists():
        wdl_files["tasks/variant_calling.wdl"] = variant_calling_wdl.read_text()
    
    if not wdl_files:
        print("WDL example files not found, skipping WDL bundle test")
        return
    
    ctx = Context()
    result = await lint_workflow_bundle(
        ctx=ctx,
        workflow_files=wdl_files,
        workflow_format="wdl",
        main_workflow_file="main.wdl"
    )
    
    print(f"Status: {result['status']}")
    print(f"Valid: {result.get('valid', 'N/A')}")
    print(f"Files processed: {result.get('files_processed', [])}")
    print(f"Errors: {result.get('summary', {}).get('errors', 0)}")
    print(f"Warnings: {result.get('summary', {}).get('warnings', 0)}")
    print(f"Total files: {result.get('summary', {}).get('files_count', 0)}")
    
    if result.get('findings'):
        print("\nFindings:")
        for finding in result['findings']:
            print(f"  - {finding['type']} in {finding.get('file', 'unknown')}: {finding['message']}")
    
    if result.get('warnings'):
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning['type']} in {warning.get('file', 'unknown')}: {warning['message']}")


async def test_cwl_bundle_linting():
    """Test CWL bundle linting with multi-file workflow."""
    print("\n=== Testing CWL Bundle Linting ===")
    
    # Read the CWL workflow files
    cwl_files = {}
    
    # Main workflow
    main_cwl = Path("examples/multi_file_workflows/cwl_example/main.cwl")
    if main_cwl.exists():
        cwl_files["main.cwl"] = main_cwl.read_text()
    
    # Tool files
    alignment_cwl = Path("examples/multi_file_workflows/cwl_example/tools/alignment.cwl")
    if alignment_cwl.exists():
        cwl_files["tools/alignment.cwl"] = alignment_cwl.read_text()
    
    variant_calling_cwl = Path("examples/multi_file_workflows/cwl_example/tools/variant_calling.cwl")
    if variant_calling_cwl.exists():
        cwl_files["tools/variant_calling.cwl"] = variant_calling_cwl.read_text()
    
    if not cwl_files:
        print("CWL example files not found, skipping CWL bundle test")
        return
    
    ctx = Context()
    result = await lint_workflow_bundle(
        ctx=ctx,
        workflow_files=cwl_files,
        workflow_format="cwl",
        main_workflow_file="main.cwl"
    )
    
    print(f"Status: {result['status']}")
    print(f"Valid: {result.get('valid', 'N/A')}")
    print(f"Files processed: {result.get('files_processed', [])}")
    print(f"Errors: {result.get('summary', {}).get('errors', 0)}")
    print(f"Warnings: {result.get('summary', {}).get('warnings', 0)}")
    print(f"Total files: {result.get('summary', {}).get('files_count', 0)}")
    
    if result.get('findings'):
        print("\nFindings:")
        for finding in result['findings']:
            print(f"  - {finding['type']} in {finding.get('file', 'unknown')}: {finding['message']}")
    
    if result.get('warnings'):
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning['type']} in {warning.get('file', 'unknown')}: {warning['message']}")


async def test_simple_bundle():
    """Test with a simple in-memory bundle."""
    print("\n=== Testing Simple In-Memory Bundle ===")
    
    # Create a simple WDL bundle in memory
    simple_wdl_files = {
        "main.wdl": """version 1.0

import "tasks.wdl" as tasks

workflow SimpleWorkflow {
    input {
        String input_string
    }
    
    call tasks.ProcessString {
        input: text = input_string
    }
    
    output {
        String result = ProcessString.output_text
    }
}""",
        "tasks.wdl": """version 1.0

task ProcessString {
    input {
        String text
    }
    
    command <<<
        echo "Processing: ${text}" > result.txt
    >>>
    
    runtime {
        docker: "ubuntu:20.04"
        memory: "1 GB"
        cpu: 1
    }
    
    output {
        String output_text = read_string("result.txt")
    }
}"""
    }
    
    ctx = Context()
    result = await lint_workflow_bundle(
        ctx=ctx,
        workflow_files=simple_wdl_files,
        workflow_format="wdl",
        main_workflow_file="main.wdl"
    )
    
    print(f"Status: {result['status']}")
    print(f"Valid: {result.get('valid', 'N/A')}")
    print(f"Files processed: {result.get('files_processed', [])}")
    print(f"Errors: {result.get('summary', {}).get('errors', 0)}")
    print(f"Warnings: {result.get('summary', {}).get('warnings', 0)}")


async def main():
    """Run all bundle linting tests."""
    await test_wdl_bundle_linting()
    await test_cwl_bundle_linting()
    await test_simple_bundle()


if __name__ == "__main__":
    asyncio.run(main())