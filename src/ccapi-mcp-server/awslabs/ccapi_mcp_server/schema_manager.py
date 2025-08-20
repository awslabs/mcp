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

import json
import os
from awslabs.ccapi_mcp_server.aws_client import get_aws_client
from awslabs.ccapi_mcp_server.errors import ClientError
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict


# all schema metadata is stored in .schemas/schema_metadata.json. The schemas themselves are all stored in the directory.
SCHEMA_CACHE_DIR = '.schemas'
SCHEMA_METADATA_FILE = 'schema_metadata.json'
SCHEMA_UPDATE_INTERVAL = timedelta(days=7)  # Check for updates weekly


class SchemaManager:
    """Responsible for keeping track of schemas, cacheing them locally, and updating them if they are outdated."""

    def __init__(self):
        """Initialize the schema manager with the cache directory."""
        cache_dir = os.path.join(os.path.dirname(__file__), '.schemas')
        self.cache_dir = Path(cache_dir)
        self.metadata_file = self.cache_dir / SCHEMA_METADATA_FILE
        self.schema_registry: Dict[str, dict] = {}

        # Ensure cache directory exists
        self.cache_dir.mkdir(exist_ok=True)

        # Load metadata if it exists
        self.metadata = self._load_metadata()

        # Load cached schemas into registry
        self._load_cached_schemas()

    def _load_metadata(self) -> dict:
        """Load schema metadata from file or create if it doesn't exist."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print('Corrupted metadata file. Creating new one.')

        # Default metadata
        metadata = {'version': '1', 'schemas': {}}

        # Save default metadata
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def _load_cached_schemas(self):
        """Load all cached schemas into the registry."""
        for schema_file in self.cache_dir.glob('*.json'):
            if schema_file.name == SCHEMA_METADATA_FILE:
                continue

            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    if 'typeName' in schema:
                        resource_type = schema['typeName']
                        self.schema_registry[resource_type] = schema
                        print(f'Loaded schema for {resource_type} from cache')
            except (json.JSONDecodeError, IOError) as e:
                print(f'Error loading schema from {schema_file}: {str(e)}')

    async def get_schema(self, resource_type: str, region: str | None = None) -> dict:
        """Get schema for a resource type, downloading it if necessary."""
        # Check if schema is in registry
        if resource_type in self.schema_registry:
            cached_schema = self.schema_registry[resource_type]

            # If cached schema is corrupted (empty properties), force reload
            if not cached_schema.get('properties'):
                print(
                    f'Cached schema for {resource_type} is corrupted (empty properties), reloading...'
                )
                # Remove from registry to force reload
                del self.schema_registry[resource_type]
            else:
                # Check if schema needs to be updated based on last update time
                if resource_type in self.metadata['schemas']:
                    schema_metadata = self.metadata['schemas'][resource_type]
                    last_updated_str = schema_metadata.get('last_updated')

                    if last_updated_str:
                        try:
                            last_updated = datetime.fromisoformat(last_updated_str)
                            if datetime.now() - last_updated < SCHEMA_UPDATE_INTERVAL:
                                # Schema is recent enough and valid, use cached version
                                return cached_schema
                            else:
                                print(
                                    f'Schema for {resource_type} is older than {SCHEMA_UPDATE_INTERVAL.days} days, refreshing...'
                                )
                        except ValueError:
                            print(
                                f'Invalid timestamp format for {resource_type}: {last_updated_str}'
                            )
                else:
                    # No metadata for this schema but it's valid, use cached version
                    return cached_schema

        # Download schema (either not cached, expired, or corrupted)
        schema = await self._download_resource_schema(resource_type, region)
        return schema

    async def _download_resource_schema(
        self, resource_type: str, region: str | None = None
    ) -> dict:
        """Download schema for a specific resource type.

        Args:
            resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")
            region: AWS region to use for API calls

        Returns:
            The downloaded schema or None if download failed
        """
        # Extract service name from resource type
        parts = resource_type.split('::')
        if len(parts) < 2:
            raise ClientError(
                f"Invalid resource type format: {resource_type}. Expected format like 'Namespace::Service::Resource'"
            )

        # If no local spec file or it failed to load, try CloudFormation API
        # Retry logic for schema download
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(
                    f'Downloading schema for {resource_type} using CloudFormation API (attempt {attempt + 1}/{max_retries})'
                )
                cfn_client = get_aws_client('cloudformation', region)
                resp = cfn_client.describe_type(Type='RESOURCE', TypeName=resource_type)
                schema_str = resp['Schema']

                if not schema_str or len(schema_str) < 100:  # Basic sanity check
                    raise ClientError(f'Schema response too short: {len(schema_str)} characters')

                spec = json.loads(schema_str)

                # Validate that the schema has properties (not empty)
                if not spec.get('properties'):
                    raise ClientError(
                        f'Downloaded schema for {resource_type} has no properties - API may have failed'
                    )

                # For known taggable resources, verify Tags property exists
                if resource_type in [
                    'AWS::S3::Bucket',
                    'AWS::EC2::Instance',
                    'AWS::RDS::DBInstance',
                ]:
                    if 'Tags' not in spec.get('properties', {}):
                        print(
                            f'Warning: {resource_type} schema missing Tags property, but resource should support tagging'
                        )

                # Save schema to cache only if it's valid
                schema_file = self.cache_dir / f'{resource_type.replace("::", "_")}.json'
                with open(schema_file, 'w') as f:
                    f.write(schema_str)

                # Update registry with the valid schema
                self.schema_registry[resource_type] = spec

                # Update metadata
                self.metadata['schemas'][resource_type] = {
                    'last_updated': datetime.now().isoformat(),
                    'file_path': str(schema_file),
                    'source': 'cloudformation_api',
                }

                with open(self.metadata_file, 'w') as f:
                    json.dump(self.metadata, f, indent=2)

                print(f'Processed and cached schema for {resource_type}')
                return spec

            except Exception as e:
                print(f'Schema download attempt {attempt + 1} failed: {str(e)}')
                if attempt == max_retries - 1:  # Last attempt
                    raise ClientError(
                        f'Failed to download valid schema for {resource_type} after {max_retries} attempts: {str(e)}'
                    )
                # Wait before retry
                import time

                time.sleep(1)

        # Should never reach here
        raise ClientError(f'Failed to download schema for {resource_type}')


_schema_manager_instance = SchemaManager()


# used to load a single instance of the schema manager
def schema_manager() -> SchemaManager:
    """Loads a singleton of the resource."""
    return _schema_manager_instance
