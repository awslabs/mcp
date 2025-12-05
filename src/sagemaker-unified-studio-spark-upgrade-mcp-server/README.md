# SageMaker Unified Studio MCP for Spark Upgrade

A fully managed remote MCP server that provides specialized tools and guidance for upgrading Apache Spark applications on Amazon EMR. This server accelerates Spark version upgrades through automated analysis, code transformation, and validation capabilities.

**Important Note**: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

## Key Features

- **Automated Upgrade Planning**: Analyze project structure and generate comprehensive upgrade plans
- **Code Transformation**: Automated PySpark and Scala code updates for version compatibility
- **Build Configuration**: Update and manage project dependencies and build environments
- **Validation & Testing**: Run unit tests, integration tests, and EMR validation jobs
- **Data Quality Validation**: Ensure data integrity throughout the upgrade process
- **Cross-Platform Support**: Works with Amazon EMR on EC2 and Amazon EMR Serverless

## Apache Spark Upgrade Agent Capabilities

- **Project Analysis**: Deep analysis of Spark application structure, dependencies, and API usage
- **Upgrade Planning**: Generate step-by-step upgrade plans with risk assessment
- **Code Migration**: Automated code transformations for API changes and deprecations
- **Dependency Management**: Update Maven/SBT/pip dependencies for target Spark versions
- **Build Validation**: Compile and build projects with iterative error resolution
- **Testing Integration**: Execute comprehensive test suites and validation workflows
- **EMR Integration**: Submit and monitor EMR jobs for upgrade validation
- **Observability**: Track upgrade progress and analyze results


## Architecture
The upgrade agent has three main components: any MCP-compatible AI Assistant in your development environment for interaction, the [MCP Proxy for AWS](https://github.com/aws/mcp-proxy-for-aws) that handles secure communication between your client and the MCP server, and the Amazon SageMaker Unified Studio Managed MCP Server (in preview) that provides specialized Spark upgrade tools for Amazon EMR. This diagram illustrates how you interact with the Amazon SageMaker Unified Studio Managed MCP Server through your AI Assistant.


The AI assistant will orchestrate the upgrade using specialized tools provided by the MCP server following these steps:

- **Planner**: The agent will analyze your project structure and generate an upgrade plan. You may generate a new plan or leverage an existing plan and you may also review the plan and revise it.

- **Compile and build**: The agent will review and update build environment and upgrade the project build configuration, it will build the project and make iterative changes to fix build errors until the application compiles and builds successfully.

- **Spark code edit**: The agent can update the project build configuration, compile and build the project in build Step, or fix Spark upgrade errors detected at runtime.

- **Build & test**: The agent can run unit test and integration test locally, and also submit EMR validation job run, the agent can monitor the job status and verify the upgrade job execution status and data quality validation status.

- **Observability**: The upgrade process can be tracked by the agent using observability tools built for EMR platform. Users are also able to list their upgrade analysis and review their status by respective tools.

Please refer to [Using Spark Upgrade Tools](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-upgrade-agent-tools.html) for a list of major tools for each steps.

### Supported Upgrade Paths
- **Spark 2.x to 3.x**: Major version upgrades with breaking changes
- **Spark 3.x to 3.y**: Minor version upgrades with compatibility updates
- **EMR Release Upgrades**:
    - For EMR-EC2
        - Source Version: EMR 5.20.0 and later
        - Target Version: Any version above EMR 5.20.0 and below EMR 7.12.0

    - For EMR-Serverless
        - Source Version: EMR Serverless 6.6.0 and later
        - Target Version: Any version above EMR Serverless 6.6.0 and below EMR Serverless 7.12.0



## Configuration

You can configure the Apache Spark Upgrade Agent MCP server for use with any MCP client using the following URL:

```url
https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-upgrade/mcp
```

**Note:** The specific configuration format varies by MCP client. Below is an example for [Kiro CLI](https://kiro.dev/).

**Kiro CLI**

```json
{
  "mcpServers": {
    "spark-upgrade": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws@latest",
        "https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-upgrade/mcp",
        "--service",
        "sagemaker-unified-studio-mcp",
        "--profile",
        "spark-upgrade-profile",
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

See [Using the Upgrade Agent](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-upgrade-agent-using.html) for the configuration guidance for different MCP clients like Kiro, Cline and GitHub CoPilot.

## Usage Examples

1. **Run the spark upgrade analysis**:
   ```
   Help me upgrade my spark application in <project-path> from 2.4 to Spark 3.5. you can use EMR-S Application is xxg017hmd2agxxxx to run the validation and s3 paths s3://<s3-staging-path> to store updated application artifacts.
   ```

2. **List the analyses**:
   ```
   Provide me a list of analyses performed by the spark agent
   ```

3. **Describe Analysis**:
   ```
   can you explain the analysis 439715b3-xxxx-42a6-xxxx-3bf7f1fxxxx
   ```
4. **Reuse Plan for other analysis**:
    ```
    Use my upgrade_plan spark_upgrade_plan_xxx.json to upgrade my project in <project-path>
    ```

## AWS Authentication

### Step 1: Configure AWS CLI Profile
```
aws configure set profile.spark-upgrade-profile.role_arn ${IAM_ROLE}
aws configure set profile.spark-upgrade-profile.source_profile <AWS CLI Profile to assume the IAM role - ex: default>
aws configure set profile.spark-upgrade-profile.region ${SMUS_MCP_REGION}
```
### Step 2: if you are using Kiro CLI, use the following command to add the MCP configuration
```
kiro-cli-chat mcp add \
    --name "spark-upgrade" \
    --command "uvx" \
    --args "[\"mcp-proxy-for-aws@latest\",\"https://sagemaker-unified-studio-mcp.${SMUS_MCP_REGION}.api.aws/spark-upgrade/mcp\", \"--service\", \"sagemaker-unified-studio-mcp\", \"--profile\", \"spark-upgrade-profile\", \"--region\", \"${SMUS_MCP_REGION}\", \"--read-timeout\", \"180\"]" \
    --timeout 180000\
    --scope global
```
For more infomation, refer to [AWS docs](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-upgrade-agent-setup.html)
## Data Usage

This server processes your code and configuration files to provide upgrade recommendations. No sensitive data is stored permanently, and all processing follows AWS data protection standards.

## FAQs

### 1. Which Spark versions are supported?
For EMR-EC2

    Source Version: EMR 5.20.0 and later

    Target Version: Any version above EMR 5.20.0 and below EMR 7.12.0

For EMR-Serverless

    Source Version: EMR Serverless 6.6.0 and later

    Target Version: Any version above EMR Serverless 6.6.0 and below EMR Serverless 7.12.0



### 2. Can I use this for Scala applications?

Yes, the agent supports both PySpark and Scala Spark applications, including Maven and SBT build system

### 3. What about custom libraries and UDFs?

The agent analyzes custom dependencies and provides guidance for updating user-defined functions and third-party libraries.

### 4. How does data quality validation work?

The agent compares output data between old and new Spark versions using configurable validation rules and statistical analysis.

### 5. Can I customize the upgrade process?

Yes, you can modify upgrade plans, exclude specific transformations, and customize validation criteria based on your requirements.

### 6. What if the automated upgrade fails?

The agent provides detailed error analysis, suggested fixes, and fallback strategies. You maintain full control over all changes.
