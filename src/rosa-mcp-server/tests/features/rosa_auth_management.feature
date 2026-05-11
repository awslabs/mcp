Feature: ROSA Authentication Management (Live API)
  As a security administrator
  I want to verify identity provider operations

  Background:
    Given a real OCM client is available
    And a test ROSA cluster exists

  @live @readonly
  Scenario: List identity providers
    When I list identity providers for the test cluster
    Then the response should be a valid IDP list

  @live @write
  Scenario: Create and delete an HTPasswd identity provider
    When I create a test IDP named "bdd-test-idp" of type HTPasswd
    Then the IDP creation should succeed
    And "bdd-test-idp" should appear in the IDP list
    When I delete the test IDP "bdd-test-idp"
    Then "bdd-test-idp" should no longer appear in the IDP list
