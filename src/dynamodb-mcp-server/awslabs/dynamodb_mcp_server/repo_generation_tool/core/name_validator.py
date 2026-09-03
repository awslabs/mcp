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

"""Validation of schema-supplied names that are interpolated into generated source code.

The generators render source code through Jinja2 with autoescaping disabled, because
autoescaping is HTML-oriented and would corrupt code syntax. Nothing downstream escapes
schema values, so every name taken from schema.json reaches the generated source verbatim.
This module is the gate that makes that safe: a name that could alter the structure of the
generated code is rejected here, before any template is rendered.

Names land in two kinds of position in the generated code, and each needs a different rule:

Identifier positions
    Class names, ``def`` names, parameter names, attribute accesses and import names --
    for example ``class {{ entity_name }}`` and ``{{ field.name }}: str``. Escaping is not
    possible in an identifier position, so the value must itself be a valid, non-keyword
    Python identifier. This is not a new restriction in practice: a value that is not an
    identifier has never produced importable generated code, it produced a SyntaxError or
    silently broken output.

String-literal positions
    Values that only ever appear inside a quoted string, a docstring or a comment -- for
    example ``entity_type="{{ entity_config.entity_type }}"``. DynamoDB itself allows
    almost any character in an attribute name, so these are deliberately NOT restricted to
    an identifier; they are checked only for the few characters that let a value escape its
    enclosing context: quotes and backslashes (which terminate a string literal), and
    newlines (which end a comment and can close a docstring). Ordinary characters such as
    spaces, ``#`` and non-ASCII text remain valid.

Key templates
    ``pk_template`` / ``sk_template`` need a third rule because they are rendered into
    f-strings, where ``{`` and ``}`` are live expression syntax rather than literal text.
    A brace region that does not match the supported ``{placeholder}`` form is rejected, so
    a value like ``{__import__('os').system('...')}`` cannot reach an f-string and execute
    when the generated module is imported. Note that this is not covered by the placeholder
    extraction in KeyTemplateParser: that regex matches only a brace region whose contents are
    word characters, and silently ignores any other brace region, which is the dangerous case.
"""

import keyword
import re
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
)


# Characters that let a value break out of the context it is interpolated into.
# Quotes and backslashes terminate or escape a Python string literal; newlines end a
# comment and can close a docstring, turning the remainder of the value into live code.
_LITERAL_BREAKING_CHARS: dict[str, str] = {
    '"': 'double quote',
    "'": 'single quote',
    '\\': 'backslash',
    '\n': 'newline',
    '\r': 'carriage return',
}

# A brace region inside a key template must be a supported placeholder: a parameter name
# with an optional format spec, e.g. {user_id} or {score:05d}. Anything else, including a
# stray or unmatched brace, is rejected because these templates are rendered into
# f-strings where braces are executable syntax.
_PLACEHOLDER_PATTERN = re.compile(r'\{(\w+)(?::[^{}]*)?\}')
_ANY_BRACE_REGION = re.compile(r'\{[^{}]*\}|[{}]')

# A value that is concatenated into a larger identifier only has to be made of identifier
# characters; it may start with a digit because it never stands alone.
_IDENTIFIER_FRAGMENT_PATTERN = re.compile(r'[A-Za-z0-9_]+')


def _describe_breaking_chars(value: str) -> list[str]:
    """Return human-readable names of the literal-breaking characters present in value."""
    return [name for char, name in _LITERAL_BREAKING_CHARS.items() if char in value]


def validate_python_identifier(value: object, field_path: str) -> list[ValidationError]:
    """Validate a name that reaches an identifier position in the generated code.

    Args:
        value: The name to validate
        field_path: Full field path for error messages, e.g. 'tables[0].entities.User'

    Returns:
        List of validation errors, empty when the name is a safe identifier
    """
    if not isinstance(value, str):
        return [
            ValidationError(
                path=field_path,
                message=f'Name must be a string, found {type(value).__name__}',
                suggestion='Use a string that is a valid Python identifier',
            )
        ]

    if not value.isidentifier():
        return [
            ValidationError(
                path=field_path,
                message=(
                    f"Name '{value}' is not a valid Python identifier, so it cannot be used "
                    'in generated code'
                ),
                suggestion=(
                    'Use only letters, digits and underscores, and do not start with a digit'
                ),
            )
        ]

    # Soft keywords (match, case, type, _) are only reserved in specific syntactic
    # positions, but they are rejected here too: they are never a sensible name and
    # allowing them would make the safety of the generated code depend on context.
    if keyword.iskeyword(value) or keyword.issoftkeyword(value):
        return [
            ValidationError(
                path=field_path,
                message=f"Name '{value}' is a reserved Python keyword",
                suggestion='Choose a name that is not a Python keyword',
            )
        ]

    return []


def validate_identifier_fragment(value: object, field_path: str) -> list[ValidationError]:
    """Validate a value that is concatenated into a larger generated identifier.

    Used for values that only ever appear as a suffix, such as a GSI name in
    ``build_gsi_pk_for_lookup_{{ safe_name }}``. Because the value never stands alone it may
    begin with a digit and may coincide with a keyword -- ``..._lookup_0`` and
    ``..._lookup_class`` are both valid identifiers -- so only the character set is checked.

    Args:
        value: The fragment to validate
        field_path: Full field path for error messages

    Returns:
        List of validation errors, empty when the fragment is safe to concatenate
    """
    if not isinstance(value, str):
        return [
            ValidationError(
                path=field_path,
                message=f'Name must be a string, found {type(value).__name__}',
                suggestion='Use a string containing only letters, digits and underscores',
            )
        ]

    if not _IDENTIFIER_FRAGMENT_PATTERN.fullmatch(value):
        return [
            ValidationError(
                path=field_path,
                message=(
                    f"Name '{value}' cannot be used to build a method name in the generated code"
                ),
                suggestion=(
                    'Use only letters, digits, underscores and hyphens (a hyphen is '
                    'converted to an underscore)'
                ),
            )
        ]

    return []


def validate_literal_safe(
    value: object, field_path: str, *, allow_braces: bool = False
) -> list[ValidationError]:
    """Validate a name that only reaches string-literal, docstring or comment positions.

    Any character DynamoDB permits is accepted except those that would let the value
    escape its enclosing string literal, docstring or comment.

    Args:
        value: The value to validate
        field_path: Full field path for error messages
        allow_braces: Permit braces, for a key template whose brace regions are checked
            separately by validate_key_template. Leave this False for every other value:
            some string-literal positions are f-strings, where a brace executes.

    Returns:
        List of validation errors, empty when the value cannot break out of a literal
    """
    if not isinstance(value, str):
        return [
            ValidationError(
                path=field_path,
                message=f'Value must be a string, found {type(value).__name__}',
                suggestion='Use a string value',
            )
        ]

    found = _describe_breaking_chars(value)

    # Braces are rejected unless the caller is validating a key template, which uses them
    # for placeholders and checks each brace region itself. Several values that reach only
    # string literals (a table name, for example) are also rendered inside f-strings in the
    # usage examples, where a brace is a live expression rather than literal text, so a
    # brace alone is enough to inject code without ever closing the quote.
    if not allow_braces and ('{' in value or '}' in value):
        found.append('brace')

    if found:
        return [
            ValidationError(
                path=field_path,
                message=(
                    f'Value must not contain {", ".join(found)}, because it is written into '
                    'generated source code'
                ),
                suggestion=(
                    'Remove quote, backslash, newline and brace characters from the value'
                ),
            )
        ]

    return []


def validate_prose_safe(value: object, field_path: str) -> list[ValidationError]:
    """Validate free-text prose, such as an access pattern description.

    Prose is held to a different rule than a name because an apostrophe is ordinary in
    English ("Get courier's active delivery") and rejecting it would be a pointless
    restriction. Every position a description reaches is a docstring, a comment or a
    double-quoted string, so an apostrophe cannot terminate any of them.

    A double quote, backslash and newline are still rejected, and so are braces: one
    description site is rendered inside an f-string, where a brace is a live expression
    rather than literal text.

    Args:
        value: The prose value to validate
        field_path: Full field path for error messages

    Returns:
        List of validation errors, empty when the prose cannot break out of its context
    """
    if not isinstance(value, str):
        return [
            ValidationError(
                path=field_path,
                message=f'Value must be a string, found {type(value).__name__}',
                suggestion='Use a string value',
            )
        ]

    found = [
        name for char, name in _LITERAL_BREAKING_CHARS.items() if char != "'" and char in value
    ]
    if '{' in value or '}' in value:
        found.append('brace')

    if found:
        return [
            ValidationError(
                path=field_path,
                message=(
                    f'Value must not contain {", ".join(found)}, because it is written into '
                    'generated source code'
                ),
                suggestion=(
                    'Remove double quote, backslash, newline and brace characters; an '
                    'apostrophe is allowed'
                ),
            )
        ]

    return []


def validate_default_value(value: object, field_path: str) -> list[ValidationError]:
    """Validate a parameter default, which is rendered into a generated def signature.

    A default is emitted as an expression in the signature, so it is evaluated when the
    module is imported rather than when the method is called. A string default that escapes
    its quotes therefore executes at import time.

    Only string defaults need checking. A non-string default taken from JSON is one of
    int, float, bool, None, list or dict, and is rendered through Python's own repr of the
    parsed value, which quotes and escapes its contents correctly.

    Args:
        value: The default value to validate
        field_path: Full field path for error messages

    Returns:
        List of validation errors, empty when the default is safe to render
    """
    if not isinstance(value, str):
        return []

    return validate_literal_safe(value, field_path)


def validate_key_template(value: object, field_path: str) -> list[ValidationError]:
    """Validate a pk_template / sk_template value.

    Key templates are rendered into f-strings, so in addition to the literal-safety rule
    every brace region must be a supported ``{placeholder}`` and every placeholder name
    must be a usable identifier.

    Args:
        value: The template to validate
        field_path: Full field path for error messages

    Returns:
        List of validation errors, empty when the template is safe to render
    """
    errors = validate_literal_safe(value, field_path, allow_braces=True)
    if errors:
        return errors

    # validate_literal_safe has already rejected a non-string, but the check is repeated
    # rather than asserted: an assert is removed under python -O, and this is a security
    # boundary that must not depend on assertions being enabled.
    if not isinstance(value, str):
        return [
            ValidationError(
                path=field_path,
                message=f'Template must be a string, found {type(value).__name__}',
                suggestion='Use a string template such as USER#{user_id}',
            )
        ]

    for region in _ANY_BRACE_REGION.findall(value):
        if not _PLACEHOLDER_PATTERN.fullmatch(region):
            return [
                ValidationError(
                    path=field_path,
                    message=(
                        f"Template '{value}' contains an unsupported brace expression '{region}'"
                    ),
                    suggestion=(
                        'Use placeholders of the form {field_name} or {field_name:format}, '
                        'and do not use a bare { or } character'
                    ),
                )
            ]

    for placeholder_name in _PLACEHOLDER_PATTERN.findall(value):
        placeholder_errors = validate_python_identifier(
            placeholder_name, f'{field_path} placeholder {{{placeholder_name}}}'
        )
        if placeholder_errors:
            return placeholder_errors

    return []
