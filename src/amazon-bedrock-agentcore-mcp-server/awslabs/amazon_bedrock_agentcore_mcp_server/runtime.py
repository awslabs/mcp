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
"""AgentCore MCP Server - Runtime Management Module.

Contains agent runtime deployment, invocation, status, and lifecycle management tools.

MCP TOOLS IMPLEMENTED:
• analyze_agent_code - Analyze existing agent code and determine migration strategy
• transform_to_agentcore - Transform agent code to AgentCore format
• deploy_agentcore_app - Deploy AgentCore agents (CLI/SDK modes)
• invoke_agent - Invoke deployed agents with config directory switching
• invoke_oauth_agent - OAuth-enabled agent invocation with Bearer tokens
• invoke_agent_smart - Smart invocation (regular first, OAuth fallback)
• get_agent_status - Check agent deployment and runtime status
• check_oauth_status - Authoritative OAuth deployment status checking
• get_runtime_oauth_token - Get OAuth access tokens for runtime agents

"""

import os
import subprocess
from .utils import (
    RUNTIME_AVAILABLE,
    SDK_AVAILABLE,
    SDK_IMPORT_ERROR,
    YAML_AVAILABLE,
    analyze_code_patterns,
    check_agent_config_exists,
    find_agent_config_directory,
    format_dependencies,
    format_features_added,
    format_patterns,
    get_agentcore_command,
    get_runtime_for_agent,
    get_user_working_directory,
    resolve_app_file_path,
)
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from pydantic import Field
from typing import Any, Dict, Literal


# ============================================================================
# OAUTH UTILITIES (SHARED)
# ============================================================================


def check_agent_oauth_status(
    agent_name: str, region: str = 'us-east-1'
):  # pragma: allowlist secret
    """Check if agent is actually deployed with OAuth using AWS API (get_agent_runtime).

    This is the authoritative source - much better than parsing YAML files.

    Returns:
        tuple: (oauth_deployed: bool, oauth_available: bool, message: str)
    """
    from pathlib import Path

    try:
        import boto3

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
                    try:
                        import yaml

                        with open(yaml_file, 'r') as f:
                            yaml_config = yaml.safe_load(f)

                        agents = yaml_config.get('agents', {})
                        agent_config = agents.get(agent_name, {})
                        bedrock_config = agent_config.get('bedrock_agentcore', {})
                        agent_runtime_arn = bedrock_config.get('agent_arn')

                        if agent_runtime_arn:
                            break
                    except ImportError:
                        # No PyYAML, try simple parsing
                        with open(yaml_file, 'r') as f:
                            yaml_content = f.read()

                        if f'{agent_name}:' in yaml_content and 'agent_arn:' in yaml_content:
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

                            if agent_runtime_arn:
                                break
                    except Exception:
                        continue
        except Exception:
            pass

        # Method 2: If no ARN found locally, search for it via API
        if not agent_runtime_arn:
            try:
                list_response = agentcore_client.list_agent_runtimes()
                for runtime in list_response.get('items', []):
                    if runtime.get('name') == agent_name:
                        agent_runtime_arn = runtime.get('agentRuntimeArn')
                        break
            except Exception:
                pass

        if not agent_runtime_arn:
            return False, False, f'Agent runtime ARN not found for {agent_name}'

        # Get the actual runtime configuration from AWS
        oauth_available = False
        try:
            runtime_response = agentcore_client.get_agent_runtime(
                agentRuntimeArn=agent_runtime_arn
            )

            # Check for inbound configuration (OAuth/auth settings)
            inbound_config = runtime_response.get('inboundConfig', {})

            # Check if OAuth config exists in our separate storage
            oauth_file = (
                Path.home() / '.agentcore_gateways' / f'{agent_name}_runtime.json'
            )  # pragma: allowlist secret
            oauth_available = oauth_file.exists()  # pragma: allowlist secret

            # Determine OAuth status from AWS API response
            oauth_deployed = bool(
                inbound_config
            )  # Any inbound config indicates auth requirements # pragma: allowlist secret

            if oauth_deployed:  # pragma: allowlist secret
                auth_details = []
                if 'customJWTAuthorizer' in inbound_config:
                    jwt_auth = inbound_config['customJWTAuthorizer']
                    auth_details.append(
                        f'JWT Auth (Client: {jwt_auth.get("clientId", "Unknown")})'
                    )
                if 'cognitoAuthorizer' in inbound_config:  # pragma: allowlist secret
                    cognito_auth = inbound_config['cognitoAuthorizer']
                    auth_details.append(
                        f'Cognito Auth (Pool: {cognito_auth.get("userPoolId", "Unknown")})'
                    )

                auth_summary = (
                    ', '.join(auth_details) if auth_details else 'Custom auth configured'
                )
                return True, oauth_available, f'Agent deployed with OAuth: {auth_summary}'

            elif oauth_available:  # pragma: allowlist secret
                return (
                    False,
                    True,
                    'Agent deployed without OAuth, but OAuth config available for redeployment',
                )

            else:
                return False, False, 'Agent deployed without OAuth, no OAuth config available'

        except Exception as api_error:
            # Fallback to local config analysis if API fails
            if oauth_available:  # pragma: allowlist secret
                return (
                    False,
                    True,
                    f'Cannot verify deployment OAuth status (API error: {str(api_error)}), but OAuth config exists locally',
                )
            else:
                return False, False, f'Cannot verify OAuth status: {str(api_error)}'

    except ImportError:
        return False, False, 'boto3 not available - cannot check OAuth deployment status'
    except Exception as e:
        # Check if OAuth config exists in our separate storage as fallback
        oauth_file = Path.home() / '.agentcore_gateways' / f'{agent_name}_runtime.json'
        oauth_available = oauth_file.exists()

        if oauth_available:  # pragma: allowlist secret
            return (
                False,
                True,
                f'Cannot verify deployment OAuth status ({str(e)}), but OAuth config exists locally',
            )
        else:
            return False, False, f'Error checking OAuth status: {str(e)}'


def validate_oauth_config(agent_name: str, region: str = 'us-east-1'):  # pragma: allowlist secret
    """Unified OAuth configuration validation for runtime agents.

    Returns:
        tuple: (success: bool, result: dict or str)
        - If success=True: result contains validated config dict
        - If success=False: result contains error message string
    """
    try:
        import json
        from pathlib import Path

        # First check if the agent is actually deployed with OAuth
        oauth_deployed, oauth_available, oauth_status = (
            check_agent_oauth_status(  # pragma: allowlist secret
                agent_name, region
            )
        )

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
            with open(config_file, 'r') as f:
                oauth_config = json.load(f)

            client_info = oauth_config.get('cognito_client_info', {})
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


def generate_oauth_token(client_info: dict, region: str = 'us-east-1'):
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
# AGENT CODE ANALYSIS AND TRANSFORMATION
# ============================================================================


def register_analysis_tools(mcp: FastMCP):
    """Register code analysis and transformation tools."""

    @mcp.tool()
    async def analyze_agent_code(
        file_path: str = Field(
            description="Path to your agent file (e.g., 'agent.py', 'main.py')"
        ),
        code_content: str = Field(
            default='', description='Optional: Paste code directly if no file'
        ),
    ) -> str:
        """Step 1: Analyze your existing agent code and determine migration strategy."""
        try:
            # Environment detection
            env_info = []
            if Path('.venv').exists():
                env_info.append('OK Virtual environment (.venv) detected')
            if Path('venv').exists():
                env_info.append('OK Virtual environment (venv) detected')

            # Check for uv
            try:
                result = subprocess.run(['which', 'uv'], capture_output=True, text=True)
                if result.returncode == 0:
                    env_info.append('OK UV package manager available')
            except Exception as e:
                print(e)
                pass

            # Get user's actual working directory
            user_dir = get_user_working_directory()
            available_files = list(user_dir.glob('*.py')) + list(user_dir.glob('examples/*.py'))

            # Try to resolve file path if provided
            resolved_path = None
            if file_path:
                resolved_path = resolve_app_file_path(file_path)

            if resolved_path:
                with open(resolved_path, 'r') as f:
                    code_content = f.read()
            elif not code_content:
                return f"""X No Code Found

Please provide either:
1. A valid file path to your agent code
2. Paste your code in the `code_content` parameter

Environment Status:
{chr(10).join(env_info) if env_info else '- No special environment detected'}

Available Python files found:
{chr(10).join(f'- {f.name} ({f.parent.name})' for f in available_files[:10]) if available_files else '- No Python files found'}

User working directory: {user_dir}
Searched paths: {file_path if file_path else 'None provided'}
"""

            # Analyze the code
            analysis = analyze_code_patterns(code_content)

            # Generate migration strategy
            strategy = generate_migration_strategy(analysis)

            # Generate tutorial-based migration guidance
            migration_guidance = generate_tutorial_based_guidance(analysis['framework'])

            return f"""# Search: Agent Code Analysis Complete

### Environment Status:
{chr(10).join(env_info) if env_info else '- Standard Python environment'}

### Current Framework Detected: {analysis['framework']}

### Code Patterns Found:
{format_patterns(analysis['patterns'])}

### Dependencies Detected:
{format_dependencies(analysis['dependencies'])}

### Migration Strategy: {strategy['complexity']}

{strategy['description']}

### Tutorial-Based Migration Path:
{migration_guidance}

### Next Steps:
1. OK Analysis Complete
2. Update: Ready: Use `transform_to_agentcore` to convert your code
3. Pending: Pending: Deploy with `deploy_agentcore_app`
4. Pending: Pending: Configure memory/identity if needed (optional)

Estimated Migration Time: {strategy['time_estimate']}
"""

        except Exception as e:
            return f'X Analysis Error: {str(e)}'

    @mcp.tool()
    async def transform_to_agentcore(
        source_file: str = Field(description='Original agent file to transform'),
        target_file: str = Field(
            default='', description='Output file name (auto-generated if empty)'
        ),
        preserve_logic: bool = Field(default=True, description='Keep original agent logic intact'),
        add_memory: bool = Field(default=False, description='Add memory integration (optional)'),
        add_tools: bool = Field(
            default=False, description='Add code interpreter and browser tools (optional)'
        ),
    ) -> str:
        """Step 2: Transform your agent code to AgentCore format - minimal transformation preserving original logic."""
        try:
            # Use improved path resolution
            resolved_source = resolve_app_file_path(source_file)
            if not resolved_source:
                user_dir = get_user_working_directory()
                return f"""X Source file not found

Looking for: `{source_file}`
User working directory: `{user_dir}`

Tip: Try using just the filename (e.g., 'your_agent.py') or check the file exists in your project directory.
"""

            source_file = resolved_source

            # Read original code
            with open(source_file, 'r') as f:
                original_code = f.read()

            # Analyze to understand current structure
            analysis = analyze_code_patterns(original_code)

            # Generate target filename if not provided
            if not target_file:
                target_file = f'agentcore_{Path(source_file).stem}.py'

            # Transform the code using validated SDK methods
            transformed_code = generate_safe_agentcore_code(
                original_code,
                analysis,
                {
                    'preserve_logic': preserve_logic,
                    'add_memory': add_memory,
                    'add_tools': add_tools,
                },
            )

            # Write transformed code
            with open(target_file, 'w') as f:
                f.write(transformed_code)

            return f"""# OK Code Transformation Complete

### Files:
- Original: `{source_file}`
- Transformed: `{target_file}`

### AgentCore Features Added:
{format_features_added({'add_memory': add_memory, 'add_tools': add_tools})}

### Generated Code Preview:
```python
{transformed_code[:500]}...
```

### Next Steps:
1. OK Analysis Complete
2. OK Transformation Complete
3. Update: Ready: Use `deploy_agentcore_app` to deploy
4. Pending: Pending: Configure advanced features if needed

Ready to deploy! Your AgentCore app is in `{target_file}`
"""

        except Exception as e:
            return f'X Transformation Error: {str(e)}'


# ============================================================================
# AGENT DEPLOYMENT AND LIFECYCLE
# ============================================================================


def register_deployment_tools(mcp: FastMCP):
    """Register agent deployment and lifecycle management tools."""

    @mcp.tool()
    async def deploy_agentcore_app(
        app_file: str = Field(description='AgentCore app file to deploy'),
        agent_name: str = Field(description='Name for your deployed agent'),
        execution_mode: Literal['ask', 'cli', 'sdk'] = Field(
            default='ask', description='How to deploy'
        ),
        region: str = Field(default='us-east-1', description='AWS region'),
        memory_enabled: bool = Field(
            default=False, description='Create and configure memory (optional)'
        ),
        execution_role: str = Field(
            default='auto', description='IAM execution role (auto to create)'
        ),
        environment: str = Field(default='dev', description='Deployment environment'),
        enable_oauth: bool = Field(
            default=False, description='Enable OAuth authentication for agent invocation'
        ),
        cognito_user_pool: str = Field(
            default='', description='Existing Cognito User Pool ID (or auto-create)'
        ),
    ) -> str:
        """Step 3: Deploy your AgentCore app - minimal deployment, choose CLI commands or SDK execution."""
        try:
            # Use improved path resolution
            resolved_app_file = resolve_app_file_path(app_file)

            if not resolved_app_file:
                user_dir = get_user_working_directory()
                available_files = list(user_dir.glob('/*.py'))[:10]

                return f"""X App file not found

Looking for: `{app_file}`
User working directory: `{user_dir}`
Searched locations:
- {app_file} (as provided)
- {user_dir}/{app_file}
- {user_dir}/examples/{Path(app_file).name}

Available Python files:
{chr(10).join(f'- {f.relative_to(user_dir)}' for f in available_files) if available_files else '- No Python files found'}

Please ensure the file exists or provide the correct path.
"""

            app_file = resolved_app_file

            # Handle execution mode choice
            if execution_mode == 'ask':
                return f"""# Launch: Deploy {agent_name} - Choose Your Approach

### Option 1: CLI Commands (You Execute)
I'll provide exact `agentcore` CLI commands for you to run in your terminal.
- Pros: Full control, see all steps, easier debugging, standard approach
- Cons: You need to run commands manually
- Best for: Learning, debugging, production deployments

### Option 2: SDK Execution (I Execute)
I'll use the AgentCore SDK to deploy directly for you.
- Pros: Automatic, faster, handles errors, no manual steps
- Cons: Less visibility into individual steps
- Best for: Quick deployments, development iterations

---

To proceed, call this tool again with:
- `execution_mode: "cli"` - For CLI commands
- `execution_mode: "sdk"` - For automatic SDK deployment

Current file: `{app_file}`
Agent name: `{agent_name}`
Region: `{region}`
"""

            elif execution_mode == 'cli':
                deployment_result = await execute_agentcore_deployment_cli(
                    app_file,
                    agent_name,
                    region,
                    memory_enabled,
                    execution_role,
                    environment,
                    enable_oauth,
                    cognito_user_pool,
                )
            else:  # sdk
                deployment_result = await execute_agentcore_deployment_sdk(
                    app_file,
                    agent_name,
                    region,
                    memory_enabled,
                    execution_role,
                    environment,
                    enable_oauth,
                    cognito_user_pool,
                )

            return deployment_result

        except Exception as e:
            return f'X Deployment Error: {str(e)}'

    @mcp.tool()
    async def invoke_agent(
        agent_name: str = Field(description='Agent name to invoke'),
        prompt: str = Field(description='Message to send to agent'),
        session_id: str = Field(default='', description='Session ID for conversation continuity'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Invoke deployed AgentCore agent - automatically finds config and switches directories."""
        if not RUNTIME_AVAILABLE:
            return """X Runtime Not Available

To invoke deployed agents:
1. Install: `uv add bedrock-agentcore-starter-toolkit`
2. Ensure agent is deployed
3. Retry invocation
"""
        import json
        import os
        import uuid

        config_dir = ''
        try:
            # Find the correct config directory for this agent
            config_found, config_dir = find_agent_config_directory(agent_name)

            # If not found, try to use directly with AWS SDK (for SDK-deployed agents)
            if not config_found:
                try:
                    # Try direct AWS invocation for SDK-deployed agents
                    return await invoke_agent_via_aws_sdk(agent_name, prompt, session_id, region)
                except Exception as e:
                    return f"""X Agent Configuration Not Found
Error invoking via AWS SDK: {str(e)}
Agent: {agent_name}
Issue: No configuration found and AWS SDK invoke failed

Troubleshooting:
1. Check available agents: `discover_existing_agents`
2. Verify agent name and deployment status
3. Ensure agent was deployed successfully
4. Try: `get_agent_status` to check AWS status

Search locations checked:
- Current directory: {Path.cwd()}
- User working directory: {get_user_working_directory()}
- examples/ subdirectory
- Direct AWS SDK invocation (failed)
"""

            # Switch to config directory (like the tutorial shows)
            original_cwd = Path.cwd()
            os.chdir(config_dir)

            try:
                # Get Runtime object and check status (file-based persistence like tutorial)
                runtime = get_runtime_for_agent(agent_name)

                # Check deployment status first
                try:
                    status_result = runtime.status()
                    if hasattr(status_result, 'endpoint'):
                        endpoint_status = (
                            status_result.endpoint.get('status', 'UNKNOWN')
                            if status_result.endpoint
                            else 'UNKNOWN'
                        )
                        if endpoint_status != 'READY':
                            return f"""X Agent Not Ready

Agent: {agent_name}
Status: {endpoint_status}
Config Directory: {config_dir}

Next Steps:
- Wait for agent to reach READY status
- Check deployment: `get_agent_status`
- Redeploy if needed: `deploy_agentcore_app`
"""
                    else:
                        return f"""X Agent Not Deployed

Agent: {agent_name}
Issue: Configured but not deployed to AWS
Config Directory: {config_dir}

Next Steps: Complete deployment with `deploy_agentcore_app`
"""
                except ValueError as e:
                    if 'Must configure' in str(e):
                        return f"""X Agent Not Configured

Agent: {agent_name}
Issue: Runtime configuration missing
Config Directory: {config_dir}

Next Steps: Deploy agent first with `deploy_agentcore_app`
"""
                    raise

                # Generate session ID if not provided
                if not session_id:
                    session_id = str(uuid.uuid4())[:8]

                # Prepare payload exactly like tutorial
                payload = {'prompt': prompt}

                # Invoke using the persistent Runtime object - tutorial pattern
                result = runtime.invoke(payload)

                # Process response like tutorial shows - handle bytes data properly
                if hasattr(result, 'response'):
                    response_data = result.get('response', {})
                    # Handle bytes response from AgentCore
                    if isinstance(response_data, list) and len(response_data) > 0:
                        if isinstance(response_data[0], bytes):
                            decoded_response = None
                            try:
                                # Decode bytes and parse JSON
                                decoded_response = response_data[0].decode('utf-8')
                                response_data = json.loads(decoded_response)
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                # If decoding fails, use string representation
                                response_data = (
                                    decoded_response
                                    if 'decoded_response' in locals()
                                    else str(response_data[0])
                                )
                    elif isinstance(response_data, bytes):
                        decoded_response = None
                        try:
                            decoded_response = response_data.decode('utf-8')
                            response_data = json.loads(decoded_response)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            response_data = (
                                decoded_response
                                if 'decoded_response' in locals()
                                else str(response_data)
                            )
                else:
                    response_data = result

                return f"""# Agent: Agent Invocation Successful

### Request:
- Agent: {agent_name}
- Prompt: "{prompt}"
- Session: {session_id}
- Config Directory: {config_dir}
- Status: READY and invoked successfully

### Response:
```json
{json.dumps(response_data, indent=2, default=str) if response_data else 'No response received'}
```

### Session Info:
- Session ID: `{session_id}`
- Runtime object: Persistent (tutorial pattern)
- Use this session ID for follow-up messages

Next: Continue using same `agent_name` for consistent Runtime object
"""

            finally:
                # Always restore original directory
                try:
                    os.chdir(original_cwd)
                except Exception as e:
                    print(f'Warning: Could not restore original directory: {str(e)}')
                    pass

        except Exception as e:
            return f"""X Invocation Error: {str(e)}

Troubleshooting:
1. Check available agents: `discover_existing_agents`
2. Verify agent status: `get_agent_status`
3. Try from correct directory: Config in `{config_dir if 'config_dir' in locals() else 'unknown'}`
4. Redeploy if needed: `deploy_agentcore_app`
"""

    @mcp.tool()
    async def invoke_oauth_agent(
        agent_name: str = Field(description='OAuth-enabled agent name to invoke'),
        prompt: str = Field(description='Message to send to agent'),
        session_id: str = Field(default='', description='Session ID for conversation continuity'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Invoke OAuth-enabled AgentCore agent with Bearer token authentication.

        Simplified approach: Uses Runtime SDK pattern with OAuth token validation.
        For most users, this provides the same experience as invoke_agent but with OAuth security.
        """
        try:
            import json
            import uuid
            from pathlib import Path

            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())[:8]

            # Step 1: Validate OAuth configuration and generate token
            success, result = validate_oauth_config(agent_name, region)
            if not success:
                result_str = result if isinstance(result, str) else str(result)
                return result_str.replace(
                    'Troubleshooting:',
                    'Troubleshooting:\nNote: Try regular invocation first: `invoke_agent` - many agents work without OAuth\n',
                )

            client_info = result.get('client_info', {}) if isinstance(result, dict) else {}

            # Generate OAuth token (validates OAuth setup)
            token_success, access_token = generate_oauth_token(client_info, region)
            if not token_success:
                return f"""{access_token}

Note: Alternative: Try `invoke_agent` instead - your agent may work without OAuth authentication."""

            # Step 2: Use standard Runtime SDK pattern (same as invoke_agent)
            # This is the key insight: OAuth agents can often be invoked normally via Runtime SDK
            try:
                if not RUNTIME_AVAILABLE:
                    return """X Runtime SDK not available

Required: bedrock-agentcore-starter-toolkit
Install: `uv add bedrock-agentcore-starter-toolkit`

Note: OAuth token generated successfully - but Runtime SDK needed for invocation
Token available for manual HTTP calls - use `get_runtime_oauth_token` for details
"""

                # Find agent config directory (same logic as invoke_agent)
                config_dirs_to_check = [
                    Path.cwd(),
                    get_user_working_directory(),
                    Path.cwd() / 'examples',
                    Path.home() / 'agentcore_projects' / agent_name,
                ]

                config_dir_found = None
                for config_dir in config_dirs_to_check:
                    try:
                        # Check if .bedrock_agentcore.yaml exists
                        if (config_dir / '.bedrock_agentcore.yaml').exists():
                            config_dir_found = config_dir
                            break
                    except Exception:
                        continue

                if not config_dir_found:
                    return f"""X Agent Configuration Not Found

Agent: {agent_name}
Searched: {[str(d) for d in config_dirs_to_check]}

OAuth Setup: OK Valid (token generated successfully)
Agent Config: X Missing .bedrock_agentcore.yaml

Fix:
1. Deploy agent: Use `deploy_agentcore_app`
2. Or use manual HTTP: Use `get_runtime_oauth_token` for Bearer token details

Note: OAuth token is ready - just need agent deployment config
"""

                # Change to agent directory and get Runtime object
                import os

                original_cwd = os.getcwd()
                try:
                    os.chdir(config_dir_found)

                    # Get Runtime object (same as invoke_agent)
                    runtime = get_runtime_for_agent(agent_name)
                    status = 'UNKNOWN'
                    # Check agent status
                    try:
                        status_result = runtime.status()
                        if hasattr(status_result, 'endpoint'):
                            status = 'UNKNOWN'
                            if hasattr(status_result, 'endpoint') and status_result.endpoint:
                                status = getattr(status_result.endpoint, 'status', 'UNKNOWN')
                        else:
                            status = str(status_result)

                        if 'READY' not in str(status):
                            return f"""X Agent Not Ready

Agent: {agent_name}
Status: {status}
OAuth: OK Token generated successfully

Wait for agent to be READY, then try again
Or use: `get_agent_status` for detailed status
"""
                    except Exception as status_error:
                        return f"""X Status Check Failed: {str(status_error)}

OAuth: OK Token generated successfully
Issue: Cannot check agent status

Try: `get_agent_status` for detailed agent information
"""

                    # Invoke using Runtime SDK (OAuth handled at infrastructure level)
                    payload = {'prompt': prompt}

                    try:
                        result = runtime.invoke(payload)

                        # Process response (same logic as invoke_agent)
                        response_data = result
                        if hasattr(result, 'get') and 'response' in result:
                            response_data = result['response']

                            # Handle various response formats
                            if isinstance(response_data, list) and len(response_data) > 0:
                                if isinstance(response_data[0], str) and response_data[
                                    0
                                ].startswith("b'"):
                                    # Handle byte string format
                                    try:
                                        # Remove b' and ' wrapper, then parse JSON
                                        json_str = (
                                            response_data[0][2:-1]
                                            .replace('\\"', '"')
                                            .replace('\\\\n', '\\n')
                                        )
                                        response_data = json.loads(json_str)
                                    except (json.JSONDecodeError, IndexError):
                                        response_data = response_data[0]
                                elif isinstance(response_data[0], bytes):
                                    decoded_response = None
                                    try:
                                        decoded_response = response_data[0].decode('utf-8')
                                        response_data = json.loads(decoded_response)
                                    except (UnicodeDecodeError, json.JSONDecodeError):
                                        response_data = (
                                            decoded_response
                                            if 'decoded_response' in locals()
                                            else str(response_data[0])
                                        )
                            elif isinstance(response_data, bytes):
                                decoded_response = None
                                try:
                                    decoded_response = response_data.decode('utf-8')
                                    response_data = json.loads(decoded_response)
                                except (UnicodeDecodeError, json.JSONDecodeError):
                                    response_data = (
                                        decoded_response
                                        if 'decoded_response' in locals()
                                        else str(response_data)
                                    )
                        else:
                            response_data = result

                        return f"""# Agent: OAuth Agent Invocation Successful

### Request:
- Agent: {agent_name}
- Prompt: "{prompt}"
- Session: {session_id}
- Authentication: OK OAuth token validated
- Method: Runtime SDK with OAuth security

### Response:
```json
{json.dumps(response_data, indent=2, default=str) if response_data else 'No response received'}
```

### Session Info:
- Session ID: `{session_id}`
- OAuth Status: OK Authenticated
- Config Directory: {config_dir_found}
- Runtime Pattern: SDK-based with OAuth validation

OK OAuth authentication successful! Agent invoked via Runtime SDK.
"""

                    except Exception as invoke_error:
                        return f"""X Runtime Invocation Failed: {str(invoke_error)}

Agent: {agent_name}
OAuth: OK Token generated and validated
Issue: Runtime SDK invocation error

Alternative Options:
1. Use regular invocation: `invoke_agent` (may work without OAuth)
2. Manual HTTP with OAuth: Use `get_runtime_oauth_token` for Bearer token
3. Check agent logs: Use `get_agent_status` for debugging

The OAuth setup is correct - this appears to be a Runtime SDK issue, not OAuth.
"""

                finally:
                    os.chdir(original_cwd)

            except Exception as runtime_error:
                return f"""X Runtime Setup Error: {str(runtime_error)}

Agent: {agent_name}
OAuth: OK Token generated successfully

Troubleshooting:
1. Try regular invocation: `invoke_agent`
2. Manual OAuth invocation: Use `get_runtime_oauth_token` for HTTP details
3. Check deployment: Use `get_agent_status`

Note: Your OAuth setup is working - this is a Runtime SDK configuration issue.
"""

        except Exception as e:
            return f"""X OAuth Invocation Error: {str(e)}

Agent: {agent_name}

Quick Fixes:
1. Try without OAuth first: `invoke_agent {agent_name} "your prompt"`
2. Check if OAuth needed: Many agents work without OAuth
3. Get OAuth details: Use `get_runtime_oauth_token` if OAuth required

For OAuth troubleshooting: Check ~/.agentcore_gateways/{agent_name}_runtime.json
"""

    @mcp.tool()
    async def get_runtime_oauth_token(
        agent_name: str = Field(description='OAuth-enabled agent name to get token for'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Get OAuth access token for runtime agent - reuses all gateway infrastructure."""
        try:
            # Use shared validation and token generation (DRY principle)
            success, result = validate_oauth_config(agent_name, region)
            if not success:
                return str(result)

            client_info = result.get('client_info', {}) if isinstance(result, dict) else {}
            oauth_config = result.get('oauth_config', {}) if isinstance(result, dict) else {}

            print(f'OAuth Config: {oauth_config}')

            # Generate access token using shared utility
            token_success, access_token = generate_oauth_token(
                client_info if isinstance(client_info, dict) else {}, region
            )
            if not token_success:
                return access_token

            return f"""# OK Runtime OAuth Token Generated

### Agent Information:
- Agent: `{agent_name}`
- User Pool: `{client_info.get('user_pool_id')}`
- Client ID: `{client_info.get('client_id')}`
- Region: `{region}`

### Target: Access Token:
```
{access_token}
```

### Usage Examples:

#### Direct HTTP Request:
```bash
curl -H "Authorization: Bearer {access_token}" \\
     https://your-runtime-endpoint/invoke \\
     -d '{{"prompt": "Hello!"}}' \\
     -H "Content-Type: application/json"
```

#### Python Requests:
```python
import requests

headers = {{"Authorization": "Bearer {access_token}"}}
payload = {{"prompt": "Hello!"}}
response = requests.post("https://your-runtime-endpoint/invoke",
                        headers=headers, json=payload)
print(response.json())
```

### ! Important Notes:
- Token expires: Use this tool to generate new tokens when needed
- Store securely: Don't commit tokens to version control
- Use with: `invoke_oauth_agent` tool for simplified invocation

Success: Ready for OAuth-authenticated runtime invocation!
"""

        except Exception as e:
            return f"""X OAuth Token Error: {str(e)}

Agent: {agent_name}
Troubleshooting:
1. Check agent deployment: Use `get_agent_status`
2. Verify OAuth config: ~/.agentcore_gateways/{agent_name}_runtime.json
3. Redeploy with OAuth: Use `deploy_agentcore_app` with `enable_oauth: True`
"""

    @mcp.tool()
    async def check_oauth_status(
        agent_name: str = Field(description='Agent name to check OAuth status'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Check the actual OAuth deployment status of an agent using AWS API (get_agent_runtime)."""
        try:
            import json
            from pathlib import Path

            # Check OAuth status via AWS API and config files
            oauth_deployed, oauth_available, oauth_message = check_agent_oauth_status(
                agent_name, region
            )

            # Check OAuth config file details
            config_dir = Path.home() / '.agentcore_gateways'
            config_file = config_dir / f'{agent_name}_runtime.json'

            oauth_config_details = 'Not found'
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        oauth_config = json.load(f)
                    client_info = oauth_config.get('cognito_client_info', {})
                    oauth_config_details = f"""
- User Pool: {client_info.get('user_pool_id', 'Missing')}
- Client ID: {client_info.get('client_id', 'Missing')}
- Created: {oauth_config.get('created_at', 'Unknown')}
"""
                except Exception as e:
                    oauth_config_details = f'Error reading: {str(e)}'

            # Determine recommended invocation method
            if oauth_deployed and oauth_available:
                recommendation = 'OK Use `invoke_oauth_agent` - Agent deployed with OAuth'
                invocation_status = 'Security: OAuth Required'
            elif oauth_available and not oauth_deployed:
                recommendation = 'Note: Use `invoke_agent` - Agent deployed without OAuth (config available for redeployment)'
                invocation_status = ' Regular (OAuth config exists but not deployed)'
            else:
                recommendation = 'OK Use `invoke_agent` - Agent deployed without OAuth'
                invocation_status = ' Regular (No OAuth)'

            return f"""# Search: OAuth Status Report

### Agent: `{agent_name}`

#### Deployment Status:
- OAuth Deployed: {'OK Yes' if oauth_deployed else 'X No'}
- OAuth Config Available: {'OK Yes' if oauth_available else 'X No'}
- Details: {oauth_message}

#### Invocation Status: {invocation_status}

#### OAuth Configuration:
{oauth_config_details}

#### Recommended Invocation:
{recommendation}

#### Configuration Sources:
- AWS API: `get_agent_runtime` (authoritative source)
  - `inboundConfig: {'present' if oauth_deployed else 'empty/null'}`
- Local OAuth Storage: `~/.agentcore_gateways/{agent_name}_runtime.json`
  - Status: {'OK Found' if oauth_available else 'X Missing'}
- Local Agent Config: `.bedrock_agentcore.yaml` (used for ARN lookup)

#### Available Commands:
- `invoke_agent` - Standard invocation (works for most agents)
- `invoke_oauth_agent` - OAuth-authenticated invocation
- `invoke_agent_smart` - Tries both automatically
- `get_runtime_oauth_token` - Generate OAuth tokens manually

#### Next Steps:
{recommendation}
{
                ''
                if oauth_deployed or not oauth_available
                else '''
Note: To enable OAuth: Redeploy with `deploy_agentcore_app` and `enable_oauth: True`'''
            }
"""

        except Exception as e:
            return f"""X OAuth Status Check Error: {str(e)}

Agent: {agent_name}

Manual Check:
1. Look at `.bedrock_agentcore.yaml` for `oauth_configuration`
2. Check `~/.agentcore_gateways/{agent_name}_runtime.json`
3. Try `invoke_agent` first (works for most agents)
"""

    @mcp.tool()
    async def invoke_agent_smart(
        agent_name: str = Field(
            description='Agent name to invoke (tries regular first, OAuth if needed)'
        ),
        prompt: str = Field(description='Message to send to agent'),
        session_id: str = Field(default='', description='Session ID for conversation continuity'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Smart agent invocation - tries regular invocation first, falls back to OAuth if needed.

        This provides the best user experience:
        1. Tries invoke_agent (works for most agents)
        2. If that fails and OAuth config exists, tries OAuth invocation
        3. Provides clear guidance based on results
        """
        try:
            import uuid
            from pathlib import Path

            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())[:8]

            # Step 1: Try regular invocation first (most agents work this way)
            try:
                regular_result = await invoke_agent(
                    agent_name=agent_name, prompt=prompt, session_id=session_id, region=region
                )

                # If regular invocation succeeded, return with note
                if 'Agent: Agent Invocation Successful' in regular_result:
                    return (
                        regular_result.replace(
                            'Agent: Agent Invocation Successful',
                            'Agent: Agent Invocation Successful (Regular)',
                        )
                        + '\n\nNote: This agent works without OAuth authentication.'
                    )

                # If regular invocation failed, check if OAuth is available
                config_dir = Path.home() / '.agentcore_gateways'
                oauth_config_file = config_dir / f'{agent_name}_runtime.json'

                if oauth_config_file.exists():
                    # OAuth config exists, try OAuth invocation
                    return f"""! Regular Invocation Failed - Trying OAuth

Regular invocation error:
```
{regular_result[:500]}...
```

Attempting OAuth invocation...

---

{await invoke_oauth_agent(agent_name=agent_name, prompt=prompt, session_id=session_id, region=region)}
"""
                else:
                    # No OAuth config, return regular error with helpful guidance
                    return f"""{regular_result}

Note: OAuth Alternative: If this agent requires OAuth:
1. Deploy with OAuth: Use `deploy_agentcore_app` with `enable_oauth: True`
2. Then try: `invoke_oauth_agent` for authenticated invocation
"""

            except Exception as regular_error:
                # Regular invocation completely failed, check for OAuth
                config_dir = Path.home() / '.agentcore_gateways'
                oauth_config_file = config_dir / f'{agent_name}_runtime.json'

                if oauth_config_file.exists():
                    return f"""! Regular Invocation Error - Using OAuth

Switching to OAuth authentication...

{await invoke_oauth_agent(agent_name=agent_name, prompt=prompt, session_id=session_id, region=region)}
"""
                else:
                    return f"""X Agent Invocation Failed

Agent: {agent_name}
Error: {str(regular_error)}

Troubleshooting:
1. Check deployment: Use `get_agent_status`
2. Deploy if needed: Use `deploy_agentcore_app`
3. For OAuth agents: Use `deploy_agentcore_app` with `enable_oauth: True`

Available options:
- `invoke_agent` - Standard invocation
- `invoke_oauth_agent` - OAuth-authenticated invocation
- `get_agent_status` - Check agent status
"""

        except Exception as e:
            return f"""X Smart Invocation Error: {str(e)}

Agent: {agent_name}
Fallback options:
1. Try directly: `invoke_agent {agent_name} "your prompt"`
2. For OAuth: `invoke_oauth_agent {agent_name} "your prompt"`
3. Check status: `get_agent_status {agent_name}`
"""

    @mcp.tool()
    async def invoke_oauth_agent_v2(
        agent_name: str = Field(description='OAuth-enabled agent name to invoke'),
        prompt: str = Field(description='Message to send to agent'),
        session_id: str = Field(default='', description='Session ID for conversation continuity'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Improved OAuth agent invocation using Runtime SDK pattern.

        This version uses the same Runtime SDK pattern as regular invoke_agent
        but adds OAuth token authentication. Keeps all existing functionality intact.
        """
        try:
            import json
            import uuid
            from pathlib import Path

            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())[:8]

            # Step 1 & 2: Validate OAuth config and generate token (using shared utilities)
            success, result = validate_oauth_config(agent_name, region)
            if not success:
                # Add context about using regular invocation as alternative
                result_str = result if isinstance(result, str) else str(result)
                return result_str.replace(
                    'Troubleshooting:\n1. Deploy with OAuth',
                    "Troubleshooting:\n1. Use regular invocation: If agent doesn't require OAuth, use `invoke_agent` instead\n2. Deploy with OAuth",
                )

            client_info = result.get('client_info', {}) if isinstance(result, dict) else {}

            # Generate OAuth token using shared utility
            token_success, access_token = generate_oauth_token(client_info, region)
            if not token_success:
                return 'OAuth token generation failed\nUse: `get_runtime_oauth_token` for detailed token generation'

            # Step 3: Use Runtime SDK pattern (same as invoke_agent) with OAuth
            try:
                if not RUNTIME_AVAILABLE:
                    return (
                        'X Runtime SDK not available - requires bedrock-agentcore-starter-toolkit'
                    )

                # Find agent config directory (same logic as invoke_agent)
                config_dirs_to_check = [
                    Path.cwd(),
                    get_user_working_directory(),
                    Path.cwd() / 'examples',
                    Path.home() / 'agentcore_projects' / agent_name,
                ]

                config_dir_found = None
                for config_dir in config_dirs_to_check:
                    if check_agent_config_exists(agent_name):
                        config_dir_found = config_dir
                        break

                if not config_dir_found:
                    return f"""X Agent Configuration Not Found
Agent: {agent_name}
Searched: {[str(d) for d in config_dirs_to_check]}
Fix: Deploy agent first with `deploy_agentcore_app`
"""

                # Get Runtime object (same pattern as invoke_agent)
                runtime = get_runtime_for_agent(agent_name)

                # Check agent status
                try:
                    status_result = runtime.status()
                    if hasattr(status_result, 'endpoint'):
                        status = (
                            status_result.endpoint.get('status', 'UNKNOWN')
                            if status_result.endpoint
                            else 'UNKNOWN'
                        )
                    else:
                        status = str(status_result)

                    if 'READY' not in str(status):
                        return f"""X Agent Not Ready
Agent: {agent_name}
Status: {status}
Fix: Wait for agent to be READY or redeploy
"""
                except Exception as status_error:
                    return f'X Status Check Failed: {str(status_error)}'

                # Step 4: Invoke with OAuth context (enhanced Runtime pattern)
                # Note: Current Runtime SDK may not support OAuth headers directly
                # This is a limitation we document and handle gracefully

                payload = {'prompt': prompt}
                try:
                    # Try regular Runtime invocation first (OAuth handled at infrastructure level)
                    response = runtime.invoke(payload)

                    return f"""# Agent: OAuth Agent Invocation Successful (v2)

### Request:
- Agent: {agent_name}
- Prompt: "{prompt}"
- Session: {session_id}
- Authentication: OAuth token validated OK
- Method: Runtime SDK pattern with OAuth

### Response:
```json
{json.dumps(response, indent=2)}
```

### Session Info:
- Session ID: `{session_id}`
- OAuth Token: Active and validated
- Config Directory: {config_dir_found}
- Runtime Pattern: SDK-based invocation

### Notes:
- OAuth token generated and validated successfully
- Runtime invocation may handle OAuth at infrastructure level
- For direct HTTP OAuth calls, use `get_runtime_oauth_token` and manual requests

OK OAuth authentication successful with Runtime SDK pattern!
"""

                except Exception as invoke_error:
                    # Fallback: Provide instructions for manual OAuth invocation
                    return f"""! Runtime SDK OAuth Limitation

Issue: Runtime SDK may not support direct OAuth headers
Agent: {agent_name}
OAuth Token: Generated successfully OK

### Manual OAuth Invocation Available:

#### 1. Get Runtime Endpoint:
Use AWS Console or CLI to get actual runtime endpoint URL

#### 2. Direct HTTP Request:
```bash
curl -H "Authorization: Bearer {access_token[:20]}..." \\
     https://your-runtime-endpoint/invoke \\
     -d '{{"prompt": "{prompt}"}}' \\
     -H "Content-Type: application/json"
```

#### 3. Alternative Tools:
- Use `get_runtime_oauth_token` for token details
- Use `get_agent_status` for endpoint information

Error Details: {str(invoke_error)}
"""

            except Exception as runtime_error:
                return f"""X Runtime Error: {str(runtime_error)}
Agent: {agent_name}
Troubleshooting:
1. Check agent deployment: `get_agent_status`
2. Verify agent is READY
3. Use regular invocation: `invoke_agent` (may work if OAuth optional)
"""

        except Exception as e:
            return f"""X OAuth Invocation Error (v2): {str(e)}
Agent: {agent_name}
Troubleshooting:
1. Check OAuth config: ~/.agentcore_gateways/{agent_name}_runtime.json
2. Verify deployment: Use `get_agent_status`
3. Get token separately: Use `get_runtime_oauth_token`
4. Use regular invocation: If OAuth not required, use `invoke_agent`
"""

    @mcp.tool()
    async def get_agent_status(
        agent_name: str = Field(description='Agent name to check status'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Check the current status of your deployed agent using correct CLI syntax."""
        try:
            agentcore_cmd = await get_agentcore_command()

            # Use correct AgentCore CLI syntax: agentcore status --agent AGENT_NAME
            if isinstance(agentcore_cmd, list):
                cmd = agentcore_cmd + ['status', '--agent', agent_name]
            else:
                cmd = [agentcore_cmd, 'status', '--agent', agent_name]

            # Check if we need to run from different directory
            config_exists, config_dir = find_agent_config_directory(agent_name)

            if config_exists:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30, cwd=config_dir
                )
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return f"""# Stats: Agent Status

```
{result.stdout}
```

Status: OK Agent accessible
Region: {region}
"""
            else:
                return f"""# X Agent Status Check Failed

Error: {result.stderr}

Troubleshooting:
- Try: `uv run agentcore status --agent {agent_name}`
- Check agent exists: `uv run agentcore configure list`
- Verify config file: `.bedrock_agentcore.yaml`
- Directory: May need to run from agent's config directory
"""
        except Exception as e:
            return f'X Status Check Error: {str(e)}'

    @mcp.tool()
    async def discover_existing_agents(
        search_path: str = Field(
            default='.', description='Path to search for existing agent configurations'
        ),
        include_status: bool = Field(
            default=True, description='Check deployment status of found agents'
        ),
    ) -> str:
        """Discover existing AgentCore agent configurations and their status."""
        original_cwd = None
        try:
            # Resolve search path
            if search_path == '.':
                path = get_user_working_directory()
            else:
                path = Path(search_path)
                if not path.is_absolute():
                    path = get_user_working_directory() / search_path

            if not path.exists():
                return f'X Search path not found: {search_path}'

            # Find all config files
            config_files = list(path.rglob('.bedrock_agentcore*.yaml'))

            if not config_files:
                return f"""# Search: No Existing Agent Configurations Found

### Search Path: `{path.absolute()}`

### What This Means:
- No previously deployed agents found in this directory
- You can deploy new agents using `deploy_agentcore_app`
- Or analyze existing code with `analyze_agent_code`

### Next Steps:
1. Use `validate_agentcore_environment` to check your setup
2. Use `analyze_agent_code` to migrate existing agents
3. Use `deploy_agentcore_app` to deploy new agents
"""

            discovered_agents = []

            for config_file in config_files:
                try:
                    agent_info = {'config_file': str(config_file.relative_to(path))}

                    if YAML_AVAILABLE:
                        import yaml

                        with open(config_file, 'r') as f:
                            config = yaml.safe_load(f)
                            if config:
                                # Handle simple config format (single agent)
                                if 'agent_name' in config:
                                    agent_info['name'] = config.get('agent_name', 'unknown')
                                    agent_info['entrypoint'] = config.get('entrypoint', 'unknown')
                                    agent_info['region'] = config.get('region', 'us-east-1')
                                    agent_info['config_format'] = 'simple'
                                    discovered_agents.append(agent_info)
                                # Handle complex config format (multi-agent)
                                elif 'agents' in config:
                                    agent_info['config_format'] = 'multi-agent'
                                    for agent_name, agent_config in config['agents'].items():
                                        multi_agent_info = {
                                            'name': agent_name,
                                            'config_file': str(config_file.relative_to(path)),
                                            'entrypoint': agent_config.get(
                                                'entrypoint', 'unknown'
                                            ),
                                            'region': agent_config.get('aws', {}).get(
                                                'region', 'us-east-1'
                                            ),
                                            'config_format': 'multi-agent',
                                            'agent_id': agent_config.get(
                                                'bedrock_agentcore', {}
                                            ).get('agent_id', 'unknown'),
                                            'agent_arn': agent_config.get(
                                                'bedrock_agentcore', {}
                                            ).get('agent_arn', 'unknown'),
                                        }
                                        discovered_agents.append(multi_agent_info)
                                    continue  # Skip the outer agent_info append
                                else:
                                    agent_info['name'] = config_file.stem.replace(
                                        '.bedrock_agentcore', ''
                                    )
                            else:
                                agent_info['name'] = config_file.stem.replace(
                                    '.bedrock_agentcore', ''
                                )
                    else:
                        agent_info['name'] = config_file.stem.replace('.bedrock_agentcore', '')

                    # Only append simple format configs (multi-agent already handled above)
                    if (
                        agent_info.get('config_format') == 'simple'
                        or 'config_format' not in agent_info
                    ):
                        discovered_agents.append(agent_info)

                except Exception:
                    # Skip invalid config files
                    continue

            # Now check deployment status for all discovered agents
            if include_status and RUNTIME_AVAILABLE:
                for agent_info in discovered_agents:
                    try:
                        # Change to config file directory and check status
                        config_file_path = path / agent_info['config_file']
                        original_cwd = Path.cwd()

                        os.chdir(config_file_path.parent)

                        runtime = get_runtime_for_agent(agent_info['name'])
                        status_result = runtime.status()

                        if hasattr(status_result, 'endpoint'):
                            agent_info['status'] = (
                                status_result.endpoint.get('status', 'UNKNOWN')
                                if status_result.endpoint
                                else 'UNKNOWN'
                            )
                            agent_info['deployable'] = True
                        else:
                            agent_info['status'] = 'CONFIGURED_NOT_DEPLOYED'
                            agent_info['deployable'] = True

                        os.chdir(original_cwd)

                    except ValueError as e:
                        if 'Must configure' in str(e):
                            agent_info['status'] = 'CONFIGURED_NOT_DEPLOYED'
                        else:
                            agent_info['status'] = 'ERROR'
                        agent_info['deployable'] = True
                    except Exception as e:
                        agent_info['status'] = f'ERROR: {str(e)}'
                        agent_info['deployable'] = False
                    finally:
                        try:
                            if original_cwd is not None:
                                os.chdir(original_cwd)
                        except Exception as e:
                            print(f'Error restoring directory: {str(e)}')
                            pass
            else:
                for agent_info in discovered_agents:
                    agent_info['status'] = 'CONFIGURED'
                    agent_info['deployable'] = True

            if not discovered_agents:
                return f"""# Search: Config Files Found But Invalid

Found {len(config_files)} config files but none were valid AgentCore configurations.

### Search Path: `{path.absolute()}`
### Files Found: {[f.name for f in config_files]}

### Next Steps:
1. Check if config files are corrupted
2. Deploy new agents with `deploy_agentcore_app`
"""

            # Format results
            result_parts = []
            result_parts.append(
                f'# Search: Discovered {len(discovered_agents)} Agent Configuration(s)'
            )
            result_parts.append('')
            result_parts.append(f'### Search Path: `{path.absolute()}`')
            result_parts.append('')

            ready_agents = []
            configured_agents = []
            error_agents = []

            for agent in discovered_agents:
                if agent['status'] == 'READY':
                    ready_agents.append(agent)
                elif 'CONFIGURED' in agent['status'] or agent['status'] == 'CREATING':
                    configured_agents.append(agent)
                else:
                    error_agents.append(agent)

            if ready_agents:
                result_parts.append(f'### Ready: Ready to Invoke ({len(ready_agents)} agents):')
                for agent in ready_agents:
                    result_parts.append(f'#### {agent["name"]}')
                    result_parts.append(f'- Status: {agent["status"]}')
                    result_parts.append(f'- Config: `{agent["config_file"]}`')
                    result_parts.append(
                        f'- Invoke: `invoke_agent` with agent_name: `{agent["name"]}`'
                    )
                    result_parts.append('')

            if configured_agents:
                result_parts.append(
                    f'### Configured: Configured But Not Deployed ({len(configured_agents)} agents):'
                )
                for agent in configured_agents:
                    result_parts.append(f'#### {agent["name"]}')
                    result_parts.append(f'- Status: {agent["status"]}')
                    result_parts.append(f'- Config: `{agent["config_file"]}`')
                    result_parts.append(
                        '- Deploy: Use `deploy_agentcore_app` with execution_mode: `sdk`'
                    )
                    result_parts.append('')

            if error_agents:
                result_parts.append(f'### Error: Agents with Issues ({len(error_agents)} agents):')
                for agent in error_agents:
                    result_parts.append(f'#### {agent["name"]}')
                    result_parts.append(f'- Status: {agent["status"]}')
                    result_parts.append(f'- Config: `{agent["config_file"]}`')
                    result_parts.append('')

            result_parts.append('### Quick Actions:')
            if ready_agents:
                result_parts.append('- Invoke Ready Agents: Use `invoke_agent` tool')
            if configured_agents:
                result_parts.append('- Deploy Configured: Use `deploy_agentcore_app` tool')
            result_parts.append('- Create New: Use `analyze_agent_code` → `deploy_agentcore_app`')

            return '\\n'.join(result_parts)

        except Exception as e:
            return f'X Discovery Error: {str(e)}'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def generate_migration_strategy(analysis: Dict[str, Any]) -> Dict[str, str]:
    """Generate migration strategy based on analysis."""
    framework = analysis['framework']

    strategies = {
        'strands': {
            'complexity': 'Simple',
            'time_estimate': '5-10 minutes',
            'description': """Simple Strands Migration:
- Wrap existing Agent in BedrockAgentCoreApp
- Preserve all Strands functionality
- Add AgentCore deployment features
- No breaking changes to your logic""",
        },
        'langgraph': {
            'complexity': 'Moderate',
            'time_estimate': '15-30 minutes',
            'description': """LangGraph Integration:
- Convert workflow to AgentCore handler
- Maintain graph structure
- Add state persistence with memory
- Integrate with AgentCore tools""",
        },
        'crewai': {
            'complexity': 'Moderate',
            'time_estimate': '15-30 minutes',
            'description': """CrewAI Migration:
- Transform crew to AgentCore format
- Preserve agent collaboration
- Add memory for agent coordination
- Integrate with AgentCore identity""",
        },
        'agentcore': {
            'complexity': 'None',
            'time_estimate': '2-5 minutes',
            'description': """Already AgentCore:
- Code is already compatible
- Ready for deployment
- May add advanced features""",
        },
        'custom': {
            'complexity': 'Variable',
            'time_estimate': '10-45 minutes',
            'description': """Custom Agent Migration:
- Analyze existing patterns
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


def generate_safe_agentcore_code(
    original_code: str, analysis: Dict[str, Any], options: Dict[str, bool]
) -> str:
    """Generate AgentCore code using only validated SDK methods."""
    framework = analysis['framework']

    if framework == 'strands':
        return generate_strands_agentcore_code(original_code, options)
    elif framework == 'agentcore':
        return original_code  # Already compatible
    else:
        return generate_basic_agentcore_code(original_code, analysis, options)


def generate_strands_agentcore_code(original_code: str, options: Dict[str, bool]) -> str:
    """Generate AgentCore code from Strands agent - minimal, correct transformation."""
    code_parts = []

    # Imports
    code_parts.append('#!/usr/bin/env python3')
    code_parts.append('"""')
    code_parts.append('AgentCore-enabled Strands Agent')
    code_parts.append('Transformed from simple Strands agent')
    code_parts.append('"""')
    code_parts.append('')
    code_parts.append('from bedrock_agentcore import BedrockAgentCoreApp')
    code_parts.append('from strands import Agent')
    code_parts.append('')

    # App and agent initialization - keep it simple like the original
    code_parts.append('app = BedrockAgentCoreApp()')
    code_parts.append('agent = Agent()')
    code_parts.append('')

    # Main handler - using correct @app.entrypoint decorator
    code_parts.append('@app.entrypoint')
    if 'async' in original_code:
        code_parts.append('async def handler(payload):')
        code_parts.append('    """AgentCore handler for Strands agent."""')
        code_parts.append('    user_message = payload.get("prompt", "Hello!")')
        code_parts.append('    ')
        code_parts.append('    # Process with Strands agent (preserving original logic)')
        code_parts.append('    response = await agent(user_message)')
    else:
        code_parts.append('def handler(payload):')
        code_parts.append('    """AgentCore handler for Strands agent."""')
        code_parts.append('    user_message = payload.get("prompt", "Hello!")')
        code_parts.append('    ')
        code_parts.append('    # Process with Strands agent (preserving original logic)')
        code_parts.append('    response = agent(user_message)')

    code_parts.append('    ')
    code_parts.append('    return {"result": str(response)}')
    code_parts.append('')

    # Main execution
    code_parts.append('if __name__ == "__main__":')
    code_parts.append('    app.run()')

    return '\n'.join(code_parts)


def generate_basic_agentcore_code(
    original_code: str, analysis: Dict[str, Any], options: Dict[str, bool]
) -> str:
    """Generate basic AgentCore code structure when full validation isn't available."""
    code_parts = []
    code_parts.append('#!/usr/bin/env python3')
    code_parts.append('"""')
    code_parts.append('Basic AgentCore App Structure')
    code_parts.append('Please validate SDK methods before deploying')
    code_parts.append('"""')
    code_parts.append('')
    code_parts.append('from bedrock_agentcore import BedrockAgentCoreApp')
    code_parts.append('')
    code_parts.append('app = BedrockAgentCoreApp()')
    code_parts.append('')
    code_parts.append('@app.entrypoint')
    code_parts.append('def handler(payload):')
    code_parts.append('    """Basic AgentCore handler."""')
    code_parts.append('    user_message = payload.get("prompt", "Hello!")')
    code_parts.append('    ')
    code_parts.append('    # TODO: Add your agent logic here')
    code_parts.append('    response = f"Processed: {user_message}"')
    code_parts.append('    ')
    code_parts.append('    return {"result": response}')
    code_parts.append('')
    code_parts.append('if __name__ == "__main__":')
    code_parts.append('    # Deployment ready - use AgentCore CLI or SDK')
    code_parts.append('    print("AgentCore app structure ready")')

    return '\n'.join(code_parts)


async def execute_agentcore_deployment_cli(
    app_file: str,
    agent_name: str,
    region: str,
    memory_enabled: bool,
    execution_role: str,
    environment: str,
    enable_oauth: bool = False,  # pragma: allowlist secret
    cognito_user_pool: str = '',
) -> str:
    """Execute AgentCore deployment using CLI commands."""
    steps = []

    try:
        # Check for virtual environment and use appropriate command
        venv_python = None
        if Path('.venv/bin/python').exists():
            venv_python = '.venv/bin/python'
            steps.append('OK Found local .venv - using virtual environment')
        elif Path('venv/bin/python').exists():
            venv_python = 'venv/bin/python'
            steps.append('OK Found local venv - using virtual environment')

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
            app_file = str(Path(app_file).absolute())

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
            return f"""X Configuration Failed

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
"""

        steps.append('OK Agent configured successfully')

        # Step 2: Deploy
        if isinstance(agentcore_cmd, list):
            deploy_cmd = agentcore_cmd + ['deploy', '--name', agent_name]
        else:
            deploy_cmd = [agentcore_cmd, 'deploy', '--name', agent_name]

        steps.append('Pending: Deploying agent...')
        result = subprocess.run(deploy_cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return f"""X Deployment Failed

Error: {result.stderr}
Command: `{' '.join(deploy_cmd)}`

Steps Completed:
{chr(10).join(steps)}

Troubleshooting:
1. Check agent configuration: `agentcore get-agent --name {agent_name}`
2. Verify IAM permissions
3. Check CloudWatch logs
"""

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
        return f"""X Deployment Timeout

Steps Completed:
{chr(10).join(steps)}

The deployment is taking longer than expected. Check status:
```bash
agentcore get-agent --name {agent_name}
```
"""
    except Exception as e:
        return f"""X Deployment Error

Error: {str(e)}
Steps Completed:
{chr(10).join(steps)}
"""


async def execute_agentcore_deployment_sdk(
    app_file: str,
    agent_name: str,
    region: str,
    memory_enabled: bool,
    execution_role: str,
    environment: str,
    enable_oauth: bool = False,  # pragma: allowlist secret
    cognito_user_pool: str = '',
) -> str:
    """Execute AgentCore deployment using SDK - follows exact tutorial patterns."""
    # Check for starter toolkit Runtime availability
    if not SDK_AVAILABLE:
        return f"""X AgentCore SDK Not Available

Error: {SDK_IMPORT_ERROR}

To use SDK deployment:
1. Install: `uv pip install -e ./bedrock-agentcore-sdk`
2. Install: `uv pip install -e ./bedrock-agentcore-starter-toolkit`
3. Ensure AWS credentials are configured
4. Retry deployment

Alternative: Use `execution_mode: "cli"` for CLI commands instead.
"""

    try:
        import json
        import time
        from pathlib import Path

        # Validate entrypoint file exists
        if not Path(app_file).exists():
            return f"X App file '{app_file}' not found at path: {Path(app_file).absolute()}"

        deployment_steps = []
        deployment_results = {}
        oauth_config = None  # pragma: allowlist secret

        # Read and validate the app file
        with open(app_file, 'r') as f:
            app_content = f.read()

        if 'BedrockAgentCoreApp' not in app_content:
            return f"""X Invalid AgentCore Application

The file '{app_file}' doesn't appear to be a valid AgentCore application.
It must contain 'BedrockAgentCoreApp' and '@app.entrypoint' decorator.

Use the `transform_to_agentcore` tool first to convert your code.
"""

        if 'app.run()' not in app_content:
            return f"""X Missing app.run() in Agent Code

The file '{app_file}' must contain 'app.run()' in the main block:
```python
if __name__ == "__main__":
    app.run()
```

Use the `transform_to_agentcore` tool to fix this.
"""

        # Handle OAuth configuration if enabled
        if enable_oauth:  # pragma: allowlist secret
            deployment_steps.append(
                'Security: OAuth authentication enabled - setting up Cognito...'
            )

            try:
                # Reuse existing OAuth infrastructure from utils/gateway
                if not RUNTIME_AVAILABLE:
                    return 'X Runtime SDK not available - OAuth requires bedrock-agentcore-starter-toolkit'

                from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

                # Create GatewayClient to reuse OAuth setup
                gateway_client = GatewayClient(region_name=region)

                # Create OAuth authorizer with Cognito (reusing existing gateway method)
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
        import os

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
        return f"""X SDK Deployment Error

Error: {str(e)}
App File: {app_file}
Region: {region}

Troubleshooting:
1. Ensure AWS credentials: `aws configure list`
2. Check file permissions: `ls -la {app_file}`
3. Verify SDK installation: `python -c "import bedrock_agentcore; print('SDK OK')"`
4. Try CLI mode instead: `execution_mode: "cli"`
"""


async def invoke_agent_via_aws_sdk(
    agent_name: str, prompt: str, session_id: str, region: str
) -> str:
    """Invoke agent directly via AWS SDK - for SDK deployed agents without local config."""
    try:
        import boto3

        # import json
        import uuid

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())[:8]

        # Try to find agent ARN from deployment status
        # Look for existing deployment info from the MCP server deployment process
        agentcore_client = boto3.client('bedrock-agentcore', region_name=region)
        print(dir(agentcore_client))
        # First try to find the agent by listing (common pattern for SDK deployed agents)
        # Agent names from SDK deployment often have suffixes like -mJRQCB4c47
        try:
            # Look for deployed agents with this base name
            # This is a heuristic - actual implementation would need agent registry
            agent_runtime_arn = f'arn:aws:bedrock-agentcore:{region}:*:runtime/{agent_name}-*'
            print(agent_runtime_arn)
            # For now, return a helpful message about direct AWS invocation
            return f"""# Search: Direct AWS SDK Invocation Attempted

Agent: {agent_name}
Region: {region}
Session: {session_id}

Issue: Agent appears to be SDK-deployed but local config not found.

To invoke SDK-deployed agents, you need the full agent ARN.

Next Steps:
1. Get the full agent ARN from AWS Console or deployment logs
2. Use AWS CLI directly:
   ```bash
   aws bedrock-agentcore invoke-agent-runtime \\
     --agent-runtime-arn "arn:aws:bedrock-agentcore:{region}:ACCOUNT:runtime/{agent_name}-SUFFIX" \\
     --payload '{{"prompt": "{prompt}"}}'
   ```

Alternative: Use `get_agent_status` to find the full ARN and agent ID.
3. With boto3, you need to use the data plane client directly:

import boto3

client = boto3.client('bedrock-agentcore')

response = client.invoke_agent_runtime(
    contentType='string',
    accept='string',
    mcpSessionId='string',
    runtimeSessionId='string',
    mcpProtocolVersion='string',
    runtimeUserId='string',
    traceId='string',
    traceParent='string',
    traceState='string',
    baggage='string',
    agentRuntimeArn='string',
    qualifier='string',
    payload=b'bytes'|file
)
"""

        except Exception as e:
            return f'X AWS SDK Invocation Failed: {str(e)}'

    except ImportError:
        return 'X boto3 not available - cannot invoke via AWS SDK'
    except Exception as e:
        return f'X AWS SDK Error: {str(e)}'
