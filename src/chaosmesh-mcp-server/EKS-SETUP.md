# Chaos Mesh MCP EKS Setup Guide / Chaos Mesh MCP EKS 设置指南

This document describes how to configure and use Chaos Mesh MCP tools in AWS EKS environments. / 本文档描述了如何在 AWS EKS 环境中配置和使用 Chaos Mesh MCP 工具。

## Quick Start / 快速开始

### 1. Run Setup Script / 运行设置脚本

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
./setup-eks-permissions.sh
```

This script will: / 这个脚本会：
- Check necessary tools (kubectl, aws cli, helm) / 检查必要的工具（kubectl, aws cli, helm）
- Verify EKS cluster connection / 验证 EKS 集群连接
- Install Chaos Mesh (if not installed) / 安装 Chaos Mesh（如果未安装）
- Apply RBAC configuration / 应用 RBAC 配置
- Generate service account kubeconfig / 生成服务账户的 kubeconfig

### 2. Use Service Account kubeconfig / 使用服务账户 kubeconfig

```bash
export KUBECONFIG=/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
```

### 3. Start MCP Server / 启动 MCP 服务器

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
python server.py --kubeconfig ./chaos-mesh-mcp-kubeconfig
```

## New Feature: Namespace Support / 新功能：命名空间支持

### Supported Namespace Operations / 支持的命名空间操作

All Chaos Mesh MCP tools now support specifying custom namespaces: / 所有 Chaos Mesh MCP 工具现在都支持指定自定义命名空间：

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

### New Tools / 新增工具

- `list_namespaces()`: List all available namespaces in the cluster / 列出集群中所有可用的命名空间
- `list_services_in_namespace(namespace="default")`: List all services in a specified namespace / 列出指定命名空间中的所有服务

### Usage Examples / 使用示例

```python
# List all namespaces / 列出所有命名空间
namespaces = list_namespaces()

# List services in votingapp namespace / 列出 votingapp 命名空间中的服务
services = list_services_in_namespace("votingapp")

# Kill 50% of votingapp pods in votingapp namespace / 在 votingapp 命名空间中杀死 50% 的 votingapp pods
pod_kill(
    service="votingapp",
    duration="30s", 
    mode="fixed-percent",
    value="50",
    namespace="votingapp"
)

# Apply CPU stress in production namespace / 在 production 命名空间中对 api-service 进行 CPU 压力测试
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

# Delete experiment in testing namespace / 删除 testing 命名空间中的实验
delete_experiment(
    type="POD_KILL",
    name="experiment-123",
    namespace="testing"
)
```

## Key Improvements / 主要改进

### 1. Enhanced Kubernetes Client Initialization / 增强的 Kubernetes 客户端初始化
- Support for in-cluster and out-of-cluster configuration / 支持集群内和集群外配置
- Better error handling and diagnostic information / 更好的错误处理和诊断信息
- Automatic EKS environment detection / 自动检测 EKS 环境

### 2. Chaos Mesh Client Optimization / Chaos Mesh 客户端优化
- Health checks on startup / 启动时健康检查
- Retry mechanisms and exponential backoff / 重试机制和指数退避
- Detailed error reporting / 详细的错误报告

### 3. RBAC Permission Configuration / RBAC 权限配置
- Dedicated service account / 专用的服务账户
- Cross-namespace permission support / 跨命名空间权限支持
- Principle of least privilege / 最小权限原则

### 4. Improved Error Handling / 改进的错误处理
- Structured logging / 结构化日志记录
- Detailed error messages / 详细的错误信息
- Troubleshooting suggestions / 故障排除建议

### 5. Namespace Support / 命名空间支持
- All tools support custom namespaces / 所有工具都支持自定义命名空间
- Automatic service discovery and validation / 自动服务发现和验证
- Cross-namespace operation permissions / 跨命名空间操作权限

## Troubleshooting / 故障排除

### Common Issues / 常见问题

1. **Kubernetes Connection Failed / Kubernetes 连接失败**
   ```bash
   aws eks update-kubeconfig --region <region> --name <cluster-name>
   ```

2. **Chaos Mesh Not Installed / Chaos Mesh 未安装**
   ```bash
   helm repo add chaos-mesh https://charts.chaos-mesh.org
   helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace
   ```

3. **Insufficient Permissions / 权限不足**
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

4. **Namespace Does Not Exist / 命名空间不存在**
   ```bash
   # Check if namespace exists / 检查命名空间是否存在
   kubectl get namespaces
   
   # Create namespace / 创建命名空间
   kubectl create namespace <namespace-name>
   ```

5. **Service Not Found / 服务未找到**
   ```bash
   # List services in namespace / 列出命名空间中的服务
   kubectl get services -n <namespace>
   
   # Check service labels / 检查服务标签
   kubectl get pods -n <namespace> --show-labels
   ```

### Health Check / 健康检查

Use the built-in health check tool: / 使用内置的健康检查工具：

```python
# Call in MCP client / 在 MCP 客户端中调用
health_status = health_check()
print(health_status)
```

### View Logs / 日志查看

```bash
# View Chaos Mesh controller logs / 查看 Chaos Mesh 控制器日志
kubectl logs -n chaos-mesh -l app.kubernetes.io/name=chaos-mesh

# View experiment status / 查看实验状态
kubectl get podchaos --all-namespaces
kubectl describe podchaos <experiment-name> -n <namespace>

# View experiments in specific namespace / 查看特定命名空间的实验
kubectl get podchaos -n <namespace>
```

## Configuration Options / 配置选项

### Environment Variables / 环境变量

- `KUBECONFIG`: kubeconfig file path / kubeconfig 文件路径
- `AWS_REGION`: AWS region / AWS 区域
- `CHAOS_MESH_NAMESPACE`: Chaos Mesh namespace (default: chaos-mesh) / Chaos Mesh 命名空间（默认：chaos-mesh）

### Command Line Arguments / 命令行参数

```bash
python server.py --help
```

- `--transport`: Transport type (default: stdio) / 传输类型（默认：stdio）
- `--skip-env-check`: Skip environment check / 跳过环境检查
- `--kubeconfig`: Specify kubeconfig file path / 指定 kubeconfig 文件路径

## Best Practices / 最佳实践

1. **Use service accounts / 使用服务账户**: Avoid using personal credentials / 避免使用个人凭证
2. **Minimal permissions / 最小权限**: Only grant necessary permissions / 只授予必要的权限
3. **Namespace isolation / 命名空间隔离**: Use different namespaces for different environments / 在不同环境使用不同命名空间
4. **Monitor experiments / 监控实验**: Regularly check experiment status / 定期检查实验状态
5. **Clean up resources / 清理资源**: Delete completed experiments promptly / 及时删除完成的实验
6. **Detailed logging / 日志记录**: Enable verbose logging for troubleshooting / 启用详细日志以便故障排除

## Security Considerations / 安全考虑

1. **Network policies / 网络策略**: Limit Chaos Mesh network access / 限制 Chaos Mesh 的网络访问
2. **Resource limits / 资源限制**: Set appropriate resource quotas / 设置适当的资源配额
3. **Audit logging / 审计日志**: Enable Kubernetes audit logging / 启用 Kubernetes 审计日志
4. **Access control / 访问控制**: Use RBAC to limit access permissions / 使用 RBAC 限制访问权限
5. **Namespace isolation / 命名空间隔离**: Use namespaces for environment isolation / 使用命名空间进行环境隔离

## Supported Experiment Types / 支持的实验类型

- Pod fault injection (kill, failure) / Pod 故障注入（kill, failure）
- Container fault injection / 容器故障注入
- CPU/memory stress testing / CPU/内存压力测试
- Network faults (delay, partition, bandwidth limits) / 网络故障（延迟、分区、带宽限制）
- Host-level faults / 主机级别故障
- Disk faults / 磁盘故障

## Updates and Maintenance / 更新和维护

Regularly update components: / 定期更新组件：

```bash
# Update Chaos Mesh / 更新 Chaos Mesh
helm upgrade chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh

# Update Python dependencies / 更新 Python 依赖
pip install --upgrade chaos-mesh kubernetes mcp
```

## Namespace Management / 命名空间管理

### Create New Namespace for Testing / 创建新命名空间进行测试

```bash
# Create testing namespace / 创建测试命名空间
kubectl create namespace chaos-testing

# Deploy application in testing namespace / 在测试命名空间中部署应用
kubectl apply -f your-app.yaml -n chaos-testing

# Run chaos experiments in testing namespace / 在测试命名空间中运行混沌实验
pod_kill(service="your-app", duration="30s", mode="one", value="1", namespace="chaos-testing")
```

### Cross-namespace Experiment Management / 跨命名空间实验管理

```bash
# View experiments in all namespaces / 查看所有命名空间中的实验
kubectl get podchaos --all-namespaces

# Clean up all experiments in specific namespace / 清理特定命名空间中的所有实验
kubectl delete podchaos --all -n <namespace>
```
