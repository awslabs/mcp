Feature: ROSA Advisor and Recommendations
  As a cloud architect
  I want to get best-practice recommendations
  So that I can make informed decisions about cluster configuration

  Background:
    Given the ROSA advisor is initialized

  Scenario Outline: Recommend instance type by workload
    When I request instance recommendation for "<workload>" workload with <vcpus> vCPUs and <memory>GB memory
    Then the recommendation should be from the "<family>" family

    Examples:
      | workload | vcpus | memory | family |
      | general  | 4     | 16     | m5     |
      | memory   | 4     | 32     | r5     |
      | compute  | 8     | 16     | c5     |
      | gpu      | 8     | 64     | p3     |

  Scenario: Validate valid cluster configuration
    When I validate cluster config:
      | cluster_name | my-prod-cluster |
      | multi_az     | true            |
      | replicas     | 3               |
      | machine_type | m5.xlarge       |
      | version      | 4.14.5          |
    Then the validation should pass
    And there should be no errors

  Scenario: Validate catches invalid cluster name
    When I validate cluster config with name "MY-INVALID-CLUSTER-NAME-THAT-IS-WAY-TOO-LONG-FOR-ROSA-CLUSTERS-REALLY"
    Then the validation should fail
    And the error should mention "cluster name"

  Scenario: Validate catches multi-AZ replica mismatch
    When I validate cluster config:
      | cluster_name | my-cluster |
      | multi_az     | true       |
      | replicas     | 4          |
      | machine_type | m5.xlarge  |
      | version      | 4.14.5     |
    Then the validation should fail
    And the error should mention "multiple of 3"

  Scenario: Validate catches uppercase in name
    When I validate cluster config with name "My-Cluster"
    Then the validation should fail
    And the error should mention "lowercase"

  Scenario: Validate catches bad version format
    When I validate cluster config:
      | cluster_name | my-cluster |
      | multi_az     | false      |
      | replicas     | 2          |
      | machine_type | m5.xlarge  |
      | version      | 4.14       |
    Then the validation should fail
    And the error should mention "version"

  Scenario Outline: Recommend cluster config by environment
    When I request recommended config for "<environment>"
    Then the config should have multi_az <multi_az>
    And the config should have replicas <replicas>

    Examples:
      | environment | multi_az | replicas |
      | production  | true     | 3        |
      | staging     | true     | 3        |
      | development | false    | 2        |

  Scenario: Estimate cluster cost
    When I estimate cost for 3 m5.xlarge nodes in us-east-1
    Then the estimate should include monthly cost
    And the estimate should include per-node cost
    And the monthly cost should be greater than 0
