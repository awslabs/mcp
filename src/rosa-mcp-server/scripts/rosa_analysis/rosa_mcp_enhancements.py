```json
{
  "tool_functions": [
    {
      "name": "validate_cluster_config",
      "description": "Validate cluster configuration based on best practices",
      "code": "def validate_cluster_config(config: dict) -> list:\n    \"\"\"Validate cluster configuration against best practices.\n\n    Args:\n        config (dict): Cluster configuration dictionary.\n\n    Returns:\n        list: List of validation errors.\n    \"\"\"\n    errors = []\n\n    # Validate worker node count\n    worker_count = config.get('worker_nodes', {}).get('nodeCount', 0)\n    if worker_count < WORKER_NODE_MIN_COUNT:\n        errors.append(f'Worker node count ({worker_count}) is below the recommended minimum ({WORKER_NODE_MIN_COUNT}).')\n\n    # Validate control plane node count\n    control_plane_count = config.get('control_plane', {}).get('nodeCount', 0)\n    if control_plane_count < CONTROL_PLANE_MIN_COUNT:\n        errors.append(f'Control plane node count ({control_plane_count}) is below the recommended minimum ({CONTROL_PLANE_MIN_COUNT}).')\n\n    # Add more validation rules as needed\n\n    return errors"
    },
    {
      "name": "apply_dry_run",
      "description": "Perform a dry-run operation before applying changes",
      "code": "def apply_dry_run(operation: Callable, *args, **kwargs) -> None:\n    \"\"\"Perform a dry-run operation before applying changes.\n\n    Args:\n        operation (Callable): The operation to be performed.\n        *args: Positional arguments for the operation.\n        **kwargs: Keyword arguments for the operation.\n    \"\"\"\n    print('Performing dry-run...')\n    operation(*args, dry_run=True, **kwargs)\n    print('Dry-run completed successfully. Review the changes and proceed with caution.')"
    }
  ],
  "function_enhancements": [
    {
      "name": "create_cluster",
      "enhancement": "Add validation for cluster configuration and network settings"
    },
    {
      "name": "upgrade_cluster",
      "enhancement": "Implement backup and recovery strategies before upgrading"
    },
    {
      "name": "delete_cluster",
      "enhancement": "Add dry-run option and confirmation prompt"
    }
  ],
  "validation_rules": [
    {
      "name": "validate_network_config",
      "description": "Validate network configuration based on recommendations",
      "code": "def validate_network_config(config: dict) -> list:\n    \"\"\"Validate network configuration against recommendations.\n\n    Args:\n        config (dict): Network configuration dictionary.\n\n    Returns:\n        list: List of validation errors.\n    \"\"\"\n    errors = []\n\n    # Validate CIDR ranges\n    machine_cidr = config.get('machine_cidr')\n    service_cidr = config.get('service_cidr')\n    if not is_valid_cidr(machine_cidr):\n        errors.append(f'Invalid machine CIDR range: {machine_cidr}')\n    if not is_valid_cidr(service_cidr):\n        errors.append(f'Invalid service CIDR range: {service_cidr}')\n\n    # Validate host prefix\n    host_prefix = config.get('host_prefix')\n    if not (1 <= host_prefix <= 32):\n        errors.append(f'Invalid host prefix: {host_prefix}. Must be between 1 and 32.')\n\n    # Add more validation rules as needed\n\n    return errors"
    }
  ],
  "helper_functions": [
    {
      "name": "perform_cluster_upgrade",
      "description": "Helper function to perform a cluster upgrade",
      "code": "def perform_cluster_upgrade(cluster_name: str, target_version: str) -> None:\n    \"\"\"Perform a cluster upgrade to the specified target version.\n\n    Args:\n        cluster_name (str): Name of the cluster to upgrade.\n        target_version (str): Target OpenShift version for the upgrade.\n    \"\"\"\n    cluster = get_cluster(cluster_name)\n    current_version = cluster.version\n\n    if current_version == target_version:\n        print(f'Cluster {cluster_name} is already at version {target_version}.')\n        return\n\n    print(f'Backing up cluster {cluster_name} before upgrade...')\n    backup_cluster(cluster_name)\n\n    print(f'Upgrading cluster {cluster_name} from {current_version} to {target_version}...')\n    upgrade_cluster(cluster_name, target_version)\n\n    print(f'Upgrade completed. Verifying cluster health...')\n    verify_cluster_health(cluster_name)\n\n    print(f'Upgrading monitoring and logging components...')\n    upgrade_monitoring_components(cluster_name)\n\n    print(f'Cluster {cluster_name} has been successfully upgraded to version {target_version}.')"
    }
  ],
  "constants": [
    {
      "name": "WORKER_NODE_MIN_COUNT",
      "value": 3,
      "description": "Minimum recommended number of worker nodes"
    },
    {
      "name": "WORKER_NODE_RECOMMENDED_COUNT",
      "value": 6,
      "description": "Recommended number of worker nodes"
    },
    {
      "name": "CONTROL_PLANE_MIN_COUNT",
      "value": 3,
      "description": "Minimum recommended number of control plane nodes"
    },
    {
      "name": "CONTROL_PLANE_RECOMMENDED_COUNT",
      "value": 3,
      "description": "Recommended number of control plane nodes"
    },
    {
      "name": "RECOMMENDED_INSTANCE_TYPES",
      "value": ["m5.xlarge", "m5.2xlarge", "m5.4xlarge"],
      "description": "Recommended instance types for worker nodes"
    }
  ]
}
```