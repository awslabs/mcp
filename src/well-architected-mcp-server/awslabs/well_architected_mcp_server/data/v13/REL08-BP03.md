---
id: "REL08-BP03"
title: "Integrate resiliency testing as part of your deployment"
framework: "WAF"
domain: "Reliability"
capability: "How do you implement change?"
risk_level: "Medium"
---

# REL08-BP03 Integrate resiliency testing as part of your deployment

## Anti-Patterns
- Lack of observability and monitoring in deployment processes
- Reliance on humans to resolve system failures
- Poor quality analysis mechanisms
- Focus on known issues in a system and a lack of experimentation to identify any unknowns
- Identification of failures, but no resolution
- No documentation of findings and runbooks

## Implementation Guidance
 The most common resiliency testing forms that can be integrated in your system's deployments are disaster recovery and chaos engineering.
- Include updates to your disaster recovery plans and standard operating procedures (SOPs) with any significant deployment.
- Integrate reliability testing into your automated deployment pipelines. Services such as[AWS Resilience Hub](https://aws.amazon.com/resilience-hub/)can be [integrated into your CI/CD pipeline](https://aws.amazon.com/blogs/architecture/continually-assessing-application-resilience-with-aws-resilience-hub-and-aws-codepipeline/) to establish continuous resilience assessments that are automatically evaluated as part of every deployment.
- Define your applications in AWS Resilience Hub. Resilience assessments generate code snippets that help you create recovery procedures as AWS Systems Manager documents for your applications and provide a list of recommended Amazon CloudWatch monitors and alarms.
- Once your DR plans and SOPs are updated, complete disaster recovery testing to verify that they are effective. Disaster recovery testing helps you determine if you can restore your system after an event and return to normal operations. You can simulate various disaster recovery strategies and identify whether your planning is sufficient to meet your uptime requirements. Common disaster recovery strategies include backup and restore, pilot light, cold standby, warm standby, hot standby, and active-active, and they all differ in cost and complexity. Before disaster recovery testing, we recommend that you define your recovery time objective (RTO) and recovery point objective (RPO) to simplify the choice of strategy to simulate. AWS offers disaster recovery tools like [AWS Elastic Disaster Recovery](https://aws.amazon.com/disaster-recovery/) to help you get started with your planning and testing.
- Chaos engineering experiments introduce disruptions to the system, such as network outages and service failures. By simulating with controlled failures, you can discover your system's vulnerabilities while containing the impacts of the injected failures. Just like the other strategies, run controlled failure simulations in non-production environments using services like [AWS Fault Injection Service](https://aws.amazon.com/fis/) to gain confidence before deploying in production.

## Resources
### Related Documents
- [Experiment with failure using resilience testing to build recovery preparedness](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/qa.nt.6-experiment-with-failure-using-resilience-testing-to-build-recovery-preparedness.html)
- [Continually assessing application resilience with AWS Resilience Hub and AWS CodePipeline](https://aws.amazon.com/blogs/architecture/continually-assessing-application-resilience-with-aws-resilience-hub-and-aws-codepipeline/)
- [Disaster recovery (DR) architecture on AWS, part 1: Strategies for recovery in the cloud](https://aws.amazon.com/blogs/architecture/disaster-recovery-dr-architecture-on-aws-part-i-strategies-for-recovery-in-the-cloud/)
- [Verify the resilience of your workloads using Chaos Engineering](https://aws.amazon.com/blogs/architecture/verify-the-resilience-of-your-workloads-using-chaos-engineering/)
- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Chaos Engineering Workshop](https://disaster-recovery.workshop.aws/en/intro/concepts/chaos-engineering.html)
### Related Videos
- [AWS re:Invent 2020: Testing Resilience using Chaos Engineering](https://www.youtube.com/watch?v=OlobVYPkxgg)
- [Improve Application Resilience with AWS Fault Injection Service](https://www.youtube.com/watch?v=N0aZZVVZiUw)
- [Prepare & Protect Your Applications From Disruption With AWS Resilience Hub](https://www.youtube.com/watch?v=xa4BVl4N1Gw)
