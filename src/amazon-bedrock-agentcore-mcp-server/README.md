# AWS Labs Amazon Bedrock Agent Core MCP Server

An AWS Labs Model Context Protocol (MCP) server for Amazon Bedrock Agent Core. This MCP server allows you to build, deploy, and manage intelligent agents with advanced capabilities like memory, OAuth authentication, and gateway integrations.

### Features:

Transform and modernize your existing agent code from any framework (Strands, Langgraph, LangChain, LlamaIndex, AutoGen, CrewAI, etc.) into production-ready AgentCore agents through intelligent analysis and automated code transformation.

**🔄 Agent Code Transformation:**
* **Analyze existing agents** - Detect frameworks, patterns, and migration strategies
* **Transform to AgentCore** - Automated code conversion with best practices
* **Framework agnostic** - Works with any Python-based agent framework

**🚀 Production Deployment:**
* **One-click deployment** with OAuth authentication and memory capabilities
* **Smart invocation** with automatic fallback between authentication methods
* **Status monitoring** and runtime health checks

**🔧 Infrastructure Management:**
* **Gateway creation** for MCP-compatible integrations with AWS services
* **Credential management** with secure API key storage and runtime injection
* **Memory integration** with semantic and summary strategies

**🎯 Developer Experience:**
* **15 specialized tools** for every stage of agent development
* **Live tool inspection** with MCP Inspector integration
* **Coding assistant integration** (VS Code, Amazon Q Developer, Kiro, Cline, Cursor, Windsurf, etc.)

### Pre-Requisites:

1. [Sign-Up for an AWS account](https://aws.amazon.com/free/?trk=78b916d7-7c94-4cab-98d9-0ce5e648dd5f&sc_channel=ps&ef_id=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB:G:s&s_kwcid=AL!4422!3!432339156162!e!!g!!aws%20sign%20up!9572385111!102212379327&gad_campaignid=9572385111&gbraid=0AAAAADjHtp99c5A9DUyUaUQVhVEoi8of3&gclid=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB)
2. [Set up Amazon Bedrock Agent Core](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html) access in your AWS account
3. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
4. `uv venv python 3.10` or `3.11` has been tested to work well



### Tools:

This MCP server provides **15 comprehensive tools** organized into functional categories:

> **📋 Note:** Tool availability and features may change between versions. For the most up-to-date and complete list of available tools with their current parameters and descriptions, use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) or call the `server_info` tool directly.
>
> **🔍 Live Tool Inspection:**
> ```bash
> # For published version:
> npx @modelcontextprotocol/inspector uvx awslabs.amazon-bedrock-agentcore-mcp-server
>
> # For local development:
> npx @modelcontextprotocol/inspector uv run python -m awslabs.amazon_bedrock_agentcore_mcp_server.server
> ```
>
> ![MCP Inspector Tools Overview](images/mcp-inspector-tools-overview.png)
> *MCP Inspector showing all 15 tools with their parameters, descriptions, and real-time testing capabilities*

## 🔧 Server & Environment (2 tools)

#### server_info
  - **Comprehensive server diagnostics and architecture overview** - Shows operational status, module breakdown, tool inventory by category, recommended usage workflows, and server configuration details
  - Parameters: None
  - **What it shows:** Server version, operational status, modular architecture details (utils, runtime, gateway, identity, memory), tool categories with counts, key features, recommended usage patterns, and compatibility information
  - Example: `Get complete server overview: server_info()`

#### validate_agentcore_environment
  - Validate AgentCore development environment and check for existing agent configurations
  - Required Parameters: project_path (str)
  - Optional Parameters: check_existing_agents (bool)
  - Example: `Validate current directory: validate_agentcore_environment(project_path=".")`

## 🔍 Discovery & Analysis (4 tools)

#### what_agents_can_i_invoke
  - Find all available agents that can be invoked (local + AWS deployments)
  - Parameters: None
  - Example: `Find available agents: what_agents_can_i_invoke()`

#### project_discover
  - Consolidated project discovery for agents, configs, and resources
  - Required Parameters: action (str) - "agents", "configs", or "all"
  - Optional Parameters: search_path (str)
  - Example: `Find all agent files: project_discover(action="agents", search_path=".")`

#### discover_agentcore_examples
  - Dynamically discover working examples from amazon-bedrock-agentcore-samples repository
  - Parameters: None
  - Example: `Get latest examples: discover_agentcore_examples()`

#### analyze_agent_code
  - Analyze existing agent code and determine migration strategy
  - Required Parameters: file_path (str)
  - Optional Parameters: code_content (str)
  - Example: `Analyze my agent: analyze_agent_code(file_path="my_agent.py")`

## 🚀 Deployment & Runtime (4 tools)

#### transform_to_agentcore
  - Transform existing agent code to AgentCore format
  - Required Parameters: file_path (str)
  - Optional Parameters: output_file (str), framework (str)
  - Example: `Transform agent: transform_to_agentcore(file_path="old_agent.py", output_file="new_agent.py")`

#### deploy_agentcore_app
  - Deploy AgentCore agents with support for OAuth authentication, memory integration, and runtime configuration
  - Required Parameters: agent_file (str)
  - Optional Parameters: agent_name (str), enable_oauth (bool), region (str)
  - Example: `Deploy my agent with OAuth: deploy_agentcore_app(agent_file="my_agent.py", enable_oauth=True)`

#### invoke_agent
  - Invoke deployed AgentCore agent
  - Required Parameters: agent_name (str)
  - Optional Parameters: message (str), region (str)
  - Example: `Invoke my chatbot agent: invoke_agent(agent_name="my-chatbot", message="Hello, how can you help?")`

#### get_agent_status
  - Check agent deployment and runtime status
  - Required Parameters: agent_name (str)
  - Optional Parameters: region (str)
  - Example: `Check agent status: get_agent_status(agent_name="my-agent")`

## 🔐 Authentication & Security (2 tools)

#### get_oauth_access_token
  - Generate OAuth access tokens for AgentCore gateways using multiple methods
  - Required Parameters: method (str) - "gateway_client", "manual_curl", or "ask"
  - Optional Parameters: gateway_name (str), region (str)
  - Example: `Get OAuth token: get_oauth_access_token(method="gateway_client", gateway_name="my-gateway")`

#### manage_credentials
  - Secure API key credential provider management for runtime injection into agents
  - Required Parameters: action (str)
  - Optional Parameters: provider_name (str), api_key (str), description (str), region (str)
  - Example: `Store OpenAI key: manage_credentials(action="create", provider_name="openai-key", api_key="sk-...", description="OpenAI GPT API")`

## 🌐 Infrastructure & Resources (3 tools)

#### agent_gateway
  - Comprehensive gateway management for creating MCP-compatible gateways with AWS service integrations
  - Required Parameters: action (str)
  - Optional Parameters: gateway_name (str), target_type (str), smithy_model (str), region (str)
  - Example: `Create DynamoDB gateway: agent_gateway(action="create", gateway_name="my-gateway", target_type="smithyModel", smithy_model="dynamodb")`

#### agent_memory
  - Complete memory management system for agents with semantic and summary strategies
  - Required Parameters: action (str)
  - Optional Parameters: agent_name (str), memory_id (str), strategy_types (List[str]), region (str)
  - Example: `Create agent memory: agent_memory(action="create", agent_name="my-agent", strategy_types=["semantic", "summary"])`

#### migration_info
  - Information about migrating from the original monolithic server
  - Parameters: None
  - Example: `Get migration guide: migration_info()`


## Setup

### IAM Configuration

1. Provision a user in your AWS account IAM
2. Attach a policy that contains at a minimum the `bedrock-agentcore:*`, `bedrock:*`, `cognito-idp:*`, and `s3:*` permissions for full functionality. Alternatively create a custom policy with the specific permissions needed. Always follow the principal of least privilege when granting users permissions. See the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_service-with-iam.html) for more information on IAM permissions for Amazon Bedrock Agent Core.
3. Use `aws configure` on your environment to configure the credentials (access ID and access key)

### Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.amazon-bedrock-agentcore-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWJlZHJvY2stYWdlbnRjb3JlLW1jcC1zZXJ2ZXJAIGF0ZXN0IiwiZW52Ijp7IkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Bedrock%20Agent%20Core%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
      "mcpServers": {
            "awslabs.amazon-bedrock-agentcore-mcp-server": {
                  "command": "uvx",
                  "args": ["awslabs.amazon-bedrock-agentcore-mcp-server"],
                  "env": {
                    "FASTMCP_LOG_LEVEL": "ERROR",
                    "AWS_PROFILE": "[Your AWS Profile Name]",
                    "AWS_REGION": "[Region where you want to deploy agents]"
                  },
                  "disabled": false,
                  "autoApprove": []
                }
      }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.amazon-bedrock-agentcore-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-bedrock-agentcore-mcp-server@latest",
        "awslabs.amazon-bedrock-agentcore-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "[Your AWS Profile Name]",
        "AWS_REGION": "[Region where you want to deploy agents]"
      }
    }
  }
}
```

or docker after a successful `docker build -t awslabs/amazon-bedrock-agentcore-mcp-server.`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

```json
  {
    "mcpServers": {
      "awslabs.amazon-bedrock-agentcore-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/amazon-bedrock-agentcore-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
NOTE: Your credentials will need to be kept refreshed from your host

## Best Practices

- Follow the principle of least privilege when setting up IAM permissions
- Use separate AWS profiles for different environments (dev, test, prod)
- Monitor agent deployment status and OAuth configurations for security
- Implement proper error handling in your agent applications
- Use memory and credential providers for enhanced agent capabilities

## Security Considerations

When using this MCP server, consider:

- This MCP server needs permissions to create, deploy, and manage Amazon Bedrock Agent Core resources
- OAuth authentication provides secure access to deployed agents
- Credential providers encrypt and securely store API keys for runtime injection
- This MCP server can create, modify, and delete agent resources in your account

## Troubleshooting

- If you encounter permission errors, verify your IAM user has the correct policies attached for Bedrock Agent Core
- For deployment issues, check agent file syntax and AWS region availability
- If OAuth authentication fails, verify Cognito configuration and DNS propagation
- For memory integration issues, ensure memory resources are in ACTIVE status
- For general Amazon Bedrock Agent Core issues, consult the [Amazon Bedrock Agent Core developer guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

## Testing

### Running Tests

The project includes a comprehensive test suite to ensure reliability and compliance with MCP standards. To run the tests:

```bash
# Install development dependencies
uv sync --dev

# Run all tests
uv run pytest tests/

# Run tests with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_basic.py -v

# Run tests with coverage report
uv run pytest tests/ --cov=awslabs.amazon_bedrock_agentcore_mcp_server --cov-report=html
```

### Test Scope and Coverage

The test suite consists of **69 comprehensive tests** covering all aspects of the MCP server:

#### 🔧 **Core Functionality Tests** (`test_basic.py` - 12 tests)
- Server initialization and tool registration verification
- All **15 MCP tools** operational testing
- OAuth authentication and token management
- Code analysis and framework detection
- Project discovery and GitHub integration
- Gateway, credential, and memory operations
- Error handling for invalid parameters and missing files

#### 📦 **Package Structure Tests** (`test_init.py` - 11 tests)
- Package version and import validation
- Module structure compliance with MCP guidelines
- Constants and Pydantic models availability
- Tool registration function verification
- Cross-module dependency validation

#### 🔗 **Integration Tests** (`test_main.py` - 11 tests)
- End-to-end server lifecycle testing
- All tools callable verification with real parameters
- OAuth and deployment workflow integration
- Discovery tools and GitHub API integration
- Comprehensive error handling scenarios
- AWS credential and region validation

#### 📋 **Data Models Tests** (`test_models.py` - 13 tests)
- Pydantic model validation and serialization
- Enum validations (AgentStatus, MemoryStrategy, GatewayTargetType, CredentialProviderType)
- AgentConfig, GatewayConfig, and DeploymentResult models
- Field validation and constraint testing
- JSON serialization/deserialization

#### 🏗️ **Server Architecture Tests** (`test_server.py` - 15 tests)
- Modular architecture validation
- Tool registration across all modules (utils, runtime, gateway, identity, memory)
- Module integration and dependency testing
- Error handling and SDK availability scenarios
- MCP protocol compliance verification

#### 🛠️ **Utility Function Tests** (`test_utils.py` - 8 tests)
- Path resolution and file discovery
- Environment detection and validation
- SDK method validation and availability checking
- Directory handling and configuration management

### Test Environment Requirements

- **Python 3.10+** with `uv` package manager
- **No AWS credentials required** - tests use mocking for AWS services
- **No external dependencies** - all tests run in isolated environment
- **Fast execution** - full test suite completes in ~7 seconds

### What's Tested vs What's Not

#### ✅ **Comprehensive Coverage:**
- All **15 MCP tools** functionality and error handling
- Modular architecture and proper module separation
- MCP protocol compliance and message formatting
- Pydantic model validation and serialization
- Environment detection and configuration management
- Error scenarios and edge cases

#### ⚠️ **Integration Testing Limitations:**
- **AWS API calls are mocked** - tests don't deploy real AWS resources
- **OAuth flows are simulated** - no actual Cognito integration testing
- **GitHub API calls may fail** - network-dependent tests handle failures gracefully
- **AgentCore SDK installation** - tests handle SDK unavailability scenarios

### Continuous Integration

Tests are designed for CI/CD environments and include:
- Deterministic results with proper mocking
- Isolated test execution with no side effects
- Comprehensive error path validation
- Performance benchmarks under 10 seconds total runtime

## Development

### Local Development Setup

For local development and testing:

```bash
# Clone the repository (if working from source)
git clone https://github.com/awslabs/mcp.git
cd mcp/src/amazon-bedrock-agentcore-mcp-server

# Install dependencies
uv sync

# Run the server locally
uv run python -m awslabs.amazon_bedrock_agentcore_mcp_server.server

# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv run python -m awslabs.amazon_bedrock_agentcore_mcp_server.server
```

### Key Dependencies

The server requires these core dependencies:
- **`requests>=2.31.0`** - For GitHub API integration and HTTP requests
- **`PyYAML>=6.0`** - For configuration file parsing
- **`boto3>=1.38.18`** - For AWS service integration
- **`mcp>=1.11.0`** - Model Context Protocol framework

Optional dependencies (auto-detected):
- **`bedrock-agentcore`** - Core AgentCore SDK for deployment
- **`bedrock-agentcore-starter-toolkit`** - Simplified tools and utilities

## Version

Current MCP server version: 0.1.0
