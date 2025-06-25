# Bedrock Advisor MCP Server Tool Reference

This document provides detailed information about the tools available in the Bedrock Advisor MCP Server.

## Tool Overview

The Bedrock Advisor MCP Server provides the following tools:

1. **recommend_model**: Get intelligent model recommendations based on criteria
2. **get_model_info**: Get detailed information about a specific model
3. **list_models**: List all available models with optional filtering
4. **compare_models**: Compare multiple models side-by-side with detailed analysis
5. **search_models**: Search for models using natural language queries
6. **estimate_cost**: Estimate costs for using a specific model based on usage patterns
7. **compare_costs**: Compare costs across multiple models for the same usage pattern
8. **check_model_availability**: Check availability of a specific model across AWS regions
9. **check_region_availability**: Check what models are available in a specific AWS region
10. **compare_model_availability**: Compare availability of multiple models across regions
11. **get_models_by_provider**: Get all models from a specific provider
12. **get_models_by_capabilities**: Find models that match specific capability requirements
13. **get_supported_regions**: Get list of all AWS regions that support Bedrock
14. **refresh_model_data**: Refresh model data from AWS Bedrock API
15. **get_data_status**: Get current status of model data including freshness and source information

## Detailed Tool Reference

### recommend_model

Get intelligent model recommendations based on criteria.

#### Parameters

- **use_case** (dict, required): Use case specification including primary use case and optional complexity
  - **primary** (str, required): Primary use case (e.g., "text-generation", "code-generation", "summarization")
  - **secondary** (List[str], optional): Secondary use cases
  - **complexity** (str, optional): Complexity level ("simple", "moderate", "complex")
- **performance_requirements** (dict, optional): Performance requirements
  - **max_latency_ms** (int, optional): Maximum acceptable latency in milliseconds
  - **accuracy_priority** (str, optional): Accuracy priority ("low", "medium", "high")
  - **latency_priority** (str, optional): Latency priority ("low", "medium", "high")
- **cost_constraints** (dict, optional): Cost constraints
  - **budget_priority** (str, optional): Budget priority ("low", "medium", "high")
  - **max_cost_per_1k_tokens** (float, optional): Maximum cost per 1,000 tokens
- **technical_requirements** (dict, optional): Technical requirements
  - **requires_function_calling** (bool, optional): Whether function calling is required
  - **min_context_length** (int, optional): Minimum context length required
  - **requires_multimodal** (bool, optional): Whether multimodal capabilities are required
- **region_preference** (List[str], optional): Preferred AWS regions for model availability
- **max_recommendations** (int, optional): Maximum number of recommendations to return (default: 3)

#### Returns

- **recommendations** (List[dict]): List of recommended models with scores and explanations
- **summary** (dict): Summary of the recommendation process

#### Example

```python
response = recommend_model(
    use_case={
        "primary": "text-generation",
        "secondary": ["summarization", "question-answering"],
        "complexity": "moderate"
    },
    performance_requirements={
        "max_latency_ms": 2000,
        "accuracy_priority": "high"
    },
    cost_constraints={"budget_priority": "medium"},
    technical_requirements={
        "requires_function_calling": True,
        "min_context_length": 100000
    },
    region_preference=["us-east-1", "us-west-2"],
    max_recommendations=3
)
```

### get_model_info

Get detailed information about a specific model.

#### Parameters

- **model_id** (str, required): ID of the model to get information about
- **include_availability** (bool, optional): Include availability information in the response (default: True)
- **include_pricing** (bool, optional): Include pricing information in the response (default: True)
- **include_performance** (bool, optional): Include performance information in the response (default: True)

#### Returns

- **model** (dict): Basic model information
- **capabilities** (dict): Model capabilities
- **performance** (dict, optional): Performance metrics
- **pricing** (dict, optional): Pricing information
- **availability** (dict, optional): Availability information
- **data_status** (dict): Status of the model data

#### Example

```python
response = get_model_info(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    include_availability=True,
    include_pricing=True,
    include_performance=True
)
```

### list_models

List all available models with optional filtering.

#### Parameters

- **provider** (str, optional): Filter by provider name (e.g., "Anthropic", "Amazon", "Meta")
- **region** (str, optional): Filter by region (e.g., "us-east-1", "us-west-2")
- **capabilities** (dict, optional): Filter by capabilities (e.g., {"text_generation": True, "multimodal": True})

#### Returns

- **models** (List[dict]): List of models matching the filters
- **total_count** (int): Total number of models found
- **filters_applied** (dict): Filters that were applied
- **data_status** (dict): Status of the model data

#### Example

```python
response = list_models(
    provider="Anthropic",
    region="us-east-1",
    capabilities={"function_calling": True, "multimodal": True}
)
```

### compare_models

Compare multiple models side-by-side with detailed analysis.

#### Parameters

- **model_ids** (List[str], required): List of model IDs to compare
- **criteria** (dict, optional): Comparison criteria including use_case, performance_requirements, cost_constraints
- **include_detailed_analysis** (bool, optional): Include detailed feature analysis and recommendations (default: True)

#### Returns

- **comparison_results** (dict): Comparison results for each model
- **detailed_analysis** (dict, optional): Detailed analysis of the models
- **models_compared** (int): Number of models compared
- **criteria_used** (dict): Criteria used for comparison
- **summary** (dict): Summary of the comparison

#### Example

```python
response = compare_models(
    model_ids=[
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240229-v1:0",
        "amazon.titan-text-express-v1:0"
    ],
    criteria={
        "use_case": {"primary": "text-generation"},
        "performance_requirements": {"accuracy_priority": "high"}
    },
    include_detailed_analysis=True
)
```

### search_models

Search for models using natural language queries.

#### Parameters

- **query** (str, required): Search query for model names, providers, or capabilities
- **limit** (int, optional): Maximum number of results to return (default: 10)

#### Returns

- **search_results** (List[dict]): List of models matching the search query
- **query** (str): The search query used
- **total_found** (int): Total number of models found
- **limited_to** (int): Maximum number of results returned

#### Example

```python
response = search_models(
    query="multimodal models with function calling",
    limit=5
)
```

### estimate_cost

Estimate costs for using a specific model based on usage patterns.

#### Parameters

- **model_id** (str, required): Model ID to estimate costs for
- **usage** (dict, required): Usage parameters
  - **expected_requests_per_month** (int, required): Expected number of requests per month
  - **avg_input_tokens** (int, required): Average number of input tokens per request
  - **avg_output_tokens** (int, required): Average number of output tokens per request
- **include_optimizations** (bool, optional): Include cost optimization recommendations (default: True)
- **include_projections** (bool, optional): Include cost projections for different usage scenarios (default: True)

#### Returns

- **cost_estimate** (dict): Detailed cost estimate
- **model_id** (str): The model ID used for estimation
- **usage_parameters** (dict): The usage parameters used for estimation

#### Example

```python
response = estimate_cost(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    usage={
        "expected_requests_per_month": 10000,
        "avg_input_tokens": 1000,
        "avg_output_tokens": 500
    },
    include_optimizations=True,
    include_projections=True
)
```

### compare_costs

Compare costs across multiple models for the same usage pattern.

#### Parameters

- **model_ids** (List[str], required): List of model IDs to compare costs for
- **usage** (dict, required): Usage parameters
  - **expected_requests_per_month** (int, required): Expected number of requests per month
  - **avg_input_tokens** (int, required): Average number of input tokens per request
  - **avg_output_tokens** (int, required): Average number of output tokens per request

#### Returns

- **cost_comparison** (dict): Detailed cost comparison
- **models_compared** (int): Number of models compared
- **usage_parameters** (dict): The usage parameters used for comparison

#### Example

```python
response = compare_costs(
    model_ids=[
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240229-v1:0",
        "amazon.titan-text-express-v1:0"
    ],
    usage={
        "expected_requests_per_month": 10000,
        "avg_input_tokens": 1000,
        "avg_output_tokens": 500
    }
)
```

### check_model_availability

Check availability of a specific model across AWS regions.

#### Parameters

- **model_id** (str, required): Model ID to check availability for
- **regions** (List[str], optional): List of regions to check. If not provided, checks all Bedrock regions.

#### Returns

- **availability_check** (dict): Availability information for each region
- **model_id** (str): The model ID checked
- **regions_checked** (List[str] or str): The regions checked

#### Example

```python
response = check_model_availability(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)
```

### check_region_availability

Check what models are available in a specific AWS region.

#### Parameters

- **region** (str, required): AWS region to check (e.g., "us-east-1")

#### Returns

- **region_availability** (dict): Models available in the region
- **region** (str): The region checked

#### Example

```python
response = check_region_availability(
    region="us-east-1"
)
```

### compare_model_availability

Compare availability of multiple models across regions.

#### Parameters

- **model_ids** (List[str], required): List of model IDs to compare availability for

#### Returns

- **availability_comparison** (dict): Comparison of model availability across regions
- **models_compared** (List[str]): The models compared

#### Example

```python
response = compare_model_availability(
    model_ids=[
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240229-v1:0",
        "amazon.titan-text-express-v1:0"
    ]
)
```

### get_models_by_provider

Get all models from a specific provider.

#### Parameters

- **provider_name** (str, required): Provider name (e.g., "Anthropic", "Amazon", "Meta", "Cohere")

#### Returns

- **models** (List[dict]): List of models from the provider
- **provider_name** (str): The provider name
- **total_count** (int): Total number of models found

#### Example

```python
response = get_models_by_provider(
    provider_name="Anthropic"
)
```

### get_models_by_capabilities

Find models that match specific capability requirements.

#### Parameters

- **capabilities** (Dict[str, bool], required): Capabilities to filter by (e.g., {"text_generation": True, "multimodal": True, "function_calling": True})

#### Returns

- **models** (List[dict]): List of models matching the capabilities
- **capabilities_filter** (dict): The capabilities filter used
- **total_count** (int): Total number of models found

#### Example

```python
response = get_models_by_capabilities(
    capabilities={
        "text_generation": True,
        "multimodal": True,
        "function_calling": True
    }
)
```

### get_supported_regions

Get list of all AWS regions that support Bedrock.

#### Parameters

None

#### Returns

- **supported_regions** (List[str]): List of supported regions
- **bedrock_regions** (List[str]): List of regions where Bedrock is available
- **total_regions** (int): Total number of supported regions

#### Example

```python
response = get_supported_regions()
```

### refresh_model_data

Refresh model data from AWS Bedrock API.

#### Parameters

- **force_refresh** (bool, optional): Force refresh even if data is recent (default: False)

#### Returns

- **refresh_result** (dict): Result of the refresh operation
- **data_status** (dict): Status of the model data after refresh

#### Example

```python
response = refresh_model_data(
    force_refresh=True
)
```

### get_data_status

Get current status of model data including freshness and source information.

#### Parameters

None

#### Returns

- **data_status** (dict): Status of the model data
- **total_models** (int): Total number of models available
- **using_live_api** (bool): Whether live API data is being used

#### Example

```python
response = get_data_status()
```
