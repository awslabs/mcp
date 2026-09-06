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

"""Utilities for bounded fan-out across AWS regions."""

import asyncio
import base64
import binascii
import json
from .aws_service_base import format_response, handle_aws_error
from dataclasses import dataclass
from fastmcp import Context
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    cast,
)


RequestState = TypeVar('RequestState')
Success = TypeVar('Success')


@dataclass
class RegionalFanoutResult(Generic[Success]):
    """Outcomes from querying a set of regions."""

    successes: Dict[str, Success]
    errors: Dict[str, Dict[str, Any]]


@dataclass
class RegionalPageResult:
    """Merged outcomes from paginated regional list operations."""

    items: List[Dict[str, Any]]
    next_tokens: Dict[str, str]
    errors: Dict[str, Dict[str, Any]]
    successful_regions: List[str]


class RegionalTokenError(ValueError):
    """A structured validation failure for an opaque regional pagination token."""

    def __init__(self, reason: str, **details: Any):
        """Initialize the error with a stable reason and contextual details."""
        super().__init__(reason)
        self.reason = reason
        self.details = details


async def fan_out_regions(
    requests: Mapping[str, RequestState],
    worker: Callable[[str, RequestState], Awaitable[Success]],
    *,
    ctx: Context,
    operation: str,
    service_name: str,
    max_concurrency: int,
) -> RegionalFanoutResult[Success]:
    """Execute one worker per region with bounded concurrency.

    The utility owns execution mechanics and standard AWS error formatting. Callers
    decide how to create clients and interpret regional outcomes.

    Args:
        requests: Region keys mapped to caller-defined request state.
        worker: Async callable that executes one regional request.
        ctx: The MCP context object.
        operation: The AWS operation being performed.
        service_name: The user-facing AWS service name.
        max_concurrency: Maximum number of regional workers running concurrently.

    Returns:
        Regional successes and errors, each preserving request order.

    Raises:
        ValueError: If max_concurrency is less than one.
    """
    if max_concurrency < 1:
        raise ValueError('max_concurrency must be at least 1')

    semaphore = asyncio.Semaphore(max_concurrency)

    async def query_region(
        region: str, request_state: RequestState
    ) -> Tuple[str, Optional[Success], Optional[Dict[str, Any]]]:
        async with semaphore:
            try:
                value = await worker(region, request_state)
                return region, value, None
            except Exception as error:
                formatted_error = await format_regional_aws_error(
                    ctx, error, operation, service_name
                )
                return region, None, formatted_error

    outcomes = await asyncio.gather(
        *(query_region(region, state) for region, state in requests.items())
    )

    successes: Dict[str, Success] = {}
    errors: Dict[str, Dict[str, Any]] = {}
    for region, value, error in outcomes:
        if error is not None:
            errors[region] = error
        else:
            successes[region] = cast(Success, value)

    return RegionalFanoutResult(successes=successes, errors=errors)


async def collect_regional_pages(
    requests: Mapping[str, RequestState],
    worker: Callable[
        [str, RequestState],
        Awaitable[Tuple[List[Dict[str, Any]], Optional[str]]],
    ],
    *,
    ctx: Context,
    operation: str,
    service_name: str,
    max_concurrency: int,
) -> RegionalPageResult:
    """Execute regional list workers and merge their items and pagination state."""
    outcomes = await fan_out_regions(
        requests,
        worker,
        ctx=ctx,
        operation=operation,
        service_name=service_name,
        max_concurrency=max_concurrency,
    )

    items: List[Dict[str, Any]] = []
    next_tokens: Dict[str, str] = {}
    for region, (regional_items, next_token) in outcomes.successes.items():
        for item in regional_items:
            item['region'] = region
            items.append(item)
        if next_token:
            next_tokens[region] = next_token

    return RegionalPageResult(
        items=items,
        next_tokens=next_tokens,
        errors=outcomes.errors,
        successful_regions=list(outcomes.successes),
    )


async def format_regional_aws_error(
    ctx: Context,
    error: Exception,
    operation: str,
    service_name: str,
) -> Dict[str, Any]:
    """Classify an AWS regional failure and retain fields useful to callers."""
    classified = await handle_aws_error(ctx, error, operation, service_name)
    useful_fields = (
        'error_type',
        'message',
        'request_id',
        'http_status',
        'boto_error_type',
        'exception_type',
        'details',
    )
    return {field: classified[field] for field in useful_fields if field in classified}


def encode_regional_next_token(region_next_tokens: Mapping[str, str]) -> str:
    """Encode per-region pagination state as one opaque token."""
    payload = json.dumps(region_next_tokens, separators=(',', ':'), sort_keys=True)
    return base64.b64encode(payload.encode('utf-8')).decode('ascii')


def _decode_region_map(next_token: str) -> Dict[str, str]:
    """Decode an opaque token into its per-region pagination map.

    Raises:
        RegionalTokenError: If the token is malformed or contains invalid state.
    """
    try:
        decoded = base64.b64decode(next_token.encode('ascii'), validate=True).decode('utf-8')
        parsed = json.loads(decoded)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as error:
        raise RegionalTokenError('decode_error', cause=str(error)) from error

    if not isinstance(parsed, dict):
        raise RegionalTokenError('not_region_map')
    if not parsed:
        raise RegionalTokenError('empty_region_map')

    invalid_regions = sorted(
        region
        for region, token in parsed.items()
        if not isinstance(region, str) or not isinstance(token, str) or not token.strip()
    )
    if invalid_regions:
        raise RegionalTokenError('invalid_region_tokens', regions=invalid_regions)

    return dict(parsed)


def is_regional_next_token(next_token: Optional[str]) -> bool:
    """Report whether a token carries per-region pagination state.

    Lets callers detect a multi-region token before they know which regions it
    should be validated against.
    """
    if not next_token:
        return False
    try:
        _decode_region_map(next_token)
    except RegionalTokenError:
        return False
    return True


def decode_regional_next_token(
    next_token: Optional[str], supported_regions: Sequence[str]
) -> Dict[str, Optional[str]]:
    """Decode and validate opaque per-region pagination state.

    Omitting the token starts a request in every supported region.

    Raises:
        RegionalTokenError: If the token is malformed or contains invalid state.
    """
    if not next_token:
        return dict.fromkeys(supported_regions)

    parsed = _decode_region_map(next_token)

    unsupported_regions = sorted(set(parsed) - set(supported_regions))
    if unsupported_regions:
        raise RegionalTokenError('unsupported_regions', regions=unsupported_regions)

    return dict(parsed)


def parse_regional_next_token(
    next_token: Optional[str],
    supported_regions: Sequence[str],
) -> Tuple[Dict[str, Optional[str]], Optional[Dict[str, Any]]]:
    """Resolve an opaque token into regional request state or a validation response."""
    supported_region_list = list(supported_regions)
    try:
        return decode_regional_next_token(next_token, supported_region_list), None
    except RegionalTokenError as error:
        data: Dict[str, Any] = {'parameter': 'next_token'}
        if error.reason == 'decode_error':
            data['supported_regions'] = supported_region_list
            message = (
                'Invalid multi-region next_token. Pass the next_token from the previous '
                'response back unchanged, along with the same `regions` list. Decode error: '
                f'{error.details["cause"]}'
            )
        elif error.reason == 'not_region_map':
            message = (
                'Invalid multi-region next_token: decoded pagination state must be a non-empty '
                'region-to-token map. Pass the previous response next_token unchanged.'
            )
        elif error.reason == 'empty_region_map':
            message = (
                'Invalid multi-region next_token: the regional pagination map is empty. Start '
                'a new query by omitting next_token.'
            )
        elif error.reason == 'invalid_region_tokens':
            data['invalid_regions'] = error.details['regions']
            message = (
                'Invalid multi-region next_token: every regional token must be a non-empty '
                'string. Pass the previous response next_token unchanged.'
            )
        else:
            unsupported_regions = error.details['regions']
            data['unsupported_regions'] = unsupported_regions
            data['supported_regions'] = supported_region_list
            message = (
                'Invalid multi-region next_token: it contains region key(s) absent from the '
                f'`regions` list: {", ".join(unsupported_regions)}. Pass the same `regions` '
                'list the token was produced with.'
            )
        return {}, format_response('error', data, message)
