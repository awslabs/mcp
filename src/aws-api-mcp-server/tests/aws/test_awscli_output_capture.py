"""Tests for thread-safe awscli output capture (ContextVar-based).

Tests the _capture_awscli_output context manager and the monkey-patches
applied by _install_awscli_output_patch.
"""

import pytest
import sys
import threading
from awslabs.aws_api_mcp_server.core.aws.driver import translate_cli_to_ir
from awslabs.aws_api_mcp_server.core.aws.service import (
    _capture_awscli_output,
    _capture_stderr,
    _capture_stdout,
    _install_awscli_output_patch,
    execute_awscli_customization,
)
from awslabs.aws_api_mcp_server.core.common.command import IRCommand
from awslabs.aws_api_mcp_server.core.common.errors import AwsApiMcpError
from awslabs.aws_api_mcp_server.core.common.models import (
    AwsCliAliasResponse,
    CommandMetadata,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch


class TestCaptureAwscliOutput:
    """Tests for the _capture_awscli_output context manager."""

    def test_capture_stdout_via_get_stdout_text_writer(self):
        """Output written via get_stdout_text_writer is captured."""
        import awscli.compat

        _install_awscli_output_patch()

        with _capture_awscli_output() as (stdout_buf, stderr_buf):
            writer = awscli.compat.get_stdout_text_writer()
            writer.write('hello from formatter')

        assert stdout_buf.getvalue() == 'hello from formatter'
        assert stderr_buf.getvalue() == ''

    def test_capture_stderr_via_get_stderr_text_writer(self):
        """Output written via get_stderr_text_writer is captured."""
        import awscli.compat

        _install_awscli_output_patch()

        with _capture_awscli_output() as (stdout_buf, stderr_buf):
            writer = awscli.compat.get_stderr_text_writer()
            writer.write('error message')

        assert stdout_buf.getvalue() == ''
        assert stderr_buf.getvalue() == 'error message'

    def test_capture_stdout_via_uni_print(self):
        """Output written via uni_print (no out_file) is captured to stdout."""
        import awscli.customizations.utils

        _install_awscli_output_patch()

        with _capture_awscli_output() as (stdout_buf, stderr_buf):
            awscli.customizations.utils.uni_print('bucket listing\n')

        assert stdout_buf.getvalue() == 'bucket listing\n'
        assert stderr_buf.getvalue() == ''

    def test_capture_stderr_via_uni_print(self):
        """Output written via uni_print(out_file=sys.stderr) is captured to stderr."""
        import awscli.customizations.utils

        _install_awscli_output_patch()

        with _capture_awscli_output() as (stdout_buf, stderr_buf):
            awscli.customizations.utils.uni_print('warning\n', sys.stderr)

        assert stdout_buf.getvalue() == ''
        assert stderr_buf.getvalue() == 'warning\n'

    def test_capture_via_clidriver_get_stderr_text_writer(self):
        """Output via clidriver's local get_stderr_text_writer binding is captured."""
        import awscli.clidriver

        _install_awscli_output_patch()

        with _capture_awscli_output() as (stdout_buf, stderr_buf):
            writer = awscli.clidriver.get_stderr_text_writer()
            writer.write('clidriver error\n')

        assert stderr_buf.getvalue() == 'clidriver error\n'

    def test_capture_via_s3_subcommands_uni_print(self):
        """S3 subcommands' local uni_print binding writes to capture."""
        import awscli.customizations.s3.subcommands

        _install_awscli_output_patch()

        with _capture_awscli_output() as (stdout_buf, stderr_buf):
            awscli.customizations.s3.subcommands.uni_print('2024-01-01 bucket-name\n')

        assert stdout_buf.getvalue() == '2024-01-01 bucket-name\n'

    def test_no_capture_outside_context(self):
        """Outside the context manager, output goes to real stdout/stderr."""
        import awscli.compat

        _install_awscli_output_patch()

        # Outside context: get_stdout_text_writer should return real stdout
        writer = awscli.compat.get_stdout_text_writer()
        assert writer is sys.stdout or hasattr(writer, 'write')
        # Should not raise — just goes to real stdout
        # (We don't assert on sys.stdout content in tests)

    def test_context_var_isolation_nested(self):
        """Nested capture contexts are independent."""
        import awscli.customizations.utils

        _install_awscli_output_patch()

        with _capture_awscli_output() as (outer_stdout, outer_stderr):
            awscli.customizations.utils.uni_print('outer\n')

            with _capture_awscli_output() as (inner_stdout, inner_stderr):
                awscli.customizations.utils.uni_print('inner\n')

            # After inner exits, outer is active again
            awscli.customizations.utils.uni_print('outer again\n')

        assert inner_stdout.getvalue() == 'inner\n'
        assert outer_stdout.getvalue() == 'outer\nouter again\n'

    def test_capture_resets_on_exception(self):
        """ContextVar is reset even if an exception occurs inside the context."""
        import awscli.compat

        _install_awscli_output_patch()

        stdout_buf = None
        try:
            with _capture_awscli_output() as (stdout_buf, stderr_buf):
                awscli.compat.get_stdout_text_writer().write('before error')
                raise ValueError('test error')
        except ValueError:
            pass

        # After exception, capture should be inactive
        assert _capture_stdout.get() is None
        assert _capture_stderr.get() is None
        # The buffer should still have what was written before the error
        assert stdout_buf is not None
        assert stdout_buf.getvalue() == 'before error'


class TestCaptureThreadSafety:
    """Tests verifying thread-safety of the ContextVar-based capture."""

    def test_concurrent_captures_are_isolated(self):
        """Multiple threads capturing simultaneously get independent buffers."""
        import awscli.customizations.utils

        _install_awscli_output_patch()

        results = {}
        barrier = threading.Barrier(4)

        def worker(thread_id):
            barrier.wait()  # Synchronize start
            with _capture_awscli_output() as (stdout_buf, stderr_buf):
                # Simulate some work with interleaving
                for i in range(10):
                    awscli.customizations.utils.uni_print(f't{thread_id}-{i}\n')
                results[thread_id] = stdout_buf.getvalue()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should only see its own output
        for thread_id in range(4):
            expected_lines = [f't{thread_id}-{i}' for i in range(10)]
            actual_lines = results[thread_id].strip().split('\n')
            assert actual_lines == expected_lines, f"Thread {thread_id} saw other thread's output"

    def test_thread_pool_executor_isolation(self):
        """ThreadPoolExecutor workers get isolated capture buffers."""
        import awscli.customizations.utils

        _install_awscli_output_patch()

        def task(task_id):
            with _capture_awscli_output() as (stdout_buf, stderr_buf):
                awscli.customizations.utils.uni_print(f'task-{task_id}-output\n')
                return stdout_buf.getvalue()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(task, i): i for i in range(8)}
            for future in as_completed(futures):
                task_id = futures[future]
                result = future.result()
                assert result == f'task-{task_id}-output\n'

    def test_one_thread_capturing_does_not_affect_another(self):
        """A thread without capture active is unaffected by another thread's capture."""
        import awscli.compat

        _install_awscli_output_patch()

        non_capturing_saw_real_stdout = threading.Event()
        capturing_started = threading.Event()

        def capturing_thread():
            with _capture_awscli_output() as (stdout_buf, stderr_buf):
                capturing_started.set()
                # Wait for non-capturing thread to check
                non_capturing_saw_real_stdout.wait(timeout=5)

        def non_capturing_thread():
            capturing_started.wait(timeout=5)
            # This thread has no active capture, should get real stdout
            writer = awscli.compat.get_stdout_text_writer()
            # Real stdout (not a StringIO capture buffer)
            assert writer is not None
            # The writer should be the original stdout or equivalent
            assert _capture_stdout.get() is None
            non_capturing_saw_real_stdout.set()

        t1 = threading.Thread(target=capturing_thread)
        t2 = threading.Thread(target=non_capturing_thread)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert non_capturing_saw_real_stdout.is_set()


class TestExecuteAwscliCustomizationWithCapture:
    """Tests for execute_awscli_customization using the new ContextVar capture."""

    @patch('awslabs.aws_api_mcp_server.core.aws.service.get_awscli_driver')
    def test_stdout_captured_from_driver(self, mock_get_driver):
        """Output written by driver.main via patched sinks is captured."""
        import awscli.customizations.utils

        _install_awscli_output_patch()

        mock_driver = Mock()

        def fake_main(args):
            # Simulate what awscli does: write via uni_print
            awscli.customizations.utils.uni_print('2024-01-01 my-bucket\n')
            return 0

        mock_driver.main.side_effect = fake_main
        mock_get_driver.return_value = mock_driver

        cli_command = 'aws s3 ls'
        ir_command = translate_cli_to_ir(cli_command).command
        assert ir_command is not None

        result = execute_awscli_customization(cli_command, ir_command)

        assert isinstance(result, AwsCliAliasResponse)
        assert result.response == '2024-01-01 my-bucket\n'
        assert result.error == ''

    @patch('awslabs.aws_api_mcp_server.core.aws.service.get_awscli_driver')
    def test_stderr_captured_raises_error(self, mock_get_driver):
        """When only stderr has content, an AwsApiMcpError is raised."""
        import awscli.compat

        _install_awscli_output_patch()

        mock_driver = Mock()

        def fake_main(args):
            # Simulate awscli writing error via get_stderr_text_writer
            writer = awscli.compat.get_stderr_text_writer()
            writer.write('\nAn error occurred (NoSuchBucket)\n')
            return 255

        mock_driver.main.side_effect = fake_main
        mock_get_driver.return_value = mock_driver

        ir_command = IRCommand(
            command_metadata=CommandMetadata(
                service_sdk_name='s3',
                service_full_sdk_name='Amazon S3',
                operation_sdk_name='ls',
            ),
            parameters={},
            region='us-east-1',
            is_awscli_customization=True,
        )

        with pytest.raises(AwsApiMcpError) as exc_info:
            execute_awscli_customization('aws s3 ls s3://no-such-bucket/', ir_command)

        assert 'NoSuchBucket' in str(exc_info.value)

    @patch('awslabs.aws_api_mcp_server.core.aws.service.get_awscli_driver')
    def test_stderr_captured_via_clidriver_binding(self, mock_get_driver):
        """Errors written via clidriver's local get_stderr_text_writer are captured."""
        import awscli.clidriver

        _install_awscli_output_patch()

        mock_driver = Mock()

        def fake_main(args):
            # Simulate clidriver's write_exception path
            writer = awscli.clidriver.get_stderr_text_writer()
            writer.write('\nClientError: bucket does not exist\n')
            return 255

        mock_driver.main.side_effect = fake_main
        mock_get_driver.return_value = mock_driver

        ir_command = IRCommand(
            command_metadata=CommandMetadata(
                service_sdk_name='s3',
                service_full_sdk_name='Amazon S3',
                operation_sdk_name='ls',
            ),
            parameters={},
            region='us-east-1',
            is_awscli_customization=True,
        )

        with pytest.raises(AwsApiMcpError) as exc_info:
            execute_awscli_customization('aws s3 ls s3://no-such-bucket/', ir_command)

        assert 'bucket does not exist' in str(exc_info.value)

    @patch('awslabs.aws_api_mcp_server.core.aws.service.get_awscli_driver')
    def test_both_stdout_and_stderr_captured(self, mock_get_driver):
        """When both stdout and stderr have content, response includes both."""
        import awscli.compat
        import awscli.customizations.utils

        _install_awscli_output_patch()

        mock_driver = Mock()

        def fake_main(args):
            awscli.customizations.utils.uni_print('partial output\n')
            writer = awscli.compat.get_stderr_text_writer()
            writer.write('warning: something\n')
            return 0

        mock_driver.main.side_effect = fake_main
        mock_get_driver.return_value = mock_driver

        ir_command = IRCommand(
            command_metadata=CommandMetadata(
                service_sdk_name='s3',
                service_full_sdk_name='Amazon S3',
                operation_sdk_name='ls',
            ),
            parameters={},
            region='us-east-1',
            is_awscli_customization=True,
        )

        result = execute_awscli_customization('aws s3 ls', ir_command)

        assert result.response == 'partial output\n'
        assert result.error == 'warning: something\n'

    @patch('awslabs.aws_api_mcp_server.core.aws.service.get_awscli_driver')
    def test_driver_exception_raises_mcp_error(self, mock_get_driver):
        """When driver.main raises an exception, AwsApiMcpError is raised."""
        mock_driver = Mock()
        mock_driver.main.side_effect = RuntimeError('segfault simulation')
        mock_get_driver.return_value = mock_driver

        ir_command = IRCommand(
            command_metadata=CommandMetadata(
                service_sdk_name='s3',
                service_full_sdk_name='Amazon S3',
                operation_sdk_name='ls',
            ),
            parameters={},
            region='us-east-1',
            is_awscli_customization=True,
        )

        with pytest.raises(AwsApiMcpError) as exc_info:
            execute_awscli_customization('aws s3 ls', ir_command)

        assert 'segfault simulation' in str(exc_info.value)

    @patch('awslabs.aws_api_mcp_server.core.aws.service.get_awscli_driver')
    def test_concurrent_executions_isolated(self, mock_get_driver):
        """Concurrent execute_awscli_customization calls don't leak output."""
        import awscli.customizations.utils

        _install_awscli_output_patch()

        barrier = threading.Barrier(4)

        def fake_main_factory(task_id):
            def fake_main(args):
                barrier.wait()  # Synchronize
                for i in range(5):
                    awscli.customizations.utils.uni_print(f'task{task_id}-line{i}\n')
                return 0

            return fake_main

        results = {}

        # Use side_effect to return a unique driver per call, keyed by thread
        thread_drivers = {}

        def get_driver_for_thread(credentials):
            tid = threading.current_thread().ident
            return thread_drivers[tid]

        mock_get_driver.side_effect = get_driver_for_thread

        def run_task(task_id):
            driver = Mock()
            driver.main.side_effect = fake_main_factory(task_id)
            thread_drivers[threading.current_thread().ident] = driver

            ir_command = IRCommand(
                command_metadata=CommandMetadata(
                    service_sdk_name='s3',
                    service_full_sdk_name='Amazon S3',
                    operation_sdk_name='ls',
                ),
                parameters={},
                region='us-east-1',
                is_awscli_customization=True,
            )

            result = execute_awscli_customization('aws s3 ls', ir_command)
            results[task_id] = result.response

        threads = [threading.Thread(target=run_task, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for task_id in range(4):
            expected = ''.join(f'task{task_id}-line{i}\n' for i in range(5))
            assert results[task_id] == expected, (
                f'Task {task_id} captured wrong output: {results[task_id]!r}'
            )


class TestPatchIdempotency:
    """Tests that _install_awscli_output_patch is safe to call multiple times."""

    def test_install_is_idempotent(self):
        """Calling _install_awscli_output_patch multiple times is safe."""
        import awscli.compat

        _install_awscli_output_patch()
        first_ref = awscli.compat.get_stdout_text_writer

        _install_awscli_output_patch()
        second_ref = awscli.compat.get_stdout_text_writer

        # Should be the same patched function, not double-wrapped
        assert first_ref is second_ref
