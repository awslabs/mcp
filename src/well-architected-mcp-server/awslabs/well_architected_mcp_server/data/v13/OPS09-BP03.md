---
id: "OPS09-BP03"
title: "Review operations metrics and prioritize improvement"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you understand the health of your operations?"
risk_level: "Medium"
---

# OPS09-BP03 Review operations metrics and prioritize improvement

## Desired Outcome
- Operations leaders and staff regularly meet to review metrics over a given reporting period. Challenges are communicated, wins are celebrated, and lessons learned are shared.
- Stakeholders and business leaders are regularly briefed on the state of operations and solicited for input regarding goals, KPIs, and future initiatives. Tradeoffs between service delivery, operations, and maintenance are discussed and placed into context.

## Anti-Patterns
- A new product is launched, but the Tier 1 and Tier 2 operations teams are not adequately trained to support or given additional staff. Metrics that show the decrease in ticket resolution times and increase in incident volumes are not seen by leaders. Action is taken weeks later when subscription numbers start to fall as discontent users move off the platform.
- A manual process for performing maintenance on a workload has been in place for a long time. While a desire to automate has been present, this was a low priority given the low importance of the system. Over time however, the system has grown in importance and now these manual processes consume a majority of operations' time. No resources are scheduled for providing increased tooling to operations, leading to staff burnout as workloads increase. Leadership becomes aware once it's reported that staff are leaving for other competitors.

## Implementation Guidance
 Dedicate time to review operations metrics between stakeholders and operations teams and review report data. Place these reports in the contexts of the organizations goals and objectives to determine if they're being met. Identify sources of ambiguity where goals are not clear, or where there may be conflicts between what is asked for and what is given.

 Identify where time, people, and tools can aid in operations outcomes. Determine which KPIs this would impact and what targets for success should be. Revisit regularly to ensure operations is resourced sufficiently to support the line of business.

## Resources
### Related Documents
- [ Amazon Athena ](https://aws.amazon.com/athena/)
- [ Amazon CloudWatch metrics and dimensions reference ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CW_Support_For_AWS.html)
- [ Amazon Quick Suite ](https://aws.amazon.com/quicksight/)
- [AWS Glue](https://aws.amazon.com/glue/)
- [AWS Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/populate-data-catalog.html)
- [ Collect metrics and logs from Amazon EC2 instances and on-premises servers with the Amazon CloudWatch Agent ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [ Using Amazon CloudWatch metrics ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)
