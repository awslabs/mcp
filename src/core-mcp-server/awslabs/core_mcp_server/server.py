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

import asyncio
import loguru
import os
import pathlib
import sys
from fastmcp import FastMCP
from fastmcp.server.proxy import ProxyClient
from typing import List, TypedDict


current_dir = pathlib.Path(__file__).parent
prompt_understanding_path = current_dir / 'static' / 'PROMPT_UNDERSTANDING.md'
with open(prompt_understanding_path, 'r', encoding='utf-8') as f:
    PROMPT_UNDERSTANDING = f.read()


class ContentItem(TypedDict):
    """A TypedDict representing a single content item in an MCP response.

    This class defines the structure for content items used in MCP server responses.
    Each content item contains a type identifier and the actual content text.

    Attributes:
        type (str): The type identifier for the content (e.g., 'text', 'error')
        text (str): The actual content text
    """

    type: str
    text: str


class McpResponse(TypedDict, total=False):
    """A TypedDict representing an MCP server response.

    This class defines the structure for responses returned by MCP server tools.
    It supports optional fields through total=False, allowing responses to omit
    the isError field when not needed.

    Attributes:
        content (List[ContentItem]): List of content items in the response
        isError (bool, optional): Flag indicating if the response represents an error
    """

    content: List[ContentItem]
    isError: bool


# Set up logging
logger = loguru.logger

logger.remove()
logger.add(sys.stderr, level='DEBUG')


mcp = FastMCP(
    'mcp-core MCP server.  This is the starting point for all solutions created',
    dependencies=[
        'loguru',
    ],
)


@mcp.tool(name='prompt_understanding')
def get_prompt_understanding() -> str:
    """MCP-CORE Prompt Understanding.

    ALWAYS Use this tool first to understand the user's query and translate it into AWS expert advice.
    """
    return PROMPT_UNDERSTANDING


# Helper function to import a server if not already imported
async def call_import_server(server, prefix, server_name, imported_servers=None):
    """Import an MCP server if not already imported.

    This function imports an MCP server using the FastMCP.as_proxy method and
    adds it to the set of imported servers to avoid duplicates.

    Args:
        server: The MCP server to import
        prefix: The prefix to use for the server
        server_name: The name of the server for logging purposes
        imported_servers: A set of already imported server prefixes

    Returns:
        The updated set of imported servers
    """
    if imported_servers is None:
        imported_servers = set()

    if prefix not in imported_servers:
        try:
            local_proxy = FastMCP.as_proxy(
                ProxyClient(server),
            )
            await mcp.import_server(local_proxy, prefix=prefix)
            imported_servers.add(prefix)
            logger.info(f'Successfully imported {server_name}')
        except Exception as e:
            logger.error(f'Failed to import {server_name}: {e}')

    return imported_servers


def is_role_set(name: str) -> bool:
    """Returns true when the role is set in the environment variables.

    Args:
        name (str): The name of the role or environment variable to check.
    Will also check for unix style env var name and vice-versa based on input.
    for example: "aws-foundation" -> "AWS_FOUNDATION"
    """
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        alt_name = (
            name.replace('-', '_').upper() if '-' in name else name.replace('_', '-').lower()
        )
        value = os.environ.get(alt_name)
    return value is not None and value.strip() != ''


async def import_aws_knowledge_server(imported_servers: set) -> set:
    """Import the AWS Knowledge MCP server if not already imported.

    This function imports the AWS Knowledge MCP server using a remote configuration
    and adds it to the set of imported servers to avoid duplicates.

    Args:
        imported_servers: A set of already imported server prefixes
    Returns:
        The updated set of imported servers
    """
    config = {
        'mcpServers': {
            'aws-knowledge-mcp-server': {
                'command': 'uvx',
                'args': [
                    'mcp-proxy',
                    '--transport',
                    'streamablehttp',
                    'https://knowledge-mcp.global.api.aws',
                ],
                'env': os.environ,
            }
        }
    }
    return await call_import_server(
        config, 'aws_knowledge', 'aws_knowledge_server', imported_servers
    )


# Import subservers based on role configuration
async def setup():
    """Set up and import MCP servers based on role-based environment variables.

    This function dynamically imports MCP servers based on the role environment variables
    that are set. It uses a helper function to import each server only once, avoiding
    duplicates when a server is needed by multiple roles. If no roles are enabled,
    it will not import any servers.

    The function handles the following roles:
    - AWS Foundation
    - Dev Tools
    - CI/CD DevOps
    - Container Orchestration
    - Serverless Architecture
    - Analytics Warehouse
    - Data Platform Engineering
    - Frontend Development
    - Solutions Architect
    - FinOps
    - Monitoring & Observability
    - Caching & Performance
    - Security & Identity
    - SQL DB Specialist
    - NoSQL DB Specialist
    - Time Series DB Specialist
    - Messaging & Events
    - Healthcare & Life Sciences
    """
    # roles - environment variables for role-based server configuration
    aws_foundation = is_role_set('aws-foundation')
    dev_tools = is_role_set('dev-tools')
    ci_cd_devops = is_role_set('ci-cd-devops')
    container_orchestration = is_role_set('container-orchestration')
    serverless_architecture = is_role_set('serverless-architecture')
    analytics_warehouse = is_role_set('analytics-warehouse')
    data_platform_eng = is_role_set('data-platform-eng')
    frontend_dev = is_role_set('frontend-dev')
    solutions_architect = is_role_set('solutions-architect')
    finops = is_role_set('finops')
    monitoring_observability = is_role_set('monitoring-observability')
    caching_performance = is_role_set('caching-performance')
    security_identity = is_role_set('security-identity')
    sql_db_specialist = is_role_set('sql-db-specialist')
    nosql_db_specialist = is_role_set('nosql-db-specialist')
    timeseries_db_specialist = is_role_set('timeseries-db-specialist')
    messaging_events = is_role_set('messaging-events')
    healthcare_lifesci = is_role_set('healthcare-lifesci')
    # Track which servers have been imported to avoid duplicates
    imported_servers = set()

    # AWS Foundation
    if aws_foundation:
        from awslabs.aws_api_mcp_server.server import server as aws_api_server

        logger.info('Enabling AWS Knowledge Foundation servers')
        imported_servers = await import_aws_knowledge_server(imported_servers)
        imported_servers = await call_import_server(
            aws_api_server, 'aws_api', 'aws_api_server', imported_servers
        )

    # Dev Tools
    if dev_tools:
        from awslabs.code_doc_gen_mcp_server.server import mcp as code_doc_gen_server
        from awslabs.git_repo_research_mcp_server.server import mcp as git_repo_research_server

        logger.info('Enabling Dev Tools servers')
        imported_servers = await call_import_server(
            git_repo_research_server,
            'git_repo_research',
            'git_repo_research_server',
            imported_servers,
        )
        imported_servers = await call_import_server(
            code_doc_gen_server, 'code_doc_gen', 'code_doc_gen_server', imported_servers
        )
        imported_servers = await import_aws_knowledge_server(imported_servers)

    # CI/CD DevOps
    if ci_cd_devops:
        from awslabs.cdk_mcp_server.core.server import mcp as cdk_server
        from awslabs.cfn_mcp_server.server import mcp as cfn_server

        logger.info('Enabling CI/CD DevOps servers')
        imported_servers = await call_import_server(
            cdk_server, 'cdk', 'cdk_server', imported_servers
        )
        imported_servers = await call_import_server(
            cfn_server, 'cfn', 'cfn_server', imported_servers
        )

    # Container Orchestration
    if container_orchestration:
        from awslabs.ecs_mcp_server.main import mcp as ecs_server
        from awslabs.eks_mcp_server.server import mcp as eks_server
        from awslabs.finch_mcp_server.server import mcp as finch_server

        logger.info('Enabling Container Orchestration servers')
        imported_servers = await call_import_server(
            eks_server, 'eks', 'eks_server', imported_servers
        )
        imported_servers = await call_import_server(
            ecs_server, 'ecs', 'ecs_server', imported_servers
        )
        imported_servers = await call_import_server(
            finch_server, 'finch', 'finch_server', imported_servers
        )

    # Serverless Architecture
    if serverless_architecture:
        from awslabs.amazon_sns_sqs_mcp_server.server import mcp as sns_sqs_server
        from awslabs.aws_serverless_mcp_server.server import mcp as serverless_server
        from awslabs.lambda_tool_mcp_server.server import mcp as lambda_tool_server
        from awslabs.stepfunctions_tool_mcp_server.server import mcp as stepfunctions_tool_server

        logger.info('Enabling Serverless Architecture servers')
        imported_servers = await call_import_server(
            serverless_server, 'serverless', 'serverless_server', imported_servers
        )
        imported_servers = await call_import_server(
            lambda_tool_server, 'lambda_tool', 'lambda_tool_server', imported_servers
        )
        imported_servers = await call_import_server(
            stepfunctions_tool_server,
            'stepfunctions_tool',
            'stepfunctions_tool_server',
            imported_servers,
        )
        imported_servers = await call_import_server(
            sns_sqs_server, 'sns_sqs', 'sns_sqs_server', imported_servers
        )

    # Analytics Warehouse
    if analytics_warehouse:
        from awslabs.aws_dataprocessing_mcp_server.server import mcp as dataprocessing_server
        from awslabs.redshift_mcp_server.server import mcp as redshift_server
        from awslabs.syntheticdata_mcp_server.server import mcp as syntheticdata_server
        from awslabs.timestream_for_influxdb_mcp_server.server import (
            mcp as timestream_for_influxdb_server,
        )

        logger.info('Enabling Analytics Warehouse servers')
        imported_servers = await call_import_server(
            redshift_server, 'redshift', 'redshift_server', imported_servers
        )
        imported_servers = await call_import_server(
            timestream_for_influxdb_server,
            'timestream_for_influxdb',
            'timestream_for_influxdb_server',
            imported_servers,
        )
        imported_servers = await call_import_server(
            dataprocessing_server, 'dataprocessing', 'dataprocessing_server', imported_servers
        )
        imported_servers = await call_import_server(
            syntheticdata_server, 'syntheticdata', 'syntheticdata_server', imported_servers
        )

    # Data Platform Engineering
    if data_platform_eng:
        from awslabs.aws_dataprocessing_mcp_server.server import mcp as dataprocessing_server
        from awslabs.dynamodb_mcp_server.server import app as dynamodb_server
        from awslabs.s3_tables_mcp_server.server import app as s3_tables_server

        logger.info('Enabling Data Platform Engineering servers')
        imported_servers = await call_import_server(
            dynamodb_server, 'dynamodb', 'dynamodb_server', imported_servers
        )
        imported_servers = await call_import_server(
            s3_tables_server, 's3_tables', 's3_tables_server', imported_servers
        )
        imported_servers = await call_import_server(
            dataprocessing_server, 'dataprocessing', 'dataprocessing_server', imported_servers
        )

    # Frontend Development
    if frontend_dev:
        from awslabs.frontend_mcp_server.server import mcp as frontend_server
        from awslabs.nova_canvas_mcp_server.server import mcp as nova_canvas_server

        logger.info('Enabling Frontend Development servers')
        imported_servers = await call_import_server(
            frontend_server, 'frontend', 'frontend_server', imported_servers
        )
        imported_servers = await call_import_server(
            nova_canvas_server, 'nova_canvas', 'nova_canvas_server', imported_servers
        )

    # Solutions Architect
    if solutions_architect:
        from awslabs.aws_diagram_mcp_server.server import mcp as diagram_server
        from awslabs.aws_pricing_mcp_server.server import mcp as pricing_server
        from awslabs.cost_explorer_mcp_server.server import app as cost_explorer_server
        from awslabs.syntheticdata_mcp_server.server import mcp as syntheticdata_server

        logger.info('Enabling Solutions Architect servers')
        imported_servers = await call_import_server(
            diagram_server, 'diagram', 'diagram_server', imported_servers
        )
        imported_servers = await call_import_server(
            pricing_server, 'pricing', 'pricing_server', imported_servers
        )
        imported_servers = await call_import_server(
            cost_explorer_server, 'cost_explorer', 'cost_explorer_server', imported_servers
        )
        imported_servers = await call_import_server(
            syntheticdata_server, 'syntheticdata', 'syntheticdata_server', imported_servers
        )
        imported_servers = await import_aws_knowledge_server(imported_servers)

    # FinOps
    if finops:
        from awslabs.aws_pricing_mcp_server.server import mcp as pricing_server
        from awslabs.billing_cost_management_mcp_server.server import (
            mcp as billing_cost_management_server,
        )
        from awslabs.cloudwatch_mcp_server.server import mcp as cloudwatch_server
        from awslabs.cost_explorer_mcp_server.server import app as cost_explorer_server

        logger.info('Enabling FinOps servers')
        imported_servers = await call_import_server(
            cost_explorer_server, 'cost_explorer', 'cost_explorer_server', imported_servers
        )
        imported_servers = await call_import_server(
            pricing_server, 'pricing', 'pricing_server', imported_servers
        )
        imported_servers = await call_import_server(
            cloudwatch_server, 'cloudwatch', 'cloudwatch_server', imported_servers
        )
        imported_servers = await call_import_server(
            billing_cost_management_server,
            'billing_cost_management',
            'billing_cost_management_server',
            imported_servers,
        )

    # Monitoring & Observability
    if monitoring_observability:
        from awslabs.cloudtrail_mcp_server.server import mcp as cloudtrail_server
        from awslabs.cloudwatch_appsignals_mcp_server.server import (
            mcp as cloudwatch_appsignals_server,
        )
        from awslabs.cloudwatch_mcp_server.server import mcp as cloudwatch_server
        from awslabs.prometheus_mcp_server.server import mcp as prometheus_server

        logger.info('Enabling Monitoring & Observability servers')
        imported_servers = await call_import_server(
            cloudwatch_server, 'cloudwatch', 'cloudwatch_server', imported_servers
        )
        imported_servers = await call_import_server(
            cloudwatch_appsignals_server,
            'cloudwatch_appsignals',
            'cloudwatch_appsignals_server',
            imported_servers,
        )
        imported_servers = await call_import_server(
            prometheus_server, 'prometheus', 'prometheus_server', imported_servers
        )
        imported_servers = await call_import_server(
            cloudtrail_server, 'cloudtrail', 'cloudtrail_server', imported_servers
        )

    # Caching & Performance
    if caching_performance:
        from awslabs.elasticache_mcp_server.main import mcp as elasticache_server
        from awslabs.memcached_mcp_server.main import mcp as memcached_server

        logger.info('Enabling Caching & Performance servers')
        imported_servers = await call_import_server(
            elasticache_server, 'elasticache', 'elasticache_server', imported_servers
        )
        imported_servers = await call_import_server(
            memcached_server, 'memcached', 'memcached_server', imported_servers
        )

    # Security & Identity
    if security_identity:
        from awslabs.aws_support_mcp_server.server import mcp as support_server
        from awslabs.iam_mcp_server.server import mcp as iam_server
        from awslabs.well_architected_security_mcp_server.server import (
            mcp as well_architected_security_server,
        )

        logger.info('Enabling Security & Identity servers')
        imported_servers = await call_import_server(
            iam_server, 'iam', 'iam_server', imported_servers
        )
        imported_servers = await call_import_server(
            support_server, 'support', 'support_server', imported_servers
        )
        imported_servers = await call_import_server(
            well_architected_security_server,
            'well-architected-security',
            ' well_architected_security_server',
            imported_servers,
        )

    # SQL DB Specialist
    if sql_db_specialist:
        from awslabs.aurora_dsql_mcp_server.server import mcp as aurora_dsql_server
        from awslabs.mysql_mcp_server.server import mcp as mysql_server
        from awslabs.postgres_mcp_server.server import mcp as postgres_server
        from awslabs.redshift_mcp_server.server import mcp as redshift_server

        logger.info('Enabling SQL DB Specialist servers')
        imported_servers = await call_import_server(
            postgres_server, 'postgres', 'postgres_server', imported_servers
        )
        imported_servers = await call_import_server(
            mysql_server, 'mysql', 'mysql_server', imported_servers
        )
        imported_servers = await call_import_server(
            aurora_dsql_server, 'aurora_dsql', 'aurora_dsql_server', imported_servers
        )
        imported_servers = await call_import_server(
            redshift_server, 'redshift', 'redshift_server', imported_servers
        )

    # NoSQL DB Specialist
    if nosql_db_specialist:
        from awslabs.amazon_keyspaces_mcp_server.server import mcp as keyspaces_server
        from awslabs.amazon_neptune_mcp_server.server import mcp as neptune_server
        from awslabs.documentdb_mcp_server.server import mcp as documentdb_server
        from awslabs.dynamodb_mcp_server.server import app as dynamodb_server

        logger.info('Enabling NoSQL DB Specialist servers')
        imported_servers = await call_import_server(
            dynamodb_server, 'dynamodb', 'dynamodb_server', imported_servers
        )
        imported_servers = await call_import_server(
            documentdb_server, 'documentdb', 'documentdb_server', imported_servers
        )
        imported_servers = await call_import_server(
            keyspaces_server, 'keyspaces', 'keyspaces_server', imported_servers
        )
        imported_servers = await call_import_server(
            neptune_server, 'neptune', 'neptune_server', imported_servers
        )

    # Time Series DB Specialist
    if timeseries_db_specialist:
        from awslabs.cloudwatch_mcp_server.server import mcp as cloudwatch_server
        from awslabs.prometheus_mcp_server.server import mcp as prometheus_server
        from awslabs.timestream_for_influxdb_mcp_server.server import (
            mcp as timestream_for_influxdb_server,
        )

        logger.info('Enabling Time Series DB Specialist servers')
        imported_servers = await call_import_server(
            timestream_for_influxdb_server,
            'timestream_for_influxdb',
            'timestream_for_influxdb_server',
            imported_servers,
        )
        imported_servers = await call_import_server(
            prometheus_server, 'prometheus', 'prometheus_server', imported_servers
        )
        imported_servers = await call_import_server(
            cloudwatch_server, 'cloudwatch', 'cloudwatch_server', imported_servers
        )

    # Messaging & Events
    if messaging_events:
        from awslabs.amazon_mq_mcp_server.server import mcp as mq_server
        from awslabs.amazon_sns_sqs_mcp_server.server import mcp as sns_sqs_server

        logger.info('Enabling Messaging & Events servers')
        imported_servers = await call_import_server(
            sns_sqs_server, 'sns_sqs', 'sns_sqs_server', imported_servers
        )
        imported_servers = await call_import_server(mq_server, 'mq', 'mq_server', imported_servers)

    # Healthcare & Life Sciences
    if healthcare_lifesci:
        from awslabs.aws_healthomics_mcp_server.server import mcp as healthomics_server

        logger.info('Enabling Healthcare & Life Sciences servers')
        imported_servers = await call_import_server(
            healthomics_server, 'healthomics', 'healthomics_server', imported_servers
        )


def main() -> None:
    """Run the MCP server."""
    asyncio.run(setup())
    mcp.run()


if __name__ == '__main__':  # pragma: no cover
    main()
