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

"""AgentCore MCP Server - Core Utilities Module.

Shared utilities for AgentCore operations including authentication,
environment validation, file resolution, and project discovery.

Implemented MCP Tools:
- get_oauth_access_token: OAuth token generation for gateway access
- validate_agentcore_environment: Development environment validation
- what_agents_can_i_invoke: Agent discovery (local + AWS)
- project_discover: Project file and configuration discovery
- discover_agentcore_examples: GitHub examples repository integration
"""

import boto3
import os
import re
import subprocess
import yaml
from bedrock_agentcore import BedrockAgentCoreApp

## Optional YAML support for configuration parsing
## AgentCore SDK and starter toolkit imports
from bedrock_agentcore.memory import MemoryClient, MemoryControlPlaneClient
from bedrock_agentcore.services.identity import IdentityClient

## CRITICAL: Import the Runtime class from starter toolkit for actual deployment
from bedrock_agentcore_starter_toolkit import Runtime
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from pydantic import Field
from typing import Any, Dict, List, Optional
from urllib.parse import quote


# from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

SDK_AVAILABLE = True
RUNTIME_AVAILABLE = True
SDK_IMPORT_ERROR = None
YAML_AVAILABLE = True

## SDK capability detection
SDK_CAPABILITIES = {
    'BedrockAgentCoreApp': {
        'methods': [m for m in dir(BedrockAgentCoreApp) if not m.startswith('_')],
        'has_configure': hasattr(BedrockAgentCoreApp, 'configure'),
        'has_launch': hasattr(BedrockAgentCoreApp, 'launch'),
        'has_run': hasattr(BedrockAgentCoreApp, 'run'),
        'has_entrypoint_decorator': True,
    },
    'MemoryClient': {
        'methods': [m for m in dir(MemoryClient) if not m.startswith('_')],
        'available': True,
    },
    'MemoryControlPlaneClient': {
        'methods': [m for m in dir(MemoryControlPlaneClient) if not m.startswith('_')],
        'available': True,
    },
    'IdentityClient': {
        'methods': [m for m in dir(IdentityClient) if not m.startswith('_')],
        'available': True,
    },
}


## Core utility functions


def validate_sdk_method(class_name: str, method_name: str) -> bool:
    """Validate that a method actually exists in the SDK before using it."""
    if not SDK_AVAILABLE:
        return False

    if class_name not in SDK_CAPABILITIES:
        return False

    return method_name in SDK_CAPABILITIES[class_name].get('methods', [])


def resolve_app_file_path(file_path: str) -> Optional[str]:
    """Resolve agent file path with robust search strategy."""
    import os

    ## Get user's actual working directory from environment
    user_cwd = os.environ.get('PWD', os.getcwd())
    user_path = Path(user_cwd)

    ## Try multiple path resolution strategies
    search_paths = [
        ## 1. Absolute path as-is
        Path(file_path),
        ## 2. Relative to user's working directory
        user_path / file_path,
        ## 3. In examples subdirectory
        user_path / 'examples' / Path(file_path).name,
        ## 4. In current MCP server directory
        Path.cwd() / file_path,
        ## 5. Direct filename search in user directory
        user_path / Path(file_path).name,
    ]

    for path in search_paths:
        if path.exists() and path.is_file():
            return str(path.absolute())

    return None


def get_user_working_directory() -> Path:
    """Get the user's actual working directory, not MCP server's."""
    import os

    ## Try environment variables first
    user_cwd = os.environ.get('PWD') or os.environ.get('OLDPWD')
    if user_cwd and Path(user_cwd).exists():
        return Path(user_cwd)

    ## Try current working directory
    current_dir = Path.cwd()
    if current_dir.exists():
        return current_dir

    ## Last resort - use MCP server cwd
    return Path.cwd()


def get_runtime_for_agent(agent_name: str) -> 'Runtime':
    """Get Runtime object - can be recreated as it uses file-based config persistence."""
    if not RUNTIME_AVAILABLE:
        raise ImportError('Runtime not available')

    ## Create new Runtime object (they're lightweight and use file persistence)
    runtime = Runtime()

    ## CRITICAL: Runtime needs _config_path to be set for status() and invoke() to work
    config_found, config_dir = find_agent_config_directory(agent_name)
    if config_found:
        config_path = config_dir / '.bedrock_agentcore.yaml'

        ## Set the config path directly on the Runtime object
        runtime._config_path = config_path
        runtime.name = agent_name

        ## For multi-agent configs, ensure the requested agent is set as default
        if YAML_AVAILABLE and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'agents' in config and agent_name in config['agents']:
                        if config.get('default_agent') != agent_name:
                            ## Update the config to set this agent as default
                            config['default_agent'] = agent_name
                            with open(config_path, 'w') as f:
                                yaml.dump(config, f, default_flow_style=False)
            except Exception:
                pass  ## Fall back to default Runtime behavior
    else:
        ## No config found - Runtime will fail with proper error message
        runtime._config_path = None
        runtime.name = agent_name

    return runtime


def check_agent_config_exists(agent_name: str) -> tuple[bool, Path]:
    """Check if agent has existing config file (persistent across MCP server restarts)."""
    ## Look for config file in current directory (where configure() creates it)
    config_path = Path.cwd() / '.bedrock_agentcore.yaml'

    if config_path.exists():
        ## Check if this config is for our agent
        if YAML_AVAILABLE:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and config.get('agent_name') == agent_name:
                        return True, config_path
            except Exception as e:
                print(f'Error reading config file: {e}')
                pass
        ## If YAML not available, assume config exists if file exists
        return True, config_path

    return False, config_path


def find_agent_config_directory(agent_name: str) -> tuple[bool, Path]:
    """Find the directory containing the agent's configuration file."""
    search_paths = [
        Path.cwd(),  ## Current directory
        get_user_working_directory(),  ## User's working directory
        get_user_working_directory() / 'examples',  ## Examples subdirectory
        Path.cwd() / 'examples',  ## Examples in current dir
    ]

    for search_path in search_paths:
        config_path = search_path / '.bedrock_agentcore.yaml'
        if config_path.exists() and YAML_AVAILABLE:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config:
                        ## Check simple format (agent_name field)
                        if config.get('agent_name') == agent_name:
                            return True, search_path
                        ## Check complex format (agents dict)
                        if 'agents' in config and agent_name in config['agents']:
                            return True, search_path
            except Exception as e:
                print(f'Error reading config file: {e}')
                continue

    return False, Path.cwd()


async def get_agentcore_command():
    """Get the appropriate agentcore command based on environment."""
    ## Check if uv is available
    try:
        result = subprocess.run(['which', 'uv'], capture_output=True, text=True)
        if result.returncode == 0:
            return ['uv', 'run', 'agentcore']
    except Exception as e:
        print(f'Error checking uv command: {e}')
        pass

    ## Check for virtual environment
    if Path('.venv/bin/python').exists():
        return ['.venv/bin/python', '-m', 'agentcore']
    elif Path('venv/bin/python').exists():
        return ['venv/bin/python', '-m', 'agentcore']

    ## Default to system agentcore
    return 'agentcore'


def analyze_code_patterns(code: str) -> Dict[str, Any]:
    """Analyze code to detect framework and patterns."""
    patterns = {
        'framework': 'unknown',
        'patterns': [],
        'dependencies': [],
        'agent_creation': None,
        'handler_function': None,
    }

    ## Detect framework
    if 'from strands import Agent' in code or 'import strands' in code:
        patterns['framework'] = 'strands'
        patterns['patterns'].append('Strands Agent detected')
    elif 'langgraph' in code.lower():
        patterns['framework'] = 'langgraph'
        patterns['patterns'].append('LangGraph workflow detected')
    elif 'crewai' in code.lower():
        patterns['framework'] = 'crewai'
        patterns['patterns'].append('CrewAI agents detected')
    elif 'BedrockAgentCoreApp' in code:
        patterns['framework'] = 'agentcore'
        patterns['patterns'].append('Already AgentCore format')
    else:
        patterns['framework'] = 'custom'
        patterns['patterns'].append('Custom agent implementation')

    ## Extract imports
    import_matches = re.findall(r'(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
    patterns['dependencies'] = list(set(import_matches))

    ## Find agent creation
    agent_patterns = [
        r'agent\s*=\s*Agent\(',
        r'Agent\(\s*name=',
        r'class.*Agent',
    ]
    for pattern in agent_patterns:
        if re.search(pattern, code):
            patterns['agent_creation'] = pattern
            break

    ## Find handler/main function
    handler_patterns = [
        r'def\s+handler\(',
        r'def\s+main\(',
        r'@app\.entrypoint',
        r'if __name__ == ["\']__main__["\']:',
    ]
    for pattern in handler_patterns:
        if re.search(pattern, code):
            patterns['handler_function'] = pattern
            break

    return patterns


def format_patterns(patterns: List[str]) -> str:
    """Format detected patterns for display."""
    if not patterns:
        return '- No specific patterns detected'
    return '\n'.join(f'- {pattern}' for pattern in patterns)


def format_dependencies(dependencies: List[str]) -> str:
    """Format dependencies for display."""
    if not dependencies:
        return '- No dependencies detected'
    return '\n'.join(f'- {dep}' for dep in dependencies[:10])  ## Limit to first 10


def format_features_added(options: Dict[str, bool]) -> str:
    """Format features that were added."""
    features = []
    if options.get('add_memory'):
        features.append('OK Memory integration added')
    if options.get('add_tools'):
        features.append('OK Code interpreter and browser tools added')

    features.append('OK AgentCore deployment wrapper')
    features.append('OK Production-ready structure')

    return '\n'.join(features)


def get_next_steps(memory_enabled: bool) -> str:
    """Get appropriate next steps based on configuration."""
    steps = []

    if not memory_enabled:
        steps.append('- Use `configure_agent_memory` to add memory capabilities')

    steps.extend(
        [
            '- Use `setup_agent_identity` to add authentication',
            '- Use `test_deployed_agent` to verify functionality',
            '- Monitor with CloudWatch or AgentCore dashboard',
        ]
    )

    return '\n'.join(steps)


## ============================================================================
## ENVIRONMENT VALIDATION TOOLS
## ============================================================================


def register_environment_tools(mcp: FastMCP):
    """Register environment validation tools with the MCP server."""

    @mcp.tool()
    async def validate_agentcore_environment(
        project_path: str = Field(default='.', description='Path to project directory'),
        check_existing_agents: bool = Field(
            default=True, description='Check for existing agent configurations'
        ),
    ) -> str:
        """Validate AgentCore development environment and check for existing agent configurations."""
        try:
            ## Use improved directory resolution
            if project_path == '.':
                path = get_user_working_directory()
            else:
                path = Path(project_path)
                if not path.is_absolute():
                    path = get_user_working_directory() / project_path

            validation_results = []
            issues = []

            ## Check if path exists
            if not path.exists():
                return f"Project path '{project_path}' does not exist"

            validation_results.append(f'OK Project directory: {path.absolute()}')

            ## Check virtual environment
            if Path('.venv').exists():
                validation_results.append('OK Virtual environment (.venv) found')
            elif Path('venv').exists():
                validation_results.append('OK Virtual environment (venv) found')
            else:
                issues.append('! No virtual environment detected')

            ## Check for UV
            try:
                result = subprocess.run(['which', 'uv'], capture_output=True, text=True)
                if result.returncode == 0:
                    validation_results.append('OK UV package manager available')
                else:
                    issues.append('Info: UV not found (optional)')
            except Exception:
                issues.append('Info: UV not found (optional)')

            ## Check AgentCore CLI
            agentcore_cmd = await get_agentcore_command()
            try:
                if isinstance(agentcore_cmd, list):
                    test_cmd = agentcore_cmd + ['--help']
                else:
                    test_cmd = [agentcore_cmd, '--help']

                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    validation_results.append('OK AgentCore CLI available')
                else:
                    issues.append('X AgentCore CLI not working properly')
            except Exception as e:
                issues.append(f'X AgentCore CLI not found + {str(e)}')

            ## Check AWS credentials
            try:
                result = subprocess.run(
                    ['aws', 'sts', 'get-caller-identity'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    validation_results.append('OK AWS credentials configured')
                else:
                    issues.append('! AWS credentials not configured')
            except Exception:
                issues.append('! AWS CLI not found or credentials not configured')

            ## Check Python files
            python_files = list(path.glob('*.py'))
            if python_files:
                validation_results.append(f'OK Found {len(python_files)} Python files')
            else:
                issues.append('Info: No Python files found in project directory')

            ## Check for AgentCore applications
            agentcore_apps = []
            for py_file in python_files:
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        if 'BedrockAgentCoreApp' in content:
                            agentcore_apps.append(py_file.name)
                except Exception as e:
                    print(f'Error reading: {str(e)}')
                    pass

            if agentcore_apps:
                validation_results.append(
                    f'OK AgentCore applications found: {", ".join(agentcore_apps)}'
                )
            else:
                issues.append('Info: No AgentCore applications detected')

            ## Check for existing agent configurations
            existing_agents = []
            if check_existing_agents:
                config_files = list(path.glob('.bedrock_agentcore*.yaml')) + list(
                    path.glob('**/.bedrock_agentcore*.yaml')
                )
                for config_file in config_files:
                    try:
                        if YAML_AVAILABLE:
                            with open(config_file, 'r') as f:
                                config = yaml.safe_load(f)
                                if config and config.get('agent_name'):
                                    existing_agents.append(
                                        {
                                            'name': config['agent_name'],
                                            'config_file': str(config_file.relative_to(path)),
                                            'status': 'configured',
                                        }
                                    )
                        else:
                            existing_agents.append(
                                {
                                    'name': config_file.stem.replace('.bedrock_agentcore', ''),
                                    'config_file': str(config_file.relative_to(path)),
                                    'status': 'configured',
                                }
                            )
                    except Exception as e:
                        print(f'Error reading config: {str(e)}')
                        continue

                if existing_agents:
                    validation_results.append(
                        f'Update: Existing agent configurations found: {len(existing_agents)}'
                    )
                    for agent in existing_agents:
                        validation_results.append(f'  - {agent["name"]} ({agent["config_file"]})')
                else:
                    validation_results.append('Info: No existing agent configurations found')

            ## Generate report
            status = 'OK READY' if not any('X' in issue for issue in issues) else '! ISSUES FOUND'

            return f"""## Search: AgentCore Environment Validation

#### Status: {status}

#### Validation Results:
{chr(10).join(validation_results)}

#### Issues & Notes:
{chr(10).join(issues) if issues else 'OK No issues found'}

#### Project Summary:
- Directory: `{path.absolute()}`
- Python files: {len(python_files)}
- AgentCore apps: {len(agentcore_apps)}
- Existing agents: {len(existing_agents)}

{format_existing_agents_summary(existing_agents) if existing_agents else ''}

#### Next Steps:
{get_environment_next_steps(issues, existing_agents)}"""
        except Exception as e:
            return f'Environment Validation Error: {str(e)}'


def get_environment_next_steps(issues: List[str], existing_agents: List[dict] = []) -> str:
    """Generate next steps based on validation issues."""
    steps = []

    if any('AgentCore CLI' in issue for issue in issues):
        steps.append(
            '1. Install AgentCore from PyPI: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`'
        )

    if any('AWS credentials' in issue for issue in issues):
        steps.append('2. Configure AWS credentials: `aws configure`')

    if any('virtual environment' in issue for issue in issues):
        steps.append(
            '3. Create virtual environment: `python -m venv .venv && source .venv/bin/activate`'
        )

    if any('AgentCore applications' in issue for issue in issues):
        steps.append(
            '4. Use `analyze_agent_code` to analyze existing code or `transform_to_agentcore` to create AgentCore apps'
        )

    if not steps:
        steps = [
            '1. Your environment is ready! Use `analyze_agent_code` to start migration',
            '2. Or use `deploy_agentcore_app` to deploy existing AgentCore applications',
        ]

    return chr(10).join(steps)


def format_existing_agents_summary(existing_agents: List[dict]) -> str:
    """Format existing agents summary."""
    if not existing_agents:
        return ''

    summary = []
    summary.append('#### Update: Existing Agent Configurations Found:')

    for agent in existing_agents:
        summary.append(f'##### {agent["name"]}')
        summary.append(f'- Status: {agent["status"].title()}')
        summary.append(f'- Config File: `{agent["config_file"]}`')
        summary.append(f'- Ready to invoke: Use `invoke_agent` with agent_name: `{agent["name"]}`')
        summary.append('')

    return chr(10).join(summary)


## ============================================================================
## ENHANCED AGENT DISCOVERY AND RUNTIME MANAGEMENT (FROM LEGACY SERVERS)
## ============================================================================


def what_agents_can_i_invoke(region: str = 'us-east-1') -> str:
    """Target: WHAT AGENTS CAN I INVOKE?

    Smart overlap analysis combining local YAML configs with actual AWS deployments.
    Shows exactly what you can invoke, launch, or update with specific agent names.

    Categories:
    - Ready: Ready to Invoke: Deployed on AWS (invoke immediately)
    - Pending: Ready to Launch: Local config only (launch then invoke)
    - 🔵 Ready to Update: Both local + AWS but not ready
    """
    try:
        ## Get AWS deployed agents with timeout
        aws_agents = {}
        try:
            client = boto3.client('bedrock-agentcore-control', region_name=region)
            ## Use shorter timeout to prevent hanging
            aws_response = client.list_agent_runtimes(maxResults=50)

            for runtime in aws_response.get('agentRuntimes', []):
                name = runtime.get('agentRuntimeName', runtime.get('name', 'unknown'))
                if name != 'unknown':
                    aws_agents[name] = {
                        'status': runtime.get('status', 'unknown'),
                        'endpoint_status': runtime.get('status', 'UNKNOWN'),
                        'arn': runtime.get('agentRuntimeArn', runtime.get('arn', '')),
                    }
        except Exception:
            ## If AWS fails, continue with local-only analysis
            aws_agents = {}

        ## Get local configured agents from YAML
        local_agents = {}
        try:
            config_files = list(Path('.').glob('**/.bedrock_agentcore.yaml'))
            for config_file in config_files:
                if YAML_AVAILABLE:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                        if config and 'agents' in config:
                            for agent_name, agent_config in config['agents'].items():
                                ## Check if agent is deployed by looking for agent_arn/agent_id
                                bedrock_agentcore = agent_config.get('bedrock_agentcore', {})
                                agent_arn = bedrock_agentcore.get('agent_arn')
                                agent_id = bedrock_agentcore.get('agent_id')

                                ## Determine if this agent is deployed
                                is_deployed = (
                                    agent_arn
                                    and agent_id
                                    and agent_arn != 'null'
                                    and agent_id != 'null'
                                )

                                local_agents[agent_name] = {
                                    'entrypoint': agent_config.get('entrypoint', 'unknown'),
                                    'config_file': str(config_file),
                                    'is_deployed': is_deployed,
                                    'agent_arn': agent_arn,
                                    'agent_id': agent_id,
                                }
        except Exception:
            pass

        ## Analyze overlap and deployment status
        aws_only = set(aws_agents.keys()) - set(local_agents.keys())
        local_only = set(local_agents.keys()) - set(aws_agents.keys())
        both = set(aws_agents.keys()) & set(local_agents.keys())

        ## Find locally deployed agents (have agent_arn in YAML)
        locally_deployed = []
        for name, config in local_agents.items():
            if config.get('is_deployed', False):
                locally_deployed.append(name)

        ## Categorize by readiness
        ready_to_invoke = []
        ready_to_update = []
        ready_to_launch = []
        aws_not_ready = []

        ## Check AWS deployed agents
        for name in aws_only | both:
            if name in aws_agents and aws_agents[name]['endpoint_status'] == 'READY':
                ready_to_invoke.append(name)
            elif name in both:
                ready_to_update.append(name)
            else:
                aws_not_ready.append(name)

        ## Check locally deployed agents (from YAML with agent_arn)
        for name in locally_deployed:
            if name not in ready_to_invoke and name not in ready_to_update:
                ## This agent is deployed according to local config but not found on AWS query
                ## It might be deployed but AWS query failed, so mark as ready to invoke
                ready_to_invoke.append(name)

        ## Find agents that need launching
        for name in local_only:
            if name not in locally_deployed:
                ready_to_launch.append(name)

        ## If no agents found anywhere
        if not aws_agents and not local_agents:
            return f"""## Target: No Agents Found

Region: {region}
Status: No agents found in AWS or local configs

Next Steps:
- Deploy an agent: `deploy_agentcore_app(agent_file="your_agent.py", execution_mode="sdk")`
- Check examples: Look for agent files in your project
"""

        ## If only local agents and AWS failed, show local-only analysis
        if not aws_agents and local_agents:
            result_parts = ['## Target: Local Agents Analysis (AWS Query Failed)']
            result_parts.append('')
            result_parts.append('Analysis: Local configs only (AWS not accessible)')
            result_parts.append('')

            if locally_deployed:
                result_parts.append(
                    f'#### Ready: Deployed Locally ({len(locally_deployed)} agents):'
                )
                result_parts.append('*These have agent ARNs in local config*')
                result_parts.append('')
                for name in locally_deployed:
                    agent_arn = local_agents[name].get('agent_arn', 'unknown')
                    result_parts.append(f'##### {name}')
                    result_parts.append('- Status: Deployed (has ARN in config) OK')
                    result_parts.append(
                        f'- ARN: `{agent_arn[:60] if agent_arn else "unknown"}...`'
                    )
                    result_parts.append(
                        f"- Try Invoke: `invoke_agent(agent_name='{name}', prompt='Hello!')`"
                    )
                    result_parts.append('')

            not_deployed = [
                name for name in local_agents if not local_agents[name].get('is_deployed')
            ]
            if not_deployed:
                result_parts.append(f'#### Pending: Not Deployed ({len(not_deployed)} agents):')
                for name in not_deployed:
                    entrypoint = local_agents[name]['entrypoint']
                    result_parts.append(
                        f"- {name}: Deploy first `deploy_agentcore_app(agent_file='{entrypoint}', execution_mode='sdk')`"
                    )

            result_parts.append('')
            result_parts.append('Note: AWS query failed - showing local config analysis only')
            return '\\n'.join(result_parts)

        result_parts = ['## Target: What Agents Can I Invoke?']
        result_parts.append('')
        result_parts.append(f'Region: {region}')
        result_parts.append('Analysis: Local configs + AWS deployments')
        result_parts.append('')

        ## Category 1: Ready to Invoke (AWS deployed & ready)
        if ready_to_invoke:
            result_parts.append(f'#### Ready: Ready to Invoke ({len(ready_to_invoke)} agents):')
            result_parts.append('*These are deployed on AWS and ready for immediate invocation*')
            result_parts.append('')
            for name in ready_to_invoke:
                result_parts.append(f'##### {name}')
                result_parts.append('- Status: READY on AWS OK')
                if name in both:
                    result_parts.append('- Config: Local + AWS (synced)')
                else:
                    result_parts.append('- Config: AWS only (deployed elsewhere)')
                result_parts.append(
                    f"- Invoke: `invoke_agent(agent_name='{name}', prompt='Hello!')`"
                )
                result_parts.append('')

        ## Category 2: Ready to Launch (Local config only, not deployed)
        if ready_to_launch:
            result_parts.append(f'#### Pending: Ready to Launch ({len(ready_to_launch)} agents):')
            result_parts.append('*These are configured locally but not deployed to AWS*')
            result_parts.append('')
            for name in ready_to_launch:
                entrypoint = local_agents[name]['entrypoint']
                result_parts.append(f'##### {name}')
                result_parts.append('- Status: Configured locally only')
                result_parts.append(f'- Entrypoint: `{entrypoint}`')
                result_parts.append(
                    f"- Launch: `deploy_agentcore_app(agent_file='{entrypoint}', execution_mode='sdk')`"
                )
                result_parts.append(
                    f"- Then Invoke: `invoke_agent(agent_name='{name}', prompt='test')`"
                )
                result_parts.append('')

        ## Category 3: Ready to Update (Both local + AWS but not ready)
        if ready_to_update:
            result_parts.append(f'#### 🔵 Ready to Update ({len(ready_to_update)} agents):')
            result_parts.append(
                '*These exist in both local + AWS but may need updating/relaunching*'
            )
            result_parts.append('')
            for name in ready_to_update:
                entrypoint = local_agents[name]['entrypoint']
                aws_status = aws_agents[name]['endpoint_status']
                result_parts.append(f'##### {name}')
                result_parts.append(f'- Status: {aws_status} on AWS')
                result_parts.append('- Config: Local + AWS (may be out of sync)')
                result_parts.append(
                    f"- Update: `deploy_agentcore_app(agent_file='{entrypoint}', execution_mode='sdk')`"
                )
                result_parts.append(
                    f"- Then Invoke: `invoke_agent(agent_name='{name}', prompt='test')`"
                )
                result_parts.append('')

        ## AWS-only agents that are not ready
        if aws_not_ready:
            result_parts.append(f'#### ! AWS Agents Not Ready ({len(aws_not_ready)} agents):')
            for name in aws_not_ready:
                if name in aws_agents:
                    status = aws_agents[name]['endpoint_status']
                    result_parts.append(f'- {name}: Status {status} (wait or redeploy)')
            result_parts.append('')

        ## Summary
        result_parts.append('#### Stats: Summary:')
        if ready_to_invoke:
            result_parts.append(f'- Can invoke now: {len(ready_to_invoke)} agents')
        if ready_to_update:
            result_parts.append(f'- Can update then invoke: {len(ready_to_update)} agents')
        if ready_to_launch:
            result_parts.append(f'- Can launch then invoke: {len(ready_to_launch)} agents')

        if ready_to_invoke:
            result_parts.append('')
            result_parts.append(
                f"Launch: Quick Test: `invoke_agent(agent_name='{ready_to_invoke[0]}', prompt='Hello!')`"
            )

        return '\\n'.join(result_parts)

    except ImportError:
        return """Boto3 Not Available

Install boto3: `pip install boto3` or `uv add boto3`
Purpose: Query actual AWS deployed agents (source of truth)
Benefit: See real deployments vs potentially stale local YAML files
"""
    except Exception as e:
        ## Fallback to local-only analysis if everything fails
        return f"""Tool Error: {str(e)[:200]}...

Fallback: Try local analysis only:
- `discover_existing_agents()` for local configs
- `invoke_agent(agent_name='agent_name', prompt='test')` to test specific agents

AWS Setup: `aws configure` or check credentials
"""


def project_discover(action: str = 'agents', search_path: str = '.') -> str:
    """Search: CONSOLIDATED PROJECT DISCOVERY.

    Single tool for ALL discovery operations in your project.

    Actions:
    - agents: Find agent files
    - configs: Find AgentCore configurations
    - memories: Find memory resources
    - all: Complete project scan
    """
    search_path_str = str(search_path) or '.'
    try:
        search_path_obj = Path(search_path_str).absolute()
        print(f'Searching in: {search_path_obj}')
        if action == 'agents':
            ## Find potential agent files
            agent_patterns = [
                '**/*agent*.py',
                '/agent.py',
                '/main.py',
                '**/*strands*.py',
                '**/*langchain*.py',
            ]
            agent_files = []

            for pattern in agent_patterns:
                files = list(Path(search_path).glob(pattern))
                agent_files.extend([f for f in files if f not in agent_files])

            ## Filter out AgentCore files and test files
            filtered_files = [
                f
                for f in agent_files
                if not f.name.endswith('_agentcore.py')
                and 'agentcore_' not in f.name
                and 'test_' not in f.name
            ]

            if not filtered_files:
                return f"""## Search: No Agent Files Found

Search Path: `{search_path}`

Searched Patterns:
- *agent*.py, agent.py, main.py
- *strands*.py, *langchain*.py
- Excluding: AgentCore files, test files

Next Steps:
- Check different directory: `project_discover(action="agents", search_path="other/path")`
- Create new agent or place existing agent files in this directory
"""

            ## Analyze found files
            analyzed_files = []
            for file_path in filtered_files:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()

                    framework = 'Custom'
                    if 'from strands import' in content:
                        framework = 'Strands'
                    elif 'langgraph' in content.lower():
                        framework = 'LangGraph'
                    elif 'langchain' in content.lower():
                        framework = 'LangChain'

                    has_agentcore = 'BedrockAgentCoreApp' in content

                    analyzed_files.append(
                        {
                            'path': file_path.relative_to(search_path),
                            'framework': framework,
                            'agentcore': has_agentcore,
                        }
                    )
                except Exception as e:
                    print(f'Error processing {file_path}: {e}')
                    continue

            files_list = []
            for file_info in analyzed_files:
                status = 'OK AgentCore' if file_info['agentcore'] else 'X Needs transform'
                files_list.append(f'- {file_info["path"]} ({file_info["framework"]}) - {status}')

            return f"""## Search: Agent Files Discovered

Search Path: `{search_path}`
Found: {len(analyzed_files)} agent files

{chr(10).join(files_list)}

#### Quick Actions:
- Transform agent: `transform_to_agentcore(source_file="path/to/agent.py")`
- Deploy agent: `deploy_agentcore_app(app_file="path/to/agent.py", agent_name="my_agent", execution_mode="sdk")`
"""

        elif action == 'configs':
            ## Find AgentCore configuration files with status checking
            config_files = list(Path(search_path).glob('**/.bedrock_agentcore.yaml'))

            if not config_files:
                return f"""## Config: No AgentCore Configurations Found

Search Path: `{search_path}`

What this means:
- No deployed agents found
- Use `deploy_agentcore_app()` to deploy agents
- Use `project_discover(action="agents")` to find agent files
"""

            discovered_agents = []

            for config_file in config_files:
                try:
                    if YAML_AVAILABLE:
                        with open(config_file, 'r') as f:
                            config = yaml.safe_load(f)
                            if config:
                                ## Handle multi-agent config format
                                if 'agents' in config:
                                    for agent_name, agent_config in config['agents'].items():
                                        agent_info = {
                                            'name': agent_name,
                                            'config_file': str(
                                                config_file.relative_to(search_path)
                                            ),
                                            'entrypoint': agent_config.get(
                                                'entrypoint', 'unknown'
                                            ),
                                            'region': agent_config.get('aws', {}).get(
                                                'region', 'us-east-1'
                                            ),
                                            'status': 'CONFIGURED',
                                        }

                                        ## Check agent status if SDK available
                                        if RUNTIME_AVAILABLE:
                                            original_cwd = Path.cwd()
                                            try:
                                                os.chdir(config_file.parent)

                                                runtime = get_runtime_for_agent(agent_name)
                                                status_result = runtime.status()

                                                if (
                                                    hasattr(status_result, 'endpoint')
                                                    and status_result.endpoint
                                                    and hasattr(status_result.endpoint, 'get')
                                                ):
                                                    agent_info['status'] = (
                                                        status_result.endpoint.get(
                                                            'status', 'UNKNOWN'
                                                        )
                                                    )
                                                else:
                                                    agent_info['status'] = (
                                                        'CONFIGURED_NOT_DEPLOYED'
                                                    )

                                                os.chdir(original_cwd)

                                            except ValueError as e:
                                                if 'Must configure' in str(e):
                                                    agent_info['status'] = (
                                                        'CONFIGURED_NOT_DEPLOYED'
                                                    )
                                                else:
                                                    agent_info['status'] = 'ERROR'
                                            except Exception:
                                                agent_info['status'] = 'ERROR'
                                            finally:
                                                try:
                                                    os.chdir(original_cwd)
                                                except Exception as e:
                                                    print(f'Error changing directory: {e}')
                                                    pass

                                        discovered_agents.append(agent_info)

                                ## Handle simple agent config format
                                elif 'agent_name' in config:
                                    agent_info = {
                                        'name': config.get('agent_name', 'unknown'),
                                        'config_file': str(config_file.relative_to(search_path)),
                                        'entrypoint': config.get('entrypoint', 'unknown'),
                                        'region': config.get('region', 'us-east-1'),
                                        'status': 'CONFIGURED',
                                    }
                                    discovered_agents.append(agent_info)
                except Exception:
                    continue

            if not discovered_agents:
                return f"""## Config: Config Files Found But Invalid

Search Path: `{search_path}`
Config Files: {len(config_files)}

Issue: Config files exist but contain invalid configurations
Next Steps: Use `deploy_agentcore_app()` to create new valid configurations
"""

            ## Categorize agents by status
            ready_agents = [a for a in discovered_agents if a['status'] == 'READY']
            configured_agents = [
                a
                for a in discovered_agents
                if 'CONFIGURED' in a['status'] or a['status'] == 'CREATING'
            ]
            error_agents = [a for a in discovered_agents if a['status'] in ['ERROR', 'UNKNOWN']]

            result_parts = ['## Config: AgentCore Configurations Discovered']
            result_parts.append('')
            result_parts.append(f'Search Path: `{search_path}`')
            result_parts.append(f'Total Agents: {len(discovered_agents)}')
            result_parts.append('')

            if ready_agents:
                result_parts.append(f'#### Ready: Ready to Invoke ({len(ready_agents)} agents):')
                for agent in ready_agents:
                    result_parts.append(f'##### {agent["name"]}')
                    result_parts.append('- Status: READY OK')
                    result_parts.append(f'- Config: `{agent["config_file"]}`')
                    result_parts.append(
                        f"- Invoke: `invoke_agent(agent_name='{agent['name']}', prompt='test')`"
                    )
                    result_parts.append('')

            if configured_agents:
                result_parts.append(
                    f'#### Pending: Configured But Not Deployed ({len(configured_agents)} agents):'
                )
                for agent in configured_agents:
                    result_parts.append(f'##### {agent["name"]}')
                    result_parts.append(f'- Status: {agent["status"]}')
                    result_parts.append(f'- Config: `{agent["config_file"]}`')
                    result_parts.append(
                        f"- Deploy: `deploy_agentcore_app(app_file='{agent['entrypoint']}', agent_name='{agent['name']}', execution_mode='sdk')`"
                    )
                    result_parts.append('')

            if error_agents:
                result_parts.append(
                    f'#### Error: Agents with Issues ({len(error_agents)} agents):'
                )
                for agent in error_agents:
                    result_parts.append(f'##### {agent["name"]}')
                    result_parts.append(f'- Status: {agent["status"]}')
                    result_parts.append(f'- Config: `{agent["config_file"]}`')
                    result_parts.append('')

            result_parts.append('#### Quick Actions:')
            if ready_agents:
                result_parts.append(
                    f"- Test Ready Agent: `invoke_agent(agent_name='{ready_agents[0]['name']}', prompt='Hello!')`"
                )
            if configured_agents:
                result_parts.append(
                    f"- Deploy Agent: `deploy_agentcore_app(app_file='{configured_agents[0]['entrypoint']}', agent_name='{configured_agents[0]['name']}', execution_mode='sdk')`"
                )

            return '\\n'.join(result_parts)

        elif action == 'memories':
            if not SDK_AVAILABLE:
                return 'SDK Not Available: Cannot check memory resources without AgentCore SDK'

            try:
                from bedrock_agentcore.memory import MemoryClient

                memory_client = MemoryClient()

                memories = memory_client.list_memories(max_results=50)

                if not memories:
                    return """## Memory: No Memory Resources Found

No AgentCore memory resources found in your AWS account.

Next Steps:
- Create memory: Use memory management tools
- Setup memory for agent: Integrate memory into agent deployment
"""

                memory_list = []
                for memory in memories:
                    memory_id = memory.get('memoryId', 'unknown')[:20] + '...'
                    name = memory.get('name', 'unnamed')
                    status = memory.get('status', 'unknown')
                    memory_list.append(f'- {name} ({memory_id}) - {status}')

                return f"""## Memory: Memory Resources Found

Found: {len(memories)} memory resources

{chr(10).join(memory_list)}

#### Next Actions:
- Health check: Check memory status
- Setup with agent: Integrate memory with agents
"""
            except Exception as e:
                return f'Memory Discovery Error: {str(e)}'

        elif action == 'all':
            ## Complete project scan
            agents_result = project_discover(action='agents', search_path=str(search_path))
            configs_result = project_discover(action='configs', search_path=str(search_path))
            memories_result = project_discover(action='memories', search_path=str(search_path))

            return f"""## Search: Complete Project Discovery

Search Path: `{search_path}`

---

{agents_result}

---

{configs_result}

---

{memories_result}

---

#### Overall Project Status:
- Use discovered agents with `transform_to_agentcore`, `deploy_agentcore_app`
- Check existing configurations with `get_agent_status`
- Manage memory resources with memory tools
"""

        else:
            return f"""Unknown Action: `{action}`

Available Actions:
- `agents` - Find agent files
- `configs` - Find AgentCore configurations
- `memories` - Find memory resources
- `all` - Complete project scan

Example: `project_discover(action="agents")`
"""

    except Exception as e:
        return f'Discovery Error: {str(e)}'


## ============================================================================
## MCP TOOL REGISTRATION FOR DISCOVERY FUNCTIONS
## ============================================================================


def register_discovery_tools(mcp: FastMCP):
    """Register enhanced agent discovery and runtime management tools."""

    @mcp.tool()
    async def get_agent_logs(
        agent_name: str = Field(description='Name of the deployed agent'),
        hours_back: int = Field(default=1, description='Hours of logs to retrieve (default: 1)'),
        max_events: int = Field(
            default=50, description='Maximum number of log events (default: 50)'
        ),
        error_only: bool = Field(default=False, description='Only show error/exception logs'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Get CloudWatch logs for an AgentCore agent runtime for troubleshooting."""
        try:
            import boto3
            from datetime import datetime, timedelta

            # First, get the agent runtime ID from the control plane
            control_client = boto3.client('bedrock-agentcore-control', region_name=region)
            agents = control_client.list_agent_runtimes(maxResults=50)

            agent_runtime_id = None
            agent_arn = None

            for agent in agents.get('agentRuntimes', []):
                if agent.get('agentRuntimeName', agent.get('name')) == agent_name:
                    agent_arn = agent.get('agentRuntimeArn', '')
                    if agent_arn:
                        # Extract runtime ID from ARN
                        # ARN format: arn:aws:bedrock-agentcore:region:account:runtime/runtime-id
                        agent_runtime_id = agent_arn.split('/')[-1]
                    break

            if not agent_runtime_id:
                return f"""# Agent Logs - Agent Not Found

Agent: {agent_name}
Status: Not found in deployed agents

Use project_discover with action 'aws' to see available agents."""

            # Construct log group name (pattern: /aws/bedrock-agentcore/runtimes/{runtime-id}-{endpoint})
            endpoint_name = 'DEFAULT'  # Most common endpoint name
            log_group_name = f'/aws/bedrock-agentcore/runtimes/{agent_runtime_id}-{endpoint_name}'

            # Create CloudWatch Logs client
            logs_client = boto3.client('logs', region_name=region)

            # Check if log group exists
            try:
                logs_response = logs_client.describe_log_groups(
                    logGroupNamePrefix=log_group_name, limit=1
                )

                if not logs_response.get('logGroups'):
                    return f"""# Agent Logs - Log Group Not Found

Agent: {agent_name}
Runtime ID: {agent_runtime_id}
Expected Log Group: {log_group_name}
Status: Log group does not exist

This could mean:
- Agent hasn't been invoked yet
- Different endpoint name (try invoking the agent first)
- Agent deployment issue"""

            except Exception as e:
                return f"""# Agent Logs - Access Error

Agent: {agent_name}
Runtime ID: {agent_runtime_id}
Log Group: {log_group_name}
Error: {str(e)}

Check AWS permissions for CloudWatch Logs access."""

            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)

            # Get log events
            filter_pattern = None
            if error_only:
                filter_pattern = '?ERROR ?Exception ?Failed ?Traceback'

            try:
                events_response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    filterPattern=filter_pattern,
                    startTime=int(start_time.timestamp() * 1000),
                    endTime=int(end_time.timestamp() * 1000),
                    limit=max_events,
                )

                events = events_response.get('events', [])

                if not events:
                    status_msg = 'No error logs found' if error_only else 'No logs found'
                    return f"""# Agent Logs - No Events

Agent: {agent_name}
Runtime ID: {agent_runtime_id}
Log Group: {log_group_name}
Time Range: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}
Status: {status_msg}

Try:
- Increasing hours_back parameter
- Invoking the agent to generate logs
- Setting error_only=False to see all logs"""

                # Format log events
                log_lines = []
                for event in events:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].strip()
                    log_lines.append(f'[{timestamp.strftime("%Y-%m-%d %H:%M:%S")}] {message}')

                # Get log group info
                log_group = logs_response['logGroups'][0]
                created_time = datetime.fromtimestamp(log_group['creationTime'] / 1000)

                return f"""# Agent Logs

## Agent Info:
- Name: {agent_name}
- Runtime ID: {agent_runtime_id}
- Log Group: {log_group_name}
- Created: {created_time.strftime('%Y-%m-%d %H:%M:%S')}

## Query Info:
- Time Range: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}
- Filter: {'Errors only' if error_only else 'All logs'}
- Events Found: {len(events)}

## Log Events:

{chr(10).join(log_lines)}

## Troubleshooting Tips:
- If seeing exceptions, check your agent code
- If no logs appear, try invoking the agent first
- For deployment issues, check agent configuration
- For runtime errors, review the error messages above"""

            except Exception as e:
                return f"""# Agent Logs - Retrieval Error

Agent: {agent_name}
Runtime ID: {agent_runtime_id}
Log Group: {log_group_name}
Error: {str(e)}

This could indicate:
- CloudWatch Logs permission issues
- Log group access restrictions
- Network connectivity issues"""

        except Exception as e:
            return f'Agent Logs Error: {str(e)}'

    @mcp.tool()
    async def invokable_agents(region: str = 'us-east-1') -> str:
        """Target: WHAT AGENTS CAN I INVOKE?

        Combining local YAML configs with actual AWS deployments.
        Shows exactly what you can invoke, launch, or update with specific agent names.

        Categories:
        - Ready: Ready to Invoke: Deployed on AWS (invoke immediately)
        - Pending: Ready to Launch: Local config only (launch then invoke)
        - 🔵 Ready to Update: Both local + AWS but not ready
        """
        return what_agents_can_i_invoke(region)

    @mcp.tool()
    async def project_discover(
        action: str = 'agents',  ## "agents", "configs", "memories", "all"
        search_path: str = '.',
    ) -> str:
        """Search: CONSOLIDATED PROJECT DISCOVERY.

        Single tool for ALL discovery operations in your project.

        Actions:
        - agents: Find agent files
        - configs: Find AgentCore configurations
        - memories: Find memory resources
        - all: Complete project scan

        Examples:
        - project_discover()  ## Find agents
        - project_discover(action="all")  ## Complete scan
        """
        return project_discover(action, search_path)


## ============================================================================
## GITHUB EXAMPLES DISCOVERY (DYNAMIC)
## ============================================================================


def discover_agentcore_examples_from_github(
    query: str = '',
    category: str = 'all',  ## "all", "tutorials", "use-cases", "integrations"
    format_type: str = 'all',  ## "all", "python", "jupyter", "docker"
) -> str:
    """Search: DISCOVER AGENTCORE EXAMPLES FROM GITHUB.

    Dynamically discovers working examples from amazon-bedrock-agentcore-samples repository.
    Always up-to-date with the latest samples and use cases.

    Examples:
    - discover_agentcore_examples_from_github(query="oauth")  ## Find OAuth examples
    - discover_agentcore_examples_from_github(query="memory integration")  ## Memory examples
    - discover_agentcore_examples_from_github(category="tutorials")  ## Beginner examples
    """
    try:
        import requests
        import time
        from dataclasses import dataclass, field
        from typing import Dict, List, Optional

        @dataclass
        class ExampleMetadata:
            name: str
            path: str
            description: str
            use_case: str = ''
            framework: str = ''
            level: str = ''
            components: List[str] = field(default_factory=list)
            format_type: str = ''
            github_url: str = ''
            metadata: Dict[str, str] = field(default_factory=dict)

            def __post_init__(self):
                if self.components is None:
                    self.components = []
                if self.metadata is None:
                    self.metadata = {}

        ## GitHub URLs
        base_url = 'https://api.github.com/repos/awslabs/amazon-bedrock-agentcore-samples'
        raw_base_url = (
            'https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/main'
        )
        web_base_url = 'https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main'

        ## Simple cache (in real implementation, use proper caching)
        cache = {}

        def github_search_api_with_cli(query_terms: List[str]) -> List[Dict]:
            """Use GitHub CLI for authenticated search API access."""
            try:
                import json
                import subprocess

                search_results = []

                # Check if GitHub CLI is available and authenticated
                try:
                    result = subprocess.run(
                        ['gh', 'auth', 'status'], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode != 0:
                        # Not authenticated - return special indicator
                        return [{'auth_required': True, 'gh_available': True}]
                except FileNotFoundError:
                    # GitHub CLI not installed
                    return [{'auth_required': True, 'gh_available': False}]
                except subprocess.TimeoutExpired:
                    return []  # Fall back silently on timeout

                # Search for README files with query terms
                readme_query = f'{" ".join(query_terms)} in:readme repo:awslabs/amazon-bedrock-agentcore-samples'
                try:
                    result = subprocess.run(
                        ['gh', 'api', f'/search/code?q={quote(readme_query)}'],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )

                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        for item in data.get('items', []):
                            path = item.get('path', '')
                            # Extract section and example name from path like "01-tutorials/04-AgentCore-memory/README.md"
                            path_parts = path.split('/')
                            if len(path_parts) >= 3 and path_parts[0] in [
                                '01-tutorials',
                                '02-use-cases',
                                '03-integrations',
                            ]:
                                section = path_parts[0]
                                example_name = path_parts[1]
                                search_results.append(
                                    {
                                        'section': section,
                                        'name': example_name,
                                        'relevance': 'high',
                                        'match_path': path,
                                    }
                                )
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    pass

                # Search for code files with individual terms
                for term in query_terms:
                    if len(term) > 2:  # Avoid single character searches
                        file_query = f'{term} repo:awslabs/amazon-bedrock-agentcore-samples'
                        try:
                            result = subprocess.run(
                                [
                                    'gh',
                                    'api',
                                    f'/search/code?q={quote(file_query)}',
                                ],
                                capture_output=True,
                                text=True,
                                timeout=15,
                            )

                            if result.returncode == 0:
                                data = json.loads(result.stdout)
                                for item in data.get('items', []):
                                    path = item.get('path', '')
                                    path_parts = path.split('/')
                                    if len(path_parts) >= 2 and path_parts[0] in [
                                        '01-tutorials',
                                        '02-use-cases',
                                        '03-integrations',
                                    ]:
                                        section = path_parts[0]
                                        example_name = (
                                            path_parts[1] if len(path_parts) > 1 else 'unknown'
                                        )

                                        # Avoid duplicates
                                        if not any(
                                            r['section'] == section and r['name'] == example_name
                                            for r in search_results
                                        ):
                                            search_results.append(
                                                {
                                                    'section': section,
                                                    'name': example_name,
                                                    'relevance': 'medium',
                                                    'match_path': path,
                                                }
                                            )
                        except (subprocess.TimeoutExpired, json.JSONDecodeError):
                            continue

                # Search for specific combinations
                if len(query_terms) >= 2:
                    combined_query = (
                        f'{" ".join(query_terms)} repo:awslabs/amazon-bedrock-agentcore-samples'
                    )
                    try:
                        result = subprocess.run(
                            [
                                'gh',
                                'api',
                                f'/search/code?q={quote(combined_query)}',
                            ],
                            capture_output=True,
                            text=True,
                            timeout=15,
                        )

                        if result.returncode == 0:
                            data = json.loads(result.stdout)
                            for item in data.get('items', []):
                                path = item.get('path', '')
                                path_parts = path.split('/')
                                if len(path_parts) >= 2 and path_parts[0] in [
                                    '01-tutorials',
                                    '02-use-cases',
                                    '03-integrations',
                                ]:
                                    section = path_parts[0]
                                    example_name = (
                                        path_parts[1] if len(path_parts) > 1 else 'unknown'
                                    )

                                    # Avoid duplicates, but boost relevance for combined matches
                                    existing = next(
                                        (
                                            r
                                            for r in search_results
                                            if r['section'] == section
                                            and r['name'] == example_name
                                        ),
                                        None,
                                    )
                                    if existing:
                                        existing['relevance'] = 'very_high'
                                    else:
                                        search_results.append(
                                            {
                                                'section': section,
                                                'name': example_name,
                                                'relevance': 'high',
                                                'match_path': path,
                                            }
                                        )
                    except (subprocess.TimeoutExpired, json.JSONDecodeError):
                        pass

                # Sort by relevance and return
                relevance_order = {'very_high': 0, 'high': 1, 'medium': 2}
                search_results.sort(key=lambda x: relevance_order.get(x['relevance'], 3))

                return search_results[:15]  # Limit results to avoid too many API calls

            except Exception:
                return []

        def github_search_api(query_terms: List[str]) -> List[Dict]:
            """Try GitHub's search API - first with CLI auth, then fallback."""
            # Try authenticated search with GitHub CLI first
            results = github_search_api_with_cli(query_terms)
            if results:
                return results

            # Fallback to unauthenticated approach (will likely fail but worth trying)
            try:
                search_results = []

                # Try code search in README files specifically
                readme_query = f'{" ".join(query_terms)} in:readme repo:awslabs/amazon-bedrock-agentcore-samples'
                search_url = f'https://api.github.com/search/code?q={quote(readme_query)}'

                time.sleep(0.5)  # Rate limit protection
                response = requests.get(search_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('items', []):
                        path = item.get('path', '')
                        path_parts = path.split('/')
                        if len(path_parts) >= 3 and path_parts[0] in [
                            '01-tutorials',
                            '02-use-cases',
                            '03-integrations',
                        ]:
                            section = path_parts[0]
                            example_name = path_parts[1]
                            search_results.append(
                                {'section': section, 'name': example_name, 'relevance': 'high'}
                            )

                return search_results[:15]

            except Exception:
                return []

        def fetch_repository_structure() -> Dict[str, List[str]]:
            """Fetch the repository structure organized by section."""
            if 'structure' in cache:
                return cache['structure']

            try:
                time.sleep(0.5)  ## Rate limit protection

                response = requests.get(f'{base_url}/contents', timeout=10)
                response.raise_for_status()

                main_contents = response.json()
                structure = {}

                target_dirs = ['01-tutorials', '02-use-cases', '03-integrations']

                for item in main_contents:
                    if item['type'] == 'dir' and item['name'] in target_dirs:
                        dir_name = item['name']

                        time.sleep(0.5)  ## Rate limit protection
                        dir_response = requests.get(f'{base_url}/contents/{dir_name}', timeout=10)
                        if dir_response.status_code == 200:
                            dir_contents = dir_response.json()

                            examples = []
                            for subitem in dir_contents:
                                if subitem['type'] == 'dir':
                                    examples.append(subitem['name'])

                            structure[dir_name] = examples

                cache['structure'] = structure
                return structure

            except requests.RequestException:
                return {}

        def extract_metadata_from_readme(readme_content: str) -> Dict[str, str]:
            """Extract metadata from README content with enhanced table parsing."""
            import re

            metadata = {}

            try:
                ## Enhanced markdown table parsing for various formats

                # Pattern 1: Standard metadata tables (key-value pairs)
                table_patterns = [
                    # Two-column tables: | Key | Value |
                    r'\|([^|]+)\|([^|]+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|[^|]*\|[^|]*\|\s*\n?)+)',
                    # Three-column tables with headers: | Info | Details | Extra |
                    r'\|([^|]*Information[^|]*)\|([^|]*Details[^|]*)\|[^|]*\|\s*\n\|[-:\s|]+\|\s*\n((?:\|[^|]*\|[^|]*\|[^|]*\|\s*\n?)+)',
                ]

                for pattern in table_patterns:
                    table_matches = re.finditer(
                        pattern, readme_content, re.MULTILINE | re.IGNORECASE
                    )

                    for table_match in table_matches:
                        table_content = (
                            table_match.group(3)
                            if len(table_match.groups()) >= 3
                            else table_match.group(1)
                        )
                        rows = [
                            row.strip()
                            for row in table_content.split('\n')
                            if row.strip() and '|' in row
                        ]

                        for row in rows:
                            parts = [part.strip() for part in row.split('|')]
                            if len(parts) >= 3:
                                key = parts[1].strip().lower()
                                value = parts[2].strip()

                                # Clean up key and value
                                if (
                                    key
                                    and value
                                    and key not in ['-', '--', '']
                                    and value not in ['-', '--', '']
                                ):
                                    # Normalize key names
                                    key_normalized = re.sub(r'[^\w\s]', '', key).replace(' ', '_')

                                    # Store common variations
                                    if (
                                        'use_case' in key
                                        or 'usecase' in key
                                        or key in ['type', 'use_case_type']
                                    ):
                                        metadata['use_case'] = value
                                    elif (
                                        'framework' in key
                                        or 'sdk' in key
                                        or key in ['agent_type', 'agent_framework']
                                    ):
                                        metadata['framework'] = value
                                    elif (
                                        'complexity' in key
                                        or 'level' in key
                                        or 'difficulty' in key
                                    ):
                                        metadata['level'] = value
                                    elif 'component' in key or 'tools' in key or 'tech' in key:
                                        metadata['components'] = value
                                    elif 'vertical' in key or 'domain' in key or 'industry' in key:
                                        metadata['vertical'] = value
                                    else:
                                        metadata[key_normalized] = value

                # Pattern 2: Multi-column format tables (like memory tutorial)
                # | Memory Type | Framework | Use Case | Notebook |
                memory_pattern = r'\|\s*([^|]*Memory[^|]*)\s*\|\s*([^|]*Framework[^|]*)\s*\|\s*([^|]*Use\s*Case[^|]*)\s*\|[^|]*\|\s*\n\|[-:\s|]+\|\s*\n((?:\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*\n?)+)'
                memory_match = re.search(
                    memory_pattern, readme_content, re.MULTILINE | re.IGNORECASE
                )

                if memory_match:
                    table_content = memory_match.group(4)
                    rows = [
                        row.strip()
                        for row in table_content.split('\n')
                        if row.strip() and '|' in row
                    ]

                    frameworks = set()
                    use_cases = set()
                    memory_types = set()

                    for row in rows:
                        parts = [part.strip() for part in row.split('|')]
                        if len(parts) >= 4:
                            memory_type = parts[1].strip()
                            framework = parts[2].strip()
                            use_case = parts[3].strip()

                            if memory_type and memory_type not in ['-', '--']:
                                memory_types.add(memory_type)
                            if framework and framework not in ['-', '--']:
                                frameworks.add(framework)
                            if use_case and use_case not in ['-', '--']:
                                use_cases.add(use_case)

                    if frameworks:
                        metadata['framework'] = ', '.join(frameworks)
                    if use_cases:
                        metadata['use_case'] = ', '.join(use_cases)
                    if memory_types:
                        metadata['memory_types'] = ', '.join(memory_types)

                ## Look for key-value patterns in text
                patterns = {
                    'use_case': r'(?:Use[_\s-]*[Cc]ase[^:]*|Type[^:]*|Purpose[^:]*):\s*([^\n]+)',
                    'framework': r'(?:Framework|Agent\s*Framework|SDK\s*used|Technology):\s*([^\n]+)',
                    'level': r'(?:Level|Difficulty|Skill\s*Level|Complexity):\s*([^\n]+)',
                    'components': r'(?:Components|AgentCore\s*Components|Tools|Technologies):\s*([^\n]+)',
                    'authentication': r'(?:Auth|Authentication|OAuth|Security):\s*([^\n]+)',
                    'vertical': r'(?:Vertical|Domain|Industry|Use\s*case\s*vertical):\s*([^\n]+)',
                }

                for key, pattern in patterns.items():
                    matches = re.finditer(pattern, readme_content, re.IGNORECASE)
                    for match in matches:
                        value = match.group(1).strip()
                        if value and len(value) < 200:  # Reasonable length limit
                            if key not in metadata or len(value) > len(metadata[key]):
                                metadata[key] = value

                ## Extract tags from headers and content
                tag_patterns = [
                    r'##?\s*([^#\n]+(?:oauth|auth|security|strands|langgraph|memory|tools|gateway)[^#\n]*)',
                    r'(?:supports?|includes?|features?)[^.]*?(oauth|authentication|memory|tools|gateway|strands|langgraph)',
                    r'\*\*([^*]*(?:oauth|auth|strands|memory|tools)[^*]*)\*\*',
                ]

                tags = set()
                for pattern in tag_patterns:
                    matches = re.finditer(pattern, readme_content, re.IGNORECASE)
                    for match in matches:
                        tag_text = match.group(1).lower()
                        if 'oauth' in tag_text or 'auth' in tag_text:
                            tags.add('authentication')
                        if 'strands' in tag_text:
                            tags.add('strands')
                        if 'langgraph' in tag_text:
                            tags.add('langgraph')
                        if 'memory' in tag_text:
                            tags.add('memory')
                        if 'tools' in tag_text:
                            tags.add('tools')
                        if 'gateway' in tag_text:
                            tags.add('gateway')

                if tags:
                    metadata['tags'] = ', '.join(tags)

                return metadata

            except Exception:
                return {}

        def fetch_example_details(section: str, example_name: str) -> Optional[ExampleMetadata]:
            """Fetch detailed information about a specific example."""
            cache_key = f'{section}/{example_name}'
            if cache_key in cache:
                return cache[cache_key]

            try:
                time.sleep(0.5)  ## Rate limit protection

                ## Try to fetch README
                readme_url = f'{raw_base_url}/{section}/{example_name}/README.md'
                readme_response = requests.get(readme_url, timeout=10)

                readme_content = ''
                if readme_response.status_code == 200:
                    readme_content = readme_response.text

                ## Extract description (first meaningful line)
                description = 'AgentCore example'
                if readme_content:
                    lines = readme_content.split('\n')
                    for line in lines:
                        if (
                            line.strip()
                            and not line.startswith('#')
                            and not line.startswith('|')
                            and len(line.strip()) > 20
                        ):
                            description = line.strip()[:200]
                            if description.endswith('...'):
                                description = description[:-3] + '...'
                            break

                metadata_dict = extract_metadata_from_readme(readme_content)

                ## Determine format type
                format_type = 'python'
                try:
                    time.sleep(0.5)  ## Rate limit protection
                    files_response = requests.get(
                        f'{base_url}/contents/{section}/{example_name}', timeout=10
                    )
                    if files_response.status_code == 200:
                        files = files_response.json()
                        has_notebook = any(f.get('name', '').endswith('.ipynb') for f in files)
                        has_dockerfile = any(
                            f.get('name', '').lower() in ['dockerfile', 'docker-compose.yml']
                            for f in files
                        )

                        if has_notebook:
                            format_type = 'jupyter'
                        elif has_dockerfile:
                            format_type = 'docker'
                except Exception as e:
                    print(f'Error determining format type: {e}')
                    pass

                ## Parse components
                components = []
                if 'components' in metadata_dict:
                    components = [c.strip() for c in metadata_dict['components'].split(',')]

                ## Infer components from section and name
                if section == '01-tutorials':
                    component_keywords = {
                        'memory': 'Memory',
                        'gateway': 'Gateway',
                        'runtime': 'Runtime',
                        'identity': 'Identity',
                        'tools': 'Tools',
                        'observability': 'Observability',
                    }

                    for keyword, component in component_keywords.items():
                        if keyword in example_name.lower():
                            components.append(component)

                example = ExampleMetadata(
                    name=example_name.replace('-', ' ').title(),
                    path=f'{section}/{example_name}',
                    description=description,
                    use_case=metadata_dict.get('use_case', metadata_dict.get('usecase', '')),
                    framework=metadata_dict.get('framework', ''),
                    level=metadata_dict.get('level', metadata_dict.get('difficulty', '')),
                    components=components,
                    format_type=format_type,
                    github_url=f'{web_base_url}/{section}/{example_name}',
                )

                # Store the full metadata for enhanced searching
                example.metadata = metadata_dict

                cache[cache_key] = example
                return example

            except Exception:
                return None

        ## Main discovery logic
        try:
            # First, try GitHub's search API if we have a query
            priority_results = []
            auth_status = None
            if query:
                query_terms = [
                    term.strip() for term in query.lower().split() if len(term.strip()) > 2
                ]
                if query_terms:
                    priority_results = github_search_api(query_terms)

                    # Check if we got an authentication requirement
                    if (
                        priority_results
                        and isinstance(priority_results[0], dict)
                        and 'auth_required' in priority_results[0]
                    ):
                        auth_status = priority_results[0]
                        priority_results = []

            structure = fetch_repository_structure()

            if not structure:
                return """GitHub API Error

Issue: Could not fetch repository structure
Possible causes:
- GitHub API rate limits
- Network connectivity
- Repository access issues

Manual Browse: [AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)

Repository Structure:
- `01-tutorials/` - Learning-focused examples
- `02-use-cases/` - Real-world applications
- `03-integrations/` - Framework integrations
"""

            ## Discover examples based on filters
            examples = []
            processed_examples = set()  # Track to avoid duplicates

            # Process priority results from GitHub search first
            for result in priority_results:
                section = result['section']
                example_name = result['name']

                # Filter by category if specified
                if category != 'all':
                    category_mapping = {
                        'tutorials': '01-tutorials',
                        'use-cases': '02-use-cases',
                        'integrations': '03-integrations',
                        'getting-started': '01-tutorials',
                        'advanced': '02-use-cases',
                    }

                    if category_mapping.get(category, category) != section:
                        continue

                example_key = f'{section}/{example_name}'
                if example_key not in processed_examples:
                    example = fetch_example_details(section, example_name)
                    if example:
                        examples.append(example)
                        processed_examples.add(example_key)

            # Then process remaining examples from directory structure
            for section, example_names in structure.items():
                ## Filter by category
                if category != 'all':
                    category_mapping = {
                        'tutorials': '01-tutorials',
                        'use-cases': '02-use-cases',
                        'integrations': '03-integrations',
                        'getting-started': '01-tutorials',
                        'advanced': '02-use-cases',
                    }

                    if category_mapping.get(category, category) != section:
                        continue

                ## Smart filtering: if query is provided, search all examples names first for quick matches
                if query:
                    query_lower = query.lower()
                    ## Pre-filter by example names that might match the query
                    relevant_names = []
                    for example_name in example_names:
                        example_key = f'{section}/{example_name}'
                        # Skip if already processed from GitHub search
                        if example_key in processed_examples:
                            continue
                        if any(keyword in example_name.lower() for keyword in query_lower.split()):
                            relevant_names.append(example_name)

                    ## If we found relevant names, prioritize them, otherwise fetch first few
                    if relevant_names:
                        target_names = relevant_names[:8]  ## Get up to 8 relevant matches
                    else:
                        # If we already have priority results, fetch fewer fallback examples
                        fallback_count = 4 if priority_results else 8
                        target_names = [
                            name
                            for name in example_names
                            if f'{section}/{name}' not in processed_examples
                        ][:fallback_count]
                else:
                    target_names = [
                        name
                        for name in example_names
                        if f'{section}/{name}' not in processed_examples
                    ][:6]  ## Default limit when no query

                ## Fetch details for selected examples
                for example_name in target_names:
                    example_key = f'{section}/{example_name}'
                    if example_key not in processed_examples:
                        example = fetch_example_details(section, example_name)
                        if example:
                            examples.append(example)
                            processed_examples.add(example_key)

            ## Filter by format
            if format_type != 'all':
                examples = [ex for ex in examples if ex.format_type == format_type]

            ## Enhanced semantic search by query
            if query:
                query_lower = query.lower()
                query_terms = set(query_lower.split())

                scored_examples = []

                for example in examples:
                    score = 0

                    # Build comprehensive searchable content
                    searchable_fields = {
                        'name': example.name.lower(),
                        'description': example.description.lower(),
                        'use_case': example.use_case.lower(),
                        'framework': example.framework.lower(),
                        'components': ' '.join(example.components).lower(),
                        'level': example.level.lower(),
                        'format_type': example.format_type.lower(),
                    }

                    # Add any extra metadata we extracted
                    if hasattr(example, 'metadata'):
                        for key, value in example.metadata.items():
                            if isinstance(value, str):
                                searchable_fields[key] = value.lower()

                    # Calculate relevance score
                    for term in query_terms:
                        # Exact matches in key fields get higher scores
                        if term in searchable_fields['name']:
                            score += 10
                        if term in searchable_fields['framework']:
                            score += 8
                        if term in searchable_fields['use_case']:
                            score += 6
                        if term in searchable_fields['components']:
                            score += 4

                        # Partial matches in any field
                        for field_name, field_content in searchable_fields.items():
                            if term in field_content:
                                score += 2

                        # Handle common synonyms and related terms
                        synonyms = {
                            'oauth': ['authentication', 'auth', 'security', 'login'],
                            'strands': ['agent', 'framework'],
                            'memory': ['storage', 'persistence', 'state'],
                            'tools': ['functions', 'capabilities', 'mcp'],
                            'gateway': ['api', 'endpoint', 'server'],
                            'examples': ['samples', 'tutorials', 'demos'],
                        }

                        if term in synonyms:
                            for synonym in synonyms[term]:
                                for field_content in searchable_fields.values():
                                    if synonym in field_content:
                                        score += 1

                        # Reverse synonym lookup
                        for key_term, synonym_list in synonyms.items():
                            if term in synonym_list:
                                for field_content in searchable_fields.values():
                                    if key_term in field_content:
                                        score += 1

                    # Boost score for multi-term matches in same field
                    all_content = ' '.join(searchable_fields.values())
                    if all(term in all_content for term in query_terms):
                        score += 5

                    if score > 0:
                        scored_examples.append((example, score))

                # Sort by relevance score and take results
                scored_examples.sort(key=lambda x: x[1], reverse=True)
                examples = [example for example, score in scored_examples]

            ## Format results
            if not examples:
                no_results_msg = ['## Search: No AgentCore Examples Found']
                no_results_msg.append('')
                no_results_msg.append(f'Query: "{query}" (no matches)')
                no_results_msg.append(f'Category: {category}')
                no_results_msg.append(f'Format: {format_type}')
                no_results_msg.append('')

                # Add authentication prompt if needed
                if auth_status:
                    if auth_status.get('gh_available'):
                        no_results_msg.append('🔍 **Enhanced Search Available**')
                        no_results_msg.append('')
                        no_results_msg.append(
                            "You're not authenticated with GitHub CLI. For much better search results:"
                        )
                        no_results_msg.append('')
                        no_results_msg.append('```bash')
                        no_results_msg.append('gh auth login')
                        no_results_msg.append('```')
                        no_results_msg.append('')
                        no_results_msg.append('This enables:')
                        no_results_msg.append('- Real-time GitHub code search')
                        no_results_msg.append('- Semantic matching in README files')
                        no_results_msg.append('- Much faster and more accurate results')
                        no_results_msg.append('')
                        no_results_msg.append('After authentication, try your search again!')
                        no_results_msg.append('')
                    else:
                        no_results_msg.append('🔍 **Enhanced Search Available**')
                        no_results_msg.append('')
                        no_results_msg.append('Install GitHub CLI for much better search results:')
                        no_results_msg.append('')
                        no_results_msg.append('```bash')
                        no_results_msg.append('# Install GitHub CLI')
                        no_results_msg.append('brew install gh  # macOS')
                        no_results_msg.append('# or: apt install gh  # Linux')
                        no_results_msg.append('# or: winget install GitHub.cli  # Windows')
                        no_results_msg.append('')
                        no_results_msg.append('# Then authenticate')
                        no_results_msg.append('gh auth login')
                        no_results_msg.append('```')
                        no_results_msg.append('')

                no_results_msg.append('Available Categories:')
                no_results_msg.append(
                    f'- `tutorials` - Learning-focused examples ({len(structure.get("01-tutorials", []))} available)'
                )
                no_results_msg.append(
                    f'- `use-cases` - Real-world applications ({len(structure.get("02-use-cases", []))} available)'
                )
                no_results_msg.append(
                    f'- `integrations` - Framework integrations ({len(structure.get("03-integrations", []))})'
                )
                no_results_msg.append('')
                no_results_msg.append('Try:')
                no_results_msg.append(
                    '- Broader search terms: `discover_agentcore_examples_from_github(query="memory")`'
                )
                no_results_msg.append(
                    '- All examples: `discover_agentcore_examples_from_github()`'
                )
                no_results_msg.append(
                    '- Specific category: `discover_agentcore_examples_from_github(category="tutorials")`'
                )
                no_results_msg.append('')
                no_results_msg.append(
                    'Direct Browse: [GitHub Repository](https://github.com/awslabs/amazon-bedrock-agentcore-samples)'
                )

                return '\\n'.join(no_results_msg)

            ## Group by section for display
            sections = {}
            for example in examples:
                section = example.path.split('/')[0]
                if section not in sections:
                    sections[section] = []
                sections[section].append(example)

            result_parts = ['## Search: AgentCore Examples Discovery']

            if query:
                result_parts.append(f'Query: "{query}"')

            # Indicate search method used
            if priority_results:
                result_parts.append('Search Method: GitHub CLI (authenticated) ✓')
            elif auth_status:
                if auth_status.get('gh_available'):
                    result_parts.append(
                        'Search Method: Content-based (GitHub CLI not authenticated)'
                    )
                    result_parts.append('💡 Tip: Run `gh auth login` for enhanced search!')
                else:
                    result_parts.append('Search Method: Content-based (GitHub CLI not installed)')
                    result_parts.append('💡 Tip: Install GitHub CLI for enhanced search!')
            else:
                result_parts.append('Search Method: Content-based')

            result_parts.append(f'Found: {len(examples)} examples')
            result_parts.append('')

            ## Format by section
            section_names = {
                '01-tutorials': 'Tutorial: Tutorials (Learning-focused)',
                '02-use-cases': 'Target: Use Cases (Real-world applications)',
                '03-integrations': 'Link: Integrations (Framework examples)',
            }

            for section, section_examples in sections.items():
                section_title = section_names.get(section, f'{section}')
                result_parts.append(f'#### {section_title}')
                result_parts.append('')

                for example in section_examples:
                    result_parts.append(f'##### {example.name}')
                    result_parts.append(f'- Description: {example.description}')

                    if example.use_case:
                        result_parts.append(f'- Use Case: {example.use_case}')
                    if example.framework:
                        result_parts.append(f'- Framework: {example.framework}')
                    if example.level:
                        result_parts.append(f'- Level: {example.level}')
                    if example.components:
                        result_parts.append(f'- Components: {", ".join(example.components)}')

                    # Add rich metadata from README tables
                    if hasattr(example, 'metadata') and example.metadata:
                        metadata_items = []
                        for key, value in example.metadata.items():
                            if (
                                key not in ['use_case', 'framework', 'level', 'components']
                                and value
                                and len(value) < 100
                            ):
                                if key == 'vertical':
                                    metadata_items.append(f'Industry: {value}')
                                elif key == 'authentication':
                                    metadata_items.append(f'Auth: {value}')
                                elif key == 'tags':
                                    metadata_items.append(f'Tags: {value}')
                                elif key == 'memory_types':
                                    metadata_items.append(f'Memory Types: {value}')
                                else:
                                    formatted_key = key.replace('_', ' ').title()
                                    metadata_items.append(f'{formatted_key}: {value}')

                        for item in metadata_items[:3]:  # Limit to avoid clutter
                            result_parts.append(f'- {item}')

                    result_parts.append(f'- Format: {example.format_type.title()}')
                    result_parts.append(f'- GitHub: [View Example]({example.github_url})')
                    result_parts.append('')

            result_parts.append('#### Launch: Getting Started:')
            result_parts.append('1. Browse: Click GitHub links to view examples')
            result_parts.append(
                '2. Clone: `git clone https://github.com/awslabs/amazon-bedrock-agentcore-samples.git`'
            )
            result_parts.append(
                '3. Navigate: `cd amazon-bedrock-agentcore-samples/[example-path]`'
            )
            result_parts.append('4. Follow: README instructions for setup')

            total_available = sum(len(examples) for examples in structure.values())
            result_parts.append('')
            result_parts.append(f'Repository: {total_available} total examples available')
            result_parts.append('Last Updated: Live from GitHub (dynamic)')

            return '\\n'.join(result_parts)

        except Exception as e:
            return f"""GitHub Discovery Error: {str(e)[:200]}...

Manual Browse: [AgentCore Samples Repository](https://github.com/awslabs/amazon-bedrock-agentcore-samples)

Repository Sections:
- Tutorials: Learning-focused examples for each AgentCore component
- Use Cases: Real-world application implementations
- Integrations: Framework integration patterns (Strands, LangChain, etc.)
"""

    except ImportError:
        return """Requests Library Required

Missing: `requests` library needed for GitHub API access

Install:
```bash
pip install requests
## or
uv add requests
```

Purpose: Dynamically discover working examples from AgentCore samples repository

Manual Browse: [AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
"""


def register_github_discovery_tools(mcp: FastMCP):
    """Register GitHub examples discovery tools."""

    @mcp.tool()
    async def discover_agentcore_examples(
        query: str = '',
        category: str = 'all',  ## "all", "tutorials", "use-cases", "integrations"
        format_type: str = 'all',  ## "all", "python", "jupyter", "docker"
    ) -> str:
        """Search: DISCOVER AGENTCORE EXAMPLES FROM GITHUB.

        Dynamically discovers working examples from amazon-bedrock-agentcore-samples repository.
        Always up-to-date with the latest samples and use cases.

        Examples:
        - discover_agentcore_examples(query="oauth")  ## Find OAuth examples
        - discover_agentcore_examples(query="memory integration")  ## Memory examples
        - discover_agentcore_examples(category="tutorials")  ## Beginner examples
        - discover_agentcore_examples(format_type="jupyter")  ## Notebook examples
        """
        return discover_agentcore_examples_from_github(query, category, format_type)
