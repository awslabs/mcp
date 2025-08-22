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

from .decorator import finops_prompt
from fastmcp.prompts.prompt import Message
from typing import List


@finops_prompt(
    name='analyze_graviton_opportunities',
    description='Analyzes EC2 instances and identifies opportunities to migrate to AWS Graviton processors',
    tags={'cost-optimization', 'ec2', 'graviton'},
)
def graviton_migration_analysis(
    account_ids: str, lookback_days: int = 14, region: str = ''
) -> List[Message]:  # type: ignore
    """Creates a structured conversation to guide the LLM through analyzing Graviton migration opportunities.

    Args:
        account_ids: AWS account ID(s) to analyze (comma-separated if multiple)
        lookback_days: Number of days to look back for usage data (default: 14)
        region: Optional AWS region to focus on (default: all regions)

    Returns:
        List[Message]: A list of messages forming the prompt conversation
    """
    # Convert comma-separated account IDs to a list for display
    account_id_list = [aid.strip() for aid in account_ids.split(',')]

    messages = [
        Message(
            f"""I need to identify opportunities to migrate EC2 instances to AWS Graviton processors for cost savings.

Please analyze the following AWS account(s): {', '.join(account_id_list)}
Lookback period for cost analysis: {lookback_days} days
{f'Focus on region: {region}' if region else 'Analyze all regions'}

Follow these steps:
1. Use compute_optimizer_get_ec2_instance_recommendations to retrieve instance recommendations
2. Filter the results to find instances with Graviton alternatives (look for m6g, c6g, r6g, etc. in recommendationOptions)
3. For each candidate instance:
   - Look at the potential monthly and annual savings
   - Assess migration complexity based on instance type and usage patterns
   - Note any compatibility considerations
4. Summarize the findings with:
   - Total number of instances that could benefit from Graviton migration
   - Total potential monthly and annual savings
   - Instances grouped by migration complexity (Easy, Medium, Complex)
   - Top 5 instances with highest savings potential

Present the results in a clear, actionable format with tables where appropriate."""
        ),
        Message(
            "I'll analyze the EC2 instances for Graviton migration opportunities and provide a comprehensive report with savings estimates and migration complexity assessment.",
            role='assistant',
        ),
    ]
    return messages
