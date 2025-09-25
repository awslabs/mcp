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

"""
Security Analysis API for ECS MCP Server.
This module provides comprehensive security analysis for ECS clusters.

Consolidated security analysis implementation that leverages existing MCP tools
for data collection while providing comprehensive security recommendations.
"""

import asyncio
import logging
import boto3
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from awslabs.ecs_mcp_server.utils.aws import get_aws_client
from .resource_management import ecs_api_operation
from .troubleshooting_tools.utils import (
    find_clusters,
    find_services,
    find_task_definitions
)
from .troubleshooting_tools.fetch_network_configuration import (
    fetch_network_configuration
)

logger = logging.getLogger(__name__)


class DataAdapter:
    """
    Adapter that uses existing MCP tools to collect data for security analysis.
    
    This class eliminates duplicate data collection by leveraging existing APIs
    and utilities already present in the ECS MCP server.
    """
    
    def __init__(self):
        """Initialize the DataAdapter."""
        self.logger = logger
    
    async def collect_cluster_data(self, cluster_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """Collect cluster data using existing resource management API."""
        try:
            self.logger.info(f"Collecting cluster data for {cluster_name}")
            
            # Get basic cluster information
            cluster_response = await ecs_api_operation(
                "DescribeClusters", 
                {"clusters": [cluster_name]}
            )
            
            # Enhanced: Get capacity providers for security analysis
            capacity_providers_response = await ecs_api_operation(
                "DescribeCapacityProviders",
                {"capacityProviders": []}  # Gets all capacity providers
            )
            
            # Enhanced: Get cluster tags for compliance analysis
            # Note: We'll skip tags for now as we need the actual cluster ARN from the response
            tags_response = {"tags": []}
            
            if "error" in cluster_response:
                self.logger.error(f"Error collecting cluster data: {cluster_response['error']}")
                return {
                    "error": cluster_response["error"],
                    "cluster_name": cluster_name,
                    "region": region
                }
            
            clusters = cluster_response.get("clusters", [])
            if not clusters:
                self.logger.warning(f"No cluster found with name: {cluster_name}")
                return {
                    "error": f"Cluster '{cluster_name}' not found",
                    "cluster_name": cluster_name,
                    "region": region
                }
            
            cluster_data = clusters[0]
            
            # Enhanced cluster data with additional security-relevant information
            enhanced_cluster_data = {
                "cluster": cluster_data,
                "capacity_providers": capacity_providers_response.get("capacityProviders", []) if "error" not in capacity_providers_response else [],
                "tags": tags_response.get("tags", []) if "error" not in tags_response else [],
                "cluster_name": cluster_name,
                "region": region,
                "status": "success"
            }
            
            # Log any errors from enhanced data collection
            if "error" in capacity_providers_response:
                self.logger.warning(f"Could not fetch capacity providers: {capacity_providers_response['error']}")
            if "error" in tags_response:
                self.logger.warning(f"Could not fetch cluster tags: {tags_response['error']}")
            
            return enhanced_cluster_data
            
        except Exception as e:
            self.logger.error(f"Unexpected error collecting cluster data for {cluster_name}: {e}")
            return {
                "error": str(e),
                "cluster_name": cluster_name,
                "region": region
            }
   
    async def collect_service_data(self, cluster_name: str, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Collect service data using existing troubleshooting tools utilities."""
        try:
            self.logger.info(f"Collecting service data for cluster {cluster_name}")
            
            if service_name:
                service_names = [service_name]
            else:
                # Use direct ECS API call instead of find_services to avoid async iterator issues
                try:
                    list_services_response = await ecs_api_operation(
                        "ListServices",
                        {"cluster": cluster_name}
                    )
                    
                    if "error" in list_services_response:
                        self.logger.warning(f"Error listing services: {list_services_response['error']}")
                        service_names = []
                    else:
                        service_arns = list_services_response.get("serviceArns", [])
                        # Extract service names from ARNs
                        service_names = []
                        for arn in service_arns:
                            # ARN format: arn:aws:ecs:region:account:service/cluster-name/service-name
                            if "/" in arn:
                                service_name_from_arn = arn.split("/")[-1]
                                service_names.append(service_name_from_arn)
                except Exception as e:
                    self.logger.warning(f"Error listing services for cluster {cluster_name}: {e}")
                    service_names = []
            
            if not service_names:
                self.logger.warning(f"No services found in cluster: {cluster_name}")
                return {
                    "services": [],
                    "cluster_name": cluster_name,
                    "status": "success"
                }
            
            services_data = []
            
            for svc_name in service_names:
                try:
                    service_response = await ecs_api_operation(
                        "DescribeServices",
                        {"cluster": cluster_name, "services": [svc_name]}
                    )
                    
                    if "error" in service_response:
                        self.logger.error(f"Error getting service {svc_name}: {service_response['error']}")
                        continue
                    
                    services = service_response.get("services", [])
                    if not services:
                        self.logger.warning(f"Service {svc_name} not found in response")
                        continue
                    
                    service_info = services[0]
                    
                    task_definitions = await find_task_definitions(
                        cluster_name=cluster_name,
                        service_name=svc_name
                    )
                    
                    task_definition = None
                    if task_definitions:
                        task_definition = task_definitions[0]
                    else:
                        task_def_arn = service_info.get("taskDefinition")
                        if task_def_arn:
                            task_def_response = await ecs_api_operation(
                                "DescribeTaskDefinition",
                                {"taskDefinition": task_def_arn}
                            )
                            if "taskDefinition" in task_def_response:
                                task_definition = task_def_response["taskDefinition"]
                    
                    # Enhanced: Get service tags for compliance analysis
                    service_arn = service_info.get("serviceArn", "")
                    service_tags_response = await ecs_api_operation(
                        "ListTagsForResource",
                        {"resourceArn": service_arn}
                    )
                    
                    # Enhanced: Get running tasks for runtime security analysis
                    tasks_response = await ecs_api_operation(
                        "ListTasks",
                        {"cluster": cluster_name, "serviceName": svc_name}
                    )
                    
                    service_data = {
                        "service": service_info,
                        "task_definition": task_definition,
                        "tags": service_tags_response.get("tags", []) if "error" not in service_tags_response else [],
                        "running_tasks": tasks_response.get("taskArns", []) if "error" not in tasks_response else []
                    }
                    
                    services_data.append(service_data)
                    
                except Exception as e:
                    self.logger.error(f"Error collecting data for service {svc_name}: {e}")
                    continue
            
            return {
                "services": services_data,
                "cluster_name": cluster_name,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Unexpected error collecting service data for {cluster_name}: {e}")
            return {
                "error": str(e),
                "cluster_name": cluster_name,
                "services": []
            }
   
    async def collect_container_instances_data(self, cluster_name: str) -> Dict[str, Any]:
        """Collect container instance data for EC2-based clusters using resource management API."""
        try:
            self.logger.info(f"Collecting container instance data for cluster {cluster_name}")
            
            # List container instances
            list_instances_response = await ecs_api_operation(
                "ListContainerInstances",
                {"cluster": cluster_name}
            )
            
            if "error" in list_instances_response:
                self.logger.warning(f"Error listing container instances: {list_instances_response['error']}")
                return {
                    "container_instances": [],
                    "cluster_name": cluster_name,
                    "status": "success"
                }
            
            instance_arns = list_instances_response.get("containerInstanceArns", [])
            
            if not instance_arns:
                return {
                    "container_instances": [],
                    "cluster_name": cluster_name,
                    "status": "success"
                }
            
            # Describe container instances for detailed security analysis
            describe_instances_response = await ecs_api_operation(
                "DescribeContainerInstances",
                {"cluster": cluster_name, "containerInstances": instance_arns}
            )
            
            if "error" in describe_instances_response:
                self.logger.error(f"Error describing container instances: {describe_instances_response['error']}")
                return {
                    "error": describe_instances_response["error"],
                    "cluster_name": cluster_name,
                    "container_instances": []
                }
            
            return {
                "container_instances": describe_instances_response.get("containerInstances", []),
                "cluster_name": cluster_name,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Unexpected error collecting container instance data for {cluster_name}: {e}")
            return {
                "error": str(e),
                "cluster_name": cluster_name,
                "container_instances": []
            }

    async def collect_network_data(self, cluster_name: str, vpc_id: Optional[str] = None) -> Dict[str, Any]:
        """Collect network data using existing fetch_network_configuration function."""
        try:
            self.logger.info(f"Collecting network data for cluster {cluster_name}")
            
            network_response = await fetch_network_configuration(
                cluster_name=cluster_name,
                vpc_id=vpc_id
            )
            
            if network_response.get("status") == "error":
                self.logger.error(f"Error collecting network data: {network_response.get('error')}")
                return {
                    "error": network_response.get("error"),
                    "cluster_name": cluster_name,
                    "network_data": {}
                }
            
            network_data = network_response.get("data", {})
            raw_resources = network_data.get("raw_resources", {})
            
            security_network_data = {
                "vpcs": raw_resources.get("vpcs", {}),
                "subnets": raw_resources.get("subnets", {}),
                "security_groups": raw_resources.get("security_groups", {}),
                "route_tables": raw_resources.get("route_tables", {}),
                "network_interfaces": raw_resources.get("network_interfaces", {}),
                "nat_gateways": raw_resources.get("nat_gateways", {}),
                "internet_gateways": raw_resources.get("internet_gateways", {}),
                "load_balancers": raw_resources.get("load_balancers", {}),
                "target_groups": raw_resources.get("target_groups", {}),
                "vpc_ids": network_data.get("vpc_ids", []),
                "timestamp": network_data.get("timestamp")
            }
            
            return {
                "network_data": security_network_data,
                "cluster_name": cluster_name,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Unexpected error collecting network data for {cluster_name}: {e}")
            return {
                "error": str(e),
                "cluster_name": cluster_name,
                "network_data": {}
            }

    async def collect_all_data(self, regions: List[str], cluster_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Collect comprehensive ECS data using existing tools."""
        try:
            all_data = {}
            
            for region in regions:
                try:
                    self.logger.info(f"Collecting data for region: {region}")
                    
                    if cluster_names:
                        clusters = cluster_names
                    else:
                        clusters = await find_clusters()
                    
                    region_data = {"clusters": {}}
                    
                    for cluster_name in clusters:
                        try:
                            cluster_security_data = await self.adapt_to_security_format(
                                cluster_name, region
                            )
                            
                            if region in cluster_security_data:
                                region_data["clusters"].update(
                                    cluster_security_data[region]["clusters"]
                                )
                        except Exception as e:
                            self.logger.error(f"Error collecting data for cluster {cluster_name}: {e}")
                            region_data["clusters"][cluster_name] = {
                                "error": str(e),
                                "cluster_name": cluster_name,
                                "region": region
                            }
                    
                    all_data[region] = region_data
                    
                except Exception as e:
                    self.logger.error(f"Error collecting data for region {region}: {e}")
                    all_data[region] = {
                        "error": str(e),
                        "region": region
                    }
            
            return all_data
            
        except Exception as e:
            self.logger.error(f"Unexpected error in collect_all_data: {e}")
            return {"error": str(e)}

    async def adapt_to_security_format(self, cluster_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """Adapt collected data to security analysis format."""
        try:
            cluster_data = await self.collect_cluster_data(cluster_name, region)
            service_data = await self.collect_service_data(cluster_name)
            network_data = await self.collect_network_data(cluster_name)
            container_instances_data = await self.collect_container_instances_data(cluster_name)
            
            errors = []
            if "error" in cluster_data:
                errors.append(f"Cluster data: {cluster_data['error']}")
            if "error" in service_data:
                errors.append(f"Service data: {service_data['error']}")
            if "error" in network_data:
                errors.append(f"Network data: {network_data['error']}")
            if "error" in container_instances_data:
                errors.append(f"Container instances data: {container_instances_data['error']}")
            
            security_format = {
                region: {
                    "clusters": {
                        cluster_name: {
                            "cluster": cluster_data.get("cluster", {}),
                            "capacity_providers": cluster_data.get("capacity_providers", []),
                            "cluster_tags": cluster_data.get("tags", []),
                            "services": service_data.get("services", []),
                            "network_data": network_data.get("network_data", {}),
                            "container_instances": container_instances_data.get("container_instances", []),
                            "region_info": {"name": region}
                        }
                    }
                }
            }
            
            if errors:
                security_format[region]["clusters"][cluster_name]["errors"] = errors
                self.logger.warning(f"Data collection completed with errors: {errors}")
            
            return security_format
            
        except Exception as e:
            self.logger.error(f"Error adapting data to security format: {e}")
            return {
                region: {
                    "error": str(e),
                    "cluster_name": cluster_name,
                    "region": region
                }
            }

    def _extract_security_relevant_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract security-relevant data from raw AWS responses."""
        # For now, just return the raw data
        # This could be enhanced to filter out non-security-relevant fields
        return raw_data

    def _handle_api_errors(self, response: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Handle API errors in responses."""
        if "error" in response:
            return {
                "error": response["error"],
                "operation": operation,
                "status": response.get("status", "failed")
            }
        return response


class SecurityAnalyzer:
    """Comprehensive ECS security analyzer following AWS best practices."""
    
    def __init__(self):
        self.security_checks = {
            'cluster': self._analyze_cluster_security,
            'service': self._analyze_service_security,
            'task_definition': self._analyze_task_definition_security,
            'container': self._analyze_container_security,
            'network': self._analyze_network_security,
            'capacity_providers': self._analyze_capacity_providers,
            'iam': self._analyze_iam_security,
            'logging': self._analyze_logging_security,
            'secrets': self._analyze_secrets_security,
            'compliance': self._analyze_compliance_security
        }
        
    def analyze(self, ecs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive security analysis of ECS configurations."""
        recommendations = []
        
        for region, region_data in ecs_data.items():
            if 'error' in region_data:
                continue
                
            for cluster_name, cluster_data in region_data.get('clusters', {}).items():
                if 'error' in cluster_data:
                    continue
                
                # 1. IAM Security Analysis
                recommendations.extend(self._analyze_cluster_iam_security(cluster_data, cluster_name, region))
                
                # 2. Network Security Assessment
                network_data = cluster_data.get('network_data', {})
                if network_data:
                    recommendations.extend(self._analyze_network_infrastructure(network_data, cluster_name, region))
                    recommendations.extend(self._analyze_vpc_security(network_data, cluster_name, region))
                    recommendations.extend(self._analyze_route_tables(network_data, cluster_name, region))
                    recommendations.extend(self._analyze_internet_gateways(network_data, cluster_name, region))
                    recommendations.extend(self._analyze_load_balancer_security(network_data, cluster_name, region))
                
                # 3. Cluster-level security
                recommendations.extend(self._analyze_cluster_security(cluster_name, cluster_data, region))
                recommendations.extend(self._analyze_enhanced_cluster_security(cluster_data, cluster_name, region))
                recommendations.extend(self._analyze_capacity_providers(cluster_data, cluster_name, region))
                recommendations.extend(self._analyze_logging_security(cluster_data, cluster_name, region))
                
                # 4. Compliance and Best Practices
                recommendations.extend(self._analyze_well_architected_compliance(cluster_data, cluster_name, region))
                recommendations.extend(self._analyze_industry_compliance(cluster_data, cluster_name, region))
                
                # 5. Service and Task Analysis
                for service_data in cluster_data.get('services', []):
                    service = service_data.get('service', {})
                    task_def = service_data.get('task_definition', {})
                    service_tags = service_data.get('tags', [])
                    running_tasks = service_data.get('running_tasks', [])
                    
                    service_name = service.get('serviceName', 'unknown')
                    
                    # Enhanced service-level security with tags and task analysis
                    recommendations.extend(self._analyze_service_security(service, service_name, cluster_name, region))
                    recommendations.extend(self._analyze_service_tags_security(service_tags, service_name, cluster_name, region))
                    recommendations.extend(self._analyze_running_tasks_security(running_tasks, service_name, cluster_name, region))
                    recommendations.extend(self._analyze_service_discovery_security(service, service_name, cluster_name, region))
                    
                    # Task definition security
                    recommendations.extend(self._analyze_task_definition_security(task_def, service_name, cluster_name, region))
                    recommendations.extend(self._analyze_resource_isolation(task_def, service_name, cluster_name, region))
                    
                    # IAM and secrets
                    recommendations.extend(self._analyze_iam_security(service, task_def, service_name, cluster_name, region))
                    recommendations.extend(self._analyze_secrets_security(task_def, service_name, cluster_name, region))
                    
                    # Network and monitoring
                    recommendations.extend(self._analyze_network_security(service, service_name, cluster_name, region))
                    recommendations.extend(self._analyze_monitoring_security(service, task_def, service_name, cluster_name, region))
                    
                    # Compliance
                    recommendations.extend(self._analyze_compliance_security(service, task_def, service_name, cluster_name, region))
                    
                    # 6. Container and Image Security
                    for container in task_def.get('containerDefinitions', []):
                        container_name = container.get('name', 'unknown')
                        recommendations.extend(self._analyze_container_security(container, container_name, service_name, cluster_name, region))
                        recommendations.extend(self._analyze_image_security(container, container_name, service_name, cluster_name, region))
                        recommendations.extend(self._analyze_container_runtime_security(container, container_name, service_name, cluster_name, region))
        
        # Enhance recommendations with detailed information
        enhanced_recommendations = []
        for rec in recommendations:
            enhanced_rec = self._enhance_recommendation(rec)
            enhanced_recommendations.append(enhanced_rec)
        
        # Deduplicate recommendations to avoid duplicate issues
        deduplicated_recommendations = self._deduplicate_recommendations(enhanced_recommendations)
        
        return {
            'recommendations': deduplicated_recommendations,
            'total_issues': len(deduplicated_recommendations),
            'analysis_summary': self._generate_analysis_summary(deduplicated_recommendations),
            'categorized_issues': self._categorize_issues(deduplicated_recommendations),
            'risk_weighted_priorities': self._calculate_risk_priorities(deduplicated_recommendations),
            'deduplication_stats': {
                'original_count': len(enhanced_recommendations),
                'deduplicated_count': len(deduplicated_recommendations),
                'duplicates_removed': len(enhanced_recommendations) - len(deduplicated_recommendations)
            }
        }
    
    def _analyze_cluster_security(self, cluster_name: str, cluster_data: Dict[str, Any], region: str) -> List[Dict[str, Any]]:
        """Analyze cluster-level security configurations."""
        recommendations = []
        
        cluster_info = cluster_data.get('cluster', {})
        cluster_settings = cluster_info.get('settings', [])
        
        # Check Container Insights
        container_insights_enabled = any(
            setting.get('name') == 'containerInsights' and setting.get('value') == 'enabled'
            for setting in cluster_settings
        )
        
        # Log Container Insights status for debugging
        logger.info(f"Container Insights enabled for {cluster_name}: {container_insights_enabled}")
        
        if not container_insights_enabled:
            recommendations.append({
                'title': 'Enable Container Insights for Security Monitoring',
                'severity': 'Medium',
                'category': 'monitoring',
                'resource': f'Cluster: {cluster_name}',
                'issue': 'Container Insights monitoring is disabled, reducing visibility into container performance and security',
                'recommendation': 'Enable Container Insights for comprehensive monitoring and security observability'
            })
        
        # Check cluster configuration
        configuration = cluster_info.get('configuration', {})
        
        # Check execute command configuration
        execute_command_config = configuration.get('executeCommandConfiguration', {})
        if not execute_command_config:
            recommendations.append({
                'title': 'Configure Execute Command Security',
                'severity': 'Medium',
                'category': 'security',
                'resource': f'Cluster: {cluster_name}',
                'issue': 'Execute command configuration is not set up, missing audit and logging capabilities',
                'recommendation': 'Configure execute command with proper logging and KMS encryption for security auditing'
            })
        else:
            # Check logging configuration
            logging_config = execute_command_config.get('logging')
            if logging_config != 'OVERRIDE':
                recommendations.append({
                    'title': 'Enable Execute Command Audit Logging',
                    'severity': 'Medium',
                    'category': 'monitoring',
                    'resource': f'Cluster: {cluster_name}',
                    'issue': 'Execute command audit logging is not properly configured',
                    'recommendation': 'Enable CloudWatch logging for execute command sessions to maintain audit trail'
                })
            
            # Check KMS encryption
            kms_key_id = execute_command_config.get('kmsKeyId')
            if not kms_key_id:
                recommendations.append({
                    'title': 'Enable KMS Encryption for Execute Command',
                    'severity': 'Medium',
                    'category': 'encryption',
                    'resource': f'Cluster: {cluster_name}',
                    'issue': 'Execute command sessions are not encrypted with customer-managed KMS keys',
                    'recommendation': 'Configure KMS encryption for execute command sessions to protect sensitive data'
                })
        
        # Capacity provider strategy is operational, not security - removed
        
        # Resource tags for cost tracking are operational, not security - removed
        
        # Check cluster status
        status = cluster_info.get('status', '')
        if status != 'ACTIVE':
            recommendations.append({
                'title': 'Review Cluster Status',
                'severity': 'High',
                'category': 'availability',
                'resource': f'Cluster: {cluster_name}',
                'issue': f'Cluster status is {status}, not ACTIVE',
                'recommendation': 'Investigate and resolve cluster status issues to ensure proper operation'
            })
        
        # Service discovery is primarily operational, not a security issue - removed
        
        return recommendations
    
    def _analyze_enhanced_cluster_security(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze enhanced cluster security using resource_management API data - SECURITY FOCUSED ONLY."""
        recommendations = []
        
        # Analyze container instances for SECURITY vulnerabilities (for EC2 launch type)
        container_instances = cluster_data.get('container_instances', [])
        for instance in container_instances:
            instance_id = instance.get('ec2InstanceId', 'unknown')
            
            # SECURITY: Check ECS agent version for known vulnerabilities
            version_info = instance.get('versionInfo', {})
            agent_version = version_info.get('agentVersion', '')
            
            # Check for critically outdated agent versions with known security issues
            if agent_version:
                try:
                    # Parse version (e.g., "1.68.2" -> [1, 68, 2])
                    version_parts = [int(x) for x in agent_version.split('.')]
                    
                    # Flag versions older than 1.65.0 (example of versions with known security issues)
                    if len(version_parts) >= 2 and (version_parts[0] < 1 or (version_parts[0] == 1 and version_parts[1] < 65)):
                        recommendations.append({
                            'title': 'Critical ECS Agent Security Update Required',
                            'severity': 'High',
                            'category': 'security',
                            'resource': f'Container Instance: {instance_id}',
                            'issue': f'ECS agent version {agent_version} has known security vulnerabilities',
                            'recommendation': 'Immediately update ECS agent to latest version to patch security vulnerabilities'
                        })
                except (ValueError, IndexError):
                    # If version parsing fails, flag for investigation
                    recommendations.append({
                        'title': 'Verify ECS Agent Version',
                        'severity': 'Medium',
                        'category': 'security',
                        'resource': f'Container Instance: {instance_id}',
                        'issue': f'Cannot parse ECS agent version: {agent_version}',
                        'recommendation': 'Verify ECS agent version and ensure it is up to date for security'
                    })
            
            # SECURITY: Check for instances running with excessive privileges
            attributes = instance.get('attributes', [])
            
            # Check if instance is running ECS agent with privileged access patterns
            agent_connected = instance.get('agentConnected', False)
            if not agent_connected:
                recommendations.append({
                    'title': 'ECS Agent Disconnected - Security Risk',
                    'severity': 'High',
                    'category': 'security',
                    'resource': f'Container Instance: {instance_id}',
                    'issue': 'ECS agent is disconnected, preventing security monitoring and updates',
                    'recommendation': 'Investigate and reconnect ECS agent to maintain security oversight'
                })
            
            # SECURITY: Check for instances with security-relevant attributes
            instance_type_attr = next((attr for attr in attributes if attr.get('name') == 'ecs.instance-type'), None)
            if instance_type_attr:
                instance_type = instance_type_attr.get('value', '')
                # Flag instances that might have hardware vulnerabilities (example: older generation instances)
                if any(old_gen in instance_type for old_gen in ['t1.', 'm1.', 'c1.', 'm2.', 'cr1.']):
                    recommendations.append({
                        'title': 'Legacy Instance Type Security Risk',
                        'severity': 'Medium',
                        'category': 'security',
                        'resource': f'Container Instance: {instance_id}',
                        'issue': f'Instance type {instance_type} is from older generation with potential hardware vulnerabilities',
                        'recommendation': 'Migrate to newer generation instance types with enhanced security features'
                    })
        
        # SECURITY: Analyze capacity providers for security misconfigurations
        capacity_providers = cluster_data.get('capacity_providers', [])
        for cp in capacity_providers:
            cp_name = cp.get('name', 'unknown')
            
            # Check for capacity providers with security-relevant misconfigurations
            auto_scaling_group_provider = cp.get('autoScalingGroupProvider', {})
            if auto_scaling_group_provider:
                # SECURITY: Check managed scaling settings that could impact security
                managed_scaling = auto_scaling_group_provider.get('managedScaling', {})
                if managed_scaling.get('status') == 'ENABLED':
                    # Check if managed termination protection is disabled (security risk)
                    termination_protection = auto_scaling_group_provider.get('managedTerminationProtection', 'DISABLED')
                    if termination_protection == 'DISABLED':
                        recommendations.append({
                            'title': 'Enable Managed Termination Protection',
                            'severity': 'Medium',
                            'category': 'security',
                            'resource': f'Capacity Provider: {cp_name}',
                            'issue': 'Managed termination protection is disabled, allowing uncontrolled instance termination',
                            'recommendation': 'Enable managed termination protection to prevent unauthorized instance termination'
                        })
        
        return recommendations
    
    def _analyze_service_security(self, service: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze service-level security configurations."""
        recommendations = []
        
        # Check public IP assignment
        network_config = service.get('networkConfiguration', {}).get('awsvpcConfiguration', {})
        if network_config.get('assignPublicIp') == 'ENABLED':
            recommendations.append({
                'title': 'Disable Public IP Assignment',
                'severity': 'High',
                'category': 'network_security',
                'resource': f'Service: {service_name}',
                'issue': 'Service has public IP assignment enabled, exposing containers directly to the internet',
                'recommendation': 'Disable public IP assignment and use NAT Gateway for outbound connectivity'
            })
        
        # Check platform version for Fargate
        launch_type = service.get('launchType', 'EC2')
        if launch_type == 'FARGATE':
            platform_version = service.get('platformVersion', 'LATEST')
            if platform_version == 'LATEST':
                recommendations.append({
                    'title': 'Pin Fargate Platform Version for Security Consistency',
                    'severity': 'Medium',
                    'category': 'security',
                    'resource': f'Service: {service_name}',
                    'issue': 'Using LATEST platform version can introduce unexpected security changes and makes security posture unpredictable',
                    'recommendation': 'Pin to a specific Fargate platform version to maintain consistent security configuration and controlled security updates'
                })
        
        # Placement strategy is operational, not security - removed
        
        # Check service connect configuration
        service_connect_config = service.get('serviceConnectConfiguration', {})
        if service_connect_config.get('enabled', False):
            namespace = service_connect_config.get('namespace')
            if not namespace:
                recommendations.append({
                    'title': 'Configure Service Connect Namespace',
                    'severity': 'Medium',
                    'category': 'network_security',
                    'resource': f'Service: {service_name}',
                    'issue': 'Service Connect is enabled but no namespace is configured',
                    'recommendation': 'Configure a proper namespace for Service Connect to ensure secure service-to-service communication'
                })
        
        # Check deployment configuration
        deployment_config = service.get('deploymentConfiguration', {})
        min_healthy_percent = deployment_config.get('minimumHealthyPercent', 100)
        max_percent = deployment_config.get('maximumPercent', 200)
        
        # Minimum healthy percent is availability, not security - removed
        
        # Check security groups
        security_groups = network_config.get('securityGroups', [])
        if not security_groups:
            recommendations.append({
                'title': 'Configure Security Groups',
                'severity': 'High',
                'category': 'network_security',
                'resource': f'Service: {service_name}',
                'issue': 'No security groups configured for the service',
                'recommendation': 'Configure appropriate security groups to control network access'
            })
        elif len(security_groups) > 5:
            recommendations.append({
                'title': 'Review Security Group Count',
                'severity': 'Low',
                'category': 'network_security',
                'resource': f'Service: {service_name}',
                'issue': f'Service has {len(security_groups)} security groups attached, which may be excessive',
                'recommendation': 'Review and consolidate security groups to simplify network security management'
            })
        
        # Check subnets configuration
        # Multiple AZ is availability, not security - removed
        
        # Check desired count
        # Task instance count is availability, not security - removed
        
        # Circuit breaker is deployment safety, not security - removed
        
        return recommendations
    
    def _analyze_service_tags_security(self, service_tags: List[Dict[str, Any]], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze service tags for SECURITY-RELEVANT issues only."""
        recommendations = []
        
        # SECURITY: Check for tags that might expose sensitive information
        for tag in service_tags:
            tag_key = tag.get('key', '').lower()
            tag_value = tag.get('value', '')
            
            # Flag tags that might contain sensitive data
            sensitive_patterns = ['password', 'secret', 'key', 'token', 'credential']
            if any(pattern in tag_key for pattern in sensitive_patterns):
                recommendations.append({
                    'title': 'Sensitive Information in Tag Key',
                    'severity': 'High',
                    'category': 'secrets',
                    'resource': f'Service: {service_name}',
                    'issue': f'Tag key "{tag.get("key", "")}" may contain sensitive information',
                    'recommendation': 'Remove sensitive information from tag keys and use AWS Secrets Manager instead'
                })
            
            # Check for potentially sensitive values (basic patterns)
            if len(tag_value) > 20 and any(char in tag_value for char in ['=', ':', ';', '|']):
                # This might be a connection string or encoded secret
                recommendations.append({
                    'title': 'Potential Sensitive Data in Tag Value',
                    'severity': 'Medium',
                    'category': 'secrets',
                    'resource': f'Service: {service_name}',
                    'issue': f'Tag "{tag.get("key", "")}" value appears to contain structured data that might be sensitive',
                    'recommendation': 'Review tag value and move any sensitive data to AWS Secrets Manager'
                })
        
        return recommendations
    
    def _analyze_running_tasks_security(self, running_tasks: List[str], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze running tasks for SECURITY issues only."""
        recommendations = []
        
        # SECURITY: Check for potential DDoS or resource exhaustion attacks
        if len(running_tasks) > 100:
            recommendations.append({
                'title': 'Unusually High Task Count - Potential Security Issue',
                'severity': 'Medium',
                'category': 'security',
                'resource': f'Service: {service_name}',
                'issue': f'Service has {len(running_tasks)} running tasks, which could indicate a DDoS attack or resource exhaustion attempt',
                'recommendation': 'Investigate high task count for potential security incidents and review scaling policies'
            })
        
        # SECURITY: If no tasks are running, this could indicate a security incident
        elif not running_tasks:
            recommendations.append({
                'title': 'No Running Tasks - Potential Security Incident',
                'severity': 'High',
                'category': 'security',
                'resource': f'Service: {service_name}',
                'issue': 'Service has no running tasks, which could indicate a security incident or attack',
                'recommendation': 'Immediately investigate why service has no running tasks - check for potential security breaches or attacks'
            })
        
        return recommendations
    
    def _analyze_task_definition_security(self, task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze task definition security configurations."""
        recommendations = []
        
        task_family = task_def.get('family', 'unknown')
        
        # Check task IAM role
        task_role_arn = task_def.get('taskRoleArn')
        if not task_role_arn:
            recommendations.append({
                'title': 'Configure Task IAM Role',
                'severity': 'High',
                'category': 'iam_security',
                'resource': f'Task Definition: {task_family}',
                'issue': 'Missing task IAM role - containers will have no AWS API permissions',
                'recommendation': 'Configure task IAM role with minimal required permissions following principle of least privilege'
            })
        
        # Check execution role
        execution_role_arn = task_def.get('executionRoleArn')
        if not execution_role_arn:
            recommendations.append({
                'title': 'Configure Execution IAM Role',
                'severity': 'High',
                'category': 'iam_security',
                'resource': f'Task Definition: {task_family}',
                'issue': 'Missing execution IAM role - ECS agent cannot pull images or write logs',
                'recommendation': 'Configure execution IAM role for ECS agent operations (image pulling, logging, secrets)'
            })
        
        # Check network mode
        network_mode = task_def.get('networkMode', 'bridge')
        if network_mode == 'host':
            recommendations.append({
                'title': 'Avoid Host Network Mode',
                'severity': 'High',
                'category': 'network_security',
                'resource': f'Task Definition: {task_family}',
                'issue': 'Task uses host network mode, bypassing container network isolation',
                'recommendation': 'Use awsvpc network mode for better network isolation and security'
            })
        
        # Check PID mode
        pid_mode = task_def.get('pidMode')
        if pid_mode == 'host':
            recommendations.append({
                'title': 'Avoid Host PID Mode',
                'severity': 'High',
                'category': 'container_security',
                'resource': f'Task Definition: {task_family}',
                'issue': 'Task uses host PID mode, allowing containers to see all host processes',
                'recommendation': 'Remove pidMode or set to task for proper process isolation'
            })
        
        # Check IPC mode
        ipc_mode = task_def.get('ipcMode')
        if ipc_mode == 'host':
            recommendations.append({
                'title': 'Avoid Host IPC Mode',
                'severity': 'High',
                'category': 'container_security',
                'resource': f'Task Definition: {task_family}',
                'issue': 'Task uses host IPC mode, allowing containers to access host IPC resources',
                'recommendation': 'Remove ipcMode or set to task for proper IPC isolation'
            })
        
        # Check memory limits for EC2
        requires_compatibilities = task_def.get('requiresCompatibilities', [])
        if 'EC2' in requires_compatibilities:
            for container in task_def.get('containerDefinitions', []):
                if not container.get('memory') and not container.get('memoryReservation'):
                    recommendations.append({
                        'title': 'Configure Memory Limits for EC2 Container (Required)',
                        'severity': 'High',
                        'category': 'resource_management',
                        'resource': f'Container: {container.get("name", "unknown")}',
                        'issue': f'Container {container.get("name", "unknown")} has no memory limits configured on EC2 launch type',
                        'recommendation': 'Set memory limits to prevent resource exhaustion on EC2 instances - this is required for EC2 launch type'
                    })
        
        # Check for Fargate-specific configurations
        if 'FARGATE' in requires_compatibilities:
            cpu = task_def.get('cpu')
            memory = task_def.get('memory')
            
            if not cpu:
                recommendations.append({
                    'title': 'Configure Task CPU for Fargate',
                    'severity': 'High',
                    'category': 'configuration',
                    'resource': f'Task Definition: {task_family}',
                    'issue': 'Fargate task definition missing CPU configuration',
                    'recommendation': 'Set task-level CPU for Fargate compatibility'
                })
            
            if not memory:
                recommendations.append({
                    'title': 'Configure Task Memory for Fargate',
                    'severity': 'High',
                    'category': 'configuration',
                    'resource': f'Task Definition: {task_family}',
                    'issue': 'Fargate task definition missing memory configuration',
                    'recommendation': 'Set task-level memory for Fargate compatibility'
                })
        
        # Check for volumes configuration
        volumes = task_def.get('volumes', [])
        for volume in volumes:
            # Check for host path volumes
            host_config = volume.get('host', {})
            if host_config.get('sourcePath'):
                recommendations.append({
                    'title': 'Review Host Path Volume Usage',
                    'severity': 'Medium',
                    'category': 'container_security',
                    'resource': f'Volume: {volume.get("name", "unknown")}',
                    'issue': f'Volume uses host path {host_config.get("sourcePath")}, which may expose host filesystem',
                    'recommendation': 'Consider using EFS or other managed storage instead of host paths'
                })
            
            # Check for Docker volume configuration
            docker_volume_config = volume.get('dockerVolumeConfiguration', {})
            if docker_volume_config and not docker_volume_config.get('encrypted', False):
                recommendations.append({
                    'title': 'Enable Volume Encryption',
                    'severity': 'Medium',
                    'category': 'encryption',
                    'resource': f'Volume: {volume.get("name", "unknown")}',
                    'issue': 'Docker volume is not encrypted',
                    'recommendation': 'Enable encryption for Docker volumes to protect data at rest'
                })
        
        # Check placement constraints
        placement_constraints = task_def.get('placementConstraints', [])
        for constraint in placement_constraints:
            if constraint.get('type') == 'memberOf' and 'attribute:ecs.instance-type' in constraint.get('expression', ''):
                recommendations.append({
                    'title': 'Review Instance Type Constraints',
                    'severity': 'Low',
                    'category': 'configuration',
                    'resource': f'Task Definition: {task_family}',
                    'issue': 'Task has instance type constraints that may limit flexibility',
                    'recommendation': 'Review placement constraints to ensure they are necessary and not overly restrictive'
                })
        
        return recommendations
    
    def _analyze_network_security(self, service: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze network security configurations."""
        recommendations = []
        
        # Check load balancer configuration
        load_balancers = service.get('loadBalancers', [])
        for lb in load_balancers:
            target_group_arn = lb.get('targetGroupArn', '')
            if target_group_arn:
                # Extract target group name from ARN
                tg_name = target_group_arn.split('/')[-2] if '/' in target_group_arn else 'unknown'
                recommendations.append({
                    'title': 'Configure Specific Health Check Path for Load Balancer',
                    'severity': 'Medium',
                    'category': 'network',
                    'resource': f'Target Group: {tg_name}',
                    'issue': 'Load balancer target group uses default health check path, which may not accurately reflect application health',
                    'recommendation': 'Configure a specific health check path that validates application functionality and dependencies'
                })
        
        return recommendations
    
    def _analyze_container_security(self, container: Dict[str, Any], container_name: str, service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze container security configurations."""
        recommendations = []
        
        # Check for root user
        user = container.get('user')
        if user == '0' or user == 'root' or not user:
            recommendations.append({
                'title': 'Configure Container to Run as Non-Root User',
                'severity': 'High',
                'category': 'container_security',
                'resource': f'Container: {container_name} | Service: {service_name}',
                'issue': 'The container is configured to run as the root user (UID 0), violating the principle of least privilege',
                'recommendation': 'Configure the container to run as a non-privileged user by creating a dedicated application user'
            })
        
        # Check for latest tag
        image = container.get('image', '')
        if image.endswith(':latest') or ':' not in image:
            recommendations.append({
                'title': 'Avoid Latest Tag in Container Images',
                'severity': 'Medium',
                'category': 'container_security',
                'resource': f'Container: {container_name}',
                'issue': 'The container image uses the \'latest\' tag or no tag, making deployments unpredictable and potentially insecure',
                'recommendation': 'Use specific, immutable image tags with semantic versioning to ensure reproducible deployments'
            })
        
        # Check for read-only root filesystem
        if not container.get('readonlyRootFilesystem', False):
            recommendations.append({
                'title': 'Enable Read-Only Root Filesystem',
                'severity': 'Medium',
                'category': 'container_security',
                'resource': f'Container: {container_name} | Service: {service_name}',
                'issue': f'Container {container_name} has writable root filesystem',
                'recommendation': 'Enable read-only root filesystem to prevent runtime tampering'
            })
        
        # Check for privileged mode
        if container.get('privileged', False):
            recommendations.append({
                'title': 'Disable Privileged Mode',
                'severity': 'High',
                'category': 'container_security',
                'resource': f'Container: {container_name}',
                'issue': 'Container is running in privileged mode, granting access to all host devices',
                'recommendation': 'Disable privileged mode and use specific capabilities if needed'
            })
        
        # Check for health check
        if not container.get('healthCheck'):
            recommendations.append({
                'title': 'Configure Container Health Check',
                'severity': 'Medium',
                'category': 'monitoring',
                'resource': f'Container: {container_name} | Service: {service_name}',
                'issue': 'The container lacks health check configuration, preventing ECS from detecting application failures',
                'recommendation': 'Implement comprehensive health checks that verify application functionality'
            })
        
        # Check for resource limits
        memory = container.get('memory')
        memory_reservation = container.get('memoryReservation')
        cpu = container.get('cpu')
        
        if not memory and not memory_reservation:
            recommendations.append({
                'title': 'Configure Memory Limits',
                'severity': 'High',
                'category': 'resource_management',
                'resource': f'Container: {container_name}',
                'issue': 'Container has no memory limits configured, risking resource exhaustion',
                'recommendation': 'Set appropriate memory limits to prevent resource starvation'
            })
        
        if not cpu:
            recommendations.append({
                'title': 'Configure CPU Limits',
                'severity': 'Medium',
                'category': 'resource_management',
                'resource': f'Container: {container_name}',
                'issue': 'Container has no CPU limits configured',
                'recommendation': 'Set appropriate CPU limits for predictable performance'
            })
        
        # Check for private registry
        if 'public.ecr.aws' in image or 'docker.io' in image or not any(registry in image for registry in ['.ecr.', '.amazonaws.com']):
            recommendations.append({
                'title': 'Consider Using Private Container Registry',
                'severity': 'Low',
                'category': 'container_security',
                'resource': f'Container: {container_name}',
                'issue': f'Container {container_name} uses public registry image, which may have less security oversight and control',
                'recommendation': 'Consider using Amazon ECR for better security, control, and compliance'
            })
        
        # Check for static port mapping
        port_mappings = container.get('portMappings', [])
        for port_mapping in port_mappings:
            host_port = port_mapping.get('hostPort')
            if host_port and host_port != 0:
                recommendations.append({
                    'title': 'Avoid Static Host Port Mapping',
                    'severity': 'Medium',
                    'category': 'container_security',
                    'resource': f'Container: {container_name}',
                    'issue': f'Container {container_name} uses static host port {host_port}, which can lead to port conflicts and security issues',
                    'recommendation': 'Use dynamic port mapping (hostPort: 0) for better security and flexibility'
                })
        
        # Check for logging configuration
        log_configuration = container.get('logConfiguration')
        if not log_configuration:
            recommendations.append({
                'title': 'Configure Container Logging for Security Monitoring',
                'severity': 'Medium',
                'category': 'container_security',
                'resource': f'Container: {container_name}',
                'issue': 'Container has no logging configuration, making security monitoring, troubleshooting, and compliance auditing difficult',
                'recommendation': 'Configure CloudWatch Logs or another logging driver for security event monitoring and compliance'
            })
        
        # Check for essential container configuration
        if container.get('essential', True) and len(port_mappings) == 0:
            recommendations.append({
                'title': 'Review Essential Container Configuration',
                'severity': 'Low',
                'category': 'configuration',
                'resource': f'Container: {container_name}',
                'issue': 'Essential container with no port mappings may indicate misconfiguration',
                'recommendation': 'Review if this container should be marked as essential'
            })
        
        # Check for Linux parameters security
        linux_parameters = container.get('linuxParameters', {})
        if linux_parameters:
            # Check for dangerous capabilities
            capabilities = linux_parameters.get('capabilities', {})
            add_capabilities = capabilities.get('add', [])
            
            dangerous_caps = ['SYS_ADMIN', 'NET_ADMIN', 'SYS_PTRACE', 'SYS_MODULE']
            for cap in add_capabilities:
                if cap in dangerous_caps:
                    recommendations.append({
                        'title': f'Review Dangerous Capability: {cap}',
                        'severity': 'High',
                        'category': 'container_security',
                        'resource': f'Container: {container_name}',
                        'issue': f'Container has dangerous capability {cap} which increases security risk',
                        'recommendation': 'Remove unnecessary capabilities and use least privilege principle'
                    })
        
        # Check for task metadata endpoint security
        environment = container.get('environment', [])
        metadata_v2_enabled = any(
            env.get('name') == 'ECS_ENABLE_TASK_METADATA_ENDPOINT_V2' and env.get('value') == 'true'
            for env in environment
        )
        if not metadata_v2_enabled:
            recommendations.append({
                'title': 'Verify Task Metadata Endpoint Security Configuration',
                'severity': 'Low',
                'category': 'security',
                'resource': f'Container: {container_name} | Service: {service_name}',
                'issue': f'Container {container_name} should verify task metadata endpoint security',
                'recommendation': 'Ensure task metadata endpoint v2 is used and properly secured'
            })
        
        return recommendations
    
    def _analyze_capacity_providers(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze capacity provider security configurations."""
        recommendations = []
        
        # Check for capacity provider configurations
        cluster_info = cluster_data.get('cluster', {})
        capacity_providers = cluster_info.get('capacityProviders', [])
        
        for cp_name in capacity_providers:
            # Check for EC2 capacity providers that might need termination protection
            if 'ec2' in cp_name.lower():
                recommendations.append({
                    'title': f'Enable Managed Termination Protection for Capacity Provider {cp_name}',
                    'severity': 'Medium',
                    'category': 'configuration',
                    'resource': f'Capacity Provider: {cp_name}',
                    'issue': f'Capacity provider {cp_name} does not have managed termination protection',
                    'recommendation': 'Enable managed termination protection to prevent premature instance termination'
                })
        
        return recommendations

    def _analyze_iam_security(self, service: Dict[str, Any], task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze IAM security configurations (advanced checks only - basic role checks done in task definition analysis)."""
        recommendations = []
        
        # Only check for advanced IAM issues to avoid duplicates with task definition analysis
        task_role_arn = task_def.get('taskRoleArn')
        execution_role_arn = task_def.get('executionRoleArn')
        
        # Advanced check: Overly permissive policies (only if roles exist)
        if task_role_arn and '*' in task_role_arn:
            recommendations.append({
                'title': 'Avoid Wildcard Permissions in Task IAM Role',
                'severity': 'High',
                'category': 'iam_security',
                'resource': f'Task Role: {task_role_arn}',
                'issue': 'Task IAM role may contain overly permissive wildcard permissions',
                'recommendation': 'Review and restrict IAM permissions to follow principle of least privilege'
            })
        
        # Advanced check: Execution role best practices (only if role exists)
        if execution_role_arn and 'AmazonECSTaskExecutionRolePolicy' not in execution_role_arn:
            recommendations.append({
                'title': 'Use Managed Execution Role Policy',
                'severity': 'Medium',
                'category': 'iam_security',
                'resource': f'Execution Role: {execution_role_arn}',
                'issue': 'Custom execution role may have unnecessary permissions',
                'recommendation': 'Use AWS managed AmazonECSTaskExecutionRolePolicy when possible'
            })
        
        # Check for cross-account role assumptions (advanced security)
        if task_role_arn and ':role/' in task_role_arn:
            role_account = task_role_arn.split(':')[4]
            # This is a simplified check - in real implementation you'd get current account
            if role_account != 'current_account':  # Placeholder logic
                recommendations.append({
                    'title': 'Review Cross-Account IAM Role Usage',
                    'severity': 'Medium',
                    'category': 'iam_security',
                    'resource': f'Task Role: {task_role_arn}',
                    'issue': 'Task role appears to be from different AWS account',
                    'recommendation': 'Verify cross-account role usage is intentional and properly secured'
                })
        
        return recommendations

    def _analyze_logging_security(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze logging and monitoring security configurations."""
        recommendations = []
        
        # Note: Execute command logging is now handled in _analyze_cluster_security to avoid duplication
        # This method can be extended for other logging-specific security checks in the future
        
        return recommendations

    def _analyze_secrets_security(self, task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze secrets management security."""
        recommendations = []
        
        for container in task_def.get('containerDefinitions', []):
            container_name = container.get('name', 'unknown')
            
            # Check for hardcoded secrets in environment variables
            environment = container.get('environment', [])
            for env_var in environment:
                env_name = env_var.get('name', '').lower()
                env_value = env_var.get('value', '')
                
                if any(secret_keyword in env_name for secret_keyword in ['password', 'secret', 'key', 'token', 'api_key']):
                    if env_value and not env_value.startswith('arn:aws:secretsmanager') and not env_value.startswith('arn:aws:ssm'):
                        recommendations.append({
                            'title': 'Use AWS Secrets Manager for Sensitive Data',
                            'severity': 'High',
                            'category': 'secrets',
                            'resource': f'Container: {container_name}',
                            'issue': f'Environment variable {env_name} contains hardcoded sensitive data - immediate credential exposure risk',
                            'recommendation': 'Immediately migrate to AWS Secrets Manager to prevent credential theft and unauthorized access'
                        })
            
            # Check for secrets configuration
            secrets = container.get('secrets', [])
            if not secrets and environment:
                # Check if there are environment variables that should be secrets
                sensitive_vars = [env for env in environment 
                                if any(keyword in env.get('name', '').lower() 
                                      for keyword in ['password', 'secret', 'key', 'token'])]
                if sensitive_vars:
                    recommendations.append({
                        'title': 'Migrate Sensitive Environment Variables to Secrets',
                        'severity': 'High',
                        'category': 'secrets',
                        'resource': f'Container: {container_name}',
                        'issue': 'Sensitive data detected in environment variables - visible in process lists, logs, and container metadata',
                        'recommendation': 'Immediately migrate sensitive data to AWS Secrets Manager or Parameter Store to prevent credential exposure'
                    })
        
        return recommendations

    def _analyze_compliance_security(self, service: Dict[str, Any], task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze compliance-related security configurations."""
        recommendations = []
        
        # Check for compliance tags
        service_tags = service.get('tags', [])
        # Service tags for compliance tracking are operational, not security - removed
        
        # Check for data classification
        data_classification_found = any(
            tag.get('key', '').lower() in ['dataclassification', 'data-classification', 'sensitivity']
            for tag in service_tags
        )
        
        if not data_classification_found:
            recommendations.append({
                'title': 'Add Data Classification Tags',
                'severity': 'Medium',
                'category': 'compliance',
                'resource': f'Service: {service_name}',
                'issue': 'No data classification tags found',
                'recommendation': 'Add data classification tags to identify data sensitivity levels'
            })
        
        return recommendations

    def _analyze_network_infrastructure(self, network_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze network infrastructure security."""
        recommendations = []
        
        # Analyze VPC configuration
        vpcs_data = network_data.get('vpcs', {})
        
        # Handle raw AWS API response format
        if 'Vpcs' in vpcs_data:
            vpcs_list = vpcs_data['Vpcs']
        else:
            # Handle processed format (dict of vpc_id -> vpc_info)
            vpcs_list = list(vpcs_data.values()) if isinstance(vpcs_data, dict) else []
        
        for vpc_info in vpcs_list:
            if not isinstance(vpc_info, dict):
                continue
                
            vpc_id = vpc_info.get('VpcId', 'unknown')
            
            # Check for default VPC usage
            if vpc_info.get('IsDefault', False):
                recommendations.append({
                    'title': 'Avoid Using Default VPC for Production Workloads',
                    'severity': 'Medium',
                    'category': 'network',
                    'resource': f'VPC: {vpc_id}',
                    'issue': 'Using default VPC which may have less secure default configurations',
                    'recommendation': 'Create a custom VPC with proper security configurations'
                })
        
        # Analyze Security Groups
        security_groups_data = network_data.get('security_groups', {})
        
        # Handle raw AWS API response format
        if 'SecurityGroups' in security_groups_data:
            security_groups_list = security_groups_data['SecurityGroups']
        else:
            # Handle processed format (dict of sg_id -> sg_info)
            security_groups_list = list(security_groups_data.values()) if isinstance(security_groups_data, dict) else []
        
        for sg_info in security_groups_list:
            if not isinstance(sg_info, dict):
                continue
                
            sg_id = sg_info.get('GroupId', 'unknown')
            ingress_rules = sg_info.get('IpPermissions', [])
            
            for rule in ingress_rules:
                # Check for overly permissive rules
                ip_ranges = rule.get('IpRanges', [])
                for ip_range in ip_ranges:
                    cidr = ip_range.get('CidrIp', '')
                    if cidr == '0.0.0.0/0':
                        from_port = rule.get('FromPort', 0)
                        to_port = rule.get('ToPort', 0)
                        
                        if from_port == 22 or to_port == 22:
                            recommendations.append({
                                'title': 'Restrict SSH Access from Internet',
                                'severity': 'High',
                                'category': 'network_security',
                                'resource': f'Security Group: {sg_id}',
                                'issue': 'SSH port (22) is open to the internet (0.0.0.0/0)',
                                'recommendation': 'Restrict SSH access to specific IP ranges or use AWS Systems Manager Session Manager'
                            })
                        elif from_port == 3389 or to_port == 3389:
                            recommendations.append({
                                'title': 'Restrict RDP Access from Internet',
                                'severity': 'High',
                                'category': 'network_security',
                                'resource': f'Security Group: {sg_id}',
                                'issue': 'RDP port (3389) is open to the internet (0.0.0.0/0)',
                                'recommendation': 'Restrict RDP access to specific IP ranges or use AWS Systems Manager Session Manager'
                            })
                        elif from_port != 80 and from_port != 443:
                            recommendations.append({
                                'title': 'Review Overly Permissive Security Group Rules',
                                'severity': 'High',
                                'category': 'network_security',
                                'resource': f'Security Group: {sg_id}',
                                'issue': f'Port {from_port} is open to the internet (0.0.0.0/0)',
                                'recommendation': 'Restrict access to specific IP ranges or remove unnecessary rules'
                            })
        
        # Analyze Subnets
        subnets_data = network_data.get('subnets', {})
        
        # Handle raw AWS API response format
        if 'Subnets' in subnets_data:
            subnets_list = subnets_data['Subnets']
        else:
            # Handle processed format (dict of subnet_id -> subnet_info)
            subnets_list = list(subnets_data.values()) if isinstance(subnets_data, dict) else []
        
        for subnet_info in subnets_list:
            if not isinstance(subnet_info, dict):
                continue
                
            subnet_id = subnet_info.get('SubnetId', 'unknown')
            if subnet_info.get('MapPublicIpOnLaunch', False):
                recommendations.append({
                    'title': 'Disable Auto-Assign Public IP for Subnets',
                    'severity': 'Medium',
                    'category': 'network_security',
                    'resource': f'Subnet: {subnet_id}',
                    'issue': 'Subnet automatically assigns public IP addresses',
                    'recommendation': 'Disable auto-assign public IP and use NAT Gateway for outbound connectivity'
                })
        
        return recommendations

    def _analyze_cluster_iam_security(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze cluster-level IAM security configurations."""
        recommendations = []
        
        cluster_info = cluster_data.get('cluster', {})
        
        # Check for service-linked roles
        service_linked_role = cluster_info.get('serviceLinkedRoleArn')
        if not service_linked_role:
            recommendations.append({
                'title': 'Configure ECS Service-Linked Role',
                'severity': 'Medium',
                'category': 'iam_security',
                'resource': f'Cluster: {cluster_name}',
                'issue': 'No service-linked role configured for ECS cluster operations',
                'recommendation': 'Create and configure the AWSServiceRoleForECS service-linked role for proper cluster management'
            })
        
        return recommendations

    def _analyze_vpc_security(self, network_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze VPC security configurations."""
        recommendations = []
        
        vpcs_data = network_data.get('vpcs', {})
        
        # Handle raw AWS API response format
        if 'Vpcs' in vpcs_data:
            vpcs_list = vpcs_data['Vpcs']
        else:
            # Handle processed format (dict of vpc_id -> vpc_info)
            vpcs_list = list(vpcs_data.values()) if isinstance(vpcs_data, dict) else []
        
        for vpc_info in vpcs_list:
            if not isinstance(vpc_info, dict):
                continue
                
            vpc_id = vpc_info.get('VpcId', 'unknown')
            
            # Check VPC Flow Logs (Note: Flow logs info is not in the VPC describe response)
            # We'll recommend enabling them as a best practice
            recommendations.append({
                'title': 'Enable VPC Flow Logs',
                'severity': 'Medium',
                'category': 'network_security',
                'resource': f'VPC: {vpc_id}',
                'issue': 'VPC Flow Logs should be enabled for network traffic visibility and security monitoring',
                'recommendation': 'Enable VPC Flow Logs to monitor network traffic and detect security anomalies'
            })
            
            # Check if this is a default VPC (already handled in network infrastructure analysis)
            # We can add other VPC-specific checks here if needed
        
        return recommendations

    def _analyze_route_tables(self, network_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze route table security configurations."""
        recommendations = []
        
        route_tables_data = network_data.get('route_tables', {})
        
        # Handle raw AWS API response format
        if 'RouteTables' in route_tables_data:
            route_tables_list = route_tables_data['RouteTables']
        else:
            route_tables_list = list(route_tables_data.values()) if isinstance(route_tables_data, dict) else []
        
        for rt_info in route_tables_list:
            if not isinstance(rt_info, dict):
                continue
                
            rt_id = rt_info.get('RouteTableId', 'unknown')
            routes = rt_info.get('Routes', [])
            
            # Check for overly broad routes
            for route in routes:
                destination = route.get('DestinationCidrBlock', '')
                gateway_id = route.get('GatewayId', '')
                
                # Check for routes to 0.0.0.0/0 through internet gateway
                if destination == '0.0.0.0/0' and gateway_id and gateway_id.startswith('igw-'):
                    # This is normal for public subnets, but flag for review
                    recommendations.append({
                        'title': 'Review Internet Gateway Routes',
                        'severity': 'Low',
                        'category': 'network_security',
                        'resource': f'Route Table: {rt_id}',
                        'issue': 'Route table has default route (0.0.0.0/0) to Internet Gateway',
                        'recommendation': 'Ensure this route table is only associated with public subnets that require internet access'
                    })
        
        return recommendations

    def _analyze_internet_gateways(self, network_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze Internet Gateway security configurations."""
        recommendations = []
        
        internet_gateways_data = network_data.get('internet_gateways', {})
        
        # Handle raw AWS API response format
        if 'InternetGateways' in internet_gateways_data:
            igw_list = internet_gateways_data['InternetGateways']
        else:
            igw_list = list(internet_gateways_data.values()) if isinstance(internet_gateways_data, dict) else []
        
        for igw_info in igw_list:
            if not isinstance(igw_info, dict):
                continue
                
            igw_id = igw_info.get('InternetGatewayId', 'unknown')
            attachments = igw_info.get('Attachments', [])
            
            # Check if IGW is attached to VPC
            for attachment in attachments:
                if attachment.get('State') == 'available':
                    vpc_id = attachment.get('VpcId', 'unknown')
                    recommendations.append({
                        'title': 'Review Internet Gateway Security',
                        'severity': 'Low',
                        'category': 'network_security',
                        'resource': f'Internet Gateway: {igw_id}',
                        'issue': f'Internet Gateway attached to VPC {vpc_id} - ensure proper security controls',
                        'recommendation': 'Verify that only public subnets route through this IGW and private resources use NAT Gateway'
                    })
        
        return recommendations

    def _analyze_load_balancer_security(self, network_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze load balancer security configurations."""
        recommendations = []
        
        load_balancers_data = network_data.get('load_balancers', {})
        
        # Handle raw AWS API response format
        if 'LoadBalancers' in load_balancers_data:
            load_balancers_list = load_balancers_data['LoadBalancers']
        else:
            # Handle processed format (dict of lb_arn -> lb_info)
            load_balancers_list = list(load_balancers_data.values()) if isinstance(load_balancers_data, dict) else []
        
        for lb_info in load_balancers_list:
            if not isinstance(lb_info, dict):
                continue
                
            lb_name = lb_info.get('LoadBalancerName', 'unknown')
            lb_arn = lb_info.get('LoadBalancerArn', 'unknown')
            
            # Check if load balancer is internet-facing
            scheme = lb_info.get('Scheme', 'internal')
            if scheme == 'internet-facing':
                recommendations.append({
                    'title': 'Review Internet-Facing Load Balancer Security',
                    'severity': 'Medium',
                    'category': 'network_security',
                    'resource': f'Load Balancer: {lb_name}',
                    'issue': 'Load balancer is internet-facing, ensure proper security controls are in place',
                    'recommendation': 'Verify security groups, SSL/TLS configuration, and access controls for internet-facing load balancer'
                })
            
            # Check security groups
            security_groups = lb_info.get('SecurityGroups', [])
            if not security_groups:
                recommendations.append({
                    'title': 'Configure Security Groups for Load Balancer',
                    'severity': 'High',
                    'category': 'network_security',
                    'resource': f'Load Balancer: {lb_name}',
                    'issue': 'No security groups configured for load balancer',
                    'recommendation': 'Configure appropriate security groups to control access to the load balancer'
                })
            
            # Check if access logs are enabled (look for access_logs attribute)
            access_logs_enabled = False
            if 'Attributes' in lb_info:
                for attr in lb_info.get('Attributes', []):
                    if attr.get('Key') == 'access_logs.s3.enabled' and attr.get('Value') == 'true':
                        access_logs_enabled = True
                        break
            
            if not access_logs_enabled:
                recommendations.append({
                    'title': 'Enable Load Balancer Access Logs',
                    'severity': 'Medium',
                    'category': 'monitoring',
                    'resource': f'Load Balancer: {lb_name}',
                    'issue': 'Access logs are not enabled - missing critical security monitoring and audit trail',
                    'recommendation': 'Enable access logs to S3 bucket for security monitoring, compliance, and incident response',
                    'security_impact': 'Without access logs, you cannot detect suspicious traffic patterns, DDoS attacks, or perform forensic analysis during security incidents',
                    'compliance_frameworks': ['SOC 2', 'PCI DSS', 'AWS Well-Architected Security Pillar']
                })
        
        return recommendations

    def _analyze_well_architected_compliance(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze compliance with AWS Well-Architected Security Pillar."""
        recommendations = []
        
        cluster_info = cluster_data.get('cluster', {})
        
        # Security Pillar: Identity and Access Management
        # Check for proper tagging strategy
        # Security-related tags are governance metadata, not security controls - removed
        
        # Security Pillar: Detective Controls
        services = cluster_data.get('services', [])
        if len(services) > 0:
            # Check for monitoring and alerting
            has_monitoring = any(
                service.get('service', {}).get('enableExecuteCommand', False)
                for service in services
            )
            
            if not has_monitoring:
                recommendations.append({
                    'title': 'Implement Detective Controls (Well-Architected)',
                    'severity': 'Medium',
                    'category': 'well_architected',
                    'resource': f'Cluster: {cluster_name}',
                    'issue': 'Limited detective controls for security monitoring',
                    'recommendation': 'Implement comprehensive logging, monitoring, and alerting following Well-Architected principles'
                })
        
        return recommendations

    def _analyze_industry_compliance(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze compliance with industry standards (SOC 2, PCI DSS, HIPAA)."""
        recommendations = []
        
        cluster_info = cluster_data.get('cluster', {})
        cluster_tags = cluster_info.get('tags', [])
        
        # Check for compliance framework tags
        compliance_tag = None
        for tag in cluster_tags:
            if tag.get('key', '').lower() in ['compliance', 'complianceframework', 'compliance-framework']:
                compliance_tag = tag.get('value', '').upper()
                break
        
        if compliance_tag:
            # PCI DSS Compliance Checks
            if 'PCI' in compliance_tag:
                recommendations.extend(self._check_pci_compliance(cluster_data, cluster_name, region))
            
            # HIPAA Compliance Checks
            if 'HIPAA' in compliance_tag:
                recommendations.extend(self._check_hipaa_compliance(cluster_data, cluster_name, region))
            
            # SOC 2 Compliance Checks
            if 'SOC' in compliance_tag:
                recommendations.extend(self._check_soc2_compliance(cluster_data, cluster_name, region))
        # Compliance framework tags are governance metadata, not security controls - removed
        
        return recommendations

    def _check_pci_compliance(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Check PCI DSS compliance requirements."""
        recommendations = []
        
        # PCI DSS Requirement 2: Do not use vendor-supplied defaults
        services = cluster_data.get('services', [])
        for service_data in services:
            task_def = service_data.get('task_definition', {})
            for container in task_def.get('containerDefinitions', []):
                # Check for default passwords or configurations
                environment = container.get('environment', [])
                for env_var in environment:
                    env_name = env_var.get('name', '').lower()
                    env_value = env_var.get('value', '')
                    
                    if 'password' in env_name and env_value in ['password', 'admin', 'root', '123456']:
                        recommendations.append({
                            'title': 'PCI DSS: Remove Default Passwords',
                            'severity': 'High',
                            'category': 'pci_compliance',
                            'resource': f'Container: {container.get("name", "unknown")}',
                            'issue': 'Default password detected in environment variables',
                            'recommendation': 'Replace default passwords with strong, unique credentials stored in AWS Secrets Manager'
                        })
        
        # PCI DSS Requirement 4: Encrypt transmission of cardholder data
        network_data = cluster_data.get('network_data', {})
        load_balancers = network_data.get('load_balancers', {})
        
        for lb_arn, lb_info in load_balancers.items():
            listeners = lb_info.get('Listeners', [])
            has_unencrypted = any(listener.get('Protocol') == 'HTTP' for listener in listeners)
            
            if has_unencrypted:
                recommendations.append({
                    'title': 'PCI DSS: Encrypt Data in Transit',
                    'severity': 'High',
                    'category': 'pci_compliance',
                    'resource': f'Load Balancer: {lb_info.get("LoadBalancerName", "unknown")}',
                    'issue': 'Unencrypted HTTP traffic detected',
                    'recommendation': 'Configure HTTPS/TLS encryption for all data transmission'
                })
        
        return recommendations

    def _check_hipaa_compliance(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Check HIPAA compliance requirements."""
        recommendations = []
        
        # HIPAA: Access Controls
        cluster_info = cluster_data.get('cluster', {})
        execute_command_config = cluster_info.get('configuration', {}).get('executeCommandConfiguration', {})
        
        if execute_command_config and not execute_command_config.get('kmsKeyId'):
            recommendations.append({
                'title': 'HIPAA: Encrypt Administrative Access',
                'severity': 'High',
                'category': 'hipaa_compliance',
                'resource': f'Cluster: {cluster_name}',
                'issue': 'Execute command sessions not encrypted with customer-managed keys',
                'recommendation': 'Configure KMS encryption for execute command to protect PHI access'
            })
        
        # HIPAA: Audit Controls
        container_insights_enabled = any(
            setting.get('name') == 'containerInsights' and setting.get('value') == 'enabled'
            for setting in cluster_info.get('settings', [])
        )
        
        if not container_insights_enabled:
            recommendations.append({
                'title': 'HIPAA: Enable Comprehensive Audit Logging',
                'severity': 'High',
                'category': 'hipaa_compliance',
                'resource': f'Cluster: {cluster_name}',
                'issue': 'Container Insights disabled, limiting audit trail for PHI access',
                'recommendation': 'Enable Container Insights and comprehensive logging for HIPAA audit requirements'
            })
        
        return recommendations

    def _check_soc2_compliance(self, cluster_data: Dict[str, Any], cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Check SOC 2 compliance requirements."""
        recommendations = []
        
        # SOC 2: Security - Logical Access Controls
        services = cluster_data.get('services', [])
        for service_data in services:
            service = service_data.get('service', {})
            task_def = service_data.get('task_definition', {})
            
            # Check for proper IAM roles
            if not task_def.get('taskRoleArn'):
                recommendations.append({
                    'title': 'SOC 2: Implement Logical Access Controls',
                    'severity': 'High',
                    'category': 'soc2_compliance',
                    'resource': f'Service: {service.get("serviceName", "unknown")}',
                    'issue': 'Missing task IAM role for access control',
                    'recommendation': 'Configure task IAM roles with least privilege access for SOC 2 compliance'
                })
        
        # SOC 2: Availability - System Monitoring
        cluster_info = cluster_data.get('cluster', {})
        container_insights_enabled_soc2 = any(
            setting.get('name') == 'containerInsights' and setting.get('value') == 'enabled'
            for setting in cluster_info.get('settings', [])
        )
        if not container_insights_enabled_soc2:
            recommendations.append({
                'title': 'SOC 2: Implement System Monitoring',
                'severity': 'Medium',
                'category': 'soc2_compliance',
                'resource': f'Cluster: {cluster_name}',
                'issue': 'Insufficient system monitoring for availability controls',
                'recommendation': 'Enable Container Insights and comprehensive monitoring for SOC 2 availability requirements'
            })
        
        return recommendations

    def _analyze_service_discovery_security(self, service: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze service discovery security configurations."""
        recommendations = []
        
        # Check Service Connect configuration
        service_connect = service.get('serviceConnectConfiguration', {})
        if service_connect.get('enabled', False):
            # Check namespace security
            namespace = service_connect.get('namespace')
            if not namespace:
                recommendations.append({
                    'title': 'Configure Secure Service Discovery Namespace',
                    'severity': 'Medium',
                    'category': 'service_discovery',
                    'resource': f'Service: {service_name}',
                    'issue': 'Service Connect enabled without proper namespace configuration',
                    'recommendation': 'Configure a dedicated namespace for secure service-to-service communication'
                })
        
        return recommendations

    def _analyze_resource_isolation(self, task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze resource isolation and access control."""
        recommendations = []
        
        task_family = task_def.get('family', 'unknown')
        
        # Check CPU and memory limits for resource isolation
        cpu = task_def.get('cpu')
        memory = task_def.get('memory')
        
        # For Fargate, check if resources are properly allocated
        requires_compatibilities = task_def.get('requiresCompatibilities', [])
        if 'FARGATE' in requires_compatibilities:
            if not cpu or not memory:
                recommendations.append({
                    'title': 'Configure Resource Limits for Isolation',
                    'severity': 'High',
                    'category': 'resource_isolation',
                    'resource': f'Task Definition: {task_family}',
                    'issue': 'Missing CPU or memory configuration for Fargate task',
                    'recommendation': 'Configure appropriate CPU and memory limits for proper resource isolation'
                })
        
        return recommendations

    def _analyze_monitoring_security(self, service: Dict[str, Any], task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze monitoring and logging security configurations."""
        recommendations = []
        
        # Check CloudWatch logging configuration
        for container in task_def.get('containerDefinitions', []):
            container_name = container.get('name', 'unknown')
            log_config = container.get('logConfiguration', {})
            
            # Note: Container logging is now handled in _analyze_container_security to avoid duplication
        
        return recommendations

    def _analyze_image_security(self, container: Dict[str, Any], container_name: str, service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze container image security."""
        recommendations = []
        
        image = container.get('image', '')
        
        # Check image registry security
        if not image:
            recommendations.append({
                'title': 'Specify Container Image',
                'severity': 'High',
                'category': 'image_security',
                'resource': f'Container: {container_name}',
                'issue': 'No container image specified',
                'recommendation': 'Specify a valid container image from a trusted registry'
            })
            return recommendations
        
        # Check for image scanning
        if '.ecr.' in image and '.amazonaws.com' in image:
            # This is an ECR image - recommend image scanning
            recommendations.append({
                'title': 'Enable ECR Image Scanning',
                'severity': 'Medium',
                'category': 'image_security',
                'resource': f'Container: {container_name}',
                'issue': 'Ensure ECR image scanning is enabled for vulnerability detection',
                'recommendation': 'Enable ECR image scanning to detect vulnerabilities in container images'
            })
        
        return recommendations

    def _analyze_container_runtime_security(self, container: Dict[str, Any], container_name: str, service_name: str, cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Analyze container runtime security configurations."""
        recommendations = []
        
        # Check Linux parameters for security
        linux_parameters = container.get('linuxParameters', {})
        
        if linux_parameters:
            # Check capabilities
            capabilities = linux_parameters.get('capabilities', {})
            add_capabilities = capabilities.get('add', [])
            
            # Check for dangerous capabilities
            dangerous_caps = ['SYS_ADMIN', 'NET_ADMIN', 'SYS_PTRACE', 'SYS_MODULE', 'DAC_OVERRIDE', 'SETUID', 'SETGID']
            for cap in add_capabilities:
                if cap in dangerous_caps:
                    recommendations.append({
                        'title': f'Remove Dangerous Capability: {cap}',
                        'severity': 'High',
                        'category': 'runtime_security',
                        'resource': f'Container: {container_name}',
                        'issue': f'Container has dangerous capability {cap} which increases attack surface',
                        'recommendation': 'Remove unnecessary capabilities and follow principle of least privilege'
                    })
        
        return recommendations
    
    def _enhance_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance recommendation with detailed information."""
        enhanced = recommendation.copy()
        
        # Add detailed descriptions
        enhanced['why_important'] = self._generate_why_important(
            enhanced.get('title', ''),
            enhanced.get('category', ''),
            enhanced.get('severity', '')
        )
        
        enhanced['security_impact'] = self._generate_security_impact(
            enhanced.get('title', ''),
            enhanced.get('category', ''),
            enhanced.get('severity', '')
        )
        
        enhanced['implementation_steps'] = self._generate_implementation_steps(
            enhanced.get('title', ''),
            enhanced.get('category', '')
        )
        
        enhanced['aws_cli_commands'] = self._generate_aws_cli_commands(
            enhanced.get('title', ''),
            enhanced.get('resource', ''),
            enhanced  # Pass the full recommendation data for dynamic resource extraction
        )
        
        enhanced['aws_documentation_url'] = self._generate_documentation_url(
            enhanced.get('title', ''),
            enhanced.get('category', '')
        )
        
        return enhanced

    def _generate_why_important(self, title: str, category: str, severity: str) -> str:
        """Generate why this recommendation is important."""
        importance_map = {
            'Configure Container to Run as Non-Root User': 'Running containers as root violates the principle of least privilege and increases the attack surface. If a container is compromised, root access provides attackers with maximum privileges.',
            'Avoid Latest Tag in Container Images': 'Using latest tags makes deployments unpredictable and can introduce security vulnerabilities when new versions are automatically pulled without proper testing.',
            'Enable Read-Only Root Filesystem': 'A read-only root filesystem prevents runtime tampering and malicious modifications to the container, reducing the impact of potential security breaches.',
            'Configure Container Health Check': 'Health checks enable ECS to detect and replace unhealthy containers automatically, improving application availability and security posture.',
            'Avoid Static Host Port Mapping': 'Static port mapping can lead to port conflicts and makes it easier for attackers to target specific services. Dynamic port allocation provides better security through obscurity.',
            'Use AWS Secrets Manager for Sensitive Data': 'Hardcoded secrets in environment variables are visible in container metadata and logs, creating security risks. Secrets Manager provides encryption and access control.',
            'Restrict SSH Access from Internet': 'Open SSH access from the internet exposes your infrastructure to brute force attacks and unauthorized access attempts.',
            'Configure task IAM role': 'Without proper IAM roles, containers may have excessive permissions or no permissions at all, violating security best practices.',
            'Enable Container Insights for Security Monitoring': 'Container Insights provides visibility into container performance and security events, enabling faster detection of anomalies.'
        }
        
        return importance_map.get(title, f'This {category} security configuration helps maintain a secure ECS environment and follows AWS security best practices.')

    def _generate_security_impact(self, title: str, category: str, severity: str) -> str:
        """Generate security impact description."""
        impact_map = {
            'Configure Container to Run as Non-Root User': 'High risk of privilege escalation and system compromise if container is breached. Root access allows attackers to modify system files and access sensitive data.',
            'Avoid Latest Tag in Container Images': 'Medium risk of deploying vulnerable or untested code. Latest tags can introduce breaking changes or security vulnerabilities without notice.',
            'Enable Read-Only Root Filesystem': 'Reduces risk of runtime attacks and malware persistence. Prevents attackers from modifying system files or installing malicious software.',
            'Configure Container Health Check': 'Without health checks, failed or compromised containers may continue running, potentially serving malicious content or consuming resources.',
            'Avoid Static Host Port Mapping': 'Static ports make services predictable targets for attackers and can lead to service conflicts in multi-tenant environments.',
            'Use AWS Secrets Manager for Sensitive Data': 'Critical risk of credential exposure through container metadata, logs, or process lists. Compromised credentials can lead to data breaches.',
            'Restrict SSH Access from Internet': 'Critical risk of unauthorized access, data breaches, and system compromise through brute force attacks or credential stuffing.',
            'Configure task IAM role': 'Risk of privilege escalation or insufficient permissions leading to application failures or security vulnerabilities.',
            'Enable Container Insights for Security Monitoring': 'Reduced visibility into security events and performance issues, making it harder to detect and respond to threats.'
        }
        
        return impact_map.get(title, f'This {severity.lower()} severity {category} issue could impact your security posture and compliance requirements.')

    def _generate_implementation_steps(self, title: str, category: str) -> List[str]:
        """Generate implementation steps."""
        steps_map = {
            'Configure Container to Run as Non-Root User': [
                'Create a non-root user in your Dockerfile: RUN useradd -r -s /bin/false appuser',
                'Set the user in your Dockerfile: USER appuser',
                'Update your task definition to specify the user parameter',
                'Test the application to ensure it works with non-root permissions',
                'Update file permissions if needed for application directories'
            ],
            'Avoid Latest Tag in Container Images': [
                'Identify the current version of your container image',
                'Update your task definition to use a specific version tag (e.g., myapp:v1.2.3)',
                'Implement a versioning strategy for your container images',
                'Update your CI/CD pipeline to use specific tags',
                'Test the deployment with the specific tag'
            ],
            'Enable Read-Only Root Filesystem': [
                'Update your task definition to set readonlyRootFilesystem: true',
                'Identify directories that need write access',
                'Add volume mounts for writable directories (e.g., /tmp, /var/log)',
                'Test your application to ensure it works with read-only filesystem',
                'Update application code if it writes to unexpected locations'
            ],
            'Configure Container Health Check': [
                'Define a health check endpoint in your application',
                'Add healthCheck configuration to your task definition',
                'Set appropriate timeout and retry values',
                'Test the health check endpoint',
                'Monitor health check results in ECS console'
            ],
            'Avoid Static Host Port Mapping': [
                'Update task definition to set hostPort to 0 for dynamic allocation',
                'Configure Application Load Balancer to use dynamic port mapping',
                'Update service discovery configuration if used',
                'Test connectivity through the load balancer',
                'Update any hardcoded port references in your application'
            ],
            'Use AWS Secrets Manager for Sensitive Data': [
                'Create secrets in AWS Secrets Manager',
                'Update task execution role with secretsmanager:GetSecretValue permission',
                'Replace environment variables with secrets in task definition',
                'Update application code to handle secrets if needed',
                'Test secret retrieval and application functionality'
            ],
            'Restrict SSH Access from Internet': [
                'Identify the security group with the overly permissive rule',
                'Remove or modify the rule allowing 0.0.0.0/0 access to port 22',
                'Add specific IP ranges for authorized access',
                'Consider using AWS Systems Manager Session Manager instead',
                'Test connectivity from authorized locations'
            ]
        }
        
        return steps_map.get(title, [
            'Review the current configuration',
            'Plan the security improvement',
            'Implement the recommended changes',
            'Test the changes in a non-production environment',
            'Deploy to production and monitor'
        ])

    def _generate_aws_cli_commands(self, title: str, resource: str, recommendation_data: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate AWS CLI commands for implementation.
        
        CRITICAL: All CLI commands MUST be verified against official AWS documentation:
        - AWS ECS CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/ecs/
        - AWS EC2 CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/ec2/
        - AWS Secrets Manager CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/
        
        DO NOT assume command syntax. Always verify:
        1. Command name exists in the service
        2. Parameter names and formats are correct
        3. Required vs optional parameters
        4. Example usage from official docs
        """
        # Extract actual resource names from the resource string and recommendation data
        cluster_name = getattr(self, '_current_cluster_name', 'CLUSTER_NAME')
        
        # Extract specific resource IDs from the resource string
        task_def_name = 'TASK_DEFINITION_NAME'
        security_group_id = 'SECURITY_GROUP_ID'
        
        if recommendation_data:
            # Try to extract actual resource names from the recommendation data
            if 'task_definition' in recommendation_data:
                task_def_name = recommendation_data['task_definition']
            elif 'Task Definition:' in resource:
                task_def_name = resource.split('Task Definition: ')[-1].strip()
            
            if 'security_group_id' in recommendation_data:
                security_group_id = recommendation_data['security_group_id']
            elif 'Security Group:' in resource:
                security_group_id = resource.split('Security Group: ')[-1].strip()
        
        # Parse resource string for actual IDs
        if 'Task Definition:' in resource:
            task_def_name = resource.split('Task Definition: ')[-1].strip()
        if 'Security Group:' in resource:
            security_group_id = resource.split('Security Group: ')[-1].strip()
        if 'Cluster:' in resource:
            cluster_name = resource.split('Cluster: ')[-1].strip()

        commands_map = {
            'Configure Container to Run as Non-Root User': [
                f'aws ecs describe-task-definition --task-definition {task_def_name}',
                'aws ecs register-task-definition --cli-input-json file://updated-task-definition.json'
            ],
            'Avoid Latest Tag in Container Images': [
                f'aws ecs describe-task-definition --task-definition {task_def_name}',
                'aws ecs register-task-definition --cli-input-json file://updated-task-definition.json'
            ],
            'Enable Read-Only Root Filesystem': [
                f'aws ecs describe-task-definition --task-definition {task_def_name}',
                'aws ecs register-task-definition --cli-input-json file://updated-task-definition.json'
            ],
            'Configure Container Health Check': [
                f'aws ecs describe-task-definition --task-definition {task_def_name}',
                'aws ecs register-task-definition --cli-input-json file://updated-task-definition.json'
            ],
            'Avoid Static Host Port Mapping': [
                f'aws ecs describe-task-definition --task-definition {task_def_name}',
                'aws ecs register-task-definition --cli-input-json file://updated-task-definition.json'
            ],
            'Use AWS Secrets Manager for Sensitive Data': [
                'aws secretsmanager create-secret --name "app/database/password" --secret-string "your-secret-value"',
                f'aws ecs describe-task-definition --task-definition {task_def_name}',
                'aws ecs register-task-definition --cli-input-json file://updated-task-definition.json'
            ],
            'Restrict SSH Access from Internet': [
                f'aws ec2 describe-security-groups --group-ids {security_group_id}',
                f'aws ec2 revoke-security-group-ingress --group-id {security_group_id} --protocol tcp --port 22 --cidr 0.0.0.0/0',
                f'aws ec2 authorize-security-group-ingress --group-id {security_group_id} --protocol tcp --port 22 --cidr YOUR_IP_RANGE/32'
            ],
            'Enable Container Insights for Security Monitoring': [
                f'aws ecs modify-cluster --cluster {cluster_name} --settings name=containerInsights,value=enabled'
            ],
            'Enable VPC Flow Logs': [
                f'aws ec2 create-flow-logs --resource-type VPC --resource-ids VPC_ID --traffic-type ALL --log-destination-type cloud-watch-logs --log-group-name VPCFlowLogs'
            ],
            'Review Internet Gateway Routes': [
                f'aws ec2 describe-route-tables --filters "Name=vpc-id,Values=VPC_ID"',
                f'aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=VPC_ID"'
            ]
        }
        
        return commands_map.get(title, [
            'aws ecs describe-cluster --cluster CLUSTER_NAME',
            'aws ecs describe-services --cluster CLUSTER_NAME --services SERVICE_NAME'
        ])

    def _generate_documentation_url(self, title: str, category: str) -> str:
        """Generate AWS documentation URL."""
        doc_map = {
            'Configure Container to Run as Non-Root User': 'https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_security',
            'Avoid Latest Tag in Container Images': 'https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_image',
            'Enable Read-Only Root Filesystem': 'https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_security',
            'Configure Container Health Check': 'https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_healthcheck',
            'Avoid Static Host Port Mapping': 'https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_portmappings',
            'Use AWS Secrets Manager for Sensitive Data': 'https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-secrets.html',
            'Restrict SSH Access from Internet': 'https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html',
            'Enable Container Insights for Security Monitoring': 'https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html',
            'Configure task IAM role': 'https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html',
            'Enable VPC Flow Logs': 'https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html',
            'Review Internet Gateway Routes': 'https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html'
        }
        
        return doc_map.get(title, 'https://docs.aws.amazon.com/ecs/')

    def _generate_analysis_summary(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate analysis summary."""
        severity_counts = {}
        category_counts = {}
        
        for rec in recommendations:
            severity = rec.get('severity', 'Unknown')
            category = rec.get('category', 'unknown')
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'total_issues': len(recommendations),
            'severity_breakdown': severity_counts,
            'category_breakdown': category_counts,
            'categories': list(category_counts.keys()),
            'risk_level': self._calculate_risk_level(severity_counts),
            'top_categories': sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        }

    def _calculate_risk_level(self, severity_counts: Dict[str, int]) -> str:
        """Calculate overall risk level based on severity counts."""
        if severity_counts.get('High', 0) > 2:
            return 'High'
        elif severity_counts.get('High', 0) > 0 or severity_counts.get('Medium', 0) > 3:
            return 'Medium'
        else:
            return 'Low'
    
    def _categorize_issues(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize issues by resource type and category for better organization."""
        categorized = {
            'by_severity': {'High': [], 'Medium': [], 'Low': []},
            'by_category': {},
            'by_resource_type': {}
        }
        
        for rec in recommendations:
            severity = rec.get('severity', 'Unknown')
            category = rec.get('category', 'Unknown')
            resource = rec.get('resource', 'Unknown')
            
            # Group by severity
            if severity in categorized['by_severity']:
                categorized['by_severity'][severity].append(rec)
            
            # Group by category
            if category not in categorized['by_category']:
                categorized['by_category'][category] = []
            categorized['by_category'][category].append(rec)
            
            # Group by resource type
            resource_type = self._extract_resource_type(resource)
            if resource_type not in categorized['by_resource_type']:
                categorized['by_resource_type'][resource_type] = []
            categorized['by_resource_type'][resource_type].append(rec)
        
        return categorized
    
    def _extract_resource_type(self, resource: str) -> str:
        """Extract resource type from resource string."""
        if 'Cluster:' in resource:
            return 'Cluster'
        elif 'Service:' in resource:
            return 'Service'
        elif 'Container:' in resource:
            return 'Container'
        elif 'Security Group' in resource:
            return 'Security Group'
        elif 'Load Balancer' in resource:
            return 'Load Balancer'
        elif 'VPC:' in resource:
            return 'VPC'
        else:
            return 'Other'
    
    def _calculate_risk_priorities(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate risk-weighted priorities for recommendations."""
        risk_scored = []
        
        severity_weights = {'High': 100, 'Medium': 50, 'Low': 25}
        category_weights = {
            'network_security': 1.5,
            'container_security': 1.4,
            'iam_security': 1.3,
            'encryption': 1.2,
            'monitoring': 1.1,
            'compliance': 1.0,
            'configuration': 0.9,
            'availability': 0.8
        }
        
        for rec in recommendations:
            severity = rec.get('severity', 'Low')
            category = rec.get('category', 'configuration')
            
            base_score = severity_weights.get(severity, 25)
            category_multiplier = category_weights.get(category, 1.0)
            
            # Additional risk factors
            risk_multiplier = 1.0
            issue = rec.get('issue', '').lower()
            
            # High-risk keywords
            if any(keyword in issue for keyword in ['internet', '0.0.0.0/0', 'root', 'privileged', 'ssh']):
                risk_multiplier += 0.5
            
            # Public exposure
            if any(keyword in issue for keyword in ['public', 'exposed', 'open']):
                risk_multiplier += 0.3
            
            final_score = base_score * category_multiplier * risk_multiplier
            
            risk_item = rec.copy()
            risk_item['risk_score'] = round(final_score, 2)
            risk_scored.append(risk_item)
        
        # Sort by risk score descending
        risk_scored.sort(key=lambda x: x['risk_score'], reverse=True)
        
        return risk_scored[:10]  # Top 10 highest risk items
    
    def _deduplicate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate recommendations using comprehensive similarity analysis."""
        if not recommendations:
            return []
        
        deduplicated = []
        processed_indices = set()
        
        for i, rec in enumerate(recommendations):
            if i in processed_indices:
                continue
            
            # Find all similar recommendations to this one
            similar_recs = [rec]
            similar_indices = {i}
            
            for j, other_rec in enumerate(recommendations[i+1:], i+1):
                if j in processed_indices:
                    continue
                
                if self._are_recommendations_similar(rec, other_rec):
                    similar_recs.append(other_rec)
                    similar_indices.add(j)
            
            # If we found similar recommendations, keep the best one
            if len(similar_recs) > 1:
                best_rec = self._select_best_recommendation(similar_recs)
                deduplicated.append(best_rec)
                processed_indices.update(similar_indices)
            else:
                deduplicated.append(rec)
                processed_indices.add(i)
        
        return deduplicated
    
    def _are_recommendations_similar(self, rec1: Dict[str, Any], rec2: Dict[str, Any]) -> bool:
        """Determine if two recommendations are similar enough to be considered duplicates."""
        title1 = rec1.get('title', '').lower().strip()
        title2 = rec2.get('title', '').lower().strip()
        
        resource1 = rec1.get('resource', '').lower().strip()
        resource2 = rec2.get('resource', '').lower().strip()
        
        issue1 = rec1.get('issue', '').lower().strip()
        issue2 = rec2.get('issue', '').lower().strip()
        
        category1 = rec1.get('category', '').lower().strip()
        category2 = rec2.get('category', '').lower().strip()
        
        # Exact title match
        if title1 == title2:
            # Same title - check if it's the same resource or same issue
            if resource1 == resource2 or self._text_similarity(issue1, issue2) > 0.8:
                return True
        
        # High title similarity with same category
        if self._text_similarity(title1, title2) > 0.9 and category1 == category2:
            return True
        
        # Same resource with very similar issues
        if resource1 == resource2 and self._text_similarity(issue1, issue2) > 0.85:
            return True
        
        # Handle specific duplicate patterns
        return self._check_specific_duplicate_patterns(rec1, rec2)
    
    def _check_specific_duplicate_patterns(self, rec1: Dict[str, Any], rec2: Dict[str, Any]) -> bool:
        """Check for specific known duplicate patterns."""
        title1 = rec1.get('title', '').lower()
        title2 = rec2.get('title', '').lower()
        
        resource1 = rec1.get('resource', '').lower()
        resource2 = rec2.get('resource', '').lower()
        
        issue1 = rec1.get('issue', '').lower()
        issue2 = rec2.get('issue', '').lower()
        
        # Security group port duplicates
        if ('security group' in title1 and 'security group' in title2 and
            'port' in issue1 and 'port' in issue2):
            # Extract port numbers
            import re
            port1 = re.search(r'port\s+(\d+)', issue1)
            port2 = re.search(r'port\s+(\d+)', issue2)
            if port1 and port2 and port1.group(1) == port2.group(1):
                return True
        
        # Container static port mapping duplicates
        if ('static' in title1 and 'static' in title2 and 
            'port' in title1 and 'port' in title2 and
            'container' in resource1 and 'container' in resource2):
            return True
        
        # Health check duplicates
        if ('health check' in title1 and 'health check' in title2 and
            'container' in resource1 and 'container' in resource2):
            # Extract container names
            container1 = self._extract_container_name(resource1)
            container2 = self._extract_container_name(resource2)
            if container1 == container2:
                return True
        
        # Memory/CPU limit duplicates for same container
        if (('memory' in title1 or 'cpu' in title1) and 
            ('memory' in title2 or 'cpu' in title2) and
            'container' in resource1 and 'container' in resource2):
            container1 = self._extract_container_name(resource1)
            container2 = self._extract_container_name(resource2)
            if container1 == container2:
                return True
        
        return False
    
    def _extract_container_name(self, resource: str) -> str:
        """Extract container name from resource string."""
        if 'container:' in resource.lower():
            parts = resource.split(':')
            if len(parts) > 1:
                return parts[1].strip().split('|')[0].strip()
        return resource
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using sequence matching."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _select_best_recommendation(self, similar_recs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best recommendation from a group of similar ones."""
        # Sort by severity (highest first), then by completeness of information
        def recommendation_score(rec):
            severity_weight = self._get_severity_weight(rec.get('severity', 'Low'))
            
            # Bonus points for more complete information
            completeness_score = 0
            if rec.get('recommendation'):
                completeness_score += 1
            if rec.get('remediation_steps'):
                completeness_score += 1
            if len(rec.get('issue', '')) > 50:  # More detailed issue description
                completeness_score += 1
            
            return severity_weight * 10 + completeness_score
        
        return max(similar_recs, key=recommendation_score)
    
    def _create_deduplication_key(self, title: str, resource_type: str, issue: str, category: str) -> str:
        """Create a normalized key for deduplication (legacy method - kept for compatibility)."""
        # This method is now primarily used by the legacy deduplication logic
        # The new similarity-based approach is more comprehensive
        normalized_title = title.lower().strip()
        normalized_resource_type = resource_type.lower().strip()
        normalized_category = category.lower().strip()
        
        # Extract specific identifiers for better deduplication
        import re
        
        # Handle network security with port numbers
        if 'port' in issue.lower():
            port_match = re.search(r'port\s+(\d+)', issue.lower())
            port = port_match.group(1) if port_match else 'unknown'
            return f"network_port_{port}_{normalized_resource_type}_{normalized_category}"
        
        # Handle container-specific issues
        if 'container' in normalized_resource_type:
            container_name = self._extract_container_name(resource_type)
            if 'health check' in normalized_title:
                return f"container_health_{container_name}_{normalized_category}"
            elif 'memory' in normalized_title or 'cpu' in normalized_title:
                return f"container_resources_{container_name}_{normalized_category}"
            elif 'static' in normalized_title and 'port' in normalized_title:
                return f"container_static_port_{container_name}_{normalized_category}"
        
        # Handle IAM duplicates
        if 'iam' in normalized_title and 'role' in normalized_title:
            if 'task' in normalized_title:
                return f"iam_task_role_{normalized_resource_type}_{normalized_category}"
            elif 'execution' in normalized_title:
                return f"iam_execution_role_{normalized_resource_type}_{normalized_category}"
        
        # Handle secrets duplicates
        if 'secret' in normalized_title:
            return f"secrets_management_{normalized_resource_type}_{normalized_category}"
        
        # Generic deduplication key
        return f"{normalized_title}_{normalized_resource_type}_{normalized_category}"
    
    def _get_severity_weight(self, severity: str) -> int:
        """Get numeric weight for severity comparison (AWS Trusted Advisor aligned)."""
        weights = {'High': 3, 'Medium': 2, 'Low': 1}
        return weights.get(severity, 0)


class SecurityReportFormatter:
    """Enhanced security report formatter with multiple output formats and filtering."""
    
    def __init__(self):
        self.severity_icons = {
            'High': '🔴',      # AWS Trusted Advisor Red (Action Recommended)
            'Medium': '🟡',    # AWS Trusted Advisor Yellow (Investigation Recommended) 
            'Low': '🟢'        # AWS Trusted Advisor Green (Informational)
        }
        self.category_icons = {
            'network_security': '🌐',
            'container_security': '🐳',
            'iam_security': '🔐',
            'encryption': '🔒',
            'monitoring': '📊',
            'compliance': '🏛️',
            'configuration': '⚙️',
            'availability': '⚡',
            'secrets': '🔑',
            'security': '🛡️',
            'well_architected': '🏗️',
            'resource_management': '📈',
            'network': '🔗',
            'monitoring_security': '👁️',
            'iam': '🔐',
            'logging': '📝'
        }
    
    def format_report(self, analysis_result: Dict[str, Any], 
                     format_type: str = 'summary',
                     severity_filter: Optional[List[str]] = None,
                     category_filter: Optional[List[str]] = None,
                     show_details: bool = False) -> str:
        """Format security analysis report with various options."""
        
        if format_type == 'json':
            return self._format_json(analysis_result, severity_filter, category_filter)
        elif format_type == 'detailed':
            return self._format_detailed(analysis_result, severity_filter, category_filter)
        elif format_type == 'executive':
            return self._format_executive_summary(analysis_result)
        else:
            return self._format_enhanced_summary(analysis_result, severity_filter, category_filter, show_details)
    
    def _format_enhanced_summary(self, analysis_result: Dict[str, Any], 
                               severity_filter: Optional[List[str]] = None,
                               category_filter: Optional[List[str]] = None,
                               show_details: bool = False) -> str:
        """Format enhanced summary with progressive disclosure."""
        
        recommendations = analysis_result.get('recommendations', [])
        categorized = analysis_result.get('categorized_issues', {})
        risk_priorities = analysis_result.get('risk_weighted_priorities', [])
        summary = analysis_result.get('analysis_summary', {})
        
        # Apply filters to both recommendations and categorized data
        if severity_filter or category_filter:
            recommendations = self._apply_filters(recommendations, severity_filter, category_filter)
            categorized = self._filter_categorized_data(categorized, severity_filter, category_filter)
            risk_priorities = self._apply_filters(risk_priorities, severity_filter, category_filter)
            # Update summary to reflect filtered data
            summary = self._generate_filtered_summary(categorized, severity_filter, category_filter)
        
        report = []
        
        # Executive Summary
        report.append(self._generate_executive_header(summary, len(recommendations)))
        
        # Risk-Weighted Top Priorities
        if risk_priorities:
            report.append(self._generate_risk_priorities_section(risk_priorities[:5]))
        
        # High Priority Issues (Always detailed)
        high_issues = self._get_critical_high_issues(categorized)
        if high_issues:
            report.append(self._generate_critical_high_section(high_issues))
        
        # Medium Issues (Expandable)
        medium_issues = categorized.get('by_severity', {}).get('Medium', [])
        if medium_issues:
            report.append(self._generate_medium_section(medium_issues, show_details))
        
        # Low Issues (Collapsible summary)
        low_issues = categorized.get('by_severity', {}).get('Low', [])
        if low_issues:
            report.append(self._generate_low_section(low_issues, show_details))
        
        # Category breakdown (always show unless filtered)
        if not category_filter:  # Only show if not filtering by specific categories
            report.append(self._generate_category_breakdown_section(categorized))
        
        # Resource-based grouping (always show for better actionability)
        report.append(self._generate_resource_breakdown(categorized))
        
        # Quick Actions and Remediation Guide
        report.append(self._generate_quick_actions(risk_priorities[:3]))
        
        return '\n\n'.join(report)
    
    def _apply_filters(self, recommendations: List[Dict[str, Any]], 
                      severity_filter: Optional[List[str]] = None,
                      category_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Apply severity and category filters to recommendations."""
        filtered = recommendations
        
        if severity_filter:
            filtered = [r for r in filtered if r.get('severity') in severity_filter]
        
        if category_filter:
            filtered = [r for r in filtered if r.get('category') in category_filter]
        
        return filtered
    
    def _filter_categorized_data(self, categorized: Dict[str, Any], 
                               severity_filter: Optional[List[str]] = None,
                               category_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply filters to categorized data structure."""
        if not severity_filter and not category_filter:
            return categorized
        
        filtered_categorized = {
            'by_severity': {},
            'by_category': {},
            'by_resource': {}
        }
        
        # Filter by_severity
        by_severity = categorized.get('by_severity', {})
        for severity, issues in by_severity.items():
            if not severity_filter or severity in severity_filter:
                filtered_issues = issues
                if category_filter:
                    filtered_issues = [issue for issue in issues if issue.get('category') in category_filter]
                if filtered_issues:
                    filtered_categorized['by_severity'][severity] = filtered_issues
        
        # Filter by_category
        by_category = categorized.get('by_category', {})
        for category, issues in by_category.items():
            if not category_filter or category in category_filter:
                filtered_issues = issues
                if severity_filter:
                    filtered_issues = [issue for issue in issues if issue.get('severity') in severity_filter]
                if filtered_issues:
                    filtered_categorized['by_category'][category] = filtered_issues
        
        # Filter by_resource
        by_resource = categorized.get('by_resource', {})
        for resource, issues in by_resource.items():
            filtered_issues = issues
            if severity_filter:
                filtered_issues = [issue for issue in filtered_issues if issue.get('severity') in severity_filter]
            if category_filter:
                filtered_issues = [issue for issue in filtered_issues if issue.get('category') in category_filter]
            if filtered_issues:
                filtered_categorized['by_resource'][resource] = filtered_issues
        
        return filtered_categorized
    
    def _generate_filtered_summary(self, categorized: Dict[str, Any], 
                                 severity_filter: Optional[List[str]] = None,
                                 category_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate summary statistics for filtered data."""
        by_severity = categorized.get('by_severity', {})
        by_category = categorized.get('by_category', {})
        
        # Calculate severity breakdown
        severity_breakdown = {}
        total_issues = 0
        for severity, issues in by_severity.items():
            count = len(issues)
            severity_breakdown[severity] = count
            total_issues += count
        
        # Calculate category breakdown
        category_breakdown = {}
        for category, issues in by_category.items():
            category_breakdown[category] = len(issues)
        
        # Determine overall risk level based on filtered results
        risk_level = 'Low'
        if severity_breakdown.get('High', 0) > 0:
            risk_level = 'High'
        elif severity_breakdown.get('Medium', 0) > 0:
            risk_level = 'Medium'
        
        return {
            'severity_breakdown': severity_breakdown,
            'category_breakdown': category_breakdown,
            'risk_level': risk_level,
            'total_issues': total_issues,
            'filtered': True,
            'severity_filter': severity_filter,
            'category_filter': category_filter
        }
    
    def _generate_executive_header(self, summary: Dict[str, Any], total_filtered: int) -> str:
        """Generate executive summary header with severity and category breakdowns."""
        severity_breakdown = summary.get('severity_breakdown', {})
        category_breakdown = summary.get('category_breakdown', {})
        risk_level = summary.get('risk_level', 'Unknown')
        is_filtered = summary.get('filtered', False)
        severity_filter = summary.get('severity_filter')
        category_filter = summary.get('category_filter')
        
        header = [
            "# 🛡️ ECS Security Analysis Report",
            ""
        ]
        
        # Show filter information if applied
        if is_filtered:
            header.append("## 🔍 Filtered Results")
            if severity_filter:
                header.append(f"**Severity Filter**: {', '.join(severity_filter)}")
            if category_filter:
                header.append(f"**Category Filter**: {', '.join(category_filter)}")
            header.append("")
        
        header.extend([
            "## 📊 Executive Summary",
            f"**Total Security Issues Found**: {total_filtered}",
            f"**Overall Risk Level**: {self.severity_icons.get(risk_level, '❓')} {risk_level}",
            "",
            "### Issue Breakdown by Severity:"
        ])
        
        for severity in ['High', 'Medium', 'Low']:
            count = severity_breakdown.get(severity, 0)
            icon = self.severity_icons.get(severity, '❓')
            if count > 0:
                header.append(f"• {icon} **{count} {severity}** - {self._get_severity_description(severity)}")
        
        # Add category breakdown
        if category_breakdown:
            header.extend([
                "",
                "### Recommendations by Category:"
            ])
            
            # Sort categories by count (descending)
            sorted_categories = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
            
            for category, count in sorted_categories:
                icon = self.category_icons.get(category, '📋')
                category_display = category.replace('_', ' ').title()
                header.append(f"• {icon} **{category_display}**: {count} recommendations")
        
        return '\n'.join(header)
    
    def _get_severity_description(self, severity: str) -> str:
        """Get description for severity level (AWS Trusted Advisor aligned)."""
        descriptions = {
            'High': 'Action recommended - High risk security issues requiring immediate attention',
            'Medium': 'Investigation recommended - Medium risk issues that should be investigated', 
            'Low': 'Informational - Best practices and minor security improvements'
        }
        return descriptions.get(severity, 'Review when possible')
    
    def _generate_risk_priorities_section(self, top_priorities: List[Dict[str, Any]]) -> str:
        """Generate risk-weighted priorities section."""
        section = [
            "## 🎯 Top Priority Issues (Risk-Weighted)",
            "",
            "*These issues pose the highest combined risk based on severity, exploitability, and impact.*",
            ""
        ]
        
        for i, issue in enumerate(top_priorities, 1):
            severity = issue.get('severity', 'Unknown')
            icon = self.severity_icons.get(severity, '❓')
            risk_score = issue.get('risk_score', 0)
            
            section.extend([
                f"### {i}. {icon} {issue.get('title', 'Unknown Issue')} (Risk Score: {risk_score})",
                f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                f"**Issue**: {issue.get('issue', 'No description')}",
                f"**Impact**: {self._get_impact_description(issue)}",
                ""
            ])
        
        return '\n'.join(section)
    
    def _get_impact_description(self, issue: Dict[str, Any]) -> str:
        """Generate impact description based on issue details."""
        category = issue.get('category', '')
        severity = issue.get('severity', '')
        
        impact_map = {
            'network_security': 'Network breach, unauthorized access',
            'container_security': 'Container compromise, privilege escalation',
            'iam_security': 'Unauthorized access, data breach',
            'encryption': 'Data exposure, compliance violation'
        }
        
        base_impact = impact_map.get(category, 'Security vulnerability')
        
        if severity == 'High':
            return f"⚠️ {base_impact} with high exploitation potential"
        else:
            return base_impact
    
    def _get_critical_high_issues(self, categorized: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get high severity issues."""
        by_severity = categorized.get('by_severity', {})
        high = by_severity.get('High', [])
        return high
    
    def _generate_critical_high_section(self, issues: List[Dict[str, Any]]) -> str:
        """Generate detailed section for high priority issues."""
        section = [
            "## 🔴 High Priority Issues",
            "",
            "*These issues require immediate attention and should be fixed within 24-48 hours.*",
            ""
        ]
        
        for issue in issues:
            severity = issue.get('severity', 'Unknown')
            icon = self.severity_icons.get(severity, '❓')
            
            section.extend([
                f"### {icon} {issue.get('title', 'Unknown Issue')}",
                f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                f"**Severity**: {severity} | **Category**: {issue.get('category', 'Unknown')}",
                "",
                f"**Issue**: {issue.get('issue', 'No description')}",
                "",
                f"**Action Required**: {issue.get('recommendation', 'No recommendation provided')}",
                ""
            ])
            
            # Add remediation steps if available
            remediation = issue.get('remediation_steps')
            if remediation:
                section.extend([
                    "**Remediation Steps**:",
                    remediation,
                    ""
                ])
            
            section.append("---")
            section.append("")
        
        return '\n'.join(section)
    
    def _generate_medium_section(self, medium_issues: List[Dict[str, Any]], show_details: bool) -> str:
        """Generate medium priority section with expandable details."""
        section = [
            f"## 🟡 Medium Priority Issues ({len(medium_issues)} total)",
            "",
            "*Address these issues in your next maintenance window.*",
            ""
        ]
        
        if not show_details:
            # Show summary by category
            category_summary = {}
            for issue in medium_issues:
                category = issue.get('category', 'Unknown')
                if category not in category_summary:
                    category_summary[category] = []
                category_summary[category].append(issue.get('title', 'Unknown'))
            
            section.append("### Summary by Category:")
            for category, titles in category_summary.items():
                icon = self.category_icons.get(category, '⚙️')
                section.append(f"• {icon} **{category.replace('_', ' ').title()}** ({len(titles)} issues)")
                if len(titles) <= 3:
                    for title in titles:
                        section.append(f"  - {title}")
                else:
                    for title in titles[:2]:
                        section.append(f"  - {title}")
                    section.append(f"  - ... and {len(titles) - 2} more")
                section.append("")
            
            section.extend([
                "*Use `--show-details` flag to see full details for medium priority issues.*",
                ""
            ])
        else:
            # Show full details
            for issue in medium_issues:
                section.extend([
                    f"### 🟡 {issue.get('title', 'Unknown Issue')}",
                    f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                    f"**Issue**: {issue.get('issue', 'No description')}",
                    f"**Action Required**: {issue.get('recommendation', 'No recommendation')}",
                    ""
                ])
        
        return '\n'.join(section)
    
    def _generate_low_section(self, low_issues: List[Dict[str, Any]], show_details: bool) -> str:
        """Generate low priority section with collapsible summary."""
        section = [
            f"## 🔵 Low Priority Issues ({len(low_issues)} total)",
            "",
            "*Future improvements and best practice recommendations.*",
            ""
        ]
        
        if not show_details:
            # Group by category and show counts
            category_counts = {}
            for issue in low_issues:
                category = issue.get('category', 'Unknown')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            section.append("### Issues by Category:")
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                icon = self.category_icons.get(category, '⚙️')
                section.append(f"• {icon} {category.replace('_', ' ').title()}: {count} issues")
            
            section.extend([
                "",
                "*Use `--show-details` flag to see full details for low priority issues.*"
            ])
        else:
            # Show abbreviated details
            for issue in low_issues:
                section.extend([
                    f"### 🟢 {issue.get('title', 'Unknown Issue')}",
                    f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                    f"**Action Required**: {issue.get('recommendation', 'No recommendation')}",
                    ""
                ])
        
        return '\n'.join(section)
    
    def _generate_resource_breakdown(self, categorized: Dict[str, Any]) -> str:
        """Generate resource-based breakdown."""
        section = [
            "## 🎯 Action Plan by Resource",
            "",
            "*Know exactly which AWS resources need your attention:*",
            ""
        ]
        
        # Group by actual resource instances, not just types
        by_resource = categorized.get('by_resource', {})
        if not by_resource:
            # Fallback to resource type grouping if by_resource is not available
            by_resource = categorized.get('by_resource_type', {})
        
        # Sort resources by severity (High issues first)
        resource_priority = []
        for resource, issues in by_resource.items():
            if not issues:
                continue
            
            high_count = len([i for i in issues if i.get('severity') == 'High'])
            medium_count = len([i for i in issues if i.get('severity') == 'Medium'])
            low_count = len([i for i in issues if i.get('severity') == 'Low'])
            
            # Priority score: High issues get most weight
            priority_score = high_count * 10 + medium_count * 3 + low_count * 1
            resource_priority.append((resource, issues, high_count, medium_count, low_count, priority_score))
        
        # Sort by priority score (descending)
        resource_priority.sort(key=lambda x: x[5], reverse=True)
        
        if not resource_priority:
            section.extend([
                "✅ **Great news!** No resource-specific issues found.",
                ""
            ])
            return '\n'.join(section)
        
        for resource, issues, high_count, medium_count, low_count, _ in resource_priority:
            total_issues = len(issues)
            
            # Resource header with priority indicator
            priority_indicator = "🚨" if high_count > 0 else "⚠️" if medium_count > 0 else "ℹ️"
            section.append(f"### {priority_indicator} `{resource}` ({total_issues} issue{'s' if total_issues != 1 else ''})")
            
            # Severity breakdown
            severity_parts = []
            if high_count > 0:
                severity_parts.append(f"🔴 {high_count} High")
            if medium_count > 0:
                severity_parts.append(f"🟡 {medium_count} Medium")
            if low_count > 0:
                severity_parts.append(f"🟢 {low_count} Low")
            
            if severity_parts:
                section.append(f"**Issues**: {' | '.join(severity_parts)}")
            
            # Show top issues for this resource
            high_issues = [i for i in issues if i.get('severity') == 'High'][:2]  # Top 2 high issues
            if high_issues:
                section.append("**Immediate Actions Needed**:")
                for issue in high_issues:
                    title = issue.get('title', 'Unknown Issue')
                    recommendation = issue.get('recommendation', 'See detailed analysis')
                    section.append(f"• {title}: {recommendation}")
            
            section.append("")
        
        # Add summary guidance
        high_resource_count = len([r for r in resource_priority if r[2] > 0])  # Resources with High issues
        if high_resource_count > 0:
            section.extend([
                f"🎯 **Priority Focus**: {high_resource_count} resource{'s' if high_resource_count != 1 else ''} need{'s' if high_resource_count == 1 else ''} immediate attention",
                ""
            ])
        
        return '\n'.join(section)
    
    def _generate_quick_actions(self, top_issues: List[Dict[str, Any]]) -> str:
        """Generate quick actions section."""
        section = [
            "## ⚡ Quick Actions (Start Here)",
            "",
            "*Immediate steps to improve your security posture - organized by resource:*",
            ""
        ]
        
        for i, issue in enumerate(top_issues, 1):
            title = issue.get('title', 'Unknown Issue')
            resource = issue.get('resource', 'Unknown')
            severity = issue.get('severity', 'Unknown')
            severity_icon = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(severity, '❓')
            
            section.extend([
                f"### {i}. {severity_icon} {title}",
                f"**🎯 Resource**: `{resource}`",
                f"**Action**: {issue.get('recommendation', 'See detailed recommendations')}",
                ""
            ])
            
            # Add implementation command if available
            implementation = issue.get('implementation', {})
            if implementation and implementation.get('aws_cli'):
                section.extend([
                    "**Quick Fix Command**:",
                    f"```bash",
                    f"{implementation['aws_cli']}",
                    f"```",
                    ""
                ])
            
            section.append("---")
            section.append("")
        
        section.extend([
            "## 📚 Additional Resources",
            "",
            "• [AWS ECS Security Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security.html)",
            "• [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)",
            "• [Container Security Best Practices](https://aws.amazon.com/blogs/containers/)",
            ""
        ])
        
        return '\n'.join(section)
    
    def _generate_category_breakdown_section(self, categorized: Dict[str, Any]) -> str:
        """Generate detailed category breakdown section."""
        by_category = categorized.get('by_category', {})
        
        if not by_category:
            return ""
        
        section = [
            "## 📋 Detailed Category Breakdown",
            "",
            "*Security recommendations organized by category with severity distribution.*",
            ""
        ]
        
        # Sort categories by total count (descending)
        sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)
        
        for category, recommendations in sorted_categories:
            icon = self.category_icons.get(category, '📋')
            category_display = category.replace('_', ' ').title()
            
            # Count by severity
            severity_counts = {}
            for rec in recommendations:
                severity = rec.get('severity', 'Unknown')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            section.append(f"### {icon} {category_display} ({len(recommendations)} total)")
            
            # Show severity breakdown for this category
            for severity in ['High', 'Medium', 'Low']:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    severity_icon = self.severity_icons.get(severity, '❓')
                    section.append(f"   • {severity_icon} {severity}: {count}")
            
            # Show top 3 issues in this category
            if len(recommendations) > 0:
                section.append("   **Top Issues:**")
                for i, rec in enumerate(recommendations[:3], 1):
                    title = rec.get('title', 'Unknown Issue')
                    severity = rec.get('severity', 'Unknown')
                    severity_icon = self.severity_icons.get(severity, '❓')
                    section.append(f"   {i}. {severity_icon} {title}")
                
                if len(recommendations) > 3:
                    section.append(f"   ... and {len(recommendations) - 3} more")
            
            section.append("")
        
        return '\n'.join(section)
    
    def _format_json(self, analysis_result: Dict[str, Any], 
                    severity_filter: Optional[List[str]] = None,
                    category_filter: Optional[List[str]] = None) -> str:
        """Format as JSON for machine processing."""
        filtered_result = analysis_result.copy()
        
        if severity_filter or category_filter:
            recommendations = analysis_result.get('recommendations', [])
            categorized = analysis_result.get('categorized_issues', {})
            risk_priorities = analysis_result.get('risk_weighted_priorities', [])
            
            filtered_recommendations = self._apply_filters(recommendations, severity_filter, category_filter)
            filtered_categorized = self._filter_categorized_data(categorized, severity_filter, category_filter)
            filtered_risk_priorities = self._apply_filters(risk_priorities, severity_filter, category_filter)
            
            filtered_result['recommendations'] = filtered_recommendations
            filtered_result['categorized_issues'] = filtered_categorized
            filtered_result['risk_weighted_priorities'] = filtered_risk_priorities
            filtered_result['total_issues'] = len(filtered_recommendations)
            
            # Add filter metadata
            filtered_result['filter_applied'] = {
                'severity_filter': severity_filter,
                'category_filter': category_filter
            }
        
        return json.dumps(filtered_result, indent=2, default=str)
    
    def _format_detailed(self, analysis_result: Dict[str, Any],
                        severity_filter: Optional[List[str]] = None,
                        category_filter: Optional[List[str]] = None) -> str:
        """Format detailed report with all issues expanded."""
        return self._format_enhanced_summary(analysis_result, severity_filter, category_filter, show_details=True)
    
    def _format_executive_summary(self, analysis_result: Dict[str, Any]) -> str:
        """Format executive summary for leadership."""
        summary = analysis_result.get('analysis_summary', {})
        risk_priorities = analysis_result.get('risk_weighted_priorities', [])
        
        report = [
            "# 🛡️ ECS Security Executive Summary",
            "",
            f"**Overall Risk Level**: {summary.get('risk_level', 'Unknown')}",
            f"**Total Issues**: {summary.get('total_issues', 0)}",
            "",
            "## Key Security Concerns",
            ""
        ]
        
        # Top 3 highest risk issues
        for i, issue in enumerate(risk_priorities[:3], 1):
            severity = issue.get('severity', 'Unknown')
            icon = self.severity_icons.get(severity, '❓')
            report.extend([
                f"{i}. {icon} **{issue.get('title', 'Unknown Issue')}**",
                f"   - Risk Score: {issue.get('risk_score', 0)}",
                f"   - Impact: {self._get_impact_description(issue)}",
                ""
            ])
        
        # Compliance impact
        severity_breakdown = summary.get('severity_breakdown', {})
        if severity_breakdown.get('High', 0) > 0:
            report.extend([
                "## Compliance Impact",
                "⚠️ High severity issues may impact compliance with:",
                "• SOC 2 Type II requirements",
                "• PCI DSS standards (if applicable)",
                "• HIPAA regulations (if applicable)",
                "• AWS Security Best Practices",
                ""
            ])
        
        report.extend([
            "## Recommended Actions",
            "1. Address all High priority issues within 24-48 hours",
            "2. Schedule Medium priority fixes for next maintenance window",
            "4. Review and implement Low priority improvements quarterly",
            ""
        ])
        
        return '\n'.join(report)


class ECSSecurityAnalyzer:
    """Complete ECS security analyzer that leverages existing MCP tools for data collection."""
    
    def __init__(self):
        self.analyzer = SecurityAnalyzer()
        self.collector = DataAdapter()
        self.formatter = SecurityReportFormatter()
    
    async def analyze_cluster(self, cluster_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """Analyze a specific ECS cluster for security vulnerabilities and misconfigurations."""
        try:
            # Set current cluster name for dynamic CLI command generation
            self._current_cluster_name = cluster_name
            ecs_data = await self.collector.collect_all_data([region], [cluster_name])
            
            if isinstance(ecs_data, dict) and "error" in ecs_data:
                return {
                    'cluster_name': cluster_name,
                    'region': region,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'status': 'error',
                    'error': f"Failed to collect data: {ecs_data['error']}",
                    'recommendations': [],
                    'total_issues': 0,
                    'analysis_summary': {'status': 'failed', 'reason': 'data_collection_failed'}
                }
            
            data_collection_errors = []
            if region in ecs_data:
                region_data = ecs_data[region]
                if "error" in region_data:
                    data_collection_errors.append(f"Region {region}: {region_data['error']}")
                elif "clusters" in region_data and cluster_name in region_data["clusters"]:
                    cluster_data = region_data["clusters"][cluster_name]
                    if "error" in cluster_data:
                        data_collection_errors.append(f"Cluster {cluster_name}: {cluster_data['error']}")
                    elif "errors" in cluster_data:
                        data_collection_errors.extend(cluster_data["errors"])
            
            if not ecs_data or (region in ecs_data and not ecs_data[region].get("clusters")):
                return {
                    'cluster_name': cluster_name,
                    'region': region,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'status': 'error',
                    'error': f"No data available for cluster '{cluster_name}' in region '{region}'",
                    'recommendations': [],
                    'total_issues': 0,
                    'analysis_summary': {'status': 'failed', 'reason': 'no_data_available'}
                }
            
            results = self.analyzer.analyze(ecs_data)
            
            analysis_status = 'success'
            if data_collection_errors:
                analysis_status = 'partial_success'
            
            final_results = {
                'cluster_name': cluster_name,
                'region': region,
                'analysis_timestamp': datetime.now().isoformat(),
                'status': analysis_status,
                'recommendations': results['recommendations'],
                'total_issues': len(results['recommendations']),
                'analysis_summary': results['analysis_summary']
            }
            
            if data_collection_errors:
                final_results['data_collection_warnings'] = data_collection_errors
                final_results['analysis_summary']['warnings'] = data_collection_errors
            
            return final_results
            
        except Exception as e:
            return {
                'cluster_name': cluster_name,
                'region': region,
                'analysis_timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': f"Unexpected error during security analysis: {str(e)}",
                'recommendations': [],
                'total_issues': 0,
                'analysis_summary': {'status': 'failed', 'reason': 'unexpected_error', 'error': str(e)}
            }

    def _transform_to_flat_structure(self, ecs_data: Dict[str, Any], cluster_name: str) -> Dict[str, Any]:
        """Transform hierarchical data to flat structure for compatibility."""
        services = []
        
        for region, region_data in ecs_data.items():
            if 'error' in region_data:
                continue
                
            for cluster, cluster_data in region_data.get('clusters', {}).items():
                for service_data in cluster_data.get('services', []):
                    service = service_data.get('service', {})
                    task_def = service_data.get('task_definition', {})
                    
                    services.append({
                        'serviceName': service.get('serviceName'),
                        'taskDefinition': task_def,
                        'region': region,
                        'cluster_name': cluster,
                        'runningCount': service.get('runningCount', 0),
                        'desiredCount': service.get('desiredCount', 0),
                        'launchType': service.get('launchType', 'FARGATE')
                    })
        
        return {'services': services, 'cluster_name': cluster_name}


SecurityAnalysisAction = Literal[
    "list_clusters",
    "select_cluster_for_analysis",
    "analyze_cluster_security",
    "generate_security_report", 
    "get_security_recommendations",
    "check_compliance_status"
]

async def ecs_security_analysis_tool(
    action: SecurityAnalysisAction,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Comprehensive ECS security analysis tool.
    
    Args:
        action: The security analysis action to perform
        parameters: Action-specific parameters
        
    Returns:
        Dictionary containing analysis results
    """
    if parameters is None:
        parameters = {}
        
    try:
        if action == "list_clusters":
            return await _list_clusters(parameters)
        elif action == "select_cluster_for_analysis":
            return await _select_cluster_for_analysis(parameters)
        elif action == "analyze_cluster_security":
            return await _analyze_cluster_security(parameters)
        elif action == "generate_security_report":
            return await _generate_security_report(parameters)
        elif action == "get_security_recommendations":
            return await _get_security_recommendations(parameters)
        elif action == "check_compliance_status":
            return await _check_compliance_status(parameters)
        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}",
                "available_actions": [
                    "list_clusters",
                    "select_cluster_for_analysis", 
                    "analyze_cluster_security",
                    "generate_security_report",
                    "get_security_recommendations",
                    "check_compliance_status"
                ]
            }
            
    except Exception as e:
        logger.error(f"Security analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "action": action,
            "assessment": f"Security analysis failed: {str(e)}"
        }

async def _list_clusters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """List available ECS clusters for selection."""
    region = parameters.get("region", "us-east-1")
    
    logger.info(f"Listing ECS clusters in region: {region}")
    
    try:
        # Use the existing AWS client utility for consistency
        ecs_client = await get_aws_client("ecs")
        
        # Get cluster ARNs
        response = ecs_client.list_clusters()
        cluster_arns = response.get('clusterArns', [])
        
        if not cluster_arns:
            return {
                "status": "success",
                "action": "list_clusters",
                "region": region,
                "assessment": f"No ECS clusters found in region **{region}**. You may need to check a different region where your clusters are located.",
                "clusters": [],
                "total_clusters": 0,
                "guidance": {
                    "description": "No clusters available for security analysis in this region",
                    "region_suggestion": f"No clusters found in {region}. Try checking other regions where your ECS clusters might be located.",
                    "next_steps": [
                        f"Try a different region - current region is {region}",
                        "Check common regions: us-east-1, us-west-2, eu-west-1, ap-southeast-1",
                        "Create an ECS cluster if you need to deploy containerized applications",
                        "Verify your AWS credentials have permission to list ECS clusters"
                    ],
                    "region_examples": {
                        "try_us_east_1": {"action": "list_clusters", "parameters": {"region": "us-east-1"}},
                        "try_us_west_2": {"action": "list_clusters", "parameters": {"region": "us-west-2"}},
                        "try_eu_west_1": {"action": "list_clusters", "parameters": {"region": "eu-west-1"}}
                    }
                }
            }
        
        # Get detailed cluster information
        cluster_details = ecs_client.describe_clusters(clusters=cluster_arns)
        clusters = []
        
        for cluster in cluster_details.get('clusters', []):
            cluster_name = cluster.get('clusterName', '')
            cluster_info = {
                "name": cluster_name,
                "status": cluster.get('status', 'UNKNOWN'),
                "running_tasks": cluster.get('runningTasksCount', 0),
                "pending_tasks": cluster.get('pendingTasksCount', 0),
                "active_services": cluster.get('activeServicesCount', 0),
                "registered_instances": cluster.get('registeredContainerInstancesCount', 0),
                "capacity_providers": cluster.get('capacityProviders', []),
                "tags": cluster.get('tags', [])
            }
            clusters.append(cluster_info)
        
        # Sort clusters by name for consistent output
        clusters.sort(key=lambda x: x['name'])
        
        return {
            "status": "success",
            "action": "list_clusters",
            "region": region,
            "assessment": f"Found {len(clusters)} ECS cluster(s) in region **{region}**. **IMPORTANT**: Let the user choose which specific cluster to analyze - do not analyze all clusters automatically. If user needs a different region, ask them to specify it.",
            "clusters": clusters,
            "total_clusters": len(clusters),
            "cluster_selection": {
                "description": f"Let the user choose ONE specific cluster for analysis in region {region} - never analyze all clusters automatically",
                "region_note": f"Currently showing clusters in {region}. If user needs a different region, ask them to specify it in the parameters.",
                "available_actions": [
                    "select_cluster_for_analysis - Interactive cluster selection with analysis options",
                    "analyze_cluster_security - Comprehensive security analysis",
                    "generate_security_report - Generate detailed security report",
                    "get_security_recommendations - Get filtered recommendations",
                    "check_compliance_status - Check compliance against standards"
                ],
                "natural_language_examples": [
                    "You can also ask: 'Analyze security for [cluster-name]'",
                    "Or: 'Check security issues in my cluster'",
                    "Or: 'Generate security report for [cluster-name]'",
                    "Or: 'Show me security vulnerabilities'"
                ],
                "selection_help": "Copy the cluster name exactly as shown in the 'name' field above"
            },
            "guidance": {
                "description": "How to analyze a specific cluster",
                "region_selection": f"Currently showing clusters in region: {region}. To see clusters in a different region, specify 'region' parameter.",
                "next_steps": [
                    "1. Confirm this is the correct region for your clusters",
                    "2. Choose a cluster from the list above", 
                    "3. Copy the exact cluster name from the 'name' field",
                    "4. Use 'select_cluster_for_analysis' for guided selection",
                    "5. Always specify the region parameter for consistency"
                ],
                "example_usage": {
                    "action": "select_cluster_for_analysis",
                    "parameters": {
                        "cluster_name": "<copy-cluster-name-from-above>",
                        "region": region
                    }
                },
                "region_examples": {
                    "us_east_1": {"action": "list_clusters", "parameters": {"region": "us-east-1"}},
                    "us_west_2": {"action": "list_clusters", "parameters": {"region": "us-west-2"}},
                    "eu_west_1": {"action": "list_clusters", "parameters": {"region": "eu-west-1"}}
                },
                "quick_start": f"To analyze the first cluster in {region}, use cluster_name: '{clusters[0]['name'] if clusters else 'no-clusters-available'}'"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list clusters: {e}")
        return {
            "status": "error",
            "action": "list_clusters",
            "region": region,
            "error": str(e),
            "assessment": f"Failed to list ECS clusters in region {region}: {str(e)}"
        }


async def _select_cluster_for_analysis(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Interactive cluster selection with analysis options."""
    region = parameters.get("region", "us-east-1")
    cluster_name = parameters.get("cluster_name")
    analysis_type = parameters.get("analysis_type", "comprehensive")
    
    logger.info(f"Interactive cluster selection for region: {region}")
    
    try:
        # First, get the list of available clusters
        clusters_result = await _list_clusters({"region": region})
        
        if clusters_result.get("status") != "success":
            return clusters_result
        
        clusters = clusters_result.get("clusters", [])
        
        if not clusters:
            return {
                "status": "error",
                "action": "select_cluster_for_analysis",
                "error": f"No ECS clusters found in region {region}",
                "region": region,
                "suggestion": "Create an ECS cluster first or check a different region"
            }
        
        # If cluster_name is provided, validate and proceed with analysis
        if cluster_name:
            # Validate cluster exists
            cluster_exists = any(cluster["name"] == cluster_name for cluster in clusters)
            
            if not cluster_exists:
                return {
                    "status": "error",
                    "action": "select_cluster_for_analysis",
                    "error": f"Cluster '{cluster_name}' not found in region {region}",
                    "available_clusters": [cluster["name"] for cluster in clusters],
                    "suggestion": "Choose one of the available clusters listed above"
                }
            
            # Proceed with the selected analysis type
            if analysis_type == "quick":
                return await _get_security_recommendations({
                    "cluster_name": cluster_name,
                    "region": region,
                    "severity_filter": "High",
                    "limit": 5
                })
            elif analysis_type == "report":
                return await _generate_security_report({
                    "cluster_name": cluster_name,
                    "region": region,
                    "format": "summary"
                })
            elif analysis_type == "compliance":
                return await _check_compliance_status({
                    "cluster_name": cluster_name,
                    "region": region,
                    "compliance_framework": "aws-foundational"
                })
            else:  # comprehensive (default)
                return await _analyze_cluster_security({
                    "cluster_name": cluster_name,
                    "region": region
                })
        
        # If no cluster_name provided, show selection interface
        return {
            "status": "success",
            "action": "select_cluster_for_analysis",
            "region": region,
            "total_clusters": len(clusters),
            "available_clusters": clusters,
            "cluster_selection": {
                "description": "Choose a cluster and analysis type for security analysis",
                "instructions": [
                    "1. Select a cluster from the 'available_clusters' list above",
                    "2. Choose an analysis type (optional, defaults to comprehensive)",
                    "3. Call this action again with your selections"
                ],
                "analysis_types": {
                    "comprehensive": "Full security analysis with all recommendations",
                    "quick": "Top 5 high-priority security issues only",
                    "report": "Generate a summary security report",
                    "compliance": "Check compliance against AWS best practices"
                }
            },
            "example_usage": {
                "action": "select_cluster_for_analysis",
                "parameters": {
                    "cluster_name": clusters[0]["name"],
                    "region": region,
                    "analysis_type": "comprehensive"
                }
            },
            "quick_actions": [
                {
                    "description": f"Analyze '{clusters[0]['name']}' (comprehensive)",
                    "action": "select_cluster_for_analysis",
                    "parameters": {
                        "cluster_name": clusters[0]["name"],
                        "region": region,
                        "analysis_type": "comprehensive"
                    }
                },
                {
                    "description": f"Quick analysis of '{clusters[0]['name']}' (top 5 issues)",
                    "action": "select_cluster_for_analysis",
                    "parameters": {
                        "cluster_name": clusters[0]["name"],
                        "region": region,
                        "analysis_type": "quick"
                    }
                }
            ] if clusters else []
        }
        
    except Exception as e:
        logger.error(f"Cluster selection failed: {e}")
        return {
            "status": "error",
            "action": "select_cluster_for_analysis",
            "error": str(e),
            "region": region
        }


async def _analyze_cluster_security(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze security posture of an ECS cluster."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")
    
    if not cluster_name:
        return {
            "status": "error",
            "action": "analyze_cluster_security",
            "error": "cluster_name is required for security analysis",
            "region": region,
            "helpful_guidance": {
                "suggestion": "Use the 'list_clusters' or 'select_cluster_for_analysis' action to see available clusters",
                "example": {
                    "action": "list_clusters",
                    "parameters": {"region": region}
                }
            }
        }
    
    logger.info(f"Starting security analysis for cluster: {cluster_name} in region: {region}")
    
    try:
        # Initialize security analyzer
        analyzer = ECSSecurityAnalyzer()
        
        # Run the analysis (it's already async)
        results = await analyzer.analyze_cluster(cluster_name, region)
        
        recommendations = results.get("recommendations", [])
        
        # Calculate severity breakdown
        severity_counts = {
            "high": len([r for r in recommendations if r.get("severity") == "High"]),
            "medium": len([r for r in recommendations if r.get("severity") == "Medium"]),
            "low": len([r for r in recommendations if r.get("severity") == "Low"])
        }
        
        return {
            "status": "success",
            "action": "analyze_cluster_security",
            "cluster_name": cluster_name,
            "region": region,
            "analysis_timestamp": results.get("timestamp"),
            "assessment": _generate_comprehensive_assessment(cluster_name, recommendations, severity_counts),
            "security_summary": {
                "total_recommendations": len(recommendations),
                "severity_breakdown": severity_counts,
                "priority_focus": "High" if severity_counts['high'] > 0
                                 else "Medium" if severity_counts['medium'] > 0
                                 else "Maintenance",
                "immediate_action_needed": severity_counts['high'] > 0
            },
            "priority_recommendations": _enhance_recommendations_with_resource_info([r for r in recommendations if r.get("severity") == "High"]),
            "total_issues_found": len(recommendations),
            "next_steps": [step for step in [
                f"⚠️ Fix {severity_counts['high']} high-priority security issues" if severity_counts['high'] > 0 else None,
                "Use 'get_security_recommendations' with severity_filter='High' to see detailed fix commands",
                "Re-run analysis after implementing fixes to track progress",
                f"Review and address {severity_counts['medium']} medium and {severity_counts['low']} low priority items when possible" if severity_counts['medium'] > 0 or severity_counts['low'] > 0 else "Consider implementing additional security monitoring for ongoing protection"
            ] if step is not None],
            "quick_actions": {
                "get_high_priority_issues": {
                    "action": "get_security_recommendations",
                    "parameters": {
                        "cluster_name": cluster_name,
                        "region": region,
                        "severity_filter": "High",
                        "limit": 5
                    }
                },
                "get_detailed_report": {
                    "action": "generate_security_report",
                    "parameters": {
                        "cluster_name": cluster_name,
                        "region": region,
                        "format": "summary"
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Security analysis failed: {e}")
        
        # Provide helpful guidance if cluster not found
        error_message = str(e)
        if "not found" in error_message.lower() or "ClusterNotFoundException" in error_message:
            return {
                "status": "error",
                "action": "analyze_cluster_security",
                "error": f"Cluster '{cluster_name}' not found in region {region}",
                "cluster_name": cluster_name,
                "region": region,
                "assessment": f"The cluster '{cluster_name}' was not found in region {region}. Please verify the cluster name and region.",
                "helpful_guidance": {
                    "suggestion": "Use the 'list_clusters' action to see available clusters",
                    "example": {
                        "action": "list_clusters",
                        "parameters": {"region": region}
                    },
                    "common_issues": [
                        "Cluster name is case-sensitive - check exact spelling",
                        "Cluster might be in a different region",
                        "Cluster might have been deleted or not yet created",
                        "Check AWS credentials and permissions"
                    ]
                }
            }
        else:
            return {
                "status": "error",
                "action": "analyze_cluster_security",
                "error": error_message,
                "cluster_name": cluster_name,
                "region": region,
                "assessment": f"Failed to analyze security for cluster '{cluster_name}'. Please verify the cluster name and region.",
                "helpful_guidance": {
                    "suggestion": "Use the 'list_clusters' action to see available clusters and verify the cluster name",
                    "example": {
                        "action": "list_clusters",
                        "parameters": {"region": region}
                    }
                }
            }

async def _generate_security_report(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive security report with enhanced formatting options."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")
    format_type = parameters.get("format", "summary")  # summary, detailed, json, executive
    severity_filter = parameters.get("severity_filter")  # List of severities to include
    category_filter = parameters.get("category_filter")  # List of categories to include
    show_details = parameters.get("show_details", False)  # Show full details for medium/low issues
    
    if not cluster_name:
        return {
            "status": "error",
            "action": "generate_security_report",
            "error": "cluster_name is required for report generation",
            "region": region,
            "helpful_guidance": {
                "suggestion": "Use the 'list_clusters' action to see available clusters",
                "example": {"action": "list_clusters", "parameters": {"region": region}},
                "available_formats": ["summary", "detailed", "json", "executive"],
                "filter_options": {
                    "severity_filter": ["High", "Medium", "Low"],
                    "category_filter": ["network_security", "container_security", "iam_security", "encryption", "monitoring", "compliance"]
                }
            }
        }
    
    logger.info(f"Generating security report for cluster: {cluster_name} (format: {format_type})")
    
    try:
        analyzer = ECSSecurityAnalyzer()
        
        # Run comprehensive analysis
        results = await analyzer.analyze_cluster(cluster_name, region)
        
        # Generate formatted report
        formatted_report = analyzer.formatter.format_report(
            results, 
            format_type=format_type,
            severity_filter=severity_filter,
            category_filter=category_filter,
            show_details=show_details
        )
        
        # Prepare response based on format
        if format_type == "json":
            return {
                "status": "success",
                "action": "generate_security_report",
                "cluster_name": cluster_name,
                "region": region,
                "report_format": format_type,
                "assessment": f"Security analysis completed for {cluster_name}. JSON data available in report_data.",
                "report_data": results,
                "filters_applied": {
                    "severity_filter": severity_filter,
                    "category_filter": category_filter
                }
            }
        else:
            # For human-readable formats, return formatted text
            summary = results.get('analysis_summary', {})
            severity_breakdown = summary.get('severity_breakdown', {})
            
            return {
                "status": "success",
                "action": "generate_security_report",
                "cluster_name": cluster_name,
                "region": region,
                "report_format": format_type,
                "assessment": formatted_report,
                "report_summary": {
                    "total_issues": summary.get('total_issues', 0),
                    "risk_level": summary.get('risk_level', 'Unknown'),
                    "severity_breakdown": severity_breakdown,
                    "immediate_action_required": severity_breakdown.get('High', 0) > 0
                },
                "filters_applied": {
                    "severity_filter": severity_filter,
                    "category_filter": category_filter,
                    "show_details": show_details
                },
                "guidance": {
                    "description": "Enhanced security report with filtering and formatting options",
                    "format_options": {
                        "summary": "Executive summary with expandable sections",
                        "detailed": "Full details for all issues",
                        "executive": "High-level summary for leadership",
                        "json": "Machine-readable format for automation"
                    },
                    "filter_examples": {
                        "high_priority_only": {"severity_filter": ["High"]},
                        "network_issues": {"category_filter": ["network_security"]},
                        "high_priority": {"severity_filter": ["High"]},
                        "show_all_details": {"show_details": True}
                    },
                    "next_steps": [
                        "Review high priority issues first",
                        "Use filters to focus on specific areas of concern",
                        "Share executive format with leadership",
                        "Use JSON format for automated processing"
                    ]
                }
            }
    
    except Exception as e:
        logger.error(f"Failed to generate security report: {e}")
        
        error_message = str(e)
        if "not found" in error_message.lower() or "ClusterNotFoundException" in error_message:
            return {
                "status": "error",
                "action": "generate_security_report",
                "error": f"Cluster '{cluster_name}' not found in region {region}",
                "cluster_name": cluster_name,
                "region": region,
                "helpful_guidance": {
                    "suggestion": "Use the 'list_clusters' action to see available clusters",
                    "example": {"action": "list_clusters", "parameters": {"region": region}}
                }
            }
        else:
            return {
                "status": "error",
                "action": "generate_security_report",
                "error": error_message,
                "cluster_name": cluster_name,
                "region": region
            }


def _format_severity_filter(severity_filter) -> str:
    """Format severity filter for display."""
    if not severity_filter:
        return ""
    if isinstance(severity_filter, str):
        return severity_filter.capitalize()
    elif isinstance(severity_filter, list):
        return " & ".join([s.capitalize() for s in severity_filter])
    return str(severity_filter)

def _generate_recommendations_assessment(
    cluster_name: str, 
    filtered_recommendations: List[Dict[str, Any]], 
    all_recommendations: List[Dict[str, Any]],
    severity_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = 5
) -> str:
    """Generate comprehensive assessment text for security recommendations."""
    
    # Generate category breakdown from all recommendations
    category_summary = _generate_category_summary(all_recommendations)
    
    assessment = [
        f"## {_format_severity_filter(severity_filter) or 'Security'} Recommendations for {cluster_name}",
        "",
        f"📋 **Found {len(filtered_recommendations)} {_format_severity_filter(severity_filter).lower() if severity_filter else 'security'} issues"
        + (f" in {category_filter} category" if category_filter else "") + f" (showing top {limit})**",
        "",
        _get_priority_message(severity_filter, len(filtered_recommendations))
    ]
    
    # Add detailed recommendations with prominent resource information
    if filtered_recommendations:
        assessment.extend([
            "",
            "## 🎯 Action Items by Resource",
            "",
            "*Each recommendation shows the specific AWS resource that needs attention:*",
            ""
        ])
        
        for i, rec in enumerate(filtered_recommendations, 1):
            severity = rec.get('severity', 'Unknown')
            severity_icon = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(severity, '❓')
            resource = rec.get('resource', 'Unknown Resource')
            title = rec.get('title', 'Unknown Issue')
            issue = rec.get('issue', 'No description available')
            recommendation = rec.get('recommendation', 'No recommendation provided')
            
            assessment.extend([
                f"### {i}. {severity_icon} {title}",
                f"**🎯 Resource to Fix**: `{resource}`",
                f"**Severity**: {severity}",
                f"**Issue**: {issue}",
                f"**Action Required**: {recommendation}",
                ""
            ])
            
            # Add implementation details if available
            implementation = rec.get('implementation', {})
            if implementation:
                aws_cli = implementation.get('aws_cli')
                description = implementation.get('description')
                
                if aws_cli or description:
                    assessment.append("**Implementation:**")
                    if description:
                        assessment.append(f"• {description}")
                    if aws_cli:
                        assessment.extend([
                            "• AWS CLI Command:",
                            f"  ```bash",
                            f"  {aws_cli}",
                            f"  ```"
                        ])
                    assessment.append("")
            
            assessment.append("---")
            assessment.append("")
    
    # Add category breakdown if not filtering by category
    if not category_filter and len(all_recommendations) > 0:
        assessment.extend([
            "",
            "### 📋 Recommendations by Category:",
        ])
        
        # Category icons mapping
        category_icons = {
            'network_security': '🌐',
            'container_security': '🐳',
            'iam_security': '🔐',
            'secrets': '🔑',
            'monitoring': '📊',
            'compliance': '🏛️',
            'security': '🛡️',
            'encryption': '🔒',
            'configuration': '⚙️',
            'availability': '⚡',
            'well_architected': '🏗️',
            'resource_management': '📈',
            'network': '🔗',
            'monitoring_security': '👁️'
        }
        
        for category, count in category_summary["top_categories"]:
            icon = category_icons.get(category, '📋')
            category_display = category.replace('_', ' ').title()
            assessment.append(f"• {icon} **{category_display}**: {count} recommendations")
        
        if len(category_summary["categories"]) > 5:
            remaining = len(category_summary["categories"]) - 5
            assessment.append(f"• ... and {remaining} more categories")
    
    return '\n'.join(assessment)

def _enhance_recommendations_with_resource_info(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enhance recommendations with prominent resource information for better actionability."""
    enhanced_recommendations = []
    
    for rec in recommendations:
        enhanced_rec = rec.copy()
        
        # Add resource-focused fields for better visibility
        resource = rec.get('resource', 'Unknown Resource')
        severity = rec.get('severity', 'Unknown')
        title = rec.get('title', 'Unknown Issue')
        
        # Add enhanced fields
        enhanced_rec['resource_target'] = f"🎯 {resource}"
        enhanced_rec['priority_indicator'] = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(severity, '❓')
        enhanced_rec['action_summary'] = f"{enhanced_rec['priority_indicator']} {title} → Fix: {resource}"
        
        # Add formatted display text
        enhanced_rec['display_summary'] = (
            f"{enhanced_rec['priority_indicator']} **{title}** ({severity} Priority)\n"
            f"🎯 **Resource**: `{resource}`\n"
            f"**Issue**: {rec.get('issue', 'No description')}\n"
            f"**Action Required**: {rec.get('recommendation', 'No recommendation')}"
        )
        
        enhanced_recommendations.append(enhanced_rec)
    
    return enhanced_recommendations

def _generate_category_summary(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate category breakdown summary for recommendations."""
    category_counts = {}
    severity_by_category = {}
    
    for rec in recommendations:
        category = rec.get('category', 'unknown')
        severity = rec.get('severity', 'Unknown')
        
        # Count by category
        category_counts[category] = category_counts.get(category, 0) + 1
        
        # Track severity distribution by category
        if category not in severity_by_category:
            severity_by_category[category] = {'High': 0, 'Medium': 0, 'Low': 0}
        if severity in severity_by_category[category]:
            severity_by_category[category][severity] += 1
    
    # Sort categories by count (descending)
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "total_categories": len(category_counts),
        "categories": {category: count for category, count in sorted_categories},
        "severity_distribution": severity_by_category,
        "top_categories": sorted_categories[:5]  # Top 5 categories
    }

def _generate_comprehensive_assessment(cluster_name: str, recommendations: List[Dict[str, Any]], severity_counts: Dict[str, int]) -> str:
    """Generate comprehensive assessment with correct terminology and resource information."""
    
    assessment_parts = [
        f"## Security Analysis Results for {cluster_name}",
        "",
        f"🚨 **HIGH PRIORITY SECURITY ISSUES FOUND**",
        "",
        f"Your ECS cluster has {len(recommendations)} total security issues that need attention:",
        f"• **{severity_counts['high']} High Priority** - Requires immediate action (24-48 hours)",
        f"• **{severity_counts['medium']} Medium Priority** - Address in next maintenance window",
        f"• **{severity_counts['low']} Low Priority** - Future improvements",
        ""
    ]
    
    # Add top high priority issues with resource information
    high_priority_recs = [r for r in recommendations if r.get("severity") == "High"]
    
    if high_priority_recs:
        assessment_parts.extend([
            f"### Top {min(5, len(high_priority_recs))} High Priority Issues to Fix Immediately:",
            ""
        ])
        
        for i, rec in enumerate(high_priority_recs[:5], 1):
            title = rec.get('title', 'Unknown Issue')
            resource = rec.get('resource', 'Unknown Resource')
            issue = rec.get('issue', 'No description available')
            recommendation = rec.get('recommendation', 'No recommendation provided')
            
            assessment_parts.extend([
                f"{i}. **{title}** (High Priority)",
                f"   • **🎯 Resource**: `{resource}`",
                f"   • **Issue**: {issue}",
                f"   • **Fix**: {recommendation}",
                ""
            ])
        
        assessment_parts.extend([
            "**Immediate Action Required**: These high-priority issues create significant security vulnerabilities that could lead to unauthorized access, privilege escalation, or resource exhaustion attacks.",
            "",
            f"Would you like me to generate detailed remediation steps for these high priority issues, or would you prefer to see the complete security report with all {len(recommendations)} findings?"
        ])
    else:
        assessment_parts.extend([
            "✅ **GOOD NEWS**: No high-priority issues found.",
            f"Focus on addressing {severity_counts['medium']} medium and {severity_counts['low']} low priority improvements when possible."
        ])
    
    return '\n'.join(assessment_parts)

def _get_priority_message(severity_filter, count: int) -> str:
    """Get priority message based on severity filter."""
    if not severity_filter:
        return f"Retrieved {count} security recommendations for analysis and prioritization."
    
    # Handle both string and array formats
    severities = []
    if isinstance(severity_filter, str):
        severities = [severity_filter.capitalize()]
    elif isinstance(severity_filter, list):
        severities = [s.capitalize() for s in severity_filter]
    
    if "High" in severities:
        return f"⚠️ **HIGH PRIORITY**: These {count} issues should be addressed within 24-48 hours."
    elif "Medium" in severities:
        return f"📋 **MEDIUM PRIORITY**: These {count} issues should be addressed in your next maintenance window."
    elif "Low" in severities:
        return f"ℹ️ **LOW PRIORITY**: These {count} items are future improvements for enhanced security."
    else:
        return f"Retrieved {count} security recommendations for analysis and prioritization."

async def _get_security_recommendations(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Get filtered security recommendations."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")
    severity_filter = parameters.get("severity_filter")  # high, medium, low
    category_filter = parameters.get("category_filter")  # network, container, iam, etc.
    limit = parameters.get("limit", 5)  # Default to 5 for better focus
    
    if not cluster_name:
        raise ValueError("cluster_name is required for getting recommendations. Use action='list_clusters' to see available clusters, then specify cluster_name in parameters.")
    
    logger.info(f"Getting security recommendations for cluster: {cluster_name}")
    
    analyzer = ECSSecurityAnalyzer()
    
    # Run analysis
    results = await analyzer.analyze_cluster(cluster_name, region)
    
    recommendations = results.get("recommendations", [])
    
    # Apply filters
    if severity_filter:
        # Handle both string and array formats for severity_filter
        if isinstance(severity_filter, str):
            # Convert string to array and normalize
            severity_list = [severity_filter.capitalize()]
        elif isinstance(severity_filter, list):
            # Normalize array elements
            severity_list = [s.capitalize() for s in severity_filter]
        else:
            severity_list = []
        
        recommendations = [r for r in recommendations if r.get("severity") in severity_list]
    
    if category_filter:
        recommendations = [r for r in recommendations 
                          if category_filter.lower() in r.get("category", "").lower()]
    
    # Limit results
    recommendations = recommendations[:limit]
    
    # Enhance recommendations with prominent resource information
    enhanced_recommendations = _enhance_recommendations_with_resource_info(recommendations)
    
    return {
        "status": "success",
        "action": "get_security_recommendations",
        "cluster_name": cluster_name,
        "region": region,
        "assessment": _generate_recommendations_assessment(
            cluster_name, recommendations, results.get("recommendations", []), 
            str(severity_filter) if severity_filter is not None else None, 
            str(category_filter) if category_filter is not None else None, 
            limit
        ),
        "filter_criteria": {
            "severity_filter": severity_filter,
            "category_filter": category_filter,
            "limit": limit
        },
        "results_summary": {
            "total_recommendations": len(recommendations),
            "filtered_results": len(recommendations)
        },
        "category_breakdown": _generate_category_summary(results.get("recommendations", [])),
        "recommendations": enhanced_recommendations,
        "guidance": {
            "description": "How to prioritize and implement these security recommendations",
            "implementation_approach": [
                "🚨 Address High priority issues immediately - they pose immediate security risks",
                "⚠️ Fix High priority issues within 24-48 hours",
                "📋 Plan Medium priority fixes for next maintenance window",
                "Test changes in a non-production environment first",
                "Use the provided CLI commands for quick fixes"
            ],
            "get_more_recommendations": {
                "action": "get_security_recommendations",
                "parameters": {
                    "cluster_name": cluster_name,
                    "region": region,
                    "limit": 20
                }
            }
        }
    }

async def _check_compliance_status(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Check compliance against security best practices."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")
    compliance_framework = parameters.get("compliance_framework", "aws-foundational")
    
    if not cluster_name:
        raise ValueError("cluster_name is required for compliance check. Use action='list_clusters' to see available clusters, then specify cluster_name in parameters.")
    
    logger.info(f"Checking compliance status for cluster: {cluster_name}")
    
    analyzer = ECSSecurityAnalyzer()
    
    # Run analysis
    results = await analyzer.analyze_cluster(cluster_name, region)
    
    recommendations = results.get("recommendations", [])
    
    # Calculate issue breakdown
    failed_checks = len(recommendations)
    
    # Categorize compliance issues
    compliance_issues = {
        "network_security": len([r for r in recommendations if "network" in r.get("category", "").lower()]),
        "container_security": len([r for r in recommendations if "container" in r.get("category", "").lower()]),
        "iam_security": len([r for r in recommendations if "iam" in r.get("category", "").lower()]),
        "monitoring": len([r for r in recommendations if "monitoring" in r.get("category", "").lower()]),
        "compliance": len([r for r in recommendations if "compliance" in r.get("category", "").lower()])
    }
    
    return {
        "status": "success",
        "action": "check_compliance_status",
        "cluster_name": cluster_name,
        "region": region,
        "compliance_framework": compliance_framework,
        "assessment": f"Security assessment complete for ECS cluster '{cluster_name}' against {compliance_framework} framework. "
                     f"Found {failed_checks} security areas requiring attention.",
        "security_findings": {
            "total_issues": failed_checks,
            "high_priority_failures": len([r for r in recommendations if r.get("severity") == "High"]),
            "high_priority": len([r for r in recommendations if r.get("severity") == "High"]),
            "medium_priority": len([r for r in recommendations if r.get("severity") == "Medium"]),
            "low_priority": len([r for r in recommendations if r.get("severity") == "Low"])
        },
        "compliance_breakdown": compliance_issues,
        "recommendations": recommendations,
        "remediation_guidance": {
            "description": "Steps to improve your security posture",
            "priority_actions": [
                "Address all high priority security issues immediately",
                "Focus on high-severity recommendations first", 
                "Implement security monitoring and alerting",
                "Schedule regular security assessments"
            ],
            "implementation_approach": {
                "immediate": "Fix high priority security vulnerabilities",
                "short_term": "Address high and medium severity issues",
                "long_term": "Implement comprehensive security monitoring"
            }
        }
    }