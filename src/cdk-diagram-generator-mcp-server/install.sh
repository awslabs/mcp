#!/bin/bash

# CDK Diagram Generator MCP Server Installation Script

echo "Installing CDK Diagram Generator MCP Server..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js 18 or later."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d 'v' -f 2)
NODE_MAJOR_VERSION=$(echo $NODE_VERSION | cut -d '.' -f 1)
if [ $NODE_MAJOR_VERSION -lt 18 ]; then
    echo "Error: Node.js version 18 or later is required. Current version: $NODE_VERSION"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the project
echo "Building the project..."
npm run build

# Create output directory if it doesn't exist
mkdir -p output

# Create MCP configuration
echo "Creating MCP configuration..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > mcp-config.json << EOL
{
  "mcpServers": {
    "cdk-diagram-generator": {
      "command": "node",
      "args": ["${SCRIPT_DIR}/build/index.js"],
      "env": {
        "CDK_DIAGRAM_OUTPUT_DIR": "${SCRIPT_DIR}/output"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
EOL

echo "Installation complete!"
echo ""
echo "To add this server to your MCP configuration:"
echo ""
echo "For Claude Desktop:"
echo "1. Copy the contents of mcp-config.json"
echo "2. Open ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "3. Add the cdk-diagram-generator configuration to the mcpServers object"
echo ""
echo "For Claude VSCode Extension:"
echo "1. Copy the contents of mcp-config.json"
echo "2. Open ~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
echo "3. Add the cdk-diagram-generator configuration to the mcpServers object"
echo ""
echo "To test the server, run:"
echo "node build/index.js"
