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

import os
import urllib.parse
from dotenv import load_dotenv


load_dotenv()

MCP_TRANSPORT = os.getenv('MCP_TRANSPORT', 'stdio')

VALKEY_CFG = {
    'host': os.getenv('VALKEY_HOST', '127.0.0.1'),
    'port': int(os.getenv('VALKEY_PORT', 6379)),
    'username': os.getenv('VALKEY_USERNAME', None),
    'password': os.getenv('VALKEY_PWD', ''),
    'ssl': os.getenv('VALKEY_USE_SSL', False) in ('true', '1', 't'),
    'ssl_ca_path': os.getenv('VALKEY_SSL_CA_PATH', None),
    'ssl_keyfile': os.getenv('VALKEY_SSL_KEYFILE', None),
    'ssl_certfile': os.getenv('VALKEY_SSL_CERTFILE', None),
    'ssl_cert_reqs': os.getenv('VALKEY_SSL_CERT_REQS', 'required'),
    'ssl_ca_certs': os.getenv('VALKEY_SSL_CA_CERTS', None),
    'cluster_mode': os.getenv('VALKEY_CLUSTER_MODE', False) in ('true', '1', 't'),
}


def generate_valkey_uri():
    """Generates Valkey URL."""
    cfg = VALKEY_CFG
    scheme = 'valkeys' if cfg.get('ssl') else 'valkey'
    host = cfg.get('host', '127.0.0.1')
    port = cfg.get('port', 6379)

    username = cfg.get('username')
    password = cfg.get('password')

    # Auth part - use quote() for auth components to preserve spaces as %20
    def safe_quote(value):
        """Safely quote a value that might be None."""
        if value is None:
            return ''
        return urllib.parse.quote(str(value))

    if username:
        auth_part = f'{safe_quote(username)}:{safe_quote(password)}@'
    elif password:
        auth_part = f':{safe_quote(password)}@'
    else:
        auth_part = ''

    # Base URI
    base_uri = f'{scheme}://{auth_part}{host}:{port}'

    # Additional SSL query parameters if SSL is enabled
    query_params = {}
    if cfg.get('ssl'):
        if cfg.get('ssl_cert_reqs'):
            query_params['ssl_cert_reqs'] = cfg['ssl_cert_reqs']
        if cfg.get('ssl_ca_certs'):
            query_params['ssl_ca_certs'] = cfg['ssl_ca_certs']
        if cfg.get('ssl_keyfile'):
            query_params['ssl_keyfile'] = cfg['ssl_keyfile']
        if cfg.get('ssl_certfile'):
            query_params['ssl_certfile'] = cfg['ssl_certfile']
        if cfg.get('ssl_ca_path'):
            query_params['ssl_ca_path'] = cfg['ssl_ca_path']

    if query_params:
        # Build query string with proper URL encoding
        query_parts = []
        for key, value in sorted(query_params.items()):
            encoded_value = urllib.parse.quote(str(value), safe='')
            query_parts.append(f'{key}={encoded_value}')
        base_uri += '?' + '&'.join(query_parts)

    return base_uri
