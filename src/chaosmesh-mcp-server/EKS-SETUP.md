# Chaos Mesh MCP EKS 设置指南

本文档描述了如何在 AWS EKS 环境中配置和使用 Chaos Mesh MCP 工具。

## 快速开始

### 1. 运行设置脚本

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
./setup-eks-permissions.sh
```

这个脚本会：
- 检查必要的工具（kubectl, aws cli, helm）
- 验证 EKS 集群连接
- 安装 Chaos Mesh（如果未安装）
- 应用 RBAC 配置
- 生成服务账户的 kubeconfig

### 2. 使用服务账户 kubeconfig

```bash
export KUBECONFIG=/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
```

### 3. 启动 MCP 服务器

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
python server.py --kubeconfig ./chaos-mesh-mcp-kubeconfig
```

## 新功能：命名空间支持

### 支持的命名空间操作

所有 Chaos Mesh MCP 工具现在都支持指定自定义命名空间：

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

### 新增工具

- `list_namespaces()`: 列出集群中所有可用的命名空间
- `list_services_in_namespace(namespace="default")`: 列出指定命名空间中的所有服务

### 使用示例

```python
# 列出所有命名空间
namespaces = list_namespaces()

# 列出 votingapp 命名空间中的服务
services = list_services_in_namespace("votingapp")

# 在 votingapp 命名空间中杀死 50% 的 votingapp pods
pod_kill(
    service="votingapp",
    duration="30s", 
    mode="fixed-percent",
    value="50",
    namespace="votingapp"
)

# 在 production 命名空间中对 api-service 进行 CPU 压力测试
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

# 删除 testing 命名空间中的实验
delete_experiment(
    type="POD_KILL",
    name="experiment-123",
    namespace="testing"
)
```

## 主要改进

### 1. 增强的 Kubernetes 客户端初始化
- 支持集群内和集群外配置
- 更好的错误处理和诊断信息
- 自动检测 EKS 环境

### 2. Chaos Mesh 客户端优化
- 启动时健康检查
- 重试机制和指数退避
- 详细的错误报告

### 3. RBAC 权限配置
- 专用的服务账户
- 跨命名空间权限支持
- 最小权限原则

### 4. 改进的错误处理
- 结构化日志记录
- 详细的错误信息
- 故障排除建议

### 5. 命名空间支持
- 所有工具都支持自定义命名空间
- 自动服务发现和验证
- 跨命名空间操作权限

## 故障排除

### 常见问题

1. **Kubernetes 连接失败**
   ```bash
   aws eks update-kubeconfig --region <region> --name <cluster-name>
   ```

2. **Chaos Mesh 未安装**
   ```bash
   helm repo add chaos-mesh https://charts.chaos-mesh.org
   helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace
   ```

3. **权限不足**
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

4. **命名空间不存在**
   ```bash
   # 检查命名空间是否存在
   kubectl get namespaces
   
   # 创建命名空间
   kubectl create namespace <namespace-name>
   ```

5. **服务未找到**
   ```bash
   # 列出命名空间中的服务
   kubectl get services -n <namespace>
   
   # 检查服务标签
   kubectl get pods -n <namespace> --show-labels
   ```

### 健康检查

使用内置的健康检查工具：

```python
# 在 MCP 客户端中调用
health_status = health_check()
print(health_status)
```

### 日志查看

```bash
# 查看 Chaos Mesh 控制器日志
kubectl logs -n chaos-mesh -l app.kubernetes.io/name=chaos-mesh

# 查看实验状态
kubectl get podchaos --all-namespaces
kubectl describe podchaos <experiment-name> -n <namespace>

# 查看特定命名空间的实验
kubectl get podchaos -n <namespace>
```

## 配置选项

### 环境变量

- `KUBECONFIG`: kubeconfig 文件路径
- `AWS_REGION`: AWS 区域
- `CHAOS_MESH_NAMESPACE`: Chaos Mesh 命名空间（默认：chaos-mesh）

### 命令行参数

```bash
python server.py --help
```

- `--transport`: 传输类型（默认：stdio）
- `--skip-env-check`: 跳过环境检查
- `--kubeconfig`: 指定 kubeconfig 文件路径

## 最佳实践

1. **使用服务账户**: 避免使用个人凭证
2. **最小权限**: 只授予必要的权限
3. **命名空间隔离**: 在不同环境使用不同命名空间
4. **监控实验**: 定期检查实验状态
5. **清理资源**: 及时删除完成的实验
6. **日志记录**: 启用详细日志以便故障排除

## 安全考虑

1. **网络策略**: 限制 Chaos Mesh 的网络访问
2. **资源限制**: 设置适当的资源配额
3. **审计日志**: 启用 Kubernetes 审计日志
4. **访问控制**: 使用 RBAC 限制访问权限
5. **命名空间隔离**: 使用命名空间进行环境隔离

## 支持的实验类型

- Pod 故障注入（kill, failure）
- 容器故障注入
- CPU/内存压力测试
- 网络故障（延迟、分区、带宽限制）
- 主机级别故障
- 磁盘故障

## 更新和维护

定期更新组件：

```bash
# 更新 Chaos Mesh
helm upgrade chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh

# 更新 Python 依赖
pip install --upgrade chaos-mesh kubernetes mcp
```

## 命名空间管理

### 创建新命名空间进行测试

```bash
# 创建测试命名空间
kubectl create namespace chaos-testing

# 在测试命名空间中部署应用
kubectl apply -f your-app.yaml -n chaos-testing

# 在测试命名空间中运行混沌实验
pod_kill(service="your-app", duration="30s", mode="one", value="1", namespace="chaos-testing")
```

### 跨命名空间实验管理

```bash
# 查看所有命名空间中的实验
kubectl get podchaos --all-namespaces

# 清理特定命名空间中的所有实验
kubectl delete podchaos --all -n <namespace>
```
