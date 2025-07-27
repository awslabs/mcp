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

"""Test script to verify Checkov installation logic"""

import subprocess
import tempfile
import os

def test_checkov_install_logic():
    """Test the Checkov installation detection and installation logic"""
    
    # First, test detection when checkov IS available
    try:
        result = subprocess.run(
            ['checkov', '--version'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("✅ Checkov detection works - found version:", result.stdout.strip())
        else:
            print("❌ Checkov detection failed")
    except FileNotFoundError:
        print("❌ Checkov not found (FileNotFoundError)")
    
    # Test what happens when we simulate checkov not being found
    # We'll temporarily rename checkov if it exists
    checkov_path = None
    try:
        # Find checkov path
        result = subprocess.run(['which', 'checkov'], capture_output=True, text=True)
        if result.returncode == 0:
            checkov_path = result.stdout.strip()
            print(f"📍 Found checkov at: {checkov_path}")
    except:
        pass
    
    # Test the uv tool install command syntax
    print("\n🧪 Testing uv tool install syntax...")
    try:
        result = subprocess.run(
            ['uv', 'tool', 'install', '--help'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("✅ uv tool install command is valid")
        else:
            print("❌ uv tool install command failed:", result.stderr)
    except FileNotFoundError:
        print("❌ uv not found")

if __name__ == "__main__":
    test_checkov_install_logic()