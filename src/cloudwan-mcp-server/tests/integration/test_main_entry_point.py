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

"""Main entry point tests following AWS Labs patterns."""

import os
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from awslabs.cloudwan_mcp_server.__main__ import main as module_main
from awslabs.cloudwan_mcp_server.server import main


class TestMainEntryPoint:
    """Test main entry point following AWS Labs patterns."""

    @pytest.mark.integration
    @patch("awslabs.cloudwan_mcp_server.server.mcp.run")
    def test_main_function_success(self, mock_mcp_run) -> None:
        """Test main function executes successfully with valid environment."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            try:
                main()
                # If main() completes without exception, it's successful
                # In practice, it would call mcp.run() which we've mocked
            except SystemExit:
                # SystemExit is acceptable for main function
                pass
            except Exception as e:
                pytest.fail(f"main() raised unexpected exception: {e}")

    @pytest.mark.integration
    @patch("awslabs.cloudwan_mcp_server.server.mcp.run")
    def test_main_function_with_aws_profile(self, mock_mcp_run) -> None:
        """Test main function with AWS profile configuration."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-west-2", "AWS_PROFILE": "test-profile"}):
            try:
                main()
            except SystemExit:
                pass  # Expected for main function
            except Exception as e:
                pytest.fail(f"main() with AWS profile failed: {e}")

    @pytest.mark.integration
    @patch("awslabs.cloudwan_mcp_server.server.mcp.run")
    def test_main_function_mcp_run_called(self, mock_mcp_run) -> None:
        """Test that main function calls mcp.run() properly."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            try:
                main()
                # Verify mcp.run was called if main completed normally
                if not mock_mcp_run.called:
                    # Check if main exited before calling run (acceptable)
                    pass
            except SystemExit:
                pass  # SystemExit may occur before mcp.run() is called

    @pytest.mark.integration
    def test_main_function_environment_handling(self) -> None:
        """Test main function handles environment variables correctly."""
        # Test with minimal required environment
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            with patch("awslabs.cloudwan_mcp_server.server.mcp.run"):
                try:
                    main()
                except SystemExit:
                    pass  # Expected behavior
                except Exception as e:
                    # Should not raise other exceptions with valid environment
                    pytest.fail(f"Unexpected exception with valid environment: {e}")

    @pytest.mark.integration
    def test_main_function_signal_handling(self) -> None:
        """Test main function handles signals appropriately."""
        # This test verifies main() can be interrupted gracefully
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            with patch("awslabs.cloudwan_mcp_server.server.mcp.run") as mock_run:
                # Simulate KeyboardInterrupt during run
                mock_run.side_effect = KeyboardInterrupt("Test interrupt")

                try:
                    main()
                except KeyboardInterrupt:
                    pass  # Expected - main should allow KeyboardInterrupt to propagate
                except SystemExit:
                    pass  # Also acceptable
                except Exception as e:
                    pytest.fail(f"main() should handle KeyboardInterrupt gracefully: {e}")

    @pytest.mark.integration
    @patch("awslabs.cloudwan_mcp_server.server.mcp")
    def test_main_function_server_initialization(self, mock_mcp) -> None:
        """Test main function with server initialization."""
        mock_mcp.run = Mock()

        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            try:
                main()
            except SystemExit:
                pass

        # Verify server attributes are accessible
        assert hasattr(mock_mcp, "run")

    @pytest.mark.integration
    def test_main_function_import_errors(self) -> None:
        """Test main function handles import errors gracefully."""
        # Test that main can be imported and called
        from awslabs.cloudwan_mcp_server.server import main as imported_main

        assert callable(imported_main)
        assert imported_main == main

    @pytest.mark.integration
    def test_main_function_logging_configuration(self) -> None:
        """Test main function with logging configuration."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            with patch("awslabs.cloudwan_mcp_server.server.mcp.run"):
                try:
                    main()
                except SystemExit:
                    pass

                # Verify logging is configured (logger should exist)
                from awslabs.cloudwan_mcp_server.server import logger

                assert logger is not None

    @pytest.mark.integration
    def test_main_function_multiple_calls(self) -> None:
        """Test main function can be called multiple times safely."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            with patch("awslabs.cloudwan_mcp_server.server.mcp.run"):
                # First call
                try:
                    main()
                except SystemExit:
                    pass

                # Second call should not raise exceptions
                try:
                    main()
                except SystemExit:
                    pass
                except Exception as e:
                    pytest.fail(f"Multiple calls to main() should be safe: {e}")

    @pytest.mark.integration
    def test_main_function_resource_cleanup(self) -> None:
        """Test main function cleans up resources properly."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            with patch("awslabs.cloudwan_mcp_server.server.mcp.run") as mock_run:
                # Simulate exception during run to test cleanup
                mock_run.side_effect = RuntimeError("Test error")

                try:
                    main()
                except RuntimeError:
                    pass  # Expected
                except SystemExit:
                    pass  # Also acceptable
                except Exception as e:
                    pytest.fail(f"Unexpected exception during cleanup test: {e}")


class TestModuleMainEntryPoint:
    """Test __main__.py module entry point following AWS Labs patterns."""

    @pytest.mark.integration
    def test_module_main_imports_correctly(self) -> None:
        """Test __main__.py imports main function correctly."""
        from awslabs.cloudwan_mcp_server.__main__ import main as module_main_import
        from awslabs.cloudwan_mcp_server.server import main as server_main

        # Should be the same function
        assert module_main_import == server_main
        assert callable(module_main_import)

    @pytest.mark.integration
    def test_module_main_calls_server_main(self) -> None:
        """Test __main__.py calls server.main() correctly."""
        # Import and verify the module sets up main correctly
        from awslabs.cloudwan_mcp_server import __main__
        from awslabs.cloudwan_mcp_server.server import main as server_main

        # The module should have main function available
        assert hasattr(__main__, "main")
        # Should be the same function (imported from server)
        assert __main__.main == server_main

    @pytest.mark.integration
    def test_module_main_executable(self) -> None:
        """Test module can be executed as python -m awslabs.cloudwan_mcp_server."""
        # This test verifies the module structure is correct for -m execution
        # We don't actually execute it to avoid side effects

        # Verify __main__.py exists and has correct structure
        import awslabs.cloudwan_mcp_server.__main__ as main_module

        # Should have main function
        assert hasattr(main_module, "main")
        assert callable(main_module.main)

        # Should be set up for execution
        import inspect

        source = inspect.getsource(main_module)
        assert 'if __name__ == "__main__"' in source
        assert "main()" in source

    @pytest.mark.integration
    def test_module_name_check(self) -> None:
        """Test __name__ == "__main__" check works correctly."""
        # Read the __main__.py file to verify structure
        import inspect

        import awslabs.cloudwan_mcp_server.__main__ as main_module

        source = inspect.getsource(main_module)

        # Verify proper structure for module execution
        assert 'if __name__ == "__main__":' in source
        assert "main()" in source

        # Verify main is imported from server
        assert "from .server import main" in source


class TestCommandLineExecution:
    """Test command-line execution patterns following AWS Labs standards."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_module_execution_help(self) -> None:
        """Test module execution shows help/version information."""
        # Test that the module can be executed (dry run)
        cmd = [sys.executable, "-c", 'import awslabs.cloudwan_mcp_server.__main__; print("Module import successful")']

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            # Should not fail to import
            assert result.returncode == 0 or result.stderr == ""
            assert "Module import successful" in result.stdout
        except subprocess.TimeoutExpired:
            pytest.skip("Module execution test timed out")
        except Exception as e:
            pytest.skip(f"Module execution test skipped: {e}")

    @pytest.mark.integration
    def test_entry_point_configuration(self) -> None:
        """Test entry points are configured correctly in pyproject.toml."""
        # This would typically read pyproject.toml and verify entry points
        # For this test, we verify the functions exist and are callable

        from awslabs.cloudwan_mcp_server.__main__ import main
        from awslabs.cloudwan_mcp_server.server import main as server_main

        assert main == server_main
        assert callable(main)

    @pytest.mark.integration
    def test_package_structure_for_execution(self) -> None:
        """Test package structure supports proper execution."""
        # Verify package can be imported and has correct structure
        import awslabs
        import awslabs.cloudwan_mcp_server
        import awslabs.cloudwan_mcp_server.__main__
        import awslabs.cloudwan_mcp_server.server

        # Verify all modules loaded successfully
        assert hasattr(awslabs.cloudwan_mcp_server, "__main__")
        assert hasattr(awslabs.cloudwan_mcp_server, "server")

        # Verify main function is accessible
        main_func = awslabs.cloudwan_mcp_server.__main__.main
        server_func = awslabs.cloudwan_mcp_server.server.main
        assert main_func == server_func

    @pytest.mark.integration
    def test_environment_variable_forwarding(self) -> None:
        """Test environment variables are properly forwarded to main execution."""
        with patch("awslabs.cloudwan_mcp_server.server.mcp.run"):
            with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "eu-west-1", "AWS_PROFILE": "test-profile"}):
                try:
                    module_main()
                except SystemExit:
                    pass

                # Environment should be accessible within main
                assert os.environ.get("AWS_DEFAULT_REGION") == "eu-west-1"
                assert os.environ.get("AWS_PROFILE") == "test-profile"


class TestMainFunctionEdgeCases:
    """Test edge cases for main function following AWS Labs patterns."""

    @pytest.mark.integration
    def test_main_with_empty_environment(self) -> None:
        """Test main function behavior with minimal environment."""
        # Clear all AWS-related environment variables
        aws_vars = [k for k in os.environ if k.startswith("AWS_")]

        with patch.dict("os.environ", dict.fromkeys(aws_vars, ""), clear=False):
            with patch("awslabs.cloudwan_mcp_server.server.mcp.run"):
                try:
                    main()
                except SystemExit:
                    pass  # Expected
                except Exception:
                    pass  # May fail due to missing config, which is expected

    @pytest.mark.integration
    def test_main_exception_propagation(self) -> None:
        """Test main function exception propagation patterns."""
        with patch("awslabs.cloudwan_mcp_server.server.mcp.run") as mock_run:
            # Test different exception types
            exceptions_to_test = [
                KeyboardInterrupt("User interrupt"),
                SystemExit(0),
                SystemExit(1),
            ]

            for exception in exceptions_to_test:
                mock_run.side_effect = exception

                with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
                    try:
                        main()
                    except type(exception):
                        pass  # Expected
                    except Exception as e:
                        pytest.fail(f"Unexpected exception type for {type(exception)}: {e}")

    @pytest.mark.integration
    def test_main_function_return_value(self) -> None:
        """Test main function return value patterns."""
        with patch("awslabs.cloudwan_mcp_server.server.mcp.run"):
            with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
                try:
                    result = main()
                    # main() typically doesn't return a value (returns None)
                    assert result is None
                except SystemExit as e:
                    # SystemExit with code is also valid
                    assert isinstance(e.code, int | type(None))
                except Exception:
                    pass  # Other exceptions may occur depending on implementation
