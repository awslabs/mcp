---
id: "PERF05-BP03"
title: "Define a process to improve workload performance"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do your organizational practices and culture contribute to performance efficiency in your workload?"
risk_level: "Medium"
---

# PERF05-BP03 Define a process to improve workload performance

## Anti-Patterns
- You assume your current architecture is static and won’t be updated over time.
- You introduce architecture changes over time with no metric justification.

## Implementation Guidance
 Your workload's performance has a few key constraints. Document these so that you know what kinds of innovation might improve the performance of your workload. Use this information when learning about new services or technology as it becomes available to identify ways to alleviate constraints or bottlenecks.

 Identify the key performance constraints for your workload. Document your workload’s performance constraints so that you know what kinds of innovation might improve the performance of your workload.

## Implementation Steps
- **Identify KPIs:** Identify your workload performance KPIs as outlined in [PERF05-BP01 Establish key performance indicators (KPIs) to measure workload health and performance](perf_process_culture_establish_key_performance_indicators.md) to baseline your workload.
- **Implement monitoring:** Use [AWS observability tools](https://docs.aws.amazon.com/wellarchitected/latest/management-and-governance-guide/aws-observability-tools.html) to collect performance metrics and measure KPIs.
- **Conduct analysis:** Conduct in-depth analysis to identify the areas (like configuration and application code) in your workload that is under-performing as outlined in [PERF05-BP02 Use monitoring solutions to understand the areas where performance is most critical](perf_process_culture_use_monitoring_solutions.md). Use your analysis and performance tools to identify the performance improvement strategies.
- **Validate improvements:** Use sandbox or pre-production environments to validate the effectiveness of improvement strategies.
- **Implement changes:** Implement the changes in production and continually monitor the workload’s performance. Document the improvements, and communicate the changes to stakeholders.
- **Revisit and refine:** Regularly review your performance improvement process to identify areas for enhancement.

## Resources
### Related Documents
- [AWS Blog](https://aws.amazon.com/blogs/)
- [What's New with AWS](https://aws.amazon.com/new/?ref=wellarchitected)
- [AWS Skill Builder](https://explore.skillbuilder.aws/learn)
### Related Videos
- [AWS re:Invent 2022 - Delivering sustainable, high-performing architectures ](https://www.youtube.com/watch?v=FBc9hXQfat0)
- [AWS re:Invent 2023 - Optimize cost and performance and track progress toward mitigation ](https://www.youtube.com/watch?v=keAfy8f84E0)
- [AWS re:Invent 2022 - AWS optimization: Actionable steps for immediate results ](https://www.youtube.com/watch?v=0ifvNf2Tx3w)
- [AWS re:Invent 2022 - Optimize your AWS workloads with best-practice guidance ](https://www.youtube.com/watch?v=t8yl1TrnuIk)
### Related Examples
- [AWS Github](https://github.com/aws)
