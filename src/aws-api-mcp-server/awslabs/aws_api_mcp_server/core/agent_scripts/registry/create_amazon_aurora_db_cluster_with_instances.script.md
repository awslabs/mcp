---
description: Creates a complete Amazon Aurora database cluster with instances, handling both cluster creation and instance provisioning in the proper sequence
---

# Create Aurora Database Cluster with Instance

## Overview
This script creates a complete Amazon Aurora database setup by first creating an empty Aurora cluster, then adding a database instance to make it queryable. The script uses AWS Secrets Manager for password management and includes proper status monitoring with retry logic.

## Parameters
- cluster_identifier (required): Unique identifier for the Aurora cluster
- instance_identifier (required): Unique identifier for the Aurora instance
- engine (required): Database engine type (aurora-mysql or aurora-postgresql)
- engine_version (optional): Specific engine version to use
- master_username (required): Master username for the database
- instance_class (optional, default: db.t3.medium): Instance class for the database instance (e.g., db.r6g.large)
- database_name (optional): Name of the initial database to create
- vpc_security_group_ids (optional): Comma-separated list of VPC security group IDs
- db_subnet_group_name (optional): Name of the DB subnet group
- backup_retention_period (optional, default: 7): Number of days to retain backups
- preferred_backup_window (optional): Preferred backup window in UTC
- preferred_maintenance_window (optional): Preferred maintenance window

## Steps

### 1. Verify Dependencies
Check for required tools and warn the user if any are missing.

Constraints:
- You MUST verify the following tools are available in your context: `call_aws`
- You MUST inform the user about any missing tools with a clear message
- You MUST ask if the user wants to proceed anyway despite missing tools
- You MUST respect the user's decision to proceed or abort

### 2. Validate AWS Credentials and Permissions
Verify that AWS credentials are configured and have necessary permissions.

Constraints:
- You MUST check current AWS identity using `aws sts get-caller-identity`
- You MUST verify the user has permissions to create RDS clusters and instances
- You SHOULD inform the user about the AWS account and region being used
- You MUST abort if credentials are not properly configured
- You MUST NOT retrieve or display the actual password value because passwords should never be exposed in logs or outputs

### 3. Create Aurora Database Cluster
Create the Aurora cluster with the specified configuration.

Constraints:
- You MUST use `call_aws` to create the cluster with: `aws rds create-db-cluster --db-cluster-identifier {cluster_identifier} --engine {engine} --master-username {master_username} --manage-master-user-password --master-user-secret-kms-key-id alias/aws/secretsmanager`
- You MUST NOT use any password-related parameters like `--master-user-password` because managed passwords from Secrets Manager must be used exclusively
- You SHOULD include optional parameters like `--engine-version`, `--database-name`, `--vpc-security-group-ids`, `--db-subnet-group-name`, `--backup-retention-period`, `--preferred-backup-window`, `--preferred-maintenance-window` if provided
- You MUST capture the cluster creation response for monitoring purposes

### 4. Monitor Cluster Creation Status
Wait for the cluster to become available before creating the instance.

Constraints:
- You MUST use `call_aws` to check cluster status with: `aws rds describe-db-clusters --db-cluster-identifier {cluster_identifier}`
- You MUST retry status checks using only the `call_aws` tool and MUST NOT use any system tools for waiting or sleeping because system tools are not available in this context
- You MUST check the cluster status by making repeated `call_aws` calls
- You MUST continue monitoring until the cluster status is "available"
- You MUST abort if the cluster status becomes "failed" or remains in a pending state for more than 20 minutes
- You MUST provide status updates to the user during the waiting period

### 5. Create Database Instance
Create the database instance and attach it to the cluster.

Constraints:
- You MUST use `call_aws` to create the instance with: `aws rds create-db-instance --db-instance-identifier {instance_identifier} --db-cluster-identifier {cluster_identifier} --db-instance-class {instance_class} --engine {engine}`
- You MUST NOT specify password-related parameters for the instance because it inherits authentication from the cluster
- You MUST include the engine parameter to ensure compatibility with the cluster
- You MUST capture the instance creation response for monitoring purposes
- You MUST provide an ARN of the managed secret used for created cluster

### 6. Monitor Instance Creation Status
Wait for the instance to become available.

Constraints:
- You MUST use `call_aws` to check instance status with: `aws rds describe-db-instances --db-instance-identifier {instance_identifier}`
- You MUST retry status checks using only the `call_aws` tool and MUST NOT use any system tools for waiting because system tools are not available in this context
- You MUST check the instance status by making repeated `call_aws` calls
- You MUST continue monitoring until the instance status is "available"
- You MUST abort if the instance status becomes "failed" or remains in a pending state for more than 20 minutes
- You MUST provide status updates to the user during the waiting period

### 7. Retrieve Connection Information
Gather the necessary connection details for the user.

Constraints:
- You MUST use `call_aws` to get cluster endpoint information with: `aws rds describe-db-clusters --db-cluster-identifier {cluster_identifier}`
- You MUST extract and display the cluster endpoint URL, port, and database name
- You MUST remind the user that the password is managed in AWS Secrets Manager under the secret name provided
- You MUST NOT attempt to retrieve or display the actual password value because passwords should never be exposed

### 8. Validate Final Setup
Confirm that both cluster and instance are properly configured and available.

Constraints:
- You MUST perform a final status check on both the cluster and instance
- You MUST verify that the instance is properly associated with the cluster
- You MUST confirm that managed password authentication is enabled
- You MUST provide a summary of the created resources including identifiers and endpoints

## Examples

### Example Input
```
cluster_identifier: my-aurora-cluster
instance_identifier: my-aurora-instance-1
engine: aurora-mysql
instance_class: db.r6g.large
master_username: admin
secret_name: aurora-master-password
database_name: myapp
```

### Example Output
```
Aurora cluster 'my-aurora-cluster' created successfully
Aurora instance 'my-aurora-instance-1' created and attached to cluster
Cluster endpoint: my-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com:3306
Database name: myapp
Master username: admin
Password: Managed in AWS Secrets Manager (secret: aurora-master-password)
```

## Troubleshooting

### Cluster Creation Fails
If cluster creation fails, check that the engine version is supported in your region and that you have sufficient permissions for RDS and Secrets Manager operations.

### Instance Creation Fails
If instance creation fails after successful cluster creation, verify that the instance class is compatible with the Aurora engine and available in your region's availability zones.

### Long Creation Times
Aurora cluster and instance creation can take 10-20 minutes. The script will monitor progress and provide updates, but extended wait times are normal for Aurora resources.
