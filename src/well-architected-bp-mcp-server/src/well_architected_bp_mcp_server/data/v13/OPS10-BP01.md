---
id: "OPS10-BP01"
title: "Use a process for event, incident, and problem management"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you manage workload and operations events?"
risk_level: "High"
effort: "Medium"
---

# OPS10-BP01 Use a process for event, incident, and problem management

## Desired Outcome
Your organization effectively manages operational events, incidents, and problems through well-documented and centrally stored processes. These processes are consistently updated to reflect changes, streamlining handling and maintaining high service reliability and workload performance.

## Anti-Patterns
- You reactively, rather than proactively, respond to events.
- Inconsistent approaches are taken to different types of events or incidents.
- Your organization does not analyze and learn from incidents to prevent future occurrences.

## Implementation Guidance
 Implementing this best practice means you are tracking workload events. You have processes to handle incidents and problems. The processes are documented, shared, and updated frequently. Problems are identified, prioritized, and fixed.

 **Understanding events, incidents, and problems**
- **Events:** An *event* is an observation of an action, occurrence, or change of state. Events can be planned or unplanned and they can originate internally or externally to the workload.
- **Incidents:** *Incidents* are events that require a response, like unplanned interruptions or degradations of service quality. They represent disruptions that need immediate attention to restore normal workload operation.
- **Problems:** *Problems* are the underlying causes of one or more incidents. Identifying and resolving problems involves digging deeper into the incidents to prevent future occurrences.

## Implementation Steps
 **Events**

1.  **Monitor events:**
   - [Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html) and [utilize workload observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/utilizing-workload-observability.html).
   - Monitor actions taken by a user, role, or an AWS service are recorded as events in [AWS CloudTrail](https://aws.amazon.com/cloudtrail/).
   - Respond to operational changes in your applications in real time with [Amazon EventBridge](https://aws.amazon.com/eventbridge/).
   - Continually assess, monitor, and record resource configuration changes with [AWS Config](https://aws.amazon.com/config/).

1.  **Create processes:**
   - Develop a process to assess which events are significant and require monitoring. This involves setting thresholds and parameters for normal and abnormal activities.
   - Determine criteria escalating an event to an incident. This could be based on the severity, impact on users, or deviation from expected behavior.
   - Regularly review the event monitoring and response processes. This includes analyzing past incidents, adjusting thresholds, and refining alerting mechanisms.

 **Incidents**

1.  **Respond to incidents:**
   - Use insights from observability tools to quickly identify and respond to incidents.
   - Implement [AWS Systems Manager Ops Center](https://aws.amazon.com/systems-manager/features/#OpsCenter) to aggregate, organize, and prioritize operational items and incidents.
   - Use services like [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) and [AWS X-Ray](https://aws.amazon.com/xray/) for deeper analysis and troubleshooting.
   - Consider [AWS Managed Services (AMS)](https://aws.amazon.com/managed-services/) for enhanced incident management, leveraging its proactive, preventative, and detective capabilities. AMS extends operational support with services like monitoring, incident detection and response, and security management.
   - Enterprise Support customers can use [AWS Incident Detection and Response](https://aws.amazon.com/premiumsupport/aws-incident-detection-response/), which provides continual proactive monitoring and incident management for production workloads.

1.  **Create an incident management process:**
   - Establish a structured incident management process, including clear roles, communication protocols, and steps for resolution.
   - Integrate incident management with tools like [Amazon Q Developer in chat applications](https://aws.amazon.com/chatbot/) for efficient response and coordination.
   - Categorize incidents by severity, with predefined [incident response plans](https://docs.aws.amazon.com/incident-manager/latest/userguide/response-plans.html) for each category.

1.  **Learn and improve:**
   - Conduct [post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_perform_rca_process.html) to understand root causes and resolution effectiveness.
   - Continually update and improve response plans based on reviews and evolving practices.
   - Document and share lessons learned across teams to enhance operational resilience.
   - Enterprise Support customers can request the [Incident Management Workshop](https://aws.amazon.com/premiumsupport/technology-and-programs/proactive-services/#Operational_Workshops_and_Deep_Dives) from their Technical Account Manager. This guided workshop tests your existing incident response plan and helps you identify areas for improvement.

 **Problems**

1.  **Identify problems:**
   - Use data from previous incidents to identify recurring patterns that may indicate deeper systemic issues.
   - Leverage tools like [AWS CloudTrail](https://aws.amazon.com/cloudtrail/) and [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) to analyze trends and uncover underlying problems.
   - Engage cross-functional teams, including operations, development, and business units, to gain diverse perspectives on the root causes.

1.  **Create a problem management process:**
   - Develop a structured process for problem management, focusing on long-term solutions rather than quick fixes.
   - Incorporate root cause analysis (RCA) techniques to investigate and understand the underlying causes of incidents.
   - Update operational policies, procedures, and infrastructure based on findings to prevent recurrence.

1.  **Continue to improve:**
   - Foster a culture of constant learning and improvement, encouraging teams to proactively identify and address potential problems.
   - Regularly review and revise problem management processes and tools to align with evolving business and technology landscapes.
   - Share insights and best practices across the organization to build a more resilient and efficient operational environment.

1.  **Engage AWS Support:**
   - Use AWS support resources, such as [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/), for proactive guidance and optimization recommendations.
   - Enterprise Support customers can access specialized programs like [AWS Countdown](https://aws.amazon.com/premiumsupport/aws-countdown/) for support during critical events.

## Resources
### Related Best Practices
- [OPS04-BP01 Identify key performance indicators](ops_observability_identify_kpis.md)
- [OPS04-BP02 Implement application telemetry](ops_observability_application_telemetry.md)
- [OPS07-BP03 Use runbooks to perform procedures](ops_ready_to_support_use_runbooks.md)
- [OPS07-BP04 Use playbooks to investigate issues](ops_ready_to_support_use_playbooks.md)
- [OPS08-BP01 Analyze workload metrics](ops_workload_observability_analyze_workload_metrics.md)
- [OPS11-BP02 Perform post-incident analysis](ops_evolve_ops_perform_rca_process.md)
### Related Documents
- [AWS Security Incident Response Guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/welcome.html)
- [AWS Incident Detection and Response ](https://aws.amazon.com/premiumsupport/aws-incident-detection-response/)
- [AWS Cloud Adoption Framework: Operations Perspective - Incident and problem management ](https://docs.aws.amazon.com/whitepapers/latest/aws-caf-operations-perspective/incident-and-problem-management.html)
- [Incident Management in the Age of DevOps and SRE](https://www.infoq.com/presentations/incident-management-devops-sre/)
- [PagerDuty - What is Incident Management?](https://www.pagerduty.com/resources/learn/what-is-incident-management/)
### Related Videos
- [ Top incident response tips from AWS](https://www.youtube.com/watch?v=Cu20aOvnHwA)
- [AWS re:Invent 2022 - The Amazon Builders' Library: 25 yrs of Amazon operational excellence ](https://www.youtube.com/watch?v=DSRhgBd_gtw)
- [AWS re:Invent 2022 - AWS Incident Detection and Response (SUP201) ](https://www.youtube.com/watch?v=IbSgM4IP9IE)
- [ Introducing Incident Manager from AWS Systems Manager](https://www.youtube.com/watch?v=I6lScgh4qds)
### Related Examples
- [AWS Proactive Services – Incident Management Workshop](https://aws.amazon.com/premiumsupport/technology-and-programs/proactive-services/#Operational_Workshops_and_Deep_Dives)
- [ How to Automate Incident Response with PagerDuty and AWS Systems Manager Incident Manager](https://aws.amazon.com/blogs/mt/how-to-automate-incident-response-with-pagerduty-and-aws-systems-manager-incident-manager/)
- [ Engage Incident Responders with the On-Call Schedules in AWS Systems Manager Incident Manager](https://aws.amazon.com/blogs/mt/engage-incident-responders-with-the-on-call-schedules-in-aws-systems-manager-incident-manager/)
- [ Improve the Visibility and Collaboration during Incident Handling in AWS Systems Manager Incident Manager](https://aws.amazon.com/blogs/mt/improve-the-visibility-and-collaboration-during-incident-handling-in-aws-systems-manager-incident-manager/)
- [ Incident reports and service requests in AMS ](https://docs.aws.amazon.com/managedservices/latest/userguide/support-experience.html)
### Related Services
- [Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html)
