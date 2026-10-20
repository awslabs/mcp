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

"""Retry guidance for tool error responses.

Every error response carries a ``retry_strategy`` telling the caller what to do next:

- ``retry_same_request``: the failure is transient (throttling, connection, 5xx).
- ``modify_request``: the arguments must change before trying again.
- ``do_not_retry``: the failure cannot be fixed during this run (permissions, opt-in).

The strategy is derived from the existing ``error_type`` values, which are left
unchanged. Unknown or missing types get ``do_not_retry``.
"""

from typing import Any, Dict, Iterable, Optional, Tuple


RETRY_SAME_REQUEST = 'retry_same_request'
MODIFY_REQUEST = 'modify_request'
DO_NOT_RETRY = 'do_not_retry'

DEFAULT_RETRY_STRATEGY = DO_NOT_RETRY

_HINT_THROTTLED = 'The request was throttled. Wait briefly, then retry the same request.'
_HINT_TRANSIENT = 'The service failed transiently. Retry the same request.'
_HINT_INVALID = 'The request arguments are invalid. Correct them using the message, then retry.'
_HINT_NOT_FOUND = 'Nothing matched the request. Broaden or correct the filters, then retry.'
_HINT_INVALID_NEXT_TOKEN = (
    'The next_token is expired or no longer matches the request. Call again without '
    'next_token to restart from the first page.'
)
_HINT_ACCESS = (
    'The caller lacks permission for this operation. Do not retry; '
    'report the missing permission to the user.'
)
_HINT_OPT_IN = (
    'The account is not opted in or enrolled for this feature. Do not retry; '
    'tell the user how to enable it.'
)

# error_type -> (retry_strategy, hint). Covers both AWS error codes passed through by
# handle_aws_error and the lowercase values set on local format_response errors.
_ERROR_TYPE_GUIDANCE: Dict[str, Tuple[str, Optional[str]]] = {
    # Throttling
    'ThrottlingException': (RETRY_SAME_REQUEST, _HINT_THROTTLED),
    'Throttling': (RETRY_SAME_REQUEST, _HINT_THROTTLED),
    'ThrottledException': (RETRY_SAME_REQUEST, _HINT_THROTTLED),
    'TooManyRequestsException': (RETRY_SAME_REQUEST, _HINT_THROTTLED),
    'RequestLimitExceeded': (RETRY_SAME_REQUEST, _HINT_THROTTLED),
    'LimitExceededException': (RETRY_SAME_REQUEST, _HINT_THROTTLED),
    'throttling_error': (RETRY_SAME_REQUEST, _HINT_THROTTLED),
    # Transient service and connection failures
    'aws_connection_error': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'InternalServerException': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'InternalServerError': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'InternalFailure': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'ServiceUnavailable': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'ServiceUnavailableException': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'RequestTimeout': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'RequestTimeoutException': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'InternalErrorException': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    # A builtin TimeoutError reaching handle_aws_error (e.g. polling an Athena query)
    'unknown_timeouterror': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    'service_unavailable': (RETRY_SAME_REQUEST, _HINT_TRANSIENT),
    # Invalid arguments
    'validation_error': (MODIFY_REQUEST, _HINT_INVALID),
    'invalid_operation': (MODIFY_REQUEST, _HINT_INVALID),
    'invalid_parameter_value': (MODIFY_REQUEST, _HINT_INVALID),
    'ValidationException': (MODIFY_REQUEST, _HINT_INVALID),
    'InvalidInputException': (MODIFY_REQUEST, _HINT_INVALID),
    'InvalidNextTokenException': (MODIFY_REQUEST, _HINT_INVALID),
    'ExpiredNextTokenException': (MODIFY_REQUEST, _HINT_INVALID),
    'InvalidRequestException': (MODIFY_REQUEST, _HINT_INVALID),
    'BadRequestException': (MODIFY_REQUEST, _HINT_INVALID),
    'BillExpirationException': (MODIFY_REQUEST, _HINT_INVALID),
    'RequestChangedException': (MODIFY_REQUEST, _HINT_INVALID),
    'invalid_next_token': (MODIFY_REQUEST, _HINT_INVALID_NEXT_TOKEN),
    # Nothing matched
    'no_results': (MODIFY_REQUEST, _HINT_NOT_FOUND),
    'ResourceNotFoundException': (MODIFY_REQUEST, _HINT_NOT_FOUND),
    'resource_not_found': (MODIFY_REQUEST, _HINT_NOT_FOUND),
    'NotFoundException': (MODIFY_REQUEST, _HINT_NOT_FOUND),
    'not_found': (MODIFY_REQUEST, _HINT_NOT_FOUND),
    # Permissions and account state
    'access_denied': (DO_NOT_RETRY, _HINT_ACCESS),
    'UnauthorizedOperation': (DO_NOT_RETRY, _HINT_ACCESS),
    'UnauthorizedException': (DO_NOT_RETRY, _HINT_ACCESS),
    'AuthFailure': (DO_NOT_RETRY, _HINT_ACCESS),
    'OptInRequiredException': (DO_NOT_RETRY, _HINT_OPT_IN),
    'opt_in_required': (DO_NOT_RETRY, _HINT_OPT_IN),
    'enrollment_error': (DO_NOT_RETRY, _HINT_OPT_IN),
    'DataUnavailableException': (DO_NOT_RETRY, None),
}

# Families of AWS codes matched by prefix, checked after the exact table.
_ERROR_TYPE_PREFIX_GUIDANCE: Tuple[Tuple[str, Tuple[str, Optional[str]]], ...] = (
    ('InvalidParameter', (MODIFY_REQUEST, _HINT_INVALID)),
    ('AccessDenied', (DO_NOT_RETRY, _HINT_ACCESS)),
)


def classify_error(
    error_type: Optional[str], http_status: Optional[int] = None
) -> Tuple[str, Optional[str]]:
    """Return the (retry_strategy, hint) for an error.

    Args:
        error_type: The response's error_type, if any
        http_status: The AWS HTTP status, if any. An otherwise unmapped 5xx is transient.

    Returns:
        Tuple of retry_strategy and an optional fixed hint
    """
    if error_type:
        if error_type in _ERROR_TYPE_GUIDANCE:
            return _ERROR_TYPE_GUIDANCE[error_type]
        for prefix, guidance in _ERROR_TYPE_PREFIX_GUIDANCE:
            if error_type.startswith(prefix):
                return guidance
    if isinstance(http_status, int) and http_status >= 500:
        return RETRY_SAME_REQUEST, _HINT_TRANSIENT
    return DEFAULT_RETRY_STRATEGY, None


def combine_guidance(guidance: Iterable[Tuple[str, Optional[str]]]) -> Tuple[str, Optional[str]]:
    """Combine the (retry_strategy, hint) of several failures, e.g. one per region.

    Identical guidance is kept as is. Otherwise do_not_retry wins (some part cannot
    succeed during this run), then retry_same_request (a transient part may succeed on
    retry), then modify_request, with no hint since none fits every failure.

    Args:
        guidance: (retry_strategy, hint) pairs, as returned by classify_error

    Returns:
        Tuple of the combined retry_strategy and an optional hint
    """
    unique = set(guidance)
    if len(unique) == 1:
        return unique.pop()
    strategies = {retry_strategy for retry_strategy, _ in unique}
    for retry_strategy in (DO_NOT_RETRY, RETRY_SAME_REQUEST, MODIFY_REQUEST):
        if retry_strategy in strategies:
            return retry_strategy, None
    return DEFAULT_RETRY_STRATEGY, None


def add_retry_guidance(response: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of an error response with retry_strategy and hint filled in.

    A call site that sets retry_strategy overrides the mapping, and no mapped hint is
    added, since it may contradict the override. A call site that sets only hint keeps it.

    Args:
        response: An error response dict (status='error')

    Returns:
        The response with retry_strategy, and hint when one applies
    """
    if 'retry_strategy' in response:
        return response

    retry_strategy, hint = classify_error(response.get('error_type'), response.get('http_status'))
    enriched = {**response, 'retry_strategy': retry_strategy}
    if hint is not None:
        enriched.setdefault('hint', hint)
    return enriched


class InvalidNextTokenError(Exception):
    """The caller's next_token was rejected; the caller must restart without it."""

    def __init__(self, operation: str, error_code: str):
        """Record the operation and the service error code that rejected the token."""
        super().__init__(f'{operation}: next_token rejected ({error_code})')
        self.operation = operation
        self.error_code = error_code
