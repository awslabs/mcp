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

"""Unit tests for validators module."""

from awslabs.aws_appsync_mcp_server.validators import (
    get_dangerous_patterns,
    validate_graphql_schema,
)


class TestValidateGraphQLSchema:
    """Test cases for validate_graphql_schema function."""

    def test_empty_schema(self):
        """Test validation of empty schema."""
        issues = validate_graphql_schema('')
        assert 'Schema definition cannot be empty' in issues

    def test_whitespace_only_schema(self):
        """Test validation of whitespace-only schema."""
        issues = validate_graphql_schema('   \n\t  ')
        assert 'Schema definition cannot be empty' in issues

    def test_valid_schema(self):
        """Test validation of valid schema."""
        schema = """
        type Query {
            hello: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert len(issues) == 0

    def test_missing_query_type(self):
        """Test validation when Query type is missing."""
        schema = """
        type User {
            id: ID!
            name: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert 'Schema must include a Query type' in issues

    def test_unbalanced_braces_more_open(self):
        """Test validation with more opening braces."""
        schema = """
        type Query {
            hello: String
            nested: {
        """
        issues = validate_graphql_schema(schema)
        assert any('Unbalanced braces' in issue for issue in issues)

    def test_unbalanced_braces_more_close(self):
        """Test validation with more closing braces."""
        schema = """
        type Query {
            hello: String
        }}
        """
        issues = validate_graphql_schema(schema)
        assert any('Unbalanced braces' in issue for issue in issues)

    def test_single_dangerous_pattern(self):
        """Test detection of single dangerous pattern."""
        schema = """
        type Query {
            hello: String
            # This contains rm command
        }
        """
        issues = validate_graphql_schema(schema)
        assert any(
            'Potentially dangerous patterns detected in the schema: rm' in issue
            for issue in issues
        )

    def test_multiple_dangerous_patterns(self):
        """Test detection of multiple dangerous patterns."""
        schema = """
        type Query {
            hello: String
            # This contains rm and sudo commands
        }
        """
        issues = validate_graphql_schema(schema)
        dangerous_issue = next(
            (
                issue
                for issue in issues
                if 'Potentially dangerous patterns detected in the schema:' in issue
            ),
            None,
        )
        assert dangerous_issue is not None
        assert 'rm' in dangerous_issue
        assert 'sudo' in dangerous_issue

    def test_no_dangerous_patterns(self):
        """Test schema with no dangerous patterns."""
        schema = """
        type Query {
            user(id: ID!): User
        }

        type User {
            id: ID!
            name: String!
            email: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert not any(
            'Potentially dangerous patterns detected in the schema:' in issue for issue in issues
        )

    def test_case_insensitive_query_detection(self):
        """Test that Query type detection is case insensitive."""
        schema = """
        type query {
            hello: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert not any('Schema must include a Query type' in issue for issue in issues)

    def test_complex_valid_schema(self):
        """Test validation of complex but valid schema."""
        schema = """
        type Query {
            users: [User!]!
            user(id: ID!): User
        }

        type Mutation {
            createUser(input: CreateUserInput!): User
        }

        type User {
            id: ID!
            name: String!
            posts: [Post!]!
        }

        type Post {
            id: ID!
            title: String!
            author: User!
        }

        input CreateUserInput {
            name: String!
        }
        """
        issues = validate_graphql_schema(schema)
        assert len(issues) == 0


class TestGetDangerousPatterns:
    """Test cases for get_dangerous_patterns function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        patterns = get_dangerous_patterns()
        assert isinstance(patterns, list)

    def test_contains_expected_patterns(self):
        """Test that function returns expected dangerous patterns."""
        patterns = get_dangerous_patterns()
        expected_patterns = ['|', ';', 'rm', 'sudo', 'cmd', 'powershell']
        for pattern in expected_patterns:
            assert pattern in patterns

    def test_non_empty_list(self):
        """Test that function returns non-empty list."""
        patterns = get_dangerous_patterns()
        assert len(patterns) > 0

    def test_contains_unix_patterns(self):
        """Test that function includes Unix-specific patterns."""
        patterns = get_dangerous_patterns()
        unix_patterns = ['bash', 'chmod', 'curl', '/bin/']
        for pattern in unix_patterns:
            assert pattern in patterns

    def test_contains_windows_patterns(self):
        """Test that function includes Windows-specific patterns."""
        patterns = get_dangerous_patterns()
        windows_patterns = ['cmd', 'powershell', 'reg', '.bat']
        for pattern in windows_patterns:
            assert pattern in patterns
