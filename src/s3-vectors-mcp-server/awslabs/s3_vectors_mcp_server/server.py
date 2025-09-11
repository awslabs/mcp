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

"""AWS S3 Vectors MCP Server implementation.

This server provides a Model Context Protocol (MCP) interface for interacting with AWS S3 Vectors service,
enabling programmatic access to embed and store vectors, as well as query for similar vectors using
Amazon Bedrock models for embeddings.
"""

import argparse
import boto3
import functools
import json
import os
import platform
import sys
import traceback
import uuid
from awslabs.s3_vectors_mcp_server import __version__
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from s3vectors.core.services import BedrockService, S3VectorService
from s3vectors.utils.config import get_region
from typing import Annotated, Any, Dict, Optional


class S3VectorsMCPServer(FastMCP):
    """Extended FastMCP server with logging capabilities."""

    def __init__(self, *args, **kwargs):
        """Initialize the S3 Vectors MCP server with logging capabilities.

        Args:
            *args: Positional arguments passed to FastMCP
            **kwargs: Keyword arguments passed to FastMCP
        """
        super().__init__(*args, **kwargs)

        os_name = platform.system().lower()
        if os_name == 'darwin':
            self.log_dir = os.path.expanduser('~/Library/Logs')
        elif os_name == 'windows':
            self.log_dir = os.path.expanduser('~/AppData/Local/Logs')
        else:
            self.log_dir = os.path.expanduser('~/.local/share/s3-vectors-mcp-server/logs/')


# Initialize FastMCP app
app = S3VectorsMCPServer(
    name='s3-vectors-server',
    instructions='A Model Context Protocol (MCP) server that enables programmatic access to AWS S3 Vectors service. This server provides tools for embedding text using Amazon Bedrock models and storing/querying vectors in S3 Vectors service for similarity search and retrieval.',
    version=__version__,
)


def log_tool_call_with_response(func):
    """Decorator to log tool call, response, and errors, using the function name automatically.

    Skips logging during tests if MCP_SERVER_DISABLE_LOGGING is set.

    Args:
        func: The function to decorate

    Returns:
        The decorated function
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Disable logging during tests
        if os.environ.get('PYTEST_CURRENT_TEST') or os.environ.get('MCP_SERVER_DISABLE_LOGGING'):
            return await func(*args, **kwargs)
        tool_name = func.__name__
        # Log the call
        try:
            os.makedirs(app.log_dir, exist_ok=True)
            log_file = os.path.join(app.log_dir, 'mcp-server-awslabs.s3-vectors-mcp-server.log')
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'tool': tool_name,
                'event': 'call',
                'args': args,
                'kwargs': kwargs,
                'mcp_version': __version__,
            }
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')
        except Exception as e:
            print(
                f"ERROR: Failed to create or write to log file in directory '{app.log_dir}': {e}",
                file=sys.stderr,
            )
            sys.exit(1)
        # Execute the function and log response or error
        try:
            response = await func(*args, **kwargs)
            try:
                log_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'tool': tool_name,
                    'event': 'response',
                    'response': response,
                    'mcp_version': __version__,
                }
                with open(log_file, 'a') as f:
                    f.write(json.dumps(log_entry, default=str) + '\n')
            except Exception as e:
                print(
                    f"ERROR: Failed to log response in directory '{app.log_dir}': {e}",
                    file=sys.stderr,
                )
            return response
        except Exception as e:
            tb = traceback.format_exc()
            try:
                log_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'tool': tool_name,
                    'event': 'error',
                    'error': str(e),
                    'traceback': tb,
                    'mcp_version': __version__,
                }
                with open(log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as log_e:
                print(
                    f"ERROR: Failed to log error in directory '{app.log_dir}': {log_e}",
                    file=sys.stderr,
                )
            raise

    return wrapper


def log_tool_call(tool_name, *args, **kwargs):
    """Log a tool call with its arguments and metadata to the server log file.

    Args:
        tool_name (str): The name of the tool being called.
        *args: Positional arguments passed to the tool.
        **kwargs: Keyword arguments passed to the tool.
    """
    try:
        os.makedirs(app.log_dir, exist_ok=True)
        log_file = os.path.join(app.log_dir, 'mcp-server-awslabs.s3-vectors-mcp-server.log')
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tool': tool_name,
            'args': args,
            'kwargs': kwargs,
            'mcp_version': __version__,
        }
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')
    except Exception as e:
        print(
            f"ERROR: Failed to create or write to log file in directory '{app.log_dir}': {e}",
            file=sys.stderr,
        )


def get_aws_session(profile_name: Optional[str] = None) -> boto3.Session:
    """Create AWS session with optional profile.

    Args:
        profile_name: Optional AWS profile name

    Returns:
        boto3.Session: Configured AWS session
    """
    if profile_name:
        return boto3.Session(profile_name=profile_name)
    else:
        return boto3.Session()


def get_env_or_param(param_value: Optional[str], env_var: str, param_name: str) -> str:
    """Get value from parameter or environment variable, with validation.

    Args:
        param_value: Parameter value (takes precedence)
        env_var: Environment variable name
        param_name: Parameter name for error messages

    Returns:
        str: The resolved value

    Raises:
        ValueError: If neither parameter nor environment variable is set
    """
    if param_value:
        return param_value

    env_value = os.getenv(env_var)
    if env_value:
        return env_value

    raise ValueError(
        f'{param_name} must be provided either as parameter or via {env_var} environment variable'
    )


def get_optional_env_or_param(param_value: Optional[str], env_var: str) -> Optional[str]:
    """Get optional value from parameter or environment variable.

    Args:
        param_value: Parameter value (takes precedence)
        env_var: Environment variable name

    Returns:
        Optional[str]: The resolved value or None
    """
    if param_value:
        return param_value
    return os.getenv(env_var)


@app.tool()
@log_tool_call_with_response
async def s3vectors_put(
    text: Annotated[str, Field(..., description='Text to embed and store as vector')],
    vector_id: Annotated[
        Optional[str],
        Field(None, description='Optional vector ID (auto-generated if not provided)'),
    ] = None,
    metadata: Annotated[
        Optional[Dict[str, Any]],
        Field(None, description='Optional metadata to store with the vector'),
    ] = None,
) -> str:
    """Embed text and store as vector in S3 Vectors.

    This tool takes input text, generates embeddings using Amazon Bedrock models,
    and stores the resulting vector in AWS S3 Vectors service for later similarity search.

    Environment Variables (required):
        S3VECTORS_BUCKET_NAME: S3 bucket name for vector storage
        S3VECTORS_INDEX_NAME: Vector index name
        S3VECTORS_MODEL_ID: Bedrock embedding model ID

    Environment Variables (optional):
        S3VECTORS_REGION: AWS region (defaults to configured region)
        S3VECTORS_PROFILE: AWS profile name (defaults to default profile)
        S3VECTORS_DIMENSIONS: Embedding dimensions (model-specific default if not set)

    Args:
        text: Text to embed and store
        vector_id: Optional vector ID (auto-generated UUID if not provided)
        metadata: Optional metadata dictionary to store with the vector

    Returns:
        JSON string with operation result including vector_id, bucket, index, and metadata

    Raises:
        ValueError: If required environment variables are not set
        Exception: If embedding generation or vector storage fails

    Example:
        text: "This is sample text to embed"
        vector_id: "doc-123" (optional)
        metadata: {"category": "documentation", "version": "1.0"} (optional)
    """
    try:
        # Get required parameters from env vars
        bucket_name = get_env_or_param(None, 'S3VECTORS_BUCKET_NAME', 'S3VECTORS_BUCKET_NAME')
        idx_name = get_env_or_param(None, 'S3VECTORS_INDEX_NAME', 'S3VECTORS_INDEX_NAME')
        mdl_id = get_env_or_param(None, 'S3VECTORS_MODEL_ID', 'S3VECTORS_MODEL_ID')

        # Get optional parameters
        aws_profile = get_optional_env_or_param(None, 'S3VECTORS_PROFILE')
        dimensions_str = get_optional_env_or_param(None, 'S3VECTORS_DIMENSIONS')
        dimensions = int(dimensions_str) if dimensions_str else None

        # Set defaults
        if vector_id is None:
            vector_id = str(uuid.uuid4())
        if metadata is None:
            metadata = {}

        # Initialize AWS session and get region
        session = get_aws_session(aws_profile)
        aws_region = get_optional_env_or_param(None, 'S3VECTORS_REGION') or get_region(session)

        # Initialize AWS services
        bedrock_service = BedrockService(session, aws_region, debug=False)
        s3vector_service = S3VectorService(session, aws_region, debug=False)

        # Generate embedding
        embedding = bedrock_service.embed_text(mdl_id, text, dimensions)

        # Store vector
        result_vector_id = s3vector_service.put_vector(
            bucket_name=bucket_name,
            index_name=idx_name,
            vector_id=vector_id,
            embedding=embedding,
            metadata=metadata,
        )

        # Prepare result
        result = {
            'success': True,
            'vector_id': result_vector_id,
            'bucket': bucket_name,
            'index': idx_name,
            'model_id': mdl_id,
            'region': aws_region,
            'profile': aws_profile,
            'text_length': len(text),
            'embedding_dimensions': len(embedding),
            'metadata': metadata,
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        error_result = {'success': False, 'error': str(e), 'operation': 's3vectors_put'}
        return json.dumps(error_result, indent=2)


@app.tool()
@log_tool_call_with_response
async def s3vectors_query(
    query_text: Annotated[str, Field(..., description='Text to query for similar vectors')],
    top_k: Annotated[int, Field(10, description='Number of similar vectors to return')] = 10,
    filter_expr: Annotated[
        Optional[Dict[str, Any]],
        Field(None, description='Optional metadata filter expression (JSON format)'),
    ] = None,
    return_metadata: Annotated[
        bool, Field(True, description='Include metadata in results')
    ] = True,
    return_distance: Annotated[
        bool, Field(False, description='Include similarity distance in results')
    ] = False,
) -> str:
    """Query for similar vectors in S3 Vectors.

    This tool takes input text, generates embeddings using Amazon Bedrock models,
    and searches for similar vectors in AWS S3 Vectors service using vector similarity.

    Environment Variables (required):
        S3VECTORS_BUCKET_NAME: S3 bucket name for vector storage
        S3VECTORS_INDEX_NAME: Vector index name
        S3VECTORS_MODEL_ID: Bedrock embedding model ID

    Environment Variables (optional):
        S3VECTORS_REGION: AWS region (defaults to configured region)
        S3VECTORS_PROFILE: AWS profile name (defaults to default profile)
        S3VECTORS_DIMENSIONS: Embedding dimensions (model-specific default if not set)

    Args:
        query_text: Text to query for similar vectors
        top_k: Number of similar vectors to return (default: 10)
        filter_expr: Optional metadata filter expression (JSON format)
        return_metadata: Include metadata in results (default: True)
        return_distance: Include similarity distance in results (default: False)

    Returns:
        JSON string with query results including similar vectors and their metadata

    Filter Expression (filter_expr):
        Supports AWS S3 Vectors API operators for metadata-based filtering.

        Comparison Operators:
        - $eq: Equal to
        - $ne: Not equal to
        - $gt: Greater than
        - $gte: Greater than or equal to
        - $lt: Less than
        - $lte: Less than or equal to
        - $in: Value in array
        - $nin: Value not in array

        Logical Operators:
        - $and: Logical AND (all conditions must be true)
        - $or: Logical OR (at least one condition must be true)
        - $not: Logical NOT (condition must be false)

    Examples:
        Single condition filters:
        {"category": {"$eq": "documentation"}}
        {"status": {"$ne": "archived"}}
        {"version": {"$gte": "2.0"}}
        {"category": {"$in": ["docs", "guides", "tutorials"]}}

        Multiple condition filters:
        {"$and": [{"category": "tech"}, {"version": "1.0"}]}
        {"$or": [{"category": "docs"}, {"category": "guides"}]}
        {"$not": {"category": {"$eq": "archived"}}}

        Complex nested conditions:
        {"$and": [{"category": "tech"}, {"$or": [{"version": "1.0"}, {"version": "2.0"}]}]}
        {"$and": [{"category": "documentation"}, {"version": {"$gte": "1.0"}}, {"status": {"$ne": "draft"}}]}
        {"$or": [{"$and": [{"category": "docs"}, {"version": "1.0"}]}, {"$and": [{"category": "guides"}, {"version": "2.0"}]}]}

    Notes:
        - String comparisons are case-sensitive
        - Ensure filter values match the data types in your metadata
        - Use proper JSON format with double quotes for keys and string values

    Raises:
        ValueError: If required environment variables are not set
        Exception: If embedding generation or vector query fails

    Example:
        query_text: "Find similar documentation"
        top_k: 5
        filter_expr: {"category": {"$eq": "documentation"}}
        return_metadata: True
        return_distance: False
    """
    try:
        # Get required parameters from env vars
        bucket_name = get_env_or_param(None, 'S3VECTORS_BUCKET_NAME', 'S3VECTORS_BUCKET_NAME')
        idx_name = get_env_or_param(None, 'S3VECTORS_INDEX_NAME', 'S3VECTORS_INDEX_NAME')
        mdl_id = get_env_or_param(None, 'S3VECTORS_MODEL_ID', 'S3VECTORS_MODEL_ID')

        # Get optional parameters
        aws_profile = get_optional_env_or_param(None, 'S3VECTORS_PROFILE')
        dimensions_str = get_optional_env_or_param(None, 'S3VECTORS_DIMENSIONS')
        dimensions = int(dimensions_str) if dimensions_str else None

        # Initialize AWS session first
        session = get_aws_session(aws_profile)

        # Get region (requires session)
        aws_region = get_optional_env_or_param(None, 'S3VECTORS_REGION') or get_region(session)

        # Initialize AWS services
        bedrock_service = BedrockService(session, aws_region, debug=False)
        s3vector_service = S3VectorService(session, aws_region, debug=False)

        # Generate query embedding
        query_embedding = bedrock_service.embed_text(mdl_id, query_text, dimensions)

        # Prepare query parameters
        query_params = {
            'bucket_name': bucket_name,
            'index_name': idx_name,
            'query_embedding': query_embedding,
            'k': top_k,
            'return_metadata': return_metadata,
            'return_distance': return_distance,
        }

        # Add optional parameters if provided
        if filter_expr:
            # Convert dict to JSON string as S3VectorService expects string
            filter_expr_str = json.dumps(filter_expr)
            query_params['filter_expr'] = filter_expr_str

        # Perform vector search
        search_results = s3vector_service.query_vectors(**query_params)

        # Format results
        formatted_results = []
        for result in search_results:
            formatted_result = {
                'vector_id': result.get('vectorId'),
                'similarity': result.get('similarity'),
            }

            if return_metadata and 'metadata' in result:
                formatted_result['metadata'] = result.get('metadata', {})

            if return_distance and 'similarity' in result:
                # S3VectorService returns 'similarity' which is the distance/score
                formatted_result['distance'] = result.get('similarity')

            formatted_results.append(formatted_result)

        # Prepare response
        response = {
            'success': True,
            'query_text': query_text,
            'bucket': bucket_name,
            'index': idx_name,
            'model_id': mdl_id,
            'region': aws_region,
            'profile': aws_profile,
            'top_k': top_k,
            'filter': filter_expr,
            'return_metadata': return_metadata,
            'return_distance': return_distance,
            'query_embedding_dimensions': len(query_embedding),
            'results_count': len(formatted_results),
            'results': formatted_results,
        }

        return json.dumps(response, indent=2)

    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'operation': 's3vectors_query',
        }
        return json.dumps(error_result, indent=2)


def main():
    """Run the MCP server with CLI argument support.

    This function initializes and runs the AWS S3 Vectors MCP server, which provides
    programmatic access to embed and query vectors through the Model Context Protocol.
    """
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for S3 Vectors'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default=None,
        help='Directory to write logs to. Defaults to /var/logs on Linux and ~/Library/Logs on MacOS.',
    )

    args = parser.parse_args()

    # Determine log directory
    if args.log_dir:
        app.log_dir = os.path.expanduser(args.log_dir)

    # Log program startup details
    log_tool_call(
        'server_start',
        argv=sys.argv,
        parsed_args=vars(args),
        mcp_version=__version__,
        python_version=sys.version,
        platform=platform.platform(),
    )

    app.run()


# FastMCP application runner
if __name__ == '__main__':
    print('Starting S3 Vectors MCP server...')
    main()
