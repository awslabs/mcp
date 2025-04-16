# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the CDK analyzer module."""

import pytest
from awslabs.cost_analysis_mcp_server.cdk_analyzer import CDKAnalyzer, analyze_cdk_project
from pathlib import Path


class TestCDKAnalyzer:
    """Tests for the CDKAnalyzer class."""

    def test_init(self, sample_cdk_project):
        """Test CDKAnalyzer initialization."""
        analyzer = CDKAnalyzer(sample_cdk_project)
        assert analyzer.project_path == Path(sample_cdk_project)

    @pytest.mark.asyncio
    async def test_analyze_python_file(self, sample_cdk_project):
        """Test analyzing a Python CDK file."""
        analyzer = CDKAnalyzer(sample_cdk_project)
        python_file = Path(sample_cdk_project) / 'app.py'

        services = analyzer._analyze_file(python_file)

        assert services is not None
        assert len(services) > 0

        service_names = {service['name'] for service in services}
        assert 'lambda' in service_names
        assert 'dynamodb' in service_names

    @pytest.mark.asyncio
    async def test_analyze_typescript_file(self, sample_cdk_project):
        """Test analyzing a TypeScript CDK file."""
        analyzer = CDKAnalyzer(sample_cdk_project)
        ts_file = Path(sample_cdk_project) / 'lib' / 'stack.ts'

        services = analyzer._analyze_file(ts_file)

        assert services is not None
        assert len(services) > 0

        service_names = {service['name'] for service in services}
        assert 's3' in service_names
        assert 'iam' in service_names

    @pytest.mark.asyncio
    async def test_analyze_invalid_file(self, temp_output_dir):
        """Test analyzing an invalid file."""
        analyzer = CDKAnalyzer(temp_output_dir)
        invalid_file = Path(temp_output_dir) / 'invalid.py'

        # Create an invalid file
        invalid_file.write_text('print("Hello, World!")')

        services = analyzer._analyze_file(invalid_file)
        assert len(services) == 0

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_file(self, temp_output_dir):
        """Test analyzing a nonexistent file."""
        analyzer = CDKAnalyzer(temp_output_dir)
        nonexistent_file = Path(temp_output_dir) / 'nonexistent.py'

        services = analyzer._analyze_file(nonexistent_file)
        assert len(services) == 0

    @pytest.mark.asyncio
    async def test_analyze_project_with_mixed_files(self, sample_cdk_project):
        """Test analyzing a project with both Python and TypeScript files."""
        analyzer = CDKAnalyzer(sample_cdk_project)
        result = await analyzer.analyze_project()

        assert result['status'] == 'success'
        assert 'services' in result

        services = {service['name'] for service in result['services']}
        assert 'lambda' in services
        assert 'dynamodb' in services
        assert 's3' in services
        assert 'iam' in services

    @pytest.mark.asyncio
    async def test_analyze_empty_project(self, temp_output_dir):
        """Test analyzing an empty project directory."""
        analyzer = CDKAnalyzer(temp_output_dir)
        result = await analyzer.analyze_project()

        assert result['status'] == 'success'
        assert 'services' in result
        assert len(result['services']) == 0

    @pytest.mark.asyncio
    async def test_analyze_project_with_init_files(self, sample_cdk_project):
        """Test that __init__.py files are ignored."""
        # Create an __init__.py file with AWS imports
        init_file = Path(sample_cdk_project) / '__init__.py'
        init_file.write_text("""
from aws_cdk import aws_s3
from aws_cdk import aws_lambda
        """)

        analyzer = CDKAnalyzer(sample_cdk_project)
        result = await analyzer.analyze_project()

        # Verify that services from __init__.py are not included
        init_services = set()
        for service in result['services']:
            if str(init_file) in str(service.get('source_file', '')):
                init_services.add(service['name'])

        assert len(init_services) == 0

    @pytest.mark.asyncio
    async def test_analyze_project_with_malformed_files(self, temp_output_dir):
        """Test analyzing files with malformed AWS imports."""
        # Create a file with malformed imports
        malformed_file = Path(temp_output_dir) / 'malformed.py'
        malformed_file.write_text("""
# Malformed imports
from aws_cdk import
import aws_lambda as
from aws_cdk.aws_
        """)

        analyzer = CDKAnalyzer(temp_output_dir)
        result = await analyzer.analyze_project()

        assert result['status'] == 'success'
        assert 'services' in result
        assert len(result['services']) == 0

    @pytest.mark.asyncio
    async def test_analyze_project_wrapper(self, sample_cdk_project):
        """Test the analyze_cdk_project wrapper function."""
        result = await analyze_cdk_project(sample_cdk_project)

        assert result['status'] == 'success'
        assert 'services' in result
        assert len(result['services']) > 0

        services = {service['name'] for service in result['services']}
        assert 'lambda' in services
        assert 'dynamodb' in services
        assert 's3' in services
        assert 'iam' in services

    @pytest.mark.asyncio
    async def test_analyze_project_wrapper_error(self):
        """Test error handling in the analyze_cdk_project wrapper function."""
        result = await analyze_cdk_project('/nonexistent/path')

        assert result['status'] == 'error'
        assert 'services' in result
        assert len(result['services']) == 0
        assert 'message' in result
        assert 'error' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_analyze_project_with_complex_imports(self, sample_cdk_project):
        """Test analyzing files with complex import patterns."""
        # Create a file with various import patterns
        complex_file = Path(sample_cdk_project) / 'complex.py'
        complex_file.write_text("""
# Multiple imports in one line
from aws_cdk import aws_lambda as lambda_, aws_dynamodb as ddb

# Import with alias
import aws_cdk.aws_s3 as s3

# Multi-line imports
from aws_cdk import (
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_rds as rds,
)

# Direct import
from aws_cdk.aws_sns import Topic
        """)

        analyzer = CDKAnalyzer(sample_cdk_project)
        result = await analyzer.analyze_project()

        assert result['status'] == 'success'
        services = {service['name'] for service in result['services']}

        # Check that all services from complex imports are detected
        expected_services = {'lambda', 'dynamodb', 's3', 'iam', 'ec2', 'rds', 'sns'}
        assert expected_services.issubset(services)
