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

"""Tests for the models module — BaseSchema exclude_none behavior."""

import json
import pydantic_core
from awslabs.redshift_mcp_server.models import BaseSchema
from pydantic import Field
from typing import Optional


class DummySchema(BaseSchema):
    """Minimal test schema to verify BaseSchema behavior."""

    required_field: str = Field(..., description='Always present')
    optional_field: Optional[str] = Field(None, description='May be None')
    optional_int: Optional[int] = Field(None, description='May be None')


class TestBaseSchemaExcludeNone:
    """Tests for BaseSchema exclude_none serialization."""

    def test_model_dump_excludes_none(self):
        """Test that model_dump excludes None fields."""
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)
        dumped = obj.model_dump()

        assert dumped == {'required_field': 'hello'}
        assert 'optional_field' not in dumped
        assert 'optional_int' not in dumped

    def test_model_dump_json_excludes_none(self):
        """Test that model_dump_json excludes None fields."""
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)
        parsed = json.loads(obj.model_dump_json())

        assert parsed == {'required_field': 'hello'}
        assert 'optional_field' not in parsed

    def test_pydantic_core_to_json_excludes_none(self):
        """Test that pydantic_core.to_json also excludes None fields.

        This is the serialization path used by FastMCP when converting tool results
        to TextContent. Without the model_serializer, this would include all None fields.
        """
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)
        raw_json = pydantic_core.to_json(obj, indent=2)
        parsed = json.loads(raw_json)

        assert parsed == {'required_field': 'hello'}
        assert 'optional_field' not in parsed
        assert 'optional_int' not in parsed

    def test_model_dump_preserves_non_none(self):
        """Test that non-None optional fields are preserved."""
        obj = DummySchema(required_field='hello', optional_field='world', optional_int=42)
        dumped = obj.model_dump()

        assert dumped == {'required_field': 'hello', 'optional_field': 'world', 'optional_int': 42}

    def test_json_size_reduction(self):
        """Test that excluding None reduces JSON size."""
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)

        json_without = pydantic_core.to_json(obj)
        json_with = json.dumps(
            {'required_field': 'hello', 'optional_field': None, 'optional_int': None}
        ).encode()

        assert len(json_without) < len(json_with)

    def test_nested_model_excludes_none_recursively(self):
        """Nested BaseSchema models also exclude None when serialized together."""

        class Inner(BaseSchema):
            name: str = Field(...)
            value: Optional[int] = Field(default=None)

        class Outer(BaseSchema):
            label: str = Field(...)
            items: list[Inner] = Field(default_factory=list)
            note: Optional[str] = Field(default=None)

        obj = Outer(
            label='test',
            items=[Inner(name='a', value=None), Inner(name='b', value=42)],
        )
        dumped = obj.model_dump()

        assert 'note' not in dumped
        assert dumped['items'][0] == {'name': 'a'}
        assert dumped['items'][1] == {'name': 'b', 'value': 42}

    def test_false_and_zero_values_preserved(self):
        """Falsy non-None values (False, 0, empty string) are preserved."""
        obj = DummySchema(required_field='', optional_field='', optional_int=0)
        dumped = obj.model_dump()

        assert dumped['required_field'] == ''
        assert dumped['optional_field'] == ''
        assert dumped['optional_int'] == 0
