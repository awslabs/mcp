#
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
#

"""Tests for the diagrams module of the diagrams-mcp-server."""

import os
import pytest
import signal
import sys
from awslabs.aws_diagram_mcp_server.diagrams_tools import (
    generate_diagram,
    get_diagram_examples,
    list_diagram_icons,
)
from awslabs.aws_diagram_mcp_server.models import DiagramType
from unittest.mock import patch


class TestGetDiagramExamples:
    """Tests for the get_diagram_examples function."""

    def test_get_all_examples(self):
        """Test getting all diagram examples."""
        response = get_diagram_examples(DiagramType.ALL)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have examples for each diagram type
        assert any(key.startswith('aws_') for key in response.examples.keys())
        assert any(key.startswith('sequence') for key in response.examples.keys())
        assert any(key.startswith('flow') for key in response.examples.keys())
        assert any(key.startswith('class') for key in response.examples.keys())
        assert any(key.startswith('k8s_') for key in response.examples.keys())
        assert any(key.startswith('onprem_') for key in response.examples.keys())
        assert any(key.startswith('custom_') for key in response.examples.keys())

    def test_get_aws_examples(self):
        """Test getting AWS diagram examples."""
        response = get_diagram_examples(DiagramType.AWS)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that all examples are AWS examples
        assert all(key.startswith('aws_') for key in response.examples.keys())
        # Check that we have the expected AWS examples
        assert 'aws_basic' in response.examples
        assert 'aws_grouped_workers' in response.examples
        assert 'aws_clustered_web_services' in response.examples
        assert 'aws_event_processing' in response.examples
        assert 'aws_bedrock' in response.examples

    def test_get_sequence_examples(self):
        """Test getting sequence diagram examples."""
        response = get_diagram_examples(DiagramType.SEQUENCE)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the sequence example
        assert 'sequence' in response.examples

    def test_get_flow_examples(self):
        """Test getting flow diagram examples."""
        response = get_diagram_examples(DiagramType.FLOW)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the flow example
        assert 'flow' in response.examples

    def test_get_class_examples(self):
        """Test getting class diagram examples."""
        response = get_diagram_examples(DiagramType.CLASS)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the class example
        assert 'class' in response.examples

    def test_get_k8s_examples(self):
        """Test getting Kubernetes diagram examples."""
        response = get_diagram_examples(DiagramType.K8S)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the expected K8s examples
        assert 'k8s_exposed_pod' in response.examples
        assert 'k8s_stateful' in response.examples

    def test_get_onprem_examples(self):
        """Test getting on-premises diagram examples."""
        response = get_diagram_examples(DiagramType.ONPREM)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the expected on-premises examples
        assert 'onprem_web_service' in response.examples
        assert 'onprem_web_service_colored' in response.examples

    def test_get_custom_examples(self):
        """Test getting custom diagram examples."""
        response = get_diagram_examples(DiagramType.CUSTOM)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the custom example
        assert 'custom_rabbitmq' in response.examples


class TestListDiagramIcons:
    """Tests for the list_diagram_icons function."""

    def test_list_icons_without_filters(self):
        """Test listing diagram icons without filters."""
        response = list_diagram_icons()
        assert response.providers is not None
        assert len(response.providers) > 0
        # Check that we have the expected providers
        assert 'aws' in response.providers
        assert 'gcp' in response.providers
        assert 'k8s' in response.providers
        assert 'onprem' in response.providers
        assert 'programming' in response.providers
        # Check that the providers don't have services (just provider names)
        assert response.providers['aws'] == {}
        assert response.filtered is False
        assert response.filter_info is None

    def test_list_icons_with_provider_filter(self):
        """Test listing diagram icons with provider filter."""
        response = list_diagram_icons(provider_filter='aws')
        assert response.providers is not None
        assert len(response.providers) == 1
        assert 'aws' in response.providers
        assert response.filtered is True
        assert response.filter_info == {'provider': 'aws'}
        # Check that we have services for AWS
        assert 'compute' in response.providers['aws']
        assert 'database' in response.providers['aws']
        assert 'network' in response.providers['aws']
        # Check that we have icons for AWS compute
        assert 'EC2' in response.providers['aws']['compute']
        assert 'Lambda' in response.providers['aws']['compute']

    def test_list_icons_with_provider_and_service_filter(self):
        """Test listing diagram icons with provider and service filter."""
        response = list_diagram_icons(provider_filter='aws', service_filter='compute')
        assert response.providers is not None
        assert len(response.providers) == 1
        assert 'aws' in response.providers
        assert len(response.providers['aws']) == 1
        assert 'compute' in response.providers['aws']
        assert response.filtered is True
        assert response.filter_info == {'provider': 'aws', 'service': 'compute'}
        # Check that we have icons for AWS compute
        assert 'EC2' in response.providers['aws']['compute']
        assert 'Lambda' in response.providers['aws']['compute']

    def test_list_icons_with_invalid_provider(self):
        """Test listing diagram icons with invalid provider."""
        response = list_diagram_icons(provider_filter='invalid_provider')
        assert response.providers == {}
        assert response.filtered is True
        assert response.filter_info is not None
        assert response.filter_info.get('provider') == 'invalid_provider'
        assert 'error' in response.filter_info

    def test_list_icons_with_invalid_service(self):
        """Test listing diagram icons with invalid service."""
        response = list_diagram_icons(provider_filter='aws', service_filter='invalid_service')
        assert response.providers is not None
        assert 'aws' in response.providers
        assert response.providers['aws'] == {}
        assert response.filtered is True
        assert response.filter_info is not None
        assert response.filter_info.get('provider') == 'aws'
        assert response.filter_info.get('service') == 'invalid_service'
        assert 'error' in response.filter_info

    def test_list_icons_with_service_filter_only(self):
        """Test listing diagram icons with only service filter."""
        response = list_diagram_icons(service_filter='compute')
        assert response.providers == {}
        assert response.filtered is True
        assert response.filter_info is not None
        assert response.filter_info.get('service') == 'compute'
        assert 'error' in response.filter_info


class TestGenerateDiagram:
    """Tests for the generate_diagram function."""

    @pytest.mark.asyncio
    async def test_generate_diagram_success(self, aws_diagram_code, temp_workspace_dir):
        """Test successful diagram generation."""
        result = await generate_diagram(
            code=aws_diagram_code,
            filename='test_aws_diagram',
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        expected_path = os.path.join(
            temp_workspace_dir, 'generated-diagrams', 'test_aws_diagram.png'
        )
        assert result.path == expected_path

    @pytest.mark.asyncio
    async def test_generate_diagram_with_absolute_path(self, aws_diagram_code, temp_workspace_dir):
        """Test diagram generation with an absolute path."""
        absolute_path = os.path.join(temp_workspace_dir, 'absolute_path_diagram')
        result = await generate_diagram(
            code=aws_diagram_code,
            filename=absolute_path,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        expected_path = f'{absolute_path}.png'
        assert result.path == expected_path

    @pytest.mark.asyncio
    async def test_generate_diagram_with_random_filename(
        self, aws_diagram_code, temp_workspace_dir
    ):
        """Test diagram generation with a random filename."""
        result = await generate_diagram(
            code=aws_diagram_code,
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        assert os.path.dirname(result.path) == os.path.join(
            temp_workspace_dir, 'generated-diagrams'
        )
        assert os.path.basename(result.path).startswith('diagram_')

    @pytest.mark.asyncio
    async def test_generate_diagram_with_invalid_code(
        self, invalid_diagram_code, temp_workspace_dir
    ):
        """Test diagram generation with invalid code."""
        result = await generate_diagram(
            code=invalid_diagram_code,
            filename='test_invalid_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None
        assert 'error' in result.message.lower()

    @pytest.mark.asyncio
    async def test_generate_diagram_with_dangerous_code(
        self, dangerous_diagram_code, temp_workspace_dir
    ):
        """Test diagram generation with dangerous code."""
        result = await generate_diagram(
            code=dangerous_diagram_code,
            filename='test_dangerous_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None
        assert 'security issues' in result.message.lower()

    @pytest.mark.asyncio
    async def test_generate_diagram_with_timeout(self, aws_diagram_code, temp_workspace_dir):
        """Test diagram generation with a timeout."""
        # Use a very short timeout to force a timeout error
        result = await generate_diagram(
            code=aws_diagram_code,
            filename='test_timeout_diagram',
            timeout=1,  # 1 second timeout
            workspace_dir=temp_workspace_dir,
        )
        # The test could pass or fail depending on how fast the diagram is generated
        # If it's fast enough, it will succeed; if not, it will timeout
        if result.status == 'error':
            # Check if the error is about a missing executable or a timeout
            if 'executablenotfound' in result.message.lower() or 'dot' in result.message.lower():
                # This is fine, the test environment might not have graphviz installed
                pass
            else:
                # If it's another error, it should be a timeout
                assert 'timeout' in result.message.lower()
        else:
            assert result.path is not None
            assert os.path.exists(result.path)

    @pytest.mark.asyncio
    async def test_generate_sequence_diagram(self, sequence_diagram_code, temp_workspace_dir):
        """Test generating a sequence diagram."""
        result = await generate_diagram(
            code=sequence_diagram_code,
            filename='test_sequence_diagram',
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')

    @pytest.mark.asyncio
    async def test_generate_flow_diagram(self, flow_diagram_code, temp_workspace_dir):
        """Test generating a flow diagram."""
        result = await generate_diagram(
            code=flow_diagram_code,
            filename='test_flow_diagram',
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        expected_path = os.path.join(
            temp_workspace_dir, 'generated-diagrams', 'test_flow_diagram.png'
        )
        assert result.path == expected_path

    @pytest.mark.asyncio
    async def test_generate_diagram_with_show_parameter(self, temp_workspace_dir):
        """Test diagram generation with show parameter already set."""
        code = """with Diagram("Test Show Parameter", show=False, filename='test_show_param'):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""
        result = await generate_diagram(
            code=code,
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')

    @pytest.mark.asyncio
    async def test_generate_diagram_with_filename_parameter(self, temp_workspace_dir):
        """Test diagram generation with filename parameter already set."""
        code = """with Diagram("Test Filename Parameter", filename='test_filename_param'):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""
        result = await generate_diagram(
            code=code,
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # The filename in the code should be overridden by the workspace_dir path
        assert os.path.dirname(result.path) == os.path.join(
            temp_workspace_dir, 'generated-diagrams'
        )


class TestNamespaceRCEPrevention:
    """Tests verifying the execution namespace does not contain dangerous modules.

    These tests validate the fix for the variable aliasing RCE vulnerability
    (CVSS 10.0) where attackers could bypass the static scanner by aliasing
    pre-imported modules (e.g., x = os; x.system('calc.exe')).
    """

    @pytest.mark.asyncio
    async def test_os_alias_rce_blocked(self, temp_workspace_dir):
        """PoC from security report: os module aliasing must fail at runtime."""
        code = """x = os\nx.system('echo test')"""
        result = await generate_diagram(
            code=code,
            filename='test_os_alias_rce',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        # Should fail because os is not in the namespace (NameError)
        # or be caught by the scanner
        assert result.path is None

    @pytest.mark.asyncio
    async def test_os_popen_alias_rce_blocked(self, temp_workspace_dir):
        """os.popen via aliasing must fail at runtime."""
        code = """x = os\nx.popen('echo test')"""
        result = await generate_diagram(
            code=code,
            filename='test_os_popen_alias_rce',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None

    @pytest.mark.asyncio
    async def test_diagrams_module_os_leak_blocked(self, temp_workspace_dir):
        """Bare 'diagrams' module must not leak os via diagrams.os attribute."""
        code = """x = diagrams.os\nx.system('echo test')"""
        result = await generate_diagram(
            code=code,
            filename='test_diagrams_os_leak',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None

    @pytest.mark.asyncio
    async def test_function_extraction_rce_blocked(self, temp_workspace_dir):
        """Extracting os.system to a variable must fail at runtime."""
        code = """f = os.system\nf('echo test')"""
        result = await generate_diagram(
            code=code,
            filename='test_func_extract_rce',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None

    @pytest.mark.asyncio
    async def test_legitimate_diagram_still_works(self, aws_diagram_code, temp_workspace_dir):
        """Ensure the fix doesn't break legitimate diagram generation."""
        result = await generate_diagram(
            code=aws_diagram_code,
            filename='test_legit_after_fix',
            workspace_dir=temp_workspace_dir,
        )
        # Skip if Graphviz not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)

    @pytest.mark.asyncio
    async def test_builtins_import_blocked(self, temp_workspace_dir):
        """__builtins__['__import__'] must not be accessible in user code."""
        code = """m = __builtins__['__import__']('os')\nm.system('echo test')"""
        result = await generate_diagram(
            code=code,
            filename='test_builtins_import',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None

    @pytest.mark.asyncio
    async def test_builtins_restricted_still_works(self, aws_diagram_code, temp_workspace_dir):
        """Verify restricted __builtins__ still allows legitimate diagram generation."""
        result = await generate_diagram(
            code=aws_diagram_code,
            filename='test_builtins_safe',
            workspace_dir=temp_workspace_dir,
        )
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)

    @pytest.mark.asyncio
    async def test_urlretrieve_path_traversal_blocked(self, temp_workspace_dir):
        """Verify urlretrieve does not allow path traversal in filename."""
        code = """urlretrieve('https://example.com/icon.png', '/etc/cron.d/backdoor.png')"""
        result = await generate_diagram(
            code=code,
            filename='test_urlretrieve_traversal',
            workspace_dir=temp_workspace_dir,
        )
        # Should either error (no Diagram block) or download to temp dir only.
        # The path traversal (/etc/cron.d/) is stripped to just 'backdoor.png'.
        assert result.status == 'error'

    @pytest.mark.asyncio
    async def test_urlretrieve_non_image_blocked(self, temp_workspace_dir):
        """Verify urlretrieve rejects non-image file extensions."""
        code = """urlretrieve('https://example.com/payload.py', 'payload.py')"""
        result = await generate_diagram(
            code=code,
            filename='test_urlretrieve_extension',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None

    @pytest.mark.asyncio
    async def test_urlretrieve_ftp_scheme_blocked(self, temp_workspace_dir):
        """Verify urlretrieve rejects non-HTTP schemes."""
        code = """urlretrieve('ftp://evil.com/backdoor.png', 'backdoor.png')"""
        result = await generate_diagram(
            code=code,
            filename='test_urlretrieve_scheme',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None


class TestSafeUrlretrieve:
    """Unit tests for the _safe_urlretrieve function."""

    def test_rejects_ftp_scheme(self):
        """Reject non-HTTP URL schemes."""
        from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

        with pytest.raises(ValueError, match='Only http/https URLs are allowed'):
            _safe_urlretrieve('ftp://evil.com/icon.png', 'icon.png')

    def test_rejects_file_scheme(self):
        """Reject file:// URL scheme."""
        from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

        with pytest.raises(ValueError, match='Only http/https URLs are allowed'):
            _safe_urlretrieve('file:///etc/passwd', 'passwd.png')

    def test_rejects_non_image_extension(self):
        """Reject non-image file extensions."""
        from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

        with pytest.raises(ValueError, match='Only image files are allowed'):
            _safe_urlretrieve('https://example.com/payload.py', 'payload.py')

    def test_rejects_no_extension(self):
        """Reject files without an extension."""
        from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

        with pytest.raises(ValueError, match='Only image files are allowed'):
            _safe_urlretrieve('https://example.com/payload', 'payload')

    def test_strips_path_traversal(self):
        """Path traversal components are stripped to basename only."""
        with patch(
            'awslabs.aws_diagram_mcp_server.diagrams_tools._real_urlretrieve',
            return_value=('/tmp/fake', {}),
        ) as mock_retrieve:
            from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

            path, _ = _safe_urlretrieve('https://example.com/icon.png', '../../etc/icon.png')
            # The download path must use only the basename, not the traversal path
            assert os.path.basename(path) == 'icon.png'
            assert '/etc/' not in path
            assert '../../' not in path
            mock_retrieve.assert_called_once()

    def test_rejects_empty_filename(self):
        """Reject empty filename."""
        from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

        with pytest.raises(ValueError, match='Filename cannot be empty'):
            _safe_urlretrieve('https://example.com/icon.png', '/')

    def test_accepts_valid_image_extensions(self):
        """Valid image extensions pass validation and reach the download call."""
        with patch(
            'awslabs.aws_diagram_mcp_server.diagrams_tools._real_urlretrieve',
            return_value=('/tmp/fake', {}),
        ) as mock_retrieve:
            from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.bmp', '.webp']:
                _safe_urlretrieve(f'https://example.com/icon{ext}', f'icon{ext}')
            assert mock_retrieve.call_count == 8

    def test_downloads_to_unique_temp_dir(self):
        """Each call downloads to a unique temp directory."""
        with patch(
            'awslabs.aws_diagram_mcp_server.diagrams_tools._real_urlretrieve',
            return_value=('/tmp/fake', {}),
        ):
            from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

            path1, _ = _safe_urlretrieve('https://example.com/a.png', 'a.png')
            path2, _ = _safe_urlretrieve('https://example.com/b.png', 'b.png')
            # Each invocation should use a different temp directory
            assert os.path.dirname(path1) != os.path.dirname(path2)

    def test_uses_url_basename_when_filename_omitted(self):
        """Filename defaults to URL path basename when not provided."""
        with patch(
            'awslabs.aws_diagram_mcp_server.diagrams_tools._real_urlretrieve',
            return_value=('/tmp/fake', {}),
        ):
            from awslabs.aws_diagram_mcp_server.diagrams_tools import _safe_urlretrieve

            path, _ = _safe_urlretrieve('https://example.com/my-icon.png')
            assert os.path.basename(path) == 'my-icon.png'


class TestCrossPlatformTimeout:
    """Tests for cross-platform timeout handling in generate_diagram."""

    def test_signal_module_imported(self):
        """Test that the diagrams_tools module imports signal and threading."""
        dt = sys.modules.get('awslabs.aws_diagram_mcp_server.diagrams_tools')
        assert dt is not None
        assert hasattr(dt, 'signal')
        assert hasattr(dt, 'threading')

    @pytest.mark.asyncio
    async def test_unix_path_uses_sigalrm(self, aws_diagram_code, temp_workspace_dir):
        """Test that SIGALRM is used on Unix platforms."""
        if sys.platform == 'win32':
            pytest.skip('SIGALRM only available on Unix')

        assert hasattr(signal, 'SIGALRM')
        # Just verify generate_diagram works on this platform
        result = await generate_diagram(
            code=aws_diagram_code,
            filename='test_unix_timeout',
            workspace_dir=temp_workspace_dir,
        )
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')
        assert result.status == 'success'

    @pytest.mark.asyncio
    async def test_threading_fallback_when_sigalrm_unavailable(
        self, aws_diagram_code, temp_workspace_dir
    ):
        """Test that threading fallback is used when SIGALRM is unavailable."""
        # Remove SIGALRM to force the threading fallback path
        sigalrm = getattr(signal, 'SIGALRM', None)
        if sigalrm is None:
            pytest.skip('Already on a platform without SIGALRM')

        with patch.object(signal, 'SIGALRM', new=sigalrm, create=True):
            # Delete SIGALRM so hasattr returns False
            delattr(signal, 'SIGALRM')
            try:
                result = await generate_diagram(
                    code=aws_diagram_code,
                    filename='test_no_sigalrm',
                    workspace_dir=temp_workspace_dir,
                )
            finally:
                # Restore SIGALRM
                signal.SIGALRM = sigalrm
            if result.status == 'error' and (
                'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
            ):
                pytest.skip('Graphviz not installed, skipping test')
            # Should succeed or fail with a diagram error, not a SIGALRM crash
            assert result.status in ('success', 'error')
            if result.status == 'error':
                assert 'sigalrm' not in result.message.lower()

    @pytest.mark.asyncio
    async def test_threading_timeout_triggers(self, temp_workspace_dir):
        """Test that the threading-based timeout fires correctly."""
        # Use a CPU-bound busy loop instead of time.sleep to avoid
        # the import statement being rejected by the security scanner.
        slow_code = """
x = 0
with Diagram("Slow Diagram", show=False):
    while x < 10**12:
        x += 1
    ELB("lb") >> EC2("web")
"""
        sigalrm = getattr(signal, 'SIGALRM', None)
        if sigalrm is None:
            pytest.skip('Already on a platform without SIGALRM')

        delattr(signal, 'SIGALRM')
        try:
            result = await generate_diagram(
                code=slow_code,
                filename='test_timeout',
                timeout=2,
                workspace_dir=temp_workspace_dir,
            )
        finally:
            signal.SIGALRM = sigalrm
        assert result.status == 'error'
        assert 'timed out' in result.message.lower()
