
## Overview

The EKS Resiliency Checker is a comprehensive tool that evaluates Amazon EKS clusters against 28 critical resiliency best practices. It performs automated checks across three main categories: Application workloads, Control Plane configuration, and Data Plane setup. The tool provides detailed findings, compliance status, and actionable remediation guidance for each check.

## Check Categories

### Application Related Checks (A1-A14)
These checks focus on application workload resilience and operational best practices.

### Control Plane Related Checks (C1-C5)
These checks evaluate the EKS control plane configuration for security, monitoring, and scalability.

### Data Plane Related Checks (D1-D7)
These checks assess worker node configuration, resource management, and cluster infrastructure.

---

## Detailed Check Descriptions

### **A1: Avoid Running Singleton Pods**
**Purpose**: Identifies standalone pods that aren't managed by controllers (Deployments, StatefulSets, etc.)

**What it checks**:
- Scans all pods across specified namespaces
- Identifies pods without `ownerReferences` (indicating they're not managed by controllers)
- Excludes system namespaces from the check

**Why it matters**:
- Singleton pods have no automatic restart capability if they fail
- No rolling update or scaling capabilities
- Difficult to manage and maintain
- Single point of failure for applications

**Compliance**: ✅ PASS if no singleton pods found, ❌ FAIL if any exist

---

### **A2: Run Multiple Replicas**
**Purpose**: Ensures Deployments and StatefulSets have more than one replica for high availability

**What it checks**:
- Examines all Deployments and StatefulSets
- Identifies workloads with `replicas: 1`
- Provides list of single-replica workloads

**Why it matters**:
- Single replica = single point of failure
- No availability during updates or node failures
- Cannot handle traffic spikes
- Violates high availability principles

**Compliance**: ✅ PASS if all workloads have >1 replica, ❌ FAIL if any have only 1 replica

---

### **A3: Use Pod Anti-Affinity**
**Purpose**: Ensures multi-replica deployments spread pods across different nodes

**What it checks**:
- Focuses on Deployments with >1 replica
- Checks for `podAntiAffinity` configuration in pod specs
- Identifies deployments that could have pods scheduled on the same node

**Why it matters**:
- Prevents all replicas from running on the same node
- Protects against node-level failures
- Improves fault tolerance and availability
- Better resource distribution

**Compliance**: ✅ PASS if multi-replica deployments have anti-affinity, ❌ FAIL if missing

---

### **A4: Use Liveness Probes**
**Purpose**: Ensures containers have health checks to detect and restart unhealthy instances

**What it checks**:
- Scans Deployments, StatefulSets, and DaemonSets
- Verifies each container has a `livenessProbe` configured
- Checks across all specified namespaces

**Why it matters**:
- Automatically restarts unhealthy containers
- Prevents zombie processes and deadlocks
- Improves application reliability
- Essential for self-healing applications

**Compliance**: ✅ PASS if all containers have liveness probes, ❌ FAIL if any are missing

---

### **A5: Use Readiness Probes**
**Purpose**: Ensures containers signal when they're ready to receive traffic

**What it checks**:
- Examines all workload types (Deployments, StatefulSets, DaemonSets)
- Verifies each container has a `readinessProbe`
- Identifies containers that might receive traffic before being ready

**Why it matters**:
- Prevents traffic routing to unready pods
- Improves user experience during deployments
- Reduces failed requests and timeouts
- Essential for zero-downtime deployments

**Compliance**: ✅ PASS if all containers have readiness probes, ❌ FAIL if any are missing

---

### **A6: Use Pod Disruption Budgets**
**Purpose**: Protects critical workloads during voluntary disruptions (updates, scaling, maintenance)

**What it checks**:
- Identifies critical workloads (multi-replica Deployments, all StatefulSets)
- Checks for corresponding PodDisruptionBudget resources
- Matches PDB selectors with workload selectors

**Why it matters**:
- Prevents all replicas from being terminated simultaneously
- Maintains availability during cluster maintenance
- Controls the pace of rolling updates
- Essential for production workloads

**Compliance**: ✅ PASS if critical workloads have PDBs, ❌ FAIL if any are unprotected

---

### **A7: Run Kubernetes Metrics Server**
**Purpose**: Ensures the cluster has metrics collection capability for monitoring and autoscaling

**What it checks**:
- Looks for metrics-server deployment in kube-system namespace
- Tests accessibility of the metrics API endpoint
- Verifies metrics collection infrastructure is available

**Why it matters**:
- Required for Horizontal Pod Autoscaler (HPA)
- Enables `kubectl top` commands
- Foundation for monitoring and alerting
- Essential for resource-based scaling decisions

**Compliance**: ✅ PASS if metrics server is running, ❌ FAIL if not found or inaccessible

---

### **A8: Use Horizontal Pod Autoscaler**
**Purpose**: Identifies multi-replica workloads that could benefit from automatic scaling

**What it checks**:
- Finds Deployments and StatefulSets with >1 replica
- Excludes system namespaces
- Checks for existing HPA resources protecting these workloads
- Supports both autoscaling/v1 and autoscaling/v2 APIs

**Why it matters**:
- Automatically scales applications based on demand
- Improves resource utilization
- Handles traffic spikes without manual intervention
- Reduces costs by scaling down during low usage

**Compliance**: ✅ PASS if multi-replica workloads have HPAs, ❌ FAIL if unprotected workloads exist

---

### **A9: Use Custom Metrics Scaling**
**Purpose**: Checks for advanced scaling capabilities beyond basic CPU/memory metrics

**What it checks**:
- Verifies custom metrics API availability
- Looks for external metrics API
- Checks for Prometheus Adapter deployment
- Identifies KEDA (event-driven autoscaling) installation
- Finds HPAs using custom or external metrics

**Why it matters**:
- Enables scaling based on business metrics (queue length, response time)
- More sophisticated than basic resource metrics
- Better alignment with application performance
- Supports event-driven architectures

**Compliance**: ✅ PASS if custom metrics infrastructure exists, ❌ FAIL if only basic metrics available

---

### **A10: Use Vertical Pod Autoscaler**
**Purpose**: Ensures workloads have right-sizing capabilities for resource optimization

**What it checks**:
- Looks for VPA controller components (recommender, updater, admission controller)
- Verifies VPA CRD installation
- Checks for existing VPA resources
- Identifies deployments without VPA configuration
- Detects Goldilocks (VPA UI) if installed

**Why it matters**:
- Automatically adjusts resource requests/limits
- Prevents over/under-provisioning
- Improves cluster resource utilization
- Reduces costs through right-sizing

**Compliance**: Three scenarios evaluated:
- ✅ PASS if VPA is installed and used appropriately
- ❌ FAIL if VPA infrastructure missing
- ❌ FAIL if VPA installed but not used

---

### **A11: Use PreStop Hooks**
**Purpose**: Ensures applications handle termination gracefully (excludes DaemonSets)

**What it checks**:
- Examines Deployments and StatefulSets only
- Verifies containers have `lifecycle.preStop` hooks configured
- Intentionally excludes DaemonSets (system services don't need graceful termination)

**Why it matters**:
- Allows applications to finish processing requests
- Prevents data loss during pod termination
- Improves user experience during deployments
- Essential for stateful applications

**Compliance**: ✅ PASS if application workloads have preStop hooks, ❌ FAIL if missing

---

### **A12: Use a Service Mesh**
**Purpose**: Detects service mesh implementation for advanced networking and observability

**What it checks**:
- Looks for Istio components (namespaces, CRDs, deployments)
- Checks for Linkerd installation
- Identifies Consul service mesh
- Detects sidecar proxy containers in application pods

**Why it matters**:
- Provides traffic management and security
- Enables advanced observability and tracing
- Improves service-to-service communication
- Adds resilience patterns (circuit breaking, retries)

**Compliance**: ✅ PASS if any service mesh detected, ❌ FAIL if none found

---

### **A13: Monitor Your Applications**
**Purpose**: Ensures comprehensive monitoring solution is deployed

**What it checks**:
- Looks for Prometheus stack (deployments, CRDs, namespaces)
- Detects CloudWatch Container Insights
- Identifies third-party monitoring (Datadog, New Relic, Dynatrace)
- Checks for monitoring infrastructure components

**Why it matters**:
- Essential for observability and alerting
- Enables proactive issue detection
- Supports troubleshooting and performance optimization
- Required for production operations

**Compliance**: ✅ PASS if monitoring solution detected, ❌ FAIL if none found

---

### **A14: Use Centralized Logging**
**Purpose**: Verifies log aggregation and centralized logging infrastructure

**What it checks**:
- Looks for Fluentd/Fluent Bit log collectors
- Detects Elasticsearch/OpenSearch backends
- Identifies CloudWatch Logs integration
- Checks for Loki logging stack

**Why it matters**:
- Centralizes logs from all cluster components
- Enables log analysis and troubleshooting
- Supports compliance and audit requirements
- Essential for distributed system debugging

**Compliance**: ✅ PASS if logging solution detected, ❌ FAIL if none found

---

### **C1: Monitor Control Plane Logs**
**Purpose**: Ensures EKS control plane logging is enabled for visibility and troubleshooting

**What it checks**:
- Uses AWS EKS API to check cluster logging configuration
- Verifies if 'api' log type is enabled in CloudWatch
- Checks control plane logging status

**Why it matters**:
- Provides visibility into cluster operations
- Essential for troubleshooting authentication and authorization issues
- Required for security auditing and compliance
- Helps identify performance bottlenecks

**Compliance**: ✅ PASS if control plane logging enabled, ❌ FAIL if disabled

---

### **C2: Cluster Authentication**
**Purpose**: Verifies proper authentication mechanisms are configured

**What it checks**:
- Checks for EKS Access Entries (modern API-based method)
- Falls back to aws-auth ConfigMap (traditional method)
- Verifies authentication configuration exists and is properly set up

**Why it matters**:
- Controls who can access the cluster
- EKS Access Entries provide better security than ConfigMap
- Essential for cluster security and access control
- Required for multi-user environments

**Compliance**: ✅ PASS if either authentication method properly configured, ❌ FAIL if neither found

---

### **C3: Running Large Clusters**
**Purpose**: Identifies large clusters (>1000 services) and checks for scale optimizations

**What it checks**:
- Counts total services in the cluster
- If >1000 services, checks for:
  - kube-proxy IPVS mode (better than iptables at scale)
  - AWS VPC CNI IP caching (WARM_IP_TARGET setting)

**Why it matters**:
- Large clusters face performance challenges with default settings
- iptables mode becomes inefficient with many services
- IP caching prevents EC2 API throttling
- Critical for maintaining performance at scale

**Compliance**: 
- ✅ PASS if <1000 services (no optimization needed)
- ✅ PASS if >1000 services with proper optimizations
- ❌ FAIL if >1000 services without optimizations

---

### **C4: EKS Control Plane Endpoint Access Control**
**Purpose**: Ensures API server endpoint access is properly restricted

**What it checks**:
- Examines cluster endpoint access configuration
- Checks public/private access settings
- Verifies CIDR restrictions on public access
- Flags unrestricted public access (0.0.0.0/0)

**Why it matters**:
- Prevents unauthorized access to cluster API
- Reduces attack surface
- Best practice for production clusters
- Required for security compliance

**Compliance**: ✅ PASS if access properly restricted, ❌ FAIL if unrestricted public access

---

### **C5: Avoid Catch-All Admission Webhooks**
**Purpose**: Identifies overly broad admission webhooks that could impact performance

**What it checks**:
- Scans MutatingWebhookConfiguration and ValidatingWebhookConfiguration
- Identifies webhooks with:
  - Missing namespace/object selectors
  - Wildcard (*) in API groups, versions, or resources
  - Overly permissive scope settings

**Why it matters**:
- Catch-all webhooks intercept ALL matching requests
- Can cause significant performance degradation
- May lead to unexpected behavior
- Difficult to troubleshoot

**Compliance**: ✅ PASS if no catch-all webhooks found, ❌ FAIL if overly broad webhooks detected

---

### **D1: Use Kubernetes Cluster Autoscaler or Karpenter**
**Purpose**: Ensures automatic node scaling capability is available

**What it checks**:
- Looks for Cluster Autoscaler deployment
- Checks for Karpenter installation (namespace, deployments, CRDs)
- Verifies at least one node autoscaling solution exists

**Why it matters**:
- Automatically scales worker nodes based on demand
- Prevents resource shortages during traffic spikes
- Reduces costs by scaling down unused nodes
- Essential for dynamic workloads

**Compliance**: ✅ PASS if either solution found, ❌ FAIL if neither exists

---

### **D2: Worker Nodes Spread Across Multiple AZs**
**Purpose**: Ensures high availability through multi-AZ node distribution

**What it checks**:
- Examines all worker nodes
- Counts nodes per availability zone using node labels
- Checks for balanced distribution across AZs (within 20% variance)

**Why it matters**:
- Protects against AZ-level failures
- Improves application availability
- Better resource distribution
- Required for production workloads

**Compliance**: 
- ✅ PASS if nodes spread across multiple AZs with balanced distribution
- ❌ FAIL if single AZ or uneven distribution

---

### **D3: Configure Resource Requests/Limits**
**Purpose**: Ensures all deployments have proper resource constraints

**What it checks**:
- Examines all Deployments in target namespaces
- Verifies each container has CPU and memory requests AND limits
- Identifies deployments without complete resource specifications

**Why it matters**:
- Prevents resource starvation and noisy neighbor problems
- Enables proper scheduling decisions
- Required for Quality of Service guarantees
- Essential for cluster stability

**Compliance**: ✅ PASS if all deployments have complete resource specs, ❌ FAIL if any are missing

---

### **D4: Namespace ResourceQuotas**
**Purpose**: Ensures resource governance is in place for namespaces

**What it checks**:
- Focuses on `default` namespace and user-created namespaces
- Ignores system namespaces (`kube-system`, `kube-public`, `kube-node-lease`)
- Verifies ResourceQuota objects exist for target namespaces

**Why it matters**:
- Prevents resource abuse and overconsumption
- Enables multi-tenancy
- Controls cluster resource allocation
- Required for production environments

**Compliance**: ✅ PASS if all target namespaces have ResourceQuotas, ❌ FAIL if any are missing

---

### **D5: Namespace LimitRanges**
**Purpose**: Ensures default resource limits are configured for namespaces

**What it checks**:
- Focuses on `default` namespace and user-created namespaces
- Ignores system namespaces (`kube-system`, `kube-public`, `kube-node-lease`)
- Verifies LimitRange objects exist for target namespaces

**Why it matters**:
- Provides default resource limits for containers
- Prevents containers from consuming unlimited resources
- Complements ResourceQuotas for complete resource governance
- Essential for cluster stability

**Compliance**: ✅ PASS if all target namespaces have LimitRanges, ❌ FAIL if any are missing

---

### **D6: Monitor CoreDNS Metrics**
**Purpose**: Ensures DNS service monitoring is configured

**What it checks**:
- Verifies CoreDNS deployment exists with metrics port (9153)
- Looks for ServiceMonitor (Prometheus Operator) or scrape configs
- Checks for DNS monitoring infrastructure

**Why it matters**:
- DNS is critical for cluster functionality
- Monitoring helps detect DNS performance issues
- Essential for troubleshooting connectivity problems
- Required for production operations

**Compliance**: ✅ PASS if CoreDNS metrics are monitored, ❌ FAIL if monitoring missing

---

### **D7: CoreDNS Configuration**
**Purpose**: Verifies CoreDNS is properly managed and configured

**What it checks**:
- For EKS auto mode clusters: Always passes (managed automatically)
- For regular clusters: Checks if CoreDNS is managed by EKS Managed Add-on
- Verifies CoreDNS deployment exists

**Why it matters**:
- EKS Managed Add-ons provide automatic updates and security patches
- Better integration with EKS platform
- Simplified management and maintenance
- Improved security posture

**Compliance**: 
- ✅ PASS for auto mode clusters (always managed)
- ✅ PASS if CoreDNS is EKS managed add-on
- ❌ FAIL if CoreDNS is self-managed in regular clusters

---

## Summary

The EKS Resiliency Checker provides a comprehensive evaluation of cluster health across 28 critical areas. Each check includes:

- **Clear compliance status** (✅ PASS / ❌ FAIL)
- **Detailed findings** with specific resources identified
- **Actionable remediation guidance** with code examples
- **Contextual explanations** of why each check matters

The tool helps ensure EKS clusters follow best practices for:
- **High Availability**: Multi-replica deployments, anti-affinity, PDBs
- **Scalability**: Autoscaling, resource management, large cluster optimizations  
- **Observability**: Monitoring, logging, metrics collection
- **Security**: Access control, endpoint restrictions, authentication
- **Operational Excellence**: Resource governance, graceful termination, service mesh

This comprehensive approach helps teams build and maintain resilient, production-ready EKS clusters.