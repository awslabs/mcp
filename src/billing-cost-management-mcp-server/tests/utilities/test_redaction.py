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

"""Tests for redacting ARNs and account IDs from error text."""

import pytest
from awslabs.billing_cost_management_mcp_server.utilities.redaction import (
    REDACTED_ACCOUNT_ID,
    REDACTED_ARN,
    redact_identifiers,
)


CALLER_ARN = 'arn:aws:sts::123456789012:assumed-role/ExampleRole/example-session'


class TestRedactIdentifiers:
    """redact_identifiers replaces ARNs and 12-digit account IDs in strings."""

    def test_access_denied_message(self):
        """The caller ARN, the resource ARN and their account IDs are all removed."""
        message = (
            f'User: {CALLER_ARN} is not authorized to perform: billing:GetBillingView on '
            'resource: arn:aws:billing::210987654321:billingview/primary because no '
            'resource-based policy allows the billing:GetBillingView action'
        )

        result = redact_identifiers(message)

        assert result == (
            f'User: {REDACTED_ARN} is not authorized to perform: billing:GetBillingView on '
            f'resource: {REDACTED_ARN} because no resource-based policy allows the '
            'billing:GetBillingView action'
        )

    @pytest.mark.parametrize(
        'arn',
        [
            'arn:aws:iam::123456789012:role/service-role/Example',
            'arn:aws-cn:sts::123456789012:assumed-role/Example/session',
            'arn:aws-us-gov:iam::123456789012:user/example',
            'arn:aws:ce::123456789012:costcategory/0123abcd-4567-89ef',
            'arn:aws:s3:::example-bucket',
            'arn:aws:savingsplans::123456789012:savingsplan/0123abcd',
        ],
    )
    def test_any_partition_and_service(self, arn):
        """ARNs of every partition and service are replaced whole."""
        assert redact_identifiers(f"bad value '{arn}'.") == f"bad value '{REDACTED_ARN}'."

    @pytest.mark.parametrize(
        'text, expected',
        [
            (
                'Account 123456789012 is not allowed to access this resource.',
                f'Account {REDACTED_ACCOUNT_ID} is not allowed to access this resource.',
            ),
            ('linked account 123456789012.', f'linked account {REDACTED_ACCOUNT_ID}.'),
            (
                'accounts [123456789012,210987654321]',
                f'accounts [{REDACTED_ACCOUNT_ID},{REDACTED_ACCOUNT_ID}]',
            ),
        ],
    )
    def test_bare_account_ids(self, text, expected):
        """A standalone 12-digit number is an account ID, including at a sentence end."""
        assert redact_identifiers(text) == expected

    @pytest.mark.parametrize(
        'text',
        [
            'Amount 123456789012.50 exceeds the limit',  # decimal amount
            'id 1234567890123 is too long',  # 13 digits
            'id 12345678901 is too short',  # 11 digits
            'date 2026-10-01T00:00:00Z',
            'request a1b2c3d4-5678-90ab-cdef-1234567890ab',
            'request 1a2b3c4d-1111-2222-3333-123456789012',  # all-digit last UUID group
            'learn:aws:things',
        ],
    )
    def test_other_numbers_are_kept(self, text):
        """Amounts, dates, request IDs and other digit runs are not account IDs."""
        assert redact_identifiers(text) == text

    def test_nested_structures(self):
        """Strings inside dicts and lists are redacted; keys and non-strings are kept."""
        value = {
            'message': f'User: {CALLER_ARN}',
            'http_status': 403,
            'items': ['account 123456789012', None, 1.5, {'arn': CALLER_ARN}],
            'pair': ('123456789012', True),
        }

        result = redact_identifiers(value)

        assert result == {
            'message': f'User: {REDACTED_ARN}',
            'http_status': 403,
            'items': [f'account {REDACTED_ACCOUNT_ID}', None, 1.5, {'arn': REDACTED_ARN}],
            'pair': (REDACTED_ACCOUNT_ID, True),
        }

    def test_unchanged_value_is_returned_as_is(self):
        """Nothing to redact: the same object comes back."""
        value = {'message': 'Throttled', 'items': ['a']}
        assert redact_identifiers(value) is value

    @pytest.mark.parametrize(
        'text, expected',
        [
            ('table account_123456789012_cur', f'table account_{REDACTED_ACCOUNT_ID}_cur'),
            (
                'bucket cur-2024-123456789012 denied',
                f'bucket cur-2024-{REDACTED_ACCOUNT_ID} denied',
            ),
            ('key aaaa-123456789012', f'key aaaa-{REDACTED_ACCOUNT_ID}'),
            (
                'role arn:aws:iam::123456789012:role/a,b denied, retry',
                f'role {REDACTED_ARN} denied, retry',
            ),
            ('ARN:AWS:IAM::123456789012:role/Example', REDACTED_ARN),
            (
                '{"Message": "User: \\"arn:aws:sts::123456789012:assumed-role/R/s\\""}',
                f'{{"Message": "User: \\"{REDACTED_ARN}\\""}}',
            ),
        ],
    )
    def test_edge_forms(self, text, expected):
        """Underscore neighbours, commas in role names, upper case and JSON escapes."""
        assert redact_identifiers(text) == expected

    def test_namedtuple_kept_as_namedtuple(self):
        """A namedtuple is rebuilt field by field."""
        from collections import namedtuple

        Pair = namedtuple('Pair', 'account note')
        result = redact_identifiers(Pair('123456789012', 'ok'))

        assert result == Pair(REDACTED_ACCOUNT_ID, 'ok')
        assert isinstance(result, Pair)
