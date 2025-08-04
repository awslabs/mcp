# Chaos Mesh MCP Server - uvx 使用指南 / Usage Guide

## 快速开始 / Quick Start

### 1. 环境设置（一次性）/ Environment Setup (One-time)

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
./setup-uvx.sh
```

这个脚本会：/ This script will:
- 运行 EKS 权限设置 / Run EKS permission setup
- 生成 Kubernetes service account kubeconfig / Generate Kubernetes service account kubeconfig
- 安装 Chaos Mesh（如果需要）/ Install Chaos Mesh (if needed)
- 创建环境配置文件 / Create environment configuration file

### 2. MCP 配置 / MCP Configuration

你的 `~/.aws/amazonq/mcp.json` 已经配置为：/ Your `~/.aws/amazonq/mcp.json` is configured as:

```json
"chaosmesh-mcp": {
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/RadiumGu/Chaosmesh-MCP.git",
    "chaosmesh-mcp",
    "--kubeconfig",
    "/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig",
    "--skip-env-check",
    "--transport",
    "stdio"
  ],
  "env": {
    "KUBECONFIG": "/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig",
    "AWS_REGION": "us-east-2"
  },
  "autoApprove": [],
  "disabled": false,
  "transportType": "stdio"
}
```

### 3. 使用 / Usage

重启 Amazon Q CLI：/ Restart Amazon Q CLI:

```bash
# 退出当前会话 / Exit current session
/quit

# 重新启动 / Restart
q chat
```

## 对比 / Comparison

### 之前的方式 / Previous Method:
```bash
git clone https://github.com/RadiumGu/Chaosmesh-MCP.git
cd Chaosmesh-MCP/
uv venv
source .venv/bin/activate
uv sync
./setup-eks-permissions.sh
export KUBECONFIG=/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
uv run server.py
```

### 现在的方式 / Current Method:
```bash
# 一次性设置 / One-time setup
./setup-uvx.sh

# 之后自动运行，无需手动管理 / Automatic execution afterwards, no manual management needed
```

## 优势 / Advantages

1. **自动依赖管理 / Automatic Dependency Management**：uvx 自动处理 Python 环境和依赖包 / uvx automatically handles Python environment and dependencies
2. **版本隔离 / Version Isolation**：每次运行都是干净的环境 / Clean environment for each run
3. **简化维护 / Simplified Maintenance**：无需手动管理虚拟环境 / No need to manually manage virtual environments
4. **直接从 Git / Direct from Git**：无需本地克隆和同步 / No need for local cloning and syncing

## 故障排除 / Troubleshooting

### 检查 kubeconfig / Check kubeconfig
```bash
ls -la /home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
```

### 验证 Kubernetes 连接 / Verify Kubernetes Connection
```bash
export KUBECONFIG=/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
kubectl get pods -n chaos-mesh
```

### 重新运行设置 / Re-run Setup
```bash
./setup-uvx.sh
```

### 手动测试 uvx / Manual uvx Testing
```bash
uvx --from git+https://github.com/RadiumGu/Chaosmesh-MCP.git chaosmesh-mcp --help
```

## 环境要求 / Environment Requirements

### 必需工具 / Required Tools:
- `kubectl` - Kubernetes 命令行工具 / Kubernetes command-line tool
- `aws` - AWS CLI 工具 / AWS CLI tool
- `uvx` - Python 包执行工具 / Python package execution tool
- `helm` - Kubernetes 包管理器（用于安装 Chaos Mesh）/ Kubernetes package manager (for Chaos Mesh installation)

### 必需权限 / Required Permissions:
- EKS 集群访问权限 / EKS cluster access permissions
- 创建和管理 Kubernetes 资源的权限 / Permissions to create and manage Kubernetes resources
- AWS 区域配置 / AWS region configuration

## 文件说明 / File Description

- `setup-uvx.sh` - 环境设置脚本 / Environment setup script
- `chaos-mesh-mcp-kubeconfig` - 生成的 Kubernetes 配置文件 / Generated Kubernetes config file
- `~/.aws/amazonq/chaosmesh-env` - 环境变量配置文件 / Environment variables config file

## 注意事项 / Notes

1. 确保 EKS 集群正在运行 / Ensure EKS cluster is running
2. 确保有足够的权限安装 Chaos Mesh / Ensure sufficient permissions to install Chaos Mesh
3. 如果遇到权限问题，请检查 RBAC 配置 / Check RBAC configuration if encountering permission issues
4. Token 有效期为 24 小时，过期后需要重新运行设置脚本 / Token is valid for 24 hours, re-run setup script after expiration
