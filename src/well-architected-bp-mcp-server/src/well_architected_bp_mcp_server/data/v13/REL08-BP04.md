---
id: "REL08-BP04"
title: "Deploy using immutable infrastructure"
framework: "WAF"
domain: "Reliability"
capability: "How do you implement change?"
risk_level: "Medium"
---

# REL08-BP04 Deploy using immutable infrastructure

## Desired Outcome
With immutable infrastructure, no [in-place modifications](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/deployment-strategies.html#in-place-deployments) are allowed to run infrastructure resources within a workload. Instead, when a change is needed, a new set of updated infrastructure resources containing all the necessary changes are deployed in parallel to your existing resources. This deployment is validated automatically, and if successful, traffic is gradually shifted to the new set of resources.

 This deployment strategy applies to software updates, security patches, infrastructure changes, configuration updates, and application updates, among others.

## Anti-Patterns
- Implementing in-place changes to running infrastructure resources.

## Implementation Guidance
 **Automation**

 When defining an immutable infrastructure deployment strategy, it is recommended to use [automation](https://aws.amazon.com/iam/) as much as possible to increase reproducibility and minimize the potential of human error. For more detail, see [REL08-BP05 Deploy changes with automation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_automated_changemgmt.html) and [Automating safe, hands-off deployments](https://aws.amazon.com/builders-library/automating-safe-hands-off-deployments/).

 With [infrastructure as code (IaC)](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/infrastructure-as-code.html), infrastructure provisioning, orchestration, and deployment steps are defined in a programmatic, descriptive, and declarative way and stored in a source control system. Leveraging infrastructure as code makes it simpler to automate infrastructure deployment and helps achieve infrastructure immutability.

 **Deployment patterns**

 When a change in the workload is required, the immutable infrastructure deployment strategy mandates that a new set of infrastructure resources is deployed, including all necessary changes. It is important for this new set of resources to follow a rollout pattern that minimizes user impact. There are two main strategies for this deployment:

 [https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/canary-deployments.html](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/canary-deployments.html): The practice of directing a small number of your customers to the new version, usually running on a single service instance (the canary). You then deeply scrutinize any behavior changes or errors that are generated. You can remove traffic from the canary if you encounter critical problems and send the users back to the previous version. If the deployment is successful, you can continue to deploy at your desired velocity, while monitoring the changes for errors, until you are fully deployed. AWS CodeDeploy can be configured with a [deployment configuration](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html) that allows a canary deployment.

 [https://docs.aws.amazon.com/whitepapers/latest/overview-deployment-options/bluegreen-deployments.html](https://docs.aws.amazon.com/whitepapers/latest/overview-deployment-options/bluegreen-deployments.html): Similar to the canary deployment, except that a full fleet of the application is deployed in parallel. You alternate your deployments across the two stacks (blue and green). Once again, you can send traffic to the new version, and fall back to the old version if you see problems with the deployment. Commonly all traffic is switched at once, however you can also use fractions of your traffic to each version to dial up the adoption of the new version using the weighted DNS routing capabilities of Amazon Route 53. AWS CodeDeploy and [AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/relnotes/release-2020-05-18-ts-deploy.html) can be configured with a deployment configuration that allows a blue/green deployment.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/blue-green-deployment.png)

 **Drift detection**

 *Drift* is defined as any change that causes an infrastructure resource to have a different state or configuration to what is expected. Any type of unmanaged configuration change goes against the notion of immutable infrastructure, and should be detected and remediated in order to have a successful implementation of immutable infrastructure.

## Implementation Steps
- Disallow the in-place modification of running infrastructure resources.
  - You can use [AWS Identity and Access Management (IAM)](https://aws.amazon.com/iam/) to specify who or what can access services and resources in AWS, centrally manage fine-grained permissions, and analyze access to refine permissions across AWS.
- Automate the deployment of infrastructure resources to increase reproducibility and minimize the potential of human error.
  - As described in the [Introduction to DevOps on AWS whitepaper](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/automation.html), automation is a cornerstone with AWS services and is internally supported in all services, features, and offerings.
  - *[Prebaking](https://docs.aws.amazon.com/whitepapers/latest/overview-deployment-options/prebaking-vs.-bootstrapping-amis.html)* your Amazon Machine Image (AMI) can speed up the time to launch them. [EC2 Image Builder](https://aws.amazon.com/image-builder/) is a fully managed AWS service that helps you automate the creation, maintenance, validation, sharing, and deployment of customized, secure, and up-to-date Linux or Windows custom AMI.
  - Some of the services that support automation are:
    - [AWS Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/) is a service to rapidly deploy and scale web applications developed with Java, .NET, PHP, Node.js, Python, Ruby, Go, and Docker on familiar servers such as Apache, NGINX, Passenger, and IIS.
    - [AWS Proton](https://aws.amazon.com/proton/) helps platform teams connect and coordinate all the different tools your development teams need for infrastructure provisioning, code deployments, monitoring, and updates. AWS Proton enables automated infrastructure as code provisioning and deployment of serverless and container-based applications.
  - Leveraging infrastructure as code makes it easy to automate infrastructure deployment, and helps achieve infrastructure immutability. AWS provides services that enable the creation, deployment, and maintenance of infrastructure in a programmatic, descriptive, and declarative way.
    - [AWS CloudFormation](https://aws.amazon.com/cloudformation/) helps developers create AWS resources in an orderly and predictable fashion. Resources are written in text files using JSON or YAML format. The templates require a specific syntax and structure that depends on the types of resources being created and managed. You author your resources in JSON or YAML with any code editor, check it into a version control system, and then AWS CloudFormation builds the specified services in safe, repeatable manner.
    - [AWS Serverless Application Model (AWS SAM)](https://aws.amazon.com/serverless/sam/) is an open-source framework that you can use to build serverless applications on AWS. AWS SAM integrates with other AWS services, and is an extension of AWS CloudFormation.
    - [AWS Cloud Development Kit (AWS CDK)](https://aws.amazon.com/cdk/) is an open-source software development framework to model and provision your cloud application resources using familiar programming languages. You can use AWS CDK to model application infrastructure using TypeScript, Python, Java, and .NET. AWS CDK uses AWS CloudFormation in the background to provision resources in a safe, repeatable manner.
    - [AWS Cloud Control API](https://aws.amazon.com/cloudcontrolapi/) introduces a common set of Create, Read, Update, Delete, and List (CRUDL) APIs to help developers manage their cloud infrastructure in an easy and consistent way. The Cloud Control API common APIs allow developers to uniformly manage the lifecycle of AWS and third-party services.
- Implement deployment patterns that minimize user impact.
  - Canary deployments:
    - [ Set up an API Gateway canary release deployment ](https://docs.aws.amazon.com/apigateway/latest/developerguide/canary-release.html)
    - [ Create a pipeline with canary deployments for Amazon ECS using AWS App Mesh](https://aws.amazon.com/blogs/containers/create-a-pipeline-with-canary-deployments-for-amazon-ecs-using-aws-app-mesh/)
  - Blue/green deployments: the [Blue/Green Deployments on AWS whitepaper](https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/welcome.html) describes [example techniques](https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/implementation-techniques.html) to implement blue/green deployment strategies.
- Detect configuration or state drifts. For more detail, see [Detecting unmanaged configuration changes to stacks and resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html).

## Resources
### Related Best Practices
- [ REL08-BP05 Deploy changes with automation ](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_automated_changemgmt.html)
### Related Documents
- [ Automating safe, hands-off deployments ](https://aws.amazon.com/builders-library/automating-safe-hands-off-deployments/)
- [ Leveraging AWS CloudFormation to create an immutable infrastructure at Nubank ](https://aws.amazon.com/blogs/mt/leveraging-immutable-infrastructure-nubank/)
- [ Infrastructure as code ](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/infrastructure-as-code.html)
- [ Implementing an alarm to automatically detect drift in AWS CloudFormation stacks ](https://docs.aws.amazon.com/blogs/mt/implementing-an-alarm-to-automatically-detect-drift-in-aws-cloudformation-stacks/)
### Related Videos
- [AWS re:Invent 2020: Reliability, consistency, and confidence through immutability ](https://www.youtube.com/watch?v=jUSYnRztttY)
