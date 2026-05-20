---
id: "SEC11-BP01"
title: "Train for application security"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "Medium"
---

# SEC11-BP01 Train for application security

## Desired Outcome
You equip your team with the knowledge and skills necessary to design and build software with security in mind from the outset. Through training on threat modeling and secure development practices, your team has a deep understanding of potential security risks and how to mitigate them during the software development lifecycle (SDLC). This proactive approach to security is part of your team's culture, and you become able to identify and remediate potential security issues early on. As a result, your team delivers high-quality, secure software and features more efficiently, which accelerates the overall delivery timeline. You have a collaborative and inclusive security culture within your organization, where the ownership of security is shared across all builders.

## Anti-Patterns
- You wait until a security review, and then consider the security properties of a system.
- You leave all security decisions to a central security team.
- You don't communicate how the decisions taken in the SDLC relate to the overall security expectations or policies of the organization.
- You perform the security review process too late.

## Implementation Guidance
 To build secure and high-quality software, provide training to your team on common practices for secure development and operation of applications. This practice can help your team prevent, detect, and remediate security issues earlier in the development lifecycle, which can accelerate your delivery timeline.

 To achieve this practice, consider training your team on threat modeling using AWS resources like the [Threat Modeling Workshop](https://catalog.workshops.aws/threatmodel/en-US). Threat modeling can help your team understand potential security risks and design systems with security in mind from the outset. Additionally, you can provide access to [AWS Training and Certification](https://www.aws.training/LearningLibrary?filters=Language%3A1%20Domain%3A27), industry, or AWS Partner training on secure development practices. For more detail on a comprehensive approach to designing, developing, securing, and efficiently operating at scale, see [AWS DevOps Guidance](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/devops-guidance.html).

 Clearly define and communicate your organization's security review process, and outline the responsibilities of your team, the security team, and other stakeholders. Publish self-service guidance, code examples, and templates that demonstrate how to meet your security requirements. You can use AWS services like [AWS CloudFormation](https://aws.amazon.com/cloudformation/), [AWS Cloud Development Kit (AWS CDK) (AWS CDK) Constructs](https://docs.aws.amazon.com/cdk/v2/guide/constructs.html), and [Service Catalog](https://aws.amazon.com/servicecatalog/) to provide pre-approved, secure configurations and reduce the need for custom setups.

 Regularly gather feedback from your team on their experience with the security review process and training, and use this feedback to continuously improve. Conduct game days or bug bash campaigns to identify and address security issues while simultaneously enhancing your team's skills.

## Implementation Steps
1.  **Identify training needs**: Assess the current skill level and knowledge gaps within your team regarding secure development practices through surveys, code reviews, or discussions with team members.

1.  **Plan the training**: Based on the identified needs, create a training plan that covers relevant topics such as threat modeling, secure coding practices, security testing, and secure deployment practices. Employ resources like the [Threat Modeling Workshop](https://catalog.workshops.aws/threatmodel/en-US), [AWS Training and Certification](https://www.aws.training/LearningLibrary?filters=Language%3A1%20Domain%3A27), and industry or AWS Partner training programs.

1.  **Schedule and deliver training**: Schedule regular training sessions or workshops for your team. These can be instructor-led or self-paced, depending on your team's preferences and availability. Encourage hands-on exercises and practical examples to reinforce the learning.

1.  **Define a security review process**: Collaborate with your security team and other stakeholders to clearly define the security review process for your applications. Document the responsibilities of each team or individual involved in the process, including your development team, security team, and other relevant stakeholders.

1.  **Create self-service resources**: Develop self-service guidance, code examples, and templates that demonstrate how to meet your organization's security requirements. Consider AWS services like [CloudFormation](https://aws.amazon.com/cloudformation/), [AWS CDK Constructs](https://docs.aws.amazon.com/cdk/v2/guide/constructs.html), and [Service Catalog](https://aws.amazon.com/servicecatalog/) to provide pre-approved, secure configurations and reduce the need for custom setups.

1.  **Communicate and socialize**: Effectively communicate the security review process and the available self-service resources to your team. Conduct training sessions or workshops to familiarize them with these resources, and verify that they understand how to use them.

1.  **Gather feedback and improve**: Regularly collect feedback from your team on their experience with the security review process and training. Use this feedback to identify areas for improvement and continuously refine the training materials, self-service resources, and the security review process.

1.  **Conduct security exercises**: Organize game days or bug bash campaigns to identify and address security issues within your applications. These exercises not only help uncover potential vulnerabilities but also serve as practical learning opportunities for your team that enhance their skills in secure development and operation.

1.  **Continue to learn and improve:** Encourage your team to stay up to date with the latest secure development practices, tools, and techniques. Regularly review and update your training materials and resources to reflect the evolving security landscape and best practices.

## Resources
### Related Best Practices
- [SEC11-BP08 Build a program that embeds security ownership in workload teams](sec_appsec_build_program_that_embeds_security_ownership_in_teams.md)
### Related Documents
- [AWS Training and Certification](https://www.aws.training/LearningLibrary?query=&filters=Language%3A1%20Domain%3A27&from=0&size=15&sort=_score&trk=el_a134p000007C9OtAAK&trkCampaign=GLBL-FY21-TRAINCERT-800-Security&sc_channel=el&sc_campaign=GLBL-FY21-TRAINCERT-800-Security-Blog&sc_outcome=Training_and_Certification&sc_geo=mult)
- [How to think about cloud security governance](https://aws.amazon.com/blogs/security/how-to-think-about-cloud-security-governance/)
- [How to approach threat modeling](https://aws.amazon.com/blogs/security/how-to-approach-threat-modeling/)
- [Accelerating training – The AWS Skills Guild](https://docs.aws.amazon.com/whitepapers/latest/public-sector-cloud-transformation/accelerating-training-the-aws-skills-guild.html)
- [AWS DevOps Sagas](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/the-devops-sagas.html)
### Related Videos
- [Proactive security: Considerations and approaches](https://www.youtube.com/watch?v=CBrUE6Qwfag)
### Related Examples
- [Workshop on threat modeling](https://catalog.workshops.aws/threatmodel)
- [Industry awareness for developers](https://owasp.org/www-project-top-ten/)
### Related Services
- [AWS CloudFormation](https://aws.amazon.com/cloudformation/)
- [AWS Cloud Development Kit (AWS CDK) (AWS CDK) Constructs](https://docs.aws.amazon.com/cdk/v2/guide/constructs.html)
- [Service Catalog](https://aws.amazon.com/servicecatalog/)
