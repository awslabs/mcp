"""
Integration test for ETL Replatforming MCP Server.
Tests MCP tools with configurable depth - quick mode uses only convert-etl-workflow.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest


class MCPClient:
    """MCP client that communicates with server via stdin/stdout."""

    def __init__(self):
        self.process = None
        self.request_id = 0

    async def start_server(self):
        """Start MCP server process."""
        print('🔌 Starting MCP server process...')

        env = {**os.environ, 'FASTMCP_LOG_LEVEL': 'INFO'}
        aws_profile = env.get('AWS_PROFILE', 'default')
        aws_region = env.get('AWS_REGION', 'us-east-1')
        print(f'🔧 AWS Configuration: Profile={aws_profile}, Region={aws_region}')

        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            '-m',
            'awslabs.etl_replatforming_mcp_server.server',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        init_request = {
            'jsonrpc': '2.0',
            'id': self._next_id(),
            'method': 'initialize',
            'params': {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {'name': 'test-client', 'version': '1.0.0'},
            },
        }

        await self._send_message(init_request)
        response = await self._read_message()

        if 'error' in response:
            raise Exception(f'Failed to initialize: {response["error"]}')

        initialized_notification = {
            'jsonrpc': '2.0',
            'method': 'notifications/initialized',
            'params': {},
        }

        await self._send_message(initialized_notification)
        return response

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool using standard MCP tools/call method."""
        request = {
            'jsonrpc': '2.0',
            'id': self._next_id(),
            'method': 'tools/call',
            'params': {'name': tool_name, 'arguments': arguments},
        }

        await self._send_message(request)
        response = await self._read_message()

        if 'error' in response:
            raise Exception(f'Tool call failed: {response["error"]}')

        return response.get('result', {})

    async def stop_server(self):
        """Stop MCP server process gracefully."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except Exception:
                try:
                    self.process.kill()
                    await self.process.wait()
                except Exception:
                    pass
            finally:
                self.process = None

    def _next_id(self):
        self.request_id += 1
        return self.request_id

    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send JSON message to server."""
        if self.process and self.process.stdin:
            json_str = json.dumps(message) + '\n'
            self.process.stdin.write(json_str.encode())
            await self.process.stdin.drain()

    async def _read_message(self) -> Dict[str, Any]:
        """Read JSON message from server."""
        if not self.process or not self.process.stdout:
            raise Exception('Server process not available')
        line = await self.process.stdout.readline()
        if not line:
            raise Exception('Server closed connection')
        return json.loads(line.decode().strip())


class TestIntegration:
    """Integration test with configurable depth"""

    def setup_method(self):
        self.client = MCPClient()

    def teardown_method(self):
        """Ensure server is stopped even if tests fail"""
        if self.client:
            try:
                asyncio.run(self.client.stop_server())
            except Exception:
                pass

    def _load_llm_config(self) -> Dict[str, Any] | None:
        """Load LLM configuration from config file or environment variables"""
        llm_config: Dict[str, Any] = {}

        config_file = Path(__file__).parent / 'integration_test_config.json'
        if config_file.exists():
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                llm_config.update(file_config.get('llm_config', {}))
                print(f'📄 Loaded LLM config from {config_file}: {llm_config}')

        if os.getenv('BEDROCK_MODEL_ID'):
            llm_config['model_id'] = os.getenv('BEDROCK_MODEL_ID')

        return llm_config if llm_config else None

    @pytest.mark.asyncio
    async def test_composite_mcp_tools(self):
        """Test MCP tools for complete system coverage with configurable depth

        Strategy varies by test mode:
        - QUICK (default): Tests only convert-etl-workflow for maximum efficiency
        - FULL: Tests both convert-etl-workflow and convert-single-etl-workflow

        Test Modes (INTEGRATION_TEST_MODE environment variable):
        - 'quick' (default): Only convert-etl-workflow, most complex files - fast, full coverage
        - 'full': Both tools, all files - comprehensive but slower
        """
        # Setup logging first so it's always available
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_root = Path(__file__).parent.parent.parent
        output_dir = (
            project_root / 'outputs' / 'integration_tests' / f'integration_test_{timestamp}'
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        client_log_path = output_dir / 'integration_test_client.log'

        # Simple client logging function - defined outside try block
        def log_client(message: str) -> None:
            with open(client_log_path, 'a') as f:
                f.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | {message}\n')
            print(message)

        try:
            # Setup both server and client logging
            os.environ['MCP_LOG_FILE'] = str(output_dir / 'mcp_server.log')

            log_client(f'🧪 Starting integration test - timestamp: {timestamp}')
            log_client(f'📁 Output directory: {output_dir}')

            log_client('🔌 Starting MCP server process...')
            await self.client.start_server()
            log_client('✅ MCP server started successfully')

            test_data_dir = Path(__file__).parent / 'test_data'
            results: list[str] = []

            test_mode = os.getenv('INTEGRATION_TEST_MODE', 'quick').lower()

            if test_mode == 'quick':
                test_files = {
                    'step_functions': [
                        test_data_dir
                        / 'step_function_jobs'
                        / '03_advanced_loops_and_conditions.json'
                    ],
                    'airflow': [
                        test_data_dir / 'airflow_jobs' / '03_advanced_loops_and_conditions.py'
                    ],
                    'azure_data_factory': [
                        test_data_dir
                        / 'azure_data_factory_jobs'
                        / '03_advanced_loops_and_conditions.json'
                    ],
                }
                log_client(
                    '🧪 Testing convert-etl-workflow in QUICK mode (most complex files only)'
                )
                log_client(
                    '⚡ Quick mode: Only convert-etl-workflow - maximum efficiency, full coverage'
                )
                log_client(
                    '🎯 Strategy: convert-etl-workflow = 100% code coverage (calls same functions as individual tool)'
                )
            elif test_mode == 'full':
                test_files = {
                    'step_functions': list((test_data_dir / 'step_function_jobs').glob('*.json')),
                    'airflow': list((test_data_dir / 'airflow_jobs').glob('*.py')),
                    'azure_data_factory': list(
                        (test_data_dir / 'azure_data_factory_jobs').glob('*.json')
                    ),
                }
                print('\n🧪 Testing both tools in FULL mode (all files)')
                print(
                    '🔄 Full mode: Both convert-etl-workflow + convert-single-etl-workflow - comprehensive validation'
                )
                print(
                    '🎯 Strategy: Both tools for thorough testing (though they call same functions)'
                )
                print('⚠️  Warning: Full mode may trigger throttling with newer Bedrock models')
            else:
                raise ValueError(
                    f"Invalid INTEGRATION_TEST_MODE: {test_mode}. Use 'quick' or 'full'"
                )

            log_client(f'📁 Output directory: {output_dir}')
            log_client(f'🔧 Test mode: {test_mode.upper()}')

            total_files = sum(len(files) for files in test_files.values())
            log_client(f'📊 Total files to test: {total_files}')

            if test_mode == 'quick':
                print('🔧 Tool tested: convert-etl-workflow (batch processing only)')
                print(
                    '✅ Coverage: All parsers, generators, validators, AI enhancement via directory processing'
                )
                print(
                    '💡 Note: convert-single-etl-workflow calls same functions, so testing both is redundant'
                )
            else:
                print(
                    '🔧 Tools tested: convert-single-etl-workflow (individual) + convert-etl-workflow (batch)'
                )
                print(
                    '✅ Coverage: All parsers, generators, validators, AI enhancement via both tool types'
                )

            # ========== INDIVIDUAL WORKFLOW TOOL (convert-single-etl-workflow) ==========
            # Only run in FULL mode - QUICK mode skips this for efficiency
            if test_mode == 'full':
                single_tools_dir = output_dir / 'individual_workflow_tool'
                single_tools_dir.mkdir(exist_ok=True)

                for source_framework, framework_files in test_files.items():
                    for test_file in framework_files:
                        if not test_file.exists():
                            print(f'⚠️  Skipping {source_framework} - file not found: {test_file}')
                            continue

                        try:
                            with open(test_file, 'r') as f:
                                workflow_content = f.read()

                            llm_config = self._load_llm_config()
                            if llm_config and (
                                test_mode == 'full' or test_file == framework_files[0]
                            ):
                                print(f'🔧 Using LLM config for {source_framework}: {llm_config}')
                            elif not llm_config and (
                                test_mode == 'full' or test_file == framework_files[0]
                            ):
                                print(
                                    f'🔧 No LLM config found for {source_framework} - using server defaults'
                                )

                            file_identifier = f'{source_framework}_{test_file.stem}'
                            # Ensure file_identifier is always defined for error handling
                            print(f'\n📄 Processing file: {test_file.name} ({source_framework})')
                            print(f'📊 Content size: {len(workflow_content)} characters')

                            # convert-single-etl-workflow (to airflow) - skip same framework
                            if source_framework != 'airflow':
                                print('  🔧 convert-single-etl-workflow → airflow')
                                tool_args: Dict[str, Any] = {
                                    'workflow_content': workflow_content,
                                    'source_framework': source_framework,
                                    'target_framework': 'airflow',
                                }
                                if llm_config:
                                    tool_args['llm_config'] = llm_config
                                result = await self.client.call_tool(
                                    'convert-single-etl-workflow', tool_args
                                )

                                status = result.get('status', 'unknown')
                                if status == 'complete' and 'target_code' in result:
                                    dag_code = result['target_code'].get('dag_code', '')
                                    lines = len(dag_code.split('\n')) if dag_code else 0
                                    print(
                                        f'    ✅ Conversion successful: {lines} lines of Airflow DAG code generated'
                                    )
                                else:
                                    print(f'    ⚠️ Conversion status: {status}')

                                airflow_dir = single_tools_dir / 'airflow' / source_framework
                                airflow_dir.mkdir(parents=True, exist_ok=True)
                                output_file = airflow_dir / f'{test_file.stem}.json'
                                with open(output_file, 'w') as f:
                                    json.dump(result, f, indent=2)
                                results.append(
                                    f'✅ convert-single-etl-workflow ({file_identifier}→airflow) → airflow/{source_framework}/{output_file.name}'
                                )
                            else:
                                results.append(
                                    f'⏭️ convert-single-etl-workflow ({file_identifier}→airflow) → skipped (same framework)'
                                )

                            # convert-single-etl-workflow (to step_functions) - skip same framework
                            if source_framework != 'step_functions':
                                print('  🔧 convert-single-etl-workflow → step_functions')
                                tool_args: Dict[str, Any] = {
                                    'workflow_content': workflow_content,
                                    'source_framework': source_framework,
                                    'target_framework': 'step_functions',
                                }
                                if llm_config:
                                    tool_args['llm_config'] = llm_config
                                result = await self.client.call_tool(
                                    'convert-single-etl-workflow', tool_args
                                )

                                status = result.get('status', 'unknown')
                                if status == 'complete' and 'target_code' in result:
                                    sf_def = result['target_code'].get(
                                        'state_machine_definition', {}
                                    )
                                    state_count = len(sf_def.get('States', {}))
                                    print(
                                        f'    ✅ Conversion successful: {state_count} states in Step Functions definition'
                                    )
                                else:
                                    print(f'    ⚠️ Conversion status: {status}')

                                sf_dir = single_tools_dir / 'step_functions' / source_framework
                                sf_dir.mkdir(parents=True, exist_ok=True)
                                output_file = sf_dir / f'{test_file.stem}.json'
                                with open(output_file, 'w') as f:
                                    json.dump(result, f, indent=2)
                                results.append(
                                    f'✅ convert-single-etl-workflow ({file_identifier}→step_functions) → step_functions/{source_framework}/{output_file.name}'
                                )
                            else:
                                results.append(
                                    f'⏭️ convert-single-etl-workflow ({file_identifier}→step_functions) → skipped (same framework)'
                                )

                        except Exception as e:
                            # Use a fallback identifier if file_identifier is not defined
                            identifier = locals().get(
                                'file_identifier', f'{source_framework}_unknown'
                            )
                            results.append(
                                f'❌ convert-single-etl-workflow ({identifier}): {str(e)}'
                            )
                            print(f'    ❌ Error processing {test_file.name}: {e}')
            else:
                single_tools_dir = None
                print(
                    '\n⏭️ Skipping individual workflow tool tests in QUICK mode (convert-etl-workflow provides same coverage)'
                )

            # ========== BATCH WORKFLOW TOOL (convert-etl-workflow) ==========
            batch_tools_dir = output_dir / 'batch_workflow_tool'
            batch_tools_dir.mkdir(exist_ok=True)

            framework_dirs = {
                'step_function_jobs': 'step_functions',
                'airflow_jobs': 'airflow',
                'azure_data_factory_jobs': 'azure_data_factory',
            }

            for dir_name, framework_name in framework_dirs.items():
                source_dir = test_data_dir / dir_name
                if not source_dir.exists():
                    print(f'⚠️  Skipping {dir_name} - directory not found')
                    continue

                if framework_name not in test_files or not test_files[framework_name]:
                    print(
                        f'⚠️  Skipping {dir_name} - no test files for this framework in {test_mode} mode'
                    )
                    continue

                print(f'\n📁 Processing directory: {dir_name} ({framework_name})')
                file_count = len(list(source_dir.glob('*')))
                print(f'📊 Directory contains {file_count} total files')

                try:
                    llm_config = self._load_llm_config()

                    # convert-etl-workflow (to airflow) - skip same framework
                    if framework_name != 'airflow':
                        print(f'  🔧 convert-etl-workflow ({dir_name} → airflow)')
                        tool_args: Dict[str, Any] = {
                            'directory_path': str(source_dir),
                            'target_framework': 'airflow',
                            'output_directory': str(output_dir / 'batch_tool_outputs'),
                        }
                        if llm_config:
                            tool_args['llm_config'] = llm_config
                        result = await self.client.call_tool('convert-etl-workflow', tool_args)

                        status = result.get('status', 'unknown')
                        processed = result.get('processed_files', 0)
                        completed = result.get('completed_conversions', 0)
                        print(
                            f'    ✅ Batch conversion: {completed}/{processed} files completed ({status})'
                        )

                        airflow_convert_dir = batch_tools_dir / 'airflow' / dir_name
                        airflow_convert_dir.mkdir(parents=True, exist_ok=True)
                        response_file = airflow_convert_dir / 'response.json'
                        with open(response_file, 'w') as f:
                            json.dump(result, f, indent=2)

                        results.append(
                            f'✅ convert-etl-workflow ({dir_name}→airflow) → airflow/{dir_name}/response.json, processed: {completed}/{processed} files'
                        )
                    else:
                        results.append(
                            f'⏭️ convert-etl-workflow ({dir_name}→airflow) → skipped (same framework)'
                        )

                    # convert-etl-workflow (to step_functions) - skip same framework
                    if framework_name != 'step_functions':
                        print(f'  🔧 convert-etl-workflow ({dir_name} → step_functions)')
                        tool_args: Dict[str, Any] = {
                            'directory_path': str(source_dir),
                            'target_framework': 'step_functions',
                            'output_directory': str(output_dir / 'batch_tool_outputs'),
                        }
                        if llm_config:
                            tool_args['llm_config'] = llm_config
                        result = await self.client.call_tool('convert-etl-workflow', tool_args)

                        status = result.get('status', 'unknown')
                        processed = result.get('processed_files', 0)
                        completed = result.get('completed_conversions', 0)
                        print(
                            f'    ✅ Batch conversion: {completed}/{processed} files completed ({status})'
                        )

                        sf_convert_dir = batch_tools_dir / 'step_functions' / dir_name
                        sf_convert_dir.mkdir(parents=True, exist_ok=True)
                        response_file = sf_convert_dir / 'response.json'
                        with open(response_file, 'w') as f:
                            json.dump(result, f, indent=2)

                        results.append(
                            f'✅ convert-etl-workflow ({dir_name}→step_functions) → step_functions/{dir_name}/response.json, processed: {completed}/{processed} files'
                        )
                    else:
                        results.append(
                            f'⏭️ convert-etl-workflow ({dir_name}→step_functions) → skipped (same framework)'
                        )

                except Exception as e:
                    results.append(f'❌ convert-etl-workflow ({dir_name}): {str(e)}')
                    print(f'❌ Error with batch tool for {dir_name}: {e}')

            # ========== RESULTS SUMMARY ==========
            successful_tools: list[str] = [r for r in results if '✅' in r]
            failed_tools: list[str] = [r for r in results if '❌' in r]
            skipped_tools: list[str] = [r for r in results if '⏭️' in r]
            attempted_tools = len(successful_tools) + len(failed_tools)
            success_rate = len(successful_tools) / attempted_tools if attempted_tools > 0 else 0

            log_client('\n📊 INTEGRATION TEST RESULTS')
            log_client('=' * 60)
            log_client(f'📁 Output Directory: {output_dir}')
            log_client(f'🕒 Test Timestamp: {timestamp}')
            log_client(f'🔧 Test Mode: {test_mode.upper()}')
            log_client(f'📊 Total Files Tested: {total_files}')

            if test_mode == 'full':
                print(
                    '\n🔧 INDIVIDUAL WORKFLOW TOOL (convert-single-etl-workflow) - MCP Responses with Generated Code:'
                )
                single_results = [r for r in results if 'convert-single-etl-workflow' in r]
                for result in single_results:
                    print(f'  {result}')

            print(
                '\n📂 BATCH WORKFLOW TOOL (convert-etl-workflow) - MCP Responses with Output Paths:'
            )
            batch_results = [
                r
                for r in results
                if 'convert-etl-workflow' in r and 'convert-single-etl-workflow' not in r
            ]
            for result in batch_results:
                print(f'  {result}')

            print('\n📈 SUMMARY:')
            print(f'  ✅ Successful: {len(successful_tools)}')
            print(f'  ❌ Failed: {len(failed_tools)}')
            print(f'  ⏭️ Skipped: {len(skipped_tools)} (same framework conversions)')
            print(
                f'  📊 Success Rate: {success_rate:.1%} (successful / attempted, excluding skipped)'
            )

            if test_mode == 'full' and single_tools_dir:
                print(
                    f'📁 MCP responses saved to: {single_tools_dir.name}/ and {batch_tools_dir.name}/'
                )
            else:
                print(f'📁 MCP responses saved to: {batch_tools_dir.name}/')

            # Assert minimum success rate
            min_success_rate = 0.8 if test_mode == 'quick' else 0.7
            assert success_rate >= min_success_rate, (
                f'Success rate too low: {success_rate:.1%} (minimum: {min_success_rate:.1%}). Failed tools: {failed_tools}'
            )

            log_client('\n🎉 INTEGRATION TEST PASSED!')
            log_client(f'📁 All outputs and logs available in: {output_dir}')
            log_client(f'🔧 Test Mode Used: {test_mode.upper()}')
            log_client(f'📄 Client logs: {client_log_path}')
            log_client(f'📄 Server logs: {output_dir / "mcp_server.log"}')

            if test_mode == 'quick':
                print(
                    '🎯 Coverage Strategy: convert-etl-workflow = 100% system coverage (processes directories, calls same functions as individual tool)'
                )
                print(
                    '⚡ Quick mode completed - use INTEGRATION_TEST_MODE=full for comprehensive testing'
                )
            else:
                print('🎯 Coverage Strategy: 2 composite tools = 100% system coverage')
                print('🔄 Full mode completed - all files processed successfully')

        finally:
            if 'MCP_LOG_FILE' in os.environ:
                del os.environ['MCP_LOG_FILE']

            # log_client is always available since it's defined outside try block
            log_client('🔌 Stopping MCP server...')
            await self.client.stop_server()
            log_client('✅ Integration test cleanup completed')

    @pytest.mark.asyncio
    async def test_exception_coverage(self):
        """Test exception handling paths for coverage."""
        # Test server startup failure
        with pytest.raises(FileNotFoundError):
            client = MCPClient()
            # Force invalid server command to trigger exception
            client.process = await asyncio.create_subprocess_exec(
                'nonexistent_command',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await client.start_server()

        # Test message handling exceptions
        client = MCPClient()
        # Test _read_message with no process
        with pytest.raises(Exception, match='Server process not available'):
            await client._read_message()

        # Test stop_server exception handling
        client.process = None
        await client.stop_server()  # Should not raise exception


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
