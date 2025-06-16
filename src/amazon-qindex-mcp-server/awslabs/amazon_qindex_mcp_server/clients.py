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
from botocore.config import Config
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
        return session.client('qbusiness', config=Config(user_agent_extra='QIndex-MCP-Server/1.0'))

    def _validate_attribute_filter(self, attribute_filter: Dict) -> None:
        """Validate the attribute filter parameter.

        Args:
            attribute_filter (Dict): The attribute filter to validate

        Raises:
            ValueError: If the attribute filter is invalid
        """
        if not isinstance(attribute_filter, dict):
            raise ValueError('attribute_filter must be a dictionary')

        # Check for direct attribute name/value structure
        if 'attributeName' in attribute_filter and 'attributeValue' in attribute_filter:
            # Add security validation for attributeName
            self._validate_string_safety(str(attribute_filter['attributeName']), 'attributeName')

            value = attribute_filter['attributeValue']
            if not isinstance(value, dict):
                raise ValueError('attributeValue must be a dictionary')
            valid_value_types = ['StringValue', 'StringListValue', 'LongValue', 'DateValue']
            if not any(key in value for key in valid_value_types):
                raise ValueError(
                    'attributeValue must contain one of: ' + ', '.join(valid_value_types)
                )

            # Add security validation for string values
            if 'StringValue' in value:
                self._validate_string_safety(str(value['StringValue']), 'StringValue')
            if 'StringListValue' in value:
                for item in value['StringListValue']:
                    self._validate_string_safety(str(item), 'StringListValue item')
            return

        # Check for nested filter structure
        if 'equalsTo' in attribute_filter:
            equals_to = attribute_filter['equalsTo']
            if not isinstance(equals_to, dict):
                raise ValueError('equalsTo must be a dictionary')
            if 'name' not in equals_to or 'value' not in equals_to:
                raise ValueError('equalsTo must contain name and value')
            # Add security validation for nested values
            self._validate_string_safety(str(equals_to['name']), 'equalsTo.name')

    def _validate_content_source(self, content_source: Dict) -> None:
        """Validate the content source parameter.

        Args:
            content_source (Dict): The content source to validate

        Raises:
            ValueError: If the content source is invalid
        """
        if not isinstance(content_source, dict):
            raise ValueError('content_source must be a dictionary')

        # Check for retriever field instead of sourceType
        if 'retriever' not in content_source:
            raise ValueError("content_source must include 'retriever'")

        # Validate retriever has required retrieverId
        retriever = content_source.get('retriever')
        if not isinstance(retriever, dict) or 'retrieverId' not in retriever:
            raise ValueError("content_source.retriever must include 'retrieverId'")

    def _validate_max_results(self, max_results: int) -> None:
        """Validate the max_results parameter.

        Args:
            max_results (int): The maximum number of results to validate

        Raises:
            ValueError: If max_results is invalid
        """
        if not isinstance(max_results, int):
            raise ValueError('max_results must be an integer')

        if max_results < 1 or max_results > 100:
            raise ValueError('max_results must be between 1 and 100')

    def _validate_string_safety(self, value: str, param_name: str) -> None:
        """Validate string parameters for dangerous patterns.

        Args:
            value: String value to validate
            param_name: Name of parameter being validated

        Raises:
            ValueError: If dangerous patterns are detected
        """
        # Check for command injection patterns
        dangerous_patterns = [
            ';',
            '&&',
            '||',
            '|',
            '>',
            '<',
            '>>',
            '<<',
            '$(',
            '`',
            '{',
            '}',
            '[',
            ']',
            '$(',
            '${',
            'eval',
            'exec',
            'system',
        ]

        for pattern in dangerous_patterns:
            if pattern in value:
                raise ValueError(f'Invalid character/pattern detected in {param_name}')

        # Check for excessive length
        if len(value) > 1000:  # Adjust limit as needed
            raise ValueError(f'{param_name} exceeds maximum length')

    def _validate_required_params(self, application_id: str, query_text: str) -> None:
        """Validate the required parameters.

        Args:
            application_id (str): The application ID to validate
            query_text (str): The query text to validate

        Raises:
            ValueError: If any required parameter is invalid
        """
        if not application_id or not isinstance(application_id, str):
            raise ValueError('application_id must be a non-empty string')

        if not query_text or not isinstance(query_text, str):
            raise ValueError('query_text must be a non-empty string')

        if len(query_text.strip()) == 0:
            raise ValueError('query_text cannot be empty or only whitespace')

        self._validate_string_safety(application_id, 'application_id')
        self._validate_string_safety(query_text, 'query_text')

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
            # Validate required parameters
            self._validate_required_params(application_id, query_text)

            # Validate optional parameters if provided
            if attribute_filter is not None:
                self._validate_attribute_filter(attribute_filter)
            if content_source is not None:
                self._validate_content_source(content_source)
            if max_results is not None:
                self._validate_max_results(max_results)
            if next_token is not None and not isinstance(next_token, str):
                raise ValueError('next_token must be a string')

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
