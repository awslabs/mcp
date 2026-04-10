"""
Unit tests for the time_utils module.
"""

import datetime
import unittest

from awslabs.ecs_mcp_server.utils.time_utils import calculate_time_window, _ensure_datetime


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

    # -- Tests for string-to-datetime coercion (issue #2858) --

    def test_string_end_time_with_z_suffix(self):
        """Test that an ISO-8601 string end_time with Z suffix is parsed correctly."""
        start_time, end_time = calculate_time_window(
            time_window=3600,
            end_time="2026-04-03T12:00:00Z",
        )
        self.assertEqual(end_time, datetime.datetime(2026, 4, 3, 12, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual((end_time - start_time).total_seconds(), 3600)

    def test_string_start_time_and_end_time(self):
        """Test that both start_time and end_time as strings are parsed correctly."""
        start_time, end_time = calculate_time_window(
            start_time="2026-04-03T10:00:00Z",
            end_time="2026-04-03T12:00:00Z",
        )
        self.assertEqual(start_time, datetime.datetime(2026, 4, 3, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(end_time, datetime.datetime(2026, 4, 3, 12, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual((end_time - start_time).total_seconds(), 7200)

    def test_string_with_timezone_offset(self):
        """Test that an ISO-8601 string with explicit timezone offset is parsed correctly."""
        start_time, end_time = calculate_time_window(
            end_time="2026-04-03T14:00:00+02:00",
        )
        # +02:00 means 12:00 UTC
        self.assertEqual(end_time.utcoffset(), datetime.timedelta(hours=2))
        self.assertEqual(end_time.hour, 14)

    def test_string_start_time_only(self):
        """Test that a string start_time without end_time works (end defaults to now)."""
        start_time, end_time = calculate_time_window(
            start_time="2026-01-01T00:00:00Z",
        )
        self.assertEqual(start_time, datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc))
        # end_time should be approximately now
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(abs((end_time - now).total_seconds()) < 5)

    def test_ensure_datetime_none(self):
        """Test that _ensure_datetime returns None for None input."""
        self.assertIsNone(_ensure_datetime(None))

    def test_ensure_datetime_passthrough(self):
        """Test that _ensure_datetime passes through datetime objects unchanged."""
        dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        self.assertEqual(_ensure_datetime(dt), dt)

    def test_ensure_datetime_string(self):
        """Test that _ensure_datetime parses ISO-8601 strings."""
        result = _ensure_datetime("2026-04-03T12:00:00Z")
        self.assertEqual(result, datetime.datetime(2026, 4, 3, 12, 0, 0, tzinfo=datetime.timezone.utc))
