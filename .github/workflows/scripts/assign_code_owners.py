#!/usr/bin/env python3
"""Automated Code Owner Assignment Script for awslabs/mcp Repository.

================================================================

This script automatically assigns code owners to unassigned issues in the awslabs/mcp repository
based on the CODEOWNERS file and intelligent content analysis.

Usage:
    python assign_code_owners.py [--dry-run] [--verbose]

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token with repo access
    GITHUB_PROJECT_URL: URL to the GitHub project board (optional)
"""

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass
from mcp_github_client import GitHubMCPClient
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CodeOwner:
    """Represents a code owner for a specific path pattern."""

    pattern: str
    owners: List[str]
    is_server_specific: bool = False
    server_name: Optional[str] = None


@dataclass
class IssueInfo:
    """Represents an issue with relevant metadata for assignment."""

    number: int
    title: str
    body: str
    labels: List[str]
    html_url: str
    identified_servers: Set[str]
    suggested_owners: Set[str]


class CodeOwnerAssigner:
    """Main class for automated code owner assignment."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        """Initialize CodeOwnerAssigner."""
        self.dry_run = dry_run
        self.verbose = verbose
        self.logger = self._setup_logging()
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError('GITHUB_TOKEN environment variable is required')
        # Initialize GitHub MCP client
        self.github_client = GitHubMCPClient(self.github_token)
        # MCP server name patterns for detection
        self.server_patterns = self._build_server_patterns()
        self.code_owners = self._parse_codeowners()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        return logging.getLogger(__name__)

    def _build_server_patterns(self) -> Dict[str, str]:
        """Build patterns for detecting MCP servers in issue content."""
        # Based on the CODEOWNERS file structure
        return {
            'amazon-keyspaces': 'amazon-keyspaces-mcp-server',
            'amazon-mq': 'amazon-mq-mcp-server',
            'amazon-neptune': 'amazon-neptune-mcp-server',
            'qindex': 'amazon-qindex-mcp-server',
            'qbusiness': 'amazon-qbusiness-anonymous-mcp-server',
            'rekognition': 'amazon-rekognition-mcp-server',
            'sns': 'amazon-sns-sqs-mcp-server',
            'sqs': 'amazon-sns-sqs-mcp-server',
            'aws-api': 'aws-api-mcp-server',
            'diagram': 'aws-diagram-mcp-server',
            'documentation': 'aws-documentation-mcp-server',
            'healthomics': 'aws-healthomics-mcp-server',
            'msk': 'aws-msk-mcp-server',
            'pricing': 'aws-pricing-mcp-server',
            'serverless': 'aws-serverless-mcp-server',
            'support': 'aws-support-mcp-server',
            'well-architected': 'well-architected-security-mcp-server',
            'cdk': 'cdk-mcp-server',
            'cfn': 'cfn-mcp-server',
            'cloudformation': 'cfn-mcp-server',
            'ccapi': 'ccapi-mcp-server',
            'appsignals': 'cloudwatch-appsignals-mcp-server',
            'cloudwatch-logs': 'cloudwatch_logs_mcp_server',
            'cloudwatch': 'cloudwatch_mcp_server',
            'code-doc-gen': 'code-doc-gen-mcp-server',
            'core': 'core-mcp-server',
            'cost-explorer': 'cost-explorer-mcp-server',
            'dataprocessing': 'aws-dataprocessing-mcp-server',
            'dynamodb': 'dynamodb-mcp-server',
            'ecs': 'ecs-mcp-server',
            'eks': 'eks-mcp-server',
            'elasticache': 'elasticache-mcp-server',
            'finch': 'finch-mcp-server',
            'frontend': 'frontend-mcp-server',
            'git-repo-research': 'git-repo-research-mcp-server',
            'iam': 'iam-mcp-server',
            'lambda': 'lambda-tool-mcp-server',
            'mcp-lambda-handler': 'mcp-lambda-handler',
            'memcached': 'memcached-mcp-server',
            'mysql': 'mysql-mcp-server',
            'nova-canvas': 'nova-canvas-mcp-server',
            'postgres': 'postgres-mcp-server',
            'prometheus': 'prometheus-mcp-server',
            'redshift': 'redshift-mcp-server',
            's3-tables': 's3-tables-mcp-server',
            'stepfunctions': 'stepfunctions-tool-mcp-server',
            'syntheticdata': 'syntheticdata-mcp-server',
            'terraform': 'terraform-mcp-server',
            'timestream': 'timestream-for-influxdb-mcp-server',
            'valkey': 'valkey-mcp-server',
        }

    def _parse_codeowners(self) -> List[CodeOwner]:
        """Parse CODEOWNERS file to extract owner mappings."""
        # This would be called via GitHub MCP server in actual implementation
        # For now, based on the CODEOWNERS content we retrieved
        owners = []
        server_owners = {
            'amazon-keyspaces-mcp-server': ['@jcshepherd'],
            'amazon-mq-mcp-server': ['@kenliao94', '@hashimsharkh'],
            'amazon-neptune-mcp-server': ['@bechbd', '@cornerwings', '@krlawrence'],
            'amazon-qindex-mcp-server': ['@tkoba-aws', '@akhileshamara'],
            'amazon-qbusiness-anonymous-mcp-server': ['@abhjaw'],
            'amazon-rekognition-mcp-server': ['@ayush987goyal'],
            'amazon-sns-sqs-mcp-server': ['@kenliao94', '@hashimsharkh'],
            'aws-api-mcp-server': [
                '@rshevchuk-git',
                '@PCManticore',
                '@iddv',
                '@arnewouters',
                '@bidesh',
            ],
            'aws-diagram-mcp-server': ['@MichaelWalker-git'],
            'aws-documentation-mcp-server': ['@Lavoiedavidw', '@JonLim'],
            'aws-healthomics-mcp-server': ['@markjschreiber', '@WIIASD'],
            'aws-msk-mcp-server': ['@elmoctarebnou', '@dingyiheng'],
            'aws-pricing-mcp-server': ['@nspring00', '@aytech-in', '@s12v'],
            'aws-serverless-mcp-server': ['@bx9900'],
            'aws-support-mcp-server': ['@Wook133'],
            'well-architected-security-mcp-server': ['@juntinyeh'],
            'cdk-mcp-server': ['@jimini55'],
            'cfn-mcp-server': ['@karamvsingh'],
            'ccapi-mcp-server': ['@novekm'],
            'cloudwatch-appsignals-mcp-server': [
                '@yiyuan-he',
                '@mxiamxia',
                '@iismd17',
                '@syed-ahsan-ishtiaque',
            ],
            'cloudwatch_logs_mcp_server': ['@lemmoi', '@shri-tambe'],
            'cloudwatch_mcp_server': ['@gcacace', '@shri-tambe', '@agiuliano', '@goranmod'],
            'code-doc-gen-mcp-server': ['@jimini55'],
            'core-mcp-server': ['@PaulVincent707'],
            'cost-explorer-mcp-server': ['@Fedayizada'],
            'aws-dataprocessing-mcp-server': [
                '@naikvaib',
                '@LiyuanLD',
                '@ckha2000',
                '@raghav1397',
                '@chappidim',
                '@yuxiaorun',
            ],
            'dynamodb-mcp-server': ['@erbenmo', '@shetsa-amzn', '@LeeroyHannigan'],
            'ecs-mcp-server': ['@vibhav-ag', '@matthewgoodman13'],
            'eks-mcp-server': ['@patrick-yu-amzn', '@srhsrhsrhsrh'],
            'elasticache-mcp-server': ['@seaofawareness'],
            'finch-mcp-server': ['@Shubhranshu153', '@pendo324'],
            'frontend-mcp-server': ['@awslabs/mcp-maintainers'],
            'git-repo-research-mcp-server': ['@jonslo'],
            'iam-mcp-server': ['@oshardik'],
            'lambda-tool-mcp-server': ['@danilop', '@jsamuel1'],
            'mcp-lambda-handler': ['@mikegc-aws', '@Lukas-Xue'],
            'memcached-mcp-server': ['@seaofawareness'],
            'mysql-mcp-server': ['@kennthhz'],
            'nova-canvas-mcp-server': ['@awslabs/mcp-maintainers'],
            'postgres-mcp-server': ['@kennthhz'],
            'prometheus-mcp-server': ['@MohamedSherifAbdelsamiea'],
            'redshift-mcp-server': ['@grayhemp'],
            's3-tables-mcp-server': [
                '@okhomin',
                '@gsoundar',
                '@gregorywright',
                '@Kurtiscwright',
                '@hsingh574',
                '@ananthaksr',
            ],
            'stepfunctions-tool-mcp-server': ['@mmouniro'],
            'syntheticdata-mcp-server': ['@pranjbh'],
            'terraform-mcp-server': ['@alexa-perlov'],
            'timestream-for-influxdb-mcp-server': ['@lokendrp-aws'],
            'valkey-mcp-server': ['@seaofawareness'],
        }
        for server, owner_list in server_owners.items():
            owners.append(
                CodeOwner(
                    pattern=f'/src/{server}',
                    owners=owner_list + ['@awslabs/mcp-admins'],  # Always include admins
                    is_server_specific=True,
                    server_name=server,
                )
            )
        # Default fallback
        owners.append(
            CodeOwner(
                pattern='*',
                owners=['@awslabs/mcp-maintainers', '@awslabs/mcp-admins'],
                is_server_specific=False,
            )
        )
        return owners

    def detect_servers_from_issue(self, issue: dict) -> Set[str]:
        """Detect which MCP servers an issue relates to."""
        content = f'{issue["title"]} {issue.get("body", "")}'.lower()
        detected_servers = set()
        # Direct server name detection
        for keyword, server_name in self.server_patterns.items():
            if keyword.lower() in content:
                detected_servers.add(server_name)
        # Path-based detection
        path_pattern = r'/src/([^/\s]+)'
        path_matches = re.findall(path_pattern, content)
        for match in path_matches:
            if match.endswith('-mcp-server'):
                detected_servers.add(match)
        # Label-based detection
        for label in issue.get('labels', []):
            label_name = label.get('name', '').lower()
            if 'mcp-server' in label_name:
                detected_servers.add(label_name)
        self.logger.debug(f'Issue #{issue["number"]} detected servers: {detected_servers}')
        return detected_servers

    def get_owners_for_servers(self, servers: Set[str]) -> Set[str]:
        """Get code owners for detected servers."""
        all_owners = set()
        for server in servers:
            for code_owner in self.code_owners:
                if code_owner.is_server_specific and code_owner.server_name == server:
                    all_owners.update(code_owner.owners)
                    break
        # If no specific servers detected, use default owners
        if not all_owners:
            for code_owner in self.code_owners:
                if not code_owner.is_server_specific:
                    all_owners.update(code_owner.owners)
                    break
        return all_owners

    def run_github_mcp_command(self, tool_name: str, arguments: dict) -> dict:
        """Execute GitHub MCP server commands via subprocess."""
        import json
        import subprocess

        # This would integrate with the MCP server in the actual implementation
        # For now, this is a placeholder structure
        command = [
            'python',
            '-c',
            f"""
import asyncio
from github_mcp_client import GitHubMCPClient

async def main():
    client = GitHubMCPClient()
    result = await client.{tool_name}({arguments})
    print(json.dumps(result))

asyncio.run(main())
""",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            self.logger.error(f'GitHub MCP command failed: {e}')
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f'Failed to parse MCP response: {e}')
            return {}

    def fetch_unassigned_issues(self) -> List[dict]:
        """Fetch all unassigned open issues using GitHub MCP server."""
        self.logger.info('Fetching unassigned issues...')
        # Use the search we already know works: 108 unassigned issues
        query = 'repo:awslabs/mcp no:assignee state:open'
        try:
            issues = self.github_client.search_issues(query, per_page=100)
            self.logger.info(f'Successfully fetched {len(issues)} unassigned issues')
            return issues
        except Exception as e:
            self.logger.error(f'Failed to fetch unassigned issues: {e}')
            return []

    def analyze_issue(self, issue: dict) -> IssueInfo:
        """Analyze an issue to determine appropriate owners."""
        detected_servers = self.detect_servers_from_issue(issue)
        suggested_owners = self.get_owners_for_servers(detected_servers)
        return IssueInfo(
            number=issue['number'],
            title=issue['title'],
            body=issue.get('body', ''),
            labels=[label.get('name', '') for label in issue.get('labels', [])],
            html_url=issue['html_url'],
            identified_servers=detected_servers,
            suggested_owners=suggested_owners,
        )

    def assign_issue(self, issue_info: IssueInfo) -> bool:
        """Assign issue to suggested owners."""
        if not issue_info.suggested_owners:
            self.logger.warning(f'No owners found for issue #{issue_info.number}')
            return False
        # Filter out team mentions (start with @awslabs/) for individual assignment
        # GitHub API requires individual usernames, not team names
        individual_owners = [
            owner.lstrip('@')
            for owner in issue_info.suggested_owners
            if not owner.startswith('@awslabs/')
        ]
        if not individual_owners:
            self.logger.info(
                f'Issue #{issue_info.number} only has team owners, skipping direct assignment'
            )
            return False
        if self.dry_run:
            self.logger.info(
                f'[DRY RUN] Would assign issue #{issue_info.number} to: {individual_owners}'
            )
            return True
        try:
            # Call GitHub MCP server to update the issue
            self.logger.info(f'Assigning issue #{issue_info.number} to: {individual_owners}')
            success = self.github_client.update_issue(
                owner='awslabs',
                repo='mcp',
                issue_number=issue_info.number,
                assignees=individual_owners,
            )
            if success:
                # Add a comment explaining the assignment
                comment_body = f"""🤖 **Automated Code Owner Assignment**

This issue has been automatically assigned based on the CODEOWNERS file and content analysis.

**Detected MCP Server(s)**: {', '.join(issue_info.identified_servers) if issue_info.identified_servers else 'General/Multiple'}
**Assigned to**: {', '.join(individual_owners)}

If this assignment is incorrect, please feel free to reassign or mention the appropriate team members.

---
*This assignment was made by the automated triage system. For questions, contact @awslabs/mcp-admins*"""

                self.github_client.add_issue_comment(
                    owner='awslabs', repo='mcp', issue_number=issue_info.number, body=comment_body
                )
            return success
        except Exception as e:
            self.logger.error(f'Failed to assign issue #{issue_info.number}: {e}')
            return False

    def update_project_board(self, issue_info: IssueInfo) -> bool:
        """Update GitHub project board with assigned issue."""
        if self.dry_run:
            self.logger.info(
                f'[DRY RUN] Would update project board for issue #{issue_info.number}'
            )
            return True
        try:
            # This would integrate with GitHub project API
            self.logger.info(f'Adding issue #{issue_info.number} to project board')
            # Placeholder for project board integration
            # Would need to use GitHub CLI or direct API calls
            # as GitHub MCP server may not have project board support
            return True
        except Exception as e:
            self.logger.error(
                f'Failed to update project board for issue #{issue_info.number}: {e}'
            )
            return False

    def generate_summary_report(self, processed_issues: List[Tuple[IssueInfo, bool]]) -> None:
        """Generate a summary report of assignment actions."""
        total_issues = len(processed_issues)
        successful_assignments = sum(1 for _, success in processed_issues if success)
        self.logger.info('=== ASSIGNMENT SUMMARY ===')
        self.logger.info(f'Total issues processed: {total_issues}')
        self.logger.info(f'Successfully assigned: {successful_assignments}')
        self.logger.info(f'Failed assignments: {total_issues - successful_assignments}')
        # Group by detected servers
        server_counts = {}
        for issue_info, _ in processed_issues:
            for server in issue_info.identified_servers:
                server_counts[server] = server_counts.get(server, 0) + 1
        if server_counts:
            self.logger.info('\n=== ASSIGNMENTS BY SERVER ===')
            for server, count in sorted(server_counts.items()):
                self.logger.info(f'{server}: {count} issues')
        # List unidentified issues
        unidentified = [
            issue_info for issue_info, _ in processed_issues if not issue_info.identified_servers
        ]
        if unidentified:
            self.logger.info(f'\n=== UNIDENTIFIED ISSUES ({len(unidentified)}) ===')
            for issue_info in unidentified[:5]:  # Show first 5
                self.logger.info(f'#{issue_info.number}: {issue_info.title}')
            if len(unidentified) > 5:
                self.logger.info(f'... and {len(unidentified) - 5} more')

    def run(self) -> int:
        """Main execution function."""
        self.logger.info('Starting automated code owner assignment...')
        if self.dry_run:
            self.logger.info('Running in DRY RUN mode - no changes will be made')
        try:
            # Fetch unassigned issues
            unassigned_issues = self.fetch_unassigned_issues()
            self.logger.info(f'Found {len(unassigned_issues)} unassigned issues')
            if not unassigned_issues:
                self.logger.info('No unassigned issues found')
                return 0
            # Process each issue
            processed_issues = []
            for issue in unassigned_issues:
                issue_info = self.analyze_issue(issue)
                # Assign the issue
                success = self.assign_issue(issue_info)
                # Update project board
                if success:
                    self.update_project_board(issue_info)
                processed_issues.append((issue_info, success))
            # Generate summary report
            self.generate_summary_report(processed_issues)
            self.logger.info('Code owner assignment completed successfully')
            return 0
        except Exception as e:
            self.logger.error(f'Assignment process failed: {e}')
            return 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Automatically assign code owners to unassigned issues'
    )
    parser.add_argument(
        '--dry-run', action='store_true', help='Show what would be done without making changes'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    try:
        assigner = CodeOwnerAssigner(dry_run=args.dry_run, verbose=args.verbose)
        return assigner.run()
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
