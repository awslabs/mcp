# Chaos Mesh MCP Server / Chaos Mesh MCP 服务器

A Model Context Protocol (MCP) server for Chaos Mesh fault injection, optimized for AWS EKS environments with full namespace support.

一个用于 Chaos Mesh 故障注入的模型上下文协议（MCP）服务器，针对 AWS EKS 环境进行了优化，支持完整的命名空间功能。

## Features / 功能特性

- **Pod Fault Injection / Pod 故障注入**: Kill pods, inject failures, stress CPU/memory / 杀死 Pod、注入故障、CPU/内存压力测试
- **Network Chaos / 网络混沌**: Simulate network delays, partitions, bandwidth limits / 模拟网络延迟、分区、带宽限制
- **Host-level Chaos / 主机级混沌**: CPU/memory stress, disk operations on nodes / 节点上的 CPU/内存压力、磁盘操作
- **EKS Optimized / EKS 优化**: Enhanced support for AWS EKS with proper RBAC and authentication / 增强的 AWS EKS 支持，具有适当的 RBAC 和身份验证
- **Namespace Support / 命名空间支持**: All tools support custom namespaces / 所有工具都支持自定义命名空间
- **Improved Error Handling / 改进的错误处理**: Detailed error messages and retry mechanisms / 详细的错误消息和重试机制
- **Health Monitoring / 健康监控**: Built-in health checks and diagnostics / 内置健康检查和诊断
- **uvx Integration / uvx 集成**: Simplified installation and dependency management with uvx / 使用 uvx 简化安装和依赖管理

## Quick Start with uvx (Recommended) / 使用 uvx 快速开始（推荐）

### 1. One-time Environment Setup / 一次性环境设置

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP

# Run the uvx setup script (includes EKS permissions and kubeconfig generation)
# 运行 uvx 设置脚本（包括 EKS 权限和 kubeconfig 生成）
./setup-uvx.sh
```

This script will: / 此脚本将：
- Install Chaos Mesh (if not present) / 安装 Chaos Mesh（如果不存在）
- Create necessary RBAC permissions / 创建必要的 RBAC 权限
- Generate `chaos-mesh-mcp-kubeconfig` file with service account credentials / 生成带有服务账户凭据的 `chaos-mesh-mcp-kubeconfig` 文件
- Create environment configuration for uvx / 为 uvx 创建环境配置
- Verify the setup / 验证设置

### 2. MCP Configuration / MCP 配置

Add to your `~/.aws/amazonq/mcp.json`: / 添加到您的 `~/.aws/amazonq/mcp.json`：

```json
{
  "mcpServers": {
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
  }
}
```

### 3. Start Using / 开始使用

Restart your Amazon Q CLI session: / 重启您的 Amazon Q CLI 会话：

```bash
# Exit current session / 退出当前会话
/quit

# Restart / 重新启动
q chat
```

The MCP server will now run automatically via uvx when needed! / MCP 服务器现在将在需要时通过 uvx 自动运行！

## Alternative: Manual Setup (Legacy) / 替代方案：手动设置（传统方式）

If you prefer the traditional approach or need to troubleshoot: / 如果您喜欢传统方法或需要故障排除：

### 1. Clone and Setup Environment / 克隆并设置环境

```bash
git clone https://github.com/RadiumGu/Chaosmesh-MCP.git
cd Chaosmesh-MCP/
uv venv
source .venv/bin/activate
uv sync
```

### 2. Generate Kubeconfig / 生成 Kubeconfig

```bash
# Make the setup script executable / 使设置脚本可执行
chmod +x setup-eks-permissions.sh

# Run the setup script to generate kubeconfig and configure permissions
# 运行设置脚本以生成 kubeconfig 并配置权限
./setup-eks-permissions.sh
```

### 3. Start MCP Server / 启动 MCP 服务器

```bash
# Use the generated kubeconfig / 使用生成的 kubeconfig
export KUBECONFIG=./chaos-mesh-mcp-kubeconfig
uv run python server.py --kubeconfig ./chaos-mesh-mcp-kubeconfig
```

## uvx vs Manual Installation / uvx 与手动安装对比

### uvx Advantages (Recommended) / uvx 优势（推荐）:
- ✅ **Automatic dependency management / 自动依赖管理**: No need to manage Python environments / 无需管理 Python 环境
- ✅ **Direct from Git / 直接从 Git**: Always uses latest version from repository / 始终使用仓库的最新版本
- ✅ **Version isolation / 版本隔离**: Clean environment for each run / 每次运行都是干净的环境
- ✅ **Simplified maintenance / 简化维护**: No manual virtual environment management / 无需手动虚拟环境管理
- ✅ **One-time setup / 一次性设置**: Just run `./setup-uvx.sh` once / 只需运行一次 `./setup-uvx.sh`

### Manual Installation / 手动安装:
- ⚠️ Requires manual dependency management / 需要手动依赖管理
- ⚠️ Need to sync repository updates manually / 需要手动同步仓库更新
- ⚠️ Virtual environment maintenance required / 需要虚拟环境维护
- ✅ More control over the environment / 对环境有更多控制
- ✅ Easier for development and debugging / 更容易进行开发和调试

## Troubleshooting Setup / 设置故障排除

If you encounter issues: / 如果遇到问题：

1. **Missing kubeconfig file / 缺少 kubeconfig 文件**: Run `./setup-uvx.sh` or `./setup-eks-permissions.sh` / 运行 `./setup-uvx.sh` 或 `./setup-eks-permissions.sh`
2. **Permission errors / 权限错误**: Ensure your AWS credentials have EKS access / 确保您的 AWS 凭据具有 EKS 访问权限
3. **Connection issues / 连接问题**: Verify kubectl can access your cluster / 验证 kubectl 可以访问您的集群
4. **uvx issues / uvx 问题**: Check if uvx is installed: `uvx --version` / 检查是否安装了 uvx：`uvx --version`

For detailed setup instructions, see [SETUP.md](SETUP.md) and [UVX-USAGE.md](UVX-USAGE.md). / 有关详细的设置说明，请参阅 [SETUP.md](SETUP.md) 和 [UVX-USAGE.md](UVX-USAGE.md)。

## Namespace Support / 命名空间支持

All Chaos Mesh MCP tools now support specifying custom namespaces: / 所有 Chaos Mesh MCP 工具现在都支持指定自定义命名空间：

### Available Tools with Namespace Support / 支持命名空间的可用工具

- `pod_kill(service, duration, mode, value, namespace="default")`
- `pod_failure(service, duration, mode, value, namespace="default")`
- `pod_cpu_stress(service, duration, mode, value, container_names, workers, load, namespace="default")`
- `pod_memory_stress(service, duration, mode, value, container_names, size, time, namespace="default")`
- `container_kill(service, duration, mode, value, container_names, namespace="default")`
- `network_partition(service, mode, value, direction, external_targets, namespace="default")`
- `network_bandwidth(service, mode, value, direction, rate, limit, buffer, external_targets, namespace="default")`
- `delete_experiment(type, name, namespace="default")`
- `inject_delay_fault(service, delay, namespace="default")`
- `remove_delay_fault(service, namespace="default")`

### New Namespace Management Tools / 新的命名空间管理工具

- `list_namespaces()`: List all available namespaces / 列出所有可用的命名空间
- `list_services_in_namespace(namespace="default")`: List services in a specific namespace / 列出特定命名空间中的服务
- `health_check()`: Check system health / 检查系统健康状况

### Example Usage / 使用示例

```python
# List all namespaces / 列出所有命名空间
namespaces = list_namespaces()

# List services in votingapp namespace / 列出 votingapp 命名空间中的服务
services = list_services_in_namespace("votingapp")

# Kill 50% of votingapp pods in votingapp namespace for 30 seconds
# 在 votingapp 命名空间中杀死 50% 的 votingapp pods，持续 30 秒
pod_kill(
    service="votingapp",
    duration="30s", 
    mode="fixed-percent",
    value="50",
    namespace="votingapp"
)

# Apply CPU stress in production namespace
# 在 production 命名空间中应用 CPU 压力
pod_cpu_stress(
    service="api-service",
    duration="2m",
    mode="fixed",
    value="2",
    container_names=["api"],
    workers=2,
    load=80,
    namespace="production"
)

# Check system health / 检查系统健康状况
health_status = health_check()
```

## Installation / 安装

### Prerequisites / 先决条件

- **uvx**: Python package runner (recommended) / Python 包运行器（推荐）
- **kubectl**: Configured for your cluster / 为您的集群配置
- **Helm**: For Chaos Mesh installation / 用于 Chaos Mesh 安装
- **AWS CLI**: For EKS environments / 用于 EKS 环境
- **Python 3.10+**: Required by uvx / uvx 所需

### uvx Installation (Recommended) / uvx 安装（推荐）

```bash
# Install uvx if not already installed / 如果尚未安装，请安装 uvx
pip install uvx

# Run one-time setup / 运行一次性设置
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
./setup-uvx.sh
```

uvx will automatically handle all Python dependencies: / uvx 将自动处理所有 Python 依赖项：
- `chaos-mesh>=1.2.13`
- `kubernetes>=32.0.1` 
- `mcp[cli]>=1.7.1`

### Manual Installation (Alternative) / 手动安装（替代方案）

```bash
# Clone repository / 克隆仓库
git clone https://github.com/RadiumGu/Chaosmesh-MCP.git
cd Chaosmesh-MCP/

# Setup Python environment / 设置 Python 环境
uv venv
source .venv/bin/activate
uv sync

# Install dependencies manually / 手动安装依赖项
pip install chaos-mesh>=1.2.13 kubernetes>=32.0.1 mcp[cli]>=1.7.1
```

## Configuration / 配置

### uvx Configuration (Recommended) / uvx 配置（推荐）

For uvx-based deployment, use the automated setup: / 对于基于 uvx 的部署，使用自动化设置：

```bash
./setup-uvx.sh
```

This script will: / 此脚本将：
- Install Chaos Mesh if not present / 如果不存在则安装 Chaos Mesh
- Create necessary RBAC permissions with cross-namespace support / 创建具有跨命名空间支持的必要 RBAC 权限
- Generate a service account kubeconfig / 生成服务账户 kubeconfig
- Create environment configuration for uvx / 为 uvx 创建环境配置
- Verify the setup / 验证设置

### EKS Environment (Manual) / EKS 环境（手动）

For manual AWS EKS cluster setup: / 对于手动 AWS EKS 集群设置：

```bash
./setup-eks-permissions.sh
```

This script will: / 此脚本将：
- Install Chaos Mesh if not present / 如果不存在则安装 Chaos Mesh
- Create necessary RBAC permissions with cross-namespace support / 创建具有跨命名空间支持的必要 RBAC 权限
- Generate a service account kubeconfig / 生成服务账户 kubeconfig
- Verify the setup / 验证设置

### Manual Configuration / 手动配置

1. **Install Chaos Mesh / 安装 Chaos Mesh**:
   ```bash
   helm repo add chaos-mesh https://charts.chaos-mesh.org
   helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace
   ```

2. **Apply RBAC / 应用 RBAC**:
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

## Troubleshooting / 故障排除

### Common Issues / 常见问题

1. **uvx Command Not Found / 找不到 uvx 命令**:
   ```bash
   pip install uvx
   ```

2. **Connection Timeouts / 连接超时**: 
   - Check Chaos Mesh installation / 检查 Chaos Mesh 安装
   - Verify RBAC permissions / 验证 RBAC 权限
   - Use `health_check()` tool / 使用 `health_check()` 工具

3. **Permission Denied / 权限被拒绝**:
   - Apply RBAC configuration / 应用 RBAC 配置
   - Use service account kubeconfig / 使用服务账户 kubeconfig
   - Re-run `./setup-uvx.sh` / 重新运行 `./setup-uvx.sh`

4. **Service Not Found / 找不到服务**:
   - Verify service name and namespace / 验证服务名称和命名空间
   - Use `list_services_in_namespace()` to check available services / 使用 `list_services_in_namespace()` 检查可用服务
   - Check label selectors / 检查标签选择器

5. **Namespace Issues / 命名空间问题**:
   - Use `list_namespaces()` to see available namespaces / 使用 `list_namespaces()` 查看可用命名空间
   - Ensure namespace exists before running experiments / 确保在运行实验之前命名空间存在

6. **uvx Installation Issues / uvx 安装问题**:
   - Check if kubeconfig exists / 检查 kubeconfig 是否存在: `ls -la /home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig`
   - Verify Kubernetes connection / 验证 Kubernetes 连接: `kubectl get pods -n chaos-mesh`
   - Re-run setup / 重新运行设置: `./setup-uvx.sh`

### Debug Mode / 调试模式

For uvx (automatic via MCP configuration) / 对于 uvx（通过 MCP 配置自动）:
```json
"env": {
  "KUBECONFIG": "/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig",
  "AWS_REGION": "us-east-2",
  "DEBUG": "true"
}
```

For manual mode / 对于手动模式:
```bash
python server.py --skip-env-check --kubeconfig ./chaos-mesh-mcp-kubeconfig
```

### Logs / 日志

Check Chaos Mesh controller logs / 检查 Chaos Mesh 控制器日志:
```bash
kubectl logs -n chaos-mesh -l app.kubernetes.io/name=chaos-mesh
```

Check experiments across namespaces / 检查跨命名空间的实验:
```bash
kubectl get podchaos --all-namespaces
```

### Migration from Manual to uvx / 从手动迁移到 uvx

If migrating from manual installation, see [MIGRATION-TO-UVX.md](MIGRATION-TO-UVX.md) for detailed instructions. / 如果从手动安装迁移，请参阅 [MIGRATION-TO-UVX.md](MIGRATION-TO-UVX.md) 获取详细说明。

## Architecture / 架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │────│  Chaos Mesh MCP │────│   Kubernetes    │
│   MCP 客户端     │    │     Server       │    │    Cluster      │
│                 │    │   MCP 服务器      │    │   Kubernetes    │
│                 │    │                  │    │     集群        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                       ┌──────────────────┐
                       │   Chaos Mesh     │
                       │   Controllers    │
                       │  Chaos Mesh      │
                       │    控制器        │
                       └──────────────────┘
```

## Security / 安全性

- Uses dedicated service account with minimal permissions / 使用具有最小权限的专用服务账户
- Supports cross-namespace operations with proper RBAC / 支持具有适当 RBAC 的跨命名空间操作
- Token-based authentication for EKS / EKS 的基于令牌的身份验证
- Namespace isolation support / 命名空间隔离支持
- Audit logging support / 审计日志支持

## Best Practices / 最佳实践

1. **Use service accounts / 使用服务账户**: Avoid using personal credentials / 避免使用个人凭据
2. **Namespace isolation / 命名空间隔离**: Use different namespaces for different environments / 为不同环境使用不同的命名空间
3. **Monitor experiments / 监控实验**: Regularly check experiment status across namespaces / 定期检查跨命名空间的实验状态
4. **Clean up resources / 清理资源**: Delete completed experiments promptly / 及时删除已完成的实验
5. **Detailed logging / 详细日志**: Enable verbose logging for troubleshooting / 启用详细日志以进行故障排除

## Contributing / 贡献

1. Fork the repository / 分叉仓库
2. Create a feature branch / 创建功能分支
3. Make your changes / 进行更改
4. Test in EKS environment with multiple namespaces / 在具有多个命名空间的 EKS 环境中测试
5. Submit a pull request / 提交拉取请求

## License / 许可证

This project is licensed under the MIT License. / 此项目根据 MIT 许可证授权。

## Support / 支持

For issues and questions / 对于问题和疑问:
1. Check the troubleshooting section above / 检查上面的故障排除部分
2. Review logs and health status / 查看日志和健康状态
3. Consult the documentation / 查阅文档:
   - [EKS Setup Guide / EKS 设置指南](EKS-SETUP.md)
   - [General Setup Guide / 通用设置指南](SETUP.md)
   - [uvx Usage Guide / uvx 使用指南](UVX-USAGE.md)
   - [Migration Guide / 迁移指南](MIGRATION-TO-UVX.md)
4. Use namespace management tools for debugging / 使用命名空间管理工具进行调试
5. Check the [GitHub Issues](https://github.com/RadiumGu/Chaosmesh-MCP/issues) page / 查看 [GitHub Issues](https://github.com/RadiumGu/Chaosmesh-MCP/issues) 页面

## Documentation / 文档

- **[README.md](README.md)** - This file, main documentation / 此文件，主要文档
- **[SETUP.md](SETUP.md)** - Detailed setup instructions / 详细设置说明
- **[EKS-SETUP.md](EKS-SETUP.md)** - EKS-specific setup guide / EKS 特定设置指南
- **[UVX-USAGE.md](UVX-USAGE.md)** - uvx installation and usage guide / uvx 安装和使用指南
- **[MIGRATION-TO-UVX.md](MIGRATION-TO-UVX.md)** - Migration from manual to uvx / 从手动迁移到 uvx
