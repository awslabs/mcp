#!/bin/bash

# Simplified uvx environment setup script / 简化的 uvx 环境设置脚本

set -e

echo "=== Setting up Chaos Mesh MCP for uvx / 为 uvx 设置 Chaos Mesh MCP ==="

# Get script directory / 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run original setup script / 运行原始设置脚本
echo "Running EKS permissions setup... / 运行 EKS 权限设置..."
"$SCRIPT_DIR/setup-eks-permissions.sh"

# Check generated kubeconfig / 检查生成的 kubeconfig
KUBECONFIG_PATH="$SCRIPT_DIR/chaos-mesh-mcp-kubeconfig"
if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo "ERROR: Kubeconfig not generated at $KUBECONFIG_PATH / 错误：未在 $KUBECONFIG_PATH 生成 Kubeconfig"
    exit 1
fi

echo "✓ Kubeconfig generated at $KUBECONFIG_PATH / ✓ Kubeconfig 已生成在 $KUBECONFIG_PATH"

# Create environment configuration file / 创建环境配置文件
ENV_FILE="$HOME/.aws/amazonq/chaosmesh-env"
cat > "$ENV_FILE" << EOF
# Chaos Mesh MCP Environment Configuration / Chaos Mesh MCP 环境配置
export KUBECONFIG="$KUBECONFIG_PATH"
export AWS_REGION="${AWS_REGION:-us-east-2}"
EOF

echo "✓ Environment configuration saved to $ENV_FILE / ✓ 环境配置已保存到 $ENV_FILE"

echo ""
echo "=== Setup Complete / 设置完成 ==="
echo ""
echo "To use with uvx, update your mcp.json configuration: / 要与 uvx 一起使用，请更新您的 mcp.json 配置："
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
echo "Or source the environment file before running uvx: / 或在运行 uvx 之前 source 环境文件："
echo "source $ENV_FILE"
