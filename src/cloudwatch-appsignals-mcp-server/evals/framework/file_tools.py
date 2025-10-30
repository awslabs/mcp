"""File operation tools for agent evaluations.

Provides list_files, read_file, and write_file tools in Bedrock format.
"""

from typing import Any, Dict, List


def get_file_tools() -> List[Dict[str, Any]]:
    """Define file operation tools in Bedrock format.

    Returns:
        List of tool specifications for file operations
    """
    return [
        {
            'toolSpec': {
                'name': 'list_files',
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
                'name': 'read_file',
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
                'name': 'write_file',
                'description': 'Write content to a file (overwrites existing content)',
                'inputSchema': {
                    'json': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'Path to file (relative to project root)',
                            },
                            'content': {'type': 'string', 'description': 'Content to write'},
                        },
                        'required': ['path', 'content'],
                    }
                },
            }
        },
    ]
