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
"""Configuration module for Keyspaces MCP Server."""

import os
from .consts import CASSANDRA_DEFAULT_PORT, ENV_DIRECTORY, ENV_FILENAME
from dataclasses import dataclass
from dotenv import load_dotenv


# Load environment variables from ENV_FILENAME in the user's home directory,
#  if it exists.
home_dir = os.path.expanduser('~')
load_dotenv(os.path.join(home_dir, ENV_DIRECTORY, ENV_FILENAME))


@dataclass
class DatabaseConfig:
    """Database configuration for Cassandra/Keyspaces connection."""

    use_keyspaces: bool

    # Cassandra configuration
    cassandra_contact_points: str
    cassandra_port: int
    cassandra_local_datacenter: str
    cassandra_username: str
    cassandra_password: str

    # Keyspaces configuration
    keyspaces_endpoint: str
    keyspaces_region: str

    @classmethod
    def from_env(cls):
        """Create a DatabaseConfig instance from environment variables."""
        return cls(
            use_keyspaces=os.getenv('DB_USE_KEYSPACES', 'false').lower() == 'true',
            cassandra_contact_points=os.getenv('DB_CASSANDRA_CONTACT_POINTS', '127.0.0.1'),
            cassandra_port=int(os.getenv('DB_CASSANDRA_PORT', CASSANDRA_DEFAULT_PORT)),
            cassandra_local_datacenter=os.getenv('DB_CASSANDRA_LOCAL_DATACENTER', 'datacenter1'),
            cassandra_username=os.getenv('DB_CASSANDRA_USERNAME', ''),
            cassandra_password=os.getenv('DB_CASSANDRA_PASSWORD', ''),
            keyspaces_endpoint=os.getenv(
                'DB_KEYSPACES_ENDPOINT', 'cassandra.us-east-1.amazonaws.com'
            ),
            keyspaces_region=os.getenv('DB_KEYSPACES_REGION', 'us-east-1'),
        )


@dataclass
class AppConfig:
    """Application configuration for Keyspaces MCP Server."""

    database_config: DatabaseConfig

    @classmethod
    def from_env(cls):
        """Create an AppConfig instance from environment variables."""
        return cls(database_config=DatabaseConfig.from_env())
