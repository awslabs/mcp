---
id: "PERF01-BP07"
title: "Use a data-driven approach for architectural choices"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select appropriate cloud resources and architecture for your workload?"
risk_level: "Medium"
---

# PERF01-BP07 Use a data-driven approach for architectural choices

## Anti-Patterns
- You assume your current architecture is static and should not be updated over time.
- Your architectural choices are based upon guesses and assumptions.
- You introduce architecture changes over time without justification.

## Implementation Guidance
 Use internal experience and knowledge of the cloud or external resources such as published use cases or whitepapers to choose resources and services in your architecture. You should have a well-defined process that encourages experimentation and benchmarking with the services that could be used in your workload.

 Backlogs for critical workloads should consist of not just user stories which deliver functionality relevant to business and users, but also technical stories which form an architecture runway for the workload. This runway is informed by new advancements in technology and new services and adopts them based on data and proper justification. This verifies that the architecture remains future-proof and does not stagnate.

## Implementation Steps
- Engage with key stakeholders to define workload requirements, including performance, availability, and cost considerations. Consider factors such as the number of users and usage pattern for your workload.
- Create an architecture runway or a technology backlog which is prioritized along with the functional backlog.
- Evaluate and assess different cloud services (for more detail, see [PERF01-BP01 Learn about and understand available cloud services and features](perf_architecture_understand_cloud_services_and_features.md)).
- Explore different architectural patterns, like microservices or serverless, that meet your performance requirements (for more detail, see [PERF01-BP02 Use guidance from your cloud provider or an appropriate partner to learn about architecture patterns and best practices](perf_architecture_guidance_architecture_patterns_best_practices.md)).
- Consult other teams, architecture diagrams, and resources, such as AWS Solution Architects, [AWS Architecture Center](https://aws.amazon.com/architecture/), and [AWS Partner Network](https://aws.amazon.com/partners/), to help you choose the right architecture for your workload.
- Define performance metrics like throughput and response time that can help you evaluate the performance of your workload.
- Experiment and use defined metrics to validate the performance of the selected architecture.
- Continually monitor and make adjustments as needed to maintain the optimal performance of your architecture.
- Document your selected architecture and decisions as a reference for future updates and learnings.
- Continually review and update the architecture selection approach based on learnings, new technologies, and metrics that indicate a needed change or problem in the current approach.

## Resources
### Related Documents
- [AWS Solutions Library](https://aws.amazon.com/solutions/)
- [AWS Knowledge Center](https://aws.amazon.com/premiumsupport/knowledge-center/)
- [ Architectural Patterns to Build End-to-End Data Driven Applications on AWS](https://docs.aws.amazon.com/whitepapers/latest/build-e2e-data-driven-applications/build-e2e-data-driven-applications.html)
### Related Videos
- [This is my Architecture](https://aws.amazon.com/architecture/this-is-my-architecture/)
- [AWS re:Invent 2021 - Data-driven enterprise: Going from vision to value ](https://www.youtube.com/watch?v=_D0PF2N2AfA)
- [AWS re:Invent 2022 - Delivering sustainable, high-performing architectures ](https://www.youtube.com/watch?v=FBc9hXQfat0)
- [AWS re:Invent 2023 - Optimize cost and performance and track progress toward mitigation ](https://www.youtube.com/watch?v=keAfy8f84E0)
- [AWS re:Invent 2022 - AWS optimization: Actionable steps for immediate results ](https://www.youtube.com/watch?v=0ifvNf2Tx3w)
### Related Examples
- [AWS Samples](https://github.com/aws-samples)
- [AWS SDK Examples](https://github.com/awsdocs/aws-doc-sdk-examples)
