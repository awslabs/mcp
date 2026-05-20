---
id: "SUS06-BP05"
title: "Use managed device farms for testing"
framework: "WAF"
domain: "Sustainability"
capability: "How do your organizational processes support your sustainability goals?"
risk_level: "Low"
---

# SUS06-BP05 Use managed device farms for testing

## Anti-Patterns
- You manually test and deploy your application on individual physical devices.
- You do not use app testing service to test and interact with your apps (for example, Android, iOS, and web apps) on real, physical devices.

## Implementation Guidance
 Using Managed device farms can help you to streamline the testing process for new features on a representative set of hardware. Managed device farms offer diverse device types including older, less popular hardware, and avoid customer sustainability impact from unnecessary device upgrades.

## Implementation Steps
- **Define testing requirements**: Define your testing requirements and plan (like test type, operating systems, and test schedule).
  - You can use [Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html) to collect and analyze client-side data and shape your testing plan.
- **Select a managed device farm:** Select a managed device farm that can support your testing requirements. For example, you can use [AWS Device Farm](https://docs.aws.amazon.com/devicefarm/latest/developerguide/welcome.html) to test and understand the impact of your changes on a representative set of hardware.
- **Use automation:** Use automation and continuous integration/continuous deployment (CI/CD) to schedule and run your tests.
  - [Integrating AWS Device Farm with your CI/CD pipeline to run cross-browser Selenium tests](https://aws.amazon.com/blogs/devops/integrating-aws-device-farm-with-ci-cd-pipeline-to-run-cross-browser-selenium-tests/)
  - [Building and testing iOS and iPadOS apps with AWS DevOps and mobile services](https://aws.amazon.com/blogs/devops/building-and-testing-ios-and-ipados-apps-with-aws-devops-and-mobile-services/)
- **Review and adjust:** Continually review your testing results and make necessary improvements.

## Resources
### Related Documents
- [AWS Device Farm device list](https://awsdevicefarm.info/)
- [Viewing the CloudWatch RUM dashboard](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM-view-data.html)
### Related Videos
- [AWS re:Invent 2023 - Improve your mobile and web app quality using AWS Device Farm](https://www.youtube.com/watch?v=__93Tm0YCRg)
- [AWS re:Invent 2021 - Optimize applications through end user insights with Amazon CloudWatch RUM](https://www.youtube.com/watch?v=NMaeujY9A9Y)
### Related Examples
- [AWS Device Farm Sample App for Android](https://github.com/aws-samples/aws-device-farm-sample-app-for-android)
- [AWS Device Farm Sample App for iOS](https://github.com/aws-samples/aws-device-farm-sample-app-for-ios)
- [Appium Web tests for AWS Device Farm](https://github.com/aws-samples/aws-device-farm-sample-web-app-using-appium-python)
