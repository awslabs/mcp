# 迁移到 uvx 方式运行 Chaos Mesh MCP

本文档描述如何将 Chaos Mesh MCP 从本地 `uv run` 方式迁移到 `uvx` 方式。

## 当前方式 vs uvx 方式

### 当前方式
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

### uvx 方式
```bash
# 一次性设置
./setup-uvx.sh

# 之后 uvx 会自动处理依赖和运行
```

## 迁移步骤

### 1. 运行环境设置脚本

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
./setup-uvx.sh
```

这个脚本会：
- 运行原始的 `setup-eks-permissions.sh`
- 生成必要的 kubeconfig 文件
- 创建环境配置文件

### 2. 更新 MCP 配置

你的 `~/.aws/amazonq/mcp.json` 中的 `chaosmesh-mcp` 配置已经更新为：

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

### 3. 测试新配置

重启 Amazon Q CLI 来测试新配置：

```bash
# 退出当前 Q 会话
/quit

# 重新启动
q chat
```

## 优势

### uvx 方式的优势：
1. **自动依赖管理**：uvx 自动处理 Python 环境和依赖
2. **无需本地克隆**：直接从 Git 仓库运行
3. **版本隔离**：每次运行都是干净的环境
4. **简化维护**：无需手动管理虚拟环境

### 保留的必要步骤：
1. **EKS 权限设置**：仍需要运行 `setup-eks-permissions.sh` 来配置 Kubernetes 权限
2. **Kubeconfig 生成**：需要生成专用的 service account kubeconfig
3. **Chaos Mesh 安装**：确保 Chaos Mesh 在集群中正确安装

## 环境依赖

### 仍然需要的环境设置：
- **Kubeconfig 文件**：`/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig`
- **AWS 配置**：AWS CLI 配置和区域设置
- **Kubernetes 访问**：EKS 集群访问权限
- **Chaos Mesh**：集群中安装的 Chaos Mesh

### 自动化的部分：
- Python 环境管理
- 依赖包安装
- 代码获取和更新

## 故障排除

### 如果 uvx 方式失败：
1. 检查 kubeconfig 文件是否存在：
   ```bash
   ls -la /home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
   ```

2. 验证 Kubernetes 连接：
   ```bash
   export KUBECONFIG=/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig
   kubectl get pods -n chaos-mesh
   ```

3. 重新运行设置脚本：
   ```bash
   ./setup-uvx.sh
   ```

### 回退到原方式：
如果需要回退，可以将 mcp.json 中的配置改回：

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

## 总结

uvx 方式简化了依赖管理，但环境设置（EKS 权限、Kubeconfig、Chaos Mesh）仍然是必需的一次性步骤。这种混合方式结合了 uvx 的便利性和必要的环境配置。
