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

"""Unit tests for PricingCache class."""

import json
from awslabs.aws_healthomics_mcp_server.analysis.pricing_cache import PricingCache
from unittest.mock import MagicMock, patch


class TestPricingCacheGetInstanceSpecs:
    """Test cases for get_instance_specs method."""

    def test_get_instance_specs_m_xlarge(self):
        """Test parsing omics.m.xlarge instance type."""
        cpus, memory = PricingCache.get_instance_specs('omics.m.xlarge')
        assert cpus == 4
        assert memory == 16.0  # 4 vCPUs * 4 GiB/vCPU

    def test_get_instance_specs_c_2xlarge(self):
        """Test parsing omics.c.2xlarge instance type."""
        cpus, memory = PricingCache.get_instance_specs('omics.c.2xlarge')
        assert cpus == 8
        assert memory == 16.0  # 8 vCPUs * 2 GiB/vCPU

    def test_get_instance_specs_r_4xlarge(self):
        """Test parsing omics.r.4xlarge instance type."""
        cpus, memory = PricingCache.get_instance_specs('omics.r.4xlarge')
        assert cpus == 16
        assert memory == 128.0  # 16 vCPUs * 8 GiB/vCPU

    def test_get_instance_specs_large(self):
        """Test parsing omics.m.large instance type."""
        cpus, memory = PricingCache.get_instance_specs('omics.m.large')
        assert cpus == 2
        assert memory == 8.0  # 2 vCPUs * 4 GiB/vCPU

    def test_get_instance_specs_48xlarge(self):
        """Test parsing omics.r.48xlarge instance type (largest)."""
        cpus, memory = PricingCache.get_instance_specs('omics.r.48xlarge')
        assert cpus == 192
        assert memory == 1536.0  # 192 vCPUs * 8 GiB/vCPU

    def test_get_instance_specs_invalid_format(self):
        """Test parsing invalid instance type format."""
        cpus, memory = PricingCache.get_instance_specs('invalid')
        assert cpus == 0
        assert memory == 0.0

    def test_get_instance_specs_unknown_size(self):
        """Test parsing instance type with unknown size."""
        cpus, memory = PricingCache.get_instance_specs('omics.m.unknown')
        assert cpus == 0
        assert memory == 0.0

    def test_get_instance_specs_unknown_family_uses_default(self):
        """Test parsing instance type with unknown family uses default memory ratio."""
        cpus, memory = PricingCache.get_instance_specs('omics.x.xlarge')
        assert cpus == 4
        assert memory == 16.0  # 4 vCPUs * 4 GiB/vCPU (default)


class TestPricingCacheCacheBehavior:
    """Test cases for cache hit/miss behavior."""

    def setup_method(self):
        """Clear cache before each test."""
        PricingCache.clear_cache()
        PricingCache._pricing_client = None

    def teardown_method(self):
        """Clear cache after each test."""
        PricingCache.clear_cache()
        PricingCache._pricing_client = None

    def test_cache_miss_then_hit(self):
        """Test that cache miss fetches from API and subsequent call hits cache."""
        mock_price_response = {
            'PriceList': [
                json.dumps(
                    {
                        'terms': {
                            'OnDemand': {
                                'term1': {
                                    'priceDimensions': {'dim1': {'pricePerUnit': {'USD': '0.50'}}}
                                }
                            }
                        }
                    }
                )
            ]
        }

        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.return_value = mock_price_response
            mock_get_client.return_value = mock_client

            # First call - cache miss
            price1 = PricingCache.get_price('omics.m.xlarge', 'us-east-1')
            assert price1 == 0.50
            assert mock_client.get_products.call_count == 1

            # Second call - cache hit
            price2 = PricingCache.get_price('omics.m.xlarge', 'us-east-1')
            assert price2 == 0.50
            assert mock_client.get_products.call_count == 1  # No additional API call

    def test_cache_different_regions(self):
        """Test that different regions are cached separately."""
        mock_price_response_east = {
            'PriceList': [
                json.dumps(
                    {
                        'terms': {
                            'OnDemand': {
                                'term1': {
                                    'priceDimensions': {'dim1': {'pricePerUnit': {'USD': '0.50'}}}
                                }
                            }
                        }
                    }
                )
            ]
        }
        mock_price_response_west = {
            'PriceList': [
                json.dumps(
                    {
                        'terms': {
                            'OnDemand': {
                                'term1': {
                                    'priceDimensions': {'dim1': {'pricePerUnit': {'USD': '0.55'}}}
                                }
                            }
                        }
                    }
                )
            ]
        }

        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.side_effect = [
                mock_price_response_east,
                mock_price_response_west,
            ]
            mock_get_client.return_value = mock_client

            price_east = PricingCache.get_price('omics.m.xlarge', 'us-east-1')
            price_west = PricingCache.get_price('omics.m.xlarge', 'us-west-2')

            assert price_east == 0.50
            assert price_west == 0.55
            assert mock_client.get_products.call_count == 2

    def test_cache_size(self):
        """Test cache size tracking."""
        assert PricingCache.get_cache_size() == 0

        # Manually add to cache
        PricingCache._cache['test:us-east-1'] = 1.0
        assert PricingCache.get_cache_size() == 1

        PricingCache._cache['test2:us-west-2'] = 2.0
        assert PricingCache.get_cache_size() == 2

    def test_clear_cache(self):
        """Test cache clearing."""
        PricingCache._cache['test:us-east-1'] = 1.0
        assert PricingCache.get_cache_size() == 1

        PricingCache.clear_cache()
        assert PricingCache.get_cache_size() == 0


class TestPricingCacheFetchFromApi:
    """Test cases for _fetch_price_from_api method."""

    def setup_method(self):
        """Clear cache before each test."""
        PricingCache.clear_cache()
        PricingCache._pricing_client = None

    def teardown_method(self):
        """Clear cache after each test."""
        PricingCache.clear_cache()
        PricingCache._pricing_client = None

    def test_fetch_price_unknown_region(self):
        """Test fetching price for unknown region returns None."""
        price = PricingCache._fetch_price_from_api('omics.m.xlarge', 'unknown-region')
        assert price is None

    def test_fetch_price_empty_price_list(self):
        """Test fetching price when API returns empty price list."""
        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.return_value = {'PriceList': []}
            mock_get_client.return_value = mock_client

            price = PricingCache._fetch_price_from_api('omics.m.xlarge', 'us-east-1')
            assert price is None

    def test_fetch_price_api_exception(self):
        """Test fetching price when API raises exception."""
        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.side_effect = Exception('API Error')
            mock_get_client.return_value = mock_client

            price = PricingCache._fetch_price_from_api('omics.m.xlarge', 'us-east-1')
            assert price is None

    def test_fetch_price_storage_type(self):
        """Test fetching price for storage type."""
        mock_price_response = {
            'PriceList': [
                json.dumps(
                    {
                        'terms': {
                            'OnDemand': {
                                'term1': {
                                    'priceDimensions': {'dim1': {'pricePerUnit': {'USD': '0.025'}}}
                                }
                            }
                        }
                    }
                )
            ]
        }

        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.return_value = mock_price_response
            mock_get_client.return_value = mock_client

            price = PricingCache._fetch_price_from_api('Run Storage', 'us-east-1')
            assert price == 0.025

            # Verify the filter used resourceType for storage
            call_args = mock_client.get_products.call_args
            filters = call_args.kwargs['Filters']
            resource_filter = next(f for f in filters if f['Field'] == 'resourceType')
            assert resource_filter['Value'] == 'Run Storage'


class TestPricingCacheConstants:
    """Test cases for PricingCache constants."""

    def test_size_to_cpus_mapping(self):
        """Test SIZE_TO_CPUS mapping contains expected values."""
        assert PricingCache.SIZE_TO_CPUS['large'] == 2
        assert PricingCache.SIZE_TO_CPUS['xlarge'] == 4
        assert PricingCache.SIZE_TO_CPUS['2xlarge'] == 8
        assert PricingCache.SIZE_TO_CPUS['4xlarge'] == 16
        assert PricingCache.SIZE_TO_CPUS['8xlarge'] == 32
        assert PricingCache.SIZE_TO_CPUS['12xlarge'] == 48
        assert PricingCache.SIZE_TO_CPUS['16xlarge'] == 64
        assert PricingCache.SIZE_TO_CPUS['24xlarge'] == 96
        assert PricingCache.SIZE_TO_CPUS['32xlarge'] == 128
        assert PricingCache.SIZE_TO_CPUS['48xlarge'] == 192

    def test_family_memory_ratio_mapping(self):
        """Test FAMILY_MEMORY_RATIO mapping contains expected values."""
        assert PricingCache.FAMILY_MEMORY_RATIO['c'] == 2
        assert PricingCache.FAMILY_MEMORY_RATIO['m'] == 4
        assert PricingCache.FAMILY_MEMORY_RATIO['r'] == 8

    def test_region_name_map(self):
        """Test REGION_NAME_MAP contains expected regions."""
        assert 'us-east-1' in PricingCache.REGION_NAME_MAP
        assert 'us-west-2' in PricingCache.REGION_NAME_MAP
        assert 'eu-west-1' in PricingCache.REGION_NAME_MAP
        assert PricingCache.REGION_NAME_MAP['us-east-1'] == 'US East (N. Virginia)'


class TestPricingCacheGetPriceWithError:
    """Test cases for get_price_with_error method (Requirements 1.5)."""

    def setup_method(self):
        """Clear cache before each test."""
        PricingCache.clear_cache()
        PricingCache._pricing_client = None

    def teardown_method(self):
        """Clear cache after each test."""
        PricingCache.clear_cache()
        PricingCache._pricing_client = None

    def test_get_price_with_error_success(self):
        """Test get_price_with_error returns price and no error on success."""
        mock_price_response = {
            'PriceList': [
                json.dumps(
                    {
                        'terms': {
                            'OnDemand': {
                                'term1': {
                                    'priceDimensions': {'dim1': {'pricePerUnit': {'USD': '0.50'}}}
                                }
                            }
                        }
                    }
                )
            ]
        }

        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.return_value = mock_price_response
            mock_get_client.return_value = mock_client

            price, error = PricingCache.get_price_with_error('omics.m.xlarge', 'us-east-1')

            assert price == 0.50
            assert error is None

    def test_get_price_with_error_api_unavailable(self):
        """Test get_price_with_error returns error message when API is unavailable."""
        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.side_effect = Exception('Connection refused')
            mock_get_client.return_value = mock_client

            price, error = PricingCache.get_price_with_error('omics.m.xlarge', 'us-east-1')

            assert price is None
            assert error is not None
            assert 'omics.m.xlarge' in error
            assert 'us-east-1' in error

    def test_get_price_with_error_empty_price_list(self):
        """Test get_price_with_error returns error message when no pricing found."""
        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.return_value = {'PriceList': []}
            mock_get_client.return_value = mock_client

            price, error = PricingCache.get_price_with_error('omics.m.xlarge', 'us-east-1')

            assert price is None
            assert error is not None
            assert 'Unable to retrieve pricing' in error
            assert 'omics.m.xlarge' in error
            assert 'us-east-1' in error

    def test_get_price_with_error_unknown_region(self):
        """Test get_price_with_error returns error message for unknown region."""
        price, error = PricingCache.get_price_with_error('omics.m.xlarge', 'unknown-region')

        assert price is None
        assert error is not None
        assert 'Unable to retrieve pricing' in error
        assert 'unknown-region' in error

    def test_get_price_with_error_uses_cache(self):
        """Test get_price_with_error uses cache on subsequent calls."""
        mock_price_response = {
            'PriceList': [
                json.dumps(
                    {
                        'terms': {
                            'OnDemand': {
                                'term1': {
                                    'priceDimensions': {'dim1': {'pricePerUnit': {'USD': '0.75'}}}
                                }
                            }
                        }
                    }
                )
            ]
        }

        with patch.object(PricingCache, '_get_pricing_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_products.return_value = mock_price_response
            mock_get_client.return_value = mock_client

            # First call - cache miss
            price1, error1 = PricingCache.get_price_with_error('omics.r.xlarge', 'us-east-1')
            assert price1 == 0.75
            assert error1 is None
            assert mock_client.get_products.call_count == 1

            # Second call - cache hit
            price2, error2 = PricingCache.get_price_with_error('omics.r.xlarge', 'us-east-1')
            assert price2 == 0.75
            assert error2 is None
            assert mock_client.get_products.call_count == 1  # No additional API call
