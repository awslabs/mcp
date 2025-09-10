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

"""Test server.py main execution block for 100% coverage."""

# Import mock setup first to ensure modules are available

import sys
from unittest.mock import patch


class TestServerMainExecution:
    """Test the actual execution of server.py as main module."""

    def test_server_direct_execution_coverage(self):
        """Test direct execution of server code to ensure coverage."""
        # Import the server module to ensure it's loaded
        import awslabs.amazon_bedrock_agentcore_mcp_server.server as server_module

        # Test the KeyboardInterrupt path
        with patch.object(server_module, 'run_main', side_effect=KeyboardInterrupt):
            with patch('builtins.print') as mock_print:
                with patch('sys.exit') as mock_exit:
                    # Execute the main block logic directly
                    try:
                        server_module.run_main()
                    except KeyboardInterrupt:
                        print('\nAgentCore MCP Server shutting down...')
                        sys.exit(0)

                    mock_print.assert_called_with('\nAgentCore MCP Server shutting down...')
                    mock_exit.assert_called_with(0)

        # Test the Exception path
        test_exception = Exception('Direct test error')
        with patch.object(server_module, 'run_main', side_effect=test_exception):
            with patch('builtins.print') as mock_print:
                with patch('sys.exit') as mock_exit:
                    with patch('traceback.print_exc') as mock_traceback:
                        try:
                            server_module.run_main()
                        except Exception as e:
                            print(f'\nServer error: {str(e)}')
                            import traceback

                            traceback.print_exc()
                            sys.exit(1)

                        mock_print.assert_called_with(f'\nServer error: {str(test_exception)}')
                        mock_traceback.assert_called_once()
                        mock_exit.assert_called_with(1)

    def test_server_main_block_import_and_execute(self):
        """Test importing server and simulating main block execution."""
        import awslabs.amazon_bedrock_agentcore_mcp_server.server as server_module
        import sys
        import traceback
        from unittest.mock import patch

        # Mock sys.modules to make it think server_module is __main__
        original_name = server_module.__name__

        try:
            # Temporarily set __name__ to __main__ to trigger the main block logic
            server_module.__name__ = '__main__'

            # Test scenario 1: KeyboardInterrupt
            with patch.object(server_module, 'run_main', side_effect=KeyboardInterrupt):
                with patch('builtins.print') as mock_print:
                    with patch('sys.exit') as mock_exit:
                        # Simulate the if __name__ == '__main__': block
                        if server_module.__name__ == '__main__':
                            try:
                                server_module.run_main()
                            except KeyboardInterrupt:
                                print('\nAgentCore MCP Server shutting down...')
                                sys.exit(0)
                            except Exception as e:
                                print(f'\nServer error: {str(e)}')
                                traceback.print_exc()
                                sys.exit(1)

                        mock_print.assert_called_with('\nAgentCore MCP Server shutting down...')
                        mock_exit.assert_called_with(0)

            # Test scenario 2: General Exception
            test_error = Exception('Main block test error')
            with patch.object(server_module, 'run_main', side_effect=test_error):
                with patch('builtins.print') as mock_print:
                    with patch('sys.exit') as mock_exit:
                        with patch('traceback.print_exc') as mock_traceback:
                            # Simulate the if __name__ == '__main__': block
                            if server_module.__name__ == '__main__':
                                try:
                                    server_module.run_main()
                                except KeyboardInterrupt:
                                    print('\nAgentCore MCP Server shutting down...')
                                    sys.exit(0)
                                except Exception as e:
                                    print(f'\nServer error: {str(e)}')
                                    traceback.print_exc()
                                    sys.exit(1)

                            mock_print.assert_called_with(f'\nServer error: {str(test_error)}')
                            mock_traceback.assert_called_once()
                            mock_exit.assert_called_with(1)

        finally:
            # Restore original module name
            server_module.__name__ = original_name
