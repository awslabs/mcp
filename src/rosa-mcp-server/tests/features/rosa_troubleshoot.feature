Feature: ROSA Troubleshooting (Live + Logic)

  @advisor
  Scenario: Search troubleshoot guide for pod issues
    When I search the troubleshoot guide for "pod stuck pending"
    Then at least 1 result should be returned
    And the result should mention "Pending"

  @advisor
  Scenario: Search troubleshoot guide for network issues
    When I search the troubleshoot guide for "connection timeout dns"
    Then at least 1 result should be returned

  @advisor
  Scenario: Get metrics guidance
    When I request metrics guidance
    Then the response should include ContainerInsights metrics
    And the response should include recommended alarms
