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

"""bedrock-advisor-mcp-server implementation.

This server provides tools for getting intelligent recommendations for Amazon Bedrock
foundation models based on specific use case requirements.
"""

# Import models and services
from awslabs.bedrock_advisor_mcp_server.models.requests import (
    CompareModelsRequest,
    EstimateCostRequest,
    GetModelInfoRequest,
    ListModelsRequest,
    ModelAvailabilityRequest,
    RecommendModelRequest,
    RefreshModelsRequest,
    RegionAvailabilityRequest,
)
from awslabs.bedrock_advisor_mcp_server.services.availability_checker import (
    AvailabilityChecker,
)
from awslabs.bedrock_advisor_mcp_server.services.comparison import ComparisonService
from awslabs.bedrock_advisor_mcp_server.services.cost_estimator import CostEstimator
from awslabs.bedrock_advisor_mcp_server.services.data_updater import BedrockDataUpdater
from awslabs.bedrock_advisor_mcp_server.services.model_data import ModelDataService
from awslabs.bedrock_advisor_mcp_server.services.recommendation import (
    RecommendationEngine,
)
from awslabs.bedrock_advisor_mcp_server.utils.error_handler import ErrorHandler
from awslabs.bedrock_advisor_mcp_server.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional


# Create the MCP server
mcp = FastMCP(
    'awslabs.bedrock-advisor-mcp-server',
    dependencies=[
        'pydantic',
        'boto3',
    ],
    log_level='ERROR',
    instructions="""Use this server to get intelligent recommendations for Amazon Bedrock foundation models.

WORKFLOW:
1. recommend_model:
   - Get personalized model suggestions based on your specific requirements
   - Specify use case, performance requirements, cost constraints, etc.

2. get_model_info:
   - Get detailed information about a specific Bedrock model
   - Learn about capabilities, pricing, and availability

3. compare_models:
   - Compare multiple models side-by-side
   - Analyze differences in capabilities, performance, and cost

4. estimate_cost:
   - Estimate costs based on expected usage patterns
   - Get optimization recommendations to reduce costs

5. check_model_availability:
   - Check if a model is available in specific regions
   - Plan for multi-region deployments

6. list_models:
   - List all available models with optional filtering
   - Filter by provider, region, or capabilities

7. search_models:
   - Search models using natural language queries
   - Find models by name, provider, or capabilities

8. get_models_by_provider:
   - Get all models from a specific provider
   - Compare offerings from AI companies

9. get_models_by_capabilities:
   - Find models that match specific capability requirements
   - Filter by features like multimodal, function calling, etc.

10. check_region_availability:
    - Check what models are available in a specific region
    - Regional deployment planning

11. compare_model_availability:
    - Compare availability of multiple models across regions
    - Multi-model deployment strategies

12. get_supported_regions:
    - Get list of all AWS regions that support Bedrock
    - Regional planning and availability information

13. refresh_model_data:
    - Refresh model data from AWS Bedrock API
    - Get latest models, pricing, and availability

14. get_data_status:
    - Get current status of model data
    - Check data freshness and source information

15. compare_costs:
    - Compare costs across multiple models
    - Understand cost differences for specific usage patterns
""",
)

# Initialize services
model_service = ModelDataService()
recommendation_engine = RecommendationEngine()
comparison_service = ComparisonService()
cost_estimator = CostEstimator()
availability_checker = AvailabilityChecker()
data_updater = BedrockDataUpdater()

# Initialize dynamic data
# Commented out for testing
# asyncio.create_task(data_updater._initialize_dynamic_data())


@mcp.tool(name='recommend_model')
async def mcp_recommend_model(
    use_case: Dict[str, Any] = Field(
        ...,
        description='Use case specification including primary use case and optional complexity',
    ),
    performance_requirements: Optional[Dict[str, Any]] = Field(
        default=None,
        description='Performance requirements including latency and accuracy priorities',
    ),
    cost_constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description='Cost constraints including budget priority and maximum cost',
    ),
    technical_requirements: Optional[Dict[str, Any]] = Field(
        default=None,
        description='Technical requirements including function calling, context length, etc.',
    ),
    region_preference: Optional[List[str]] = Field(
        default=None,
        description='Preferred AWS regions for model availability',
    ),
    max_recommendations: Optional[int] = Field(
        default=3,
        description='Maximum number of recommendations to return',
    ),
) -> Dict[str, Any]:
    """Get intelligent model recommendations based on criteria.

    This tool analyzes your requirements across multiple dimensions to recommend
    the most suitable Amazon Bedrock foundation models for your use case.
    """
    try:
        # Validate request
        request = RecommendModelRequest(
            use_case=use_case,
            performance_requirements=performance_requirements,
            cost_constraints=cost_constraints,
            technical_requirements=technical_requirements,
            region_preference=region_preference,
            max_recommendations=max_recommendations,
        )

        # Get all models
        models = model_service.get_all_models()

        # Get recommendations
        recommendations = recommendation_engine.recommend_models(
            models=models,
            criteria=request.dict(exclude_none=True),
            max_recommendations=request.max_recommendations,
        )

        # Generate summary
        summary = {
            'total_models_evaluated': len(models),
            'criteria_used': [f'Primary use case: {request.use_case.primary}'],
            'top_recommendation': recommendations[0]['model']['model_name']
            if recommendations
            else None,
        }

        # Add additional criteria to summary
        if request.performance_requirements:
            summary['criteria_used'].append('Performance requirements')
        if request.cost_constraints:
            summary['criteria_used'].append('Cost constraints')
        if request.technical_requirements:
            summary['criteria_used'].append('Technical requirements')
        if request.region_preference:
            summary['criteria_used'].append(
                f'Region preference: {", ".join(request.region_preference)}'
            )

        # Create response
        return {'recommendations': recommendations, 'summary': summary}

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='recommend_model')


@mcp.tool(name='get_model_info')
async def mcp_get_model_info(
    model_id: str = Field(
        ...,
        description='ID of the model to get information about',
    ),
    include_availability: bool = Field(
        default=True,
        description='Include availability information in the response',
    ),
    include_pricing: bool = Field(
        default=True,
        description='Include pricing information in the response',
    ),
    include_performance: bool = Field(
        default=True,
        description='Include performance information in the response',
    ),
) -> Dict[str, Any]:
    """Get detailed information about a specific model.

    This tool retrieves comprehensive information about an Amazon Bedrock
    foundation model, including capabilities, performance metrics, pricing,
    and regional availability.
    """
    try:
        # Validate request
        request = GetModelInfoRequest(
            model_id=model_id,
            include_availability=include_availability,
            include_pricing=include_pricing,
            include_performance=include_performance,
        )

        # Get model
        model = model_service.get_model(request.model_id)

        # Create response
        response = {
            'model': {
                'model_id': model.model_id,
                'model_name': model.model_name,
                'provider_name': model.provider_name,
                'input_modalities': model.input_modalities,
                'output_modalities': model.output_modalities,
                'response_streaming_supported': model.response_streaming_supported,
                'customizations_supported': model.customizations_supported,
                'max_tokens': model.max_tokens,
                'context_length': model.context_length,
            }
        }

        # Add capabilities
        response['capabilities'] = model.capabilities.dict()

        # Add performance if requested
        if request.include_performance and model.performance:
            response['performance'] = model.performance.dict()

        # Add pricing if requested
        if request.include_pricing and model.pricing:
            response['pricing'] = model.pricing.dict()

        # Add availability if requested
        if request.include_availability:
            response['availability'] = model.availability.dict()

        # Add data status
        response['data_status'] = {
            'using_live_data': model_service._use_api,
            'last_refresh': model_service.get_data_status().get('last_refresh'),
            'total_models_available': len(model_service.get_all_models()),
        }

        return response

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='get_model_info')


@mcp.tool(name='list_models')
async def mcp_list_models(
    provider: Optional[str] = Field(
        None,
        description="Filter by provider name (e.g., 'Anthropic', 'Amazon', 'Meta')",
    ),
    region: Optional[str] = Field(
        None, description="Filter by region (e.g., 'us-east-1', 'us-west-2')"
    ),
    capabilities: Optional[Dict[str, bool]] = Field(
        None,
        description="Filter by capabilities (e.g., {'text_generation': True, 'multimodal': True})",
    ),
) -> Dict[str, Any]:
    """List all available Bedrock foundation models with optional filtering.

    This tool provides a comprehensive list of all foundation models available
    in Amazon Bedrock, with options to filter by provider, region, or capabilities.
    """
    try:
        # Create and validate request
        request = ListModelsRequest(provider=provider, region=region, capabilities=capabilities)

        # Get models based on filters
        if request.provider:
            models = model_service.get_models_by_provider(request.provider)
        elif request.region:
            models = model_service.get_models_by_region(request.region)
        elif request.capabilities:
            models = model_service.get_models_by_capabilities(**request.capabilities)
        else:
            models = model_service.get_all_models()

        # Format response
        model_list = []
        for model in models:
            model_info = {
                'model_id': model.model_id,
                'model_name': model.model_name,
                'provider_name': model.provider_name,
                'input_modalities': model.input_modalities,
                'output_modalities': model.output_modalities,
                'capabilities': model.capabilities.dict(),
                'regions': model.availability.regions if model.availability else [],
                'status': model.availability.status if model.availability else 'UNKNOWN',
            }

            # Add pricing if available
            if model.pricing:
                model_info['pricing'] = {
                    'input_token_price': model.pricing.input_token_price,
                    'output_token_price': model.pricing.output_token_price,
                    'currency': model.pricing.currency,
                    'unit': model.pricing.unit,
                }

            model_list.append(model_info)

        return {
            'models': model_list,
            'total_count': len(model_list),
            'filters_applied': {
                'provider': request.provider,
                'region': request.region,
                'capabilities': request.capabilities,
            },
            'data_status': model_service.get_data_status(),
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='list_models')


@mcp.tool(name='compare_models')
async def mcp_compare_models(
    model_ids: List[str] = Field(
        description="List of model IDs to compare (e.g., ['anthropic.claude-3-5-sonnet-20241022-v2:0', 'amazon.nova-premier-v1:0'])"
    ),
    criteria: Optional[Dict[str, Any]] = Field(
        None,
        description='Comparison criteria including use_case, performance_requirements, cost_constraints',
    ),
    include_detailed_analysis: bool = Field(
        True, description='Include detailed feature analysis and recommendations'
    ),
) -> Dict[str, Any]:
    """Compare multiple Bedrock foundation models side-by-side.

    This tool provides comprehensive comparison between multiple models,
    including capabilities, performance, pricing, and suitability analysis.
    """
    try:
        # Create and validate request
        request = CompareModelsRequest(
            model_ids=model_ids,
            criteria=criteria,
            include_detailed_analysis=include_detailed_analysis,
        )

        # Get models to compare
        models = []
        for model_id in request.model_ids:
            try:
                model = model_service.get_model(model_id)
                models.append(model)
            except Exception as e:
                logger.warning(f'Could not find model {model_id}: {e}')

        if len(models) < 2:
            return {
                'error': 'InsufficientModels',
                'message': f'Need at least 2 valid models to compare. Found {len(models)} valid models.',
                'valid_models': [m.model_id for m in models],
                'success': False,
            }

        # Set default criteria if not provided
        comparison_criteria = request.criteria or {
            'use_case': {'primary': 'text-generation', 'complexity': 'moderate'},
            'performance_requirements': {
                'accuracy_priority': 'high',
                'latency_priority': 'medium',
            },
            'cost_constraints': {'budget_priority': 'medium'},
        }

        # Perform comparison
        comparison_results = comparison_service.compare_models(models, comparison_criteria)

        # Generate detailed analysis if requested
        detailed_analysis = None
        if request.include_detailed_analysis:
            detailed_analysis = comparison_service.generate_usage_scenario_comparison(
                models, comparison_criteria
            )

        return {
            'comparison_results': comparison_results,
            'detailed_analysis': detailed_analysis,
            'models_compared': len(models),
            'criteria_used': comparison_criteria,
            'summary': comparison_service.generate_recommendation_summary(comparison_results),
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='compare_models')


@mcp.tool(name='search_models')
async def mcp_search_models(
    query: str = Field(
        description="Search query for model names, providers, or capabilities (e.g., 'claude', 'code generation', 'multimodal')"
    ),
    limit: Optional[int] = Field(10, description='Maximum number of results to return'),
) -> Dict[str, Any]:
    """Search for Bedrock foundation models using text queries.

    This tool allows you to search through available models using natural language
    queries that match against model names, providers, capabilities, and descriptions.
    """
    try:
        # Perform search
        search_results = model_service.search_models(query)

        # Limit results if specified
        if limit and len(search_results) > limit:
            search_results = search_results[:limit]

        # Format results
        formatted_results = []
        for model in search_results:
            model_info = {
                'model_id': model.model_id,
                'model_name': model.model_name,
                'provider_name': model.provider_name,
                'capabilities': model.capabilities.dict(),
                'regions': model.availability.regions if model.availability else [],
                'pricing_summary': {
                    'input_price': model.pricing.input_token_price if model.pricing else None,
                    'output_price': model.pricing.output_token_price if model.pricing else None,
                    'currency': model.pricing.currency if model.pricing else None,
                }
                if model.pricing
                else None,
            }
            formatted_results.append(model_info)

        return {
            'search_results': formatted_results,
            'query': query,
            'total_found': len(formatted_results),
            'limited_to': limit,
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='search_models')


@mcp.tool(name='estimate_cost')
async def mcp_estimate_cost(
    model_id: str = Field(description='Model ID to estimate costs for'),
    usage: Dict[str, Any] = Field(
        description='Usage parameters including expected_requests_per_month, avg_input_tokens, avg_output_tokens'
    ),
    include_optimizations: bool = Field(
        True, description='Include cost optimization recommendations'
    ),
    include_projections: bool = Field(
        True, description='Include cost projections for different usage scenarios'
    ),
) -> Dict[str, Any]:
    """Estimate costs for using a specific Bedrock model based on usage patterns.

    This tool calculates detailed cost estimates including breakdowns of input/output costs,
    monthly projections, and optimization recommendations.
    """
    try:
        # Create and validate request
        request = EstimateCostRequest(model_id=model_id, usage=usage)

        # Get the model
        model = model_service.get_model(request.model_id)

        # Estimate costs
        cost_estimate = cost_estimator.estimate_cost(
            model=model,
            usage=request.usage,
            include_optimizations=include_optimizations,
            include_projections=include_projections,
        )

        return {
            'cost_estimate': cost_estimate,
            'model_id': request.model_id,
            'usage_parameters': request.usage,
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='estimate_cost')


@mcp.tool(name='compare_costs')
async def mcp_compare_costs(
    model_ids: List[str] = Field(description='List of model IDs to compare costs for'),
    usage: Dict[str, Any] = Field(
        description='Usage parameters including expected_requests_per_month, avg_input_tokens, avg_output_tokens'
    ),
) -> Dict[str, Any]:
    """Compare costs across multiple Bedrock models for the same usage pattern.

    This tool helps you understand cost differences between models for your specific usage.
    """
    try:
        # Get models
        models = []
        for model_id in model_ids:
            try:
                model = model_service.get_model(model_id)
                models.append(model)
            except Exception as e:
                logger.warning(f'Could not find model {model_id}: {e}')

        if len(models) < 2:
            return {
                'error': 'InsufficientModels',
                'message': f'Need at least 2 valid models to compare costs. Found {len(models)} valid models.',
                'success': False,
            }

        # Compare costs
        cost_comparison = cost_estimator.compare_costs(models, usage)

        return {
            'cost_comparison': cost_comparison,
            'models_compared': len(models),
            'usage_parameters': usage,
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='compare_costs')


@mcp.tool(name='check_model_availability')
async def mcp_check_model_availability(
    model_id: str = Field(description='Model ID to check availability for'),
    regions: Optional[List[str]] = Field(
        None,
        description="List of regions to check (e.g., ['us-east-1', 'us-west-2']). If not provided, checks all Bedrock regions",
    ),
) -> Dict[str, Any]:
    """Check availability of a specific model across AWS regions.

    This tool verifies whether a model is available in specific regions,
    helping with deployment planning and regional strategy.
    """
    try:
        # Create and validate request
        request = ModelAvailabilityRequest(model_id=model_id, regions=regions)

        # Check availability
        availability_result = await availability_checker.check_model_availability(
            model_id=request.model_id, regions=request.regions
        )

        return {
            'availability_check': availability_result,
            'model_id': request.model_id,
            'regions_checked': request.regions or 'all_bedrock_regions',
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='check_model_availability')


@mcp.tool(name='check_region_availability')
async def mcp_check_region_availability(
    region: str = Field(description="AWS region to check (e.g., 'us-east-1')"),
) -> Dict[str, Any]:
    """Check what models are available in a specific AWS region.

    This tool provides a comprehensive list of all models available
    in a particular region, useful for regional deployment planning.
    """
    try:
        # Create and validate request
        request = RegionAvailabilityRequest(region=region)

        # Check region availability
        region_availability = await availability_checker.check_region_availability(request.region)

        return {
            'region_availability': region_availability,
            'region': request.region,
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='check_region_availability')


@mcp.tool(name='compare_model_availability')
async def mcp_compare_model_availability(
    model_ids: List[str] = Field(description='List of model IDs to compare availability for'),
) -> Dict[str, Any]:
    """Compare availability of multiple models across regions.

    This tool helps you understand which models are available in which regions,
    useful for multi-model deployment strategies.
    """
    try:
        # Compare availability
        availability_comparison = await availability_checker.compare_model_availability(model_ids)

        return {
            'availability_comparison': availability_comparison,
            'models_compared': model_ids,
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='compare_model_availability')


@mcp.tool(name='get_supported_regions')
async def mcp_get_supported_regions() -> Dict[str, Any]:
    """Get list of all AWS regions that support Amazon Bedrock.

    This tool provides information about all regions where Bedrock is available,
    including region names and any additional metadata.
    """
    try:
        # Get supported regions
        supported_regions = model_service.get_supported_regions()
        bedrock_regions = availability_checker.get_bedrock_regions()

        return {
            'supported_regions': supported_regions,
            'bedrock_regions': bedrock_regions,
            'total_regions': len(supported_regions),
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='get_supported_regions')


@mcp.tool(name='refresh_model_data')
async def mcp_refresh_model_data(
    force_refresh: bool = Field(False, description='Force refresh even if data is recent'),
) -> Dict[str, Any]:
    """Refresh model data from AWS Bedrock API.

    This tool updates the local model database with the latest information
    from AWS Bedrock, including new models, pricing updates, and availability changes.
    """
    try:
        # Create and validate request
        request = RefreshModelsRequest(force_refresh=force_refresh)

        # Refresh model data
        updated_count = await model_service.refresh_models(force_refresh=request.force_refresh)

        return {
            'refresh_result': {
                'models_updated': updated_count,
                'force_refresh': request.force_refresh,
                'timestamp': model_service.get_data_status().get('last_refresh'),
            },
            'data_status': model_service.get_data_status(),
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='refresh_model_data')


@mcp.tool(name='get_data_status')
async def mcp_get_data_status() -> Dict[str, Any]:
    """Get current status of the model data including freshness and source information.

    This tool provides information about when the data was last updated,
    how many models are available, and whether live API data is being used.
    """
    try:
        # Get data status
        data_status = model_service.get_data_status()

        return {
            'data_status': data_status,
            'total_models': len(model_service.get_all_models()),
            'using_live_api': model_service._use_api,
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='get_data_status')


@mcp.tool(name='get_models_by_provider')
async def mcp_get_models_by_provider(
    provider_name: str = Field(
        description="Provider name (e.g., 'Anthropic', 'Amazon', 'Meta', 'Cohere')"
    ),
) -> Dict[str, Any]:
    """Get all models from a specific provider.

    This tool filters models by provider, useful for comparing offerings
    from specific AI companies or understanding provider capabilities.
    """
    try:
        # Get models by provider
        models = model_service.get_models_by_provider(provider_name)

        # Format results
        formatted_models = []
        for model in models:
            model_info = {
                'model_id': model.model_id,
                'model_name': model.model_name,
                'capabilities': model.capabilities.dict(),
                'regions': model.availability.regions if model.availability else [],
                'pricing': {
                    'input_price': model.pricing.input_token_price if model.pricing else None,
                    'output_price': model.pricing.output_token_price if model.pricing else None,
                    'currency': model.pricing.currency if model.pricing else None,
                }
                if model.pricing
                else None,
            }
            formatted_models.append(model_info)

        return {
            'models': formatted_models,
            'provider_name': provider_name,
            'total_count': len(formatted_models),
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='get_models_by_provider')


@mcp.tool(name='get_models_by_capabilities')
async def mcp_get_models_by_capabilities(
    capabilities: Dict[str, bool] = Field(
        description="Capabilities to filter by (e.g., {'text_generation': True, 'multimodal': True, 'function_calling': True})"
    ),
) -> Dict[str, Any]:
    """Get models that match specific capability requirements.

    This tool filters models based on their capabilities, helping you find
    models that support specific features like multimodal input, function calling, etc.
    """
    try:
        # Get models by capabilities
        models = model_service.get_models_by_capabilities(**capabilities)

        # Format results
        formatted_models = []
        for model in models:
            model_info = {
                'model_id': model.model_id,
                'model_name': model.model_name,
                'provider_name': model.provider_name,
                'capabilities': model.capabilities.dict(),
                'regions': model.availability.regions if model.availability else [],
                'pricing_summary': {
                    'input_price': model.pricing.input_token_price if model.pricing else None,
                    'output_price': model.pricing.output_token_price if model.pricing else None,
                }
                if model.pricing
                else None,
            }
            formatted_models.append(model_info)

        return {
            'models': formatted_models,
            'capabilities_filter': capabilities,
            'total_count': len(formatted_models),
            'success': True,
        }

    except Exception as e:
        return ErrorHandler.handle_exception(e, tool_name='get_models_by_capabilities')


class BedrockAdvisorServer:
    """Bedrock Advisor MCP Server class.

    This class provides a wrapper around the FastMCP server for compatibility
    with the run_server.py script.
    """

    def __init__(self):
        """Initialize the Bedrock Advisor MCP Server."""
        self.server = mcp


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
