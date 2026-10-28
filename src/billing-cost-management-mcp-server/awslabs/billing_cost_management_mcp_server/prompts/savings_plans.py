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
from typing import List


# get_savings_plans_purchase_recommendation accepts only these lookback periods.
_LOOKBACK_PERIODS = {7: 'SEVEN_DAYS', 30: 'THIRTY_DAYS', 60: 'SIXTY_DAYS'}
# Savings Plans terms; the API has no other term lengths.
_TERMS = {1: 'ONE_YEAR', 3: 'THREE_YEARS'}
# The API shape also lists LIGHT/MEDIUM/HEAVY_UTILIZATION (Reserved Instances only); Cost Explorer
# rejects them for Savings Plans.
_PAYMENT_OPTIONS = ('NO_UPFRONT', 'PARTIAL_UPFRONT', 'ALL_UPFRONT')


@finops_prompt(
    name='analyze_savings_plans_opportunities',
    description='Analyzes AWS usage and identifies opportunities for Savings Plans purchases',
    tags={'cost-optimization', 'savings-plans', 'commitment-discounts'},
)
def savings_plans_analysis(
    account_ids: str,
    lookback_days: int = 30,
    term_in_years: int = 1,
    payment_option: str = 'NO_UPFRONT',
) -> List[Message]:  # type: ignore
    """Creates a structured conversation to guide the LLM through analyzing Savings Plans purchase opportunities.

    Args:
        account_ids: AWS account ID(s) to analyze (comma-separated if multiple)
        lookback_days: Days of usage the recommendation is based on: 7, 30 or 60 (default: 30;
            other values use the closest of these)
        term_in_years: Savings Plans term length in years (1 or 3, default: 1)
        payment_option: NO_UPFRONT, PARTIAL_UPFRONT or ALL_UPFRONT (default: NO_UPFRONT)

    Returns:
        List[Message]: A list of messages forming the prompt conversation
    """
    account_id_list = [aid.strip() for aid in account_ids.split(',') if aid.strip()]
    lookback_days = int(lookback_days)
    supported_days = min(_LOOKBACK_PERIODS, key=lambda days: abs(days - lookback_days))
    lookback_period = _LOOKBACK_PERIODS[supported_days]
    term_in_years = int(term_in_years)
    if term_in_years not in _TERMS:
        raise ValueError(f'term_in_years must be 1 or 3, got {term_in_years}')
    term = _TERMS[term_in_years]
    given_payment_option = payment_option
    payment_option = payment_option.strip().upper()
    if payment_option not in _PAYMENT_OPTIONS:
        raise ValueError(
            f'payment_option must be NO_UPFRONT, PARTIAL_UPFRONT or ALL_UPFRONT, got {given_payment_option!r}'
        )
    account_filter = (
        ' and `filter` '
        + json.dumps({'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': account_id_list}})
        if account_id_list
        else ''
    )

    messages = [
        Message(
            f"""I need to identify opportunities to purchase AWS Savings Plans to optimize costs.

Please analyze the following AWS account(s): {', '.join(account_id_list)}
Lookback period for usage analysis: {lookback_days} days{'' if supported_days == lookback_days else f' (recommendations support 7, 30 or 60 days; using {supported_days})'}
Savings Plans term length: {term_in_years} {'year' if term_in_years == 1 else 'years'}

Follow these steps:
1. Use `sp-recommendation` `get_savings_plans_purchase_recommendation` once per Savings Plans type you evaluate (`savings_plans_type` COMPUTE_SP, EC2_INSTANCE_SP, SAGEMAKER_SP or DATABASE_SP), with `term_in_years` {term}, `payment_option` {payment_option} and `lookback_period_in_days` {lookback_period}{account_filter}.
2. For each recommendation, report as returned:
   - HourlyCommitmentToPurchase, EstimatedMonthlySavingsAmount, EstimatedSavingsPercentage and EstimatedROI
   - EstimatedAverageUtilization of the new commitment
3. For the recommendations you present, use `sp-recommendation` `get_savings_plan_purchase_recommendation_details` with the `recommendation_detail_id` (the RecommendationDetailId of the recommendation) to check whether the commitment would go unused in some hours (hourly EstimatedNewCommitmentUtilization).
4. Use `sp-performance` to show the coverage and utilization of the Savings Plans already in place.
5. Summarize the findings with:
   - Total potential monthly and annual savings
   - Recommended commitment amounts by Savings Plans type
   - Risk of unused commitment, based on the hourly utilization from step 3
   - When the recommendations were generated (they are precomputed and may predate recent purchases)

Present the results in a clear, actionable format with tables where appropriate."""
        ),
        Message(
            "I'll analyze the AWS usage patterns and provide a comprehensive report on Savings Plans purchase opportunities with estimated savings and commitment recommendations.",
            role='assistant',
        ),
    ]
    return messages
