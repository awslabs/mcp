# Chaos Mesh MCP Server

A Model Context Protocol (MCP) server for Chaos Mesh fault injection, optimized for AWS EKS environments with full namespace support.

## Features

- **Pod Fault Injection**: Kill pods, inject failures, stress CPU/memory
- **Network Chaos**: Simulate network delays, partitions, bandwidth limits
- **Host-level Chaos**: CPU/memory stress, disk operations on nodes
- **EKS Optimized**: Enhanced support for AWS EKS with proper RBAC and authentication
- **Namespace Support**: All tools support custom namespaces
- **Improved Error Handling**: Detailed error messages and retry mechanisms
- **Health Monitoring**: Built-in health checks and diagnostics
- **uvx Integration**: Simplified installation and dependency management with uvx

## Quick Start with uvx (Recommended)

### 1. One-time Environment Setup

```bash
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP

# Run the uvx setup script (includes EKS permissions and kubeconfig generation)
./setup-uvx.sh
```

This script will:
- Install Chaos Mesh (if not present)
- Create necessary RBAC permissions
- Generate `chaos-mesh-mcp-kubeconfig` file with service account credentials
- Create environment configuration for uvx
- Verify the setup

### 2. MCP Configuration

Add to your `~/.aws/amazonq/mcp.json`:

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

### 3. Start Using

Restart your Amazon Q CLI session:

```bash
# Exit current session
/quit

# Restart
q chat
```

The MCP server will now run automatically via uvx when needed!

## Alternative: Manual Setup (Legacy)

If you prefer the traditional approach or need to troubleshoot:

### 1. Clone and Setup Environment

```bash
git clone https://github.com/RadiumGu/Chaosmesh-MCP.git
cd Chaosmesh-MCP/
uv venv
source .venv/bin/activate
uv sync
```

### 2. Generate Kubeconfig

```bash
# Make the setup script executable
chmod +x setup-eks-permissions.sh

# Run the setup script to generate kubeconfig and configure permissions
./setup-eks-permissions.sh
```

### 3. Start MCP Server

```bash
# Use the generated kubeconfig
export KUBECONFIG=./chaos-mesh-mcp-kubeconfig
uv run python server.py --kubeconfig ./chaos-mesh-mcp-kubeconfig
```

## uvx vs Manual Installation

### uvx Advantages (Recommended):
- ✅ **Automatic dependency management**: No need to manage Python environments
- ✅ **Direct from Git**: Always uses latest version from repository
- ✅ **Version isolation**: Clean environment for each run
- ✅ **Simplified maintenance**: No manual virtual environment management
- ✅ **One-time setup**: Just run `./setup-uvx.sh` once

### Manual Installation:
- ⚠️ Requires manual dependency management
- ⚠️ Need to sync repository updates manually
- ⚠️ Virtual environment maintenance required
- ✅ More control over the environment
- ✅ Easier for development and debugging

## Troubleshooting Setup

If you encounter issues:

1. **Missing kubeconfig file**: Run `./setup-uvx.sh` or `./setup-eks-permissions.sh`
2. **Permission errors**: Ensure your AWS credentials have EKS access
3. **Connection issues**: Verify kubectl can access your cluster
4. **uvx issues**: Check if uvx is installed: `uvx --version`

For detailed setup instructions, see [SETUP.md](SETUP.md) and [UVX-USAGE.md](UVX-USAGE.md).

## Namespace Support

All Chaos Mesh MCP tools now support specifying custom namespaces:

### Available Tools with Namespace Support

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

### New Namespace Management Tools

- `list_namespaces()`: List all available namespaces
- `list_services_in_namespace(namespace="default")`: List services in a specific namespace
- `health_check()`: Check system health

### Example Usage

```python
# List all namespaces
namespaces = list_namespaces()

# List services in votingapp namespace
services = list_services_in_namespace("votingapp")

# Kill 50% of votingapp pods in votingapp namespace for 30 seconds
pod_kill(
    service="votingapp",
    duration="30s", 
    mode="fixed-percent",
    value="50",
    namespace="votingapp"
)

# Apply CPU stress in production namespace
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

# Check system health
health_status = health_check()
```

## Installation

### Prerequisites

- **uvx**: Python package runner (recommended)
- **kubectl**: Configured for your cluster
- **Helm**: For Chaos Mesh installation
- **AWS CLI**: For EKS environments
- **Python 3.10+**: Required by uvx

### uvx Installation (Recommended)

```bash
# Install uvx if not already installed
pip install uvx

# Run one-time setup
cd /home/ec2-user/mcp-servers/Chaosmesh-MCP
./setup-uvx.sh
```

uvx will automatically handle all Python dependencies:
- `chaos-mesh>=1.2.13`
- `kubernetes>=32.0.1` 
- `mcp[cli]>=1.7.1`

### Manual Installation (Alternative)

```bash
# Clone repository
git clone https://github.com/RadiumGu/Chaosmesh-MCP.git
cd Chaosmesh-MCP/

# Setup Python environment
uv venv
source .venv/bin/activate
uv sync

# Install dependencies manually
pip install chaos-mesh>=1.2.13 kubernetes>=32.0.1 mcp[cli]>=1.7.1
```

## Configuration

### uvx Configuration (Recommended)

For uvx-based deployment, use the automated setup:

```bash
./setup-uvx.sh
```

This script will:
- Install Chaos Mesh if not present
- Create necessary RBAC permissions with cross-namespace support
- Generate a service account kubeconfig
- Create environment configuration for uvx
- Verify the setup

### EKS Environment (Manual)

For manual AWS EKS cluster setup:

```bash
./setup-eks-permissions.sh
```

This script will:
- Install Chaos Mesh if not present
- Create necessary RBAC permissions with cross-namespace support
- Generate a service account kubeconfig
- Verify the setup

### Manual Configuration

1. **Install Chaos Mesh**:
   ```bash
   helm repo add chaos-mesh https://charts.chaos-mesh.org
   helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace
   ```

2. **Apply RBAC**:
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

## Troubleshooting

### Common Issues

1. **uvx Command Not Found**:
   ```bash
   pip install uvx
   ```

2. **Connection Timeouts**: 
   - Check Chaos Mesh installation
   - Verify RBAC permissions
   - Use `health_check()` tool

3. **Permission Denied**:
   - Apply RBAC configuration
   - Use service account kubeconfig
   - Re-run `./setup-uvx.sh`

4. **Service Not Found**:
   - Verify service name and namespace
   - Use `list_services_in_namespace()` to check available services
   - Check label selectors

5. **Namespace Issues**:
   - Use `list_namespaces()` to see available namespaces
   - Ensure namespace exists before running experiments

6. **uvx Installation Issues**:
   - Check if kubeconfig exists: `ls -la /home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig`
   - Verify Kubernetes connection: `kubectl get pods -n chaos-mesh`
   - Re-run setup: `./setup-uvx.sh`

### Debug Mode

For uvx (automatic via MCP configuration):
```json
"env": {
  "KUBECONFIG": "/home/ec2-user/mcp-servers/Chaosmesh-MCP/chaos-mesh-mcp-kubeconfig",
  "AWS_REGION": "us-east-2",
  "DEBUG": "true"
}
```

For manual mode:
```bash
python server.py --skip-env-check --kubeconfig ./chaos-mesh-mcp-kubeconfig
```

### Logs

Check Chaos Mesh controller logs:
```bash
kubectl logs -n chaos-mesh -l app.kubernetes.io/name=chaos-mesh
```

Check experiments across namespaces:
```bash
kubectl get podchaos --all-namespaces
```

### Migration from Manual to uvx

If migrating from manual installation, see [MIGRATION-TO-UVX.md](MIGRATION-TO-UVX.md) for detailed instructions.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │────│  Chaos Mesh MCP │────│   Kubernetes    │
│                 │    │     Server       │    │    Cluster      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                       ┌──────────────────┐
                       │   Chaos Mesh     │
                       │   Controllers    │
                       └──────────────────┘
```

## Security

- Uses dedicated service account with minimal permissions
- Supports cross-namespace operations with proper RBAC
- Token-based authentication for EKS
- Namespace isolation support
- Audit logging support

## Best Practices

1. **Use service accounts**: Avoid using personal credentials
2. **Namespace isolation**: Use different namespaces for different environments
3. **Monitor experiments**: Regularly check experiment status across namespaces
4. **Clean up resources**: Delete completed experiments promptly
5. **Detailed logging**: Enable verbose logging for troubleshooting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test in EKS environment with multiple namespaces
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs and health status
3. Consult the documentation:
   - [EKS Setup Guide](EKS-SETUP.md)
   - [General Setup Guide](SETUP.md)
   - [uvx Usage Guide](UVX-USAGE.md)
   - [Migration Guide](MIGRATION-TO-UVX.md)
4. Use namespace management tools for debugging
5. Check the [GitHub Issues](https://github.com/RadiumGu/Chaosmesh-MCP/issues) page

## Documentation

- **[README.md](README.md)** - This file, main documentation
- **[SETUP.md](SETUP.md)** - Detailed setup instructions
- **[EKS-SETUP.md](EKS-SETUP.md)** - EKS-specific setup guide
- **[UVX-USAGE.md](UVX-USAGE.md)** - uvx installation and usage guide
- **[MIGRATION-TO-UVX.md](MIGRATION-TO-UVX.md)** - Migration from manual to uvx
