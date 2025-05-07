"""awslabs openapi MCP Server implementation."""

import argparse
import asyncio
import httpx

# Import from our modules - use direct imports from sub-modules for better patching in tests
from awslabs.openapi_mcp_server import get_caller_info, logger
from awslabs.openapi_mcp_server.api.config import Config, load_config
from awslabs.openapi_mcp_server.prompts.instructions import generate_api_instructions
from awslabs.openapi_mcp_server.utils.openapi import load_openapi_spec
from mcp.server.fastmcp import FastMCP


def create_mcp_server(config: Config) -> FastMCP:
    """Create and configure the FastMCP server.

    Args:
        config: Server configuration

    Returns:
        FastMCP: The configured FastMCP server
    """
    logger.info('Creating FastMCP server')

    # Create the FastMCP server
    server = FastMCP(
        'awslabs.openapi-mcp-server',
        instructions='This server acts as a bridge between OpenAPI specifications and LLMs, allowing models to have a better understanding of available API capabilities without requiring manual tool definitions.',
        dependencies=[
            'pydantic',
            'loguru',
            'httpx',
        ],
    )

    try:
        # Load OpenAPI spec
        if not config.api_spec_url and not config.api_spec_path:
            logger.error('No API spec URL or path provided')
            raise ValueError('Either api_spec_url or api_spec_path must be provided')

        logger.debug(
            f'Loading OpenAPI spec from URL: {config.api_spec_url} or path: {config.api_spec_path}'
        )
        openapi_spec = load_openapi_spec(url=config.api_spec_url, path=config.api_spec_path)

        # Generate dynamic instructions
        logger.info(f'Generating instructions for API: {config.api_name}')
        asyncio.run(generate_api_instructions(server, config.api_name, openapi_spec))

        # Create a client for the API
        if not config.api_base_url:
            logger.error('No API base URL provided')
            raise ValueError('API base URL must be provided')

        # Configure authentication
        headers = {}

        if config.auth_type == 'basic':
            if not config.auth_username or not config.auth_password:
                logger.warning('Basic authentication enabled but username or password is missing')
            else:
                # Store auth in a variable that will be used later when creating the client
                # Use _ prefix to indicate intentionally unused variable (for future use)
                _auth = httpx.BasicAuth(
                    username=config.auth_username,
                    password=config.auth_password,
                )
                logger.info(f'Using Basic authentication for user: {config.auth_username}')

        elif config.auth_type == 'bearer':
            if not config.auth_token:
                logger.warning('Bearer authentication enabled but token is missing')
            else:
                headers['Authorization'] = f'Bearer {config.auth_token}'
                logger.info('Using Bearer token authentication')

        elif config.auth_type == 'api_key':
            if not config.auth_api_key:
                logger.warning('API key authentication enabled but API key is missing')
            else:
                if config.auth_api_key_in == 'header':
                    headers[config.auth_api_key_name] = config.auth_api_key
                    logger.info(
                        f'Using API key authentication in header: {config.auth_api_key_name}'
                    )
                elif config.auth_api_key_in == 'query':
                    logger.info(
                        f'Using API key authentication in query parameter: {config.auth_api_key_name}'
                    )
                elif config.auth_api_key_in == 'cookie':
                    # Create cookies dict to be used later when creating the client
                    _cookies = {config.auth_api_key_name: config.auth_api_key}
                    logger.info(
                        f'Using API key authentication in cookie: {config.auth_api_key_name}'
                    )
                else:
                    logger.warning(f'Unsupported API key location: {config.auth_api_key_in}')

    except Exception as e:
        caller_info = get_caller_info()
        logger.error(f'Error setting up API: {e} (called from {caller_info})')

    return server


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='This project is a server that dynamically creates Machine Conversation Protocol (MCP) tools and resources from OpenAPI specifications. It allows Large Language Models (LLMs) to interact with APIs through the Machine Conversation Protocol.'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, help='Port to run the server on')
    parser.add_argument('--api-name', help='Name of the API (default: petstore)')
    parser.add_argument('--api-url', help='Base URL of the API')
    parser.add_argument('--spec-url', help='URL of the OpenAPI specification')
    parser.add_argument('--spec-path', help='Local path to the OpenAPI specification file')
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set logging level',
    )

    args = parser.parse_args()

    # Set up logging with loguru at specified level
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), level=args.log_level)
    logger.info(f'Starting server with logging level: {args.log_level}')

    # Load configuration
    logger.debug('Loading configuration from arguments and environment')
    config = load_config(args)
    logger.debug(f'Configuration loaded: api_name={config.api_name}, transport={config.transport}')

    # Create and run the MCP server
    logger.info('Creating MCP server')
    mcp_server = create_mcp_server(config)

    # Run server with appropriate transport
    if config.transport == 'sse':
        logger.info(f'Running server with SSE transport on port {config.port}')
        mcp_server.settings.port = config.port
        mcp_server.run(transport='sse')
    else:
        logger.info('Running server with stdio transport')
        mcp_server.run()


if __name__ == '__main__':
    main()
