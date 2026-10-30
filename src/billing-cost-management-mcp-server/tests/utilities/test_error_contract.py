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

"""Tests for the error_type -> retry_strategy mapping."""

import pytest
from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
    format_response,
)
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
    _ERROR_TYPE_GUIDANCE,
    _ERROR_TYPE_PREFIX_GUIDANCE,
    DO_NOT_RETRY,
    MODIFY_REQUEST,
    RETRY_SAME_REQUEST,
    add_retry_guidance,
    classify_error,
    combine_guidance,
)


class TestClassifyError:
    """Tests for classify_error."""

    @pytest.mark.parametrize(
        'error_type',
        [
            'ThrottlingException',
            'Throttling',
            'TooManyRequestsException',
            'LimitExceededException',
            'throttling_error',
        ],
    )
    def test_throttling_is_retried(self, error_type):
        """Throttling codes are transient."""
        strategy, hint = classify_error(error_type)
        assert strategy == RETRY_SAME_REQUEST
        assert hint is not None

    @pytest.mark.parametrize(
        'error_type',
        [
            'aws_connection_error',
            'InternalServerException',
            'InternalErrorException',
            'ServiceUnavailable',
            'service_unavailable',
            'unknown_timeouterror',
        ],
    )
    def test_connection_and_server_errors_are_retried(self, error_type):
        """Connection failures and server-side errors are transient."""
        assert classify_error(error_type)[0] == RETRY_SAME_REQUEST

    def test_unmapped_5xx_is_retried(self):
        """An unmapped code with a 5xx status is transient."""
        assert classify_error('SomeNewServiceError', http_status=503)[0] == RETRY_SAME_REQUEST

    def test_unmapped_4xx_is_not_retried(self):
        """An unmapped code with a 4xx status gets the default."""
        assert classify_error('SomeNewClientError', http_status=400) == (DO_NOT_RETRY, None)

    def test_mapped_code_wins_over_5xx(self):
        """The error_type mapping takes precedence over the HTTP status."""
        assert classify_error('AccessDeniedException', http_status=500)[0] == DO_NOT_RETRY

    @pytest.mark.parametrize(
        'error_type',
        [
            'validation_error',
            'ValidationException',
            'invalid_operation',
            'InvalidParameterValue',
            'InvalidParameterCombination',
            'InvalidRequestException',
            'ExpiredNextTokenException',
        ],
    )
    def test_validation_requires_modified_request(self, error_type):
        """Invalid arguments must change before retrying, including the InvalidParameter* family."""
        assert classify_error(error_type)[0] == MODIFY_REQUEST

    @pytest.mark.parametrize(
        'error_type', ['InvalidNextTokenException', 'ExpiredNextTokenException']
    )
    def test_service_next_token_codes_share_invalid_next_token_guidance(self, error_type):
        """A token the service rejects gets the restart-without-next_token hint."""
        assert classify_error(error_type) == classify_error('invalid_next_token')

    @pytest.mark.parametrize(
        'error_type',
        ['AccessDenied', 'AccessDeniedException', 'access_denied', 'UnauthorizedOperation'],
    )
    def test_access_denied_is_not_retried(self, error_type):
        """Permission failures cannot be fixed during the run, including the AccessDenied* family."""
        strategy, hint = classify_error(error_type)
        assert strategy == DO_NOT_RETRY
        assert hint is not None

    @pytest.mark.parametrize(
        'error_type', ['OptInRequiredException', 'opt_in_required', 'DataUnavailableException']
    )
    def test_account_state_is_not_retried(self, error_type):
        """Opt-in and data availability failures cannot be fixed during the run."""
        assert classify_error(error_type)[0] == DO_NOT_RETRY

    def test_data_unavailable_hint_says_no_data_not_failure(self):
        """DataUnavailableException tells the caller there is no data, and the usual causes."""
        strategy, hint = classify_error('DataUnavailableException')
        assert strategy == DO_NOT_RETRY
        assert hint is not None
        assert 'The service has no data for this request' in hint
        assert 'too recent to have been processed yet' in hint
        assert 'a filter value that matches nothing' in hint
        assert 'not a failure and not a zero' in hint

    def test_data_unavailable_hint_is_service_neutral(self):
        """Pricing Calculator raises the same code, so the hint names no Cost Explorer report."""
        hint = classify_error('DataUnavailableException')[1] or ''
        for specific in ('Savings Plans', 'Reserved Instance', '2-3 days'):
            assert specific not in hint

    @pytest.mark.parametrize(
        'error_type, guidance',
        [*_ERROR_TYPE_GUIDANCE.items(), *_ERROR_TYPE_PREFIX_GUIDANCE],
    )
    def test_every_mapped_error_type_has_a_hint(self, error_type, guidance):
        """A mapped error type always carries recovery guidance, not just a strategy.

        Hints are keyed by error_type, so each must hold for every service that raises it.
        """
        assert guidance[1], f'{error_type} is mapped without a hint'

    @pytest.mark.parametrize(
        'error_type',
        [
            'no_results',
            'ResourceNotFoundException',
            'resource_not_found',
            'NotFoundException',
            'not_found',
        ],
    )
    def test_not_found_requires_modified_request(self, error_type):
        """Nothing matched, so the request must change."""
        assert classify_error(error_type)[0] == MODIFY_REQUEST

    @pytest.mark.parametrize('error_type', [None, '', 'unknown_keyerror', 'multi_region_error'])
    def test_missing_or_unknown_defaults_to_do_not_retry(self, error_type):
        """Missing and unrecognized types get the conservative default with no hint."""
        assert classify_error(error_type) == (DO_NOT_RETRY, None)


class TestCombineGuidance:
    """Tests for combine_guidance."""

    def test_identical_guidance_keeps_hint(self):
        """Failures with the same guidance keep its hint."""
        throttled = classify_error('ThrottlingException')
        assert combine_guidance([throttled, throttled]) == throttled

    def test_transient_mix_is_retried_without_hint(self):
        """Throttling plus a 5xx is still transient, with no single hint."""
        guidance = [classify_error('ThrottlingException'), classify_error('X', http_status=503)]
        assert combine_guidance(guidance) == (RETRY_SAME_REQUEST, None)

    def test_transient_wins_over_modify(self):
        """A throttled region may still hold the result, so retrying is right."""
        guidance = [
            classify_error('ThrottlingException'),
            classify_error('ResourceNotFoundException'),
        ]
        assert combine_guidance(guidance) == (RETRY_SAME_REQUEST, None)

    def test_do_not_retry_wins(self):
        """Any failure that cannot succeed during this run makes the whole not retryable."""
        guidance = [classify_error('ThrottlingException'), classify_error('AccessDeniedException')]
        assert combine_guidance(guidance) == (DO_NOT_RETRY, None)

    def test_empty_gets_default(self):
        """No failures gets the conservative default."""
        assert combine_guidance([]) == (DO_NOT_RETRY, None)

    def test_non_int_http_status_ignored(self):
        """A malformed http_status does not raise."""
        assert classify_error(None, http_status='500') == (DO_NOT_RETRY, None)  # type: ignore[arg-type]


class TestAddRetryGuidance:
    """Tests for add_retry_guidance."""

    def test_adds_strategy_and_hint(self):
        """Fills in both fields from the mapping, leaving the input unchanged."""
        response = {'status': 'error', 'error_type': 'ThrottlingException'}

        enriched = add_retry_guidance(response)

        assert enriched['retry_strategy'] == RETRY_SAME_REQUEST
        assert enriched['hint']
        assert 'retry_strategy' not in response

    def test_omits_hint_when_none_applies(self):
        """No hint key is added for the default."""
        enriched = add_retry_guidance({'status': 'error'})

        assert enriched['retry_strategy'] == DO_NOT_RETRY
        assert 'hint' not in enriched

    def test_uses_http_status_from_response(self):
        """The http_status that handle_aws_error sets feeds the 5xx rule."""
        enriched = add_retry_guidance(
            {'status': 'error', 'error_type': 'SomeNewServiceError', 'http_status': 502}
        )

        assert enriched['retry_strategy'] == RETRY_SAME_REQUEST

    def test_explicit_strategy_is_kept_without_mapped_hint(self):
        """An override is returned untouched; a mapped hint could contradict it."""
        response = {
            'status': 'error',
            'error_type': 'validation_error',
            'retry_strategy': DO_NOT_RETRY,
        }

        assert add_retry_guidance(response) is response

    def test_explicit_hint_is_kept(self):
        """A tool-set hint survives while the strategy is still derived."""
        enriched = add_retry_guidance(
            {'status': 'error', 'error_type': 'validation_error', 'hint': 'Use YYYY-MM-DD.'}
        )

        assert enriched['retry_strategy'] == MODIFY_REQUEST
        assert enriched['hint'] == 'Use YYYY-MM-DD.'


class TestFormatResponseOverrides:
    """Tests for the retry_strategy / hint kwargs on format_response."""

    def test_overrides_added_when_supplied(self):
        """Both kwargs land at the top level."""
        response = format_response(
            'error',
            {},
            'Region not supported',
            error_type='validation_error',
            retry_strategy=DO_NOT_RETRY,
            hint='Ask the user to pick a supported region.',
        )

        assert response['retry_strategy'] == DO_NOT_RETRY
        assert response['hint'] == 'Ask the user to pick a supported region.'

    def test_shape_unchanged_when_omitted(self):
        """Existing callers keep the same shape."""
        response = format_response('error', {}, 'boom', error_type='validation_error')

        assert 'retry_strategy' not in response
        assert 'hint' not in response


class TestSdkStandardRetryableCodes:
    """Codes the AWS SDKs' standard retry mode lists as transient or throttling."""

    @pytest.mark.parametrize(
        'error_type',
        [
            'InternalError',
            'IDPCommunicationError',
            'PriorRequestNotComplete',
            'RequestThrottled',
            'RequestThrottledException',
            'ProvisionedThroughputExceededException',
            'TransactionInProgressException',
            'EC2ThrottledException',
            'SlowDown',
            'BandwidthLimitExceeded',
        ],
    )
    def test_retry_same_request(self, error_type):
        """These arrive with a 4xx status too, so they need an explicit mapping."""
        assert classify_error(error_type, 400)[0] == RETRY_SAME_REQUEST
