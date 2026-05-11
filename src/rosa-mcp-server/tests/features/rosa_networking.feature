Feature: ROSA Networking (Live API)
  As a network engineer
  I want to verify ingress operations

  Background:
    Given a real OCM client is available
    And a test ROSA cluster exists

  @live @readonly
  Scenario: List ingress controllers
    When I list ingresses for the test cluster
    Then at least 1 ingress should exist
    And the default ingress should have a DNS name
