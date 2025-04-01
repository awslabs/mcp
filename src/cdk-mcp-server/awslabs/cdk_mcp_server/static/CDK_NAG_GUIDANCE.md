# CDK Nag Guidance

This guide provides implementation details for CDK Nag in AWS CDK projects. CDK Nag analyzes CDK constructs to identify security issues based on AWS Well-Architected Framework best practices.

## Table of Contents

1. [Optional Integration](#optional-integration)
2. [AwsSolutions Rule Pack](#awssolutions-rule-pack)
3. [Suppressing Violations](#suppressing-violations)

## Optional Integration

CDK Nag can be made optional in your CDK projects, which is particularly useful during development or prototyping phases. Here are several approaches to make CDK Nag optional:

### Using Environment Variables

```typescript
import { AwsSolutionsChecks } from 'cdk-nag';
import { App } from 'aws-cdk-lib';

// Create your CDK app
const app = new App();

// Add your stacks
new MyStack(app, 'MyStack');

// Apply CDK Nag conditionally based on environment variable
if (process.env.ENABLE_CDK_NAG === 'true') {
  console.log('CDK Nag enabled - checking for security issues');
  AwsSolutionsChecks.check(app);
} else {
  console.log('CDK Nag disabled - skipping security checks');
}
```

### Using CDK Context Parameters

```typescript
import { AwsSolutionsChecks } from 'cdk-nag';
import { App } from 'aws-cdk-lib';

// Create your CDK app
const app = new App();

// Add your stacks
new MyStack(app, 'MyStack');

// Apply CDK Nag conditionally based on context parameter
if (app.node.tryGetContext('enableCdkNag') === 'true') {
  console.log('CDK Nag enabled - checking for security issues');
  AwsSolutionsChecks.check(app);
} else {
  console.log('CDK Nag disabled - skipping security checks');
}
```

To enable CDK Nag with this approach, use:

```bash
cdk deploy --context enableCdkNag=true
```

### Environment-Specific Application

You can also apply CDK Nag only to specific environments:

```typescript
import { AwsSolutionsChecks } from 'cdk-nag';
import { App, Stack } from 'aws-cdk-lib';

// Create your CDK app
const app = new App();

// Get environment from context
const environment = app.node.tryGetContext('environment') || 'development';

// Add your stacks
const stack = new MyStack(app, 'MyStack');

// Apply CDK Nag only to production and staging environments
if (['production', 'staging'].includes(environment)) {
  console.log(`Applying CDK Nag checks for ${environment} environment`);
  AwsSolutionsChecks.check(stack);
}
```

## AwsSolutions Rule Pack

The AwsSolutions rule pack is the primary rule pack provided by CDK Nag. It contains rules based on AWS Solutions best practices and the AWS Well-Architected Framework.

To apply the AwsSolutions rule pack:

```typescript
import { AwsSolutionsChecks } from 'cdk-nag';
import { App } from 'aws-cdk-lib';

// Create your CDK app
const app = new App();

// Add your stacks
new MyStack(app, 'MyStack');

// Apply AwsSolutions checks
AwsSolutionsChecks.check(app);
```

## Suppressing Violations

⚠️ **CRITICAL: HUMAN DEVELOPER RESPONSIBILITY ONLY** ⚠️

CDK Nag suppressions should NEVER be applied by AI assistants or MCP clients. This is exclusively a human developer responsibility that requires careful consideration and security expertise.

### Process for Handling Violations

1. **Review**: Human developers should review all CDK Nag warnings and errors
2. **Analyze**: Determine if each violation represents a genuine security concern
3. **Remediate**: Whenever possible, fix the underlying issue rather than suppressing
4. **Document**: If suppression is necessary, document the specific reason with detailed justification
5. **Approve**: Require explicit human approval (ideally through code review)

### For Human Developers Only

The following code examples are provided ONLY for human developers to understand the syntax. AI assistants should NOT implement these patterns without explicit human review and approval.

#### Stack-Level Suppressions

```typescript
// HUMAN DEVELOPER RESPONSIBILITY - DO NOT IMPLEMENT AUTOMATICALLY
// This code must only be added after careful security review
import { NagSuppressions } from 'cdk-nag';
import { Stack } from 'aws-cdk-lib';

// Create your stack
const stack = new MyStack(app, 'MyStack');

// Suppress a rule for the entire stack
NagSuppressions.addStackSuppressions(stack, [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'REQUIRES SPECIFIC HUMAN JUSTIFICATION',
  },
]);
```

#### Resource-Level Suppressions

```typescript
// HUMAN DEVELOPER RESPONSIBILITY - DO NOT IMPLEMENT AUTOMATICALLY
// This code must only be added after careful security review
import { NagSuppressions } from 'cdk-nag';
import { Role, ServicePrincipal, ManagedPolicy } from 'aws-cdk-lib/aws-iam';

// Create a role with a managed policy
const role = new Role(this, 'MyRole', {
  assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
});
role.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('AmazonS3ReadOnlyAccess'));

// Suppress the warning for this specific role
NagSuppressions.addResourceSuppressions(role, [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'REQUIRES SPECIFIC HUMAN JUSTIFICATION',
  },
]);
```

#### Path-Based Suppressions

```typescript
// HUMAN DEVELOPER RESPONSIBILITY - DO NOT IMPLEMENT AUTOMATICALLY
// This code must only be added after careful security review
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';

// Create a construct
const myConstruct = new MyConstruct(this, 'MyConstruct');

// Suppress a rule for the construct and all its children
NagSuppressions.addResourceSuppressionsByPath(
  stack,
  '/MyStack/MyConstruct',
  [
    {
      id: 'AwsSolutions-IAM5',
      reason: 'REQUIRES SPECIFIC HUMAN JUSTIFICATION',
    },
  ]
);
```

For more detailed security best practices by service (IAM, S3, Cognito, API Gateway), please use the **CDK Guidance** tool in this MCP server and refer to the Security Best Practices section.
