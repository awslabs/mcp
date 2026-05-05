"""Integration tests for CDK generation."""

import json
import pytest
from awslabs.dynamodb_mcp_server.cdk_generator import CdkGenerator


MINIMAL_JSON_DATA = {
    'tables': [
        {
            'TableName': 'SimpleTable',
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
            ],
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'},
            ],
        }
    ]
}


@pytest.mark.integration
class TestCdkGeneration:
    """Tests for complete CDK generation."""

    def test_complete_cdk_generation_minimal(self, tmp_path):
        """Test generation with minimal data model - single table, partition key only."""
        json_file = tmp_path / 'dynamodb_data_model.json'
        json_file.write_text(json.dumps(MINIMAL_JSON_DATA, indent=2))

        generator = CdkGenerator()
        generator.generate(json_file)

        # Verify cdk directory was created
        cdk_dir = json_file.parent / 'cdk'
        assert cdk_dir.exists(), 'CDK directory should be created'

        # Verify cdk init files exist (from cdk init)
        assert (cdk_dir / 'bin' / 'cdk.ts').exists(), 'bin/cdk.ts should exist'
        assert (cdk_dir / 'package.json').exists(), 'package.json should exist'
        assert (cdk_dir / 'tsconfig.json').exists(), 'tsconfig.json should exist'
        assert (cdk_dir / 'cdk.json').exists(), 'cdk.json should exist'
        assert (cdk_dir / 'jest.config.js').exists(), 'jest.config.js should exist'
        assert (cdk_dir / '.gitignore').exists(), '.gitignore should exist'
        assert (cdk_dir / '.npmignore').exists(), '.npmignore should exist'
        assert (cdk_dir / 'README.md').exists(), 'README.md should exist'
        assert (cdk_dir / 'test' / 'cdk.test.ts').exists(), 'test/cdk.test.ts should exist'

        # Verify lib directory exists
        assert (cdk_dir / 'lib').exists(), 'lib directory should exist'

        # Verify stack file was generated
        stack_files = list((cdk_dir / 'lib').glob('*.ts'))
        assert len(stack_files) > 0, 'Stack file should be generated in lib/'

        # Verify stack file contains table definitions
        stack_file = stack_files[0]
        stack_content = stack_file.read_text()
        assert 'SimpleTable' in stack_content, 'Stack should contain SimpleTable definition'
        assert 'TableV2' in stack_content, 'Stack should use TableV2 construct'
        assert 'RemovalPolicy.DESTROY' in stack_content, 'Stack should use DESTROY removal policy'

    def test_complete_cdk_generation_complex(self, complex_json_file):
        """Test generation with complex data model - multiple tables, sort keys, and GSIs."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'
        stack_files = list((cdk_dir / 'lib').glob('*.ts'))
        stack_file = stack_files[0]
        stack_content = stack_file.read_text()

        # Verify both tables are present
        assert 'UserTable' in stack_content, 'Stack should contain UserTable'
        assert 'OrderTable' in stack_content, 'Stack should contain OrderTable'

        # Verify GSI is present
        assert 'StatusIndex' in stack_content, 'Stack should contain StatusIndex GSI'

        # Verify CfnOutput for each table
        assert 'UserTableName' in stack_content, 'Stack should export UserTableName'
        assert 'OrderTableName' in stack_content, 'Stack should export OrderTableName'

    def test_stack_filename_matches_cdk_init(self, complex_json_file):
        """Test that stack filename matches what cdk init created."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'

        # Parse bin/cdk.ts to get expected stack filename
        bin_file = cdk_dir / 'bin' / 'cdk.ts'
        bin_content = bin_file.read_text()

        # Extract import statement
        import re

        import_pattern = r"import\s*{\s*(\w+)\s*}\s*from\s*['\"]\.\.\/lib\/([^'\"]+)['\"]"
        match = re.search(import_pattern, bin_content)
        assert match, 'Should find import statement in bin/cdk.ts'

        expected_class_name = match.group(1)
        expected_filename = match.group(2)
        if not expected_filename.endswith('.ts'):
            expected_filename = f'{expected_filename}.ts'

        # Verify stack file exists with correct name
        stack_file = cdk_dir / 'lib' / expected_filename
        assert stack_file.exists(), f'Stack file should exist at {stack_file}'

        # Verify class name is used in generated file
        stack_content = stack_file.read_text()
        assert f'export class {expected_class_name}' in stack_content, (
            f'Stack file should use class name {expected_class_name}'
        )

    def test_readme_custom_template_replaces_cdk_init(self, complex_json_file):
        """Test that custom README template replaces the default cdk init README."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'
        readme_file = cdk_dir / 'README.md'

        # Verify README.md exists in generated cdk/ directory
        assert readme_file.exists(), 'README.md should exist in generated cdk/ directory'

        # Verify README is NOT the default cdk init README (check for custom content markers)
        readme_text = readme_file.read_text()
        assert 'Cost Performance DynamoDB CDK' in readme_text, (
            'README should contain custom title "Cost Performance DynamoDB CDK"'
        )
        assert 'AWS DynamoDB MCP Server' in readme_text, (
            'README should reference AWS DynamoDB MCP Server'
        )
        assert 'https://github.com/awslabs/mcp/tree/main/src/dynamodb-mcp-server' in readme_text, (
            'README should contain link to MCP server documentation'
        )

    def test_package_json_has_required_dependencies(self, complex_json_file):
        """Test that package.json contains required dependencies."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'
        package_json_file = cdk_dir / 'package.json'

        assert package_json_file.exists(), 'package.json should exist'

        package_json = json.loads(package_json_file.read_text())

        # Verify required dependencies
        assert 'dependencies' in package_json, 'package.json should have dependencies'
        assert 'aws-cdk-lib' in package_json['dependencies'], (
            'package.json should include aws-cdk-lib'
        )
        assert 'constructs' in package_json['dependencies'], (
            'package.json should include constructs'
        )

    def test_cdk_json_has_correct_app_entry(self, complex_json_file):
        """Test that cdk.json has correct app entry point."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'
        cdk_json_file = cdk_dir / 'cdk.json'

        assert cdk_json_file.exists(), 'cdk.json should exist'

        cdk_json = json.loads(cdk_json_file.read_text())

        # Verify app entry point
        assert 'app' in cdk_json, "cdk.json should have 'app' entry"
        assert cdk_json['app'] is not None, 'cdk.json app entry should not be null'

    def test_tsconfig_exists(self, complex_json_file):
        """Test that tsconfig.json exists for TypeScript compilation."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'
        tsconfig_file = cdk_dir / 'tsconfig.json'

        assert tsconfig_file.exists(), 'tsconfig.json should exist'

        tsconfig = json.loads(tsconfig_file.read_text())

        # Verify basic TypeScript configuration
        assert 'compilerOptions' in tsconfig, 'tsconfig.json should have compilerOptions'

    def test_gsi_projection_type_keys_only(self, tmp_path):
        """Test that GSI with KEYS_ONLY projection renders correctly."""
        json_data = {
            'tables': [
                {
                    'TableName': 'TestTable',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                        {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                    'GlobalSecondaryIndexes': [
                        {
                            'IndexName': 'GSI1',
                            'KeySchema': [
                                {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                            ],
                            'Projection': {'ProjectionType': 'KEYS_ONLY'},
                        }
                    ],
                }
            ]
        }

        json_file = tmp_path / 'dynamodb_data_model.json'
        json_file.write_text(json.dumps(json_data, indent=2))

        generator = CdkGenerator()
        generator.generate(json_file)

        cdk_dir = json_file.parent / 'cdk'
        stack_files = list((cdk_dir / 'lib').glob('*.ts'))
        stack_file = stack_files[0]
        stack_content = stack_file.read_text()

        # Verify GSI is present with KEYS_ONLY projection type
        assert 'GSI1' in stack_content, 'Stack should contain GSI1'
        assert 'projectionType: dynamodb.ProjectionType.KEYS_ONLY' in stack_content, (
            'Stack should include projectionType: dynamodb.ProjectionType.KEYS_ONLY'
        )

    def test_ttl_attribute_included_when_enabled(self, tmp_path):
        """Test that timeToLiveAttribute is included for tables with TTL enabled."""
        json_data = {
            'tables': [
                {
                    'TableName': 'TableWithTTL',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                    'TimeToLiveSpecification': {
                        'AttributeName': 'expiry_time',
                        'Enabled': True,
                    },
                }
            ]
        }

        json_file = tmp_path / 'dynamodb_data_model.json'
        json_file.write_text(json.dumps(json_data, indent=2))

        generator = CdkGenerator()
        generator.generate(json_file)

        cdk_dir = json_file.parent / 'cdk'
        stack_files = list((cdk_dir / 'lib').glob('*.ts'))
        stack_file = stack_files[0]
        stack_content = stack_file.read_text()

        # Verify TTL attribute is present
        assert "timeToLiveAttribute: 'expiry_time'" in stack_content, (
            'Stack should include timeToLiveAttribute for table with TTL enabled'
        )

    def test_ttl_attribute_omitted_when_disabled(self, tmp_path):
        """Test that timeToLiveAttribute is omitted for tables with TTL disabled."""
        json_data = {
            'tables': [
                {
                    'TableName': 'TableWithoutTTL',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                    'TimeToLiveSpecification': {
                        'AttributeName': 'expiry_time',
                        'Enabled': False,
                    },
                }
            ]
        }

        json_file = tmp_path / 'dynamodb_data_model.json'
        json_file.write_text(json.dumps(json_data, indent=2))

        generator = CdkGenerator()
        generator.generate(json_file)

        cdk_dir = json_file.parent / 'cdk'
        stack_files = list((cdk_dir / 'lib').glob('*.ts'))
        stack_file = stack_files[0]
        stack_content = stack_file.read_text()

        # Verify TTL attribute is not present
        assert 'timeToLiveAttribute' not in stack_content, (
            'Stack should not include timeToLiveAttribute for table with TTL disabled'
        )

    def test_ttl_attribute_omitted_when_not_specified(self, tmp_path):
        """Test that timeToLiveAttribute is omitted for tables without TimeToLiveSpecification."""
        json_data = {
            'tables': [
                {
                    'TableName': 'TableWithoutTTLSpec',
                    'AttributeDefinitions': [
                        {'AttributeName': 'pk', 'AttributeType': 'S'},
                    ],
                    'KeySchema': [
                        {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    ],
                }
            ]
        }

        json_file = tmp_path / 'dynamodb_data_model.json'
        json_file.write_text(json.dumps(json_data, indent=2))

        generator = CdkGenerator()
        generator.generate(json_file)

        cdk_dir = json_file.parent / 'cdk'
        stack_files = list((cdk_dir / 'lib').glob('*.ts'))
        stack_file = stack_files[0]
        stack_content = stack_file.read_text()

        # Verify TTL attribute is not present
        assert 'timeToLiveAttribute' not in stack_content, (
            'Stack should not include timeToLiveAttribute for table without TimeToLiveSpecification'
        )
