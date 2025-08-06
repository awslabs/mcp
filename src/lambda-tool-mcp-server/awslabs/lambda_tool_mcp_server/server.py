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

"""awslabs lambda MCP Server implementation."""

import json
import logging
import os
import re
from typing import Optional, Dict

import boto3
from pydantic import BaseModel, Field, validator
from mcp.server.fastmcp import Context, FastMCP

# ------------------------------------------------------------------------------
# logging setup
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Pydantic model for AWS credentials passed in to every tool call
# ------------------------------------------------------------------------------
class AWSConfig(BaseModel):
    """AWS credentials and region for creating clients."""
    aws_access_key_id: str = Field(..., description="AWS access key ID")
    aws_secret_access_key: str = Field(..., description="AWS secret access key")
    region_name: str = Field(..., description="AWS region, e.g. 'us-east-1'")

    @validator("region_name")
    def region_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("region_name must be a non-empty string")
        return v

# ------------------------------------------------------------------------------
# Read optional function‐filtering parameters from env for compatibility
# ------------------------------------------------------------------------------
FUNCTION_PREFIX = os.environ.get("FUNCTION_PREFIX", "").strip()
FUNCTION_LIST = [
    fn.strip()
    for fn in os.environ.get("FUNCTION_LIST", "").split(",")
    if fn.strip()
]
FUNCTION_TAG_KEY = os.environ.get("FUNCTION_TAG_KEY", "").strip()
FUNCTION_TAG_VALUE = os.environ.get("FUNCTION_TAG_VALUE", "").strip()
FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY = os.environ.get(
    "FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY"
)

logger.info(f"FUNCTION_PREFIX: {FUNCTION_PREFIX!r}")
logger.info(f"FUNCTION_LIST: {FUNCTION_LIST}")
logger.info(f"FUNCTION_TAG_KEY: {FUNCTION_TAG_KEY!r}")
logger.info(f"FUNCTION_TAG_VALUE: {FUNCTION_TAG_VALUE!r}")
logger.info(f"FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY: {FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY!r}")

# ------------------------------------------------------------------------------
# MCP server instance
# ------------------------------------------------------------------------------
mcp = FastMCP(
    "awslabs.lambda-tool-mcp-server",
    instructions=(
        "Use AWS Lambda functions to improve your answers. "
        "These Lambda functions give you additional capabilities and access "
        "to AWS services and resources in an AWS account."
    ),
    dependencies=["pydantic", "boto3"],
)


# ------------------------------------------------------------------------------
# Helper: instantiate any AWS client from AWSConfig
# ------------------------------------------------------------------------------
def get_aws_client(service_name: str, credentials: AWSConfig):
    """
    Create a boto3 client for the given service using explicit credentials.
    """
    return boto3.client(
        service_name,
        aws_access_key_id=credentials.aws_access_key_id,
        aws_secret_access_key=credentials.aws_secret_access_key,
        region_name=credentials.region_name,
    )


# ------------------------------------------------------------------------------
# Validation / filtering for function discovery
# ------------------------------------------------------------------------------
def validate_function_name(function_name: str) -> bool:
    """Allow if no prefix/list is set, else must match."""
    if not FUNCTION_PREFIX and not FUNCTION_LIST:
        return True
    if FUNCTION_PREFIX and function_name.startswith(FUNCTION_PREFIX):
        return True
    if FUNCTION_LIST and function_name in FUNCTION_LIST:
        return True
    return False


def filter_functions_by_tag(functions, tag_key: str, tag_value: str):
    """Return only functions with the given tag key=value."""
    logger.info(f"Filtering {len(functions)} functions by tag {tag_key}={tag_value}")
    filtered = []
    for fn in functions:
        try:
            tags = get_aws_client("lambda", aws_creds).list_tags(
                Resource=fn["FunctionArn"]
            ).get("Tags", {})
            if tags.get(tag_key) == tag_value:
                filtered.append(fn)
        except Exception as e:
            logger.warning(f"Could not retrieve tags for {fn['FunctionName']}: {e}")
    logger.info(f"{len(filtered)} functions remain after tag filter.")
    return filtered


# ------------------------------------------------------------------------------
# Schema registry helper
# ------------------------------------------------------------------------------
def get_schema_from_registry(
    schemas_client, schema_arn: str
) -> Optional[str]:
    """Fetch and return the raw schema content for a given ARN."""
    try:
        parts = schema_arn.split(":")
        if len(parts) < 6:
            logger.error(f"Bad schema ARN: {schema_arn}")
            return None
        registry, name = parts[5].split("/")[1:]
        resp = schemas_client.describe_schema(
            RegistryName=registry, SchemaName=name
        )
        return resp.get("Content")
    except Exception as e:
        logger.error(f"Error fetching schema {schema_arn}: {e}")
        return None


# ------------------------------------------------------------------------------
# Generic invoker implementation
# ------------------------------------------------------------------------------
async def invoke_lambda_function_impl(
    function_name: str,
    parameters: Dict,
    aws_config: AWSConfig,
    ctx: Context,
) -> str:
    """
    Invoke a Lambda by name, passing parameters, using the provided AWSConfig.
    """
    await ctx.info(f"Invoking {function_name} with parameters: {parameters}")
    lambda_client = get_aws_client("lambda", aws_config)

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(parameters),
    )
    await ctx.info(f"StatusCode: {response['StatusCode']}")
    if "FunctionError" in response:
        errmsg = f"Function {function_name} error: {response['FunctionError']}"
        await ctx.error(errmsg)
        return errmsg

    payload = response["Payload"].read()
    try:
        parsed = json.loads(payload)
        pretty = json.dumps(parsed, indent=2)
        return f"Function {function_name} returned:\n{pretty}"
    except Exception:
        return f"Function {function_name} returned raw payload: {payload!r}"


# ------------------------------------------------------------------------------
# Tool‐factory: create one decorator per Lambda
# ------------------------------------------------------------------------------
def create_lambda_tool(
    function_name: str, description: str, schema_arn: Optional[str] = None
):
    """
    Dynamically register an MCP tool that calls a specific Lambda.
    Expects incoming parameters to include:
      - aws_config: dict matching AWSConfig
      - payload: dict of the actual function arguments
    """
    tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", function_name)
    if tool_name[0].isdigit():
        tool_name = "_" + tool_name

    # pull in JSON schema if available
    doc = description
    if schema_arn:
        # note: we fetch schema only once at startup
        aws_creds = AWSConfig(
            aws_access_key_id="DUMMY",
            aws_secret_access_key="DUMMY",
            region_name="us-east-1",
        )
        client = get_aws_client("schemas", aws_creds)
        schema_content = get_schema_from_registry(client, schema_arn)
        if schema_content:
            doc = f"{description}\n\nInput Schema:\n{schema_content}"

    @mcp.tool(name=tool_name, description=doc)
    async def _lambda_tool(args: Dict, ctx: Context) -> str:
        """
        args must have:
          - aws_config: { aws_access_key_id, aws_secret_access_key, region_name }
          - payload: the dict passed to the Lambda
        """
        # validate aws_config
        raw_conf = args.get("aws_config")
        aws_conf = AWSConfig(**raw_conf)
        payload = args.get("payload", {})
        return await invoke_lambda_function_impl(
            function_name, payload, aws_conf, ctx
        )

    return _lambda_tool


# ------------------------------------------------------------------------------
# Discover & register all your Lambda functions
# ------------------------------------------------------------------------------
def register_lambda_functions():
    # for discovery we still need a client; fall back to env if no creds
    # allows your MCP server to discover fns via profile if you want.
    fallback = boto3.Session().client("lambda")
    all_fns = fallback.list_functions()["Functions"]
    valid = [f for f in all_fns if validate_function_name(f["FunctionName"])]

    if FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE:
        valid = filter_functions_by_tag(valid, FUNCTION_TAG_KEY, FUNCTION_TAG_VALUE)

    for fn in valid:
        arn = fn["FunctionArn"]
        desc = fn.get("Description", f"Invoke Lambda {fn['FunctionName']}")
        schema_arn = None
        if FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY:
            tags = fallback.list_tags(Resource=arn).get("Tags", {})
            schema_arn = tags.get(FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY)
        create_lambda_tool(fn["FunctionName"], desc, schema_arn)

    logger.info(f"Registered {len(valid)} Lambda tools.")


# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------
def main():
    register_lambda_functions()
    mcp.run()


if __name__ == "__main__":
    main()
