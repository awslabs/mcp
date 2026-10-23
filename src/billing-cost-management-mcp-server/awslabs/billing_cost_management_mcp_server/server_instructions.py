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
"""Server instructions built from the tools and prompts the server actually serves.

The TOOLS and PROMPTS sections are generated from ``list_tools()`` / ``list_prompts()``
when the server starts (see ``server.py``'s lifespan), so they name exactly what is
mounted. Each tool gets a one-line blurb from ``TOOL_BLURBS``; a tool without one falls
back to the first sentence of its description, so a new tool is never left out.
``tests/test_server_instructions.py`` keeps ``TOOL_BLURBS`` and the mounted tools equal.
"""

import re
from typing import Iterable, Mapping, Optional


# One line per tool, for routing between tools. The full contract stays in each
# tool's description.
TOOL_BLURBS = {
    'cost-explorer': 'Historical cost and usage data with flexible filtering, grouping and forecasts',
    'compute-optimizer': (
        'Performance-based rightsizing recommendations for EC2, Auto Scaling groups, EBS, '
        'Lambda, RDS and ECS, including Graviton (ARM64) options'
    ),
    'compute-optimizer-automation': (
        'Compute Optimizer Automation rules, events, recommended actions, and rule previews '
        '(implementing Compute Optimizer recommendations automatically via rules or on demand)'
    ),
    'cost-optimization': (
        'Cost Optimization Hub savings recommendations across AWS services (idle resources, '
        'rightsizing, Graviton migration, Savings Plans and Reserved Instances) and the '
        'cost efficiency score'
    ),
    'storage-lens': 'Query S3 Storage Lens metrics data using Athena SQL',
    'aws-pricing': 'AWS service pricing information from the AWS Price List API',
    'bcm-pricing-calc': (
        'Work with workload estimates from AWS Billing and Cost Management Pricing Calculator'
    ),
    'budgets': 'AWS Budgets: budget limits, actual and forecasted spend',
    'budget-actions': 'Enforcement actions attached to AWS Budgets',
    'budget-notifications': 'Alert thresholds (notifications) configured on AWS Budgets',
    'cost-anomaly': 'Cost anomalies detected by AWS Cost Anomaly Detection',
    'cost-comparison': 'Compare costs between two one-month periods and the drivers of the change',
    'free-tier-usage': 'Monitor AWS Free Tier usage',
    'rec-details': (
        'One Cost Optimization Hub recommendation enriched with Compute Optimizer metrics '
        'and Cost Explorer purchase recommendations'
    ),
    'ri-performance': 'Analyze Reserved Instance coverage and utilization',
    'sp-performance': 'Analyze Savings Plans coverage and utilization',
    'sp-explorer': (
        'Describe the Savings Plans an account owns, including queued, returned, and '
        'payment-failed plans that Cost Explorer does not report, plus rates on owned plans '
        'and the offerings available to purchase'
    ),
    'sp-recommendation': (
        'Get Savings Plans purchase recommendations, the hourly data-points behind one, and '
        'the recommendation generation history'
    ),
    'sp-purchase-analyzer': (
        'Run Savings Plans Purchase Analyzer what-if analyses (max savings, custom commitment, '
        'target average coverage) and retrieve their results'
    ),
    'session-sql': (
        'Execute SQL queries on the session database. A tool response too large to return '
        'inline is stored in SQL and replaced by a handle card (`data_stored: true`, '
        '`table_name`, `query_tool`, `sample_queries`); query the table named in the result '
        'with the tool named in `query_tool`.'
    ),
    'list-billing-groups': 'AWS Billing Conductor billing groups',
    'list-account-associations': 'Linked accounts associated with AWS Billing Conductor billing groups',
    'list-billing-group-cost-reports': (
        'AWS Billing Conductor billing group cost reports (actual vs pro forma charges)'
    ),
    'get-billing-group-cost-report': (
        "One billing group's pro forma margin report, broken down by service or billing period"
    ),
    'list-custom-line-items': 'AWS Billing Conductor custom line items',
    'list-custom-line-item-versions': 'Versions of an AWS Billing Conductor custom line item',
    'list-resources-associated-to-custom-line-item': (
        'Resources associated with an AWS Billing Conductor custom line item'
    ),
    'list-pricing-rules': 'AWS Billing Conductor pricing rules',
    'list-pricing-plans': 'AWS Billing Conductor pricing plans',
    'list-pricing-rules-for-plan': 'Pricing rules in an AWS Billing Conductor pricing plan',
    'list-pricing-plans-for-rule': 'AWS Billing Conductor pricing plans that use a pricing rule',
    'get-billing-transfer-preference': (
        'Auto billing group creation preference for an inbound billing transfer'
    ),
    'get-billing-view': 'Metadata of one AWS billing view (read-only)',
    'list-billing-views': 'Billing views available for a time period (read-only)',
    'list-source-views-for-billing-view': (
        'Source views a custom billing view is built from (read-only)'
    ),
    'get-resource-policy': 'Resource-based policy attached to a billing view (read-only)',
    'list-billing-view-segments': 'Segments of a billing view over a time period (read-only)',
    'list-cost-allocation-tags': 'Cost allocation tags and their activation status',
    'list-cost-allocation-tag-backfill-history': 'History of cost allocation tag backfill requests',
    'describe-cost-category-definition': 'Full definition (rules) of one cost category',
    'list-cost-category-definitions': 'Cost category definitions in the account',
    'invoicing': (
        'AWS Invoicing data — invoice summaries with amounts, tax, discounts/fees, currency/FX, '
        'due dates, PO numbers, and credit memos'
    ),
    'invoice-units': (
        'AWS invoice units: groups of accounts that receive a separate invoice (read-only)'
    ),
    'procurement-preferences': (
        'AWS Procurement Portal preferences: portal connections and e-invoice / purchase-order '
        'settings (read-only)'
    ),
    'credits': (
        'AWS Billing credits — credit balance, expiration, product applicability, sharing '
        'configuration, and the per-service allocation ledger'
    ),
    'get-billing-preferences': (
        'Billing preferences: Reserved Instance / Savings Plans and credit sharing, billing '
        'alerts, and their change history'
    ),
    'enterprise-support': (
        'AWS Enterprise Support charge data for a closed billing period — the Support charge and '
        'the Support-eligible spend it was calculated from, the contract terms that govern how '
        'the charge is allocated, and the per-linked-account breakdown'
    ),
}

PREAMBLE = """AWS Billing and Cost Management MCP Server - Provides AWS cost optimization tools and prompts through MCP.

Unless the user or the host's instructions specify otherwise:
1. Use the UnblendedCost metric
2. Exclude Credits and Refunds
3. Be concise and focus on essential information first
4. For optimization queries, lead with the highest-impact recommendations; when truncating, state how many were omitted and their combined savings

Available components:"""

GUIDANCE = """For financial analysis:
1. Start with a high-level view of costs using cost-explorer with the SERVICE dimension
2. Look for cost optimization opportunities with cost-optimization or compute-optimizer
3. For S3-specific optimizations, use storage-lens
4. For budget monitoring, use budgets
5. For anomaly detection, use cost-anomaly

For optimization recommendations:
1. Use cost-optimization for cost savings recommendations across services, including idle resources, rightsizing, Graviton migration, and Savings Plans / Reserved Instances purchases.
2. Use cost-optimization `get_recommendation` for one Cost Optimization Hub recommendation; use rec-details only when Compute Optimizer and Cost Explorer enrichment is wanted.
3. Use compute-optimizer for performance-based recommendations for compute resources such as EC2, ECS, EBS, Lambda, RDS, and Auto Scaling groups.
4. Use ri-performance and sp-performance to analyze existing Reserved Instances and Savings Plans.

For multi-account environments:
- Include the LINKED_ACCOUNT dimension in cost-explorer queries
- compute-optimizer takes `account_ids` as a JSON array with one account ID per call; make one call per account
- cost-optimization takes accounts in `filters`, e.g. '{"accountIds": ["123456789012"]}'; its top-level `account_id` applies only to `list_enrollment_statuses`"""


def first_sentence(description: Optional[str]) -> str:
    """Return the first sentence of a tool description, whitespace-collapsed."""
    text = ' '.join((description or '').split())
    return re.split(r'(?<=[.!?])\s', text, maxsplit=1)[0].rstrip('.')


def build_instructions(
    tools: Iterable,
    prompts: Iterable,
    blurbs: Optional[Mapping[str, str]] = None,
) -> str:
    """Build the server instructions from the served tools and prompts.

    Args:
        tools: Served tools (objects with ``name`` and ``description``), in listing order.
        prompts: Served prompts (objects with ``name`` and ``description``).
        blurbs: Tool name -> one-line blurb. Defaults to ``TOOL_BLURBS``. Blurbs for tools
            that are not served are ignored.
    """
    blurbs = TOOL_BLURBS if blurbs is None else blurbs
    tool_lines = [
        f'- {tool.name}: {blurbs.get(tool.name) or first_sentence(tool.description)}'
        for tool in tools
    ]
    prompt_lines = [f'- {prompt.name}: {prompt.description or ""}'.rstrip() for prompt in prompts]
    sections = [PREAMBLE, 'TOOLS:\n' + '\n'.join(tool_lines)]
    if prompt_lines:
        sections.append('PROMPTS:\n' + '\n'.join(prompt_lines))
    sections.append(GUIDANCE)
    return '\n\n'.join(sections) + '\n'
