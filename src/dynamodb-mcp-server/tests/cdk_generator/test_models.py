"""Unit tests for CDK generator data models.

Tests are organized incrementally with nested classes:
1. Start with simplest valid table
2. Add one feature at a time
3. Test both valid cases and validation errors for each feature
"""

import copy
import pytest
from awslabs.dynamodb_mcp_server.cdk_generator.models import (
    DataModel,
    GlobalSecondaryIndex,
    KeyAttribute,
)


BASE_SIMPLE_TABLE = {
    'tables': [
        {
            'TableName': 'SimpleTable',
            'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
        }
    ]
}


def extend_json(base, updates):
    """Deep copy base and merge updates."""
    result = copy.deepcopy(base)

    def deep_merge(target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge(target[key], value)
            else:
                target[key] = value

    deep_merge(result, updates)
    return result


class TestKeyAttribute:
    """Test KeyAttribute class."""

    def test_to_cdk_type_string(self):
        """S maps to STRING."""
        attr = KeyAttribute(name='pk', type='S')
        assert attr.to_cdk_type() == 'STRING'

    def test_to_cdk_type_number(self):
        """N maps to NUMBER."""
        attr = KeyAttribute(name='pk', type='N')
        assert attr.to_cdk_type() == 'NUMBER'

    def test_to_cdk_type_binary(self):
        """B maps to BINARY."""
        attr = KeyAttribute(name='pk', type='B')
        assert attr.to_cdk_type() == 'BINARY'

    def test_to_cdk_type_invalid(self):
        """Invalid type raises ValueError with message."""
        attr = KeyAttribute(name='pk', type='X')
        with pytest.raises(
            ValueError, match=r"Invalid attribute type\. type: 'X', expected: S, N, or B"
        ):
            attr.to_cdk_type()


class TestGlobalSecondaryIndex:
    """Test GlobalSecondaryIndex class."""

    def test_has_multi_partition_keys_single(self):
        """Single partition key returns False."""
        gsi = GlobalSecondaryIndex(
            index_name='GSI1',
            partition_keys=[KeyAttribute(name='pk', type='S')],
        )
        assert not gsi.has_multi_partition_keys()

    def test_has_multi_partition_keys_multiple(self):
        """Multiple partition keys returns True."""
        gsi = GlobalSecondaryIndex(
            index_name='GSI1',
            partition_keys=[
                KeyAttribute(name='pk1', type='S'),
                KeyAttribute(name='pk2', type='S'),
            ],
        )
        assert gsi.has_multi_partition_keys()

    def test_has_multi_sort_keys_none(self):
        """No sort keys returns False."""
        gsi = GlobalSecondaryIndex(
            index_name='GSI1',
            partition_keys=[KeyAttribute(name='pk', type='S')],
            sort_keys=[],
        )
        assert not gsi.has_multi_sort_keys()

    def test_has_multi_sort_keys_single(self):
        """Single sort key returns False."""
        gsi = GlobalSecondaryIndex(
            index_name='GSI1',
            partition_keys=[KeyAttribute(name='pk', type='S')],
            sort_keys=[KeyAttribute(name='sk', type='S')],
        )
        assert not gsi.has_multi_sort_keys()

    def test_has_multi_sort_keys_multiple(self):
        """Multiple sort keys returns True."""
        gsi = GlobalSecondaryIndex(
            index_name='GSI1',
            partition_keys=[KeyAttribute(name='pk', type='S')],
            sort_keys=[
                KeyAttribute(name='sk1', type='S'),
                KeyAttribute(name='sk2', type='N'),
            ],
        )
        assert gsi.has_multi_sort_keys()


class TestDataModelFromJson:
    """Test DataModel.from_json() with incremental complexity."""

    class TestRootValidation:
        """Test root-level JSON validation (before any table parsing)."""

        def test_input_not_dict(self):
            """Error: Input must be a dictionary."""
            with pytest.raises(ValueError, match='Input must be a dictionary'):
                DataModel.from_json('not a dict')

        def test_missing_tables_field(self):
            """Error: 'tables' field missing."""
            data = {}
            with pytest.raises(ValueError, match='Configuration must contain a "tables" property'):
                DataModel.from_json(data)

        def test_tables_not_list(self):
            """Error: 'tables' is not a list."""
            data = {'tables': 'not a list'}
            with pytest.raises(
                ValueError, match='Configuration "tables" property must be an array'
            ):
                DataModel.from_json(data)

        def test_empty_tables_list(self):
            """Error: tables list is empty."""
            data = {'tables': []}
            with pytest.raises(ValueError, match='Data model must contain at least one table'):
                DataModel.from_json(data)

    class TestMinimalTable:
        """Test the simplest possible valid table (partition key only)."""

        def test_parse_minimal_table(self):
            """Parse table with only partition key."""
            model = DataModel.from_json(BASE_SIMPLE_TABLE)
            assert len(model.tables) == 1
            table = model.tables[0]
            assert table.table_name == 'SimpleTable'
            assert table.partition_key.name == 'pk'
            assert table.partition_key.type == 'S'
            assert table.sort_key is None
            assert len(table.global_secondary_indexes) == 0

        class TestTableStructure:
            """Test table-level structure validation."""

            def test_table_not_object(self):
                """Error: table is not an object."""
                data = {'tables': ['not_an_object']}
                with pytest.raises(ValueError, match=r'tables\[0\] must be an object'):
                    DataModel.from_json(data)

            def test_missing_table_name(self):
                """Error: TableName missing."""
                data = {
                    'tables': [
                        {
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(ValueError, match=r'tables\[0\]\.TableName must be a string'):
                    DataModel.from_json(data)

            def test_table_name_not_string(self):
                """Error: TableName is not string."""
                data = {
                    'tables': [
                        {
                            'TableName': 123,
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(ValueError, match=r'tables\[0\]\.TableName must be a string'):
                    DataModel.from_json(data)

            def test_missing_attribute_definitions(self):
                """Error: AttributeDefinitions missing."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError, match=r'tables\[0\]\.AttributeDefinitions must be an array'
                ):
                    DataModel.from_json(data)

            def test_attribute_definitions_not_array(self):
                """Error: AttributeDefinitions not array."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': 'not_array',
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError, match=r'tables\[0\]\.AttributeDefinitions must be an array'
                ):
                    DataModel.from_json(data)

            def test_missing_key_schema(self):
                """Error: KeySchema missing."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                        }
                    ]
                }
                with pytest.raises(ValueError, match=r'tables\[0\]\.KeySchema must be an array'):
                    DataModel.from_json(data)

            def test_key_schema_not_array(self):
                """Error: KeySchema not array."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': 'not_array',
                        }
                    ]
                }
                with pytest.raises(ValueError, match=r'tables\[0\]\.KeySchema must be an array'):
                    DataModel.from_json(data)

        class TestAttributeDefinitions:
            """Test AttributeDefinitions validation."""

            def test_attribute_not_object(self):
                """Error: attribute definition not object."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': ['not_object'],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError, match=r'tables\[0\]\.AttributeDefinitions\[0\] must be an object'
                ):
                    DataModel.from_json(data)

            def test_missing_attribute_name(self):
                """Error: AttributeName missing."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [{'AttributeType': 'S'}],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.AttributeDefinitions\[0\]\.AttributeName must be a string',
                ):
                    DataModel.from_json(data)

            def test_attribute_name_not_string(self):
                """Error: AttributeName not string."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [{'AttributeName': 123, 'AttributeType': 'S'}],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.AttributeDefinitions\[0\]\.AttributeName must be a string',
                ):
                    DataModel.from_json(data)

            def test_missing_attribute_type(self):
                """Error: AttributeType missing."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [{'AttributeName': 'pk'}],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.AttributeDefinitions\[0\]\.AttributeType must be 'S', 'N', or 'B'",
                ):
                    DataModel.from_json(data)

            def test_invalid_attribute_type(self):
                """Error: AttributeType not S/N/B."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'X'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.AttributeDefinitions\[0\]\.AttributeType must be 'S', 'N', or 'B'",
                ):
                    DataModel.from_json(data)

            def test_second_attribute_error_shows_correct_index(self):
                """Error in second attribute shows [1]."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'sk', 'AttributeType': 'INVALID'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.AttributeDefinitions\[1\]\.AttributeType must be 'S', 'N', or 'B'",
                ):
                    DataModel.from_json(data)

        class TestKeySchema:
            """Test KeySchema validation."""

            def test_key_element_not_object(self):
                """Error: key element not object."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': ['not_object'],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError, match=r'tables\[0\]\.KeySchema\[0\] must be an object'
                ):
                    DataModel.from_json(data)

            def test_missing_key_attribute_name(self):
                """Error: key AttributeName missing."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.KeySchema\[0\]\.AttributeName must be a string',
                ):
                    DataModel.from_json(data)

            def test_key_attribute_name_not_string(self):
                """Error: key AttributeName not string."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 123, 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.KeySchema\[0\]\.AttributeName must be a string',
                ):
                    DataModel.from_json(data)

            def test_missing_key_type(self):
                """Error: KeyType missing."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.KeySchema\[0\]\.KeyType must be 'HASH' or 'RANGE'",
                ):
                    DataModel.from_json(data)

            def test_invalid_key_type(self):
                """Error: KeyType not HASH/RANGE."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'INVALID'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.KeySchema\[0\]\.KeyType must be 'HASH' or 'RANGE'",
                ):
                    DataModel.from_json(data)

            def test_missing_partition_key(self):
                """Error: no HASH key in KeySchema."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'sk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'sk', 'KeyType': 'RANGE'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError, match=r'tables\[0\]\.KeySchema must contain exactly one HASH key'
                ):
                    DataModel.from_json(data)

            def test_multiple_partition_keys(self):
                """Error: multiple HASH keys in base table."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk1', 'AttributeType': 'S'},
                                {'AttributeName': 'pk2', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [
                                {'AttributeName': 'pk1', 'KeyType': 'HASH'},
                                {'AttributeName': 'pk2', 'KeyType': 'HASH'},
                            ],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.KeySchema must contain exactly one HASH key, found 2',
                ):
                    DataModel.from_json(data)

            def test_undefined_key_attribute(self):
                """Error: KeySchema references undefined attribute."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'undefined', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.KeySchema\[0\]: AttributeName 'undefined' not found in AttributeDefinitions",
                ):
                    DataModel.from_json(data)

            def test_second_key_error_shows_correct_index(self):
                """Error in second key shows [1]."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [
                                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                                {'AttributeName': 'undefined_sk', 'KeyType': 'RANGE'},
                            ],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.KeySchema\[1\]: AttributeName 'undefined_sk' not found in AttributeDefinitions",
                ):
                    DataModel.from_json(data)

            def test_key_schema_not_array(self):
                """Error: KeySchema is not an array."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': 'not-an-array',
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.KeySchema must be an array',
                ):
                    DataModel.from_json(data)

            def test_attribute_not_in_definitions(self):
                """Error: AttributeName in KeySchema not in AttributeDefinitions."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'missing_attr', 'KeyType': 'HASH'}],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.KeySchema\[0\]: AttributeName 'missing_attr' not found in AttributeDefinitions",
                ):
                    DataModel.from_json(data)

    class TestTableWithSortKey:
        """Test adding sort key to base table."""

        def test_parse_table_with_sort_key(self):
            """Parse table with partition + sort key."""
            data = {
                'tables': [
                    {
                        'TableName': 'TableWithSortKey',
                        'AttributeDefinitions': [
                            {'AttributeName': 'pk', 'AttributeType': 'S'},
                            {'AttributeName': 'sk', 'AttributeType': 'N'},
                        ],
                        'KeySchema': [
                            {'AttributeName': 'pk', 'KeyType': 'HASH'},
                            {'AttributeName': 'sk', 'KeyType': 'RANGE'},
                        ],
                    }
                ]
            }
            model = DataModel.from_json(data)
            table = model.tables[0]
            assert table.sort_key is not None
            assert table.sort_key.name == 'sk'
            assert table.sort_key.type == 'N'

        def test_multiple_sort_keys(self):
            """Error: multiple RANGE keys in base table."""
            data = {
                'tables': [
                    {
                        'TableName': 'Test',
                        'AttributeDefinitions': [
                            {'AttributeName': 'pk', 'AttributeType': 'S'},
                            {'AttributeName': 'sk1', 'AttributeType': 'S'},
                            {'AttributeName': 'sk2', 'AttributeType': 'S'},
                        ],
                        'KeySchema': [
                            {'AttributeName': 'pk', 'KeyType': 'HASH'},
                            {'AttributeName': 'sk1', 'KeyType': 'RANGE'},
                            {'AttributeName': 'sk2', 'KeyType': 'RANGE'},
                        ],
                    }
                ]
            }
            with pytest.raises(
                ValueError,
                match=r'tables\[0\]\.KeySchema must contain at most one RANGE key, found 2',
            ):
                DataModel.from_json(data)

        def test_undefined_sort_key(self):
            """Error: sort key not in AttributeDefinitions."""
            data = {
                'tables': [
                    {
                        'TableName': 'Test',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [
                            {'AttributeName': 'pk', 'KeyType': 'HASH'},
                            {'AttributeName': 'undefined_sk', 'KeyType': 'RANGE'},
                        ],
                    }
                ]
            }
            with pytest.raises(
                ValueError,
                match=r"tables\[0\]\.KeySchema\[1\]: AttributeName 'undefined_sk' not found",
            ):
                DataModel.from_json(data)

    class TestTableWithGSI:
        """Test adding Global Secondary Indexes to table."""

        class TestSingleKeyGSI:
            """Test GSI with single partition/sort keys."""

            def test_parse_gsi_with_partition_key_only(self):
                """Parse GSI with only partition key."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [{'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                table = model.tables[0]
                assert table.global_secondary_indexes is not None
                assert len(table.global_secondary_indexes) == 1
                gsi = table.global_secondary_indexes[0]
                assert gsi.index_name == 'GSI1'
                assert len(gsi.partition_keys) == 1
                assert gsi.partition_keys[0].name == 'gsi_pk'
                assert len(gsi.sort_keys) == 0
                assert not gsi.has_multi_partition_keys()
                assert not gsi.has_multi_sort_keys()

            def test_parse_gsi_with_partition_and_sort_key(self):
                """Parse GSI with partition + sort key."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk', 'AttributeType': 'N'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_sk', 'KeyType': 'RANGE'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.partition_keys) == 1
                assert len(gsi.sort_keys) == 1
                assert gsi.sort_keys[0].name == 'gsi_sk'
                assert not gsi.has_multi_partition_keys()
                assert not gsi.has_multi_sort_keys()

            class TestGSIStructure:
                """Test GSI structure validation."""

                def test_gsi_not_object(self):
                    """Error: GSI not object."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'}
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': ['not_object'],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\] must be an object',
                    ):
                        DataModel.from_json(data)

                def test_gsi_missing_index_name(self):
                    """Error: GSI missing IndexName."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {'KeySchema': [{'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}]}
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.IndexName must be a string',
                    ):
                        DataModel.from_json(data)

                def test_gsi_index_name_not_string(self):
                    """Error: IndexName not string."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 123,
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.IndexName must be a string',
                    ):
                        DataModel.from_json(data)

                def test_gsi_missing_key_schema(self):
                    """Error: GSI missing KeySchema."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'}
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [{'IndexName': 'GSI1'}],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema must be an array',
                    ):
                        DataModel.from_json(data)

                def test_gsi_key_schema_not_array(self):
                    """Error: GSI KeySchema not array."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'}
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {'IndexName': 'GSI1', 'KeySchema': 'not_array'}
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema must be an array',
                    ):
                        DataModel.from_json(data)

                def test_gsi_missing_partition_key(self):
                    """Error: GSI has no HASH key."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_sk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_sk', 'KeyType': 'RANGE'}
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema must contain at least one HASH key',
                    ):
                        DataModel.from_json(data)

                def test_gsi_undefined_attribute(self):
                    """Error: GSI key not in AttributeDefinitions."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'}
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {
                                                'AttributeName': 'undefined_gsi_pk',
                                                'KeyType': 'HASH',
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r"tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema\[0\]: AttributeName 'undefined_gsi_pk' not found",
                    ):
                        DataModel.from_json(data)

                def test_second_gsi_error_shows_correct_index(self):
                    """Error in second GSI shows [1]."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi1_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi1_pk', 'KeyType': 'HASH'}
                                        ],
                                    },
                                    {
                                        'IndexName': 'GSI2',
                                        'KeySchema': [
                                            {'AttributeName': 'undefined_pk', 'KeyType': 'HASH'}
                                        ],
                                    },
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r"tables\[0\]\.GlobalSecondaryIndexes\[1\]\.KeySchema\[0\]: AttributeName 'undefined_pk' not found",
                    ):
                        DataModel.from_json(data)

                def test_duplicate_gsi_names(self):
                    """Error: table has duplicate GSI names."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'TestTable',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk1', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk2', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'DuplicateGSI',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk1', 'KeyType': 'HASH'}
                                        ],
                                    },
                                    {
                                        'IndexName': 'DuplicateGSI',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk2', 'KeyType': 'HASH'}
                                        ],
                                    },
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r"Table contains duplicate GSI names\. table_name: 'TestTable', gsi_names: DuplicateGSI",
                    ):
                        DataModel.from_json(data)

        class TestMultiKeyGSI:
            """Test GSI with multiple partition/sort keys (composite keys).

            AWS Limit: Max 4 attributes per partition key, max 4 per sort key.
            """

            def test_parse_gsi_with_two_partition_keys(self):
                """Parse GSI with 2 HASH keys."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithMultiKeyGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk2', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'MultiKeyGSI',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk1', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk2', 'KeyType': 'HASH'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.partition_keys) == 2
                assert gsi.partition_keys[0].name == 'gsi_pk1'
                assert gsi.partition_keys[1].name == 'gsi_pk2'
                assert gsi.has_multi_partition_keys()

            def test_parse_gsi_with_three_partition_keys(self):
                """Parse GSI with 3 HASH keys."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithMultiKeyGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk2', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk3', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'MultiKeyGSI',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk1', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk2', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk3', 'KeyType': 'HASH'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.partition_keys) == 3
                assert gsi.has_multi_partition_keys()

            def test_parse_gsi_with_four_partition_keys(self):
                """Parse GSI with 4 HASH keys (max allowed)."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithMultiKeyGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk2', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk3', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk4', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'MultiKeyGSI',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk1', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk2', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk3', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk4', 'KeyType': 'HASH'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.partition_keys) == 4
                assert gsi.has_multi_partition_keys()

            def test_parse_gsi_with_two_sort_keys(self):
                """Parse GSI with 2 RANGE keys."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithMultiKeyGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk1', 'AttributeType': 'N'},
                                {'AttributeName': 'gsi_sk2', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'MultiKeyGSI',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_sk1', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk2', 'KeyType': 'RANGE'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.sort_keys) == 2
                assert gsi.has_multi_sort_keys()

            def test_parse_gsi_with_three_sort_keys(self):
                """Parse GSI with 3 RANGE keys."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithMultiKeyGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk1', 'AttributeType': 'N'},
                                {'AttributeName': 'gsi_sk2', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk3', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'MultiKeyGSI',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_sk1', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk2', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk3', 'KeyType': 'RANGE'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.sort_keys) == 3
                assert gsi.has_multi_sort_keys()

            def test_parse_gsi_with_four_sort_keys(self):
                """Parse GSI with 4 RANGE keys (max allowed)."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithMultiKeyGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk1', 'AttributeType': 'N'},
                                {'AttributeName': 'gsi_sk2', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk3', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk4', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'MultiKeyGSI',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_sk1', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk2', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk3', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk4', 'KeyType': 'RANGE'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.sort_keys) == 4
                assert gsi.has_multi_sort_keys()

            def test_parse_gsi_with_multi_partition_and_sort_keys(self):
                """Parse GSI with multiple HASH and RANGE keys."""
                data = {
                    'tables': [
                        {
                            'TableName': 'TableWithMultiKeyGSI',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk2', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk1', 'AttributeType': 'N'},
                                {'AttributeName': 'gsi_sk2', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'MultiKeyGSI',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk1', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk2', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_sk1', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk2', 'KeyType': 'RANGE'},
                                    ],
                                    'Projection': {'ProjectionType': 'KEYS_ONLY'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert len(gsi.partition_keys) == 2
                assert len(gsi.sort_keys) == 2
                assert gsi.has_multi_partition_keys()
                assert gsi.has_multi_sort_keys()

            def test_has_multi_partition_keys_detection(self):
                """Verify has_multi_partition_keys() returns True."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk2', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk1', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk2', 'KeyType': 'HASH'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert gsi.has_multi_partition_keys() is True

            def test_has_multi_sort_keys_detection(self):
                """Verify has_multi_sort_keys() returns True."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk2', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_sk1', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk2', 'KeyType': 'RANGE'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert gsi.has_multi_sort_keys() is True

            def test_gsi_with_five_partition_keys_error(self):
                """Error: GSI has more than 4 partition keys."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk2', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk3', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk4', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk5', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk1', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk2', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk3', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk4', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_pk5', 'KeyType': 'HASH'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema must contain at most 4 HASH keys, found 5',
                ):
                    DataModel.from_json(data)

            def test_gsi_with_five_sort_keys_error(self):
                """Error: GSI has more than 4 sort keys."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk1', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk2', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk3', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk4', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_sk5', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                                        {'AttributeName': 'gsi_sk1', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk2', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk3', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk4', 'KeyType': 'RANGE'},
                                        {'AttributeName': 'gsi_sk5', 'KeyType': 'RANGE'},
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema must contain at most 4 RANGE keys, found 5',
                ):
                    DataModel.from_json(data)

            def test_gsi_missing_key_type(self):
                """Error: GSI KeySchema element missing KeyType."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [{'AttributeName': 'gsi_pk'}],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema\[0\]\.KeyType must be 'HASH' or 'RANGE'",
                ):
                    DataModel.from_json(data)

            def test_gsi_invalid_key_type(self):
                """Error: GSI KeySchema element has invalid KeyType."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [
                                        {'AttributeName': 'gsi_pk', 'KeyType': 'INVALID'}
                                    ],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r"tables\[0\]\.GlobalSecondaryIndexes\[0\]\.KeySchema\[0\]\.KeyType must be 'HASH' or 'RANGE'",
                ):
                    DataModel.from_json(data)

        class TestGSIProjection:
            """Test GSI projection configuration."""

            def test_projection_type_all(self):
                """Parse GSI with ProjectionType ALL."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [{'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}],
                                    'Projection': {'ProjectionType': 'ALL'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert gsi.projection_type == 'ALL'
                assert gsi.non_key_attributes == []

            def test_projection_type_keys_only(self):
                """Parse GSI with ProjectionType KEYS_ONLY."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [{'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}],
                                    'Projection': {'ProjectionType': 'KEYS_ONLY'},
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert gsi.projection_type == 'KEYS_ONLY'
                assert gsi.non_key_attributes == []

            def test_projection_type_include_with_attributes(self):
                """Parse GSI with ProjectionType INCLUDE and NonKeyAttributes."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'},
                                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'GlobalSecondaryIndexes': [
                                {
                                    'IndexName': 'GSI1',
                                    'KeySchema': [{'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}],
                                    'Projection': {
                                        'ProjectionType': 'INCLUDE',
                                        'NonKeyAttributes': ['attr1', 'attr2'],
                                    },
                                }
                            ],
                        }
                    ]
                }
                model = DataModel.from_json(data)
                assert model.tables[0].global_secondary_indexes is not None
                gsi = model.tables[0].global_secondary_indexes[0]
                assert gsi.projection_type == 'INCLUDE'
                assert gsi.non_key_attributes == ['attr1', 'attr2']

            class TestProjectionValidation:
                """Test projection validation rules."""

                def test_projection_include_without_attributes(self):
                    """Error: INCLUDE missing NonKeyAttributes."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {'ProjectionType': 'INCLUDE'},
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.NonKeyAttributes is required when ProjectionType is INCLUDE',
                    ):
                        DataModel.from_json(data)

                def test_projection_include_with_empty_attributes(self):
                    """Error: INCLUDE with empty NonKeyAttributes array."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {
                                            'ProjectionType': 'INCLUDE',
                                            'NonKeyAttributes': [],
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.NonKeyAttributes is required when ProjectionType is INCLUDE',
                    ):
                        DataModel.from_json(data)

                def test_projection_all_with_attributes(self):
                    """Error: ALL has NonKeyAttributes."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {
                                            'ProjectionType': 'ALL',
                                            'NonKeyAttributes': ['attr1'],
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.NonKeyAttributes is not allowed when ProjectionType is ALL',
                    ):
                        DataModel.from_json(data)

                def test_projection_keys_only_with_attributes(self):
                    """Error: KEYS_ONLY has NonKeyAttributes."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {
                                            'ProjectionType': 'KEYS_ONLY',
                                            'NonKeyAttributes': ['attr1'],
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.NonKeyAttributes is not allowed when ProjectionType is KEYS_ONLY',
                    ):
                        DataModel.from_json(data)

                def test_non_key_attributes_not_string(self):
                    """Error: NonKeyAttributes contains non-string."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {
                                            'ProjectionType': 'INCLUDE',
                                            'NonKeyAttributes': ['attr1', 123, 'attr3'],
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.NonKeyAttributes\[1\] must be a string',
                    ):
                        DataModel.from_json(data)

                def test_non_key_attributes_empty_string(self):
                    """Error: NonKeyAttributes contains empty string."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {
                                            'ProjectionType': 'INCLUDE',
                                            'NonKeyAttributes': ['attr1', '', 'attr3'],
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.NonKeyAttributes\[1\] must not be empty',
                    ):
                        DataModel.from_json(data)

                def test_invalid_projection_type(self):
                    """Error: Invalid ProjectionType value."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {
                                            'ProjectionType': 'INVALID_TYPE',
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r"tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.ProjectionType must be 'ALL', 'KEYS_ONLY', or 'INCLUDE'",
                    ):
                        DataModel.from_json(data)

                def test_non_key_attributes_not_array(self):
                    """Error: NonKeyAttributes is not an array."""
                    data = {
                        'tables': [
                            {
                                'TableName': 'Test',
                                'AttributeDefinitions': [
                                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                                    {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                                ],
                                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                'GlobalSecondaryIndexes': [
                                    {
                                        'IndexName': 'GSI1',
                                        'KeySchema': [
                                            {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'}
                                        ],
                                        'Projection': {
                                            'ProjectionType': 'INCLUDE',
                                            'NonKeyAttributes': 'not-an-array',
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                    with pytest.raises(
                        ValueError,
                        match=r'tables\[0\]\.GlobalSecondaryIndexes\[0\]\.Projection\.NonKeyAttributes must be an array',
                    ):
                        DataModel.from_json(data)

    class TestTableWithTTL:
        """Test adding TimeToLiveSpecification to table."""

        def test_parse_table_with_ttl_enabled(self):
            """Parse table with TTL enabled."""
            data = {
                'tables': [
                    {
                        'TableName': 'TableWithTTL',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        'TimeToLiveSpecification': {
                            'AttributeName': 'expiry_time',
                            'Enabled': True,
                        },
                    }
                ]
            }
            model = DataModel.from_json(data)
            table = model.tables[0]
            assert table.ttl_attribute == 'expiry_time'

        def test_parse_table_with_ttl_disabled(self):
            """Parse table with TTL disabled (ttl_attribute should be None)."""
            data = {
                'tables': [
                    {
                        'TableName': 'TableWithTTLDisabled',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                        'TimeToLiveSpecification': {
                            'AttributeName': 'expiry_time',
                            'Enabled': False,
                        },
                    }
                ]
            }
            model = DataModel.from_json(data)
            table = model.tables[0]
            assert table.ttl_attribute is None

        def test_parse_table_without_ttl(self):
            """Parse table without TTL specification."""
            data = {
                'tables': [
                    {
                        'TableName': 'TableWithoutTTL',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                    }
                ]
            }
            model = DataModel.from_json(data)
            table = model.tables[0]
            assert table.ttl_attribute is None

        class TestTTLValidation:
            """Test TTL validation rules."""

            def test_ttl_not_object(self):
                """Error: TimeToLiveSpecification not object."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'TimeToLiveSpecification': 'not_object',
                        }
                    ]
                }
                with pytest.raises(
                    ValueError, match=r'tables\[0\]\.TimeToLiveSpecification must be an object'
                ):
                    DataModel.from_json(data)

            def test_ttl_missing_enabled(self):
                """Error: Enabled field missing."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'TimeToLiveSpecification': {'AttributeName': 'expiry_time'},
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.TimeToLiveSpecification\.Enabled must be a boolean',
                ):
                    DataModel.from_json(data)

            def test_ttl_enabled_not_boolean(self):
                """Error: Enabled not boolean."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'TimeToLiveSpecification': {
                                'AttributeName': 'expiry_time',
                                'Enabled': 'true',
                            },
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.TimeToLiveSpecification\.Enabled must be a boolean',
                ):
                    DataModel.from_json(data)

            def test_ttl_missing_attribute_name_when_enabled(self):
                """Error: AttributeName missing when Enabled=true."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'TimeToLiveSpecification': {'Enabled': True},
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.TimeToLiveSpecification\.AttributeName must be a string',
                ):
                    DataModel.from_json(data)

            def test_ttl_attribute_name_not_string(self):
                """Error: AttributeName not string."""
                data = {
                    'tables': [
                        {
                            'TableName': 'Test',
                            'AttributeDefinitions': [
                                {'AttributeName': 'pk', 'AttributeType': 'S'}
                            ],
                            'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                            'TimeToLiveSpecification': {'AttributeName': 123, 'Enabled': True},
                        }
                    ]
                }
                with pytest.raises(
                    ValueError,
                    match=r'tables\[0\]\.TimeToLiveSpecification\.AttributeName must be a string',
                ):
                    DataModel.from_json(data)

    class TestMultipleTables:
        """Test data model with multiple tables."""

        def test_parse_multiple_tables(self):
            """Parse data model with 2+ tables."""
            data = {
                'tables': [
                    {
                        'TableName': 'Table1',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                    },
                    {
                        'TableName': 'Table2',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'N'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                    },
                ]
            }
            model = DataModel.from_json(data)
            assert len(model.tables) == 2
            assert model.tables[0].table_name == 'Table1'
            assert model.tables[1].table_name == 'Table2'

        def test_second_table_error_shows_correct_index(self):
            """Error in second table shows tables[1]."""
            data = {
                'tables': [
                    {
                        'TableName': 'Table1',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                    },
                    {
                        'TableName': 'Table2',
                        'AttributeDefinitions': [
                            {'AttributeName': 'pk', 'AttributeType': 'INVALID'}
                        ],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                    },
                ]
            }
            with pytest.raises(
                ValueError,
                match=r"tables\[1\]\.AttributeDefinitions\[0\]\.AttributeType must be 'S', 'N', or 'B'",
            ):
                DataModel.from_json(data)

        def test_duplicate_table_names(self):
            """Error: multiple tables have same name."""
            data = {
                'tables': [
                    {
                        'TableName': 'DuplicateTable',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                    },
                    {
                        'TableName': 'DuplicateTable',
                        'AttributeDefinitions': [{'AttributeName': 'pk', 'AttributeType': 'S'}],
                        'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                    },
                ]
            }
            with pytest.raises(
                ValueError,
                match=r'Data model contains duplicate table names\. table_names: DuplicateTable',
            ):
                DataModel.from_json(data)
