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

"""Tests for validators module."""

from awslabs.aws_appsync_mcp_server.validators import validate_graphql_schema


class TestValidateGraphQLSchema:
    """Test cases for validate_graphql_schema function."""

    def test_valid_schema(self):
        """Test valid GraphQL schema returns no issues."""
        schema = """
        type Query {
            hello: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert issues == []

    def test_empty_schema(self):
        """Test empty schema returns error."""
        issues = validate_graphql_schema('')
        assert 'Schema definition cannot be empty' in issues

    def test_whitespace_only_schema(self):
        """Test whitespace-only schema returns error."""
        issues = validate_graphql_schema('   \n\t  ')
        assert 'Schema definition cannot be empty' in issues

    def test_missing_query_type(self):
        """Test schema without Query type returns error."""
        schema = """
        type User {
            id: ID!
            name: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert 'Schema must include a Query type' in issues

    def test_query_type_case_insensitive(self):
        """Test Query type detection is case insensitive."""
        schema = """
        type query {
            hello: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert not any('Query type' in issue for issue in issues)

    def test_unbalanced_braces_more_open(self):
        """Test schema with more opening braces."""
        schema = """
        type Query {
            hello: String
            nested: {
        """
        issues = validate_graphql_schema(schema)
        assert 'Unbalanced braces: 2 opening, 0 closing' in issues

    def test_unbalanced_braces_more_close(self):
        """Test schema with more closing braces."""
        schema = """
        type Query {
            hello: String
        }}
        """
        issues = validate_graphql_schema(schema)
        assert 'Unbalanced braces: 1 opening, 2 closing' in issues

    def test_multiple_issues(self):
        """Test schema with multiple validation issues."""
        schema = """
        type User {
            id: ID!
        """
        issues = validate_graphql_schema(schema)
        assert len(issues) == 2
        assert 'Schema must include a Query type' in issues
        assert 'Unbalanced braces: 1 opening, 0 closing' in issues

    def test_complex_valid_schema(self):
        """Test complex but valid schema."""
        schema = """
        type Query {
            user(id: ID!): User
            users: [User!]!
        }

        type Mutation {
            createUser(input: CreateUserInput!): User
        }

        type User {
            id: ID!
            name: String!
            email: String
        }

        input CreateUserInput {
            name: String!
            email: String
        }
        """
        issues = validate_graphql_schema(schema)
        assert issues == []

    def test_query_with_extra_whitespace(self):
        """Test Query type with various whitespace patterns."""
        schemas = [
            'type  Query  {  hello: String  }',
            'type\nQuery\n{\nhello: String\n}',
            'type\tQuery\t{\thello: String\t}',
        ]
        for schema in schemas:
            issues = validate_graphql_schema(schema)
            assert not any('Query type' in issue for issue in issues)
