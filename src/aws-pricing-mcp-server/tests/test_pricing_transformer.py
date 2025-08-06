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

"""Tests for the pricing_transformer module of the aws-pricing-mcp-server."""

import json
import pytest
from awslabs.aws_pricing_mcp_server.models import OutputOptions
from awslabs.aws_pricing_mcp_server.pricing_transformer import (
    _is_free_product,
    transform_pricing_data,
)


class TestOutputOptionsFiltering:
    """Tests for the output options filtering functionality."""

    def test_output_options_model_creation(self):
        """Test OutputOptions model creation and validation."""
        # Test with pricing_terms
        options = OutputOptions(
            pricing_terms=['OnDemand'], product_attributes=None, exclude_free_products=False
        )
        assert options.pricing_terms == ['OnDemand']
        assert options.exclude_free_products is False

        # Test with multiple pricing terms
        options = OutputOptions(
            pricing_terms=['OnDemand', 'Reserved'],
            product_attributes=None,
            exclude_free_products=False,
        )
        assert options.pricing_terms == ['OnDemand', 'Reserved']

        # Test with None (default)
        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=False
        )
        assert options.pricing_terms is None

        # Test with product_attributes
        options = OutputOptions(
            pricing_terms=None,
            product_attributes=['instanceType', 'location'],
            exclude_free_products=False,
        )
        assert options.product_attributes == ['instanceType', 'location']

        # Test with both pricing_terms and product_attributes
        options = OutputOptions(
            pricing_terms=['OnDemand'],
            product_attributes=['instanceType'],
            exclude_free_products=False,
        )
        assert options.pricing_terms == ['OnDemand']
        assert options.product_attributes == ['instanceType']

        # Test with exclude_free_products
        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=True
        )
        assert options.exclude_free_products is True

        # Test default value for exclude_free_products
        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=False
        )
        assert options.exclude_free_products is False

    def test_transform_pricing_data_no_options(self):
        """Test that no filtering is applied when output_options is None."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Compute Instance'},
                    'terms': {
                        'OnDemand': {'price': '$0.0464'},
                        'Reserved': {'1yr': '$0.030', '3yr': '$0.020'},
                    },
                }
            )
        ]

        result = transform_pricing_data(sample_data, None)
        assert len(result) == 1

        # Check that all terms are preserved
        item = result[0]
        assert 'OnDemand' in item['terms']
        assert 'Reserved' in item['terms']
        # serviceCode should be removed
        assert 'serviceCode' not in item

    def test_transform_pricing_data_ondemand_only(self):
        """Test filtering to OnDemand pricing terms only."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Compute Instance'},
                    'terms': {
                        'OnDemand': {'price': '$0.0464'},
                        'Reserved': {'1yr': '$0.030', '3yr': '$0.020'},
                    },
                }
            ),
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Storage'},
                    'terms': {
                        'OnDemand': {'price': '$0.10'},
                        'Reserved': {'1yr': '$0.08', '3yr': '$0.06'},
                    },
                }
            ),
        ]

        output_options = OutputOptions(
            pricing_terms=['OnDemand'], product_attributes=None, exclude_free_products=False
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 2

        # Check that only OnDemand terms remain
        for item in result:
            assert 'OnDemand' in item['terms']
            assert 'Reserved' not in item['terms']
            assert 'serviceCode' not in item

    def test_transform_pricing_data_multiple_terms(self):
        """Test filtering with multiple allowed pricing terms."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Compute Instance'},
                    'terms': {
                        'OnDemand': {'price': '$0.0464'},
                        'Reserved': {'1yr': '$0.030', '3yr': '$0.020'},
                        'Spot': {'variable': '$0.025'},
                    },
                }
            )
        ]

        output_options = OutputOptions(
            pricing_terms=['OnDemand', 'Reserved'],
            product_attributes=None,
            exclude_free_products=False,
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 1

        item = result[0]
        assert 'OnDemand' in item['terms']
        assert 'Reserved' in item['terms']
        assert 'Spot' not in item['terms']
        assert 'serviceCode' not in item

    def test_transform_pricing_data_reserved_only(self):
        """Test filtering to Reserved pricing terms only."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Compute Instance'},
                    'terms': {
                        'OnDemand': {'price': '$0.0464'},
                        'Reserved': {'1yr': '$0.030', '3yr': '$0.020'},
                    },
                }
            )
        ]

        output_options = OutputOptions(
            pricing_terms=['Reserved'], product_attributes=None, exclude_free_products=False
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 1

        item = result[0]
        assert 'OnDemand' not in item['terms']
        assert 'Reserved' in item['terms']
        assert 'serviceCode' not in item

    def test_transform_pricing_data_empty_list(self):
        """Test that transform_pricing_data returns empty list for empty input."""
        result = transform_pricing_data([], None)
        assert result == []

    def test_transform_pricing_data_no_terms_section(self):
        """Test filtering with items that don't have a terms section."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Compute Instance'},
                    # No "terms" section
                }
            )
        ]

        output_options = OutputOptions(
            pricing_terms=['OnDemand'], product_attributes=None, exclude_free_products=False
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 1

        # Item should be preserved as-is when there are no terms to filter
        item = result[0]
        assert 'product' in item
        assert 'terms' not in item
        assert 'serviceCode' not in item

    def test_transform_pricing_data_json_error(self):
        """Test error handling when JSON deserialization fails."""
        sample_data = ['invalid json string', json.dumps({'valid': 'data'})]

        output_options = OutputOptions(
            pricing_terms=['OnDemand'], product_attributes=None, exclude_free_products=False
        )

        with pytest.raises(ValueError, match='Invalid JSON format in pricing data at index 0'):
            transform_pricing_data(sample_data, output_options)

    def test_transform_pricing_data_size_reduction(self):
        """Test that filtering actually reduces response size."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Compute Instance'},
                    'terms': {
                        'OnDemand': {'price': '$0.0464'},
                        'Reserved': {
                            '1yr': '$0.030',
                            '3yr': '$0.020',
                            'details': 'lots of additional reserved instance details here',
                        },
                    },
                }
            )
        ]

        # Test with no filtering
        unfiltered_result = transform_pricing_data(sample_data, None)
        unfiltered_size = sum(len(str(item)) for item in unfiltered_result)

        # Test with OnDemand filtering
        output_options = OutputOptions(
            pricing_terms=['OnDemand'], product_attributes=None, exclude_free_products=False
        )
        filtered_result = transform_pricing_data(sample_data, output_options)
        filtered_size = sum(len(str(item)) for item in filtered_result)

        # Filtered result should be smaller
        assert filtered_size < unfiltered_size

        # Verify content is correct
        filtered_item = filtered_result[0]
        assert 'OnDemand' in filtered_item['terms']
        assert 'Reserved' not in filtered_item['terms']
        assert 'serviceCode' not in filtered_item

    def test_transform_pricing_data_product_attributes_only(self):
        """Test filtering to specific product attributes only."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {
                        'productFamily': 'Compute Instance',
                        'attributes': {
                            'instanceType': 't3.medium',
                            'location': 'US East (N. Virginia)',
                            'memory': '4 GiB',
                            'storage': '1 x 30 SSD',
                            'networkPerformance': 'Up to 5 Gigabit',
                            'processorFeatures': 'Intel AVX, Intel Turbo',
                        },
                    },
                    'terms': {'OnDemand': {'price': '$0.0464'}},
                }
            )
        ]

        output_options = OutputOptions(
            pricing_terms=None,
            product_attributes=['instanceType', 'location', 'memory'],
            exclude_free_products=False,
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 1

        # Check that only specified attributes remain
        item = result[0]
        attributes = item['product']['attributes']
        assert 'instanceType' in attributes
        assert 'location' in attributes
        assert 'memory' in attributes
        assert 'storage' not in attributes
        assert 'networkPerformance' not in attributes
        assert 'processorFeatures' not in attributes

        # Terms should be preserved unchanged
        assert 'OnDemand' in item['terms']
        assert 'serviceCode' not in item

    def test_transform_pricing_data_combined_pricing_and_attributes(self):
        """Test filtering with both pricing terms and product attributes."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {
                        'productFamily': 'Compute Instance',
                        'attributes': {
                            'instanceType': 't3.medium',
                            'location': 'US East (N. Virginia)',
                            'memory': '4 GiB',
                            'storage': '1 x 30 SSD',
                            'networkPerformance': 'Up to 5 Gigabit',
                            'processorFeatures': 'Intel AVX, Intel Turbo',
                        },
                    },
                    'terms': {
                        'OnDemand': {'price': '$0.0464'},
                        'Reserved': {'1yr': '$0.030', '3yr': '$0.020'},
                        'Spot': {'variable': '$0.025'},
                    },
                }
            )
        ]

        output_options = OutputOptions(
            pricing_terms=['OnDemand', 'Reserved'],
            product_attributes=['instanceType', 'location'],
            exclude_free_products=False,
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 1

        item = result[0]

        # Check that only specified pricing terms remain
        assert 'OnDemand' in item['terms']
        assert 'Reserved' in item['terms']
        assert 'Spot' not in item['terms']

        # Check that only specified attributes remain
        attributes = item['product']['attributes']
        assert 'instanceType' in attributes
        assert 'location' in attributes
        assert 'memory' not in attributes
        assert 'storage' not in attributes
        assert 'networkPerformance' not in attributes
        assert 'processorFeatures' not in attributes
        assert 'serviceCode' not in item

    def test_transform_pricing_data_no_product_section(self):
        """Test filtering with items that don't have a product section."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    # No "product" section
                    'terms': {'OnDemand': {'price': '$0.0464'}},
                }
            )
        ]

        output_options = OutputOptions(
            pricing_terms=None,
            product_attributes=['instanceType', 'location'],
            exclude_free_products=False,
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 1

        # Item should be preserved as-is when there is no product section to filter
        item = result[0]
        assert 'product' not in item
        assert 'terms' in item
        assert 'serviceCode' not in item

    def test_transform_pricing_data_no_product_attributes_section(self):
        """Test filtering with items that have product but no attributes section."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {
                        'productFamily': 'Compute Instance',
                        # No "attributes" section
                    },
                    'terms': {'OnDemand': {'price': '$0.0464'}},
                }
            )
        ]

        output_options = OutputOptions(
            pricing_terms=None,
            product_attributes=['instanceType', 'location'],
            exclude_free_products=False,
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 1

        # Item should be preserved as-is when there are no attributes to filter
        item = result[0]
        assert 'product' in item
        assert 'attributes' not in item['product']
        assert 'terms' in item
        assert 'serviceCode' not in item

    def test_transform_pricing_data_product_attributes_size_reduction(self):
        """Test that product attribute filtering reduces response size."""
        # Create item with many product attributes
        large_attributes = {f'attribute_{i}': f'value_{i}' for i in range(20)}
        large_attributes.update(
            {
                'instanceType': 't3.medium',
                'location': 'US East (N. Virginia)',
                'memory': '4 GiB',
            }
        )

        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {
                        'productFamily': 'Compute Instance',
                        'attributes': large_attributes,
                    },
                    'terms': {'OnDemand': {'price': '$0.0464'}},
                }
            )
        ]

        # Test with no filtering
        unfiltered_result = transform_pricing_data(sample_data, None)
        unfiltered_size = sum(len(str(item)) for item in unfiltered_result)

        # Test with attribute filtering
        output_options = OutputOptions(
            pricing_terms=None,
            product_attributes=['instanceType', 'location', 'memory'],
            exclude_free_products=False,
        )
        filtered_result = transform_pricing_data(sample_data, output_options)
        filtered_size = sum(len(str(item)) for item in filtered_result)

        # Filtered result should be significantly smaller
        assert filtered_size < unfiltered_size

        # Verify content is correct
        filtered_item = filtered_result[0]
        attributes = filtered_item['product']['attributes']
        assert len(attributes) == 3
        assert 'instanceType' in attributes
        assert 'location' in attributes
        assert 'memory' in attributes
        assert 'serviceCode' not in filtered_item

    def test_transform_pricing_data_mixed_json_strings(self):
        """Test filtering with JSON strings only (new simplified approach)."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Compute Instance'},
                    'terms': {
                        'OnDemand': {'price': '$0.0464'},
                        'Reserved': {'1yr': '$0.030', '3yr': '$0.020'},
                    },
                }
            ),
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Storage'},
                    'terms': {
                        'OnDemand': {'price': '$0.10'},
                        'Reserved': {'1yr': '$0.08', '3yr': '$0.06'},
                    },
                }
            ),
        ]

        output_options = OutputOptions(
            pricing_terms=['OnDemand'], product_attributes=None, exclude_free_products=False
        )
        result = transform_pricing_data(sample_data, output_options)

        assert len(result) == 2

        # Check that only OnDemand terms remain in both items
        for item in result:
            assert 'OnDemand' in item['terms']
            assert 'Reserved' not in item['terms']
            assert 'serviceCode' not in item


class TestExcludeFreeProductsFiltering:
    """Tests for the exclude_free_products filtering functionality."""

    def _create_product_data(self, family, price_usd, terms_type='OnDemand'):
        """Helper to create product data with specified pricing."""
        return json.dumps(
            {
                'serviceCode': 'AmazonEC2',
                'product': {'productFamily': family},
                'terms': {
                    terms_type: {
                        f'{family[:4].upper()}123.JRTCKXETXF': {
                            'priceDimensions': {
                                f'{family[:4].upper()}123.JRTCKXETXF.6YS6EN2CT7': {
                                    'pricePerUnit': {'USD': price_usd}
                                }
                            }
                        }
                    }
                },
            }
        )

    @pytest.mark.parametrize(
        'exclude_free,expected_count',
        [
            (None, 1),  # Default (None) behavior - keep free products
            (False, 1),  # Explicit False - keep free products
            (True, 0),  # True - filter out free products
        ],
    )
    def test_exclude_free_products_option_behavior(self, exclude_free, expected_count):
        """Test exclude_free_products option with free product."""
        sample_data = [self._create_product_data('Free Tier', '0.0000000000')]

        if exclude_free is None:
            result = transform_pricing_data(sample_data, None)
        else:
            options = OutputOptions(
                pricing_terms=None, product_attributes=None, exclude_free_products=exclude_free
            )
            result = transform_pricing_data(sample_data, options)

        assert len(result) == expected_count

    @pytest.mark.parametrize(
        'price_usd,should_be_kept',
        [
            ('0.0000000000', False),  # Free - filtered out
            ('0.0464000000', True),  # Paid - kept
            ('0.0000010000', True),  # Very small but non-zero - kept
        ],
    )
    def test_exclude_free_products_by_price(self, price_usd, should_be_kept):
        """Test filtering based on different price values."""
        sample_data = [self._create_product_data('Test Product', price_usd)]
        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=True
        )
        result = transform_pricing_data(sample_data, options)

        assert len(result) == (1 if should_be_kept else 0)

    def test_exclude_free_products_mixed_data(self):
        """Test filtering with mix of free and paid products."""
        sample_data = [
            self._create_product_data('Free Tier', '0.0000000000'),
            self._create_product_data('Compute Instance', '0.0464000000'),
            self._create_product_data('Another Free', '0.0000000000'),
        ]

        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=True
        )
        result = transform_pricing_data(sample_data, options)

        assert len(result) == 1
        assert result[0]['product']['productFamily'] == 'Compute Instance'

    def test_exclude_free_products_mixed_pricing_dimensions(self):
        """Test product with both free and paid pricing dimensions is kept."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Mixed Pricing'},
                    'terms': {
                        'OnDemand': {
                            'MIXED123.JRTCKXETXF': {
                                'priceDimensions': {
                                    'FREE_DIMENSION': {'pricePerUnit': {'USD': '0.0000000000'}},
                                    'PAID_DIMENSION': {'pricePerUnit': {'USD': '0.0464000000'}},
                                }
                            }
                        }
                    },
                }
            )
        ]

        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=True
        )
        result = transform_pricing_data(sample_data, options)
        assert len(result) == 1  # Kept because has non-zero price

    @pytest.mark.parametrize('terms_type', ['Reserved', 'Spot'])
    def test_exclude_free_products_no_ondemand_terms(self, terms_type):
        """Test products without OnDemand terms are always kept."""
        sample_data = [self._create_product_data('Reserved Only', '0.0300000000', terms_type)]
        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=True
        )
        result = transform_pricing_data(sample_data, options)
        assert len(result) == 1  # Kept because no OnDemand pricing to check

    @pytest.mark.parametrize(
        'malformed_data,should_be_kept',
        [
            # Missing priceDimensions - defaults to $0.00, gets filtered
            ({'OnDemand': {'KEY': {}}}, False),
            # Missing pricePerUnit - defaults to $0.00, gets filtered
            ({'OnDemand': {'KEY': {'priceDimensions': {'SUB': {}}}}}, False),
            # Invalid price format - kept as safe behavior
            (
                {
                    'OnDemand': {
                        'KEY': {'priceDimensions': {'SUB': {'pricePerUnit': {'USD': 'invalid'}}}}
                    }
                },
                True,
            ),
        ],
    )
    def test_exclude_free_products_malformed_data(self, malformed_data, should_be_kept):
        """Test handling of malformed pricing structures."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Test Product'},
                    'terms': malformed_data,
                }
            )
        ]

        options = OutputOptions(
            pricing_terms=None, product_attributes=None, exclude_free_products=True
        )
        result = transform_pricing_data(sample_data, options)
        assert len(result) == (1 if should_be_kept else 0)

    def test_exclude_free_products_combined_with_other_filters(self):
        """Test free product filtering works with other OutputOptions."""
        sample_data = [
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Free with Reserved'},
                    'terms': {
                        'OnDemand': {
                            'FREE': {
                                'priceDimensions': {
                                    'SUB': {'pricePerUnit': {'USD': '0.0000000000'}}
                                }
                            }
                        },
                        'Reserved': {
                            'RESERVED': {
                                'priceDimensions': {
                                    'SUB': {'pricePerUnit': {'USD': '0.0200000000'}}
                                }
                            }
                        },
                    },
                }
            ),
            json.dumps(
                {
                    'serviceCode': 'AmazonEC2',
                    'product': {'productFamily': 'Paid Instance'},
                    'terms': {
                        'OnDemand': {
                            'PAID': {
                                'priceDimensions': {
                                    'SUB': {'pricePerUnit': {'USD': '0.0464000000'}}
                                }
                            }
                        },
                        'Reserved': {
                            'RESERVED': {
                                'priceDimensions': {
                                    'SUB': {'pricePerUnit': {'USD': '0.0300000000'}}
                                }
                            }
                        },
                    },
                }
            ),
        ]

        options = OutputOptions(
            pricing_terms=['OnDemand'], product_attributes=None, exclude_free_products=True
        )
        result = transform_pricing_data(sample_data, options)

        # Only paid product remains, only OnDemand terms
        assert len(result) == 1
        assert result[0]['product']['productFamily'] == 'Paid Instance'
        assert 'OnDemand' in result[0]['terms']
        assert 'Reserved' not in result[0]['terms']

    @pytest.mark.parametrize(
        'item,expected',
        [
            # Free product
            (
                {
                    'terms': {
                        'OnDemand': {
                            'KEY': {
                                'priceDimensions': {
                                    'SUB': {'pricePerUnit': {'USD': '0.0000000000'}}
                                }
                            }
                        }
                    }
                },
                True,
            ),
            # Paid product
            (
                {
                    'terms': {
                        'OnDemand': {
                            'KEY': {
                                'priceDimensions': {
                                    'SUB': {'pricePerUnit': {'USD': '0.0464000000'}}
                                }
                            }
                        }
                    }
                },
                False,
            ),
            # No OnDemand terms
            (
                {
                    'terms': {
                        'Reserved': {
                            'KEY': {
                                'priceDimensions': {
                                    'SUB': {'pricePerUnit': {'USD': '0.0300000000'}}
                                }
                            }
                        }
                    }
                },
                False,
            ),
            # Malformed structure
            ({'terms': {}}, False),
            # Empty item
            ({}, False),
        ],
    )
    def test_is_free_product_helper_function(self, item, expected):
        """Test the _is_free_product helper function with various inputs."""
        assert _is_free_product(item) is expected
