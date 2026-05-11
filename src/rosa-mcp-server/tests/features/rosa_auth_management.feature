Feature: ROSA Authentication Management
  As a security administrator
  I want to manage identity providers and cluster access
  So that users can authenticate securely

  Background:
    Given the ROSA MCP server is initialized with OCM client
    And write operations are enabled

  Scenario: Show current identity (whoami)
    Given the OCM access token contains user info
    When I request whoami
    Then the response should contain the username
    And the response should contain the email

  Scenario: List identity providers
    Given a cluster with HTPasswd and GitHub IDPs configured
    When I list identity providers for the cluster
    Then the response should list both IDPs

  Scenario: Create HTPasswd identity provider
    When I create an IDP with:
      | cluster_id    | test-id          |
      | name          | local-users      |
      | idp_type      | htpasswd         |
    Then the OCM API should create the IDP
    And the IDP type should be "HTPasswdIdentityProvider"

  Scenario: Create GitHub identity provider
    When I create an IDP with:
      | cluster_id    | test-id                  |
      | name          | github-org               |
      | idp_type      | github                   |
    Then the OCM API should create the IDP
    And the IDP type should be "GithubIdentityProvider"

  Scenario: Delete identity provider
    When I delete IDP "idp-123" from cluster "test-id"
    Then the OCM API should delete the IDP

  Scenario: Create cluster admin
    When I create an admin for cluster "test-id"
    Then the response should contain a generated password
    And an HTPasswd IDP named "cluster-admin" should be created

  Scenario: Create IDP fails without write permission
    Given write operations are disabled
    When I attempt to create an IDP
    Then a ValueError should be raised
