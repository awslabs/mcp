Feature: ROSA Cluster Management (Live API)
  As a cloud architect using the ROSA MCP server
  I want to verify cluster operations work against the real OCM API

  Background:
    Given a real OCM client is available
    And a test ROSA cluster exists

  @live @readonly
  Scenario: List all ROSA clusters
    When I list all ROSA clusters via OCM API
    Then the response should contain at least 1 cluster
    And each cluster should have an id and name

  @live @readonly
  Scenario: Describe the test cluster
    When I describe the test cluster
    Then the response should contain the cluster name
    And the cluster state should be "ready"
    And the cluster should have a version
    And the cluster should have a region
    And the cluster should have a console URL

  @live @readonly
  Scenario: List available ROSA versions
    When I list available ROSA versions
    Then at least 10 versions should be available
    And all versions should be ROSA-enabled

  @live @readonly
  Scenario: List available upgrades for the test cluster
    When I check available upgrades for the test cluster
    Then the response should include the current version

  @live @readonly
  Scenario: Get cluster status
    When I get the test cluster status
    Then the status should show state "ready"
    And DNS should be ready

  @live @readonly
  Scenario: Get cluster credentials
    When I get credentials for the test cluster
    Then the response should contain a kubeconfig

  @live @readonly
  Scenario: List machine types
    When I list available machine types
    Then at least 50 machine types should be available
    And m5.xlarge should be in the list
