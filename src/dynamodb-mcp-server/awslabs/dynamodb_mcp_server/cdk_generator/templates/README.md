# Cost Performance DynamoDB CDK

CDK app to provision your DynamoDB data model.

This is part of AWS DynamoDB MCP Server, for more details see: https://github.com/awslabs/mcp/tree/main/src/dynamodb-mcp-server

## Usage

Note the stack name is fixed, so deploying this multiple times to the same AWS account and region would update the same stack and not create a new one. If you need to deploy two instances of this tasks at once, you'll need to use another AWS account or another region or to change the CDK app to use a different stack name.

### Prerequisites

- Data modeling resources created using the AWS DynamoDB MCP Server.
- Node.js 22+
- AWS account credentials. See the CDK documentation [here](https://docs.aws.amazon.com/cdk/v2/guide/configure-access.html) for details.

### Bootstrap

You only need to run the CDK bootstrap process once per account and region.

```bash
npx cdk bootstrap aws://${account}/${region}
```

### Deploy

To deploy the stack run:

```bash
npx cdk deploy
```

### Destroy

To destroy the stack run:

```bash
npx cdk destroy
```

### Example

```bash
export AWS_PROFILE=my-profile
export AWS_REGION=us-west-2

npx cdk bootstrap aws://123456789012/us-west-2

npx cdk deploy

npx cdk destroy
```

### Other Commands

- `npx cdk synth` emits the synthesized CloudFormation template
- `npx cdk diff` compare deployed stack with your AWS account/region
