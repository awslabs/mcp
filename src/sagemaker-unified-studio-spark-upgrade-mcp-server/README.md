# SageMaker Unified Studio MCP for Spark Upgrade

A fully managed remote MCP server that provides specialized tools and guidance for upgrading Apache Spark applications on Amazon EMR. This server accelerates Spark version upgrades through automated analysis, code transformation, and validation capabilities.

**Important Note**: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

## Key Features & Capabilities

- **Project Analysis & Planning**: Deep analysis of Spark application structure, dependencies, and API usage to generate comprehensive step-by-step upgrade plans with risk assessment
- **Automated Code Transformation**: Automated PySpark and Scala code updates for version compatibility, handling API changes and deprecations
- **Dependency & Build Management**: Update and manage Maven/SBT/pip dependencies and build environments for target Spark versions with iterative error resolution
- **Comprehensive Testing & Validation**: Execute unit tests, integration tests and EMR validation jobs and validates the upgraded application against target spark version
- **Data Quality Validation**: Ensure data integrity throughout the upgrade process with validation rules
- **EMR Integration & Monitoring**: Submit and monitor EMR jobs for upgrade validation across Amazon EMR on EC2 and Amazon EMR Serverless
- **Observability & Progress Tracking**: Track upgrade progress, analyze results, and provide detailed insights throughout the upgrade process


## Architecture
The upgrade agent has three main components: any MCP-compatible AI Assistant in your development environment for interaction, the [MCP Proxy for AWS](https://github.com/aws/mcp-proxy-for-aws) that handles secure communication between your client and the MCP server, and the Amazon SageMaker Unified Studio Managed MCP Server (in preview) that provides specialized Spark upgrade tools for Amazon EMR. This diagram illustrates how you interact with the Amazon SageMaker Unified Studio Managed MCP Server through your AI Assistant.

![img](https://docs.aws.amazon.com/images/emr/latest/ReleaseGuide/images/SparkUpgradeIntroduction.png)


The AI assistant will orchestrate the upgrade using specialized tools provided by the MCP server following these steps:

- **Planning**: The agent analyzes your project structure and generates or revises an upgrade plan that guides the end-to-end Spark upgrade process.

- **Compile & Build**: Agent updates the build environment and dependencies, compiles the project, and iteratively fixes build and test failures.

- **Spark code edit tool**: Applies targeted code updates to resolve Spark version incompatibilities, fixing both build-time and runtime errors.

- **Execution & Validation**: Submits remote validation jobs to EMR, monitors execution and logs, and iteratively fixes runtime and data-quality issues.

- **Observability**: Tracks upgrade progress using EMR observability tools and allows users to view upgrade analyses and status at any time.

Please refer to [Using Spark Upgrade Tools](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-upgrade-agent-tools.html) for a list of major tools for each steps.

### Supported Upgrade Paths
- We support Apache Spark upgrades from version 2.4 to 3.5. The corresponding deployment mode mappings are as follows
- **EMR Release Upgrades**:
    - For EMR-EC2
        - Source Version: EMR 5.20.0 and later
        - Target Version: EMR 7.12.0 and earlier, should be newer than EMR 5.20.0

    - For EMR-Serverless
        - Source Version: EMR Serverless 6.6.0 and later
        - Target Version: EMR Serverless 7.12.0 and earlier




## Configuration
**Note:** The specific configuration format varies by MCP client.

### One-click Installation


|   IDE   |       Install Spark Upgrade |
| :-----: |   :------: |
| Kiro IDE  | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=spark-upgrade&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22mcp-proxy-for-aws%40latest%22%2C%20%22https%3A//sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-upgrade/mcp%22%2C%20%22--service%22%2C%20%22sagemaker-unified-studio-mcp%22%2C%20%22--profile%22%2C%20%22spark-upgrade-profile%22%2C%20%22--region%22%2C%20%22us-east-1%22%2C%20%22--read-timeout%22%2C%20%22180%22%5D%2C%20%22timeout%22%3A%20180000%7D) |
| VS Code  |  [![Install in VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900)](vscode:mcp/install?%7B%22name%22%3A%22spark-upgrade%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Fsagemaker-unified-studio-mcp.us-east-1.api.aws%2Fspark-upgrade%2Fmcp%22%2C%22--service%22%2C%22sagemaker-unified-studio-mcp%22%2C%22--profile%22%2C%22spark-upgrade-profile%22%2C%22--region%22%2C%22us-east-1%22%2C%22--read-timeout%22%2C%22180%22%5D%7D)|

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
  - EMR-S
    ```
    Help me upgrade my spark application in <project-path> from EMR-EC2 version 6.0.0 to 7.12.0. you can use EMR-S Application id xxg017hmd2agxxxx and execution role <role name> to run the validation and s3 paths s3://s3-staging-path to store updated application artifacts.
    ```
  - EMR-EC2
    ```
    Upgrade my Spark application <local-project-path> from EMR-S version 6.6.0 to 7.12.0. Use EMR-EC2 Cluster j-PPXXXXTG09XX to run the validation and s3 paths s3://s3-staging-path to store updated application artifacts.
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
- For EMR-EC2
    - Source Version: EMR 5.20.0 and later
    - Target Version: EMR 7.12.0 and earlier, should be newer than EMR 5.20.0

- For EMR-Serverless
    - Source Version: EMR Serverless 6.6.0 and later
    - Target Version: EMR Serverless 7.12.0 and earlier



### 2. Can I use this for Scala applications?

Yes, the agent supports both PySpark and Scala Spark applications, including Maven and SBT build system

### 3. What about custom libraries and UDFs?

The agent analyzes custom dependencies and provides guidance for updating user-defined functions and third-party libraries.

### 4. How does data quality validation work?

The agent compares output data between old and new Spark versions using validation rules and statistical analysis.

### 5. Can I customize the upgrade process?

Yes, you can modify upgrade plans, exclude specific transformations, and customize validation criteria based on your requirements.

### 6. What if the automated upgrade fails?

The agent provides detailed error analysis, suggested fixes, and fallback strategies. You maintain full control over all changes.
