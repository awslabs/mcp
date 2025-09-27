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

"""AWS Systems Manager Documents MCP tools."""

import boto3
import json
from awslabs.systems_manager_mcp_server.context import Context
from awslabs.systems_manager_mcp_server.errors import log_error
from botocore.exceptions import ClientError
from mcp.types import CallToolResult
from pydantic import Field
from typing import Optional


def register_tools(mcp):
    """Register all document tools with the provided MCP instance."""

    def _get_ssm_client(region=None, profile=None):
        """Get SSM client with optional region and profile."""
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        return session.client('ssm', region_name=region)

    @mcp.tool()
    def create_document(
        content: str = Field(description='Document content (JSON or YAML)'),
        name: str = Field(description='Document name'),
        document_type: str = Field(
            description='Document type (Command, Automation, Policy, etc.)'
        ),
        document_format: Optional[str] = Field('JSON', description='Document format (YAML, JSON)'),
        target_type: Optional[str] = Field(None, description='Target type for the document'),
        version_name: Optional[str] = Field(None, description='Version name for the document'),
        display_name: Optional[str] = Field(None, description='Display name for the document'),
        requires: Optional[str] = Field(None, description='JSON string of required documents'),
        attachments: Optional[str] = Field(None, description='JSON string of attachments'),
        tags: Optional[str] = Field(None, description='JSON string of tags'),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Create a new AWS Systems Manager document."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {'type': 'text', 'text': 'Cannot create document: Server is in read-only mode'}
                ],
                isError=True,
            )

        try:
            request_params = {
                'Content': content,
                'Name': name,
                'DocumentType': document_type,
                'DocumentFormat': document_format,
            }

            if target_type:
                request_params['TargetType'] = target_type
            if version_name:
                request_params['VersionName'] = version_name
            if display_name:
                request_params['DisplayName'] = display_name

            # Handle JSON parameters
            if requires:
                try:
                    parsed_requires = json.loads(requires)
                    request_params['Requires'] = parsed_requires
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[{'type': 'text', 'text': f'Invalid JSON in requires: {str(e)}'}],
                        isError=True,
                    )

            if attachments:
                try:
                    parsed_attachments = json.loads(attachments)
                    request_params['Attachments'] = parsed_attachments
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {'type': 'text', 'text': f'Invalid JSON in attachments: {str(e)}'}
                        ],
                        isError=True,
                    )

            if tags:
                try:
                    parsed_tags = json.loads(tags)
                    request_params['Tags'] = parsed_tags
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[{'type': 'text', 'text': f'Invalid JSON in tags: {str(e)}'}],
                        isError=True,
                    )

            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.create_document(**request_params)

            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': f'✅ Document created successfully: {response["DocumentDescription"]["Name"]}',
                    }
                ]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'create document')

    @mcp.tool()
    def delete_document(
        name: str = Field(description='Document name'),
        document_version: Optional[str] = Field(None, description='Specific version to delete'),
        version_name: Optional[str] = Field(None, description='Specific version name to delete'),
        force: Optional[bool] = Field(
            None, description='Force deletion even if document is in use'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Delete an AWS Systems Manager document."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {'type': 'text', 'text': 'Cannot delete document: Server is in read-only mode'}
                ],
                isError=True,
            )

        try:
            request_params = {'Name': name}

            if document_version:
                request_params['DocumentVersion'] = document_version
            if version_name:
                request_params['VersionName'] = version_name
            if force:
                request_params['Force'] = force

            ssm_client = _get_ssm_client(region, profile)
            ssm_client.delete_document(**request_params)

            return CallToolResult(
                content=[{'type': 'text', 'text': f'✅ Document deleted successfully: {name}'}]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'delete document')

    @mcp.tool()
    def describe_document(
        name: str = Field(description='Document name'),
        document_version: Optional[str] = Field(None, description='Document version'),
        version_name: Optional[str] = Field(None, description='Document version name'),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Describe an AWS Systems Manager document."""
        try:
            request_params = {'Name': name}

            if document_version:
                request_params['DocumentVersion'] = document_version
            if version_name:
                request_params['VersionName'] = version_name

            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.describe_document(**request_params)

            doc = response['Document']
            output = f'✅ Document description for: {doc["Name"]}\n\n'
            output += f'- Type: {doc.get("DocumentType", "N/A")}\n'
            output += f'- Format: {doc.get("DocumentFormat", "N/A")}\n'
            output += f'- Status: {doc.get("Status", "N/A")}\n'
            output += f'- Owner: {doc.get("Owner", "N/A")}\n'
            output += f'- Version: {doc.get("DocumentVersion", "N/A")}\n'
            output += f'- Schema Version: {doc.get("SchemaVersion", "N/A")}\n'
            output += f'- Created Date: {doc.get("CreatedDate", "N/A")}\n'
            output += f'- Default Version: {doc.get("DefaultVersion", "N/A")}\n'
            output += f'- Latest Version: {doc.get("LatestVersion", "N/A")}\n'

            if doc.get('Description'):
                output += f'- Description: {doc["Description"]}\n'

            if doc.get('PlatformTypes'):
                output += f'- Platform Types: {", ".join(doc["PlatformTypes"])}\n'

            if doc.get('Requires'):
                output += f'- Requires: {len(doc["Requires"])} requirement(s)\n'
                for req in doc['Requires']:
                    output += f'  - Name: {req.get("Name", "N/A")}\n'
                    if req.get('Version'):
                        output += f'    Version: {req["Version"]}\n'
                    if req.get('RequireType'):
                        output += f'    Type: {req["RequireType"]}\n'
                    if req.get('VersionName'):
                        output += f'    Version Name: {req["VersionName"]}\n'

            if doc.get('Parameters'):
                output += f'- Parameters: {len(doc["Parameters"])} parameter(s)\n'
                for param in doc['Parameters']:
                    output += f'  - Name: {param.get("Name", "N/A")}\n'
                    output += f'    Type: {param.get("Type", "N/A")}\n'
                    if param.get('Description'):
                        output += f'    Description: {param["Description"]}\n'
                    if param.get('DefaultValue'):
                        output += f'    Default: {param["DefaultValue"]}\n'
                    if param.get('AllowedValues'):
                        output += f'    Allowed Values: {", ".join(param["AllowedValues"])}\n'
                    if param.get('AllowedPattern'):
                        output += f'    Pattern: {param["AllowedPattern"]}\n'

            if doc.get('Tags'):
                output += f'- Tags: {len(doc["Tags"])} tag(s)\n'
                for tag in doc['Tags']:
                    output += f'  - {tag.get("Key", "N/A")}: {tag.get("Value", "N/A")}\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'describe document')

    @mcp.tool()
    def describe_document_permission(
        name: str = Field(description='Document name'),
        permission_type: str = Field('Share', description='Permission type (Share)'),
        max_results: Optional[int] = Field(None, description='Maximum number of results'),
        next_token: Optional[str] = Field(None, description='Token for pagination'),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Describe permissions for an AWS Systems Manager document."""
        try:
            request_params = {'Name': name, 'PermissionType': permission_type}

            if max_results:
                request_params['MaxResults'] = max_results
            if next_token:
                request_params['NextToken'] = next_token

            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.describe_document_permission(**request_params)

            output = f'✅ Document permissions for: {name}\n\n'
            if response.get('AccountIds'):
                output += f'- Shared with accounts: {", ".join(response["AccountIds"])}\n'
            if response.get('AccountSharingInfoList'):
                output += '- Account sharing details:\n'
                for info in response['AccountSharingInfoList']:
                    output += f'  - Account: {info.get("AccountId", "N/A")}\n'
            if response.get('NextToken'):
                output += f'- Next Token: {response["NextToken"]}\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'describe document permission')

    @mcp.tool()
    def get_document(
        name: str = Field(description='Document name'),
        version_name: Optional[str] = Field(
            None, description='Document version (default: $LATEST)'
        ),
        document_version: Optional[str] = Field(None, description='Document version number'),
        document_format: Optional[str] = Field(
            None, description='Document format (YAML, JSON, TEXT)'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Retrieve an AWS Systems Manager document."""
        try:
            request_params = {'Name': name}

            if version_name:
                request_params['VersionName'] = version_name
            if document_version:
                request_params['DocumentVersion'] = document_version
            if document_format:
                request_params['DocumentFormat'] = document_format

            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.get_document(**request_params)

            document = response['Document']
            output = f'✅ Document retrieved: {document["Name"]}\n\n'
            output += f'- DisplayName: {document.get("DisplayName", "N/A")}\n'
            output += f'- Version: {document.get("VersionName", "$LATEST")}\n'
            output += f'- Type: {document.get("DocumentType", "N/A")}\n'
            output += f'- Format: {document.get("DocumentFormat", "N/A")}\n'
            output += f'- Status: {document.get("Status", "N/A")}\n'

            if document.get('Requires'):
                output += f'- Requires: {len(document["Requires"])} requirement(s)\n'
                for req in document['Requires']:
                    output += f'  - Name: {req.get("Name", "N/A")}\n'
                    if req.get('Version'):
                        output += f'    Version: {req["Version"]}\n'
                    if req.get('RequireType'):
                        output += f'    Type: {req["RequireType"]}\n'
                    if req.get('VersionName'):
                        output += f'    Version Name: {req["VersionName"]}\n'

            if document.get('Content'):
                output += f'\n**Content:**\n```\n{document["Content"]}\n```\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'get document')

    @mcp.tool()
    def list_documents(
        document_filter_list: Optional[str] = Field(
            None, description='JSON string of document filters (legacy)'
        ),
        filters: Optional[str] = Field(None, description='JSON string of filters'),
        max_results: Optional[int] = Field(50, description='Maximum number of results to return'),
        next_token: Optional[str] = Field(None, description='Token for pagination'),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """List AWS Systems Manager documents."""
        try:
            request_params = {}

            if document_filter_list:
                try:
                    doc_filters = json.loads(document_filter_list)
                    request_params['DocumentFilterList'] = doc_filters
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[
                            {
                                'type': 'text',
                                'text': f'Invalid JSON in document_filter_list: {str(e)}',
                            }
                        ],
                        isError=True,
                    )

            if filters:
                try:
                    filter_list = json.loads(filters)
                    request_params['Filters'] = filter_list
                except json.JSONDecodeError as e:
                    return CallToolResult(
                        content=[{'type': 'text', 'text': f'Invalid JSON in filters: {str(e)}'}],
                        isError=True,
                    )

            if max_results:
                request_params['MaxResults'] = max_results
            if next_token:
                request_params['NextToken'] = next_token

            ssm_client = _get_ssm_client(region, profile)
            response = ssm_client.list_documents(**request_params)

            documents = response.get('DocumentIdentifiers', [])

            if not documents:
                return CallToolResult(
                    content=[{'type': 'text', 'text': 'No documents found matching the criteria.'}]
                )

            output = f'✅ Found {len(documents)} documents:\n\n'
            for doc in documents:
                output += f'- **{doc["Name"]}**\n'
                output += f'  - Type: {doc.get("DocumentType", "N/A")}\n'
                output += f'  - Owner: {doc.get("Owner", "N/A")}\n'
                output += f'  - Format: {doc.get("DocumentFormat", "N/A")}\n'
                output += f'  - Version: {doc.get("DocumentVersion", "N/A")}\n'
                if doc.get('CreatedDate'):
                    output += f'  - Created: {doc["CreatedDate"]}\n'
                if doc.get('DisplayName'):
                    output += f'  - Display Name: {doc["DisplayName"]}\n'
                if doc.get('SchemaVersion'):
                    output += f'  - Schema Version: {doc["SchemaVersion"]}\n'
                if doc.get('PlatformTypes'):
                    output += f'  - Platforms: {", ".join(doc["PlatformTypes"])}\n'
                if doc.get('TargetType'):
                    output += f'  - Target Type: {doc["TargetType"]}\n'

                output += '\n'

            if response.get('NextToken'):
                output += f'Next Token: {response["NextToken"]}\n'

            return CallToolResult(content=[{'type': 'text', 'text': output}])

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'list documents')

    @mcp.tool()
    def modify_document_permission(
        name: str = Field(description='Document name'),
        permission_type: str = Field('Share', description='Permission type (Share)'),
        account_ids_to_add: Optional[str] = Field(
            None, description='Comma-separated account IDs to add'
        ),
        account_ids_to_remove: Optional[str] = Field(
            None, description='Comma-separated account IDs to remove'
        ),
        shared_document_version: Optional[str] = Field(
            None, description='Document version to share'
        ),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Modify permissions for an AWS Systems Manager document."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': 'Cannot modify document permission: Server is in read-only mode',
                    }
                ],
                isError=True,
            )

        try:
            request_params = {'Name': name, 'PermissionType': permission_type}

            if account_ids_to_add:
                request_params['AccountIdsToAdd'] = [
                    id.strip() for id in account_ids_to_add.split(',')
                ]
            if account_ids_to_remove:
                request_params['AccountIdsToRemove'] = [
                    id.strip() for id in account_ids_to_remove.split(',')
                ]
            if shared_document_version:
                request_params['SharedDocumentVersion'] = shared_document_version

            ssm_client = _get_ssm_client(region, profile)
            ssm_client.modify_document_permission(**request_params)

            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': f'✅ Document permissions modified successfully: {name}',
                    }
                ]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'modify document permission')

    @mcp.tool()
    def update_document(
        content: str = Field(description='Updated document content'),
        name: str = Field(description='Document name'),
        document_version: Optional[str] = Field(None, description='Document version to update'),
        document_format: Optional[str] = Field('JSON', description='Document format'),
        target_type: Optional[str] = Field(None, description='Target type for the document'),
        version_name: Optional[str] = Field(None, description='Version name for the update'),
        display_name: Optional[str] = Field(None, description='Display name for the document'),
        attachments: Optional[str] = Field(None, description='JSON array of document attachments'),
        requires: Optional[str] = Field(None, description='JSON array of document requirements'),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Update an existing AWS Systems Manager document."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {'type': 'text', 'text': 'Cannot update document: Server is in read-only mode'}
                ],
                isError=True,
            )

        try:
            # Parse JSON parameters
            if attachments:
                try:
                    attachments_list = json.loads(attachments)
                except json.JSONDecodeError:
                    return CallToolResult(
                        content=[
                            {'type': 'text', 'text': 'Invalid JSON in attachments parameter'}
                        ],
                        isError=True,
                    )

            if requires:
                try:
                    requires_list = json.loads(requires)
                except json.JSONDecodeError:
                    return CallToolResult(
                        content=[{'type': 'text', 'text': 'Invalid JSON in requires parameter'}],
                        isError=True,
                    )

            request_params = {'Content': content, 'Name': name, 'DocumentFormat': document_format}

            if document_version:
                request_params['DocumentVersion'] = document_version
            if target_type:
                request_params['TargetType'] = target_type
            if version_name:
                request_params['VersionName'] = version_name
            if display_name:
                request_params['DisplayName'] = display_name
            if attachments:
                request_params['Attachments'] = attachments_list
            if requires:
                request_params['Requires'] = requires_list

            ssm_client = _get_ssm_client(region, profile)
            ssm_client.update_document(**request_params)

            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': f'✅ Document updated successfully: {name}',
                    }
                ]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'update document')

    @mcp.tool()
    def update_document_default_version(
        name: str = Field(description='Document name'),
        document_version: str = Field(description='Document version to set as default'),
        region: Optional[str] = Field(None, description='AWS region'),
        profile: Optional[str] = Field(None, description='AWS profile'),
    ) -> CallToolResult:
        """Update the default version of an AWS Systems Manager document."""
        if Context.is_readonly():
            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': 'Cannot update document default version: Server is in read-only mode',
                    }
                ],
                isError=True,
            )

        try:
            request_params = {'Name': name, 'DocumentVersion': document_version}

            ssm_client = _get_ssm_client(region, profile)
            ssm_client.update_document_default_version(**request_params)

            return CallToolResult(
                content=[
                    {
                        'type': 'text',
                        'text': f'✅ Document default version updated successfully: {name} (version {document_version})',
                    }
                ]
            )

        except ClientError as e:
            return CallToolResult(
                content=[{'type': 'text', 'text': f'AWS Error: {e.response["Error"]["Message"]}'}],
                isError=True,
            )
        except Exception as e:
            return log_error(e, 'update document default version')
