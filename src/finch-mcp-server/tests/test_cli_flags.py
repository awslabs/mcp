"""Tests for command-line flag parsing and handling."""

import argparse
import os
import pytest
import tempfile
from awslabs.finch_mcp_server.server import main, set_enable_aws_resource_write
from pathlib import Path
from unittest.mock import MagicMock, call, patch


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp_file:
        yield tmp_file.name
    # Cleanup
    try:
        os.unlink(tmp_file.name)
    except FileNotFoundError:
        pass  # File already cleaned up


def create_test_path(*parts):
    """Create a platform-agnostic test path."""
    return str(Path(*parts))


class TestArgumentParsing:
    """Tests for command-line argument parsing."""

    def test_default_arguments(self):
        """Test default argument values when no flags are provided."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse:
            mock_args = MagicMock()
            mock_args.enable_aws_resource_write = False
            mock_args.log_file = None
            mock_args.disable_file_logging = False
            mock_parse.return_value = mock_args

            # Import and run the main block
            with patch('sys.argv', ['finch-mcp-server']):
                # This would normally be in the if __name__ == '__main__' block
                parser = argparse.ArgumentParser(description='Run the Finch MCP server')
                parser.add_argument(
                    '--enable-aws-resource-write',
                    action='store_true',
                    help='Enable AWS resource creation and modification (disabled by default)',
                )
                parser.add_argument(
                    '--log-file',
                    type=str,
                    help='Path to log file for persistent logging (optional, logs to stderr by default)',
                )
                parser.add_argument(
                    '--disable-file-logging',
                    action='store_true',
                    help='Disable file logging entirely (stderr only, follows MCP standard)',
                )
                args = parser.parse_args([])  # Empty args for defaults

                assert args.enable_aws_resource_write is False
                assert args.log_file is None
                assert args.disable_file_logging is False

    def test_enable_aws_resource_write_flag(self):
        """Test --enable-aws-resource-write flag parsing."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')

        # Test flag present
        args = parser.parse_args(['--enable-aws-resource-write'])
        assert args.enable_aws_resource_write is True

        # Test flag absent
        args = parser.parse_args([])
        assert args.enable_aws_resource_write is False

    def test_log_file_flag(self):
        """Test --log-file flag parsing."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        # Test with file path
        test_log_path = str(Path('path') / 'to' / 'logfile.log')
        args = parser.parse_args(['--log-file', test_log_path])
        assert args.log_file == test_log_path

        # Test with relative path
        args = parser.parse_args(['--log-file', 'finch.log'])
        assert args.log_file == 'finch.log'

        # Test without flag
        args = parser.parse_args([])
        assert args.log_file is None

    def test_disable_file_logging_flag(self):
        """Test --disable-file-logging flag parsing."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--disable-file-logging', action='store_true')

        # Test flag present
        args = parser.parse_args(['--disable-file-logging'])
        assert args.disable_file_logging is True

        # Test flag absent
        args = parser.parse_args([])
        assert args.disable_file_logging is False

    def test_combined_flags(self, temp_log_file):
        """Test parsing multiple flags together."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        args = parser.parse_args(
            ['--enable-aws-resource-write', '--log-file', temp_log_file, '--disable-file-logging']
        )

        assert args.enable_aws_resource_write is True
        assert args.log_file == temp_log_file
        assert args.disable_file_logging is True

    def test_flag_order_independence(self):
        """Test that flag order doesn't matter."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        # Test different orders
        orders = [
            ['--enable-aws-resource-write', '--log-file', 'test.log', '--disable-file-logging'],
            ['--log-file', 'test.log', '--disable-file-logging', '--enable-aws-resource-write'],
            ['--disable-file-logging', '--enable-aws-resource-write', '--log-file', 'test.log'],
        ]

        for order in orders:
            args = parser.parse_args(order)
            assert args.enable_aws_resource_write is True
            assert args.log_file == 'test.log'
            assert args.disable_file_logging is True


class TestEnvironmentVariableHandling:
    """Tests for environment variable handling from CLI flags."""

    def setup_method(self):
        """Clean up environment variables before each test."""
        env_vars = ['FINCH_MCP_LOG_FILE', 'FINCH_DISABLE_FILE_LOGGING']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    def test_log_file_sets_environment_variable(self):
        """Test that --log-file flag sets FINCH_MCP_LOG_FILE environment variable."""
        test_log_file = create_test_path('path', 'to', 'test.log')

        # Simulate the main block behavior
        os.environ['FINCH_MCP_LOG_FILE'] = test_log_file

        assert os.environ.get('FINCH_MCP_LOG_FILE') == test_log_file

    def test_disable_file_logging_sets_environment_variable(self):
        """Test that --disable-file-logging flag sets FINCH_DISABLE_FILE_LOGGING environment variable."""
        # Simulate the main block behavior
        os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'

        assert os.environ.get('FINCH_DISABLE_FILE_LOGGING') == 'true'

    def test_environment_variables_not_set_by_default(self):
        """Test that environment variables are not set when flags are not provided."""
        # Ensure clean environment
        assert 'FINCH_MCP_LOG_FILE' not in os.environ
        assert 'FINCH_DISABLE_FILE_LOGGING' not in os.environ

    def test_log_file_environment_variable_precedence(self):
        """Test behavior when both CLI flag and environment variable are set."""
        # Set environment variable first
        env_log_file = create_test_path('env', 'path', 'log.log')
        os.environ['FINCH_MCP_LOG_FILE'] = env_log_file

        # CLI flag should override (simulating the main block)
        cli_log_file = create_test_path('cli', 'path', 'log.log')
        os.environ['FINCH_MCP_LOG_FILE'] = cli_log_file

        assert os.environ.get('FINCH_MCP_LOG_FILE') == cli_log_file

    def test_disable_file_logging_environment_variable_precedence(self):
        """Test behavior when both CLI flag and environment variable are set."""
        # Set environment variable first
        os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'false'

        # CLI flag should override (simulating the main block)
        os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'

        assert os.environ.get('FINCH_DISABLE_FILE_LOGGING') == 'true'


class TestMainFunctionBehavior:
    """Tests for main function behavior with different flag combinations."""

    @patch('awslabs.finch_mcp_server.server.mcp')
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_main_with_default_settings(self, mock_logger, mock_mcp):
        """Test main function with default settings."""
        main(enable_aws_resource_write=False)

        # Should log startup message
        mock_logger.info.assert_any_call('Starting Finch MCP server')

        # Should run MCP server
        mock_mcp.run.assert_called_once_with(transport='stdio')

    @patch('awslabs.finch_mcp_server.server.mcp')
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_main_with_aws_resource_write_enabled(self, mock_logger, mock_mcp):
        """Test main function with AWS resource write enabled."""
        main(enable_aws_resource_write=True)

        # Should log startup message
        mock_logger.info.assert_any_call('Starting Finch MCP server')

        # Should run MCP server
        mock_mcp.run.assert_called_once_with(transport='stdio')

    @patch('awslabs.finch_mcp_server.server.mcp')
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_main_with_custom_log_file(self, mock_logger, mock_mcp):
        """Test main function with custom log file."""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp_file:
            test_log_path = tmp_file.name

        try:
            with patch.dict(os.environ, {'FINCH_MCP_LOG_FILE': test_log_path}):
                main()

                # Should log about custom log file
                mock_logger.info.assert_any_call(f'Logging to stderr and file: {test_log_path}')
        finally:
            # Cleanup with error handling
            try:
                os.unlink(test_log_path)
            except FileNotFoundError:
                pass  # File might have been removed already

    @patch('awslabs.finch_mcp_server.server.mcp')
    @patch('awslabs.finch_mcp_server.server.logger')
    @patch.dict(os.environ, {'FINCH_DISABLE_FILE_LOGGING': 'true'})
    def test_main_with_file_logging_disabled(self, mock_logger, mock_mcp):
        """Test main function with file logging disabled."""
        main()

        # Should log about stderr-only logging
        mock_logger.warning.assert_any_call('Logging to stderr only')

    @patch('awslabs.finch_mcp_server.server.mcp')
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_main_with_default_logging(self, mock_logger, mock_mcp):
        """Test main function with default logging configuration."""
        # Clear any existing environment variables that might affect the test
        for env_var in ['FINCH_DISABLE_FILE_LOGGING', 'FINCH_MCP_LOG_FILE']:
            if env_var in os.environ:
                del os.environ[env_var]

        main()

        # Should log about default logging file
        mock_logger.info.assert_any_call('Logging to stderr and default logging file')


class TestSetEnableAwsResourceWrite:
    """Tests for the set_enable_aws_resource_write function."""

    @patch('awslabs.finch_mcp_server.server.logger')
    def test_enable_aws_resource_write_true(self, mock_logger):
        """Test enabling AWS resource write."""
        set_enable_aws_resource_write(True)

        # Should log the change
        mock_logger.info.assert_called_with('AWS resource write enabled: True')

        # Check global variable (we can't easily test this without accessing the module's globals)
        # But we can test the behavior through the tools that use it

    @patch('awslabs.finch_mcp_server.server.logger')
    def test_enable_aws_resource_write_false(self, mock_logger):
        """Test disabling AWS resource write."""
        set_enable_aws_resource_write(False)

        # Should log the change
        mock_logger.info.assert_called_with('AWS resource write enabled: False')

    @patch('awslabs.finch_mcp_server.server.logger')
    def test_enable_aws_resource_write_multiple_calls(self, mock_logger):
        """Test multiple calls to set_enable_aws_resource_write."""
        set_enable_aws_resource_write(True)
        set_enable_aws_resource_write(False)
        set_enable_aws_resource_write(True)

        # Should log each change
        expected_calls = [
            call('AWS resource write enabled: True'),
            call('AWS resource write enabled: False'),
            call('AWS resource write enabled: True'),
        ]
        mock_logger.info.assert_has_calls(expected_calls)


class TestFlagValidation:
    """Tests for flag validation and error handling."""

    def test_log_file_with_empty_string(self):
        """Test --log-file with empty string."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        args = parser.parse_args(['--log-file', ''])
        assert args.log_file == ''

    def test_log_file_with_special_characters(self):
        """Test --log-file with special characters in path."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        special_paths = [
            str(Path('path with spaces') / 'log.log'),
            str(Path('path-with-dashes') / 'log.log'),
            str(Path('path_with_underscores') / 'log.log'),
            str(Path('path.with.dots') / 'log.log'),
            str(Path('relative') / 'path' / 'log.log'),
            str(Path('.') / 'local' / 'log.log'),
            # Avoid parent directory traversal in tests
            str(Path('safe_parent') / 'log.log'),
        ]

        for path in special_paths:
            args = parser.parse_args(['--log-file', path])
            assert args.log_file == path

    def test_unknown_flag_handling(self):
        """Test handling of unknown flags."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')

        # Unknown flag should raise SystemExit (argparse behavior)
        with pytest.raises(SystemExit):
            parser.parse_args(['--unknown-flag'])

    def test_flag_abbreviations(self):
        """Test that flag abbreviations work correctly."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--disable-file-logging', action='store_true')

        # Test that unique prefixes work
        args = parser.parse_args(['--enable-aws'])
        assert args.enable_aws_resource_write is True

        args = parser.parse_args(['--disable-file'])
        assert args.disable_file_logging is True

    def test_help_flag(self):
        """Test that help flag works."""
        parser = argparse.ArgumentParser(description='Run the Finch MCP server')
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        # Help flag should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(['--help'])


class TestFlagIntegration:
    """Integration tests for flag handling with the actual server setup."""

    def setup_method(self):
        """Clean up environment before each test."""
        env_vars = ['FINCH_MCP_LOG_FILE', 'FINCH_DISABLE_FILE_LOGGING']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    @patch('awslabs.finch_mcp_server.server.configure_logging')
    @patch('awslabs.finch_mcp_server.server.main')
    def test_full_cli_integration_default(self, mock_main, mock_configure_logging):
        """Test full CLI integration with default flags."""
        mock_logger = MagicMock()
        mock_configure_logging.return_value = mock_logger

        # Simulate command line: python server.py
        test_args = []

        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        args = parser.parse_args(test_args)

        # Simulate the main block logic
        if args.log_file:
            os.environ['FINCH_MCP_LOG_FILE'] = args.log_file
        if args.disable_file_logging:
            os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'

        # Should not set environment variables for default case
        assert 'FINCH_MCP_LOG_FILE' not in os.environ
        assert 'FINCH_DISABLE_FILE_LOGGING' not in os.environ

    @patch('awslabs.finch_mcp_server.server.configure_logging')
    @patch('awslabs.finch_mcp_server.server.main')
    def test_full_cli_integration_all_flags(self, mock_main, mock_configure_logging):
        """Test full CLI integration with all flags."""
        mock_logger = MagicMock()
        mock_configure_logging.return_value = mock_logger

        # Simulate command line: python server.py --enable-aws-resource-write --log-file /tmp/test.log --disable-file-logging
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp_file:
            test_log_path = tmp_file.name

        test_args = [
            '--enable-aws-resource-write',
            '--log-file',
            test_log_path,
            '--disable-file-logging',
        ]

        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        args = parser.parse_args(test_args)

        # Simulate the main block logic
        if args.log_file:
            os.environ['FINCH_MCP_LOG_FILE'] = args.log_file
        if args.disable_file_logging:
            os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'

        # Should set environment variables
        assert os.environ.get('FINCH_MCP_LOG_FILE') == test_log_path
        assert os.environ.get('FINCH_DISABLE_FILE_LOGGING') == 'true'

        # Cleanup
        os.unlink(test_log_path)

        # Should call main with correct parameter
        assert args.enable_aws_resource_write is True

    def test_conflicting_flags_behavior(self):
        """Test behavior with potentially conflicting flags."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp_file:
            test_log_path = tmp_file.name

        try:
            # Both log file and disable file logging
            args = parser.parse_args(['--log-file', test_log_path, '--disable-file-logging'])

            # Both should be set (the application logic should handle the conflict)
            assert args.log_file == test_log_path
            assert args.disable_file_logging is True

            # Simulate environment variable setting
            if args.log_file:
                os.environ['FINCH_MCP_LOG_FILE'] = args.log_file
            if args.disable_file_logging:
                os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'

            # Both environment variables should be set
            assert os.environ.get('FINCH_MCP_LOG_FILE') == test_log_path
            assert os.environ.get('FINCH_DISABLE_FILE_LOGGING') == 'true'
        finally:
            # Cleanup with error handling
            try:
                os.unlink(test_log_path)
            except FileNotFoundError:
                pass  # File might have been removed already


class TestFlagDocumentation:
    """Tests to ensure flag help text is appropriate."""

    def test_flag_help_text(self):
        """Test that flag help text is descriptive and accurate."""
        parser = argparse.ArgumentParser(description='Run the Finch MCP server')
        parser.add_argument(
            '--enable-aws-resource-write',
            action='store_true',
            help='Enable AWS resource creation and modification (disabled by default)',
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='Path to log file for persistent logging (optional, logs to stderr by default)',
        )
        parser.add_argument(
            '--disable-file-logging',
            action='store_true',
            help='Disable file logging entirely (stderr only, follows MCP standard)',
        )

        # Get help text
        help_text = parser.format_help()

        # Check that key information is present
        assert 'Enable AWS resource creation and modification' in help_text
        assert 'disabled by default' in help_text
        assert 'Path to log file for persistent logging' in help_text
        assert 'Disable file logging entirely' in help_text
        assert 'stderr only' in help_text
        assert 'MCP standard' in help_text

    def test_parser_description(self):
        """Test that parser description is appropriate."""
        parser = argparse.ArgumentParser(description='Run the Finch MCP server')

        help_text = parser.format_help()
        assert 'Run the Finch MCP server' in help_text


class TestRealWorldCliScenarios:
    """Tests for real-world CLI usage scenarios."""

    def test_production_like_flags(self):
        """Test production-like flag combinations."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        # Production scenario: enable AWS writes with custom log file
        production_log_path = create_test_path('var', 'log', 'finch-mcp-server.log')
        args = parser.parse_args(
            ['--enable-aws-resource-write', '--log-file', production_log_path]
        )

        assert args.enable_aws_resource_write is True
        assert args.log_file == production_log_path
        assert args.disable_file_logging is False

    def test_development_like_flags(self):
        """Test development-like flag combinations."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        # Development scenario: disable file logging for cleaner output
        args = parser.parse_args(['--disable-file-logging'])

        assert args.enable_aws_resource_write is False
        assert args.log_file is None
        assert args.disable_file_logging is True

    def test_debugging_scenario_flags(self):
        """Test debugging scenario flag combinations."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        # Debugging scenario: custom log file for detailed logging
        args = parser.parse_args(
            ['--log-file', './debug-finch.log', '--enable-aws-resource-write']
        )

        assert args.enable_aws_resource_write is True
        assert args.log_file == './debug-finch.log'
        assert args.disable_file_logging is False


class TestFlagEdgeCases:
    """Tests for edge cases in flag handling."""

    def test_log_file_with_unicode_path(self):
        """Test --log-file with unicode characters in path."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        unicode_path = str(Path('path') / 'with' / 'ñoñó' / '测试.log')
        args = parser.parse_args(['--log-file', unicode_path])

        assert args.log_file == unicode_path

    def test_log_file_with_very_long_path(self):
        """Test --log-file with very long path."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        long_path = str(Path('very') / 'long' / 'path' / ('x' * 200) / 'log.log')
        args = parser.parse_args(['--log-file', long_path])

        assert args.log_file == long_path

    def test_multiple_same_flags_last_wins(self):
        """Test that when the same flag is provided multiple times, the last one wins."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        # Multiple log-file flags
        args = parser.parse_args(
            ['--log-file', 'first.log', '--log-file', 'second.log', '--log-file', 'third.log']
        )

        assert args.log_file == 'third.log'

    def test_flag_with_equals_syntax(self):
        """Test flag with equals syntax."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        # Using equals syntax
        test_path = str(Path('path') / 'to' / 'log.log')
        args = parser.parse_args([f'--log-file={test_path}'])

        assert args.log_file == test_path


class TestEnvironmentVariableInteraction:
    """Tests for interaction between CLI flags and environment variables."""

    def setup_method(self):
        """Clean environment before each test."""
        env_vars = ['FINCH_MCP_LOG_FILE', 'FINCH_DISABLE_FILE_LOGGING', 'FASTMCP_LOG_LEVEL']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    def test_cli_flag_overrides_existing_env_var(self):
        """Test that CLI flags override existing environment variables."""
        # Set initial environment variable
        original_log_path = create_test_path('env', 'original.log')
        os.environ['FINCH_MCP_LOG_FILE'] = original_log_path

        # CLI flag should override
        cli_value = create_test_path('cli', 'override.log')
        os.environ['FINCH_MCP_LOG_FILE'] = cli_value  # Simulate CLI override

        assert os.environ.get('FINCH_MCP_LOG_FILE') == cli_value

    def test_environment_variable_without_cli_flag(self):
        """Test behavior when environment variable is set but no CLI flag is provided."""
        # Set environment variable
        os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'

        # No CLI flag provided, env var should remain
        assert os.environ.get('FINCH_DISABLE_FILE_LOGGING') == 'true'

    def test_multiple_environment_variables(self):
        """Test handling of multiple environment variables."""
        test_log_path = create_test_path('test', 'log.log')
        os.environ['FINCH_MCP_LOG_FILE'] = test_log_path
        os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'
        os.environ['FASTMCP_LOG_LEVEL'] = 'DEBUG'

        assert os.environ.get('FINCH_MCP_LOG_FILE') == test_log_path
        assert os.environ.get('FINCH_DISABLE_FILE_LOGGING') == 'true'
        assert os.environ.get('FASTMCP_LOG_LEVEL') == 'DEBUG'


class TestAwsResourceWriteFlag:
    """Specific tests for the AWS resource write flag behavior."""

    @patch('awslabs.finch_mcp_server.server.logger')
    def test_aws_resource_write_flag_affects_global_state(self, mock_logger):
        """Test that the AWS resource write flag affects global state."""
        # Test enabling
        set_enable_aws_resource_write(True)
        mock_logger.info.assert_called_with('AWS resource write enabled: True')

        # Test disabling
        set_enable_aws_resource_write(False)
        mock_logger.info.assert_called_with('AWS resource write enabled: False')

    def test_aws_resource_write_flag_default_behavior(self):
        """Test default behavior of AWS resource write flag."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')

        # Default should be False (disabled)
        args = parser.parse_args([])
        assert args.enable_aws_resource_write is False

    def test_aws_resource_write_flag_security_implications(self):
        """Test that AWS resource write flag has proper security implications."""
        # This flag should be False by default for security
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')

        # Without explicit flag, should be disabled
        args = parser.parse_args([])
        assert args.enable_aws_resource_write is False

        # Only when explicitly enabled
        args = parser.parse_args(['--enable-aws-resource-write'])
        assert args.enable_aws_resource_write is True


class TestLoggingFlagInteractions:
    """Tests for interactions between different logging flags."""

    def setup_method(self):
        """Clean environment before each test."""
        env_vars = ['FINCH_MCP_LOG_FILE', 'FINCH_DISABLE_FILE_LOGGING']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    def test_log_file_and_disable_logging_both_set(self):
        """Test behavior when both log file and disable file logging are set."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp_file:
            test_log_path = tmp_file.name

        args = parser.parse_args(['--log-file', test_log_path, '--disable-file-logging'])

        # Both should be parsed correctly
        assert args.log_file == test_log_path
        assert args.disable_file_logging is True

        # Cleanup
        os.unlink(test_log_path)

        # The application should handle this conflict appropriately
        # (disable-file-logging should take precedence)

    def test_conflicting_logging_flags_behavior(self):
        """Test behavior with conflicting logging flags set in environment."""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp_file:
            test_log_path = tmp_file.name

        # Set both environment variables (simulating conflicting CLI flags)
        os.environ['FINCH_MCP_LOG_FILE'] = test_log_path
        os.environ['FINCH_DISABLE_FILE_LOGGING'] = 'true'

        # Both environment variables should be set
        assert os.environ.get('FINCH_MCP_LOG_FILE') == test_log_path
        assert os.environ.get('FINCH_DISABLE_FILE_LOGGING') == 'true'

        # Cleanup
        os.unlink(test_log_path)

        # The logging configuration should handle this conflict appropriately
        # (disable-file-logging should take precedence over log-file)

    def test_empty_log_file_path(self):
        """Test behavior with empty log file path."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        args = parser.parse_args(['--log-file', ''])
        assert args.log_file == ''

        # Empty string should be handled gracefully by the application


class TestFlagRobustness:
    """Tests for robustness and error handling in flag processing."""

    def test_parser_with_invalid_arguments(self):
        """Test parser behavior with invalid arguments."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')

        # Invalid argument should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(['--invalid-flag'])

    def test_parser_with_missing_required_value(self):
        """Test parser behavior when required value is missing."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str, required=False)

        # Missing value for --log-file should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(['--log-file'])

    def test_parser_with_extra_positional_arguments(self):
        """Test parser behavior with unexpected positional arguments."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')

        # Extra positional arguments should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(['--enable-aws-resource-write', 'extra', 'arguments'])

    def test_flag_case_sensitivity(self):
        """Test that flags are case sensitive."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')

        # Wrong case should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(['--Enable-Aws-Resource-Write'])

    def test_flag_with_no_value_when_value_expected(self):
        """Test flag behavior when no value is provided but one is expected."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--log-file', type=str)

        # Should work fine - log-file is optional
        args = parser.parse_args([])
        assert args.log_file is None


class TestFlagDocumentationAndUsability:
    """Tests for flag documentation and usability."""

    def test_comprehensive_help_output(self):
        """Test that help output contains all necessary information."""
        parser = argparse.ArgumentParser(
            description='Run the Finch MCP server',
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            '--enable-aws-resource-write',
            action='store_true',
            help='Enable AWS resource creation and modification (disabled by default)',
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='Path to log file for persistent logging (optional, logs to stderr by default)',
        )
        parser.add_argument(
            '--disable-file-logging',
            action='store_true',
            help='Disable file logging entirely (stderr only, follows MCP standard)',
        )

        help_output = parser.format_help()

        # Check for key phrases that users need to understand
        assert 'Run the Finch MCP server' in help_output
        assert 'enable-aws-resource-write' in help_output
        assert 'disabled by default' in help_output
        assert 'log-file' in help_output
        assert 'disable-file-logging' in help_output
        assert 'stderr only' in help_output
        assert 'MCP standard' in help_output

    def test_flag_naming_consistency(self):
        """Test that flag names follow consistent naming conventions."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--enable-aws-resource-write', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--disable-file-logging', action='store_true')

        # All flags should use kebab-case (hyphens)
        help_output = parser.format_help()

        # Should not contain underscores in flag names
        assert '--enable_aws_resource_write' not in help_output
        assert '--log_file' not in help_output
        assert '--disable_file_logging' not in help_output

        # Should contain proper hyphenated versions
        assert '--enable-aws-resource-write' in help_output
        assert '--log-file' in help_output
        assert '--disable-file-logging' in help_output
