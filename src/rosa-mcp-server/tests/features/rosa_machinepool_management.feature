Feature: ROSA Machine Pool Management (Live API)
  As a cluster operator
  I want to verify machine pool operations against a real cluster

  Background:
    Given a real OCM client is available
    And a test ROSA cluster exists

  @live @readonly
  Scenario: List machine/node pools
    When I list pools for the test cluster
    Then at least 1 pool should exist
    And each pool should have an instance type

  @live @write
  Scenario: Create and delete a machine pool
    When I create a test machine pool named "bdd-test-pool" with 2 replicas
    Then the pool creation should succeed
    And the pool should appear in the pool list
    When I delete the test pool "bdd-test-pool"
    Then the pool should no longer exist in the list
