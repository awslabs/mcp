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

"""Isolated subprocess for executing user-supplied diagram code.

This module is invoked as a subprocess by generate_diagram() to execute
user code in a separate process, providing process-level isolation as
defense-in-depth for the code execution sandbox.

Usage (via subprocess, not directly):
    echo '{"code": "...", "output_path": "..."}' | python -m awslabs.aws_diagram_mcp_server._sandbox_runner

Input (JSON on stdin):
    code: str        - User-supplied Python code
    output_path: str - Path prefix for the generated diagram PNG

Output (JSON on stdout):
    status: str   - "success" or "error"
    path: str     - Path to generated PNG (on success)
    message: str  - Description of result or error
"""

import json
import os
import re
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import urlretrieve as _real_urlretrieve


# Allowed image extensions for icon downloads via urlretrieve.
_ALLOWED_ICON_EXTENSIONS = frozenset(
    {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.bmp', '.webp'}
)


def _safe_urlretrieve(url: str, filename: str = '') -> tuple:
    """Download an icon file with URL scheme and extension validation."""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f'Only http/https URLs are allowed, got: {parsed.scheme!r}')

    if not filename:
        filename = os.path.basename(parsed.path) or 'icon.png'

    safe_name = os.path.basename(filename)
    if not safe_name:
        raise ValueError('Filename cannot be empty')

    _, ext = os.path.splitext(safe_name)
    if ext.lower() not in _ALLOWED_ICON_EXTENSIONS:
        raise ValueError(
            f'Only image files are allowed '
            f'({", ".join(sorted(_ALLOWED_ICON_EXTENSIONS))}), got: {ext!r}'
        )

    download_dir = tempfile.mkdtemp(prefix='diagram-icons-')
    download_path = os.path.join(download_dir, safe_name)

    _, headers = _real_urlretrieve(url, download_path)  # nosec B310 - scheme validated above
    return download_path, headers


# Restricted builtins — excludes __import__, exec, eval, compile, open,
# getattr, setattr, delattr, globals, locals, vars, breakpoint.
_SAFE_BUILTINS = {
    'True': True,
    'False': False,
    'None': None,
    'bool': bool,
    'int': int,
    'float': float,
    'str': str,
    'list': list,
    'tuple': tuple,
    'dict': dict,
    'set': set,
    'frozenset': frozenset,
    'bytes': bytes,
    'bytearray': bytearray,
    'complex': complex,
    'slice': slice,
    'object': object,
    'type': type,
    'super': super,
    'property': property,
    'classmethod': classmethod,
    'staticmethod': staticmethod,
    'abs': abs,
    'all': all,
    'any': any,
    'ascii': ascii,
    'bin': bin,
    'callable': callable,
    'chr': chr,
    'divmod': divmod,
    'enumerate': enumerate,
    'filter': filter,
    'format': format,
    'hash': hash,
    'hex': hex,
    'id': id,
    'isinstance': isinstance,
    'issubclass': issubclass,
    'iter': iter,
    'len': len,
    'map': map,
    'max': max,
    'min': min,
    'next': next,
    'oct': oct,
    'ord': ord,
    'pow': pow,
    'print': print,
    'range': range,
    'repr': repr,
    'reversed': reversed,
    'round': round,
    'sorted': sorted,
    'sum': sum,
    'zip': zip,
    'ArithmeticError': ArithmeticError,
    'AssertionError': AssertionError,
    'AttributeError': AttributeError,
    'EOFError': EOFError,
    'Exception': Exception,
    'IndexError': IndexError,
    'KeyError': KeyError,
    'LookupError': LookupError,
    'NameError': NameError,
    'NotImplementedError': NotImplementedError,
    'OSError': OSError,
    'OverflowError': OverflowError,
    'RuntimeError': RuntimeError,
    'StopIteration': StopIteration,
    'TypeError': TypeError,
    'ValueError': ValueError,
    'ZeroDivisionError': ZeroDivisionError,
}


def _build_namespace():
    """Build the execution namespace with diagram imports and safe builtins.

    The namespace is built in two phases:
    1. Import diagram modules with full builtins (they need __import__)
    2. Restrict __builtins__ to _SAFE_BUILTINS before user code runs
    """
    namespace = {}

    # Phase 1: Import diagram modules (needs full builtins)
    # Security: Do NOT import 'os' or bare 'diagrams' into the namespace.
    exec(  # nosec B102 nosem
        'from diagrams import Diagram, Cluster, Edge', namespace
    )
    exec(  # nosec B102 nosem
        """from diagrams.saas.crm import *
from diagrams.saas.identity import *
from diagrams.saas.chat import *
from diagrams.saas.recommendation import *
from diagrams.saas.cdn import *
from diagrams.saas.communication import *
from diagrams.saas.media import *
from diagrams.saas.logging import *
from diagrams.saas.security import *
from diagrams.saas.social import *
from diagrams.saas.alerting import *
from diagrams.saas.analytics import *
from diagrams.saas.automation import *
from diagrams.saas.filesharing import *
from diagrams.onprem.vcs import *
from diagrams.onprem.database import *
from diagrams.onprem.gitops import *
from diagrams.onprem.workflow import *
from diagrams.onprem.etl import *
from diagrams.onprem.inmemory import *
from diagrams.onprem.identity import *
from diagrams.onprem.network import *
from diagrams.onprem.proxmox import *
from diagrams.onprem.cd import *
from diagrams.onprem.container import *
from diagrams.onprem.certificates import *
from diagrams.onprem.mlops import *
from diagrams.onprem.dns import *
from diagrams.onprem.compute import *
from diagrams.onprem.logging import *
from diagrams.onprem.registry import *
from diagrams.onprem.security import *
from diagrams.onprem.client import *
from diagrams.onprem.groupware import *
from diagrams.onprem.iac import *
from diagrams.onprem.analytics import *
from diagrams.onprem.messaging import *
from diagrams.onprem.tracing import *
from diagrams.onprem.ci import *
from diagrams.onprem.search import *
from diagrams.onprem.storage import *
from diagrams.onprem.auth import *
from diagrams.onprem.monitoring import *
from diagrams.onprem.aggregator import *
from diagrams.onprem.queue import *
from diagrams.gis.database import *
from diagrams.gis.cli import *
from diagrams.gis.server import *
from diagrams.gis.python import *
from diagrams.gis.organization import *
from diagrams.gis.cplusplus import *
from diagrams.gis.mobile import *
from diagrams.gis.javascript import *
from diagrams.gis.desktop import *
from diagrams.gis.ogc import *
from diagrams.gis.java import *
from diagrams.gis.routing import *
from diagrams.gis.data import *
from diagrams.gis.geocoding import *
from diagrams.gis.format import *
from diagrams.elastic.saas import *
from diagrams.elastic.observability import *
from diagrams.elastic.elasticsearch import *
from diagrams.elastic.orchestration import *
from diagrams.elastic.security import *
from diagrams.elastic.beats import *
from diagrams.elastic.enterprisesearch import *
from diagrams.elastic.agent import *
from diagrams.programming.runtime import *
from diagrams.programming.framework import *
from diagrams.programming.flowchart import *
from diagrams.programming.language import *
from diagrams.gcp.storage import *
from diagrams.generic.database import *
from diagrams.generic.blank import *
from diagrams.generic.network import *
from diagrams.generic.virtualization import *
from diagrams.generic.place import *
from diagrams.generic.device import *
from diagrams.generic.compute import *
from diagrams.generic.os import *
from diagrams.generic.storage import *
from diagrams.k8s.others import *
from diagrams.k8s.rbac import *
from diagrams.k8s.network import *
from diagrams.k8s.ecosystem import *
from diagrams.k8s.compute import *
from diagrams.k8s.chaos import *
from diagrams.k8s.infra import *
from diagrams.k8s.podconfig import *
from diagrams.k8s.controlplane import *
from diagrams.k8s.clusterconfig import *
from diagrams.k8s.storage import *
from diagrams.k8s.group import *
from diagrams.aws.cost import *
from diagrams.aws.ar import *
from diagrams.aws.general import *
from diagrams.aws.database import *
from diagrams.aws.management import *
from diagrams.aws.ml import *
from diagrams.aws.game import *
from diagrams.aws.enablement import *
from diagrams.aws.network import *
from diagrams.aws.quantum import *
from diagrams.aws.iot import *
from diagrams.aws.robotics import *
from diagrams.aws.migration import *
from diagrams.aws.mobile import *
from diagrams.aws.compute import *
from diagrams.aws.media import *
from diagrams.aws.engagement import *
from diagrams.aws.security import *
from diagrams.aws.devtools import *
from diagrams.aws.integration import *
from diagrams.aws.business import *
from diagrams.aws.analytics import *
from diagrams.aws.blockchain import *
from diagrams.aws.storage import *
from diagrams.aws.satellite import *
from diagrams.aws.enduser import *
""",
        namespace,
    )

    # Inject safe urlretrieve
    namespace['urlretrieve'] = _safe_urlretrieve

    # Phase 2: Restrict __builtins__ BEFORE user code runs.
    # This is the critical security boundary.
    namespace['__builtins__'] = _SAFE_BUILTINS

    return namespace


def _process_diagram_code(code: str, output_path: str) -> str:
    """Process code to inject show=False and output path into Diagram() calls."""
    if 'with Diagram(' in code:
        diagram_pattern = r'with\s+Diagram\s*\((.*?)\)'
        matches = re.findall(diagram_pattern, code)

        for match in matches:
            original_args = match.strip()
            has_show = 'show=' in original_args
            has_filename = 'filename=' in original_args

            new_args = original_args

            if has_filename:
                filename_pattern = r'filename\s*=\s*[\'"]([^\'"]*)[\'"]'
                new_args = re.sub(filename_pattern, f"filename='{output_path}'", new_args)
            else:
                if new_args and not new_args.endswith(','):
                    new_args += ', '
                new_args += f"filename='{output_path}'"

            if not has_show:
                if new_args and not new_args.endswith(','):
                    new_args += ', '
                new_args += 'show=False'

            code = code.replace(f'with Diagram({original_args})', f'with Diagram({new_args})')

    return code


def main():
    """Entry point for subprocess execution.

    Reads JSON config from stdin, executes user code in a restricted namespace,
    and writes JSON result to stdout.
    """
    try:
        config = json.loads(sys.stdin.read())
        code = config['code']
        output_path = config['output_path']
    except (json.JSONDecodeError, KeyError) as e:
        json.dump({'status': 'error', 'path': None, 'message': f'Invalid input: {e}'}, sys.stdout)
        sys.exit(1)

    try:
        namespace = _build_namespace()
        code = _process_diagram_code(code, output_path)

        # Execute user code in the restricted namespace. Process isolation
        # ensures this runs independently of the MCP server process.
        exec(code, namespace)  # nosec B102 nosem

        png_path = f'{output_path}.png'
        if os.path.exists(png_path):
            json.dump(
                {
                    'status': 'success',
                    'path': png_path,
                    'message': f'Diagram generated successfully at {png_path}',
                },
                sys.stdout,
            )
        else:
            json.dump(
                {
                    'status': 'error',
                    'path': None,
                    'message': 'Diagram file was not created. Check your code for errors.',
                },
                sys.stdout,
            )
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        json.dump(
            {
                'status': 'error',
                'path': None,
                'message': f'Error generating diagram: {error_type}: {error_message}',
            },
            sys.stdout,
        )


if __name__ == '__main__':
    main()
