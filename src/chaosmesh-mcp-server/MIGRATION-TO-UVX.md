# Migration to uvx for Running Chaos Mesh MCP / 迁移到 uvx 方式运行 Chaos Mesh MCP

This document describes how to migrate Chaos Mesh MCP from local `uv run` method to `uvx` method. / 本文档描述如何将 Chaos Mesh MCP 从本地 `uv run` 方式迁移到 `uvx` 方式。

## Current Method vs uvx Method / 当前方式 vs uvx 方式

### Current Method / 当前方式
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

### uvx Method / uvx 方式
```bash
# One-time setup / 一次性设置
./setup-uvx.sh

# After that, uvx will automatically handle dependencies and execution
# 之后 uvx 会自动处理依赖和运行
```

## Migration Steps / 迁移步骤

### 1. Run Environment Setup Script / 运行环境设置脚本

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
./setup-uvx.sh
```

This script will: / 这个脚本会：
- Run the original `setup-eks-permissions.sh` / 运行原始的 `setup-eks-permissions.sh`
- Generate necessary kubeconfig files / 生成必要的 kubeconfig 文件
- Create environment configuration files / 创建环境配置文件

### 2. Update MCP Configuration / 更新 MCP 配置

Your `chaosmesh-mcp` configuration in `~/.aws/amazonq/mcp.json` has been updated to: / 你的 `~/.aws/amazonq/mcp.json` 中的 `chaosmesh-mcp` 配置已经更新为：

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

### 3. Test New Configuration / 测试新配置

Restart Amazon Q CLI to test the new configuration: / 重启 Amazon Q CLI 来测试新配置：

```bash
# Exit current Q session / 退出当前 Q 会话
/quit

# Restart / 重新启动
q chat
```

## Advantages / 优势

### uvx Method Advantages / uvx 方式的优势：
1. **Automatic dependency management / 自动依赖管理**: uvx automatically handles Python environment and dependencies / uvx 自动处理 Python 环境和依赖
2. **No need for local cloning / 无需本地克隆**: Run directly from Git repository / 直接从 Git 仓库运行
3. **Version isolation / 版本隔离**: Clean environment for each run / 每次运行都是干净的环境
4. **Simplified maintenance / 简化维护**: No need to manually manage virtual environments / 无需手动管理虚拟环境

### Retained Necessary Steps / 保留的必要步骤：
1. **EKS permission setup / EKS 权限设置**: Still need to run `setup-eks-permissions.sh` to configure Kubernetes permissions / 仍需要运行 `setup-eks-permissions.sh` 来配置 Kubernetes 权限
2. **Kubeconfig generation / Kubeconfig 生成**: Need to generate dedicated service account kubeconfig / 需要生成专用的 service account kubeconfig
3. **Chaos Mesh installation / Chaos Mesh 安装**: Ensure Chaos Mesh is properly installed in the cluster / 确保 Chaos Mesh 在集群中正确安装

## Environment Dependencies / 环境依赖

### Still Required Environment Setup / 仍然需要的环境设置：
- **Kubeconfig file / Kubeconfig 文件**: `/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig`
- **AWS configuration / AWS 配置**: AWS CLI configuration and region settings / AWS CLI 配置和区域设置
- **Kubernetes access / Kubernetes 访问**: EKS cluster access permissions / EKS 集群访问权限
- **Chaos Mesh**: Chaos Mesh installed in the cluster / 集群中安装的 Chaos Mesh

### Automated Parts / 自动化的部分：
- Python environment management / Python 环境管理
- Dependency package installation / 依赖包安装
- Code fetching and updates / 代码获取和更新

## Troubleshooting / 故障排除

### If uvx Method Fails / 如果 uvx 方式失败：
1. Check if kubeconfig file exists / 检查 kubeconfig 文件是否存在：
   ```bash
   ls -la /home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
   ```

2. Verify Kubernetes connection / 验证 Kubernetes 连接：
   ```bash
   export KUBECONFIG=/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
   kubectl get pods -n chaos-mesh
   ```

3. Re-run setup script / 重新运行设置脚本：
   ```bash
   ./setup-uvx.sh
   ```

### Rollback to Original Method / 回退到原方式：
If you need to rollback, you can change the configuration in mcp.json back to: / 如果需要回退，可以将 mcp.json 中的配置改回：

```json
"chaosmesh-mcp": {
  "command": "uv",
  "args": [
    "--directory",
    "/home/ec2-user/mcp-servers/Chaosmesh-MCP",
    "run",
    "python",
    "server.py",
    "--kubeconfig",
    "./chaos-mesh-mcp-kubeconfig",
    "--skip-env-check",
    "--transport",
    "stdio"
  ],
  "env": {
    "AWS_REGION": "us-east-2"
  },
  "autoApprove": [],
  "disabled": false,
  "transportType": "stdio"
}
```

## Summary / 总结

The uvx method simplifies dependency management, but environment setup (EKS permissions, Kubeconfig, Chaos Mesh) is still a necessary one-time step. This hybrid approach combines the convenience of uvx with necessary environment configuration. / uvx 方式简化了依赖管理，但环境设置（EKS 权限、Kubeconfig、Chaos Mesh）仍然是必需的一次性步骤。这种混合方式结合了 uvx 的便利性和必要的环境配置。
