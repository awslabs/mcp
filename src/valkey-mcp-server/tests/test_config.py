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

"""Unit tests for config module."""

from unittest.mock import patch


class TestValkeyConfig:
    def test_defaults(self):
        with patch.dict('os.environ', {}, clear=True):
            import awslabs.valkey_mcp_server.common.config as cfg_mod
            from importlib import reload

            reload(cfg_mod)
            assert cfg_mod.VALKEY_CFG['host'] == '127.0.0.1'
            assert cfg_mod.VALKEY_CFG['port'] == 6379
            assert cfg_mod.VALKEY_CFG['ssl'] is False
            assert cfg_mod.VALKEY_CFG['cluster_mode'] is False
            assert cfg_mod.VALKEY_CFG['password'] == ''
            assert cfg_mod.VALKEY_CFG['username'] is None

    def test_env_overrides(self):
        env = {
            'VALKEY_HOST': '10.0.0.1',
            'VALKEY_PORT': '6380',
            'VALKEY_PWD': 'secret',  # pragma: allowlist secret
            'VALKEY_USERNAME': 'admin',
            'VALKEY_USE_SSL': 'true',
            'VALKEY_CLUSTER_MODE': '1',
        }
        with patch.dict('os.environ', env, clear=True):
            import awslabs.valkey_mcp_server.common.config as cfg_mod
            from importlib import reload

            reload(cfg_mod)
            assert cfg_mod.VALKEY_CFG['host'] == '10.0.0.1'
            assert cfg_mod.VALKEY_CFG['port'] == 6380
            assert cfg_mod.VALKEY_CFG['password'] == 'secret'  # pragma: allowlist secret
            assert cfg_mod.VALKEY_CFG['username'] == 'admin'
            assert cfg_mod.VALKEY_CFG['ssl'] is True
            assert cfg_mod.VALKEY_CFG['cluster_mode'] is True


class TestEmbeddingConfig:
    def test_defaults(self):
        with patch.dict('os.environ', {}, clear=True):
            import awslabs.valkey_mcp_server.common.config as cfg_mod
            from importlib import reload

            reload(cfg_mod)
            assert cfg_mod.EMBEDDING_CFG['provider'] == 'bedrock'
            assert cfg_mod.EMBEDDING_CFG['ollama_host'] == 'http://localhost:11434'
            assert cfg_mod.EMBEDDING_CFG['bedrock_normalize'] is None
            assert cfg_mod.EMBEDDING_CFG['bedrock_dimensions'] is None

    def test_bedrock_normalize_true(self):
        with patch.dict('os.environ', {'BEDROCK_NORMALIZE': 'true'}, clear=True):
            import awslabs.valkey_mcp_server.common.config as cfg_mod
            from importlib import reload

            reload(cfg_mod)
            assert cfg_mod.EMBEDDING_CFG['bedrock_normalize'] is True

    def test_bedrock_dimensions(self):
        with patch.dict('os.environ', {'BEDROCK_DIMENSIONS': '512'}, clear=True):
            import awslabs.valkey_mcp_server.common.config as cfg_mod
            from importlib import reload

            reload(cfg_mod)
            assert cfg_mod.EMBEDDING_CFG['bedrock_dimensions'] == 512

    def test_ollama_provider(self):
        env = {'EMBEDDING_PROVIDER': 'ollama', 'OLLAMA_EMBEDDING_MODEL': 'mxbai-embed-large'}
        with patch.dict('os.environ', env, clear=True):
            import awslabs.valkey_mcp_server.common.config as cfg_mod
            from importlib import reload

            reload(cfg_mod)
            assert cfg_mod.EMBEDDING_CFG['provider'] == 'ollama'
            assert cfg_mod.EMBEDDING_CFG['ollama_embedding_model'] == 'mxbai-embed-large'
