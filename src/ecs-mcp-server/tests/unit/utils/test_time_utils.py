"""
Unit tests for the time_utils module.
"""

import datetime
import unittest

from awslabs.ecs_mcp_server.utils.time_utils import _ensure_datetime, calculate_time_window


class TestTimeUtils(unittest.TestCase):
    """Unit tests for the time_utils module."""

    def test_default_time_window(self):
        """Test with default parameters."""
        start_time, end_time = calculate_time_window()
        self.assertIsNotNone(start_time)
        self.assertIsNotNone(end_time)
        self.assertEqual((end_time - start_time).total_seconds(), 3600)

    def test_explicit_start_time(self):
        """Test with explicit start_time parameter."""
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now - datetime.timedelta(hours=2)
        start_time, end_time = calculate_time_window(start_time=start)
        self.assertEqual(start_time, start)
        self.assertTrue((end_time - now).total_seconds() < 5)  # Within 5 seconds of now

    def test_explicit_end_time(self):
        """Test with explicit end_time parameter."""
        end = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        start_time, end_time = calculate_time_window(end_time=end)
        self.assertEqual(end_time, end)
        self.assertEqual((end_time - start_time).total_seconds(), 3600)

    def test_both_times_specified(self):
        """Test with both start_time and end_time specified."""
        start = datetime.datetime(2025, 5, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2025, 5, 2, tzinfo=datetime.timezone.utc)
        start_time, end_time = calculate_time_window(start_time=start, end_time=end)
        self.assertEqual(start_time, start)
        self.assertEqual(end_time, end)

    def test_timezone_handling(self):
        """Test handling of timezone-naive datetime objects."""
        naive_start = datetime.datetime(2025, 5, 1)
        naive_end = datetime.datetime(2025, 5, 2)
        start_time, end_time = calculate_time_window(start_time=naive_start, end_time=naive_end)
        self.assertIsNotNone(start_time.tzinfo)
        self.assertIsNotNone(end_time.tzinfo)
        self.assertEqual(start_time.day, naive_start.day)
        self.assertEqual(end_time.day, naive_end.day)

    def test_custom_time_window(self):
        """Test with custom time window."""
        # Using a 2-hour window (7200 seconds)
        start_time, end_time = calculate_time_window(time_window=7200)
        self.assertIsNotNone(start_time)
        self.assertIsNotNone(end_time)
        self.assertEqual((end_time - start_time).total_seconds(), 7200)

    def test_string_start_and_end_time_iso8601_z_suffix(self):
        """Strings with a 'Z' UTC suffix (as MCP serializes them) are accepted.

        MCP serializes all tool arguments as JSON, so start_time/end_time always
        arrive as ISO-8601 strings rather than datetime objects. See issue #2858.
        """
        start_time, end_time = calculate_time_window(
            start_time="2026-04-03T12:00:00Z",
            end_time="2026-04-03T13:00:00Z",
        )
        self.assertEqual(
            start_time, datetime.datetime(2026, 4, 3, 12, 0, tzinfo=datetime.timezone.utc)
        )
        self.assertEqual(
            end_time, datetime.datetime(2026, 4, 3, 13, 0, tzinfo=datetime.timezone.utc)
        )

    def test_string_time_explicit_utc_offset(self):
        """Strings with an explicit +00:00 offset are accepted."""
        start_time, end_time = calculate_time_window(
            start_time="2026-04-03T12:00:00+00:00",
            end_time="2026-04-03T13:00:00+00:00",
        )
        self.assertEqual(
            start_time, datetime.datetime(2026, 4, 3, 12, 0, tzinfo=datetime.timezone.utc)
        )
        self.assertEqual(
            end_time, datetime.datetime(2026, 4, 3, 13, 0, tzinfo=datetime.timezone.utc)
        )

    def test_string_time_naive_coerced_to_utc(self):
        """Naive strings (no tz) are coerced to UTC, matching datetime handling."""
        start_time, end_time = calculate_time_window(
            start_time="2026-04-03T12:00:00",
            end_time="2026-04-03T13:00:00",
        )
        # Same convention as test_timezone_handling for naive datetime objects.
        self.assertEqual(start_time.tzinfo, datetime.timezone.utc)
        self.assertEqual(end_time.tzinfo, datetime.timezone.utc)
        self.assertEqual(
            start_time, datetime.datetime(2026, 4, 3, 12, 0, tzinfo=datetime.timezone.utc)
        )
        self.assertEqual(
            end_time, datetime.datetime(2026, 4, 3, 13, 0, tzinfo=datetime.timezone.utc)
        )

    def test_string_start_time_only(self):
        """A string start_time alone is parsed; end_time defaults to ~now."""
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now - datetime.timedelta(hours=2)
        start_time, end_time = calculate_time_window(start_time=start.isoformat())
        self.assertEqual(start_time, start)
        self.assertTrue((end_time - now).total_seconds() < 5)  # Within 5 seconds of now

    def test_string_end_time_only(self):
        """A string end_time alone is parsed; start_time derives from time_window."""
        end = datetime.datetime(2026, 4, 3, 13, 0, tzinfo=datetime.timezone.utc)
        start_time, end_time = calculate_time_window(end_time=end.isoformat())
        self.assertEqual(end_time, end)
        self.assertEqual((end_time - start_time).total_seconds(), 3600)

    def test_malformed_string_raises_value_error(self):
        """A malformed datetime string raises a clear ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calculate_time_window(start_time="not-a-date")
        self.assertIn("not-a-date", str(ctx.exception))

    def test_datetime_objects_still_work_regression(self):
        """Regression: datetime objects continue to pass through unchanged."""
        start = datetime.datetime(2025, 5, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2025, 5, 2, tzinfo=datetime.timezone.utc)
        start_time, end_time = calculate_time_window(start_time=start, end_time=end)
        self.assertEqual(start_time, start)
        self.assertEqual(end_time, end)

    def test_ensure_datetime_passthrough_and_none(self):
        """_ensure_datetime returns None for None and passes datetime through."""
        self.assertIsNone(_ensure_datetime(None))
        dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        self.assertIs(_ensure_datetime(dt), dt)

    def test_ensure_datetime_rejects_unsupported_type(self):
        """_ensure_datetime raises ValueError for a non-str, non-datetime value."""
        with self.assertRaises(ValueError) as ctx:
            _ensure_datetime(1234567890)  # e.g. an epoch int is not supported
        self.assertIn("int", str(ctx.exception))
