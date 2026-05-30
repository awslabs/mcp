---
id: "REL07-BP04"
title: "Load test your workload"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload to adapt to changes in demand?"
risk_level: "Medium"
---

# REL07-BP04 Load test your workload

## Anti-Patterns
- Performing load testing on deployments that are not the same configuration as your production.
- Performing load testing only on individual pieces of your workload, and not on the entire workload.
- Performing load testing with a subset of requests and not a representative set of actual requests.
- Performing load testing to a small safety factor above expected load.

## Implementation Guidance
- Perform load testing to identify which aspect of your workload indicates that you must add or remove capacity. Load testing should have representative traffic similar to what you receive in production. Increase the load while watching the metrics you have instrumented to determine which metric indicates when you must add or remove resources.
  - [Distributed Load Testing on AWS: simulate thousands of connected users](https://aws.amazon.com/solutions/distributed-load-testing-on-aws/)
    - Identify the mix of requests. You may have varied mixes of requests, so you should look at various time frames when identifying the mix of traffic.
    - Implement a load driver. You can use custom code, open source, or commercial software to implement a load driver.
    - Load test initially using small capacity. You see some immediate effects by driving load onto a lesser capacity, possibly as small as one instance or container.
    - Load test against larger capacity. The effects will be different on a distributed load, so you must test against as close to a product environment as possible.

## Resources
### Related Documents
- [Distributed Load Testing on AWS: simulate thousands of connected users](https://aws.amazon.com/solutions/distributed-load-testing-on-aws/)
- [Load testing applications](https://docs.aws.amazon.com/prescriptive-guidance/latest/load-testing/welcome.html)
### Related Videos
- [AWS Summit ANZ 2023: Accelerate with confidence through AWS Distributed Load Testing](https://www.youtube.com/watch?v=4J6lVqa6Yh8)
