# ECS Security Analysis Tool - Security Checks Reference

This document provides a comprehensive overview of all security checks performed by the ECS Security Analysis Tool.

## Overview

The ECS Security Analysis Tool performs comprehensive security assessments across multiple domains to identify vulnerabilities, misconfigurations, and compliance issues in your ECS infrastructure.

## Available Actions

### 1. `list_clusters`
- **Purpose**: List all ECS clusters in a specified region
- **Parameters**: `region` (optional, defaults to us-east-1)
- **Use Case**: Discovery and cluster selection

### 2. `select_cluster_for_analysis`
- **Purpose**: Interactive cluster selection with analysis options
- **Parameters**: `cluster_name`, `region`, `analysis_type`
- **Analysis Types**: comprehensive, quick, report, compliance

### 3. `analyze_cluster_security`
- **Purpose**: Perform comprehensive security analysis of an ECS cluster
- **Parameters**: `cluster_name`, `region`, `category_filter`, `severity_filter`

### 4. `generate_security_report`
- **Purpose**: Generate formatted security reports
- **Parameters**: `cluster_name`, `region`, `format`, `severity_filter`, `show_details`
- **Formats**: summary, detailed, json, executive

### 5. `get_security_recommendations`
- **Purpose**: Get actionable security recommendations with implementation guidance
- **Parameters**: `cluster_name`, `region`, `severity_filter`, `category_filter`

### 6. `check_compliance_status`
- **Purpose**: Check compliance against specific frameworks
- **Parameters**: `cluster_name`, `region`, `compliance_framework`
- **Frameworks**: aws-foundational, pci-dss, hipaa, soc2

## Security Check Categories

### 🏗️ **Cluster-Level Security**

#### Container Insights & Monitoring
- **Check**: Container Insights enabled
- **Severity**: Medium
- **Category**: monitoring
- **Issue**: Reduced visibility into security events and performance
- **Fix**: Enable Container Insights for comprehensive monitoring

#### Execute Command Security
- **Check**: Execute command configuration
- **Severity**: Medium
- **Category**: security
- **Issue**: Missing audit and logging capabilities
- **Fix**: Configure execute command with proper logging and KMS encryption

#### Execute Command Audit Logging
- **Check**: CloudWatch logging for execute command
- **Severity**: Medium
- **Category**: monitoring
- **Issue**: No audit trail for command executions
- **Fix**: Enable CloudWatch logging for execute command sessions

#### KMS Encryption for Execute Command
- **Check**: Customer-managed KMS keys for execute command
- **Severity**: Medium
- **Category**: encryption
- **Issue**: Sessions not encrypted with customer-managed keys
- **Fix**: Configure KMS encryption for execute command sessions

#### Cluster Status
- **Check**: Cluster operational status
- **Severity**: High
- **Category**: availability
- **Issue**: Cluster not in ACTIVE state
- **Fix**: Investigate and resolve cluster status issues

### 🖥️ **Container Instance Security**

#### ECS Agent Security Updates
- **Check**: ECS agent version vulnerabilities
- **Severity**: High
- **Category**: security
- **Issue**: Known security vulnerabilities in agent version
- **Fix**: Update ECS agent to latest version

#### ECS Agent Connectivity
- **Check**: Agent connection status
- **Severity**: High
- **Category**: security
- **Issue**: Disconnected agents prevent security monitoring
- **Fix**: Investigate and reconnect ECS agent

#### Instance Type Security
- **Check**: Legacy instance types
- **Severity**: Medium
- **Category**: security
- **Issue**: Older generation instances with potential vulnerabilities
- **Fix**: Migrate to newer generation instance types

#### Managed Termination Protection
- **Check**: Termination protection on capacity providers
- **Severity**: Medium
- **Category**: security
- **Issue**: Uncontrolled instance termination allowed
- **Fix**: Enable managed termination protection

### 🌐 **Network Security**

#### Public IP Assignment
- **Check**: Public IP assignment on services
- **Severity**: High
- **Category**: network_security
- **Issue**: Containers exposed directly to internet
- **Fix**: Disable public IP assignment, use NAT Gateway

#### Security Groups Configuration
- **Check**: Security group assignment and count
- **Severity**: High/Low
- **Category**: network_security
- **Issue**: Missing or excessive security groups
- **Fix**: Configure appropriate security groups

#### Service Connect Configuration
- **Check**: Service Connect namespace configuration
- **Severity**: Medium
- **Category**: network_security
- **Issue**: Service Connect enabled without namespace
- **Fix**: Configure proper namespace for Service Connect

#### Fargate Platform Version
- **Check**: Platform version pinning
- **Severity**: Medium
- **Category**: security
- **Issue**: Using LATEST introduces unpredictable changes
- **Fix**: Pin to specific Fargate platform version

### 🔐 **IAM Security**

#### Task IAM Role
- **Check**: Task role configuration
- **Severity**: High
- **Category**: iam_security
- **Issue**: Missing task IAM role
- **Fix**: Configure task IAM role with minimal permissions

#### Execution IAM Role
- **Check**: Execution role configuration
- **Severity**: High
- **Category**: iam_security
- **Issue**: Missing execution IAM role
- **Fix**: Configure execution IAM role for ECS operations

### 📦 **Container Security**

#### Root User Execution
- **Check**: Container user configuration
- **Severity**: High
- **Category**: container_security
- **Issue**: Container runs as root user (UID 0)
- **Fix**: Create dedicated application user

#### Read-Only Root Filesystem
- **Check**: Root filesystem write permissions
- **Severity**: Medium
- **Category**: container_security
- **Issue**: Writable root filesystem increases attack surface
- **Fix**: Enable read-only root filesystem

#### Health Check Configuration
- **Check**: Container health checks
- **Severity**: Medium
- **Category**: monitoring
- **Issue**: Missing health check configuration
- **Fix**: Implement comprehensive health checks

#### Linux Security Parameters
- **Check**: Runtime security controls
- **Severity**: High
- **Category**: runtime_security
- **Issue**: Missing seccomp, AppArmor, noNewPrivileges
- **Fix**: Configure linuxParameters with security controls

#### Container Capabilities
- **Check**: Dangerous Linux capabilities
- **Severity**: High
- **Category**: runtime_security
- **Issue**: Excessive or dangerous capabilities
- **Fix**: Remove unnecessary capabilities

#### Init Process
- **Check**: Init process configuration
- **Severity**: Medium
- **Category**: container_security
- **Issue**: Missing init process causes zombie processes
- **Fix**: Enable initProcessEnabled

### 🖼️ **Image Security**

#### Image Specification
- **Check**: Container image specified
- **Severity**: High
- **Category**: image_security
- **Issue**: No container image specified
- **Fix**: Specify valid container image from trusted registry

#### ECR Vulnerability Scanning
- **Check**: ECR image scanning enabled
- **Severity**: Medium
- **Category**: image_security
- **Issue**: Vulnerability scanning not enabled
- **Fix**: Enable ECR image scanning

#### Image Tag Security
- **Check**: Mutable vs immutable tags
- **Severity**: High
- **Category**: image_security
- **Issue**: Using mutable tags allows substitution attacks
- **Fix**: Use SHA256 digest references

#### Base Image Security
- **Check**: Base image vulnerabilities
- **Severity**: High/Medium
- **Category**: image_security
- **Issue**: Outdated base images with vulnerabilities
- **Fix**: Update to supported base image versions

#### Registry Security
- **Check**: External vs ECR registry usage
- **Severity**: Low/Medium
- **Category**: image_security
- **Issue**: External registries lack integrated security
- **Fix**: Migrate to Amazon ECR

#### Package Vulnerability Scanning
- **Check**: Container package vulnerabilities
- **Severity**: High
- **Category**: image_security
- **Issue**: Packages may contain known vulnerabilities
- **Fix**: Implement comprehensive package scanning

### 🔒 **Secrets Management**

#### Environment Variable Secrets
- **Check**: Hardcoded secrets in environment variables
- **Severity**: High
- **Category**: secrets
- **Issue**: Credentials visible in metadata and logs
- **Fix**: Migrate to AWS Secrets Manager

#### Parameter Store vs Secrets Manager
- **Check**: Secret storage location
- **Severity**: Medium
- **Category**: secrets
- **Issue**: Using Parameter Store for sensitive data
- **Fix**: Use AWS Secrets Manager for automatic rotation

#### Tag Security
- **Check**: Sensitive information in tags
- **Severity**: High/Medium
- **Category**: secrets
- **Issue**: Tags may contain sensitive data
- **Fix**: Remove sensitive data from tags

### 🏗️ **Resource Management**

#### Memory Limits (EC2)
- **Check**: Memory limits on EC2 launch type
- **Severity**: High
- **Category**: resource_management
- **Issue**: No memory limits configured (required for EC2)
- **Fix**: Set memory limits to prevent resource exhaustion

#### CPU Configuration (Fargate)
- **Check**: CPU configuration for Fargate tasks
- **Severity**: High
- **Category**: configuration
- **Issue**: Missing CPU configuration
- **Fix**: Configure appropriate CPU allocation

#### Memory Configuration (Fargate)
- **Check**: Memory configuration for Fargate tasks
- **Severity**: High
- **Category**: configuration
- **Issue**: Missing memory configuration
- **Fix**: Configure appropriate memory allocation

### 🌐 **Network Infrastructure Security**

#### VPC Flow Logs
- **Check**: VPC Flow Logs enabled
- **Severity**: Medium
- **Category**: network_security
- **Issue**: No network traffic monitoring
- **Fix**: Enable VPC Flow Logs for security monitoring

#### Internet Gateway Security
- **Check**: Internet gateway route configurations
- **Severity**: High
- **Category**: network_security
- **Issue**: Overly permissive internet access
- **Fix**: Review and restrict internet gateway routes

#### Load Balancer Security
- **Check**: Load balancer encryption and configuration
- **Severity**: High/Medium
- **Category**: network_security
- **Issue**: Unencrypted traffic, insecure configurations
- **Fix**: Enable HTTPS, configure security policies

#### Route Table Security
- **Check**: Route table configurations
- **Severity**: Medium
- **Category**: network_security
- **Issue**: Overly permissive routing rules
- **Fix**: Review and restrict route table entries

### 🔍 **Advanced Security Features**

#### Service Mesh Security
- **Check**: App Mesh configuration and security
- **Severity**: Medium/High
- **Category**: service_mesh_security
- **Issue**: Missing or misconfigured service mesh security
- **Fix**: Configure App Mesh with proper security controls

#### Envoy Proxy Security
- **Check**: Envoy proxy security configuration
- **Severity**: High/Medium
- **Category**: envoy_security
- **Issue**: Missing security headers, logging, mTLS
- **Fix**: Configure Envoy security features

#### Storage Security
- **Check**: Volume and storage security
- **Severity**: Medium
- **Category**: storage_security
- **Issue**: Insecure storage configurations
- **Fix**: Configure secure storage options

#### DNS Security
- **Check**: DNS configuration security
- **Severity**: Medium
- **Category**: dns_security
- **Issue**: DNS security misconfigurations
- **Fix**: Configure secure DNS settings

## Compliance Frameworks

### 🏛️ **AWS Well-Architected Framework**
- Security pillar best practices
- Operational excellence checks
- Reliability and performance security aspects

### 💳 **PCI DSS Compliance**
- **Requirement 2**: No vendor-supplied defaults
- **Requirement 4**: Encrypt transmission of cardholder data
- **Requirement 6**: Secure development practices
- **Requirement 8**: Strong access controls

### 🏥 **HIPAA Compliance**
- Data encryption requirements
- Access control verification
- Audit logging compliance
- Network security for PHI protection

### 📊 **SOC 2 Compliance**
- Security controls verification
- Availability monitoring
- Processing integrity checks
- Confidentiality controls

## Severity Levels

### 🚨 **Critical**
- Immediate security risks requiring urgent attention
- Active vulnerabilities with known exploits
- Critical compliance violations

### ⚠️ **High**
- Significant security risks
- Should be addressed within 24-48 hours
- Major compliance issues

### 📋 **Medium**
- Moderate security concerns
- Should be addressed in next maintenance window
- Important best practice violations

### ℹ️ **Low**
- Minor security improvements
- Future enhancements for better security posture
- Optimization recommendations

## Output Formats

### Summary Report
- Executive summary with key findings
- Priority-based issue listing
- Quick action recommendations

### Detailed Report
- Comprehensive analysis with full context
- Implementation guidance
- CLI examples and commands

### JSON Report
- Machine-readable format
- Integration with other tools
- Programmatic processing

### Executive Report
- High-level overview for management
- Risk assessment summary
- Business impact analysis

## Implementation Guidance

Each security recommendation includes:
- **Issue Description**: Clear explanation of the security concern
- **Implementation Steps**: Step-by-step remediation guide
- **AWS CLI Examples**: Ready-to-use commands
- **Terraform Examples**: Infrastructure as Code snippets
- **CloudFormation Examples**: Template configurations
- **Compliance Frameworks**: Relevant standards and requirements

## Usage Examples

```bash
# List available clusters
{"action": "list_clusters", "parameters": {"region": "us-east-1"}}

# Comprehensive security analysis
{"action": "analyze_cluster_security", "parameters": {"cluster_name": "my-cluster", "region": "us-east-1"}}

# Get high-priority recommendations only
{"action": "get_security_recommendations", "parameters": {"cluster_name": "my-cluster", "severity_filter": "High"}}

# Generate executive summary report
{"action": "generate_security_report", "parameters": {"cluster_name": "my-cluster", "format": "executive"}}

# Check PCI DSS compliance
{"action": "check_compliance_status", "parameters": {"cluster_name": "my-cluster", "compliance_framework": "pci-dss"}}
```

## Security Analysis Coverage

The tool analyzes:
- **15+ security domains** across cluster, service, and container levels
- **4 compliance frameworks** (AWS Well-Architected, PCI DSS, HIPAA, SOC 2)
- **50+ specific security checks** with actionable recommendations
- **Network, IAM, container runtime, and image security** aspects
- **Advanced features** like service mesh, Envoy proxy, and storage security

## Resource Naming Convention

All security recommendations use consistent resource naming:
- **Containers**: `Container: webapp | Service: my-ecs-cluster-webapp`
- **Container Images**: `Container Image: nginx:latest | Service: my-ecs-cluster-webapp`
- **Services**: `Service: my-ecs-cluster-webapp`
- **Task Definitions**: `Task Definition: webapp-task | Service: my-ecs-cluster-webapp`
- **Clusters**: `Cluster: my-ecs-cluster`

This provides clear context and makes it easy to identify which resources need attention.
