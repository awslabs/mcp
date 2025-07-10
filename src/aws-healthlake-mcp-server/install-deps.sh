#!/bin/bash
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

# CI helper script for installing dependencies
# Tries multiple approaches to handle uv version compatibility issues

set -e

echo "Attempting to install dependencies..."

# Try frozen sync first
if uv sync --frozen --all-extras --dev; then
    echo "✅ Successfully installed dependencies with frozen lock file"
    exit 0
fi

echo "⚠️  Frozen sync failed, trying without --frozen flag..."

# Try without frozen flag
if uv sync --all-extras --dev; then
    echo "✅ Successfully installed dependencies without frozen lock"
    exit 0
fi

echo "⚠️  uv sync failed, trying pip fallback..."

# Fallback to pip with requirements file
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
    echo "✅ Successfully installed dependencies with pip fallback"
    exit 0
fi

echo "❌ All dependency installation methods failed"
exit 1
