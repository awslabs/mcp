---
id: "SEC11-BP04"
title: "Conduct code reviews"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "Medium"
---

# SEC11-BP04 Conduct code reviews

## Desired Outcome
You include code reviews during development to increase the quality of the software being written. You upskill less experienced members of the team through learnings identified during the code review. You identify opportunities for automation and support the code review process using automated tools and testing.

## Anti-Patterns
- You don't review code before deployment.
- The same person writes and reviews the code.
- You don't use automation and tools to assist or orchestrate code reviews.
- You don't train builders on application security before they review code.

## Implementation Guidance
 Code reviews help to verify the quality and security of the software during development. Manual reviews involve having a team member other than the original code author review the code for potential issues, vulnerabilities, and adherence to coding standards and best practices. This process helps catch errors, inconsistencies, and security flaws that might have been overlooked by the original developer.

 Consider [Amazon CodeGuru Security](https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/welcome.html) to help conduct automated code reviews. CodeGuru Security uses machine learning and automated reasoning to analyze your code and identify potential security vulnerabilities and coding issues. Integrate automated code reviews with your existing code repositories and continuous integration/continuous deployment (CI/CD) pipelines.

## Implementation Steps
1.  **Establish a code review process:**
   - Define when code reviews should occur, such as before merging code into the main branch or before deploying to production.
   - Determine who should be involved in the code review process, such as team members, senior developers, and security experts.
   - Decide on the code review methodology, including the process and tools to be used.

1.  **Set up code review tools:**
   - Evaluate and select code review tools that fit your team's needs, such as GitHub Pull Requests or CodeGuru Security
   - Integrate the chosen tools with your existing code repositories and CI/CD pipelines.
   - Configure the tools to enforce code review requirements, such as the minimum number of reviewers and approval rules.

1.  **Define a code review checklist and guidelines:**
   - Create a code review checklist or guidelines that outline what should be reviewed. Consider factors such as code quality, security vulnerabilities, adherence to coding standards, and performance.
   - Share the checklist or guidelines with the development team, and verify everyone understands the expectations.

1.  **Train developers on code review best practices:**
   - Provide training to your team on how to conduct effective code reviews.
   - Educate your team on application security principles and common vulnerabilities to look for during reviews.
   - Encourage knowledge sharing and pair programming sessions to upskill less experienced team members.

1.  **Implement the code review process:**
   - Integrate the code review step into your development workflow, such as creating a pull request and assigning reviewers.
   - Require that code changes undergo a code review before merge or deployment.
   - Encourage open communication and constructive feedback during the review process.

1.  **Monitor and improve:**
   - Regularly review the effectiveness of your code review process and gather feedback from the team.
   - Identify opportunities for automation or tool improvements to streamline the code review process.
   - Continuously update and refine the code review checklist or guidelines based on learnings and industry best practices.

1.  **Foster a culture of code review:**
   - Emphasize the importance of code reviews to maintain code quality and security.
   - Celebrate successes and learnings from the code review process.
   - Encourage a collaborative and supportive environment where developers feel comfortable giving and receiving feedback.

## Resources
### Related Best Practices
- [SEC11-BP02 Automate testing throughout the development and release lifecycle](sec_appsec_automate_testing_throughout_lifecycle.md)
### Related Documents
- [DevOps Guidance: DL.CR.2 Perform peer review for code changes](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cr.2-perform-peer-review-for-code-changes.html)
- [About pull requests in GitHub](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
### Related Examples
- [Automate code reviews with Amazon CodeGuru Security](https://aws.amazon.com/blogs/devops/automate-code-reviews-with-amazon-codeguru-reviewer/)
- [Automating detection of security vulnerabilities and bugs in CI/CD pipelines using Amazon CodeGuru Security CLI](https://aws.amazon.com/blogs/devops/automating-detection-of-security-vulnerabilities-and-bugs-in-ci-cd-pipelines-using-amazon-codeguru-reviewer-cli/)
### Related Videos
- [Continuous improvement of code quality with Amazon CodeGuru Security](https://www.youtube.com/watch?v=iX1i35H1OVw)
