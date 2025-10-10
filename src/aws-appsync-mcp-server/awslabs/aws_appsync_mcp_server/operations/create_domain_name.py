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

"""Create Domain Name operation for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def create_domain_name_operation(
    domain_name: str,
    certificate_arn: str,
    description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict:
    """Execute create_domain_name operation."""
    client = get_appsync_client()

    params: Dict[str, Any] = {'domainName': domain_name, 'certificateArn': certificate_arn}

    if description is not None:
        params['description'] = description
    if tags is not None:
        params['tags'] = tags

    response = client.create_domain_name(**params)
    return {'domainNameConfig': response.get('domainNameConfig', {})}
