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

"""Serverless Manager.

Handles business logic for AWS DMS Serverless operations including
migration projects, data providers, instance profiles, and data migrations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class ServerlessManager:
    """Manager for DMS Serverless operations."""

    def __init__(self, client: DMSClient):
        """Initialize serverless manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized ServerlessManager')

    # ========================================================================
    # MIGRATION PROJECT OPERATIONS
    # ========================================================================

    def create_migration_project(
        self,
        identifier: str,
        instance_profile_arn: str,
        source_data_provider_descriptors: List[Dict[str, Any]],
        target_data_provider_descriptors: List[Dict[str, Any]],
        transformation_rules: Optional[str] = None,
        description: Optional[str] = None,
        schema_conversion_application_attributes: Optional[Dict[str, Any]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create a migration project.

        Args:
            identifier: Project identifier
            instance_profile_arn: Instance profile ARN
            source_data_provider_descriptors: Source data providers
            target_data_provider_descriptors: Target data providers
            transformation_rules: Transformation rules JSON
            description: Project description
            schema_conversion_application_attributes: Schema conversion attributes
            tags: Resource tags

        Returns:
            Created migration project details
        """
        logger.info('Creating migration project', identifier=identifier)

        params: Dict[str, Any] = {
            'MigrationProjectIdentifier': identifier,
            'InstanceProfileArn': instance_profile_arn,
            'SourceDataProviderDescriptors': source_data_provider_descriptors,
            'TargetDataProviderDescriptors': target_data_provider_descriptors,
        }

        if transformation_rules:
            params['TransformationRules'] = transformation_rules
        if description:
            params['Description'] = description
        if schema_conversion_application_attributes:
            params['SchemaConversionApplicationAttributes'] = (
                schema_conversion_application_attributes
            )
        if tags:
            params['Tags'] = tags

        response = self.client.call_api('create_migration_project', **params)

        project = response.get('MigrationProject', {})

        return {
            'success': True,
            'data': {
                'migration_project': project,
                'message': 'Migration project created successfully',
            },
            'error': None,
        }

    def modify_migration_project(
        self,
        arn: str,
        identifier: Optional[str] = None,
        instance_profile_arn: Optional[str] = None,
        source_data_provider_descriptors: Optional[List[Dict[str, Any]]] = None,
        target_data_provider_descriptors: Optional[List[Dict[str, Any]]] = None,
        transformation_rules: Optional[str] = None,
        description: Optional[str] = None,
        schema_conversion_application_attributes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Modify a migration project."""
        logger.info('Modifying migration project', arn=arn)

        params: Dict[str, Any] = {'MigrationProjectArn': arn}

        if identifier:
            params['MigrationProjectIdentifier'] = identifier
        if instance_profile_arn:
            params['InstanceProfileArn'] = instance_profile_arn
        if source_data_provider_descriptors:
            params['SourceDataProviderDescriptors'] = source_data_provider_descriptors
        if target_data_provider_descriptors:
            params['TargetDataProviderDescriptors'] = target_data_provider_descriptors
        if transformation_rules:
            params['TransformationRules'] = transformation_rules
        if description:
            params['Description'] = description
        if schema_conversion_application_attributes:
            params['SchemaConversionApplicationAttributes'] = (
                schema_conversion_application_attributes
            )

        response = self.client.call_api('modify_migration_project', **params)

        project = response.get('MigrationProject', {})

        return {
            'success': True,
            'data': {
                'migration_project': project,
                'message': 'Migration project modified successfully',
            },
            'error': None,
        }

    def delete_migration_project(self, arn: str) -> Dict[str, Any]:
        """Delete a migration project."""
        logger.info('Deleting migration project', arn=arn)

        response = self.client.call_api('delete_migration_project', MigrationProjectArn=arn)

        project = response.get('MigrationProject', {})

        return {
            'success': True,
            'data': {
                'migration_project': project,
                'message': 'Migration project deleted successfully',
            },
            'error': None,
        }

    def list_migration_projects(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List migration projects."""
        logger.info('Listing migration projects', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_migration_projects', **params)

        projects = response.get('MigrationProjects', [])

        result = {
            'success': True,
            'data': {'migration_projects': projects, 'count': len(projects)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result

    # ========================================================================
    # DATA PROVIDER OPERATIONS
    # ========================================================================

    def create_data_provider(
        self,
        identifier: str,
        engine: str,
        settings: Dict[str, Any],
        description: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create a data provider."""
        logger.info('Creating data provider', identifier=identifier)

        params: Dict[str, Any] = {
            'DataProviderIdentifier': identifier,
            'Engine': engine,
            'Settings': settings,
        }

        if description:
            params['Description'] = description
        if tags:
            params['Tags'] = tags

        response = self.client.call_api('create_data_provider', **params)

        provider = response.get('DataProvider', {})

        return {
            'success': True,
            'data': {'data_provider': provider, 'message': 'Data provider created successfully'},
            'error': None,
        }

    def modify_data_provider(
        self,
        arn: str,
        identifier: Optional[str] = None,
        engine: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Modify a data provider."""
        logger.info('Modifying data provider', arn=arn)

        params: Dict[str, Any] = {'DataProviderArn': arn}

        if identifier:
            params['DataProviderIdentifier'] = identifier
        if engine:
            params['Engine'] = engine
        if settings:
            params['Settings'] = settings
        if description:
            params['Description'] = description

        response = self.client.call_api('modify_data_provider', **params)

        provider = response.get('DataProvider', {})

        return {
            'success': True,
            'data': {'data_provider': provider, 'message': 'Data provider modified successfully'},
            'error': None,
        }

    def delete_data_provider(self, arn: str) -> Dict[str, Any]:
        """Delete a data provider."""
        logger.info('Deleting data provider', arn=arn)

        response = self.client.call_api('delete_data_provider', DataProviderArn=arn)

        provider = response.get('DataProvider', {})

        return {
            'success': True,
            'data': {'data_provider': provider, 'message': 'Data provider deleted successfully'},
            'error': None,
        }

    def list_data_providers(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List data providers."""
        logger.info('Listing data providers', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_data_providers', **params)

        providers = response.get('DataProviders', [])

        result = {
            'success': True,
            'data': {'data_providers': providers, 'count': len(providers)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result

    # ========================================================================
    # INSTANCE PROFILE OPERATIONS
    # ========================================================================

    def create_instance_profile(
        self,
        identifier: str,
        description: Optional[str] = None,
        kms_key_arn: Optional[str] = None,
        publicly_accessible: Optional[bool] = None,
        network_type: Optional[str] = None,
        subnet_group_identifier: Optional[str] = None,
        vpc_security_groups: Optional[List[str]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create an instance profile."""
        logger.info('Creating instance profile', identifier=identifier)

        params: Dict[str, Any] = {'InstanceProfileIdentifier': identifier}

        if description:
            params['Description'] = description
        if kms_key_arn:
            params['KmsKeyArn'] = kms_key_arn
        if publicly_accessible is not None:
            params['PubliclyAccessible'] = publicly_accessible
        if network_type:
            params['NetworkType'] = network_type
        if subnet_group_identifier:
            params['SubnetGroupIdentifier'] = subnet_group_identifier
        if vpc_security_groups:
            params['VpcSecurityGroups'] = vpc_security_groups
        if tags:
            params['Tags'] = tags

        response = self.client.call_api('create_instance_profile', **params)

        profile = response.get('InstanceProfile', {})

        return {
            'success': True,
            'data': {
                'instance_profile': profile,
                'message': 'Instance profile created successfully',
            },
            'error': None,
        }

    def modify_instance_profile(
        self,
        arn: str,
        identifier: Optional[str] = None,
        description: Optional[str] = None,
        kms_key_arn: Optional[str] = None,
        publicly_accessible: Optional[bool] = None,
        network_type: Optional[str] = None,
        subnet_group_identifier: Optional[str] = None,
        vpc_security_groups: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Modify an instance profile."""
        logger.info('Modifying instance profile', arn=arn)

        params: Dict[str, Any] = {'InstanceProfileArn': arn}

        if identifier:
            params['InstanceProfileIdentifier'] = identifier
        if description:
            params['Description'] = description
        if kms_key_arn:
            params['KmsKeyArn'] = kms_key_arn
        if publicly_accessible is not None:
            params['PubliclyAccessible'] = publicly_accessible
        if network_type:
            params['NetworkType'] = network_type
        if subnet_group_identifier:
            params['SubnetGroupIdentifier'] = subnet_group_identifier
        if vpc_security_groups:
            params['VpcSecurityGroups'] = vpc_security_groups

        response = self.client.call_api('modify_instance_profile', **params)

        profile = response.get('InstanceProfile', {})

        return {
            'success': True,
            'data': {
                'instance_profile': profile,
                'message': 'Instance profile modified successfully',
            },
            'error': None,
        }

    def delete_instance_profile(self, arn: str) -> Dict[str, Any]:
        """Delete an instance profile."""
        logger.info('Deleting instance profile', arn=arn)

        response = self.client.call_api('delete_instance_profile', InstanceProfileArn=arn)

        profile = response.get('InstanceProfile', {})

        return {
            'success': True,
            'data': {
                'instance_profile': profile,
                'message': 'Instance profile deleted successfully',
            },
            'error': None,
        }

    def list_instance_profiles(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List instance profiles."""
        logger.info('Listing instance profiles', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_instance_profiles', **params)

        profiles = response.get('InstanceProfiles', [])

        result = {
            'success': True,
            'data': {'instance_profiles': profiles, 'count': len(profiles)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result

    # ========================================================================
    # DATA MIGRATION OPERATIONS
    # ========================================================================

    def create_data_migration(
        self,
        identifier: str,
        migration_type: str,
        service_access_role_arn: str,
        source_data_settings: List[Dict[str, Any]],
        data_migration_settings: Optional[Dict[str, Any]] = None,
        data_migration_name: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create a data migration."""
        logger.info('Creating data migration', identifier=identifier)

        params: Dict[str, Any] = {
            'DataMigrationIdentifier': identifier,
            'MigrationType': migration_type,
            'ServiceAccessRoleArn': service_access_role_arn,
            'SourceDataSettings': source_data_settings,
        }

        if data_migration_settings:
            params['DataMigrationSettings'] = data_migration_settings
        if data_migration_name:
            params['DataMigrationName'] = data_migration_name
        if tags:
            params['Tags'] = tags

        response = self.client.call_api('create_data_migration', **params)

        migration = response.get('DataMigration', {})

        return {
            'success': True,
            'data': {
                'data_migration': migration,
                'message': 'Data migration created successfully',
            },
            'error': None,
        }

    def modify_data_migration(
        self,
        arn: str,
        identifier: Optional[str] = None,
        migration_type: Optional[str] = None,
        data_migration_name: Optional[str] = None,
        data_migration_settings: Optional[Dict[str, Any]] = None,
        source_data_settings: Optional[List[Dict[str, Any]]] = None,
        number_of_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Modify a data migration."""
        logger.info('Modifying data migration', arn=arn)

        params: Dict[str, Any] = {'DataMigrationArn': arn}

        if identifier:
            params['DataMigrationIdentifier'] = identifier
        if migration_type:
            params['MigrationType'] = migration_type
        if data_migration_name:
            params['DataMigrationName'] = data_migration_name
        if data_migration_settings:
            params['DataMigrationSettings'] = data_migration_settings
        if source_data_settings:
            params['SourceDataSettings'] = source_data_settings
        if number_of_jobs:
            params['NumberOfJobs'] = number_of_jobs

        response = self.client.call_api('modify_data_migration', **params)

        migration = response.get('DataMigration', {})

        return {
            'success': True,
            'data': {
                'data_migration': migration,
                'message': 'Data migration modified successfully',
            },
            'error': None,
        }

    def delete_data_migration(self, arn: str) -> Dict[str, Any]:
        """Delete a data migration."""
        logger.info('Deleting data migration', arn=arn)

        response = self.client.call_api('delete_data_migration', DataMigrationArn=arn)

        migration = response.get('DataMigration', {})

        return {
            'success': True,
            'data': {
                'data_migration': migration,
                'message': 'Data migration deleted successfully',
            },
            'error': None,
        }

    def list_data_migrations(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List data migrations."""
        logger.info('Listing data migrations', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_data_migrations', **params)

        migrations = response.get('DataMigrations', [])

        result = {
            'success': True,
            'data': {'data_migrations': migrations, 'count': len(migrations)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result

    def start_data_migration(self, arn: str, start_type: str) -> Dict[str, Any]:
        """Start a data migration."""
        logger.info('Starting data migration', arn=arn, start_type=start_type)

        response = self.client.call_api(
            'start_data_migration', DataMigrationArn=arn, StartType=start_type
        )

        migration = response.get('DataMigration', {})

        return {
            'success': True,
            'data': {
                'data_migration': migration,
                'message': f'Data migration started with type: {start_type}',
            },
            'error': None,
        }

    def stop_data_migration(self, arn: str) -> Dict[str, Any]:
        """Stop a data migration."""
        logger.info('Stopping data migration', arn=arn)

        response = self.client.call_api('stop_data_migration', DataMigrationArn=arn)

        migration = response.get('DataMigration', {})

        return {
            'success': True,
            'data': {'data_migration': migration, 'message': 'Data migration stop initiated'},
            'error': None,
        }
