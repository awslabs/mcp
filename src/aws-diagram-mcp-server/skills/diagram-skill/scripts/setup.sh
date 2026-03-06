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

# Diagram skill prerequisite checker
# Checks for GraphViz and Python diagrams package

set -e

echo "Checking diagram skill prerequisites..."
echo ""

# Check GraphViz
if command -v dot &> /dev/null; then
    DOT_VERSION=$(dot -V 2>&1)
    echo "[OK] GraphViz installed: $DOT_VERSION"
else
    echo "[MISSING] GraphViz not found."
    echo ""
    echo "  Install GraphViz:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "    brew install graphviz"
    elif [[ -f /etc/debian_version ]]; then
        echo "    sudo apt-get install graphviz"
    elif [[ -f /etc/redhat-release ]] || [[ -f /etc/system-release ]]; then
        echo "    sudo yum install graphviz"
    else
        echo "    See https://graphviz.org/download/"
    fi
    echo ""
fi

# Check Python diagrams package
if python3 -c "import diagrams" 2>/dev/null; then
    DIAG_VERSION=$(python3 -c "import diagrams; print(diagrams.__version__)" 2>/dev/null || echo "unknown")
    echo "[OK] Python diagrams package installed: v$DIAG_VERSION"
else
    echo "[MISSING] Python diagrams package not found."
    echo ""
    echo "  Install:"
    echo "    pip install diagrams"
    echo ""
fi

# Summary
echo ""
if command -v dot &> /dev/null && python3 -c "import diagrams" 2>/dev/null; then
    echo "All prerequisites met. Ready to generate diagrams."
else
    echo "Some prerequisites are missing. Install them and re-run this script."
    exit 1
fi
