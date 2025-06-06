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

import boto3
from botocore.exceptions import ClientError
from loguru import logger
from mypy_boto3_qbusiness.type_defs import SearchRelevantContentResponseTypeDef
from typing import TYPE_CHECKING, Any, Dict, Optional


if TYPE_CHECKING:
    from mypy_boto3_qbusiness.client import QBusinessClient as Boto3QBusinessClient
else:
    Boto3QBusinessClient = object


class QBusinessClientError(Exception):
    """Custom exception for Q Business client errors."""

    pass


class QBusinessClient:
    """Client for interacting with Amazon Q Business API."""

    def __init__(
        self,
        region_name: str = 'us-east-1',
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
    ):
        """Initialize Q Business client.

        Args:
            region_name (str): AWS region name
            aws_access_key_id (Optional[str]): AWS access key ID
            aws_secret_access_key (Optional[str]): AWS secret access key
            aws_session_token (Optional[str]): AWS session token
        """
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = self._get_client()

    def _get_client(self) -> Boto3QBusinessClient:
        """Get boto3 Q Business client.

        Returns:
            Boto3QBusinessClient: Boto3 Q Business client
        """
        session = boto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            region_name=self.region_name,
        )
        return session.client('qbusiness')

    def _handle_client_error(self, error: ClientError, operation: str) -> None:
        """Handle boto3 client errors.

        Args:
            error: The ClientError exception
            operation: The operation being performed

        Raises:
            QBusinessClientError: Wrapped client error with context
        """
        error_details = error.response.get('Error', {})
        error_code = error_details.get('Code', 'Unknown')
        error_message = error_details.get('Message', 'No message provided')

        logger.error(f'AWS Q Business {operation} error: {error_code} - {error_message}')

        error_mapping = {
            'AccessDeniedException': 'Access denied',
            'ValidationException': 'Validation error',
            'ThrottlingException': 'Request throttled',
            'InternalServerException': 'Internal server error',
            'ResourceNotFoundException': 'Resource not found',
        }

        message = f'{error_mapping.get(error_code, "AWS Q Business error")}: {error_message}'
        raise QBusinessClientError(message)

    def search_relevant_content(
        self,
        application_id: str,
        query_text: str,
        attribute_filter: Optional[Dict] = None,
        content_source: Optional[Dict] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> SearchRelevantContentResponseTypeDef:
        """Search for relevant content in a Q Business application.

        Args:
            application_id (str): The unique identifier of the application
            query_text (str): The text to search for
            attribute_filter (Optional[AttributeFilter]): Filter criteria to narrow down search results based on specific document attributes
            content_source (Optional[ContentSource]): Configuration specifying which content sources to include in the search
            max_results (Optional[int]): Maximum number of results to return (1-100)
            next_token (Optional[str]): Token for pagination
            filters (Optional[Dict]): Filters to apply to the search

        Returns:
            Dict: Search results and pagination token. Response syntax:
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
            QBusinessClientError: If the API call fails
        """
        try:
            # Build request parameters
            params: Dict[str, Any] = {
                'applicationId': str(application_id),
                'queryText': str(query_text),
            }

            if attribute_filter is not None:
                params['attributeFilter'] = attribute_filter
            if content_source is not None:
                params['contentSource'] = content_source
            if max_results is not None:
                params['maxResults'] = int(max_results)
            if next_token is not None:
                params['nextToken'] = str(next_token)

            response = self.client.search_relevant_content(**params)

            if not response or 'relevantContent' not in response:
                raise QBusinessClientError('Invalid response received from AWS Q Business')

            logger.info(
                f'Successfully retrieved {len(response.get("relevantContent", []))} search results'
            )
            return response

        except ClientError as e:
            self._handle_client_error(e, 'SearchRelevantContent')
            raise
        except Exception as e:
            logger.error(f'Unexpected error searching content: {str(e)}')
            raise QBusinessClientError(f'Unexpected error: {str(e)}')