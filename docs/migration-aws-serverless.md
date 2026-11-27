# Migration Guide: AWS Serverless MCP Server to the AWS MCP Server and the SAM CLI

This guide helps you migrate from `awslabs.aws-serverless-mcp-server` to two replacements: the [AWS SAM CLI](https://github.com/aws/aws-sam-cli), which your agent runs from its own shell, and the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS, for the AWS API calls. The [`aws-serverless`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-serverless) Agent Skill replaces much of the server's built-in guidance.

## Why We're Deprecating

The AWS Serverless MCP Server registered 25 tools and 6 MCP resources. They fall into three groups:

- **Local commands and files (9 tools).** `sam_init`, `sam_build`, `sam_deploy`, `sam_local_invoke`, and `sam_logs` built a `sam` command line and ran it on your machine. `deploy_webapp` wrote a `template.yaml` and `samconfig.toml` into your project from one of three bundled Jinja2 templates, ran `sam deploy`, and uploaded a local folder of frontend assets to Amazon S3. `update_webapp_frontend` synced a local folder to S3 and created an Amazon CloudFront invalidation. `get_serverless_templates` and `get_lambda_event_schemas` downloaded files from GitHub.
- **AWS API calls (6 tools).** `configure_domain` called AWS Certificate Manager (ACM), CloudFront, and Amazon Route 53. `get_metrics` called Amazon CloudWatch `GetMetricData`. `list_registries`, `search_schema`, and `describe_schema` called the Amazon EventBridge Schemas API. `esm_optimize` read AWS Lambda event source mappings (ESMs).
- **Bundled text (10 tools).** `get_lambda_guidance`, `get_iac_guidance`, `deploy_serverless_app_help`, `webapp_deployment_help`, `esm_guidance`, `esm_kafka_troubleshoot`, and the four `secure_esm_*_policy` tools returned guidance, generated SAM templates, troubleshooting steps, and IAM policies from strings in the package. They made no AWS calls.

Coding agents can already run shell commands, so your agent can run the same `sam` and `aws` commands itself and read their full output. The AWS MCP Server makes the AWS API calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It also reaches the rest of each API, which this server didn't have.

`run_script` has no access to your local files, can't start processes, and has no network access other than `call_boto3`. Steps that read your project folder (`sam build`, `sam deploy`, `sam local invoke`, and uploading built frontend assets) stay in your agent's shell.

### What the `aws-serverless` skill covers, and what it doesn't

The `aws-serverless` skill routes serverless work to a Lambda form factor and to the specialized skill that owns it, and keeps shared references on Lambda configuration, cold starts, concurrency, event sources, API Gateway, SAM and CDK resource types, production readiness, and troubleshooting. Against this server's bundled content:

| Old content | Covered by `aws-serverless`? |
|-------------|------------------------------|
| When to use Lambda, by use case (`get_lambda_guidance`) | Yes, and in more depth: its compute decision flow chooses between Event Functions, Web Functions, MicroVMs, and Managed Instances, and its references cover limits, packaging, and edge cases |
| SAM resource types and Globals, CDK serverless constructs, and `sam sync` (part of `get_iac_guidance`) | Yes, in `references/deployment.md` |
| Choosing among CloudFormation, SAM, CDK, and Terraform, with pros, cons, and example code (`get_iac_guidance`) | No. The [`aws-cloudformation`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-cloudformation) and [`aws-cdk`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-cdk) skills cover those tools individually |
| Step-by-step deployment help (`deploy_serverless_app_help`, `webapp_deployment_help`) | Partly. The skill covers architecture and SAM resources, and links to task skills such as `connecting-lambda-to-api-gateway` and `deploying-custom-domain-rest-api`. It doesn't walk through `sam init`, `sam build`, and `sam deploy`, or the Lambda Web Adapter templates `deploy_webapp` used |
| SQS, Kinesis, and DynamoDB Streams ESM settings, batch failures, filtering, and ESM provisioned mode (part of `esm_guidance` and `esm_optimize`) | Yes, in `references/event-sources.md` and `references/concurrency.md` |
| Generated SAM templates with VPC, subnets, security groups, and an MSK cluster (`esm_guidance`) | No. The agent writes the template, using the skill's references and the SAM documentation |
| Kafka ESM connectivity diagnosis: timeout before or after reaching the brokers, STS, Lambda, or on-failure destination unreachable, and authentication failures (`esm_kafka_troubleshoot`) | No. The skill's `troubleshooting.md` covers Lambda errors by message, not Kafka ESM connectivity. Use the AWS Knowledge Center article [How do I troubleshoot Lambda triggers that poll from Amazon MSK and self-managed Apache Kafka clusters?](https://repost.aws/knowledge-center/lambda-trigger-msk-kafka-cluster) |
| ESM IAM policy templates for MSK, SQS, Kinesis, and DynamoDB Streams (`secure_esm_*_policy`, `templates/iam_policies.py`) | No. See [Event source mapping IAM policies](#event-source-mapping-iam-policies) below |
| Runtime-to-event-type file map for seven runtimes (`get_lambda_event_schemas`) | No. See the table below |
| Fixed CloudWatch metric sets for Lambda, API Gateway, and CloudFront (`get_metrics`) | Partly. `references/production.md` lists a minimum alarm set (errors, throttles, p99 duration, iterator age, concurrent executions, DLQ depth); the agent queries those metrics with `GetMetricData` |
| EventBridge Schema Registry usage (`list_registries`, `search_schema`, `describe_schema` descriptions) | Partly. `aws-serverless` routes schema registry work to the [`amazon-eventbridge-event-bus`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/specialized-skills/serverless-skills/amazon-eventbridge-event-bus) skill, which covers registries for publishing open formats. Neither covers looking up AWS service event schemas in the `aws.events` registry |
| Serverless Land pattern search (`get_serverless_templates`) | No |
| SAM CLI commands for local testing and logs | No. The skill mentions `sam build` and `sam sync`, not `sam local invoke` or `sam logs` |

## Installing the Replacement

### AWS SAM CLI

Keep the SAM CLI installed, since the old server needed it too, and let your agent run `sam` commands in its shell. `sam local invoke` and `sam build --use-container` also need Docker, as before. See [Installing the AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html). The steps below also use the AWS CLI for S3 uploads and stack outputs.

### AWS MCP Server

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws-cli@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "AWS_REGION=us-east-1"
      ]
    }
  }
}
```

Set `AWS_REGION` to the Region of your serverless applications. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

### Installing the Agent Skills

```bash
npx skills add aws/agent-toolkit-for-aws/skills
```

This installs the `aws-serverless` skill along with the other core skills. An agent connected to the AWS MCP Server can also load it with the server's `retrieve_skill` tool.

### Permissions

The SAM CLI and AWS CLI use the same credentials and permissions as before. Your identity needs these for the `run_script` calls in this guide:

- Metrics: `cloudwatch:GetMetricData`
- Schemas: `schemas:ListRegistries`, `schemas:SearchSchemas`, and `schemas:DescribeSchema`
- Event source mappings: `lambda:ListEventSourceMappings` and `lambda:GetEventSourceMapping`, plus `lambda:UpdateEventSourceMapping` to apply changes
- Custom domains: `acm:RequestCertificate`, `acm:DescribeCertificate`, `acm:ListCertificates`, `cloudfront:GetDistributionConfig`, `cloudfront:UpdateDistribution`, `route53:ListHostedZonesByName`, and `route53:ChangeResourceRecordSets`
- Stacks and frontends: `cloudformation:DescribeStacks` and `cloudfront:CreateInvalidation`

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

### SAM CLI commands (host agent)

The SAM tools become `sam` commands your agent runs in its shell, from the project directory. The flags below come from the server's source.

| Old tool | What it ran | Replacement |
|----------|-------------|-------------|
| `sam_init` | `sam init --name <project_name> [--runtime <runtime>] --dependency-manager <manager> --output-dir <project_directory> --no-interactive --app-template <template> --architecture <arch> --package-type <Zip\|Image>`, plus `--base-image`, `--location`, `--extra-context`, `--tracing`, `--application-insights`, and the config options when set | The same command. Every other `sam init` option works too |
| `sam_build` | `sam build` with `--base-dir`, `--build-dir`, `--build-image`, `--container-env-var`, `--container-env-var-file`, `--manifest`, `--use-container`, `--parallel`, `--parameter-overrides`, `--template-file`, `--region`, and `--profile` when set | `sam build` with the same options, for example `sam build --use-container --parallel` |
| `sam_deploy` | `sam deploy --stack-name <application_name> --no-confirm-changeset`, plus `--template-file`, `--s3-bucket`, `--s3-prefix`, `--parameter-overrides`, `--capabilities`, `--tags`, `--metadata`, `--resolve-s3`, `--config-file`, `--config-env`, `--region`, and `--profile` when set. Required `--allow-write` | `sam deploy --stack-name <name> --resolve-s3 --capabilities CAPABILITY_IAM`. Drop `--no-confirm-changeset` to review the change set before it runs |
| `sam_local_invoke` | Wrote `event_data` to a temporary `.temp-event-*.json` file in the project if no `event_file` was given, then ran `sam local invoke <resource_name>` with `--template`, `--event`, `--env-vars`, `--docker-network`, `--container-env-vars`, `--parameter-overrides`, `--log-file`, `--layer-cache-basedir`, `--region`, and `--profile` when set. Returned stdout as `function_output` and stderr as `logs` | `sam local invoke <resource_name> --event events/event.json`, or pipe the event in with `echo '<json>' \| sam local invoke <resource_name> --event -` |
| `sam_logs` | `sam logs` with `--name`, `--stack-name`, `--cw-log-group`, `--start-time`, `--end-time`, `--config-file`, `--config-env`, `--save-params`, `--region`, and `--profile` when set. Required `--allow-sensitive-data-access` | `sam logs --stack-name <stack> [--name <resource>] --start-time '10min ago'`. `sam logs --tail` follows new events, which the old tool didn't offer |

### Web application deployment (host agent)

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `deploy_webapp` | Required `--allow-write`. Checked that dependencies were installed in `built_artifacts_path` (`node_modules`, `.dist-info`, or `vendor/bundle`) and that the startup script existed, or generated a `bootstrap` script such as `exec node <entry_point>`. Rendered the `backend`, `frontend`, or `fullstack` Jinja2 template into `<project_root>/template.yaml`, overwriting any file there, and wrote `samconfig.toml`. In a background thread, ran `sam deploy --stack-name <project_name> --capabilities CAPABILITY_IAM --no-confirm-changeset --no-fail-on-empty-changeset [--region]`, without `sam build`, then read the stack outputs and uploaded `built_assets_path` to the `WebsiteBucket` output with `upload_file`. Returned at once and recorded progress in a status file under the system temp directory | The agent writes `template.yaml` (a backend function with the [Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) layer, or an S3 bucket and CloudFront distribution for a frontend), then runs `sam deploy` as below. The old templates are in [`template/templates`](https://github.com/awslabs/mcp/tree/main/src/aws-serverless-mcp-server/awslabs/aws_serverless_mcp_server/template/templates) for reference. For a Node.js web server, the `aws-serverless` skill routes to Lambda Web Functions instead |
| `update_webapp_frontend` | Required `--allow-write`. Called `DescribeStacks` on the stack named `project_name`, read the `WebsiteBucket` output, uploaded every file in `built_assets_path` with `PutObject`, deleted objects that weren't in the folder, and, with `invalidate_cache` on (the default), created a CloudFront invalidation for `/*` | `aws s3 sync <built_assets_path> s3://<WebsiteBucket> --delete` in the shell, then `CreateInvalidation` through `run_script` or `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"` |

For a frontend or fullstack deployment, the agent might run:

```bash
sam deploy --stack-name my-app --resolve-s3 --capabilities CAPABILITY_IAM --region us-east-1
aws cloudformation describe-stacks --stack-name my-app --region us-east-1 --query "Stacks[0].Outputs"
aws s3 sync ./dist "s3://<WebsiteBucket>" --delete
aws cloudfront create-invalidation --distribution-id <CloudFrontDistributionId> --paths "/*"
```

The old templates output `WebsiteBucket`, `CloudFrontURL`, and `CloudFrontDistributionId` for frontends, and `ApiEndpoint`, `FunctionArn`, and `FunctionName` for backends.

### Templates and examples downloaded from GitHub (host agent)

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `get_serverless_templates` | Listed the top level of the [`aws-samples/serverless-patterns`](https://github.com/aws-samples/serverless-patterns) repository through the GitHub API, kept the first 5 folders whose names contained `template_type` or `runtime`, and returned each folder's `README.md` | Browse [Serverless Land patterns](https://serverlessland.com/patterns), or have the agent fetch the repository. `sam init --location <git-url>` also starts a project from a Git repository |
| `get_lambda_event_schemas` | Downloaded one event type definition from GitHub for 7 runtimes and up to 7 event sources (`api-gw`, `s3`, `sns`, `dynamodb`, `sqs`, `kinesis`, `eventbridge`) | Use the event types in your runtime's library, listed below. `sam local generate-event <service> <event>` also prints a sample event |

| Runtime | Event types |
|---------|-------------|
| Node.js / TypeScript | [`@types/aws-lambda`](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/aws-lambda/trigger) |
| Python | [`aws-lambda-powertools` data classes](https://docs.powertools.aws.dev/lambda/python/latest/utilities/data_classes/) |
| Java | [`aws-lambda-java-events`](https://github.com/aws/aws-lambda-java-libs/tree/main/aws-lambda-java-events) |
| PHP (Bref) | [`bref/src/Event`](https://github.com/brefphp/bref/tree/master/src/Event) |
| .NET | [`Amazon.Lambda.*Events`](https://github.com/aws/aws-lambda-dotnet/tree/master/Libraries/src) |
| Go | [`aws-lambda-go/events`](https://github.com/aws/aws-lambda-go/tree/main/events) |
| Rust | [`aws_lambda_events`](https://github.com/awslabs/aws-lambda-rust-runtime/tree/main/lambda-events/src/event) |

### AWS API calls (AWS MCP Server)

With the AWS MCP Server, ask your agent to perform the same operation and it makes the equivalent calls through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. `call_boto3` pages list operations automatically.

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `get_metrics` | Called `GetMetricData` for the last 24 hours (or `start_time` to `end_time`) at a 60-second period. For `lambda`: `Invocations`, `Errors`, and `Throttles` (Sum) and `Duration` (Average and p99) for `function_name`, or for a function named `project_name`. For `apiGateway` (on by default with `lambda`): `Count`, `4XXError`, and `5XXError` (Sum) and `Latency` (Average and p95), with dimensions `ApiName` set to `project_name` and `Stage` (default `prod`). For `cloudfront`: `Requests`, `BytesDownloaded`, `TotalErrorRate`, and `OriginLatency` for `distribution_id` | `call_boto3(service_name="cloudwatch", operation_name="GetMetricData", params={...})`, as in the example below. Read the function name from the stack's `FunctionName` output first |
| `list_registries` | `ListRegistries` with `RegistryNamePrefix`, `Scope`, `Limit`, and `NextToken` | `call_boto3(service_name="schemas", operation_name="ListRegistries", params={"Scope": "AWS"})` |
| `search_schema` | `SearchSchemas` with `Keywords` and `RegistryName` | `call_boto3(service_name="schemas", operation_name="SearchSchemas", params={"RegistryName": "aws.events", "Keywords": "aws.s3"})` |
| `describe_schema` | `DescribeSchema` with `RegistryName`, `SchemaName`, and optional `SchemaVersion`, returning the name, ARN, version, content, and last modified time | `call_boto3(service_name="schemas", operation_name="DescribeSchema", params={"RegistryName": "aws.events", "SchemaName": "aws.s3@ObjectCreated"})`. `ExportSchema` with `Type` `JSONSchemaDraft4` returns the schema in JSON Schema form |
| `esm_optimize(action="analyze")` | Called `ListEventSourceMappings` with no filter (one page, in the Region from `AWS_DEFAULT_REGION`, default `us-east-1`), and returned it with the min and max values from the Lambda `CreateEventSourceMapping` model and a fixed list of tradeoffs for each target (`failure_rate`, `latency`, `throughput`, `cost`) | `call_boto3(service_name="lambda", operation_name="ListEventSourceMappings", params={"FunctionName": ...})` or `GetEventSourceMapping` with the `UUID`. The `aws-serverless` skill's `event-sources.md` and `concurrency.md` cover the settings and their tradeoffs |
| `esm_optimize(action="validate")` | Checked `configs` against a fixed list of settings each event source doesn't support and against the min and max values in the Lambda service model. Made no AWS calls | Ask the agent to check the settings against `event-sources.md`, or apply them with `UpdateEventSourceMapping`, where the service rejects values it doesn't accept |
| `esm_optimize(action="generate_template")` | Required `--allow-write`. Returned a SAM template with a Lambda-backed custom resource that called `UpdateEventSourceMapping` with `optimized_configs`, plus a deployment script | Call `UpdateEventSourceMapping` through `run_script` after you approve the change, as in the example below, or change the `Events` properties of the function in your own template and run `sam deploy` |

To read a function's Lambda metrics the way `get_metrics` did, the agent might run:

```python
region = "us-east-1"
stack = (await call_boto3(service_name="cloudformation", operation_name="DescribeStacks", region_name=region, params={"StackName": "my-app"}))["Stacks"][0]
outputs = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
fn = outputs["FunctionName"]
end = datetime.datetime.now(datetime.timezone.utc)
queries = []
for i, (name, stat) in enumerate([("Invocations", "Sum"), ("Errors", "Sum"), ("Throttles", "Sum"), ("Duration", "Average"), ("Duration", "p99")]):
    queries.append({
        "Id": f"q{i}",
        "Label": f"{name} ({stat})",
        "MetricStat": {
            "Metric": {"Namespace": "AWS/Lambda", "MetricName": name, "Dimensions": [{"Name": "FunctionName", "Value": fn}]},
            "Period": 300,
            "Stat": stat,
        },
    })
resp = await call_boto3(
    service_name="cloudwatch",
    operation_name="GetMetricData",
    region_name=region,
    params={"StartTime": (end - datetime.timedelta(hours=24)).isoformat(), "EndTime": end.isoformat(), "MetricDataQueries": queries},
)
result = {r["Label"]: [[str(t), v] for t, v in zip(r["Timestamps"], r["Values"])] for r in resp["MetricDataResults"]}
result
```

CloudFront publishes its metrics in `us-east-1` with the dimensions `DistributionId` and `Region` set to `Global`, so pass `region_name="us-east-1"` and both dimensions for `AWS/CloudFront` queries. `OriginLatency` is reported only when additional metrics are turned on for the distribution.

To apply a new batch size and batching window to an event source mapping after you approve it, the agent might run:

```python
uuid = "<esm-uuid>"
before = await call_boto3(service_name="lambda", operation_name="GetEventSourceMapping", region_name="us-east-1", params={"UUID": uuid})
after = await call_boto3(
    service_name="lambda",
    operation_name="UpdateEventSourceMapping",
    region_name="us-east-1",
    params={"UUID": uuid, "BatchSize": 100, "MaximumBatchingWindowInSeconds": 5},
)
result = {k: (before.get(k), after.get(k)) for k in ("BatchSize", "MaximumBatchingWindowInSeconds", "State")}
result
```

If the mapping is defined in a SAM or CloudFormation template, change it there instead, so the next deployment doesn't revert it.

### Custom domains (AWS MCP Server)

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `configure_domain` | Required `--allow-write`. With `create_certificate` on (the default), called ACM `RequestCertificate` with DNS validation in the `region` you passed (or the default Region), then waited up to 15 minutes for the certificate to be issued; otherwise took the first `ISSUED` certificate from one page of `ListCertificates` whose domain matched. Searched one page of CloudFront `ListDistributions` for an origin whose domain contained `<project_name>-bucket`, then called `GetDistributionConfig` and `UpdateDistribution` to add `domain_name` to the aliases and set the certificate with `sni-only` and `TLSv1.2_2021`. With `create_route53_record` on (the default), found the first hosted zone from `ListHostedZones` whose name ended the domain and upserted an `A` alias record to `<distribution_id>.cloudfront.net` | The steps below through `run_script`, or set the alias and certificate on the distribution in your template and run `sam deploy` |

The agent can run each step through `run_script` and check its result before the next one:

1. Request the certificate in `us-east-1`, which CloudFront requires: `call_boto3(service_name="acm", operation_name="RequestCertificate", region_name="us-east-1", params={"DomainName": "app.example.com", "ValidationMethod": "DNS"})`.
2. Call `DescribeCertificate` for the `CertificateArn` and read `DomainValidationOptions[0].ResourceRecord`, which can take a few seconds to appear. Add that `CNAME` record to the hosted zone with Route 53 `ChangeResourceRecordSets`, after finding the zone with `ListHostedZonesByName`. ACM issues the certificate only after it sees this record.
3. Call `DescribeCertificate` again until `Status` is `ISSUED`. `run_script` doesn't run boto3 waiters, so each check is a separate call.
4. Call CloudFront `GetDistributionConfig` for the `CloudFrontDistributionId` stack output, add the domain to `Aliases`, set `ViewerCertificate` to the certificate ARN with `"SSLSupportMethod": "sni-only"` and `"MinimumProtocolVersion": "TLSv1.2_2021"`, and call `UpdateDistribution` with the config and `"IfMatch"` set to the `ETag`.
5. Upsert an `A` alias record (and an `AAAA` record if IPv6 is on) with `"AliasTarget": {"HostedZoneId": "Z2FDTNDATAQYW2", "DNSName": <the distribution's DomainName>, "EvaluateTargetHealth": False}`.

A domain set this way isn't in your template, so the stack drifts from it. The old `frontend` and `fullstack` templates already took a custom domain and certificate ARN in their `Aliases` and `ViewerCertificate`; keeping them in the template means the next `sam deploy` keeps them. For a REST API with a custom domain, the `deploying-custom-domain-rest-api` skill walks through the steps.

### Guidance and policy tools (Agent Skills)

| Old tool | What it returned | Replacement |
|----------|------------------|-------------|
| `get_lambda_guidance` | A fixed overview of when to use Lambda and when not to, pros, cons, decision criteria, and notes for 7 use cases (`api`, `data-processing`, `real-time`, `scheduled-tasks`, `web-app`, `mobile-backend`, `iot`) | The `aws-serverless` skill's compute decision flow |
| `get_iac_guidance` | A comparison of CloudFormation, SAM, CDK, and Terraform, with setup steps and example code for one of them | `aws-serverless` `references/deployment.md` for SAM and CDK resources, and the `aws-cloudformation` and `aws-cdk` skills |
| `deploy_serverless_app_help` | Six fixed steps for an `event_driven`, `backend`, or `fullstack` application, pointing to `sam_init`, `get_iac_guidance`, `sam_build`, and `sam_deploy` | The [SAM CLI](#sam-cli-commands-host-agent) commands above, with the `aws-serverless` skill for the architecture |
| `webapp_deployment_help` | Fixed help text on the parameters of `deploy_webapp` for each deployment type | [Web application deployment](#web-application-deployment-host-agent) above |
| `esm_guidance` | Required `--allow-write`. Setup, networking, or troubleshooting text for `dynamodb`, `kinesis`, `kafka`, or `sqs`, including generated SAM templates with VPC, security groups, IAM roles, and event source mappings | `aws-serverless` `references/event-sources.md` and `references/concurrency.md`, with the agent writing the template |
| `esm_kafka_troubleshoot` | Fixed diagnosis steps for MSK and self-managed Kafka (`diagnosis`), and resolution steps for one issue type, such as `pre-broker-timeout`, `sts-unreachable`, or `authentication-failed`. Required `--allow-write` for any issue type other than `diagnosis` | No Agent Skill covers this. Use the [Knowledge Center article on Lambda triggers for MSK and self-managed Kafka](https://repost.aws/knowledge-center/lambda-trigger-msk-kafka-cluster), and have the agent read the mapping's `StateTransitionReason` and `LastProcessingResult` with `GetEventSourceMapping` |
| `secure_esm_msk_policy`, `secure_esm_sqs_policy`, `secure_esm_kinesis_policy`, `secure_esm_dynamodb_policy` | Required `--allow-write`. Validated the Region, account ID, and names, and filled them into one of the IAM policy templates in `templates/iam_policies.py` | See below |

#### Event source mapping IAM policies

The four policy tools filled your Region, account, and resource names into fixed policy documents and made no AWS calls. Start from the AWS managed policies `AWSLambdaMSKExecutionRole`, `AWSLambdaSQSQueueExecutionRole`, `AWSLambdaKinesisExecutionRole`, and `AWSLambdaDynamoDBExecutionRole`, or the SAM policy templates `SQSPollerPolicy`, `KinesisStreamReadPolicy`, and `DynamoDBStreamReadPolicy`, and scope their `Resource` to your stream, queue, or cluster. The old templates stay in [`templates/iam_policies.py`](https://github.com/awslabs/mcp/blob/main/src/aws-serverless-mcp-server/awslabs/aws_serverless_mcp_server/templates/iam_policies.py) for reference. To check a policy the agent wrote, it can call IAM Access Analyzer through `run_script`:

```python
resp = await call_boto3(
    service_name="accessanalyzer",
    operation_name="ValidatePolicy",
    region_name="us-east-1",
    params={"policyDocument": policy_json, "policyType": "IDENTITY_POLICY"},
)
result = [(f["findingType"], f["issueCode"], f["findingDetails"]) for f in resp["findings"]]
result
```

### MCP resources

| Old resource | What it returned | Replacement |
|--------------|------------------|-------------|
| `template://list` | The names and frameworks of the three `deploy_webapp` templates | The template files in [`template/templates`](https://github.com/awslabs/mcp/tree/main/src/aws-serverless-mcp-server/awslabs/aws_serverless_mcp_server/template/templates) |
| `template://{template_name}` | The parameters, frameworks, and example usage of one template | The same files |
| `deployment://list` | The `deploy_webapp` deployments recorded in status files under the system temp directory (`aws-serverless-mcp-server-deployments`) | `call_boto3(service_name="cloudformation", operation_name="ListStacks", params={"StackStatusFilter": [...]})`, or `aws cloudformation list-stacks` |
| `deployment://{project_name}` | The recorded status of one deployment, with the CloudFormation stack status, reason, and outputs | `call_boto3(service_name="cloudformation", operation_name="DescribeStacks", params={"StackName": ...})`, and `DescribeStackEvents` for the cause of a failure |
| `streaming://infrastructure-setup` | Fixed keywords that told the agent to pick `esm_guidance`, `esm_optimize`, or `esm_kafka_troubleshoot` | Not needed; the `aws-serverless` skill's description tells the agent when to load it |
| `streaming://natural-language-detection` | Fixed phrases and a five-step workflow for the same purpose | Not needed |

### Command-line flags and environment variables

| Old setting | Replacement |
|-------------|-------------|
| `--allow-write` | IAM decides whether a deployment or API change succeeds, and your agent host asks before running shell commands you haven't allowed. See the first row of the Summary of Gaps. |
| `--allow-sensitive-data-access` | Not needed. `sam logs` and `logs:FilterLogEvents` need the matching IAM permissions |
| `AWS_REGION` | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call. Pass `--region` to `sam` and `aws` commands |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block. In the shell, `AWS_PROFILE` still selects the profile for `sam` and `aws` |
| `FASTMCP_LOG_LEVEL` | Not needed; it set the old server's log level |

## What Improves

- **Every SAM CLI command and flag.** The server wrapped five commands with a fixed set of options. The agent can also run `sam sync --watch`, `sam validate --lint`, `sam local start-api`, `sam logs --tail`, `sam list stack-outputs`, and `sam delete`, which the server had no tools for.
- **Deployment progress and errors in the conversation.** `deploy_webapp` returned "initiated successfully" at once and ran `sam deploy` in a background thread; its result went to the server log and a status file, and the agent had to read the `deployment://` resource to learn whether it failed. When the agent runs `sam deploy` in its shell, it reads CloudFormation's events and errors as they happen.
- **Your `template.yaml` stays yours.** `deploy_webapp` overwrote `template.yaml` and `samconfig.toml` in the project root on every call. With the replacement, the agent edits your template in place, and you can review the diff.
- **Schema search with a page size.** `search_schema` passed `limit` to `SearchSchemas` as a string, and the API takes an integer, so every call with a `limit` failed with `ParamValidationError` before reaching AWS. `call_boto3` passes the parameters you give it, and pages automatically.
- **Calls in the Region you choose.** The schema tools always called the Region in `AWS_REGION` when the server started (default `us-east-1`), and `esm_optimize` listed mappings in `AWS_DEFAULT_REGION`, not the `region` you passed. `call_boto3` takes `region_name` on each call.
- **Custom domains that resolve.** `configure_domain` requested a DNS-validated certificate but never created the validation record, so the certificate stayed pending until you added it, and the tool's wait timed out after 15 minutes. It looked up the distribution by an origin domain containing `<project_name>-bucket`, and the old templates let CloudFormation name the bucket. Its alias record pointed to `<distribution_id>.cloudfront.net`, and a distribution's domain name is not its ID. The steps above create the validation record, use the distribution ID from the stack outputs, and point the alias at the distribution's `DomainName`.
- **CloudFront metrics with data.** `get_metrics` queried `AWS/CloudFront` metrics with only the `DistributionId` dimension and in the Region you passed. CloudFront publishes them in `us-east-1` with `Region` set to `Global` too, so the query matches no data otherwise.
- **The rest of each API.** `run_script` reaches every CloudWatch, Lambda, EventBridge Schemas, CloudFormation, ACM, CloudFront, and Route 53 operation, such as CloudWatch Logs Insights queries, `GetFunctionConfiguration`, or `DescribeStackEvents`.

## Workflow Change

### Before (AWS Serverless MCP Server)

1. Install the SAM CLI and Docker, and start the server with `--allow-write` to deploy and `--allow-sensitive-data-access` to read logs.
2. Call `sam_init`, `sam_build`, and `sam_deploy`, or `deploy_webapp` with a deployment type and configuration, then poll the `deployment://` resource.
3. Call `get_metrics` and `sam_logs` to watch the application, and the guidance and `esm_*` tools for advice and templates.

### After (AWS SAM CLI and AWS MCP Server)

1. Ask your agent to create, build, test, or deploy the application. It runs `sam` in its shell, and your agent host asks you to approve each command unless you've allowed it. The `aws-serverless` skill guides the architecture and template.
2. For a web frontend, the agent runs `sam deploy`, `aws s3 sync`, and a CloudFront invalidation.
3. The agent reads metrics, schemas, stacks, and event source mappings through `run_script`, and makes changes, such as `UpdateEventSourceMapping`, after you approve them.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only mode (without `--allow-write`, the deploy, domain, frontend, ESM template, ESM guidance, and policy tools refused to run) | Not available | Deny `cloudformation:CreateChangeSet`, `cloudformation:ExecuteChangeSet`, `lambda:UpdateEventSourceMapping`, `cloudfront:UpdateDistribution`, and `route53:ChangeResourceRecordSets` to the identity your agent uses, with an identity-based policy, a permissions boundary, or an SCP. Leave `sam deploy` and `aws` commands to ask for approval in your agent host |
| Sensitive data mode (without `--allow-sensitive-data-access`, `sam_logs` refused to run) | Not available | Deny `logs:FilterLogEvents`, `logs:GetLogEvents`, and `logs:StartQuery` to the identity, or leave `sam logs` to ask for approval |
| Web application templates with Lambda Web Adapter, S3, and CloudFront, filled in from a few parameters | Changed | The agent writes the template, starting from the old files in [`template/templates`](https://github.com/awslabs/mcp/tree/main/src/aws-serverless-mcp-server/awslabs/aws_serverless_mcp_server/template/templates) if you like. For a Node.js server, the `aws-lambda-web-functions` skill |
| Generated `bootstrap` startup script and dependency check before deployment | Changed | The agent writes the script (for example `exec node app.js`) and runs `npm install --omit=dev` or `pip install -t` in the artifacts folder |
| Deployment status files and the `deployment://` resources | Not available | CloudFormation `DescribeStacks` and `DescribeStackEvents` |
| Kafka ESM troubleshooting steps (`esm_kafka_troubleshoot`) | Not available | No Agent Skill covers them; use the Knowledge Center article linked above with `GetEventSourceMapping` |
| ESM IAM policy templates (`secure_esm_*_policy`) | Not available | The AWS managed `AWSLambda*ExecutionRole` policies or SAM policy templates, checked with IAM Access Analyzer `ValidatePolicy` |
| Generated SAM templates for ESM setup and updates (`esm_guidance`, `esm_optimize`) | Changed | The agent writes the template, or calls `UpdateEventSourceMapping` after you approve |
| Runtime-to-event-type map (`get_lambda_event_schemas`) | Changed | The library table above, or `sam local generate-event` |
| Choosing among CloudFormation, SAM, CDK, and Terraform (`get_iac_guidance`) | Changed | The `aws-cloudformation` and `aws-cdk` skills cover those tools; no Agent Skill compares all four |
| Serverless Land pattern search (`get_serverless_templates`) | Not available | [Serverless Land patterns](https://serverlessland.com/patterns), or `sam init --location <git-url>` |
| Fixed metric sets for Lambda, API Gateway, and CloudFront (`get_metrics`) | Changed | `GetMetricData` as in the example above; `aws-serverless` `references/production.md` lists the metrics to alarm on |
| Redaction of 12-digit account IDs, access keys, IP addresses, emails, and similar strings in `esm_optimize` template results | Not available | `run_script` returns the API's response as AWS sends it; `call_boto3` uses your credentials and doesn't return them |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` to standard error at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.aws-serverless-mcp-server@latest` get that final release.
- The `src/aws-serverless-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.aws-serverless-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.aws-serverless-mcp-server`
