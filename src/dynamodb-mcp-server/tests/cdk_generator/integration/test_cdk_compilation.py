"""Integration tests for CDK project compilation and synthesis."""

import pytest
import subprocess
from awslabs.dynamodb_mcp_server.cdk_generator import CdkGenerator


@pytest.mark.integration
class TestCdkCompilation:
    """Tests for TypeScript compilation and CDK synthesis."""

    def test_typescript_compilation(self, complex_json_file):
        """Test that generated CDK app compiles without errors."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'

        # Run npm run build to compile TypeScript
        try:
            result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=cdk_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )

            assert result.returncode == 0, (
                f'TypeScript compilation should succeed. stderr: {result.stderr}'
            )

        except subprocess.TimeoutExpired:
            pytest.skip('npm build timed out - skipping compilation test')
        except FileNotFoundError:
            pytest.skip('npm not found - skipping compilation test')

    def test_cdk_synthesis(self, complex_json_file):
        """Test that generated CDK app synthesizes successfully."""
        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'

        # First ensure npm dependencies are installed
        try:
            install_result = subprocess.run(
                ['npm', 'install'],
                cwd=cdk_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if install_result.returncode != 0:
                pytest.skip(
                    f'npm install failed - skipping synthesis test: {install_result.stderr}'
                )

            # Run cdk synth to generate CloudFormation template
            result = subprocess.run(
                ['npx', 'cdk', 'synth'],
                cwd=cdk_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )

            assert result.returncode == 0, f'CDK synthesis should succeed. stderr: {result.stderr}'

            # Verify CloudFormation template was generated
            cdk_out = cdk_dir / 'cdk.out'
            assert cdk_out.exists(), 'cdk.out directory should be created'

            # Verify template file exists
            template_files = list(cdk_out.glob('*.json'))
            assert len(template_files) > 0, 'CloudFormation template should be generated'

        except subprocess.TimeoutExpired:
            pytest.skip('CDK synthesis timed out - skipping test')
        except FileNotFoundError:
            pytest.skip('npx or npm not found - skipping synthesis test')
