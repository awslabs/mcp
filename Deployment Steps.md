





_**# Deploying eks-mcp-server on Amazon EKS**_ 

This guide provides step-by-step instructions for deploying the `eks-mcp-server` to an Amazon EKS cluster. The `eks-mcp-server` provides AI code assistants with tools for managing EKS clusters and Kubernetes resources, streamlining development and operations.

_**## Prerequisites**_ 

Before you begin, ensure you have the following prerequisites in place:

- **An active AWS account** with the necessary permissions to create and manage EKS clusters, IAM roles, and related resources.
- **AWS CLI** installed and configured with your AWS credentials.
- **kubectl** installed and configured to communicate with your Kubernetes cluster.
- **An existing Amazon EKS cluster.** If you don't have one, you can create one using the [EKS documentation](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html).
- **Docker** installed and running on your local machine.
- **An AWS secret** named `aws-credentials` in your Kubernetes cluster containing your AWS access key ID and secret access key. You can create this secret using the following command:

  ```bash
  kubectl create secret generic aws-credentials \
    --from-literal=AWS_ACCESS_KEY_ID=<YOUR_AWS_ACCESS_KEY_ID> \
    --from-literal=AWS_SECRET_ACCESS_KEY=<YOUR_AWS_SECRET_ACCESS_KEY>
  ```




## Deployment Steps

Follow these steps to deploy the `eks-mcp-server` to your EKS cluster:

**1. Create Kubernetes Manifests**

Create the following Kubernetes manifest files:

- `configmap.yaml`
- `deployment.yaml`
- `service.yaml`

**2. Apply the Manifests**

Apply the manifests to your cluster in the following order:

```bash
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

**3. Verify the Deployment**

Check the status of the deployment:

```bash
kubectl get deployments
```

You should see the `eks-mcp-server` deployment with a status of `1/1`.

**4. Access the Service**

Get the external IP address of the service:

```bash
kubectl get services
```

You can now use this IP address to interact with the `eks-mcp-server`.


