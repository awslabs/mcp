"""awslabs lambda MCP Server implementation."""

import argparse
import boto3
import json
import logging
import os
import re
from mcp.server.fastmcp import Context, FastMCP
from typing import Optional


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWS_PROFILE = os.environ.get('AWS_PROFILE', 'default')
logger.info(f'AWS_PROFILE: {AWS_PROFILE}')

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
logger.info(f'AWS_REGION: {AWS_REGION}')

FUNCTION_PREFIX = os.environ.get('FUNCTION_PREFIX', '')
logger.info(f'FUNCTION_PREFIX: {FUNCTION_PREFIX}')

FUNCTION_LIST = [
    function_name.strip()
    for function_name in os.environ.get('FUNCTION_LIST', '').split(',')
    if function_name.strip()
]
logger.info(f'FUNCTION_LIST: {FUNCTION_LIST}')

FUNCTION_TAG_KEY = os.environ.get('FUNCTION_TAG_KEY', '')
logger.info(f'FUNCTION_TAG_KEY: {FUNCTION_TAG_KEY}')

FUNCTION_TAG_VALUE = os.environ.get('FUNCTION_TAG_VALUE', '')
logger.info(f'FUNCTION_TAG_VALUE: {FUNCTION_TAG_VALUE}')

FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY = os.environ.get('FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY')
logger.info(f'FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY: {FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY}')

# Initialize AWS clients
session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
lambda_client = session.client('lambda')
schemas_client = session.client('schemas')

mcp = FastMCP(
    'awslabs.lambda-mcp-server',
    instructions="""Use AWS Lambda functions to improve your answers.
    These Lambda functions give you additional capabilities and access to AWS services and resources in an AWS account.""",
    dependencies=['pydantic', 'boto3'],
)


def validate_function_name(function_name: str) -> bool:
    """Validate that the function name is valid and can be called."""
    # If both prefix and list are empty, consider all functions valid
    if not FUNCTION_PREFIX and not FUNCTION_LIST:
        return True

    # Otherwise, check if the function name matches the prefix or is in the list
    return (FUNCTION_PREFIX and function_name.startswith(FUNCTION_PREFIX)) or (
        function_name in FUNCTION_LIST
    )


def sanitize_tool_name(name: str) -> str:
    """Sanitize a Lambda function name to be used as a tool name."""
    # Remove prefix if present
    if name.startswith(FUNCTION_PREFIX):
        name = name[len(FUNCTION_PREFIX) :]

    # Replace invalid characters with underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

    # Ensure name doesn't start with a number
    if name and name[0].isdigit():
        name = '_' + name

    return name


def format_lambda_response(function_name: str, payload: bytes) -> str:
    """Format the Lambda function response payload."""
    try:
        # Try to parse the payload as JSON
        payload_json = json.loads(payload)
        return f'Function {function_name} returned: {json.dumps(payload_json, indent=2)}'
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Return raw payload if not JSON
        return f'Function {function_name} returned payload: {payload}'


async def invoke_lambda_function_impl(function_name: str, parameters: dict, ctx: Context) -> str:
    """Tool that invokes an AWS Lambda function with a JSON payload."""
    await ctx.info(f'Invoking {function_name} with parameters: {parameters}')

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(parameters),
    )

    await ctx.info(f'Function {function_name} returned with status code: {response["StatusCode"]}')

    if 'FunctionError' in response:
        error_message = (
            f'Function {function_name} returned with error: {response["FunctionError"]}'
        )
        await ctx.error(error_message)
        return error_message

    payload = response['Payload'].read()
    # Format the response payload
    return format_lambda_response(function_name, payload)


def get_schema_from_registry(schema_arn: str) -> Optional[dict]:
    """Fetch schema from EventBridge Schema Registry.

    Args:
        schema_arn: ARN of the schema to fetch

    Returns:
        Schema content if successful, None if failed
    """
    try:
        # Parse registry name and schema name from ARN
        # ARN format: arn:aws:schemas:region:account:schema/registry-name/schema-name
        arn_parts = schema_arn.split(':')
        if len(arn_parts) < 6:
            logger.error(f'Invalid schema ARN format: {schema_arn}')
            return None

        registry_schema = arn_parts[5].split('/')
        if len(registry_schema) != 3:
            logger.error(f'Invalid schema path in ARN: {arn_parts[5]}')
            return None

        registry_name = registry_schema[1]
        schema_name = registry_schema[2]

        # Get the latest schema version
        response = schemas_client.describe_schema(
            RegistryName=registry_name,
            SchemaName=schema_name,
        )

        # Return the raw schema content
        return response['Content']

    except Exception as e:
        logger.error(f'Error fetching schema from registry: {e}')
        return None


def create_lambda_tool(function_name: str, description: str, schema_arn: Optional[str] = None):
    """Create a tool function for a Lambda function.

    Args:
        function_name: Name of the Lambda function
        description: Base description for the tool
        schema_arn: Optional ARN of the input schema in the Schema Registry
    """
    # Create a meaningful tool name
    tool_name = sanitize_tool_name(function_name)

    # Define the inner function
    async def lambda_function(parameters: dict, ctx: Context) -> str:
        """Tool for invoking a specific AWS Lambda function with parameters."""
        # Use the same implementation as the generic invoke function
        return await invoke_lambda_function_impl(function_name, parameters, ctx)

    # Set the function's documentation
    if schema_arn:
        schema = get_schema_from_registry(schema_arn)
        if schema:
            #  We add the schema to the description because mcp.tool does not expose overriding the tool schema.
            description_with_schema = f'{description}\n\nInput Schema:\n{schema}'
            lambda_function.__doc__ = description_with_schema
            logger.info(f'Added schema from registry to description for function {function_name}')
        else:
            lambda_function.__doc__ = description
    else:
        lambda_function.__doc__ = description

    logger.info(f'Registering tool {tool_name} with description: {description}')
    # Apply the decorator manually with the specific name
    decorated_function = mcp.tool(name=tool_name)(lambda_function)

    return decorated_function


def get_schema_arn_from_function_arn(function_arn: str) -> Optional[str]:
    """Get schema ARN from function tags if configured.

    Args:
        function_arn: ARN of the Lambda function

    Returns:
        Schema ARN if found and configured, None otherwise
    """
    if not FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY:
        logger.info(
            'No schema tag environment variable provided (FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY ).'
        )
        return None

    try:
        tags_response = lambda_client.list_tags(Resource=function_arn)
        tags = tags_response.get('Tags', {})
        if FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY in tags:
            return tags[FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY]
        else:
            logger.info(
                f'No schema arn provided for function {function_arn} via tag {FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY}'
            )
    except Exception as e:
        logger.warning(f'Error checking tags for function {function_arn}: {e}')

    return None


def filter_functions_by_tag(functions, tag_key, tag_value):
    """Filter Lambda functions by a specific tag key-value pair.

    Args:
        functions: List of Lambda function objects
        tag_key: Tag key to filter by
        tag_value: Tag value to filter by

    Returns:
        List of Lambda functions that have the specified tag key-value pair
    """
    logger.info(f'Filtering functions by tag key-value pair: {tag_key}={tag_value}')
    tagged_functions = []

    for function in functions:
        try:
            # Get tags for the function
            tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
            tags = tags_response.get('Tags', {})

            # Check if the function has the specified tag key-value pair
            if tag_key in tags and tags[tag_key] == tag_value:
                tagged_functions.append(function)
        except Exception as e:
            logger.warning(f'Error getting tags for function {function["FunctionName"]}: {e}')

    logger.info(f'{len(tagged_functions)} Lambda functions found with tag {tag_key}={tag_value}.')
    return tagged_functions


def get_all_lambda_functions(functions: list, marker: Optional[str] = '', max_items: Optional[int] = 50) -> list:
    """Retrieve all Lambda functions using pagination.

    Args:
        functions: List to store the retrieved functions
        marker: Marker for pagination
        max_items: Maximum number of items to retrieve per page
    
    Returns:
        List of all Lambda functions
    """
    logger.info('Retrieving all Lambda functions...')
    try:
        query = {
            'MaxItems': max_items,
        }
        if marker:
            query['Marker'] = marker
        response = lambda_client.list_functions(**query)
        functions += response['Functions']
        if len(response['Functions']) == max_items:
            get_all_lambda_functions(functions, response['NextMarker'])
    except Exception as e:
        logger.error(f'Error retrieving Lambda functions: {e}')
    
    logger.info(f'Total Lambda functions found: {len(functions)}')
    return functions


def register_lambda_functions():
    """Register Lambda functions as individual tools."""
    try:
        logger.info('Registering Lambda functions as individual tools...')

        # Get all functions
        all_functions = get_all_lambda_functions([])
        logger.info(f'Total Lambda functions found: {len(all_functions)}')

        # First filter by function name if prefix or list is set
        if FUNCTION_PREFIX or FUNCTION_LIST:
            valid_functions = [
                f for f in all_functions if validate_function_name(f['FunctionName'])
            ]
            logger.info(f'{len(valid_functions)} Lambda functions found after name filtering.')
        else:
            valid_functions = all_functions
            logger.info(
                'No name filtering applied (both FUNCTION_PREFIX and FUNCTION_LIST are empty).'
            )

        # Then filter by tag if both FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE are set and non-empty
        if FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE:
            tagged_functions = filter_functions_by_tag(
                valid_functions, FUNCTION_TAG_KEY, FUNCTION_TAG_VALUE
            )
            valid_functions = tagged_functions
        elif FUNCTION_TAG_KEY or FUNCTION_TAG_VALUE:
            logger.warning(
                'Both FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE must be set to filter by tag.'
            )
            valid_functions = []

        for function in valid_functions:
            function_name = function['FunctionName']
            description = function.get('Description', f'AWS Lambda function: {function_name}')
            schema_arn = get_schema_arn_from_function_arn(function['FunctionArn'])

            create_lambda_tool(function_name, description, schema_arn)

        logger.info('Lambda functions registered successfully as individual tools.')

    except Exception as e:
        logger.error(f'Error registering Lambda functions as tools: {e}')


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Model Context Protocol (MCP) server for Lambda'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    register_lambda_functions()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
