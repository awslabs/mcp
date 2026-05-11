Feature: ROSA Operators (Live API)
  As a cluster operator
  I want to manage operators and verify their status

  Background:
    Given a real OCM client is available
    And a test ROSA cluster exists

  @live @readonly
  Scenario: List STS operator roles
    When I list STS operator roles for the test cluster
    Then at least 4 operator roles should exist
    And each role should have a name and role_arn

  @live @readonly
  Scenario: Get cluster operators health
    When I get cluster operators status
    Then at least 10 operators should be listed
    And all critical operators should be available

  @live @readonly
  Scenario: List STS credential requests
    When I list STS credential requests
    Then at least 4 credential requests should exist

  @live @readonly
  Scenario: List STS policies
    When I list STS policies
    Then at least 20 policies should exist
    And policies should include operator role types
