"""Configuration module for the OpenAPI MCP Server."""

import os
from dataclasses import dataclass
from typing import Optional, Any

from awslabs.openapi_mcp_server import logger, get_caller_info


@dataclass
class Config:
    """Configuration for the OpenAPI MCP Server."""
    
    # API information
    api_name: str = "petstore"
    api_base_url: str = "https://petstore3.swagger.io/api/v3"
    api_spec_url: str = ""
    api_spec_path: str = ""
    
    # Authentication
    auth_type: str = "none"  # none, basic, bearer, api_key
    auth_username: str = ""
    auth_password: str = ""
    auth_token: str = ""
    auth_api_key: str = ""
    auth_api_key_name: str = "api_key"
    auth_api_key_in: str = "header"  # header, query, cookie
    
    # Server configuration
    port: int = 8000
    # Default to localhost for security; use SERVER_HOST env var to override when needed (e.g. in Docker)
    host: str = "127.0.0.1"
    debug: bool = False
    transport: str = "stdio"  # stdio, sse
    message_timeout: int = 60


def load_config(args: Any = None) -> Config:
    """
    Load configuration from arguments and environment variables.
    
    Args:
        args: Command line arguments
        
    Returns:
        Config: Configuration object
    """
    logger.debug("Loading configuration")
    
    # Get caller information for debugging
    caller_info = get_caller_info()
    logger.debug(f"Called from {caller_info}")
    
    # Create default config
    config = Config()
    
    # Load from environment variables
    env_vars = {
        # API information
        "API_NAME": (lambda v: setattr(config, "api_name", v)),
        "API_BASE_URL": (lambda v: setattr(config, "api_base_url", v)),
        "API_SPEC_URL": (lambda v: setattr(config, "api_spec_url", v)),
        "API_SPEC_PATH": (lambda v: setattr(config, "api_spec_path", v)),
        
        # Authentication
        "AUTH_TYPE": (lambda v: setattr(config, "auth_type", v)),
        "AUTH_USERNAME": (lambda v: setattr(config, "auth_username", v)),
        "AUTH_PASSWORD": (lambda v: setattr(config, "auth_password", v)),
        "AUTH_TOKEN": (lambda v: setattr(config, "auth_token", v)),
        "AUTH_API_KEY": (lambda v: setattr(config, "auth_api_key", v)),
        "AUTH_API_KEY_NAME": (lambda v: setattr(config, "auth_api_key_name", v)),
        "AUTH_API_KEY_IN": (lambda v: setattr(config, "auth_api_key_in", v)),
        
        # Server configuration
        "SERVER_PORT": (lambda v: setattr(config, "port", int(v))),
        "SERVER_HOST": (lambda v: setattr(config, "host", v)),
        "SERVER_DEBUG": (lambda v: setattr(config, "debug", v.lower() == "true")),
        "SERVER_TRANSPORT": (lambda v: setattr(config, "transport", v)),
        "SERVER_MESSAGE_TIMEOUT": (lambda v: setattr(config, "message_timeout", int(v))),
    }
    
    # Load environment variables
    env_loaded = {}
    for key, setter in env_vars.items():
        if key in os.environ:
            env_value = os.environ[key]
            setter(env_value)
            env_loaded[key] = env_value
    
    if env_loaded:
        logger.debug(f"Loaded {len(env_loaded)} environment variables: {', '.join(env_loaded.keys())}")
    
    # Load from arguments
    if args:
        if hasattr(args, "api_name") and args.api_name:
            logger.debug(f"Setting API name from arguments: {args.api_name}")
            config.api_name = args.api_name
            
        if hasattr(args, "api_url") and args.api_url:
            logger.debug(f"Setting API base URL from arguments: {args.api_url}")
            config.api_base_url = args.api_url
            
        if hasattr(args, "spec_url") and args.spec_url:
            logger.debug(f"Setting API spec URL from arguments: {args.spec_url}")
            config.api_spec_url = args.spec_url
            
        if hasattr(args, "spec_path") and args.spec_path:
            logger.debug(f"Setting API spec path from arguments: {args.spec_path}")
            config.api_spec_path = args.spec_path
            
        if hasattr(args, "port") and args.port:
            logger.debug(f"Setting port from arguments: {args.port}")
            config.port = args.port
            
        if hasattr(args, "sse") and args.sse:
            logger.debug("Setting transport to SSE from arguments")
            config.transport = "sse"
    
    # Log final configuration details
    logger.info(f"Configuration loaded: API name={config.api_name}, transport={config.transport}, port={config.port}")
    
    return config
