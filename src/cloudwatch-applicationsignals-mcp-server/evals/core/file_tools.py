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

"""File operation tools for agent evaluations.

Provides list_files, read_file, and write_file tools in Bedrock format.
"""

from .captor import MESSAGE_CONTENT
from typing import Any, Dict, List


FILE_TOOL_LIST_FILES = 'list_files'
FILE_TOOL_READ_FILE = 'read_file'
FILE_TOOL_WRITE_FILE = 'write_file'


def get_file_tools() -> List[Dict[str, Any]]:
    """Define file operation tools in Bedrock format.

    Returns:
        List of tool specifications for file operations
    """
    return [
        {
            'toolSpec': {
                'name': FILE_TOOL_LIST_FILES,
                'description': 'List files in a directory',
                'inputSchema': {
                    'json': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'Path to directory (relative to project root)',
                            }
                        },
                        'required': ['path'],
                    }
                },
            }
        },
        {
            'toolSpec': {
                'name': FILE_TOOL_READ_FILE,
                'description': 'Read contents of a file',
                'inputSchema': {
                    'json': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'Path to file (relative to project root)',
                            }
                        },
                        'required': ['path'],
                    }
                },
            }
        },
        {
            'toolSpec': {
                'name': FILE_TOOL_WRITE_FILE,
                'description': 'Write content to a file (overwrites existing content)',
                'inputSchema': {
                    'json': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'Path to file (relative to project root)',
                            },
                            MESSAGE_CONTENT: {'type': 'string', 'description': 'Content to write'},
                        },
                        'required': ['path', MESSAGE_CONTENT],
                    }
                },
            }
        },
    ]
