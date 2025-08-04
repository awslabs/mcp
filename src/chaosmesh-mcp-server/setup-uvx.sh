#!/bin/bash

# 简化的 uvx 环境设置脚本

set -e

echo "=== Setting up Chaos Mesh MCP for uvx ==="

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 运行原始设置脚本
echo "Running EKS permissions setup..."
"$SCRIPT_DIR/setup-eks-permissions.sh"

# 检查生成的 kubeconfig
KUBECONFIG_PATH="$SCRIPT_DIR/chaos-mesh-mcp-kubeconfig"
if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo "ERROR: Kubeconfig not generated at $KUBECONFIG_PATH"
    exit 1
fi

echo "✓ Kubeconfig generated at $KUBECONFIG_PATH"

# 创建环境配置文件
ENV_FILE="$HOME/.aws/amazonq/chaosmesh-env"
cat > "$ENV_FILE" << EOF
# Chaos Mesh MCP Environment Configuration
export KUBECONFIG="$KUBECONFIG_PATH"
export AWS_REGION="${AWS_REGION:-us-east-2}"
EOF

echo "✓ Environment configuration saved to $ENV_FILE"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To use with uvx, update your mcp.json configuration:"
echo ""
echo '"chaosmesh-mcp": {'
echo '  "command": "uvx",'
echo '  "args": ['
echo '    "--from",'
echo '    "git+https://github.com/RadiumGu/Chaosmesh-MCP.git",'
echo '    "chaosmesh-mcp",'
echo '    "--kubeconfig",'
echo "    \"$KUBECONFIG_PATH\","
echo '    "--skip-env-check",'
echo '    "--transport",'
echo '    "stdio"'
echo '  ],'
echo '  "env": {'
echo "    \"KUBECONFIG\": \"$KUBECONFIG_PATH\","
echo '    "AWS_REGION": "us-east-2"'
echo '  },'
echo '  "autoApprove": [],'
echo '  "disabled": false,'
echo '  "transportType": "stdio"'
echo '}'
echo ""
echo "Or source the environment file before running uvx:"
echo "source $ENV_FILE"
