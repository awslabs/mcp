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

"""Handler for EKS resiliency checks in the EKS MCP Server."""

import json  # Needed for json.dumps in some checks
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import ResiliencyCheckResponse
from collections import Counter
from loguru import logger
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, Optional


class EKSResiliencyHandler:
    """Handler for EKS resiliency checks in the EKS MCP Server."""

    def __init__(self, mcp, client_cache):
        """Initialize the EKS resiliency handler.

        Args:
            mcp: The MCP server instance
            client_cache: K8sClientCache instance to share between handlers
        """
        self.mcp = mcp
        self.client_cache = client_cache

        # Register the comprehensive check tool
        self.mcp.tool(name='check_eks_resiliency')(self.check_eks_resiliency)

    async def check_eks_resiliency(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ..., description='Name of the EKS cluster to check for resiliency best practices.'
        ),
        namespace: Optional[str] = Field(
            None, description='Optional namespace to limit the check scope.'
        ),
    ) -> ResiliencyCheckResponse:
        """Check EKS cluster for resiliency best practices.

        This tool runs a comprehensive set of resiliency checks against your EKS cluster
        to identify potential issues that could impact application availability and
        provides remediation guidance.

        Checks included:
        Application Related Checks
        - A1: Singleton pods without controller management
        - A2: Deployments with only one replica
        - A3: Multi-replica deployments without pod anti-affinity
        - A4: Deployments without liveness probes
        - A5: Deployments without readiness probes
        - A6: Workloads without Pod Disruption Budgets
        - A7: Kubernetes Metrics Server
        - A8: Horizontal Pod Autoscaler (HPA)
        - A9: Custom metrics scaling
        - A10: Vertical Pod Autoscaler (VPA)
        - A11: PreStop hooks for graceful termination
        - A12: Service mesh usage
        - A13: Application monitoring
        - A14: Centralized logging


        ControlPlane Related Checks
        - C1: Monitor Control Plane Logs
        - C2: Cluster Authentication
        - C3: Running large clusters
        - C4: EKS Control Plane Endpoint Access Control
        - C5: Avoid catch-all admission webhooks

        DataPlane Related Checks
        - D1: Use Kubernetes Cluster Autoscaler or Karpenter
        - D2: Worker nodes spread across multiple AZs
        - D3: Configure Resource Requests/Limits
        - D4: Namespace ResourceQuotas
        - D5: Namespace LimitRanges
        - D6: Monitor CoreDNS metrics
        - D7: CoreDNS Configuration
        """
        try:
            logger.info(f'Starting resiliency check for cluster: {cluster_name}')

            # Get K8s client for the cluster
            try:
                client = self.client_cache.get_client(cluster_name)
                logger.info(f'Successfully obtained K8s client for cluster: {cluster_name}')
            except Exception as e:
                logger.error(f'Failed to get K8s client for cluster {cluster_name}: {str(e)}')
                error_msg = f'Failed to connect to cluster {cluster_name}: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return ResiliencyCheckResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    check_results=[
                        {
                            'check_name': 'Connection Error',
                            'compliant': False,
                            'impacted_resources': [],
                            'details': error_msg,
                            'remediation': 'Verify that the cluster exists and is accessible.',
                        }
                    ],
                    overall_compliant=False,
                    summary=f'Failed to connect to cluster {cluster_name}: {str(e)}',
                )

            # Run all checks and collect results
            check_results = []
            all_compliant = True

            # Application Related Checks
            # Check A1: Singleton pods without controller management
            try:
                logger.info('Running singleton pods check')
                singleton_result = self._check_singleton_pods(client, namespace)
                check_results.append(singleton_result)
                if not singleton_result['compliant']:
                    all_compliant = False
                logger.info(f'Singleton pods check completed: {singleton_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in singleton pods check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A1',
                        'check_name': 'Avoid running singleton Pods',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A2: Deployments with only one replica
            try:
                logger.info('Running multiple replicas check')
                replicas_result = self._check_multiple_replicas(client, namespace)
                check_results.append(replicas_result)
                if not replicas_result['compliant']:
                    all_compliant = False
                logger.info(f'Multiple replicas check completed: {replicas_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in multiple replicas check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A2',
                        'check_name': 'Run multiple replicas',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A3: Multi-replica deployments without pod anti-affinity
            try:
                logger.info('Running pod anti-affinity check')
                anti_affinity_result = self._check_pod_anti_affinity(client, namespace)
                check_results.append(anti_affinity_result)
                if not anti_affinity_result['compliant']:
                    all_compliant = False
                logger.info(
                    f'Pod anti-affinity check completed: {anti_affinity_result["compliant"]}'
                )
            except Exception as e:
                logger.error(f'Error in pod anti-affinity check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A3',
                        'check_name': 'Use pod anti-affinity',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A4: Deployments without liveness probes
            try:
                logger.info('Running liveness probe check')
                liveness_result = self._check_liveness_probe(client, namespace)
                check_results.append(liveness_result)
                if not liveness_result['compliant']:
                    all_compliant = False
                logger.info(f'Liveness probe check completed: {liveness_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in liveness probe check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A4',
                        'check_name': 'Use liveness probes',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A5: Deployments without readiness probes
            try:
                logger.info('Running readiness probe check')
                readiness_result = self._check_readiness_probe(client, namespace)
                check_results.append(readiness_result)
                if not readiness_result['compliant']:
                    all_compliant = False
                logger.info(f'Readiness probe check completed: {readiness_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in readiness probe check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A5',
                        'check_name': 'Use readiness probes',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A6: Critical workloads without Pod Disruption Budgets
            try:
                logger.info('Running pod disruption budget check')
                pdb_result = self._check_pod_disruption_budget(client, namespace)
                check_results.append(pdb_result)
                if not pdb_result['compliant']:
                    all_compliant = False
                logger.info(f'Pod disruption budget check completed: {pdb_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in pod disruption budget check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A6',
                        'check_name': 'Use Pod Disruption Budgets',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A7: Kubernetes Metrics Server
            try:
                logger.info('Running metrics server check')
                metrics_server_result = self._check_metrics_server(client, namespace)
                check_results.append(metrics_server_result)
                if not metrics_server_result['compliant']:
                    all_compliant = False
                logger.info(
                    f'Metrics server check completed: {metrics_server_result["compliant"]}'
                )
            except Exception as e:
                logger.error(f'Error in metrics server check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A7',
                        'check_name': 'Run Kubernetes Metrics Server',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A8: Horizontal Pod Autoscaler (HPA)
            try:
                logger.info('Running HPA check')
                hpa_result = self._check_horizontal_pod_autoscaler(client, namespace)
                check_results.append(hpa_result)
                if not hpa_result['compliant']:
                    all_compliant = False
                logger.info(f'HPA check completed: {hpa_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in HPA check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A8',
                        'check_name': 'Use Horizontal Pod Autoscaler',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A9: Custom metrics scaling
            try:
                logger.info('Running custom metrics check')
                custom_metrics_result = self._check_custom_metrics(client, namespace)
                check_results.append(custom_metrics_result)
                if not custom_metrics_result['compliant']:
                    all_compliant = False
                logger.info(
                    f'Custom metrics check completed: {custom_metrics_result["compliant"]}'
                )
            except Exception as e:
                logger.error(f'Error in custom metrics check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A9',
                        'check_name': 'Use custom metrics scaling',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A10: Vertical Pod Autoscaler (VPA)
            try:
                logger.info('Running VPA check')
                vpa_result = self._check_vertical_pod_autoscaler(client, namespace)
                check_results.append(vpa_result)
                if not vpa_result['compliant']:
                    all_compliant = False
                logger.info(f'VPA check completed: {vpa_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in VPA check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A10',
                        'check_name': 'Use Vertical Pod Autoscaler',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A11: PreStop hooks for graceful termination
            try:
                logger.info('Running preStop hooks check')
                prestop_result = self._check_prestop_hooks(client, namespace)
                check_results.append(prestop_result)
                if not prestop_result['compliant']:
                    all_compliant = False
                logger.info(f'PreStop hooks check completed: {prestop_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in preStop hooks check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A11',
                        'check_name': 'Use preStop hooks',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A12: Service mesh usage
            try:
                logger.info('Running service mesh check')
                service_mesh_result = self._check_service_mesh(client, namespace)
                check_results.append(service_mesh_result)
                if not service_mesh_result['compliant']:
                    all_compliant = False
                logger.info(f'Service mesh check completed: {service_mesh_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in service mesh check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A12',
                        'check_name': 'Use a Service Mesh',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A13: Application monitoring
            try:
                logger.info('Running monitoring check')
                monitoring_result = self._check_monitoring(client, namespace)
                check_results.append(monitoring_result)
                if not monitoring_result['compliant']:
                    all_compliant = False
                logger.info(f'Monitoring check completed: {monitoring_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in monitoring check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A13',
                        'check_name': 'Monitor your applications',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check A14: Centralized logging
            try:
                logger.info('Running centralized logging check')
                logging_result = self._check_centralized_logging(client, namespace)
                check_results.append(logging_result)
                if not logging_result['compliant']:
                    all_compliant = False
                logger.info(f'Centralized logging check completed: {logging_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in centralized logging check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'A14',
                        'check_name': 'Use centralized logging',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # ControlPlane Related Checks
            # Check C1: Monitor Control Plane Logs
            try:
                logger.info('Running control plane metrics check')
                c1_result = self._check_c1(client, cluster_name, namespace)
                check_results.append(c1_result)
                if not c1_result['compliant']:
                    all_compliant = False
                logger.info(f'Control plane metrics check completed: {c1_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in control plane metrics check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'C1',
                        'check_name': 'Monitor Control Plane Logs',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check C2: Cluster Authentication
            try:
                logger.info('Running cluster authentication check')
                c2_result = self._check_c2(client, cluster_name, namespace)
                check_results.append(c2_result)
                if not c2_result['compliant']:
                    all_compliant = False
                logger.info(f'Cluster authentication check completed: {c2_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in cluster authentication check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'C2',
                        'check_name': 'Cluster Authentication',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check C3: Running large clusters
            try:
                logger.info('Running large clusters check')
                c3_result = self._check_c3(client, cluster_name, namespace)
                check_results.append(c3_result)
                if not c3_result['compliant']:
                    all_compliant = False
                logger.info(f'Large clusters check completed: {c3_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in large clusters check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'C3',
                        'check_name': 'Running large clusters',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check C4: EKS Control Plane Endpoint Access Control
            try:
                logger.info('Running control plane endpoint access check')
                c4_result = self._check_c4(client, cluster_name, namespace)
                check_results.append(c4_result)
                if not c4_result['compliant']:
                    all_compliant = False
                logger.info(
                    f'Control plane endpoint access check completed: {c4_result["compliant"]}'
                )
            except Exception as e:
                logger.error(f'Error in control plane endpoint access check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'C4',
                        'check_name': 'EKS Control Plane Endpoint Access Control',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check C5: Avoid catch-all admission webhooks
            try:
                logger.info('Running admission webhooks check')
                c5_result = self._check_c5(client, cluster_name, namespace)
                check_results.append(c5_result)
                if not c5_result['compliant']:
                    all_compliant = False
                logger.info(f'Admission webhooks check completed: {c5_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in admission webhooks check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'C5',
                        'check_name': 'Avoid catch-all admission webhooks',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # DataPlane Related Checks
            # Check D1: Use Kubernetes Cluster Autoscaler or Karpenter
            try:
                logger.info('Running node autoscaling check')
                d1_result = self._check_d1(client, cluster_name, namespace)
                check_results.append(d1_result)
                if not d1_result['compliant']:
                    all_compliant = False
                logger.info(f'Node autoscaling check completed: {d1_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in node autoscaling check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'D1',
                        'check_name': 'Use Kubernetes Cluster Autoscaler or Karpenter',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check D2: Worker nodes spread across multiple AZs
            try:
                logger.info('Running AZ distribution check')
                d2_result = self._check_d2(client, cluster_name, namespace)
                check_results.append(d2_result)
                if not d2_result['compliant']:
                    all_compliant = False
                logger.info(f'AZ distribution check completed: {d2_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in AZ distribution check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'D2',
                        'check_name': 'Worker nodes spread across multiple AZs',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check D3: Configure Resource Requests/Limits
            try:
                logger.info('Running resource requests/limits check')
                d3_result = self._check_d3(client, cluster_name, namespace)
                check_results.append(d3_result)
                if not d3_result['compliant']:
                    all_compliant = False
                logger.info(f'Resource requests/limits check completed: {d3_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in resource requests/limits check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'D3',
                        'check_name': 'Configure Resource Requests/Limits',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check D4: Namespace ResourceQuotas
            try:
                logger.info('Running namespace resource quotas check')
                d4_result = self._check_d4(client, cluster_name, namespace)
                check_results.append(d4_result)
                if not d4_result['compliant']:
                    all_compliant = False
                logger.info(f'Namespace resource quotas check completed: {d4_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in namespace resource quotas check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'D4',
                        'check_name': 'Namespace ResourceQuotas',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check D5: Namespace LimitRanges
            try:
                logger.info('Running namespace limit ranges check')
                d5_result = self._check_d5(client, cluster_name, namespace)
                check_results.append(d5_result)
                if not d5_result['compliant']:
                    all_compliant = False
                logger.info(f'Namespace limit ranges check completed: {d5_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in namespace limit ranges check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'D5',
                        'check_name': 'Namespace LimitRanges',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check D6: Monitor CoreDNS metrics
            try:
                logger.info('Running CoreDNS metrics check')
                d6_result = self._check_d6(client, cluster_name, namespace)
                check_results.append(d6_result)
                if not d6_result['compliant']:
                    all_compliant = False
                logger.info(f'CoreDNS metrics check completed: {d6_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in CoreDNS metrics check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'D6',
                        'check_name': 'Monitor CoreDNS metrics',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # Check D7: CoreDNS Configuration
            try:
                logger.info('Running CoreDNS configuration check')
                d7_result = self._check_d7(client, cluster_name, namespace)
                check_results.append(d7_result)
                if not d7_result['compliant']:
                    all_compliant = False
                logger.info(f'CoreDNS configuration check completed: {d7_result["compliant"]}')
            except Exception as e:
                logger.error(f'Error in CoreDNS configuration check: {str(e)}')
                check_results.append(
                    {
                        'check_id': 'D7',
                        'check_name': 'CoreDNS Configuration',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Check failed with error: {str(e)}',
                        'remediation': '',
                    }
                )
                all_compliant = False

            # check_results.append(self._check_resource_requests(client, namespace))
            # etc.

            # Create summary with namespace information
            passed_count = sum(1 for r in check_results if r['compliant'])
            total_count = len(check_results)

            # Include namespace information in the summary
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            summary = f'Resiliency checks {scope_info}: {passed_count}/{total_count} PASSED'

            if not all_compliant:
                failed_checks = [r['check_name'] for r in check_results if not r['compliant']]
                summary += f'\nFailed checks: {", ".join(failed_checks)}'

            logger.info(f'Resiliency check completed with summary: {summary}')

            log_with_request_id(ctx, LogLevel.INFO, f'Resiliency check completed: {summary}')

            # Create the response object
            response = ResiliencyCheckResponse(
                isError=False,
                content=[TextContent(type='text', text=summary)],
                check_results=check_results,
                overall_compliant=all_compliant,
                summary=summary,
            )

            # Add complete JSON output to the content
            response_dict = {
                'check_results': check_results,
                'overall_compliant': all_compliant,
                'summary': summary,
            }
            json_output = json.dumps(response_dict, indent=2)
            response.content.append(
                TextContent(
                    type='text', text=f'Complete JSON output:\n```json\n{json_output}\n```'
                )
            )

            return response
        except Exception as e:
            logger.error(f'Unexpected error in check_eks_resiliency: {str(e)}')
            error_msg = f'Resiliency check failed with error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Create error check result
            error_check_result = {
                'check_name': 'Unexpected Error',
                'compliant': False,
                'impacted_resources': [],
                'details': f'An unexpected error occurred: {str(e)}',
                'remediation': 'Please check the server logs for more details.',
            }

            # Create the error response object
            error_summary = f'Resiliency check failed with error: {str(e)}'
            response = ResiliencyCheckResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                check_results=[error_check_result],
                overall_compliant=False,
                summary=error_summary,
            )

            # Add complete JSON output to the content
            response_dict = {
                'check_results': [error_check_result],
                'overall_compliant': False,
                'summary': error_summary,
            }
            json_output = json.dumps(response_dict, indent=2)
            response.content.append(
                TextContent(
                    type='text', text=f'Complete JSON output:\n```json\n{json_output}\n```'
                )
            )

            return response

    def _check_singleton_pods(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A1: Singleton pods without controller management."""
        singleton_pods = []
        try:
            logger.info(
                f'Starting singleton pods check, namespace: {namespace if namespace else "all"}'
            )

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking pods in namespace: {namespace}')
            else:
                logger.info('Checking pods across all namespaces')

            # Use the K8sApis list_resources method
            logger.info('Calling list_resources to get pods')
            pods_response = k8s_api.list_resources(kind='Pod', api_version='v1', **kwargs)

            # Log the number of pods found
            pod_count = len(pods_response.items) if hasattr(pods_response, 'items') else 0
            logger.info(f'Retrieved {pod_count} pods')

            # Process the response
            for pod in pods_response.items:
                try:
                    pod_dict = pod.to_dict() if hasattr(pod, 'to_dict') else pod

                    # Check if pod has owner references
                    metadata = pod_dict.get('metadata', {})
                    owner_refs = metadata.get('ownerReferences', [])

                    # Make sure we get the namespace from the pod metadata
                    pod_namespace = metadata.get('namespace')
                    if not pod_namespace:
                        logger.warning("Pod missing namespace information, using 'default'")
                        pod_namespace = 'default'

                    name = metadata.get('name', 'unknown')

                    logger.debug(f'Checking pod {pod_namespace}/{name}')

                    if not owner_refs:
                        logger.info(f'Found singleton pod: {pod_namespace}/{name}')
                        singleton_pods.append(f'{pod_namespace}/{name}')
                except Exception as pod_error:
                    logger.error(f'Error processing pod: {str(pod_error)}')

            is_compliant = len(singleton_pods) == 0
            details = f'Found {len(singleton_pods)} singleton pods not managed by controllers'
            logger.info(details)

            remediation = """Convert singleton pods to Deployments, StatefulSets, or other controllers:
1. Create a Deployment/StatefulSet manifest with the same pod spec
2. Apply the new controller resource
3. Delete the standalone pod once the controller-managed pod is running

Example:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      # Copy your pod spec here
```"""

            # Prepare a more detailed message that includes namespace information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            detailed_message = f'Found {len(singleton_pods)} singleton pods not managed by controllers {scope_info}'

            return {
                'check_id': 'A1',
                'check_name': 'Avoid running singleton Pods',
                'compliant': is_compliant,
                'impacted_resources': singleton_pods,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking singleton pods: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')
            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = f'API error while checking singleton pods {scope_info}: {str(e)}'

            return {
                'check_id': 'A1',
                'check_name': 'Avoid running singleton Pods',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_multiple_replicas(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A2: Deployments and StatefulSets with only one replica."""
        single_replica_workloads = []
        try:
            logger.info(
                f'Starting multiple replicas check, namespace: {namespace if namespace else "all"}'
            )

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking workloads in namespace: {namespace}')
            else:
                logger.info('Checking workloads across all namespaces')

            # Check Deployments
            logger.info('Calling list_resources to get deployments')
            deployments_response = k8s_api.list_resources(
                kind='Deployment', api_version='apps/v1', **kwargs
            )

            # Log the number of deployments found
            deployment_count = (
                len(deployments_response.items) if hasattr(deployments_response, 'items') else 0
            )
            logger.info(f'Retrieved {deployment_count} deployments')

            # Process deployments
            for deployment in deployments_response.items:
                try:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )

                    # Get deployment metadata
                    metadata = deployment_dict.get('metadata', {})
                    deploy_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Check replicas
                    spec = deployment_dict.get('spec', {})
                    replicas = spec.get('replicas', 0)

                    logger.debug(
                        f'Checking deployment {deploy_namespace}/{name} with {replicas} replicas'
                    )

                    if replicas == 1:
                        logger.info(f'Found single replica deployment: {deploy_namespace}/{name}')
                        single_replica_workloads.append(f'Deployment {deploy_namespace}/{name}')
                except Exception as deploy_error:
                    logger.error(f'Error processing deployment: {str(deploy_error)}')

            # Check StatefulSets
            logger.info('Calling list_resources to get statefulsets')
            try:
                statefulsets_response = k8s_api.list_resources(
                    kind='StatefulSet', api_version='apps/v1', **kwargs
                )

                # Log the number of statefulsets found
                statefulset_count = (
                    len(statefulsets_response.items)
                    if hasattr(statefulsets_response, 'items')
                    else 0
                )
                logger.info(f'Retrieved {statefulset_count} statefulsets')

                # Process statefulsets
                for statefulset in statefulsets_response.items:
                    try:
                        statefulset_dict = (
                            statefulset.to_dict()
                            if hasattr(statefulset, 'to_dict')
                            else statefulset
                        )

                        # Get statefulset metadata
                        metadata = statefulset_dict.get('metadata', {})
                        sts_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Check replicas
                        spec = statefulset_dict.get('spec', {})
                        replicas = spec.get('replicas', 0)

                        logger.debug(
                            f'Checking statefulset {sts_namespace}/{name} with {replicas} replicas'
                        )

                        if replicas == 1:
                            logger.info(
                                f'Found single replica statefulset: {sts_namespace}/{name}'
                            )
                            single_replica_workloads.append(f'StatefulSet {sts_namespace}/{name}')
                    except Exception as sts_error:
                        logger.error(f'Error processing statefulset: {str(sts_error)}')
            except Exception as sts_list_error:
                logger.warning(f'Error listing statefulsets: {str(sts_list_error)}')

            is_compliant = len(single_replica_workloads) == 0

            # Prepare a more detailed message that includes namespace information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            detailed_message = f'Found {len(single_replica_workloads)} workloads (Deployments/StatefulSets) with only 1 replica {scope_info}'
            logger.info(detailed_message)

            remediation = """Increase the number of replicas for your deployments and statefulsets:

For Deployments:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 2  # Increase this to at least 2 for high availability
  # ... rest of deployment spec
```

For StatefulSets:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: my-app
spec:
  replicas: 2  # Increase this to at least 2 for high availability
  # ... rest of statefulset spec
```

You can also use the kubectl scale command:
```
kubectl scale deployment/my-deployment --replicas=2
kubectl scale statefulset/my-statefulset --replicas=2
```"""

            return {
                'check_id': 'A2',
                'check_name': 'Run multiple replicas',
                'compliant': is_compliant,
                'impacted_resources': single_replica_workloads,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking multiple replicas: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = (
                f'API error while checking workloads for multiple replicas {scope_info}: {str(e)}'
            )

            return {
                'check_id': 'A2',
                'check_name': 'Run multiple replicas',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_pod_anti_affinity(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A3: Multi-replica deployments without pod anti-affinity."""
        deployments_without_anti_affinity = []
        try:
            logger.info(
                f'Starting pod anti-affinity check, namespace: {namespace if namespace else "all"}'
            )

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking deployments in namespace: {namespace}')
            else:
                logger.info('Checking deployments across all namespaces')

            # Use the K8sApis list_resources method to get deployments
            logger.info('Calling list_resources to get deployments')
            deployments_response = k8s_api.list_resources(
                kind='Deployment', api_version='apps/v1', **kwargs
            )

            # Log the number of deployments found
            deployment_count = (
                len(deployments_response.items) if hasattr(deployments_response, 'items') else 0
            )
            logger.info(f'Retrieved {deployment_count} deployments')

            # Process the response
            for deployment in deployments_response.items:
                try:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )

                    # Get deployment metadata
                    metadata = deployment_dict.get('metadata', {})
                    deploy_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Check replicas
                    spec = deployment_dict.get('spec', {})
                    replicas = spec.get('replicas', 0)

                    # Skip deployments with only 1 replica
                    if replicas <= 1:
                        logger.debug(
                            f'Skipping deployment {deploy_namespace}/{name} with {replicas} replicas'
                        )
                        continue

                    # Check for pod anti-affinity
                    template_spec = spec.get('template', {}).get('spec', {})
                    affinity = template_spec.get('affinity', {})
                    pod_anti_affinity = affinity.get('podAntiAffinity', None)

                    has_anti_affinity = pod_anti_affinity is not None

                    logger.debug(
                        f'Checking deployment {deploy_namespace}/{name} for pod anti-affinity: {has_anti_affinity}'
                    )

                    if not has_anti_affinity:
                        logger.info(
                            f'Found deployment without pod anti-affinity: {deploy_namespace}/{name}'
                        )
                        deployments_without_anti_affinity.append(f'{deploy_namespace}/{name}')
                except Exception as deploy_error:
                    logger.error(f'Error processing deployment: {str(deploy_error)}')

            is_compliant = len(deployments_without_anti_affinity) == 0

            # Prepare a more detailed message that includes namespace information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            detailed_message = f'Found {len(deployments_without_anti_affinity)} multi-replica deployments without pod anti-affinity {scope_info}'
            logger.info(detailed_message)

            remediation = """Add pod anti-affinity to your deployments to ensure pods are scheduled on different nodes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 2
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - my-app
              topologyKey: "kubernetes.io/hostname"
```"""

            return {
                'check_id': 'A3',
                'check_name': 'Use pod anti-affinity',
                'compliant': is_compliant,
                'impacted_resources': deployments_without_anti_affinity,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking pod anti-affinity: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = f'API error while checking deployments for pod anti-affinity {scope_info}: {str(e)}'

            return {
                'check_id': 'A3',
                'check_name': 'Use pod anti-affinity',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_liveness_probe(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A4: Deployments without liveness probes."""
        workloads_without_liveness = []
        try:
            logger.info(
                f'Starting liveness probe check, namespace: {namespace if namespace else "all"}'
            )

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking workloads in namespace: {namespace}')
            else:
                logger.info('Checking workloads across all namespaces')

            # Check Deployments
            logger.info('Checking Deployments for liveness probes')
            try:
                deployments_response = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', **kwargs
                )

                # Log the number of deployments found
                deployment_count = (
                    len(deployments_response.items)
                    if hasattr(deployments_response, 'items')
                    else 0
                )
                logger.info(f'Retrieved {deployment_count} deployments')

                # Process the response
                for deployment in deployments_response.items:
                    try:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )

                        # Get deployment metadata
                        metadata = deployment_dict.get('metadata', {})
                        deploy_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Check containers for liveness probes
                        template_spec = (
                            deployment_dict.get('spec', {}).get('template', {}).get('spec', {})
                        )
                        containers = template_spec.get('containers', [])

                        has_liveness_probe = True
                        for container in containers:
                            if not container.get('livenessProbe'):
                                has_liveness_probe = False
                                break

                        logger.debug(
                            f'Checking deployment {deploy_namespace}/{name} for liveness probe: {has_liveness_probe}'
                        )

                        if not has_liveness_probe:
                            logger.info(
                                f'Found deployment without liveness probe: {deploy_namespace}/{name}'
                            )
                            workloads_without_liveness.append(
                                f'Deployment: {deploy_namespace}/{name}'
                            )
                    except Exception as deploy_error:
                        logger.error(f'Error processing deployment: {str(deploy_error)}')
            except Exception as e:
                logger.error(f'Error listing deployments: {str(e)}')

            # Check StatefulSets
            logger.info('Checking StatefulSets for liveness probes')
            try:
                statefulsets_response = k8s_api.list_resources(
                    kind='StatefulSet', api_version='apps/v1', **kwargs
                )

                # Log the number of statefulsets found
                statefulset_count = (
                    len(statefulsets_response.items)
                    if hasattr(statefulsets_response, 'items')
                    else 0
                )
                logger.info(f'Retrieved {statefulset_count} statefulsets')

                # Process the response
                for statefulset in statefulsets_response.items:
                    try:
                        statefulset_dict = (
                            statefulset.to_dict()
                            if hasattr(statefulset, 'to_dict')
                            else statefulset
                        )

                        # Get statefulset metadata
                        metadata = statefulset_dict.get('metadata', {})
                        ss_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Check containers for liveness probes
                        template_spec = (
                            statefulset_dict.get('spec', {}).get('template', {}).get('spec', {})
                        )
                        containers = template_spec.get('containers', [])

                        has_liveness_probe = True
                        for container in containers:
                            if not container.get('livenessProbe'):
                                has_liveness_probe = False
                                break

                        logger.debug(
                            f'Checking statefulset {ss_namespace}/{name} for liveness probe: {has_liveness_probe}'
                        )

                        if not has_liveness_probe:
                            logger.info(
                                f'Found statefulset without liveness probe: {ss_namespace}/{name}'
                            )
                            workloads_without_liveness.append(
                                f'StatefulSet: {ss_namespace}/{name}'
                            )
                    except Exception as ss_error:
                        logger.error(f'Error processing statefulset: {str(ss_error)}')
            except Exception as e:
                logger.error(f'Error listing statefulsets: {str(e)}')

            # Check DaemonSets
            logger.info('Checking DaemonSets for liveness probes')
            try:
                daemonsets_response = k8s_api.list_resources(
                    kind='DaemonSet', api_version='apps/v1', **kwargs
                )

                # Log the number of daemonsets found
                daemonset_count = (
                    len(daemonsets_response.items) if hasattr(daemonsets_response, 'items') else 0
                )
                logger.info(f'Retrieved {daemonset_count} daemonsets')

                # Process the response
                for daemonset in daemonsets_response.items:
                    try:
                        daemonset_dict = (
                            daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                        )

                        # Get daemonset metadata
                        metadata = daemonset_dict.get('metadata', {})
                        ds_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Check containers for liveness probes
                        template_spec = (
                            daemonset_dict.get('spec', {}).get('template', {}).get('spec', {})
                        )
                        containers = template_spec.get('containers', [])

                        has_liveness_probe = True
                        for container in containers:
                            if not container.get('livenessProbe'):
                                has_liveness_probe = False
                                break

                        logger.debug(
                            f'Checking daemonset {ds_namespace}/{name} for liveness probe: {has_liveness_probe}'
                        )

                        if not has_liveness_probe:
                            logger.info(
                                f'Found daemonset without liveness probe: {ds_namespace}/{name}'
                            )
                            workloads_without_liveness.append(f'DaemonSet: {ds_namespace}/{name}')
                    except Exception as ds_error:
                        logger.error(f'Error processing daemonset: {str(ds_error)}')
            except Exception as e:
                logger.error(f'Error listing daemonsets: {str(e)}')

            is_compliant = len(workloads_without_liveness) == 0

            # Prepare a more detailed message that includes namespace information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            detailed_message = f'Found {len(workloads_without_liveness)} workloads without liveness probes {scope_info}'
            logger.info(detailed_message)

            remediation = """Add liveness probes to your workloads to detect and restart unhealthy containers:

```yaml
apiVersion: apps/v1
kind: Deployment  # or StatefulSet, DaemonSet
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: my-container
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```"""

            return {
                'check_id': 'A4',
                'check_name': 'Use liveness probes',
                'compliant': is_compliant,
                'impacted_resources': workloads_without_liveness,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking liveness probes: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = (
                f'API error while checking deployments for liveness probes {scope_info}: {str(e)}'
            )

            return {
                'check_id': 'A4',
                'check_name': 'Use liveness probes',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_readiness_probe(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A5: Deployments without readiness probes."""
        workloads_without_readiness = []
        try:
            logger.info(
                f'Starting readiness probe check, namespace: {namespace if namespace else "all"}'
            )

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking workloads in namespace: {namespace}')
            else:
                logger.info('Checking workloads across all namespaces')

            # Check Deployments
            logger.info('Checking Deployments for readiness probes')
            try:
                deployments_response = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', **kwargs
                )

                # Log the number of deployments found
                deployment_count = (
                    len(deployments_response.items)
                    if hasattr(deployments_response, 'items')
                    else 0
                )
                logger.info(f'Retrieved {deployment_count} deployments')

                # Process the response
                for deployment in deployments_response.items:
                    try:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )

                        # Get deployment metadata
                        metadata = deployment_dict.get('metadata', {})
                        deploy_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Check containers for readiness probes
                        template_spec = (
                            deployment_dict.get('spec', {}).get('template', {}).get('spec', {})
                        )
                        containers = template_spec.get('containers', [])

                        has_readiness_probe = True
                        for container in containers:
                            if not container.get('readinessProbe'):
                                has_readiness_probe = False
                                break

                        logger.debug(
                            f'Checking deployment {deploy_namespace}/{name} for readiness probe: {has_readiness_probe}'
                        )

                        if not has_readiness_probe:
                            logger.info(
                                f'Found deployment without readiness probe: {deploy_namespace}/{name}'
                            )
                            workloads_without_readiness.append(
                                f'Deployment: {deploy_namespace}/{name}'
                            )
                    except Exception as deploy_error:
                        logger.error(f'Error processing deployment: {str(deploy_error)}')
            except Exception as e:
                logger.error(f'Error listing deployments: {str(e)}')

            # Check StatefulSets
            logger.info('Checking StatefulSets for readiness probes')
            try:
                statefulsets_response = k8s_api.list_resources(
                    kind='StatefulSet', api_version='apps/v1', **kwargs
                )

                # Log the number of statefulsets found
                statefulset_count = (
                    len(statefulsets_response.items)
                    if hasattr(statefulsets_response, 'items')
                    else 0
                )
                logger.info(f'Retrieved {statefulset_count} statefulsets')

                # Process the response
                for statefulset in statefulsets_response.items:
                    try:
                        statefulset_dict = (
                            statefulset.to_dict()
                            if hasattr(statefulset, 'to_dict')
                            else statefulset
                        )

                        # Get statefulset metadata
                        metadata = statefulset_dict.get('metadata', {})
                        ss_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Check containers for readiness probes
                        template_spec = (
                            statefulset_dict.get('spec', {}).get('template', {}).get('spec', {})
                        )
                        containers = template_spec.get('containers', [])

                        has_readiness_probe = True
                        for container in containers:
                            if not container.get('readinessProbe'):
                                has_readiness_probe = False
                                break

                        logger.debug(
                            f'Checking statefulset {ss_namespace}/{name} for readiness probe: {has_readiness_probe}'
                        )

                        if not has_readiness_probe:
                            logger.info(
                                f'Found statefulset without readiness probe: {ss_namespace}/{name}'
                            )
                            workloads_without_readiness.append(
                                f'StatefulSet: {ss_namespace}/{name}'
                            )
                    except Exception as ss_error:
                        logger.error(f'Error processing statefulset: {str(ss_error)}')
            except Exception as e:
                logger.error(f'Error listing statefulsets: {str(e)}')

            # Check DaemonSets
            logger.info('Checking DaemonSets for readiness probes')
            try:
                daemonsets_response = k8s_api.list_resources(
                    kind='DaemonSet', api_version='apps/v1', **kwargs
                )

                # Log the number of daemonsets found
                daemonset_count = (
                    len(daemonsets_response.items) if hasattr(daemonsets_response, 'items') else 0
                )
                logger.info(f'Retrieved {daemonset_count} daemonsets')

                # Process the response
                for daemonset in daemonsets_response.items:
                    try:
                        daemonset_dict = (
                            daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                        )

                        # Get daemonset metadata
                        metadata = daemonset_dict.get('metadata', {})
                        ds_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Check containers for readiness probes
                        template_spec = (
                            daemonset_dict.get('spec', {}).get('template', {}).get('spec', {})
                        )
                        containers = template_spec.get('containers', [])

                        has_readiness_probe = True
                        for container in containers:
                            if not container.get('readinessProbe'):
                                has_readiness_probe = False
                                break

                        logger.debug(
                            f'Checking daemonset {ds_namespace}/{name} for readiness probe: {has_readiness_probe}'
                        )

                        if not has_readiness_probe:
                            logger.info(
                                f'Found daemonset without readiness probe: {ds_namespace}/{name}'
                            )
                            workloads_without_readiness.append(f'DaemonSet: {ds_namespace}/{name}')
                    except Exception as ds_error:
                        logger.error(f'Error processing daemonset: {str(ds_error)}')
            except Exception as e:
                logger.error(f'Error listing daemonsets: {str(e)}')

            is_compliant = len(workloads_without_readiness) == 0

            # Prepare a more detailed message that includes namespace information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            detailed_message = f'Found {len(workloads_without_readiness)} workloads without readiness probes {scope_info}'
            logger.info(detailed_message)

            remediation = """Add readiness probes to your workloads to prevent traffic to pods that are not ready:

```yaml
apiVersion: apps/v1
kind: Deployment  # or StatefulSet, DaemonSet
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: my-container
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```"""

            # Return all impacted resources
            return {
                'check_id': 'A5',
                'check_name': 'Use readiness probes',
                'compliant': is_compliant,
                'impacted_resources': workloads_without_readiness,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking readiness probes: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = (
                f'API error while checking deployments for readiness probes {scope_info}: {str(e)}'
            )

            return {
                'check_id': 'A5',
                'check_name': 'Use readiness probes',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_pod_disruption_budget(
        self, k8s_api, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check A6: Workloads without Pod Disruption Budgets."""
        workloads_without_pdb = []
        pdbs_found = False
        try:
            logger.info(f'Starting PDB check, namespace: {namespace if namespace else "all"}')

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking resources in namespace: {namespace}')
            else:
                logger.info('Checking resources across all namespaces')

            # Get all deployments with multiple replicas
            logger.info('Calling list_resources to get deployments')
            deployments_response = k8s_api.list_resources(
                kind='Deployment', api_version='apps/v1', **kwargs
            )

            critical_workloads = []

            # Process deployments
            for deployment in deployments_response.items:
                try:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )

                    # Get deployment metadata
                    metadata = deployment_dict.get('metadata', {})
                    deploy_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Check replicas
                    spec = deployment_dict.get('spec', {})
                    replicas = spec.get('replicas', 0)

                    # Only consider deployments with multiple replicas as critical
                    if replicas > 1:
                        logger.debug(f'Found critical deployment: {deploy_namespace}/{name}')
                        critical_workloads.append(
                            {
                                'name': name,
                                'namespace': deploy_namespace,
                                'kind': 'Deployment',
                                'selector': spec.get('selector', {}).get('matchLabels', {}),
                            }
                        )
                except Exception as deploy_error:
                    logger.error(f'Error processing deployment: {str(deploy_error)}')

            # Get all statefulsets (considered critical by default)
            logger.info('Calling list_resources to get statefulsets')
            statefulsets_response = k8s_api.list_resources(
                kind='StatefulSet', api_version='apps/v1', **kwargs
            )

            # Process statefulsets
            for statefulset in statefulsets_response.items:
                try:
                    statefulset_dict = (
                        statefulset.to_dict() if hasattr(statefulset, 'to_dict') else statefulset
                    )

                    # Get statefulset metadata
                    metadata = statefulset_dict.get('metadata', {})
                    ss_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    spec = statefulset_dict.get('spec', {})

                    logger.debug(f'Found critical statefulset: {ss_namespace}/{name}')
                    critical_workloads.append(
                        {
                            'name': name,
                            'namespace': ss_namespace,
                            'kind': 'StatefulSet',
                            'selector': spec.get('selector', {}).get('matchLabels', {}),
                        }
                    )
                except Exception as ss_error:
                    logger.error(f'Error processing statefulset: {str(ss_error)}')

            # Get all PDBs
            logger.info('Calling list_resources to get PDBs')
            try:
                pdbs_response = k8s_api.list_resources(
                    kind='PodDisruptionBudget', api_version='policy/v1', **kwargs
                )
                pdbs_found = True
            except Exception:
                # Try beta API if v1 fails
                try:
                    pdbs_response = k8s_api.list_resources(
                        kind='PodDisruptionBudget', api_version='policy/v1beta1', **kwargs
                    )
                    pdbs_found = True
                except Exception as pdb_error:
                    logger.error(f'Error listing PDBs: {str(pdb_error)}')
                    pdbs_response = None

            # Process PDBs if found
            pdb_targets = set()
            if pdbs_found and pdbs_response:
                for pdb in pdbs_response.items:
                    try:
                        pdb_dict = pdb.to_dict() if hasattr(pdb, 'to_dict') else pdb

                        # Get PDB metadata
                        metadata = pdb_dict.get('metadata', {})
                        pdb_namespace = metadata.get('namespace', 'default')

                        # Get selector
                        spec = pdb_dict.get('spec', {})
                        selector = spec.get('selector', {}).get('matchLabels', {})

                        if selector:
                            # json already imported at the top
                            selector_str = json.dumps(selector, sort_keys=True)
                            pdb_targets.add(f'{pdb_namespace}/{selector_str}')
                    except Exception as pdb_error:
                        logger.error(f'Error processing PDB: {str(pdb_error)}')

            # Find critical workloads without PDBs
            for workload in critical_workloads:
                try:
                    # json already imported at the top
                    selector_str = json.dumps(workload['selector'], sort_keys=True)
                    if f'{workload["namespace"]}/{selector_str}' not in pdb_targets:
                        workloads_without_pdb.append(
                            f'{workload["namespace"]}/{workload["name"]} ({workload["kind"]})'
                        )
                except Exception as check_error:
                    logger.error(f'Error checking workload against PDBs: {str(check_error)}')

            # Determine compliance
            is_compliant = (
                pdbs_found and len(workloads_without_pdb) == 0 and len(critical_workloads) > 0
            )

            # Prepare a more detailed message that includes namespace information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'

            details = []
            if pdbs_found:
                details.append(f'PDBs are configured {scope_info}')
            else:
                details.append(f'No PDBs found {scope_info}')

            if workloads_without_pdb:
                details.append(
                    f'Found {len(workloads_without_pdb)} critical workloads without PDBs'
                )
            elif len(critical_workloads) > 0:
                details.append('All critical workloads are protected by PDBs')
            else:
                details.append('No critical workloads found')

            detailed_message = '; '.join(details)
            logger.info(detailed_message)

            remediation = """Add Pod Disruption Budgets (PDBs) to protect your critical workloads during voluntary disruptions:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 1  # or use maxUnavailable: 1
  selector:
    matchLabels:
      app: my-app  # Must match your deployment/statefulset selector
```"""

            return {
                'check_id': 'A6',
                'check_name': 'Use Pod Disruption Budgets',
                'compliant': is_compliant,
                'impacted_resources': workloads_without_pdb,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking Pod Disruption Budgets: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = (
                f'API error while checking Pod Disruption Budgets {scope_info}: {str(e)}'
            )

            return {
                'check_id': 'A6',
                'check_name': 'Use Pod Disruption Budgets',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_metrics_server(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A7: Kubernetes Metrics Server."""
        try:
            logger.info('Starting metrics server check')
            metrics_server_exists = False

            # Check if metrics-server deployment exists in kube-system namespace
            try:
                deployments_response = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', namespace='kube-system'
                )

                for deployment in deployments_response.items:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )
                    metadata = deployment_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if 'metrics-server' in name:
                        logger.info(f'Found metrics-server deployment: {name}')
                        metrics_server_exists = True
                        break
            except Exception as deploy_error:
                logger.error(f'Error checking for metrics-server deployment: {str(deploy_error)}')

            # If not found in kube-system, check all namespaces if no specific namespace was provided
            if not metrics_server_exists and namespace is None:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'metrics-server' in name:
                            logger.info(
                                f'Found metrics-server deployment: {metadata.get("namespace", "unknown")}/{name}'
                            )
                            metrics_server_exists = True
                            break
                except Exception as deploy_error:
                    logger.error(
                        f'Error checking for metrics-server deployment in all namespaces: {str(deploy_error)}'
                    )

            # Alternative check: try to access metrics API
            if not metrics_server_exists:
                try:
                    # Use the K8sApis client to call the metrics API
                    api_client = k8s_api.api_client
                    api_response = api_client.call_api(
                        '/apis/metrics.k8s.io/v1beta1/nodes',
                        'GET',
                        auth_settings=['BearerToken'],
                        response_type='object',
                    )

                    if api_response and api_response[0]:
                        logger.info('Metrics API is accessible')
                        metrics_server_exists = True
                except Exception as api_error:
                    logger.info(f'Metrics API is not accessible: {str(api_error)}')

            is_compliant = metrics_server_exists

            detailed_message = (
                'Metrics Server is running'
                if metrics_server_exists
                else 'Metrics Server is not installed'
            )
            logger.info(detailed_message)

            remediation = """
            Install the Kubernetes Metrics Server:

            ```bash
            kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
            ```

            For EKS, you can also use:

            ```bash
            kubectl apply -f https://github.com/aws/eks-charts/raw/master/stable/metrics-server/values.yaml
            ```

            Or with Helm:

            ```bash
            helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
            helm upgrade --install metrics-server metrics-server/metrics-server
            ```
            """

            return {
                'check_id': 'A7',
                'check_name': 'Run Kubernetes Metrics Server',
                'compliant': is_compliant,
                'impacted_resources': [],
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking for metrics server: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'API error while checking for metrics server: {str(e)}'

            return {
                'check_id': 'A7',
                'check_name': 'Run Kubernetes Metrics Server',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_horizontal_pod_autoscaler(
        self, k8s_api, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check A8: Horizontal Pod Autoscaler (HPA) - identifies workloads without HPAs."""
        workloads_without_hpa = []
        try:
            logger.info(f'Starting HPA check, namespace: {namespace if namespace else "all"}')

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking workloads in namespace: {namespace}')
            else:
                logger.info('Checking workloads across all namespaces')

            # Step 1: Collect target workloads (Deployments and StatefulSets with replicas > 1)
            target_workloads = []

            # Get Deployments
            logger.info('Collecting Deployments for HPA analysis')
            try:
                deployments_response = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', **kwargs
                )

                for deployment in deployments_response.items:
                    try:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        deploy_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Skip system namespaces
                        if deploy_namespace in ['kube-system', 'kube-public', 'kube-node-lease']:
                            continue

                        # Check replicas - only consider workloads with multiple replicas
                        spec = deployment_dict.get('spec', {})
                        replicas = spec.get('replicas', 0)

                        if replicas > 1:
                            target_workloads.append(
                                {'name': name, 'namespace': deploy_namespace, 'kind': 'Deployment'}
                            )
                            logger.debug(
                                f'Found target deployment: {deploy_namespace}/{name} ({replicas} replicas)'
                            )
                    except Exception as deploy_error:
                        logger.error(f'Error processing deployment: {str(deploy_error)}')
            except Exception as e:
                logger.error(f'Error listing deployments: {str(e)}')

            # Get StatefulSets
            logger.info('Collecting StatefulSets for HPA analysis')
            try:
                statefulsets_response = k8s_api.list_resources(
                    kind='StatefulSet', api_version='apps/v1', **kwargs
                )

                for statefulset in statefulsets_response.items:
                    try:
                        statefulset_dict = (
                            statefulset.to_dict()
                            if hasattr(statefulset, 'to_dict')
                            else statefulset
                        )
                        metadata = statefulset_dict.get('metadata', {})
                        ss_namespace = metadata.get('namespace', 'default')
                        name = metadata.get('name', 'unknown')

                        # Skip system namespaces
                        if ss_namespace in ['kube-system', 'kube-public', 'kube-node-lease']:
                            continue

                        # Check replicas - only consider workloads with multiple replicas
                        spec = statefulset_dict.get('spec', {})
                        replicas = spec.get('replicas', 0)

                        if replicas > 1:
                            target_workloads.append(
                                {'name': name, 'namespace': ss_namespace, 'kind': 'StatefulSet'}
                            )
                            logger.debug(
                                f'Found target statefulset: {ss_namespace}/{name} ({replicas} replicas)'
                            )
                    except Exception as ss_error:
                        logger.error(f'Error processing statefulset: {str(ss_error)}')
            except Exception as e:
                logger.error(f'Error listing statefulsets: {str(e)}')

            # Step 2: Collect existing HPA targets
            hpa_protected_workloads = set()

            # Try v2 API first
            logger.info('Collecting existing HPAs (v2 API)')
            try:
                hpas_response = k8s_api.list_resources(
                    kind='HorizontalPodAutoscaler', api_version='autoscaling/v2', **kwargs
                )

                hpa_count = len(hpas_response.items) if hasattr(hpas_response, 'items') else 0
                logger.info(f'Found {hpa_count} HPAs with v2 API')

                for hpa in hpas_response.items:
                    try:
                        hpa_dict = hpa.to_dict() if hasattr(hpa, 'to_dict') else hpa
                        metadata = hpa_dict.get('metadata', {})
                        hpa_namespace = metadata.get('namespace', 'default')

                        # Get scale target reference
                        spec = hpa_dict.get('spec', {})
                        scale_target_ref = spec.get('scaleTargetRef', {})
                        target_kind = scale_target_ref.get('kind', '')
                        target_name = scale_target_ref.get('name', '')

                        if target_kind in ['Deployment', 'StatefulSet'] and target_name:
                            hpa_protected_workloads.add(f'{hpa_namespace}/{target_name}')
                            logger.debug(
                                f'Found HPA protecting: {hpa_namespace}/{target_name} ({target_kind})'
                            )
                    except Exception as hpa_error:
                        logger.error(f'Error processing HPA: {str(hpa_error)}')
            except Exception as v2_error:
                logger.info(f'Error accessing autoscaling/v2 API: {str(v2_error)}')

                # Try v1 API if v2 fails
                logger.info('Trying v1 API for HPAs')
                try:
                    hpas_response = k8s_api.list_resources(
                        kind='HorizontalPodAutoscaler', api_version='autoscaling/v1', **kwargs
                    )

                    hpa_count = len(hpas_response.items) if hasattr(hpas_response, 'items') else 0
                    logger.info(f'Found {hpa_count} HPAs with v1 API')

                    for hpa in hpas_response.items:
                        try:
                            hpa_dict = hpa.to_dict() if hasattr(hpa, 'to_dict') else hpa
                            metadata = hpa_dict.get('metadata', {})
                            hpa_namespace = metadata.get('namespace', 'default')

                            # Get scale target reference
                            spec = hpa_dict.get('spec', {})
                            scale_target_ref = spec.get('scaleTargetRef', {})
                            target_kind = scale_target_ref.get('kind', '')
                            target_name = scale_target_ref.get('name', '')

                            if target_kind in ['Deployment', 'StatefulSet'] and target_name:
                                hpa_protected_workloads.add(f'{hpa_namespace}/{target_name}')
                                logger.debug(
                                    f'Found HPA protecting: {hpa_namespace}/{target_name} ({target_kind})'
                                )
                        except Exception as hpa_error:
                            logger.error(f'Error processing HPA: {str(hpa_error)}')
                except Exception as v1_error:
                    logger.info(f'Error accessing autoscaling/v1 API: {str(v1_error)}')

            # Step 3: Find workloads without HPAs
            for workload in target_workloads:
                workload_key = f'{workload["namespace"]}/{workload["name"]}'
                if workload_key not in hpa_protected_workloads:
                    workloads_without_hpa.append(
                        f'{workload["namespace"]}/{workload["name"]} ({workload["kind"]})'
                    )
                    logger.debug(f'Found workload without HPA: {workload_key}')

            # Step 4: Determine compliance and prepare response
            is_compliant = len(workloads_without_hpa) == 0 and len(target_workloads) > 0

            # Prepare detailed message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'

            if len(target_workloads) == 0:
                detailed_message = (
                    f'No multi-replica workloads found {scope_info} that require HPAs'
                )
            elif len(workloads_without_hpa) == 0:
                detailed_message = (
                    f'All {len(target_workloads)} multi-replica workloads have HPAs {scope_info}'
                )
            else:
                detailed_message = f'Found {len(workloads_without_hpa)} workloads without HPAs out of {len(target_workloads)} multi-replica workloads {scope_info}'

            logger.info(detailed_message)

            remediation = """Configure Horizontal Pod Autoscalers (HPAs) for your multi-replica workloads:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: my-namespace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment  # or StatefulSet
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Or using kubectl:
```bash
kubectl autoscale deployment my-app --cpu-percent=80 --min=2 --max=10 -n my-namespace
kubectl autoscale statefulset my-statefulset --cpu-percent=80 --min=2 --max=10 -n my-namespace
```"""

            return {
                'check_id': 'A8',
                'check_name': 'Use Horizontal Pod Autoscaler',
                'compliant': is_compliant,
                'impacted_resources': workloads_without_hpa,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking for HPAs: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = f'API error while checking workloads for HPAs {scope_info}: {str(e)}'

            return {
                'check_id': 'A8',
                'check_name': 'Use Horizontal Pod Autoscaler',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_custom_metrics(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A9: Custom metrics scaling."""
        try:
            logger.info('Starting custom metrics check')

            custom_metrics_api_exists = False
            external_metrics_api_exists = False
            prometheus_adapter_exists = False
            keda_exists = False
            custom_hpas = []

            # Check if custom metrics API is available
            try:
                api_client = k8s_api.api_client
                api_response = api_client.call_api(
                    '/apis/custom.metrics.k8s.io/v1beta1',
                    'GET',
                    auth_settings=['BearerToken'],
                    response_type='object',
                )

                if api_response and api_response[0]:
                    logger.info('Custom Metrics API is available')
                    custom_metrics_api_exists = True
            except Exception as api_error:
                logger.info(f'Custom Metrics API is not available: {str(api_error)}')

            # Check if external metrics API is available
            try:
                api_client = k8s_api.api_client
                api_response = api_client.call_api(
                    '/apis/external.metrics.k8s.io/v1beta1',
                    'GET',
                    auth_settings=['BearerToken'],
                    response_type='object',
                )

                if api_response and api_response[0]:
                    logger.info('External Metrics API is available')
                    external_metrics_api_exists = True
            except Exception as api_error:
                logger.info(f'External Metrics API is not available: {str(api_error)}')

            # Check for Prometheus Adapter deployment
            try:
                # Check in monitoring namespace first
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1', namespace='monitoring'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'prometheus-adapter' in name:
                            logger.info(f'Found Prometheus Adapter deployment: {name}')
                            prometheus_adapter_exists = True
                            break
                except Exception:
                    pass

                # If not found, check all namespaces
                if not prometheus_adapter_exists:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'prometheus-adapter' in name:
                            logger.info(
                                f'Found Prometheus Adapter deployment: {metadata.get("namespace", "unknown")}/{name}'
                            )
                            prometheus_adapter_exists = True
                            break
            except Exception as deploy_error:
                logger.error(f'Error checking for Prometheus Adapter: {str(deploy_error)}')

            # Check for KEDA deployment
            try:
                # Check in keda namespace first
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1', namespace='keda'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'keda' in name:
                            logger.info(f'Found KEDA deployment: {name}')
                            keda_exists = True
                            break
                except Exception:
                    pass

                # If not found, check all namespaces
                if not keda_exists:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'keda' in name:
                            logger.info(
                                f'Found KEDA deployment: {metadata.get("namespace", "unknown")}/{name}'
                            )
                            keda_exists = True
                            break
            except Exception as deploy_error:
                logger.error(f'Error checking for KEDA: {str(deploy_error)}')

            # Check for HPAs using custom or external metrics
            try:
                # Prepare kwargs for filtering
                kwargs = {}
                if namespace:
                    kwargs['namespace'] = namespace

                hpas_response = k8s_api.list_resources(
                    kind='HorizontalPodAutoscaler', api_version='autoscaling/v2', **kwargs
                )

                for hpa in hpas_response.items:
                    hpa_dict = hpa.to_dict() if hasattr(hpa, 'to_dict') else hpa
                    metadata = hpa_dict.get('metadata', {})
                    hpa_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Check for custom or external metrics
                    spec = hpa_dict.get('spec', {})
                    metrics = spec.get('metrics', [])

                    for metric in metrics:
                        metric_type = metric.get('type', '')
                        if metric_type in ['Object', 'Pods', 'External']:
                            logger.info(
                                f'Found HPA with custom/external metrics: {hpa_namespace}/{name}'
                            )
                            custom_hpas.append(f'{hpa_namespace}/{name}')
                            break
            except Exception as hpa_error:
                logger.info(f'Error checking for HPAs with custom metrics: {str(hpa_error)}')

            # Determine compliance based on findings
            is_compliant = (
                custom_metrics_api_exists
                or external_metrics_api_exists
                or prometheus_adapter_exists
                or keda_exists
                or len(custom_hpas) > 0
            )

            # Prepare detailed message
            details = []
            if custom_metrics_api_exists:
                details.append('Custom Metrics API is available')
            if external_metrics_api_exists:
                details.append('External Metrics API is available')
            if prometheus_adapter_exists:
                details.append('Prometheus Adapter is deployed')
            if keda_exists:
                details.append('KEDA is deployed')
            if custom_hpas:
                details.append(f'Found {len(custom_hpas)} HPAs using custom or external metrics')
            if not details:
                details.append('No custom or external metrics scaling capabilities found')

            detailed_message = '; '.join(details)
            logger.info(detailed_message)

            remediation = """
            Set up custom metrics scaling with one of these options:

            1. Install Prometheus and Prometheus Adapter:
            ```bash
            helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
            helm install prometheus prometheus-community/prometheus
            helm install prometheus-adapter prometheus-community/prometheus-adapter
            ```

            2. Install KEDA for event-driven autoscaling:
            ```bash
            helm repo add kedacore https://kedacore.github.io/charts
            helm install keda kedacore/keda --namespace keda --create-namespace
            ```

            3. Configure an HPA with custom metrics:
            ```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: custom_metric
      target:
        type: AverageValue
        averageValue: 100
            ```
            """

            return {
                'check_id': 'A9',
                'check_name': 'Use custom metrics scaling',
                'compliant': is_compliant,
                'impacted_resources': custom_hpas,
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking for custom metrics scaling: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'API error while checking for custom metrics scaling: {str(e)}'

            return {
                'check_id': 'A9',
                'check_name': 'Use custom metrics scaling',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_vertical_pod_autoscaler(
        self, k8s_api, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check A10: Vertical Pod Autoscaler (VPA)."""
        try:
            logger.info(f'Starting VPA check, namespace: {namespace if namespace else "all"}')

            vpa_components = []
            vpa_resources = []
            goldilocks_exists = False
            deployments_without_vpa = []
            all_deployments = []

            # Check for VPA components (admission controller, recommender, updater)
            try:
                # Check in kube-system namespace first
                deployments_response = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', namespace='kube-system'
                )

                for deployment in deployments_response.items:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )
                    metadata = deployment_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if 'vpa-' in name:
                        logger.info(f'Found VPA component: {name}')
                        vpa_components.append(f'kube-system/{name}')
            except Exception:
                pass

            # If not found in kube-system, check all namespaces
            if not vpa_components:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'vpa-' in name:
                            logger.info(f'Found VPA component: {deploy_namespace}/{name}')
                            vpa_components.append(f'{deploy_namespace}/{name}')
                except Exception:
                    pass

            # Check if VPA CRD is installed
            vpa_crd_exists = False
            vpa_target_refs = []

            try:
                # Try v1 API first
                api_client = k8s_api.api_client
                api_response = api_client.call_api(
                    '/apis/autoscaling.k8s.io/v1/verticalpodautoscalers',
                    'GET',
                    auth_settings=['BearerToken'],
                    response_type='object',
                )

                if api_response and api_response[0]:
                    logger.info('VPA CRD is installed (v1)')
                    vpa_crd_exists = True

                    # Process VPA resources
                    for vpa in api_response[0].get('items', []):
                        metadata = vpa.get('metadata', {})
                        vpa_namespace = metadata.get('namespace', 'unknown')
                        name = metadata.get('name', 'unknown')
                        vpa_resources.append(f'{vpa_namespace}/{name}')

                        # Extract target reference
                        target_ref = vpa.get('spec', {}).get('targetRef', {})
                        if target_ref and target_ref.get('kind') == 'Deployment':
                            target_name = f'{vpa_namespace}/{target_ref.get("name", "unknown")}'
                            vpa_target_refs.append(target_name)
            except Exception:
                # Try beta API if v1 fails
                try:
                    api_client = k8s_api.api_client
                    api_response = api_client.call_api(
                        '/apis/autoscaling.k8s.io/v1beta2/verticalpodautoscalers',
                        'GET',
                        auth_settings=['BearerToken'],
                        response_type='object',
                    )

                    if api_response and api_response[0]:
                        logger.info('VPA CRD is installed (v1beta2)')
                        vpa_crd_exists = True

                        # Process VPA resources
                        for vpa in api_response[0].get('items', []):
                            metadata = vpa.get('metadata', {})
                            vpa_namespace = metadata.get('namespace', 'unknown')
                            name = metadata.get('name', 'unknown')
                            vpa_resources.append(f'{vpa_namespace}/{name}')

                            # Extract target reference
                            target_ref = vpa.get('spec', {}).get('targetRef', {})
                            if target_ref and target_ref.get('kind') == 'Deployment':
                                target_name = (
                                    f'{vpa_namespace}/{target_ref.get("name", "unknown")}'
                                )
                                vpa_target_refs.append(target_name)
                except Exception:
                    logger.info('VPA CRD is not installed')

            # Check for Goldilocks (VPA UI)
            try:
                # Check in goldilocks namespace first
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1', namespace='goldilocks'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'goldilocks' in name:
                            logger.info(f'Found Goldilocks: {name}')
                            goldilocks_exists = True
                            break
                except Exception:
                    pass

                # If not found, check all namespaces
                if not goldilocks_exists:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'goldilocks' in name:
                            logger.info(
                                f'Found Goldilocks: {metadata.get("namespace", "unknown")}/{name}'
                            )
                            goldilocks_exists = True
                            break
            except Exception:
                pass

            # Get all deployments
            try:
                # Prepare kwargs for filtering
                kwargs = {}
                if namespace:
                    kwargs['namespace'] = namespace

                deployments_response = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', **kwargs
                )

                for deployment in deployments_response.items:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )
                    metadata = deployment_dict.get('metadata', {})
                    deploy_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Skip system deployments
                    if deploy_namespace == 'kube-system' and (
                        'vpa-' in name.lower() or 'metrics-server' in name.lower()
                    ):
                        continue

                    all_deployments.append(f'{deploy_namespace}/{name}')
            except Exception as deploy_error:
                logger.error(f'Error listing deployments: {str(deploy_error)}')

            # Find deployments without VPA
            for deployment in all_deployments:
                if deployment not in vpa_target_refs:
                    deployments_without_vpa.append(deployment)

            # Determine VPA installation and usage status
            vpa_fully_installed = len(vpa_components) > 0 and vpa_crd_exists
            vpa_in_use = len(vpa_resources) > 0

            # Prepare scope information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'

            # Scenario 1: VPA not properly installed
            if not vpa_fully_installed:
                details = []
                if not vpa_crd_exists:
                    details.append('VPA CRD is not installed')
                if len(vpa_components) == 0:
                    details.append('VPA controller components are not deployed')
                if goldilocks_exists:
                    details.append(
                        'Goldilocks (VPA UI) is installed but VPA infrastructure is missing'
                    )

                detailed_message = f'VPA check {scope_info}: {"; ".join(details) if details else "VPA infrastructure not found"}'
                logger.info(detailed_message)

                remediation = """
Install the Vertical Pod Autoscaler infrastructure:

```bash
# Option 1: Official installation script
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler/
./hack/vpa-up.sh
```

```bash
# Option 2: Helm installation
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install vpa fairwinds-stable/vpa --namespace vpa --create-namespace
```

After installation, create VPA resources for your deployments."""

                return {
                    'check_id': 'A10',
                    'check_name': 'Use Vertical Pod Autoscaler',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': detailed_message,
                    'remediation': remediation,
                }

            # Scenario 2: VPA installed but not used
            elif not vpa_in_use:
                details = []
                if vpa_components:
                    details.append(f'VPA components are running: {", ".join(vpa_components)}')
                if vpa_crd_exists:
                    details.append('VPA CRD is installed')
                if goldilocks_exists:
                    details.append('Goldilocks (VPA UI) is available')
                details.append('No VPA objects configured')
                if len(all_deployments) > 0:
                    details.append(f'{len(all_deployments)} deployments could benefit from VPA')

                detailed_message = f'VPA check {scope_info}: {"; ".join(details)}'
                logger.info(detailed_message)

                # Show deployments that could use VPA
                if len(all_deployments) > 10:
                    impacted_resources = all_deployments[:10] + [
                        f'... and {len(all_deployments) - 10} more deployments'
                    ]
                else:
                    impacted_resources = all_deployments

                remediation = """
VPA infrastructure is ready! Create VPA resources for your deployments:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: my-namespace
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Start with recommendations only
```

Recommended approach:
1. Start with `updateMode: "Off"` to see recommendations
2. Review the recommendations for a few days
3. Change to `updateMode: "Auto"` for automatic resource updates

Consider installing Goldilocks for better VPA visualization:
```bash
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install goldilocks fairwinds-stable/goldilocks --namespace goldilocks --create-namespace
```"""

                return {
                    'check_id': 'A10',
                    'check_name': 'Use Vertical Pod Autoscaler',
                    'compliant': False,
                    'impacted_resources': impacted_resources,
                    'details': detailed_message,
                    'remediation': remediation,
                }

            # Scenario 3: VPA installed and in use
            else:
                is_compliant = len(deployments_without_vpa) == 0 and len(all_deployments) > 0

                details = []
                if vpa_components:
                    details.append(f'VPA components are running: {", ".join(vpa_components)}')
                if vpa_crd_exists:
                    details.append('VPA CRD is installed')
                details.append(f'Found {len(vpa_resources)} VPA resources')
                if goldilocks_exists:
                    details.append('Goldilocks (VPA UI) is available')

                if len(all_deployments) == 0:
                    details.append('No deployments found')
                elif len(deployments_without_vpa) == 0:
                    details.append('All deployments have VPA configured')
                else:
                    details.append(
                        f'{len(deployments_without_vpa)} of {len(all_deployments)} deployments still need VPA configuration'
                    )

                detailed_message = f'VPA check {scope_info}: {"; ".join(details)}'
                logger.info(detailed_message)

                # Show deployments that still need VPA
                if len(deployments_without_vpa) > 10:
                    impacted_resources = deployments_without_vpa[:10] + [
                        f'... and {len(deployments_without_vpa) - 10} more deployments'
                    ]
                else:
                    impacted_resources = deployments_without_vpa

                remediation = """
Add VPA resources for the remaining deployments:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: <deployment-name>-vpa
  namespace: <deployment-namespace>
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: <deployment-name>
  updatePolicy:
    updateMode: "Off"  # Start with recommendations only
```

For each deployment listed in impacted_resources, create a corresponding VPA resource.
Start with `updateMode: "Off"` to review recommendations before enabling automatic updates."""

                return {
                    'check_id': 'A10',
                    'check_name': 'Use Vertical Pod Autoscaler',
                    'compliant': is_compliant,
                    'impacted_resources': impacted_resources,
                    'details': detailed_message,
                    'remediation': remediation if not is_compliant else '',
                }

        except Exception as e:
            logger.error(f'Error checking for VPA: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = f'API error while checking for VPA {scope_info}: {str(e)}'

            return {
                'check_id': 'A10',
                'check_name': 'Use Vertical Pod Autoscaler',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_prestop_hooks(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A11: PreStop hooks for graceful termination.

        Note: DaemonSets are excluded from this check as they typically run system-level
        services that don't require graceful termination and can slow down node maintenance.
        """
        try:
            logger.info(
                f'Starting preStop hooks check, namespace: {namespace if namespace else "all"}'
            )

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking resources in namespace: {namespace}')
            else:
                logger.info('Checking resources across all namespaces')

            deployments_without_prestop = []
            statefulsets_without_prestop = []

            # Check deployments
            try:
                deployments_response = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', **kwargs
                )

                for deployment in deployments_response.items:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )
                    metadata = deployment_dict.get('metadata', {})
                    deploy_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Check containers for preStop hooks
                    template_spec = (
                        deployment_dict.get('spec', {}).get('template', {}).get('spec', {})
                    )
                    containers = template_spec.get('containers', [])

                    has_prestop_hook = True
                    for container in containers:
                        lifecycle = container.get('lifecycle', {})
                        if not lifecycle or not lifecycle.get('preStop'):
                            has_prestop_hook = False
                            break

                    if not has_prestop_hook:
                        logger.info(
                            f'Found deployment without preStop hooks: {deploy_namespace}/{name}'
                        )
                        deployments_without_prestop.append(f'{deploy_namespace}/{name}')
            except Exception as deploy_error:
                logger.error(f'Error checking deployments for preStop hooks: {str(deploy_error)}')

            # Check statefulsets
            try:
                statefulsets_response = k8s_api.list_resources(
                    kind='StatefulSet', api_version='apps/v1', **kwargs
                )

                for statefulset in statefulsets_response.items:
                    statefulset_dict = (
                        statefulset.to_dict() if hasattr(statefulset, 'to_dict') else statefulset
                    )
                    metadata = statefulset_dict.get('metadata', {})
                    ss_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Check containers for preStop hooks
                    template_spec = (
                        statefulset_dict.get('spec', {}).get('template', {}).get('spec', {})
                    )
                    containers = template_spec.get('containers', [])

                    has_prestop_hook = True
                    for container in containers:
                        lifecycle = container.get('lifecycle', {})
                        if not lifecycle or not lifecycle.get('preStop'):
                            has_prestop_hook = False
                            break

                    if not has_prestop_hook:
                        logger.info(
                            f'Found statefulset without preStop hooks: {ss_namespace}/{name}'
                        )
                        statefulsets_without_prestop.append(f'{ss_namespace}/{name}')
            except Exception as ss_error:
                logger.error(f'Error checking statefulsets for preStop hooks: {str(ss_error)}')

            # Note: DaemonSets are intentionally excluded from this check as they typically
            # run system-level services (logging agents, monitoring agents, etc.) that:
            # 1. Don't handle user traffic requiring graceful termination
            # 2. Are designed to be resilient to immediate termination
            # 3. Can slow down node maintenance operations if they have preStop hooks

            # Combine resources without preStop hooks (excluding DaemonSets)
            all_resources_without_prestop = (
                deployments_without_prestop + statefulsets_without_prestop
            )

            is_compliant = len(all_resources_without_prestop) == 0

            # Prepare detailed message
            details = []
            if deployments_without_prestop:
                details.append(
                    f'Found {len(deployments_without_prestop)} deployments without preStop hooks'
                )
            if statefulsets_without_prestop:
                details.append(
                    f'Found {len(statefulsets_without_prestop)} statefulsets without preStop hooks'
                )
            if not details:
                details.append('All application workloads have preStop hooks configured')

            # Add note about DaemonSets being excluded
            details.append("DaemonSets are excluded as they typically don't require preStop hooks")

            # Prepare a more detailed message that includes namespace information
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            detailed_message = f'PreStop hooks check {scope_info}: {"; ".join(details)}'
            logger.info(detailed_message)

            remediation = """
            Add preStop hooks to your application workloads (Deployments and StatefulSets) for graceful termination:

            ```yaml
apiVersion: apps/v1
kind: Deployment  # or StatefulSet
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: my-container
        lifecycle:
          preStop:
            exec:
              command: ["sh", "-c", "sleep 10"]  # Give time for connections to drain
            ```

            For web servers, consider a more sophisticated preStop hook:

            ```yaml
lifecycle:
  preStop:
    exec:
      command: [
        "sh", "-c",
        "sleep 5 && /usr/local/bin/nginx -s quit"
      ]
            ```

            Note: DaemonSets are excluded from this check as they typically run system-level
            services that don't require graceful termination and can slow down node operations.
            """

            return {
                'check_id': 'A11',
                'check_name': 'Use preStop hooks',
                'compliant': is_compliant,
                'impacted_resources': all_resources_without_prestop[
                    :10
                ],  # Limit to 10 to avoid too large response
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking for preStop hooks: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            # Include namespace information in error message
            scope_info = f"in namespace '{namespace}'" if namespace else 'across all namespaces'
            error_message = f'API error while checking for preStop hooks {scope_info}: {str(e)}'

            return {
                'check_id': 'A11',
                'check_name': 'Use preStop hooks',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_service_mesh(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A12: Service mesh usage."""
        try:
            logger.info('Starting service mesh check')

            service_mesh_components = []

            # Check for Istio components
            istio_found = False

            # Check for istio namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['istio-system', 'istio']:
                        logger.info(f'Found Istio namespace: {name}')
                        istio_found = True
                        service_mesh_components.append(f'Namespace: {name}')
                        break
            except Exception as ns_error:
                logger.error(f'Error checking for Istio namespace: {str(ns_error)}')

            # Check for istio CRDs
            if not istio_found:
                try:
                    api_client = k8s_api.api_client
                    api_response = api_client.call_api(
                        '/apis/networking.istio.io/v1alpha3/virtualservices',
                        'GET',
                        auth_settings=['BearerToken'],
                        response_type='object',
                    )

                    if api_response and api_response[0]:
                        logger.info('Istio CRDs found')
                        istio_found = True
                        service_mesh_components.append('Istio CRDs')
                except Exception:
                    pass

            # Check for istio deployments
            if not istio_found:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'istio' in name:
                            logger.info(f'Found Istio deployment: {deploy_namespace}/{name}')
                            istio_found = True
                            service_mesh_components.append(
                                f'Deployment: {deploy_namespace}/{name}'
                            )
                            break
                except Exception:
                    pass

            # Check for Linkerd components
            linkerd_found = False

            # Check for linkerd namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['linkerd', 'linkerd-system']:
                        logger.info(f'Found Linkerd namespace: {name}')
                        linkerd_found = True
                        service_mesh_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for linkerd CRDs
            if not linkerd_found:
                try:
                    api_client = k8s_api.api_client
                    api_response = api_client.call_api(
                        '/apis/linkerd.io/v1alpha2',
                        'GET',
                        auth_settings=['BearerToken'],
                        response_type='object',
                    )

                    if api_response and api_response[0]:
                        logger.info('Linkerd CRDs found')
                        linkerd_found = True
                        service_mesh_components.append('Linkerd CRDs')
                except Exception:
                    pass

            # Check for linkerd deployments
            if not linkerd_found:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'linkerd' in name:
                            logger.info(f'Found Linkerd deployment: {deploy_namespace}/{name}')
                            linkerd_found = True
                            service_mesh_components.append(
                                f'Deployment: {deploy_namespace}/{name}'
                            )
                            break
                except Exception:
                    pass

            # Check for Consul components
            consul_found = False

            # Check for consul namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['consul', 'consul-system']:
                        logger.info(f'Found Consul namespace: {name}')
                        consul_found = True
                        service_mesh_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for consul CRDs
            if not consul_found:
                try:
                    api_client = k8s_api.api_client
                    api_response = api_client.call_api(
                        '/apis/consul.hashicorp.com/v1alpha1',
                        'GET',
                        auth_settings=['BearerToken'],
                        response_type='object',
                    )

                    if api_response and api_response[0]:
                        logger.info('Consul CRDs found')
                        consul_found = True
                        service_mesh_components.append('Consul CRDs')
                except Exception:
                    pass

            # Check for consul deployments
            if not consul_found:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'consul' in name:
                            logger.info(f'Found Consul deployment: {deploy_namespace}/{name}')
                            consul_found = True
                            service_mesh_components.append(
                                f'Deployment: {deploy_namespace}/{name}'
                            )
                            break
                except Exception:
                    pass

            # Check for sidecars in application pods
            has_sidecars = False

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace

            try:
                pods_response = k8s_api.list_resources(kind='Pod', api_version='v1', **kwargs)

                for pod in pods_response.items:
                    pod_dict = pod.to_dict() if hasattr(pod, 'to_dict') else pod
                    metadata = pod_dict.get('metadata', {})
                    pod_namespace = metadata.get('namespace', 'default')
                    name = metadata.get('name', 'unknown')

                    # Skip system namespaces
                    if pod_namespace in ['kube-system', 'istio-system', 'linkerd', 'consul']:
                        continue

                    # Check for sidecar containers
                    spec = pod_dict.get('spec', {})
                    containers = spec.get('containers', [])

                    if len(containers) > 1:
                        for container in containers:
                            container_name = container.get('name', '').lower()
                            if (
                                container_name
                                in ['istio-proxy', 'linkerd-proxy', 'consul-proxy', 'envoy']
                                or 'proxy' in container_name
                                or 'sidecar' in container_name
                            ):
                                logger.info(
                                    f'Found sidecar container: {container_name} in {pod_namespace}/{name}'
                                )
                                has_sidecars = True
                                service_mesh_components.append(
                                    f'Sidecar: {container_name} in {pod_namespace}/{name}'
                                )
                                break

                    if has_sidecars:
                        break
            except Exception as pod_error:
                logger.error(f'Error checking for sidecars: {str(pod_error)}')

            # Determine if a service mesh is in use
            service_mesh_in_use = istio_found or linkerd_found or consul_found or has_sidecars

            # Prepare detailed message
            details = []
            if service_mesh_in_use:
                if istio_found:
                    details.append('Istio service mesh detected')
                if linkerd_found:
                    details.append('Linkerd service mesh detected')
                if consul_found:
                    details.append('Consul service mesh detected')
                if has_sidecars and not (istio_found or linkerd_found or consul_found):
                    details.append('Service mesh proxies detected in application pods')
            else:
                details.append('No service mesh detected in the cluster')

            detailed_message = '; '.join(details)
            logger.info(detailed_message)

            remediation = """
            Install a service mesh to improve application resilience and observability:

            1. Istio:
            ```bash
            curl -L https://istio.io/downloadIstio | sh -
            cd istio-*
            ./bin/istioctl install --set profile=default
            ```

            2. Linkerd:
            ```bash
            curl -sL https://run.linkerd.io/install | sh
            export PATH=$PATH:$HOME/.linkerd2/bin
            linkerd install | kubectl apply -f -
            ```
            """

            return {
                'check_id': 'A12',
                'check_name': 'Use a Service Mesh',
                'compliant': service_mesh_in_use,
                'impacted_resources': service_mesh_components,
                'details': detailed_message,
                'remediation': remediation if not service_mesh_in_use else '',
            }

        except Exception as e:
            logger.error(f'Error checking for service mesh: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'API error while checking for service mesh: {str(e)}'

            return {
                'check_id': 'A12',
                'check_name': 'Use a Service Mesh',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_monitoring(self, k8s_api, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Check A13: Application monitoring."""
        try:
            logger.info('Starting monitoring check')

            monitoring_components = []

            # Check for Prometheus components
            prometheus_found = False

            # Check for prometheus namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['prometheus', 'monitoring']:
                        logger.info(f'Found Prometheus namespace: {name}')
                        prometheus_found = True
                        monitoring_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for prometheus operator CRDs
            if not prometheus_found:
                try:
                    api_client = k8s_api.api_client
                    api_response = api_client.call_api(
                        '/apis/monitoring.coreos.com/v1',
                        'GET',
                        auth_settings=['BearerToken'],
                        response_type='object',
                    )

                    if api_response and api_response[0]:
                        logger.info('Prometheus CRDs found')
                        prometheus_found = True
                        monitoring_components.append('Prometheus CRDs')
                except Exception:
                    pass

            # Check for prometheus deployments
            if not prometheus_found:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'prometheus' in name or 'alertmanager' in name or 'grafana' in name:
                            logger.info(f'Found Prometheus component: {deploy_namespace}/{name}')
                            prometheus_found = True
                            monitoring_components.append(f'Deployment: {deploy_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for prometheus statefulsets
            if not prometheus_found:
                try:
                    statefulsets_response = k8s_api.list_resources(
                        kind='StatefulSet', api_version='apps/v1'
                    )

                    for statefulset in statefulsets_response.items:
                        statefulset_dict = (
                            statefulset.to_dict()
                            if hasattr(statefulset, 'to_dict')
                            else statefulset
                        )
                        metadata = statefulset_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        ss_namespace = metadata.get('namespace', 'unknown')

                        if 'prometheus' in name:
                            logger.info(f'Found Prometheus statefulset: {ss_namespace}/{name}')
                            prometheus_found = True
                            monitoring_components.append(f'StatefulSet: {ss_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for CloudWatch Container Insights
            cloudwatch_found = False

            # Check for cloudwatch namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['amazon-cloudwatch']:
                        logger.info(f'Found CloudWatch namespace: {name}')
                        cloudwatch_found = True
                        monitoring_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for cloudwatch agent daemonset
            if not cloudwatch_found:
                try:
                    daemonsets_response = k8s_api.list_resources(
                        kind='DaemonSet', api_version='apps/v1'
                    )

                    for daemonset in daemonsets_response.items:
                        daemonset_dict = (
                            daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                        )
                        metadata = daemonset_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        ds_namespace = metadata.get('namespace', 'unknown')

                        if 'cloudwatch' in name and 'fluent' not in name:  # Exclude logging agents
                            logger.info(f'Found CloudWatch agent: {ds_namespace}/{name}')
                            cloudwatch_found = True
                            monitoring_components.append(f'DaemonSet: {ds_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for cloudwatch agent deployment
            if not cloudwatch_found:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'cloudwatch' in name and 'fluent' not in name:  # Exclude logging agents
                            logger.info(f'Found CloudWatch agent: {deploy_namespace}/{name}')
                            cloudwatch_found = True
                            monitoring_components.append(f'Deployment: {deploy_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for Datadog
            datadog_found = False

            # Check for datadog namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['datadog']:
                        logger.info(f'Found Datadog namespace: {name}')
                        datadog_found = True
                        monitoring_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for datadog agent daemonset
            if not datadog_found:
                try:
                    daemonsets_response = k8s_api.list_resources(
                        kind='DaemonSet', api_version='apps/v1'
                    )

                    for daemonset in daemonsets_response.items:
                        daemonset_dict = (
                            daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                        )
                        metadata = daemonset_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        ds_namespace = metadata.get('namespace', 'unknown')

                        if 'datadog' in name:
                            logger.info(f'Found Datadog agent: {ds_namespace}/{name}')
                            datadog_found = True
                            monitoring_components.append(f'DaemonSet: {ds_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for New Relic
            newrelic_found = False

            # Check for newrelic namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['newrelic']:
                        logger.info(f'Found New Relic namespace: {name}')
                        newrelic_found = True
                        monitoring_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for newrelic agent daemonset
            if not newrelic_found:
                try:
                    daemonsets_response = k8s_api.list_resources(
                        kind='DaemonSet', api_version='apps/v1'
                    )

                    for daemonset in daemonsets_response.items:
                        daemonset_dict = (
                            daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                        )
                        metadata = daemonset_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        ds_namespace = metadata.get('namespace', 'unknown')

                        if 'newrelic' in name:
                            logger.info(f'Found New Relic agent: {ds_namespace}/{name}')
                            newrelic_found = True
                            monitoring_components.append(f'DaemonSet: {ds_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for Dynatrace
            dynatrace_found = False

            # Check for dynatrace namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['dynatrace']:
                        logger.info(f'Found Dynatrace namespace: {name}')
                        dynatrace_found = True
                        monitoring_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for dynatrace agent daemonset
            if not dynatrace_found:
                try:
                    daemonsets_response = k8s_api.list_resources(
                        kind='DaemonSet', api_version='apps/v1'
                    )

                    for daemonset in daemonsets_response.items:
                        daemonset_dict = (
                            daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                        )
                        metadata = daemonset_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        ds_namespace = metadata.get('namespace', 'unknown')

                        if 'dynatrace' in name or 'oneagent' in name:
                            logger.info(f'Found Dynatrace agent: {ds_namespace}/{name}')
                            dynatrace_found = True
                            monitoring_components.append(f'DaemonSet: {ds_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Determine if monitoring is in use
            monitoring_in_use = (
                prometheus_found
                or cloudwatch_found
                or datadog_found
                or newrelic_found
                or dynatrace_found
            )

            # Prepare detailed message
            details = []
            if monitoring_in_use:
                if prometheus_found:
                    details.append('Prometheus monitoring detected')
                if cloudwatch_found:
                    details.append('CloudWatch Container Insights detected')
                if datadog_found:
                    details.append('Datadog monitoring detected')
                if newrelic_found:
                    details.append('New Relic monitoring detected')
                if dynatrace_found:
                    details.append('Dynatrace monitoring detected')
            else:
                details.append('No monitoring solution detected in the cluster')

            detailed_message = '; '.join(details)
            logger.info(detailed_message)

            remediation = """
            Install a monitoring solution for your cluster:

            1. Prometheus Stack with Grafana:
            ```bash
            helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
            helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace
            ```

            2. CloudWatch Container Insights (for EKS):
            ```bash
            curl -s https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/your-cluster-name/;s/{{region_name}}/your-region/" | kubectl apply -f -
            ```

            3. Datadog:
            ```bash
            helm repo add datadog https://helm.datadoghq.com
            helm install datadog datadog/datadog --set datadog.apiKey=YOUR_API_KEY --namespace datadog --create-namespace
            ```
            """

            return {
                'check_id': 'A13',
                'check_name': 'Monitor your applications',
                'compliant': monitoring_in_use,
                'impacted_resources': monitoring_components,
                'details': detailed_message,
                'remediation': remediation if not monitoring_in_use else '',
            }

        except Exception as e:
            logger.error(f'Error checking for monitoring solutions: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'API error while checking for monitoring solutions: {str(e)}'

            return {
                'check_id': 'A13',
                'check_name': 'Monitor your applications',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_centralized_logging(
        self, k8s_api, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check A14: Centralized logging."""
        try:
            logger.info('Starting centralized logging check')

            logging_components = []

            # Check for Fluentd/Fluent Bit
            fluentd_found = False

            # Check for fluentd/fluent-bit daemonsets
            try:
                daemonsets_response = k8s_api.list_resources(
                    kind='DaemonSet', api_version='apps/v1'
                )

                for daemonset in daemonsets_response.items:
                    daemonset_dict = (
                        daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                    )
                    metadata = daemonset_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()
                    ds_namespace = metadata.get('namespace', 'unknown')

                    if 'fluentd' in name or 'fluent-bit' in name:
                        logger.info(f'Found Fluentd/Fluent Bit: {ds_namespace}/{name}')
                        fluentd_found = True
                        logging_components.append(f'DaemonSet: {ds_namespace}/{name}')
                        break
            except Exception:
                pass

            # Check for fluentd/fluent-bit deployments
            if not fluentd_found:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'fluentd' in name or 'fluent-bit' in name:
                            logger.info(f'Found Fluentd/Fluent Bit: {deploy_namespace}/{name}')
                            fluentd_found = True
                            logging_components.append(f'Deployment: {deploy_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for Elasticsearch/OpenSearch
            elastic_found = False

            # Check for elastic namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['elasticsearch', 'elastic', 'logging', 'opensearch']:
                        logger.info(f'Found Elasticsearch/OpenSearch namespace: {name}')
                        elastic_found = True
                        logging_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for elastic operator CRDs
            if not elastic_found:
                try:
                    api_client = k8s_api.api_client
                    api_response = api_client.call_api(
                        '/apis/elasticsearch.k8s.elastic.co/v1',
                        'GET',
                        auth_settings=['BearerToken'],
                        response_type='object',
                    )

                    if api_response and api_response[0]:
                        logger.info('Elasticsearch CRDs found')
                        elastic_found = True
                        logging_components.append('Elasticsearch CRDs')
                except Exception:
                    try:
                        api_client = k8s_api.api_client
                        api_response = api_client.call_api(
                            '/apis/opensearch.opster.io/v1',
                            'GET',
                            auth_settings=['BearerToken'],
                            response_type='object',
                        )

                        if api_response and api_response[0]:
                            logger.info('OpenSearch CRDs found')
                            elastic_found = True
                            logging_components.append('OpenSearch CRDs')
                    except Exception:
                        pass

            # Check for elastic/opensearch statefulsets
            if not elastic_found:
                try:
                    statefulsets_response = k8s_api.list_resources(
                        kind='StatefulSet', api_version='apps/v1'
                    )

                    for statefulset in statefulsets_response.items:
                        statefulset_dict = (
                            statefulset.to_dict()
                            if hasattr(statefulset, 'to_dict')
                            else statefulset
                        )
                        metadata = statefulset_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        ss_namespace = metadata.get('namespace', 'unknown')

                        if 'elasticsearch' in name or 'opensearch' in name:
                            logger.info(f'Found Elasticsearch/OpenSearch: {ss_namespace}/{name}')
                            elastic_found = True
                            logging_components.append(f'StatefulSet: {ss_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Check for CloudWatch Logs
            cloudwatch_logs_found = False

            # Check for cloudwatch namespace
            try:
                namespaces_response = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces_response.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name in ['amazon-cloudwatch']:
                        logger.info(f'Found CloudWatch namespace: {name}')
                        cloudwatch_logs_found = True
                        logging_components.append(f'Namespace: {name}')
                        break
            except Exception:
                pass

            # Check for fluent-bit daemonset in cloudwatch namespace
            if not cloudwatch_logs_found:
                try:
                    daemonsets_response = k8s_api.list_resources(
                        kind='DaemonSet', api_version='apps/v1', namespace='amazon-cloudwatch'
                    )

                    for daemonset in daemonsets_response.items:
                        daemonset_dict = (
                            daemonset.to_dict() if hasattr(daemonset, 'to_dict') else daemonset
                        )
                        metadata = daemonset_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'fluent-bit' in name:
                            logger.info(f'Found CloudWatch Logs agent: {name}')
                            cloudwatch_logs_found = True
                            logging_components.append(f'DaemonSet: amazon-cloudwatch/{name}')
                            break
                except Exception:
                    pass

            # Check for Loki
            loki_found = False

            # Check for loki statefulset or deployment
            try:
                statefulsets_response = k8s_api.list_resources(
                    kind='StatefulSet', api_version='apps/v1'
                )

                for statefulset in statefulsets_response.items:
                    statefulset_dict = (
                        statefulset.to_dict() if hasattr(statefulset, 'to_dict') else statefulset
                    )
                    metadata = statefulset_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()
                    ss_namespace = metadata.get('namespace', 'unknown')

                    if 'loki' in name:
                        logger.info(f'Found Loki: {ss_namespace}/{name}')
                        loki_found = True
                        logging_components.append(f'StatefulSet: {ss_namespace}/{name}')
                        break
            except Exception:
                pass

            if not loki_found:
                try:
                    deployments_response = k8s_api.list_resources(
                        kind='Deployment', api_version='apps/v1'
                    )

                    for deployment in deployments_response.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        deploy_namespace = metadata.get('namespace', 'unknown')

                        if 'loki' in name:
                            logger.info(f'Found Loki: {deploy_namespace}/{name}')
                            loki_found = True
                            logging_components.append(f'Deployment: {deploy_namespace}/{name}')
                            break
                except Exception:
                    pass

            # Determine if centralized logging is in use
            logging_in_use = fluentd_found or elastic_found or cloudwatch_logs_found or loki_found

            # Prepare detailed message
            details = []
            if logging_in_use:
                if fluentd_found:
                    details.append('Fluentd/Fluent Bit logging detected')
                if elastic_found:
                    details.append('Elasticsearch/OpenSearch logging detected')
                if cloudwatch_logs_found:
                    details.append('CloudWatch Logs detected')
                if loki_found:
                    details.append('Loki logging detected')
            else:
                details.append('No centralized logging solution detected in the cluster')

            detailed_message = '; '.join(details)
            logger.info(detailed_message)

            remediation = """
            Install a centralized logging solution:

            1. EFK Stack (Elasticsearch, Fluentd, Kibana):
            ```bash
            helm repo add elastic https://helm.elastic.co
            helm install elasticsearch elastic/elasticsearch --namespace logging --create-namespace
            helm install kibana elastic/kibana --namespace logging
            helm install fluentd bitnami/fluentd --namespace logging
            ```

            2. CloudWatch Logs (for EKS):
            ```bash
            curl -s https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/your-cluster-name/;s/{{region_name}}/your-region/" | kubectl apply -f -
            ```

            3. Loki with Grafana:
            ```bash
            helm repo add grafana https://grafana.github.io/helm-charts
            helm install loki grafana/loki-stack --namespace logging --create-namespace
            ```
            """

            return {
                'check_id': 'A14',
                'check_name': 'Use centralized logging',
                'compliant': logging_in_use,
                'impacted_resources': logging_components,
                'details': detailed_message,
                'remediation': remediation if not logging_in_use else '',
            }

        except Exception as e:
            logger.error(f'Error checking for logging solutions: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'API error while checking for logging solutions: {str(e)}'

            return {
                'check_id': 'A14',
                'check_name': 'Use centralized logging',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_c1(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check C1: Monitor Control Plane Metrics."""
        try:
            logger.info(f'Starting control plane metrics check for cluster: {cluster_name}')

            # Cluster name is now passed as a parameter
            if not cluster_name:
                return {
                    'check_id': 'C1',
                    'check_name': 'Monitor Control Plane Metrics',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': 'No cluster name provided',
                    'remediation': 'Ensure you are connected to a valid EKS cluster.',
                }

            # Create EKS client using AwsHelper
            try:
                eks_client = AwsHelper.create_boto3_client('eks')

                # Get cluster info
                cluster_info = eks_client.describe_cluster(name=cluster_name)

                # Check if CloudWatch metrics for EKS control plane are enabled
                logging_config = (
                    cluster_info['cluster'].get('logging', {}).get('clusterLogging', [])
                )
                control_plane_logging_enabled = False

                for config in logging_config:
                    if config.get('enabled', False) and 'api' in config.get('types', []):
                        control_plane_logging_enabled = True
                        break

                # Prepare remediation guidance
                remediation = f"""
                Enable control plane logging for your EKS cluster:

                ```bash
                aws eks update-cluster-config \\
                  --region <region> \\
                  --name {cluster_name} \\
                  --logging '{{"clusterLogging":[{{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}}]}}'
                ```

                Or using eksctl:
                ```bash
                eksctl utils update-cluster-logging \\
                  --enable-types api,audit,authenticator,controllerManager,scheduler \\
                  --region <region> \\
                  --cluster {cluster_name}
                ```
                """

                return {
                    'check_id': 'C1',
                    'check_name': 'Monitor Control Plane Metrics',
                    'compliant': control_plane_logging_enabled,
                    'impacted_resources': [cluster_name]
                    if not control_plane_logging_enabled
                    else [],
                    'details': 'Control plane logging is enabled'
                    if control_plane_logging_enabled
                    else 'Control plane logging is not enabled',
                    'remediation': remediation if not control_plane_logging_enabled else '',
                }

            except Exception as e:
                logger.error(f'Error checking control plane metrics: {str(e)}')
                return {
                    'check_id': 'C1',
                    'check_name': 'Monitor Control Plane Metrics',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': f'Error checking control plane metrics: {str(e)}',
                    'remediation': '',
                }

        except Exception as e:
            logger.error(f'Error checking control plane metrics: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking control plane metrics: {str(e)}'

            return {
                'check_id': 'C1',
                'check_name': 'Monitor Control Plane Metrics',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_c2(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check C2: Cluster Authentication."""
        try:
            logger.info(f'Starting cluster authentication check for cluster: {cluster_name}')

            # Cluster name is now passed as a parameter
            if not cluster_name:
                return {
                    'check_id': 'C2',
                    'check_name': 'Cluster Authentication',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': 'No cluster name provided',
                    'remediation': 'Ensure you are connected to a valid EKS cluster.',
                }

            # Create EKS client
            eks_client = AwsHelper.create_boto3_client('eks')

            # Check for aws-auth ConfigMap
            aws_auth_exists = False
            aws_auth_configured = False
            access_entries_enabled = False

            # Check for aws-auth ConfigMap
            try:
                aws_auth = k8s_api.list_resources(
                    kind='ConfigMap', api_version='v1', namespace='kube-system', name='aws-auth'
                )

                if aws_auth and hasattr(aws_auth, 'items') and len(aws_auth.items) > 0:
                    aws_auth_exists = True

                    # Check if aws-auth has mapRoles and mapUsers
                    aws_auth_item = aws_auth.items[0]
                    aws_auth_dict = (
                        aws_auth_item.to_dict()
                        if hasattr(aws_auth_item, 'to_dict')
                        else aws_auth_item
                    )

                    if aws_auth_dict.get('data') and (
                        'mapRoles' in aws_auth_dict['data'] or 'mapUsers' in aws_auth_dict['data']
                    ):
                        aws_auth_configured = True
            except Exception as e:
                logger.warning(f'Error checking aws-auth ConfigMap: {str(e)}')

            # Check if EKS access entries are enabled using boto3 API
            try:
                # First check authentication mode
                cluster_info = eks_client.describe_cluster(name=cluster_name)
                access_config = cluster_info['cluster'].get('accessConfig', {})

                if (
                    access_config.get('authenticationMode') == 'API_AND_CONFIG_MAP'
                    or access_config.get('authenticationMode') == 'API'
                ):
                    access_entries_enabled = True
                else:
                    # Try to list access entries as a fallback
                    try:
                        response = eks_client.list_access_entries(
                            clusterName=cluster_name, maxResults=1
                        )
                        if (
                            response
                            and 'accessEntries' in response
                            and len(response['accessEntries']) > 0
                        ):
                            access_entries_enabled = True
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f'Error checking EKS access entries: {str(e)}')

            # Determine authentication method and compliance
            if access_entries_enabled:
                details = 'Using EKS access entries (modern authentication method)'
                is_compliant = True
            elif aws_auth_exists and aws_auth_configured:
                details = 'Using aws-auth ConfigMap for authentication (traditional method)'
                is_compliant = True
            elif aws_auth_exists:
                details = 'aws-auth ConfigMap exists but is not properly configured'
                is_compliant = False
            else:
                details = 'No authentication method detected'
                is_compliant = False

            # Prepare remediation guidance
            remediation = """
            For EKS access entries (recommended for new clusters):

            ```bash
            # Enable API authentication mode
            aws eks update-cluster-config \\
              --region <region> \\
              --name <cluster-name> \\
              --access-config authenticationMode=API_AND_CONFIG_MAP

            # Create access entries for IAM roles/users
            aws eks create-access-entry \\
              --cluster-name <cluster-name> \\
              --principal-arn arn:aws:iam::<account-id>:role/<role-name> \\
              --kubernetes-groups system:masters
            ```

            For aws-auth ConfigMap (traditional method):

            ```bash
            # Create or update aws-auth ConfigMap
            kubectl apply -f - <<EOF
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: aws-auth
              namespace: kube-system
            data:
              mapRoles: |
                - rolearn: arn:aws:iam::<account-id>:role/<role-name>
                  username: <username>
                  groups:
                  - system:masters
            EOF
            ```
            """

            return {
                'check_id': 'C2',
                'check_name': 'Cluster Authentication',
                'compliant': is_compliant,
                'impacted_resources': [],
                'details': details,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking cluster authentication: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking cluster authentication: {str(e)}'

            return {
                'check_id': 'C2',
                'check_name': 'Cluster Authentication',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_c3(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check C3: Running large clusters."""
        try:
            logger.info('Starting large cluster check')

            # First check the number of services in the cluster
            service_count = 0
            try:
                services = k8s_api.list_resources(kind='Service', api_version='v1')
                service_count = len(services.items) if hasattr(services, 'items') else 0
                logger.info(f'Found {service_count} services in the cluster')
            except Exception as e:
                logger.error(f'Could not count services in the cluster: {str(e)}')
                return {
                    'check_id': 'C3',
                    'check_name': 'Running large clusters',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': f'Could not count services in the cluster: {str(e)}',
                    'remediation': '',
                }

            # If less than 1000 services, the cluster is not considered "large"
            if service_count < 1000:
                return {
                    'check_id': 'C3',
                    'check_name': 'Running large clusters',
                    'compliant': True,
                    'impacted_resources': [],
                    'details': f'Cluster has {service_count} services, which is less than 1000. No large cluster optimizations needed yet.',
                    'remediation': '',
                }

            # For clusters with 1000+ services, check optimizations
            issues = []
            best_practices = []

            # Check 1: Check if kube-proxy is running in IPVS mode for large clusters
            kube_proxy_mode = 'unknown'
            try:
                # Get kube-proxy ConfigMap
                kube_proxy_cm = k8s_api.list_resources(
                    kind='ConfigMap',
                    api_version='v1',
                    namespace='kube-system',
                    name='kube-proxy-config',
                )

                if (
                    kube_proxy_cm
                    and hasattr(kube_proxy_cm, 'items')
                    and len(kube_proxy_cm.items) > 0
                ):
                    kube_proxy_cm_item = kube_proxy_cm.items[0]
                    kube_proxy_cm_dict = (
                        kube_proxy_cm_item.to_dict()
                        if hasattr(kube_proxy_cm_item, 'to_dict')
                        else kube_proxy_cm_item
                    )

                    if (
                        kube_proxy_cm_dict.get('data')
                        and 'config.conf' in kube_proxy_cm_dict['data']
                    ):
                        config_data = kube_proxy_cm_dict['data']['config.conf']
                        if 'mode: "ipvs"' in config_data:
                            kube_proxy_mode = 'ipvs'
                            best_practices.append(
                                'kube-proxy is running in IPVS mode, which is recommended for large clusters'
                            )
                        else:
                            kube_proxy_mode = 'iptables'
                            issues.append(
                                'kube-proxy is running in iptables mode, which may cause network latency in clusters with >1000 services'
                            )
            except Exception as e:
                logger.warning(f'Could not determine kube-proxy mode: {str(e)}')
                issues.append('Could not determine kube-proxy mode')

            # Check 2: Check if AWS VPC CNI is used and has IP caching enabled
            vpc_cni_used = False
            cni_ip_caching = False
            try:
                # Check for aws-node DaemonSet
                aws_node_ds = k8s_api.list_resources(
                    kind='DaemonSet',
                    api_version='apps/v1',
                    namespace='kube-system',
                    name='aws-node',
                )

                if aws_node_ds and hasattr(aws_node_ds, 'items') and len(aws_node_ds.items) > 0:
                    vpc_cni_used = True
                    aws_node_ds_item = aws_node_ds.items[0]
                    aws_node_ds_dict = (
                        aws_node_ds_item.to_dict()
                        if hasattr(aws_node_ds_item, 'to_dict')
                        else aws_node_ds_item
                    )

                    # Check for WARM_IP_TARGET env var
                    containers = (
                        aws_node_ds_dict.get('spec', {})
                        .get('template', {})
                        .get('spec', {})
                        .get('containers', [])
                    )
                    for container in containers:
                        if container.get('name') == 'aws-node':
                            for env in container.get('env', []):
                                if (
                                    env.get('name') == 'WARM_IP_TARGET'
                                    and env.get('value')
                                    and int(env.get('value', '0')) > 0
                                ):
                                    cni_ip_caching = True
                                    best_practices.append(
                                        f'AWS VPC CNI has IP caching enabled (WARM_IP_TARGET={env.get("value")})'
                                    )
                                    break

                    if vpc_cni_used and not cni_ip_caching:
                        issues.append(
                            'AWS VPC CNI is used but does not have IP caching enabled (WARM_IP_TARGET), which may cause EC2 API throttling'
                        )
            except Exception as e:
                logger.warning(f'Could not check CNI configuration: {str(e)}')
                issues.append('Could not check CNI configuration')

            # Determine compliance based on findings
            is_compliant = kube_proxy_mode == 'ipvs' and (not vpc_cni_used or cni_ip_caching)

            details = [f'Cluster has {service_count} services (>1000)']
            if best_practices:
                details.extend(best_practices)
            if issues:
                details.extend(issues)

            # Prepare remediation guidance
            remediation = """
            For large clusters (>1000 services), consider the following optimizations:

            1. Configure kube-proxy to use IPVS mode:
            ```yaml
            # Edit the kube-proxy ConfigMap
            kubectl edit configmap -n kube-system kube-proxy-config

            # Set mode to "ipvs" in the config.conf section:
            mode: "ipvs"
            ```

            2. Enable IP caching for AWS VPC CNI:
            ```bash
            # Set WARM_IP_TARGET to cache IPs
            kubectl set env daemonset -n kube-system aws-node WARM_IP_TARGET=5
            ```

            3. Consider other large cluster optimizations:
            - Use node affinity and anti-affinity for critical workloads
            - Implement cluster autoscaler for dynamic scaling
            - Use separate node groups for system and application workloads
            - Consider AWS EKS Fargate for serverless workloads
            """

            return {
                'check_id': 'C3',
                'check_name': 'Running large clusters',
                'compliant': is_compliant,
                'impacted_resources': [],
                'details': '; '.join(details),
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking large cluster optimizations: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking large cluster optimizations: {str(e)}'

            return {
                'check_id': 'C3',
                'check_name': 'Running large clusters',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_c4(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check C4: EKS Control Plane Endpoint Access Control."""
        try:
            logger.info(
                f'Starting control plane endpoint access check for cluster: {cluster_name}'
            )

            # Cluster name is now passed as a parameter
            if not cluster_name:
                return {
                    'check_id': 'C4',
                    'check_name': 'EKS Control Plane Endpoint Access Control',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': 'No cluster name provided',
                    'remediation': 'Ensure you are connected to a valid EKS cluster.',
                }

            # Create EKS client
            eks_client = AwsHelper.create_boto3_client('eks')

            # Get cluster info
            cluster_info = eks_client.describe_cluster(name=cluster_name)
            vpc_config = cluster_info['cluster'].get('resourcesVpcConfig', {})

            # Check endpoint access configuration
            public_access = vpc_config.get('endpointPublicAccess', False)
            private_access = vpc_config.get('endpointPrivateAccess', False)
            public_access_cidrs = vpc_config.get('publicAccessCidrs', [])

            # Create resource entry with access configuration details
            access_config = []
            if public_access:
                cidrs_str = ', '.join(public_access_cidrs) if public_access_cidrs else '0.0.0.0/0'
                access_config.append(
                    f'{cluster_name}: Public={public_access} ({cidrs_str}), Private={private_access}'
                )
            else:
                access_config.append(
                    f'{cluster_name}: Public={public_access}, Private={private_access}'
                )

            # Compliant if public access is disabled or restricted to specific CIDRs (not 0.0.0.0/0)
            is_compliant = not public_access or (
                public_access and '0.0.0.0/0' not in public_access_cidrs
            )

            details = (
                'Control plane endpoint access is properly restricted'
                if is_compliant
                else 'Control plane endpoint has unrestricted public access'
            )

            # Prepare remediation guidance
            remediation = """
            Restrict public access to your EKS cluster control plane:

            ```bash
            # Option 1: Disable public access entirely (if you have private access enabled)
            aws eks update-cluster-config \\
              --region <region> \\
              --name <cluster-name> \\
              --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true

            # Option 2: Restrict public access to specific CIDR blocks
            aws eks update-cluster-config \\
              --region <region> \\
              --name <cluster-name> \\
              --resources-vpc-config publicAccessCidrs=<cidr1>,<cidr2>
            ```

            Replace <cidr1>,<cidr2> with your specific IP ranges (e.g., "192.168.1.0/24,10.0.0.0/16").
            """

            return {
                'check_id': 'C4',
                'check_name': 'EKS Control Plane Endpoint Access Control',
                'compliant': is_compliant,
                'impacted_resources': access_config,
                'details': details,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking control plane endpoint access: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking control plane endpoint access: {str(e)}'

            return {
                'check_id': 'C4',
                'check_name': 'EKS Control Plane Endpoint Access Control',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_c5(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check C5: Avoid catch-all admission webhooks."""
        try:
            logger.info('Starting admission webhooks check')

            catch_all_webhooks = []

            # Check mutating webhooks
            try:
                # Use the K8s API to get mutating webhook configurations
                mutating_webhooks = k8s_api.list_resources(
                    kind='MutatingWebhookConfiguration',
                    api_version='admissionregistration.k8s.io/v1',
                )

                if mutating_webhooks and hasattr(mutating_webhooks, 'items'):
                    for webhook_config in mutating_webhooks.items:
                        webhook_config_dict = (
                            webhook_config.to_dict()
                            if hasattr(webhook_config, 'to_dict')
                            else webhook_config
                        )
                        webhook_name = webhook_config_dict.get('metadata', {}).get(
                            'name', 'unknown'
                        )

                        for webhook in webhook_config_dict.get('webhooks', []):
                            # Check for catch-all patterns
                            is_catch_all = False
                            reasons = []

                            # Check namespace selector
                            namespace_selector = webhook.get('namespaceSelector', {})
                            if not namespace_selector or not namespace_selector.get(
                                'matchExpressions', []
                            ):
                                is_catch_all = True
                                reasons.append('no namespaceSelector')

                            # Check object selector
                            object_selector = webhook.get('objectSelector', {})
                            if not object_selector or not object_selector.get(
                                'matchExpressions', []
                            ):
                                is_catch_all = True
                                reasons.append('no objectSelector')

                            # Check rules
                            for rule in webhook.get('rules', []):
                                api_groups = rule.get('apiGroups', [])
                                api_versions = rule.get('apiVersions', [])
                                resources = rule.get('resources', [])

                                if '*' in api_groups or len(api_groups) == 0:
                                    is_catch_all = True
                                    reasons.append('wildcard apiGroups')

                                if '*' in api_versions or len(api_versions) == 0:
                                    is_catch_all = True
                                    reasons.append('wildcard apiVersions')

                                if '*' in resources or len(resources) == 0:
                                    is_catch_all = True
                                    reasons.append('wildcard resources')

                            # Check scope
                            if webhook.get('scope') == '*':
                                is_catch_all = True
                                reasons.append('wildcard scope')

                            if is_catch_all:
                                catch_all_webhooks.append(
                                    f'MutatingWebhook: {webhook_name}/{webhook.get("name", "unknown")} ({", ".join(reasons)})'
                                )
            except Exception as e:
                logger.warning(f'Error checking mutating webhooks: {str(e)}')

            # Check validating webhooks
            try:
                # Use the K8s API to get validating webhook configurations
                validating_webhooks = k8s_api.list_resources(
                    kind='ValidatingWebhookConfiguration',
                    api_version='admissionregistration.k8s.io/v1',
                )

                if validating_webhooks and hasattr(validating_webhooks, 'items'):
                    for webhook_config in validating_webhooks.items:
                        webhook_config_dict = (
                            webhook_config.to_dict()
                            if hasattr(webhook_config, 'to_dict')
                            else webhook_config
                        )
                        webhook_name = webhook_config_dict.get('metadata', {}).get(
                            'name', 'unknown'
                        )

                        for webhook in webhook_config_dict.get('webhooks', []):
                            # Check for catch-all patterns
                            is_catch_all = False
                            reasons = []

                            # Check namespace selector
                            namespace_selector = webhook.get('namespaceSelector', {})
                            if not namespace_selector or not namespace_selector.get(
                                'matchExpressions', []
                            ):
                                is_catch_all = True
                                reasons.append('no namespaceSelector')

                            # Check object selector
                            object_selector = webhook.get('objectSelector', {})
                            if not object_selector or not object_selector.get(
                                'matchExpressions', []
                            ):
                                is_catch_all = True
                                reasons.append('no objectSelector')

                            # Check rules
                            for rule in webhook.get('rules', []):
                                api_groups = rule.get('apiGroups', [])
                                api_versions = rule.get('apiVersions', [])
                                resources = rule.get('resources', [])

                                if '*' in api_groups or len(api_groups) == 0:
                                    is_catch_all = True
                                    reasons.append('wildcard apiGroups')

                                if '*' in api_versions or len(api_versions) == 0:
                                    is_catch_all = True
                                    reasons.append('wildcard apiVersions')

                                if '*' in resources or len(resources) == 0:
                                    is_catch_all = True
                                    reasons.append('wildcard resources')

                            # Check scope
                            if webhook.get('scope') == '*':
                                is_catch_all = True
                                reasons.append('wildcard scope')

                            if is_catch_all:
                                catch_all_webhooks.append(
                                    f'ValidatingWebhook: {webhook_name}/{webhook.get("name", "unknown")} ({", ".join(reasons)})'
                                )
            except Exception as e:
                logger.warning(f'Error checking validating webhooks: {str(e)}')

            # Determine compliance based on findings
            is_compliant = len(catch_all_webhooks) == 0

            if is_compliant:
                details = 'No catch-all admission webhooks found'
            else:
                details = f'Found {len(catch_all_webhooks)} catch-all admission webhooks'

            # Prepare remediation guidance
            remediation = """
            Update your webhook configurations to use more specific selectors:

            ```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: my-webhook
webhooks:
- name: my-webhook.example.com
  # Add namespace selector
  namespaceSelector:
    matchExpressions:
    - key: kubernetes.io/metadata.name
      operator: NotIn
      values: ["kube-system", "kube-public"]

  # Add object selector
  objectSelector:
    matchLabels:
      app: my-app

  # Specify rules more precisely
  rules:
  - apiGroups: ["apps"]
    apiVersions: ["v1"]
    resources: ["deployments"]
    scope: "Namespaced"
            ```

            This helps avoid performance issues and unexpected behavior in your cluster.
            """

            return {
                'check_id': 'C5',
                'check_name': 'Avoid catch-all admission webhooks',
                'compliant': is_compliant,
                'impacted_resources': catch_all_webhooks,
                'details': details,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking admission webhooks: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking admission webhooks: {str(e)}'

            return {
                'check_id': 'C5',
                'check_name': 'Avoid catch-all admission webhooks',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_d1(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check D1: Use Kubernetes Cluster Autoscaler or Karpenter."""
        try:
            logger.info('Starting node autoscaling check')

            auto_scaling_components = []

            # Check for cluster-autoscaler deployment
            cluster_autoscaler_exists = False
            try:
                # Use the K8sApis list_resources method to get deployments
                deployments = k8s_api.list_resources(kind='Deployment', api_version='apps/v1')

                for deployment in deployments.items:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )
                    metadata = deployment_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()
                    namespace = metadata.get('namespace', '')

                    if 'cluster-autoscaler' in name:
                        cluster_autoscaler_exists = True
                        auto_scaling_components.append(f'Deployment: {namespace}/{name}')
                        logger.info(f'Found Cluster Autoscaler deployment: {namespace}/{name}')
                        break
            except Exception as e:
                logger.warning(f'Error checking for Cluster Autoscaler: {str(e)}')

            # Check for Karpenter controller
            karpenter_exists = False
            try:
                # Check for karpenter namespace
                namespaces = k8s_api.list_resources(kind='Namespace', api_version='v1')

                for ns in namespaces.items:
                    ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                    metadata = ns_dict.get('metadata', {})
                    name = metadata.get('name', '').lower()

                    if name == 'karpenter':
                        karpenter_exists = True
                        auto_scaling_components.append(f'Namespace: {name}')
                        logger.info(f'Found Karpenter namespace: {name}')
                        break

                # If namespace not found, check for karpenter deployment in any namespace
                if not karpenter_exists:
                    deployments = k8s_api.list_resources(kind='Deployment', api_version='apps/v1')

                    for deployment in deployments.items:
                        deployment_dict = (
                            deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                        )
                        metadata = deployment_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()
                        namespace = metadata.get('namespace', '')

                        if 'karpenter' in name:
                            karpenter_exists = True
                            auto_scaling_components.append(f'Deployment: {namespace}/{name}')
                            logger.info(f'Found Karpenter deployment: {namespace}/{name}')
                            break

                # Check for Karpenter CRDs
                if not karpenter_exists:
                    try:
                        api_response = k8s_api.api_client.call_api(
                            '/apis/karpenter.sh/v1alpha5',
                            'GET',
                            auth_settings=['BearerToken'],
                            response_type='object',
                        )
                        if api_response and api_response[0]:
                            karpenter_exists = True
                            auto_scaling_components.append('Karpenter CRDs')
                            logger.info('Found Karpenter CRDs')
                    except Exception as e:
                        logger.warning(f'Error checking for Karpenter CRDs: {str(e)}')
            except Exception as e:
                logger.warning(f'Error checking for Karpenter: {str(e)}')

            # Either Cluster Autoscaler or Karpenter is sufficient
            is_compliant = cluster_autoscaler_exists or karpenter_exists

            details = []
            if cluster_autoscaler_exists:
                details.append('Cluster Autoscaler is deployed')
            if karpenter_exists:
                details.append('Karpenter is deployed')
            if not is_compliant:
                details.append('Neither Cluster Autoscaler nor Karpenter is deployed')

            detailed_message = '; '.join(details)
            logger.info(f'Node autoscaling check completed: {is_compliant}')

            remediation = """
            Deploy either Cluster Autoscaler or Karpenter for node autoscaling:

            For Cluster Autoscaler:
            ```
            helm repo add autoscaler https://kubernetes.github.io/autoscaler
            helm install cluster-autoscaler autoscaler/cluster-autoscaler \
              --namespace kube-system \
              --set autoDiscovery.clusterName=<your-cluster-name> \
              --set awsRegion=<your-region>
            ```

            For Karpenter:
            ```
            helm repo add karpenter https://charts.karpenter.sh
            helm install karpenter karpenter/karpenter \
              --namespace karpenter \
              --create-namespace \
              --set serviceAccount.create=true \
              --set serviceAccount.name=karpenter \
              --set clusterName=<your-cluster-name> \
              --set clusterEndpoint=<your-cluster-endpoint>
            ```
            """

            return {
                'check_id': 'D1',
                'check_name': 'Use Kubernetes Cluster Autoscaler or Karpenter',
                'compliant': is_compliant,
                'impacted_resources': auto_scaling_components if is_compliant else [],
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking for node autoscaling: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking for node autoscaling: {str(e)}'

            return {
                'check_id': 'D1',
                'check_name': 'Use Kubernetes Cluster Autoscaler or Karpenter',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_d2(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check D2: Worker nodes spread across multiple AZs."""
        try:
            logger.info('Starting AZ distribution check')

            # Get all nodes
            nodes = k8s_api.list_resources(kind='Node', api_version='v1')

            az_counts = Counter()

            # Count nodes per AZ
            for node in nodes.items:
                node_dict = node.to_dict() if hasattr(node, 'to_dict') else node
                labels = node_dict.get('metadata', {}).get('labels', {})

                # Try both the new and old label for availability zone
                az = labels.get('topology.kubernetes.io/zone') or labels.get(
                    'failure-domain.beta.kubernetes.io/zone'
                )

                if az:
                    az_counts[az] += 1

            num_azs = len(az_counts)
            total_nodes = sum(az_counts.values())

            # Check if nodes are spread across multiple AZs
            is_multi_az = num_azs > 1

            if not is_multi_az:
                logger.info('Worker nodes are not spread across multiple AZs')

                remediation = """
                Ensure worker nodes are spread across multiple Availability Zones:

                For managed node groups:
                ```
                eksctl create nodegroup \
                  --cluster=<your-cluster-name> \
                  --name=<nodegroup-name> \
                  --node-type=<instance-type> \
                  --nodes=3 \
                  --nodes-min=3 \
                  --nodes-max=6 \
                  --asg-access \
                  --node-zones=<region>a,<region>b,<region>c
                ```

                For self-managed nodes, create Auto Scaling Groups in multiple AZs.
                """

                return {
                    'check_id': 'D2',
                    'check_name': 'Worker nodes spread across multiple AZs',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': 'Worker nodes are not spread across multiple AZs',
                    'remediation': remediation,
                }

            # Check if spread is roughly even (max 20% variance allowed)
            avg_nodes_per_az = total_nodes / num_azs
            spread_ok = all(
                abs(count - avg_nodes_per_az) / avg_nodes_per_az <= 0.2
                for count in az_counts.values()
            )

            is_compliant = is_multi_az and spread_ok

            details = (
                f'Nodes are spread across {num_azs} AZs: {dict(az_counts)}. '
                f'{"Spread is balanced." if spread_ok else "Spread is uneven across AZs."}'
            )

            logger.info(f'AZ distribution check completed: {is_compliant}')

            remediation = """
            Rebalance your nodes across Availability Zones:

            1. For managed node groups, update the desired capacity for each AZ:
            ```
            aws eks update-nodegroup-config \
              --cluster-name <your-cluster-name> \
              --nodegroup-name <nodegroup-name> \
              --scaling-config desiredSize=<desired-size>
            ```

            2. For self-managed nodes, adjust the desired capacity of your Auto Scaling Groups.

            3. Consider using Cluster Autoscaler with balanced capacity across AZs.
            """

            return {
                'check_id': 'D2',
                'check_name': 'Worker nodes spread across multiple AZs',
                'compliant': is_compliant,
                'impacted_resources': [] if is_compliant else list(az_counts),
                'details': details,
                'remediation': remediation if not spread_ok else '',
            }

        except Exception as e:
            logger.error(f'Error checking AZ distribution: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking AZ distribution: {str(e)}'

            return {
                'check_id': 'D2',
                'check_name': 'Worker nodes spread across multiple AZs',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_d3(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check D3: Configure Resource Requests/Limits."""
        try:
            logger.info('Starting resource requests/limits check')

            workloads_without_resources = []
            workloads_with_memory_mismatch = []

            # Prepare kwargs for filtering
            kwargs = {}
            if namespace:
                kwargs['namespace'] = namespace
                logger.info(f'Checking workloads in namespace: {namespace}')
            else:
                logger.info('Checking workloads across all namespaces')

            # Helper function to parse memory values to bytes for comparison
            def parse_memory_to_bytes(memory_str):
                """Convert memory string (e.g., '128Mi', '1Gi') to bytes for comparison."""
                if not memory_str:
                    return 0

                memory_str = str(memory_str).strip()

                # Handle different units
                multipliers = {
                    'Ki': 1024,
                    'Mi': 1024**2,
                    'Gi': 1024**3,
                    'Ti': 1024**4,
                    'k': 1000,
                    'M': 1000**2,
                    'G': 1000**3,
                    'T': 1000**4,
                }

                # Extract number and unit
                import re

                match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Za-z]*)$', memory_str)
                if not match:
                    # If no unit, assume bytes
                    try:
                        return int(float(memory_str))
                    except (ValueError, TypeError):
                        return 0

                value, unit = match.groups()
                try:
                    value = float(value)
                    if unit in multipliers:
                        return int(value * multipliers[unit])
                    else:
                        # No unit or unknown unit, assume bytes
                        return int(value)
                except (ValueError, TypeError):
                    return 0

            # Helper function to check resource configuration
            def check_workload_resources(workload_dict, workload_type):
                metadata = workload_dict.get('metadata', {})
                workload_namespace = metadata.get('namespace', 'default')
                name = metadata.get('name', 'unknown')

                # Get containers from pod template
                containers = (
                    workload_dict.get('spec', {})
                    .get('template', {})
                    .get('spec', {})
                    .get('containers', [])
                )

                # Check if all containers have resource requests and limits
                all_have_resources = True
                has_memory_mismatch = False

                for container in containers:
                    resources = container.get('resources', {})

                    # Check if resources, requests, and limits are defined
                    if (
                        not resources
                        or not resources.get('requests')
                        or not resources.get('limits')
                    ):
                        all_have_resources = False
                        break

                    # Check if CPU and memory requests and limits are defined
                    requests = resources.get('requests', {})
                    limits = resources.get('limits', {})

                    if (
                        'cpu' not in requests
                        or 'memory' not in requests
                        or 'cpu' not in limits
                        or 'memory' not in limits
                    ):
                        all_have_resources = False
                        break

                    # Check if memory request equals memory limit
                    memory_request = requests.get('memory', '')
                    memory_limit = limits.get('memory', '')

                    if memory_request and memory_limit:
                        request_bytes = parse_memory_to_bytes(memory_request)
                        limit_bytes = parse_memory_to_bytes(memory_limit)

                        if request_bytes != limit_bytes and request_bytes > 0 and limit_bytes > 0:
                            has_memory_mismatch = True
                            logger.info(
                                f'{workload_type} has memory request/limit mismatch: {workload_namespace}/{name} (request: {memory_request}, limit: {memory_limit})'
                            )

                if not all_have_resources:
                    workloads_without_resources.append(
                        f'{workload_type}: {workload_namespace}/{name}'
                    )
                    logger.info(
                        f'{workload_type} without proper resource requests/limits: {workload_namespace}/{name}'
                    )
                elif has_memory_mismatch:
                    workloads_with_memory_mismatch.append(
                        f'{workload_type}: {workload_namespace}/{name}'
                    )
                    logger.info(
                        f'{workload_type} with memory request/limit mismatch: {workload_namespace}/{name}'
                    )

            # Check Deployments
            logger.info('Checking Deployments for resource requests/limits')
            try:
                deployments = k8s_api.list_resources(
                    kind='Deployment', api_version='apps/v1', **kwargs
                )

                for deployment in deployments.items:
                    deployment_dict = (
                        deployment.to_dict() if hasattr(deployment, 'to_dict') else deployment
                    )
                    check_workload_resources(deployment_dict, 'Deployment')
            except Exception as e:
                logger.error(f'Error checking deployments: {str(e)}')

            # Check StatefulSets
            logger.info('Checking StatefulSets for resource requests/limits')
            try:
                statefulsets = k8s_api.list_resources(
                    kind='StatefulSet', api_version='apps/v1', **kwargs
                )

                for statefulset in statefulsets.items:
                    statefulset_dict = (
                        statefulset.to_dict() if hasattr(statefulset, 'to_dict') else statefulset
                    )
                    check_workload_resources(statefulset_dict, 'StatefulSet')
            except Exception as e:
                logger.error(f'Error checking statefulsets: {str(e)}')

            # Combine all issues for compliance check
            all_impacted_resources = workloads_without_resources + workloads_with_memory_mismatch
            is_compliant = len(all_impacted_resources) == 0

            # Build detailed message with separated categories
            details = []
            if workloads_without_resources:
                details.append(
                    f'Missing resource specs: {len(workloads_without_resources)} workloads ({", ".join(workloads_without_resources)})'
                )
            if workloads_with_memory_mismatch:
                details.append(
                    f'Memory request/limit mismatch: {len(workloads_with_memory_mismatch)} workloads ({", ".join(workloads_with_memory_mismatch)})'
                )

            if not details:
                detailed_message = (
                    'All workloads (Deployments/StatefulSets) have proper resource configuration'
                )
            else:
                detailed_message = '; '.join(details)

            logger.info(f'Resource requests/limits check completed: {is_compliant}')

            # Create structured impacted resources with categories
            structured_resources = {}
            if workloads_without_resources:
                structured_resources['missing_resource_specs'] = workloads_without_resources
            if workloads_with_memory_mismatch:
                structured_resources['memory_request_limit_mismatch'] = (
                    workloads_with_memory_mismatch
                )

            remediation = """
            Configure resource requests and limits for all containers in your workloads:

            For missing resource specifications:
            ```yaml
apiVersion: apps/v1
kind: Deployment  # or StatefulSet
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: my-container
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "128Mi"  # Same as request for Guaranteed QoS
            ```

            For Guaranteed QoS (recommended for critical workloads), set memory requests equal to limits:
            ```yaml
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"  # Must match request for Guaranteed QoS
            ```

            Consider using the Vertical Pod Autoscaler in recommendation mode to determine appropriate values.
            """

            return {
                'check_id': 'D3',
                'check_name': 'Configure Resource Requests/Limits',
                'compliant': is_compliant,
                'impacted_resources': structured_resources if structured_resources else [],
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking resource requests/limits: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking resource requests/limits: {str(e)}'

            return {
                'check_id': 'D3',
                'check_name': 'Configure Resource Requests/Limits',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_d6(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check D14: Monitor CoreDNS metrics."""
        try:
            logger.info('Starting CoreDNS metrics check')

            # Check if CoreDNS is deployed with Prometheus metrics enabled
            coredns_deployments = k8s_api.list_resources(
                kind='Deployment',
                api_version='apps/v1',
                namespace='kube-system',
                field_selector='metadata.name=coredns',
            )

            if not hasattr(coredns_deployments, 'items') or len(coredns_deployments.items) == 0:
                logger.info('CoreDNS deployment not found')

                remediation = """
                CoreDNS deployment not found. This is unusual for an EKS cluster.

                Check if CoreDNS is running as a different resource type:
                ```
                kubectl get all -n kube-system -l k8s-app=kube-dns
                ```

                If CoreDNS is not deployed, consider installing it:
                ```
                helm repo add coredns https://coredns.github.io/helm
                helm install coredns coredns/coredns --namespace kube-system
                ```
                """

                return {
                    'check_id': 'D6',
                    'check_name': 'Monitor CoreDNS metrics',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': 'CoreDNS deployment not found',
                    'remediation': remediation,
                }

            # Check if CoreDNS has metrics enabled (port 9153)
            coredns_deployment = coredns_deployments.items[0]
            coredns_deployment_dict = (
                coredns_deployment.to_dict()
                if hasattr(coredns_deployment, 'to_dict')
                else coredns_deployment
            )

            metrics_enabled = False
            containers = (
                coredns_deployment_dict.get('spec', {})
                .get('template', {})
                .get('spec', {})
                .get('containers', [])
            )

            for container in containers:
                if container.get('name') == 'coredns':
                    for port in container.get('ports', []):
                        if port.get('containerPort') == 9153:
                            metrics_enabled = True
                            logger.info('CoreDNS metrics port 9153 is enabled')
                            break

            # Check if there's a ServiceMonitor for CoreDNS (if using Prometheus Operator)
            has_service_monitor = False
            try:
                api_response = k8s_api.api_client.call_api(
                    '/apis/monitoring.coreos.com/v1',
                    'GET',
                    auth_settings=['BearerToken'],
                    response_type='object',
                )

                # If the API exists, check for ServiceMonitors
                if api_response and api_response[0]:
                    service_monitors = k8s_api.list_resources(
                        group='monitoring.coreos.com',
                        version='v1',
                        kind='ServiceMonitor',
                        plural='servicemonitors',
                    )

                    for monitor in service_monitors.items:
                        monitor_dict = (
                            monitor.to_dict() if hasattr(monitor, 'to_dict') else monitor
                        )
                        metadata = monitor_dict.get('metadata', {})
                        name = metadata.get('name', '').lower()

                        if 'coredns' in name or 'kube-dns' in name:
                            has_service_monitor = True
                            logger.info(
                                f'Found ServiceMonitor for CoreDNS: {metadata.get("namespace", "")}/{name}'
                            )
                            break
            except Exception as e:
                logger.warning(f'Error checking for ServiceMonitor CRD: {str(e)}')
                # ServiceMonitor CRD might not be installed
                pass

            # Check if there's a Prometheus scrape config for CoreDNS
            has_prometheus_scrape = False
            try:
                # Look for ConfigMaps that might contain Prometheus configuration
                config_maps = k8s_api.list_resources(
                    kind='ConfigMap', api_version='v1', label_selector='app=prometheus'
                )

                for cm in config_maps.items:
                    cm_dict = cm.to_dict() if hasattr(cm, 'to_dict') else cm
                    data = cm_dict.get('data', {})

                    # Check common Prometheus config files
                    for key in ['prometheus.yml', 'prometheus.yaml']:
                        if key in data and ('coredns' in data[key] or 'kube-dns' in data[key]):
                            has_prometheus_scrape = True
                            logger.info(
                                f'Found Prometheus scrape config for CoreDNS in ConfigMap: {cm_dict.get("metadata", {}).get("namespace", "")}/{cm_dict.get("metadata", {}).get("name", "")}'
                            )
                            break

                    if has_prometheus_scrape:
                        break
            except Exception as e:
                logger.warning(f'Error checking for Prometheus ConfigMaps: {str(e)}')
                pass

            is_compliant = metrics_enabled and (has_service_monitor or has_prometheus_scrape)

            details = []
            if metrics_enabled:
                details.append('CoreDNS metrics port is enabled')
            else:
                details.append('CoreDNS metrics port is not enabled')

            if has_service_monitor:
                details.append('ServiceMonitor for CoreDNS exists')
            elif has_prometheus_scrape:
                details.append('Prometheus scrape config for CoreDNS exists')
            else:
                details.append('No monitoring configuration found for CoreDNS')

            detailed_message = '; '.join(details)
            logger.info(f'CoreDNS metrics check completed: {is_compliant}')

            remediation = """
            Enable CoreDNS metrics monitoring:

            1. Ensure CoreDNS metrics port is exposed (should be by default on EKS):
            ```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coredns
  namespace: kube-system
spec:
  template:
    spec:
      containers:
      - name: coredns
        ports:
        - containerPort: 9153
          name: metrics
          protocol: TCP
            ```

            2. Create a ServiceMonitor for CoreDNS (if using Prometheus Operator):
            ```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: coredns
  namespace: monitoring
spec:
  endpoints:
  - bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
    interval: 30s
    port: metrics
  jobLabel: k8s-app
  namespaceSelector:
    matchNames:
    - kube-system
  selector:
    matchLabels:
      k8s-app: kube-dns
            ```

            3. Or add a scrape config to Prometheus (if not using Prometheus Operator):
            ```yaml
            scrape_configs:
              - job_name: 'coredns'
                kubernetes_sd_configs:
                - role: endpoints
                  namespaces:
                    names:
                    - kube-system
                relabel_configs:
                - source_labels: [__meta_kubernetes_service_label_k8s_app]
                  regex: kube-dns
                  action: keep
                - source_labels: [__meta_kubernetes_endpoint_port_name]
                  regex: metrics
                  action: keep
            ```
            """

            return {
                'check_id': 'D6',
                'check_name': 'Monitor CoreDNS metrics',
                'compliant': is_compliant,
                'impacted_resources': [],
                'details': detailed_message,
                'remediation': remediation if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking CoreDNS metrics: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking CoreDNS metrics: {str(e)}'

            return {
                'check_id': 'D6',
                'check_name': 'Monitor CoreDNS metrics',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _check_d4(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if namespaces have ResourceQuotas configured."""
        try:
            logger.info('Starting namespace resource quotas check')

            # If a specific namespace is provided, only check that namespace
            if namespace:
                # Check if the namespace exists
                try:
                    ns = k8s_api.list_resources(
                        kind='Namespace',
                        api_version='v1',
                        field_selector=f'metadata.name={namespace}',
                    )

                    if not hasattr(ns, 'items') or len(ns.items) == 0:
                        return {
                            'check_id': 'D4',
                            'check_name': 'Namespace ResourceQuotas',
                            'compliant': False,
                            'impacted_resources': [],
                            'details': f'Namespace {namespace} not found',
                            'remediation': '',
                        }

                    # Check if the namespace has a ResourceQuota
                    quotas = k8s_api.list_resources(
                        kind='ResourceQuota', api_version='v1', namespace=namespace
                    )

                    has_quota = hasattr(quotas, 'items') and len(quotas.items) > 0

                    return {
                        'check_id': 'D4',
                        'check_name': 'Namespace ResourceQuotas',
                        'compliant': has_quota,
                        'impacted_resources': [] if has_quota else [namespace],
                        'details': f'Namespace {namespace} {"has" if has_quota else "does not have"} ResourceQuota',
                        'remediation': self._get_resource_quota_remediation()
                        if not has_quota
                        else '',
                    }
                except Exception as e:
                    logger.error(
                        f'Error checking ResourceQuota for namespace {namespace}: {str(e)}'
                    )
                    return {
                        'check_id': 'D4',
                        'check_name': 'Namespace ResourceQuotas',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Error checking ResourceQuota for namespace {namespace}: {str(e)}',
                        'remediation': '',
                    }

            # Check all namespaces
            namespaces = k8s_api.list_resources(kind='Namespace', api_version='v1')

            quotas = k8s_api.list_resources(kind='ResourceQuota', api_version='v1')

            # Create a set of namespaces that have ResourceQuotas
            quota_ns_set = set()
            for quota in quotas.items:
                quota_dict = quota.to_dict() if hasattr(quota, 'to_dict') else quota
                ns = quota_dict.get('metadata', {}).get('namespace')
                if ns:
                    quota_ns_set.add(ns)

            # Check only default namespace and user-created namespaces, excluding system namespaces
            system_namespaces_to_ignore = {'kube-system', 'kube-public', 'kube-node-lease'}
            target_namespaces = []
            missing = []

            for ns in namespaces.items:
                ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                ns_name = ns_dict.get('metadata', {}).get('name')

                # Include default namespace and any user-created namespaces
                if ns_name and ns_name not in system_namespaces_to_ignore:
                    target_namespaces.append(ns_name)
                    if ns_name not in quota_ns_set:
                        missing.append(ns_name)

            is_compliant = len(missing) == 0

            if len(target_namespaces) == 0:
                detailed_message = "No target namespaces found (this should not happen as 'default' namespace should always exist)"
            elif is_compliant:
                detailed_message = f'All {len(target_namespaces)} target namespaces have ResourceQuota (including default namespace)'
            else:
                detailed_message = f'Found {len(missing)} of {len(target_namespaces)} target namespaces without ResourceQuota: {", ".join(missing)}'
            logger.info(f'Namespace resource quotas check completed: {is_compliant}')

            return {
                'check_id': 'D4',
                'check_name': 'Namespace ResourceQuotas',
                'compliant': is_compliant,
                'impacted_resources': missing,
                'details': detailed_message,
                'remediation': self._get_resource_quota_remediation() if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking namespace resource quotas: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking namespace resource quotas: {str(e)}'

            return {
                'check_id': 'D4',
                'check_name': 'Namespace ResourceQuotas',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _get_resource_quota_remediation(self) -> str:
        """Get remediation guidance for ResourceQuota."""
        return """
        Create ResourceQuotas for your namespaces:

        ```yaml
        apiVersion: v1
        kind: ResourceQuota
        metadata:
          name: compute-resources
          namespace: my-namespace
        spec:
          hard:
            requests.cpu: "4"
            requests.memory: 8Gi
            limits.cpu: "8"
            limits.memory: 16Gi
            pods: "20"
            services: "10"
            persistentvolumeclaims: "5"
        ```

        Apply with:
        ```
        kubectl apply -f resource-quota.yaml
        ```
        """

    def _check_d5(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if namespaces have LimitRanges configured."""
        try:
            logger.info('Starting namespace limit ranges check')

            # If a specific namespace is provided, only check that namespace
            if namespace:
                # Check if the namespace exists
                try:
                    ns = k8s_api.list_resources(
                        kind='Namespace',
                        api_version='v1',
                        field_selector=f'metadata.name={namespace}',
                    )

                    if not hasattr(ns, 'items') or len(ns.items) == 0:
                        return {
                            'check_id': 'D5',
                            'check_name': 'Namespace LimitRanges',
                            'compliant': False,
                            'impacted_resources': [],
                            'details': f'Namespace {namespace} not found',
                            'remediation': '',
                        }

                    # Check if the namespace has a LimitRange
                    limit_ranges = k8s_api.list_resources(
                        kind='LimitRange', api_version='v1', namespace=namespace
                    )

                    has_limit_range = (
                        hasattr(limit_ranges, 'items') and len(limit_ranges.items) > 0
                    )

                    return {
                        'check_id': 'D5',
                        'check_name': 'Namespace LimitRanges',
                        'compliant': has_limit_range,
                        'impacted_resources': [] if has_limit_range else [namespace],
                        'details': f'Namespace {namespace} {"has" if has_limit_range else "does not have"} LimitRange',
                        'remediation': self._get_limit_range_remediation()
                        if not has_limit_range
                        else '',
                    }
                except Exception as e:
                    logger.error(f'Error checking LimitRange for namespace {namespace}: {str(e)}')
                    return {
                        'check_id': 'D5',
                        'check_name': 'Namespace LimitRanges',
                        'compliant': False,
                        'impacted_resources': [],
                        'details': f'Error checking LimitRange for namespace {namespace}: {str(e)}',
                        'remediation': '',
                    }

            # Check all namespaces
            namespaces = k8s_api.list_resources(kind='Namespace', api_version='v1')

            limit_ranges = k8s_api.list_resources(kind='LimitRange', api_version='v1')

            # Create a set of namespaces that have LimitRanges
            limit_range_ns_set = set()
            for lr in limit_ranges.items:
                lr_dict = lr.to_dict() if hasattr(lr, 'to_dict') else lr
                ns = lr_dict.get('metadata', {}).get('namespace')
                if ns:
                    limit_range_ns_set.add(ns)

            # Check only default namespace and user-created namespaces, excluding system namespaces
            system_namespaces_to_ignore = {'kube-system', 'kube-public', 'kube-node-lease'}
            target_namespaces = []
            missing = []

            for ns in namespaces.items:
                ns_dict = ns.to_dict() if hasattr(ns, 'to_dict') else ns
                ns_name = ns_dict.get('metadata', {}).get('name')

                # Include default namespace and any user-created namespaces
                if ns_name and ns_name not in system_namespaces_to_ignore:
                    target_namespaces.append(ns_name)
                    if ns_name not in limit_range_ns_set:
                        missing.append(ns_name)

            is_compliant = len(missing) == 0

            if len(target_namespaces) == 0:
                detailed_message = "No target namespaces found (this should not happen as 'default' namespace should always exist)"
            elif is_compliant:
                detailed_message = f'All {len(target_namespaces)} target namespaces have LimitRange (including default namespace)'
            else:
                detailed_message = f'Found {len(missing)} of {len(target_namespaces)} target namespaces without LimitRange: {", ".join(missing)}'
            logger.info(f'Namespace limit ranges check completed: {is_compliant}')

            return {
                'check_id': 'D5',
                'check_name': 'Namespace LimitRanges',
                'compliant': is_compliant,
                'impacted_resources': missing,
                'details': detailed_message,
                'remediation': self._get_limit_range_remediation() if not is_compliant else '',
            }

        except Exception as e:
            logger.error(f'Error checking namespace limit ranges: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking namespace limit ranges: {str(e)}'

            return {
                'check_id': 'D5',
                'check_name': 'Namespace LimitRanges',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }

    def _get_limit_range_remediation(self) -> str:
        """Get remediation guidance for LimitRange."""
        return """
        Create LimitRanges for your namespaces:

        ```yaml
        apiVersion: v1
        kind: LimitRange
        metadata:
          name: default-limits
          namespace: my-namespace
        spec:
          limits:
          - default:
              cpu: 500m
              memory: 512Mi
            defaultRequest:
              cpu: 100m
              memory: 128Mi
            max:
              cpu: 2
              memory: 2Gi
            min:
              cpu: 50m
              memory: 64Mi
            type: Container
        ```

        Apply with:
        ```
        kubectl apply -f limit-range.yaml
        ```
        """

    def _check_d7(
        self, k8s_api, cluster_name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check D15: Verify CoreDNS configuration and EKS managed addon status.

        For auto mode clusters (clusters with computeConfig.enabled=true), this check always passes.
        For non-auto mode clusters, this check verifies if CoreDNS is managed by EKS Managed Add-on.
        """
        try:
            logger.info(f'Starting CoreDNS configuration check for cluster: {cluster_name}')

            # Cluster name is now passed as a parameter
            if not cluster_name:
                return {
                    'check_id': 'D7',
                    'check_name': 'CoreDNS Configuration',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': 'No cluster name provided',
                    'remediation': 'Ensure you are connected to a valid EKS cluster.',
                }

            # Create EKS client using AwsHelper
            try:
                eks_client = AwsHelper.create_boto3_client('eks')

                # Get cluster info
                cluster_info = eks_client.describe_cluster(name=cluster_name)
                cluster_info['cluster'].get('version', '')

                # Check if the cluster is an EKS auto mode cluster by checking computeConfig.enabled
                is_auto_mode = False
                compute_config = cluster_info['cluster'].get('computeConfig', {})
                if compute_config and compute_config.get('enabled', False):
                    is_auto_mode = True
                    node_pools = compute_config.get('nodePools', [])
                    logger.info(
                        f'Cluster {cluster_name} is an EKS auto mode cluster with node pools: {", ".join(node_pools)}'
                    )

                # Check if the cluster is using EKS managed addons for CoreDNS
                has_managed_coredns = False
                try:
                    addons = eks_client.list_addons(clusterName=cluster_name)
                    for addon in addons.get('addons', []):
                        if addon.lower() == 'coredns':
                            has_managed_coredns = True
                            logger.info(
                                f'Cluster {cluster_name} is using EKS managed addon for CoreDNS'
                            )
                            break
                except Exception as e:
                    logger.warning(f'Error checking EKS managed addons: {str(e)}')

                # Check for CoreDNS deployment using k8s_api
                coredns_found = False
                coredns_deployment = None
                try:
                    deployments = k8s_api.list_resources(
                        kind='Deployment',
                        api_version='apps/v1',
                        namespace='kube-system',
                        label_selector='k8s-app=kube-dns',
                    )

                    if hasattr(deployments, 'items') and len(deployments.items) > 0:
                        coredns_found = True
                        coredns_deployment = deployments.items[0]
                        logger.info('Found CoreDNS deployment in kube-system namespace')
                except Exception as e:
                    logger.warning(f'Error checking CoreDNS deployment: {str(e)}')

                # Determine compliance based on findings
                details = []

                if not coredns_found:
                    details.append('CoreDNS deployment not found')
                    is_compliant = False
                else:
                    details.append('CoreDNS is deployed')

                    if has_managed_coredns:
                        details.append('Using EKS managed addon for CoreDNS')

                    if is_auto_mode:
                        node_pools = (
                            cluster_info['cluster'].get('computeConfig', {}).get('nodePools', [])
                        )
                        details.append(
                            f'Cluster is running in EKS auto mode with node pools: {", ".join(node_pools)}'
                        )
                        # For auto mode clusters, always pass the check
                        is_compliant = True
                    else:
                        # For non-auto mode clusters, check if CoreDNS is managed by EKS
                        if has_managed_coredns:
                            details.append('CoreDNS is managed by EKS Managed Add-on')
                            is_compliant = True
                        else:
                            details.append('CoreDNS is not managed by EKS Managed Add-on')
                            is_compliant = False

                detailed_message = '; '.join(details)
                logger.info(f'CoreDNS configuration check completed: {is_compliant}')

                # Prepare remediation guidance based on findings
                remediation = ''
                if not is_compliant:
                    if not coredns_found:
                        remediation = f"""
                        CoreDNS is not deployed in your cluster. This is unusual for an EKS cluster.

                        Enable CoreDNS as an EKS managed addon:
                        ```bash
                        aws eks update-addon \\
                          --cluster-name {cluster_name} \\
                          --addon-name coredns \\
                          --resolve-conflicts OVERWRITE
                        ```
                        """
                    elif not is_auto_mode and not has_managed_coredns:
                        remediation = f"""
                        For non-auto mode clusters, it's recommended to use EKS managed addon for CoreDNS.
                        This provides better integration, automatic updates, and improved security.

                        Enable CoreDNS as an EKS managed addon:
                        ```bash
                        aws eks update-addon \\
                          --cluster-name {cluster_name} \\
                          --addon-name coredns \\
                          --resolve-conflicts PRESERVE
                        ```

                        Benefits of using EKS managed addons:
                        - Automatic updates to new versions
                        - Security patches are automatically applied
                        - Simplified management through AWS console or CLI
                        - Better integration with EKS
                        """

                # Prepare impacted resources list
                impacted_resources = []
                if coredns_found and coredns_deployment:
                    coredns_dict = (
                        coredns_deployment.to_dict()
                        if hasattr(coredns_deployment, 'to_dict')
                        else coredns_deployment
                    )
                    metadata = coredns_dict.get('metadata', {})
                    name = metadata.get('name')
                    namespace = metadata.get('namespace', 'kube-system')
                    impacted_resources.append(f'{namespace}/{name}')

                return {
                    'check_id': 'D7',
                    'check_name': 'CoreDNS Configuration',
                    'compliant': is_compliant,
                    'impacted_resources': impacted_resources,
                    'details': detailed_message,
                    'remediation': remediation if not is_compliant else '',
                }
            except Exception as e:
                logger.error(f'Error checking CoreDNS configuration: {str(e)}')
                return {
                    'check_id': 'D7',
                    'check_name': 'CoreDNS Configuration',
                    'compliant': False,
                    'impacted_resources': [],
                    'details': f'Error checking CoreDNS configuration: {str(e)}',
                    'remediation': '',
                }

        except Exception as e:
            logger.error(f'Error checking CoreDNS configuration: {str(e)}')
            import traceback

            logger.error(f'Traceback: {traceback.format_exc()}')

            error_message = f'Error checking CoreDNS configuration: {str(e)}'

            return {
                'check_id': 'D7',
                'check_name': 'CoreDNS Configuration',
                'compliant': False,
                'impacted_resources': [],
                'details': error_message,
                'remediation': '',
            }
