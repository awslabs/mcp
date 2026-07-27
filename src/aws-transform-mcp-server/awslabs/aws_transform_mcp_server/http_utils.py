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

"""HTTP utilities: error class, retry logic, and shared request helper."""

import asyncio
import httpx
import random
from awslabs.aws_transform_mcp_server.consts import (
    MAX_RETRIES,
    RETRYABLE_STATUSES,
    TIMEOUT_SECONDS,
)
from loguru import logger
from typing import Any, Dict, Optional


class HttpError(Exception):
    """HTTP error with status code and response body."""

    def __init__(self, status_code: int, body: Any, message: Optional[str] = None) -> None:
        """Initialize with status code, response body, and optional message."""
        super().__init__(message or f'HTTP {status_code}')
        self.status_code = status_code
        self.body = body
        self.message = message or f'HTTP {status_code}'


def get_retry_delay(attempt: int, status: Optional[int] = None) -> float:
    """Return the retry delay in seconds using exponential backoff with jitter.

    Args:
        attempt: Zero-based retry attempt number.
        status: HTTP status code (429 uses a longer base delay).

    Returns:
        Delay in seconds.
    """
    base = 1.0 if status == 429 else 0.2
    exponential = base * (2**attempt)
    return exponential * (1 + random.random() * 0.1)


def extract_error_message(error_body: Any, fallback: str) -> str:
    """Extract an error message from a response body dict, or return fallback."""
    if isinstance(error_body, dict) and 'message' in error_body:
        return error_body['message']
    return fallback


def is_retryable(status_code: int) -> bool:
    """Return True if the status code is retryable."""
    return status_code in RETRYABLE_STATUSES


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[bytes] = None,
    max_retries: int = MAX_RETRIES,
    timeout_seconds: float = TIMEOUT_SECONDS,
) -> httpx.Response:
    """Make an HTTP request with exponential-backoff retry on transient errors.

    Retries on status codes in RETRYABLE_STATUSES and on httpx.TimeoutException.

    Args:
        client: An httpx.AsyncClient instance.
        method: HTTP method (e.g. 'POST').
        url: Request URL.
        headers: Request headers.
        body: Request body bytes (optional).
        max_retries: Maximum number of retry attempts.
        timeout_seconds: Per-request timeout in seconds.

    Returns:
        The httpx.Response on success.

    Raises:
        HttpError: On non-retryable HTTP errors, or after exhausting retries.
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(
                method,
                url,
                headers=headers,
                content=body,
                timeout=timeout_seconds,
            )

            if response.is_success:
                return response

            # Parse error body
            try:
                error_body = response.json()
            except Exception:
                error_body = {'message': response.reason_phrase or f'HTTP {response.status_code}'}

            error = HttpError(
                response.status_code,
                error_body,
                f'HTTP {response.status_code}: '
                f'{extract_error_message(error_body, response.reason_phrase or str(response.status_code))}',  # noqa: E501
            )

            if is_retryable(response.status_code) and attempt < max_retries:
                last_error = error
                delay = get_retry_delay(attempt, response.status_code)
                logger.debug(
                    'Retryable HTTP {} on attempt {}, sleeping {:.2f}s',
                    response.status_code,
                    attempt,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            raise error

        except httpx.TimeoutException as exc:
            if attempt < max_retries:
                last_error = exc
                delay = get_retry_delay(attempt)
                logger.debug(
                    'Timeout on attempt {}, sleeping {:.2f}s',
                    attempt,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            raise HttpError(
                0,
                {'message': f'Request timed out after {timeout_seconds}s'},
                f'Request timed out after {timeout_seconds}s',
            ) from exc

    # Should not be reached, but safety net
    if last_error is not None:
        raise last_error
    raise HttpError(0, {'message': 'Request failed after retries'}, 'Request failed after retries')
