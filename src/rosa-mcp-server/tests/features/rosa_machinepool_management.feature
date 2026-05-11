Feature: ROSA Machine Pool Management
  As a cluster operator
  I want to manage machine pools and node pools
  So that I can scale and configure worker nodes

  Background:
    Given the ROSA MCP server is initialized with OCM client
    And write operations are enabled

  Scenario: List machine pools for a Classic cluster
    Given a Classic ROSA cluster with ID "classic-id"
    When I list machine pools for cluster "classic-id"
    Then the OCM API should call machine_pools endpoint
    And the response should contain pool data

  Scenario: List node pools for an HCP cluster
    Given an HCP ROSA cluster with ID "hcp-id"
    When I list machine pools for cluster "hcp-id"
    Then the OCM API should call node_pools endpoint

  Scenario: Create machine pool with fixed replicas
    When I create a machine pool with:
      | cluster_id    | test-id     |
      | name          | gpu-workers |
      | instance_type | p3.2xlarge  |
      | replicas      | 3           |
    Then the pool should be created with 3 replicas
    And the instance type should be "p3.2xlarge"

  Scenario: Create machine pool with autoscaling
    When I create a machine pool with:
      | cluster_id    | test-id       |
      | name          | auto-workers  |
      | instance_type | m5.xlarge     |
      | min_replicas  | 2             |
      | max_replicas  | 10            |
    Then the pool should have autoscaling configured
    And min replicas should be 2
    And max replicas should be 10

  Scenario: Create machine pool with spot instances
    When I create a machine pool with spot_max_price 0.5
    Then the pool should have spot market options configured

  Scenario: Create machine pool with labels and taints
    When I create a machine pool with:
      | cluster_id    | test-id      |
      | name          | dedicated    |
      | instance_type | m5.xlarge    |
    And labels {"workload": "ml", "team": "data-science"}
    And taints [{"key": "dedicated", "value": "ml", "effect": "NoSchedule"}]
    Then the pool should have the labels set
    And the pool should have the taints set

  Scenario: Create machine pool on HCP cluster uses node_pools
    Given an HCP ROSA cluster with ID "hcp-id"
    When I create a machine pool on cluster "hcp-id"
    Then the OCM API should use the node_pools endpoint

  Scenario: Update machine pool replicas
    When I update machine pool "workers" on cluster "test-id" with replicas 5
    Then the OCM API should patch with replicas 5

  Scenario: Delete machine pool
    When I delete machine pool "gpu-workers" from cluster "test-id"
    Then the OCM API should delete the pool
    And the response should confirm deletion
