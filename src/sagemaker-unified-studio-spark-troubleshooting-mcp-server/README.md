# SageMaker Unified Studio MCP for Spark Troubleshooting

A fully managed remote MCP server that provides specialized tools for troubleshooting Apache Spark applications on Amazon EMR, AWS Glue, and Amazon SageMaker Notebooks. This server simplifies the troubleshooting process through conversational AI capabilities, automated workload analysis, and intelligent code recommendations.

**Important Note**: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server. The Amazon SageMaker Unified Studio MCP server is in preview and is subject to change.

## Key Features & Capabilities

- **Intelligent Failure Analysis**: Automatically analyzes Spark event logs, error messages, and resource usage to pinpoint exact issues including memory problems, configuration errors, and code bugs
- **Multi-Platform Support**: Troubleshoot PySpark and Scala applications across Amazon EMR on EC2, EMR Serverless, AWS Glue, and Amazon SageMaker Notebooks
- **Automated Feature Extraction**: Connects to platform-specific spark history server (EMR, Glue, EMR-Serverless) to extract comprehensive context
- **GenAI Root Cause Analysis**: Leverages AI models and Spark knowledge base to correlate features and identify root causes of performance issues or failures
- **Code Recommendation Engine**: Provides actionable code modifications, configuration adjustments, and architectural improvements with concrete examples
- **Natural Language Interface**: Use conversational prompts to request troubleshooting analysis and code recommendations

## Architecture

The troubleshooting agent has three main components: an MCP-compatible AI Assistant in your development environment for interaction, the [MCP Proxy for AWS](https://github.com/aws/mcp-proxy-for-aws) that handles secure communication and authentication between your client and AWS services, and the Amazon SageMaker Unified Studio Remote MCP Server (preview) that provides specialized Spark troubleshooting tools for Amazon EMR, AWS Glue and Amazon SageMaker Notebooks. This diagram illustrates how you interact with the Amazon SageMaker Unified Studio Remote MCP Server through your AI Assistant.

![img](https://docs.aws.amazon.com/images/emr/latest/ReleaseGuide/images/spark-troubleshooting-agent-architecture.png)

The AI assistant orchestrates the troubleshooting process using specialized tools provided by the MCP server following these steps:

- **Feature Extraction and Context Building**: Automatically collects and analyzes telemetry data from your Spark application including Spark History Server logs, configuration settings, and error traces. Extracts key performance metrics, resource utilization patterns, and failure signatures.

- **GenAI Root Cause Analyzer and Recommendation Engine**: Leverages AI models and Spark knowledge base to correlate extracted features and identify root causes of performance issues or failures. Provides diagnostic insights and analysis of application execution problems.

- **GenAI Spark Code Recommendation**: Based on root cause analysis, analyzes existing code patterns and identifies inefficient operations that need fixes. Provides actionable recommendations including specific code modifications, configuration adjustments, and architectural improvements.

### Supported Platforms & Languages

- **Languages**: Python (PySpark) and Scala Spark applications
- **Target Platforms**:
    - Amazon EMR on EC2
    - Amazon EMR Serverless
    - AWS Glue
    - Amazon SageMaker Notebooks

### Data Source Integration

- **EMR on EC2**: Connects to [EMR Persistent UI](https://docs.aws.amazon.com/emr/latest/ManagementGuide/app-history-spark-UI.html) for cluster analysis
- **AWS Glue**: Builds context from Glue Studio's [Spark UI](https://docs.aws.amazon.com/glue/latest/dg/monitor-spark-ui-jobs.html) for job analysis
- **EMR Serverless**: Connects to EMR-Serverless [Spark History Server](https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_GetDashboardForJobRun.html) for job run analysis

## Configuration

You can configure the Apache Spark Troubleshooting Agent MCP server for use with any MCP client.

**Example Configuration for Kiro CLI:**

For code troubleshooting, you can add:
```json
{
    "mcpServers": {
    "sagemaker-unified-studio-mcp-troubleshooting": {
        "type": "stdio",
        "command": "uvx",
        "args": [
        "mcp-proxy-for-aws@latest",
        "https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-troubleshooting/mcp",
        "--service",
        "sagemaker-unified-studio-mcp",
        "--profile",
        "smus-mcp-profile",
        "--region",
        "us-east-1",
        "--read-timeout",
        "180"
        ],
        "timeout": 180000,
        "disabled": false
    }
    }
}
```

For code recommendations, you can also add:

```json
{
    "sagemaker-unified-studio-mcp-code-rec": {
    "type": "stdio",
    "command": "uvx",
    "args": [
        "mcp-proxy-for-aws@latest",
        "https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-code-recommendation/mcp",
        "--service",
        "sagemaker-unified-studio-mcp",
        "--profile",
        "smus-mcp-profile",
        "--region",
        "us-east-1",
        "--read-timeout",
        "180"
    ],
    "timeout": 180000,
    "disabled": false
    }
}
```

## Setup & Installation

### Deploy CloudFormation Stack

Choose the appropriate **Launch Stack** button for your region to deploy the required resources, See [Setup Documentation](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/spark-troubleshooting-agent-setup.html) for complete list

### Setup Local Environment and AWS CLI Profile

Copy the 1-line instruction from the CloudFormation output and execute it locally:

```bash
export SMUS_MCP_REGION=us-east-1 && export IAM_ROLE=arn:aws:iam::111122223333:role/spark-troubleshooting-role-xxxxxx
```

```bash
aws configure set profile.smus-mcp-profile.role_arn ${IAM_ROLE}
aws configure set profile.smus-mcp-profile.source_profile default
aws configure set profile.smus-mcp-profile.region ${SMUS_MCP_REGION}
```

### One-click Installation


|   IDE   |       Install Spark Troubleshooting | Install Spark Code Recommendation |
| :-----: |  :-----: | :------: |
| Kiro IDE  | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=spark-troubleshooting&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22mcp-proxy-for-aws%40latest%22%2C%20%22https%3A//sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-troubleshooting/mcp%22%2C%20%22--service%22%2C%20%22sagemaker-unified-studio-mcp%22%2C%20%22--profile%22%2C%20%22smus-mcp-profile%22%2C%20%22--region%22%2C%20%22us-east-1%22%2C%20%22--read-timeout%22%2C%20%22180%22%5D%2C%20%22timeout%22%3A%20180000%7D)  | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=spark-code-rec&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22mcp-proxy-for-aws%40latest%22%2C%20%22https%3A//sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-code-recommendation/mcp%22%2C%20%22--service%22%2C%20%22sagemaker-unified-studio-mcp%22%2C%20%22--profile%22%2C%20%22smus-mcp-profile%22%2C%20%22--region%22%2C%20%22us-east-1%22%2C%20%22--read-timeout%22%2C%20%22180%22%5D%2C%20%22timeout%22%3A%20180000%7D) |
| VS Code  |  [![Install Troubleshooting VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900)](vscode:mcp/install?%7B%22name%22%3A%22sagemaker-unified-studio-mcp-troubleshooting%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Fsagemaker-unified-studio-mcp.us-east-1.api.aws%2Fspark-troubleshooting%2Fmcp%22%2C%22--service%22%2C%22sagemaker-unified-studio-mcp%22%2C%22--profile%22%2C%22smus-mcp-profile%22%2C%22--region%22%2C%22us-east-1%22%2C%22--read-timeout%22%2C%22180%22%5D%7D) | [![Install Code Recommendation in VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900)](vscode:mcp/install?%7B%22name%22%3A%22sagemaker-unified-studio-mcp-code-rec%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Fsagemaker-unified-studio-mcp.us-east-1.api.aws%2Fspark-code-recommendation%2Fmcp%22%2C%22--service%22%2C%22sagemaker-unified-studio-mcp%22%2C%22--profile%22%2C%22smus-mcp-profile%22%2C%22--region%22%2C%22us-east-1%22%2C%22--read-timeout%22%2C%22180%22%5D%7D) |

### Configure MCP Client (Kiro CLI Example)

```bash
# Add Spark Troubleshooting MCP Server
kiro-cli-chat mcp add \
    --name "sagemaker-unified-studio-mcp-troubleshooting" \
    --command "uvx" \
    --args "[\"mcp-proxy-for-aws@latest\",\"https://sagemaker-unified-studio-mcp.${SMUS_MCP_REGION}.api.aws/spark-troubleshooting/mcp\", \"--service\", \"sagemaker-unified-studio-mcp\", \"--profile\", \"smus-mcp-profile\", \"--region\", \"${SMUS_MCP_REGION}\", \"--read-timeout\", \"180\"]" \
    --timeout 180000 \
    --scope global

# Add Spark Code Recommendation MCP Server
kiro-cli-chat mcp add \
    --name "sagemaker-unified-studio-mcp-code-rec" \
    --command "uvx" \
    --args "[\"mcp-proxy-for-aws@latest\",\"https://sagemaker-unified-studio-mcp.${SMUS_MCP_REGION}.api.aws/spark-code-recommendation/mcp\", \"--service\", \"sagemaker-unified-studio-mcp\", \"--profile\", \"smus-mcp-profile\", \"--region\", \"${SMUS_MCP_REGION}\", \"--read-timeout\", \"180\"]" \
    --timeout 180000 \
    --scope global
```

## Usage Examples

### 1. Troubleshoot Spark Job Execution Failures

**EMR on EC2 Troubleshooting:**
```
Troubleshoot my EMR-EC2 step with id s-xxxxxxxxxxxx on cluster j-xxxxxxxxxxxxx
```

**Glue Job Troubleshooting:**
```
Troubleshoot my Glue job with job run id jr_xxxxxxxxxxxxxxxxxxxxxxxxxxxx and job name test_job
```

**EMR Serverless Troubleshooting:**
```
Troubleshoot my EMR-Serverless job run with application id 00xxxxxxxx and job run id 00xxxxxxxx
```

### 2. Request Code Fix Recommendations

**EMR on EC2 Code Recommendations:**
```
Recommend code fix for my EMR-EC2 step with id s-STEP_ID on cluster j-CLUSTER_ID
```

**Glue Job Code Recommendations:**
```
Recommend code fix for my Glue job with job run id jr_JOB_RUN_ID and job name test_job
```

## Limitations & Requirements

### Supported Workload States
- **Failed Workloads Only**: Tools only support responses for failed Spark workloads

### Platform-Specific Considerations

- **EMR Persistent UI**: When analyzing Amazon EMR-EC2 workloads, the tool connects to EMR Persistent UI. See [limitations](https://docs.aws.amazon.com/emr/latest/ManagementGuide/app-history-spark-UI.html#app-history-spark-UI-limitations)
- **Glue Studio Spark UI**: Retrieves information by parsing Spark event logs from Amazon S3. Maximum allowed event log size: 512 MB (2 GB for rolling logs)
- **Code Recommendations**: Only supported for Amazon EMR-EC2 and AWS Glue workloads for PySpark applications
- **Regional Resources**: The agent is regional and uses underlying EMR resources in that region. Cross-region troubleshooting is not supported

## Troubleshooting Common Issues

### MCP Server Failed to Load
- Verify MCP configurations are properly set up
- Validate JSON syntax for missing commas, quotes, or brackets
- Verify local AWS credentials and IAM role policy configuration
- Run `/mcp` to verify server availability (Kiro CLI)

### Slow Tool Loading
- Tools may take a few seconds to load on first launch
- Try restarting the chat if tools don't appear
- Run `/tools` command to verify tool availability

### Tool Invocation Errors
- **Throttling Error**: Wait a few seconds before retrying
- **AccessDeniedException**: Check and fix permission issues
- **InvalidInputException**: Correct tool input parameters
- **ResourceNotFoundException**: Fix input parameters for resource reference
- **Internal Service Exception**: Document analysis ID and contact AWS support

## Data Usage

This server processes your Spark application logs and configuration files to provide troubleshooting recommendations. No sensitive data is stored permanently, and all processing follows AWS data protection standards.

## Security Best Practices

- **Trust Settings**: Do not enable "trust" setting by default for all tool calls
- **Version Control**: Operate on git-versioned build environments when accepting code recommendations
- **Review Process**: Review each tool execution to understand what changes are being made
- **Code Changes**: Maintain full control over all code modifications and recommendations

## FAQs

### 1. What types of Spark applications are supported?
The agent supports both PySpark and Scala Spark applications running on Amazon EMR on EC2, EMR Serverless, AWS Glue, and Amazon SageMaker Notebooks.

### 2. What happens if my Spark job is still running?
The troubleshooting tools only support analysis of failed Spark workloads.

### 3. Can I get code recommendations for successful jobs?
Code recommendations are primarily focused on fixing issues in failed workloads, but you can request code-level suggestions for optimization even without a full failure analysis.

### 4. How does the agent access my Spark logs?
The agent connects to platform-specific interfaces: EMR Persistent UI for EMR-EC2, Glue Studio Spark UI for AWS Glue, Spark History Server for EMR Serverless And S3/Cloudwatch logs to extract necessary telemetry data.

### 5. Is my data secure during the troubleshooting process?
Yes, all processing follows AWS data protection standards. The agent analyzes logs and configurations temporarily to provide recommendations without permanently storing sensitive data.

### 6. What should I do if the automated troubleshooting doesn't identify the issue?
The agent provides detailed error analysis and suggested fixes. If issues persist, you can escalate to AWS support with the analysis ID and tool responses for further assistance.

For more information, refer to the [AWS EMR Spark Troubleshooting Documentation](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/spark-troubleshoot.html).
