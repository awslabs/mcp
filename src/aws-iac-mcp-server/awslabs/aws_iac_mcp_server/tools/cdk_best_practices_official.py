# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from ..knowledge_models import KnowledgeResult


# A summary of https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html
CDK_OFFICIAL_BEST_PRACTICES_SUMMARY = """
# AWS CDK Best Practices

## Core Philosophy
The AWS CDK enables you to define your entire application in code - infrastructure, runtime logic, and configuration. This allows changes to be reviewed, tested, and rolled back consistently.

## Coding Best Practices

### Start Simple, Add Complexity Only When Needed
- Keep things as simple as possible
- Add complexity only when requirements dictate
- Refactor as needed - don't architect for all scenarios upfront

### Repository and Package Structure
- **Start with**: Single package in a single repository
- **Move to separate repos when**: Packages used in multiple applications OR different teams own them
- **Avoid**: Multiple unrelated CDK applications in same repository (increases blast radius)
- **Use**: Private package repositories (CodeArtifact) for shared constructs
- **Reason**: Changes in one app shouldn't trigger deployment of others

### Infrastructure and Runtime Code Together
- Keep infrastructure code and runtime logic (Lambda functions, Docker images) in the same package
- Bundle them as self-contained constructs
- Test both kinds of code together
- Version them in sync

### Align with AWS Well-Architected Framework
- A CDK application maps to a "component" in Well-Architected terminology
- Components are units of technical ownership
- Workloads are sets of components delivering business value

## Construct Best Practices

### Model with Constructs, Deploy with Stacks
- Use **Constructs** to encapsulate reusable logical units
- Use **Stacks** only to compose and connect constructs for deployment
- Everything in a stack deploys together
- Example: Website construct contains S3 bucket, API Gateway, Lambda, RDS - instantiated in stacks

### Configure with Properties and Methods, Not Environment Variables
- Constructs and stacks should accept properties objects for configuration
- Environment variable lookups are an anti-pattern
- Limit environment variables to top-level app for development environment info
- Reason: Avoids machine-specific dependencies

### Unit Test Your Infrastructure
- Avoid network lookups during synthesis
- Model all production stages in code
- Single commit should always generate same template
- Write tests to confirm generated templates match expectations

### Don't Change Logical IDs of Stateful Resources
- Changing logical ID replaces the resource
- For databases, S3 buckets, VPCs - this is rarely desired
- Write unit tests asserting logical IDs remain static
- Logical ID derived from construct `id` and position in construct tree

### Constructs Aren't Enough for Compliance
- Don't rely solely on wrapper constructs (like MyCompanyBucket) for security
- Use service control policies and permission boundaries for enforcement
- Use Aspects or CloudFormation Guard for pre-deployment validation
- Wrapper constructs may prevent using AWS Solutions Constructs or third-party packages

## Application Best Practices

### Make Decisions at Synthesis Time
- Avoid CloudFormation Parameters, Conditions, and { Fn::If }
- Use your programming language's if statements and features
- Make all decisions in CDK code, not at deployment time
- Treat CloudFormation as implementation detail, not language target

### Use Generated Resource Names, Not Physical Names
- **Don't**: Hardcode bucket names, table names, etc.
- **Why**: Can't deploy twice to same account, can't replace immutable resources
- **Do**: Omit names, let CDK generate them
- **Access**: Pass generated names via environment variables, SSM Parameter Store, or stack references
- **Between stacks**: Pass references in same app, use .fromArn() methods across apps

### Define Removal Policies and Log Retention
- CDK defaults to retaining data (S3 buckets, databases)
- CDK defaults to retaining all logs forever
- **Production**: Carefully define removal and logging policies for each resource
- **Reason**: Defaults can result in unnecessary storage costs
- **Validate**: Use Aspects to check policies across stacks

### Separate Stacks by Deployment Requirements
- **Keep together**: Resources that deploy together
- **Separate**: Stateful resources (databases) from stateless resources
- **Enable**: Termination protection on stateful stacks
- **Benefit**: Freely destroy/recreate stateless stacks without data loss
- **Avoid**: Nesting stateful resources in constructs likely to move/rename

### Commit cdk.context.json for Determinism
- Context providers cache non-deterministic values (VPC lookups, AMI IDs)
- Commit cdk.context.json to version control
- **Reason**: Future synthesis produces same template
- **Example risks**: New AZ launches, IP space must be recreated; new AMI releases, instances replaced
- **For custom lookups**: Write separate script, store in file, read in CDK app

### Let CDK Manage Roles and Security Groups
- Use .grant() convenience methods (bucket.grantRead(myLambda))
- CDK creates roles with minimal permissions automatically
- **Don't**: Require predefined roles from security team (reduces flexibility)
- **Do**: Use service control policies and permission boundaries for guardrails

### Model All Production Stages in Code
- **Don't**: Create single parameterized template
- **Do**: Create separate stack for each environment with configuration in code
- **Secrets**: Use Secrets Manager and Systems Manager Parameter Store
- **Result**: Deterministic builds, reliable unit testing, no out-of-band changes

### Measure Everything
- Create metrics, alarms, and dashboards for all resources
- Measure business metrics, not just infrastructure metrics
- Use measurements to automate deployment decisions (rollbacks)
- Use L2 construct convenience methods (table.metricUserErrors())

## Security Best Practices

### Use Construct Permission Methods
- Prefer bucket.grantRead(lambda) over manual IAM policies
- Creates minimally scoped permissions automatically
- Reduces boilerplate CloudFormation

### Enable Encryption by Default
- S3 buckets, EBS volumes, databases
- Require SSL/TLS for data in transit

### Never Hardcode Secrets
- Use Secrets Manager or Parameter Store
- Reference by name or ARN in code

### Manage Deployment Permissions
- Control who can deploy CDK apps
- Define what actions they can take
- Use permission boundaries and service control policies

## Testing Best Practices

### Write Unit Tests
- Test infrastructure code like application code
- Use snapshot tests for large templates
- Detect unintended changes

### Validate Security and Compliance
- Test security properties before deployment
- Use Aspects for validation
- Integrate CloudFormation Guard

### Ensure Deterministic Synthesis
- Same code should always produce same template
- Avoid network calls during synthesis
- Never modify AWS resources during synthesis
- Use custom resources for deployment-time changes

## Deployment Best Practices

### Use CDK Asset Bundling
- Bundle Lambda code and Docker images with CDK
- Deploy assets alongside infrastructure

### Apply DRY Principle
- Don't Repeat Yourself
- Extract common patterns into reusable constructs

### Keep Documentation Updated
- Document constructs with clear comments
- Provide usage examples
- Update as code evolves

## Anti-Patterns to Avoid

❌ Environment variable lookups in constructs
❌ Hardcoded resource names
❌ CloudFormation Parameters for environment differences
❌ Network calls during synthesis
❌ Modifying AWS resources during synthesis
❌ Multiple unrelated apps in same repository
❌ Relying solely on wrapper constructs for compliance
❌ Changing logical IDs of stateful resources
❌ Nesting stateful resources deeply
"""

CDK_OFFICIAL_BEST_PRACTICES_KNOWLEDGE = KnowledgeResult(
    rank=1,
    title='AWS CDK Best Practices',
    url='https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html',
    context=CDK_OFFICIAL_BEST_PRACTICES_SUMMARY,
)
