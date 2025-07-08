# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Enhanced constants for the ROSA MCP Server based on e-book insights."""

# Original constants remain...
from .consts import *

# Enhanced constants from ROSA e-book analysis

# ROSA CLI Best Practices
ROSA_CLI_BEST_PRACTICES = {
    "rosa_cli_commands": {
        "account_management": [
                {
                        "command": "rosa login",
                        "syntax": "rosa login [OPTIONS]",
                        "options": [
                                "--token TOKEN",
                                "--insecure"
                        ],
                        "description": "Log in to your Red Hat account"
                },
                {
                        "command": "rosa logout",
                        "syntax": "rosa logout",
                        "description": "Log out of your Red Hat account"
                }
        ],
        "cluster_management": [
                {
                        "command": "rosa create cluster",
                        "syntax": "rosa create cluster --cluster-name NAME [OPTIONS]",
                        "options": [
                                "--cluster-name NAME",
                                "--machine-cidr CIDR",
                                "--service-cidr CIDR",
                                "--host-prefix PREFIX",
                                "--multi-az|--single-az",
                                "--watch",
                                "--dry-run"
                        ],
                        "description": "Create a new OpenShift cluster on AWS"
                },
                {
                        "command": "rosa list clusters",
                        "syntax": "rosa list clusters",
                        "description": "List all OpenShift clusters"
                },
                {
                        "command": "rosa describe cluster",
                        "syntax": "rosa describe cluster --cluster CLUSTER",
                        "options": [
                                "--cluster CLUSTER"
                        ],
                        "description": "Describe a specific OpenShift cluster"
                },
                {
                        "command": "rosa delete cluster",
                        "syntax": "rosa delete cluster --cluster CLUSTER",
                        "options": [
                                "--cluster CLUSTER",
                                "--watch",
                                "--force"
                        ],
                        "description": "Delete an OpenShift cluster"
                }
        ],
        "cluster_operations": [
                {
                        "command": "rosa restart cluster",
                        "syntax": "rosa restart cluster --cluster CLUSTER",
                        "options": [
                                "--cluster CLUSTER",
                                "--watch"
                        ],
                        "description": "Restart an OpenShift cluster"
                },
                {
                        "command": "rosa upgrade cluster",
                        "syntax": "rosa upgrade cluster --cluster CLUSTER [OPTIONS]",
                        "options": [
                                "--cluster CLUSTER",
                                "--version VERSION",
                                "--watch"
                        ],
                        "description": "Upgrade an OpenShift cluster to a newer version"
                }
        ]
},
}

# Networking Recommendations
ROSA_NETWORK_RECOMMENDATIONS = {
    "Networking Configuration Best Practices": [
        "Use private subnets for worker nodes and internal load balancers",
        "Configure network policies to restrict pod-to-pod communication",
        "Implement network encryption (IPsec or WireGuard) for cluster networking",
        "Use separate VPCs or subnets for production and non-production clusters",
        "Leverage AWS PrivateLink for secure communication with AWS services"
],
    "Private Cluster Setup Patterns": [
        "Deploy the cluster in a private VPC with no internet gateway",
        "Use AWS VPN or AWS Direct Connect for administrative access",
        "Configure bastion hosts or AWS Systems Manager for secure access",
        "Implement egress proxies or NAT gateways for controlled internet access",
        "Leverage AWS PrivateLink for secure communication with AWS services"
],
    "Ingress Controller Configurations": [
        "Use the ROSA-managed AWS Load Balancer Controller for ingress",
        "Configure SSL/TLS termination at the load balancer level",
        "Implement path-based routing for multiple applications",
        "Enable AWS WAF for web application firewall protection",
        "Leverage AWS Global Accelerator for global load balancing"
],
    "Load Balancer Recommendations": [
        "Use AWS Network Load Balancers for high performance and low latency",
        "Configure cross-zone load balancing for high availability",
        "Implement health checks and target group configurations",
        "Enable access logging and monitoring for load balancers",
        "Leverage AWS Global Accelerator for global load balancing"
],
    "Security Group and Firewall Rules": [
        "Restrict inbound traffic to control plane and worker nodes",
        "Allow only necessary ports and protocols for cluster communication",
        "Implement security group rules based on least privilege principle",
        "Use AWS Network Firewall for distributed firewall protection",
        "Leverage AWS Security Hub for continuous security monitoring"
],
}

# Operational Best Practices

# Cost Optimization Strategies
ROSA_COST_OPTIMIZATION = {
    "cost_optimization_strategies": [
        "Utilize AWS Cost Explorer to monitor and analyze costs",
        "Implement tagging strategies for better cost allocation and tracking",
        "Leverage AWS Auto Scaling to automatically scale resources based on demand",
        "Consider using AWS Reserved Instances for long-term workloads",
        "Implement AWS Trusted Advisor recommendations for cost optimization",
        "Regularly review and right-size resources based on utilization"
],
    "instance_type_recommendations": [
        "For general-purpose workloads, consider using AWS EC2 instances from the M5 or M6g family",
        "For compute-intensive workloads, consider using AWS EC2 instances from the C5 or C6g family",
        "For memory-intensive workloads, consider using AWS EC2 instances from the R5 or R6g family",
        "For GPU-accelerated workloads, consider using AWS EC2 instances from the P3 or G4 family",
        "For ARM-based workloads, consider using AWS Graviton instances from the M6g or C6g family"
],
    "resource_sizing_guidelines": [
        "Monitor resource utilization and scale resources based on actual demand",
        "Use AWS Auto Scaling to automatically scale resources based on defined metrics",
        "Consider using AWS CloudWatch to set alarms and notifications for resource utilization",
        "Follow AWS best practices for sizing resources based on workload requirements",
        "Regularly review and right-size resources based on utilization patterns"
],
    "reserved_instance_patterns": [
        "Analyze historical usage patterns to identify long-term, predictable workloads",
        "Consider using AWS Reserved Instances for long-term, predictable workloads",
        "Utilize AWS Cost Explorer to identify potential savings with Reserved Instances",
        "Implement a centralized Reserved Instance management strategy",
        "Regularly review and modify Reserved Instance commitments based on changing workload patterns"
],
    "spot_instance_usage": [
        "Identify workloads that can tolerate interruptions and are suitable for Spot Instances",
        "Utilize AWS Auto Scaling to automatically scale Spot Instances based on demand",
        "Implement fault-tolerant architectures to handle Spot Instance interruptions",
        "Leverage AWS Spot Instance Advisor to identify potential savings with Spot Instances",
        "Regularly monitor and adjust Spot Instance usage based on pricing and availability"
],
}
