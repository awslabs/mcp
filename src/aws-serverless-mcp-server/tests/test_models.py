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
"""Tests for the models module."""

from awslabs.aws_serverless_mcp_server.models import (
    BackendConfiguration,
    DeployWebAppRequest,
    FrontendConfiguration,
)


class TestBackendConfiguration:
    """Tests for the BackendConfiguration model."""

    def test_valid_backend_configuration(self):
        """Test creating a valid BackendConfiguration."""
        config = BackendConfiguration(
            built_artifacts_path='/path/to/artifacts',
            runtime='nodejs22.x',
            port=3000,
            framework=None,
            startup_script=None,
            entry_point=None,
            generate_startup_script=False,
            architecture='x86_64',
            memory_size=512,
            timeout=30,
            stage='prod',
            cors=True,
            environment=None,
            database_configuration=None,
        )
        assert config.built_artifacts_path == '/path/to/artifacts'
        assert config.runtime == 'nodejs22.x'
        assert config.port == 3000
        assert config.framework is None
        assert config.architecture == 'x86_64'
        assert config.memory_size == 512
        assert config.timeout == 30
        assert config.stage == 'prod'
        assert config.cors is True

    def test_backend_configuration_with_optional_fields(self):
        """Test creating a BackendConfiguration with optional fields."""
        config = BackendConfiguration(
            built_artifacts_path='/path/to/artifacts',
            runtime='python3.13',
            port=8080,
            framework='flask',
            startup_script='start.sh',
            entry_point='app.py',
            generate_startup_script=True,
            architecture='arm64',
            memory_size=1024,
            timeout=60,
            stage='dev',
            cors=False,
            environment={'ENV': 'development'},
            database_configuration={'table_name': 'my-table'},
        )
        assert config.built_artifacts_path == '/path/to/artifacts'
        assert config.runtime == 'python3.13'
        assert config.port == 8080
        assert config.framework == 'flask'
        assert config.startup_script == 'start.sh'
        assert config.entry_point == 'app.py'
        assert config.generate_startup_script is True
        assert config.architecture == 'arm64'
        assert config.memory_size == 1024
        assert config.timeout == 60
        assert config.stage == 'dev'
        assert config.cors is False
        assert config.environment == {'ENV': 'development'}
        assert config.database_configuration == {'table_name': 'my-table'}


class TestFrontendConfiguration:
    """Tests for the FrontendConfiguration model."""

    def test_valid_frontend_configuration(self):
        """Test creating a valid FrontendConfiguration."""
        config = FrontendConfiguration(
            built_assets_path='/path/to/assets',
            framework=None,
            index_document='index.html',
            error_document=None,
            custom_domain=None,
            certificate_arn=None,
        )
        assert config.built_assets_path == '/path/to/assets'
        assert config.framework is None
        assert config.index_document == 'index.html'
        assert config.error_document is None
        assert config.custom_domain is None
        assert config.certificate_arn is None

    def test_frontend_configuration_with_optional_fields(self):
        """Test creating a FrontendConfiguration with optional fields."""
        config = FrontendConfiguration(
            built_assets_path='/path/to/assets',
            framework='react',
            index_document='main.html',
            error_document='error.html',
            custom_domain='example.com',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            # Add all possible parameters here, if any new ones exist in the model
            # For example, if there are additional fields like "routing_rules" or "metadata", include them:
            # routing_rules=[{'condition': '...', 'redirect': '...'}],
            # metadata={'key': 'value'},
        )
        assert config.built_assets_path == '/path/to/assets'
        assert config.framework == 'react'
        assert config.index_document == 'main.html'
        assert config.error_document == 'error.html'
        assert config.custom_domain == 'example.com'
        assert (
            config.certificate_arn
            == 'arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012'
        )


class TestDeployWebAppRequest:
    """Tests for the DeployWebAppRequest model."""

    def test_valid_backend_deployment_request(self):
        """Test creating a valid backend deployment request."""
        backend_config = BackendConfiguration(
            built_artifacts_path='/path/to/artifacts',
            runtime='nodejs22.x',
            port=3000,
            framework=None,
            startup_script=None,
            entry_point=None,
            generate_startup_script=False,
            architecture='x86_64',
            memory_size=512,
            timeout=30,
            stage='prod',
            cors=True,
            environment=None,
            database_configuration=None,
        )
        request = DeployWebAppRequest(
            deployment_type='backend',
            project_name='my-backend-app',
            project_root='/path/to/project',
            backend_configuration=backend_config,
            frontend_configuration=None,
            region=None,
        )
        assert request.deployment_type == 'backend'
        assert request.project_name == 'my-backend-app'
        assert request.project_root == '/path/to/project'
        assert request.backend_configuration == backend_config
        assert request.frontend_configuration is None
        assert request.region is None

    def test_valid_frontend_deployment_request(self):
        """Test creating a valid frontend deployment request."""
        frontend_config = FrontendConfiguration(
            built_assets_path='/path/to/assets',
            framework=None,
            index_document='index.html',
            error_document=None,
            custom_domain=None,
            certificate_arn=None,
        )
        request = DeployWebAppRequest(
            deployment_type='frontend',
            project_name='my-frontend-app',
            project_root='/path/to/project',
            backend_configuration=None,
            frontend_configuration=frontend_config,
            region=None,
        )
        assert request.deployment_type == 'frontend'
        assert request.project_name == 'my-frontend-app'
        assert request.project_root == '/path/to/project'
        assert request.frontend_configuration == frontend_config
        assert request.backend_configuration is None
        assert request.region is None

    def test_valid_fullstack_deployment_request(self):
        """Test creating a valid fullstack deployment request."""
        backend_config = BackendConfiguration(
            built_artifacts_path='/path/to/artifacts',
            runtime='nodejs22.x',
            port=3000,
            framework='express',
            startup_script='start.sh',
            entry_point='app.js',
            generate_startup_script=True,
            architecture='arm64',
            memory_size=1024,
            timeout=60,
            stage='dev',
            cors=False,
            environment={'ENV': 'development'},
            database_configuration={'table_name': 'my-table'},
        )
        frontend_config = FrontendConfiguration(
            built_assets_path='/path/to/assets',
            framework='react',
            index_document='main.html',
            error_document='error.html',
            custom_domain='example.com',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
        )
        request = DeployWebAppRequest(
            deployment_type='fullstack',
            project_name='my-fullstack-app',
            project_root='/path/to/project',
            backend_configuration=backend_config,
            frontend_configuration=frontend_config,
            region='us-east-1',
        )
        assert request.deployment_type == 'fullstack'
        assert request.project_name == 'my-fullstack-app'
        assert request.project_root == '/path/to/project'
        assert request.backend_configuration == backend_config
        assert request.frontend_configuration == frontend_config
        assert request.region == 'us-east-1'
