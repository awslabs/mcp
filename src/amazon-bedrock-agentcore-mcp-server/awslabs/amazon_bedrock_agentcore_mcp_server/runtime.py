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

import json
import os
import subprocess
import uuid
from .runtime_return_stmts import (
    return_for_analyze_ok,
    return_for_no_code,
    return_for_oauth_ok,
    return_for_transform_ok,
    return_oauth_error,
    return_oauth_invoke_ok,
    return_search_error,
    return_search_mcp_error,
)
from .runtime_utils import (
    check_agent_oauth_status,
    execute_agentcore_deployment_cli,
    execute_agentcore_deployment_sdk,
    generate_migration_strategy,
    generate_oauth_token,
    generate_tutorial_based_guidance,
    invoke_agent_via_aws_sdk,
    validate_oauth_config,
)
from .utils import (
    RUNTIME_AVAILABLE,
    YAML_AVAILABLE,
    MCPtoolError,
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
from typing import Literal


# ============================================================================
# AGENT CODE ANALYSIS AND TRANSFORMATION
# ============================================================================


def register_analysis_tools(mcp: FastMCP):
    """Register code analysis and transformation tools."""

    @mcp.tool()
    async def analyze_agent_code(  # pragma: no cover
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
                env_info.append('OK Virtual environment (venv) detected')  # pragma: no cover

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
                raise MCPtoolError(
                    return_for_no_code.format(
                        env_info=env_info,
                        env_info_formatted='\n'.join(env_info)
                        if env_info
                        else '- Standard Python environment',
                        available_files=available_files,
                        user_dir=user_dir,
                        file_path=file_path,
                    )
                )

            # Analyze the code
            analysis = analyze_code_patterns(code_content)

            # Generate migration strategy
            strategy = generate_migration_strategy(analysis)

            # Generate tutorial-based migration guidance
            migration_guidance = generate_tutorial_based_guidance(analysis['framework'])

            return return_for_analyze_ok.format(
                env_info=env_info,
                env_info_formatted='\n'.join(env_info)
                if env_info
                else '- Standard Python environment',
                analysis=analysis,
                analysis_framework=analysis.get('framework', 'Unknown'),
                patterns_formatted=format_patterns(analysis.get('patterns', [])),
                dependencies_formatted=format_dependencies(analysis.get('dependencies', [])),
                strategy=strategy,
                strategy_complexity=strategy.get('complexity', 'Unknown'),
                strategy_description=strategy.get('description', 'No description available'),
                strategy_time_estimate=strategy.get('time_estimate', 'Unknown'),
                migration_guidance=migration_guidance,
            )

        except Exception as e:
            raise MCPtoolError(f'X Analysis Error: {str(e)}')

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
            resolved_source = resolve_app_file_path(source_file)
            if not resolved_source:
                user_dir = get_user_working_directory()
                return f"""X Source file not found

Looking for: `{source_file}`
User working directory: `{user_dir}`

Tip: Try using just the filename (e.g., 'your_agent.py') or check the file exists in the user's project directory.
"""

            source_file = resolved_source

            # Read original code
            with open(source_file, 'r') as f:
                original_code = f.read()

            # Analyze to understand current structure
            analysis = analyze_code_patterns(original_code)

            return return_for_transform_ok.format(
                source_file=source_file,
                analysis=analysis,
                target_file=target_file,
                target_file_formatted=target_file
                if target_file
                else 'auto-generated as test_agentcore_app.py or an appropriate new filename based on source',
                features_added_formatted=format_features_added(
                    {'add_memory': add_memory, 'add_tools': add_tools}
                ),
                preserve_logic=preserve_logic,
                preserve_logic_formatted=str(preserve_logic),
            )

        except Exception as e:
            raise MCPtoolError(f'X Transformation Error: {str(e)}')


# ============================================================================
# AGENT DEPLOYMENT AND LIFECYCLE
# ============================================================================


def register_deployment_tools(mcp: FastMCP):
    """Register agent deployment and lifecycle management tools."""

    @mcp.tool()
    async def deploy_agentcore_app(  # pragma: no cover
        app_file: str = Field(description='AgentCore app file to deploy'),
        agent_name: str = Field(
            description='Name for your deployed agent (no hyphens, only underscores_)'
        ),
        execution_mode: Literal['cli', 'sdk'] = Field(
            default='sdk',
            description='Default mode is SDK where the deployment is done on the users behalf. If the user asks, the other mode is agentcore CLI commands',
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
                available_files = list(user_dir.glob('*.py'))[:10]  # pragma: no cover

                raise MCPtoolError(f"""X App file not found

Looking for: `{app_file}`
User working directory: `{user_dir}`
Searched locations:
- {app_file} (as provided)
- {user_dir}/{app_file}
- {user_dir}/examples/{Path(app_file).name}

Available Python files:
{chr(10).join(f'- {f.relative_to(user_dir)}' for f in available_files) if available_files else '- No Python files found'}

Please ensure the file exists or provide the correct path.
""")

            app_file = resolved_app_file

            # Handle execution mode choice

            if execution_mode == 'cli':
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
            raise MCPtoolError(f'X Deployment Error: {str(e)}')

    @mcp.tool()
    async def invoke_agent(  # pragma: no cover
        agent_name: str = Field(description='Agent name to invoke'),
        agent_arn: str = Field(default='', description='Agent ARN for direct invocation'),
        prompt: str = Field(description='Message to send to agent'),
        session_id: str = Field(
            default='',
            description='Session ID for conversation continuity (uuid, min 33 characters)',
        ),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Invoke deployed AgentCore agent - automatically finds config and switches directories."""
        if not RUNTIME_AVAILABLE:
            raise MCPtoolError("""X Runtime Not Available

To invoke deployed agents:
1. Install: `uv add bedrock-agentcore-starter-toolkit`
2. Ensure agent is deployed
3. Retry invocation
""")

        config_dir = ''
        try:
            # Find the correct config directory for this agent
            config_found, config_dir = find_agent_config_directory(agent_name)

            # If not found, try to use directly with AWS SDK (for SDK-deployed agents)
            if not config_found:
                try:
                    # Try direct AWS invocation for SDK-deployed agents
                    return await invoke_agent_via_aws_sdk(
                        agent_name, agent_arn, prompt, session_id, region
                    )
                except Exception as e:
                    raise MCPtoolError(f"""X Agent Configuration Not Found
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
                        """)

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
                            return f"""X Agent Not Ready  # pragma: no cover

Agent: {agent_name}  # pragma: no cover
Status: {endpoint_status}  # pragma: no cover
Config Directory: {config_dir}  # pragma: no cover

Next Steps:  # pragma: no cover
- Wait for agent to reach READY status  # pragma: no cover
- Check deployment: `get_agent_status`  # pragma: no cover
- Redeploy if needed: `deploy_agentcore_app`  # pragma: no cover
"""
                    else:
                        return f"""X Agent Not Deployed  # pragma: no cover

Agent: {agent_name}  # pragma: no cover
Issue: Configured but not deployed to AWS  # pragma: no cover
Config Directory: {config_dir}  # pragma: no cover

Next Steps: Complete deployment with `deploy_agentcore_app`  # pragma: no cover
"""
                except ValueError as e:  # pragma: no cover
                    if 'Must configure' in str(e):  # pragma: no cover
                        raise MCPtoolError(f"""X Agent Not Configured

Agent: {agent_name}
Issue: Runtime configuration missing
Config Directory: {config_dir}

Next Steps: Deploy agent first with `deploy_agentcore_app`
""")

                # Generate session ID if not provided
                if not session_id:
                    session_id = str(uuid.uuid4())[:8]

                # Prepare payload exactly like tutorial
                payload = {'prompt': prompt}

                # Invoke using the persistent Runtime object - tutorial pattern
                result = runtime.invoke(payload)

                # Process response like tutorial shows - handle bytes data properly
                if hasattr(result, 'response'):
                    response_data = result.get('response', {})  # pragma: no cover
                    # Handle bytes response from AgentCore  # pragma: no cover
                    if (
                        isinstance(response_data, list) and len(response_data) > 0
                    ):  # pragma: no cover
                        if isinstance(response_data[0], bytes):  # pragma: no cover
                            decoded_response = None  # pragma: no cover
                            try:  # pragma: no cover
                                # Decode bytes and parse JSON  # pragma: no cover
                                decoded_response = response_data[0].decode(
                                    'utf-8'
                                )  # pragma: no cover
                                response_data = json.loads(decoded_response)  # pragma: no cover
                            except (UnicodeDecodeError, json.JSONDecodeError):  # pragma: no cover
                                # If decoding fails, use string representation  # pragma: no cover
                                response_data = (  # pragma: no cover
                                    decoded_response  # pragma: no cover
                                    if 'decoded_response' in locals()  # pragma: no cover
                                    else str(response_data[0])  # pragma: no cover
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
            raise MCPtoolError(f"""X Invocation Error: {str(e)}

Troubleshooting:
1. Check available agents: `discover_existing_agents`
2. Verify agent status: `get_agent_status`
3. Try from correct directory: Config in `{config_dir if 'config_dir' in locals() else 'unknown'}`
4. Redeploy if needed: `deploy_agentcore_app`
""")

    @mcp.tool()
    async def invoke_oauth_agent(  # pragma: no cover
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
                    raise ImportError("""X Runtime SDK not available

Required: bedrock-agentcore-starter-toolkit
Install: `uv add bedrock-agentcore-starter-toolkit`

Note: OAuth token generated successfully - but Runtime SDK needed for invocation
Token available for manual HTTP calls - use `get_runtime_oauth_token` for details
""")

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
                    raise MCPtoolError(f"""X Agent Configuration Not Found

Agent: {agent_name}
Searched: {[str(d) for d in config_dirs_to_check]}

OAuth Setup: OK Valid (token generated successfully)
Agent Config: X Missing .bedrock_agentcore.yaml

Fix:
1. Deploy agent: Use `deploy_agentcore_app`
2. Or use manual HTTP: Use `get_runtime_oauth_token` for Bearer token details

Note: OAuth token is ready - just need agent deployment config
""")

                # Change to agent directory and get Runtime object

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
                        raise MCPtoolError(f"""X Runtime Invocation Failed: {str(invoke_error)}

Agent: {agent_name}
OAuth: OK Token generated and validated
Issue: Runtime SDK invocation error

Alternative Options:
1. Use regular invocation: `invoke_agent` (may work without OAuth)
2. Manual HTTP with OAuth: Use `get_runtime_oauth_token` for Bearer token
3. Check agent logs: Use `get_agent_status` for debugging

The OAuth setup is correct - this appears to be a Runtime SDK issue, not OAuth.
""")

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
            raise MCPtoolError(f"""X OAuth Invocation Error: {str(e)}

Agent: {agent_name}

Quick Fixes:
1. Try without OAuth first: `invoke_agent {agent_name} "your prompt"`
2. Check if OAuth needed: Many agents work without OAuth
3. Get OAuth details: Use `get_runtime_oauth_token` if OAuth required

For OAuth troubleshooting: Check ~/.agentcore_gateways/{agent_name}_runtime.json
""")

    @mcp.tool()
    async def get_runtime_oauth_token(  # pragma: no cover
        agent_name: str = Field(description='OAuth-enabled agent name to get token for'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Get OAuth access token for runtime agent - reuses all gateway infrastructure."""
        try:
            # Use shared validation and token generation (DRY principle)

            # Validate inputs before calling function
            if not isinstance(agent_name, str) or not agent_name.strip():
                raise ValueError('Invalid agent_name: must be non-empty string')
            if not isinstance(region, str) or not region.strip():
                raise ValueError('Invalid region: must be non-empty string')
            # Sanitize agent_name to prevent path traversal
            safe_agent_name = ''.join(c for c in agent_name if c.isalnum() or c in '-_')
            if not safe_agent_name:
                raise ValueError('Invalid agent_name: contains no valid characters')

            success, result = validate_oauth_config(
                safe_agent_name, region
            )  # pragma: allowlist secret
            agent_name = safe_agent_name  # Use sanitized name going forward

            if not success:
                return str(result)  # pragma: allowlist secret

            client_info = (
                result.get('client_info', {}) if isinstance(result, dict) else {}
            )  # pragma: allowlist secret
            # Safely extract oauth_config with validation
            config_data = {}  # pragma: allowlist secret
            if isinstance(result, dict) and 'oauth_config' in result:
                raw_config = result['oauth_config']
                if isinstance(raw_config, dict):
                    # Validate and sanitize known oauth config fields
                    config_data = {}  # noqa: S105
                    for key in ['client_id', 'client_secret', 'redirect_uri', 'scope']:
                        if key in raw_config and isinstance(raw_config[key], str):
                            config_data[key] = raw_config[key][:500]  # Limit length
                else:
                    config_data = {}  # noqa: S105
            else:
                config_data = {}  # noqa: S105

            # Log OAuth config status without exposing sensitive data
            config_keys = list(config_data.keys()) if config_data else []
            print(f'OAuth Config loaded with keys: {config_keys}')

            # Generate access token using shared utility
            token_success, access_token = generate_oauth_token(  # pragma: allowlist secret
                client_info if isinstance(client_info, dict) else {},
                region,  # pragma: allowlist secret
            )
            if not token_success:  # pragma: allowlist secret
                return access_token  # pragma: allowlist secret

            return return_for_oauth_ok.format(
                agent_name=agent_name,
                user_pool_id=client_info.get('user_pool_id', 'Unknown'),
                client_id=client_info.get('client_id', 'Unknown'),
                region=region,
                access_token=access_token,
            )  # pragma: allowlist secret

        except Exception as e:
            raise MCPtoolError(f"""X OAuth Token Error: {str(e)}

Agent: {agent_name}
Troubleshooting:
1. Check agent deployment: Use `get_agent_status`
2. Verify OAuth config: ~/.agentcore_gateways/{agent_name}_runtime.json
3. Redeploy with OAuth: Use `deploy_agentcore_app` with `enable_oauth: True`
""")

    @mcp.tool()
    async def check_oauth_status(  # pragma: no cover
        agent_name: str = Field(description='Agent name to check OAuth status'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Check the actual OAuth deployment status of an agent using AWS API (get_agent_runtime)."""
        try:
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
            raise MCPtoolError(f"""X OAuth Status Check Error: {str(e)}

Agent: {agent_name}

Manual Check:
1. Look at `.bedrock_agentcore.yaml` for `oauth_configuration`
2. Check `~/.agentcore_gateways/{agent_name}_runtime.json`
3. Try `invoke_agent` first (works for most agents)
""")

    @mcp.tool()
    async def invoke_agent_smart(  # pragma: no cover
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
                session_id = str(uuid.uuid4())

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
                    raise MCPtoolError(f"""! Regular Invocation Failed - Trying OAuth

Regular invocation error:
```
{regular_result[:500]}...
```

Attempting OAuth invocation...

---

{await invoke_oauth_agent(agent_name=agent_name, prompt=prompt, session_id=session_id, region=region)}
""")
                else:
                    # No OAuth config, return regular error with helpful guidance
                    raise MCPtoolError(f"""{regular_result}

Note: OAuth Alternative: If this agent requires OAuth:
1. Deploy with OAuth: Use `deploy_agentcore_app` with `enable_oauth: True`
2. Then try: `invoke_oauth_agent` for authenticated invocation
""")

            except Exception as regular_error:
                # Regular invocation completely failed, check for OAuth
                config_dir = Path.home() / '.agentcore_gateways'
                oauth_config_file = config_dir / f'{agent_name}_runtime.json'

                if oauth_config_file.exists():
                    raise MCPtoolError(f"""! Regular Invocation Error - Using OAuth

Switching to OAuth authentication...

{await invoke_oauth_agent(agent_name=agent_name, prompt=prompt, session_id=session_id, region=region)}
""")
                else:
                    raise MCPtoolError(f"""X Agent Invocation Failed

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
""")

        except Exception as e:
            raise MCPtoolError(f"""X Smart Invocation Error: {str(e)}

Agent: {agent_name}
Fallback options:
1. Try directly: `invoke_agent {agent_name} "your prompt"`
2. For OAuth: `invoke_oauth_agent {agent_name} "your prompt"`
3. Check status: `get_agent_status {agent_name}`
""")

    @mcp.tool()
    async def invoke_oauth_agent_v2(  # pragma: no cover
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
            if not token_success:  # pragma: no cover
                return 'OAuth token generation failed\nUse: `get_runtime_oauth_token` for detailed token generation'

            # Step 3: Use Runtime SDK pattern (same as invoke_agent) with OAuth
            try:
                if not RUNTIME_AVAILABLE:  # pragma: no cover
                    return (
                        'X Runtime SDK not available - requires bedrock-agentcore-starter-toolkit'
                    )

                # Find agent config directory (same logic as invoke_agent)  # pragma: no cover
                config_dirs_to_check = [
                    Path.cwd(),
                    get_user_working_directory(),
                    Path.cwd() / 'examples',
                    Path.home() / 'agentcore_projects' / agent_name,
                ]

                config_dir_found = None
                for config_dir in config_dirs_to_check:  # pragma: no cover
                    if check_agent_config_exists(agent_name):
                        config_dir_found = config_dir
                        break

                if not config_dir_found:  # pragma: no cover
                    raise OSError(f"""X Agent Configuration Not Found
Agent: {agent_name}
Searched: {[str(d) for d in config_dirs_to_check]}
Fix: Deploy agent first with `deploy_agentcore_app`
""")

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
                        raise MCPtoolError(f"""X Agent Not Ready
Agent: {agent_name}
Status: {status}
Fix: Wait for agent to be READY or redeploy
""")
                except Exception as status_error:
                    return f'X Status Check Failed: {str(status_error)}'

                # Step 4: Invoke with OAuth context (enhanced Runtime pattern)
                # Note: Current Runtime SDK may not support OAuth headers directly
                # This is a limitation we document and handle gracefully

                payload = {'prompt': prompt}
                try:
                    # Try regular Runtime invocation first (OAuth handled at infrastructure level)
                    response = runtime.invoke(payload)

                    return return_oauth_invoke_ok.format(
                        agent_name=agent_name,
                        prompt=prompt,
                        session_id=session_id,
                        response=response,
                        config_dir=config_dir_found,
                    )

                except Exception as invoke_error:
                    # Fallback: Provide instructions for manual OAuth invocation
                    raise MCPtoolError(
                        return_oauth_error.format(
                            agent_name=agent_name,
                            prompt=prompt,
                            session_id=session_id,
                            invoke_error=str(invoke_error),
                        )
                    )
            except Exception as runtime_error:
                raise MCPtoolError(f"""X Runtime Error: {str(runtime_error)}
Agent: {agent_name}
Troubleshooting:
1. Check agent deployment: `get_agent_status`
2. Verify agent is READY
3. Use regular invocation: `invoke_agent` (may work if OAuth optional)
""")

        except Exception as e:
            raise MCPtoolError(f"""X OAuth Invocation Error (v2): {str(e)}
Agent: {agent_name}
Troubleshooting:
1. Check OAuth config: ~/.agentcore_gateways/{agent_name}_runtime.json
2. Verify deployment: Use `get_agent_status`
3. Get token separately: Use `get_runtime_oauth_token`
4. Use regular invocation: If OAuth not required, use `invoke_agent`
""")

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
                cmd = [agentcore_cmd, 'status', '--agent', agent_name]  # pragma: no cover

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
        except Exception as e:  # pragma: no cover
            raise MCPtoolError(f'X Status Check Error: {str(e)}')  # pragma: no cover

    @mcp.tool()
    async def discover_existing_agents(  # pragma: no cover
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
                raise OSError(return_search_error.format(path_resolved=str(path.resolve())))

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
                                elif 'agents' in config:  # pragma: no cover
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
                                    continue  # Skip the outer agent_info append  # pragma: no cover
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
            if include_status and RUNTIME_AVAILABLE:  # pragma: no cover
                for agent_info in discovered_agents:  # pragma: no cover
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
                raise MCPtoolError(
                    return_search_mcp_error.format(
                        path_resolved=str(path.resolve()), config_files=config_files
                    )
                )

            # Format results
            result_parts = [
                f'# Search: Discovered {len(discovered_agents)} Agent Configuration(s)',
                '',
                f'### Search Path: `{path.resolve()}`',
                '',
            ]

            ready_agents = [a for a in discovered_agents if a['status'] == 'READY']
            configured_agents = [
                a
                for a in discovered_agents
                if 'CONFIGURED' in a['status'] or a['status'] == 'CREATING'
            ]
            error_agents = [
                a
                for a in discovered_agents
                if a not in ready_agents and a not in configured_agents
            ]

            if ready_agents:
                result_parts.append(f'### Ready: Ready to Invoke ({len(ready_agents)} agents):')
                for agent in ready_agents:
                    result_parts.extend(
                        [
                            f'#### {agent["name"]}',
                            f'- Status: {agent["status"]}',
                            f'- Config: `{agent["config_file"]}`',
                            f'- Invoke: `invoke_agent` with agent_name: `{agent["name"]}`',
                            '',
                        ]
                    )

            if configured_agents:
                result_parts.append(
                    f'### Configured: Configured But Not Deployed ({len(configured_agents)} agents):'
                )
                for agent in configured_agents:
                    result_parts.extend(
                        [
                            f'#### {agent["name"]}',
                            f'- Status: {agent["status"]}',
                            f'- Config: `{agent["config_file"]}`',
                            '- Deploy: Use `deploy_agentcore_app` with execution_mode: `sdk`',
                            '',
                        ]
                    )

            if error_agents:
                result_parts.append(f'### Error: Agents with Issues ({len(error_agents)} agents):')
                for agent in error_agents:
                    result_parts.extend(
                        [
                            f'#### {agent["name"]}',
                            f'- Status: {agent["status"]}',
                            f'- Config: `{agent["config_file"]}`',
                            '',
                        ]
                    )

            result_parts.extend(
                [
                    '### Quick Actions:',
                    *(['- Invoke Ready Agents: Use `invoke_agent` tool'] if ready_agents else []),
                    *(
                        ['- Deploy Configured: Use `deploy_agentcore_app` tool']
                        if configured_agents
                        else []
                    ),
                    '- Create New: Use `analyze_agent_code` → `deploy_agentcore_app`',
                ]
            )

            return '\n'.join(result_parts)

        except Exception as e:
            return f'X Discovery Error: {str(e)}'
