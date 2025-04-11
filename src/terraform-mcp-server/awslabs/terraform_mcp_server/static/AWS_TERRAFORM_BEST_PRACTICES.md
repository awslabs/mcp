# AWS Terraform Provider Best Practices

_This document was automatically extracted from the AWS Prescriptive Guidance PDF._

_Source: [https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/terraform-aws-provider-best-practices/terraform-aws-provider-best-practices.pdf](https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/terraform-aws-provider-best-practices/terraform-aws-provider-best-practices.pdf)_

## Best practices for using the Terraform AWS Provider

## AWS Prescriptive Guidance

Copyright © 2025 Amazon Web Services, Inc. and/or its aﬃliates. All rights reserved.

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

AWS Prescriptive Guidance: Best practices for using the Terraform

## AWS Provider

Copyright © 2025 Amazon Web Services, Inc. and/or its aﬃliates. All rights reserved.

Amazon's trademarks and trade dress may not be used in connection with any product or service

that is not Amazon's, in any manner that is likely to cause confusion among customers, or in any

manner that disparages or discredits Amazon. All other trademarks not owned by Amazon are

the property of their respective owners, who may or may not be aﬃliated with, connected to, or

sponsored by Amazon.

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Table of Contents

Introduction.....................................................................................................................................1

Objectives.......................................................................................................................................................1

Target audience.............................................................................................................................................2

Overview..........................................................................................................................................3

Security best practices....................................................................................................................5

Follow the principle of least privilege.....................................................................................................5

Use IAM roles................................................................................................................................................6

Grant least privilege access by using IAM policies...........................................................................6

Assume IAM roles for local authentication........................................................................................6

Use IAM roles for Amazon EC2 authentication.................................................................................8

Use dynamic credentials for HCP Terraform workspaces...............................................................9

Use IAM roles in AWS CodeBuild.........................................................................................................9

Run GitHub Actions remotely on HCP Terraform.............................................................................9

Use GitHub Actions with OIDC and conﬁgure the AWS Credentials action.................................9

Use GitLab with OIDC and the AWS CLI............................................................................................9

Use unique IAM users with legacy automation tools.........................................................................10

Use the Jenkins AWS Credentials plugin.........................................................................................10

Continuously monitor, validate, and optimize least privilege...........................................................10

Continuously monitor access key usage..........................................................................................10

Continually validate IAM policies .........................................................................................................6

Secure remote state storage...................................................................................................................11

Enable encryption and access controls............................................................................................12

Limit direct access to collaborative workﬂows...............................................................................12

Use AWS Secrets Manager.......................................................................................................................12

Continuously scan infrastructure and source code.............................................................................12

Use AWS services for dynamic scanning..........................................................................................13

Perform static analysis........................................................................................................................13

Ensure prompt remediation................................................................................................................13

Enforce policy checks................................................................................................................................13

Backend best practices..................................................................................................................15

Use Amazon S3 for remote storage.......................................................................................................16

Enable remote state locking..............................................................................................................16

Enable versioning and automatic backups......................................................................................16

Restore previous versions if needed.................................................................................................17

iii

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Use HCP Terraform...............................................................................................................................17

Facilitate team collaboration...................................................................................................................17

Improve accountability by using AWS CloudTrail..........................................................................17

Separate the backends for each environment.....................................................................................18

Reduce the scope of impact...............................................................................................................18

Restrict production access..................................................................................................................18

Simplify access controls......................................................................................................................18

Avoid shared workspaces....................................................................................................................19

Actively monitor remote state activity..................................................................................................19

Get alerts on suspicious unlocks.......................................................................................................19

Monitor access attempts.....................................................................................................................19

Best practices for code base structure and organization............................................................20

Implement a standard repository structure.........................................................................................21

Root module structure.........................................................................................................................24

Reusable module structure.................................................................................................................24

Structure for modularity..........................................................................................................................25

Don't wrap single resources...............................................................................................................26

Encapsulate logical relationships......................................................................................................26

Keep inheritance ﬂat............................................................................................................................26

Reference resources in outputs..........................................................................................................26

Don't conﬁgure providers....................................................................................................................26

Declare required providers..................................................................................................................27

Follow naming conventions.....................................................................................................................28

Follow guidelines for resource naming............................................................................................28

Follow guidelines for variable naming.............................................................................................28

Use attachment resources........................................................................................................................29

Use default tags .........................................................................................................................................30

Meet Terraform registry requirements..................................................................................................30

Use recommended module sources.......................................................................................................31

Registry...................................................................................................................................................31

VCS providers.........................................................................................................................................32

Follow coding standards...........................................................................................................................33

Follow style guidelines........................................................................................................................34

Conﬁgure pre-commit hooks.............................................................................................................34

Best practices for AWS Provider version management...............................................................35

Add automated version checks...............................................................................................................35

iv

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Monitor new releases................................................................................................................................35

Contribute to providers............................................................................................................................36

Best practices for community modules........................................................................................37

Discover community modules.................................................................................................................37

Use variables for customization ........................................................................................................37

Understand dependencies ........................................................................................................................37

Use trusted sources...................................................................................................................................38

Subscribe to notiﬁcations ...................................................................................................................38

Contribute to community modules........................................................................................................38

FAQ.................................................................................................................................................40

Next steps......................................................................................................................................41

Resources........................................................................................................................................42

References....................................................................................................................................................42

Tools..............................................................................................................................................................42

Document history..........................................................................................................................43

Glossary..........................................................................................................................................44

#.....................................................................................................................................................................44

A.....................................................................................................................................................................45

B.....................................................................................................................................................................48

C.....................................................................................................................................................................50

D.....................................................................................................................................................................53

E.....................................................................................................................................................................57

F.....................................................................................................................................................................59

G.....................................................................................................................................................................61

H.....................................................................................................................................................................62

I......................................................................................................................................................................63

L.....................................................................................................................................................................65

M....................................................................................................................................................................67

O....................................................................................................................................................................71

P.....................................................................................................................................................................73

Q....................................................................................................................................................................76

R.....................................................................................................................................................................76

S.....................................................................................................................................................................79

T.....................................................................................................................................................................83

U.....................................................................................................................................................................84

V.....................................................................................................................................................................85

v

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

W....................................................................................................................................................................85

Z.....................................................................................................................................................................86

vi

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Best practices for using the Terraform AWS Provider

Michael Begin, Senior DevOps Consultant, Amazon Web Services (AWS)

May 2024  (document history)

Managing infrastructure as code (IaC) with Terraform on AWS oﬀers important beneﬁts such as

improved consistency, security, and agility. However, as your Terraform conﬁguration grows in size

and complexity, it becomes critical to follow best practices to avoid pitfalls.

This guide provides recommended best practices for using the Terraform AWS Provider from

HashiCorp. It walks you through proper versioning, security controls, remote backends, codebase

structure, and community providers to optimize Terraform on AWS. Each section dives into more

details on the speciﬁcs of applying these best practices:

*Security

*Backends

*Code base structure and organization

*AWS Provider version management

*Community modules

## Objectives

This guide helps you gain operational knowledge on the Terraform AWS Provider and addresses

the following business goals that you can achieve by following IaC best practices around security,

reliability, compliance, and developer productivity.

*Improve infrastructure code quality and consistency across Terraform projects.

*Accelerate developer onboarding and ability to contribute to infrastructure code.

*Increase business agility through faster infrastructure changes.

*Reduce errors and downtime related to infrastructure changes.

*Optimize infrastructure costs by following IaC best practices.

*Strengthen your overall security posture through best practice implementation.

Objectives 1

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Target audience

The target audience for this guide includes technical leads and managers who oversee teams

that use Terraform for IaC on AWS. Other potential readers include infrastructure engineers,

DevOps engineers, solutions architects, and developers who actively use Terraform to manage AWS

infrastructure.

Following these best practices will save time and help unlock the beneﬁts of IaC for these roles.

Target audience 2

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Overview

Terraform providers are plugins that allow Terraform to interact with diﬀerent APIs. The Terraform

AWS Provider is the oﬃcial plugin for managing AWS infrastructure as code (IaC) with Terraform. It

translates Terraform syntax into AWS API calls to create, read, update, and delete AWS resources.

The AWS Provider handles authentication, translating Terraform syntax to AWS API calls, and

provisioning resources in AWS. You use a Terraform provider  code block to conﬁgure the provider

plugin that Terraform uses to interact with the AWS API. You can conﬁgure multiple AWS Provider

blocks to manage resources across diﬀerent AWS accounts and Regions.

Here's an example Terraform conﬁguration that uses multiple AWS Provider blocks with aliases

to manage an Amazon Relational Database Service (Amazon RDS) database that has a replica in a

diﬀerent Region and account. The primary and secondary providers assume diﬀerent AWS Identity

and Access Management (IAM) roles:

# Configure the primary AWS Provider

provider "aws" {

region = "us-west-1"

alias  = "primary"

}

# Configure a secondary AWS Provider for the replica Region and account

provider "aws" {

region      = "us-east-1"

alias       = "replica"

assume_role {

role_arn     = "arn:aws:iam::<replica-account-id>:role/<role-name>"

session_name = "terraform-session"

}

}

# Primary Amazon RDS database

resource "aws_db_instance" "primary" {

provider = aws.primary

# ... RDS instance configuration

}

# Read replica in a different Region and account

resource "aws_db_instance" "read_replica" {

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

provider = aws.replica

# ... RDS read replica configuration

replicate_source_db = aws_db_instance.primary.id

}

In this example:

*The ﬁrst provider  block conﬁgures the primary AWS Provider in the us-west-1  Region with

the alias primary .

*The second provider  block conﬁgures a secondary AWS Provider in the us-east-1  Region

with the alias replica. This provider is used to create a read replica of the primary database in

a diﬀerent Region and account. The assume_role  block is used to assume an IAM role in the

replica account. The role_arn  speciﬁes the Amazon Resource Name (ARN) of the IAM role to

assume, and session_name  is a unique identiﬁer for the Terraform session.

*The aws_db_instance.primary  resource creates the primary Amazon RDS database by using

the primary provider in the us-west-1  Region.

*The aws_db_instance.read_replica  resource creates a read replica of the primary database

in the us-east-1  Region by using the replica provider. The replicate_source_db

attribute references the ID of the primary  database.

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Security best practices

Properly managing authentication, access controls, and security is critical for secure usage of the

Terraform AWS Provider. This section outlines best practices around:

*IAM roles and permissions for least-privilege access

*Securing credentials to help prevent unauthorized access to AWS accounts and resources

*Remote state encryption to help protect sensitive data

*Infrastructure and source code scanning to identify misconﬁgurations

*Access controls for remote state storage

*Sentinel policy enforcement to implement governance guardrails

Following these best practices helps strengthen your security posture when you use Terraform to

manage AWS infrastructure.

## Follow the principle of least privilege

Least privilege  is a fundamental security principle that refers to granting only the minimum

permissions required for a user, process, or system to perform its intended functions. It's a core

concept in access control and a preventative measure against unauthorized access and potential

data breaches.

The principle of least privilege is emphasized multiple times in this section because it directly

relates to how Terraform authenticates and runs actions against cloud providers such as AWS.

When you use Terraform to provision and manage AWS resources, it acts on behalf of an entity

(user or role) that requires appropriate permissions to make API calls. Not following least privilege

opens up major security risks:

*If Terraform has excessive permissions beyond what's needed, an unintended misconﬁguration

could make undesired changes or deletions.

*Overly permissive access grants increase the scope of impact if Terraform state ﬁles or

credentials are compromised.

*Not following least privilege goes against security best practices and regulatory compliance

requirements for granting minimal required access.

Follow the principle of least privilege 5

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Use IAM roles

Use IAM roles instead of IAM users wherever possible to enhance security with the Terraform

AWS Provider. IAM roles provide temporary security credentials that automatically rotate, which

eliminates the need to manage long-term access keys. Roles also oﬀer precise access controls

through IAM policies.

## Grant least privilege access by using IAM policies

Carefully construct IAM policies to ensure that roles and users have only the minimum set of

permissions that are required for their workload. Start with an empty policy and iteratively add

allowed services and actions. To accomplish this:

*Enable IAM Access Analyzer to evaluate policies and highlight unused permissions that can be

removed.

*Manually review policies to remove any capabilities that aren't essential for the role's intended

responsibility.

*Use IAM policy variables and tags to simplify permission management.

Well-constructed policies grant just enough access to accomplish the workload's responsibilities

and nothing more. Deﬁne actions at the operation level, and allow calls only to required APIs on

speciﬁc resources.

Following this best practice reduces the scope of impact and follows the fundamental security

principles of separation of duties and least privilege access. Start strict and open access gradually

as needed, instead of starting open and trying to restrict access later.

## Assume IAM roles for local authentication

When you run Terraform locally, avoid conﬁguring static access keys. Instead, use IAM roles to grant

privileged access temporarily without exposing long-term credentials.

First, create an IAM role with the necessary minimum permissions and add a trust relationship

that allows the IAM role to be assumed by your user account or federated identity. This authorizes

temporary usage of the role.

Trust relationship policy example:

Use IAM roles 6

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

{

"Version": "2012-10-17",

"Statement": [

{

"Effect": "Allow",

"Principal": {

"AWS": "arn:aws:iam::111122223333:role/terraform-execution"

},

"Action": "sts:AssumeRole"

}

]

}

Then, run the AWS CLI command aws sts assume-role to retrieve short-lived credentials for the

role. These credentials are typically valid for one hour.

AWS CLI command example:

aws sts assume-role --role-arn arn:aws:iam::111122223333:role/terraform-execution --

role-session-name terraform-session-example

The output of the command contains an access key, secret key, and session token that you can use

to authenticate to AWS:

{

"AssumedRoleUser": {

"AssumedRoleId": "AROA3XFRBF535PLBIFPI4:terraform-session-example",

"Arn": "arn:aws:sts::111122223333:assumed-role/terraform-execution/terraform-

session-example"

},

"Credentials": {

"SecretAccessKey": " wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",

"SessionToken": " AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT

+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/

IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/

AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE",

"Expiration": "2024-03-15T00:05:07Z",

"AccessKeyId": ...

}

}

The AWS Provider can also automatically handle assuming the role.

Assume IAM roles for local authentication 7

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Provider conﬁguration example for assuming an IAM role:

provider "aws" {

assume_role {

role_arn     = "arn:aws:iam::111122223333:role/terraform-execution"

session_name = "terraform-session-example"

}

}

This grants elevated privilege strictly for the Terraform session's duration. The temporary keys

cannot be leaked because they expire automatically after the maximum duration of the session.

The key beneﬁts of this best practice include improved security compared with long-lived access

keys, ﬁne-grained access controls on the role for least privileges, and the ability to easily revoke

access by modifying the role's permissions. By using IAM roles, you also avoid having to directly

store secrets locally in scripts or on disk, which helps you share Terraform conﬁguration securely

across a team.

Use IAM roles for Amazon EC2 authentication

When you run Terraform from Amazon Elastic Compute Cloud (Amazon EC2) instances, avoid

storing long-term credentials locally. Instead, use IAM roles and instance proﬁles to grant least-

privilege permissions automatically.

First, create an IAM role with the minimum permissions and assign the role to the instance proﬁle.

The instance proﬁle allows EC2 instances to inherit the permissions deﬁned in the role. Then,

launch instances by specifying that instance proﬁle. The instance will authenticate through the

attached role.

Before you run any Terraform operations, verify that the role is present in the instance metadata to

conﬁrm that the credentials were successfully inherited.

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-

metadata-token-ttl-seconds: 21600")

curl -H "X-aws-ec2-metadata-token: $TOKEN" -s http://169.254.169.254/latest/meta-data/

iam/security-credentials/

This approach avoids hardcoding permanent AWS keys into scripts or Terraform conﬁguration

within the instance. The temporary credentials are made available to Terraform transparently

through the instance role and proﬁle.

Use IAM roles for Amazon EC2 authentication 8

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

The key beneﬁts of this best practice include improved security over long-term credentials,

reduced credential management overhead, and consistency between development, test, and

production environments. IAM role authentication simpliﬁes Terraform runs from EC2 instances

while enforcing least-privilege access.

## Use dynamic credentials for HCP Terraform workspaces

HCP Terraform is a managed service provided by HashiCorp that helps teams use Terraform to

provision and manage infrastructure across multiple projects and environments. When you run

Terraform in HCP Terraform, use dynamic credentials to simplify and secure AWS authentication.

Terraform automatically exchanges temporary credentials on each run without needing IAM role

assumption.

Beneﬁts include easier secret rotation, centralized credential management across workspaces,

least-privilege permissions, and eliminating hardcoded keys. Relying on hashed ephemeral keys

enhances security compared with long-lived access keys.

## Use IAM roles in AWS CodeBuild

In AWS CodeBuild, run your builds by using an IAM role that's assigned to the CodeBuild project.

This allows each build to automatically inherit temporary credentials from the role instead of using

long-term keys.

## Run GitHub Actions remotely on HCP Terraform

Conﬁgure GitHub Actions workﬂows to run Terraform remotely on HCP Terraform workspaces. Rely

on dynamic credentials and remote state locking instead of GitHub secrets management.

Use GitHub Actions with OIDC and conﬁgure the AWS Credentials

action

Use the OpenID Connect (OIDC) standard to federate GitHub Actions identity through IAM. Use the

Conﬁgure AWS Credentials action to exchange the GitHub token for temporary AWS credentials

without needing long-term access keys.

## Use GitLab with OIDC and the AWS CLI

Use the OIDC standard to federate GitLab identities through IAM for temporary access. By

relying on OIDC, you avoid having to directly manage long-term AWS access keys within GitLab.

Use dynamic credentials for HCP Terraform workspaces 9

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Credentials are exchanged just-in-time, which improves security. Users also gain least privilege

access according to the permissions in the IAM role.

## Use unique IAM users with legacy automation tools

If you have automation tools and scripts that lack native support for using IAM roles, you can

create individual IAM users to grant programmatic access. The principle of least privilege still

applies. Minimize policy permissions and rely on separate roles for each pipeline or script. As you

migrate to more modern tools or scripts, begin supporting roles natively and gradually transition

to them.

## Warning

IAM users have long-term credentials, which present a security risk. To help mitigate this

risk, we recommend that you provide these users with only the permissions they require to

perform the task and that you remove these users when they are no longer needed.

## Use the Jenkins AWS Credentials plugin

Use the AWS Credentials plugin in Jenkins to centrally conﬁgure and inject AWS credentials into

builds dynamically. This avoids checking secrets into source control.

Continuously monitor, validate, and optimize least privilege

Over time, additional permissions might get granted that can exceed the minimum policies

required. Continuously analyze access to identify and remove any unnecessary entitlements.

## Continuously monitor access key usage

If you cannot avoid using access keys, use IAM credential reports to ﬁnd unused access keys that

are older than 90 days, and revoke inactive keys across both user accounts and machine roles. Alert

administrators to manually conﬁrm the removal of keys for active employees and systems.

Monitoring key usage helps you optimize permissions because you can identify and remove unused

entitlements. When you follow this best practice with access key rotation, it limits credential

lifespan and enforces least privilege access.

Use unique IAM users with legacy automation tools 10

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

AWS provides several services and features that you can use to set up alerts and notiﬁcations for

administrators. Here are some options:

*AWS Conﬁg: You can use AWS Conﬁg rules to evaluate the conﬁguration settings of your AWS

resources, including IAM access keys. You can create custom rules to check for speciﬁc conditions,

such as unused access keys that are older than a speciﬁc number of days. When a rule is violated,

AWS Conﬁg can start an evaluation for remediation or send notiﬁcations to an Amazon Simple

Notiﬁcation Service (Amazon SNS) topic.

*AWS Security Hub: Security Hub provides a comprehensive view of your AWS account's security

posture and can help detect and notify you about potential security issues, including unused or

inactive IAM access keys. Security Hub can integrate with Amazon EventBridge and Amazon SNS

or Amazon Q Developer in chat applications to send notiﬁcations to administrators.

*AWS Lambda: Lambda functions can be called by various events, including Amazon CloudWatch

Events or AWS Conﬁg rules. You can write custom Lambda functions to evaluate IAM access key

usage, perform additional checks, and send notiﬁcations by using services such as Amazon SNS

or Amazon Q Developer in chat applications.

## Continually validate IAM policies

Use IAM Access Analyzer to evaluate policies that are attached to roles and identify any unused

services or excess actions that were granted. Implement periodic access reviews to manually verify

that policies match current requirements.

Compare the existing policy with the policy generated by IAM Access Analyzer and remove any

unnecessary permissions. You should also provide reports to users and automatically revoke

unused permissions after a grace period. This helps ensure that minimal policies remain in eﬀect.

Proactively and frequently revoking obsolete access minimizes the credentials that might be at risk

during a breach. Automation provides sustainable, long-term credential hygiene and permissions

optimization. Following this best practice limits the scope of impact by proactively enforcing least

privilege across AWS identities and resources.

## Secure remote state storage

Remote state storage refers to storing the Terraform state ﬁle remotely instead of locally on the

machine where Terraform is running. The state ﬁle is crucial because it keeps track of the resources

that are provisioned by Terraform and their metadata.

Continually validate IAM policies 11

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Failure to secure remote state can lead to serious issues such as loss of state data, inability to

manage infrastructure, inadvertent resource deletion, and exposure of sensitive information that

might be present in the state ﬁle. For this reason, securing remote state storage is crucial for

production-grade Terraform usage.

## Enable encryption and access controls

Use Amazon Simple Storage Service (Amazon S3) server-side encryption (SSE) to encrypt remote

state at rest.

Limit direct access to collaborative workﬂows

*Structure collaboration workﬂows in HCP Terraform or in a CI/CD pipeline within your Git

repository to limit direct state access.

*Rely on pull requests, run approvals, policy checks, and notiﬁcations to coordinate changes.

Following these guidelines helps secure sensitive resource attributes and avoids conﬂicts with team

members' changes. Encryption and strict access protections help reduce the attack surface, and

collaboration workﬂows enable productivity.

## Use AWS Secrets Manager

There are many resources and data sources in Terraform that store secret values in plaintext in the

state ﬁle. Avoid storing secrets in state―use AWS Secrets Manager instead.

Instead of attempting to manually encrypt sensitive values, rely on Terraform's built-in support for

sensitive state management. When exporting sensitive values to output, make sure that the values

are marked as sensitive.

## Continuously scan infrastructure and source code

Proactively scan both infrastructure and source code continuously for risks such as exposed

credentials or misconﬁgurations to harden your security posture. Address ﬁndings promptly by

reconﬁguring or patching resources.

Enable encryption and access controls 12

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Use AWS services for dynamic scanning

Use AWS native tools such as Amazon Inspector, AWS Security Hub, Amazon Detective, and

Amazon GuardDuty to monitor provisioned infrastructure across accounts and Regions. Schedule

recurring scans in Security Hub to track deployment and conﬁguration drift. Scan EC2 instances,

Lambda functions, containers, S3 buckets, and other resources.

## Perform static analysis

Embed static analyzers such as Checkov directly into CI/CD pipelines to scan Terraform

conﬁguration code (HCL) and identify risks preemptively before deployment. This moves security

checks to an earlier point in the development process (referred to as shifting left) and prevents

misconﬁgured infrastructure.

## Ensure prompt remediation

For all scan ﬁndings, ensure prompt remediation by either updating Terraform conﬁguration,

applying patches, or reconﬁguring resources manually as appropriate. Lower risk levels by

addressing the root causes.

Using both infrastructure scanning and code scanning provides layered insight across Terraform

conﬁgurations, the provisioned resources, and application code. This maximizes the coverage of risk

and compliance through preventative, detective, and reactive controls while embedding security

earlier into the software development lifecycle (SDLC).

## Enforce policy checks

Use code frameworks such as HashiCorp Sentinel policies  to provide governance guardrails and

standardized templates for infrastructure provisioning with Terraform.

Sentinel policies can deﬁne requirements or restrictions on Terraform conﬁguration to align with

organizational standards and best practices. For example, you can use Sentinel policies to:

*Require tags on all resources.

*Restrict instance types to an approved list.

*Enforce mandatory variables.

*Prevent the destruction of production resources.

Use AWS services for dynamic scanning 13

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Embedding policy checks into Terraform conﬁguration lifecycles enables proactive enforcement of

standards and architecture guidelines. Sentinel provides shared policy logic that helps accelerate

development while preventing unapproved practices.

Enforce policy checks 14

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Backend best practices

Using a proper remote backend to store your state ﬁle is critical for enabling collaboration,

ensuring state ﬁle integrity through locking, providing reliable backup and recovery, integrating

with CI/CD workﬂows, and taking advantage of advanced security, governance, and management

features oﬀered by managed services such as HCP Terraform.

Terraform supports various backend types such as Kubernetes, HashiCorp Consul, and HTTP.

However, this guide focuses on Amazon S3, which is an optimal backend solution for most AWS

users.

As a fully managed object storage service that oﬀers high durability and availability, Amazon S3

provides a secure, scalable and low-cost backend for managing Terraform state on AWS. The global

footprint and resilience of Amazon S3 exceeds what most teams can achieve by self-managing

state storage. Additionally, being natively integrated with AWS access controls, encryption options,

versioning capabilities, and other services makes Amazon S3 a convenient backend choice.

This guide doesn't provide backend guidance for other solutions such as Kubernetes or Consul

because the primary target audience is AWS customers. For teams that are fully in the AWS

Cloud, Amazon S3 is typically the ideal choice over Kubernetes or HashiCorp Consul clusters. The

simplicity, resilience, and tight AWS integration of Amazon S3 state storage provides an optimal

foundation for most users who follow AWS best practices. Teams can take advantage of the

durability, backup protections, and availability of AWS services to keep remote Terraform state

highly resilient.

Following the backend recommendations in this section will lead to more collaborative Terraform

code bases while limiting the impact of errors or unauthorized modiﬁcations. By implementing a

well-architected remote backend, teams can optimize Terraform workﬂows.

Best practices:

*Use Amazon S3 for remote storage

*Facilitate team collaboration

*Separate the backends for each environment

*Actively monitor remote state activity

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Use Amazon S3 for remote storage

Storing Terraform state remotely in Amazon S3 and implementing state locking  and consistency

checking by using Amazon DynamoDB provide major beneﬁts over local ﬁle storage. Remote state

enables team collaboration, change tracking, backup protections, and remote locking for increased

safety.

Using Amazon S3 with the S3 Standard storage class (default) instead of ephemeral local storage

or self-managed solutions provides 99.999999999% durability and 99.99% availability protections

to prevent accidental state data loss. AWS managed services such as Amazon S3 and DynamoDB

provide service-level agreements (SLAs) that exceed what most organizations can achieve when

they self-manage storage. Rely on these protections to keep remote backends accessible.

## Enable remote state locking

DynamoDB locking restricts state access to prevent concurrent write operations. This prevents

simultaneous modiﬁcations from multiple users and reduces errors.

Example backend conﬁguration with state locking:

terraform {

backend "s3" {

bucket         = "myorg-terraform-states"

key            = "myapp/production/tfstate"

region         = "us-east-1"

dynamodb_table = "TerraformStateLocking"

}

}

## Enable versioning and automatic backups

For additional safeguarding, enable automatic versioning and backups  by using AWS Backup on

Amazon S3 backends. Versioning preserves all previous versions of the state whenever changes are

made. It also lets you restore previous working state snapshots if needed to roll back unwanted

changes or recover from accidents.

Use Amazon S3 for remote storage 16

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Restore previous versions if needed

Versioned Amazon S3 state buckets make it easy to revert changes by restoring a previous known

good state snapshot. This helps protect against accidental changes and provides additional backup

capabilities.

## Use HCP Terraform

HCP Terraform provides a fully managed backend alternative to conﬁguring your own state

storage. HCP Terraform automatically handles the secure storage of state and encryption while

unlocking additional features.

When you use HCP Terraform, state is stored remotely by default, which enables state sharing

and locking across your organization. Detailed policy controls help you restrict state access and

changes.

Additional capabilities include version control integrations, policy guardrails, workﬂow automation,

variables management, and single sign-on integrations with SAML. You can also use Sentinel policy

as code to implement governance controls.

Although HCP Terraform requires using a software as a service (SaaS) platform, for many teams

the beneﬁts around security, access controls, automated policy checks, and collaboration features

make it an optimal choice over self-managing state storage with Amazon S3 or DynamoDB.

Easy integration with services such as GitHub and GitLab with minor conﬁguration also appeals to

users who fully embrace cloud and SaaS tools for better team workﬂows.

## Facilitate team collaboration

Use remote backends to share state data across all the members of your Terraform team. This

facilitates collaboration because it gives the entire team visibility into infrastructure changes.

Shared backend protocols combined with state history transparency simplify internal change

management. All infrastructure changes go through the established pipeline, which increases

business agility across the enterprise.

## Improve accountability by using AWS CloudTrail

Integrate AWS CloudTrail with the Amazon S3 bucket to capture API calls made to the state bucket.

Filter CloudTrail events to track PutObject , DeleteObject,  and other relevant calls.

Restore previous versions if needed 17

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

CloudTrail logs show the AWS identity of the principal that made each API call for state change.

The user's identity can be matched to a machine account or to members of the team who interact

with the backend storage.

Combine CloudTrail logs with Amazon S3 state versioning to tie infrastructure changes to the

principal who applied them. By analyzing multiple revisions, you can attribute any updates to the

machine account or responsible team member.

If an unintended or disruptive change occurs, state versioning provides rollback capabilities.

CloudTrail traces the change to the user so you can discuss preventative improvements.

We also recommend that you enforce IAM permissions to limit state bucket access. Overall, S3

Versioning and CloudTrail monitoring supports auditing across infrastructure changes. Teams gain

improved accountability, transparency, and audit capabilities into the Terraform state history.

## Separate the backends for each environment

Use distinct Terraform backends for each application environment. Separate backends isolate state

between development, test, and production.

## Reduce the scope of impact

Isolating state helps ensure that changes in lower environments don't impact production

infrastructure. Accidents or experiments in development and test environments have limited

impact.

## Restrict production access

Lock down permissions for the production state backend to read-only access for most users. Limit

who can modify the production infrastructure to the CI/CD pipeline and break glass roles.

## Simplify access controls

Managing permissions at the backend level simpliﬁes access control between environments.

Using distinct S3 buckets for each application and environment means that broad read or write

permissions can be granted on entire backend buckets.

Separate the backends for each environment 18

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Avoid shared workspaces

Although you can use Terraform workspaces to separate state between environments, distinct

backends provide stronger isolation. If you have shared workspaces, accidents can still impact

multiple environments.

Keeping environment backends fully isolated minimizes the impact of any single failure or

breach. Separate backends also align access controls to the environment's sensitivity level. For

example, you can provide write protection for the production environment and broader access for

development and test environments.

## Actively monitor remote state activity

Continuously monitoring remote state activity is critical for detecting potential issues early. Look

for anomalous unlocks, changes, or access attempts.

## Get alerts on suspicious unlocks

Most state changes should run through CI/CD pipelines. Generate alerts if state unlocks occur

directly through developer workstations, which could signal unauthorized or untested changes.

## Monitor access attempts

Authentication failures on state buckets might indicate reconnaissance activity. Notice if multiple

accounts are trying to access state, or unusual IP addresses appear, which signals compromised

credentials.

Avoid shared workspaces 19

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Best practices for code base structure and organization

Proper code base structure and organization is critical as Terraform usage grows across large teams

and enterprises. A well-architected code base enables collaboration at scale while enhancing

maintainability.

This section provides recommendations on Terraform modularity, naming conventions,

documentation, and coding standards that support quality and consistency.

Guidance includes breaking conﬁguration into reusable modules by environment and components,

establishing naming conventions by using preﬁxes and suﬃxes, documenting modules and clearly

explaining inputs and outputs, and applying consistent formatting rules by using automated style

checks.

Additional best practices cover logically organizing modules and resources in a structured

hierarchy, cataloging public and private modules in documentation, and abstracting unnecessary

implementation details in modules to simplify usage.

By implementing code base structure guidelines around modularity, documentation, standards, and

logical organization, you can support broad collaboration across teams while keeping Terraform

maintainable as usage spreads across an organization. By enforcing conventions and standards, you

can avoid the complexity of a fragmented code base.

Best practices:

*Implement a standard repository structure

*Structure for modularity

*Follow naming conventions

*Use attachment resources

*Use default tags

*Meet Terraform registry requirements

*Use recommended module sources

*Follow coding standards

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Implement a standard repository structure

We recommend that you implement the following repository layout. Standardizing on these

consistency practices across modules improves discoverability, transparency, organization, and

reliability while enabling reuse across many Terraform conﬁgurations.

*Root module or directory: This should be the primary entry point for both Terraform root and

re-usable modules and is expected to be unique. If you have a more complex architecture, you

can use nested modules to create lightweight abstractions. This helps you describe infrastructure

in terms of its architecture instead of directly, in terms of physical objects.

*README : The root module and any nested modules should have README ﬁles. This ﬁle must

be named README.md . It should contain a description of the module and what it should be

used for. If you want to include an example of using this module with other resources, put it in

an examples  directory. Consider including a diagram that depicts the infrastructure resources

the module might create and their relationships. Use terraform-docs  to automatically generate

inputs or outputs of the module.

*main.tf: This is the primary entry point. For a simple module, all resources might be created in

this ﬁle. For a complex module, resource creation might be spread across multiple ﬁles, but any

nested module calls should be in the main.tf  ﬁle.

*variables.tf and outputs.tf: These ﬁles contain the declarations for variables and outputs. All

variables and outputs should have one-sentence or two-sentence descriptions that explain

their purpose. These descriptions are used for documentation. For more information, see the

HashiCorp documentation for variable conﬁguration and output conﬁguration.

*All variables must have a deﬁned type.

*The variable declaration can also include a default argument. If the declaration includes a

default argument, the variable is considered to be optional, and the default value is used if you

don't set a value when you call the module or run Terraform. The default argument requires

a literal value and cannot reference other objects in the conﬁguration. To make a variable

required, omit a default in the variable declaration and consider whether setting nullable =

false makes sense.

*For variables that have environment-independent values (such as disk_size ), provide default

values.

*For variables that have environment-speciﬁc values (such as project_id ), don't provide

default values. In this case, the calling module must provide meaningful values.

Implement a standard repository structure 21

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

*Use empty defaults for variables such as empty strings or lists only when leaving the variable

empty is a valid preference that the underlying APIs don't reject.

*Be judicious in your use of variables. Parameterize values only if they must vary for each

instance or environment. When you decide whether to expose a variable, ensure that you have

a concrete use case for changing that variable. If there's only a small chance that a variable

might be needed, don't expose it.

*Adding a variable with a default value is backward compatible.

*Removing a variable is backward incompatible.

*In cases where a literal is reused in multiple places, you should use a local value without

exposing it as a variable.

*Don't pass outputs directly through input variables, because doing so prevents them from

being properly added to the dependency graph. To ensure that implicit dependencies  are

created, make sure that outputs reference attributes from resources. Instead of referencing an

input variable for an instance directly, pass the attribute.

*locals.tf: This ﬁle contains local values that assign a name to an expression, so a name can be

used multiple times within a module instead of repeating the expression. Local values are like

a function's temporary local variables. The expressions in local values aren't limited to literal

constants; they can also reference other values in the module, including variables, resource

attributes, or other local values, in order to combine them.

*providers.tf: This ﬁle contains the terraform block  and provider blocks. provider  blocks must

be declared only in root modules by consumers of modules.

If you're using HCP Terraform, also add an empty cloud block . The cloud  block should be

conﬁgured entirely through environment variables and environment variable credentials as part

of a CI/CD pipeline.

*versions.tf: This ﬁle contains the required_providers block. All Terraform modules must declare

which providers it requires so that Terraform can install and use these providers.

*data.tf: For simple conﬁguration, put data sources next to the resources that reference them.

For example, if you are fetching an image to be used in launching an instance, place it alongside

the instance instead of collecting data resources in their own ﬁle. If the number of data sources

becomes too large, consider moving them to a dedicated data.tf  ﬁle.

*.tfvars ﬁles: For root modules, you can provide non-sensitive variables by using a .tfvars  ﬁle.

For consistency, name the variable ﬁles terraform.tfvars . Place common values at the root

of the repository, and environment-speciﬁc values within the envs/ folder.

Implement a standard repository structure 22

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

*Nested modules: Nested modules should exist under the modules/  subdirectory. Any nested

module that has a README.md  is considered usable by an external user. If a README.md  doesn't

exist, the module is considered for internal use only. Nested modules should be used to split

complex behavior into multiple small modules that users can carefully pick and choose.

If the root module includes calls to nested modules, these calls should use relative paths such

as ./modules/sample-module  so that Terraform will consider them to be part of the same

repository or package instead of downloading them again separately.

If a repository or package contains multiple nested modules, they should ideally be composable

by the caller instead of directly calling each other and creating a deeply nested tree of modules.

*Examples: Examples of using a reusable module should exist under the examples/  subdirectory

at the root of the repository. For each example, you can add a README to explain the goal and

usage of the example. Examples for submodules should also be placed in the root examples/

directory.

Because examples are often copied into other repositories for customization, module blocks

should have their source set to the address an external caller would use, not to a relative path.

*Service named ﬁles: Users often want to separate Terraform resources by service in multiple

ﬁles. This practice should be discouraged as much as possible, and resources should be deﬁned

in main.tf instead. However, if a collection of resources (for example, IAM roles and policies)

exceeds 150 lines, it's reasonable to break it into its own ﬁles, such as iam.tf. Otherwise, all

resource code should be deﬁned in the main.tf .

*Custom scripts : Use scripts only when necessary. Terraform doesn't account for, or manage,

the state of resources that are created through scripts. Use custom scripts only when Terraform

resources don't support the desired behavior. Place custom scripts called by Terraform in a

scripts/  directory.

*Helper scripts : Organize helper scripts that aren't called by Terraform in a helpers/  directory.

Document helper scripts in the README.md  ﬁle with explanations and example invocations. If

helper scripts accept arguments, provide argument checking and --help  output.

*Static ﬁles: Static ﬁles that Terraform references but doesn't run (such as startup scripts loaded

onto EC2 instances) must be organized into a files/ directory. Place lengthy documents in

external ﬁles, separate from their HCL. Reference them with the ﬁle() function.

*Templates: For ﬁles that the Terraform templateﬁle function reads in, use the ﬁle extension

.tftpl. Templates must be placed in a templates/  directory.

Implement a standard repository structure 23

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Root module structure

Terraform always runs in the context of a single root module. A complete Terraform conﬁguration

consists of a root module and the tree of child modules (which includes the modules that are called

by the root module, any modules called by those modules, and so on).

Terraform root module layout basic example:

.

### data.tf

### envs

#   ### dev

#   #   ### terraform.tfvars

#   ### prod

#   #   ### terraform.tfvars

#   ### test

#       ### terraform.tfvars

### locals.tf

### main.tf

### outputs.tf

### providers.tf

### README.md

### terraform.tfvars

### variables.tf

### versions.tf

## Reusable module structure

Reusable modules follow the same concepts as root modules. To deﬁne a module, create a new

directory for it and place the .tf ﬁles inside, just as you would deﬁne a root module. Terraform

can load modules either from local relative paths or from remote repositories. If you expect a

module to be reused by many conﬁgurations, place it in its own version control repository. It's

important to keep the module tree relatively ﬂat to make it easier to reuse the modules in diﬀerent

combinations.

Terraform reusable module layout basic example:

.

### data.tf

### examples

Root module structure 24

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

#   ### multi-az-new-vpc

#   #   ### data.tf

#   #   ### locals.tf

#   #   ### main.tf

#   #   ### outputs.tf

#   #   ### providers.tf

#   #   ### README.md

#   #   ### terraform.tfvars

#   #   ### variables.tf

#   #   ### versions.tf

#   #   ### vpc.tf

#   ### single-az-existing-vpc

#   #   ### data.tf

#   #   ### locals.tf

#   #   ### main.tf

#   #   ### outputs.tf

#   #   ### providers.tf

#   #   ### README.md

#   #   ### terraform.tfvars

#   #   ### variables.tf

#   #   ### versions.tf

### iam.tf

### locals.tf

### main.tf

### outputs.tf

### README.md

### variables.tf

### versions.tf

## Structure for modularity

In principle, you can combine any resources and other constructs into a module, but overusing

nested and reusable modules can make your overall Terraform conﬁguration harder to understand

and maintain, so use these modules in moderation.

When it makes sense, break your conﬁguration into reusable modules that raise the level of

abstraction by describing a new concept in your architecture that is constructed from resource

types.

When you modularize your infrastructure into reusable deﬁnitions, aim for logical sets of resources

instead of individual components or overly complex collections.

Structure for modularity 25

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

Don't wrap single resources

You shouldn't create modules that are thin wrappers around other single resource types. If you

have trouble ﬁnding a name for your module that's diﬀerent from the name of the main resource

type inside it, your module probably isn't creating a new abstraction―it's adding unnecessary

complexity. Instead, use the resource type directly in the calling module.

## Encapsulate logical relationships

Group sets of related resources such as networking foundations, data tiers, security controls, and

applications. A reusable module should encapsulate infrastructure pieces that work together to

enable a capability.

Keep inheritance ﬂat

When you nest modules in subdirectories, avoid going more than one or two levels deep. Deeply

nested inheritance structures complicate conﬁgurations and troubleshooting. Modules should build

on other modules―not build tunnels through them.

By focusing modules on logical resource groupings that represent architecture patterns, teams can

quickly conﬁgure reliable infrastructure foundations. Balance abstraction without over-engineering

or over-simpliﬁcation.

## Reference resources in outputs

For every resource that's deﬁned in a reusable module, include at least one output that references

the resource. Variables and outputs let you infer dependencies between modules and resources.

Without any outputs, users cannot properly order your module in relation to their Terraform

conﬁgurations.

Well-structured modules that provide environment consistency, purpose-driven groupings, and

exported resource references enable organization-wide Terraform collaboration at scale. Teams can

assemble infrastructure from reusable building blocks.

Don't conﬁgure providers

Although shared modules inherit providers from calling modules, modules should not conﬁgure

provider settings themselves. Avoid specifying provider conﬁguration blocks in modules. This

conﬁguration should only be declared once globally.

Don't wrap single resources 26

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Declare required providers

Although provider conﬁgurations are shared between modules, shared modules must also declare

their own provider requirements. This practice enables Terraform to ensure that there is a single

version of the provider that's compatible with all modules in the conﬁguration, and to specify the

source address that serves as the global (module-agnostic) identiﬁer for the provider. However,

module-speciﬁc provider requirements don't specify any of the conﬁguration settings that

determine what remote endpoints the provider will access, such as an AWS Region.

By declaring version requirements and avoiding hardcoded provider conﬁguration, modules provide

portability and reusability across Terraform conﬁgurations using shared providers.

For shared modules, deﬁne the minimum required provider versions in a required_providers block

in versions.tf .

To declare that a module requires a particular version of the AWS provider, use a

required_providers  block inside a terraform  block:

terraform {

required_version = ">= 1.0.0"

required_providers {

aws = {

source  = "hashicorp/aws"

version = ">= 4.0.0"

}

}

}

If a shared module supports only a speciﬁc version of the AWS provider, use the pessimistic

constraint operator  (~> ), which allows only the rightmost version component to increment:

terraform {

required_version = ">= 1.0.0"

required_providers {

aws = {

source  = "hashicorp/aws"

version = "~> 4.0"

}

Declare required providers 27

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

}

}

In this example, ~> 4.0 allows the installation of 4.57.1  and 4.67.0  but not 5.0.0. For more

information, see Version Constraint Syntax in the HashiCorp documentation.

## Follow naming conventions

Clear, descriptive names simplify your understanding of relationships between resources in the

module and the purpose of conﬁguration values. Consistency with style guidelines enhances

readability for both module users and maintainers.

## Follow guidelines for resource naming

*Use snake_case  (where lowercase terms are separated by underscores) for all resource names to

match Terraform style standards. This practice ensures consistency with the naming convention

for resource types, data source types, and other predeﬁned values. This convention doesn't apply

to name arguments.

*To simplify references to a resource that is the only one of its type (for example, a single load

balancer for an entire module), name the resource main  or this for clarity.

*Use meaningful names that describe the purpose and context of the resource, and that help

diﬀerentiate between similar resources (for example, primary  for the main database and

read_replica  for a read replica of the database).

*Use singular, not plural names.

*Don't repeat the resource type in the resource name.

## Follow guidelines for variable naming

*Add units to the names of inputs, local variables, and outputs that represent numeric values such

as disk size or RAM size (for example, ram_size_gb  for RAM size in gigabytes). This practice

makes the expected input unit clear for conﬁguration maintainers.

*Use binary units such as MiB and GiB for storage sizes, and decimal units such as MB or GB for

other metrics.

*Give Boolean variables positive names such as enable_external_access .

Follow naming conventions 28

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Use attachment resources

Some resources have pseudo-resources embedded as attributes in them. Where possible, you

should avoid using these embedded resource attributes and use the unique resource to attach that

pseudo-resource instead. These resource relationships can cause cause-and-eﬀect issues that are

unique for each resource.

Using an embedded attribute (avoid this pattern):

resource "aws_security_group" "allow_tls" {

...

ingress {

description      = "TLS from VPC"

from_port        = 443

to_port          = 443

protocol         = "tcp"

cidr_blocks      = [aws_vpc.main.cidr_block]

ipv6_cidr_blocks = [aws_vpc.main.ipv6_cidr_block]

}

egress {

from_port        = 0

to_port          = 0

protocol         = "-1"

cidr_blocks      = ["0.0.0.0/0"]

ipv6_cidr_blocks = ["::/0"]

}

}

Using attachment resources (preferred):

resource "aws_security_group" "allow_tls" {

...

}

resource "aws_security_group_rule" "example" {

type              = "ingress"

description      = "TLS from VPC"

from_port        = 443

to_port          = 443

protocol         = "tcp"

cidr_blocks      = [aws_vpc.main.cidr_block]

Use attachment resources 29

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

ipv6_cidr_blocks = [aws_vpc.main.ipv6_cidr_block]

security_group_id = aws_security_group.allow_tls.id

}

## Use default tags

Assign tags to all resources that can accept tags. The Terraform AWS Provider has an

aws_default_tags data source that you should use inside the root module.

Consider adding necessary tags to all resources that are created by a Terraform module. Here's a

list of possible tags to attach:

*Name : Human-readable resource name

*AppId : The ID for the application that uses the resource

*AppRole: The resource's technical function; for example, "webserver" or "database"

*AppPurpose : The resource's business purpose; for example, "frontend ui" or "payment processor"

*Environment: The software environment, such as dev, test, or prod

*Project: The projects that use the resource

*CostCenter : Who to bill for resource usage

## Meet Terraform registry requirements

A module repository must meet all of the following requirements so it can be published to a

Terraform registry.

You should always follow these requirements even if you aren't planning to publish the module

to a registry in the short term. By doing so, you can publish the module to a registry later without

having to change the conﬁguration and structure of the repository.

*Repository name: For a module repository, use the three-part name terraform-aws-<NAME> ,

where <NAME> reﬂects the type of infrastructure the module manages. The <NAME>  segment can

contain additional hyphens (for example, terraform-aws-iam-terraform-roles ).

*Standard module structure: The module must adhere to the standard repository structure. This

allows the registry to inspect your module and generate documentation, track resource usage,

and more.

Use default tags 30

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

*After you create the Git repository, copy the module ﬁles to the root of the repository. We

recommend that you place each module that is intended to be reusable in the root of its own

repository, but you can also reference modules from subdirectories.

*If you're using HCP Terraform, publish the modules that are intended to be shared to your

organization registry. The registry handles downloads and controls access with HCP Terraform

API tokens, so consumers do not need access to the module's source repository even when

they run Terraform from the command line.

*Location and permissions: The repository must be in one of your conﬁgured version control

system (VCS) providers, and the HCP Terraform VCS user account must have administrator access

to the repository. The registry needs administrator access to create the webhooks to import new

module versions.

*x.y.z tags for releases: At least one release tag must be present for you to publish a module. The

registry uses release tags to identify module versions. Release tag names must use semantic

versioning, which you can optionally preﬁx with a v (for example, v1.1.0  and 1.1.0 ). The

registry ignores tags that do not look like version numbers. For more information about

publishing modules, see the Terraform documentation.

For more information, see Preparing a Module Repository in the Terraform documentation.

## Use recommended module sources

Terraform uses the source argument in a module block to ﬁnd and download the source code for

a child module.

We recommend that you use local paths for closely related modules that have the primary purpose

of factoring out repeated code elements, and using a native Terraform module registry or a VCS

provider for modules that are intended to be shared by multiple conﬁgurations.

The following examples illustrate the most common and recommended source types for sharing

modules. Registry modules support versioning. You should always provide a speciﬁc version, as

shown in the following examples.

## Registry

Terraform registry:

module "lambda" {

Use recommended module sources 31

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

source = "github.com/terraform-aws-modules/terraform-aws-lambda.git?

ref=e78cdf1f82944897ca6e30d6489f43cf24539374" #--> v4.18.0

...

}

By pinning commit hashes, you can avoid drift from public registries that are vulnerable to supply

chain attacks.

HCP Terraform:

module "eks_karpenter" {

source = "app.terraform.io/my-org/eks/aws"

version = "1.1.0"

...

enable_karpenter = true

}

Terraform Enterprise:

module "eks_karpenter" {

source = "terraform.mydomain.com/my-org/eks/aws"

version = "1.1.0"

...

enable_karpenter = true

}

## VCS providers

VCS providers support the ref argument for selecting a speciﬁc revision, as shown in the following

examples.

GitHub (HTTPS):

module "eks_karpenter" {

VCS providers 32

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

source = "github.com/my-org/terraform-aws-eks.git?ref=v1.1.0"

...

enable_karpenter = true

}

Generic Git repository (HTTPS):

module "eks_karpenter" {

source = "git::https://example.com/terraform-aws-eks.git?ref=v1.1.0"

...

enable_karpenter = true

}

Generic Git repository (SSH):

## Warning

You need to conﬁgure credentials to access private repositories.

module "eks_karpenter" {

source = "git::ssh://username@example.com/terraform-aws-eks.git?ref=v1.1.0"

...

enable_karpenter = true

}

## Follow coding standards

Apply consistent Terraform formatting rules and styles across all conﬁguration ﬁles. Enforce

standards by using automated style checks in CI/CD pipelines. When you embed coding best

practices into team workﬂows, conﬁgurations remain readable, maintainable, and collaborative as

usage spreads widely across an organization.

Follow coding standards 33

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Follow style guidelines

*Format all Terraform ﬁles (.tf ﬁles) with the terraform fmt  command to match HashiCorp style

standards.

*Use the terraform validate  command to verify the syntax and structure of your conﬁguration.

*Statically analyze code quality by using TFLint . This linter checks for Terraform best practices

beyond just formatting and fails builds when it encounters errors.

Conﬁgure pre-commit hooks

Conﬁgure client-side pre-commit hooks that run terraform fmt , tflint , checkov , and other

code scans and style checks before you allow commits. This practice helps you validate standards

conformance earlier in developer workﬂows.

Use pre-commit frameworks such as pre-commit to add Terraform linting, formatting, and code

scanning as hooks on your local machine. Hooks run on each Git commit and fail the commit if

checks don't pass.

Moving style and quality checks to local pre-commit hooks provides rapid feedback to developers

before changes are introduced. Standards become part of the coding workﬂow.

Follow style guidelines 34

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Best practices for AWS Provider version management

Carefully managing versions of the AWS Provider and associated Terraform modules is critical for

stability. This section outlines best practices around version constraints and upgrades.

Best practices:

*Add automated version checks

*Monitor new releases

*Contribute to providers

## Add automated version checks

Add version checks for Terraform providers in your CI/CD pipelines to validate version pinning, and

fail builds if the version is undeﬁned.

*Add TFLint  checks in CI/CD pipelines to scan for provider versions that don't have pinned major/

minor version constraints deﬁned. Use the TFLint ruleset plugin for Terraform AWS Provider,

which provides rules for detecting possible errors and checks for best practices about AWS

resources.

*Fail CI runs that detect unpinned provider versions to prevent implicit upgrades from reaching

production.

## Monitor new releases

*Monitor provider release notes and changelog feeds. Get notiﬁcations on new major/minor

releases.

*Assess release notes for potentially breaking changes and evaluate their impact on your existing

infrastructure.

*Upgrade minor versions in non-production environments ﬁrst to validate them before updating

the production environment.

By automating version checks in pipelines and monitoring new releases, you can catch unsupported

upgrades early and give your teams time to evaluate the impact of new major/minor releases

before you update production environments.

Add automated version checks 35

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Contribute to providers

Actively contribute to HashiCorp AWS Provider by reporting defects or requesting features in

GitHub issues:

*Open well-documented issues on the AWS Provider repository to detail any bugs you

encountered or functionality that is missing. Provide reproducible steps.

*Request and vote on enhancements to expand the capabilities of the AWS Provider for managing

new services.

*Reference issued pull requests when you contribute proposed ﬁxes for provider defects or

enhancements. Link to related issues.

*Follow the contribution guidelines in the repository for coding conventions, testing standards,

and documentation.

By giving back to the providers you use, you can provide direct input into their roadmap and help

improve their quality and capabilities for all users.

Contribute to providers 36

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Best practices for community modules

Using modules eﬀectively is key to managing complex Terraform conﬁgurations and promoting

reuse. This section provides best practices around community modules, dependencies, sources,

abstraction, and contributions.

Best practices:

*Discover community modules

*Understand dependencies

*Use trusted sources

*Contribute to community modules

## Discover community modules

Search the Terraform Registry, GitHub , and other sources for existing AWS modules that might

solve your use case before you build a new module. Look for popular options that have recent

updates and are actively maintained.

## Use variables for customization

When you use community modules, pass inputs through variables instead of forking or directly

modifying the source code. Override defaults where required instead of changing the internals of

the module.

Forking should be limited to contributing ﬁxes or features to the original module to beneﬁt the

broader community.

## Understand dependencies

Before you use the module, review its source code and documentation to identify dependencies:

*Required providers: Note the versions of AWS, Kubernetes, or other providers the module

requires.

*Nested modules: Check for other modules used internally that introduce cascading

dependencies.

Discover community modules 37

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

*External data sources: Note the APIs, custom plugins, or infrastructure dependencies that the

module relies on.

By mapping out the full tree of direct and indirect dependencies, you can avoid surprises when you

use the module.

## Use trusted sources

Sourcing Terraform modules from unveriﬁed or unknown publishers introduces signiﬁcant risk. Use

modules only from trusted sources.

*Favor certiﬁed modules from the Terraform Registry that are published by veriﬁed creators such

as AWS or HashiCorp partners.

*For custom modules, review publisher history, support levels, and usage reputation, even if the

module is from your own organization.

By not allowing modules from unknown or unvetted sources, you can reduce the risk of injecting

vulnerabilities or maintenance issues into your code.

Subscribe to notiﬁcations

Subscribe to notiﬁcations for new module releases from trusted publishers:

*Watch GitHub module repositories to get alerts on new versions of the module.

*Monitor publisher blogs and changelogs for updates.

*Get proactive notiﬁcations for new versions from veriﬁed, highly rated sources instead of

implicitly pulling in updates.

Consuming modules only from trusted sources and monitoring changes provide stability and

security. Vetted modules enhance productivity while minimizing supply chain risk.

## Contribute to community modules

Submit ﬁxes and enhancements for community modules that are hosted in GitHub:

*Open pull requests on modules to address defects or limitations that you encounter in your

usage.

Use trusted sources 38

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

*Request new best practice conﬁgurations to be added to existing OSS modules by creating

issues.

Contributing to community modules enhances reusable, codiﬁed patterns for all Terraform

practitioners.

Contribute to community modules 39

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## FAQ

Q. Why focus on the AWS Provider?

A. The AWS Provider is one of the most widely used and complex providers for provisioning

infrastructure in Terraform. Following these best practices help users optimize their usage of the

provider for the AWS environment.

Q. I'm new to Terraform. Can I use this guide?

A. The guide is for people who are new to Terraform as well as more advanced practitioners who

want  to level up their skills. The practices improve workﬂows for users at any stage of learning.

Q. What are some key best practices covered?

A. Key best practices include using IAM roles over access keys, pinning versions, incorporating

automated testing , remote state locking, credential rotation, contributing back to providers, and

logically organizing code bases.

Q. Where can I learn more about Terraform?

A. The Resources section includes links to the oﬃcial HashiCorp Terraform documentation and

community forums. Use the links to learn more about advanced Terraform workﬂows.

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Next steps

Here are some potential next steps after reading this guide:

*If you have an existing Terraform code base, review your conﬁguration and identify areas that

could be improved based on the recommendations that are provided in this guide. For example,

review best practices for implementing remote backends, separating code into modules, using

version pinning, and so on, and validate these in your conﬁguration.

*If you don't have an existing Terraform code base, use these best practices when you structure

your new conﬁguration. Follow the advice around state management, authentication, code

structure, and so on from the beginning.

*Try using some of the HashiCorp community modules referenced in this guide to see if they

simplify your architecture patterns. The modules allow higher levels of abstraction, so you don't

have to rewrite common resources.

*Enable linting, security scans, policy checks, and automated testing tools to reinforce some of

the best practices around security, compliance, and code quality. Tools such as TFLint, tfsec, and

Checkov can help.

*Review the latest AWS Provider documentation to see if there are any new resources or

functionality that could help optimize your Terraform usage. Stay up to date on new versions of

the AWS Provider.

*For additional guidance, see the Terraform documentation, best practices guide, and style guide

on the HashiCorp website.

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

## Resources

## References

The following links provide additional reading material for the Terraform AWS Provider and using

Terraform for IaC on AWS.

*Terraform AWS Provider (HashiCorp documentation)

*Terraform modules for AWS services (Terraform Registry)

*The AWS and HashiCorp Partnership (HashiCorp blog post)

*Dynamic Credentials with the AWS Provider (HCP Terraform documentation)

*DynamoDB State Locking  (Terraform documentation)

*Enforce Policy with Sentinel (Terraform documentation)

## Tools

The following tools help improve code quality and automation of Terraform conﬁgurations on

AWS, as recommended in this best practices guide.

Code quality:

*Checkov: Scans Terraform code to identify misconﬁgurations before deployment.

*TFLint : Identiﬁes possible errors, deprecated syntax, and unused declarations. This linter can also

enforce AWS best practices and naming conventions.

*terraform-docs : Generates documentation from Terraform modules in various output formats.

Automation tools:

*HCP Terraform: Helps teams version, collaborate, and build Terraform workﬂows with policy

checks and approval gates.

*Atlantis : An open source Terraform pull request automation tool for validating code changes.

*CDK for Terraform: A framework that lets you use familiar languages such as TypeScript, Python,

Java, C#, and Go instead of HashiCorp Conﬁguration Language (HCL) to deﬁne, provision, and

test your Terraform infrastructure as code.

References 42

## AWS Prescriptive Guidance Best practices for using the Terraform AWS Provider

