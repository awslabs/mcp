Feature: ROSA Advanced Operations (Live API)

  Background:
    Given a real OCM client is available
    And a test ROSA cluster exists

  @live @readonly
  Scenario: Get cluster metrics - alerts
    When I query alerts metrics for the test cluster
    Then the response should be valid metrics data

  @live @readonly
  Scenario: Get cluster metrics - cluster operators
    When I query cluster_operators metrics for the test cluster
    Then the response should be valid metrics data

  @live @readonly
  Scenario: Check delete protection
    When I check delete protection for the test cluster
    Then the response should indicate protection status

  @live @readonly
  Scenario: List available add-ons
    When I list available add-ons
    Then at least 1 add-on should be available
    And each add-on should have a name and id
