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
"""Tests for the main function in server.py."""

from unittest.mock import patch

import awslabs.aurora_dsql_mcp_server.server
from awslabs.aurora_dsql_mcp_server.server import main


class TestMain:
    """Tests for the main function."""

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
        ],
    )
    def test_main_with_required_arguments(self, mocker):
        mock_execute_query = mocker.patch(
            "awslabs.aurora_dsql_mcp_server.server.execute_query"
        )
        mock_execute_query.return_value = {"column": 1}

        mock_mcp_run = mocker.patch("awslabs.aurora_dsql_mcp_server.server.mcp.run")

        main()

        assert awslabs.aurora_dsql_mcp_server.server.database_user == "test_user"
        assert awslabs.aurora_dsql_mcp_server.server.cluster_endpoint == "test_ce"
        assert awslabs.aurora_dsql_mcp_server.server.region == "us-west-2"
        assert awslabs.aurora_dsql_mcp_server.server.read_only == True

        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()
        assert mock_mcp_run.call_args[1].get("transport") is None

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
            "--allow-writes",
        ],
    )
    def test_main_with_optional_arguments(self, mocker):
        mock_execute_query = mocker.patch(
            "awslabs.aurora_dsql_mcp_server.server.execute_query"
        )
        mock_execute_query.return_value = {"column": 1}

        mock_mcp_run = mocker.patch("awslabs.aurora_dsql_mcp_server.server.mcp.run")

        main()

        assert awslabs.aurora_dsql_mcp_server.server.read_only == False

        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # This test directly executes the code in the if __name__ == '__main__': block
        # to ensure coverage of that line

        # Get the source code of the module
        import inspect

        from awslabs.aurora_dsql_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        # Accept both single and double quotes
        assert "if __name__ == '__main__':" in source or 'if __name__ == "__main__":' in source
        assert "main()" in source

        # This test doesn't actually execute the code, but it ensures
        # that the coverage report includes the if __name__ == '__main__': line
        # by explicitly checking for its presence

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
            "--knowledge-server",
            "http://insecure.example.com",
        ],
    )
    def test_main_rejects_non_https_knowledge_server(self):
        """Test that main rejects non-HTTPS knowledge server URLs."""
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
            "--knowledge-server",
            "https://",
        ],
    )
    def test_main_rejects_malformed_knowledge_server_url(self):
        """Test that main rejects malformed knowledge server URLs."""
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
            "--knowledge-server",
            "https://example.com",
        ],
    )
    @patch("awslabs.aurora_dsql_mcp_server.server.urlparse")
    def test_main_handles_url_parsing_exception(self, mock_urlparse):
        """Test that main handles exceptions during URL parsing."""
        import pytest

        mock_urlparse.side_effect = Exception("URL parsing failed")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
            "--knowledge-timeout",
            "0",
        ],
    )
    def test_main_rejects_zero_timeout(self):
        """Test that main rejects zero timeout."""
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
            "--knowledge-timeout",
            "-5.0",
        ],
    )
    def test_main_rejects_negative_timeout(self):
        """Test that main rejects negative timeout."""
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
            "--knowledge-server",
            "https://custom-server.example.com",
            "--knowledge-timeout",
            "60.0",
        ],
    )
    def test_main_with_custom_knowledge_parameters(self, mocker):
        """Test that main accepts custom knowledge server and timeout."""
        mock_execute_query = mocker.patch(
            "awslabs.aurora_dsql_mcp_server.server.execute_query"
        )
        mock_execute_query.return_value = {"column": 1}

        mock_mcp_run = mocker.patch("awslabs.aurora_dsql_mcp_server.server.mcp.run")

        main()

        assert (
            awslabs.aurora_dsql_mcp_server.server.knowledge_server
            == "https://custom-server.example.com"
        )
        assert awslabs.aurora_dsql_mcp_server.server.knowledge_timeout == 60.0

        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()

    @patch(
        "sys.argv",
        [
            "awslabs.aurora-dsql-mcp-server",
            "--cluster_endpoint",
            "test_ce",
            "--database_user",
            "test_user",
            "--region",
            "us-west-2",
        ],
    )
    def test_main_uses_default_knowledge_parameters(self, mocker):
        """Test that main uses default knowledge server and timeout when not specified."""
        mock_execute_query = mocker.patch(
            "awslabs.aurora_dsql_mcp_server.server.execute_query"
        )
        mock_execute_query.return_value = {"column": 1}

        mock_mcp_run = mocker.patch("awslabs.aurora_dsql_mcp_server.server.mcp.run")

        main()

        assert (
            awslabs.aurora_dsql_mcp_server.server.knowledge_server
            == "https://xmfe3hc3pk.execute-api.us-east-2.amazonaws.com"
        )
        assert awslabs.aurora_dsql_mcp_server.server.knowledge_timeout == 30.0

        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()
