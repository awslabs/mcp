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

"""Unit tests for pagination functionality."""

import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    CursorBasedPaginationToken,
    GenomicsFile,
    GenomicsFileType,
    GlobalContinuationToken,
    PaginationCacheEntry,
    PaginationMetrics,
    StoragePaginationRequest,
    StoragePaginationResponse,
)
from datetime import datetime


class TestStoragePaginationRequest:
    """Test cases for StoragePaginationRequest."""

    def test_valid_request(self):
        """Test valid pagination request creation."""
        request = StoragePaginationRequest(
            max_results=100, continuation_token='token123', buffer_size=500
        )

        assert request.max_results == 100
        assert request.continuation_token == 'token123'
        assert request.buffer_size == 500

    def test_default_values(self):
        """Test default values for pagination request."""
        request = StoragePaginationRequest()

        assert request.max_results == 100
        assert request.continuation_token is None
        assert request.buffer_size == 500

    def test_buffer_size_adjustment(self):
        """Test automatic buffer size adjustment."""
        # Buffer size should be adjusted if too small
        request = StoragePaginationRequest(max_results=1000, buffer_size=100)
        assert request.buffer_size >= request.max_results * 2

    def test_validation_errors(self):
        """Test validation errors for invalid parameters."""
        # Test max_results <= 0
        with pytest.raises(ValueError, match='max_results must be greater than 0'):
            StoragePaginationRequest(max_results=0)

        with pytest.raises(ValueError, match='max_results must be greater than 0'):
            StoragePaginationRequest(max_results=-1)

        # Test max_results too large
        with pytest.raises(ValueError, match='max_results cannot exceed 10000'):
            StoragePaginationRequest(max_results=10001)


class TestStoragePaginationResponse:
    """Test cases for StoragePaginationResponse."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_datetime = datetime(2023, 1, 1, 12, 0, 0)

    def create_test_file(self, path: str, file_type: GenomicsFileType) -> GenomicsFile:
        """Helper method to create test GenomicsFile objects."""
        return GenomicsFile(
            path=path,
            file_type=file_type,
            size_bytes=1000,
            storage_class='STANDARD',
            last_modified=self.base_datetime,
            tags={},
            source_system='s3',
            metadata={},
        )

    def test_response_creation(self):
        """Test pagination response creation."""
        files = [
            self.create_test_file('s3://bucket/file1.bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/file2.bam', GenomicsFileType.BAM),
        ]

        response = StoragePaginationResponse(
            results=files,
            next_continuation_token='next_token',
            has_more_results=True,
            total_scanned=100,
            buffer_overflow=False,
        )

        assert len(response.results) == 2
        assert response.next_continuation_token == 'next_token'
        assert response.has_more_results is True
        assert response.total_scanned == 100
        assert response.buffer_overflow is False

    def test_default_values(self):
        """Test default values for pagination response."""
        response = StoragePaginationResponse(results=[])

        assert response.results == []
        assert response.next_continuation_token is None
        assert response.has_more_results is False
        assert response.total_scanned == 0
        assert response.buffer_overflow is False


class TestGlobalContinuationToken:
    """Test cases for GlobalContinuationToken."""

    def test_token_creation(self):
        """Test continuation token creation."""
        token = GlobalContinuationToken(
            s3_tokens={'bucket1': 'token1', 'bucket2': 'token2'},
            healthomics_sequence_token='seq_token',
            healthomics_reference_token='ref_token',
            last_score_threshold=0.5,
            page_number=2,
            total_results_seen=150,
        )

        assert token.s3_tokens == {'bucket1': 'token1', 'bucket2': 'token2'}
        assert token.healthomics_sequence_token == 'seq_token'
        assert token.healthomics_reference_token == 'ref_token'
        assert token.last_score_threshold == 0.5
        assert token.page_number == 2
        assert token.total_results_seen == 150

    def test_default_values(self):
        """Test default values for continuation token."""
        token = GlobalContinuationToken()

        assert token.s3_tokens == {}
        assert token.healthomics_sequence_token is None
        assert token.healthomics_reference_token is None
        assert token.last_score_threshold is None
        assert token.page_number == 0
        assert token.total_results_seen == 0

    def test_encode_decode(self):
        """Test token encoding and decoding."""
        original_token = GlobalContinuationToken(
            s3_tokens={'bucket1': 'token1'},
            healthomics_sequence_token='seq_token',
            healthomics_reference_token='ref_token',
            last_score_threshold=0.75,
            page_number=3,
            total_results_seen=200,
        )

        # Encode token
        encoded = original_token.encode()
        assert isinstance(encoded, str)
        assert len(encoded) > 0

        # Decode token
        decoded_token = GlobalContinuationToken.decode(encoded)

        assert decoded_token.s3_tokens == original_token.s3_tokens
        assert (
            decoded_token.healthomics_sequence_token == original_token.healthomics_sequence_token
        )
        assert (
            decoded_token.healthomics_reference_token == original_token.healthomics_reference_token
        )
        assert decoded_token.last_score_threshold == original_token.last_score_threshold
        assert decoded_token.page_number == original_token.page_number
        assert decoded_token.total_results_seen == original_token.total_results_seen

    def test_encode_decode_empty_token(self):
        """Test encoding and decoding empty token."""
        empty_token = GlobalContinuationToken()

        encoded = empty_token.encode()
        decoded = GlobalContinuationToken.decode(encoded)

        assert decoded.s3_tokens == {}
        assert decoded.healthomics_sequence_token is None
        assert decoded.healthomics_reference_token is None
        assert decoded.page_number == 0

    def test_decode_invalid_token(self):
        """Test decoding invalid tokens."""
        # Test invalid base64
        with pytest.raises(ValueError, match='Invalid continuation token format'):
            GlobalContinuationToken.decode('invalid_base64!')

        # Test invalid JSON
        invalid_json = base64.b64encode(b'not_json').decode('utf-8')
        with pytest.raises(ValueError, match='Invalid continuation token format'):
            GlobalContinuationToken.decode(invalid_json)

        # Test missing required fields
        incomplete_data = {'s3_tokens': {}}
        json_str = json.dumps(incomplete_data)
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

        # Should not raise error, should use defaults
        decoded = GlobalContinuationToken.decode(encoded)
        assert decoded.page_number == 0  # Default value

    def test_is_empty(self):
        """Test empty token detection."""
        # Test empty token
        empty_token = GlobalContinuationToken()
        assert empty_token.is_empty() is True

        # Test token with S3 tokens
        token_with_s3 = GlobalContinuationToken(s3_tokens={'bucket': 'token'})
        assert token_with_s3.is_empty() is False

        # Test token with HealthOmics tokens
        token_with_ho = GlobalContinuationToken(healthomics_sequence_token='token')
        assert token_with_ho.is_empty() is False

        # Test token with page number only
        token_with_page = GlobalContinuationToken(page_number=1)
        assert token_with_page.is_empty() is False

    def test_has_more_pages(self):
        """Test more pages detection."""
        # Test empty token
        empty_token = GlobalContinuationToken()
        assert empty_token.has_more_pages() is False

        # Test token with S3 tokens
        token_with_s3 = GlobalContinuationToken(s3_tokens={'bucket': 'token'})
        assert token_with_s3.has_more_pages() is True

        # Test token with HealthOmics sequence token
        token_with_seq = GlobalContinuationToken(healthomics_sequence_token='token')
        assert token_with_seq.has_more_pages() is True

        # Test token with HealthOmics reference token
        token_with_ref = GlobalContinuationToken(healthomics_reference_token='token')
        assert token_with_ref.has_more_pages() is True


class TestCursorBasedPaginationToken:
    """Test cases for CursorBasedPaginationToken."""

    def test_token_creation(self):
        """Test cursor token creation."""
        token = CursorBasedPaginationToken(
            cursor_value='0.75',
            cursor_type='score',
            storage_cursors={'s3': 'cursor1', 'healthomics': 'cursor2'},
            page_size=50,
            total_seen=100,
        )

        assert token.cursor_value == '0.75'
        assert token.cursor_type == 'score'
        assert token.storage_cursors == {'s3': 'cursor1', 'healthomics': 'cursor2'}
        assert token.page_size == 50
        assert token.total_seen == 100

    def test_encode_decode(self):
        """Test cursor token encoding and decoding."""
        original_token = CursorBasedPaginationToken(
            cursor_value='2023-01-01T12:00:00Z',
            cursor_type='timestamp',
            storage_cursors={'s3': 'cursor1'},
            page_size=25,
            total_seen=75,
        )

        # Encode token
        encoded = original_token.encode()
        assert isinstance(encoded, str)
        assert encoded.startswith('cursor:')

        # Decode token
        decoded_token = CursorBasedPaginationToken.decode(encoded)

        assert decoded_token.cursor_value == original_token.cursor_value
        assert decoded_token.cursor_type == original_token.cursor_type
        assert decoded_token.storage_cursors == original_token.storage_cursors
        assert decoded_token.page_size == original_token.page_size
        assert decoded_token.total_seen == original_token.total_seen

    def test_decode_invalid_cursor_token(self):
        """Test decoding invalid cursor tokens."""
        # Test token without cursor prefix
        with pytest.raises(ValueError, match='Invalid cursor token format'):
            CursorBasedPaginationToken.decode('no_prefix_token')

        # Test invalid base64 after prefix
        with pytest.raises(ValueError, match='Invalid cursor token format'):
            CursorBasedPaginationToken.decode('cursor:invalid_base64!')

        # Test invalid JSON
        invalid_json = base64.b64encode(b'not_json').decode('utf-8')
        with pytest.raises(ValueError, match='Invalid cursor token format'):
            CursorBasedPaginationToken.decode(f'cursor:{invalid_json}')


class TestPaginationMetrics:
    """Test cases for PaginationMetrics."""

    def test_metrics_creation(self):
        """Test pagination metrics creation."""
        metrics = PaginationMetrics(
            page_number=2,
            total_results_fetched=50,
            total_objects_scanned=200,
            buffer_overflows=1,
            cache_hits=10,
            cache_misses=5,
            api_calls_made=8,
            search_duration_ms=1500,
            ranking_duration_ms=200,
            storage_fetch_duration_ms=1000,
        )

        assert metrics.page_number == 2
        assert metrics.total_results_fetched == 50
        assert metrics.total_objects_scanned == 200
        assert metrics.buffer_overflows == 1
        assert metrics.cache_hits == 10
        assert metrics.cache_misses == 5
        assert metrics.api_calls_made == 8
        assert metrics.search_duration_ms == 1500
        assert metrics.ranking_duration_ms == 200
        assert metrics.storage_fetch_duration_ms == 1000

    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = PaginationMetrics(
            page_number=1,
            total_results_fetched=25,
            total_objects_scanned=100,
            cache_hits=8,
            cache_misses=2,
        )

        metrics_dict = metrics.to_dict()

        assert metrics_dict['page_number'] == 1
        assert metrics_dict['total_results_fetched'] == 25
        assert metrics_dict['total_objects_scanned'] == 100
        assert metrics_dict['cache_hits'] == 8
        assert metrics_dict['cache_misses'] == 2

        # Test calculated fields
        assert 'efficiency_ratio' in metrics_dict
        assert 'cache_hit_ratio' in metrics_dict

        # Test efficiency ratio calculation
        expected_efficiency = 25 / 100  # results_fetched / objects_scanned
        assert abs(metrics_dict['efficiency_ratio'] - expected_efficiency) < 0.001

        # Test cache hit ratio calculation
        expected_cache_ratio = 8 / 10  # cache_hits / (cache_hits + cache_misses)
        assert abs(metrics_dict['cache_hit_ratio'] - expected_cache_ratio) < 0.001

    def test_metrics_edge_cases(self):
        """Test metrics edge cases."""
        # Test division by zero handling
        metrics = PaginationMetrics(
            total_results_fetched=10,
            total_objects_scanned=0,  # Division by zero case
            cache_hits=0,
            cache_misses=0,  # Division by zero case
        )

        metrics_dict = metrics.to_dict()

        # Should handle division by zero gracefully
        assert metrics_dict['efficiency_ratio'] == 10.0  # 10 / max(0, 1) = 10
        assert metrics_dict['cache_hit_ratio'] == 0.0  # 0 / max(0, 1) = 0


class TestPaginationCacheEntry:
    """Test cases for PaginationCacheEntry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_datetime = datetime(2023, 1, 1, 12, 0, 0)

    def create_test_file(self, path: str) -> GenomicsFile:
        """Helper method to create test GenomicsFile objects."""
        return GenomicsFile(
            path=path,
            file_type=GenomicsFileType.BAM,
            size_bytes=1000,
            storage_class='STANDARD',
            last_modified=self.base_datetime,
            tags={},
            source_system='s3',
            metadata={},
        )

    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        files = [
            self.create_test_file('s3://bucket/file1.bam'),
            self.create_test_file('s3://bucket/file2.bam'),
        ]

        metrics = PaginationMetrics(page_number=1, total_results_fetched=2)

        entry = PaginationCacheEntry(
            search_key='test_search',
            page_number=1,
            intermediate_results=files,
            score_threshold=0.5,
            storage_tokens={'bucket1': 'token1'},
            timestamp=1640995200.0,  # Fixed timestamp
            metrics=metrics,
        )

        assert entry.search_key == 'test_search'
        assert entry.page_number == 1
        assert len(entry.intermediate_results) == 2
        assert entry.score_threshold == 0.5
        assert entry.storage_tokens == {'bucket1': 'token1'}
        assert entry.timestamp == 1640995200.0
        assert entry.metrics == metrics

    def test_is_expired(self):
        """Test cache entry expiration."""
        import time

        # Create entry with current timestamp
        entry = PaginationCacheEntry(search_key='test', page_number=1, timestamp=time.time())

        # Should not be expired with large TTL
        assert entry.is_expired(3600) is False  # 1 hour TTL

        # Create entry with old timestamp
        old_entry = PaginationCacheEntry(
            search_key='test',
            page_number=1,
            timestamp=time.time() - 7200,  # 2 hours ago
        )

        # Should be expired with small TTL
        assert old_entry.is_expired(3600) is True  # 1 hour TTL

    def test_update_timestamp(self):
        """Test timestamp update."""
        import time

        entry = PaginationCacheEntry(
            search_key='test',
            page_number=1,
            timestamp=0.0,  # Old timestamp
        )

        # Update timestamp
        before_update = time.time()
        entry.update_timestamp()
        after_update = time.time()

        # Timestamp should be updated to current time
        assert before_update <= entry.timestamp <= after_update


class TestPaginationIntegration:
    """Integration tests for pagination components."""

    def test_token_roundtrip_consistency(self):
        """Test that tokens maintain consistency through encode/decode cycles."""
        # Test GlobalContinuationToken
        global_token = GlobalContinuationToken(
            s3_tokens={'bucket1': 'token1', 'bucket2': 'token2'},
            healthomics_sequence_token='seq_token',
            healthomics_reference_token='ref_token',
            last_score_threshold=0.85,
            page_number=5,
            total_results_seen=500,
        )

        # Multiple encode/decode cycles
        for _ in range(3):
            encoded = global_token.encode()
            global_token = GlobalContinuationToken.decode(encoded)

        # Values should remain consistent
        assert global_token.s3_tokens == {'bucket1': 'token1', 'bucket2': 'token2'}
        assert global_token.last_score_threshold == 0.85
        assert global_token.page_number == 5

        # Test CursorBasedPaginationToken
        cursor_token = CursorBasedPaginationToken(
            cursor_value='0.75',
            cursor_type='score',
            storage_cursors={'s3': 'cursor1', 'healthomics': 'cursor2'},
            page_size=100,
            total_seen=250,
        )

        # Multiple encode/decode cycles
        for _ in range(3):
            encoded = cursor_token.encode()
            cursor_token = CursorBasedPaginationToken.decode(encoded)

        # Values should remain consistent
        assert cursor_token.cursor_value == '0.75'
        assert cursor_token.cursor_type == 'score'
        assert cursor_token.page_size == 100
        assert cursor_token.total_seen == 250

    def test_pagination_state_transitions(self):
        """Test pagination state transitions."""
        # Start with empty token
        token = GlobalContinuationToken()
        assert token.is_empty() is True
        assert token.has_more_pages() is False

        # Add S3 token (simulating first page results)
        token.s3_tokens['bucket1'] = 'page1_token'
        token.page_number = 1
        token.total_results_seen = 50

        assert token.is_empty() is False
        assert token.has_more_pages() is True

        # Add HealthOmics tokens (simulating more results)
        token.healthomics_sequence_token = 'seq_page1_token'
        token.healthomics_reference_token = 'ref_page1_token'
        token.page_number = 2
        token.total_results_seen = 150

        assert token.has_more_pages() is True

        # Clear all tokens (simulating end of results)
        token.s3_tokens.clear()
        token.healthomics_sequence_token = None
        token.healthomics_reference_token = None

        assert token.has_more_pages() is False

    def test_pagination_metrics_accumulation(self):
        """Test pagination metrics accumulation across pages."""
        # Simulate metrics from multiple pages
        page1_metrics = PaginationMetrics(
            page_number=1,
            total_results_fetched=50,
            total_objects_scanned=200,
            api_calls_made=5,
            cache_hits=2,
            cache_misses=3,
        )

        page2_metrics = PaginationMetrics(
            page_number=2,
            total_results_fetched=30,
            total_objects_scanned=150,
            api_calls_made=3,
            cache_hits=4,
            cache_misses=1,
        )

        # Convert to dictionaries for easier comparison
        page1_dict = page1_metrics.to_dict()
        page2_dict = page2_metrics.to_dict()

        # Verify individual page metrics
        assert page1_dict['efficiency_ratio'] == 50 / 200  # 0.25
        assert page2_dict['efficiency_ratio'] == 30 / 150  # 0.2

        assert page1_dict['cache_hit_ratio'] == 2 / 5  # 0.4
        assert page2_dict['cache_hit_ratio'] == 4 / 5  # 0.8

        # Simulate accumulated metrics
        total_results = page1_metrics.total_results_fetched + page2_metrics.total_results_fetched
        total_scanned = page1_metrics.total_objects_scanned + page2_metrics.total_objects_scanned
        total_api_calls = page1_metrics.api_calls_made + page2_metrics.api_calls_made
        total_cache_hits = page1_metrics.cache_hits + page2_metrics.cache_hits
        total_cache_misses = page1_metrics.cache_misses + page2_metrics.cache_misses

        assert total_results == 80
        assert total_scanned == 350
        assert total_api_calls == 8
        assert total_cache_hits == 6
        assert total_cache_misses == 4

        # Overall efficiency should be between individual page efficiencies
        overall_efficiency = total_results / total_scanned  # 80/350 ≈ 0.229
        assert page2_dict['efficiency_ratio'] < overall_efficiency < page1_dict['efficiency_ratio']
