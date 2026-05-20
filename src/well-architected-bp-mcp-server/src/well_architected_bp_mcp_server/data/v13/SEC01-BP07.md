---
id: "SEC01-BP07"
title: "Identify threats and prioritize mitigations using a threat model"
framework: "WAF"
domain: "Security"
capability: "How do you securely operate your workload?"
risk_level: "High"
---

# SEC01-BP07 Identify threats and prioritize mitigations using a threat model

## Implementation Guidance
 **What is threat modeling?**

 “Threat modeling works to identify, communicate, and understand threats and mitigations within the context of protecting something of value.” – [The Open Web Application Security Project (OWASP) Application Threat Modeling](https://owasp.org/www-community/Threat_Modeling)

 **Why should you threat model?**

 Systems are complex, and are becoming increasingly more complex and capable over time, delivering more business value and increased customer satisfaction and engagement. This means that IT design decisions need to account for an ever-increasing number of use cases. This complexity and number of use-case permutations typically makes unstructured approaches ineffective for finding and mitigating threats. Instead, you need a systematic approach to enumerate the potential threats to the system, and to devise mitigations and prioritize these mitigations to make sure that the limited resources of your organization have the maximum impact in improving the overall security posture of the system.

 Threat modeling is designed to provide this systematic approach, with the aim of finding and addressing issues early in the design process, when the mitigations have a low relative cost and effort compared to later in the lifecycle. This approach aligns with the industry principle of [*shift-left* security](https://owasp.org/www-project-devsecops-guideline/latest/00a-Overview). Ultimately, threat modeling integrates with an organization’s risk management process and helps drive decisions on which controls to implement by using a threat driven approach.

 **When should threat modeling be performed?**

 Start threat modeling as early as possible in the lifecycle of your workload, this gives you better flexibility on what to do with the threats you have identified. Much like software bugs, the earlier you identify threats, the more cost effective it is to address them. A threat model is a living document and should continue to evolve as your workloads change. Revisit your threat models over time, including when there is a major change, a change in the threat landscape, or when you adopt a new feature or service.

## Implementation Steps
 **How can we perform threat modeling?**

 There are many different ways to perform threat modeling. Much like programming languages, there are advantages and disadvantages to each, and you should choose the way that works best for you. One approach is to start with [Shostack’s 4 Question Frame for Threat Modeling](https://github.com/adamshostack/4QuestionFrame), which poses open-ended questions to provide structure to your threat modeling exercise:

1.  **What are we working on?**

    The purpose of this question is to help you understand and agree upon the system you are building and the details about that system that are relevant to security. Creating a model or diagram is the most popular way to answer this question, as it helps you to visualize what you are building, for example, using a [data flow diagram](https://en.wikipedia.org/wiki/Data-flow_diagram). Writing down assumptions and important details about your system also helps you define what is in scope. This allows everyone contributing to the threat model to focus on the same thing, and avoid time-consuming detours into out-of-scope topics (including out of date versions of your system). For example, if you are building a web application, it is probably not worth your time threat modeling the operating system trusted boot sequence for browser clients, as you have no ability to affect this with your design.

1.  **What can go wrong?**

    This is where you identify threats to your system. Threats are accidental or intentional actions or events that have unwanted impacts and could affect the security of your system. Without a clear understanding of what could go wrong, you have no way of doing anything about it.

    There is no canonical list of what can go wrong. Creating this list requires brainstorming and collaboration between all of the individuals within your team and [relevant personas involved](https://aws.amazon.com/blogs/security/how-to-approach-threat-modeling/#tips) in the threat modeling exercise. You can aid your brainstorming by using a model for identifying threats, such as [STRIDE](https://en.wikipedia.org/wiki/STRIDE_(security)), which suggests different categories to evaluate: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of privilege. In addition, you might want to aid the brainstorming by reviewing existing lists and research for inspiration, including the [OWASP Top 10](https://owasp.org/www-project-top-ten/), [HiTrust Threat Catalog](https://hitrustalliance.net/hitrust-threat-catalogue/), and your organization’s own threat catalog.

1.  **What are we going to do about it?**

    As was the case with the previous question, there is no canonical list of all possible mitigations. The inputs into this step are the identified threats, actors, and areas of improvement from the previous step.

    Security and compliance is a [shared responsibility between you and AWS](https://aws.amazon.com/compliance/shared-responsibility-model/). It’s important to understand that when you ask “What are we going to do about it?”, that you are also asking “Who is responsible for doing something about it?”. Understanding the balance of responsibilities between you and AWS helps you scope your threat modeling exercise to the mitigations that are under your control, which are typically a combination of AWS service configuration options and your own system-specific mitigations.

    For the AWS portion of the shared responsibility, you will find that [AWS services are in-scope of many compliance programs](https://aws.amazon.com/compliance/services-in-scope/). These programs help you to understand the robust controls in place at AWS to maintain security and compliance of the cloud. The audit reports from these programs are available for download for AWS customers from [AWS Artifact](https://aws.amazon.com/artifact/).

    Regardless of which AWS services you are using, there’s always an element of customer responsibility, and mitigations aligned to these responsibilities should be included in your threat model. For security control mitigations for the AWS services themselves, you want to consider implementing security controls across domains, including domains such as identity and access management (authentication and authorization), data protection (at rest and in transit), infrastructure security, logging, and monitoring. The documentation for each AWS service has a [dedicated security chapter](https://docs.aws.amazon.com/security/) that provides guidance on the security controls to consider as mitigations. Importantly, consider the code that you are writing and its code dependencies, and think about the controls that you could put in place to address those threats. These controls could be things such as [input validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html), [session handling](https://owasp.org/www-project-mobile-top-10/2014-risks/m9-improper-session-handling), and [bounds handling](https://owasp.org/www-community/vulnerabilities/Buffer_Overflow). Often, the majority of vulnerabilities are introduced in custom code, so focus on this area.

1.  **Did we do a good job?**

    The aim is for your team and organization to improve both the quality of threat models and the velocity at which you are performing threat modeling over time. These improvements come from a combination of practice, learning, teaching, and reviewing. To go deeper and get hands on, it’s recommended that you and your team complete the [Threat modeling the right way for builders training course](https://explore.skillbuilder.aws/learn/course/external/view/elearning/13274/threat-modeling-the-right-way-for-builders-workshop) or [workshop](https://catalog.workshops.aws/threatmodel/en-US). In addition, if you are looking for guidance on how to integrate threat modeling into your organization’s application development lifecycle, see [How to approach threat modeling](https://aws.amazon.com/blogs/security/how-to-approach-threat-modeling/) post on the AWS Security Blog.

 **Threat Composer**

 To aid and guide you in performing threat modeling, consider using the [Threat Composer](https://github.com/awslabs/threat-composer#threat-composer) tool, which aims to your reduce time-to-value when threat modeling. The tool helps you do the following:
- Write useful threat statements aligned to [threat grammar](https://catalog.workshops.aws/threatmodel/en-US/what-can-go-wrong/threat-grammar) that work in a natural non-linear workflow
- Generate a human-readable threat model
- Generate a machine-readable threat model to allow you treat threat models as code
- Help you to quickly identify areas of quality and coverage improvement using the Insights Dashboard

 For further reference, visit Threat Composer and switch to the system-defined **Example Workspace**.

## Resources
### Related Best Practices
- [SEC01-BP03 Identify and validate control objectives](sec_securely_operate_control_objectives.md)
- [SEC01-BP04 Stay up to date with security threats and recommendations](sec_securely_operate_updated_threats.md)
- [SEC01-BP05 Reduce security management scope](sec_securely_operate_reduce_management_scope.md)
- [SEC01-BP08 Evaluate and implement new security services and features regularly ](sec_securely_operate_implement_services_features.md)
### Related Documents
- [How to approach threat modeling](https://aws.amazon.com/blogs/security/how-to-approach-threat-modeling/) (AWS Security Blog)
- [ NIST: Guide to Data-Centric System Threat modeling ](https://csrc.nist.gov/publications/detail/sp/800-154/draft)
### Related Videos
- [AWS Summit ANZ 2021 - How to approach threat modeling ](https://www.youtube.com/watch?v=GuhIefIGeuA)
- [AWS Summit ANZ 2022 - Scaling security – Optimise for fast and secure delivery ](https://www.youtube.com/watch?v=DjNPihdWHeA)
### Related Training
- [ Threat modeling the right way for builders – AWS Skill Builder virtual self-paced training ](https://explore.skillbuilder.aws/learn/course/external/view/elearning/13274/threat-modeling-the-right-way-for-builders-workshop)
- [ Threat modeling the right way for builders – AWS Workshop ](https://catalog.workshops.aws/threatmodel)
### Related Tools
- [Threat Composer](https://github.com/awslabs/threat-composer#threat-composer)
