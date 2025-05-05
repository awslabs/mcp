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

import sys
import valkey
from awslabs.valkey_mcp_server.common.config import VALKEY_CFG
from awslabs.valkey_mcp_server.version import __version__
from typing import Optional, Type, Union
from valkey import Valkey
from valkey.cluster import ValkeyCluster


class ValkeyConnectionManager:
    """Manages connection to Valkey."""

    _instance: Optional[Valkey] = None

    @classmethod
    def get_connection(cls, decode_responses: bool = True) -> Valkey:
        """Create connection to Valkey if none present or returns existing connection.

        Args:
            decode_responses: Whether to decode response bytes to strings. Defaults to True.

        Returns:
            Valkey: A Valkey connection instance.
        """
        if cls._instance is None:
            try:
                valkey_class: Type[Union[Valkey, ValkeyCluster]] = (
                    valkey.cluster.ValkeyCluster if VALKEY_CFG['cluster_mode'] else valkey.Valkey
                )

                # Get SSL settings with defaults
                ssl_enabled = VALKEY_CFG.get('ssl', False)
                ssl_cert_reqs = VALKEY_CFG.get('ssl_cert_reqs')
                if ssl_enabled and ssl_cert_reqs is None:
                    ssl_cert_reqs = 'required'

                # Build connection kwargs
                connection_kwargs = {
                    'host': VALKEY_CFG['host'],
                    'port': VALKEY_CFG['port'],
                    'username': VALKEY_CFG.get('username'),
                    'password': VALKEY_CFG.get('password', ''),
                    'ssl': ssl_enabled,
                    'ssl_ca_path': VALKEY_CFG.get('ssl_ca_path'),
                    'ssl_keyfile': VALKEY_CFG.get('ssl_keyfile'),
                    'ssl_certfile': VALKEY_CFG.get('ssl_certfile'),
                    'ssl_cert_reqs': ssl_cert_reqs,
                    'ssl_ca_certs': VALKEY_CFG.get('ssl_ca_certs'),
                    'decode_responses': decode_responses,
                    'lib_name': f'valkey-py(mcp-server_v{__version__})',
                }

                # Add max_connections parameter based on mode
                if VALKEY_CFG['cluster_mode']:
                    connection_kwargs['max_connections_per_node'] = 10
                else:
                    connection_kwargs['max_connections'] = 10

                # Create new instance
                cls._instance = valkey_class(**connection_kwargs)

            except valkey.exceptions.ConnectionError:
                print('Failed to connect to Valkey server', file=sys.stderr)
                raise
            except valkey.exceptions.AuthenticationError:
                print('Authentication failed', file=sys.stderr)
                raise
            except valkey.exceptions.TimeoutError:
                print('Connection timed out', file=sys.stderr)
                raise
            except valkey.exceptions.ResponseError as e:
                print(f'Response error: {e}', file=sys.stderr)
                raise
            except valkey.exceptions.ValkeyError as e:
                print(f'Valkey error: {e}', file=sys.stderr)
                raise
            except valkey.exceptions.ClusterError as e:
                print(f'Valkey Cluster error: {e}', file=sys.stderr)
                raise
            except Exception as e:
                print(f'Unexpected error: {e}', file=sys.stderr)
                raise

        return cls._instance
