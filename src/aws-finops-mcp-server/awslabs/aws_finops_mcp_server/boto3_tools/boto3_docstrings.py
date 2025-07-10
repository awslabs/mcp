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

"""Combined docstrings for AWS FinOps MCP Server boto3 methods.

This file contains docstrings for all supported AWS services in the FinOps MCP Server,
organized in a single dictionary grouped by service name.
"""

boto3_docstrings = {
    'cost_optimization_hub': {
        'get_recommendation': """
        Returns both the current and recommended resource configuration and the estimated cost impact for a recommendation.

        The recommendationId is only valid for up to a maximum of 24 hours as recommendations are refreshed daily.
        To retrieve the recommendationId, use the ListRecommendations API.

        Parameters
        ----------
        recommendationId : str, required
            The ID for the recommendation. This ID is returned by the ListRecommendations API and
            is only valid for 24 hours as recommendations are refreshed daily.

        Returns
        -------
        dict
            Response containing detailed information about the recommendation including:
            - recommendationId: The unique identifier for the recommendation
            - resourceId: The ID of the resource associated with the recommendation
            - resourceArn: The ARN of the resource associated with the recommendation
            - accountId: The AWS account ID associated with the recommendation
            - currencyCode: The currency code used for cost calculations (e.g., 'USD')
            - recommendationLookbackPeriodInDays: The number of days used to generate the recommendation
            - costCalculationLookbackPeriodInDays: The number of days used to calculate costs
            - estimatedSavingsPercentage: The estimated percentage of savings
            - estimatedSavingsOverCostCalculationLookbackPeriod: The estimated savings amount over the lookback period
            - currentResourceType: The type of the current resource (e.g., 'Ec2Instance', 'LambdaFunction')
            - recommendedResourceType: The type of the recommended resource
            - region: The AWS region of the resource
            - source: The source of the recommendation ('ComputeOptimizer' or 'CostExplorer')
            - lastRefreshTimestamp: When the recommendation was last refreshed
            - estimatedMonthlySavings: The estimated monthly savings amount
            - estimatedMonthlyCost: The estimated monthly cost after implementing the recommendation
            - implementationEffort: The effort required to implement ('VeryLow', 'Low', 'Medium', 'High', 'VeryHigh')
            - restartNeeded: Whether implementing the recommendation requires a restart
            - actionType: The type of action recommended (e.g., 'Rightsize', 'Stop', 'Upgrade')
            - rollbackPossible: Whether the recommendation can be rolled back if implemented
            - currentResourceDetails: Detailed information about the current resource configuration
            - recommendedResourceDetails: Detailed information about the recommended resource configuration
        """,
        'list_recommendations': """
        Returns a list of recommendations based on specified filters.

        This API allows you to retrieve and filter cost optimization recommendations across multiple
        AWS regions and accounts in your organization.

        Parameters
        ----------
        filter : dict, optional
            The constraints that you want all returned recommendations to match.
            {
                'restartNeeded': True|False,  # Whether implementing requires a restart
                'rollbackPossible': True|False,  # Whether implementation can be rolled back
                'implementationEfforts': ['VeryLow'|'Low'|'Medium'|'High'|'VeryHigh'],  # Required effort
                'accountIds': ['string'],  # List of account IDs
                'regions': ['string'],  # List of AWS regions
                'resourceTypes': ['Ec2Instance'|'LambdaFunction'|'EbsVolume'|'EcsService'|...],  # Resource types
                'actionTypes': ['Rightsize'|'Stop'|'Upgrade'|'PurchaseSavingsPlans'|...],  # Action types
                'tags': [{'key': 'string', 'value': 'string'}],  # Resource tags
                'resourceIds': ['string'],  # List of resource IDs
                'resourceArns': ['string'],  # List of resource ARNs
                'recommendationIds': ['string']  # List of recommendation IDs
            }
        orderBy : dict, optional
            The ordering of recommendations by a dimension.
            {
                'dimension': 'string',  # Dimension to sort by
                'order': 'Asc'|'Desc'  # Sort order
            }
        includeAllRecommendations : bool, optional
            If True, returns all recommendations for a resource. If False (default),
            returns a single recommendation per resource (de-duped by resourceId).
        maxResults : int, optional
            The maximum number of recommendations to return (1-100).
            Default is 100.
        nextToken : str, optional
            The token to retrieve the next set of results.

        Returns
        -------
        dict
            Response containing a list of recommendations with the following structure:
            {
                'items': [  # List of recommendation objects
                    {
                        'recommendationId': 'string',  # Unique ID for the recommendation
                        'accountId': 'string',  # AWS account ID
                        'region': 'string',  # AWS region
                        'resourceId': 'string',  # Resource ID
                        'resourceArn': 'string',  # Resource ARN
                        'currentResourceType': 'string',  # Current resource type
                        'recommendedResourceType': 'string',  # Recommended resource type
                        'estimatedMonthlySavings': float,  # Estimated monthly savings
                        'estimatedSavingsPercentage': float,  # Savings as percentage
                        'estimatedMonthlyCost': float,  # Estimated monthly cost after implementation
                        'currencyCode': 'string',  # Currency code (e.g., 'USD')
                        'implementationEffort': 'string',  # Implementation effort level
                        'restartNeeded': bool,  # Whether restart is needed
                        'actionType': 'string',  # Type of action recommended
                        'rollbackPossible': bool,  # Whether rollback is possible
                        'source': 'string',  # Source of the recommendation
                        'lastRefreshTimestamp': datetime  # When recommendation was last refreshed
                    }
                ],
                'nextToken': 'string'  # Token for pagination
            }
        """,
        'list_recommendation_summaries': """
        Returns a concise representation of savings estimates for resources grouped by a specified dimension.

        This API provides aggregated savings information across different types of recommendations,
        allowing you to view potential savings by account, region, resource type, or other dimensions.

        Parameters
        ----------
        groupBy : str, required
            The grouping of recommendations by a dimension. Valid values include:
            - 'ACCOUNT_ID': Group by AWS account ID
            - 'REGION': Group by AWS region
            - 'RESOURCE_TYPE': Group by resource type
            - 'ACTION_TYPE': Group by action type
            - 'IMPLEMENTATION_EFFORT': Group by implementation effort
            - 'RESTART_NEEDED': Group by whether restart is needed
            - 'ROLLBACK_POSSIBLE': Group by whether rollback is possible
        filter : dict, optional
            Describes a filter that returns a more specific list of recommendations.
            {
                'restartNeeded': True|False,  # Whether implementing requires a restart
                'rollbackPossible': True|False,  # Whether implementation can be rolled back
                'implementationEfforts': ['VeryLow'|'Low'|'Medium'|'High'|'VeryHigh'],  # Required effort
                'accountIds': ['string'],  # List of account IDs
                'regions': ['string'],  # List of AWS regions
                'resourceTypes': ['Ec2Instance'|'LambdaFunction'|'EbsVolume'|'EcsService'|...],  # Resource types
                'actionTypes': ['Rightsize'|'Stop'|'Upgrade'|'PurchaseSavingsPlans'|...],  # Action types
                'tags': [{'key': 'string', 'value': 'string'}],  # Resource tags
            }
            Note: The 'recommendationIds', 'resourceArns', and 'resourceIds' filters are not supported for this API.
        maxResults : int, optional
            The maximum number of recommendation summaries to return (1-100).
            Default is 100.
        metrics : list, optional
            Additional metrics to be returned. Currently, the only valid value is 'SavingsPercentage'.
        nextToken : str, optional
            The token to retrieve the next set of results.

        Returns
        -------
        dict
            Response containing recommendation summaries grouped by the specified dimension:
            {
                'estimatedTotalDedupedSavings': float,  # Total estimated monthly savings across all recommendations
                'items': [  # List of recommendation summary objects
                    {
                        'group': 'string',  # The group value (e.g., account ID, region, resource type)
                        'estimatedMonthlySavings': float,  # Estimated monthly savings for this group
                        'recommendationCount': int,  # Number of recommendations in this group
                        'savingsPercentage': float  # Optional, only if requested in metrics parameter
                    }
                ],
                'nextToken': 'string'  # Token for pagination
            }

        Examples
        --------
        Group recommendations by account ID:

        ```python
        response = client.list_recommendation_summaries(
            groupBy='ACCOUNT_ID',
            filter={
                'resourceTypes': ['Ec2Instance', 'LambdaFunction']
            }
        )
        ```

        Group recommendations by resource type with savings percentage:

        ```python
        response = client.list_recommendation_summaries(
            groupBy='RESOURCE_TYPE',
            metrics=['SavingsPercentage']
        )
        ```
        """,
    },
    'compute_optimizer': {
        'get_auto_scaling_group_recommendations': """
        Returns Auto Scaling group recommendations.

        Compute Optimizer generates recommendations for Amazon EC2 Auto Scaling groups that meet a specific set of requirements.

        Parameters
        ----------
        accountIds : list, optional
            The ID of the AWS account for which to return Auto Scaling group recommendations.
            If your account is the management account of an organization, use this parameter to specify the member account.
            Only one account ID can be specified per request.
        autoScalingGroupArns : list, optional
            The Amazon Resource Name (ARN) of the Auto Scaling groups for which to return recommendations.
        nextToken : str, optional
            The token to advance to the next page of recommendations.
        maxResults : int, optional
            The maximum number of recommendations to return with a single call.
            To retrieve the remaining results, make another request with the returned nextToken value.
        filters : list, optional
            An array of objects that describe a filter to return a more specific list of recommendations.
            Specify 'Finding' to filter by finding classification (e.g., 'Optimized', 'NotOptimized').
            Specify 'RecommendationSourceType' to filter by resource type.
            Specify 'FindingReasonCodes' to filter by finding reason code (e.g., 'CPUUnderprovisioned').
            Specify 'InferredWorkloadTypes' to filter by inferred workload.
            You can also filter by tag:key and tag-key tags.
        recommendationPreferences : dict, optional
            Describes the recommendation preferences to return.
            Contains 'cpuVendorArchitectures' which specifies the CPU vendor and architecture
            (e.g., 'AWS_ARM64', 'CURRENT').

        Returns
        -------
        dict
            Response containing Auto Scaling group recommendations and metadata.
        """,
        'get_ebs_volume_recommendations': """
        Returns Amazon EBS volume recommendations.

        Compute Optimizer generates recommendations for Amazon EBS volumes that meet a specific set of requirements.

        Parameters
        ----------
        volumeArns : list, optional
            The Amazon Resource Name (ARN) of the volumes for which to return recommendations.
        nextToken : str, optional
            The token to advance to the next page of recommendations.
        maxResults : int, optional
            The maximum number of volume recommendations to return with a single call.
            To retrieve the remaining results, make another request with the returned nextToken value.
        filters : list, optional
            An array of objects that describe a filter to return a more specific list of recommendations.
            Specify 'Finding' to filter by finding classification (e.g., 'Optimized', 'NotOptimized').
            You can also filter by tag:key and tag-key tags.
            A tag:key is a key and value combination of a tag assigned to your recommendations.
            A tag-key is the key of a tag assigned to your recommendations.
        accountIds : list, optional
            The ID of the AWS account for which to return volume recommendations.
            If your account is the management account of an organization, use this parameter to specify the member account.
            Only one account ID can be specified per request.

        Returns
        -------
        dict
            Response containing EBS volume recommendations and metadata, including current configuration,
            finding classification, utilization metrics, and recommended configuration options.
        """,
        'get_ec2_instance_recommendations': """
        Returns Amazon EC2 instance recommendations.

        Compute Optimizer generates recommendations for Amazon EC2 instances that meet a specific set of requirements.

        Parameters
        ----------
        instanceArns : list, optional
            The Amazon Resource Name (ARN) of the instances for which to return recommendations.
        nextToken : str, optional
            The token to advance to the next page of recommendations.
        maxResults : int, optional
            The maximum number of instance recommendations to return with a single call.
            To retrieve the remaining results, make another request with the returned nextToken value.
        filters : list, optional
            An array of objects that describe a filter to return a more specific list of recommendations.
            Specify 'Finding' to filter by finding classification (e.g., 'Underprovisioned', 'Overprovisioned', 'Optimized').
            Specify 'RecommendationSourceType' to filter by resource type.
            Specify 'FindingReasonCodes' to filter by finding reason code (e.g., 'CPUUnderprovisioned').
            Specify 'InferredWorkloadTypes' to filter by inferred workload.
            You can also filter by tag:key and tag-key tags.
        accountIds : list, optional
            The ID of the AWS account for which to return instance recommendations.
            If your account is the management account of an organization, use this parameter to specify the member account.
            Only one account ID can be specified per request.
        recommendationPreferences : dict, optional
            Describes the recommendation preferences to return.
            Contains 'cpuVendorArchitectures' which specifies the CPU vendor and architecture
            (e.g., 'AWS_ARM64', 'CURRENT').

        Returns
        -------
        dict
            Response containing EC2 instance recommendations and metadata, including current configuration,
            finding classification, utilization metrics, and recommended instance types.
        """,
        'get_ecs_service_recommendations': """
        Returns Amazon ECS service recommendations.

        Compute Optimizer generates recommendations for Amazon ECS services on Fargate that meet a specific set of requirements.

        Parameters
        ----------
        serviceArns : list, optional
            The ARN that identifies the Amazon ECS service.
            Format: arn:aws:ecs:region:aws_account_id:service/cluster-name/service-name
        nextToken : str, optional
            The token to advance to the next page of recommendations.
        maxResults : int, optional
            The maximum number of service recommendations to return with a single call.
            To retrieve the remaining results, make another request with the returned nextToken value.
        filters : list, optional
            An array of objects that describe a filter to return a more specific list of recommendations.
            Specify 'Finding' to filter by finding classification (e.g., 'Optimized', 'Underprovisioned', 'Overprovisioned').
            Specify 'FindingReasonCode' to filter by finding reason code (e.g., 'CPUUnderprovisioned', 'MemoryOverprovisioned').
            You can also filter by tag:key and tag-key tags.
        accountIds : list, optional
            The ID of the AWS account for which to return ECS service recommendations.
            If your account is the management account of an organization, use this parameter to specify the member account.
            Only one account ID can be specified per request.

        Returns
        -------
        dict
            Response containing RDS database recommendations in the 'rdsDBRecommendations' field,
            including current database configuration, finding classification, and recommended configuration options.
        """,
        'get_rds_database_recommendations': """
        Returns Amazon Aurora and RDS database recommendations.

        Compute Optimizer generates recommendations for Amazon Aurora and RDS databases that meet a specific set of requirements.

        Parameters
        ----------
        resourceArns : list, optional
            The ARN that identifies the Amazon Aurora or RDS database.
            Format for DB instance: arn:aws:rds:{region}:{accountId}:db:{resourceName}
            Format for DB cluster: arn:aws:rds:{region}:{accountId}:cluster:{resourceName}
        nextToken : str, optional
            The token to advance to the next page of recommendations.
        maxResults : int, optional
            The maximum number of database recommendations to return with a single call.
            To retrieve the remaining results, make another request with the returned nextToken value.
        filters : list, optional
            An array of objects that describe a filter to return a more specific list of recommendations.
            Specify 'InstanceFinding', 'InstanceFindingReasonCode', 'StorageFinding', 'StorageFindingReasonCode', or 'Idle'
            to filter by different criteria.
            You can also filter by tag:key and tag-key tags.
        accountIds : list, optional
            The ID of the AWS account for which to return database recommendations.
            If your account is the management account of an organization, use this parameter to specify the member account.
            Only one account ID can be specified per request.
        recommendationPreferences : dict, optional
            Describes the recommendation preferences to return.
            Contains 'cpuVendorArchitectures' which specifies the CPU vendor and architecture
            (e.g., 'AWS_ARM64', 'CURRENT').

        Returns
        -------
        dict
            Response containing RDS database recommendations in the 'rdsDBRecommendations' field,
            including current configuration, finding classification, and recommended instance types.
        """,
        'get_lambda_function_recommendations': """
        Returns AWS Lambda function recommendations.

        Compute Optimizer generates recommendations for Lambda functions that meet a specific set of requirements.

        Parameters
        ----------
        functionArns : list, optional
            The Amazon Resource Name (ARN) of the Lambda functions for which to return recommendations.
            You can specify a qualified or unqualified ARN. If you specify an unqualified ARN without a function
            version suffix, Compute Optimizer will return recommendations for the latest ($LATEST) version of the function.
        accountIds : list, optional
            The ID of the AWS account for which to return function recommendations.
            If your account is the management account of an organization, use this parameter to specify the member account.
            Only one account ID can be specified per request.
        filters : list, optional
            An array of objects that describe a filter to return a more specific list of recommendations.
            Specify 'Finding' to filter by finding classification (e.g., 'Optimized', 'NotOptimized', 'Unavailable').
            Specify 'FindingReasonCode' to filter by finding reason code (e.g., 'MemoryOverprovisioned', 'MemoryUnderprovisioned').
            You can also filter by tag:key and tag-key tags.
        nextToken : str, optional
            The token to advance to the next page of recommendations.
        maxResults : int, optional
            The maximum number of recommendations to return with a single call.
            To retrieve the remaining results, make another request with the returned nextToken value.

        Returns
        -------
        dict
            Response containing Lambda function recommendations and metadata, including current configuration,
            finding classification, utilization metrics, and recommended memory sizes.
        """,
        'get_idle_recommendations': """
        Returns idle resource recommendations.

        Compute Optimizer generates recommendations for idle resources that meet a specific set of requirements.

        Parameters
        ----------
        resourceArns : list, optional
            The Amazon Resource Name (ARN) of the resources for which to return idle recommendations.
        nextToken : str, optional
            The token to advance to the next page of recommendations.
        maxResults : int, optional
            The maximum number of idle resource recommendations to return with a single call.
            To retrieve the remaining results, make another request with the returned nextToken value.
        filters : list, optional
            An array of objects that describe a filter to return a more specific list of recommendations.
            Specify 'Finding' to filter by finding classification.
            Specify 'ResourceType' to filter by resource type.
            You can also filter by tag:key and tag-key tags.
        accountIds : list, optional
            The ID of the AWS account for which to return idle resource recommendations.
            If your account is the management account of an organization, use this parameter to specify the member account.
            Only one account ID can be specified per request.
        orderBy : dict, optional
            The order to sort the idle resource recommendations.
            Contains 'dimension' (e.g., 'SavingsValue', 'SavingsValueAfterDiscount') and 'order' (e.g., 'Asc', 'Desc').

        Returns
        -------
        dict
            Response containing idle resource recommendations in the 'idleRecommendations' field,
            including resource details, finding classification, and savings opportunity information.
        """,
        'get_effective_recommendation_preferences': """
        Returns the recommendation preferences that are in effect for a given resource.

        Considers all applicable preferences that you might have set at the resource, account, and organization level.
        When you create a recommendation preference, you can set its status to 'Active' or 'Inactive'.
        Use this action to view the recommendation preferences that are in effect, or 'Active'.

        Parameters
        ----------
        resourceArn : str, required
            The Amazon Resource Name (ARN) of the resource for which to return recommendation preferences.
            This must be a valid ARN for a resource in your account. Example format for EC2 instance:
            arn:aws:ec2:{region}:{accountId}:instance/{instanceId}
            Only EC2 instance and Auto Scaling group ARNs are currently supported.

        Returns
        -------
        dict
            Response containing the effective recommendation preferences for the specified resource, including:
            - enhancedInfrastructureMetrics: Status of the enhanced infrastructure metrics preference
            - externalMetricsPreference: Provider of the external metrics recommendation preference
            - lookBackPeriod: Number of days the utilization metrics are analyzed
            - utilizationPreferences: Resource's CPU and memory utilization preferences
            - preferredResources: Preferred resources for recommendations
        """,
    },
    'cost_explorer': {
        'get_reservation_purchase_recommendation': """
        Gets recommendations for reservation purchases that could help you reduce your costs.

        AWS generates recommendations by identifying your On-Demand usage during a specific time period
        and collecting your usage into categories that are eligible for a reservation. After AWS has these
        categories, it simulates every combination of reservations to identify the best number of each
        type of Reserved Instance (RI) to purchase to maximize your estimated savings.

        Parameters
        ----------
        Service : str, required
            The specific service to get recommendations for (e.g., 'Amazon Redshift', 'Amazon RDS',
            'Amazon ElastiCache', 'Amazon OpenSearch').
        AccountId : str, optional
            The account ID that is associated with the recommendation.
        AccountScope : str, optional
            The account scope that you want your recommendations for.
            Valid values: 'PAYER' (includes management account and member accounts) or 'LINKED' (member accounts only).
        LookbackPeriodInDays : str, optional
            The number of previous days to analyze.
            Valid values: 'SEVEN_DAYS', 'THIRTY_DAYS', 'SIXTY_DAYS'.
        TermInYears : str, optional
            The reservation term in years.
            Valid values: 'ONE_YEAR', 'THREE_YEARS'.
        PaymentOption : str, optional
            The payment option for the reservation.
            Valid values: 'NO_UPFRONT', 'PARTIAL_UPFRONT', 'ALL_UPFRONT', 'LIGHT_UTILIZATION',
            'MEDIUM_UTILIZATION', 'HEAVY_UTILIZATION'.
        ServiceSpecification : dict, optional
            The hardware specifications for the service instances.
            For EC2 specifications, use:
            {
                'EC2Specification': {
                    'OfferingClass': 'STANDARD' or 'CONVERTIBLE'
                }
            }
        PageSize : int, optional
            The number of recommendations that you want returned in a single response.
        NextPageToken : str, optional
            The pagination token that indicates the next set of results to retrieve.
        Filter : dict, optional
            Filters to apply to the recommendation results.
            For this API, only NOT is supported, and dimensions are limited to 'LINKED_ACCOUNT'.
            Example:
            {
                'Not': {
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': ['123456789012']
                    }
                }
            }

        Returns
        -------
        dict
            Response containing reservation purchase recommendations, including:
            - Recommendations for each service
            - Estimated monthly savings
            - Upfront cost
            - Estimated ROI
            - Break even point
            - Instance details and purchase recommendations
        """,
        'get_savings_plans_purchase_recommendation': """
        Retrieves Savings Plans purchase recommendations.

        First use StartSavingsPlansPurchaseRecommendationGeneration to generate a new set of
        recommendations, and then use this method to retrieve them.

        Parameters
        ----------
        SavingsPlansType : str, required
            The type of Savings Plans recommendation you want to retrieve.
            Valid values: 'COMPUTE_SP', 'EC2_INSTANCE_SP', 'SAGEMAKER_SP'.
        TermInYears : str, required
            The savings plan term in years.
            Valid values: 'ONE_YEAR', 'THREE_YEARS'.
        PaymentOption : str, required
            The payment option for the Savings Plan.
            Valid values: 'NO_UPFRONT', 'PARTIAL_UPFRONT', 'ALL_UPFRONT'.
        LookbackPeriodInDays : str, required
            The lookback period used to generate the recommendation.
            Valid values: 'SEVEN_DAYS', 'THIRTY_DAYS', 'SIXTY_DAYS'.
        AccountScope : str, optional
            The account scope that you want your recommendations for.
            Valid values: 'PAYER' (includes management account and member accounts) or 'LINKED' (member accounts only).
        NextPageToken : str, optional
            The token to retrieve the next set of results.
        PageSize : int, optional
            The number of recommendations that you want returned in a single response.
        Filter : dict, optional
            You can filter your recommendations by Account ID with the LINKED_ACCOUNT dimension.
            For this API, only the Dimensions filter with Key as LINKED_ACCOUNT is supported.
            Example:
            {
                'Dimensions': {
                    'Key': 'LINKED_ACCOUNT',
                    'Values': ['123456789012', '123456789013']
                }
            }

        Returns
        -------
        dict
            Response containing Savings Plans purchase recommendations, including:
            - Estimated monthly savings
            - Upfront cost
            - Estimated ROI
            - Break even point
            - Hourly commitment recommendations
            - Account-specific recommendations
        """,
        'get_cost_and_usage': """
        Retrieves cost and usage metrics for your account.

        You can specify which cost and usage-related metric to return and filter and group your data
        by various dimensions such as SERVICE or AZ in a specific time range. Management accounts in
        an organization have access to all member accounts.

        Parameters
        ----------
        TimePeriod : dict, required
            The time period that you want the usage and costs for.
            The start date is inclusive, but the end date is exclusive.
            {
                'Start': 'string', # Required, format: 'YYYY-MM-DD'
                'End': 'string'    # Required, format: 'YYYY-MM-DD'
            }
        Granularity : str, required
            The granularity of the results.
            Valid values: 'DAILY', 'MONTHLY', 'HOURLY'.
        Metrics : list, required
            Which metrics to return in the query.
            Valid values: 'AmortizedCost', 'BlendedCost', 'NetAmortizedCost', 'NetUnblendedCost',
            'NormalizedUsageAmount', 'UnblendedCost', 'UsageQuantity'.
            Note: For meaningful UsageQuantity metrics, filter by UsageType or UsageTypeGroups.
        GroupBy : list, optional
            You can group AWS costs using up to two different groups.
            Each group is a dict with:
            {
                'Type': 'DIMENSION'|'TAG'|'COST_CATEGORY',
                'Key': 'string'
            }
            Valid DIMENSION values: 'AZ', 'INSTANCE_TYPE', 'LEGAL_ENTITY_NAME', 'INVOICING_ENTITY',
            'LINKED_ACCOUNT', 'OPERATION', 'PLATFORM', 'PURCHASE_TYPE', 'SERVICE', 'TENANCY',
            'RECORD_TYPE', 'USAGE_TYPE'.
        Filter : dict, optional
            Filters AWS costs by different dimensions.
            Supports complex expressions with AND, OR, NOT operators and filtering by:
            - Dimensions (e.g., SERVICE, REGION)
            - Tags
            - Cost Categories
            Example:
            {
                'And': [
                    {
                        'Dimensions': {
                            'Key': 'SERVICE',
                            'Values': ['Amazon EC2']
                        }
                    },
                    {
                        'Tags': {
                            'Key': 'Environment',
                            'Values': ['Production']
                        }
                    }
                ]
            }
        BillingViewArn : str, optional
            The Amazon Resource Name (ARN) that uniquely identifies a specific billing view.
        NextPageToken : str, optional
            The token to retrieve the next set of results.

        Returns
        -------
        dict
            Response containing cost and usage data based on the specified parameters, including:
            - GroupDefinitions: The groups specified by Filter or GroupBy parameters
            - ResultsByTime: Time periods covered by the results, with:
              - TimePeriod: Start and end dates
              - Total: Total amount of cost or usage accrued during the period
              - Groups: Grouped data based on the GroupBy parameter
              - Estimated: Whether the result is estimated
            - DimensionValueAttributes: Attributes that apply to dimension values
        """,
    },
}


def get_docstring(service, method):
    """Retrieve a docstring for a specific service and method.

    Parameters
    ----------
    service : str
        The AWS service name (cost_optimization_hub, compute_optimizer, cost_explorer)
    method : str
        The method name

    Returns:
    -------
    str
        The docstring for the specified method, or None if not found
    """
    if service in boto3_docstrings and method in boto3_docstrings[service]:
        return boto3_docstrings[service][method]
    return None


def list_available_methods():
    """List all available methods with docstrings.

    Returns:
    -------
    dict
        A dictionary mapping services to their available methods
    """
    result = {}
    for service, methods in boto3_docstrings.items():
        result[service] = list(methods.keys())
    return result
