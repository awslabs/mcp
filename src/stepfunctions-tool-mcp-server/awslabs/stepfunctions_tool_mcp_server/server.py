"""awslabs Step Functions Tool MCP Server implementation."""

import argparse
import asyncio
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

STATE_MACHINE_PREFIX = os.environ.get('STATE_MACHINE_PREFIX', '')
logger.info(f'STATE_MACHINE_PREFIX: {STATE_MACHINE_PREFIX}')

STATE_MACHINE_LIST = [
    state_machine_name.strip()
    for state_machine_name in os.environ.get('STATE_MACHINE_LIST', '').split(',')
    if state_machine_name.strip()
]
logger.info(f'STATE_MACHINE_LIST: {STATE_MACHINE_LIST}')

STATE_MACHINE_TAG_KEY = os.environ.get('STATE_MACHINE_TAG_KEY', '')
logger.info(f'STATE_MACHINE_TAG_KEY: {STATE_MACHINE_TAG_KEY}')

STATE_MACHINE_TAG_VALUE = os.environ.get('STATE_MACHINE_TAG_VALUE', '')
logger.info(f'STATE_MACHINE_TAG_VALUE: {STATE_MACHINE_TAG_VALUE}')

STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY = os.environ.get('STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY')
logger.info(f'STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY: {STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY}')

# Initialize AWS clients
session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
sfn_client = session.client('stepfunctions')
schemas_client = session.client('schemas')

mcp = FastMCP(
    'awslabs.stepfunctions-tool-mcp-server',
    instructions="""Use AWS Step Functions state machines to improve your answers.
    These state machines give you additional capabilities and access to AWS services and resources in an AWS account.""",
    dependencies=['pydantic', 'boto3'],
)


def validate_state_machine_name(state_machine_name: str) -> bool:
    """Validate that the state machine name is valid and can be called."""
    # If both prefix and list are empty, consider all state machines valid
    if not STATE_MACHINE_PREFIX and not STATE_MACHINE_LIST:
        return True

    # Otherwise, check if the state machine name matches the prefix or is in the list
    return (STATE_MACHINE_PREFIX and state_machine_name.startswith(STATE_MACHINE_PREFIX)) or (
        state_machine_name in STATE_MACHINE_LIST
    )


def sanitize_tool_name(name: str) -> str:
    """Sanitize a Step Functions state machine name to be used as a tool name."""
    # Remove prefix if present
    if name.startswith(STATE_MACHINE_PREFIX):
        name = name[len(STATE_MACHINE_PREFIX) :]

    # Replace invalid characters with underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

    # Ensure name doesn't start with a number
    if name and name[0].isdigit():
        name = '_' + name

    return name


def format_state_machine_response(state_machine_name: str, payload: bytes) -> str:
    """Format the Step Functions state machine response payload."""
    try:
        # Try to parse the payload as JSON
        payload_json = json.loads(payload)
        return f'State machine {state_machine_name} returned: {json.dumps(payload_json, indent=2)}'
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Return raw payload if not JSON
        return f'State machine {state_machine_name} returned payload: {payload}'


async def invoke_standard_state_machine_impl(
    state_machine_name: str, state_machine_arn: str, parameters: dict, ctx: Context
) -> str:
    """Execute a Standard state machine using StartExecution and poll for completion."""
    await ctx.info(
        f'Starting asynchronous execution of Standard state machine {state_machine_name}'
    )

    # Start the execution
    response = sfn_client.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(parameters),
    )

    await ctx.info(f'Started execution {response["executionArn"]}')

    # Wait for execution to complete
    while True:
        execution = sfn_client.describe_execution(executionArn=response['executionArn'])
        status = execution['status']
        await ctx.info(f'Execution status: {status}')

        if status == 'SUCCEEDED':
            output = execution['output']
            return format_state_machine_response(state_machine_name, output.encode())
        elif status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
            error_message = (
                f'State machine {state_machine_name} execution failed with status: {status}'
            )
            if 'error' in execution:
                error_message += f', error: {execution["error"]}'
            if 'cause' in execution:
                error_message += f', cause: {execution["cause"]}'
            await ctx.error(error_message)
            return error_message

        # Wait before checking again
        await asyncio.sleep(1)


async def invoke_express_state_machine_impl(
    state_machine_name: str, state_machine_arn: str, parameters: dict, ctx: Context
) -> str:
    """Execute an Express state machine using StartSyncExecution."""
    await ctx.info(f'Starting synchronous execution of Express state machine {state_machine_name}')

    # Start synchronous execution
    response = sfn_client.start_sync_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(parameters),
    )

    # Check execution status
    status = response['status']
    await ctx.info(f'Express execution completed with status: {status}')

    if status == 'SUCCEEDED':
        output = response['output']
        return format_state_machine_response(state_machine_name, output.encode())
    else:
        error_message = (
            f'Express state machine {state_machine_name} execution failed with status: {status}'
        )
        if 'error' in response:
            error_message += f', error: {response["error"]}'
        if 'cause' in response:
            error_message += f', cause: {response["cause"]}'
        await ctx.error(error_message)
        return error_message


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


def create_state_machine_tool(
    state_machine_name: str,
    state_machine_arn: str,
    state_machine_type: str,
    description: str,
    schema_arn: Optional[str] = None,
):
    """Create a tool function for a Step Functions state machine.

    Args:
        state_machine_name: Name of the Step Functions state machine
        state_machine_arn: ARN of the Step Functions state machine
        state_machine_type: Type of the state machine (STANDARD or EXPRESS)
        description: Base description for the tool
        schema_arn: Optional ARN of the input schema in the Schema Registry
    """
    # Create a meaningful tool name
    tool_name = sanitize_tool_name(state_machine_name)

    # Define the inner function
    async def state_machine_function(parameters: dict, ctx: Context) -> str:
        """Tool for invoking a specific AWS Step Functions state machine with parameters."""
        # Use the appropriate implementation based on state machine type
        if state_machine_type == 'EXPRESS':
            return await invoke_express_state_machine_impl(
                state_machine_name, state_machine_arn, parameters, ctx
            )
        else:  # STANDARD
            return await invoke_standard_state_machine_impl(
                state_machine_name, state_machine_arn, parameters, ctx
            )

    # Set the function's documentation
    if schema_arn:
        schema = get_schema_from_registry(schema_arn)
        if schema:
            #  We add the schema to the description because mcp.tool does not expose overriding the tool schema.
            description_with_schema = f'{description}\n\nInput Schema:\n{schema}'
            state_machine_function.__doc__ = description_with_schema
            logger.info(
                f'Added schema from registry to description for state machine {state_machine_name}'
            )
        else:
            state_machine_function.__doc__ = description
    else:
        state_machine_function.__doc__ = description

    logger.info(f'Registering tool {tool_name} with description: {description}')
    # Apply the decorator manually with the specific name
    decorated_function = mcp.tool(name=tool_name)(state_machine_function)

    return decorated_function


def get_schema_arn_from_state_machine_arn(state_machine_arn: str) -> Optional[str]:
    """Get schema ARN from state machine tags if configured.

    Args:
        state_machine_arn: ARN of the Step Functions state machine

    Returns:
        Schema ARN if found and configured, None otherwise
    """
    if not STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY:
        logger.info(
            'No schema tag environment variable provided (STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY ).'
        )
        return None

    try:
        tags_response = sfn_client.list_tags_for_resource(resourceArn=state_machine_arn)
        tags = {tag['key']: tag['value'] for tag in tags_response.get('tags', [])}
        if STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY in tags:
            return tags[STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY]
        else:
            logger.info(
                f'No schema arn provided for state machine {state_machine_arn} via tag {STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY}'
            )
    except Exception as e:
        logger.warning(f'Error checking tags for state machine {state_machine_arn}: {e}')

    return None


def filter_state_machines_by_tag(state_machines, tag_key, tag_value):
    """Filter Step Functions state machines by a specific tag key-value pair.

    Args:
        state_machines: List of Step Functions state machine objects
        tag_key: Tag key to filter by
        tag_value: Tag value to filter by

    Returns:
        List of Step Functions state machines that have the specified tag key-value pair
    """
    logger.info(f'Filtering state machines by tag key-value pair: {tag_key}={tag_value}')
    tagged_state_machines = []

    for state_machine in state_machines:
        try:
            # Get tags for the state machine
            tags_response = sfn_client.list_tags_for_resource(
                resourceArn=state_machine['stateMachineArn']
            )
            tags = {tag['key']: tag['value'] for tag in tags_response.get('tags', [])}

            # Check if the state machine has the specified tag key-value pair
            if tag_key in tags and tags[tag_key] == tag_value:
                tagged_state_machines.append(state_machine)
        except Exception as e:
            logger.warning(f'Error getting tags for state machine {state_machine["name"]}: {e}')

    logger.info(
        f'{len(tagged_state_machines)} Step Functions state machines found with tag {tag_key}={tag_value}.'
    )
    return tagged_state_machines


def register_state_machines():
    """Register Step Functions state machines as individual tools."""
    try:
        logger.info('Registering Step Functions state machines as individual tools...')
        state_machines = sfn_client.list_state_machines()

        # Get all state machines
        all_state_machines = state_machines['stateMachines']
        logger.info(f'Total Step Functions state machines found: {len(all_state_machines)}')

        # First filter by state machine name if prefix or list is set
        if STATE_MACHINE_PREFIX or STATE_MACHINE_LIST:
            valid_state_machines = [
                sm for sm in all_state_machines if validate_state_machine_name(sm['name'])
            ]
            logger.info(
                f'{len(valid_state_machines)} Step Functions state machines found after name filtering.'
            )
        else:
            valid_state_machines = all_state_machines
            logger.info(
                'No name filtering applied (both STATE_MACHINE_PREFIX and STATE_MACHINE_LIST are empty).'
            )

        # Then filter by tag if both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE are set and non-empty
        if STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE:
            tagged_state_machines = filter_state_machines_by_tag(
                valid_state_machines, STATE_MACHINE_TAG_KEY, STATE_MACHINE_TAG_VALUE
            )
            valid_state_machines = tagged_state_machines
        elif STATE_MACHINE_TAG_KEY or STATE_MACHINE_TAG_VALUE:
            logger.warning(
                'Both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE must be set to filter by tag.'
            )
            valid_state_machines = []

        for state_machine in valid_state_machines:
            state_machine_name = state_machine['name']
            state_machine_arn = state_machine['stateMachineArn']

            # Get state machine description from describe_state_machine
            try:
                state_machine_details = sfn_client.describe_state_machine(
                    stateMachineArn=state_machine_arn
                )
                description = state_machine_details.get(
                    'description', f'AWS Step Functions state machine: {state_machine_name}'
                )
                # Parse definition and get Comment if present
                definition = json.loads(state_machine_details.get('definition', '{}'))
                if 'Comment' in definition:
                    description = f'{description}\n\nWorkflow Description: {definition["Comment"]}'
            except Exception as e:
                logger.warning(
                    f'Error getting details for state machine {state_machine_name}: {e}'
                )
                description = f'AWS Step Functions state machine: {state_machine_name}'

            schema_arn = get_schema_arn_from_state_machine_arn(state_machine_arn)
            create_state_machine_tool(
                state_machine_name,
                state_machine_arn,
                state_machine['type'],
                description,
                schema_arn,
            )

        logger.info('Step Functions state machines registered successfully as individual tools.')

    except Exception as e:
        logger.error(f'Error registering Step Functions state machines as tools: {e}')


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Model Context Protocol (MCP) server for Step Functions'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    register_state_machines()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
