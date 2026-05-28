---
id: "OPS09-BP01"
title: "Measure operations goals and KPIs with metrics"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you understand the health of your operations?"
risk_level: "Medium"
---

# OPS09-BP01 Measure operations goals and KPIs with metrics

## Desired Outcome
- The organization publishes and shares the goals and KPIs for the operations teams.
- You establish metrics that reflect these KPIs. Examples may include:
  - Ticket queue depth or average age of ticket
  - Ticket count grouped by type of issue
  - Time spent working issues with or without a standardized operating procedure (SOP)
  - Amount of time spent recovering from a failed code push
  - Call volume

## Anti-Patterns
- Deployment deadlines are missed because developers are pulled away to perform troubleshooting tasks. Development teams argue for more personnel, but cannot quantify how many they need because the time taken away cannot be measured.
- A Tier 1 desk was set up to handle user calls. Over time, more workloads were added, but no headcount was allocated to the Tier 1 desk. Customer satisfaction suffers as call times increase and issues go longer without resolution, but management sees no indicators of such, preventing any action.
- A problematic workload has been handed off to a separate operations team for upkeep. Unlike other workloads, this new one was not supplied with proper documentation and runbooks. As such, teams spend longer troubleshooting and addressing failures. However, there are no metrics documenting this, which makes accountability difficult.

## Implementation Guidance
Schedule time with business leaders and stakeholders to determine what the overall goals of the service will be. Determine what the tasks of various operations teams should be and what challenges they could be approached with. Using these, brainstorm key performance indicators (KPIs) that might reflect these operations goals. These might be customer satisfaction, time from feature conception to deployment, average issue resolution time, or cost efficiencies.

 Working from KPIs, identify the metrics and sources of data that might reflect these goals best. Customer satisfaction may be an combination of various metrics such as call wait or response times, satisfaction scores, and types of issues raised. Deployment times may be the sum of time needed for testing and deployment, plus any post-deployment fixes that needed to be added. Statistics showing the time spent on different types of issues (or the counts of those issues) can provide a window into where targeted effort is needed.

## Resources
### Related Documents
- [ Quick Suite - Using KPIs ](https://docs.aws.amazon.com/quicksight/latest/user/kpi.html)
- [ Amazon CloudWatch - Using Metrics ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)
- [ Building Dashboards ](https://aws.amazon.com/builders-library/building-dashboards-for-operational-visibility/)
- [ How to track your cost optimization KPIs with KPI Dashboard ](https://aws.amazon.com/blogs/aws-cloud-financial-management/how-to-track-your-cost-optimization-kpis-with-the-kpi-dashboard/)
- [AWS DevOps Guidance ](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/devops-guidance.html)
### Related Examples
- [ Monitor the performance of your software delivery using native AWS monitoring and observability tools ](https://catalog.us-east-1.prod.workshops.aws/workshops/3b7f3d77-c6ef-44b2-aa29-d2719b8be897/en-US)
- [ Balance deployment speed and stability with DORA metrics ](https://aws.amazon.com/blogs/devops/balance-deployment-speed-and-stability-with-dora-metrics/)
- [ Example MLOps operational metrics in the financial services industry ](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-unlock-value-data-financial-services/operational-metrics.html)
- [ How to track your cost optimization KPIs with the KPI Dashboard ](https://aws.amazon.com/blogs/aws-cloud-financial-management/how-to-track-your-cost-optimization-kpis-with-the-kpi-dashboard/)
