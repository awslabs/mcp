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

"""AWS IoT SiteWise Data Ingestion Helper Prompt."""

from awslabs.aws_iot_sitewise_mcp_server.validation import (
    validate_string_for_injection,
)
from mcp.server.fastmcp.prompts import Prompt


def data_ingestion_helper(data_source: str, target_assets: str) -> str:
    """Generate a comprehensive guide for setting up data ingestion into AWS IoT SiteWise.

    This prompt helps design and \
        implement data ingestion strategies for industrial data,
    including asset modeling, gateway configuration, and data mapping.

    Args:
        data_source: Description of the data source (
            OPC-UA server,
            Modbus devices,
            etc.)
        target_assets: Description of target assets or \
                asset models

    Returns:
        Comprehensive data ingestion strategy guide
    """
    validate_string_for_injection(data_source)
    validate_string_for_injection(target_assets)
    return f"""
You are an AWS IoT SiteWise data ingestion expert helping to set up \
    industrial data collection.

**Data Source**: {data_source}
**Target Assets**: {target_assets}

Please provide a comprehensive data ingestion strategy following these steps:

1. **Asset Model Design**:
   - Analyze the target assets and design appropriate asset models
   - Use create_asset_model to create models with proper:
     - Property definitions (measurements, attributes, transforms, metrics)
     - Data types and units
     - Hierarchical relationships
   - Consider composite models for reusable components

2. **Asset Creation**:
   - Use create_asset to instantiate assets from the models
   - Set up proper asset hierarchies using associate_assets
   - Configure asset properties with appropriate aliases for data mapping

3. **Gateway Configuration** (if applicable):
   - Use create_gateway for edge data collection
   - Configure gateway capabilities using update_gateway_capability_config
   - Set up data source connections (OPC-UA, Modbus, etc.)

4. **Data Mapping Strategy**:
   - Map data source fields to asset properties
   - Set up property aliases for easy data ingestion
   - Configure data transformations if needed
   - Plan for data quality and validation

5. **Time Series Management**:
   - Use list_time_series to understand existing data streams
   - Associate time series with properties using \
       link_time_series_asset_property
   - Plan for historical data migration if needed

6. **Data Ingestion Implementation**:
   - For real-time data: Configure gateway or use AWS IoT Core rules
   - For batch data: Use batch_put_asset_property_value
   - Set up proper timestamp handling and data quality indicators
   - Implement error handling and retry logic

7. **Validation and Testing**:
   - Use get_asset_property_value to verify data ingestion
   - Check get_asset_property_value_history for historical data
   - Validate data quality and completeness
   - Test aggregation functions with get_asset_property_aggregates

8. **Monitoring and Alerting**:
   - Set up CloudWatch metrics for data ingestion monitoring
   - Configure alarms for data quality issues
   - Plan for data retention and storage optimization
   - Use describe_logging_options to enable detailed logging

9. **Security and Access Control**:
   - Configure appropriate IAM roles and policies
   - Set up encryption using put_default_encryption_configuration
   - Plan for network security and VPC configuration

10. **Performance Optimization**:
    - Configure storage settings with put_storage_configuration
    - Plan for multi-layer storage if needed
    - Optimize batch sizes and ingestion frequency
    - Consider warm tier storage for analytical queries

**Deliverables**:
- Step-by-step implementation plan
- Sample code for data ingestion
- Asset model definitions (JSON)
- Gateway configuration examples
- Monitoring and alerting setup
- Troubleshooting guide

**Best Practices**:
- Use meaningful property aliases
- Implement proper error handling
- Plan for scalability
- Consider data governance and compliance
- Document data lineage and transformations

Please provide specific AWS CLI commands, JSON configurations, and \
    code examples where applicable.
Address any potential challenges and provide solutions for common issues.
"""


# Create the prompt using from_function
data_ingestion_helper_prompt = Prompt.from_function(
    data_ingestion_helper,
    name='data_ingestion_helper',
    description=(
        'Generate a comprehensive guide for setting up data ingestion into AWS IoT SiteWise'
    ),
)
