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

"""AgentCore MCP Server - Runtime Management Module utility functions.

Covering the following functionalities:
- OAuth configuration validation
- OAuth token generation
- Migration strategy generation
- Tutorial-based guidance generation
- Deployment execution via CLI or SDK.
"""

# ============================================================================
# OAUTH UTILITIES (SHARED)
# ============================================================================
import boto3
import json
import os
import subprocess
import time
import uuid
from .utils import (
    RUNTIME_AVAILABLE,
    SDK_AVAILABLE,
    SDK_IMPORT_ERROR,
    MCPtoolError,
    get_runtime_for_agent,
    get_user_working_directory,
)
from pathlib import Path
from typing import Any, Dict


def check_agent_oauth_status(  # pragma: no cover
    agent_name: str, region: str = 'us-east-1'
):  # pragma: allowlist secret
    """Check if agent is actually deployed with OAuth using AWS API (get_agent_runtime).

    This is the authoritative source - much better than parsing YAML files.

    Returns:
        tuple: (oauth_deployed: bool, oauth_available: bool, message: str)
    """
    from pathlib import Path

    try:
        # Get the actual deployed agent configuration from AWS
        agentcore_client = boto3.client('bedrock-agentcore-control', region_name=region)

        # First, we need to find the agent runtime ARN
        # Try to get it from local YAML if available, otherwise search
        agent_runtime_arn = None

        # Method 1: Try to get ARN from local YAML config
        try:
            config_dirs_to_check = [
                Path.cwd(),
                get_user_working_directory(),
                Path.cwd() / 'examples',
                Path.home() / 'agentcore_projects' / agent_name,
            ]

            for config_dir in config_dirs_to_check:
                yaml_file = config_dir / '.bedrock_agentcore.yaml'
                if yaml_file.exists():
                    try:  # pragma: no cover
                        import yaml

                        with open(yaml_file, 'r') as f:
                            yaml_config = yaml.safe_load(f)

                        agents = yaml_config.get('agents', {})
                        agent_config = agents.get(agent_name, {})
                        bedrock_config = agent_config.get('bedrock_agentcore', {})
                        agent_runtime_arn = bedrock_config.get('agent_arn')

                        if agent_runtime_arn:
                            break
                    except ImportError:  # pragma: no cover
                        # No PyYAML, try simple parsing  # pragma: no cover
                        with open(yaml_file, 'r') as f:  # pragma: no cover
                            yaml_content = f.read()

                        if (
                            f'{agent_name}:' in yaml_content and 'agent_arn:' in yaml_content
                        ):  # pragma: no cover
                            lines = yaml_content.split('\n')
                            in_agent_section = False
                            for line in lines:
                                if f'{agent_name}:' in line:
                                    in_agent_section = True
                                elif in_agent_section and line.strip().startswith('agent_arn:'):
                                    agent_runtime_arn = line.split('agent_arn:')[1].strip()
                                    break
                                elif (
                                    in_agent_section and not line.startswith(' ') and line.strip()
                                ):
                                    # Left the agent section
                                    break

                            if agent_runtime_arn:  # pragma: no cover
                                break
                    except Exception as e:  # pragma: no cover
                        raise MCPtoolError(f'YAML Parsing Error: {str(e)}')
        except Exception as e:  # pragma: no cover
            raise MCPtoolError(f'YAML Config Check Error: {str(e)}')

        # Method 2: If no ARN found locally, search for it via API
        if not agent_runtime_arn:
            try:
                list_response = agentcore_client.list_agent_runtimes()
                for runtime in list_response.get('items', []):
                    if runtime.get('name') == agent_name:
                        agent_runtime_arn = runtime.get('agentRuntimeArn')
                        break
            except Exception as e:
                raise MCPtoolError(f'API List Error: {str(e)}')

        if not agent_runtime_arn:
            return False, False, f'Agent runtime ARN not found for {agent_name}'

        # Get the actual runtime configuration from AWS
        auth_file_exits = False
        try:
            runtime_response = agentcore_client.get_agent_runtime(
                agentRuntimeArn=agent_runtime_arn
            )

            # Check for inbound configuration (OAuth/auth settings)
            inbound_config = runtime_response.get('inboundConfig', {})

            # Check if OAuth config exists in our separate storage
            oauth_file = (  # pragma: allowlist secret
                Path.home() / '.agentcore_gateways' / f'{agent_name}_runtime.json'
            )  # pragma: allowlist secret

            try:
                # Validate the file path is within expected directory
                oauth_file = oauth_file.resolve()
                if not str(oauth_file).startswith(str(Path.home() / '.agentcore_gateways')):
                    auth_file_exits = False  # noqa: S105
                else:
                    auth_file_exits = oauth_file.exists()  # noqa: S105  # pragma: no cover
            except (OSError, ValueError):  # pragma: no cover
                auth_file_exits = False  # noqa: S105  # pragma: no cover

            # Determine OAuth status from AWS API response
            oauth_deployed = bool(
                inbound_config
            )  # Any inbound config indicates auth requirements # pragma: allowlist secret

            if oauth_deployed:  # pragma: no cover
                auth_details = []  # pragma: no cover
                if 'customJWTAuthorizer' in inbound_config:  # pragma: no cover
                    jwt_auth = inbound_config['customJWTAuthorizer']
                    auth_details.append(
                        f'JWT Auth (Client: {jwt_auth.get("clientId", "Unknown")})'
                    )
                if 'cognitoAuthorizer' in inbound_config:  # pragma: allowlist secret
                    # cognito_auth = inbound_config['cognitoAuthorizer']  # pragma: allowlist secret

                    cognito_auth = inbound_config.get('cognitoAuthorizer')  # noqa: S105
                    if cognito_auth and isinstance(cognito_auth, dict):
                        # Validate required fields exist and are strings
                        user_pool_id = cognito_auth.get('userPoolId', 'Unknown')
                        if isinstance(user_pool_id, str) and user_pool_id:
                            cognito_auth = {'userPoolId': user_pool_id}
                        else:
                            cognito_auth = {'userPoolId': 'Unknown'}
                    else:
                        cognito_auth = {'userPoolId': 'Unknown'}

                    auth_details.append(
                        f'Cognito Auth (Pool: {cognito_auth.get("userPoolId", "Unknown")})'
                    )

                auth_summary = (
                    ', '.join(auth_details) if auth_details else 'Custom auth configured'
                )
                return (
                    True,
                    auth_file_exits,
                    f'Agent deployed with OAuth: {auth_summary}',
                )  # pragma: no cover

            elif auth_file_exits:  # pragma: allowlist secret  # pragma: no cover
                return (  # pragma: no cover
                    False,  # pragma: no cover
                    True,  # pragma: no cover
                    'Agent deployed without OAuth, but OAuth config available for redeployment',  # pragma: no cover
                )  # pragma: no cover

            else:  # pragma: no cover
                return (
                    False,
                    False,
                    'Agent deployed without OAuth, no OAuth config available',
                )  # pragma: no cover

        except Exception as api_error:  # pragma: no cover
            # Fallback to local config analysis if API fails  # pragma: no cover
            if auth_file_exits:  # pragma: allowlist secret  # pragma: no cover
                return (  # pragma: no cover
                    False,  # pragma: no cover
                    True,  # pragma: no cover
                    f'Cannot verify deployment OAuth status (API error: {str(api_error)}), but OAuth config exists locally',  # pragma: no cover
                )  # pragma: no cover
            else:  # pragma: no cover
                return (
                    False,
                    False,
                    f'Cannot verify OAuth status: {str(api_error)}',
                )  # pragma: no cover

    except ImportError:  # pragma: no cover
        return (
            False,
            False,
            'boto3 not available - cannot check OAuth deployment status',
        )  # pragma: no cover
    except Exception as e:
        # Check if OAuth config exists in our separate storage as fallback
        oauth_file = Path.home() / '.agentcore_gateways' / f'{agent_name}_runtime.json'
        auth_file_exits = oauth_file.exists()

        if auth_file_exits:  # pragma: allowlist secret
            return (
                False,
                True,
                f'Cannot verify deployment OAuth status ({str(e)}), but OAuth config exists locally',
            )
        else:
            return False, False, f'Error checking OAuth status: {str(e)}'


def validate_oauth_config(agent_name: str, region: str = 'us-east-1'):  # pragma: no cover
    """Unified OAuth configuration validation for runtime agents.

    Returns:
        tuple: (success: bool, result: dict or str)
        - If success=True: result contains validated config dict
        - If success=False: result contains error message string
    """
    try:
        # First check if the agent is actually deployed with OAuth
        # Validate inputs before calling function
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError('Invalid agent_name: must be non-empty string')
        if not isinstance(region, str) or not region.strip():
            raise ValueError('Invalid region: must be non-empty string')
        # Sanitize agent_name to prevent path traversal
        safe_agent_name = ''.join(c for c in agent_name if c.isalnum() or c in '-_')
        if not safe_agent_name:
            raise ValueError('Invalid agent_name: contains no valid characters')

        oauth_deployed, oauth_available, oauth_status = check_agent_oauth_status(  # noqa: S105
            safe_agent_name, region
        )

        # Log OAuth status without sensitive information
        print(
            f'OAuth status - Available: {bool(oauth_available)}, Deployed: {bool(oauth_deployed)}'
        )
        agent_name = safe_agent_name  # Use sanitized name going forward

        # Load OAuth configuration (same format as gateways)
        config_dir = Path.home() / '.agentcore_gateways'
        config_file = config_dir / f'{agent_name}_runtime.json'

        if not config_file.exists():
            return (
                False,
                f"""X OAuth Agent Configuration Not Found

Agent: {agent_name}
Expected Config: {config_file}
Agent OAuth Status: {oauth_status}

Troubleshooting:
1. Deploy with OAuth: Use `deploy_agentcore_app` with `enable_oauth: True`
2. Check agent name: Ensure agent was deployed with OAuth enabled

Available OAuth configs:
{list(config_dir.glob('*_runtime.json')) if config_dir.exists() else 'None found'}

Note: Check `.bedrock_agentcore.yaml` - if `oauth_configuration: null`, agent wasn't deployed with OAuth
""",
            )

        # Read and validate OAuth configuration
        try:
            with open(config_file, 'r') as f:  # pragma: allowlist secret
                try:
                    # Limit file size to prevent DoS
                    _ = f.seek(0, 2)  # Seek to end
                    file_size = f.tell()
                    f.seek(0)  # Reset to beginning

                    if file_size > 1024 * 1024:  # 1MB limit
                        raise ValueError('OAuth configuration file too large')

                    content = f.read()
                    oauth_config = json.loads(content)

                    # Validate it's a dict and has expected structure
                    if not isinstance(oauth_config, dict):
                        raise ValueError('Invalid OAuth configuration format')

                except (json.JSONDecodeError, ValueError, OSError) as e:
                    raise ValueError(
                        f'Failed to load OAuth configuration: {e}'
                    )  # pragma: allowlist secret

            client_info = oauth_config.get('cognito_client_info', {})  # pragma: allowlist secret
            if not client_info:
                return (
                    False,
                    f"""X Invalid OAuth Configuration

Config File: {config_file}
Issue: Missing 'cognito_client_info' section

Fix: Redeploy agent with `enable_oauth: True`
""",
                )

            # Validate required Cognito fields
            required_fields = ['user_pool_id', 'client_id']
            missing_fields = [field for field in required_fields if not client_info.get(field)]
            if missing_fields:
                return (
                    False,
                    f"""X Incomplete Cognito Configuration

Missing Fields: {missing_fields}
Config File: {config_file}

Fix: Redeploy agent with `enable_oauth: True`
""",
                )

            # Return validated configuration
            return True, {
                'oauth_config': oauth_config,
                'client_info': client_info,
                'config_file': config_file,
            }

        except json.JSONDecodeError as e:
            return (
                False,
                f"""X Invalid JSON Configuration

Config File: {config_file}
JSON Error: {str(e)}

Fix: Delete config file and redeploy with `enable_oauth: True`
""",
            )

    except Exception as e:
        return (
            False,
            f"""X OAuth Config Validation Error: {str(e)}

Agent: {agent_name}
Troubleshooting:
1. Check agent deployment: Use `get_agent_status`
2. Verify OAuth config: ~/.agentcore_gateways/{agent_name}_runtime.json
3. Redeploy with OAuth: Use `deploy_agentcore_app` with `enable_oauth: True`
""",
        )


def generate_oauth_token(client_info: dict, region: str = 'us-east-1'):  # pragma: no cover
    """Generate OAuth access token using existing gateway infrastructure.

    Args:
        client_info: Cognito client info from validated config
        region: AWS region

    Returns:
        tuple: (success: bool, result: str)
        - If success=True: result contains access token
        - If success=False: result contains error message
    """
    try:
        # Import here to avoid startup issues
        from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

        # Get access token using GatewayClient (same logic as gateway tools)
        gateway_client = GatewayClient(region_name=region)
        access_token = gateway_client.get_access_token_for_cognito(client_info)

        return True, access_token

    except ImportError as import_error:
        return (
            False,
            f"""X Missing Dependencies: {str(import_error)}

Required for OAuth token generation:
1. bedrock-agentcore-starter-toolkit
2. boto3 for AWS API access

Install: `uv add bedrock-agentcore-starter-toolkit`
""",
        )
    except Exception as token_error:
        return (
            False,
            f"""X Token Generation Failed: {str(token_error)}

Troubleshooting:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify Cognito setup: Check AWS Console
3. Check permissions: Cognito access required
""",
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def generate_migration_strategy(analysis: Dict[str, Any]) -> Dict[str, str]:
    """Generate migration strategy based on analysis."""
    framework = analysis['framework']

    bedrock_agencore_wrapper = """- Wrap existing Agent handler with agentcore decorator. i.e.
                                        a. Add `from bedrock_agentcore.runtime import BedrockAgentCoreApp` to imports
                                        b. Initialize app with `app = BedrockAgentCoreApp()`
                                        c. Change entrypoint to `@app.entrypoint` decorator
                                        d. Change direct calls to `agent("prompt")` to payload handling with `payload.get("prompt")`
                                        e. Add `if __name__ == "__main__": app.run()` at the end
                                        """

    strategies = {
        'strands': {
            'complexity': 'Simple',
            'time_estimate': '5-10 minutes',
            'description': f"""Simple Strands Migration:
{bedrock_agencore_wrapper}
- Preserve all Strands functionality, for example, calling the agent with `agent(prompt)`
- Add AgentCore deployment features
- No breaking changes to your logic""",
        },
        'langgraph': {
            'complexity': 'Moderate',
            'time_estimate': '15-30 minutes',
            'description': """LangGraph Integration:
{bedrock_agencore_wrapper}
- Maintain graph structure and other logic, for example, calling the graph with `graph.run(inputs)` or `.invoke()` or `.ainvoke()`
- Add state persistence with memory
- Integrate with AgentCore tools""",
        },
        'crewai': {
            'complexity': 'Moderate',
            'time_estimate': '15-30 minutes',
            'description': """CrewAI Migration:
{bedrock_agencore_wrapper}
- Preserve agent collaboration and coordination, for example, calling the crew with `crew.kickoff()`
- Add memory for agent coordination
- Integrate with AgentCore identity""",
        },
        'agentcore': {
            'complexity': 'None',
            'time_estimate': '2-5 minutes',
            'description': """Already AgentCore:
- Code is already compatible
- Check for syntax errors
- Ready for deployment
- May add advanced features""",
        },
        'custom': {
            'complexity': 'Variable',
            'time_estimate': '10-30 minutes',
            'description': """Custom Agent Migration:
- Analyze existing patterns
- Check for examples in tutorials form github.com/awslabs/amazon_bedrock_agentcore_agent_examples with the appropriate tool
- Create AgentCore wrapper
- Preserve core logic
- Add deployment capabilities""",
        },
    }

    return strategies.get(framework, strategies['custom'])


def generate_tutorial_based_guidance(framework: str) -> str:
    """Generate step-by-step guidance based on AgentCore tutorials."""
    guidance = {
        'strands': """
Following Strands → AgentCore Tutorial Pattern:
Full strands tutorial link - https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/01-AgentCore-runtime/01-hosting-agent/01-strands-with-bedrock-model/runtime_with_strands_and_bedrock_models.ipynb
Step 1: Transform local prototype to production agent
```python
# Your current: agent("hello!")
# AgentCore: @app.entrypoint + payload handling
```

Step 2: Minimal code changes for production deployment
- Wrap in `BedrockAgentCoreApp()`
- Add `@app.entrypoint` decorator
- Handle `payload.get("prompt")` instead of direct calls

Step 3: Framework-agnostic deployment
- Agent code contains `app.run()` for HTTP server
- Use `Runtime()` class from starter toolkit for deployment
- Zero infrastructure management required

Tutorial Reference: Runtime Tutorial - Basic Agent Setup
""",
        'langgraph': """
Following LangGraph → AgentCore Tutorial Pattern:
Full LangGraph tutorial link - https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/01-AgentCore-runtime/01-hosting-agent/02-langgraph-with-bedrock-model/runtime_with_langgraph_and_bedrock_models.ipynb
Step 1: Preserve your graph workflow
- Keep existing nodes and edges
- Wrap entire workflow in AgentCore handler

Step 2: Add production capabilities
- Serverless HTTP services with auto-scaling
- Multi-modal processing support
- Memory for state persistence

Step 3: Gateway integration (optional)
- Transform nodes into MCP tools via Gateway
- Unified MCP protocol for all graph operations

Tutorial Reference: Gateway Tutorial - API Transformation
""",
        'crewai': """
Following CrewAI → AgentCore Tutorial Pattern:
Full Tutorial link - https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/01-AgentCore-runtime/01-hosting-agent/04-crewai-with-bedrock-model/runtime-with-crewai-and-bedrock-models.ipynb
Step 1: Transform crew coordination
- Preserve agent collaboration patterns
- Wrap crew.kickoff() in AgentCore handler

Step 2: Add enterprise features
- Identity management for multi-agent security
- Memory for crew coordination state
- Gateway for external tool integrations

Tutorial Reference: Identity Tutorial - Multi-Agent Auth
""",
        'agentcore': """
Already AgentCore Compatible:
Multiple tutorials available at - https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/01-AgentCore-runtime/01-hosting-agent
Your code follows AgentCore patterns. Next steps:
- Validate: Use `inspect_agentcore_sdk` to check methods
- Deploy: Use `deploy_agentcore_app` with CLI or SDK
- Enhance: Add memory/identity/gateway as needed

Tutorial Reference: All tutorials for enhancement options
""",
        'custom': """
Following Custom Agent → AgentCore Tutorial Pattern:

Step 1: Minimal transformation approach
- Focus on agent logic preservation
- Add AgentCore wrapper around existing code

Step 2: Progressive enhancement
- Start with basic deployment
- Add capabilities incrementally (memory, auth, tools)

Step 3: Production readiness
- Use enterprise-grade scaling and security
- Leverage AgentCore's infrastructure management

Tutorial Reference: Runtime Tutorial - Framework Integration
""",
    }

    return guidance.get(framework, guidance['custom'])


async def execute_agentcore_deployment_cli(  # pragma: no cover
    app_file: str,  # pragma: no cover
    agent_name: str,  # pragma: no cover
    region: str,  # pragma: no cover
    memory_enabled: bool,  # pragma: no cover
    execution_role: str,  # pragma: no cover
    environment: str,  # pragma: no cover
    enable_oauth: bool = False,  # pragma: allowlist secret  # pragma: no cover
    cognito_user_pool: str = '',  # pragma: no cover
) -> str:  # pragma: no cover
    """Execute AgentCore deployment using CLI commands."""  # pragma: no cover
    steps = []  # pragma: no cover

    try:  # pragma: no cover
        # Check for virtual environment and use appropriate command  # pragma: no cover
        venv_python = None  # pragma: no cover
        if Path('.venv/bin/python').exists():  # pragma: no cover
            venv_python = '.venv/bin/python'  # pragma: no cover
            steps.append('OK Found local .venv - using virtual environment')  # pragma: no cover
        elif Path('venv/bin/python').exists():  # pragma: no cover
            venv_python = 'venv/bin/python'  # pragma: no cover
            steps.append('OK Found local venv - using virtual environment')  # pragma: no cover

        # Check if uv is available for package management
        uv_available = False
        try:
            result = subprocess.run(['which', 'uv'], capture_output=True, text=True)
            if result.returncode == 0:
                uv_available = True
                steps.append('OK UV package manager detected')
        except Exception as e:
            print(f'UV check error: {str(e)}')
            pass

        # Check if agentcore CLI is available
        agentcore_cmd = 'agentcore'  # Correct CLI name
        if uv_available:
            agentcore_cmd = ['uv', 'run', 'agentcore']
        elif venv_python:
            agentcore_cmd = [venv_python, '-m', 'agentcore']
        else:
            agentcore_cmd = ['agentcore']

        # Use absolute path (should already be resolved by calling function)
        if not Path(app_file).is_absolute():
            app_file = str(Path(app_file).resolve())

        if not Path(app_file).exists():
            user_dir = get_user_working_directory()
            return f"""X File Not Found

App file: {app_file}
User working directory: {user_dir}

Available Python files:
{list(user_dir.glob('*.py'))[:5]}
"""

        # Step 1: Configure
        if isinstance(agentcore_cmd, list):
            configure_cmd = agentcore_cmd + [
                'configure',
                '--entrypoint',
                app_file,
                '--name',
                agent_name,
                '--region',
                region,
                '--execution-role',
                execution_role,
            ]
        else:
            configure_cmd = [
                agentcore_cmd,
                'configure',
                '--entrypoint',
                app_file,
                '--name',
                agent_name,
                '--region',
                region,
                '--execution-role',
                execution_role,
            ]

        steps.append('Pending: Configuring agent...')
        steps.append(f'Command: `{" ".join(configure_cmd)}`')
        result = subprocess.run(configure_cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise MCPtoolError(f"""X Configuration Failed

Error: {result.stderr}
Command: `{' '.join(configure_cmd)}`

Environment Details:
- Virtual env: {venv_python or 'Not found'}
- UV available: {uv_available}
- Working dir: {Path.cwd()}

Troubleshooting:
1. Install AgentCore from PyPI: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`
2. Check AWS credentials: `aws sts get-caller-identity`
3. Verify file exists: `ls -la {app_file}`
""")

        steps.append('OK Agent configured successfully')

        # Step 2: Deploy
        if isinstance(agentcore_cmd, list):
            deploy_cmd = agentcore_cmd + ['deploy', '--name', agent_name]
        else:
            deploy_cmd = [agentcore_cmd, 'deploy', '--name', agent_name]

        steps.append('Pending: Deploying agent...')
        result = subprocess.run(deploy_cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise MCPtoolError(f"""X Deployment Failed

Error: {result.stderr}
Command: `{' '.join(deploy_cmd)}`

Steps Completed:
{chr(10).join(steps)}

Troubleshooting:
1. Check agent configuration: `agentcore get-agent --name {agent_name}`
2. Verify IAM permissions
3. Check CloudWatch logs
""")

        steps.append('OK Agent deployed successfully')

        # Step 3: Get agent info
        if isinstance(agentcore_cmd, list):
            info_cmd = agentcore_cmd + ['get-agent', '--name', agent_name]
        else:
            info_cmd = [agentcore_cmd, 'get-agent', '--name', agent_name]
        result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)

        agent_info = result.stdout if result.returncode == 0 else 'Info unavailable'

        return f"""# Launch: Deployment Successful!

### Deployment Steps:
{chr(10).join(steps)}

### Agent Information:
```json
{agent_info}
```

### Testing Your Agent:
```bash
# Test with a simple prompt
agentcore invoke --agent {agent_name} '{{"prompt": "Hello, how are you?"}}'

# Monitor logs
agentcore logs --agent {agent_name} --tail
```

### Next Steps:
- Use `invoke_agent` to test your deployed agent
- Use `get_agent_status` to monitor agent health

Your agent is live and ready to use!
"""

    except subprocess.TimeoutExpired:
        raise MCPtoolError(f"""X Deployment Timeout

Steps Completed:
{chr(10).join(steps)}

The deployment is taking longer than expected. Check status:
```bash
agentcore get-agent --name {agent_name}
```
""")
    except Exception as e:
        raise MCPtoolError(f"""X Deployment Error

Error: {str(e)}
Steps Completed:
{chr(10).join(steps)}
""")


async def execute_agentcore_deployment_sdk(  # pragma: no cover
    app_file: str,
    agent_name: str,
    region: str,
    memory_enabled: bool,
    execution_role: str,
    environment: str,
    enable_oauth: bool = False,  # pragma: allowlist secret  # pragma: no cover
    cognito_user_pool: str = '',
) -> str:  # pragma: no cover
    """Execute AgentCore deployment using SDK - follows exact tutorial patterns."""  # pragma: no cover
    # Check for starter toolkit Runtime availability  # pragma: no cover
    if not SDK_AVAILABLE:  # pragma: no cover
        return f"""X AgentCore SDK Not Available

Error: {SDK_IMPORT_ERROR}

To use SDK deployment:
1. Install: `uv pip install -e ./bedrock-agentcore-sdk`
2. Install: `uv pip install -e ./bedrock-agentcore-starter-toolkit`
3. Ensure AWS credentials are configured
4. Retry deployment

Alternative: Use `execution_mode: "cli"` for CLI commands instead.
"""

    try:  # pragma: no cover
        # Validate entrypoint file exists
        if not Path(app_file).exists():
            return f"X App file '{app_file}' not found at path: {Path(app_file).resolve()}"  # pragma: no cover

        deployment_steps = []
        deployment_results = {}
        oauth_config = None  # pragma: allowlist secret  # pragma: no cover

        # Read and validate the app file
        with open(app_file, 'r') as f:
            app_content = f.read()

        if 'BedrockAgentCoreApp' not in app_content:
            raise MCPtoolError(f"""X Invalid AgentCore Application

The file '{app_file}' doesn't appear to be a valid AgentCore application.
It must contain 'BedrockAgentCoreApp' and '@app.entrypoint' decorator.

Use the `transform_to_agentcore` tool first to convert your code.
""")

        if 'app.run()' not in app_content:
            raise MCPtoolError(f"""X Missing app.run() in Agent Code

The file '{app_file}' must contain 'app.run()' in the main block:
```python
if __name__ == "__main__":
    app.run()
```

Use the `transform_to_agentcore` tool to fix this.
""")

        # Handle OAuth configuration if enabled
        if enable_oauth:  # pragma: allowlist secret
            deployment_steps.append(
                'Security: OAuth authentication enabled - setting up Cognito...'
            )

            try:
                # Reuse existing OAuth infrastructure from utils/gateway  # pragma: no cover
                if not RUNTIME_AVAILABLE:  # pragma: no cover
                    return 'X Runtime SDK not available - OAuth requires bedrock-agentcore-starter-toolkit'

                from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

                # Create GatewayClient to reuse OAuth setup  # pragma: no cover
                gateway_client = GatewayClient(region_name=region)

                # Create OAuth authorizer with Cognito (reusing existing gateway method)  # pragma: no cover
                cognito_result = gateway_client.create_oauth_authorizer_with_cognito(  # pragma: allowlist secret
                    f'{agent_name}_runtime'
                )
                client_info = cognito_result.get('client_info', {})

                deployment_steps.append(
                    f'OK Cognito User Pool: {client_info.get("user_pool_id", "Unknown")}'
                )
                deployment_steps.append(f'OK Client ID: {client_info.get("client_id", "Unknown")}')

                # Store OAuth config in SAME FORMAT as gateways for reuse
                config_dir = Path.home() / '.agentcore_gateways'  # Same directory as gateways!
                config_dir.mkdir(exist_ok=True)

                oauth_config = {  # pragma: allowlist secret
                    'gateway_name': f'{agent_name}_runtime',  # Same format as gateways
                    'gateway_id': f'runtime_{agent_name}',
                    'region': region,
                    'cognito_client_info': client_info,  # Same key as gateways
                    'oauth_enabled': True,  # pragma: allowlist secret
                    'agent_name': agent_name,  # Additional runtime-specific info
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                }

                config_file = config_dir / f'{agent_name}_runtime.json'  # Same naming pattern
                with open(config_file, 'w') as f:
                    json.dump(oauth_config, f, indent=2)

                deployment_steps.append(f'OK OAuth config stored: {config_file}')
                deployment_steps.append(
                    'OK Config format compatible with existing `get_oauth_access_token` tool'
                )
                deployment_results['oauth_config'] = oauth_config

            except Exception as oauth_error:
                return f"""X OAuth Setup Failed

                            Error: {str(oauth_error)} # pragma: allowlist secret
                            Agent: {agent_name}

                            Troubleshooting:
                            1. Check AWS permissions for Cognito operations
                            2. Verify region: {region}
                            3. Install starter toolkit: `uv add bedrock-agentcore-starter-toolkit`
                            4. Try without OAuth first: `enable_oauth: False`
                            """

        # CORRECT TUTORIAL PATTERN - Use bedrock_agentcore_starter_toolkit.Runtime
        deployment_steps.append('Launch: Using bedrock_agentcore_starter_toolkit.Runtime...')

        # Get the directory containing the app file for proper entrypoint handling
        app_path = Path(app_file)
        app_dir = app_path.parent

        # Change to app directory (Runtime expects to work from app directory like tutorials)

        original_cwd = os.getcwd()
        try:
            os.chdir(app_dir)
            deployment_steps.append(f'Directory: Working directory: {app_dir}')

            # Get Runtime object (file-based persistence like tutorial)
            runtime = get_runtime_for_agent(agent_name)
            deployment_steps.append(f'OK Runtime object ready for {agent_name}')

            # Step 1: Configure with OAuth if enabled (exact tutorial pattern from notebooks)
            deployment_steps.append('Config: Step 1: Configuring agent...')

            configure_params = {
                'entrypoint': app_path.name,  # Just filename like tutorials
                'auto_create_execution_role': (execution_role == 'auto'),
                'auto_create_ecr': True,
                'agent_name': agent_name,
                'region': region,
            }

            # Note: OAuth configuration will be handled at invocation time
            # Runtime.configure() doesn't support inbound_config directly
            if enable_oauth and oauth_config:  # pragma: allowlist secret
                deployment_steps.append('OK OAuth config prepared - will be used for invocation')

            configure_result = runtime.configure(**configure_params)

            # Runtime uses file-based persistence (config saved to .bedrock_agentcore.yaml)

            deployment_steps.append('OK Agent configured successfully')
            deployment_results['configure_result'] = str(configure_result)

            # Step 2: Launch (exact tutorial pattern)
            deployment_steps.append('Launch: Step 2: Launching agent...')

            launch_result = runtime.launch()

            # Runtime uses file-based persistence (deployment state managed by AWS)

            deployment_steps.append('OK Launch initiated successfully')
            deployment_results['launch_result'] = str(launch_result)

            # Step 3: Wait for READY status (exact tutorial pattern)
            deployment_steps.append('Pending: Step 3: Waiting for agent to be ready...')

            max_wait_time = 300  # 5 minutes
            wait_start = time.time()

            while time.time() - wait_start < max_wait_time:
                status_result = runtime.status()
                print(status_result)
                # Handle different status response formats from starter toolkit
                if hasattr(status_result, 'endpoint'):
                    status = (
                        status_result.endpoint.get('status', 'UNKNOWN')
                        if status_result.endpoint
                        else 'UNKNOWN'
                    )
                    deployment_results['endpoint_info'] = status_result.endpoint
                else:
                    status = str(status_result)

                deployment_steps.append(f'Stats: Current status: {status}')

                # Check for terminal states
                terminal_states = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
                if any(state in str(status) for state in terminal_states):
                    if 'READY' in str(status):
                        deployment_steps.append('OK Agent is READY!')
                        deployment_results['status'] = 'READY'
                        # Agent is ready - Runtime will use persistent config for invoke
                        break
                    else:
                        deployment_steps.append(f'X Agent deployment failed with status: {status}')
                        deployment_results['status'] = str(status)
                        break

                time.sleep(10)  # Wait 10 seconds between checks
            else:
                deployment_steps.append(
                    'Timeout: Deployment timeout - agent may still be starting'
                )
                deployment_results['status'] = 'TIMEOUT'

            # Step 4: Test invoke if ready (exact tutorial pattern)
            if deployment_results.get('status') == 'READY':
                deployment_steps.append('Test: Step 4: Testing agent invocation...')
                try:
                    test_payload = {'prompt': 'Hello! Testing deployment.'}

                    # For OAuth agents, test invocation requires proper authentication
                    if enable_oauth:  # pragma: allowlist secret
                        deployment_steps.append('! OAuth-enabled agent - skipping direct test')
                        deployment_steps.append(
                            'Note: Use `get_runtime_oauth_token` and `invoke_oauth_agent` for testing'
                        )
                        deployment_results['test_status'] = 'SKIPPED_OAUTH_REQUIRED'
                    else:
                        invoke_response = runtime.invoke(test_payload)
                        deployment_steps.append('OK Agent test invocation successful!')
                        deployment_results['test_response'] = invoke_response
                        deployment_results['test_status'] = 'PASSED'

                except Exception as e:
                    deployment_steps.append(f'! Agent test failed: {str(e)}')
                    deployment_results['test_status'] = f'FAILED: {str(e)}'

        finally:
            # Always restore original working directory
            os.chdir(original_cwd)

        # Generate success response with OAuth information
        oauth_summary = ''  # pragma: allowlist secret
        if enable_oauth and oauth_config:  # pragma: allowlist secret
            client_info = oauth_config.get('cognito_client_info', {})  # pragma: allowlist secret
            oauth_summary = f"""

### OAuth Configuration:
- Authentication: Bearer token required for invocation
- User Pool: `{client_info.get('user_pool_id', 'Unknown')}`
- Client ID: `{client_info.get('client_id', 'Unknown')}`
- Discovery URL: `https://cognito-idp.{region}.amazonaws.com/{client_info.get('user_pool_id', 'Unknown')}/.well-known/jwks.json`
- OAuth Config: Stored in `~/.agentcore_gateways/{agent_name}_runtime.json`"""

        return f"""# Launch: SDK Deployment Successful!

### Deployment Steps:
{chr(10).join(deployment_steps)}

### Deployment Results:
- Agent Name: `{agent_name}`
- Region: `{region}`
- Status: `{deployment_results.get('status', 'DEPLOYED')}`
- OAuth Enabled: `{enable_oauth}` # pragma: allowlist secret
{f'- Test Status: `{deployment_results.get("test_status", "N/A")}`' if deployment_results.get('test_status') else ''}
{oauth_summary} # pragma: allowlist secret

### Next Steps:
- Use `invoke_agent` to interact with your deployed agent{'' if not enable_oauth else ' (with OAuth tokens)'}
- Use `get_agent_status` to monitor agent health
{'- Use `get_runtime_oauth_token` for OAuth token generation' if enable_oauth else ''}

Your agent is deployed and ready to use! Success:
"""

    except Exception as e:
        raise MCPtoolError(f"""X SDK Deployment Error

Error: {str(e)}
App File: {app_file}
Region: {region}

Troubleshooting:
1. Ensure AWS credentials: `aws configure list`
2. Check file permissions: `ls -la {app_file}`
3. Verify SDK installation: `python -c "import bedrock_agentcore; print('SDK OK')"`
4. Try CLI mode instead: `execution_mode: "cli"`
""")


async def invoke_agent_via_aws_sdk(
    agent_name: str, agent_arn: str, prompt: str, session_id: str, region: str
) -> str:
    """Invoke agent directly via AWS SDK - for SDK deployed agents without local config."""
    try:
        import json

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        agentcore_client = boto3.client('bedrock-agentcore', region_name=region)
        # If no ARN provided, find it via list_agent_runtimes
        if not agent_arn:
            try:
                control_client = boto3.client('bedrock-agentcore-control', region_name=region)
                list_response = control_client.list_agent_runtimes()
                for runtime in list_response.get('agentRuntimes', []):
                    if runtime.get('agentRuntimeName') == agent_name:
                        agent_arn = runtime.get('agentRuntimeArn')
                        break

                if not agent_arn:
                    raise MCPtoolError(f'Agent runtime not found: {agent_name}')
            except Exception as e:
                raise MCPtoolError(f'Failed to find agent ARN: {str(e)}')

        # Use correct payload format: JSON string
        payload = json.dumps({'prompt': prompt})

        req = {'agentRuntimeArn': agent_arn, 'runtimeSessionId': session_id, 'payload': payload}

        response = agentcore_client.invoke_agent_runtime(**req)

        # Handle StreamingBody response
        if 'response' in response:
            response_content = response['response'].read().decode('utf-8')
            try:
                parsed_response = json.loads(response_content)
                return f"""# Agent: AWS SDK Invocation Successful

### Request:
- Agent: {agent_name}
- ARN: {agent_arn}
- Prompt: "{prompt}"
- Session: {session_id}

### Response:
```json
{json.dumps(parsed_response, indent=2)}
```

### Session Info:
- Session ID: `{session_id}`
- Method: Direct AWS SDK
- Status: {response.get('statusCode', 'Unknown')}
"""
            except json.JSONDecodeError:
                return f'Raw response: {response_content}'

        return str(response)

    except ImportError:
        raise ImportError('X boto3 not available - cannot invoke via AWS SDK')
    except Exception as e:
        raise MCPtoolError(f'X AWS SDK Error: {str(e)}')
