"""
Unit tests for the cache utility.
"""

import time
import unittest

from bedrock_advisor.utils.cache import SimpleCache


class TestSimpleCache(unittest.TestCase):
    """Test cases for the SimpleCache class."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = SimpleCache(ttl_seconds=0.1)  # 100ms TTL for faster testing

    def test_put_and_get(self):
        """Test putting and getting items from the cache."""
        # Put items in the cache
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")

        # Get items from the cache
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertEqual(self.cache.get("key2"), "value2")

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        # Put an item in the cache
        self.cache.put("key1", "value1")

        # Verify it's in the cache
        self.assertEqual(self.cache.get("key1"), "value1")

        # Wait for TTL to expire
        time.sleep(0.2)

        # Verify it's expired
        self.assertIsNone(self.cache.get("key1"))

    def test_clear(self):
        """Test clearing the cache."""
        # Put items in the cache
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")

        # Clear the cache
        self.cache.clear()

        # Verify all items are removed
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    def test_get_all(self):
        """Test getting all items from the cache."""
        # Put items in the cache
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")

        # Get all items
        all_items = self.cache.get_all()

        # Verify all items are returned
        self.assertEqual(len(all_items), 2)
        self.assertIn("value1", all_items)
        self.assertIn("value2", all_items)

    def test_get_all_with_expired_items(self):
        """Test getting all items with some expired items."""
        # Put items in the cache
        self.cache.put("key1", "value1")

        # Wait for TTL to expire
        time.sleep(0.2)

        # Put another item in the cache
        self.cache.put("key2", "value2")

        # Get all items
        all_items = self.cache.get_all()

        # Verify only non-expired items are returned
        self.assertEqual(len(all_items), 1)
        self.assertIn("value2", all_items)
        self.assertNotIn("value1", all_items)

    def test_get_stats(self):
        """Test getting cache statistics."""
        # Put items in the cache
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")

        # Get items (hits)
        self.cache.get("key1")
        self.cache.get("key2")

        # Get non-existent item (miss)
        self.cache.get("key3")

        # Get stats
        stats = self.cache.get_stats()

        # Verify stats
        self.assertEqual(stats["size"], 2)
        self.assertEqual(stats["ttl_seconds"], 0.1)
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 2/3)


if __name__ == "__main__":
    unittest.main()
