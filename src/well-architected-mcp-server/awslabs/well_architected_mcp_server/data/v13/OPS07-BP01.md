---
id: "OPS07-BP01"
title: "Ensure personnel capability"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you know that you are ready to support a workload?"
risk_level: "High"
effort: "High"
---

# OPS07-BP01 Ensure personnel capability

## Desired Outcome
- There are enough trained personnel to support the workload at times when the workload is available.
- You provide training for your personnel on the software and services that make up your workload.

## Anti-Patterns
- Deploying a workload without team members trained to operate the platform and services in use.
- Not having enough personnel to support on-call rotations or personnel taking time off.

## Implementation Guidance
 Validate that there are sufficient trained personnel to support the workload. Verify that you have enough team members to cover normal operational activities, including on-call rotations.

 **Customer example**

 AnyCompany Retail makes sure that teams supporting the workload are properly staffed and trained. They have enough engineers to support an on-call rotation. Personnel get training on the software and platform that the workload is built on and are encouraged to earn certifications. There are enough personnel so that people can take time off while still supporting the workload and the on-call rotation.

## Implementation Steps
1.  Assign an adequate number of personnel to operate and support your workload, including on-call duties, security issues, and lifecycle events, such as end of support and certificate rotation tasks.

1.  Train your personnel on the software and platforms that compose your workload.

   1.  [AWS Training and Certification](https://aws.amazon.com/training/) has a library of courses about AWS. They provide free and paid courses, online and in-person.

   1.  [AWS hosts events and webinars](https://aws.amazon.com/events/) where you learn from AWS experts.

1. Perform the following on a regular basis:
   - Evaluate team size and skills as operating conditions and the workload change.
   - Adjust team size and skills to match operational requirements.
   - Verify ability and capacity to [address planned lifecycle events](https://docs.aws.amazon.com/health/latest/ug/aws-health-planned-lifecycle-events.html), unplanned security, and operational notifications through AWS Health.

## Resources
### Related Best Practices
- [OPS11-BP04 Perform knowledge management](ops_evolve_ops_knowledge_management.md) - Team members must have the information necessary to operate and support the workload. Knowledge management is the key to providing that.
### Related Documents
- [AWS Events and Webinars](https://aws.amazon.com/events/)
- [AWS Training and Certification](https://aws.amazon.com/training/)
