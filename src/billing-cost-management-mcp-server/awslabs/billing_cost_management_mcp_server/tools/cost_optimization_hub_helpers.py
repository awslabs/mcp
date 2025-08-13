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

"""
Helper functions for AWS Cost Optimization Hub operations.

These functions handle the specific operations for the Cost Optimization Hub tool.
"""

from typing import Any, Dict, Optional
from fastmcp import Context
from ..utilities.aws_service_base import format_response

def format_currency_amount(amount: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Format currency amount for better readability.
    
    Args:
        amount: Currency amount from Cost Optimization Hub API
        
    Returns:
        Formatted currency amount dictionary
    """
    if not amount:
        return None
    
    return {
        "amount": amount.get("amount"),
        "currency": amount.get("currency"),
        "formatted": f"{amount.get('amount')} {amount.get('currency')}"
    }


def format_timestamp(timestamp: Any) -> Optional[str]:
    """Format a timestamp to ISO format string.
    
    Args:
        timestamp: Timestamp from Cost Optimization Hub API
        
    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return None

    return timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)


async def list_recommendations(
    ctx: Context,
    coh_client: Any,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    include_all_recommendations: Optional[bool] = None
) -> Dict[str, Any]:
    """List recommendations from Cost Optimization Hub.
    
    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        max_results: Maximum number of results to return
        next_token: Pagination token
        filters: Optional filters dictionary
        include_all_recommendations: Whether to include all recommendations
        
    Returns:
        Dict containing recommendations
    """
    # Prepare the request parameters
    request_params = {"includeAllRecommendations": include_all_recommendations or False}

    if max_results:
        request_params["maxResults"] = int(max_results)
    
    if next_token:
        request_params["nextToken"] = next_token
    
    if filters:
        request_params["filter"] = filters

    # Make the API call
    await ctx.info("Fetching recommendations from Cost Optimization Hub")
    response = coh_client.list_recommendations(**request_params)

    # Format the response for better readability
    formatted_response = {
        "recommendations": [],
        "next_token": response.get("nextToken")
    }

    # Process recommendations
    for rec in response.get("recommendations", []):
        formatted_rec = {
            "resource_id": rec.get("resourceId"),
            "resource_type": rec.get("resourceType"),
            "account_id": rec.get("accountId"),
            "estimated_monthly_savings": format_currency_amount(rec.get("estimatedMonthlySavings")),
            "status": rec.get("status"),
            "last_refresh_timestamp": format_timestamp(rec.get("lastRefreshTimestamp")),
            "recommendation_id": rec.get("recommendationId"),
        }
        
        # Add source if present
        if "source" in rec:
            formatted_rec["source"] = rec.get("source")
            
        # Add lookback period if present
        if "lookbackPeriodInDays" in rec:
            formatted_rec["lookback_period_in_days"] = rec.get("lookbackPeriodInDays")
            
        formatted_response["recommendations"].append(formatted_rec)

    # Return formatted response
    return format_response("success", formatted_response)


async def get_recommendation(
    ctx: Context,
    coh_client: Any,
    resource_id: str,
    resource_type: str
) -> Dict[str, Any]:
    """Get detailed information about a specific recommendation.
    
    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        resource_id: Resource ID
        resource_type: Resource type
        
    Returns:
        Dict containing detailed recommendation information
    """
    # Prepare the request parameters
    request_params = {
        "resourceId": resource_id,
        "resourceType": resource_type
    }

    # Make the API call
    await ctx.info(f"Fetching recommendation for resource {resource_id} of type {resource_type}")
    response = coh_client.get_recommendation(**request_params)

    # Format the recommendation for better readability
    recommendation = response.get("recommendation", {})
    
    formatted_response = {
        "resource_id": recommendation.get("resourceId"),
        "resource_type": recommendation.get("resourceType"),
        "account_id": recommendation.get("accountId"),
        "estimated_monthly_savings": format_currency_amount(recommendation.get("estimatedMonthlySavings")),
        "status": recommendation.get("status"),
        "last_refresh_timestamp": format_timestamp(recommendation.get("lastRefreshTimestamp")),
        "recommendation_id": recommendation.get("recommendationId"),
    }
    
    # Add source if present
    if "source" in recommendation:
        formatted_response["source"] = recommendation.get("source")
        
    # Add lookback period if present
    if "lookbackPeriodInDays" in recommendation:
        formatted_response["lookback_period_in_days"] = recommendation.get("lookbackPeriodInDays")
    
    # Add current resource details
    current_resource = recommendation.get("currentResource", {})
    formatted_response["current_resource"] = {
        "resource_details": current_resource.get("resourceDetails", {})
    }
    
    # Add recommended resource details
    recommended_resources = []
    for recommended in recommendation.get("recommendedResources", []):
        recommended_resource = {
            "resource_details": recommended.get("resourceDetails", {}),
            "estimated_monthly_savings": format_currency_amount(recommended.get("estimatedMonthlySavings")),
        }
        
        # Add cost breakdown if present
        if "costBreakdown" in recommended:
            cost_breakdown = []
            for breakdown in recommended.get("costBreakdown", []):
                cost_breakdown.append({
                    "description": breakdown.get("description"),
                    "amount": format_currency_amount(breakdown.get("amount"))
                })
            recommended_resource["cost_breakdown"] = cost_breakdown
        
        recommended_resources.append(recommended_resource)
    
    formatted_response["recommended_resources"] = recommended_resources
    
    # Add implementation steps if present
    if "implementationEffort" in recommendation:
        implementation = recommendation.get("implementationEffort", {})
        formatted_response["implementation_effort"] = {
            "effort_level": implementation.get("effortLevel"),
            "required_actions": implementation.get("requiredActions", [])
        }

    # Return formatted response
    return format_response("success", formatted_response)


async def list_recommendation_summaries(
    ctx: Context,
    coh_client: Any,
    group_by: str,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """List recommendation summaries from Cost Optimization Hub.
    
    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        max_results: Maximum number of results to return
        next_token: Pagination token
        filters: Optional filters dictionary
        group_by: Grouping parameter
        
    Returns:
        Dict containing recommendation summaries
    """
    # Prepare the request parameters
    request_params = {"groupBy": group_by}

    if max_results:
        request_params["maxResults"] = int(max_results)
    
    if next_token:
        request_params["nextToken"] = next_token
    
    if filters:
        request_params["filter"] = filters

    # Make the API call
    await ctx.info(f"Fetching recommendation summaries grouped by {group_by}")
    response = coh_client.list_recommendation_summaries(**request_params)

    # Format the response for better readability
    formatted_response = {
        "summaries": [],
        "next_token": response.get("nextToken")
    }

    # Process recommendation summaries
    for summary in response.get("summaries", []):
        formatted_summary = {
            "dimension_value": summary.get("dimensionValue"),
            "recommendation_count": summary.get("recommendationCount"),
            "estimated_monthly_savings": format_currency_amount(summary.get("estimatedMonthlySavings")),
        }
        
        formatted_response["summaries"].append(formatted_summary)

    # Return formatted response
    return format_response("success", formatted_response)