#!/usr/bin/env python3
"""GitHub MCP Client Integration for Code Owner Assignment.

======================================================

This module provides a wrapper around the GitHub MCP server for use in automation scripts.
It handles the MCP server communication and provides a clean Python interface.
"""

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


class GitHubMCPClient:
    """Client for interacting with the GitHub MCP server."""

    def __init__(self, github_token: str):
        """Initialize MCP Client."""
        self.github_token = github_token
        self.logger = logging.getLogger(__name__)
        self._mcp_config = self._create_mcp_config()

    def _create_mcp_config(self) -> Dict[str, Any]:
        """Create MCP configuration for GitHub server."""
        return {
            'mcpServers': {
                'github.com/github/github-mcp-server': {
                    'autoApprove': [],
                    'disabled': False,
                    'timeout': 60,
                    'type': 'stdio',
                    'command': 'docker',
                    'args': [
                        'run',
                        '-i',
                        '--rm',
                        '-e',
                        'GITHUB_PERSONAL_ACCESS_TOKEN',
                        'ghcr.io/github/github-mcp-server',
                    ],
                    'env': {'GITHUB_PERSONAL_ACCESS_TOKEN': self.github_token},
                }
            }
        }

    def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a GitHub MCP server tool via subprocess."""
        # Create temporary script to call MCP server
        script_content = f'''
import asyncio
import json
import sys
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

async def main():
    server_params = StdioServerParameters(
        command="docker",
        args=[
            "run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server"
        ],
        env={{"GITHUB_PERSONAL_ACCESS_TOKEN": "{self.github_token}"}}
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                result = await session.call_tool("{tool_name}", {json.dumps(arguments)})
                print(json.dumps(result.content[0].text if result.content else {{}}, indent=2))
    except Exception as e:
        print(json.dumps({{"error": str(e)}}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_script = f.name

            # Execute the script
            result = subprocess.run(
                [sys.executable, temp_script],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            # Clean up
            Path(temp_script).unlink()
            if result.returncode != 0:
                self.logger.error(f'MCP tool call failed: {result.stderr}')
                return {'error': result.stderr}
            return json.loads(result.stdout) if result.stdout.strip() else {}
        except subprocess.TimeoutExpired:
            self.logger.error(f'MCP tool call timed out for {tool_name}')
            return {'error': 'Timeout'}
        except json.JSONDecodeError as e:
            self.logger.error(f'Failed to parse MCP response: {e}')
            return {'error': f'JSON decode error: {e}'}
        except Exception as e:
            self.logger.error(f'MCP tool call failed: {e}')
            return {'error': str(e)}

    def search_issues(self, query: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """Search for issues using GitHub MCP server."""
        result = self._call_mcp_tool('search_issues', {'query': query, 'perPage': per_page})
        if 'error' in result:
            self.logger.error(f'Failed to search issues: {result["error"]}')
            return []
        return result.get('items', [])

    def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        assignees: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
    ) -> bool:
        """Update issue with assignees and/or labels."""
        update_data = {}
        if assignees:
            update_data['assignees'] = assignees
        if labels:
            update_data['labels'] = labels
        if not update_data:
            return False
        result = self._call_mcp_tool(
            'update_issue',
            {'owner': owner, 'repo': repo, 'issue_number': issue_number, **update_data},
        )
        if 'error' in result:
            self.logger.error(f'Failed to update issue #{issue_number}: {result["error"]}')
            return False
        return True

    def get_file_contents(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Get file contents from repository."""
        result = self._call_mcp_tool(
            'get_file_contents', {'owner': owner, 'repo': repo, 'path': path}
        )
        if 'error' in result:
            self.logger.error(f'Failed to get file {path}: {result["error"]}')
            return None
        return result.get('content', '')

    def add_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> bool:
        """Add a comment to an issue."""
        result = self._call_mcp_tool(
            'add_issue_comment',
            {'owner': owner, 'repo': repo, 'issue_number': issue_number, 'body': body},
        )
        if 'error' in result:
            self.logger.error(f'Failed to add comment to issue #{issue_number}: {result["error"]}')
            return False
        return True
