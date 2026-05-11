Feature: ROSA Cluster Management
  As a cloud architect using the ROSA MCP server
  I want to manage ROSA clusters through the MCP interface
  So that I can create, monitor, and maintain OpenShift clusters on AWS

  Background:
    Given the ROSA MCP server is initialized with OCM client
    And write operations are enabled

  Scenario: List all ROSA clusters
    When I request to list all ROSA clusters
    Then the response should contain cluster data
    And the OCM API should be called with product filter "rosa"

  Scenario: List clusters with custom search
    When I request to list clusters with search "state = 'ready'"
    Then the OCM API should be called with search "state = 'ready'"

  Scenario: Describe a specific cluster
    Given a cluster with ID "test-cluster-id" exists
    When I request to describe cluster "test-cluster-id"
    Then the response should contain cluster details
    And the response should include the cluster name
    And the response should include the cluster state

  Scenario: Create a new ROSA cluster with STS
    When I create a cluster with:
      | name          | my-rosa-cluster |
      | region        | us-east-1       |
      | aws_account_id| 123456789012    |
      | multi_az      | true            |
      | compute_nodes | 3               |
    Then the OCM API should receive a create cluster request
    And the request body should have product "rosa"
    And the request body should have multi_az enabled
    And the request body should have 3 compute nodes

  Scenario: Create cluster fails without write permission
    Given write operations are disabled
    When I attempt to create a cluster "test-cluster"
    Then a ValueError should be raised with message containing "allow-write"

  Scenario: Delete a cluster
    When I delete cluster "test-cluster-id"
    Then the OCM API should receive a delete request for "test-cluster-id"
    And the response should indicate deletion initiated

  Scenario: List available ROSA versions
    When I request available ROSA versions
    Then the response should contain version data
    And the OCM API should filter for rosa_enabled versions

  Scenario Outline: List versions by channel group
    When I request versions for channel group "<channel>"
    Then the OCM API should filter for channel_group "<channel>"

    Examples:
      | channel   |
      | stable    |
      | candidate |
      | nightly   |

  Scenario: Get available upgrades for a cluster
    Given a cluster with version "4.14.5" and available upgrades ["4.14.6", "4.14.7"]
    When I request upgrades for the cluster
    Then the response should show current version "4.14.5"
    And the response should list available upgrades

  Scenario: Schedule cluster upgrade
    When I schedule an upgrade to version "4.14.6" for cluster "test-id"
    Then the OCM API should create an upgrade policy
    And the policy should target version "4.14.6"

  Scenario: Get cluster credentials
    When I request credentials for cluster "test-id"
    Then the response should contain kubeconfig data

  Scenario: Get install logs
    When I request install logs for cluster "test-id" with tail 100
    Then the OCM API should request logs with tail parameter
