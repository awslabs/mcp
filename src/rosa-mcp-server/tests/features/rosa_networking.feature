Feature: ROSA Networking Management
  As a network engineer
  I want to manage ingress controllers
  So that I can control traffic routing

  Background:
    Given the ROSA MCP server is initialized with OCM client
    And write operations are enabled

  Scenario: List ingress controllers
    When I list ingresses for cluster "test-id"
    Then the response should contain ingress data

  Scenario: Create NLB ingress
    When I create an ingress with:
      | cluster_id | test-id |
      | lb_type    | nlb     |
      | private    | false   |
    Then the ingress should use NLB load balancer type

  Scenario: Create private ingress with route selectors
    When I create a private ingress with route selectors {"environment": "internal"}
    Then the ingress should be private
    And the ingress should have route selectors

  Scenario: Update ingress
    When I update ingress "ing-123" on cluster "test-id" to private
    Then the OCM API should patch the ingress

  Scenario: Delete ingress
    When I delete ingress "ing-123" from cluster "test-id"
    Then the OCM API should delete the ingress
