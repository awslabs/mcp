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

"""ROSA advisor handler providing best-practice recommendations."""

import json
import re
from mcp.server.fastmcp import Context
from mcp.types import TextContent


# Recommended instance types by workload category
INSTANCE_RECOMMENDATIONS = {
    'general': ['m5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge', 'm6i.xlarge', 'm6i.2xlarge'],
    'memory': ['r5.large', 'r5.xlarge', 'r5.2xlarge', 'r5.4xlarge', 'r6i.xlarge'],
    'compute': ['c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'c6i.xlarge'],
    'gpu': ['p3.2xlarge', 'p3.8xlarge', 'g4dn.xlarge', 'g4dn.2xlarge'],
}

# Instance type specifications (vCPUs, memory_gb, hourly_cost_usd)
INSTANCE_SPECS = {
    'm5.large': {'vcpus': 2, 'memory_gb': 8, 'hourly_cost': 0.096},
    'm5.xlarge': {'vcpus': 4, 'memory_gb': 16, 'hourly_cost': 0.192},
    'm5.2xlarge': {'vcpus': 8, 'memory_gb': 32, 'hourly_cost': 0.384},
    'm5.4xlarge': {'vcpus': 16, 'memory_gb': 64, 'hourly_cost': 0.768},
    'm6i.xlarge': {'vcpus': 4, 'memory_gb': 16, 'hourly_cost': 0.192},
    'm6i.2xlarge': {'vcpus': 8, 'memory_gb': 32, 'hourly_cost': 0.384},
    'r5.large': {'vcpus': 2, 'memory_gb': 16, 'hourly_cost': 0.126},
    'r5.xlarge': {'vcpus': 4, 'memory_gb': 32, 'hourly_cost': 0.252},
    'r5.2xlarge': {'vcpus': 8, 'memory_gb': 64, 'hourly_cost': 0.504},
    'r5.4xlarge': {'vcpus': 16, 'memory_gb': 128, 'hourly_cost': 1.008},
    'r6i.xlarge': {'vcpus': 4, 'memory_gb': 32, 'hourly_cost': 0.252},
    'c5.large': {'vcpus': 2, 'memory_gb': 4, 'hourly_cost': 0.085},
    'c5.xlarge': {'vcpus': 4, 'memory_gb': 8, 'hourly_cost': 0.170},
    'c5.2xlarge': {'vcpus': 8, 'memory_gb': 16, 'hourly_cost': 0.340},
    'c5.4xlarge': {'vcpus': 16, 'memory_gb': 32, 'hourly_cost': 0.680},
    'c6i.xlarge': {'vcpus': 4, 'memory_gb': 8, 'hourly_cost': 0.170},
    'p3.2xlarge': {'vcpus': 8, 'memory_gb': 61, 'hourly_cost': 3.06},
    'p3.8xlarge': {'vcpus': 32, 'memory_gb': 244, 'hourly_cost': 12.24},
    'g4dn.xlarge': {'vcpus': 4, 'memory_gb': 16, 'hourly_cost': 0.526},
    'g4dn.2xlarge': {'vcpus': 8, 'memory_gb': 32, 'hourly_cost': 0.752},
}

# Recommended configurations per environment
ENVIRONMENT_CONFIGS = {
    'production': {
        'multi_az': True,
        'replicas': 3,
        'machine_type': 'm5.xlarge',
        'private': True,
        'etcd_encryption': True,
    },
    'staging': {
        'multi_az': True,
        'replicas': 3,
        'machine_type': 'm5.large',
        'private': False,
        'etcd_encryption': False,
    },
    'development': {
        'multi_az': False,
        'replicas': 2,
        'machine_type': 'm5.large',
        'private': False,
        'etcd_encryption': False,
    },
}

# ROSA service cost per hour (approximate)
ROSA_SERVICE_HOURLY_COST = 0.171


class RosaAdvisorHandler:
    """Handler providing ROSA best-practice recommendations and validation."""

    def __init__(self, mcp):
        """Initialize the handler.

        Args:
            mcp: The FastMCP server instance.
        """
        self.mcp = mcp

        self.mcp.tool(name='rosa_recommend_instance_type')(self.rosa_recommend_instance_type)
        self.mcp.tool(name='rosa_validate_cluster_config')(self.rosa_validate_cluster_config)
        self.mcp.tool(name='rosa_recommend_cluster_config')(self.rosa_recommend_cluster_config)
        self.mcp.tool(name='rosa_estimate_cluster_cost')(self.rosa_estimate_cluster_cost)

    async def rosa_recommend_instance_type(
        self,
        ctx: Context,
        workload_type: str = 'general',
        vcpus: int = 4,
        memory_gb: int = 16,
    ) -> list[TextContent]:
        """Recommend an EC2 instance type for ROSA worker nodes.

        Args:
            ctx: MCP context.
            workload_type: Workload category (general, memory, compute, gpu).
            vcpus: Minimum required vCPUs.
            memory_gb: Minimum required memory in GB.
        """
        if workload_type not in INSTANCE_RECOMMENDATIONS:
            raise ValueError(
                f"Invalid workload_type '{workload_type}'. "
                f"Must be one of: {', '.join(INSTANCE_RECOMMENDATIONS.keys())}"
            )

        candidates = INSTANCE_RECOMMENDATIONS[workload_type]
        recommended = []

        for instance_type in candidates:
            specs = INSTANCE_SPECS.get(instance_type)
            if specs and specs['vcpus'] >= vcpus and specs['memory_gb'] >= memory_gb:
                recommended.append({
                    'instance_type': instance_type,
                    'vcpus': specs['vcpus'],
                    'memory_gb': specs['memory_gb'],
                    'hourly_cost_usd': specs['hourly_cost'],
                })

        if not recommended:
            # Fall back to largest in category
            fallback = candidates[-1]
            specs = INSTANCE_SPECS[fallback]
            recommended.append({
                'instance_type': fallback,
                'vcpus': specs['vcpus'],
                'memory_gb': specs['memory_gb'],
                'hourly_cost_usd': specs['hourly_cost'],
                'note': 'Largest available in category; may not meet all requirements.',
            })

        result = {
            'workload_type': workload_type,
            'requested': {'vcpus': vcpus, 'memory_gb': memory_gb},
            'recommendations': recommended,
        }

        return [TextContent(type='text', text=json.dumps(result, indent=2))]

    async def rosa_validate_cluster_config(
        self,
        ctx: Context,
        cluster_name: str,
        multi_az: bool,
        replicas: int,
        machine_type: str,
        version: str,
    ) -> list[TextContent]:
        """Validate a cluster configuration against ROSA best practices.

        Args:
            ctx: MCP context.
            cluster_name: Proposed cluster name.
            multi_az: Whether multi-AZ is enabled.
            replicas: Number of worker replicas.
            machine_type: EC2 instance type for workers.
            version: OpenShift version (X.Y.Z format).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate cluster name: 2-54 chars, lowercase alphanumeric + hyphens,
        # no leading/trailing hyphen
        if len(cluster_name) < 2 or len(cluster_name) > 54:
            errors.append(
                f"Cluster name must be 2-54 characters, got {len(cluster_name)}."
            )
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', cluster_name) and len(cluster_name) >= 2:
            errors.append(
                "Cluster name must be lowercase alphanumeric with hyphens, "
                "no leading/trailing hyphen."
            )
        elif len(cluster_name) == 1 and not re.match(r'^[a-z0-9]$', cluster_name):
            errors.append(
                "Single-character cluster name must be lowercase alphanumeric."
            )

        # Validate multi_az + replicas
        if multi_az and replicas % 3 != 0:
            errors.append(
                f"With multi_az enabled, replicas must be a multiple of 3, got {replicas}."
            )

        # Minimum replicas for production
        if replicas < 2:
            warnings.append(
                f"Replicas count of {replicas} is below the recommended minimum of 2 for production."
            )

        # Validate version format
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            errors.append(
                f"Version must be in X.Y.Z format, got '{version}'."
            )

        # Validate machine type
        if machine_type not in INSTANCE_SPECS:
            warnings.append(
                f"Machine type '{machine_type}' is not in the known recommendations list. "
                "Ensure it is supported for ROSA."
            )

        result = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'config': {
                'cluster_name': cluster_name,
                'multi_az': multi_az,
                'replicas': replicas,
                'machine_type': machine_type,
                'version': version,
            },
        }

        return [TextContent(type='text', text=json.dumps(result, indent=2))]

    async def rosa_recommend_cluster_config(
        self,
        ctx: Context,
        environment: str = 'production',
    ) -> list[TextContent]:
        """Get recommended cluster configuration for an environment.

        Args:
            ctx: MCP context.
            environment: Target environment (production, staging, development).
        """
        if environment not in ENVIRONMENT_CONFIGS:
            raise ValueError(
                f"Invalid environment '{environment}'. "
                f"Must be one of: {', '.join(ENVIRONMENT_CONFIGS.keys())}"
            )

        config = ENVIRONMENT_CONFIGS[environment]
        machine_specs = INSTANCE_SPECS.get(config['machine_type'], {})

        result = {
            'environment': environment,
            'recommended_config': config,
            'machine_specs': machine_specs,
            'notes': [],
        }

        if environment == 'production':
            result['notes'] = [
                'Multi-AZ provides high availability across failure domains.',
                'Private cluster recommended for production workloads.',
                'etcd encryption protects secrets at rest.',
                'Consider enabling delete protection after creation.',
                'Minimum 3 replicas for HA; scale based on workload.',
            ]
        elif environment == 'staging':
            result['notes'] = [
                'Multi-AZ for staging mirrors production topology.',
                'Public API can be acceptable for staging.',
                'Consider same machine type as production for accurate testing.',
            ]
        else:
            result['notes'] = [
                'Single-AZ reduces costs for development.',
                'Minimum 2 replicas for basic workload scheduling.',
                'Use smaller instance types to save costs.',
            ]

        return [TextContent(type='text', text=json.dumps(result, indent=2))]

    async def rosa_estimate_cluster_cost(
        self,
        ctx: Context,
        machine_type: str,
        replicas: int,
        multi_az: bool = False,
        region: str = 'us-east-1',
    ) -> list[TextContent]:
        """Estimate monthly cluster cost based on EC2 on-demand pricing.

        Args:
            ctx: MCP context.
            machine_type: EC2 instance type for worker nodes.
            replicas: Number of worker replicas.
            multi_az: Whether multi-AZ is enabled.
            region: AWS region (used for reference; pricing is approximate).
        """
        specs = INSTANCE_SPECS.get(machine_type)
        if not specs:
            raise ValueError(
                f"Unknown machine type '{machine_type}'. "
                f"Known types: {', '.join(sorted(INSTANCE_SPECS.keys()))}"
            )

        hours_per_month = 730  # Average hours in a month

        # Worker node costs
        worker_hourly = specs['hourly_cost'] * replicas
        worker_monthly = worker_hourly * hours_per_month

        # ROSA service fee
        rosa_service_monthly = ROSA_SERVICE_HOURLY_COST * hours_per_month

        # Control plane costs (included in ROSA service fee for HCP;
        # for Classic, 3 control plane nodes are managed)
        # We include a rough estimate for Classic control plane
        control_plane_monthly = 0.0

        total_monthly = worker_monthly + rosa_service_monthly + control_plane_monthly

        result = {
            'estimate': {
                'machine_type': machine_type,
                'replicas': replicas,
                'multi_az': multi_az,
                'region': region,
            },
            'costs': {
                'worker_nodes': {
                    'hourly_per_node': specs['hourly_cost'],
                    'hourly_total': round(worker_hourly, 3),
                    'monthly_total': round(worker_monthly, 2),
                },
                'rosa_service_fee': {
                    'hourly': ROSA_SERVICE_HOURLY_COST,
                    'monthly': round(rosa_service_monthly, 2),
                },
                'estimated_monthly_total': round(total_monthly, 2),
            },
            'notes': [
                'Estimates are based on on-demand EC2 pricing for us-east-1.',
                'Actual costs may vary by region and with reserved/spot pricing.',
                'Does not include data transfer, EBS, or load balancer costs.',
                'ROSA service fee covers cluster management overhead.',
            ],
        }

        return [TextContent(type='text', text=json.dumps(result, indent=2))]
