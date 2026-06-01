---
id: "SUS06-BP05"
title: "Use managed device farms for testing"
pillar: "Sustainability"
risk_level: "LOW"
capability: "How do your organizational processes support your sustainability goals?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_dev_a5.html"
description: "Use managed device farms to efficiently test a new feature on a representative set of hardware."
area: ["Process and culture"]
---

# SUS06-BP05 Use managed device farms for testing

Use managed device farms to efficiently test a new feature on a
representative set of hardware.

**Common anti-patterns:**

- You manually test and deploy your application on individual
physical devices.
- You do not use app testing service to test and interact with
your apps (for example, Android, iOS, and web apps) on real,
physical devices.

**Benefits of establishing this best
practice:** Using managed device farms for testing
cloud-enabled applications provides a number of benefits:

- They include more efficient features to test application on wide
range of devices.
- They eliminate the need for in-house infrastructure for testing.
- They offer diverse device types, including older and less
popular hardware, which eliminates the need for unnecessary
device upgrades.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

Using Managed device farms can help you to streamline the testing
process for new features on a representative set of hardware.
Managed device farms offer diverse device types including older,
less popular hardware, and avoid customer sustainability impact
from unnecessary device upgrades.

### Implementation steps

- **Define testing
requirements**: Define your testing requirements and
plan (like test type, operating systems, and test schedule).

You can use
[Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html) to collect and analyze client-side
data and shape your testing plan.

- **Select a managed device
farm:** Select a managed device farm that can support
your testing requirements. For example, you can use
[AWS Device Farm](https://docs.aws.amazon.com/devicefarm/latest/developerguide/welcome.html) to test and understand the impact of your
changes on a representative set of hardware.
- **Use automation:** Use
automation and continuous integration/continuous deployment
(CI/CD) to schedule and run your tests.

[Integrating
AWS Device Farm with your CI/CD pipeline to run
cross-browser Selenium tests](https://aws.amazon.com/blogs/devops/integrating-aws-device-farm-with-ci-cd-pipeline-to-run-cross-browser-selenium-tests/)
- [Building
and testing iOS and iPadOS apps with AWS DevOps and mobile
services](https://aws.amazon.com/blogs/devops/building-and-testing-ios-and-ipados-apps-with-aws-devops-and-mobile-services/)

- **Review and adjust:**
Continually review your testing results and make necessary
improvements.

## Resources

**Related documents:**

- [AWS Device Farm
device list](https://awsdevicefarm.info/)
- [Viewing
the CloudWatch RUM dashboard](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM-view-data.html)

**Related videos:**

- [AWS re:Invent 2023 - Improve your mobile and web app quality using
AWS Device Farm](https://www.youtube.com/watch?v=__93Tm0YCRg)
- [AWS re:Invent 2021 - Optimize applications through end user
insights with Amazon CloudWatch RUM](https://www.youtube.com/watch?v=NMaeujY9A9Y)

**Related examples:**

- [AWS Device Farm Sample App for Android](https://github.com/aws-samples/aws-device-farm-sample-app-for-android)
- [AWS Device Farm Sample App for iOS](https://github.com/aws-samples/aws-device-farm-sample-app-for-ios)
- [Appium
Web tests for AWS Device Farm](https://github.com/aws-samples/aws-device-farm-sample-web-app-using-appium-python)
