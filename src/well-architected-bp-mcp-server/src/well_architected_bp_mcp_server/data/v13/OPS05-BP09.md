---
id: "OPS05-BP09"
title: "Make frequent, small, reversible changes"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
risk_level: "Low"
---

# OPS05-BP09 Make frequent, small, reversible changes

## Anti-Patterns
- You deploy a new version of your application quarterly with a change window that means a core service is turned off.
- You frequently make changes to your database schema without tracking changes in your management systems.
- You perform manual in-place updates, overwriting existing installations and configurations, and have no clear roll-back plan.

## Implementation Guidance
 Use frequent, small, and reversible changes to reduce the scope and impact of a change. This eases troubleshooting, helps with faster remediation, and provides the option to roll back a change. It also increases the rate at which you can deliver value to the business.

## Resources
### Related Best Practices
- [OPS05-BP03 Use configuration management systems](ops_dev_integ_conf_mgmt_sys.md)
- [OPS05-BP04 Use build and deployment management systems](ops_dev_integ_build_mgmt_sys.md)
- [OPS06-BP04 Automate testing and rollback](ops_mit_deploy_risks_auto_testing_and_rollback.md)
### Related Documents
- [ Implementing Microservices on AWS](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/microservices-on-aws.html)
- [ Microservices - Observability ](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/observability.html)
