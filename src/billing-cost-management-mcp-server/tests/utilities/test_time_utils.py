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

"""Unit tests for the time_utils module."""

import pytest
from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
    EPOCH_MILLISECONDS_THRESHOLD,
    _first_of_next_month,
    format_timestamp_to_utc_iso,
    monthly_period_note,
    normalize_datetimes_to_iso,
    timestamp_to_utc_iso_string,
)
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


class TestUtcDatetimeStringToEpochSeconds:
    """Tests for utc_datetime_string_to_epoch_seconds function."""

    def test_date_only_format(self):
        """Test conversion with date-only format YYYY-MM-DD."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            utc_datetime_string_to_epoch_seconds,
        )

        result = utc_datetime_string_to_epoch_seconds('2024-01-01')
        assert result == 1704067200  # 2024-01-01T00:00:00 UTC

    def test_datetime_format(self):
        """Test conversion with datetime format YYYY-MM-DDTHH:MM:SS."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            utc_datetime_string_to_epoch_seconds,
        )

        result = utc_datetime_string_to_epoch_seconds('2024-01-31T23:59:59')
        assert result == 1706745599  # 2024-01-31T23:59:59 UTC

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            utc_datetime_string_to_epoch_seconds,
        )

        with pytest.raises(ValueError, match='Invalid datetime format'):
            utc_datetime_string_to_epoch_seconds('not-a-date')


class TestEpochSecondsToUtcIsoStringDatetime:
    """Tests for timestamp_to_utc_iso_string with datetime inputs."""

    def test_datetime_with_timezone(self):
        """Test conversion with timezone-aware datetime."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            timestamp_to_utc_iso_string,
        )

        dt = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
        result = timestamp_to_utc_iso_string(dt)
        assert result == '2023-11-14T22:13:20'

    def test_datetime_without_timezone(self):
        """Test conversion with naive datetime (no timezone)."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            timestamp_to_utc_iso_string,
        )

        dt = datetime(2023, 11, 14, 22, 13, 20)
        result = timestamp_to_utc_iso_string(dt)
        assert result == '2023-11-14T22:13:20'


class TestEpochSecondsToUtcIsoString:
    """Tests for the timestamp_to_utc_iso_string function."""

    def test_known_timestamp(self):
        """Test conversion of a known epoch timestamp."""
        # 2023-11-14T22:13:20 UTC
        result = timestamp_to_utc_iso_string(1700000000)
        assert result == '2023-11-14T22:13:20'

    def test_unix_epoch_zero(self):
        """Test conversion of epoch zero (1970-01-01)."""
        result = timestamp_to_utc_iso_string(0)
        assert result == '1970-01-01T00:00:00'

    def test_float_timestamp(self):
        """Test conversion of a float timestamp with fractional seconds."""
        result = timestamp_to_utc_iso_string(1700000000.5)
        assert result == '2023-11-14T22:13:20.500000'

    def test_returns_string_without_timezone(self):
        """Test that the result does not contain timezone info."""
        result = timestamp_to_utc_iso_string(1700000000)
        assert '+' not in result
        assert 'Z' not in result

    def test_different_timestamps(self):
        """Test several different timestamps for correct formatting."""
        # 2023-11-15T10:00:00 UTC = 1700042400
        result = timestamp_to_utc_iso_string(1700042400)
        assert result == '2023-11-15T10:00:00'

        # 2025-01-01T00:00:00 UTC = 1735689600
        result = timestamp_to_utc_iso_string(1735689600)
        assert result == '2025-01-01T00:00:00'


class TestNormalizeDatetimesToIso:
    """Tests for normalize_datetimes_to_iso (recursive datetime walker)."""

    def test_scalar_datetime(self):
        """A bare datetime is converted to an ISO 8601 string."""
        dt = datetime(2026, 5, 1, tzinfo=timezone.utc)
        assert normalize_datetimes_to_iso(dt) == '2026-05-01T00:00:00'

    def test_nested_structure(self):
        """Datetimes are converted at any nesting depth; other values untouched."""
        obj = {
            'Name': 'Engineering',
            'LastModified': datetime(2026, 5, 1, tzinfo=timezone.utc),
            'Rule': {'LinkedAccounts': ['123456789012']},
            'Nested': {
                'EinvoiceDeliveryActivationDate': datetime(2026, 3, 1, tzinfo=timezone.utc),
            },
            'Items': [
                {'CreateDate': datetime(2026, 1, 1, tzinfo=timezone.utc)},
                {'CreateDate': datetime(2026, 2, 1, tzinfo=timezone.utc)},
            ],
        }
        result = normalize_datetimes_to_iso(obj)
        assert result['LastModified'] == '2026-05-01T00:00:00'
        assert result['Nested']['EinvoiceDeliveryActivationDate'] == '2026-03-01T00:00:00'
        assert result['Items'][0]['CreateDate'] == '2026-01-01T00:00:00'
        assert result['Items'][1]['CreateDate'] == '2026-02-01T00:00:00'
        assert result['Name'] == 'Engineering'
        assert result['Rule']['LinkedAccounts'] == ['123456789012']

    def test_no_datetimes_unchanged(self):
        """A structure with no datetimes is returned unchanged."""
        obj = {'a': 1, 'b': ['x', 'y'], 'c': {'d': True}}
        assert normalize_datetimes_to_iso(obj) == obj

    def test_scalar_passthrough(self):
        """Non-datetime scalars pass through untouched."""
        assert normalize_datetimes_to_iso('hello') == 'hello'
        assert normalize_datetimes_to_iso(42) == 42
        assert normalize_datetimes_to_iso(None) is None


class TestFormatTimestampToUtcIso:
    """Tests for format_timestamp_to_utc_iso (datetime, epoch seconds, epoch ms)."""

    # 2021-09-28T10:40:00Z in each wire form.
    EXPECTED = '2021-09-28T10:40:00'
    EPOCH_SECONDS = 1632825600
    EPOCH_MS = 1632825600000

    def test_none_returns_none(self):
        """A missing timestamp is None, not an error string."""
        assert format_timestamp_to_utc_iso(None) is None

    def test_naive_datetime_is_taken_as_utc(self):
        """boto3-style naive datetime is formatted as-is (UTC)."""
        assert format_timestamp_to_utc_iso(datetime(2021, 9, 28, 10, 40)) == self.EXPECTED

    def test_aware_datetime_is_converted_to_utc(self):
        """An aware datetime in another zone is converted to UTC."""
        eastern = timezone(timedelta(hours=-4))
        value = datetime(2021, 9, 28, 6, 40, tzinfo=eastern)
        assert format_timestamp_to_utc_iso(value) == self.EXPECTED

    def test_epoch_seconds(self):
        """Epoch seconds (the AWS JSON wire form) are not divided by 1000."""
        assert format_timestamp_to_utc_iso(self.EPOCH_SECONDS) == self.EXPECTED

    def test_epoch_seconds_float(self):
        """Fractional epoch seconds keep their sub-second part."""
        assert format_timestamp_to_utc_iso(1632825600.5) == '2021-09-28T10:40:00.500000'

    def test_epoch_milliseconds(self):
        """Epoch milliseconds are recognized by magnitude."""
        assert format_timestamp_to_utc_iso(self.EPOCH_MS) == self.EXPECTED

    def test_threshold_boundary(self):
        """Values at the threshold are seconds; values above are milliseconds."""
        at = format_timestamp_to_utc_iso(EPOCH_MILLISECONDS_THRESHOLD)
        assert at is not None and at.startswith('5138-')
        above = format_timestamp_to_utc_iso(EPOCH_MILLISECONDS_THRESHOLD + 1)
        assert above is not None and above.startswith('1973-')

    def test_epoch_zero_is_a_value(self):
        """Epoch 0 is a real instant, not a missing value."""
        assert format_timestamp_to_utc_iso(0) == '1970-01-01T00:00:00'

    @pytest.mark.parametrize(
        'value',
        ['1632825600', '1632825600000', '2021-09-28T10:40:00Z', '2021-09-28T10:40:00+00:00'],
    )
    def test_strings(self, value):
        """Numeric and ISO 8601 strings are accepted."""
        assert format_timestamp_to_utc_iso(value) == self.EXPECTED

    @pytest.mark.parametrize(
        'value', ['not a timestamp', '', True, float('nan'), float('inf'), 1e20, [1], {}]
    )
    def test_unconvertible_returns_none_and_logs(self, value):
        """Unconvertible input returns None and logs; no error text in the value."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.time_utils.logger'
        ) as mock_logger:
            assert format_timestamp_to_utc_iso(value) is None
        mock_logger.warning.assert_called_once()


class TestMonthlyPeriodNote:
    """Tests for monthly_period_note."""

    def test_no_periods_returns_empty(self):
        """No entries, no note."""
        assert monthly_period_note('2026-01-24', '2026-03-10', []) == {}

    def test_periods_matching_request_return_empty(self):
        """Labels within the request need no note."""
        periods = [
            {'Start': '2026-01-24', 'End': '2026-02-01'},
            {'Start': '2026-02-01', 'End': '2026-03-10'},
        ]
        assert monthly_period_note('2026-01-24', '2026-03-10', periods) == {}

    def test_current_month_label_ending_before_request_caps_the_covered_range(self):
        """In the data lag the last label ends at the first day without data, before end."""
        # A MONTHLY GetSavingsPlansUtilization request for 2026-09-20 to 2026-10-28, sent on
        # 2026-10-28: October is labelled up to 2026-10-27, the first day without data.
        periods = [
            {'Start': '2026-09-01', 'End': '2026-10-01'},
            {'Start': '2026-10-01', 'End': '2026-10-27'},
        ]
        note = monthly_period_note('2026-09-20', '2026-10-28', periods, 'MONTHLY')['period_note']
        assert 'first entry, labelled 2026-09-01 to 2026-10-01, covers only 2026-09-20' in note
        assert 'last entry' not in note
        assert 'cover 2026-09-20 to 2026-10-27 (end exclusive) only' in note
        assert 'cover 2026-09-20 to 2026-10-28' not in note
        assert 'Data from 2026-10-27 is not available yet and is not included.' in note
        assert "whole calendar month (the current month's ends at the first day without data)" in (
            note
        )

    def test_single_current_month_entry_in_the_data_lag(self):
        """One snapped entry that also stops at the first day without data."""
        periods = [{'Start': '2026-10-01', 'End': '2026-10-27'}]
        note = monthly_period_note('2026-10-05', '2026-10-28', periods, 'MONTHLY')['period_note']
        assert 'entry labelled 2026-10-01 to 2026-10-27 covers only 2026-10-05 to 2026-10-27.' in (
            note
        )
        assert 'cover 2026-10-05 to 2026-10-27 (end exclusive) only' in note
        assert '2026-10-28' not in note

    def test_data_lag_alone_gets_a_note(self):
        """A request from the 1st whose current-month label stops early still gets a note."""
        periods = [
            {'Start': '2026-08-01', 'End': '2026-09-01'},
            {'Start': '2026-09-01', 'End': '2026-10-01'},
            {'Start': '2026-10-01', 'End': '2026-10-27'},
        ]
        note = monthly_period_note('2026-08-01', '2026-10-28', periods, 'MONTHLY')['period_note']
        assert 'Data from 2026-10-27 is not available yet and is not included.' in note
        assert 'Report the last month as partial' in note
        assert 'cover 2026-08-01 to 2026-10-27 (end exclusive) only' in note
        assert 'first entry' not in note
        assert 'whole calendar month, but the figures cover only the requested days' not in note

    def test_single_current_month_entry_in_the_data_lag_without_snapping(self):
        """One entry from the 1st, stopped by the data lag."""
        periods = [{'Start': '2026-10-01', 'End': '2026-10-27'}]
        note = monthly_period_note('2026-10-01', '2026-10-28', periods, 'MONTHLY')['period_note']
        assert 'Data from 2026-10-27 is not available yet and is not included.' in note
        assert 'cover 2026-10-01 to 2026-10-27 (end exclusive) only' in note

    def test_whole_month_last_label_before_the_request_end_is_not_the_data_lag(self):
        """A last label that ends on a month boundary is a past month, not the data lag."""
        periods = [{'Start': '2026-09-01', 'End': '2026-10-01'}]
        assert monthly_period_note('2026-09-01', '2026-10-28', periods, 'MONTHLY') == {}
        note = monthly_period_note('2026-09-20', '2026-10-28', periods, 'MONTHLY')['period_note']
        assert 'not available yet' not in note

    def test_daily_entries_ending_in_the_lag_get_no_note(self):
        """DAILY entries end inside their month too; only MONTHLY labels mark the data lag."""
        periods = [
            {'Start': '2026-10-25', 'End': '2026-10-26'},
            {'Start': '2026-10-26', 'End': '2026-10-27'},
        ]
        assert monthly_period_note('2026-10-25', '2026-10-28', periods, 'DAILY') == {}
        assert monthly_period_note('2026-10-25', '2026-10-28', periods) == {}

    def test_data_lag_in_december_rolls_over_the_year(self):
        """The month-end check handles December."""
        periods = [{'Start': '2026-12-01', 'End': '2026-12-27'}]
        note = monthly_period_note('2026-12-01', '2026-12-29', periods, 'monthly')['period_note']
        assert 'Data from 2026-12-27 is not available yet and is not included.' in note
        assert _first_of_next_month('2026-12-15') == '2027-01-01'
        assert _first_of_next_month('2026-01-31') == '2026-02-01'
        # A past December ends on 2027-01-01, the boundary, so it is not the lag.
        past = [{'Start': '2026-12-01', 'End': '2027-01-01'}]
        assert monthly_period_note('2026-12-01', '2027-01-10', past, 'MONTHLY') == {}

    def test_missing_start_or_end_is_not_the_data_lag(self):
        """A last entry without Start or End falls back to the requested end."""
        for last in ({'End': '2026-10-27'}, {'Start': '2026-10-01'}, None):
            periods = [{'Start': '2026-09-01', 'End': '2026-10-01'}, last]
            note = monthly_period_note('2026-09-20', '2026-10-28', periods, 'MONTHLY')
            assert 'not available yet' not in note['period_note']
            assert 'cover 2026-09-20 to 2026-10-28 (end exclusive) only' in note['period_note']

    def test_label_reaching_the_requested_end_adds_no_data_lag_sentence(self):
        """When the data reaches the requested end, the range is the request, with no lag text."""
        periods = [
            {'Start': '2026-01-01', 'End': '2026-02-01'},
            {'Start': '2026-02-01', 'End': '2026-03-01'},
        ]
        note = monthly_period_note('2026-01-24', '2026-03-01', periods)['period_note']
        assert 'cover 2026-01-24 to 2026-03-01 (end exclusive) only' in note
        assert 'not available yet' not in note

    def test_start_snapped_only(self):
        """Only the first entry is flagged when only the start is snapped."""
        periods = [
            {'Start': '2026-01-01', 'End': '2026-02-01'},
            {'Start': '2026-02-01', 'End': '2026-03-01'},
        ]
        note = monthly_period_note('2026-01-24', '2026-03-01', periods)['period_note']
        assert 'first entry, labelled 2026-01-01 to 2026-02-01, covers only 2026-01-24' in note
        assert 'last entry' not in note

    def test_end_snapped_only(self):
        """Only the last entry is flagged when only the end is snapped."""
        periods = [
            {'Start': '2026-01-01', 'End': '2026-02-01'},
            {'Start': '2026-02-01', 'End': '2026-03-01'},
        ]
        note = monthly_period_note('2026-01-01', '2026-02-10', periods)['period_note']
        assert (
            'last entry, labelled 2026-02-01 to 2026-03-01, covers only the days before 2026-02-10'
            in note
        )
        assert 'first entry' not in note

    def test_single_entry_snapped_at_both_ends(self):
        """One entry snapped at both ends is described once."""
        periods = [{'Start': '2026-01-01', 'End': '2026-02-01'}]
        note = monthly_period_note('2026-01-05', '2026-01-15', periods)['period_note']
        assert (
            'entry labelled 2026-01-01 to 2026-02-01 covers only 2026-01-05 to 2026-01-15' in note
        )

    def test_missing_first_label_still_flags_snapped_last_entry(self):
        """A first entry without a TimePeriod does not hide a snapped last entry."""
        periods = [None, {'Start': '2026-02-01', 'End': '2026-03-01'}]
        note = monthly_period_note('2026-01-24', '2026-02-10', periods)['period_note']
        assert 'last entry, labelled 2026-02-01 to 2026-03-01' in note
        assert 'first entry' not in note

    def test_missing_labels_return_empty(self):
        """Entries without a TimePeriod are not flagged."""
        assert monthly_period_note('2026-01-24', '2026-03-10', [None, {}]) == {}
