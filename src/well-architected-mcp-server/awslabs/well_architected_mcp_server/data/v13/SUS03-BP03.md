---
id: "SUS03-BP03"
title: "Optimize areas of code that consume the most time or resources"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of software and architecture patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS03-BP03 Optimize areas of code that consume the most time or resources

## Anti-Patterns
- You ignore optimizing your code for resource usage.
- You usually respond to performance issues by increasing the resources.
- Your code review and development process does not track performance changes.

## Implementation Guidance
 It is crucial to examine every functional area, including the code for a cloud architected application, to optimize its resource usage and performance. Continually monitor your workload’s performance in build environments and production and identify opportunities to improve code snippets that have particularly high resource usage. Adopt a regular review process to identify bugs or anti-patterns within your code that use resources inefficiently. Leverage simple and efficient algorithms that produce the same results for your use case.

## Implementation Steps
- **Use efficient programming language:** Use an efficient operating system and programming language for the workload. For details on energy efficient programming languages (including Rust), see [Sustainability with Rust](https://aws.amazon.com/blogs/opensource/sustainability-with-rust/).
- **Use an AI coding companion:** Consider using an AI coding companion such as [Amazon Q Developer](https://aws.amazon.com/q/developer/) to efficiently write code.
- **Automate code reviews:** While developing your workloads, adopt an automated code review process to improve quality and identify bugs and anti-patterns.
  - [ Automate code reviews with Amazon CodeGuru Reviewer ](https://aws.amazon.com/blogs/devops/automate-code-reviews-with-amazon-codeguru-reviewer/)
  - [ Detecting concurrency bugs with Amazon CodeGuru ](https://aws.amazon.com/blogs/devops/detecting-concurrency-bugs-with-amazon-codeguru/)
  - [ Raising code quality for Python applications using Amazon CodeGuru ](https://aws.amazon.com/blogs/devops/raising-code-quality-for-python-applications-using-amazon-codeguru/)
- **Use a code profiler:** Use a code profiler to identify the areas of code that use the most time or resources as targets for optimization.
  - [ Reducing your organization's carbon footprint with Amazon CodeGuru Profiler ](https://aws.amazon.com/blogs/devops/reducing-your-organizations-carbon-footprint-with-codeguru-profiler/)
  - [ Understanding memory usage in your Java application with Amazon CodeGuru Profiler ](https://aws.amazon.com/blogs/devops/understanding-memory-usage-in-your-java-application-with-amazon-codeguru-profiler/)
  - [ Improving customer experience and reducing cost with Amazon CodeGuru Profiler ](https://aws.amazon.com/blogs/devops/improving-customer-experience-and-reducing-cost-with-codeguru-profiler/)
- **Monitor and optimize:** Use continuous monitoring resources to identify components with high resource requirements or suboptimal configuration.
  - Replace computationally intensive algorithms with simpler and more efficient version that produce the same result.
  - Remove unnecessary code such as sorting and formatting.
- **Use code refactoring or transformation:** Explore the possibility of [Amazon Q code transformation](https://aws.amazon.com/q/aws/code-transformation/) for application maintenance and upgrades.
  - [ Upgrade language versions with Amazon Q Code Transformation ](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/code-transformation.html)
  - [AWS re:Invent 2023 - Automate app upgrades & maintenance using Amazon Q Code Transformation ](https://www.youtube.com/watch?v=LY76tak6Z1E)

## Resources
### Related Documents
- [What is Amazon CodeGuru Profiler?](https://docs.aws.amazon.com/codeguru/latest/profiler-ug/what-is-codeguru-profiler.html)
- [FPGA instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/fpga-getting-started.html)
- [The AWS SDKs on Tools to Build on AWS](https://aws.amazon.com/tools/)
### Related Videos
- [ Improve Code Efficiency Using Amazon CodeGuru Profiler ](https://www.youtube.com/watch?v=1pU4VddsBRw)
- [ Automate Code Reviews and Application Performance Recommendations with Amazon CodeGuru ](https://www.youtube.com/watch?v=OD8H63C0E0I)
