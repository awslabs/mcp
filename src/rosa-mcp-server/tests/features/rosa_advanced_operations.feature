Feature: ROSA Advanced Operations
  As a cluster operator
  I want to perform advanced cluster operations
  So that I can manage lifecycle and troubleshoot issues

  Background:
    Given the ROSA MCP server is initialized with OCM client
    And write operations are enabled

  Scenario: Hibernate a Classic cluster
    When I hibernate cluster "classic-id"
    Then the OCM API should POST to hibernate endpoint
    And the response should confirm hibernation initiated

  Scenario: Resume a hibernated cluster
    When I resume cluster "classic-id"
    Then the OCM API should POST to resume endpoint

  Scenario: Get cluster status
    When I get status for cluster "test-id"
    Then the response should contain state information
    And the response should contain DNS readiness

  Scenario Outline: Get cluster metrics
    When I get "<metric>" metrics for cluster "test-id"
    Then the OCM API should query metric_queries/<metric>

    Examples:
      | metric            |
      | alerts            |
      | cluster_operators |
      | nodes             |

  Scenario: Get cluster metrics rejects invalid metric
    When I request metric "invalid_metric" for cluster "test-id"
    Then a ValueError should be raised

  Scenario: List break-glass credentials (HCP)
    When I list break-glass credentials for cluster "hcp-id"
    Then the response should contain credentials list

  Scenario: Create break-glass credential
    When I create a break-glass credential for cluster "hcp-id"
    Then the OCM API should create the credential

  Scenario: Get delete protection status
    When I check delete protection for cluster "test-id"
    Then the response should show protection status

  Scenario: Enable delete protection
    When I enable delete protection for cluster "test-id"
    Then the OCM API should update delete protection to enabled

  Scenario: List available machine types
    When I list available machine types
    Then the response should contain instance types
