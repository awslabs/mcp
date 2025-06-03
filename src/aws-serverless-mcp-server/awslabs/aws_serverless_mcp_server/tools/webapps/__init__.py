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
"""Web application deployment tools for AWS Serverless MCP Server."""

from awslabs.aws_serverless_mcp_server.tools.webapps.configure_domain import ConfigureDomainTool
from awslabs.aws_serverless_mcp_server.tools.webapps.get_metrics import GetMetricsTool
from awslabs.aws_serverless_mcp_server.tools.webapps.update_webapp_frontend import (
    UpdateFrontendTool,
)
from awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp import DeployWebAppTool
from awslabs.aws_serverless_mcp_server.tools.webapps.webapp_deployment_help import (
    WebappDeploymentHelpTool,
)

__all__ = [
    ConfigureDomainTool,
    GetMetricsTool,
    UpdateFrontendTool,
    DeployWebAppTool,
    WebappDeploymentHelpTool,
]
