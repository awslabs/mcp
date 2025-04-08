# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for Lambda layer parser."""

import asyncio
import json
import sys
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the module directly relative to this test file
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from data.lambda_layer_parser import LambdaLayerParser

async def test_fetch_lambda_layer_docs():
    """Test fetching Lambda layer documentation."""
    print("Fetching Lambda layer documentation...")
    docs = await LambdaLayerParser.fetch_lambda_layer_docs()
    
    # Check if we got the essential information
    for layer_type in ["generic_layers", "python_layers"]:
        print(f"\n=== {layer_type} ===")
        
        # Check for HTML content
        if docs[layer_type]["html"]:
            print(f"✅ HTML content: {len(docs[layer_type]['html'])} characters")
        else:
            print("❌ Missing HTML content")
        
        # Check for code examples
        if docs[layer_type]["examples"]:
            print(f"✅ Code examples: {len(docs[layer_type]['examples'])} found")
            for i, example in enumerate(docs[layer_type]["examples"]):
                print(f"  Example {i+1} ({example['language']}): {len(example['code'])} characters")
        else:
            print("❌ No code examples found")
        
        # Check for directory structure
        if docs[layer_type]["directory_structure"]:
            print(f"✅ Directory structure: {len(docs[layer_type]['directory_structure'])} characters")
            print(f"  Preview: {docs[layer_type]['directory_structure'][:100]}...")
        else:
            print("❌ No directory structure information found")
        
        # Check for props
        if docs[layer_type]["props"]:
            print(f"✅ Props: {len(docs[layer_type]['props'])} found")
            for prop, details in list(docs[layer_type]["props"].items())[:5]:  # Show first 5 props
                print(f"  - {prop}")
            if len(docs[layer_type]["props"]) > 5:
                print(f"  - ... and {len(docs[layer_type]['props']) - 5} more")
        else:
            print("❌ No props found")
    
    # Save the results to a file for inspection
    output_file = os.path.join(os.path.dirname(__file__), "lambda_layer_docs.json")
    with open(output_file, "w") as f:
        # Use a custom serializer to handle non-serializable objects
        def json_serializer(obj):
            try:
                return str(obj)
            except:
                return "Not serializable"
                
        json.dump(docs, f, indent=2, default=json_serializer)
    
    print(f"\nResults saved to {output_file}")
    
    return docs

if __name__ == "__main__":
    docs = asyncio.run(test_fetch_lambda_layer_docs())
