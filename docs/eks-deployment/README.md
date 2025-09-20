# Deploying eks-mcp-server on Amazon EKS

This guide provides comprehensive instructions for deploying the `eks-mcp-server` to an Amazon EKS cluster. The `eks-mcp-server` provides AI code assistants with tools for managing EKS clusters and Kubernetes resources, streamlining development and operations.

## Prerequisites

Before you begin, ensure you have the following prerequisites in place:

- **An active AWS account** with the necessary permissions to create and manage EKS clusters, IAM roles, and related resources
- **AWS CLI** installed and configured with your AWS credentials
- **kubectl** installed and configured to communicate with your Kubernetes cluster
- **An existing Amazon EKS cluster** - If you don't have one, you can create one using the [EKS documentation](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html)
- **Docker** installed and running on your local machine (optional, for building custom images)

## IAM Permissions

The eks-mcp-server requires specific IAM permissions to function properly. Ensure your AWS credentials have the following policies attached:

### Read-Only Operations
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:DescribeInsight",
        "eks:ListInsights",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables",
        "cloudformation:DescribeStacks",
        "cloudwatch:GetMetricData",
        "logs:StartQuery",
        "logs:GetQueryResults",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:GetPolicy",
        "iam:GetPolicyVersion"
      ],
      "Resource": "*"
    }
  ]
}
```

### Write Operations (Optional)
For write operations, additional permissions are required. See the [main eks-mcp-server documentation](../../src/eks-mcp-server/README.md) for details.

## Deployment Steps

### Step 1: Create AWS Credentials Secret

Create a Kubernetes secret containing your AWS credentials:

```bash
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=<YOUR_AWS_ACCESS_KEY_ID> \
  --from-literal=AWS_SECRET_ACCESS_KEY=<YOUR_AWS_SECRET_ACCESS_KEY>
```

Alternatively, if you're using IAM roles for service accounts (IRSA), you can skip this step and configure the service account instead.

### Step 2: Apply Kubernetes Manifests

Apply the manifests in the following order:

```bash
# Apply ConfigMap first
kubectl apply -f samples/eks-mcp-server/configmap.yaml

# Apply Deployment
kubectl apply -f samples/eks-mcp-server/deployment.yaml

# Apply Service
kubectl apply -f samples/eks-mcp-server/service.yaml
```

### Step 3: Verify the Deployment

Check the status of the deployment:

```bash
kubectl get deployments -l app=eks-mcp-server
```

You should see output similar to:
```
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
eks-mcp-server   1/1     1            1           2m
```

Check the pods:
```bash
kubectl get pods -l app=eks-mcp-server
```

### Step 4: Access the Service

Get the service details:

```bash
kubectl get services eks-mcp-server
```

For LoadBalancer type services, wait for the external IP to be assigned. For ClusterIP services, you can use port-forwarding:

```bash
kubectl port-forward service/eks-mcp-server 8080:80
```

## Configuration Options

### Environment Variables

The following environment variables can be configured in the ConfigMap:

- `AWS_REGION`: AWS region for the EKS cluster (default: us-east-1)
- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARN, INFO, DEBUG)
- `AWS_PROFILE`: AWS profile to use (if using shared credentials)

### Service Types

The service can be configured with different types:

- **LoadBalancer**: Exposes the service externally using a cloud provider's load balancer
- **ClusterIP**: Exposes the service on a cluster-internal IP
- **NodePort**: Exposes the service on each Node's IP at a static port

## Advanced Configuration

### Using IAM Roles for Service Accounts (IRSA)

For production deployments, it's recommended to use IRSA instead of storing AWS credentials in secrets:

1. Create an IAM role with the required permissions
2. Associate the role with a Kubernetes service account
3. Update the deployment to use the service account

Example service account configuration:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: eks-mcp-server
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT-ID:role/eks-mcp-server-role
```

### Resource Limits

Configure resource limits based on your cluster's capacity:

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
```

## Troubleshooting

### Common Issues

#### Pod Not Starting
1. Check pod logs:
   ```bash
   kubectl logs -l app=eks-mcp-server
   ```

2. Check pod events:
   ```bash
   kubectl describe pod -l app=eks-mcp-server
   ```

#### Authentication Issues
1. Verify AWS credentials are correct
2. Check IAM permissions
3. Ensure the EKS cluster access is properly configured

#### Service Not Accessible
1. Check service configuration:
   ```bash
   kubectl describe service eks-mcp-server
   ```

2. Verify network policies and security groups
3. Check if the LoadBalancer is provisioned correctly

### Health Checks

The eks-mcp-server includes built-in health checks. Monitor the health status:

```bash
kubectl get pods -l app=eks-mcp-server -o wide
```

### Logs and Monitoring

Access application logs:
```bash
kubectl logs -f deployment/eks-mcp-server
```

For persistent logging, consider integrating with AWS CloudWatch or other logging solutions.

## Security Considerations

- Use IAM roles for service accounts instead of storing credentials in secrets
- Apply network policies to restrict traffic
- Regularly update the container image to get security patches
- Use private container registries when possible
- Implement proper RBAC for Kubernetes resources

## Cleanup

To remove the deployment:

```bash
kubectl delete -f samples/eks-mcp-server/
kubectl delete secret aws-credentials
```

## Next Steps

- Configure monitoring and alerting
- Set up automated deployments with CI/CD
- Implement backup and disaster recovery procedures
- Scale the deployment based on usage patterns

For more information about the eks-mcp-server capabilities, see the [main documentation](../../src/eks-mcp-server/README.md).

