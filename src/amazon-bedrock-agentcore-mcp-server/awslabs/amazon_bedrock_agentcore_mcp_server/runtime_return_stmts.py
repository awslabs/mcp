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
"""AgentCore MCP Server - Runtime long return statements.

Adding longer return statements and errors here.
"""

return_for_analyze_ok = """# Search: Agent Code Analysis Complete

### Environment Status:
{env_info_formatted}

### Current Framework Detected: {analysis_framework}

### Code Patterns Found:
{patterns_formatted}

### Dependencies Detected:
{dependencies_formatted}

### Migration Strategy: {strategy_complexity}

{strategy_description}

### Tutorial-Based Migration Path (Use this as a fallback, may required getting the actual tutorial and using it to guide the transformation of the agent / mcp code):
{migration_guidance}

### Next Steps:
1. OK Analysis Complete
2. Update: Ready: Use `transform_to_agentcore` to convert your code
3. Pending: Pending: Deploy with `deploy_agentcore_app`
4. Pending: Pending: Configure memory/identity if needed (optional)

Estimated Migration Time: {strategy_time_estimate}
"""
# --------------------------------------------------------------------------------------
return_for_oauth_ok = """# OK: Runtime OAuth Token Generated

### Agent Information:
- Agent: `{agent_name}`
- User Pool: `{user_pool_id}`
- Client ID: `{client_id}`
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

# --------------------------------------------------------------------------------------

return_for_no_code = """X No Code Found

Please provide either:
1. A valid file path to your agent code
2. Paste your code in the `code_content` parameter

Environment Status:
{env_info_formatted}

Available Python files found:
{available_files}

User working directory: {user_dir}
Searched paths: {file_path}
"""

# --------------------------------------------------------------------------------------

return_for_transform_ok = """# OK Code Transformation Complete

### Files:
- Original: `{source_file}`
- Analysis: {analysis}
- Transform file should be {target_file_formatted}

### AgentCore Features Added:
{features_added_formatted}

GOAL: Use the above analysis to guide a minimal transformation to AgentCore format, preserving your original agent logic.

CAUTION: Please review the generated code to ensure it is correct before using. The code returned is a best-effort transformation and may require manual adjustments. Note that
user has requested preserve_logic-{preserve_logic_formatted}

### Next Steps:
1. OK Analysis Complete
2. Follow your GOAL to transform your code
3. Pending: Please check code to see if the right transformations were applied. You may need to either make minor or major adjustments.
4. Pending: After review 3: Use `deploy_agentcore_app` to deploy
5. Pending: Configure advanced features if needed
6. Pending: Check if agent is deployed and is ready to invoke
"""

# --------------------------------------------------------------------------------------

return_for_deploy_ok = """# Launch: Deploy {agent_name} - Choose Your Approach

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

# --------------------------------------------------------------------------------------

return_oauth_invoke_ok = """# Agent: OAuth Agent Invocation Successful (v2)

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

# --------------------------------------------------------------------------------------

return_oauth_error = """! Runtime SDK OAuth Limitation

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

# --------------------------------------------------------------------------------------

return_search_error = """# Search: No Existing Agent Configurations Found

### Search Path: `{path_resolved}`

### What This Means:
- No previously deployed agents found in this directory
- You can deploy new agents using `deploy_agentcore_app`
- Or analyze existing code with `analyze_agent_code`

### Next Steps:
1. Use `validate_agentcore_environment` to check your setup
2. Use `analyze_agent_code` to migrate existing agents
3. Use `deploy_agentcore_app` to deploy new agents
"""

# --------------------------------------------------------------------------------------

return_search_mcp_error = """# Search: Config Files Found But Invalid

Found {len(config_files)} config files but none were valid AgentCore configurations.

### Search Path: `{path_resolved}`
### Files Found: {[f.name for f in config_files]}

### Next Steps:
1. Check if config files are corrupted
2. Deploy new agents with `deploy_agentcore_app`
"""
