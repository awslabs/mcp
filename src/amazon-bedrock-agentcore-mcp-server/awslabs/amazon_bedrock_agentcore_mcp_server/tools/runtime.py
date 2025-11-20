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

"""AgentCore Runtime Tool - Manage agent runtime lifecycle and operations.

Comprehensive runtime operations including configure, launch, invoke, status, and destroy.
"""

from typing import Any, Dict


def manage_agentcore_runtime() -> Dict[str, Any]:
    """Provides comprehensive information on how to deploy and manage agents in AgentCore Runtime.

    This tool returns detailed documentation about:
    - Code requirements before deployment
    - Step-by-step CLI deployment workflow
    - Validation checklist for agent code and dependencies
    - Common issues and how to avoid them

    Use this tool to understand the complete process of deploying agents to AgentCore Runtime.
    """
    deployment_guide = """
AGENTCORE RUNTIME DEPLOYMENT GUIDE
===================================

DEPLOYMENT REQUIREMENTS:
Before deploying to AgentCore Runtime, your agent code must follow this structure:

1. Required Code Pattern:
   ```python
   from bedrock_agentcore import BedrockAgentCoreApp
   from strands import Agent  # or your framework

   app = BedrockAgentCoreApp()

   @app.entrypoint
   def invoke(payload, context):
       user_message = payload.get("prompt", "Hello!")
       # Your agent logic here
       return {"result": result}

   if __name__ == "__main__":
       app.run()
   ```

2. Required Files:
   - Agent file (e.g., agent.py) with BedrockAgentCoreApp wrapper
   - requirements.txt with all dependencies

3. Key Patterns:
   - Import BedrockAgentCoreApp from bedrock_agentcore.runtime
   - Initialize with app = BedrockAgentCoreApp()
   - Use @app.entrypoint decorator on invoke function
   - Call app.run() to let AgentCore control execution

CLI DEPLOYMENT WORKFLOW:

Step 1: Install CLI
    pip install bedrock-agentcore-starter-toolkit

Step 2: Validate Agent Code Format
    Before configuring, verify your agent code follows the required pattern:

    REQUIRED CHECKS:
    ✓ Python file imports BedrockAgentCoreApp:
      from bedrock_agentcore import BedrockAgentCoreApp

    ✓ App is initialized:
      app = BedrockAgentCoreApp()

    ✓ Entrypoint function has @app.entrypoint decorator:
      @app.entrypoint
      def invoke(payload, context):

    ✓ App runs at the end:
      if __name__ == "__main__":
          app.run()

    ✓ requirements.txt exists and includes:
      - bedrock-agentcore (REQUIRED)
      - Your agent framework (e.g., strands-agents if using strands), langgraph)
      - All other dependencies (strands-agents-tools if using strands tools)

    COMMON ISSUES:
    ✗ Missing BedrockAgentCoreApp import
    ✗ Missing @app.entrypoint decorator
    ✗ Missing app.run() call
    ✗ requirements.txt missing bedrock-agentcore
    ✗ Using strands-tools instead of strands-agents-tools
    ✗ Using strands instead of strands-agents

Step 3: Configure Agent
    agentcore configure --entrypoint agent.py --non-interactive

    Available flags:
    --entrypoint, -e TEXT          Python file of agent (required)
    --name, -n TEXT                Agent name (defaults to Python file name)
    --execution-role, -er TEXT     IAM execution role ARN
    --code-build-execution-role, -cber TEXT  CodeBuild execution role ARN
    --ecr, -ecr TEXT               ECR repository name (use "auto" for automatic creation)
    --container-runtime, -ctr TEXT Container runtime (for container deployment only)
    --deployment-type, -dt TEXT    Deployment type (direct_code_deploy or container)
    --runtime, -rt TEXT            Python runtime version (PYTHON_3_10, PYTHON_3_11, PYTHON_3_12, PYTHON_3_13)
    --requirements-file, -rf TEXT  Path to requirements file of agent
    --disable-otel, -do            Disable OpenTelemetry
    --disable-memory, -dm          Disable memory (skip memory setup entirely)
    --authorizer-config, -ac TEXT  OAuth authorizer configuration as JSON string
    --request-header-allowlist, -rha TEXT  Comma-separated list of allowed request headers
    --vpc                          Enable VPC networking mode (requires --subnets and --security-groups)
    --subnets TEXT                 Comma-separated list of subnet IDs (required with --vpc)
    --security-groups TEXT         Comma-separated list of security group IDs (required with --vpc)
    --idle-timeout, -it INTEGER    Seconds before idle session terminates (60-28800, default: 900)
    --max-lifetime, -ml INTEGER    Maximum instance lifetime in seconds (60-28800, default: 28800)
    --verbose, -v                  Enable verbose output
    --region, -r TEXT              AWS region
    --protocol, -p TEXT            Agent server protocol (HTTP or MCP or A2A)
    --non-interactive, -ni         Skip prompts; use defaults unless overridden

Step 4: Deploy to AWS
    agentcore launch

    Available flags:
    --agent, -a TEXT               Agent name
    --local, -l                    Build and run locally (requires Docker/Finch/Podman)
    --local-build, -lb             Build locally and deploy to cloud (requires Docker/Finch/Podman)
    --auto-update-on-conflict, -auc  Automatically update existing agent instead of failing
    --env, -env TEXT               Environment variables for agent (format: KEY=VALUE)

Step 5: Test Deployed Agent
    agentcore invoke '{"prompt": "Hello world!"}'

    Available flags:
    --agent, -a TEXT               Agent name
    --session-id, -s TEXT          Session ID
    --bearer-token, -bt TEXT       Bearer token for OAuth authentication
    --local, -l                    Send request to a running local agent
    --user-id, -u TEXT             User ID for authorization flows
    --headers TEXT                 Custom headers (format: 'Header1:value,Header2:value2')

Step 6: Check Status
    agentcore status

    Available flags:
    --agent, -a TEXT               Agent name
    --verbose, -v                  Verbose JSON output of config, agent, and endpoint status

Step 7: Manage Sessions
    agentcore stop-session

    Available flags:
    --session-id, -s TEXT          Specific session ID to stop (optional)
    --agent, -a TEXT               Agent name

Step 8: Clean Up
    agentcore destroy

    Available flags:
    --agent, -a TEXT               Agent name
    --dry-run                      Show what would be destroyed without actually destroying
    --force                        Skip confirmation prompts
    --delete-ecr-repo              Also delete the ECR repository after removing images

ADDITIONAL COMMANDS:
    agentcore configure list
    agentcore configure set-default my_agent

KEY POINTS:
- Default deployment uses 'direct_code_deploy' (no Docker required)
- CodeBuild handles container builds automatically in the cloud
- Memory is opt-in; configure during setup or use --disable-memory
- Region defaults to us-west-2; specify with --region flag
- ARM64 architecture required (handled automatically by CodeBuild)
- Configuration stored in .bedrock_agentcore.yaml
"""

    return {'deployment_guide': deployment_guide}
