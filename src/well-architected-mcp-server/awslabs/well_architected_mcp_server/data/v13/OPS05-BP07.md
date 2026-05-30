---
id: "OPS05-BP07"
title: "Implement practices to improve code quality"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
risk_level: "Medium"
effort: "Medium"
---

# OPS05-BP07 Implement practices to improve code quality

## Desired Outcome
Your organization uses best practices like code reviews or pair programming to improve code quality. Developers and operators adopt code quality best practices as part of the software development lifecycle.

## Anti-Patterns
- You commit code to the main branch of your application without a code review. The change automatically deploys to production and causes an outage.
- A new application is developed without any unit, end-to-end, or integration tests. There is no way to test the application before deployment.
- Your teams make manual changes in production to address defects. Changes do not go through testing or code reviews and are not captured or logged through continuous integration and delivery processes.

## Implementation Guidance
 Implement practices to improve code quality to minimize defects before they are deployed. Use practices like test-driven development, code reviews, and pair programming to increase the quality of your development.

 Use the power of generative AI with Amazon Q Developer to improve developer productivity and code quality. Amazon Q Developer includes generation of code suggestions (based on large language models), production of unit tests (including boundary conditions), and code security enhancements through detection and remediation of security vulnerabilities.

 **Customer example**

 AnyCompany Retail adopts several practices to improve code quality. They have adopted test-driven development as the standard for writing applications. For some new features, they will have developers pair program together during a sprint. Every pull request goes through a code review by a senior developer before being integrated and deployed.

## Implementation Steps
1.  Adopt code quality practices like test-driven development, code reviews, and pair programming into your continuous integration and delivery process. Use these techniques to improve software quality.

   1.  Use [Amazon Q Developer](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/what-is.html), a generative AI tool that can help create unit test cases (including boundary conditions), generate functions using code and comments, implement well-known algorithms, detect security policy violations and vulnerabilities in your code, detect secrets, scan infrastructure as code (IaC), document code, and learn third-party code libraries more quickly.

   1.  [Amazon CodeGuru Reviewer](https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/welcome.html) can provide programming recommendations for Java and Python code using machine learning.

## Resources
### Related Best Practices
- [OPS05-BP02 Test and validate changes](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_test_val_chg.html)
- [OPS05-BP06 Share design standards](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_share_design_stds.html)
### Related Documents
- [Adopt a test-driven development approach](https://docs.aws.amazon.com/prescriptive-guidance/latest/best-practices-cdk-typescript-iac/development-best-practices.html)
- [Accelerate your Software Development Lifecycle with Amazon Q](https://aws.amazon.com/blogs/devops/accelerate-your-software-development-lifecycle-with-amazon-q/)
- [Amazon Q Developer, now generally available, includes previews of new capabilities to reimagine developer experience](https://aws.amazon.com/blogs/aws/amazon-q-developer-now-generally-available-includes-new-capabilities-to-reimagine-developer-experience/)
- [The Ultimate Cheat Sheet for Using Amazon Q Developer in Your IDE](https://community.aws/content/2eYoqeFRqaVnk900emsknDfzhfW/the-ultimate-cheat-sheet-for-using-amazon-q-developer-in-your-ide)
- [Shift-Left Workload, leveraging AI for Test Creation](https://community.aws/content/2gBZtC94gPzaCQRnt4P0rIYWuBx/shift-left-workload-leveraging-ai-for-test-creation)
- [Amazon Q Developer Center](https://aws.amazon.com/developer/generative-ai/amazon-q/)
- [10 ways to build applications faster with Amazon CodeWhisperer](https://aws.amazon.com/blogs/devops/10-ways-to-build-applications-faster-with-amazon-codewhisperer/)
- [Looking beyond code coverage with Amazon CodeWhisperer](https://aws.amazon.com/blogs/devops/looking-beyond-code-coverage-with-amazon-codewhisperer/)
- [Best Practices for Prompt Engineering with Amazon CodeWhisperer](https://aws.amazon.com/blogs/devops/best-practices-for-prompt-engineering-with-amazon-codewhisperer/)
- [Agile Software Guide](https://martinfowler.com/agile.html)
- [My CI/CD pipeline is my release captain](https://aws.amazon.com/builders-library/cicd-pipeline/)
- [Automate code reviews with Amazon CodeGuru Reviewer](https://aws.amazon.com/blogs/devops/automate-code-reviews-with-amazon-codeguru-reviewer/)
- [Adopt a test-driven development approach](https://docs.aws.amazon.com/prescriptive-guidance/latest/best-practices-cdk-typescript-iac/development-best-practices.html)
- [How DevFactory builds better applications with Amazon CodeGuru](https://aws.amazon.com/blogs/machine-learning/how-devfactory-builds-better-applications-with-amazon-codeguru/)
- [On Pair Programming](https://martinfowler.com/articles/on-pair-programming.html)
- [RENGA Inc. automates code reviews with Amazon CodeGuru](https://aws.amazon.com/blogs/machine-learning/renga-inc-automates-code-reviews-with-amazon-codeguru/)
- [The Art of Agile Development: Test-Driven Development](http://www.jamesshore.com/v2/books/aoad1/test_driven_development)
- [Why code reviews matter (and actually save time\$1)](https://www.atlassian.com/agile/software-development/code-reviews)
### Related Videos
- [Implement an API with Amazon Q Developer Agent for Software Development](https://www.youtube.com/watch?v=U4XEvJUvff4)
- [Installing, Configuring, & Using Amazon Q Developer with JetBrains IDEs (How-to)](https://www.youtube.com/watch?v=-iQfIhTA4J0)
- [Mastering the art of Amazon CodeWhisperer - YouTube playlist](https://www.youtube.com/playlist?list=PLDqi6CuDzubxzL-yIqgQb9UbbceYdKhpK)
- [AWS re:Invent 2020: Continuous improvement of code quality with Amazon CodeGuru](https://www.youtube.com/watch?v=iX1i35H1OVw)
- [AWS Summit ANZ 2021 - Driving a test-first strategy with CDK and test driven development](https://www.youtube.com/watch?v=1R7G_wcyd3s)
### Related Services
- [Amazon Q Developer](https://aws.amazon.com/q/developer/)
- [Amazon CodeGuru Reviewer](https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/welcome.html)
- [Amazon CodeGuru Profiler](https://docs.aws.amazon.com/codeguru/latest/profiler-ug/what-is-codeguru-profiler.html)
