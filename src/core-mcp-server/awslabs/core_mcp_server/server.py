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

# Import all servers
from awslabs.amazon_keyspaces_mcp_server.server import mcp as keyspaces_server
from awslabs.amazon_mq_mcp_server.server import mcp as mq_server
from awslabs.amazon_neptune_mcp_server.server import mcp as neptune_server
from awslabs.amazon_qbusiness_anonymous_mcp_server.server import mcp as qbusiness_anonymous_server
from awslabs.amazon_rekognition_mcp_server.server import mcp as rekognition_server
from awslabs.amazon_sns_sqs_mcp_server.server import mcp as sns_sqs_server
from awslabs.aurora_dsql_mcp_server.server import mcp as aurora_dsql_server
from awslabs.aws_api_mcp_server.server import server as aws_api_server
from awslabs.aws_bedrock_data_automation_mcp_server.server import (
    mcp as bedrock_data_automation_server,
)
from awslabs.aws_dataprocessing_mcp_server.server import mcp as dataprocessing_server
from awslabs.aws_diagram_mcp_server.server import mcp as diagram_server
from awslabs.aws_documentation_mcp_server.server_aws import mcp as aws_documentation_server
from awslabs.aws_healthomics_mcp_server.server import mcp as healthomics_server
from awslabs.aws_location_server.server import mcp as location_server
from awslabs.aws_pricing_mcp_server.server import mcp as pricing_server
from awslabs.aws_serverless_mcp_server.server import mcp as serverless_server
from awslabs.aws_support_mcp_server.server import mcp as support_server
from awslabs.bedrock_kb_retrieval_mcp_server.server import mcp as bedrock_kb_retrieval_server
from awslabs.cdk_mcp_server.core.server import mcp as cdk_server
from awslabs.cfn_mcp_server.server import mcp as cfn_server
from awslabs.cloudwatch_appsignals_mcp_server.server import mcp as cloudwatch_appsignals_server
from awslabs.cloudwatch_mcp_server.server import mcp as cloudwatch_server
from awslabs.code_doc_gen_mcp_server.server import mcp as code_doc_gen_server
from awslabs.cost_explorer_mcp_server.server import app as cost_explorer_server
from awslabs.documentdb_mcp_server.server import mcp as documentdb_server
from awslabs.dynamodb_mcp_server.server import app as dynamodb_server
from awslabs.ecs_mcp_server.main import mcp as ecs_server
from awslabs.eks_mcp_server.server import mcp as eks_server
from awslabs.elasticache_mcp_server.main import mcp as elasticache_server
from awslabs.finch_mcp_server.server import mcp as finch_server
from awslabs.frontend_mcp_server.server import mcp as frontend_server
from awslabs.git_repo_research_mcp_server.server import mcp as git_repo_research_server
from awslabs.iam_mcp_server.server import mcp as iam_server
from awslabs.lambda_tool_mcp_server.server import mcp as lambda_tool_server
from awslabs.memcached_mcp_server.main import mcp as memcached_server
from awslabs.mysql_mcp_server.server import mcp as mysql_server
from awslabs.nova_canvas_mcp_server.server import mcp as nova_canvas_server
from awslabs.postgres_mcp_server.server import mcp as postgres_server
from awslabs.prometheus_mcp_server.server import mcp as prometheus_server
from awslabs.redshift_mcp_server.server import mcp as redshift_server
from awslabs.s3_tables_mcp_server.server import app as s3_tables_server
from awslabs.stepfunctions_tool_mcp_server.server import mcp as stepfunctions_tool_server
from awslabs.syntheticdata_mcp_server.server import mcp as syntheticdata_server
from awslabs.timestream_for_influxdb_mcp_server.server import mcp as timestream_for_influxdb_server
from fastmcp import FastMCP

# from awslabs.amazon_qindex_mcp_server.server import mcp as qindex_server --> need to modify server to fix logger.remove(0)
# from awslabs.aws_msk_mcp_server.server import mcp as msk_server --> does not expose mcp server
# from awslabs.openapi_mcp_server.server import mcp_server as openapi_server --> does not expose mcp server
# from awslabs.terraform_mcp_server.server import mcp as terraform_server --> has dependency conflicts
# from awslabs.valkey_mcp_server.server import mcp as valkey_server --> has dependency conflicts
from fastmcp.server.proxy import ProxyClient
from typing import List, TypedDict


current_dir = pathlib.Path(__file__).parent
prompt_understanding_path = current_dir / 'static' / 'PROMPT_UNDERSTANDING.md'
with open(prompt_understanding_path, 'r', encoding='utf-8') as f:
    PROMPT_UNDERSTANDING = f.read()

# roles - environment variables for role-based server configuration
aws_knowledge_foundation = os.environ.get('aws-knowledge-foundation')
dev_tools = os.environ.get('dev-tools')
ci_cd_devops = os.environ.get('ci-cd-devops')
container_orchestration = os.environ.get('container-orchestration')
serverless_architecture = os.environ.get('serverless-architecture')
analytics_warehouse = os.environ.get('analytics-warehouse')
data_platform_eng = os.environ.get('data-platform-eng')
data_ingestion = os.environ.get('data-ingestion')
ai_dev = os.environ.get('ai-dev')
frontend_dev = os.environ.get('frontend-dev')
api_management = os.environ.get('api-management')
solutions_architect = os.environ.get('solutions-architect')
finops = os.environ.get('finops')
monitoring_observability = os.environ.get('monitoring-observability')
caching_performance = os.environ.get('caching-performance')
security_identity = os.environ.get('security-identity')
sql_db_specialist = os.environ.get('sql-db-specialist')
nosql_db_specialist = os.environ.get('nosql-db-specialist')
timeseries_db_specialist = os.environ.get('timeseries-db-specialist')
messaging_events = os.environ.get('messaging-events')
geospatial_services = os.environ.get('geospatial-services')
healthcare_lifesci = os.environ.get('healthcare-lifesci')


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
async def get_prompt_understanding() -> str:
    """MCP-CORE Prompt Understanding.

    ALWAYS Use this tool first to understand the user's query and translate it into AWS expert advice.
    """
    return PROMPT_UNDERSTANDING


# Import subservers based on role configuration
async def setup():
    """Set up and import MCP servers based on role-based environment variables.

    This function dynamically imports MCP servers based on the role environment variables
    that are set. It uses a helper function to import each server only once, avoiding
    duplicates when a server is needed by multiple roles. If no roles are enabled,
    it will not import any servers.

    The function handles the following roles:
    - AWS Knowledge Foundation
    - Dev Tools
    - CI/CD DevOps
    - Container Orchestration
    - Serverless Architecture
    - Analytics Warehouse
    - Data Platform Engineering
    - Data Ingestion
    - AI Development
    - Frontend Development
    - API Management
    - Solutions Architect
    - FinOps
    - Monitoring & Observability
    - Caching & Performance
    - Security & Identity
    - SQL DB Specialist
    - NoSQL DB Specialist
    - Time Series DB Specialist
    - Messaging & Events
    - Geospatial Services
    - Healthcare & Life Sciences
    """
    # Track which servers have been imported to avoid duplicates
    imported_servers = set()

    # Helper function to import a server if not already imported
    async def call_import_server(server, prefix, server_name):
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

    # AWS Knowledge Foundation
    if aws_knowledge_foundation:
        logger.info('Enabling AWS Knowledge Foundation servers')
        await call_import_server(aws_documentation_server, 'aws_docs', 'aws_documentation_server')
        await call_import_server(aws_api_server, 'aws_api', 'aws_api_server')

    # Dev Tools
    if dev_tools:
        logger.info('Enabling Dev Tools servers')
        await call_import_server(
            git_repo_research_server, 'git_repo_research', 'git_repo_research_server'
        )
        await call_import_server(code_doc_gen_server, 'code_doc_gen', 'code_doc_gen_server')
        await call_import_server(aws_documentation_server, 'aws_docs', 'aws_documentation_server')

    # CI/CD DevOps
    if ci_cd_devops:
        logger.info('Enabling CI/CD DevOps servers')
        await call_import_server(cdk_server, 'cdk', 'cdk_server')
        await call_import_server(cfn_server, 'cfn', 'cfn_server')
        # terraform_server is commented out in imports

    # Container Orchestration
    if container_orchestration:
        logger.info('Enabling Container Orchestration servers')
        await call_import_server(eks_server, 'eks', 'eks_server')
        await call_import_server(ecs_server, 'ecs', 'ecs_server')
        await call_import_server(finch_server, 'finch', 'finch_server')

    # Serverless Architecture
    if serverless_architecture:
        logger.info('Enabling Serverless Architecture servers')
        await call_import_server(serverless_server, 'serverless', 'serverless_server')
        await call_import_server(lambda_tool_server, 'lambda_tool', 'lambda_tool_server')
        await call_import_server(
            stepfunctions_tool_server, 'stepfunctions_tool', 'stepfunctions_tool_server'
        )
        await call_import_server(sns_sqs_server, 'sns_sqs', 'sns_sqs_server')

    # Analytics Warehouse
    if analytics_warehouse:
        logger.info('Enabling Analytics Warehouse servers')
        await call_import_server(redshift_server, 'redshift', 'redshift_server')
        await call_import_server(
            timestream_for_influxdb_server,
            'timestream_for_influxdb',
            'timestream_for_influxdb_server',
        )
        await call_import_server(dataprocessing_server, 'dataprocessing', 'dataprocessing_server')
        # msk_server is commented out in imports
        await call_import_server(syntheticdata_server, 'syntheticdata', 'syntheticdata_server')

    # Data Platform Engineering
    if data_platform_eng:
        logger.info('Enabling Data Platform Engineering servers')
        await call_import_server(dynamodb_server, 'dynamodb', 'dynamodb_server')
        await call_import_server(s3_tables_server, 's3_tables', 's3_tables_server')
        await call_import_server(dataprocessing_server, 'dataprocessing', 'dataprocessing_server')
        # msk_server is commented out in imports

    # Data Ingestion
    if data_ingestion:
        logger.info('Enabling Data Ingestion servers')
        await call_import_server(sns_sqs_server, 'sns_sqs', 'sns_sqs_server')
        await call_import_server(mq_server, 'mq', 'mq_server')
        # msk_server is commented out in imports
        await call_import_server(cloudwatch_server, 'cloudwatch', 'cloudwatch_server')

    # AI Development
    if ai_dev:
        logger.info('Enabling AI Development servers')
        await call_import_server(
            bedrock_kb_retrieval_server, 'bedrock_kb_retrieval', 'bedrock_kb_retrieval_server'
        )
        await call_import_server(nova_canvas_server, 'nova_canvas', 'nova_canvas_server')
        await call_import_server(rekognition_server, 'rekognition', 'rekognition_server')
        # qindex_server is commented out in imports
        await call_import_server(
            qbusiness_anonymous_server, 'qbusiness_anonymous', 'qbusiness_anonymous_server'
        )
        await call_import_server(
            bedrock_data_automation_server,
            'bedrock_data_automation',
            'bedrock_data_automation_server',
        )

    # Frontend Development
    if frontend_dev:
        logger.info('Enabling Frontend Development servers')
        await call_import_server(frontend_server, 'frontend', 'frontend_server')
        await call_import_server(nova_canvas_server, 'nova_canvas', 'nova_canvas_server')

    # API Management
    if api_management:
        logger.info('Enabling API Management servers')
        # openapi_server is commented out in imports
        await call_import_server(aws_api_server, 'aws_api', 'aws_api_server')

    # Solutions Architect
    if solutions_architect:
        logger.info('Enabling Solutions Architect servers')
        await call_import_server(diagram_server, 'diagram', 'diagram_server')
        await call_import_server(pricing_server, 'pricing', 'pricing_server')
        await call_import_server(cost_explorer_server, 'cost_explorer', 'cost_explorer_server')
        await call_import_server(syntheticdata_server, 'syntheticdata', 'syntheticdata_server')
        await call_import_server(aws_documentation_server, 'aws_docs', 'aws_documentation_server')

    # FinOps
    if finops:
        logger.info('Enabling FinOps servers')
        await call_import_server(cost_explorer_server, 'cost_explorer', 'cost_explorer_server')
        await call_import_server(pricing_server, 'pricing', 'pricing_server')
        await call_import_server(cloudwatch_server, 'cloudwatch', 'cloudwatch_server')

    # Monitoring & Observability
    if monitoring_observability:
        logger.info('Enabling Monitoring & Observability servers')
        await call_import_server(cloudwatch_server, 'cloudwatch', 'cloudwatch_server')
        await call_import_server(
            cloudwatch_appsignals_server, 'cloudwatch_appsignals', 'cloudwatch_appsignals_server'
        )
        await call_import_server(prometheus_server, 'prometheus', 'prometheus_server')

    # Caching & Performance
    if caching_performance:
        logger.info('Enabling Caching & Performance servers')
        await call_import_server(elasticache_server, 'elasticache', 'elasticache_server')
        # valkey_server is commented out in imports
        await call_import_server(memcached_server, 'memcached', 'memcached_server')

    # Security & Identity
    if security_identity:
        logger.info('Enabling Security & Identity servers')
        await call_import_server(iam_server, 'iam', 'iam_server')
        await call_import_server(support_server, 'support', 'support_server')

    # SQL DB Specialist
    if sql_db_specialist:
        logger.info('Enabling SQL DB Specialist servers')
        await call_import_server(postgres_server, 'postgres', 'postgres_server')
        await call_import_server(mysql_server, 'mysql', 'mysql_server')
        await call_import_server(aurora_dsql_server, 'aurora_dsql', 'aurora_dsql_server')
        await call_import_server(redshift_server, 'redshift', 'redshift_server')

    # NoSQL DB Specialist
    if nosql_db_specialist:
        logger.info('Enabling NoSQL DB Specialist servers')
        await call_import_server(dynamodb_server, 'dynamodb', 'dynamodb_server')
        await call_import_server(documentdb_server, 'documentdb', 'documentdb_server')
        await call_import_server(keyspaces_server, 'keyspaces', 'keyspaces_server')
        await call_import_server(neptune_server, 'neptune', 'neptune_server')

    # Time Series DB Specialist
    if timeseries_db_specialist:
        logger.info('Enabling Time Series DB Specialist servers')
        await call_import_server(
            timestream_for_influxdb_server,
            'timestream_for_influxdb',
            'timestream_for_influxdb_server',
        )
        await call_import_server(prometheus_server, 'prometheus', 'prometheus_server')
        await call_import_server(cloudwatch_server, 'cloudwatch', 'cloudwatch_server')
        # msk_server is commented out in imports

    # Messaging & Events
    if messaging_events:
        logger.info('Enabling Messaging & Events servers')
        await call_import_server(sns_sqs_server, 'sns_sqs', 'sns_sqs_server')
        await call_import_server(mq_server, 'mq', 'mq_server')
        # msk_server is commented out in imports

    # Geospatial Services
    if geospatial_services:
        logger.info('Enabling Geospatial Services servers')
        await call_import_server(location_server, 'location', 'location_server')
        await call_import_server(neptune_server, 'neptune', 'neptune_server')

    # Healthcare & Life Sciences
    if healthcare_lifesci:
        logger.info('Enabling Healthcare & Life Sciences servers')
        await call_import_server(healthomics_server, 'healthomics', 'healthomics_server')


def main() -> None:
    """Run the MCP server."""
    asyncio.run(setup())
    mcp.run()


if __name__ == '__main__':  # pragma: no cover
    main()
