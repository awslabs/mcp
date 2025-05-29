"""
Unit tests for the time_utils module.
"""

import datetime
import unittest

from awslabs.ecs_mcp_server.utils.time_utils import calculate_time_window


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
