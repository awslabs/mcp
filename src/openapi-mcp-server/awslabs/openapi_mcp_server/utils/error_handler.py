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
"""Utilities for error handling in the OpenAPI MCP Server."""

import httpx
import json
from awslabs.openapi_mcp_server import logger
from typing import Any, Dict, Optional, Type


class APIError(Exception):
    """Base exception class for API errors."""

    def __init__(
        self,
        status_code: int,
        message: str,
        details: Any = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize the API error.

        Args:
            status_code: HTTP status code
            message: Error message
            details: Additional error details
            original_error: Original exception that caused this error

        """
        self.status_code = status_code
        self.message = message
        self.details = {} if details is None else details
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        """Return a string representation of the error."""
        return f'{self.status_code}: {self.message}'

    def __repr__(self) -> str:
        """Return a representation of the error."""
        return f'{self.__class__.__name__}({self.status_code}, {repr(self.message)}, {repr(self.details)})'


class AuthenticationError(APIError):
    """Exception raised for authentication errors (401)."""

    pass


class AuthorizationError(APIError):
    """Exception raised for authorization errors (403)."""

    pass


class ResourceNotFoundError(APIError):
    """Exception raised for resource not found errors (404)."""

    pass


class ValidationError(APIError):
    """Exception raised for validation errors (422)."""

    pass


class RateLimitError(APIError):
    """Exception raised for rate limit errors (429)."""

    pass


class ServerError(APIError):
    """Exception raised for server errors (5xx)."""

    pass


class ConnectionError(APIError):
    """Exception raised for connection errors."""

    pass


class NetworkError(APIError):
    """Exception raised for network errors."""

    pass


# Map status codes to error classes
ERROR_CLASSES: Dict[Any, Type[APIError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: ResourceNotFoundError,
    422: ValidationError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
    # Request error types
    httpx.ConnectTimeout: ConnectionError,
    httpx.ReadTimeout: ConnectionError,
    httpx.ConnectError: NetworkError,
    httpx.RequestError: NetworkError,
}


def extract_error_details(response: httpx.Response) -> Dict[str, Any]:
    """Extract error details from an HTTP response.

    Args:
        response: The HTTP response

    Returns:
        A dictionary of error details

    """
    details = {}

    # Try to parse JSON response
    try:
        if response.headers.get('content-type', '').startswith('application/json'):
            details = response.json()
    except Exception as e:
        logger.debug(f'Failed to parse JSON response: {e}')

    # If we couldn't parse JSON, use the text
    if not details and response.text:
        details = {'message': response.text}

    return details


def format_error_message(status_code: int, reason: str, details: Dict[str, Any]) -> str:
    """Format an error message from status code, reason, and details.

    Args:
        status_code: HTTP status code
        reason: HTTP reason phrase
        details: Additional error details

    Returns:
        A formatted error message

    """
    # Start with the status code and reason
    message = f'{status_code} {reason}'

    # Add details if available
    if details:
        # Try to extract a message from the details
        if 'message' in details:
            message += f': {details["message"]}'
        elif 'error' in details:
            if isinstance(details['error'], str):
                message += f': {details["error"]}'
            elif isinstance(details['error'], dict) and 'message' in details['error']:
                message += f': {details["error"]["message"]}'

    # Add troubleshooting tips based on status code
    if status_code == 401:
        message += '\n\nTROUBLESHOOTING: Authentication error. Please check your credentials or ensure your token is valid. You may need to refresh your authentication tokens.'
    elif status_code == 403:
        message += "\n\nTROUBLESHOOTING: Authorization error. You don't have permission to access this resource. Please check your IAM permissions or API key scope."

    return message


def handle_http_error(error: httpx.HTTPStatusError) -> APIError:
    """Convert an HTTPX error to an appropriate APIError subclass."""
    status_code = error.response.status_code
    details = extract_error_details(error.response)
    message = format_error_message(status_code, error.response.reason_phrase, details)

    # Enhanced logging for auth errors
    if status_code == 401:
        # Extract and log authorization header (masked) for debugging
        request = error.request
        if request and hasattr(request, 'headers') and 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            # Safely mask the token
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                # Try to decode JWT token for debugging (without validation)
                try:
                    # Split the token into parts
                    parts = token.split('.')
                    if len(parts) == 3:
                        # Decode the payload (middle part)
                        # Add padding if needed
                        payload = parts[1]
                        padding = len(payload) % 4
                        if padding:
                            payload += '=' * (4 - padding)

                        # Decode base64
                        import base64

                        decoded = base64.b64decode(payload)
                        payload_data = json.loads(decoded)

                        # Check for expiration
                        if 'exp' in payload_data:
                            import time

                            exp_time = payload_data['exp']
                            now = int(time.time())
                            remaining = exp_time - now

                            if remaining < 0:
                                logger.warning(f'Token expired {abs(remaining)} seconds ago')
                            else:
                                logger.debug(
                                    f'Token expiration: {exp_time}, Current time: {now}, Remaining: {remaining}s'
                                )
                except Exception as e:
                    logger.warning(f'Could not decode token for debugging: {e}')

    # Use the appropriate error class based on status code
    error_class = ERROR_CLASSES.get(status_code, APIError)
    return error_class(status_code, message, details=details, original_error=error)


def handle_request_error(error: httpx.RequestError) -> APIError:
    """Convert an HTTPX request error to an appropriate APIError subclass."""
    # Map different request error types to different messages
    error_class = ConnectionError
    for error_type in [
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.ConnectError,
        httpx.RequestError,
    ]:
        if isinstance(error, error_type):
            error_class = ERROR_CLASSES.get(error_type, ConnectionError)
            break

    # Get more specific error message based on error type
    if isinstance(error, httpx.ConnectTimeout):
        message = 'Connection timed out: The server took too long to respond'
    elif isinstance(error, httpx.ReadTimeout):
        message = 'Read timed out: The server took too long to send a response'
    elif isinstance(error, httpx.ConnectError):
        message = f'Connection error: Could not connect to the server: {error}'
    else:
        message = f'Request error: {error}'

    # Create the error
    return error_class(500, message, original_error=error)


async def safe_request(
    client: httpx.AsyncClient, method: str, url: str, **kwargs
) -> httpx.Response:
    """Execute an HTTP request with comprehensive error handling.

    Args:
        client: The HTTPX client to use for the request
        method: The HTTP method to use
        url: The URL to request
        **kwargs: Additional arguments to pass to the client's request method

    Returns:
        The HTTP response

    Raises:
        APIError: If an error occurs during the request

    """
    try:
        # Log request details at DEBUG level
        request_details = {
            'method': method,
            'url': url,
        }

        # Log headers (safely) if present in kwargs
        if 'headers' in kwargs and kwargs['headers']:
            sanitized_headers = {}
            for header, value in kwargs['headers'].items():
                if header.lower() == 'authorization' and value:
                    # Mask authorization header for security
                    if value.startswith('Bearer ') and len(value) > 15:
                        sanitized_headers[header] = (
                            'Bearer ' + value[7:15] + '...' + value[-8:]
                            if len(value) > 30
                            else 'Bearer ****'
                        )
                    else:
                        sanitized_headers[header] = '[MASKED]'
                else:
                    sanitized_headers[header] = str(value)
            request_details['headers'] = sanitized_headers

        # Log query params if present
        if 'params' in kwargs and kwargs['params']:
            # Convert all values to strings to avoid type issues
            params_dict = {}
            for k, v in kwargs['params'].items():
                params_dict[k] = str(v) if v is not None else None
            request_details['params'] = params_dict

        logger.debug(f'Making HTTP request: {request_details}')

        # Make the request
        response = await client.request(method=method, url=url, **kwargs)

        # Log response details at DEBUG level
        logger.debug(f'Response: {response.status_code} {response.reason_phrase}')

        # Raise an exception for 4xx/5xx responses
        response.raise_for_status()

        return response

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (4xx, 5xx)
        logger.error(
            f'HTTP error when accessing {url}: {e.response.status_code} {e.response.reason_phrase}'
        )
        raise handle_http_error(e)

    except httpx.RequestError as e:
        # Handle request errors (connection, timeout, etc.)
        logger.error(f'Request error when accessing {url}: {e}')

        # Create a more specific error
        raise handle_request_error(e)

    except Exception as e:
        # Handle unexpected errors
        logger.error(f'Unexpected error when accessing {url}: {e}')
        raise APIError(500, f'Unexpected error: {e}', original_error=e)
