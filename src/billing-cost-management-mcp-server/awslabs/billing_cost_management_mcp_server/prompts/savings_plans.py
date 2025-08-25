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
    name='analyze_savings_plans_opportunities',
    description='Analyzes AWS usage and identifies opportunities for Savings Plans purchases',
    tags={'cost-optimization', 'savings-plans', 'commitment-discounts'},
)
def savings_plans_analysis(
    account_ids: str, lookback_days: int = 30, term_in_years: int = 1
) -> List[Message]:  # type: ignore
    """Creates a structured conversation to guide the LLM through analyzing Savings Plans purchase opportunities.

    Args:
        account_ids: AWS account ID(s) to analyze (comma-separated if multiple)
        lookback_days: Number of days to look back for usage data (default: 30)
        term_in_years: Savings Plans term length in years (1 or 3, default: 1)

    Returns:
        List[Message]: A list of messages forming the prompt conversation
    """
    # Convert comma-separated account IDs to a list for display
    account_id_list = [aid.strip() for aid in account_ids.split(',')]

    messages = [
        Message(
            f"""I need to identify opportunities to purchase AWS Savings Plans to optimize costs.

Please analyze the following AWS account(s): {', '.join(account_id_list)}
Lookback period for usage analysis: {lookback_days} days
Savings Plans term length: {term_in_years} {'year' if term_in_years == 1 else 'years'}

Follow these steps:
1. Use cost_explorer_get_savings_plans_purchase_recommendation to retrieve Savings Plans recommendations
2. For each recommendation:
   - Calculate the estimated savings amount and percentage
   - Determine the commitment amount required
   - Analyze the break-even point
3. Summarize the findings with:
   - Total potential monthly and annual savings
   - Recommended commitment amounts by Savings Plans type
   - ROI analysis for each recommendation
   - Risk assessment based on historical usage patterns

Present the results in a clear, actionable format with tables where appropriate."""
        ),
        Message(
            "I'll analyze the AWS usage patterns and provide a comprehensive report on Savings Plans purchase opportunities with estimated savings and commitment recommendations.",
            role='assistant',
        ),
    ]
    return messages
