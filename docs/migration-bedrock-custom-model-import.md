# Migration Guide: AWS Bedrock Custom Model Import MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.aws-bedrock-custom-model-import-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The AWS Bedrock Custom Model Import MCP Server registered 6 tools and 6 prompts. Each tool wrapped one Amazon Bedrock Custom Model Import API operation: `CreateModelImportJob`, `GetModelImportJob`, `ListModelImportJobs`, `GetImportedModel`, `ListImportedModels`, or `DeleteImportedModel`. Around those calls it added a search of one S3 bucket for the model files, a fallback to the IAM role behind your own credentials, a timestamp on every new job and model name, and approximate name matching in the two get tools. Each prompt only told the agent to use the tool of the same name. The AWS MCP Server makes the same calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It also reaches the rest of the Amazon Bedrock API.

The `aws-ai-ml` Agent Skill covers one Custom Model Import path: deploying a model you fine-tuned with SageMaker Serverless Model Customization to Amazon Bedrock, through the SageMaker Python SDK's `BedrockModelBuilder`. It lists importing other weights, such as a Hugging Face model in your own S3 bucket, as out of scope, and the `amazon-bedrock` skill doesn't cover Custom Model Import, so for those imports there's no skill to install.

## Installing the Replacement

### Configuration

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

Set `AWS_REGION` to the Region where you import models. [Custom Model Import in the Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) lists the Regions and model architectures it supports. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the permissions the old server used:

- `bedrock:CreateModelImportJob`, `bedrock:GetModelImportJob`, `bedrock:ListModelImportJobs`, `bedrock:GetImportedModel`, `bedrock:ListImportedModels`, and `bedrock:DeleteImportedModel`
- `iam:PassRole` on the service role you hand to the import job
- `s3:ListBucket` on the model bucket, which the old server used to search for model files and the agent uses to list them

The old server also called `sts:GetCallerIdentity` to pick a role when you didn't give one; the replacement doesn't. The service role itself doesn't change: it trusts `bedrock.amazonaws.com` and can read the model files in S3 (see [Create a service role for importing pre-trained models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-import-iam-role.html)).

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

Every tool in the old server called one Custom Model Import API operation, and `create_model_import_job` also read S3 and STS first. With the AWS MCP Server, ask your agent to perform the same operation and it will make the equivalent call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. The old tools turned each response into Markdown, and the job list left out each job's ARN and end time; `call_boto3` returns the API response itself.

To find the folders that hold model weights, in place of the old server's bucket search, the agent might run:

```python
listing = await call_boto3(
    service_name="s3",
    operation_name="ListObjectsV2",
    region_name="us-east-1",
    params={"Bucket": "amzn-s3-demo-bucket", "Prefix": "models/"},
)
folders = {}
for obj in listing.get("Contents", []):
    folder, _, name = obj["Key"].rpartition("/")
    entry = folders.setdefault(folder, {"safetensors": 0, "config.json": False, "bytes": 0})
    entry["bytes"] += obj["Size"]
    if name.endswith(".safetensors"):
        entry["safetensors"] += 1
    if name == "config.json":
        entry["config.json"] = True
result = {f"s3://amzn-s3-demo-bucket/{k}/": v for k, v in folders.items() if v["safetensors"]}
result
```

Set `Prefix` to the folder you keep models in, and pick the folder to import from the result.

Then, in place of `create_model_import_job`:

```python
job = await call_boto3(
    service_name="bedrock",
    operation_name="CreateModelImportJob",
    region_name="us-east-1",
    params={
        "jobName": "llama-3-2-1b-import-20261110",
        "importedModelName": "llama-3-2-1b-instruct",
        "roleArn": "arn:aws:iam::111122223333:role/BedrockModelImportRole",
        "modelDataSource": {"s3DataSource": {"s3Uri": "s3://amzn-s3-demo-bucket/models/llama-3-2-1b-instruct/"}},
        "jobTags": [{"key": "CreatedBy", "value": "agent"}],
        "importedModelTags": [{"key": "CreatedBy", "value": "agent"}],
    },
)
status = await call_boto3(
    service_name="bedrock",
    operation_name="GetModelImportJob",
    region_name="us-east-1",
    params={"jobIdentifier": job["jobArn"]},
)
result = {"jobArn": job["jobArn"], "status": status["status"]}
result
```

The `CreatedBy` tags are the ones the old server added when you passed no tags; leave them out or use your own.

And, to find a job or model by part of its name, in place of the get tools' approximate matching:

```python
jobs = await call_boto3(
    service_name="bedrock",
    operation_name="ListModelImportJobs",
    region_name="us-east-1",
    params={"nameContains": "llama", "sortBy": "CreationTime", "sortOrder": "Descending"},
)
models = await call_boto3(
    service_name="bedrock",
    operation_name="ListImportedModels",
    region_name="us-east-1",
    params={"nameContains": "llama"},
)
result = {
    "jobs": [(j["jobName"], j["status"]) for j in jobs["modelImportJobSummaries"]],
    "models": [(m["modelName"], m["modelArn"]) for m in models["modelSummaries"]],
}
result
```

`call_boto3` pages list operations automatically, so `ListModelImportJobs` and `ListImportedModels` need one call each.

### Model import jobs

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_model_import_job(request)` | Refused every call unless the server started with `--allow-write` and with `BEDROCK_MODEL_IMPORT_S3_BUCKET` set, even when the request had `modelDataSource`. Without `modelDataSource`, it listed every object in that bucket and picked the folder whose name best matched `importedModelName`, among folders that directly hold a `.safetensors` file. Without `roleArn`, it used `BEDROCK_MODEL_IMPORT_ROLE_ARN`, or else the IAM role behind your own credentials (from `GetCallerIdentity`). It appended `-YYYYMMDD-HHMMSS` to `jobName` and `importedModelName`, added a `CreatedBy=agent` tag to the job and the model when you passed no tags, set a random `clientRequestToken`, called `CreateModelImportJob`, then called `GetModelImportJob` for the status. | `run_script` combining `call_boto3(service_name="bedrock", operation_name="CreateModelImportJob", params={"jobName": ..., "importedModelName": ..., "roleArn": ..., "modelDataSource": {"s3DataSource": {"s3Uri": ...}}})` and `GetModelImportJob`, as in the second example. `jobTags`, `importedModelTags`, `clientRequestToken`, `vpcConfig`, and `importedModelKmsKeyId` work as before. |
| `get_model_import_job(job_identifier)` | Called `GetModelImportJob`. Bedrock answers a job name that doesn't exist with `ValidationException`, and on that error the tool called `ListModelImportJobs` with `nameContains` set to the identifier and took the first match, preferring an `InProgress` job. With no match, it listed every job and returned the closest name by approximate matching, picking at random on a tie. Only the job name in the response showed that it was a different job. | `call_boto3(service_name="bedrock", operation_name="GetModelImportJob", params={"jobIdentifier": ...})` with the exact job name or ARN. To search, use `ListModelImportJobs` with `nameContains`, as in the third example. |
| `list_model_import_jobs(request)` | Called `ListModelImportJobs` with the optional `statusEquals`, `nameContains`, `creationTimeAfter`, `creationTimeBefore`, `sortBy`, and `sortOrder`, and returned the first page as a Markdown table. It had no `maxResults` or `nextToken` input. | `call_boto3(service_name="bedrock", operation_name="ListModelImportJobs", params={"statusEquals": ..., "nameContains": ..., "sortBy": "CreationTime", "sortOrder": "Descending"})`, which pages automatically |

### Imported models

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `get_imported_model(model_identifier)` | Called `GetImportedModel`. On a `ValidationException`, which is what a model name that doesn't exist returns, it called `ListImportedModels` with `nameContains` and took the first model, or else listed every model and returned the closest name, picking at random on a tie | `call_boto3(service_name="bedrock", operation_name="GetImportedModel", params={"modelIdentifier": ...})` with the exact model name or ARN. To search, use `ListImportedModels` with `nameContains`. |
| `list_imported_models(request)` | Called `ListImportedModels` with the optional `nameContains`, `creationTimeAfter`, `creationTimeBefore`, `sortBy`, and `sortOrder`, and returned the first page as a Markdown table, with no `maxResults` or `nextToken` input | `call_boto3(service_name="bedrock", operation_name="ListImportedModels", params={"nameContains": ..., "sortBy": "CreationTime", "sortOrder": "Descending"})` |
| `delete_imported_model(model_identifier)` | Refused unless the server started with `--allow-write`, then called `DeleteImportedModel` with the identifier as given, with no approximate matching | `call_boto3(service_name="bedrock", operation_name="DeleteImportedModel", params={"modelIdentifier": ...})` |

### Prompts

The six prompts, which share the tool names, each returned one sentence telling the agent to use the tool of the same name. With the AWS MCP Server, ask for the operation directly.

Because `run_script` exposes the full Amazon Bedrock API, operations the old server never had, such as `TagResource` and `ListTagsForResource` on an import job or imported model, are also available.

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION` (default `us-east-1`) | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | Set them in the proxy's `env` block; the proxy signs requests with the standard AWS credential chain |
| `BEDROCK_MODEL_IMPORT_S3_BUCKET` | Name the S3 folder in your request, or ask the agent to list the bucket first, as in the first example |
| `BEDROCK_MODEL_IMPORT_ROLE_ARN` | Give the service role ARN in your request; `CreateModelImportJob` requires `roleArn` |
| `FASTMCP_LOG_LEVEL` | Not needed; it set the old server's log level |

## What Improves

- **Imports with an S3 URI and no bucket setting.** `create_model_import_job` stopped with "Please configure S3 bucket for MCP server" whenever `BEDROCK_MODEL_IMPORT_S3_BUCKET` was unset, even when the request gave `modelDataSource`. Through `call_boto3`, the S3 URI in the request is all it needs.
- **Lookups return the job or model you named.** The get tools answered a name that didn't exist with a near match. Given three job names, `llama-3-1-8b-import-20261101-101010`, `llama-3-2-1b-import-20261105-090000`, and `qwen2-5-7b-import-20261103-120000`, the old matcher answered `llama-3-2-3b-import` with the `llama-3-2-1b` job, `qwen3-8b-import` with the `qwen2-5-7b` job, and `mistral-import` with one of the two llama jobs at random. `GetModelImportJob` returns `ValidationException` ("The provided job identifier is invalid.") instead, and `nameContains` on the list operations shows every candidate.
- **The model folder you choose.** The old search compared `importedModelName` with the name of each folder that directly holds a `.safetensors` file, across the whole bucket. In testing, `llama` picked `models/llama-3-2-1b-instruct` 10 times and `models/llama-3-1-8b-instruct` 10 times in 20 tries. A folder laid out like a SageMaker training output, `finetuned/run-7/checkpoints/hf_merged/`, could only match the name `hf_merged`, so `run-7` found nothing. With `run_script`, the agent lists the folders and you name the one to import.
- **No surprise service role.** With no `roleArn` and no `BEDROCK_MODEL_IMPORT_ROLE_ARN`, the old server passed the IAM role behind your own credentials as the import job's service role. In testing, that was an EC2 instance role whose trust policy allows only `ec2.amazonaws.com`, so Bedrock couldn't assume it. `call_boto3` stops a `CreateModelImportJob` call without `roleArn` before it reaches AWS and names the four required parameters.
- **Names you choose.** The old server accepted names up to 50 characters and then appended a 16-character timestamp, so a 50-character name became 66 characters, past the API's 63-character limit for `jobName` and `importedModelName`. `call_boto3` sends the names as given.
- **Responses as data.** The old tools returned Markdown and appended fixed background text about Bedrock to each list, get, and create response, about 1,800 characters on a list response. The list tools returned only the first page. `call_boto3` returns the API response and pages list operations automatically.

## Workflow Change

### Before (AWS Bedrock Custom Model Import Server)

1. Set `BEDROCK_MODEL_IMPORT_S3_BUCKET`, and optionally `BEDROCK_MODEL_IMPORT_ROLE_ARN`, then start the server with `--allow-write`, or `create_model_import_job` and `delete_imported_model` fail.
2. Ask to import a model by name. The server searches the bucket for a matching folder, picks a role, adds a timestamp to both names, and starts the job.
3. Ask for a job or model by name. If the name doesn't exist, the server returns a near match.

### After (AWS MCP Server)

1. Give the agent your Region, the S3 folder (or the bucket to list), and the service role ARN.
2. The agent starts the job with `CreateModelImportJob` through `run_script` and checks it with `GetModelImportJob` when you ask.
3. Whether a call succeeds is decided by IAM: your identity-based policies, permissions boundaries, and service control policies (SCPs).
4. Look up jobs and models by exact name or ARN, or search with `nameContains`.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only mode by default (`create_model_import_job` and `delete_imported_model` needed `--allow-write`) | Not available | Run with credentials that allow only `bedrock:GetModelImportJob`, `bedrock:ListModelImportJobs`, `bedrock:GetImportedModel`, and `bedrock:ListImportedModels`, or deny `bedrock:CreateModelImportJob` and `bedrock:DeleteImportedModel` with a permissions boundary or SCP |
| Model folder found from the model name in `BEDROCK_MODEL_IMPORT_S3_BUCKET` | Changed | Ask the agent to list the bucket, as in the first example, and confirm the folder before it starts the job |
| Service role from `BEDROCK_MODEL_IMPORT_ROLE_ARN` or from your own credentials | Changed | Give `roleArn` in the request. The role needs a trust policy for `bedrock.amazonaws.com` and read access to the model files. |
| Timestamp suffix on job and model names | Not available | Ask the agent to add a date to the names, keeping each within 63 characters |
| `CreatedBy=agent` tags on the job and the model when you passed none | Changed | Pass `jobTags` and `importedModelTags`, as in the second example |
| A new random `clientRequestToken` on each create call | Changed | Pass your own `clientRequestToken` if you want a retried request to start only one job |
| Approximate name matching in `get_model_import_job` and `get_imported_model` | Changed | `ListModelImportJobs` or `ListImportedModels` with `nameContains`, then a get call with the exact name or ARN, as in the third example |
| Fixed background text about Bedrock and Custom Model Import in each response | Not available | See [Custom Model Import in the Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) |
| Six prompts that pointed at the tools | Not needed | Ask the agent for the operation directly |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.aws-bedrock-custom-model-import-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.aws-bedrock-custom-model-import-mcp-server`
3. The old package will remain on PyPI but won't receive updates
