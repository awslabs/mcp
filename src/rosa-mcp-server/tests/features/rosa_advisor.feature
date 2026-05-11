Feature: ROSA Advisor (No API needed)
  The advisor provides recommendations based on logic, no live API required.

  @advisor
  Scenario Outline: Recommend instance type by workload
    When I request instance recommendation for "<workload>" with <vcpus> vCPUs and <memory>GB
    Then the recommendation should include an instance from the "<family>" family

    Examples:
      | workload | vcpus | memory | family |
      | general  | 4     | 16     | m5     |
      | memory   | 4     | 32     | r5     |
      | compute  | 8     | 16     | c5     |
      | gpu      | 8     | 64     | p3     |

  @advisor
  Scenario: Validate valid cluster configuration
    When I validate config name="my-cluster" multi_az=false replicas=2 type="m5.xlarge" version="4.14.5"
    Then the validation should pass with no errors

  @advisor
  Scenario: Validate catches invalid name
    When I validate config name="MY-BAD!" multi_az=false replicas=2 type="m5.xlarge" version="4.14.5"
    Then the validation should fail

  @advisor
  Scenario: Validate catches multi-AZ mismatch
    When I validate config name="my-cluster" multi_az=true replicas=4 type="m5.xlarge" version="4.14.5"
    Then the validation should fail with "multiple of 3"

  @advisor
  Scenario Outline: Recommend config by environment
    When I request recommended config for "<env>"
    Then the config should recommend <replicas> replicas

    Examples:
      | env         | replicas |
      | production  | 3        |
      | staging     | 3        |
      | development | 2        |

  @advisor
  Scenario: Estimate cluster cost
    When I estimate cost for 3 nodes of type "m5.xlarge"
    Then the monthly estimate should be greater than 0
