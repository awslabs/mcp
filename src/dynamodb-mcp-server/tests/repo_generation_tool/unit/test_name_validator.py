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

"""Tests for name validation of values interpolated into generated source code.

The generators render code with Jinja2 autoescaping disabled, so a schema name that can
alter the structure of the generated code must be rejected during schema validation. These
tests cover the validator directly and then assert end to end that a hostile schema does not
produce a generated file.
"""

import copy
import json
import keyword
import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.codegen import generate
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.name_validator import (
    validate_default_value,
    validate_identifier_fragment,
    validate_key_template,
    validate_literal_safe,
    validate_prose_safe,
    validate_python_identifier,
)


class TestValidatePythonIdentifier:
    """Names that reach identifier positions must be usable Python identifiers."""

    @pytest.mark.parametrize('value', ['user_id', 'User', '_private', 'a1', 'CamelCase'])
    def test_accepts_valid_identifiers(self, value):
        """A valid, non-keyword identifier is accepted."""
        assert validate_python_identifier(value, 'path') == []

    @pytest.mark.parametrize(
        'value',
        [
            'has space',
            '1leading_digit',
            'has-hyphen',
            'has.dot',
            '',
            'trailing_newline\n',
            "_ = None\n    __import__('os').system('id')\n    _j",
            'quote"inside',
        ],
    )
    def test_rejects_non_identifiers(self, value):
        """A value that is not a valid identifier is rejected."""
        errors = validate_python_identifier(value, 'path')
        assert len(errors) == 1
        assert errors[0].path == 'path'

    @pytest.mark.parametrize('value', ['class', 'def', 'import', 'return', 'lambda'])
    def test_rejects_keywords(self, value):
        """A reserved keyword is rejected."""
        assert validate_python_identifier(value, 'path') != []

    @pytest.mark.parametrize('value', keyword.softkwlist)
    def test_rejects_soft_keywords(self, value):
        """A soft keyword is rejected.

        Which names are soft keywords depends on the Python version, so the set is taken
        from the keyword module rather than hard-coded.
        """
        if not value.isidentifier():
            pytest.skip(f'{value!r} is not an identifier on this Python version')
        assert validate_python_identifier(value, 'path') != []

    @pytest.mark.parametrize('value', [None, 1, [], {}])
    def test_rejects_non_strings(self, value):
        """A non-string value is reported rather than raising."""
        assert validate_python_identifier(value, 'path') != []


class TestValidateIdentifierFragment:
    """Names concatenated into a larger identifier only need identifier characters."""

    @pytest.mark.parametrize('value', ['ByEmail', '0', 'a_b', '2024', 'x1'])
    def test_accepts_identifier_characters(self, value):
        """A fragment may start with a digit because it never stands alone."""
        assert validate_identifier_fragment(value, 'path') == []

    @pytest.mark.parametrize('value', ['{', 'has space', 'a(b', 'x\ny', '', 'a"b'])
    def test_rejects_other_characters(self, value):
        """A fragment containing anything else is rejected."""
        assert validate_identifier_fragment(value, 'path') != []


class TestValidateLiteralSafe:
    """Values reaching string literals may be anything that cannot break out of one."""

    @pytest.mark.parametrize(
        'value',
        ['pk', 'attr name', 'has-hyphen', 'has.dot', 'unicode café', 'hash#inside'],
    )
    def test_accepts_values_that_cannot_escape_a_literal(self, value):
        """DynamoDB permits these, and none of them can terminate a literal."""
        assert validate_literal_safe(value, 'path') == []

    @pytest.mark.parametrize(
        'value',
        [
            'ends"here',
            "ends'here",
            'back\\slash',
            'new\nline',
            'carriage\rreturn',
            'Users"; __import__("os").system("id"); x = "',
            # Braces are rejected because several string-literal sites are f-strings, where
            # a brace is a live expression and no quote needs to be closed.
            'a{b}',
            'Users{__import__("os").system("id")}',
        ],
    )
    def test_rejects_literal_breaking_characters(self, value):
        """Quotes, backslashes, newlines and braces are rejected."""
        assert validate_literal_safe(value, 'path') != []

    def test_allows_braces_when_caller_opts_in(self):
        """A key template checks its own brace regions, so it opts out of the brace rule."""
        assert validate_literal_safe('USER#{id}', 'path', allow_braces=True) == []
        assert validate_literal_safe('USER#{id}', 'path') != []


class TestValidateDefaultValue:
    """A parameter default is an expression in a def signature, evaluated at import."""

    @pytest.mark.parametrize('value', ['abc', 'a b', 10, 1.5, True, None, [], {}])
    def test_accepts_safe_defaults(self, value):
        """Ordinary defaults, including non-strings, are accepted."""
        assert validate_default_value(value, 'path') == []

    @pytest.mark.parametrize(
        'value',
        [
            '" or __import__("os").system("id") or "',
            'a"b',
            'back\\slash',
            'new\nline',
            'brace{here}',
        ],
    )
    def test_rejects_string_defaults_that_escape_the_literal(self, value):
        """A string default that can break out of its quotes is rejected."""
        assert validate_default_value(value, 'path') != []


class TestValidateKeyTemplate:
    """Key templates are rendered into f-strings, so braces are executable syntax."""

    @pytest.mark.parametrize(
        'value',
        ['USER#{user_id}', 'PROFILE#{id}#{ts}', 'STATIC', '{score:05d}', '{price:.2f}'],
    )
    def test_accepts_supported_placeholders(self, value):
        """Supported placeholder forms, including format specs, are accepted."""
        assert validate_key_template(value, 'path') == []

    @pytest.mark.parametrize(
        'value',
        [
            # A brace expression that is not a placeholder becomes a live f-string
            # expression. KeyTemplateParser's own regex ignores these, which is why they
            # must be rejected here.
            "USER#{__import__('os').system('id')}",
            '{obj.attr}',
            'unmatched{',
            'unmatched}',
            'A#{user_id}}',
            '{}',
            # A placeholder name that is not a usable identifier reaches a lambda parameter.
            '{1bad}',
            # Breaking out of the enclosing f-string quote.
            'USER#{user_id}"; __import__("os").system("id"); #',
        ],
    )
    def test_rejects_unsupported_brace_expressions(self, value):
        """Anything other than a supported placeholder is rejected."""
        assert validate_key_template(value, 'path') != []


class TestValidateProseSafe:
    """Descriptions are prose, so an apostrophe is allowed but break-out characters are not."""

    @pytest.mark.parametrize(
        'value',
        [
            "Get courier's current active delivery",
            'Update a record (idempotent) - see docs',
            'Fetch by id & status, 50% of the time',
            'unicode café',
        ],
    )
    def test_accepts_ordinary_prose(self, value):
        """Real descriptions, including apostrophes, are accepted."""
        assert validate_prose_safe(value, 'path') == []

    @pytest.mark.parametrize(
        'value',
        [
            'ends"here',
            'back\\slash',
            'new\nline',
            'brace{here}',
            'd"""\n    __import__("os").system("id")\n    """',
        ],
    )
    def test_rejects_break_out_characters(self, value):
        """Double quotes, backslashes, newlines and braces are rejected."""
        assert validate_prose_safe(value, 'path') != []


class TestNonStringValues:
    """Every validator reports a non-string value rather than raising."""

    @pytest.mark.parametrize(
        'validator',
        [
            validate_identifier_fragment,
            validate_literal_safe,
            validate_prose_safe,
            validate_key_template,
        ],
    )
    @pytest.mark.parametrize('value', [None, 1, [], {}, True])
    def test_reports_non_string(self, validator, value):
        """A non-string is rejected with an error, not an exception."""
        errors = validator(value, 'path')
        assert len(errors) == 1
        assert errors[0].path == 'path'


BENIGN_SCHEMA = {
    'tables': [
        {
            'table_config': {
                'table_name': 'Users',
                # A space is legal in a DynamoDB attribute name and must stay accepted.
                'partition_key': 'attr name',
                'sort_key': 'sk',
            },
            'entities': {
                'User': {
                    'entity_type': 'USER',
                    'pk_template': 'USER#{user_id}',
                    'sk_template': 'PROFILE#{created_at}',
                    'fields': [
                        {'name': 'user_id', 'type': 'string', 'required': True},
                        {'name': 'created_at', 'type': 'string', 'required': True},
                    ],
                    'access_patterns': [
                        {
                            'pattern_id': 1,
                            'name': 'get_user',
                            'description': "Fetch a user's record",
                            'operation': 'GetItem',
                            'return_type': 'single_entity',
                            'parameters': [{'name': 'user_id', 'type': 'string'}],
                        }
                    ],
                }
            },
        }
    ]
}


def _schema_with(mutate):
    """Return a copy of the benign schema with a mutation applied."""
    schema = copy.deepcopy(BENIGN_SCHEMA)
    mutate(schema)
    return schema


def _entity(schema):
    """Return the single entity config from a schema copy."""
    return schema['tables'][0]['entities']['User']


PAYLOAD_IDENTIFIER = "_ = None\n    __import__('os').system('id')\n    _j"
PAYLOAD_LITERAL = 'x"; __import__("os").system("id"); y = "'


HOSTILE_SCHEMAS = {
    'field_name': lambda s: _entity(s)['fields'].append(
        {'name': PAYLOAD_IDENTIFIER, 'type': 'string', 'required': False}
    ),
    'entity_name': lambda s: s['tables'][0]['entities'].update(
        {"Bad:\n    __import__('os').system('id')\nclass X": _entity(s)}
    ),
    'pk_template_brace': lambda s: _entity(s).__setitem__(
        'pk_template', "USER#{__import__('os').system('id')}"
    ),
    'pk_template_quote': lambda s: _entity(s).__setitem__(
        'pk_template', 'USER#{user_id}"; __import__("os").system("id"); #'
    ),
    'entity_type': lambda s: _entity(s).__setitem__('entity_type', PAYLOAD_LITERAL),
    'table_name': lambda s: s['tables'][0]['table_config'].__setitem__(
        'table_name', PAYLOAD_LITERAL
    ),
    'partition_key': lambda s: s['tables'][0]['table_config'].__setitem__(
        'partition_key', PAYLOAD_LITERAL
    ),
    'pattern_name': lambda s: _entity(s)['access_patterns'][0].__setitem__(
        'name', PAYLOAD_IDENTIFIER
    ),
    'pattern_description': lambda s: _entity(s)['access_patterns'][0].__setitem__(
        'description', 'd"""\n    __import__("os").system("id")\n    """'
    ),
    'parameter_name': lambda s: _entity(s)['access_patterns'][0]['parameters'].append(
        {'name': PAYLOAD_IDENTIFIER, 'type': 'string'}
    ),
    'gsi_mapping_name': lambda s: _entity(s).__setitem__(
        'gsi_mappings', [{'name': PAYLOAD_IDENTIFIER, 'pk_template': '{user_id}'}]
    ),
    'gsi_mapping_template': lambda s: _entity(s).__setitem__(
        'gsi_mappings',
        [{'name': 'ByEmail', 'pk_template': "E#{__import__('os').system('id')}"}],
    ),
    'index_name_newline': lambda s: _entity(s)['access_patterns'][0].__setitem__(
        'index_name', "ix\n    __import__('os').system('id')"
    ),
    # Cross-table patterns drive the transaction service template, where the pattern name
    # becomes a def name and the description becomes its docstring.
    'cross_table_pattern_name': lambda s: s.__setitem__(
        'cross_table_access_patterns',
        [
            {
                'pattern_id': 90,
                'name': PAYLOAD_IDENTIFIER,
                'description': 'x',
                'operation': 'TransactWrite',
                'entities_involved': ['User'],
                'parameters': [{'name': 'user_id', 'type': 'string'}],
                'return_type': 'success_flag',
            }
        ],
    ),
    'cross_table_pattern_description': lambda s: s.__setitem__(
        'cross_table_access_patterns',
        [
            {
                'pattern_id': 91,
                'name': 'do_tx',
                'description': 'd"""\n    __import__("os").system("id")\n    """',
                'operation': 'TransactWrite',
                'entities_involved': ['User'],
                'parameters': [{'name': 'user_id', 'type': 'string'}],
                'return_type': 'success_flag',
            }
        ],
    ),
    # A parameter default is rendered into a def signature, which Python evaluates at import.
    'parameter_default': lambda s: _entity(s)['access_patterns'][0]['parameters'][0].__setitem__(
        'default', '" or __import__("os").system("id") or "'
    ),
    # A parameter description reaches the generated method docstring.
    'parameter_description': lambda s: _entity(s)['access_patterns'][0]['parameters'][
        0
    ].__setitem__('description', 'd"""\n    __import__("os").system("id")\n    """'),
    # A brace in a table name is a live expression in the usage-example f-strings.
    'table_name_brace': lambda s: s['tables'][0]['table_config'].__setitem__(
        'table_name', 'Users{__import__("os").system("id")}'
    ),
    'partition_key_brace': lambda s: s['tables'][0]['table_config'].__setitem__(
        'partition_key', 'pk{__import__("os").system("id")}'
    ),
    # Table-level GSI key attributes reach Key('...') literals in generated query code.
    'gsi_list_partition_key': lambda s: s['tables'][0].__setitem__(
        'gsi_list',
        [{'name': 'ByX', 'partition_key': PAYLOAD_LITERAL, 'sort_key': 'gsi_sk'}],
    ),
    'gsi_list_name': lambda s: s['tables'][0].__setitem__(
        'gsi_list',
        [{'name': "ByX\n    __import__('os').system('id')", 'partition_key': 'gsi_pk'}],
    ),
    # A composite GSI key is a list of attribute names, each reaching a Key('...') literal.
    'gsi_list_composite_partition_key': lambda s: s['tables'][0].__setitem__(
        'gsi_list',
        [{'name': 'ByX', 'partition_key': ['gsi_pk', PAYLOAD_LITERAL]}],
    ),
    'gsi_list_composite_sort_key': lambda s: s['tables'][0].__setitem__(
        'gsi_list',
        [{'name': 'ByX', 'partition_key': 'gsi_pk', 'sort_key': ['a', PAYLOAD_LITERAL]}],
    ),
    'gsi_list_included_attributes': lambda s: s['tables'][0].__setitem__(
        'gsi_list',
        [
            {
                'name': 'ByX',
                'partition_key': 'gsi_pk',
                'projection_type': 'INCLUDE',
                'included_attributes': ['ok', PAYLOAD_LITERAL],
            }
        ],
    ),
}


def _write_schema(tmp_path, schema):
    """Write a schema dict to tmp_path and return its path."""
    schema_path = tmp_path / 'schema.json'
    schema_path.write_text(json.dumps(schema), encoding='utf-8')
    return schema_path


class TestGenerationRejectsInjection:
    """A hostile schema must not produce generated code."""

    def test_benign_schema_still_generates(self, tmp_path):
        """The fix must not reject a legitimate schema."""
        schema_path = _write_schema(tmp_path, copy.deepcopy(BENIGN_SCHEMA))
        out_dir = tmp_path / 'out'

        result = generate(
            str(schema_path),
            output_dir=str(out_dir),
            language='python',
            generate_sample_usage=False,
            no_lint=True,
            allowed_base_dirs=[tmp_path],
        )

        assert result.success, [e.message for e in result.validation_result.errors]
        assert (out_dir / 'entities.py').exists()

    @pytest.mark.parametrize('vector', sorted(HOSTILE_SCHEMAS))
    def test_hostile_schema_is_rejected_before_rendering(self, vector, tmp_path):
        """Each injection vector fails validation and writes no code."""
        schema_path = _write_schema(tmp_path, _schema_with(HOSTILE_SCHEMAS[vector]))
        out_dir = tmp_path / 'out'

        result = generate(
            str(schema_path),
            output_dir=str(out_dir),
            language='python',
            generate_sample_usage=False,
            no_lint=True,
            allowed_base_dirs=[tmp_path],
        )

        assert not result.success, f'{vector} was not rejected'
        assert not (out_dir / 'entities.py').exists(), f'{vector} wrote generated code'

    def test_malformed_gsi_list_entry_does_not_crash(self, tmp_path):
        """A gsi_list entry that is not an object is skipped by the name checks.

        Structural validation reports the malformed entry; the name checks must not raise
        while walking past it.
        """
        schema = _schema_with(
            lambda s: s['tables'][0].__setitem__('gsi_list', ['not-an-object', 42])
        )
        schema_path = _write_schema(tmp_path, schema)

        result = generate(
            str(schema_path),
            output_dir=str(tmp_path / 'out'),
            language='python',
            generate_sample_usage=False,
            no_lint=True,
            allowed_base_dirs=[tmp_path],
        )

        assert not result.success
