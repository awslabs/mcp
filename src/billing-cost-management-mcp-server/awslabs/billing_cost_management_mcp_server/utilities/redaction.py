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

"""Redaction of AWS identifiers from error text sent to the MCP client.

AWS error messages name the caller and the resource. An AccessDenied message, for
example, reads "User: arn:aws:sts::<account>:assumed-role/<role>/<session> is not
authorized to perform: <action> on resource: <arn>". Error responses and the log
messages sent to the client replace every ARN and 12-digit account ID with a fixed
placeholder; the action and the rest of the message are kept. Successful results are
never redacted, since account IDs there are data (e.g. a LINKED_ACCOUNT group key).
"""

import re
from typing import Any


REDACTED_ARN = '[ARN redacted]'
REDACTED_ACCOUNT_ID = '[account ID redacted]'

# An ARN starts at a word boundary and runs to the next whitespace, quote, backslash
# (a JSON escape), bracket, semicolon, or a comma that ends a list or a clause (IAM
# role and session names may contain commas).
_ARN_RE = re.compile(
    r'(?<!\w)arn:aws[a-z-]*:(?:[^\s"\'`,;()\[\]{}<>\\]|,(?=[^\s,]))*', re.IGNORECASE
)
# Exactly 12 ASCII digits, not part of a longer number, a word, a decimal amount, or
# the last group of a UUID such as a request ID. An underscore or a hyphen does not
# protect it (e.g. account_123456789012, a bucket named cur-2024-123456789012).
_ACCOUNT_ID_RE = re.compile(
    r'(?<![0-9A-Za-z.])'
    r'(?<![0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-)'
    r'[0-9]{12}(?![0-9A-Za-z]|\.[0-9])'
)


def _redact_text(text: str) -> str:
    redacted = _ACCOUNT_ID_RE.sub(REDACTED_ACCOUNT_ID, _ARN_RE.sub(REDACTED_ARN, text))
    return text if redacted == text else redacted


def redact_identifiers(value: Any) -> Any:
    """Return value with ARNs and account IDs replaced in every string it contains.

    Dicts, lists and tuples are walked; their keys and non-string values are kept.
    A value with nothing to redact is returned as is.

    Args:
        value: A string, or a container of strings (e.g. an error response dict)

    Returns:
        The redacted value
    """
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        redacted = {key: redact_identifiers(item) for key, item in value.items()}
        changed = any(redacted[key] is not value[key] for key in value)
        return redacted if changed else value
    if isinstance(value, (list, tuple)):
        redacted = [redact_identifiers(item) for item in value]
        if all(new is old for new, old in zip(redacted, value)):
            return value
        if isinstance(value, tuple) and hasattr(value, '_fields'):  # namedtuple
            return type(value)(*redacted)
        return type(value)(redacted)
    return value
