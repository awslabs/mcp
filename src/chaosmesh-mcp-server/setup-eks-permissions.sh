#!/bin/bash

# EKS环境下Chaos Mesh MCP权限设置脚本

set -e

echo "=== EKS Chaos Mesh MCP Setup Script ==="

# 检查必要的工具
check_tools() {
    echo "Checking required tools..."
    
    if ! command -v kubectl &> /dev/null; then
        echo "ERROR: kubectl is not installed"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        echo "ERROR: AWS CLI is not installed"
        exit 1
    fi
    
    echo "✓ Required tools are available"
}

# 检查EKS连接
check_eks_connection() {
    echo "Checking EKS connection..."
    
    if ! kubectl cluster-info &> /dev/null; then
        echo "ERROR: Cannot connect to Kubernetes cluster"
        echo "Please run: aws eks update-kubeconfig --region <region> --name <cluster-name>"
        exit 1
    fi
    
    CLUSTER_NAME=$(kubectl config current-context | cut -d'/' -f2 2>/dev/null || echo "unknown")
    echo "✓ Connected to cluster: $CLUSTER_NAME"
}

# 检查Chaos Mesh安装
check_chaos_mesh() {
    echo "Checking Chaos Mesh installation..."
    
    if ! kubectl get namespace chaos-mesh &> /dev/null; then
        echo "WARNING: Chaos Mesh namespace not found"
        echo "Installing Chaos Mesh..."
        
        # 检查helm是否安装
        if ! command -v helm &> /dev/null; then
            echo "ERROR: helm is not installed. Please install helm first."
            exit 1
        fi
        
        # 添加Chaos Mesh Helm仓库
        helm repo add chaos-mesh https://charts.chaos-mesh.org
        helm repo update
        
        # 安装Chaos Mesh
        helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace \
            --set chaosDaemon.runtime=containerd \
            --set chaosDaemon.socketPath=/run/containerd/containerd.sock
        
        echo "Waiting for Chaos Mesh to be ready..."
        kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=chaos-mesh -n chaos-mesh --timeout=300s
    else
        echo "✓ Chaos Mesh namespace exists"
    fi
    
    # 检查Chaos Mesh控制器状态
    RUNNING_CONTROLLERS=$(kubectl get pods -n chaos-mesh -l app.kubernetes.io/name=chaos-mesh --field-selector=status.phase=Running --no-headers | wc -l)
    if [ "$RUNNING_CONTROLLERS" -eq 0 ]; then
        echo "ERROR: No running Chaos Mesh controllers found"
        exit 1
    fi
    
    echo "✓ Found $RUNNING_CONTROLLERS running Chaos Mesh controllers"
}

# 应用RBAC配置
apply_rbac() {
    echo "Applying RBAC configuration..."
    
    # 检查是否已存在
    if kubectl get serviceaccount chaos-mesh-mcp -n default &> /dev/null; then
        echo "ServiceAccount already exists, updating..."
    fi
    
    # 应用RBAC配置
    kubectl apply -f "$(dirname "$0")/rbac-config.yaml"
    
    echo "✓ RBAC configuration applied"
}

# 验证权限
verify_permissions() {
    echo "Verifying permissions..."
    
    # 测试基本权限
    if kubectl auth can-i get pods --as=system:serviceaccount:default:chaos-mesh-mcp; then
        echo "✓ Pod read permissions OK"
    else
        echo "ERROR: Pod read permissions failed"
        exit 1
    fi
    
    if kubectl auth can-i create podchaos.chaos-mesh.org --as=system:serviceaccount:default:chaos-mesh-mcp; then
        echo "✓ Chaos Mesh CRD permissions OK"
    else
        echo "ERROR: Chaos Mesh CRD permissions failed"
        exit 1
    fi
    
    echo "✓ Permissions verified successfully"
}

# 生成kubeconfig for service account
generate_kubeconfig() {
    echo "Generating kubeconfig for service account..."
    
    # 获取服务账户的token
    SECRET_NAME=$(kubectl get serviceaccount chaos-mesh-mcp -n default -o jsonpath='{.secrets[0].name}' 2>/dev/null || echo "")
    
    if [ -z "$SECRET_NAME" ]; then
        # Kubernetes 1.24+ 需要手动创建token
        kubectl create token chaos-mesh-mcp -n default --duration=8760h > "$(dirname "$0")/chaos-mesh-mcp-token"
        TOKEN=$(cat "$(dirname "$0")/chaos-mesh-mcp-token")
    else
        TOKEN=$(kubectl get secret $SECRET_NAME -n default -o jsonpath='{.data.token}' | base64 -d)
    fi
    
    # 获取集群信息
    CLUSTER_NAME=$(kubectl config current-context)
    CLUSTER_SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
    CLUSTER_CA=$(kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
    
    # 生成kubeconfig
    cat > "$(dirname "$0")/chaos-mesh-mcp-kubeconfig" << EOF
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: $CLUSTER_CA
    server: $CLUSTER_SERVER
  name: $CLUSTER_NAME
contexts:
- context:
    cluster: $CLUSTER_NAME
    user: chaos-mesh-mcp
  name: chaos-mesh-mcp-context
current-context: chaos-mesh-mcp-context
users:
- name: chaos-mesh-mcp
  user:
    token: $TOKEN
EOF
    
    echo "✓ Kubeconfig generated at $(dirname "$0")/chaos-mesh-mcp-kubeconfig"
    echo "You can use this kubeconfig by setting: export KUBECONFIG=$(dirname "$0")/chaos-mesh-mcp-kubeconfig"
}

# 主函数
main() {
    check_tools
    check_eks_connection
    check_chaos_mesh
    apply_rbac
    verify_permissions
    generate_kubeconfig
    
    echo ""
    echo "=== Setup Complete ==="
    echo "Chaos Mesh MCP is now configured for EKS environment"
    echo ""
    echo "Next steps:"
    echo "1. Update your MCP server to use the service account kubeconfig"
    echo "2. Test the MCP tools with a simple experiment"
    echo "3. Monitor the chaos-mesh namespace for any issues"
    echo ""
    echo "To use the service account kubeconfig:"
    echo "export KUBECONFIG=$(dirname "$0")/chaos-mesh-mcp-kubeconfig"
    echo ""
    echo "To start the MCP server:"
    echo "cd $(dirname "$0")"
    echo "python server.py --kubeconfig ./chaos-mesh-mcp-kubeconfig"
}

# 运行主函数
main "$@"
