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

"""Plugin registry for database analyzers."""

from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.postgresql import PostgreSQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.sqlserver import SQLServerPlugin
from typing import Dict, Type


class PluginRegistry:
    """Registry for database-specific analyzer plugins."""

    _plugins: Dict[str, Type[DatabasePlugin]] = {
        'mysql': MySQLPlugin,
        'postgresql': PostgreSQLPlugin,
        'sqlserver': SQLServerPlugin,
    }

    @classmethod
    def get_plugin(cls, db_type: str) -> DatabasePlugin:
        """Get plugin instance for the specified database type.

        Args:
            db_type: Database type ('mysql', 'postgresql', 'sqlserver')

        Returns:
            Plugin instance for the database type

        Raises:
            ValueError: If database type is not supported
        """
        plugin_class = cls._plugins.get(db_type.lower())
        if not plugin_class:
            supported = ', '.join(cls._plugins.keys())
            raise ValueError(f'Unsupported database type: {db_type}. Supported types: {supported}')
        return plugin_class()

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported database types."""
        return list(cls._plugins.keys())

    @classmethod
    def register_plugin(cls, db_type: str, plugin_class: Type[DatabasePlugin]) -> None:
        """Register a new database plugin.

        Args:
            db_type: Database type identifier
            plugin_class: Plugin class to register

        Raises:
            TypeError: If plugin_class does not inherit from DatabasePlugin
        """
        # Validate that the plugin class inherits from DatabasePlugin
        if not issubclass(plugin_class, DatabasePlugin):
            raise TypeError(
                f'Plugin class {plugin_class.__name__} must inherit from DatabasePlugin'
            )
        cls._plugins[db_type.lower()] = plugin_class
