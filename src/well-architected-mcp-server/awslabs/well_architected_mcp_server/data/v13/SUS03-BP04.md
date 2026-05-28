---
id: "SUS03-BP04"
title: "Optimize impact on devices and equipment"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of software and architecture patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS03-BP04 Optimize impact on devices and equipment

## Anti-Patterns
- You ignore the environmental impact of devices used by your customers.
- You manually manage and update resources used by customers.

## Implementation Guidance
 Implementing software patterns and features that are optimized for customer devices can reduce the environmental impact in several ways:
- Implementing new features that are backward compatible can reduce the number of hardware replacements.
- Optimizing an application to run efficiently on devices can help to reduce their energy consumption and extend their battery life (if they are powered by battery).
- Optimizing an application for devices can also reduce the data transfer over the network.

 Understand the devices and equipment used in your architecture, their expected lifecycle, and the impact of replacing those components. Implement software patterns and features that can help to minimize the device energy consumption, the need for customers to replace the device and also upgrade it manually.

## Implementation Steps
- **Conduct an inventory:** Inventory the devices used in your architecture. Devices can be mobile, tablet, IOT devices, smart light, or even smart devices in a factory.
- **Use energy-efficient devices:** Consider using energy-efficient devices in your architecture. Use power management configurations on devices to enter low power mode when not in use.
- **Run efficient applications:** Optimize the application running on the devices:
  - Use strategies such as running tasks in the background to reduce their energy consumption.
  - Account for network bandwidth and latency when building payloads, and implement capabilities that help your applications work well on low bandwidth, high latency links.
  - Convert payloads and files into optimized formats required by devices. For example, you can use [Amazon Elastic Transcoder](https://docs.aws.amazon.com/elastic-transcoder/) or [AWS Elemental MediaConvert](https://aws.amazon.com/mediaconvert/) to convert large, high quality digital media files into formats that users can play back on mobile devices, tablets, web browsers, and connected televisions.
  - Perform computationally intense activities server-side (such as image rendering), or use application streaming to improve the user experience on older devices.
  - Segment and paginate output, especially for interactive sessions, to manage payloads and limit local storage requirements.
- **Engage suppliers:** Work with device suppliers who use sustainable materials and provide transparency in their supply chains and environmental certifications.
- **Use over-the-air (OTA) updates:** Use automated over-the-air (OTA) mechanism to deploy updates to one or more devices.
  - You can use a [CI/CD pipeline](https://aws.amazon.com/blogs/mobile/build-a-cicd-pipeline-for-your-android-app-with-aws-services/) to update mobile applications.
  - You can use [AWS IoT Device Management](https://aws.amazon.com/iot-device-management/) to remotely manage connected devices at scale.
- **Use managed device farms:** To test new features and updates, use managed device farms with representative sets of hardware and iterate development to maximize the devices supported. For more details, see [SUS06-BP05 Use managed device farms for testing](sus_sus_dev_a5.md).
- **Continue to monitor and improve:** Track the energy usage of devices to identify areas for improvement. Use new technologies or best practices to enhance environmental impacts of these devices.

## Resources
### Related Documents
- [What is AWS Device Farm?](https://docs.aws.amazon.com/devicefarm/latest/developerguide/welcome.html)
- [AppStream 2.0 Documentation](https://docs.aws.amazon.com/appstream2/)
- [NICE DCV](https://docs.aws.amazon.com/dcv/)
- [ OTA tutorial for updating firmware on devices running FreeRTOS ](https://docs.aws.amazon.com/freertos/latest/userguide/dev-guide-ota-workflow.html)
- [ Optimizing Your IoT Devices for Environmental Sustainability ](https://aws.amazon.com/blogs/architecture/optimizing-your-iot-devices-for-environmental-sustainability/)
### Related Videos
- [AWS re:Invent 2023 - Improve your mobile and web app quality using AWS Device Farm](https://www.youtube.com/watch?v=__93Tm0YCRg)
