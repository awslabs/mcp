# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""AWS syntheticdata MCP Server implementation."""

import argparse
import os
import pandas as pd
import re
from awslabs.syntheticdata_mcp_server.pandas_interpreter import (
    execute_pandas_code as _execute_pandas_code,
)
from awslabs.syntheticdata_mcp_server.storage import UnifiedDataLoader
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ExecutePandasCodeInput(BaseModel):
    """Input model for executing pandas code to generate synthetic data.

    This model defines the required parameters for running pandas code in a restricted
    environment and saving the resulting DataFrames as CSV files.

    Attributes:
        code: Python code that uses pandas to generate synthetic data. The code should
            define one or more pandas DataFrames. Pandas is already available as "pd".
        workspace_dir: The current workspace directory. Critical for saving files to
            the user's current project.
        output_dir: Optional subdirectory within workspace_dir to save CSV files to.
            If not provided, files will be saved directly to workspace_dir.
    """

    code: str = Field(
        ...,
        description='Python code that uses pandas to generate synthetic data. The code should define one or more pandas DataFrames. Pandas is already available as "pd".',
    )
    workspace_dir: str = Field(
        ...,
        description="CRITICAL: The current workspace directory. Assistant must always provide this parameter to save files to the user's current project.",
    )
    output_dir: Optional[str] = Field(
        None,
        description='Optional subdirectory within workspace_dir to save CSV files to. If not provided, files will be saved directly to workspace_dir.',
    )


class ValidateAndSaveDataInput(BaseModel):
    """Input model for validating and saving data as CSV files.

    This model defines the required parameters for validating JSON Lines data structure
    and saving the data as CSV files using pandas.

    Attributes:
        data: Dictionary mapping table names to lists of records. Each record should
            be a dictionary mapping column names to values.
        workspace_dir: The current workspace directory. Critical for saving files to
            the user's current project.
        output_dir: Optional subdirectory within workspace_dir to save CSV files to.
            If not provided, files will be saved directly to workspace_dir.
    """

    data: Dict[str, List[Dict]] = Field(
        ...,
        description='Dictionary mapping table names to lists of records. Each record should be a dictionary mapping column names to values.',
    )
    workspace_dir: str = Field(
        ...,
        description="CRITICAL: The current workspace directory. Assistant must always provide this parameter to save files to the user's current project.",
    )
    output_dir: Optional[str] = Field(
        None,
        description='Optional subdirectory within workspace_dir to save CSV files to. If not provided, files will be saved directly to workspace_dir.',
    )


class LoadToStorageInput(BaseModel):
    """Input model for loading data to storage targets.

    This model defines the required parameters for loading data to configured storage
    targets like S3, with support for various formats and optimizations.

    Attributes:
        data: Dictionary mapping table names to lists of records. Each record should
            be a dictionary mapping column names to values.
        targets: List of target configurations. Each target should have a "type"
            (e.g., "s3") and target-specific "config".
    """

    data: Dict[str, List[Dict]] = Field(
        ...,
        description='Dictionary mapping table names to lists of records. Each record should be a dictionary mapping column names to values.',
    )
    targets: List[Dict[str, Any]] = Field(
        ...,
        description='List of target configurations. Each target should have a "type" (e.g., "s3") and target-specific "config".',
    )


mcp = FastMCP(
    'awslabs.syntheticdata-mcp-server',
    instructions="""
    # awslabs Synthetic Data MCP Server

    This MCP server provides tools for generating high-quality synthetic data based on business use cases.

    ## Capabilities

    - Provides detailed instructions for generating synthetic data based on business descriptions
    - Validates and saves JSON Lines data as CSV files
    - Loads data to various storage targets (S3, with more coming soon)
    - Supports multiple data formats (CSV, JSON, Parquet)
    - Handles data partitioning and storage optimization

    ## Workflow

    1. Start by describing your business domain and use case
    2. Get detailed instructions for generating synthetic data
    3. Generate the data in JSON Lines format following the instructions
    4. Validate and save the data as CSV files
    5. (Optional) Load the data to storage targets like S3 with optimized formats and partitioning

    ## Use Cases

    - Development and testing environments
    - ML model training and validation
    - Demo applications and presentations
    - Data pipeline testing
    """,
    dependencies=[
        'pydantic',
        'pandas',
        'boto3',
    ],
)


@mcp.tool(name='get_data_generation_instructions')
async def get_data_generation_instructions(
    business_description: str = Field(
        ...,
        description='A detailed description of the business domain and use case. The more specific and comprehensive the description, the better the data generation instructions will be.',
    ),
) -> Dict:
    """Get instructions for generating synthetic data based on a business description.

    This tool analyzes a business description and provides detailed instructions
    for generating synthetic data in JSON Lines format.

    Parameters:
        business_description: A description of the business use case

    Returns:
        A dictionary containing detailed instructions for generating synthetic data
    """
    try:
        # Validate input
        if not business_description or not business_description.strip():
            return {'success': False, 'error': 'Business description cannot be empty'}

        # Extract key entities and concepts from the business description
        entities = _extract_key_entities(business_description)

        # Generate instructions for data structure
        data_structure_instructions = _generate_data_structure_instructions(
            business_description, entities
        )

        # Generate instructions for data generation
        data_generation_instructions = _generate_data_generation_instructions(entities)

        # Generate example data
        example_data = _generate_example_data(entities)

        # Compile all instructions
        instructions = {
            'overview': f"Based on the business description: '{business_description}', you should generate synthetic data with the following structure and characteristics:",
            'data_structure_instructions': data_structure_instructions,
            'data_generation_instructions': data_generation_instructions,
            'format_instructions': {
                'format': 'JSON Lines',
                'description': 'Each line should be a valid JSON object representing a single record. Different tables should be in separate JSON Lines files.',
                'example': example_data,
            },
            'validation_instructions': {
                'description': 'After generating the data, use the validate_and_save_data tool to validate and save the data as CSV files.',
                'parameters': {
                    'data': 'The JSON Lines data you generated',
                    'workspace_dir': 'IMPORTANT: Always provide the current workspace directory',
                    'output_dir': 'Optional subdirectory within workspace_dir (defaults to workspace_dir)',
                },
            },
        }

        return {
            'success': True,
            'instructions': instructions,
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


@mcp.tool(name='validate_and_save_data')
async def validate_and_save_data(input_data: ValidateAndSaveDataInput) -> Dict:
    """Validate JSON Lines data and save it as CSV files.

    This tool validates the structure of JSON Lines data and saves it as CSV files
    using pandas.

    Parameters:
        data: Dictionary mapping table names to lists of records
        workspace_dir: CRITICAL - The current workspace directory
        output_dir: Optional subdirectory within workspace_dir to save CSV files to

    Returns:
        A dictionary containing validation results and paths to saved CSV files
    """
    try:
        # Initialize results
        csv_paths = {}
        row_counts = {}
        validation_results = {}
        save_dir = input_data.workspace_dir
        if input_data.output_dir:
            save_dir = os.path.join(input_data.workspace_dir, input_data.output_dir)

        # Validate all tables first
        for table_name, records in input_data.data.items():
            validation_result = _validate_table_data(table_name, records)
            validation_results[table_name] = validation_result

        # Check if all tables are valid
        all_valid = all(result['is_valid'] for result in validation_results.values())

        # If any validation failed, return error
        if not all_valid:
            error_messages = []
            for table_name, result in validation_results.items():
                if not result['is_valid']:
                    error_messages.extend(result['errors'])
            return {
                'success': False,
                'error': '; '.join(error_messages),
                'validation_results': validation_results,
            }

        # Create directory and save tables
        try:
            os.makedirs(save_dir, exist_ok=True)
            for table_name, records in input_data.data.items():
                # Convert to DataFrame
                df = pd.DataFrame(records)

                # Save as CSV
                csv_path = os.path.join(save_dir, f'{table_name}.csv')
                df.to_csv(csv_path, index=False)

                # Record results
                csv_paths[table_name] = csv_path
                row_counts[table_name] = len(df)

            return {
                'success': True,
                'validation_results': validation_results,
                'csv_paths': csv_paths,
                'row_counts': row_counts,
                'output_dir': save_dir,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'validation_results': validation_results,
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


@mcp.tool(name='load_to_storage')
async def load_to_storage(input_data: LoadToStorageInput) -> Dict:
    """Load data to one or more storage targets.

    This tool uses the UnifiedDataLoader to load data to configured storage targets.
    Currently supports:
    - S3: Load data as CSV, JSON, or Parquet files with optional partitioning

    Example targets configuration:
    ```python
    targets = [
        {
            'type': 's3',
            'config': {
                'bucket': 'my-bucket',
                'prefix': 'data/users/',
                'format': 'parquet',
                'partitioning': {'enabled': True, 'columns': ['region']},
                'storage': {'class': 'INTELLIGENT_TIERING', 'encryption': 'AES256'},
            },
        }
    ]
    ```

    Parameters:
        data: Dictionary mapping table names to lists of records
        targets: List of target configurations

    Returns:
        Dictionary containing results for each target
    """
    try:
        loader = UnifiedDataLoader()
        result = await loader.load_data(input_data.data, input_data.targets)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


@mcp.tool(name='execute_pandas_code')
async def execute_pandas_code(input_data: ExecutePandasCodeInput) -> Dict:
    """Execute pandas code to generate synthetic data and save it as CSV files.

    This tool runs pandas code in a restricted environment to generate synthetic data.
    It then saves any generated DataFrames as CSV files.

    ## Features

    1. **Multiple DataFrame Detection**: The tool automatically finds all pandas DataFrames defined in your code and saves them as separate CSV files.

    2. **Referential Integrity Checking**: For multi-table data models, the tool checks for foreign key relationships and validates that references are valid.

    3. **Third Normal Form Validation**: The tool identifies potential 3NF violations like functional dependencies between non-key attributes.

    ## Code Requirements

    - Your code should define one or more pandas DataFrames
    - No need to include imports - pandas is already available as 'pd'
    - No need to include save logic - all DataFrames will be automatically saved

    ## Example Usage

    ```python
    # Simple table
    customers_df = pd.DataFrame(
        {
            'customer_id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'city': ['New York', 'San Francisco', 'Chicago'],
        }
    )

    # Related table with foreign key
    orders_df = pd.DataFrame(
        {'order_id': [101, 102, 103], 'customer_id': [1, 2, 3], 'amount': [99.99, 149.99, 199.99]}
    )
    ```

    Parameters:
        code: Python code using pandas to generate synthetic data
        workspace_dir: CRITICAL - The current workspace directory
        output_dir: Optional subdirectory within workspace_dir to save CSV files to

    Returns:
        A dictionary containing execution results and paths to saved CSV files
    """
    try:
        # Determine the output directory
        save_dir = input_data.workspace_dir
        if input_data.output_dir:
            save_dir = os.path.join(input_data.workspace_dir, input_data.output_dir)

        # Use the imported execute_pandas_code function
        result = _execute_pandas_code(input_data.code, save_dir)

        # Only create directory and set success if DataFrames were found
        if result.get('saved_files'):
            os.makedirs(save_dir, exist_ok=True)
            result['success'] = True
            result['workspace_dir'] = input_data.workspace_dir
            if input_data.output_dir:
                result['output_subdir'] = input_data.output_dir
        else:
            result['success'] = False
            result['error'] = 'No DataFrames found in code'

        return result
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Error executing pandas code: {str(e)}',
        }


def _extract_key_entities(description: str) -> List[str]:
    """Extract key entities from a business description.

    This is a simplified implementation that looks for common patterns
    in business descriptions to identify entities.

    Args:
        description: A string describing the business use case

    Returns:
        A list of potential entity names
    """
    # Convert to lowercase for easier matching
    desc_lower = description.lower()

    # Look for common patterns like "X table", "Y database", etc.
    table_patterns = [
        r'(\w+)\s+table',
        r'table\s+of\s+(\w+)s?',
        r'(\w+)\s+database',
        r'(\w+)\s+records',
        r'(\w+)\s+data',
    ]

    entities = []
    for pattern in table_patterns:
        matches = re.findall(pattern, desc_lower)
        entities.extend(matches)

    # Look for common entity names in business domains
    common_entities = [
        'user',
        'customer',
        'product',
        'order',
        'item',
        'category',
        'transaction',
        'payment',
        'invoice',
        'employee',
        'department',
        'menu',
        'reservation',
        'booking',
        'review',
        'comment',
        'address',
        'location',
        'store',
        'supplier',
        'inventory',
    ]

    for entity in common_entities:
        if entity in desc_lower or f'{entity}s' in desc_lower:
            entities.append(entity)

    # Remove duplicates and normalize
    entities = list(set(entities))
    entities = [e.strip().lower() for e in entities if e.strip()]

    return entities


def _generate_data_structure_instructions(description: str, entities: List[str]) -> Dict:
    """Generate instructions for data structure.

    Args:
        description: A string describing the business use case
        entities: A list of potential entity names

    Returns:
        A dictionary containing instructions for data structure
    """
    # Generate general instructions
    general_instructions = [
        'Analyze the business description to identify key entities (tables) and their attributes (columns).',
        'Consider the relationships between entities (one-to-one, one-to-many, many-to-many).',
        'Design a normalized data structure with appropriate primary and foreign keys.',
        'Include appropriate data types for each column (string, integer, float, boolean, date, etc.).',
        'Consider including common fields like created_at, updated_at, status, etc. where appropriate.',
    ]

    # Generate entity-specific instructions
    entity_instructions = {}
    for entity in entities:
        entity_instructions[entity] = {
            'description': f'Consider what attributes would be relevant for a {entity} entity in this business context.',
            'suggestions': _get_entity_attribute_suggestions(entity),
        }

    # Generate relationship instructions
    relationship_instructions = [
        'Identify relationships between entities based on the business description.',
        'Use foreign keys to represent relationships between tables.',
        'Consider whether junction tables are needed for many-to-many relationships.',
        'Ensure referential integrity in your data model.',
    ]

    return {
        'general_instructions': general_instructions,
        'entity_instructions': entity_instructions,
        'relationship_instructions': relationship_instructions,
    }


def _get_entity_attribute_suggestions(entity: str) -> List[str]:
    """Get attribute suggestions for an entity.

    Args:
        entity: The name of the entity

    Returns:
        A list of suggested attributes
    """
    # Common attributes for different entity types
    attribute_suggestions = {
        'user': ['id', 'name', 'email', 'password_hash', 'created_at', 'last_login'],
        'customer': ['id', 'name', 'email', 'phone', 'address', 'created_at'],
        'product': ['id', 'name', 'description', 'price', 'category_id', 'stock_quantity'],
        'order': ['id', 'customer_id', 'order_date', 'total_amount', 'status'],
        'item': ['id', 'name', 'description', 'price', 'category_id'],
        'category': ['id', 'name', 'description', 'parent_category_id'],
        'transaction': ['id', 'order_id', 'amount', 'transaction_date', 'status'],
        'payment': ['id', 'order_id', 'amount', 'payment_date', 'payment_method'],
        'invoice': ['id', 'order_id', 'invoice_date', 'due_date', 'amount', 'status'],
        'employee': ['id', 'name', 'email', 'department_id', 'position', 'hire_date'],
        'department': ['id', 'name', 'description', 'manager_id'],
        'menu': ['id', 'name', 'description', 'start_date', 'end_date'],
        'reservation': ['id', 'customer_id', 'reservation_date', 'party_size', 'status'],
        'booking': ['id', 'customer_id', 'booking_date', 'status'],
        'review': ['id', 'customer_id', 'product_id', 'rating', 'comment', 'review_date'],
        'comment': ['id', 'user_id', 'content', 'created_at'],
        'address': ['id', 'street', 'city', 'state', 'postal_code', 'country'],
        'location': ['id', 'name', 'address', 'latitude', 'longitude'],
        'store': ['id', 'name', 'address', 'phone', 'manager_id'],
        'supplier': ['id', 'name', 'contact_name', 'email', 'phone'],
        'inventory': ['id', 'product_id', 'quantity', 'location_id', 'last_updated'],
    }

    # Return suggestions for the entity, or a generic list if not found
    return attribute_suggestions.get(entity, ['id', 'name', 'description', 'created_at'])


def _generate_data_generation_instructions(entities: List[str]) -> Dict:
    """Generate instructions for data generation.

    Args:
        entities: A list of potential entity names

    Returns:
        A dictionary containing instructions for data generation
    """
    # Generate general instructions
    general_instructions = [
        'Generate realistic and diverse data that reflects the business domain.',
        'Ensure data consistency across related tables (e.g., foreign keys reference valid primary keys).',
        'Include a mix of common and edge cases in your data.',
        'Consider the appropriate number of records for each table based on the business context.',
        'Generate data that covers various scenarios and use cases.',
    ]

    # Generate data quality instructions
    data_quality_instructions = [
        'Ensure data types are consistent (e.g., dates in ISO format, numbers as appropriate numeric types).',
        'Include appropriate null values where fields are optional.',
        'Ensure text fields have realistic lengths and formats.',
        'Generate realistic values for domain-specific fields (e.g., email addresses, phone numbers, etc.).',
        'Avoid generating duplicate primary keys.',
    ]

    return {
        'general_instructions': general_instructions,
        'data_quality_instructions': data_quality_instructions,
        'recommended_record_counts': _get_recommended_record_counts(entities),
    }


def _get_recommended_record_counts(entities: List[str]) -> Dict[str, int]:
    """Get recommended record counts for entities.

    Args:
        entities: A list of potential entity names

    Returns:
        A dictionary mapping entity names to recommended record counts
    """
    # Default record counts for different entity types
    record_counts = {}

    for entity in entities:
        # Assign different default counts based on entity type
        if entity in ['user', 'customer', 'employee']:
            record_counts[entity] = 50
        elif entity in ['product', 'item', 'category']:
            record_counts[entity] = 20
        elif entity in ['order', 'transaction', 'payment', 'invoice']:
            record_counts[entity] = 100
        else:
            record_counts[entity] = 30

    return record_counts


def _generate_example_data(entities: List[str]) -> Dict[str, List[Dict]]:
    """Generate example data for entities.

    Args:
        entities: A list of potential entity names

    Returns:
        A dictionary containing example data for entities
    """
    example_data = {}

    # Generate example data for up to 3 entities
    for entity in entities[:3]:
        example_data[entity] = _get_entity_example_data(entity)

    return example_data


def _get_entity_example_data(entity: str) -> List[Dict]:
    """Get example data for an entity.

    Args:
        entity: The name of the entity

    Returns:
        A list of example records
    """
    # Example data for different entity types
    if entity == 'user':
        return [
            {
                'id': 1,
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'created_at': '2023-01-15T10:30:00',
            },
            {
                'id': 2,
                'name': 'Jane Smith',
                'email': 'jane.smith@example.com',
                'created_at': '2023-02-20T14:45:00',
            },
        ]
    elif entity == 'product':
        return [
            {'id': 1, 'name': 'Laptop', 'price': 999.99, 'category_id': 1, 'stock_quantity': 50},
            {
                'id': 2,
                'name': 'Smartphone',
                'price': 699.99,
                'category_id': 1,
                'stock_quantity': 100,
            },
        ]
    elif entity == 'order':
        return [
            {
                'id': 1,
                'customer_id': 1,
                'order_date': '2023-03-10',
                'total_amount': 1699.98,
                'status': 'completed',
            },
            {
                'id': 2,
                'customer_id': 2,
                'order_date': '2023-03-15',
                'total_amount': 699.99,
                'status': 'processing',
            },
        ]
    else:
        # Generic example data
        return [
            {
                'id': 1,
                'name': f'{entity.capitalize()} 1',
                'description': f'Description for {entity} 1',
            },
            {
                'id': 2,
                'name': f'{entity.capitalize()} 2',
                'description': f'Description for {entity} 2',
            },
        ]


def _validate_table_data(table_name: str, records: List[Dict]) -> Dict:
    """Validate table data.

    Args:
        table_name: The name of the table
        records: A list of records for the table

    Returns:
        A dictionary containing validation results
    """
    # Check if records is a list
    if not isinstance(records, list):
        return {
            'is_valid': False,
            'errors': [f"Data for table '{table_name}' must be a list of records"],
        }

    # Check if records is empty
    if not records:
        return {
            'is_valid': False,
            'errors': [f"Data for table '{table_name}' cannot be empty"],
        }

    # Check if all records are dictionaries
    if not all(isinstance(record, dict) for record in records):
        return {
            'is_valid': False,
            'errors': [f"All records for table '{table_name}' must be dictionaries"],
        }

    # Check if all records have the same keys
    keys = set(records[0].keys())
    if not all(set(record.keys()) == keys for record in records):
        return {
            'is_valid': False,
            'errors': [f"All records for table '{table_name}' must have the same keys"],
        }

    # Check for duplicate IDs if 'id' is a key
    if 'id' in keys:
        ids = [record['id'] for record in records]
        if len(ids) != len(set(ids)):
            return {
                'is_valid': False,
                'errors': [f"Duplicate IDs found in table '{table_name}'"],
            }

    return {
        'is_valid': True,
        'errors': [],
    }


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='MCP server for generating synthetic data based on business use cases'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
