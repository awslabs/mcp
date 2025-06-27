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

"""awslabs amazon-qindex MCP Server implementation."""

import boto3
import os
import sys
from awslabs.amazon_qindex_mcp_server.clients import QBusinessClient, QBusinessClientError
from loguru import logger
from mcp.server.fastmcp import FastMCP
from mypy_boto3_qbusiness.type_defs import SearchRelevantContentResponseTypeDef
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


# Configure logging
logger.remove(0)
logger.add(sys.stderr, level='INFO')


class DocumentAttributeValue(BaseModel):
    """Model for document attribute value types."""

    stringValue: Optional[str] = Field(default=None, description='String value')
    stringListValue: Optional[List[str]] = Field(default=None, description='List of string values')
    longValue: Optional[int] = Field(default=None, description='Long integer value')
    longListValue: Optional[List[int]] = Field(
        default=None, description='List of long integer values'
    )
    dateValue: Optional[str] = Field(default=None, description='Date value in ISO 8601 format')
    dateListValue: Optional[List[str]] = Field(default=None, description='List of date values')


class DocumentAttribute(BaseModel):
    """Model for document attribute with name and value."""

    name: str = Field(description='Name of the document attribute')
    value: DocumentAttributeValue = Field(description='Value of the document attribute')


class AttributeFilter(BaseModel):
    """Model for attribute filter conditions."""

    andAllFilters: Optional[List['AttributeFilter']] = Field(
        default=None, description='List of filters to AND together'
    )
    orAllFilters: Optional[List['AttributeFilter']] = Field(
        default=None, description='List of filters to OR together'
    )
    notFilter: Optional['AttributeFilter'] = Field(
        default=None, description='Negation of a filter'
    )
    equalsTo: Optional[DocumentAttribute] = Field(default=None, description='Exact match filter')
    containsAll: Optional[DocumentAttribute] = Field(
        default=None, description='Contains all values filter'
    )
    containsAny: Optional[DocumentAttribute] = Field(
        default=None, description='Contains any values filter'
    )
    greaterThan: Optional[DocumentAttribute] = Field(
        default=None, description='Greater than filter'
    )
    greaterThanOrEquals: Optional[DocumentAttribute] = Field(
        default=None, description='Greater than or equals filter'
    )
    lessThan: Optional[DocumentAttribute] = Field(default=None, description='Less than filter')
    lessThanOrEquals: Optional[DocumentAttribute] = Field(
        default=None, description='Less than or equals filter'
    )


class RetrieverContentSource(BaseModel):
    """Model for retriever content source."""

    retrieverId: str = Field(description='Identifier of the retriever')


class ContentSource(BaseModel):
    """Model for content source configuration.

    This is a union type, so only one field should be specified.
    """

    retriever: Optional[RetrieverContentSource] = Field(
        default=None, description='Retriever to use as content source'
    )


# # Update forward references for recursive AttributeFilter
AttributeFilter.model_rebuild()


# Initialize MCP server
mcp = FastMCP(
    'awslabs.amazon-qindex-mcp-server',
    instructions="Amazon Q index for ISVs MCP server provides access to your customers' enterprise data into your applications.",
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)


@mcp.tool(name='AuthorizeQIndex')
async def authorize_qindex(
    idc_region: str = Field(
        description='The AWS region for IAM Identity Center (e.g., us-west-2)'
    ),
    isv_redirect_url: str = Field(
        description='The redirect URL registered during ISV registration'
    ),
    oauth_state: str = Field(description='Random string to prevent CSRF attacks'),
    idc_application_arn: str = Field(
        description='The Amazon Q Business application ID provided by the customer'
    ),
) -> Dict:
    """Generate the OIDC authorization URL for Q index authentication.

    This tool generates the URL that users need to visit to authenticate with their
    Amazon Q Business application through their OIDC provider.

    Parameters:
        idc_region (str): The AWS region for IAM Identity Center (e.g., us-west-2)
        isv_redirect_url (str): The redirect URL registered during ISV registration
        oauth_state (str): Random string to prevent CSRF attacks
        idc_application_arn (str): The Amazon Q Business application ID provided by the customer

    Returns:
        Dict: Response containing the authorization URL
        {
            'authorization_url': 'string'
        }
    """
    auth_url = (
        f'https://oidc.{idc_region}.amazonaws.com/authorize'
        f'?response_type=code'
        f'&redirect_uri={isv_redirect_url}'
        f'&state={oauth_state}'
        f'&client_id={idc_application_arn}'
    )

    # Ask the user to visit the URL and provide the authorization code
    raise ValueError(
        f'Please visit this URL to sign in: {auth_url}\n'
        'After signing in, you will be redirected to your redirect URL.\n'
        'Please provide the authorization code from the redirect URL to continue.'
    )


@mcp.tool(name='CreateTokenWithIAM')
async def create_token_with_iam(
    idc_application_arn: str = Field(description='The Amazon Q Business application ID'),
    redirect_uri: str = Field(description='The redirect URL registered during ISV registration'),
    code: str = Field(description='The authorization code received from OIDC endpoint'),
    idc_region: str = Field(description='The AWS region for IAM Identity Center'),
    role_arn: str = Field(description='The ARN of the IAM role to assume'),
) -> Dict:
    """Get a token using the authorization code through IAM.

    This tool calls the CreateTokenWithIAM API to get a token using the authorization code
    received from the OIDC endpoint.

    Parameters:
        idc_application_arn (str): The Amazon Q Business application ID
        redirect_uri (str): The redirect URL registered during ISV registration
        code (str): The authorization code received from OIDC endpoint
        idc_region (str): The AWS region for IAM Identity Center
        role_arn (str): The ARN of the IAM role to assume

    Returns:
        Dict: Response containing the token information
        {
            'accessToken': 'string',
            'tokenType': 'string',
            'expiresIn': 123,
            'refreshToken': 'string',
            'idToken': 'string'
        }
    """
    try:
        # Create boto3 client for SSO OIDC
        aws_profile = os.environ.get('AWS_PROFILE', 'default')
        session = boto3.Session(region_name=idc_region, profile_name=aws_profile)

        sts_client = session.client('sts')

        assume_role_response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='automated-session',
            Tags=[
                {
                    'Key': 'qbusiness-dataaccessor:ExternalId',
                    'Value': 'Test-Tenant',  # Replace with your actual tenant ID variable
                }
            ],
        )

        # Get the temporary credentials from the assumed role
        temp_credentials = assume_role_response['Credentials']

        assumed_session = boto3.Session(
            aws_access_key_id=temp_credentials['AccessKeyId'],
            aws_secret_access_key=temp_credentials['SecretAccessKey'],
            aws_session_token=temp_credentials['SessionToken'],
            region_name=idc_region,
        )

        client = assumed_session.client('sso-oidc')

        response = client.create_token_with_iam(
            clientId=idc_application_arn,
            redirectUri=redirect_uri,
            grantType='authorization_code',
            code=code,
        )

        return response
    except Exception as e:
        logger.error(f'Error creating token with IAM: {str(e)}')
        raise ValueError(str(e))


@mcp.tool(name='AssumeRoleWithIdentityContext')
async def assume_role_with_identity_context(
    role_arn: str = Field(description='The ARN of the IAM role to assume'),
    identity_context: str = Field(
        description='The sts:identity_context value from the decoded token'
    ),
    idc_region: str = Field(description='The AWS region for IAM Identity Center'),
    role_session_name: str = Field(
        default='qbusiness-session', description='An identifier for the assumed role session'
    ),
) -> Dict:
    """Assume an IAM role using the identity context from the token.

    This tool calls the AssumeRole API with the identity context extracted from the token
    to get temporary credentials.

    Parameters:
        role_arn (str): The ARN of the IAM role to assume
        identity_context (str): The sts:identity_context value from the decoded token
        role_session_name (str): An identifier for the assumed role session

    Returns:
        Dict: Response containing the temporary credentials
        {
            'Credentials': {
                'AccessKeyId': 'string',
                'SecretAccessKey': 'string', # pragma: allowlist secret
                'SessionToken': 'string',
                'Expiration': datetime(2015, 1, 1)
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'string',
                'Arn': 'string'
            }
        }
    """
    try:
        # Create boto3 client for STS
        aws_profile = os.environ.get('AWS_PROFILE', 'default')
        session = boto3.Session(region_name=idc_region, profile_name=aws_profile)
        client = session.client('sts')

        response = client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=role_session_name,
            ProvidedContexts=[
                {
                    'ProviderArn': 'arn:aws:iam::aws:contextProvider/IdentityCenter',
                    'ContextAssertion': identity_context,
                }
            ],
            Tags=[
                {
                    'Key': 'qbusiness-dataaccessor:ExternalId',
                    'Value': 'Test-Tenant',  # Replace with your actual tenant ID variable
                }
            ],
        )

        return response
    except Exception as e:
        logger.error(f'Error assuming role with identity context: {str(e)}')
        raise ValueError(str(e))


@mcp.tool(name='SearchRelevantContent')
async def search_relevant_content(
    application_id: str = Field(
        description='The unique identifier of the application to search in'
    ),
    query_text: str = Field(description='The text to search for'),
    attribute_filter: Optional[AttributeFilter] = Field(
        default=None,
        description='Filter criteria to narrow down search results based on specific document attributes',
    ),
    content_source: Optional[ContentSource] = Field(
        default=None,
        description='Configuration specifying which content sources to include in the search',
    ),
    max_results: Optional[int] = Field(
        default=3, description='Maximum number of results to return (1-100)', ge=1, le=100
    ),
    next_token: Optional[str] = Field(
        default=None, description='Token for pagination to get the next set of results'
    ),
    qbuiness_region: str = Field(
        default='us-east-1', description='The AWS region in which Qbusiness application is present'
    ),
    aws_access_key_id: Optional[str] = Field(
        default=None, description='AWS access key ID from temporary credentials'
    ),
    aws_secret_access_key: Optional[str] = Field(
        default=None, description='AWS secret access key from temporary credentials'
    ),
    aws_session_token: Optional[str] = Field(
        default=None, description='AWS session token from temporary credentials'
    ),
) -> SearchRelevantContentResponseTypeDef:
    """Search for relevant content in an Amazon Q Business application.

    This operation searches for content within a Q Business application based on the provided
    query text and returns relevant matches.

    IMPORTANT: This tool requires valid AWS credentials. If credentials are not provided or are invalid,
    you must first:
    1. Call AuthorizeQBusiness to get an authorization URL
    2. Have the user authenticate at that URL to get an authorization code
    3. Call CreateTokenWithIAM with the code to get a token
    4. Call AssumeRoleWithIdentityContext with the token's identity context to get temporary credentials
    5. Finally, call this tool again with those temporary credentials

    See: https://docs.aws.amazon.com/amazonq/latest/api-reference/API_SearchRelevantContent.html

    Parameters:
        application_id (str): The unique identifier of the application to search in
        query_text (str): The text to search for
        attribute_filter (Optional[AttributeFilter]): Filter criteria to narrow down search results based on specific document attributes
        content_source (Optional[ContentSource]): Configuration specifying which content sources to include in the search
        max_results (Optional[int]): Maximum number of results to return (1-100)
        next_token (Optional[str]): Token for pagination to get the next set of results
        qbuiness_region (str): The AWS region in which Qbusiness application is present
        aws_access_key_id (Optional[str]): AWS access key ID from temporary credentials
        aws_secret_access_key (Optional[str]): AWS secret access key from temporary credentials
        aws_session_token (Optional[str]): AWS session token from temporary credentials


    Returns:
        Dict: Response syntax:
        {
            'nextToken': 'string',
            'relevantContent': [
                {
                    'content': 'string',
                    'documentAttributes': [
                        {
                            'name': 'string',
                            'value': {
                                # Various value types based on attribute
                            }
                        }
                    ],
                    'documentId': 'string',
                    'documentTitle': 'string',
                    'documentUri': 'string',
                    'scoreAttributes': {
                        'scoreConfidence': 'string'
                    }
                }
            ]
        }

    Raises:
        ValueError: If there's an error with the Q Business API call or if credentials are missing/invalid
    """
    try:
        # Check for credentials first
        if not aws_access_key_id or not aws_secret_access_key:
            raise QBusinessClientError('Missing AWS credentials')

        # Create QBusinessClient with provided credentials
        client = QBusinessClient(
            region_name=qbuiness_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )

        # Convert models to dictionaries
        content_source_dict = None
        if content_source:
            content_source_dict = content_source.model_dump(exclude_none=True)
            if 'retriever' in content_source_dict:
                content_source_dict = {'retriever': content_source_dict['retriever']}

        attribute_filter_dict = None
        if attribute_filter:
            attribute_filter_dict = attribute_filter.model_dump(exclude_none=True)

        # Ensure max_results is properly typed
        max_results_int = int(max_results) if max_results is not None else None

        # Perform the search
        return client.search_relevant_content(
            application_id=str(application_id),
            query_text=str(query_text),
            attribute_filter=attribute_filter_dict,
            content_source=content_source_dict,
            max_results=max_results_int,
            next_token=str(next_token) if next_token else None,
        )
    except Exception as e:
        logger.error(f'Error searching Q Business content: {str(e)}')
        if not aws_access_key_id or not aws_secret_access_key or not aws_session_token:
            raise ValueError(
                'Missing AWS credentials. Please follow the authentication flow described in the tool documentation.'
            )
        raise ValueError(str(e))


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
