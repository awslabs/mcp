---
id: "REL13-BP03"
title: "Test disaster recovery implementation to validate the implementation"
framework: "WAF"
domain: "Reliability"
capability: "How do you plan for disaster recovery (DR)?"
risk_level: "High"
---

# REL13-BP03 Test disaster recovery implementation to validate the implementation

## Anti-Patterns
- Never exercise failovers in production.

## Implementation Guidance
 A pattern to avoid is developing recovery paths that are rarely exercised. For example, you might have a secondary data store that is used for read-only queries. When you write to a data store and the primary fails, you might want to fail over to the secondary data store. If you don’t frequently test this failover, you might find that your assumptions about the capabilities of the secondary data store are incorrect. The capacity of the secondary, which might have been sufficient when you last tested, might be no longer be able to tolerate the load under this scenario. Our experience has shown that the only error recovery that works is the path you test frequently. This is why having a small number of recovery paths is best. You can establish recovery patterns and regularly test them. If you have a complex or critical recovery path, you still need to regularly exercise that failure in production to convince yourself that the recovery path works. In the example we just discussed, you should fail over to the standby regularly, regardless of need.

## Implementation Steps
1.  Engineer your workloads for recovery. Regularly test your recovery paths. Recovery-oriented computing identifies the characteristics in systems that enhance recovery: isolation and redundancy, system-wide ability to roll back changes, ability to monitor and determine health, ability to provide diagnostics, automated recovery, modular design, and ability to restart. Exercise the recovery path to verify that you can accomplish the recovery in the specified time to the specified state. Use your runbooks during this recovery to document problems and find solutions for them before the next test.

1. For Amazon EC2-based workloads, use [AWS Elastic Disaster Recovery](https://docs.aws.amazon.com/drs/latest/userguide/what-is-drs.html) to implement and launch drill instances for your DR strategy. AWS Elastic Disaster Recovery provides the ability to efficiently run drills, which helps you prepare for a failover event. You can also frequently launch of your instances using Elastic Disaster Recovery for test and drill purposes without redirecting the traffic.

## Resources
### Related Documents
- [APN Partner: partners that can help with disaster recovery](https://aws.amazon.com/partners/find/results/?keyword=Disaster+Recovery)
- [AWS Architecture Blog: Disaster Recovery Series](https://aws.amazon.com/blogs/architecture/tag/disaster-recovery-series/)
- [AWS Marketplace: products that can be used for disaster recovery](https://aws.amazon.com/marketplace/search/results?searchTerms=Disaster+recovery)
- [AWS Elastic Disaster Recovery](https://aws.amazon.com/disaster-recovery/)
- [Disaster Recovery of Workloads on AWS: Recovery in the Cloud (AWS Whitepaper)](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html)
- [AWS Elastic Disaster Recovery Preparing for Failover](https://docs.aws.amazon.com/drs/latest/userguide/failback-preparing.html)
- [The Berkeley/Stanford recovery-oriented computing project](http://roc.cs.berkeley.edu/)
- [What is AWS Fault Injection Simulator?](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)
### Related Videos
- [AWS re:Invent 2018: Architecture Patterns for Multi-Region Active-Active Applications](https://youtu.be/2e29I3dA8o4)
- [AWS re:Invent 2019: Backup-and-restore and disaster-recovery solutions with AWS](https://youtu.be/7gNXfo5HZN8)
