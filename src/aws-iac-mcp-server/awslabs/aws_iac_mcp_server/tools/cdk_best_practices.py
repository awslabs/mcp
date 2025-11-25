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


# Sourced from a combination of
# https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html
# https://docs.aws.amazon.com/cdk/v2/guide/best-practices-security.html
# https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-cdk-layers/best-practices.html
# https://docs.aws.amazon.com/cdk/v2/guide/hello-world.html (for Getting started)
# and a tiny bit of team opinion (CDK Nag)
CDK_BEST_PRACTICES_SUMMARY = """
# AWS CDK Best Practices for AI Agents

## Getting Started with CDK

### Create a new CDK project

**Use `cdk init` to scaffold a new project**
- Create a dedicated directory for each CDK project
- Initialize with the `app` template and your preferred language
- CDK CLI creates project structure with app and stack files

Example:
```bash
# Create and navigate to project directory
mkdir my-cdk-app && cd my-cdk-app

# Initialize CDK project
cdk init app --language typescript
# Or: --language javascript, python, java, csharp, go
```

**Project structure after initialization**
- `bin/` or root: Application entry point that instantiates stacks
- `lib/` or package directory: Stack definitions and constructs
- `cdk.json`: CDK Toolkit configuration
- `package.json`, `requirements.txt`, etc.: Language-specific dependencies

**Language-specific setup steps**

Python:
```bash
cdk init app --language python
source .venv/bin/activate  # Windows: .venv\\Scripts\activate
python -m pip install -r requirements.txt
```

Java:
```bash
cdk init app --language java
# Import as Maven project in your IDE
```

Go:
```bash
cdk init app --language go
go get  # Install dependencies
```

### Configure and bootstrap your AWS environment

**Specify target account and region in stack props**
```typescript
new MyStack(app, 'MyStack', {
  env: { account: '123456789012', region: 'us-east-1' }
});
```

**Bootstrap before first deployment**
```bash
cdk bootstrap  # Uses env from code
cdk bootstrap aws://123456789012/us-east-1  # Explicit
```

### Common CDK commands

**Build, list, deploy, and destroy**
- `npm run build` (TypeScript), `mvn compile` (Java), `go build` (Go) - Build your app
- `cdk list` - List all stacks in the app
- `cdk synth` - Synthesize CloudFormation template to `cdk.out/`
- `cdk deploy` - Deploy stacks to AWS
- `cdk destroy` - Delete deployed stacks

---

## Core Development Principles

### Code Organization

**Make decisions at synthesis time**
- Use programming language conditionals (`if` statements) instead of CloudFormation conditions
- Avoid CloudFormation `Parameters`, `Conditions`, and `{ Fn::If }`
- Treat CloudFormation as an implementation detail, not a language target

Example:
```typescript
// Good: Decision at synthesis time
const bucket = isProd
  ? new s3.Bucket(this, 'ProdBucket', { versioned: true })
  : new s3.Bucket(this, 'DevBucket');

// Avoid: CloudFormation conditions
```

### Resource Naming

**Use generated names, not physical names**
- Omit resource names to let CDK generate them
- Pass generated names via environment variables or references
- Hardcoded names prevent multiple deployments and resource replacement

Example:
```typescript
// Good: Generated name
const table = new dynamodb.Table(this, 'MyTable', {
  partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING }
});
// Pass to Lambda: table.tableName

// Avoid: Hardcoded name
const table = new dynamodb.Table(this, 'MyTable', {
  tableName: 'my-fixed-table-name',  // Prevents multiple deployments
  partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING }
});
```

### Stack Organization

**Model with constructs, deploy with stacks**
- Represent logical units as `Construct`, not `Stack`
- Use stacks only for deployment composition
- Stacks are the unit of deployment - everything deploys together

**Separate stacks by deployment requirements**
- Keep stateful resources (databases, S3 buckets) in separate stacks
- Enable termination protection on stateful stacks
- Don't nest stateful resources in constructs likely to be moved or renamed

Example:
```typescript
// Separate stacks for stateful and stateless resources
class DatabaseStack extends Stack {
  public readonly table: dynamodb.Table;

  constructor(scope: Construct, id: string) {
    super(scope, id, { terminationProtection: true });
    this.table = new dynamodb.Table(this, 'Table', { ... });
  }
}

class ApiStack extends Stack {
  constructor(scope: Construct, id: string, table: dynamodb.Table) {
    super(scope, id);
    const lambda = new lambda.Function(this, 'Handler', { ... });
    table.grantReadWriteData(lambda);
  }
}
```

### Configuration

**Configure with properties and methods, not environment variables**
- Accept properties objects for full configurability in code
- Limit environment variable lookups to the top level of the app
- Use environment variables only for development environment information

Example:
```typescript
// Good: Configuration via properties
interface MyConstructProps {
  readonly retentionDays: number;
  readonly enableEncryption: boolean;
}

class MyConstruct extends Construct {
  constructor(scope: Construct, id: string, props: MyConstructProps) {
    super(scope, id);
    // Use props.retentionDays, props.enableEncryption
  }
}

// Avoid: Environment variable lookups in constructs
const retentionDays = process.env.RETENTION_DAYS; // Anti-pattern
```

### Determinism and Context

**Commit `cdk.context.json` to version control**
- Ensures deterministic deployments
- Records snapshots of non-deterministic values (AZs, AMIs, VPC lookups)
- Prevents unexpected changes from AWS-side updates

**Never modify AWS resources during synthesis**
- Synthesis should be read-only with no side effects
- Use custom resources for changes that must happen at deployment time
- Avoid network calls during synthesis when possible

### Resource Management

**Define removal policies and log retention**
- Default CDK behavior retains all data and logs forever
- Explicitly set removal policies for production resources
- Use Aspects to validate removal and logging policies

Example:
```typescript
const bucket = new s3.Bucket(this, 'Bucket', {
  removalPolicy: cdk.RemovalPolicy.DESTROY,  // Explicit for non-prod
  autoDeleteObjects: true
});

const logGroup = new logs.LogGroup(this, 'Logs', {
  retention: logs.RetentionDays.ONE_WEEK  // Explicit retention
});
```

**Don't change logical IDs of stateful resources**
- Changing logical IDs causes resource replacement
- Write unit tests asserting logical IDs remain static
- Logical ID derives from construct `id` and position in construct tree

### Testing

**Unit test your infrastructure**
- Write tests confirming generated templates match expectations
- Test that logical IDs of stateful resources remain static
- Ensure deterministic synthesis for reliable testing

Example:
```typescript
import { Template } from 'aws-cdk-lib/assertions';

test('Bucket has encryption enabled', () => {
  const stack = new MyStack(app, 'TestStack');
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::S3::Bucket', {
    BucketEncryption: {
      ServerSideEncryptionConfiguration: [{
        ServerSideEncryptionByDefault: {
          SSEAlgorithm: 'AES256'
        }
      }]
    }
  });
});
```

### Monitoring

**Measure everything**
- Create metrics, alarms, and dashboards for all resources
- Record business metrics, not just infrastructure metrics
- Use measurements to automate deployment decisions
- Use L2 construct convenience methods like `metricUserErrors()`

Example:
```typescript
const table = new dynamodb.Table(this, 'Table', { ... });

// Create alarm on user errors
const alarm = table.metricUserErrors()
  .createAlarm(this, 'UserErrorsAlarm', {
    threshold: 10,
    evaluationPeriods: 2
  });
```

---

## Constructs Best Practices

### Construct Levels

**Understand the three construct levels**
- **L1 (CfnXxx)**: Direct CloudFormation resources, 1:1 mapping
- **L2**: Curated constructs with sensible defaults and helper methods
- **L3**: Opinionated patterns combining multiple resources

### L1 Constructs (CloudFormation Resources)

**Avoid L1 constructs when possible**
- Use L2 constructs for better developer experience
- L1 constructs lack helper methods and sensible defaults

**Access underlying L1 via `defaultChild` when needed**
```typescript
const bucket = new s3.Bucket(this, 'Bucket');
const cfnBucket = bucket.node.defaultChild as s3.CfnBucket;

// Modify L1 properties not exposed by L2
cfnBucket.analyticsConfigurations = [{
  id: 'analytics',
  storageClassAnalysis: { dataExport: { ... } }
}];
```

**Use `addPropertyOverride` as ultimate escape hatch**
```typescript
const bucket = new s3.Bucket(this, 'Bucket');
const cfnBucket = bucket.node.defaultChild as s3.CfnBucket;

// Override any CloudFormation property
cfnBucket.addPropertyOverride('WebsiteConfiguration.RoutingRules', [
  {
    RedirectRule: { HostName: 'example.com' },
    RoutingRuleCondition: { HttpErrorCodeReturnedEquals: '404' }
  }
]);
```

### L2 Constructs (Curated Constructs)

**Leverage L2 helper methods**
- Use `grant*()` methods for permissions
- Use `metric*()` methods for CloudWatch metrics
- Use `addToResourcePolicy()` for resource policies
- Configure via properties, add details via methods

Example:
```typescript
const bucket = new s3.Bucket(this, 'Bucket');
const lambda = new lambda.Function(this, 'Function', { ... });

// Helper methods
bucket.grantReadWrite(lambda);
bucket.addLifecycleRule({ expiration: Duration.days(90) });
bucket.addEventNotification(
  s3.EventType.OBJECT_CREATED,
  new s3n.LambdaDestination(lambda)
);

// Metrics
const metric = bucket.metricNumberOfObjects();
metric.createAlarm(this, 'Alarm', {
  threshold: 1000,
  evaluationPeriods: 1
});
```

**Prefer L2 constructs over L1**
- Better type safety and IDE support
- Automatic creation of supporting resources (roles, policies)
- Sensible defaults following AWS best practices

### L3 Constructs (Patterns)

**Use L3 constructs carefully**
- Evaluate if a helper class is more appropriate than extending `Construct`
- Extend `Construct` only when directly interacting with AWS resources
- Extend specific L2 constructs only to change default properties

**When to extend `Construct` directly**
```typescript
import { Construct } from 'constructs';

// Good: Custom pattern combining multiple resources
class WebsiteWithApi extends Construct {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    const bucket = new s3.Bucket(this, 'Bucket', {
      websiteIndexDocument: 'index.html'
    });

    const api = new apigateway.RestApi(this, 'Api');
    // ... configure API
  }
}
```

**When to use a helper class instead**
```typescript
// Good: Logic without AWS resources
class ConfigurationBuilder {
  private config: Record<string, string> = {};

  addParameter(key: string, value: string): this {
    this.config[key] = value;
    return this;
  }

  build(): Record<string, string> {
    return this.config;
  }
}

// Use in construct
const config = new ConfigurationBuilder()
  .addParameter('key1', 'value1')
  .build();
```

**When to extend L2 constructs**
```typescript
// Good: Changing default properties of existing construct
class EncryptedBucket extends s3.Bucket {
  constructor(scope: Construct, id: string, props?: s3.BucketProps) {
    super(scope, id, {
      ...props,
      encryption: s3.BucketEncryption.KMS,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true
    });
  }
}
```

### Construct Design

**Keep constructs focused and composable**
- Each construct should represent a single logical unit
- Compose constructs to build larger patterns
- Avoid monolithic constructs that do too much

**Make constructs reusable**
- Accept configuration via properties
- Expose important resources as public properties
- Document expected usage and limitations

Example:
```typescript
interface ApiWithDatabaseProps {
  readonly databaseName: string;
  readonly apiThrottling?: apigateway.ThrottleSettings;
}

class ApiWithDatabase extends Construct {
  public readonly api: apigateway.RestApi;
  public readonly database: dynamodb.Table;

  constructor(scope: Construct, id: string, props: ApiWithDatabaseProps) {
    super(scope, id);

    this.database = new dynamodb.Table(this, 'Database', {
      tableName: props.databaseName,
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING }
    });

    this.api = new apigateway.RestApi(this, 'Api', {
      deployOptions: {
        throttlingRateLimit: props.apiThrottling?.rateLimit,
        throttlingBurstLimit: props.apiThrottling?.burstLimit
      }
    });
  }
}
```

### Compliance and Wrapper Constructs

**Don't rely solely on wrapper constructs for compliance**
- Wrapper constructs can be bypassed
- Use service control policies and permission boundaries for enforcement
- Use Aspects and CloudFormation Guard for validation
- Wrapper constructs may prevent use of third-party construct libraries

Example:
```typescript
// Wrapper construct for compliance
class CompliantBucket extends s3.Bucket {
  constructor(scope: Construct, id: string, props?: s3.BucketProps) {
    super(scope, id, {
      ...props,
      encryption: s3.BucketEncryption.KMS,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true
    });
  }
}

// But also enforce with Aspects
class BucketComplianceAspect implements IAspect {
  visit(node: IConstruct): void {
    if (node instanceof s3.CfnBucket) {
      if (!node.bucketEncryption) {
        Annotations.of(node).addError('All buckets must have encryption enabled');
      }
    }
  }
}
```

### Construct Hierarchy

**Organize constructs by abstraction level**
- Low-level constructs: Individual resources with minimal logic
- Mid-level constructs: Related resources working together
- High-level constructs: Complete features or applications

**Pass references between constructs**
```typescript
// Low-level: Individual resource
class Database extends Construct {
  public readonly table: dynamodb.Table;

  constructor(scope: Construct, id: string) {
    super(scope, id);
    this.table = new dynamodb.Table(this, 'Table', { ... });
  }
}

// Mid-level: Related resources
class ApiBackend extends Construct {
  constructor(scope: Construct, id: string, database: Database) {
    super(scope, id);

    const lambda = new lambda.Function(this, 'Handler', { ... });
    database.table.grantReadWriteData(lambda);

    const api = new apigateway.LambdaRestApi(this, 'Api', {
      handler: lambda
    });
  }
}

// High-level: Complete application
class Application extends Stack {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    const database = new Database(this, 'Database');
    const api = new ApiBackend(this, 'Api', database);
  }
}
```

---

## Security Best Practices

### IAM and Permissions Management

**Follow IAM security best practices**
- Apply principle of least privilege
- Use IAM roles instead of long-term credentials
- Regularly review and audit permissions
- Reference: [IAM Security Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/IAMBestPracticesAndUseCases.html)

**Let CDK manage roles and security groups**
- Use `grant()` convenience methods for minimal permissions
- CDK creates roles with least-privilege policies automatically
- Avoid predefined roles that limit application design flexibility

Example:
```typescript
const bucket = new s3.Bucket(this, 'Bucket');
const lambda = new lambda.Function(this, 'Function', { ... });

// Single line grants minimal read permissions
bucket.grantRead(lambda);

// Avoid: Manual role creation with broad permissions
```

**Use grant methods for resource permissions**
- L2 constructs provide `grant*()` methods for common access patterns
- Automatically creates least-privilege IAM policies
- Eliminates manual role and policy creation

Example:
```typescript
const table = new dynamodb.Table(this, 'Table', { ... });
const lambda = new lambda.Function(this, 'Function', { ... });

// Grants only necessary DynamoDB permissions
table.grantReadWriteData(lambda);
```

**Use validation tools**
- Use CDK Aspects to validate security properties before deployment
- Use CloudFormation Guard for policy-as-code validation
- Don't rely solely on wrapper constructs for compliance

Example:
```typescript
import { IAspect, IConstruct } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';

class BucketEncryptionChecker implements IAspect {
  visit(node: IConstruct): void {
    if (node instanceof s3.CfnBucket) {
      if (!node.bucketEncryption) {
        throw new Error(`Bucket ${node.node.path} must have encryption enabled`);
      }
    }
  }
}

// Apply aspect to stack
Aspects.of(stack).add(new BucketEncryptionChecker());
```

### Secrets and Sensitive Data

**Use Secrets Manager and Parameter Store**
- Store sensitive values in AWS Secrets Manager or Systems Manager Parameter Store
- Reference by name or ARN in CDK code
- Never hardcode credentials or secrets in code

Example:
```typescript
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as ssm from 'aws-cdk-lib/aws-ssm';

// Reference existing secret
const dbPassword = secretsmanager.Secret.fromSecretNameV2(
  this, 'DBPassword', 'prod/db/password'
);

// Reference parameter
const apiKey = ssm.StringParameter.valueForStringParameter(
  this, '/prod/api/key'
);

// Use in resources
const lambda = new lambda.Function(this, 'Function', {
  environment: {
    DB_PASSWORD_ARN: dbPassword.secretArn,
    API_KEY: apiKey
  }
});

dbPassword.grantRead(lambda);
```

### Resource Security

**Enable encryption by default**
- Enable encryption for S3 buckets, EBS volumes, RDS databases
- Use AWS managed keys (SSE-S3, SSE-KMS) or customer managed keys
- Many L2 constructs enable encryption by default

Example:
```typescript
// S3 bucket with encryption
const bucket = new s3.Bucket(this, 'Bucket', {
  encryption: s3.BucketEncryption.S3_MANAGED,
  enforceSSL: true  // Require SSL for all requests
});
```

**Configure secure defaults**
- Block public access on S3 buckets
- Enable VPC flow logs
- Use security groups with minimal ingress rules
- Enable CloudTrail logging

Example:
```typescript
const vpc = new ec2.Vpc(this, 'VPC', {
  flowLogs: {
    'FlowLog': {
      trafficType: ec2.FlowLogTrafficType.ALL
    }
  }
});
```

## Compliance best practices

### CDK Nag
CDK Nag provides a list of compliance rules: https://github.com/cdklabs/cdk-nag/blob/main/RULES.md

**(Optional) Use CDK Nag for compliance checks**
Before applying CDK Nag compliance checks, you MUST ask the user if they would like to use CDK Nag.

IF the user provides their consent, install cdk-nag using npm: 'npm install cdk-nag'.

Code example:
```
import { Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
```

---

## Key Takeaways

1. **Always prefer L2 constructs** over L1 constructs
2. **Use grant methods** for permissions instead of manual IAM policies
3. **Enable encryption by default** for all applicable resources
4. **Never hardcode resource names** - let CDK generate them
5. **Make decisions in code**, not CloudFormation templates
6. **Keep infrastructure and runtime code together**
7. **Use properties for configuration**, not environment variables
8. **Test infrastructure code** with unit tests
9. **Separate stateful and stateless resources** into different stacks
10. **Always define removal policies** explicitly for production resources
"""

CDK_BEST_PRACTICES_KNOWLEDGE = KnowledgeResult(
    rank=1,
    title='AWS CDK Best Practices',
    url='',
    context=CDK_BEST_PRACTICES_SUMMARY,
)
