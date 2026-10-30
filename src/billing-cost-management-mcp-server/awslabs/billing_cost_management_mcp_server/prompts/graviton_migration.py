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

import json
from .decorator import finops_prompt
from fastmcp.prompts import Message
from typing import Dict, List


@finops_prompt(
    name='analyze_graviton_opportunities',
    description=(
        'Analyzes EC2 instances and other compute resources and identifies opportunities to '
        'migrate to AWS Graviton processors'
    ),
    tags={'cost-optimization', 'ec2', 'graviton'},
)
def graviton_migration_analysis(account_ids: str, region: str = '') -> List[Message]:  # type: ignore
    """Creates a structured conversation to guide the LLM through analyzing Graviton migration opportunities.

    Args:
        account_ids: AWS account ID(s) to analyze (comma-separated if multiple)
        region: Optional AWS region to focus on (default: all regions)

    Returns:
        List[Message]: A list of messages forming the prompt conversation
    """
    account_id_list = [aid.strip() for aid in account_ids.split(',') if aid.strip()]
    coh_filters: Dict[str, List[str]] = {'actionTypes': ['MigrateToGraviton']}
    if account_id_list:
        coh_filters['accountIds'] = account_id_list
    if region:
        coh_filters['regions'] = [region]
    filters = json.dumps(coh_filters)
    order_by = json.dumps({'dimension': 'EstimatedMonthlySavings', 'order': 'Desc'})
    arm64 = json.dumps(['AWS_ARM64'])

    messages = [
        Message(
            f"""I need to identify opportunities to migrate to AWS Graviton (ARM64) processors for cost savings.

Please analyze the following AWS account(s): {', '.join(account_id_list)}
{f'Focus on region: {region}' if region else 'Analyze all regions'}

Follow these steps:
1. Use `cost-optimization` `list_recommendation_summaries` with `group_by` 'ResourceType' and `filters` '{filters}' to count the Graviton migration recommendations and their estimated monthly savings per resource type.
2. Use `cost-optimization` `list_recommendations` with the same `filters` and `order_by` '{order_by}' to list them, highest savings first. Each recommendation carries `current_resource_type`, `recommended_resource_type`, `estimated_monthly_savings` and `implementation_effort`.
3. If Cost Optimization Hub is not enrolled (`cost-optimization` `list_enrollment_statuses`) or returns no Graviton recommendations, use `compute-optimizer` `get_ec2_instance_recommendations` with `cpu_vendor_architectures` '{arm64}', one call per account (`account_ids` takes one ID) and per region. Without `cpu_vendor_architectures`, Compute Optimizer ranks only options in the instance's current CPU architecture.
4. For each candidate, note compatibility considerations (the operating system, software and dependencies must support ARM64).
5. Summarize the findings with:
   - Number of resources that could migrate to Graviton, by resource type
   - Total estimated monthly savings, and annual savings (12 x monthly)
   - Recommendations grouped by the `implementation_effort` each one reports (do not grade effort yourself)
   - Top 5 resources with the highest estimated monthly savings
   If a result has `complete_dataset: false`, say that the totals are partial.

Present the results in a clear, actionable format with tables where appropriate."""
        ),
        Message(
            "I'll analyze the Graviton migration opportunities and provide a report with savings estimates and the implementation effort of each recommendation.",
            role='assistant',
        ),
    ]
    return messages
