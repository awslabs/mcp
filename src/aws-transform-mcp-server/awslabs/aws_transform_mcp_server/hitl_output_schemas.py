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

"""AUTO-GENERATED output schema metadata for HITL components.

Ported from hitl-output-schemas.generated.ts. Each entry describes a
UX component's output shape: whether it is display-only, whether LLM input
should be merged onto the agent artifact, example responses, and the raw
JSON Schema for the _outputSchema field.

Do not edit manually -- regenerate from the schema registry.
"""
# ruff: noqa: E501

from typing import Any, Dict, List, Optional


class OutputSchemaMeta:
    """Metadata for a single UX component output schema."""

    __slots__ = ('display_only', 'merge_with_artifact', 'examples', 'json_schema', 'chat_hint')

    def __init__(
        self,
        *,
        display_only: bool,
        merge_with_artifact: bool,
        examples: List[Any],
        json_schema: Dict[str, Any],
        chat_hint: Optional[str] = None,
    ) -> None:
        """Initialize OutputSchemaMeta."""
        self.display_only = display_only
        self.merge_with_artifact = merge_with_artifact
        self.examples = examples
        self.json_schema = json_schema
        self.chat_hint = chat_hint


OUTPUT_SCHEMA_META: Dict[str, OutputSchemaMeta] = {
    'AutoForm': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'data': {
                    'fullName': 'Jane Smith',
                    'agreeToTerms': True,
                    'preferredRegions': ['us-east-1', 'eu-west-1'],
                },
                'metadata': {
                    'schemaVersion': '1.0',
                    'fieldCount': 3,
                    'validationStatus': 'valid',
                    'timestamp': '2025-01-15T10:30:00Z',
                },
            }
        ],
        json_schema={
            'title': 'AutoForm Output',
            'description': 'Output schema for AutoForm component. Returns form data as key-value pairs and validation metadata.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'data': {
                        'fullName': 'Jane Smith',
                        'agreeToTerms': True,
                        'preferredRegions': ['us-east-1', 'eu-west-1'],
                    },
                    'metadata': {
                        'schemaVersion': '1.0',
                        'fieldCount': 3,
                        'validationStatus': 'valid',
                        'timestamp': '2025-01-15T10:30:00Z',
                    },
                }
            ],
            'properties': {
                'data': {
                    'type': 'object',
                    'description': 'Form data as Record<string, FieldValue>',
                    'patternProperties': {
                        '.*': {
                            'oneOf': [
                                {'type': 'string'},
                                {'type': 'array', 'items': {'type': 'string'}},
                                {'type': 'boolean'},
                                {
                                    'type': 'array',
                                    'description': 'Array of uploaded file data (for fileUpload fields)',
                                    'items': {
                                        'type': 'object',
                                        'properties': {
                                            'name': {'type': 'string'},
                                            'content': {
                                                'type': 'string',
                                                'description': 'Base64-encoded file content',
                                            },
                                            'isZip': {'type': 'boolean'},
                                        },
                                        'required': ['name', 'content', 'isZip'],
                                        'additionalProperties': False,
                                    },
                                },
                                {
                                    'type': 'array',
                                    'description': 'Array of uploaded artifacts (for fileUploadV2 fields)',
                                    'items': {
                                        'type': 'object',
                                        'properties': {
                                            'artifactId': {'type': 'string'},
                                            'name': {'type': 'string'},
                                            'mimeType': {'type': 'string'},
                                        },
                                        'required': ['artifactId', 'name', 'mimeType'],
                                        'additionalProperties': False,
                                    },
                                },
                            ]
                        }
                    },
                    'additionalProperties': False,
                },
                'metadata': {
                    'type': 'object',
                    'properties': {
                        'schemaVersion': {'type': 'string', 'const': '1.0'},
                        'fieldCount': {'type': 'number', 'minimum': 0},
                        'validationStatus': {
                            'type': 'string',
                            'enum': ['valid', 'invalid'],
                            'description': 'Indicates if any of the form field is invalid',
                        },
                        'timestamp': {
                            'type': 'string',
                            'format': 'date-time',
                            'description': 'The time at which this object was updated on the frontend',
                        },
                    },
                    'required': ['schemaVersion', 'fieldCount', 'validationStatus', 'timestamp'],
                    'additionalProperties': False,
                },
            },
            'required': ['data', 'metadata'],
            'additionalProperties': True,
        },
    ),
    'CompleteMigration': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'CompleteMigration Output',
            'description': 'Output schema for CompleteMigration. Display-only component that shows post-migration instructions and an external link to the MGN console. No user input is collected.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ConfirmFinalizeCutOver': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'ConfirmFinalizeCutOver Output',
            'description': 'Output schema for ConfirmFinalizeCutOver. Display-only component that shows DNS provider and security groups guidance before finalize cutover. No user input is collected.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ConfirmInstanceLaunch': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'isGenerateSelected': True},
            {'uploadedFiles': []},
            {
                'uploadedFiles': [
                    {'name': 'inventory.csv', 'content': 'base64encodedcontent==', 'isZip': False}
                ]
            },
        ],
        json_schema={
            'title': 'ConfirmInstanceLaunch Output',
            'description': "Output schema for ConfirmInstanceLaunch. Collects the user's inventory choice before launching test or cutover instances. May include an uploaded inventory CSV file, or a flag indicating the user chose to generate/regenerate the inventory.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'isGenerateSelected': True},
                {'uploadedFiles': []},
                {
                    'uploadedFiles': [
                        {
                            'name': 'inventory.csv',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ]
                },
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded inventory CSV files encoded as base64. Empty array when the user chose to continue with the current inventory.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                },
                'isGenerateSelected': {
                    'type': 'boolean',
                    'description': 'True when the user clicked Generate/Regenerate inventory; false when a table-only refresh is requested.',
                },
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ConfirmInventory': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'uploadedFiles': []},
            {
                'uploadedFiles': [
                    {
                        'name': 'inventory-wave1.csv',
                        'content': 'base64encodedcontent==',
                        'isZip': False,
                    }
                ]
            },
        ],
        json_schema={
            'title': 'ConfirmInventory Output',
            'description': "Output schema for ConfirmInventory. Collects the user's inventory decision before launching a migration wave. The user can continue with the current inventory (empty uploadedFiles) or upload a modified CSV.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'uploadedFiles': []},
                {
                    'uploadedFiles': [
                        {
                            'name': 'inventory-wave1.csv',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ]
                },
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded inventory CSV files encoded as base64. Empty array when the user continues with the current inventory.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': ['uploadedFiles'],
            'additionalProperties': True,
        },
    ),
    'ConfirmLaunchConfigurations': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'uploadedFiles': []},
            {
                'uploadedFiles': [
                    {
                        'name': 'launch-config.csv',
                        'content': 'base64encodedcontent==',
                        'isZip': False,
                    }
                ]
            },
        ],
        json_schema={
            'title': 'ConfirmLaunchConfigurations Output',
            'description': "Output schema for ConfirmLaunchConfigurations. Collects the user's launch configuration decision. The user can continue with the current launch config (empty uploadedFiles) or upload a modified inventory CSV.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'uploadedFiles': []},
                {
                    'uploadedFiles': [
                        {
                            'name': 'launch-config.csv',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ]
                },
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded launch configuration CSV files encoded as base64. Empty array when the user continues with the current configuration.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': ['uploadedFiles'],
            'additionalProperties': True,
        },
    ),
    'ConsentDeleteExistingNetworkMigration': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'ConsentDeleteExistingNetworkMigration Output',
            'description': 'Output schema for ConsentDeleteExistingNetworkMigration. Display-only consent component — the user confirms by clicking the submit button. No structured payload is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'DBModCodeTransformationResults': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'selectedRepos': [{'id': 'repo-001'}, {'id': 'repo-002'}]}],
        json_schema={
            'title': 'DBModCodeTransformationResults Output',
            'description': 'Output schema for DBModCodeTransformationResults. Emits the list of selected repository IDs for code transformation, plus optional action/retryStatus fields when a retry is triggered.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'selectedRepos': [{'id': 'repo-001'}, {'id': 'repo-002'}]}],
            'properties': {
                'selectedRepos': {
                    'type': 'array',
                    'description': 'List of selected repositories. Normal path emits {id} only; retry path passes full table item objects.',
                    'items': {
                        'type': 'object',
                        'properties': {'id': {'type': 'string', 'description': 'Repository ID.'}},
                        'required': ['id'],
                        'additionalProperties': True,
                    },
                },
                'action': {
                    'type': 'string',
                    'description': 'User-triggered action. Currently only RETRY is supported.',
                    'enum': ['RETRY'],
                },
                'retryStatus': {
                    'type': 'string',
                    'description': 'Status of the retry operation. Set to IN_PROGRESS when a retry is first triggered.',
                    'enum': ['IN_PROGRESS', 'COMPLETED'],
                },
                'QT_REFRESH': {
                    'type': 'boolean',
                    'description': 'Internal refresh flag propagated via data spread.',
                },
            },
            'required': ['selectedRepos'],
            'additionalProperties': True,
        },
    ),
    'DBModDiscoveredResources': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'discoveredDatabases': [
                    {
                        'host': 'db-server-01.example.com',
                        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                        'status': 'SUCCESS',
                        'databases': ['orders', 'inventory'],
                        'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                        'dms_project_name': 'my-dms-project',
                        'instance_id': 'instance-01',
                        'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                        'instance_profile_name': 'my-profile',
                        'source': 'on-premise',
                        'port': 1433,
                        'region': 'us-east-1',
                        'endpoint': None,
                        'failure_message': None,
                        'failure_step': None,
                        'security_groups': ['sg-12345678'],
                        'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                        'source_data_source_name': 'source-endpoint',
                        'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                        'target_data_source_name': 'target-endpoint',
                        'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                        'vpc': 'vpc-12345678',
                        'customer_s3_bucket_dms': 'my-dms-bucket',
                        'subnets': [
                            {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                        ],
                        'kms_key_aliases': [],
                        'selected_key_alias': None,
                    }
                ],
                'selectedTableDatabases': [
                    {
                        'host': 'db-server-01.example.com',
                        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                        'status': 'SUCCESS',
                        'databases': ['orders', 'inventory'],
                        'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                        'dms_project_name': 'my-dms-project',
                        'instance_id': 'instance-01',
                        'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                        'instance_profile_name': 'my-profile',
                        'source': 'on-premise',
                        'port': 1433,
                        'region': 'us-east-1',
                        'endpoint': None,
                        'failure_message': None,
                        'failure_step': None,
                        'security_groups': ['sg-12345678'],
                        'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                        'source_data_source_name': 'source-endpoint',
                        'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                        'target_data_source_name': 'target-endpoint',
                        'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                        'vpc': 'vpc-12345678',
                        'customer_s3_bucket_dms': 'my-dms-bucket',
                        'subnets': [
                            {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                        ],
                        'kms_key_aliases': [],
                        'selected_key_alias': None,
                    }
                ],
                'selectedTableRepos': [
                    {
                        'repository_id': 'repo-001',
                        'repository_display_name': 'my-app',
                        'full_repository_id': 'org/my-app',
                        'owner_id': 'owner-001',
                        'owner_display_name': 'MyOrg',
                        'is_private': True,
                        'description': 'Application repository',
                        'default_branch_name': 'main',
                        'size_in_bytes': 1048576,
                        'branches': ['main', 'develop'],
                        'assessment_branch': 'main',
                    }
                ],
            }
        ],
        json_schema={
            'title': 'DBModDiscoveredResources Output',
            'description': 'Output schema for DBModDiscoveredResources. Emits discovered databases, selected databases, and selected repositories. When a retry is triggered it also includes all discovered repos, an action, and a retryStatus.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'discoveredDatabases': [
                        {
                            'host': 'db-server-01.example.com',
                            'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                            'status': 'SUCCESS',
                            'databases': ['orders', 'inventory'],
                            'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                            'dms_project_name': 'my-dms-project',
                            'instance_id': 'instance-01',
                            'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                            'instance_profile_name': 'my-profile',
                            'source': 'on-premise',
                            'port': 1433,
                            'region': 'us-east-1',
                            'endpoint': None,
                            'failure_message': None,
                            'failure_step': None,
                            'security_groups': ['sg-12345678'],
                            'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                            'source_data_source_name': 'source-endpoint',
                            'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                            'target_data_source_name': 'target-endpoint',
                            'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                            'vpc': 'vpc-12345678',
                            'customer_s3_bucket_dms': 'my-dms-bucket',
                            'subnets': [
                                {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                            ],
                            'kms_key_aliases': [],
                            'selected_key_alias': None,
                        }
                    ],
                    'selectedTableDatabases': [
                        {
                            'host': 'db-server-01.example.com',
                            'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                            'status': 'SUCCESS',
                            'databases': ['orders', 'inventory'],
                            'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                            'dms_project_name': 'my-dms-project',
                            'instance_id': 'instance-01',
                            'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                            'instance_profile_name': 'my-profile',
                            'source': 'on-premise',
                            'port': 1433,
                            'region': 'us-east-1',
                            'endpoint': None,
                            'failure_message': None,
                            'failure_step': None,
                            'security_groups': ['sg-12345678'],
                            'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                            'source_data_source_name': 'source-endpoint',
                            'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                            'target_data_source_name': 'target-endpoint',
                            'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                            'vpc': 'vpc-12345678',
                            'customer_s3_bucket_dms': 'my-dms-bucket',
                            'subnets': [
                                {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                            ],
                            'kms_key_aliases': [],
                            'selected_key_alias': None,
                        }
                    ],
                    'selectedTableRepos': [
                        {
                            'repository_id': 'repo-001',
                            'repository_display_name': 'my-app',
                            'full_repository_id': 'org/my-app',
                            'owner_id': 'owner-001',
                            'owner_display_name': 'MyOrg',
                            'is_private': True,
                            'description': 'Application repository',
                            'default_branch_name': 'main',
                            'size_in_bytes': 1048576,
                            'branches': ['main', 'develop'],
                            'assessment_branch': 'main',
                        }
                    ],
                }
            ],
            'properties': {
                'discoveredDatabases': {
                    'type': 'array',
                    'description': 'Complete list of all discovered databases (passed through from agent artifact).',
                    'items': {'type': 'object'},
                },
                'selectedTableDatabases': {
                    'type': 'array',
                    'description': 'User-selected databases from the Databases tab.',
                    'items': {'type': 'object'},
                },
                'selectedTableRepos': {
                    'type': 'array',
                    'description': 'User-selected repositories (with updated branch selections) from the Repositories tab.',
                    'items': {'type': 'object'},
                },
                'discoveredRepos': {
                    'type': 'array',
                    'description': 'Complete list of all discovered repositories. Only included when a retry action is triggered.',
                    'items': {'type': 'object'},
                },
                'action': {
                    'type': 'string',
                    'description': 'User-triggered retry action. Only present when the user clicks Retry.',
                    'enum': ['RETRY'],
                },
                'retryStatus': {
                    'type': 'string',
                    'description': 'Status of the retry operation. Set to IN_PROGRESS when retry is first triggered.',
                    'enum': ['IN_PROGRESS', 'COMPLETED'],
                },
            },
            'required': ['discoveredDatabases', 'selectedTableDatabases', 'selectedTableRepos'],
            'additionalProperties': True,
        },
    ),
    'DBModOnPremiseServerInfoTable': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'servers': [
                    {
                        'host': '10.0.1.100',
                        'port': 1433,
                        'username': 'admin',
                        'vpc_id': 'vpc-12345678',
                        'security_group_ids': 'sg-12345678,sg-87654321',
                    }
                ]
            }
        ],
        json_schema={
            'title': 'DBModOnPremiseServerInfoTable Output',
            'description': 'Output schema for DBModOnPremiseServerInfoTable. Emits the current list of on-premise server items. When the user triggers a refresh action, also includes the action flag and QT_REFRESH.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'servers': [
                        {
                            'host': '10.0.1.100',
                            'port': 1433,
                            'username': 'admin',
                            'vpc_id': 'vpc-12345678',
                            'security_group_ids': 'sg-12345678,sg-87654321',
                        }
                    ]
                }
            ],
            'properties': {
                'servers': {
                    'type': 'array',
                    'description': 'List of on-premise server items. Each item contains server connection details that may be inline-edited by the user (vpc_id, security_group_ids).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'host': {
                                'type': 'string',
                                'description': 'Server hostname or IP address (used as unique identifier).',
                            },
                            'port': {'type': 'number', 'description': 'Database port number.'},
                            'vpc_id': {
                                'type': 'string',
                                'description': 'VPC ID (editable by user).',
                            },
                            'security_group_ids': {
                                'type': 'string',
                                'description': 'Comma-separated security group IDs (editable by user).',
                            },
                        },
                        'required': ['host'],
                        'additionalProperties': True,
                    },
                },
                'action': {
                    'type': 'string',
                    'description': 'Action identifier. Set to REFRESH when the user triggers a data refresh.',
                    'enum': ['REFRESH'],
                },
                'QT_REFRESH': {
                    'type': 'boolean',
                    'description': 'Flag indicating a refresh is in progress. Set to true alongside action=REFRESH.',
                },
            },
            'required': ['servers'],
            'additionalProperties': True,
        },
    ),
    'DBModPrerequisites': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'DBModPrerequisites Output',
            'description': 'Output schema for DBModPrerequisites. This is a display-only component that shows database and source code setup guides. It never calls onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'DBModSimpleDisplay': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'DBModSimpleDisplay Output',
            'description': 'Output schema for DBModSimpleDisplay. This is a display-only component that renders a static table of databases. It never calls onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'DBModSimpleTextInput': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'data': 's3://my-bucket/migration-data/', 'enableFeatures': ['featureA', 'featureB']}
        ],
        json_schema={
            'title': 'DBModSimpleTextInput Output',
            'description': 'Output schema for DBModSimpleTextInput. Emits the current text input value along with the list of enabled feature flag names.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'data': 's3://my-bucket/migration-data/',
                    'enableFeatures': ['featureA', 'featureB'],
                }
            ],
            'properties': {
                'data': {
                    'type': 'string',
                    'description': 'The current value entered by the user in the text input field.',
                },
                'enableFeatures': {
                    'type': 'array',
                    'description': 'Array of enabled feature flag names, returned by getEnabledFeatures().',
                    'items': {'type': 'string'},
                },
            },
            'required': ['data', 'enableFeatures'],
            'additionalProperties': True,
        },
    ),
    'DataMigrationStatus': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'dataMigrationItem': [
                    {
                        'host': 'db-server-01.example.com',
                        'dbName': 'orders',
                        'status': 'COMPLETED',
                        'dataMigrationLink': 'https://console.aws.amazon.com/dms/v2/home#tasks/arn:aws:dms:us-east-1:123456789012:task:ABCDEF',
                        'preAssessmentLink': 'https://console.aws.amazon.com/dms/v2/home#assessments/ABCDEF',
                    }
                ],
                'selectedTableDataMigrationItems': [
                    {
                        'host': 'db-server-01.example.com',
                        'dbName': 'orders',
                        'status': 'COMPLETED',
                        'dataMigrationLink': 'https://console.aws.amazon.com/dms/v2/home#tasks/arn:aws:dms:us-east-1:123456789012:task:ABCDEF',
                        'preAssessmentLink': 'https://console.aws.amazon.com/dms/v2/home#assessments/ABCDEF',
                    }
                ],
            }
        ],
        json_schema={
            'title': 'DataMigrationStatus Output',
            'description': 'Output schema for DataMigrationStatus. Emits the current list of all migration items and the user-selected subset, plus optional action/retryStatus fields when a retry or skip-pre-migration-assessment action is triggered.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'dataMigrationItem': [
                        {
                            'host': 'db-server-01.example.com',
                            'dbName': 'orders',
                            'status': 'COMPLETED',
                            'dataMigrationLink': 'https://console.aws.amazon.com/dms/v2/home#tasks/arn:aws:dms:us-east-1:123456789012:task:ABCDEF',
                            'preAssessmentLink': 'https://console.aws.amazon.com/dms/v2/home#assessments/ABCDEF',
                        }
                    ],
                    'selectedTableDataMigrationItems': [
                        {
                            'host': 'db-server-01.example.com',
                            'dbName': 'orders',
                            'status': 'COMPLETED',
                            'dataMigrationLink': 'https://console.aws.amazon.com/dms/v2/home#tasks/arn:aws:dms:us-east-1:123456789012:task:ABCDEF',
                            'preAssessmentLink': 'https://console.aws.amazon.com/dms/v2/home#assessments/ABCDEF',
                        }
                    ],
                }
            ],
            'properties': {
                'dataMigrationItem': {
                    'type': 'array',
                    'description': 'Full list of all data migration items (passed through from props).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'host': {'type': 'string', 'description': 'Database server hostname.'},
                            'dbName': {'type': 'string', 'description': 'Database name.'},
                            'status': {
                                'type': 'string',
                                'description': 'Migration status (e.g. COMPLETED, FAILED, IN_PROGRESS).',
                            },
                            'dataMigrationLink': {
                                'type': 'string',
                                'description': 'URL to the DMS migration task.',
                            },
                            'preAssessmentLink': {
                                'type': 'string',
                                'description': 'URL to the pre-migration assessment report.',
                            },
                        },
                        'required': ['host', 'dbName', 'status', 'dataMigrationLink'],
                        'additionalProperties': False,
                    },
                },
                'selectedTableDataMigrationItems': {
                    'type': 'array',
                    'description': 'User-selected rows in the migration status table.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'host': {'type': 'string'},
                            'dbName': {'type': 'string'},
                            'status': {'type': 'string'},
                            'dataMigrationLink': {'type': 'string'},
                            'preAssessmentLink': {'type': 'string'},
                        },
                        'required': ['host', 'dbName', 'status', 'dataMigrationLink'],
                        'additionalProperties': False,
                    },
                },
                'action': {
                    'type': 'string',
                    'description': 'Action triggered by the user (e.g. RETRY, SKIP_PREMIGRATION_ASSESSMENT). Only present when a retry/skip action is initiated.',
                    'enum': ['RETRY', 'SKIP_PREMIGRATION_ASSESSMENT'],
                },
                'retryStatus': {
                    'type': 'string',
                    'description': 'Status of the retry operation. Only present alongside an action. Value is IN_PROGRESS when the action is first triggered.',
                    'enum': ['IN_PROGRESS', 'COMPLETED'],
                },
            },
            'required': ['dataMigrationItem', 'selectedTableDataMigrationItems'],
            'additionalProperties': True,
        },
    ),
    'DiscoveryToolDbSelection': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'discoveredInfo': [
                    {
                        'host': 'db-server-01.example.com',
                        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                        'status': 'SUCCESS',
                        'databases': ['orders', 'inventory'],
                        'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                        'dms_project_name': 'my-dms-project',
                        'instance_id': 'instance-01',
                        'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                        'instance_profile_name': 'my-profile',
                        'port': 1433,
                        'region': 'us-east-1',
                        'endpoint': None,
                        'failure_message': None,
                        'failure_step': None,
                        'security_groups': ['sg-12345678'],
                        'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                        'source_data_source_name': 'source-endpoint',
                        'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                        'target_data_source_name': 'target-endpoint',
                        'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                        'vpc': 'vpc-12345678',
                        'customer_s3_bucket_dms': 'my-dms-bucket',
                        'subnets': [
                            {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                        ],
                    }
                ]
            }
        ],
        json_schema={
            'title': 'DiscoveryToolDbSelection Output',
            'description': "Output schema for DiscoveryToolDbSelection. Emits a filtered list of discovered database entries. Items with status SUCCESS are always included; items where the user has chosen 'fixed' as their action are also included.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'discoveredInfo': [
                        {
                            'host': 'db-server-01.example.com',
                            'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                            'status': 'SUCCESS',
                            'databases': ['orders', 'inventory'],
                            'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                            'dms_project_name': 'my-dms-project',
                            'instance_id': 'instance-01',
                            'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                            'instance_profile_name': 'my-profile',
                            'port': 1433,
                            'region': 'us-east-1',
                            'endpoint': None,
                            'failure_message': None,
                            'failure_step': None,
                            'security_groups': ['sg-12345678'],
                            'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                            'source_data_source_name': 'source-endpoint',
                            'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                            'target_data_source_name': 'target-endpoint',
                            'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                            'vpc': 'vpc-12345678',
                            'customer_s3_bucket_dms': 'my-dms-bucket',
                            'subnets': [
                                {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                            ],
                        }
                    ]
                }
            ],
            'properties': {
                'discoveredInfo': {
                    'type': 'array',
                    'description': "Filtered list of discovered database connection entries. Contains only entries with status=SUCCESS or where the user selected 'fixed' as their action.",
                    'items': {
                        'type': 'object',
                        'properties': {
                            'host': {'type': 'string'},
                            'secret_arn': {'type': 'string'},
                            'status': {'type': 'string'},
                            'databases': {'type': 'array', 'items': {'type': 'string'}},
                            'dms_project_arn': {'type': 'string'},
                            'dms_project_name': {'type': 'string'},
                            'instance_id': {'type': 'string'},
                            'instance_profile_arn': {'type': 'string'},
                            'instance_profile_name': {'type': 'string'},
                            'port': {'type': 'number'},
                            'region': {'type': ['string', 'null']},
                            'endpoint': {'type': ['string', 'null']},
                            'failure_message': {'type': ['string', 'null']},
                            'failure_step': {'type': ['string', 'null']},
                            'security_groups': {'type': 'array', 'items': {'type': 'string'}},
                            'source_data_source_arn': {'type': 'string'},
                            'source_data_source_name': {'type': 'string'},
                            'target_data_source_arn': {'type': 'string'},
                            'target_data_source_name': {'type': 'string'},
                            'target_secret_arn': {'type': 'string'},
                            'vpc': {'type': 'string'},
                            'customer_s3_bucket_dms': {'type': 'string'},
                            'subnets': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'availability_zone': {'type': 'string'},
                                        'subnet_id': {'type': 'string'},
                                    },
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['host', 'secret_arn', 'status'],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['discoveredInfo'],
            'additionalProperties': True,
        },
    ),
    'DotnetCFNDownload': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'runValidation': True}, {'skipDeployment': True}],
        json_schema={
            'title': 'DotnetCFNDownload Output',
            'description': 'Output schema for DotnetCFNDownload. Emitted when the user chooses to skip deployment or trigger validation in the validation-enabled flow. The download-only flow never calls onInputChange.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'runValidation': True}, {'skipDeployment': True}],
            'oneOf': [
                {
                    'required': ['runValidation'],
                    'properties': {
                        'runValidation': {
                            'type': 'boolean',
                            'enum': [True],
                            'description': 'Set to true when the user clicks the Validate button.',
                        }
                    },
                },
                {
                    'required': ['skipDeployment'],
                    'properties': {
                        'skipDeployment': {
                            'type': 'boolean',
                            'enum': [True],
                            'description': 'Set to true when the user clicks the Skip button.',
                        }
                    },
                },
            ],
            'properties': {
                'runValidation': {
                    'type': 'boolean',
                    'description': 'Set to true when the user clicks the Validate button (enableValidation flow only).',
                },
                'skipDeployment': {
                    'type': 'boolean',
                    'description': 'Set to true when the user clicks Skip (enableValidation flow only).',
                },
            },
            'additionalProperties': True,
        },
    ),
    'DotnetConfigInfra': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=True,
        examples=[
            {
                'deployableApplications': [
                    {
                        'id': 'my-repo_MySolution_MyApp',
                        'projectAssemblyName': 'MyApp',
                        'repositoryName': 'my-repo',
                        'solutionName': 'MySolution',
                        'projectParameterStatus': 'CONFIGURED_AND_COMMITTED',
                        'projectProvisionStatus': 'NOT_PROVISIONED',
                        'commitToGit': True,
                        'provision': False,
                        'infraParameters': {
                            'deploymentType': 'ECS',
                            'clusterName': 'AWSTransformCluster',
                            'cpuOptions': '1024',
                            'memory': '2048',
                        },
                    }
                ]
            },
            {
                'closeJobAndQuit': True,
                'deployableApplications': [
                    {
                        'id': 'my-repo__MyApp',
                        'projectAssemblyName': 'MyApp',
                        'repositoryName': 'my-repo',
                        'projectParameterStatus': 'NOT_CONFIGURED',
                        'commitToGit': False,
                    }
                ],
            },
        ],
        json_schema={
            'title': 'DotnetConfigInfra Output',
            'description': 'Output schema for DotnetConfigInfra. Emitted when the user commits configured applications to git or closes the job. Builds up application state across multiple parameter-save interactions before a final commit action.',
            'displayOnly': False,
            'mergeWithArtifact': True,
            'type': 'object',
            'examples': [
                {
                    'deployableApplications': [
                        {
                            'id': 'my-repo_MySolution_MyApp',
                            'projectAssemblyName': 'MyApp',
                            'repositoryName': 'my-repo',
                            'solutionName': 'MySolution',
                            'projectParameterStatus': 'CONFIGURED_AND_COMMITTED',
                            'projectProvisionStatus': 'NOT_PROVISIONED',
                            'commitToGit': True,
                            'provision': False,
                            'infraParameters': {
                                'deploymentType': 'ECS',
                                'clusterName': 'AWSTransformCluster',
                                'cpuOptions': '1024',
                                'memory': '2048',
                            },
                        }
                    ]
                },
                {
                    'closeJobAndQuit': True,
                    'deployableApplications': [
                        {
                            'id': 'my-repo__MyApp',
                            'projectAssemblyName': 'MyApp',
                            'repositoryName': 'my-repo',
                            'projectParameterStatus': 'NOT_CONFIGURED',
                            'commitToGit': False,
                        }
                    ],
                },
            ],
            'oneOf': [
                {
                    'required': ['deployableApplications'],
                    'properties': {
                        'deployableApplications': {
                            'type': 'array',
                            'description': 'All deployable application items with updated commitToGit flags and parameter statuses.',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {
                                        'type': 'string',
                                        'description': 'Composite key: {repositoryName}_{solutionName}_{projectAssemblyName}',
                                    },
                                    'projectAssemblyName': {'type': 'string'},
                                    'repositoryName': {'type': 'string'},
                                    'solutionName': {'type': 'string'},
                                    'projectParameterStatus': {
                                        'type': 'string',
                                        'enum': [
                                            'NOT_CONFIGURED',
                                            'CONFIGURED',
                                            'CONFIGURED_AND_COMMITTED',
                                            'READY_TO_COMMIT',
                                            'IN_PROGRESS',
                                            'FAILED',
                                        ],
                                    },
                                    'projectProvisionStatus': {
                                        'type': 'string',
                                        'enum': [
                                            'NOT_COMPLETED',
                                            'NOT_PROVISIONED',
                                            'IN_PROGRESS',
                                            'FAILED',
                                            'PROVISIONED',
                                            'DEPLOYED',
                                            'ATTENTION_REQUIRED',
                                            'BUILDING_APPLICATION',
                                            'DEPLOYING_APPLICATION',
                                            'BUILD_FAILED_INFRASTRUCTURE_PROVISIONED',
                                            'BUILD_SUCCEEDED_INFRASTRUCTURE_FAILED',
                                        ],
                                    },
                                    'commitToGit': {
                                        'type': 'boolean',
                                        'description': 'True if this application was selected for commit.',
                                    },
                                    'provision': {'type': 'boolean'},
                                    'repositoryNoOfDependencies': {'type': 'number'},
                                    'repositoryDependencyList': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'string'},
                                                'name': {'type': 'string'},
                                            },
                                            'additionalProperties': False,
                                        },
                                    },
                                    'infraParameters': {
                                        'type': 'object',
                                        'properties': {
                                            'deploymentType': {
                                                'type': 'string',
                                                'enum': ['ECS', 'EC2', 'EB'],
                                            },
                                            'subnetID': {'type': 'string'},
                                            'securityGroupID': {'type': 'string'},
                                            'amiID': {'type': 'string'},
                                            'instanceType': {'type': 'string'},
                                            'storageSize': {'type': 'string'},
                                            'clusterName': {'type': 'string'},
                                            'cpuOptions': {'type': 'string'},
                                            'memory': {'type': 'string'},
                                            'diskSize': {'type': 'string'},
                                            'ecrImage': {'type': 'string'},
                                            'ecrURI': {'type': 'string'},
                                            'instanceName': {'type': 'string'},
                                            'ebEnvironmentName': {'type': 'string'},
                                            'kmsKeyArn': {'type': 'string'},
                                            'kmsInvalid': {'type': 'boolean'},
                                            'scale': {'type': 'string'},
                                            'publicSubnetsForALB': {'type': 'string'},
                                            'publicSubnetIds': {
                                                'type': 'array',
                                                'items': {'type': 'string'},
                                            },
                                            'acmArnForALB': {'type': 'string'},
                                            'acmArnsOnAccount': {
                                                'type': 'array',
                                                'items': {'type': 'string'},
                                            },
                                        },
                                        'additionalProperties': False,
                                    },
                                    'instanceID': {'type': 'string'},
                                    'clusterID': {'type': 'string'},
                                    'connectionLink': {'type': 'string'},
                                    'databaseName': {'type': 'string'},
                                    'error': {
                                        'type': 'object',
                                        'properties': {
                                            'errorMessage': {'type': 'string'},
                                            'errorDetails': {'type': 'string'},
                                            'errorFix': {'type': 'string'},
                                        },
                                        'additionalProperties': False,
                                    },
                                },
                                'required': ['id', 'projectAssemblyName'],
                                'additionalProperties': False,
                            },
                        },
                        'closeJobAndQuit': {
                            'type': 'boolean',
                            'description': 'Set to true when the user explicitly closes the job and quits from the modal.',
                        },
                    },
                }
            ],
            'properties': {
                'deployableApplications': {
                    'type': 'array',
                    'description': 'All deployable application items with updated commitToGit flags and parameter statuses.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {
                                'type': 'string',
                                'description': 'Composite key: {repositoryName}_{solutionName}_{projectAssemblyName}',
                            },
                            'projectAssemblyName': {'type': 'string'},
                            'repositoryName': {'type': 'string'},
                            'solutionName': {'type': 'string'},
                            'projectParameterStatus': {
                                'type': 'string',
                                'enum': [
                                    'NOT_CONFIGURED',
                                    'CONFIGURED',
                                    'CONFIGURED_AND_COMMITTED',
                                    'READY_TO_COMMIT',
                                    'IN_PROGRESS',
                                    'FAILED',
                                ],
                            },
                            'projectProvisionStatus': {
                                'type': 'string',
                                'enum': [
                                    'NOT_COMPLETED',
                                    'NOT_PROVISIONED',
                                    'IN_PROGRESS',
                                    'FAILED',
                                    'PROVISIONED',
                                    'DEPLOYED',
                                    'ATTENTION_REQUIRED',
                                    'BUILDING_APPLICATION',
                                    'DEPLOYING_APPLICATION',
                                    'BUILD_FAILED_INFRASTRUCTURE_PROVISIONED',
                                    'BUILD_SUCCEEDED_INFRASTRUCTURE_FAILED',
                                ],
                            },
                            'commitToGit': {
                                'type': 'boolean',
                                'description': 'True if this application was selected for commit.',
                            },
                            'provision': {'type': 'boolean'},
                            'repositoryNoOfDependencies': {'type': 'number'},
                            'repositoryDependencyList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'string'},
                                        'name': {'type': 'string'},
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'infraParameters': {
                                'type': 'object',
                                'properties': {
                                    'deploymentType': {
                                        'type': 'string',
                                        'enum': ['ECS', 'EC2', 'EB'],
                                    },
                                    'subnetID': {'type': 'string'},
                                    'securityGroupID': {'type': 'string'},
                                    'amiID': {'type': 'string'},
                                    'instanceType': {'type': 'string'},
                                    'storageSize': {'type': 'string'},
                                    'clusterName': {'type': 'string'},
                                    'cpuOptions': {'type': 'string'},
                                    'memory': {'type': 'string'},
                                    'diskSize': {'type': 'string'},
                                    'ecrImage': {'type': 'string'},
                                    'ecrURI': {'type': 'string'},
                                    'instanceName': {'type': 'string'},
                                    'ebEnvironmentName': {'type': 'string'},
                                    'kmsKeyArn': {'type': 'string'},
                                    'kmsInvalid': {'type': 'boolean'},
                                    'scale': {'type': 'string'},
                                    'publicSubnetsForALB': {'type': 'string'},
                                    'publicSubnetIds': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                    },
                                    'acmArnForALB': {'type': 'string'},
                                    'acmArnsOnAccount': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                    },
                                },
                                'additionalProperties': False,
                            },
                            'instanceID': {'type': 'string'},
                            'clusterID': {'type': 'string'},
                            'connectionLink': {'type': 'string'},
                            'databaseName': {'type': 'string'},
                            'error': {
                                'type': 'object',
                                'properties': {
                                    'errorMessage': {'type': 'string'},
                                    'errorDetails': {'type': 'string'},
                                    'errorFix': {'type': 'string'},
                                },
                                'additionalProperties': False,
                            },
                        },
                        'required': ['id', 'projectAssemblyName'],
                        'additionalProperties': False,
                    },
                },
                'closeJobAndQuit': {
                    'type': 'boolean',
                    'description': 'Set to true when the user explicitly closes the job and quits from the modal.',
                },
            },
            'required': ['deployableApplications'],
            'additionalProperties': True,
        },
    ),
    'DotnetCrossRepoSelector': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=True,
        examples=[
            {
                'userSelectionType': 'RECOMMENDED',
                'selectedTableResources': [
                    {
                        'id': 'repo-abc',
                        'name': 'my-service',
                        'sourceBranch': 'main',
                        'resourceType': 'REPOSITORY',
                        'supported': 'YES',
                        'linesOfCode': 15000,
                    }
                ],
                'targetBranchDestination': 'transform-branch',
                'targetVersion': {'value': 'net8.0', 'label': '.NET 8'},
                'totalUniqueRepos': 1,
                'serviceQuotaLimits': {
                    'repoCountMonthlyConsumed': 1,
                    'repoCountMonthlyLimit': 10,
                    'locCountMonthlyConsumed': 15000,
                    'locCountMonthlyLimit': 1000000,
                    'locCountTotalConsumed': 15000,
                    'locCountTotalLimit': 5000000,
                    'createdAt': 1700000000000,
                },
            },
            {
                'userSelectionType': 'CUSTOMIZED',
                'selectedTableResources': [],
                'retryOption': 'ASSESSMENT',
                'targetBranchDestination': 'main',
                'targetVersion': {'value': 'net8.0', 'label': '.NET 8'},
                'serviceQuotaLimits': {
                    'repoCountMonthlyConsumed': 0,
                    'repoCountMonthlyLimit': 10,
                    'locCountMonthlyConsumed': 0,
                    'locCountMonthlyLimit': 1000000,
                    'locCountTotalConsumed': 0,
                    'locCountTotalLimit': 5000000,
                    'createdAt': 1700000000000,
                },
            },
        ],
        json_schema={
            'title': 'DotnetCrossRepoSelector Output',
            'description': 'Output schema for DotnetCrossRepoSelector. Continuously emitted as the user selects cross-repo resources. The full DotnetCrossRepoSelectorState is spread into the payload, with complexity fields filtered out. Also emitted with a retryOption when the user selects a retry action.',
            'displayOnly': False,
            'mergeWithArtifact': True,
            'type': 'object',
            'examples': [
                {
                    'userSelectionType': 'RECOMMENDED',
                    'selectedTableResources': [
                        {
                            'id': 'repo-abc',
                            'name': 'my-service',
                            'sourceBranch': 'main',
                            'resourceType': 'REPOSITORY',
                            'supported': 'YES',
                            'linesOfCode': 15000,
                        }
                    ],
                    'targetBranchDestination': 'transform-branch',
                    'targetVersion': {'value': 'net8.0', 'label': '.NET 8'},
                    'totalUniqueRepos': 1,
                    'serviceQuotaLimits': {
                        'repoCountMonthlyConsumed': 1,
                        'repoCountMonthlyLimit': 10,
                        'locCountMonthlyConsumed': 15000,
                        'locCountMonthlyLimit': 1000000,
                        'locCountTotalConsumed': 15000,
                        'locCountTotalLimit': 5000000,
                        'createdAt': 1700000000000,
                    },
                },
                {
                    'userSelectionType': 'CUSTOMIZED',
                    'selectedTableResources': [],
                    'retryOption': 'ASSESSMENT',
                    'targetBranchDestination': 'main',
                    'targetVersion': {'value': 'net8.0', 'label': '.NET 8'},
                    'serviceQuotaLimits': {
                        'repoCountMonthlyConsumed': 0,
                        'repoCountMonthlyLimit': 10,
                        'locCountMonthlyConsumed': 0,
                        'locCountMonthlyLimit': 1000000,
                        'locCountTotalConsumed': 0,
                        'locCountTotalLimit': 5000000,
                        'createdAt': 1700000000000,
                    },
                },
            ],
            'properties': {
                'userSelectionType': {
                    'type': 'string',
                    'enum': ['RECOMMENDED', 'CUSTOMIZED'],
                    'description': 'Whether the user used the recommended selection or a customized selection.',
                },
                'originalDiscoveredResources': {
                    'type': 'array',
                    'description': 'Original set of discovered resources (without complexity fields).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'resourceType': {
                                'type': 'string',
                                'enum': ['REPOSITORY', 'SOLUTION', 'PROJECT'],
                            },
                            'supported': {'type': 'string', 'enum': ['YES', 'NO']},
                            'errorMessage': {'type': 'string'},
                            'repoAssessmentStatus': {'type': 'string'},
                            'linesOfCode': {'type': 'number'},
                            'dependencyList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {'id': {'type': 'string'}},
                                    'additionalProperties': False,
                                },
                            },
                            'lastCommitDate': {'type': 'string'},
                            'isRecommended': {'type': 'boolean'},
                            'solutionCount': {'type': 'number'},
                            'projectCount': {'type': 'number'},
                            'selectedSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'availableSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'projectList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'projectLinesOfCode': {'type': 'number'},
                                        'projectVersions': {'type': 'string'},
                                        'projectTypes': {'type': 'string'},
                                        'privateNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                        'publicNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'repoAssessmentReports': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'artifactId': {'type': 'string'},
                                        'artifactType': {
                                            'type': 'number',
                                            'description': 'ArtifactType enum value: 0=XLSX, 1=HTML, 2=ZIP',
                                        },
                                        'artifactReportType': {
                                            'type': 'string',
                                            'enum': ['COMBINED_ASSESSMENT', 'SUMMARY'],
                                        },
                                    },
                                    'required': ['artifactId', 'artifactType'],
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['id', 'name', 'sourceBranch', 'resourceType', 'supported'],
                        'additionalProperties': False,
                    },
                },
                'discoveredResources': {
                    'type': 'array',
                    'description': 'Current set of discovered resources (without complexity fields).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'resourceType': {
                                'type': 'string',
                                'enum': ['REPOSITORY', 'SOLUTION', 'PROJECT'],
                            },
                            'supported': {'type': 'string', 'enum': ['YES', 'NO']},
                            'errorMessage': {'type': 'string'},
                            'repoAssessmentStatus': {'type': 'string'},
                            'linesOfCode': {'type': 'number'},
                            'dependencyList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {'id': {'type': 'string'}},
                                    'additionalProperties': False,
                                },
                            },
                            'lastCommitDate': {'type': 'string'},
                            'isRecommended': {'type': 'boolean'},
                            'solutionCount': {'type': 'number'},
                            'projectCount': {'type': 'number'},
                            'selectedSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'availableSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'projectList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'projectLinesOfCode': {'type': 'number'},
                                        'projectVersions': {'type': 'string'},
                                        'projectTypes': {'type': 'string'},
                                        'privateNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                        'publicNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'repoAssessmentReports': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'artifactId': {'type': 'string'},
                                        'artifactType': {
                                            'type': 'number',
                                            'description': 'ArtifactType enum value: 0=XLSX, 1=HTML, 2=ZIP',
                                        },
                                        'artifactReportType': {
                                            'type': 'string',
                                            'enum': ['COMBINED_ASSESSMENT', 'SUMMARY'],
                                        },
                                    },
                                    'required': ['artifactId', 'artifactType'],
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['id', 'name', 'sourceBranch', 'resourceType', 'supported'],
                        'additionalProperties': False,
                    },
                },
                'selectedTableResources': {
                    'type': 'array',
                    'description': 'Resources the user has selected for transformation (without complexity fields).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'resourceType': {
                                'type': 'string',
                                'enum': ['REPOSITORY', 'SOLUTION', 'PROJECT'],
                            },
                            'supported': {'type': 'string', 'enum': ['YES', 'NO']},
                            'errorMessage': {'type': 'string'},
                            'repoAssessmentStatus': {'type': 'string'},
                            'linesOfCode': {'type': 'number'},
                            'dependencyList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {'id': {'type': 'string'}},
                                    'additionalProperties': False,
                                },
                            },
                            'lastCommitDate': {'type': 'string'},
                            'isRecommended': {'type': 'boolean'},
                            'solutionCount': {'type': 'number'},
                            'projectCount': {'type': 'number'},
                            'selectedSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'availableSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'projectList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'projectLinesOfCode': {'type': 'number'},
                                        'projectVersions': {'type': 'string'},
                                        'projectTypes': {'type': 'string'},
                                        'privateNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                        'publicNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'repoAssessmentReports': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'artifactId': {'type': 'string'},
                                        'artifactType': {
                                            'type': 'number',
                                            'description': 'ArtifactType enum value: 0=XLSX, 1=HTML, 2=ZIP',
                                        },
                                        'artifactReportType': {
                                            'type': 'string',
                                            'enum': ['COMBINED_ASSESSMENT', 'SUMMARY'],
                                        },
                                    },
                                    'required': ['artifactId', 'artifactType'],
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['id', 'name', 'sourceBranch', 'resourceType', 'supported'],
                        'additionalProperties': False,
                    },
                },
                'autoSelectedTableResources': {
                    'type': 'array',
                    'description': 'Resources auto-selected by the system.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'resourceType': {
                                'type': 'string',
                                'enum': ['REPOSITORY', 'SOLUTION', 'PROJECT'],
                            },
                            'supported': {'type': 'string', 'enum': ['YES', 'NO']},
                            'errorMessage': {'type': 'string'},
                            'repoAssessmentStatus': {'type': 'string'},
                            'linesOfCode': {'type': 'number'},
                            'dependencyList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {'id': {'type': 'string'}},
                                    'additionalProperties': False,
                                },
                            },
                            'lastCommitDate': {'type': 'string'},
                            'isRecommended': {'type': 'boolean'},
                            'solutionCount': {'type': 'number'},
                            'projectCount': {'type': 'number'},
                            'selectedSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'availableSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'projectList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'projectLinesOfCode': {'type': 'number'},
                                        'projectVersions': {'type': 'string'},
                                        'projectTypes': {'type': 'string'},
                                        'privateNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                        'publicNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'repoAssessmentReports': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'artifactId': {'type': 'string'},
                                        'artifactType': {
                                            'type': 'number',
                                            'description': 'ArtifactType enum value: 0=XLSX, 1=HTML, 2=ZIP',
                                        },
                                        'artifactReportType': {
                                            'type': 'string',
                                            'enum': ['COMBINED_ASSESSMENT', 'SUMMARY'],
                                        },
                                    },
                                    'required': ['artifactId', 'artifactType'],
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['id', 'name', 'sourceBranch', 'resourceType', 'supported'],
                        'additionalProperties': False,
                    },
                },
                'targetBranchDestination': {'type': 'string'},
                'targetVersion': {
                    'type': 'object',
                    'properties': {'value': {'type': 'string'}, 'label': {'type': 'string'}},
                    'additionalProperties': False,
                },
                'targetVersionOptions': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {'value': {'type': 'string'}, 'label': {'type': 'string'}},
                        'additionalProperties': False,
                    },
                },
                'validationStatus': {
                    'type': 'string',
                    'description': 'Validation status of the file upload flow.',
                },
                'customFileUpload': {
                    'type': 'object',
                    'properties': {
                        'fileName': {'type': 'string'},
                        'lastModified': {'type': 'number'},
                        'size': {'type': 'number'},
                    },
                    'additionalProperties': False,
                },
                'customFileUploadResources': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'resourceType': {
                                'type': 'string',
                                'enum': ['REPOSITORY', 'SOLUTION', 'PROJECT'],
                            },
                            'supported': {'type': 'string', 'enum': ['YES', 'NO']},
                            'errorMessage': {'type': 'string'},
                            'repoAssessmentStatus': {'type': 'string'},
                            'linesOfCode': {'type': 'number'},
                            'dependencyList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {'id': {'type': 'string'}},
                                    'additionalProperties': False,
                                },
                            },
                            'lastCommitDate': {'type': 'string'},
                            'isRecommended': {'type': 'boolean'},
                            'solutionCount': {'type': 'number'},
                            'projectCount': {'type': 'number'},
                            'selectedSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'availableSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'projectList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'projectLinesOfCode': {'type': 'number'},
                                        'projectVersions': {'type': 'string'},
                                        'projectTypes': {'type': 'string'},
                                        'privateNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                        'publicNugetPackage': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'repoAssessmentReports': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'artifactId': {'type': 'string'},
                                        'artifactType': {
                                            'type': 'number',
                                            'description': 'ArtifactType enum value: 0=XLSX, 1=HTML, 2=ZIP',
                                        },
                                        'artifactReportType': {
                                            'type': 'string',
                                            'enum': ['COMBINED_ASSESSMENT', 'SUMMARY'],
                                        },
                                    },
                                    'required': ['artifactId', 'artifactType'],
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['id', 'name', 'sourceBranch', 'resourceType', 'supported'],
                        'additionalProperties': False,
                    },
                },
                'errorMessage': {'type': 'string'},
                'targetBranchErrorMessage': {'type': 'string'},
                'targetVersionErrorMessage': {'type': 'string'},
                'enableBlazorViews': {'type': 'boolean'},
                'enableRazorViews': {'type': 'boolean'},
                'excludePortNetStandard': {'type': 'boolean'},
                'hasAssessmentErrors': {'type': 'boolean'},
                'isReadonly': {'type': 'boolean'},
                'totalUniqueRepos': {'type': 'number'},
                'retryOption': {
                    'type': 'string',
                    'enum': ['DISCOVERY', 'ASSESSMENT', 'UPLOAD_MISSING_NUGET'],
                    'description': 'Retry action selected by the user.',
                },
                'serviceQuotaLimits': {
                    'type': 'object',
                    'properties': {
                        'repoCountMonthlyConsumed': {'type': 'number'},
                        'repoCountMonthlyLimit': {'type': 'number'},
                        'locCountMonthlyConsumed': {'type': 'number'},
                        'locCountMonthlyLimit': {'type': 'number'},
                        'locCountTotalConsumed': {'type': 'number'},
                        'locCountTotalLimit': {'type': 'number'},
                        'createdAt': {'type': 'number'},
                    },
                    'required': [
                        'repoCountMonthlyConsumed',
                        'repoCountMonthlyLimit',
                        'locCountMonthlyConsumed',
                        'locCountMonthlyLimit',
                        'locCountTotalConsumed',
                        'locCountTotalLimit',
                        'createdAt',
                    ],
                    'additionalProperties': False,
                },
                'jobAssessmentReports': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'artifactId': {'type': 'string'},
                            'artifactType': {
                                'type': 'number',
                                'description': 'ArtifactType enum value: 0=XLSX, 1=HTML, 2=ZIP',
                            },
                            'artifactReportType': {
                                'type': 'string',
                                'enum': ['COMBINED_ASSESSMENT', 'SUMMARY'],
                            },
                        },
                        'required': ['artifactId', 'artifactType'],
                        'additionalProperties': False,
                    },
                },
                'combinedAssessmentReports': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'artifactId': {'type': 'string'},
                            'artifactType': {
                                'type': 'number',
                                'description': 'ArtifactType enum value: 0=XLSX, 1=HTML, 2=ZIP',
                            },
                            'artifactReportType': {
                                'type': 'string',
                                'enum': ['COMBINED_ASSESSMENT', 'SUMMARY'],
                            },
                        },
                        'required': ['artifactId', 'artifactType'],
                        'additionalProperties': False,
                    },
                },
            },
            'required': ['selectedTableResources', 'serviceQuotaLimits'],
            'additionalProperties': True,
        },
    ),
    'DotnetDeploymentAutomationOptions': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'configType': 'PROVISION'},
            {'nextHITL': True, 'configType': 'PROVISION'},
            {'configType': 'SKIP'},
            {'closeJobAndQuit': True},
        ],
        json_schema={
            'title': 'DotnetDeploymentAutomationOptions Output',
            'description': 'Output schema for DotnetDeploymentAutomationOptions. Emitted when the user selects a configuration type (PROVISION, SKIP, etc.) and clicks Next, or when closing the job, or when going back from the skip-complete view.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'configType': 'PROVISION'},
                {'nextHITL': True, 'configType': 'PROVISION'},
                {'configType': 'SKIP'},
                {'closeJobAndQuit': True},
            ],
            'properties': {
                'configType': {
                    'type': 'string',
                    'description': 'The deployment automation configuration type selected by the user.',
                    'examples': ['PROVISION', 'SKIP', 'COMMIT'],
                },
                'nextHITL': {
                    'type': 'boolean',
                    'description': 'Set to true when the user clicks Next and configType is not SKIP, signaling to advance to the next HITL step.',
                },
                'closeJobAndQuit': {
                    'type': 'boolean',
                    'description': 'Set to true when the user confirms closing and quitting the job.',
                },
            },
            'additionalProperties': True,
        },
    ),
    'DotnetDiscoveredRepoSelector': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=True,
        examples=[
            {
                'userSelectionType': 'TABLE',
                'discoveredResources': [
                    {'id': 'repo-1', 'name': 'my-service', 'sourceBranch': 'main'},
                    {'id': 'repo-2', 'name': 'another-service', 'sourceBranch': 'develop'},
                ],
                'selectedTableResources': [
                    {'id': 'repo-1', 'name': 'my-service', 'sourceBranch': 'main'}
                ],
                'fileValidationStatus': 'NOT_STARTED',
                'fileValidationErrorMessage': '',
                'customFileUpload': None,
                'customFileUploadResources': [],
                'bulkSelection': 'ALL',
            },
            {
                'userSelectionType': 'FILE',
                'discoveredResources': [],
                'selectedTableResources': [
                    {
                        'id': 'repo-3',
                        'name': 'external-repo',
                        'sourceBranch': 'main',
                        'repoValidationStatus': 'VALID',
                    }
                ],
                'fileValidationStatus': 'IN_PROGRESS',
                'fileValidationErrorMessage': '',
                'customFileUpload': {
                    'fileName': 'repos.json',
                    'lastModified': 1700000000000,
                    'size': 512,
                },
                'customFileUploadResources': [
                    {
                        'id': 'repo-3',
                        'name': 'external-repo',
                        'sourceBranch': 'main',
                        'repoValidationStatus': 'NOT_VALIDATED',
                    }
                ],
                'bulkSelection': 'ALL',
            },
        ],
        json_schema={
            'title': 'DotnetDiscoveredRepoSelector Output',
            'description': 'Output schema for DotnetDiscoveredRepoSelector. Continuously emitted as the user selects discovered repos from a table or uploads a CSV/JSON file. Also emitted with a retryOption when the user triggers a retry.',
            'displayOnly': False,
            'mergeWithArtifact': True,
            'type': 'object',
            'examples': [
                {
                    'userSelectionType': 'TABLE',
                    'discoveredResources': [
                        {'id': 'repo-1', 'name': 'my-service', 'sourceBranch': 'main'},
                        {'id': 'repo-2', 'name': 'another-service', 'sourceBranch': 'develop'},
                    ],
                    'selectedTableResources': [
                        {'id': 'repo-1', 'name': 'my-service', 'sourceBranch': 'main'}
                    ],
                    'fileValidationStatus': 'NOT_STARTED',
                    'fileValidationErrorMessage': '',
                    'customFileUpload': None,
                    'customFileUploadResources': [],
                    'bulkSelection': 'ALL',
                },
                {
                    'userSelectionType': 'FILE',
                    'discoveredResources': [],
                    'selectedTableResources': [
                        {
                            'id': 'repo-3',
                            'name': 'external-repo',
                            'sourceBranch': 'main',
                            'repoValidationStatus': 'VALID',
                        }
                    ],
                    'fileValidationStatus': 'IN_PROGRESS',
                    'fileValidationErrorMessage': '',
                    'customFileUpload': {
                        'fileName': 'repos.json',
                        'lastModified': 1700000000000,
                        'size': 512,
                    },
                    'customFileUploadResources': [
                        {
                            'id': 'repo-3',
                            'name': 'external-repo',
                            'sourceBranch': 'main',
                            'repoValidationStatus': 'NOT_VALIDATED',
                        }
                    ],
                    'bulkSelection': 'ALL',
                },
            ],
            'properties': {
                'userSelectionType': {
                    'type': 'string',
                    'enum': ['TABLE', 'FILE'],
                    'description': 'Whether the user is selecting repos from the discovered table or via file upload.',
                },
                'discoveredResources': {
                    'type': 'array',
                    'description': 'All discovered repositories from the agent.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'repoValidationStatus': {
                                'type': 'string',
                                'enum': [
                                    'NOT_STARTED',
                                    'IN_PROGRESS',
                                    'VALID',
                                    'INVALID',
                                    'NOT_VALIDATED',
                                ],
                            },
                            'repoValidationMessage': {'type': 'string'},
                        },
                        'required': ['id', 'name', 'sourceBranch'],
                        'additionalProperties': False,
                    },
                },
                'selectedTableResources': {
                    'type': 'array',
                    'description': 'Repositories the user has selected (either from the table or parsed from the uploaded file).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'repoValidationStatus': {
                                'type': 'string',
                                'enum': [
                                    'NOT_STARTED',
                                    'IN_PROGRESS',
                                    'VALID',
                                    'INVALID',
                                    'NOT_VALIDATED',
                                ],
                            },
                            'repoValidationMessage': {'type': 'string'},
                        },
                        'required': ['id', 'name', 'sourceBranch'],
                        'additionalProperties': False,
                    },
                },
                'fileValidationStatus': {
                    'type': 'string',
                    'enum': ['NOT_STARTED', 'IN_PROGRESS', 'SUCCEEDED', 'FAILED'],
                    'description': 'Status of the file validation when using file upload mode.',
                },
                'fileValidationErrorMessage': {
                    'type': 'string',
                    'description': 'Error message if file validation failed.',
                },
                'customFileUpload': {
                    'description': 'Metadata of the uploaded file, or null if no file uploaded.',
                    'oneOf': [
                        {
                            'type': 'object',
                            'properties': {
                                'fileName': {'type': 'string'},
                                'lastModified': {'type': 'number'},
                                'size': {'type': 'number'},
                            },
                            'required': ['fileName', 'lastModified', 'size'],
                            'additionalProperties': False,
                        },
                        {'type': 'null'},
                    ],
                },
                'customFileUploadResources': {
                    'type': 'array',
                    'description': 'Resources parsed from the uploaded file.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'repoValidationStatus': {
                                'type': 'string',
                                'enum': [
                                    'NOT_STARTED',
                                    'IN_PROGRESS',
                                    'VALID',
                                    'INVALID',
                                    'NOT_VALIDATED',
                                ],
                            },
                            'repoValidationMessage': {'type': 'string'},
                        },
                        'required': ['id', 'name', 'sourceBranch'],
                        'additionalProperties': False,
                    },
                },
                'bulkSelection': {
                    'type': 'string',
                    'enum': ['ALL', 'NONE'],
                    'description': 'Whether the user has bulk-selected all or none of the table rows.',
                },
                'retryOption': {
                    'type': 'string',
                    'enum': ['DISCOVERY'],
                    'description': 'Retry action selected by the user.',
                },
            },
            'required': [
                'userSelectionType',
                'discoveredResources',
                'selectedTableResources',
                'fileValidationStatus',
                'fileValidationErrorMessage',
                'customFileUploadResources',
                'bulkSelection',
            ],
            'additionalProperties': True,
        },
    ),
    'DotnetMissingPackages': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedArtifactIds': [
                    {
                        'artifactId': 'artifact-uuid-1234',
                        'name': 'Newtonsoft.Json.13.0.3.nupkg',
                        'lastModified': 1700000000000,
                        'size': 724512,
                    }
                ]
            },
            {'removedPackages': [{'name': 'SomePrivatePackage', 'version': '1.2.3'}]},
        ],
        json_schema={
            'title': 'DotnetMissingPackages Output',
            'description': 'Output schema for DotnetMissingPackages. Emitted in three scenarios: (1) user uploads NuGet package files (uploadedArtifactIds), (2) user removes packages (removedPackages), or (3) a refresh-only action (neither field present).',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedArtifactIds': [
                        {
                            'artifactId': 'artifact-uuid-1234',
                            'name': 'Newtonsoft.Json.13.0.3.nupkg',
                            'lastModified': 1700000000000,
                            'size': 724512,
                        }
                    ]
                },
                {'removedPackages': [{'name': 'SomePrivatePackage', 'version': '1.2.3'}]},
            ],
            'properties': {
                'uploadedArtifactIds': {
                    'type': 'array',
                    'description': 'Metadata for uploaded NuGet package artifacts. Present when the user uploads package files.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'artifactId': {
                                'type': 'string',
                                'description': 'The artifact ID returned from the upload handler.',
                            },
                            'name': {
                                'type': 'string',
                                'description': 'Original filename of the uploaded package.',
                            },
                            'lastModified': {
                                'type': 'number',
                                'description': 'Last modified timestamp in milliseconds.',
                            },
                            'size': {'type': 'number', 'description': 'File size in bytes.'},
                        },
                        'required': ['artifactId', 'name', 'lastModified', 'size'],
                        'additionalProperties': False,
                    },
                },
                'removedPackages': {
                    'type': 'array',
                    'description': 'Packages the user has chosen to remove from the missing packages list.',
                    'items': {
                        'type': 'object',
                        'properties': {'name': {'type': 'string'}, 'version': {'type': 'string'}},
                        'required': ['name'],
                        'additionalProperties': True,
                    },
                },
            },
            'additionalProperties': True,
        },
    ),
    'DotnetPostTransformationError': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'errorType': 'BUILD_ERROR', 'resolved': True},
            {'errorType': 'UT_ERROR', 'resolved': True},
        ],
        json_schema={
            'title': 'DotnetPostTransformationError Output',
            'description': 'Output schema for DotnetPostTransformationError. Automatically emitted on mount with the error type and a resolved flag. The user confirms by clicking the submit button.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'errorType': 'BUILD_ERROR', 'resolved': True},
                {'errorType': 'UT_ERROR', 'resolved': True},
            ],
            'properties': {
                'errorType': {
                    'type': 'string',
                    'description': 'The type of post-transformation error that occurred.',
                    'examples': ['BUILD_ERROR', 'UT_ERROR'],
                },
                'resolved': {
                    'type': 'boolean',
                    'description': 'Always true — automatically set to indicate the HITL has been acknowledged.',
                    'enum': [True],
                },
            },
            'required': ['resolved'],
            'additionalProperties': True,
        },
    ),
    'DotnetProvisionApplication': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=True,
        examples=[
            {
                'deployableApplications': [
                    {
                        'id': 'my-repo_MySolution_MyApp',
                        'projectAssemblyName': 'MyApp',
                        'repositoryName': 'my-repo',
                        'solutionName': 'MySolution',
                        'projectParameterStatus': 'CONFIGURED_AND_COMMITTED',
                        'projectProvisionStatus': 'IN_PROGRESS',
                        'commitToGit': True,
                        'provision': True,
                        'infraParameters': {
                            'deploymentType': 'EC2',
                            'instanceName': 'AWSTransform-MyApp',
                            'instanceType': 't3.medium',
                            'amiID': 'ami-0abcdef1234567890',
                            'subnetID': 'subnet-0123456789abcdef0',
                            'securityGroupID': 'sg-0123456789abcdef0',
                            'storageSize': '50',
                        },
                    }
                ]
            },
            {'closeJobAndQuit': True, 'deployableApplications': []},
        ],
        json_schema={
            'title': 'DotnetProvisionApplication Output',
            'description': 'Output schema for DotnetProvisionApplication. Emitted when the user selects applications for provisioning, configures infra parameters, or closes the job. Builds up application state across multiple parameter-save and provision interactions.',
            'displayOnly': False,
            'mergeWithArtifact': True,
            'type': 'object',
            'examples': [
                {
                    'deployableApplications': [
                        {
                            'id': 'my-repo_MySolution_MyApp',
                            'projectAssemblyName': 'MyApp',
                            'repositoryName': 'my-repo',
                            'solutionName': 'MySolution',
                            'projectParameterStatus': 'CONFIGURED_AND_COMMITTED',
                            'projectProvisionStatus': 'IN_PROGRESS',
                            'commitToGit': True,
                            'provision': True,
                            'infraParameters': {
                                'deploymentType': 'EC2',
                                'instanceName': 'AWSTransform-MyApp',
                                'instanceType': 't3.medium',
                                'amiID': 'ami-0abcdef1234567890',
                                'subnetID': 'subnet-0123456789abcdef0',
                                'securityGroupID': 'sg-0123456789abcdef0',
                                'storageSize': '50',
                            },
                        }
                    ]
                },
                {'closeJobAndQuit': True, 'deployableApplications': []},
            ],
            'properties': {
                'deployableApplications': {
                    'type': 'array',
                    'description': 'All deployable application items with updated provision flags, parameter statuses, and infra parameters.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {
                                'type': 'string',
                                'description': 'Composite key: {repositoryName}_{solutionName}_{projectAssemblyName}',
                            },
                            'projectAssemblyName': {'type': 'string'},
                            'repositoryName': {'type': 'string'},
                            'solutionName': {'type': 'string'},
                            'projectParameterStatus': {
                                'type': 'string',
                                'enum': [
                                    'NOT_CONFIGURED',
                                    'CONFIGURED',
                                    'CONFIGURED_AND_COMMITTED',
                                    'READY_TO_COMMIT',
                                    'IN_PROGRESS',
                                    'FAILED',
                                ],
                            },
                            'projectProvisionStatus': {
                                'type': 'string',
                                'enum': [
                                    'NOT_COMPLETED',
                                    'NOT_PROVISIONED',
                                    'IN_PROGRESS',
                                    'FAILED',
                                    'PROVISIONED',
                                    'DEPLOYED',
                                    'ATTENTION_REQUIRED',
                                    'BUILDING_APPLICATION',
                                    'DEPLOYING_APPLICATION',
                                    'BUILD_FAILED_INFRASTRUCTURE_PROVISIONED',
                                    'BUILD_SUCCEEDED_INFRASTRUCTURE_FAILED',
                                ],
                            },
                            'commitToGit': {'type': 'boolean'},
                            'provision': {
                                'type': 'boolean',
                                'description': 'True if this application was selected for provisioning.',
                            },
                            'repositoryNoOfDependencies': {'type': 'number'},
                            'repositoryDependencyList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'string'},
                                        'name': {'type': 'string'},
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'infraParameters': {
                                'type': 'object',
                                'properties': {
                                    'deploymentType': {
                                        'type': 'string',
                                        'enum': ['ECS', 'EC2', 'EB'],
                                    },
                                    'subnetID': {'type': 'string'},
                                    'securityGroupID': {'type': 'string'},
                                    'amiID': {'type': 'string'},
                                    'instanceType': {'type': 'string'},
                                    'storageSize': {'type': 'string'},
                                    'clusterName': {'type': 'string'},
                                    'cpuOptions': {'type': 'string'},
                                    'memory': {'type': 'string'},
                                    'diskSize': {'type': 'string'},
                                    'ecrImage': {'type': 'string'},
                                    'ecrURI': {'type': 'string'},
                                    'instanceName': {'type': 'string'},
                                    'ebEnvironmentName': {'type': 'string'},
                                    'kmsKeyArn': {'type': 'string'},
                                    'kmsInvalid': {'type': 'boolean'},
                                    'scale': {'type': 'string'},
                                    'publicSubnetsForALB': {'type': 'string'},
                                    'publicSubnetIds': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                    },
                                    'acmArnForALB': {'type': 'string'},
                                    'acmArnsOnAccount': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                    },
                                },
                                'additionalProperties': False,
                            },
                            'instanceID': {'type': 'string'},
                            'clusterID': {'type': 'string'},
                            'connectionLink': {'type': 'string'},
                            'databaseName': {'type': 'string'},
                            'error': {
                                'type': 'object',
                                'properties': {
                                    'errorMessage': {'type': 'string'},
                                    'errorDetails': {'type': 'string'},
                                    'errorFix': {'type': 'string'},
                                },
                                'additionalProperties': False,
                            },
                        },
                        'required': ['id', 'projectAssemblyName'],
                        'additionalProperties': False,
                    },
                },
                'closeJobAndQuit': {
                    'type': 'boolean',
                    'description': 'Set to true when the user confirms closing the job and quitting.',
                },
            },
            'required': ['deployableApplications'],
            'additionalProperties': True,
        },
    ),
    'DotnetRepositoryAccessError': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'error': 'INSUFFICIENT_PERMISSIONS', 'resolved': True},
            {'error': 'INSUFFICIENT_PR_PERMISSIONS', 'resolved': True},
            {'error': 'INVALID_CREDENTIALS', 'resolved': True},
            {'error': 'INVALID_ZIP_STRUCTURE', 'resolved': True},
        ],
        json_schema={
            'title': 'DotnetRepositoryAccessError Output',
            'description': 'Output schema for DotnetRepositoryAccessError. Automatically emitted on mount with the error code and a resolved flag. This component presents an error message; the user confirms by clicking the submit button.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'error': 'INSUFFICIENT_PERMISSIONS', 'resolved': True},
                {'error': 'INSUFFICIENT_PR_PERMISSIONS', 'resolved': True},
                {'error': 'INVALID_CREDENTIALS', 'resolved': True},
                {'error': 'INVALID_ZIP_STRUCTURE', 'resolved': True},
            ],
            'properties': {
                'error': {
                    'type': 'string',
                    'description': 'The error code describing what repository access problem occurred.',
                    'examples': [
                        'INSUFFICIENT_PERMISSIONS',
                        'INVALID_CREDENTIALS',
                        'INSUFFICIENT_PR_PERMISSIONS',
                        'INSUFFICIENT_CLONE_PERMISSIONS',
                        'INVALID_ZIP_STRUCTURE',
                        'INSUFFICIENT_PERMISSIONS_S3',
                    ],
                },
                'resolved': {
                    'type': 'boolean',
                    'description': 'Always true — automatically set to indicate the error has been acknowledged.',
                    'enum': [True],
                },
            },
            'required': ['resolved'],
            'additionalProperties': True,
        },
    ),
    'DotnetResourceSelector': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'userSelectionType': 'TABLE',
                'targetBranchDestination': 'main',
                'targetVersion': {'label': '.NET 8', 'value': 'net8.0'},
                'selectedTableResources': [
                    {
                        'id': 'repo-abc',
                        'name': 'my-dotnet-repo',
                        'sourceBranch': 'main',
                        'supported': 'YES',
                    }
                ],
            },
            {
                'userSelectionType': 'FILE',
                'targetBranchDestination': 'main',
                'targetVersion': {'label': '.NET 8', 'value': 'net8.0'},
                'customFileUploadResources': [
                    {
                        'id': 'repo-xyz',
                        'name': 'another-repo',
                        'sourceBranch': 'develop',
                        'supported': 'YES',
                    }
                ],
                'customFileUpload': {
                    'fileName': 'repositories.json',
                    'lastModified': 1700000000000,
                    'size': 1024,
                },
            },
        ],
        json_schema={
            'title': 'DotnetResourceSelector Output',
            'description': 'Output schema for DotnetResourceSelector. Continuously emitted as the user selects repositories from a table or uploads a custom file, along with the target branch and version.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'userSelectionType': 'TABLE',
                    'targetBranchDestination': 'main',
                    'targetVersion': {'label': '.NET 8', 'value': 'net8.0'},
                    'selectedTableResources': [
                        {
                            'id': 'repo-abc',
                            'name': 'my-dotnet-repo',
                            'sourceBranch': 'main',
                            'supported': 'YES',
                        }
                    ],
                },
                {
                    'userSelectionType': 'FILE',
                    'targetBranchDestination': 'main',
                    'targetVersion': {'label': '.NET 8', 'value': 'net8.0'},
                    'customFileUploadResources': [
                        {
                            'id': 'repo-xyz',
                            'name': 'another-repo',
                            'sourceBranch': 'develop',
                            'supported': 'YES',
                        }
                    ],
                    'customFileUpload': {
                        'fileName': 'repositories.json',
                        'lastModified': 1700000000000,
                        'size': 1024,
                    },
                },
            ],
            'properties': {
                'userSelectionType': {
                    'type': 'string',
                    'enum': ['TABLE', 'FILE'],
                    'description': 'Whether the user selected repositories via the table UI or a custom uploaded file.',
                },
                'targetBranchDestination': {
                    'type': 'string',
                    'description': 'The target branch where transformed code will be committed.',
                },
                'targetVersion': {
                    'type': 'object',
                    'description': 'The selected .NET target version option.',
                    'properties': {'label': {'type': 'string'}, 'value': {'type': 'string'}},
                    'additionalProperties': False,
                },
                'selectedTableResources': {
                    'type': 'array',
                    'description': 'Resources selected from the table (present when userSelectionType is TABLE).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'supported': {'type': 'string', 'enum': ['YES', 'NO']},
                            'errorMessage': {'type': 'string'},
                            'solutionCount': {'type': 'number'},
                            'projectCount': {'type': 'number'},
                            'selectedSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'projectList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'linesOfCode': {'type': 'number'},
                                        'versions': {'type': 'string'},
                                        'types': {'type': 'string'},
                                        'privateNugetPackages': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                        'publicNugetPackages': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                    },
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['id', 'name', 'sourceBranch'],
                        'additionalProperties': True,
                    },
                },
                'customFileUploadResources': {
                    'type': 'array',
                    'description': 'Resources parsed from the uploaded file (present when userSelectionType is FILE).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'sourceBranchOptions': {'type': 'array', 'items': {'type': 'string'}},
                            'supported': {'type': 'string', 'enum': ['YES', 'NO']},
                            'errorMessage': {'type': 'string'},
                            'solutionCount': {'type': 'number'},
                            'projectCount': {'type': 'number'},
                            'selectedSolutions': {'type': 'array', 'items': {'type': 'string'}},
                            'projectList': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'linesOfCode': {'type': 'number'},
                                        'versions': {'type': 'string'},
                                        'types': {'type': 'string'},
                                        'privateNugetPackages': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                        'publicNugetPackages': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'number'}},
                                            'additionalProperties': False,
                                        },
                                    },
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['id', 'name', 'sourceBranch'],
                        'additionalProperties': True,
                    },
                },
                'customFileUpload': {
                    'type': 'object',
                    'description': 'Metadata about the uploaded file (present when userSelectionType is FILE).',
                    'properties': {
                        'fileName': {'type': 'string'},
                        'lastModified': {'type': 'number'},
                        'size': {'type': 'number'},
                    },
                    'additionalProperties': False,
                },
            },
            'required': ['userSelectionType', 'targetBranchDestination', 'targetVersion'],
            'additionalProperties': True,
        },
    ),
    'DotnetReviewAndConfirm': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'jobSummary': {
                    'targetBranch': 'transform/net8-migration',
                    'targetVersion': 'net8.0',
                    'excludeStandardProjects': 'NO',
                    'numSelectedRepos': 2,
                    'numDependentRepos': 1,
                    'numPrivatePackages': 3,
                    'totalLoc': 45000,
                },
                'selectedRepos': [
                    {
                        'name': 'my-service',
                        'sourceBranch': 'main',
                        'supportedProjects': 'YES',
                        'loc': 20000,
                        'numDetectedProjects': 4,
                        'numSkippedProjects': 0,
                        'numDetectedDependencies': 2,
                    }
                ],
                'repoDependencies': [
                    {
                        'name': 'shared-lib',
                        'dependentRepos': ['my-service'],
                        'sourceBranch': 'main',
                        'supportedProjects': 'YES',
                        'loc': 5000,
                        'numDetectedProjects': 1,
                        'numSkippedProjects': 0,
                    }
                ],
                'packageDependencies': [
                    {
                        'name': 'Newtonsoft.Json',
                        'numDependentRepos': 2,
                        'frameworkStatus': 'SUCCESS',
                        'coreStatus': 'SUCCESS',
                    }
                ],
            }
        ],
        json_schema={
            'title': 'DotnetReviewAndConfirm Output',
            'description': "Output schema for DotnetReviewAndConfirm. Emitted on mount and whenever the job summary, selected repos, repo dependencies, or package dependencies change. Mirrors the agent artifact back so the agent can read the user's confirmed selections.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'jobSummary': {
                        'targetBranch': 'transform/net8-migration',
                        'targetVersion': 'net8.0',
                        'excludeStandardProjects': 'NO',
                        'numSelectedRepos': 2,
                        'numDependentRepos': 1,
                        'numPrivatePackages': 3,
                        'totalLoc': 45000,
                    },
                    'selectedRepos': [
                        {
                            'name': 'my-service',
                            'sourceBranch': 'main',
                            'supportedProjects': 'YES',
                            'loc': 20000,
                            'numDetectedProjects': 4,
                            'numSkippedProjects': 0,
                            'numDetectedDependencies': 2,
                        }
                    ],
                    'repoDependencies': [
                        {
                            'name': 'shared-lib',
                            'dependentRepos': ['my-service'],
                            'sourceBranch': 'main',
                            'supportedProjects': 'YES',
                            'loc': 5000,
                            'numDetectedProjects': 1,
                            'numSkippedProjects': 0,
                        }
                    ],
                    'packageDependencies': [
                        {
                            'name': 'Newtonsoft.Json',
                            'numDependentRepos': 2,
                            'frameworkStatus': 'SUCCESS',
                            'coreStatus': 'SUCCESS',
                        }
                    ],
                }
            ],
            'properties': {
                'jobSummary': {
                    'type': 'object',
                    'description': 'High-level summary of the transformation job.',
                    'properties': {
                        'targetBranch': {'type': 'string'},
                        'targetVersion': {'type': 'string'},
                        'excludeStandardProjects': {'type': 'string', 'enum': ['YES', 'NO']},
                        'numSelectedRepos': {'type': 'number'},
                        'numDependentRepos': {'type': 'number'},
                        'numPrivatePackages': {'type': 'number'},
                        'totalLoc': {'type': 'number'},
                    },
                    'required': [
                        'targetBranch',
                        'targetVersion',
                        'excludeStandardProjects',
                        'numSelectedRepos',
                        'numDependentRepos',
                        'numPrivatePackages',
                        'totalLoc',
                    ],
                    'additionalProperties': False,
                },
                'selectedRepos': {
                    'type': 'array',
                    'description': 'Repositories the user has selected for transformation.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'sourceBranch': {'type': 'string'},
                            'supportedProjects': {'type': 'string', 'enum': ['YES', 'NO']},
                            'loc': {'type': 'number'},
                            'numDetectedProjects': {'type': 'number'},
                            'numSkippedProjects': {'type': 'number'},
                            'numDetectedDependencies': {'type': 'number'},
                        },
                        'required': [
                            'name',
                            'sourceBranch',
                            'supportedProjects',
                            'loc',
                            'numDetectedProjects',
                            'numSkippedProjects',
                            'numDetectedDependencies',
                        ],
                        'additionalProperties': False,
                    },
                },
                'repoDependencies': {
                    'type': 'array',
                    'description': 'Repositories that are dependencies of the selected repos.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'dependentRepos': {'type': 'array', 'items': {'type': 'string'}},
                            'sourceBranch': {'type': 'string'},
                            'supportedProjects': {'type': 'string', 'enum': ['YES', 'NO']},
                            'loc': {'type': 'number'},
                            'numDetectedProjects': {'type': 'number'},
                            'numSkippedProjects': {'type': 'number'},
                        },
                        'required': [
                            'name',
                            'dependentRepos',
                            'sourceBranch',
                            'supportedProjects',
                            'loc',
                            'numDetectedProjects',
                            'numSkippedProjects',
                        ],
                        'additionalProperties': False,
                    },
                },
                'packageDependencies': {
                    'type': 'array',
                    'description': 'NuGet package dependencies detected across selected repos.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'numDependentRepos': {'type': 'number'},
                            'frameworkStatus': {
                                'type': 'string',
                                'enum': ['MISSING', 'VALIDATION_FAILED', 'SUCCESS'],
                            },
                            'coreStatus': {
                                'type': 'string',
                                'enum': ['MISSING', 'VALIDATION_FAILED', 'SUCCESS'],
                            },
                        },
                        'required': ['name', 'numDependentRepos', 'frameworkStatus', 'coreStatus'],
                        'additionalProperties': False,
                    },
                },
                'retryOption': {
                    'type': 'string',
                    'enum': ['DISCOVERY', 'ASSESSMENT', 'UPLOAD_MISSING_NUGET'],
                    'description': 'Retry action selected from the job summary actions dropdown.',
                },
            },
            'required': ['jobSummary', 'selectedRepos', 'repoDependencies', 'packageDependencies'],
            'additionalProperties': True,
        },
    ),
    'DotnetSetUpInfra': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'selectedOption': 'CREATE',
                's3Bucket': '',
                'selectedRegion': 'us-west-2',
                'kmsARN': '',
            },
            {
                'selectedOption': 'EXISTING',
                's3Bucket': 'arn:aws:s3:::my-transform-bucket',
                'selectedRegion': 'us-east-1',
                'kmsARN': 'arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-ab12-ab12-abcdef123456',
            },
        ],
        json_schema={
            'title': 'DotnetSetUpInfra Output',
            'description': 'Output schema for DotnetSetUpInfra. Continuously emitted as the user fills in S3, region, and KMS ARN fields for infrastructure setup.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'selectedOption': 'CREATE',
                    's3Bucket': '',
                    'selectedRegion': 'us-west-2',
                    'kmsARN': '',
                },
                {
                    'selectedOption': 'EXISTING',
                    's3Bucket': 'arn:aws:s3:::my-transform-bucket',
                    'selectedRegion': 'us-east-1',
                    'kmsARN': 'arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-ab12-ab12-abcdef123456',
                },
            ],
            'properties': {
                'selectedOption': {
                    'type': 'string',
                    'description': "Whether to use an existing or new S3 bucket. Values: 'EXISTING' or 'CREATE'.",
                    'examples': ['EXISTING', 'CREATE'],
                },
                's3Bucket': {
                    'type': 'string',
                    'description': 'ARN of the existing S3 bucket (when selectedOption is EXISTING), e.g. arn:aws:s3:::my-bucket.',
                },
                'selectedRegion': {
                    'type': 'string',
                    'description': "AWS region value selected by the user, e.g. 'us-east-1'.",
                },
                'kmsARN': {
                    'type': 'string',
                    'description': 'Optional KMS key ARN for encryption, e.g. arn:aws:kms:us-east-1:123456789012:key/...',
                },
            },
            'required': ['selectedOption', 's3Bucket', 'selectedRegion', 'kmsARN'],
            'additionalProperties': True,
        },
    ),
    'DownloadAndDeployNetworks': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'DownloadAndDeployNetworks Output',
            'description': 'Output schema for DownloadAndDeployNetworks. Display-only component that surfaces S3 URLs for network deployment templates (CloudFormation, CDK, Terraform, LZA). No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'DynamicHITLRenderEngine': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'migrationStrategyField': 'rehost',
                'notesField': 'Standard lift-and-shift migration.',
                'attachmentField': [
                    {
                        'name': 'architecture.zip',
                        'content': '<base64-encoded-content>',
                        'isZip': True,
                    }
                ],
            }
        ],
        json_schema={
            'title': 'DynamicHITLRenderEngine Output',
            'description': 'Output schema for DynamicHITLRenderEngine. Renders a dynamic UI tree from a JSON DOM spec. Each interactive atom (TextInput, Textarea, RadioGroup, FileUpload) reports its value keyed by fieldId into a shared state object that is emitted via onInputChange. The shape of the output is therefore fully determined by the domTreeJson prop at runtime.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'migrationStrategyField': 'rehost',
                    'notesField': 'Standard lift-and-shift migration.',
                    'attachmentField': [
                        {
                            'name': 'architecture.zip',
                            'content': '<base64-encoded-content>',
                            'isZip': True,
                        }
                    ],
                }
            ],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'EBACandidateApplicationList': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'selectedApplication': {
                    'order': 1,
                    'name': 'PayrollService',
                    'businessCriticality': 'High',
                    'selected': True,
                }
            }
        ],
        json_schema={
            'title': 'EBACandidateApplicationList Output',
            'description': "Output schema for EBACandidateApplicationList. Emits the user's selected application for deep assessment, or null if deselected.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'selectedApplication': {
                        'order': 1,
                        'name': 'PayrollService',
                        'businessCriticality': 'High',
                        'selected': True,
                    }
                }
            ],
            'properties': {
                'selectedApplication': {
                    'oneOf': [
                        {
                            'type': 'object',
                            'description': 'CandidateItem selected by the user',
                            'properties': {
                                'order': {
                                    'type': 'number',
                                    'description': 'Display order of the application',
                                },
                                'name': {'type': 'string', 'description': 'Application name'},
                                'businessCriticality': {
                                    'type': 'string',
                                    'description': 'Business criticality label',
                                },
                                'selected': {
                                    'type': 'boolean',
                                    'description': 'Whether the item is selected',
                                },
                            },
                            'required': ['order', 'name', 'businessCriticality'],
                            'additionalProperties': True,
                        },
                        {'type': 'null', 'description': 'No application selected'},
                    ]
                }
            },
            'required': ['selectedApplication'],
            'additionalProperties': True,
        },
    ),
    'EBADownloadExecutionPlan': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'EBADownloadExecutionPlan Output',
            'description': 'Output schema for EBADownloadExecutionPlan component. This is a display-only component that does not produce output data.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'EBAModernizationPathways': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'selectedPathways': [
                    {
                        'id': 'rehost',
                        'title': 'Rehost to EC2',
                        'description': 'Lift and shift to EC2',
                        'levelOfEffort': {'text': 'Low', 'severity': 'low'},
                        'businessOutcome': {'text': 'Reduced on-prem costs'},
                        'selected': True,
                    }
                ]
            }
        ],
        json_schema={
            'title': 'EBAModernizationPathways Output',
            'description': 'Output schema for EBAModernizationPathways component containing user-selected modernization pathways',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'selectedPathways': [
                        {
                            'id': 'rehost',
                            'title': 'Rehost to EC2',
                            'description': 'Lift and shift to EC2',
                            'levelOfEffort': {'text': 'Low', 'severity': 'low'},
                            'businessOutcome': {'text': 'Reduced on-prem costs'},
                            'selected': True,
                        }
                    ]
                }
            ],
            'properties': {
                'selectedPathways': {
                    'type': 'array',
                    'description': 'List of modernization pathways selected by the user',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {
                                'type': 'string',
                                'description': 'Unique identifier for the pathway',
                            },
                            'title': {
                                'type': 'string',
                                'description': 'Display title of the pathway',
                            },
                            'description': {
                                'type': 'string',
                                'description': 'Detailed description of the pathway',
                            },
                            'levelOfEffort': {
                                'type': 'object',
                                'properties': {
                                    'text': {'type': 'string'},
                                    'severity': {
                                        'type': 'string',
                                        'enum': ['low', 'medium', 'high'],
                                    },
                                },
                                'required': ['text'],
                                'additionalProperties': False,
                            },
                            'businessOutcome': {
                                'type': 'object',
                                'properties': {'text': {'type': 'string'}},
                                'required': ['text'],
                                'additionalProperties': False,
                            },
                            'selected': {'type': 'boolean'},
                        },
                        'required': [
                            'id',
                            'title',
                            'description',
                            'levelOfEffort',
                            'businessOutcome',
                        ],
                        'additionalProperties': False,
                    },
                }
            },
            'required': ['selectedPathways'],
            'additionalProperties': True,
        },
    ),
    'EXAMPLE': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'selectedItems': [
                    {
                        'id': 'item-1',
                        'label': 'Example Item',
                        'value': 'example-value',
                        'metadata': {'category': 'demo', 'priority': 'high'},
                    }
                ],
                'userNotes': 'Optional free-text from the user',
            }
        ],
        json_schema={
            'title': 'ComponentName Output',
            'description': 'Output schema for ComponentName. Describes the JSON payload returned via onInputChange() when the user interacts with this UI component. The MCP server and HITL SDK use this schema to validate, template, and route agent responses.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'selectedItems': [
                        {
                            'id': 'item-1',
                            'label': 'Example Item',
                            'value': 'example-value',
                            'metadata': {'category': 'demo', 'priority': 'high'},
                        }
                    ],
                    'userNotes': 'Optional free-text from the user',
                }
            ],
            'properties': {
                'selectedItems': {
                    'type': 'array',
                    'description': 'Items selected by the user in the UI',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {
                                'type': 'string',
                                'description': 'Unique identifier for the item',
                            },
                            'label': {
                                'type': 'string',
                                'description': 'Human-readable display label',
                            },
                            'value': {'type': 'string', 'description': 'Machine-readable value'},
                            'metadata': {
                                'type': 'object',
                                'description': 'Structured metadata for the item — additionalProperties is false here because this is a well-defined nested contract',
                                'properties': {
                                    'category': {'type': 'string'},
                                    'priority': {
                                        'type': 'string',
                                        'enum': ['low', 'medium', 'high'],
                                    },
                                },
                                'required': ['category'],
                                'additionalProperties': False,
                            },
                        },
                        'required': ['id', 'label', 'value'],
                        'additionalProperties': False,
                    },
                },
                'userNotes': {
                    'type': 'string',
                    'description': 'Optional free-text input from the user — not in required array because it is only present when the user provides input',
                },
            },
            'required': ['selectedItems'],
            'additionalProperties': True,
        },
    ),
    'FeedbackInput': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'data': 'ThumbsUp'}, {'data': 'ThumbsDown'}],
        json_schema={
            'title': 'FeedbackInput Output',
            'description': 'Output schema for FeedbackInput. Emits a thumbs-up or thumbs-down feedback signal when the user clicks one of the feedback buttons.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'data': 'ThumbsUp'}, {'data': 'ThumbsDown'}],
            'properties': {
                'data': {
                    'type': 'string',
                    'enum': ['ThumbsUp', 'ThumbsDown'],
                    'description': "The feedback value selected by the user. 'ThumbsUp' indicates positive feedback; 'ThumbsDown' indicates negative feedback.",
                }
            },
            'required': ['data'],
            'additionalProperties': True,
        },
    ),
    'FeedbackRating': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'overallRating': 4,
                'overallComment': 'Great migration experience overall.',
                'itemRatings': {'data-migration': 5, 'documentation': 3},
                'itemComments': {
                    'data-migration': 'Seamless and fast.',
                    'documentation': 'Could be more detailed.',
                },
            }
        ],
        json_schema={
            'title': 'FeedbackRating Output',
            'description': 'Output schema for FeedbackRating. Emits an aggregate rating payload whenever any rating or comment field changes, including an overall star rating, overall comment, and per-item ratings and comments.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'overallRating': 4,
                    'overallComment': 'Great migration experience overall.',
                    'itemRatings': {'data-migration': 5, 'documentation': 3},
                    'itemComments': {
                        'data-migration': 'Seamless and fast.',
                        'documentation': 'Could be more detailed.',
                    },
                }
            ],
            'properties': {
                'overallRating': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 5,
                    'description': 'Overall star rating selected by the user (0–5).',
                },
                'overallComment': {
                    'type': ['string', 'null'],
                    'description': 'Free-text overall comment entered by the user.',
                },
                'itemRatings': {
                    'type': 'object',
                    'description': 'Map of feedback item name to its star rating (0–5).',
                    'additionalProperties': False,
                    'patternProperties': {'^.+$': {'type': 'integer', 'minimum': 0, 'maximum': 5}},
                },
                'itemComments': {
                    'type': 'object',
                    'description': 'Map of feedback item name to its free-text comment.',
                    'additionalProperties': False,
                    'patternProperties': {'^.+$': {'type': 'string'}},
                },
            },
            'required': ['overallRating', 'itemRatings', 'itemComments'],
            'additionalProperties': True,
        },
    ),
    'FileDownload': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'FileDownload Output',
            'description': 'Output schema for FileDownload. This is a display-only component that renders a download button for a file artifact. It never calls onInputChange and produces no output payload.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'FileUploadComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedFiles': [
                    {'content': 'base64encodedcontent...', 'name': 'servers.csv', 'isZip': False}
                ]
            }
        ],
        json_schema={
            'title': 'FileUploadComponent Output',
            'description': 'Output schema for FileUploadComponent. Emits uploaded file data as base64 content with metadata.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedFiles': [
                        {
                            'content': 'base64encodedcontent...',
                            'name': 'servers.csv',
                            'isZip': False,
                        }
                    ]
                }
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded file data',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'content': {'type': 'string', 'description': 'File content in base64'},
                            'name': {'type': 'string', 'description': 'File name'},
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['content', 'name', 'isZip'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': ['uploadedFiles'],
            'additionalProperties': True,
        },
    ),
    'FileUploadV2': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedArtifacts': [
                    {
                        'artifactId': 'artifact-123e4567-e89b-12d3-a456-426614174000',
                        'name': 'document.pdf',
                        'mimeType': 'application/pdf',
                    }
                ]
            }
        ],
        json_schema={
            'title': 'FileUploadV2 Output',
            'description': 'Output schema for FileUploadV2. Emits an array of UploadedArtifact objects representing successfully uploaded files. Note: this component passes the array directly to onInputChange (not wrapped in an object).',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedArtifacts': [
                        {
                            'artifactId': 'artifact-123e4567-e89b-12d3-a456-426614174000',
                            'name': 'document.pdf',
                            'mimeType': 'application/pdf',
                        }
                    ]
                }
            ],
            'properties': {
                'uploadedArtifacts': {
                    'type': 'array',
                    'description': 'Array of successfully uploaded file artifacts. Note: the component calls onInputChange(artifacts) directly with the array, not wrapped in {uploadedArtifacts: ...}. This schema wraps it for convention consistency.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'artifactId': {
                                'type': 'string',
                                'description': 'Unique identifier for the uploaded artifact',
                            },
                            'name': {'type': 'string', 'description': 'Original filename'},
                            'mimeType': {'type': 'string', 'description': 'MIME type of the file'},
                        },
                        'required': ['artifactId', 'name', 'mimeType'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'GeneralConnector': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'connectorId': 'connector-abc123'}],
        json_schema={
            'title': 'GeneralConnector Output',
            'description': 'Output schema for GeneralConnector. Identifies which connector is used for the job and connector approval/reject workflow.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'connectorId': 'connector-abc123'}],
            'properties': {
                'connectorId': {
                    'type': 'string',
                    'description': 'Identifies which connector is used for the job and connector approval/reject workflow.',
                }
            },
            'required': ['connectorId'],
            'additionalProperties': True,
        },
    ),
    'CreateOrSelectConnectors': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'connectorId': 'connector-abc123', 'connectorType': 'AMAZON_S3'}],
        json_schema={
            'title': 'CreateOrSelectConnectors Output',
            'description': 'Output schema for CreateOrSelectConnectors. Identifies which connector is used for the job.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'connectorId': 'connector-abc123', 'connectorType': 'AMAZON_S3'}],
            'properties': {
                'connectorId': {
                    'type': 'string',
                    'description': 'Identifies which connector is used for the job.',
                },
                'connectorType': {
                    'type': 'string',
                    'description': 'The connector type. Use get_resource(resource="connector") to look it up.',
                },
            },
            'required': ['connectorId', 'connectorType'],
            'additionalProperties': True,
        },
    ),
    'GenericErrorHandlingComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'GenericErrorHandlingComponent Output',
            'description': 'Output schema for GenericErrorHandlingComponent. Display-only component that shows an error message from a previous migration step and prompts the user to retry. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'GenericRehostErrorHandlingComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'GenericRehostErrorHandlingComponent Output',
            'description': 'Output schema for GenericRehostErrorHandlingComponent. Display-only component that shows rehost-specific error details and a list of failed servers. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ImportNetworkData': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'useExistingVpcs': True},
            {
                'importTaskId': 'import-task-0123456789abcdef0',  # pragma: allowlist secret
                'targetNetworkTopology': 'HUB_AND_SPOKE',
            },
            {
                'importTaskId': 'import-task-0123456789abcdef0',  # pragma: allowlist secret
                'targetNetworkTopology': 'ISOLATED_VPC',
                'generateSecurityGroup': True,
            },
            {
                'uploadedFiles': [
                    {
                        'name': 'network-data.zip',
                        'content': 'base64encodedcontent==',
                        'isZip': True,
                    }
                ]
            },
        ],
        json_schema={
            'title': 'ImportNetworkData Output',
            'description': "Output schema for ImportNetworkData. Collects the user's network import selection and topology preference. The user either opts to use existing VPCs, or selects an import task plus a target network topology (and optionally a security group generation preference).",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'useExistingVpcs': True},
                {
                    'importTaskId': 'import-task-0123456789abcdef0',  # pragma: allowlist secret
                    'targetNetworkTopology': 'HUB_AND_SPOKE',
                },
                {
                    'importTaskId': 'import-task-0123456789abcdef0',  # pragma: allowlist secret
                    'targetNetworkTopology': 'ISOLATED_VPC',
                    'generateSecurityGroup': True,
                },
                {
                    'uploadedFiles': [
                        {
                            'name': 'network-data.zip',
                            'content': 'base64encodedcontent==',
                            'isZip': True,
                        }
                    ]
                },
            ],
            'properties': {
                'useExistingVpcs': {
                    'type': 'boolean',
                    'description': 'True when the user chose to use existing VPCs instead of translating and deploying new ones.',
                },
                'importTaskId': {
                    'type': 'string',
                    'description': 'The selected on-premises network import task ID.',
                },
                'targetNetworkTopology': {
                    'type': 'string',
                    'enum': ['HUB_AND_SPOKE', 'ISOLATED_VPC'],
                    'description': 'The target AWS network topology chosen by the user.',
                },
                'generateSecurityGroup': {
                    'type': 'boolean',
                    'description': 'Whether to auto-generate security groups. Only present when enableFlexibleIp is true.',
                },
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Files uploaded via the inline file uploader (delegated from FileUploaderWithDisableMode).',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {'type': 'boolean'},
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                },
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'InformationalMessageComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'InformationalMessageComponent Output',
            'description': 'Output schema for InformationalMessageComponent. This is a display-only component that renders a title and informational message. It never calls onInputChange and produces no output payload.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'KMSKeySelection': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'result': [
                    {
                        'host': 'db-server-01.example.com',
                        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                        'status': 'SUCCESS',
                        'databases': ['orders'],
                        'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                        'dms_project_name': 'my-dms-project',
                        'instance_id': 'instance-01',
                        'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                        'instance_profile_name': 'my-profile',
                        'port': 1433,
                        'region': 'us-east-1',
                        'endpoint': None,
                        'failure_message': None,
                        'failure_step': None,
                        'security_groups': ['sg-12345678'],
                        'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                        'source_data_source_name': 'source-endpoint',
                        'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                        'target_data_source_name': 'target-endpoint',
                        'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                        'vpc': 'vpc-12345678',
                        'customer_s3_bucket_dms': 'my-dms-bucket',
                        'subnets': [
                            {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                        ],
                        'kms_key_aliases': [
                            {
                                'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                                'AliasName': 'alias/my-key',
                                'CreationDate': '2024-01-01T00:00:00Z',
                                'LastUpdatedDate': '2024-01-01T00:00:00Z',
                                'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                            }
                        ],
                        'selected_key_alias': {
                            'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                            'AliasName': 'alias/my-key',
                            'CreationDate': '2024-01-01T00:00:00Z',
                            'LastUpdatedDate': '2024-01-01T00:00:00Z',
                            'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                        },
                    }
                ]
            }
        ],
        json_schema={
            'title': 'KMSKeySelection Output',
            'description': "Output schema for KMSKeySelection. Emits the full result list with each item's selected_key_alias updated based on user selection.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'result': [
                        {
                            'host': 'db-server-01.example.com',
                            'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                            'status': 'SUCCESS',
                            'databases': ['orders'],
                            'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                            'dms_project_name': 'my-dms-project',
                            'instance_id': 'instance-01',
                            'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                            'instance_profile_name': 'my-profile',
                            'port': 1433,
                            'region': 'us-east-1',
                            'endpoint': None,
                            'failure_message': None,
                            'failure_step': None,
                            'security_groups': ['sg-12345678'],
                            'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                            'source_data_source_name': 'source-endpoint',
                            'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                            'target_data_source_name': 'target-endpoint',
                            'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                            'vpc': 'vpc-12345678',
                            'customer_s3_bucket_dms': 'my-dms-bucket',
                            'subnets': [
                                {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                            ],
                            'kms_key_aliases': [
                                {
                                    'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                                    'AliasName': 'alias/my-key',
                                    'CreationDate': '2024-01-01T00:00:00Z',
                                    'LastUpdatedDate': '2024-01-01T00:00:00Z',
                                    'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                                }
                            ],
                            'selected_key_alias': {
                                'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                                'AliasName': 'alias/my-key',
                                'CreationDate': '2024-01-01T00:00:00Z',
                                'LastUpdatedDate': '2024-01-01T00:00:00Z',
                                'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                            },
                        }
                    ]
                }
            ],
            'properties': {
                'result': {
                    'type': 'array',
                    'description': "Full list of database connection results with the user's KMS key alias selection applied.",
                    'items': {
                        'type': 'object',
                        'properties': {
                            'host': {'type': 'string'},
                            'secret_arn': {'type': 'string'},
                            'status': {'type': 'string'},
                            'databases': {'type': 'array', 'items': {'type': 'string'}},
                            'dms_project_arn': {'type': 'string'},
                            'dms_project_name': {'type': 'string'},
                            'instance_id': {'type': 'string'},
                            'instance_profile_arn': {'type': 'string'},
                            'instance_profile_name': {'type': 'string'},
                            'port': {'type': 'number'},
                            'region': {'type': ['string', 'null']},
                            'endpoint': {'type': ['string', 'null']},
                            'failure_message': {'type': ['string', 'null']},
                            'failure_step': {'type': ['string', 'null']},
                            'security_groups': {'type': 'array', 'items': {'type': 'string'}},
                            'source_data_source_arn': {'type': 'string'},
                            'source_data_source_name': {'type': 'string'},
                            'target_data_source_arn': {'type': 'string'},
                            'target_data_source_name': {'type': 'string'},
                            'target_secret_arn': {'type': 'string'},
                            'vpc': {'type': 'string'},
                            'customer_s3_bucket_dms': {'type': 'string'},
                            'subnets': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'availability_zone': {'type': 'string'},
                                        'subnet_id': {'type': 'string'},
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'kms_key_aliases': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'AliasArn': {'type': 'string'},
                                        'AliasName': {'type': 'string'},
                                        'CreationDate': {'type': 'string'},
                                        'LastUpdatedDate': {'type': 'string'},
                                        'TargetKeyId': {'type': 'string'},
                                    },
                                    'required': [
                                        'AliasArn',
                                        'AliasName',
                                        'CreationDate',
                                        'LastUpdatedDate',
                                        'TargetKeyId',
                                    ],
                                    'additionalProperties': False,
                                },
                            },
                            'selected_key_alias': {
                                'description': 'The KMS key alias selected by the user, or null if none selected.',
                                'oneOf': [
                                    {
                                        'type': 'object',
                                        'properties': {
                                            'AliasArn': {'type': 'string'},
                                            'AliasName': {'type': 'string'},
                                            'CreationDate': {'type': 'string'},
                                            'LastUpdatedDate': {'type': 'string'},
                                            'TargetKeyId': {'type': 'string'},
                                        },
                                        'required': [
                                            'AliasArn',
                                            'AliasName',
                                            'CreationDate',
                                            'LastUpdatedDate',
                                            'TargetKeyId',
                                        ],
                                        'additionalProperties': False,
                                    },
                                    {'type': 'null'},
                                ],
                            },
                        },
                        'required': [
                            'host',
                            'secret_arn',
                            'status',
                            'kms_key_aliases',
                            'selected_key_alias',
                        ],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['result'],
            'additionalProperties': True,
        },
    ),
    'LaunchCutoverInstances': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'reload': True}],
        json_schema={
            'title': 'LaunchCutoverInstances Output',
            'description': 'Output schema for LaunchCutoverInstances. Emits a reload flag when the user clicks the Refresh button to poll replication status before launching cutover instances.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'reload': True}],
            'properties': {
                'reload': {
                    'type': 'boolean',
                    'description': 'Set to true when the user clicks Refresh to reload replication status data.',
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'LaunchTestInstances': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'reload': True}],
        json_schema={
            'title': 'LaunchTestInstances Output',
            'description': 'Output schema for LaunchTestInstances. Emits a reload flag when the user clicks the Refresh button to poll replication status before launching test instances.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'reload': True}],
            'properties': {
                'reload': {
                    'type': 'boolean',
                    'description': 'Set to true when the user clicks Refresh to reload replication status data.',
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeAccessRestrictedDisplay': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeAccessRestrictedDisplay Output',
            'description': 'Output schema for MainframeAccessRestrictedDisplay. Display-only component that renders an error alert when the user does not have access. onInputChange is not part of the component interface; no output is produced.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeAnalysisResults': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'file': 'base64-encoded-reclassification-file-content',
                'files': [],
                'missingNodes': [],
            }
        ],
        json_schema={
            'title': 'MainframeAnalysisResults Output',
            'description': 'Output schema for MainframeAnalysisResults. onInputChange is forwarded directly to the third-party @amzn/blu-insights-ui-components AnalysisResults component, which manages file reclassification selections. The payload shape is owned by that library and may vary; the properties documented here reflect the known contract.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'file': 'base64-encoded-reclassification-file-content',
                    'files': [],
                    'missingNodes': [],
                }
            ],
            'properties': {
                'file': {
                    'type': 'string',
                    'description': 'Base-64 encoded content of the reclassification file, if there is a reclassification.',
                },
                'files': {
                    'type': 'array',
                    'description': 'The current list of files passed through from the input (not modified), if there is a reclassification.',
                    'items': {
                        'type': 'object',
                        'properties': {},
                        'required': [],
                        'additionalProperties': True,
                    },
                },
                'missingNodes': {
                    'type': 'array',
                    'description': 'The current list of missing nodes passed through from the input (not modified), if there is a reclassification.',
                    'items': {
                        'type': 'object',
                        'properties': {},
                        'required': [],
                        'additionalProperties': True,
                    },
                },
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeAssessmentConfigurationComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'sourceCodeS3Path': 's3://my-bucket/mainframe/source-code/',
                'smfRecordsS3Path': 's3://my-bucket/mainframe/smf-records/',
            }
        ],
        json_schema={
            'title': 'MainframeAssessmentConfigurationComponent Output',
            'description': 'Output schema for MainframeAssessmentConfigurationComponent. Emits S3 path configuration for the mainframe assessment whenever either input field changes.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'sourceCodeS3Path': 's3://my-bucket/mainframe/source-code/',
                    'smfRecordsS3Path': 's3://my-bucket/mainframe/smf-records/',
                }
            ],
            'properties': {
                'sourceCodeS3Path': {
                    'type': 'string',
                    'description': "S3 URI pointing to the mainframe source code location. Must start with 's3://'.",
                    'pattern': '^s3://',
                },
                'smfRecordsS3Path': {
                    'type': 'string',
                    'description': "S3 URI pointing to the SMF records location. Must start with 's3://'.",
                    'pattern': '^s3://',
                },
            },
            'required': ['sourceCodeS3Path'],
            'additionalProperties': True,
        },
    ),
    'MainframeAssessmentSummaryComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        chat_hint=(
            'To accept or reject retirement candidates, use send_message scoped to the job '
            '(e.g. "reject all retirement candidates"). The agent processes the request, '
            're-runs the assessment, and keeps the task open for further iteration. '
            'Only use complete_task when the user explicitly wants to finalize the assessment and move on.'
        ),
        examples=[
            {
                'acceptRetirementCandidates': {
                    'nodes': [{'node_name': 'PACKAGE-A', 'node_type': 'COBOL'}]
                },
                'rejectRetirementCandidates': {
                    'nodes': [{'node_name': 'PACKAGE-B', 'node_type': 'JCL'}]
                },
                'userId': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            },
            {
                'acceptRetirementCandidates': {
                    'nodes': [{'node_name': 'LEGACY-BATCH-01', 'node_type': 'COBOL'}]
                },
                'userId': 'f9e8d7c6-b5a4-3210-fedc-ba9876543210',
            },
        ],
        json_schema={
            'title': 'MainframeAssessmentSummaryComponent Output',
            'description': 'Output schema for MainframeAssessmentSummaryComponent. When the user reviews retirement wave candidates and submits accept/reject decisions, the component emits a RetirementActionRecord with optional accepted and rejected node lists.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'acceptRetirementCandidates': {
                        'nodes': [{'node_name': 'PACKAGE-A', 'node_type': 'COBOL'}]
                    },
                    'rejectRetirementCandidates': {
                        'nodes': [{'node_name': 'PACKAGE-B', 'node_type': 'JCL'}]
                    },
                    'userId': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
                },
                {
                    'acceptRetirementCandidates': {
                        'nodes': [{'node_name': 'LEGACY-BATCH-01', 'node_type': 'COBOL'}]
                    },
                    'userId': 'f9e8d7c6-b5a4-3210-fedc-ba9876543210',
                },
            ],
            'properties': {
                'acceptRetirementCandidates': {
                    'type': 'object',
                    'description': 'Set of retirement candidate nodes the user has accepted for retirement.',
                    'properties': {
                        'nodes': {
                            'type': 'array',
                            'description': 'List of accepted retirement candidate nodes.',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'node_name': {
                                        'type': 'string',
                                        'description': 'The name of the retirement candidate node (typically the package name).',
                                    },
                                    'node_type': {
                                        'type': ['string', 'null'],
                                        'description': "The type of the node (e.g. 'COBOL', 'JCL'). May be null.",
                                    },
                                },
                                'required': ['node_name', 'node_type'],
                                'additionalProperties': False,
                            },
                        }
                    },
                    'required': ['nodes'],
                    'additionalProperties': False,
                },
                'rejectRetirementCandidates': {
                    'type': 'object',
                    'description': 'Set of retirement candidate nodes the user has rejected for retirement.',
                    'properties': {
                        'nodes': {
                            'type': 'array',
                            'description': 'List of rejected retirement candidate nodes.',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'node_name': {
                                        'type': 'string',
                                        'description': 'The name of the retirement candidate node (typically the package name).',
                                    },
                                    'node_type': {
                                        'type': ['string', 'null'],
                                        'description': "The type of the node (e.g. 'COBOL', 'JCL'). May be null.",
                                    },
                                },
                                'required': ['node_name', 'node_type'],
                                'additionalProperties': False,
                            },
                        }
                    },
                    'required': ['nodes'],
                    'additionalProperties': False,
                },
                'userId': {
                    'type': 'string',
                    'description': 'The user ID of the user performing the retirement action',
                },
                'isGenerateReport': {
                    'type': 'boolean',
                    'description': 'When true, signals the backend to generate the global retirement candidate report.',
                },
            },
            'additionalProperties': True,
        },
    ),
    'MainframeBreInputComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'reportScope': 'applicationLevel',
                'detailedLevel': False,
                'userSelectedFiles': [
                    {
                        'name': 'PAYROLL.cbl',
                        'path': '/src/cobol/PAYROLL.cbl',
                        'fileType': 'COBOL',
                        'totalLines': 1240,
                        'folderPath': '/src/cobol',
                    }
                ],
            }
        ],
        json_schema={
            'title': 'MainframeBreInputComponent Output',
            'description': 'Output schema for MainframeBreInputComponent. Collects the business-rule extraction report scope, detailed-spec flag, and the set of files selected by the user.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'reportScope': 'applicationLevel',
                    'detailedLevel': False,
                    'userSelectedFiles': [
                        {
                            'name': 'PAYROLL.cbl',
                            'path': '/src/cobol/PAYROLL.cbl',
                            'fileType': 'COBOL',
                            'totalLines': 1240,
                            'folderPath': '/src/cobol',
                        }
                    ],
                }
            ],
            'properties': {
                'reportScope': {
                    'type': 'string',
                    'enum': ['applicationLevel', 'fileLevel'],
                    'description': "Scope of the business-rule extraction report. 'applicationLevel' auto-selects all files; 'fileLevel' lets the user choose individual files.",
                },
                'detailedLevel': {
                    'type': 'boolean',
                    'description': 'When true, generates a detailed business-rule specification instead of a summary.',
                },
                'userSelectedFiles': {
                    'type': 'array',
                    'description': 'Files selected by the user for business-rule extraction. Folder-only records are excluded from this export.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name.'},
                            'path': {'type': 'string', 'description': 'Full path to the file.'},
                            'fileType': {
                                'type': 'string',
                                'description': 'Type of the file (e.g. COBOL, PL1).',
                            },
                            'totalLines': {
                                'type': 'number',
                                'description': 'Total number of lines in the file.',
                            },
                            'folderPath': {
                                'type': 'string',
                                'description': 'Parent folder path. Present only for file records (not folder records).',
                            },
                        },
                        'required': ['name', 'path'],
                        'additionalProperties': False,
                    },
                },
            },
            'required': ['reportScope', 'detailedLevel', 'userSelectedFiles'],
            'additionalProperties': True,
        },
    ),
    'MainframeBreResultComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeBreResultComponent Output',
            'description': 'Output schema for MainframeBreResultComponent. Display-only component that renders the business-rule extraction report and S3 output location. Submit and save buttons are hidden; no user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeDataLineageResultComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeDataLineageResultComponent Output',
            'description': 'Output schema for MainframeDataLineageResultComponent. Display-only component that renders data lineage and data dictionary results. Submit and save buttons are hidden; no user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeDecomposition': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'domains': [
                    {
                        'id': '52511e9-3b6e-4edf-a9e0-2ab',
                        'name': 'AccountManagement',
                        'description': 'Account management domain',
                        'numberOfFiles': 3,
                        'totalLines': 1200,
                        'central': False,
                        'files': [
                            {
                                'id': 'b7c2dcc7-021e-480b-8164-d4a9b4fed651',
                                'name': 'CBACT01C',
                                'fileType': 'COB',
                            }
                        ],
                    }
                ],
                'decompositionConfiguration': {
                    'domainSizesThresholdsPercentages': [
                        {'id': '52511e9-3b6e-4edf-a9e0-2ab', 'percentage': 40}
                    ],
                    'centerSizeThresholdPercentage': 12,
                },
                'graphMetadata': {'layout': 'ORGANIC'},
                'nodes': [
                    {
                        'id': 'b7c2dcc7-021e-480b-8164-d4a9b4fed651',
                        'x': 120,
                        'y': 340,
                        'shape': 'CIRCLE',
                        'color': 1,
                    }
                ],
                'subgraphs': [
                    {
                        'id': 'sg-1',
                        'name': 'AccountManagement',
                        'description': 'Account management',
                        'nodeIds': ['b7c2dcc7-021e-480b-8164-d4a9b4fed651'],
                    }
                ],
            }
        ],
        json_schema={
            'title': 'MainframeDecomposition Output',
            'description': 'Output schema for MainframeDecomposition. Delegates onInputChange to the @amzn/blu-insights-ui-components DecompositionResults library component, which emits domain assignment changes when the user moves files between domains in the decomposition graph.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'domains': [
                        {
                            'id': '52511e9-3b6e-4edf-a9e0-2ab',
                            'name': 'AccountManagement',
                            'description': 'Account management domain',
                            'numberOfFiles': 3,
                            'totalLines': 1200,
                            'central': False,
                            'files': [
                                {
                                    'id': 'b7c2dcc7-021e-480b-8164-d4a9b4fed651',
                                    'name': 'CBACT01C',
                                    'fileType': 'COB',
                                }
                            ],
                        }
                    ],
                    'decompositionConfiguration': {
                        'domainSizesThresholdsPercentages': [
                            {'id': '52511e9-3b6e-4edf-a9e0-2ab', 'percentage': 40}
                        ],
                        'centerSizeThresholdPercentage': 12,
                    },
                    'graphMetadata': {'layout': 'ORGANIC'},
                    'nodes': [
                        {
                            'id': 'b7c2dcc7-021e-480b-8164-d4a9b4fed651',
                            'x': 120,
                            'y': 340,
                            'shape': 'CIRCLE',
                            'color': 1,
                        }
                    ],
                    'subgraphs': [
                        {
                            'id': 'sg-1',
                            'name': 'AccountManagement',
                            'description': 'Account management',
                            'nodeIds': ['b7c2dcc7-021e-480b-8164-d4a9b4fed651'],
                        }
                    ],
                }
            ],
            'properties': {
                'domains': {
                    'type': 'array',
                    'description': 'Updated domain assignments after user interaction with the decomposition graph.',
                    'items': {
                        'type': 'object',
                        'additionalProperties': True,
                        'required': ['id', 'name', 'numberOfFiles', 'description'],
                        'properties': {
                            'id': {
                                'type': 'string',
                                'description': 'Unique identifier of the domain.',
                            },
                            'name': {
                                'type': 'string',
                                'description': 'Display name of the domain.',
                            },
                            'description': {
                                'type': 'string',
                                'description': 'Description of the domain.',
                            },
                            'numberOfFiles': {
                                'type': 'integer',
                                'description': 'Number of files in the domain.',
                            },
                            'numberOfSeeds': {
                                'type': 'integer',
                                'description': 'Number of seed files in the domain.',
                            },
                            'totalLines': {
                                'type': 'integer',
                                'description': 'Total lines of code in the domain.',
                            },
                            'central': {
                                'type': 'boolean',
                                'description': 'Whether this is the central/common domain.',
                            },
                            'sizeThresholdPercentage': {
                                'type': 'number',
                                'description': 'Configured size threshold percentage for the domain.',
                            },
                            'actualSizePercentage': {
                                'type': 'number',
                                'description': 'Actual size percentage of the domain.',
                            },
                            'isAIGenerated': {
                                'type': 'boolean',
                                'description': 'Whether this domain was generated by AI.',
                            },
                            'files': {
                                'type': 'array',
                                'description': 'Files assigned to this domain.',
                                'items': {
                                    'type': 'object',
                                    'additionalProperties': True,
                                    'required': ['id', 'name', 'fileType'],
                                    'properties': {
                                        'id': {'type': 'string'},
                                        'name': {'type': 'string'},
                                        'fileType': {'type': 'string'},
                                        'cyclomaticComplexity': {'type': 'integer'},
                                        'seeds': {'type': 'boolean'},
                                        'totalLinesOfCode': {'type': 'integer'},
                                        'isCouplingFile': {'type': 'boolean'},
                                    },
                                },
                            },
                        },
                    },
                },
                'decompositionConfiguration': {
                    'type': 'object',
                    'description': 'Configuration parameters for the decomposition algorithm.',
                    'properties': {
                        'domainSizesThresholdsPercentages': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'string', 'description': 'Domain id.'},
                                    'percentage': {
                                        'type': 'integer',
                                        'description': 'Size threshold percentage for the domain.',
                                    },
                                },
                            },
                        },
                        'centerSizeThresholdPercentage': {
                            'type': 'integer',
                            'description': 'Size threshold percentage for the central/common domain.',
                        },
                    },
                    'required': [],
                    'additionalProperties': False,
                },
                'graphMetadata': {
                    'type': 'object',
                    'description': 'Metadata about the graph layout.',
                    'properties': {
                        'layout': {
                            'type': 'string',
                            'description': 'Layout type of the graph.',
                            'enum': ['ORGANIC', 'HIERARCHICAL', 'CUSTOM'],
                        }
                    },
                    'required': [],
                    'additionalProperties': False,
                },
                'nodes': {
                    'type': 'array',
                    'description': 'Graph node positions and visual properties after user interaction.',
                    'items': {
                        'type': 'object',
                        'additionalProperties': True,
                        'properties': {
                            'id': {'type': 'string'},
                            'x': {'type': 'integer'},
                            'y': {'type': 'integer'},
                            'shape': {
                                'type': 'string',
                                'enum': ['CIRCLE', 'TRIANGLE', 'RECTANGLE', 'SQUARE'],
                            },
                            'color': {'type': 'integer'},
                        },
                        'required': ['id', 'x', 'y'],
                    },
                },
                'subgraphs': {
                    'type': 'array',
                    'description': 'Subgraph groupings defined by the user in the graph view.',
                    'items': {
                        'type': 'object',
                        'additionalProperties': True,
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'description': {'type': 'string'},
                            'nodeIds': {'type': 'array', 'items': {'type': 'string'}},
                        },
                        'required': ['id', 'name', 'description', 'nodeIds'],
                    },
                },
            },
            'required': ['domains', 'decompositionConfiguration'],
            'additionalProperties': True,
        },
    ),
    'MainframeDocGenInputComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'detailLevel': 'SUMMARY',
                'userSelectedFiles': [
                    {
                        'name': 'PAYROLL.cbl',
                        'path': '/src/cobol/PAYROLL.cbl',
                        'fileType': 'COBOL',
                        'totalLines': 1240,
                        'folderPath': '/src/cobol',
                    }
                ],
            }
        ],
        json_schema={
            'title': 'MainframeDocGenInputComponent Output',
            'description': 'Output schema for MainframeDocGenInputComponent. Collects the documentation detail level and the set of files the user has selected for documentation generation.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'detailLevel': 'SUMMARY',
                    'userSelectedFiles': [
                        {
                            'name': 'PAYROLL.cbl',
                            'path': '/src/cobol/PAYROLL.cbl',
                            'fileType': 'COBOL',
                            'totalLines': 1240,
                            'folderPath': '/src/cobol',
                        }
                    ],
                }
            ],
            'properties': {
                'detailLevel': {
                    'type': 'string',
                    'enum': ['SUMMARY', 'DETAILED'],
                    'description': 'Documentation detail level selected by the user.',
                },
                'userSelectedFiles': {
                    'type': 'array',
                    'description': 'Files selected by the user for documentation generation. Folder-only records are excluded from this export.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name.'},
                            'path': {'type': 'string', 'description': 'Full path to the file.'},
                            'fileType': {
                                'type': 'string',
                                'description': 'Type of the file (e.g. COBOL, JCL).',
                            },
                            'totalLines': {
                                'type': 'number',
                                'description': 'Total number of lines in the file.',
                            },
                            'folderPath': {
                                'type': 'string',
                                'description': 'Parent folder path. Present only for file records (not folder records).',
                            },
                        },
                        'required': ['name', 'path'],
                        'additionalProperties': False,
                    },
                },
            },
            'required': ['detailLevel', 'userSelectedFiles'],
            'additionalProperties': True,
        },
    ),
    'MainframeDocGenResultComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeDocGenResultComponent Output',
            'description': 'Output schema for MainframeDocGenResultComponent. Display-only component that shows documentation generation results and an S3 output location. Submit and save buttons are hidden; no user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeMigrationSequencePlanning': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'domainsWithSequence': [
                    {
                        'id': 'domain_with_sequence_1',
                        'domain': {
                            'id': 'domain_1',
                            'name': 'Sales',
                            'totalLines': 400,
                            'numberOfFiles': 100,
                            'description': 'Financial sales report',
                        },
                        'sequence': 1,
                        'preferred': 1,
                    },
                    {
                        'id': 'domain_with_sequence_2',
                        'domain': {
                            'id': 'domain_2',
                            'name': 'Warehouse management',
                            'totalLines': 200,
                            'numberOfFiles': 500,
                            'description': 'Display and dispatching of equipments.',
                        },
                        'sequence': 2,
                        'preferred': 2,
                    },
                ]
            }
        ],
        json_schema={
            'title': 'MainframeMigrationSequencePlanning Output',
            'description': 'Output schema for MainframeMigrationSequencePlanning. Delegates onInputChange to the @amzn/blu-insights-ui-components MigrationSequencePlanningResult library component, which emits updated domain sequences when the user reorders migration waves.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'domainsWithSequence': [
                        {
                            'id': 'domain_with_sequence_1',
                            'domain': {
                                'id': 'domain_1',
                                'name': 'Sales',
                                'totalLines': 400,
                                'numberOfFiles': 100,
                                'description': 'Financial sales report',
                            },
                            'sequence': 1,
                            'preferred': 1,
                        },
                        {
                            'id': 'domain_with_sequence_2',
                            'domain': {
                                'id': 'domain_2',
                                'name': 'Warehouse management',
                                'totalLines': 200,
                                'numberOfFiles': 500,
                                'description': 'Display and dispatching of equipments.',
                            },
                            'sequence': 2,
                            'preferred': 2,
                        },
                    ]
                }
            ],
            'properties': {
                'domainsWithSequence': {
                    'type': 'array',
                    'description': 'Updated list of domains with their assigned migration wave sequences.',
                    'items': {
                        'type': 'object',
                        'required': ['id', 'domain', 'sequence'],
                        'additionalProperties': True,
                        'properties': {
                            'id': {
                                'type': 'string',
                                'description': 'Unique identifier for the domain-sequence pairing.',
                            },
                            'domain': {
                                'type': 'object',
                                'description': 'Domain details.',
                                'required': ['id', 'name', 'numberOfFiles', 'description'],
                                'additionalProperties': True,
                                'properties': {
                                    'id': {'type': 'string'},
                                    'name': {'type': 'string'},
                                    'totalLines': {'type': 'integer'},
                                    'numberOfFiles': {'type': 'integer'},
                                    'description': {'type': 'string'},
                                },
                            },
                            'sequence': {
                                'type': 'integer',
                                'description': 'Migration wave sequence number (1-based).',
                            },
                            'preferred': {
                                'type': 'integer',
                                'description': 'User-specified preferred sequence number for this domain.',
                            },
                        },
                    },
                }
            },
            'required': ['domainsWithSequence'],
            'additionalProperties': True,
        },
    ),
    'MainframeReforgeInputComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'buildableCodeS3Path': 's3://my-bucket/buildable-code.zip',
                'businessLogicS3Path': 's3://my-bucket/bre_output.zip',
            }
        ],
        json_schema={
            'title': 'MainframeReforgeInputComponent Output',
            'description': 'Output schema for MainframeReforgeInputComponent. Emitted on every keystroke as the user fills in S3 path inputs for source project and optional business logic locations.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'buildableCodeS3Path': 's3://my-bucket/buildable-code.zip',
                    'businessLogicS3Path': 's3://my-bucket/bre_output.zip',
                }
            ],
            'properties': {
                'buildableCodeS3Path': {
                    'type': 'string',
                    'description': 'S3 URI pointing to the buildable source code archive. Required field.',
                },
                'businessLogicS3Path': {
                    'type': 'string',
                    'description': 'S3 URI pointing to the BRE business logic output archive. Optional field, only shown when isAllowlisted=true.',
                },
            },
            'required': ['buildableCodeS3Path'],
            'additionalProperties': True,
        },
    ),
    'MainframeReforgeOutputComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeReforgeOutputComponent Output',
            'description': 'Output schema for MainframeReforgeOutputComponent. This is a display-only component that shows reforge job results and S3 output location. It does not call onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'MainframeReforgeSelectComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'reforgeSelect': [
                    {
                        'className': 'AccountService',
                        'packageName': 'com.example.banking.account',
                        'loc': 342,
                    },
                    {
                        'className': 'TransactionProcessor',
                        'packageName': 'com.example.banking.transaction',
                        'loc': 518,
                    },
                ]
            }
        ],
        json_schema={
            'title': 'MainframeReforgeSelectComponent Output',
            'description': 'Output schema for MainframeReforgeSelectComponent. Emitted via the submit confirmation handler when the user confirms their class selection. Contains the list of Java classes selected for reforging.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'reforgeSelect': [
                        {
                            'className': 'AccountService',
                            'packageName': 'com.example.banking.account',
                            'loc': 342,
                        },
                        {
                            'className': 'TransactionProcessor',
                            'packageName': 'com.example.banking.transaction',
                            'loc': 518,
                        },
                    ]
                }
            ],
            'properties': {
                'reforgeSelect': {
                    'type': 'array',
                    'description': 'List of Java class records selected by the user for reforging.',
                    'items': {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'className': {
                                'type': 'string',
                                'description': 'Simple name of the Java class.',
                            },
                            'packageName': {
                                'type': 'string',
                                'description': 'Fully-qualified package name containing the class.',
                            },
                            'loc': {
                                'type': 'integer',
                                'description': 'Lines of code in the class.',
                            },
                        },
                        'required': ['className', 'packageName', 'loc'],
                    },
                }
            },
            'required': ['reforgeSelect'],
            'additionalProperties': True,
        },
    ),
    'MainframeSMFAnalysisComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeSMFAnalysisComponent Output',
            'description': 'Output schema for MainframeSMFAnalysisComponent. This is a display-only component that shows SMF analysis results (batch and CICS data) in a tabbed view. It never calls onInputChange and produces no output payload.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'MainframeSMFConfigureComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'sourceCodeS3Path': 's3://my-bucket/mainframe/buildable-project/'}],
        json_schema={
            'title': 'MainframeSMFConfigureComponent Output',
            'description': 'Output schema for MainframeSMFConfigureComponent. Emits the S3 path to the mainframe source code project whenever the input field changes.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'sourceCodeS3Path': 's3://my-bucket/mainframe/buildable-project/'}],
            'properties': {
                'sourceCodeS3Path': {
                    'type': 'string',
                    'description': "S3 URI pointing to the mainframe buildable source code project. Must start with 's3://'.",
                    'pattern': '^s3://',
                }
            },
            'required': ['sourceCodeS3Path'],
            'additionalProperties': True,
        },
    ),
    'MainframeTestDataCollectionAddComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'data': 's3://my-bucket/test-plan/testcases.json'}],
        json_schema={
            'title': 'MainframeTestDataCollectionAddComponent Output',
            'description': 'Output schema for MainframeTestDataCollectionAddComponent. Emitted on every input change and on mount when an s3Path is pre-filled. Contains the S3 URI of the test plan JSON file.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'data': 's3://my-bucket/test-plan/testcases.json'}],
            'properties': {
                'data': {
                    'type': 'string',
                    'description': 'S3 URI of the test plan JSON file provided by the user (e.g. s3://bucket-name/mycode.json).',
                }
            },
            'required': ['data'],
            'additionalProperties': True,
        },
    ),
    'MainframeTestDataCollectionConfigurationComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'jsonFilePath': 's3://my-bucket/test-data/config.json',
                'dbJclFilePath': 's3://my-bucket/test-data/db.jcl',
                'vsamJclFilePath': 's3://my-bucket/test-data/vsam.jcl',
                'seqJclFilePath': 's3://my-bucket/test-data/seq.jcl',
            }
        ],
        json_schema={
            'title': 'MainframeTestDataCollectionConfigurationComponent Output',
            'description': 'Output schema for MainframeTestDataCollectionConfigurationComponent. Emitted on every keystroke as the user fills in S3 paths for the test data configuration files (JSON config and three JCL template files).',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'jsonFilePath': 's3://my-bucket/test-data/config.json',
                    'dbJclFilePath': 's3://my-bucket/test-data/db.jcl',
                    'vsamJclFilePath': 's3://my-bucket/test-data/vsam.jcl',
                    'seqJclFilePath': 's3://my-bucket/test-data/seq.jcl',
                }
            ],
            'properties': {
                'jsonFilePath': {
                    'type': 'string',
                    'description': 'S3 URI of the JSON configuration file describing test data collection parameters.',
                },
                'dbJclFilePath': {
                    'type': 'string',
                    'description': 'S3 URI of the DB JCL template file.',
                },
                'vsamJclFilePath': {
                    'type': 'string',
                    'description': 'S3 URI of the VSAM JCL template file.',
                },
                'seqJclFilePath': {
                    'type': 'string',
                    'description': 'S3 URI of the sequential file JCL template file.',
                },
            },
            'required': ['jsonFilePath', 'dbJclFilePath', 'vsamJclFilePath', 'seqJclFilePath'],
            'additionalProperties': True,
        },
    ),
    'MainframeTestDataCollectionReviewComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeTestDataCollectionReviewComponent Output',
            'description': 'Output schema for MainframeTestDataCollectionReviewComponent. This is a display-only component that shows generated test data collection scripts in a table with view/download actions. It does not call onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'MainframeTestDataCollectionSelectionComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'userSelectedTestCases': [
                    {
                        'name': 'TESTCASE001',
                        'businessFunction': 'Account Management',
                        'businessDomain': 'Banking',
                    }
                ]
            },
            {'resetTestCaseOrder': True},
            {'validateTestPlanAlertMessage': None},
        ],
        json_schema={
            'title': 'MainframeTestDataCollectionSelectionComponent Output',
            'description': 'Output schema for MainframeTestDataCollectionSelectionComponent. Emitted when the user selects test cases, dismisses an alert, or triggers a test case order reset. Multiple distinct payload shapes are emitted.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'userSelectedTestCases': [
                        {
                            'name': 'TESTCASE001',
                            'businessFunction': 'Account Management',
                            'businessDomain': 'Banking',
                        }
                    ]
                },
                {'resetTestCaseOrder': True},
                {'validateTestPlanAlertMessage': None},
            ],
            'properties': {
                'userSelectedTestCases': {
                    'type': 'array',
                    'description': 'Array of test case records currently selected by the user in the table. Emitted on every selection change.',
                    'items': {
                        'type': 'object',
                        'additionalProperties': True,
                        'properties': {
                            'name': {
                                'type': 'string',
                                'description': 'Test case name / identifier.',
                            },
                            'businessFunction': {
                                'type': 'string',
                                'description': 'Business function associated with the test case.',
                            },
                            'businessDomain': {
                                'type': 'string',
                                'description': 'Business domain associated with the test case.',
                            },
                        },
                    },
                },
                'resetTestCaseOrder': {
                    'type': 'boolean',
                    'description': 'When true, signals the backend to reset test case ordering to its default. Emitted when the user clicks the reset order button.',
                    'enum': [True],
                },
                'validateTestPlanAlertMessage': {
                    'description': 'Set to null when the user dismisses the validation alert banner.',
                    'type': 'null',
                },
            },
            'additionalProperties': True,
        },
    ),
    'MainframeTestPlanConfigureComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'businessLogicS3Path': 's3://my-bucket/bre-output/bre.zip'}],
        json_schema={
            'title': 'MainframeTestPlanConfigureComponent Output',
            'description': 'Output schema for MainframeTestPlanConfigureComponent. Emits the S3 path to the business-logic (BRE) zip file that will be used when running the test plan.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'businessLogicS3Path': 's3://my-bucket/bre-output/bre.zip'}],
            'properties': {
                'businessLogicS3Path': {
                    'type': 'string',
                    'description': 'S3 URI pointing to the business-logic zip file produced by a prior BRE step. Matches the placeholder format s3://bucket-name/bre.zip.',
                }
            },
            'required': ['businessLogicS3Path'],
            'additionalProperties': True,
        },
    ),
    'MainframeTestPlanCreateComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'userSelectedFiles': [
                    {
                        'name': 'PAYROLL',
                        'path': '/src/cobol/PAYROLL.cbl',
                        'businessFunction': 'Payroll Processing',
                        'jobGroup': 'BATCH01',
                        'domain': 'Finance',
                        'isGroup': False,
                        'parentPath': '/payroll-group',
                    }
                ]
            }
        ],
        json_schema={
            'title': 'MainframeTestPlanCreateComponent Output',
            'description': 'Output schema for MainframeTestPlanCreateComponent. Emits the entry-point records selected by the user as the scope for the test plan to be created.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'userSelectedFiles': [
                        {
                            'name': 'PAYROLL',
                            'path': '/src/cobol/PAYROLL.cbl',
                            'businessFunction': 'Payroll Processing',
                            'jobGroup': 'BATCH01',
                            'domain': 'Finance',
                            'isGroup': False,
                            'parentPath': '/payroll-group',
                        }
                    ]
                }
            ],
            'properties': {
                'userSelectedFiles': {
                    'type': 'array',
                    'description': 'TestCaseEntryPointRecord items selected by the user.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'Entry-point or group name'},
                            'path': {
                                'type': 'string',
                                'description': 'Unique path used as the table row key',
                            },
                            'businessFunction': {
                                'type': 'string',
                                'description': 'Business function label',
                            },
                            'jobGroup': {'type': 'string', 'description': 'Job group identifier'},
                            'domain': {'type': 'string', 'description': 'Domain classification'},
                            'isGroup': {
                                'type': 'boolean',
                                'description': 'True when this record represents a group row rather than a concrete entry point',
                            },
                            'parentPath': {
                                'type': 'string',
                                'description': 'Path of the parent group row; absent for top-level items',
                            },
                        },
                        'required': ['name', 'path'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': ['userSelectedFiles'],
            'additionalProperties': True,
        },
    ),
    'MainframeTestPlanValidateComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'resetTestCaseOrder': True},
            {'deleteTestCases': {'testCaseIds': ['tc-003', 'tc-007']}},
            {'preferredOrderTestCase': {'testCaseId': 'tc-005', 'newOrder': 2}},
            {
                'mergeTestCases': {
                    'testCaseName': 'Combined Payroll Run',
                    'testCaseIds': ['tc-001', 'tc-002'],
                }
            },
            {
                'newTestCase': {
                    'testCaseName': 'Payroll Year-End Run',
                    'entrypointIds': ['ep-001', 'ep-002'],
                }
            },
        ],
        json_schema={
            'title': 'MainframeTestPlanValidateComponent Output',
            'description': 'Output schema for MainframeTestPlanValidateComponent. Each user action emits exactly one of the following mutually-exclusive payload shapes: newTestCase (create), deleteTestCases (remove), mergeTestCases (merge), preferredOrderTestCase (reorder), or resetTestCaseOrder (reset).',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'resetTestCaseOrder': True},
                {'deleteTestCases': {'testCaseIds': ['tc-003', 'tc-007']}},
                {'preferredOrderTestCase': {'testCaseId': 'tc-005', 'newOrder': 2}},
                {
                    'mergeTestCases': {
                        'testCaseName': 'Combined Payroll Run',
                        'testCaseIds': ['tc-001', 'tc-002'],
                    }
                },
                {
                    'newTestCase': {
                        'testCaseName': 'Payroll Year-End Run',
                        'entrypointIds': ['ep-001', 'ep-002'],
                    }
                },
            ],
            'properties': {
                'newTestCase': {
                    'type': 'object',
                    'description': 'Present when the user creates a new test case. Mutually exclusive with all other properties.',
                    'properties': {
                        'testCaseName': {
                            'type': 'string',
                            'description': 'Name for the newly created test case.',
                        },
                        'entrypointIds': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Entry-point IDs to associate with the new test case.',
                        },
                    },
                    'required': ['testCaseName', 'entrypointIds'],
                    'additionalProperties': False,
                },
                'deleteTestCases': {
                    'type': 'object',
                    'description': 'Present when the user removes one or more test cases. Mutually exclusive with all other properties.',
                    'properties': {
                        'testCaseIds': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'IDs of the test cases to delete.',
                        }
                    },
                    'required': ['testCaseIds'],
                    'additionalProperties': False,
                },
                'mergeTestCases': {
                    'type': 'object',
                    'description': 'Present when the user merges two or more test cases into one. Mutually exclusive with all other properties.',
                    'properties': {
                        'testCaseName': {
                            'type': 'string',
                            'description': 'Name for the merged test case.',
                        },
                        'testCaseIds': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'minItems': 2,
                            'description': 'IDs of the test cases to merge (minimum 2).',
                        },
                    },
                    'required': ['testCaseName', 'testCaseIds'],
                    'additionalProperties': False,
                },
                'preferredOrderTestCase': {
                    'type': 'object',
                    'description': 'Present when the user changes the preferred execution order of a test case. Mutually exclusive with all other properties.',
                    'properties': {
                        'testCaseId': {
                            'type': 'string',
                            'description': 'ID of the test case whose order is being updated.',
                        },
                        'newOrder': {
                            'type': 'number',
                            'description': 'New preferred execution order (1-based).',
                        },
                    },
                    'required': ['testCaseId', 'newOrder'],
                    'additionalProperties': False,
                },
                'resetTestCaseOrder': {
                    'type': 'boolean',
                    'enum': [True],
                    'description': 'Present and true when the user resets all test cases to their default execution order. Mutually exclusive with all other properties.',
                },
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeTestScriptsGenerationProvideComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'data': 's3://my-bucket/test-scripts/testcases.json'}],
        json_schema={
            'title': 'MainframeTestScriptsGenerationProvideComponent Output',
            'description': "Output schema for MainframeTestScriptsGenerationProvideComponent. This component re-uses MainframeTestDataCollectionAddComponent with variant='scriptGeneration'. Emitted on every input change containing the S3 URI of the test plan JSON file.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'data': 's3://my-bucket/test-scripts/testcases.json'}],
            'properties': {
                'data': {
                    'type': 'string',
                    'description': 'S3 URI of the test plan JSON file (e.g. s3://bucket-name/mycode.json) to use for test script generation.',
                }
            },
            'required': ['data'],
            'additionalProperties': True,
        },
    ),
    'MainframeTestScriptsGenerationReviewComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeTestScriptsGenerationReviewComponent Output',
            'description': 'Output schema for MainframeTestScriptsGenerationReviewComponent. This is a display-only component that shows generated test automation scripts in a filterable table with S3 path copy support. It does not call onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'additionalProperties': True,
        },
    ),
    'MainframeTestScriptsGenerationSelectComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'userSelectedTestCases': [
                    {
                        'name': 'TESTCASE001',
                        'businessFunction': 'Account Management',
                        'businessDomain': 'Banking',
                    }
                ]
            },
            {'resetTestCaseOrder': True},
            {'validateTestPlanAlertMessage': None},
        ],
        json_schema={
            'title': 'MainframeTestScriptsGenerationSelectComponent Output',
            'description': "Output schema for MainframeTestScriptsGenerationSelectComponent. This component re-uses MainframeTestDataCollectionSelectionComponent with variant='scriptGeneration'. Emitted when the user selects test cases, dismisses an alert, or resets test case order.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'userSelectedTestCases': [
                        {
                            'name': 'TESTCASE001',
                            'businessFunction': 'Account Management',
                            'businessDomain': 'Banking',
                        }
                    ]
                },
                {'resetTestCaseOrder': True},
                {'validateTestPlanAlertMessage': None},
            ],
            'properties': {
                'userSelectedTestCases': {
                    'type': 'array',
                    'description': 'Array of test case records currently selected for test script generation. Emitted on every selection change.',
                    'items': {
                        'type': 'object',
                        'additionalProperties': True,
                        'properties': {
                            'name': {
                                'type': 'string',
                                'description': 'Test case name / identifier.',
                            },
                            'businessFunction': {
                                'type': 'string',
                                'description': 'Business function associated with the test case.',
                            },
                            'businessDomain': {
                                'type': 'string',
                                'description': 'Business domain associated with the test case.',
                            },
                        },
                    },
                },
                'resetTestCaseOrder': {
                    'type': 'boolean',
                    'description': 'When true, signals the backend to reset test case ordering to default.',
                    'enum': [True],
                },
                'validateTestPlanAlertMessage': {
                    'description': 'Set to null when the user dismisses the validation alert banner.',
                    'type': 'null',
                },
            },
            'additionalProperties': True,
        },
    ),
    'MainframeTestToolsComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'toolIds': ['tool-001', 'tool-042', 'tool-107']}, {'toolIds': []}],
        json_schema={
            'title': 'MainframeTestToolsComponent Output',
            'description': 'Output schema for MainframeTestToolsComponent. Emits the list of selected tool IDs whenever the user changes their selection in the tool selection table.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'toolIds': ['tool-001', 'tool-042', 'tool-107']}, {'toolIds': []}],
            'properties': {
                'toolIds': {
                    'type': 'array',
                    'description': 'Array of tool record IDs selected by the user from the test tools table.',
                    'items': {
                        'type': 'string',
                        'description': 'The unique identifier of a selected tool record.',
                    },
                }
            },
            'required': ['toolIds'],
            'additionalProperties': True,
        },
    ),
    'MainframeTransformationLaunchComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'domains': [{'id': 'domain_1', 'name': 'AccountManagement'}],
                'transformationEngineProperties': [
                    {
                        'label': 'General information',
                        'type': 'step',
                        'items': [
                            {
                                'label': 'Project name',
                                'type': 'text',
                                'id': 'project',
                                'propertySet': 'generate',
                                'value': 'app',
                            },
                            {
                                'label': 'Target database',
                                'type': 'select',
                                'id': 'target.database',
                                'propertySet': 'metadata',
                                'value': 'postgresql',
                            },
                        ],
                    },
                    {
                        'label': 'GS21',
                        'type': 'step',
                        'subSteps': [
                            {
                                'label': 'Fujitsu GS21',
                                'type': 'step',
                                'items': [
                                    {
                                        'label': 'GS21 legacy system',
                                        'type': 'checkbox',
                                        'id': 'legacy.system',
                                        'propertySet': 'metadata',
                                        'value': 'gs21',
                                    }
                                ],
                            }
                        ],
                    },
                ],
                'fileMetadataGroup': [
                    {'id': 'meta_1', 'file': '*.cob', 'value': 'key1=value1;key2=value2'}
                ],
            },
            [
                {'id': 'domain_1', 'name': 'AccountManagement'},
                {'id': 'domain_2', 'name': 'Payments'},
            ],
        ],
        json_schema={
            'title': 'MainframeTransformationLaunchComponent Output',
            'description': 'Output schema for MainframeTransformationLaunchComponent. Delegates onInputChange to the @amzn/blu-insights-ui-components TransformationLaunch library component, which emits domain selections and transformation configuration options chosen by the user.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'examples': [
                {
                    'domains': [{'id': 'domain_1', 'name': 'AccountManagement'}],
                    'transformationEngineProperties': [
                        {
                            'label': 'General information',
                            'type': 'step',
                            'items': [
                                {
                                    'label': 'Project name',
                                    'type': 'text',
                                    'id': 'project',
                                    'propertySet': 'generate',
                                    'value': 'app',
                                },
                                {
                                    'label': 'Target database',
                                    'type': 'select',
                                    'id': 'target.database',
                                    'propertySet': 'metadata',
                                    'value': 'postgresql',
                                },
                            ],
                        },
                        {
                            'label': 'GS21',
                            'type': 'step',
                            'subSteps': [
                                {
                                    'label': 'Fujitsu GS21',
                                    'type': 'step',
                                    'items': [
                                        {
                                            'label': 'GS21 legacy system',
                                            'type': 'checkbox',
                                            'id': 'legacy.system',
                                            'propertySet': 'metadata',
                                            'value': 'gs21',
                                        }
                                    ],
                                }
                            ],
                        },
                    ],
                    'fileMetadataGroup': [
                        {'id': 'meta_1', 'file': '*.cob', 'value': 'key1=value1;key2=value2'}
                    ],
                },
                [
                    {'id': 'domain_1', 'name': 'AccountManagement'},
                    {'id': 'domain_2', 'name': 'Payments'},
                ],
            ],
            'oneOf': [
                {
                    'type': 'object',
                    'description': 'Full output with domains, configuration properties and file metadata. Emitted when configuration is enabled.',
                    'properties': {
                        'domains': {
                            'type': 'array',
                            'description': 'Domains selected by the user for transformation.',
                            'items': {
                                'type': 'object',
                                'additionalProperties': True,
                                'properties': {
                                    'id': {'type': 'string'},
                                    'name': {'type': 'string'},
                                },
                            },
                        },
                        'transformationEngineProperties': {
                            'type': 'array',
                            'description': "Configuration wizard steps with engine-specific properties selected by the user. Structure mirrors the input schema's step definition.",
                            'items': {
                                'type': 'object',
                                'description': 'Step to be displayed in the configuration wizard',
                                'properties': {
                                    'label': {'type': 'string', 'description': 'Step label'},
                                    'description': {
                                        'type': 'string',
                                        'description': 'Step description',
                                    },
                                    'type': {
                                        'type': 'string',
                                        'description': 'Step type or substep',
                                    },
                                    'items': {
                                        'type': 'array',
                                        'description': 'Properties to be displayed in the wizard',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'label': {
                                                    'type': 'string',
                                                    'description': 'Label of the form field to be displayed',
                                                },
                                                'type': {
                                                    'type': 'string',
                                                    'description': 'Type of the form field, can be text, checkbox, select, etc.',
                                                },
                                                'id': {
                                                    'type': 'string',
                                                    'description': 'Id of the property, correspond to the property to be injected in configuration file',
                                                },
                                                'propertySet': {
                                                    'type': 'string',
                                                    'description': 'Property set of the property (metadata, transform or generate)',
                                                },
                                                'value': {
                                                    'description': 'Current value of the property, as set by the user',
                                                    'oneOf': [
                                                        {'type': 'string'},
                                                        {'type': 'boolean'},
                                                    ],
                                                },
                                            },
                                            'required': ['label', 'type', 'id'],
                                            'additionalProperties': True,
                                        },
                                    },
                                    'subSteps': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'label': {
                                                    'type': 'string',
                                                    'description': 'SubStep label',
                                                },
                                                'type': {
                                                    'type': 'string',
                                                    'description': 'Substep',
                                                },
                                                'items': {
                                                    'type': 'array',
                                                    'description': 'Properties to be displayed in the wizard',
                                                    'items': {
                                                        'type': 'object',
                                                        'properties': {
                                                            'label': {
                                                                'type': 'string',
                                                                'description': 'Label of the form field to be displayed',
                                                            },
                                                            'type': {
                                                                'type': 'string',
                                                                'description': 'Type of the form field, can be text, checkbox, select, etc.',
                                                            },
                                                            'id': {
                                                                'type': 'string',
                                                                'description': 'Id of the property, correspond to the property to be injected in configuration file',
                                                            },
                                                            'propertySet': {
                                                                'type': 'string',
                                                                'description': 'Property set of the property (metadata, transform or generate)',
                                                            },
                                                            'value': {
                                                                'description': 'Current value of the property, as set by the user',
                                                                'oneOf': [
                                                                    {'type': 'string'},
                                                                    {'type': 'boolean'},
                                                                ],
                                                            },
                                                        },
                                                        'required': ['label', 'type', 'id'],
                                                        'additionalProperties': True,
                                                    },
                                                },
                                            },
                                            'required': ['label', 'type', 'items'],
                                            'additionalProperties': False,
                                        },
                                    },
                                },
                                'required': ['label', 'type'],
                                'additionalProperties': False,
                            },
                        },
                        'fileMetadataGroup': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {
                                        'type': 'string',
                                        'description': 'The unique identifier of the file metadata.',
                                    },
                                    'file': {
                                        'type': 'string',
                                        'description': 'The file name pattern.',
                                    },
                                    'value': {
                                        'type': 'string',
                                        'description': 'A metadata string composed of key-value pairs separated by semicolons (e.g., key1=value1;key2=value2)',
                                    },
                                },
                                'required': ['id', 'file', 'value'],
                                'additionalProperties': False,
                            },
                        },
                    },
                    'required': [],
                    'additionalProperties': False,
                },
                {
                    'type': 'array',
                    'description': 'Plain array of domain objects. Emitted when configuration is disabled.',
                    'items': {
                        'type': 'object',
                        'additionalProperties': True,
                        'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}},
                    },
                },
            ],
            'additionalProperties': True,
        },
    ),
    'MainframeTransformationResults': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeTransformationResults Output',
            'description': 'Output schema for MainframeTransformationResults. Display-only component that displays the result of a transformation process.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MainframeUpdateServiceQuota': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MainframeUpdateServiceQuota Output',
            'description': 'Output schema for MainframeUpdateServiceQuota. Display-only component that instructs the user to raise their AWS service quota. onInputChange is not present in the component props; no output is produced.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MapTagging': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'mpeId': 'MPE-123456'}, {'mpeId': ''}],
        json_schema={
            'title': 'MapTagging Output',
            'description': 'Output schema for MapTagging. Collects the Migration Portfolio Experience (MPE) ID that the user enters or removes for MAP tagging. An empty string signals removal.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'mpeId': 'MPE-123456'}, {'mpeId': ''}],
            'properties': {
                'mpeId': {
                    'type': 'string',
                    'description': 'The MPE ID entered by the user. Empty string when the user removes the MPE ID.',
                }
            },
            'required': ['mpeId'],
            'additionalProperties': True,
        },
    ),
    'MarkReadyForCutover': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'terminateTestInstances': True}, {'reload': True}],
        json_schema={
            'title': 'MarkReadyForCutover Output',
            'description': "Output schema for MarkReadyForCutover. Collects the user's preference on whether to terminate test instances when marking servers ready for cutover, plus a reload flag when the Refresh button is clicked.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'terminateTestInstances': True}, {'reload': True}],
            'properties': {
                'terminateTestInstances': {
                    'type': 'boolean',
                    'description': 'Whether the user wants to terminate test instances when marking servers ready for cutover. Defaults to true.',
                },
                'reload': {
                    'type': 'boolean',
                    'description': 'Set to true when the user clicks Refresh to reload replication status data.',
                },
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MarkdownRendererComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'MarkdownRendererComponent Output',
            'description': 'Output schema for MarkdownRendererComponent. This is a display-only component that renders markdown content and does not produce output data.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'MigrationWavePlanner': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedFiles': [
                    {
                        'name': 'migration-wave-plan.csv',
                        'content': 'base64encodedcontent==',
                        'isZip': False,
                    }
                ]
            },
            {},
        ],
        json_schema={
            'title': 'MigrationWavePlanner Output',
            'description': 'Output schema for MigrationWavePlanner. Collects the uploaded migration wave plan CSV file. An empty object is emitted on success/error to flush the artifact.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedFiles': [
                        {
                            'name': 'migration-wave-plan.csv',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ]
                },
                {},
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded wave plan CSV/ZIP files encoded as base64.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ModernizationWaves': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'selectedWaves': [
                    {
                        'waveNumber': '1',
                        'transformationComplexity': 'LOW',
                        'dbItems': [
                            {
                                'dbName': 'orders',
                                'host': 'db-server-01.example.com',
                                'region': 'us-east-1',
                                'endpoint': 'db-server-01.example.com:1433',
                                'port': '1433',
                                'vpc': 'vpc-12345678',
                                'subnets': ['subnet-12345678'],
                                'securityGroups': ['sg-12345678'],
                                'instanceProfileArn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                                'sourceDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                                'sourceSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:source-ABCDEF',  # pragma: allowlist secret
                                'targetDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                                'targetSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:target-ABCDEF',  # pragma: allowlist secret
                                'dmsProjectArn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                                'tableNames': ['orders', 'order_items'],
                                'storedProcedures': 3,
                                'tables': 2,
                                'sizeInGB': 50,
                                'complexityScore': 30,
                                'dependentRepoList': [],
                            }
                        ],
                        'codeRepoList': [
                            {
                                'codeRepoName': 'my-app',
                                'branchName': 'main',
                                'isDotnet': False,
                                'usesSQL': True,
                                'isUsingDB': True,
                                'dbDependencies': ['orders'],
                                'tableDependencies': ['orders'],
                                'status': 'COMPLETED',
                                'statusMessage': '',
                                'complexityScore': 20,
                                'linesOfCode': 15000,
                                'numberOfProjects': 2,
                                'numberOfSolutions': 1,
                                'ownerName': 'MyOrg',
                                'supported': True,
                                'findings': [],
                            }
                        ],
                    }
                ]
            }
        ],
        json_schema={
            'title': 'ModernizationWaves Output',
            'description': 'Output schema for ModernizationWaves. Emits the list of waves selected by the user in the wave planning table.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'selectedWaves': [
                        {
                            'waveNumber': '1',
                            'transformationComplexity': 'LOW',
                            'dbItems': [
                                {
                                    'dbName': 'orders',
                                    'host': 'db-server-01.example.com',
                                    'region': 'us-east-1',
                                    'endpoint': 'db-server-01.example.com:1433',
                                    'port': '1433',
                                    'vpc': 'vpc-12345678',
                                    'subnets': ['subnet-12345678'],
                                    'securityGroups': ['sg-12345678'],
                                    'instanceProfileArn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                                    'sourceDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                                    'sourceSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:source-ABCDEF',  # pragma: allowlist secret
                                    'targetDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                                    'targetSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:target-ABCDEF',  # pragma: allowlist secret
                                    'dmsProjectArn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                                    'tableNames': ['orders', 'order_items'],
                                    'storedProcedures': 3,
                                    'tables': 2,
                                    'sizeInGB': 50,
                                    'complexityScore': 30,
                                    'dependentRepoList': [],
                                }
                            ],
                            'codeRepoList': [
                                {
                                    'codeRepoName': 'my-app',
                                    'branchName': 'main',
                                    'isDotnet': False,
                                    'usesSQL': True,
                                    'isUsingDB': True,
                                    'dbDependencies': ['orders'],
                                    'tableDependencies': ['orders'],
                                    'status': 'COMPLETED',
                                    'statusMessage': '',
                                    'complexityScore': 20,
                                    'linesOfCode': 15000,
                                    'numberOfProjects': 2,
                                    'numberOfSolutions': 1,
                                    'ownerName': 'MyOrg',
                                    'supported': True,
                                    'findings': [],
                                }
                            ],
                        }
                    ]
                }
            ],
            'properties': {
                'selectedWaves': {
                    'type': 'array',
                    'description': 'The list of waves selected (checked) by the user in the wave table.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'waveNumber': {'type': 'string', 'description': 'Wave identifier.'},
                            'transformationComplexity': {
                                'type': 'string',
                                'description': 'Overall complexity rating for this wave.',
                            },
                            'dbItems': {
                                'type': 'array',
                                'description': 'Database items assigned to this wave.',
                                'items': {'type': 'object'},
                            },
                            'codeRepoList': {
                                'type': 'array',
                                'description': 'Code repositories assigned to this wave.',
                                'items': {'type': 'object'},
                            },
                        },
                        'required': ['waveNumber'],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['selectedWaves'],
            'additionalProperties': True,
        },
    ),
    'PerformDiscovery': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedFiles': [
                    {
                        'name': 'rvtools-export.xlsx',
                        'content': 'base64encodedcontent==',
                        'isZip': False,
                    }
                ],
                'successfulUploadedFiles': [],
            },
            {'successfulUploadedFiles': [{'fileName': 'rvtools-export.xlsx'}]},
        ],
        json_schema={
            'title': 'PerformDiscovery Output',
            'description': 'Output schema for PerformDiscovery. Collects discovery data files uploaded by the user (RVTools, ModelizeIT, VMware NSX exports, import templates, etc.), plus a history of previously successful uploads.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedFiles': [
                        {
                            'name': 'rvtools-export.xlsx',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ],
                    'successfulUploadedFiles': [],
                },
                {'successfulUploadedFiles': [{'fileName': 'rvtools-export.xlsx'}]},
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Files currently being uploaded, encoded as base64.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {'type': 'boolean'},
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                },
                'successfulUploadedFiles': {
                    'type': 'array',
                    'description': 'History of previously successful file uploads. Each item contains only the file name.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'fileName': {
                                'type': 'string',
                                'description': 'Name of the successfully uploaded file',
                            }
                        },
                        'required': ['fileName'],
                        'additionalProperties': False,
                    },
                },
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'RepoBranchSelection': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'repositories': [
                    {
                        'repository_id': 'repo-001',
                        'repository_display_name': 'my-app',
                        'full_repository_id': 'MyOrg/my-app',
                        'owner_id': 'owner-001',
                        'owner_display_name': 'MyOrg',
                        'is_private': True,
                        'description': 'Main application repository',
                        'default_branch_name': 'main',
                        'size_in_bytes': 2097152,
                        'branches': ['main', 'develop', 'release/1.0'],
                        'assessment_branch': 'main',
                    }
                ]
            }
        ],
        json_schema={
            'title': 'RepoBranchSelection Output',
            'description': 'Output schema for RepoBranchSelection. Emits the list of repositories with their user-selected assessment branches.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'repositories': [
                        {
                            'repository_id': 'repo-001',
                            'repository_display_name': 'my-app',
                            'full_repository_id': 'MyOrg/my-app',
                            'owner_id': 'owner-001',
                            'owner_display_name': 'MyOrg',
                            'is_private': True,
                            'description': 'Main application repository',
                            'default_branch_name': 'main',
                            'size_in_bytes': 2097152,
                            'branches': ['main', 'develop', 'release/1.0'],
                            'assessment_branch': 'main',
                        }
                    ]
                }
            ],
            'properties': {
                'repositories': {
                    'type': 'array',
                    'description': 'List of repositories with their selected assessment branches.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'repository_id': {
                                'type': 'string',
                                'description': 'Unique repository identifier.',
                            },
                            'repository_display_name': {
                                'type': 'string',
                                'description': 'Human-readable repository name.',
                            },
                            'full_repository_id': {
                                'type': 'string',
                                'description': 'Full repository path (e.g. owner/repo-name).',
                            },
                            'owner_id': {'type': 'string', 'description': 'Owner identifier.'},
                            'owner_display_name': {
                                'type': 'string',
                                'description': 'Owner display name.',
                            },
                            'is_private': {
                                'type': 'boolean',
                                'description': 'Whether the repository is private.',
                            },
                            'description': {
                                'type': 'string',
                                'description': 'Repository description.',
                            },
                            'default_branch_name': {
                                'type': 'string',
                                'description': 'Default branch name.',
                            },
                            'size_in_bytes': {
                                'type': 'number',
                                'description': 'Repository size in bytes.',
                            },
                            'branches': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'All available branches.',
                            },
                            'assessment_branch': {
                                'type': 'string',
                                'description': 'The branch selected for assessment (may differ from default_branch_name).',
                            },
                        },
                        'required': ['repository_id', 'full_repository_id', 'assessment_branch'],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['repositories'],
            'additionalProperties': True,
        },
    ),
    'RepoDbSelection': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'selectedDatabases': [
                    {
                        'dbName': 'orders',
                        'host': 'db-server-01.example.com',
                        'region': 'us-east-1',
                        'endpoint': 'db-server-01.example.com:1433',
                        'port': '1433',
                        'vpc': 'vpc-12345678',
                        'subnets': ['subnet-12345678'],
                        'securityGroups': ['sg-12345678'],
                        'instanceProfileArn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                        'sourceDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                        'sourceSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:source-ABCDEF',  # pragma: allowlist secret
                        'targetDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                        'targetSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:target-ABCDEF',  # pragma: allowlist secret
                        'dmsProjectArn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                        'tableNames': ['orders', 'order_items'],
                        'storedProcedures': 2,
                        'tables': 2,
                        'sizeInGB': 25,
                        'complexityScore': 40,
                        'dependentRepoList': [],
                        'assessmentStatus': 'COMPLETED',
                        'codeAssessmentCompleted': True,
                    }
                ]
            }
        ],
        json_schema={
            'title': 'RepoDbSelection Output',
            'description': 'Output schema for RepoDbSelection. Emits the list of databases selected by the user in the assessment table.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'selectedDatabases': [
                        {
                            'dbName': 'orders',
                            'host': 'db-server-01.example.com',
                            'region': 'us-east-1',
                            'endpoint': 'db-server-01.example.com:1433',
                            'port': '1433',
                            'vpc': 'vpc-12345678',
                            'subnets': ['subnet-12345678'],
                            'securityGroups': ['sg-12345678'],
                            'instanceProfileArn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                            'sourceDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                            'sourceSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:source-ABCDEF',  # pragma: allowlist secret
                            'targetDataProviderArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                            'targetSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:target-ABCDEF',  # pragma: allowlist secret
                            'dmsProjectArn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                            'tableNames': ['orders', 'order_items'],
                            'storedProcedures': 2,
                            'tables': 2,
                            'sizeInGB': 25,
                            'complexityScore': 40,
                            'dependentRepoList': [],
                            'assessmentStatus': 'COMPLETED',
                            'codeAssessmentCompleted': True,
                        }
                    ]
                }
            ],
            'properties': {
                'selectedDatabases': {
                    'type': 'array',
                    'description': 'Databases selected by the user in the assessment table.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'dbName': {'type': 'string', 'description': 'Database name.'},
                            'host': {'type': 'string', 'description': 'Database server hostname.'},
                            'region': {'type': 'string', 'description': 'AWS region.'},
                            'endpoint': {'type': 'string', 'description': 'Connection endpoint.'},
                            'port': {'type': 'string', 'description': 'Database port.'},
                            'vpc': {'type': 'string', 'description': 'VPC identifier.'},
                            'subnets': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Subnet IDs.',
                            },
                            'securityGroups': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Security group IDs.',
                            },
                            'instanceProfileArn': {'type': 'string'},
                            'sourceDataProviderArn': {'type': 'string'},
                            'sourceSecretArn': {'type': 'string'},
                            'targetDataProviderArn': {'type': 'string'},
                            'targetSecretArn': {'type': 'string'},
                            'dmsProjectArn': {'type': 'string'},
                            'tableNames': {'type': 'array', 'items': {'type': 'string'}},
                            'storedProcedures': {'type': 'number'},
                            'tables': {'type': 'number'},
                            'sizeInGB': {'type': 'number'},
                            'complexityScore': {'type': 'number'},
                            'dependentRepoList': {'type': 'array', 'items': {'type': 'object'}},
                            'assessmentStatus': {
                                'type': 'string',
                                'description': 'DB assessment status (e.g. COMPLETED, FAILED, IN_PROGRESS).',
                            },
                            'codeAssessmentCompleted': {'type': 'boolean'},
                            'codeAssessmentSkipped': {'type': 'boolean'},
                        },
                        'required': ['dbName', 'host'],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['selectedDatabases'],
            'additionalProperties': True,
        },
    ),
    'RequestLatestInventory': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'RequestLatestInventory Output',
            'description': 'Output schema for RequestLatestInventory. Display-only component that prompts the user to request a refreshed inventory snapshot. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ResolvePrerequisiteErrors': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'ResolvePrerequisiteErrors Output',
            'description': 'Output schema for ResolvePrerequisiteErrors. Display-only component that shows prerequisite errors per server and instructs the user to fix them before retrying. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'RetryAgentInstallation': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'howToContinue': 'sameSecret'},
            {
                'howToContinue': 'differentSecret',
                'secretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret-AbCdEf',  # pragma: allowlist secret
            },
        ],
        json_schema={
            'title': 'RetryAgentInstallation Output',
            'description': "Output schema for RetryAgentInstallation. Collects the user's choice on how to retry MGN agent installation: using the same Secrets Manager secret or a different one. When choosing a different secret, the selected secret ARN is included.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'howToContinue': 'sameSecret'},
                {
                    'howToContinue': 'differentSecret',
                    'secretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret-AbCdEf',  # pragma: allowlist secret
                },
            ],
            'properties': {
                'howToContinue': {
                    'type': 'string',
                    'enum': ['sameSecret', 'differentSecret'],
                    'description': 'Whether to retry using the same Secrets Manager secret or a different one.',
                },
                'secretArn': {
                    'type': 'string',
                    'description': "The ARN of the replacement secret. Only present when howToContinue is 'differentSecret'.",
                },
            },
            'required': ['howToContinue'],
            'additionalProperties': True,
        },
    ),
    'RetryPrerequisiteVerification': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'howToContinue': 'sameSecret'},
            {
                'howToContinue': 'differentSecret',
                'secretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret-AbCdEf',  # pragma: allowlist secret
            },
        ],
        json_schema={
            'title': 'RetryPrerequisiteVerification Output',
            'description': "Output schema for RetryPrerequisiteVerification. Collects the user's choice on how to retry prerequisite verification: using the same Secrets Manager secret or a different one. When choosing a different secret, the selected secret ARN is included.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'howToContinue': 'sameSecret'},
                {
                    'howToContinue': 'differentSecret',
                    'secretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret-AbCdEf',  # pragma: allowlist secret
                },
            ],
            'properties': {
                'howToContinue': {
                    'type': 'string',
                    'enum': ['sameSecret', 'differentSecret'],
                    'description': 'Whether to retry verification using the same Secrets Manager secret or a different one.',
                },
                'secretArn': {
                    'type': 'string',
                    'description': "The ARN of the replacement secret. Only present when howToContinue is 'differentSecret'.",
                },
            },
            'required': ['howToContinue'],
            'additionalProperties': True,
        },
    ),
    'ReviewAdditionalVpcConfigurationOptions': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'ReviewAdditionalVpcConfigurationOptions Output',
            'description': 'Output schema for ReviewAdditionalVpcConfigurationOptions. Display-only component presenting optional VPC configuration topics (third-party firewalls, VPC traffic mirroring, IPAM). No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewAppsAndWaves': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedFiles': [
                    {
                        'name': 'apps-and-waves.csv',
                        'content': 'base64encodedcontent==',
                        'isZip': False,
                    }
                ]
            },
            {},
        ],
        json_schema={
            'title': 'ReviewAppsAndWaves Output',
            'description': 'Output schema for ReviewAppsAndWaves. Collects the uploaded applications-and-waves CSV file after the user has reviewed and modified it. An empty object is emitted after a successful upload to flush the artifact.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedFiles': [
                        {
                            'name': 'apps-and-waves.csv',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ]
                },
                {},
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded application/wave assignment CSV files encoded as base64.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewAwsMigrationBusinessCase': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{}, {'retry': True}],
        json_schema={
            'title': 'ReviewAwsMigrationBusinessCase Output',
            'description': 'Output schema for ReviewAwsMigrationBusinessCase. Normal flow: approve with no content (empty {}). Only set {"retry": true} if the report generation failed and the user wants to retry.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}, {'retry': True}],
            'properties': {
                'retry': {
                    'type': 'boolean',
                    'description': 'Set to true when the user requests a retry of the business case report generation after an error. Not present in normal approve flow.',
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewMgnInventory': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedFiles': [
                    {
                        'name': 'mgn-inventory.csv',
                        'content': 'base64encodedcontent==',
                        'isZip': False,
                    }
                ]
            },
            {},
        ],
        json_schema={
            'title': 'ReviewMgnInventory Output',
            'description': 'Output schema for ReviewMgnInventory. Collects the updated MGN inventory CSV uploaded by the user after reviewing EC2 instance types, subnets, and security groups. An empty object is emitted after a successful upload to flush the artifact.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedFiles': [
                        {
                            'name': 'mgn-inventory.csv',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ]
                },
                {},
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded MGN inventory CSV files encoded as base64.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewMigrationPlan': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'uploadedFiles': [
                    {
                        'name': 'migration-plan-wave1.csv',
                        'content': 'base64encodedcontent==',
                        'isZip': False,
                    }
                ]
            }
        ],
        json_schema={
            'title': 'ReviewMigrationPlan Output',
            'description': 'Output schema for ReviewMigrationPlan. Collects the final reviewed and uploaded migration plan CSV file for a specific wave. Delegates file uploads to FileUploaderWithDisableMode.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'uploadedFiles': [
                        {
                            'name': 'migration-plan-wave1.csv',
                            'content': 'base64encodedcontent==',
                            'isZip': False,
                        }
                    ]
                }
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'Array of uploaded migration plan CSV files encoded as base64.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'File name'},
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'Whether the file is a zip archive',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewMigrationPlanPostSubnetAugmentation': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'ReviewMigrationPlanPostSubnetAugmentation Output',
            'description': 'Output schema for ReviewMigrationPlanPostSubnetAugmentation. Display-only component showing post-subnet-augmentation migration plan details, replication instructions, and test/cutover links. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewOnPremisesData': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'howToContinue': 'continue'}, {'howToContinue': 'reevaluate'}],
        json_schema={
            'title': 'ReviewOnPremisesData Output',
            'description': "Output schema for ReviewOnPremisesData. Collects the user's decision on how to proceed after reviewing on-premises discovery data: either reevaluate (collect more data) or continue to generate waves.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{'howToContinue': 'continue'}, {'howToContinue': 'reevaluate'}],
            'properties': {
                'howToContinue': {
                    'type': 'string',
                    'enum': ['continue', 'reevaluate'],
                    'description': "'continue' proceeds to generate application groupings and waves; 'reevaluate' returns to data collection.",
                }
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewReplicationStatus': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'ReviewReplicationStatus Output',
            'description': 'Output schema for ReviewReplicationStatus. Display-only component showing the replication health status table for all applications. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ReviewVpcConfiguration': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'automaticDeploy': True},
            {'automaticDeploy': False, 'outputTypes': ['CDK_L1']},
            {'vpcConfigurations': [{'name': 'vpc-prod', 'cidrBlock': '10.0.0.0/16'}]},
            {},
        ],
        json_schema={
            'title': 'ReviewVpcConfiguration Output',
            'description': "Output schema for ReviewVpcConfiguration. Collects the user's VPC deployment decision: whether to auto-deploy via AWS Transform or deploy on their own, and optionally modified VPC CIDR blocks and output format for code-gen deployments.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'automaticDeploy': True},
                {'automaticDeploy': False, 'outputTypes': ['CDK_L1']},
                {'vpcConfigurations': [{'name': 'vpc-prod', 'cidrBlock': '10.0.0.0/16'}]},
                {},
            ],
            'properties': {
                'automaticDeploy': {
                    'type': 'boolean',
                    'description': 'True when the user chose to let AWS Transform deploy the VPC networks automatically; false when the user will deploy on their own.',
                },
                'outputTypes': {
                    'type': 'array',
                    'description': 'Code-gen output format(s) chosen by the user when automaticDeploy is false and code-gen is enabled.',
                    'items': {'type': 'string', 'enum': ['CDK_L1', 'CDK_L2', 'LZA', 'TERRAFORM']},
                },
                'vpcConfigurations': {
                    'type': 'array',
                    'description': 'Modified VPC configurations when the user chose to adjust CIDR blocks before regenerating.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'includedInDeployment': {'type': 'boolean'},
                            'networkEntities': {
                                'type': 'array',
                                'items': {'type': 'object'},
                                'description': 'Network entities associated with this VPC',
                            },
                            'description': {'type': 'string'},
                            'cidrBlock': {'type': 'string'},
                        },
                        'additionalProperties': True,
                    },
                },
            },
            'required': [],
            'additionalProperties': True,
        },
    ),
    'SchemaConversionTable': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'items': [
                    {
                        'id': 'conv-001',
                        'sourceDatabaseName': 'orders',
                        'sourceDatabaseServer': 'db-server-01.example.com',
                        'targetDatabaseName': 'orders_aurora',
                        'conversionStatus': {
                            'status': 'success',
                            'percentage': 95,
                            'storageObjectConverted': 48,
                            'storageObjectTotal': 50,
                            'codeObjectConverted': 120,
                            'codeObjectTotal': 130,
                            'totalIssues': 5,
                        },
                        'artifactId': 'artifact-conv-001',
                        'conversionStatusMessage': '95% of objects converted successfully',
                        'dmsProjectLink': 'https://console.aws.amazon.com/dms/v2/home#schema-conversion/projects/ABCDEF',
                    }
                ]
            }
        ],
        json_schema={
            'title': 'SchemaConversionTable Output',
            'description': "Output schema for SchemaConversionTable. Emits the filtered list of schema conversion items representing the user's selection (only successful/warning items, or fixed items based on user actions). When a retry is initiated, emits selected items with retry=true.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'items': [
                        {
                            'id': 'conv-001',
                            'sourceDatabaseName': 'orders',
                            'sourceDatabaseServer': 'db-server-01.example.com',
                            'targetDatabaseName': 'orders_aurora',
                            'conversionStatus': {
                                'status': 'success',
                                'percentage': 95,
                                'storageObjectConverted': 48,
                                'storageObjectTotal': 50,
                                'codeObjectConverted': 120,
                                'codeObjectTotal': 130,
                                'totalIssues': 5,
                            },
                            'artifactId': 'artifact-conv-001',
                            'conversionStatusMessage': '95% of objects converted successfully',
                            'dmsProjectLink': 'https://console.aws.amazon.com/dms/v2/home#schema-conversion/projects/ABCDEF',
                        }
                    ]
                }
            ],
            'properties': {
                'items': {
                    'type': 'array',
                    'description': "Filtered list of schema conversion items. In summary-data mode (storageObject/codeObject counts present) this includes all user-selected rows. In legacy mode (no summary data) this includes only items with status SUCCESS or WARNING, plus items the user marked as 'fixed'.",
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string', 'description': 'Unique item identifier.'},
                            'sourceDatabaseName': {
                                'type': 'string',
                                'description': 'Source database name.',
                            },
                            'sourceDatabaseServer': {
                                'type': 'string',
                                'description': 'Source database server hostname.',
                            },
                            'targetDatabaseName': {
                                'type': 'string',
                                'description': 'Target database name.',
                            },
                            'conversionStatus': {
                                'type': 'object',
                                'description': 'Conversion status details.',
                                'properties': {
                                    'status': {
                                        'type': 'string',
                                        'description': 'Conversion status enum value.',
                                        'enum': [
                                            'success',
                                            'warning',
                                            'error',
                                            'info',
                                            'In progress',
                                        ],
                                    },
                                    'percentage': {
                                        'type': 'number',
                                        'description': 'Conversion completion percentage (0-100).',
                                    },
                                    'storageObjectConverted': {'type': 'number'},
                                    'storageObjectTotal': {'type': 'number'},
                                    'codeObjectConverted': {'type': 'number'},
                                    'codeObjectTotal': {'type': 'number'},
                                    'totalIssues': {'type': 'number'},
                                    'errorPopover': {
                                        'type': 'object',
                                        'properties': {
                                            'errorType': {'type': 'string'},
                                            'errorDetails': {'type': 'string'},
                                            'errorFix': {'type': 'string'},
                                        },
                                        'additionalProperties': False,
                                    },
                                    'partialConversionPopover': {
                                        'type': 'object',
                                        'properties': {
                                            'details': {'type': 'string'},
                                            'fix': {'type': 'string'},
                                        },
                                        'additionalProperties': False,
                                    },
                                },
                                'required': ['status'],
                                'additionalProperties': False,
                            },
                            'artifactId': {
                                'type': 'string',
                                'description': 'Artifact ID for downloading the conversion report.',
                            },
                            'conversionStatusMessage': {
                                'type': 'string',
                                'description': 'Human-readable status message.',
                            },
                            'dmsProjectLink': {
                                'type': 'string',
                                'description': 'URL to the DMS schema conversion project.',
                            },
                            'retry': {
                                'type': 'boolean',
                                'description': 'Set to true when item is queued for retry.',
                            },
                        },
                        'required': [
                            'id',
                            'sourceDatabaseName',
                            'sourceDatabaseServer',
                            'conversionStatus',
                        ],
                        'additionalProperties': False,
                    },
                }
            },
            'required': ['items'],
            'additionalProperties': True,
        },
    ),
    'SchemaConversionTargets': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'servers': [
                    {
                        'server_name': 'db-server-01.example.com',
                        'databases': ['orders', 'inventory'],
                        'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                        'source_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:source-ABCDEF',  # pragma: allowlist secret
                        'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:target-ABCDEF',  # pragma: allowlist secret
                        'port': 1433,
                        'region': 'us-east-1',
                        'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                        'security_groups': ['sg-12345678'],
                        'subnets': 'subnet-12345678,subnet-87654321',
                        'cluster_identifier': 'my-aurora-cluster',
                        'instance_identifier': 'my-aurora-instance',
                        'database_name': 'orders_target',
                        'instance_class': 'db.r5.large',
                        'vpc_id': 'vpc-12345678',
                        'public_access': False,
                        'create_new': True,
                        'target_engine': 'Aurora',
                    }
                ]
            }
        ],
        json_schema={
            'title': 'SchemaConversionTargets Output',
            'description': "Output schema for SchemaConversionTargets. Emits the list of server infos that correspond to the user's selected schema conversion targets. Target database details (cluster, instance, secret ARN, etc.) are included when the user has confirmed a target selection for a server.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'servers': [
                        {
                            'server_name': 'db-server-01.example.com',
                            'databases': ['orders', 'inventory'],
                            'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                            'source_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:source-ABCDEF',  # pragma: allowlist secret
                            'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:target-ABCDEF',  # pragma: allowlist secret
                            'port': 1433,
                            'region': 'us-east-1',
                            'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                            'security_groups': ['sg-12345678'],
                            'subnets': 'subnet-12345678,subnet-87654321',
                            'cluster_identifier': 'my-aurora-cluster',
                            'instance_identifier': 'my-aurora-instance',
                            'database_name': 'orders_target',
                            'instance_class': 'db.r5.large',
                            'vpc_id': 'vpc-12345678',
                            'public_access': False,
                            'create_new': True,
                            'target_engine': 'Aurora',
                        }
                    ]
                }
            ],
            'properties': {
                'servers': {
                    'type': 'array',
                    'description': 'List of selected server infos with target database configuration filled in.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'server_name': {
                                'type': 'string',
                                'description': 'Source server name (unique identifier).',
                            },
                            'databases': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'List of databases on this server.',
                            },
                            'dms_project_arn': {'type': 'string'},
                            'source_secret_arn': {'type': 'string'},
                            'target_secret_arn': {'type': 'string'},
                            'port': {'type': 'number'},
                            'region': {'type': 'string'},
                            'instance_profile_arn': {'type': 'string'},
                            'security_groups': {'type': 'array', 'items': {'type': 'string'}},
                            'subnets': {
                                'type': 'string',
                                'description': 'Comma-separated subnet IDs.',
                            },
                            'cluster_identifier': {
                                'type': 'string',
                                'description': 'Aurora cluster identifier.',
                            },
                            'instance_identifier': {
                                'type': 'string',
                                'description': 'Aurora instance identifier.',
                            },
                            'database_name': {
                                'type': 'string',
                                'description': 'Target database name.',
                            },
                            'instance_class': {
                                'type': 'string',
                                'description': 'Aurora instance class (e.g. db.r5.large).',
                            },
                            'vpc_id': {'type': 'string'},
                            'public_access': {'type': 'boolean'},
                            'create_new': {
                                'type': 'boolean',
                                'description': 'Whether to create a new target cluster.',
                            },
                            'target_engine': {
                                'type': 'string',
                                'description': 'Target engine type (e.g. Aurora, RDS).',
                            },
                            'cluster_arn': {
                                'type': 'string',
                                'description': 'ARN of an existing cluster (when create_new is false).',
                            },
                            'error_message': {
                                'type': 'string',
                                'description': 'Error message if the server has a configuration issue.',
                            },
                        },
                        'required': ['server_name'],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['servers'],
            'additionalProperties': True,
        },
    ),
    'SelectAndApproveWaves': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'waves': [{'waveName': 'Wave 1', 'waveStatus': 'Ready', 'applications': []}],
                'targetAccount': '123456789012',
            }
        ],
        json_schema={
            'title': 'SelectAndApproveWaves Output',
            'description': 'Output schema for SelectAndApproveWaves. Collects the set of migration waves the user has selected and approved for execution, along with the target AWS account.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'waves': [{'waveName': 'Wave 1', 'waveStatus': 'Ready', 'applications': []}],
                    'targetAccount': '123456789012',
                }
            ],
            'properties': {
                'waves': {
                    'type': 'array',
                    'description': 'The list of wave objects selected/approved by the user.',
                    'items': {'type': 'object', 'additionalProperties': True},
                },
                'targetAccount': {
                    'type': 'string',
                    'description': 'The AWS account ID that the selected waves will be migrated to.',
                },
            },
            'required': ['waves', 'targetAccount'],
            'additionalProperties': True,
        },
    ),
    'SelectDropdownComponent': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'SelectDropdownComponent Output',
            'description': 'Output schema for SelectDropdownComponent. This component does not call onInputChange; selected values are delivered through the HITL submit flow.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'SetEc2RecommendationPreference': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'cpuPercentage': 50,
                'offeringClass': 'STANDARD',
                'percentile': 95,
                'purchasingOption': 'ALL_UPFRONT',
                'ramPercentage': 50,
                'selectedExcludedInstanceTypes': ['t2.micro', 't3.nano'],
                'serverSpecMatchType': 'DIRECT',
                'sizingType': 'PERCENTILE',
                'tenancy': 'SHARED',
                'termLength': 'THREE_YEAR',
                'ipAssignmentStrategy': 'STATIC',
                'enableDefaultSubnetRemovalFlag': False,
                'selectedStagingAreaSubnetId': None,
            }
        ],
        json_schema={
            'title': 'SetEc2RecommendationPreference Output',
            'description': 'Output schema for SetEc2RecommendationPreference. Collects the full EC2 sizing and reservation preference state that drives the EC2 recommendation engine.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'cpuPercentage': 50,
                    'offeringClass': 'STANDARD',
                    'percentile': 95,
                    'purchasingOption': 'ALL_UPFRONT',
                    'ramPercentage': 50,
                    'selectedExcludedInstanceTypes': ['t2.micro', 't3.nano'],
                    'serverSpecMatchType': 'DIRECT',
                    'sizingType': 'PERCENTILE',
                    'tenancy': 'SHARED',
                    'termLength': 'THREE_YEAR',
                    'ipAssignmentStrategy': 'STATIC',
                    'enableDefaultSubnetRemovalFlag': False,
                    'selectedStagingAreaSubnetId': None,
                }
            ],
            'properties': {
                'cpuPercentage': {
                    'type': 'number',
                    'description': 'CPU utilization percentile override (0-100). 0 means use raw spec.',
                },
                'offeringClass': {
                    'type': 'string',
                    'enum': ['STANDARD', 'CONVERTIBLE'],
                    'description': 'Reserved Instance offering class.',
                },
                'percentile': {
                    'type': 'number',
                    'description': 'Percentile to use when sizingType is PERCENTILE (e.g. 95).',
                },
                'purchasingOption': {
                    'type': 'string',
                    'enum': ['ALL_UPFRONT', 'NO_UPFRONT', 'PARTIAL_UPFRONT'],
                    'description': 'Reserved Instance purchasing option.',
                },
                'ramPercentage': {
                    'type': 'number',
                    'description': 'RAM utilization percentile override (0-100). 0 means use raw spec.',
                },
                'selectedExcludedInstanceTypes': {
                    'type': 'array',
                    'description': 'EC2 instance type families or specific types to exclude from recommendations.',
                    'items': {'type': 'string'},
                },
                'serverSpecMatchType': {
                    'type': 'string',
                    'enum': ['DIRECT', 'CUSTOM'],
                    'description': 'Whether to match server specs directly or use custom CPU/RAM overrides.',
                },
                'sizingType': {
                    'type': ['string', 'null'],
                    'enum': ['AVG', 'MAX', 'PERCENTILE', 'SPEC', None],
                    'description': 'The EC2 sizing method to apply.',
                },
                'tenancy': {
                    'type': 'string',
                    'enum': ['SHARED', 'DEDICATED'],
                    'description': 'EC2 tenancy preference.',
                },
                'termLength': {
                    'type': 'string',
                    'enum': ['ONE_YEAR', 'THREE_YEAR'],
                    'description': 'Reserved Instance term length.',
                },
                'ipAssignmentStrategy': {
                    'type': 'string',
                    'enum': ['STATIC', 'DYNAMIC'],
                    'description': 'IP assignment strategy for migrated instances. Only present when enableFlexibleIp is true.',
                },
                'enableDefaultSubnetRemovalFlag': {
                    'type': 'boolean',
                    'description': 'Whether the staging area subnet selection feature is enabled.',
                },
                'selectedStagingAreaSubnetId': {
                    'type': ['string', 'null'],
                    'description': 'The subnet ID chosen as the MGN staging area. Only relevant when enableDefaultSubnetRemovalFlag is true.',
                },
            },
            'required': [
                'cpuPercentage',
                'offeringClass',
                'percentile',
                'purchasingOption',
                'ramPercentage',
                'serverSpecMatchType',
                'tenancy',
                'termLength',
            ],
            'additionalProperties': True,
        },
    ),
    'SetupServicePermissions': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'SetupServicePermissions Output',
            'description': 'Output schema for SetupServicePermissions. Display-only component showing instructions to set up MGN service permissions and a copyable console link. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'ShareOnPremisesServerDataWithStorageAndCollector': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'targetRegion': 'us-east-1'},
            {
                'uploadedFiles': [
                    {
                        'name': 'rvtools-export.xlsx',
                        'content': '<base64-encoded-content>',
                        'isZip': False,
                    }
                ],
                'location': 'FLOW_CHOICE_WITHOUT_STORAGE',
            },
        ],
        json_schema={
            'title': 'ShareOnPremisesServerDataWithStorageAndCollector Output',
            'description': 'Output schema for ShareOnPremisesServerDataWithStorageAndCollector. Emits two distinct payload shapes depending on user action: a file upload payload (with uploaded files and the current UI location) or a region selection payload (with the target AWS region).',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'targetRegion': 'us-east-1'},
                {
                    'uploadedFiles': [
                        {
                            'name': 'rvtools-export.xlsx',
                            'content': '<base64-encoded-content>',
                            'isZip': False,
                        }
                    ],
                    'location': 'FLOW_CHOICE_WITHOUT_STORAGE',
                },
            ],
            'properties': {
                'uploadedFiles': {
                    'type': 'array',
                    'description': 'List of files uploaded by the user, each encoded as base64. Present only when the user completes a file upload.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {
                                'type': 'string',
                                'description': 'Original filename of the uploaded file.',
                            },
                            'content': {
                                'type': 'string',
                                'description': 'Base64-encoded file content (without the data URI prefix).',
                            },
                            'isZip': {
                                'type': 'boolean',
                                'description': 'True if the file is a ZIP archive.',
                            },
                        },
                        'required': ['name', 'content', 'isZip'],
                        'additionalProperties': False,
                    },
                },
                'location': {
                    'type': 'string',
                    'description': "The UI flow location at the time of file upload (e.g. 'FLOW_CHOICE_WITHOUT_STORAGE'). Present alongside uploadedFiles.",
                },
                'targetRegion': {
                    'type': 'string',
                    'description': "The AWS region selected by the user (e.g. 'us-east-1'). Present when the user selects a target region.",
                },
            },
            'additionalProperties': True,
        },
    ),
    'SpecifyAssetsLocation': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'assetLocation': 's3://my-bucket/mainframe-assets/',
                'optInChatBox': True,
                'enableFeatures': ['CHAT_EXPERIENCE'],
            },
            {'isDownloadButtonClicked': True, 'assetLocation': 's3://my-bucket/mainframe-assets/'},
        ],
        json_schema={
            'title': 'SpecifyAssetsLocation Output',
            'description': 'Output schema for SpecifyAssetsLocation. Emits the S3 path entered by the user, an opt-in flag for the Amazon Q chat experience, and the set of enabled feature flags. An additional shape is emitted when the user clicks the Download Tools button.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'assetLocation': 's3://my-bucket/mainframe-assets/',
                    'optInChatBox': True,
                    'enableFeatures': ['CHAT_EXPERIENCE'],
                },
                {
                    'isDownloadButtonClicked': True,
                    'assetLocation': 's3://my-bucket/mainframe-assets/',
                },
            ],
            'properties': {
                'assetLocation': {
                    'type': 'string',
                    'description': 'S3 URI entered by the user pointing to the mainframe assets location.',
                },
                'optInChatBox': {
                    'type': 'boolean',
                    'description': 'Whether the user has opted in to the Amazon Q chat experience. Always false when enableChatExperienceBox is false.',
                },
                'enableFeatures': {
                    'type': 'array',
                    'description': 'List of feature flag names that are currently enabled. Derived from getEnabledFeatures(). Present in the standard emit; absent in the download-button emit.',
                    'items': {'type': 'string'},
                },
                'isDownloadButtonClicked': {
                    'type': 'boolean',
                    'description': 'Present and true only when the user clicks the Download Tools button. When present, only assetLocation is also included.',
                },
            },
            'required': ['assetLocation'],
            'additionalProperties': True,
        },
    ),
    'StartFinalizingCutover': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'StartFinalizingCutover Output',
            'description': 'Output schema for StartFinalizingCutover. Display-only component presenting the finalize-cutover confirmation screen with optional links to review launched instances or revert the cutover. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'StartReplicationAgentDeployment': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {'installationType': 'customerSelfInstall'},
            {
                'installationType': 'QInstall',
                'mgnConnectorArn': 'arn:aws:mgn:us-east-1:123456789012:connector/mgn-connector-0123456789abcdef0',
                'secretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:MgnAgentSecret-AbCdEf',  # pragma: allowlist secret
            },
        ],
        json_schema={
            'title': 'StartReplicationAgentDeployment Output',
            'description': "Output schema for StartReplicationAgentDeployment. Collects the user's choice of installation type (automated via AWS Transform or customer self-install), and when automating, the selected MGN connector ARN and Secrets Manager secret ARN.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'installationType': 'customerSelfInstall'},
                {
                    'installationType': 'QInstall',
                    'mgnConnectorArn': 'arn:aws:mgn:us-east-1:123456789012:connector/mgn-connector-0123456789abcdef0',
                    'secretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:MgnAgentSecret-AbCdEf',  # pragma: allowlist secret
                },
            ],
            'properties': {
                'installationType': {
                    'type': 'string',
                    'enum': ['QInstall', 'customerSelfInstall'],
                    'description': "'QInstall' means AWS Transform will automate agent deployment; 'customerSelfInstall' means the customer will deploy the agents themselves.",
                },
                'mgnConnectorArn': {
                    'type': 'string',
                    'description': "ARN of the selected MGN connector. Only present when installationType is 'QInstall'.",
                },
                'secretArn': {
                    'type': 'string',
                    'description': "ARN of the selected Secrets Manager secret containing server credentials. Only present when installationType is 'QInstall'.",
                },
            },
            'required': ['installationType'],
            'additionalProperties': True,
        },
    ),
    'SyntheticDataGenerationStatus': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'syntheticDataGenerationItem': [
                    {
                        'dbName': 'orders',
                        'dataStrategy': 'CLONE',
                        'status': 'COMPLETED',
                        'targetCluster': 'my-aurora-cluster',
                        'ddlScriptUrl': 's3://my-bucket/ddl/orders.sql',
                        'artifactId': 'artifact-001',
                    }
                ],
                'selectedSyntheticDataGenerationItems': [
                    {
                        'dbName': 'orders',
                        'dataStrategy': 'CLONE',
                        'status': 'COMPLETED',
                        'targetCluster': 'my-aurora-cluster',
                        'ddlScriptUrl': 's3://my-bucket/ddl/orders.sql',
                        'artifactId': 'artifact-001',
                    }
                ],
            }
        ],
        json_schema={
            'title': 'SyntheticDataGenerationStatus Output',
            'description': 'Output schema for SyntheticDataGenerationStatus. Emits all synthetic data generation items and the user-selected subset. When a retry action is triggered, also includes action and retryStatus fields.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'syntheticDataGenerationItem': [
                        {
                            'dbName': 'orders',
                            'dataStrategy': 'CLONE',
                            'status': 'COMPLETED',
                            'targetCluster': 'my-aurora-cluster',
                            'ddlScriptUrl': 's3://my-bucket/ddl/orders.sql',
                            'artifactId': 'artifact-001',
                        }
                    ],
                    'selectedSyntheticDataGenerationItems': [
                        {
                            'dbName': 'orders',
                            'dataStrategy': 'CLONE',
                            'status': 'COMPLETED',
                            'targetCluster': 'my-aurora-cluster',
                            'ddlScriptUrl': 's3://my-bucket/ddl/orders.sql',
                            'artifactId': 'artifact-001',
                        }
                    ],
                }
            ],
            'properties': {
                'syntheticDataGenerationItem': {
                    'type': 'array',
                    'description': 'Full list of all synthetic data generation items.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'dbName': {'type': 'string', 'description': 'Database name.'},
                            'dataStrategy': {
                                'type': 'string',
                                'description': 'Data strategy used (e.g. CLONE, GENERATE).',
                            },
                            'status': {
                                'type': 'string',
                                'description': 'Generation status (e.g. COMPLETED, FAILED, IN_PROGRESS).',
                            },
                            'targetCluster': {
                                'type': 'string',
                                'description': 'Target Aurora cluster identifier.',
                            },
                            'errorMessage': {
                                'type': 'string',
                                'description': 'Error message if generation failed.',
                            },
                            'ddlScriptUrl': {
                                'type': 'string',
                                'description': 'S3 URL to the DDL script.',
                            },
                            'artifactId': {
                                'type': 'string',
                                'description': 'Artifact ID for downloading generation results.',
                            },
                        },
                        'required': ['dbName', 'dataStrategy', 'status', 'targetCluster'],
                        'additionalProperties': False,
                    },
                },
                'selectedSyntheticDataGenerationItems': {
                    'type': 'array',
                    'description': 'User-selected subset of synthetic data generation items.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'dbName': {'type': 'string'},
                            'dataStrategy': {'type': 'string'},
                            'status': {'type': 'string'},
                            'targetCluster': {'type': 'string'},
                            'errorMessage': {'type': 'string'},
                            'ddlScriptUrl': {'type': 'string'},
                            'artifactId': {'type': 'string'},
                        },
                        'required': ['dbName', 'dataStrategy', 'status', 'targetCluster'],
                        'additionalProperties': False,
                    },
                },
                'action': {
                    'type': 'string',
                    'description': 'User-triggered action. Currently only RETRY is supported.',
                    'enum': ['RETRY'],
                },
                'retryStatus': {
                    'type': 'string',
                    'description': 'Status of the retry operation. Set to IN_PROGRESS when a retry is first triggered.',
                    'enum': ['IN_PROGRESS', 'COMPLETED'],
                },
            },
            'required': ['syntheticDataGenerationItem', 'selectedSyntheticDataGenerationItems'],
            'additionalProperties': True,
        },
    ),
    'TableComponent': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'editedItems': [{'id': 'row-1', 'parentId': None, 'status': 'approved'}]}],
        json_schema={
            'title': 'TableComponent Output',
            'description': 'Output schema for TableComponent. Returns edited table items with their updated cell values.',
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'editedItems': [{'id': 'row-1', 'parentId': None, 'status': 'approved'}]}
            ],
            'properties': {
                'editedItems': {
                    'type': 'array',
                    'description': 'Array of table items that were edited by the user',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {
                                'type': 'string',
                                'description': 'Unique identifier for the table row',
                            },
                            'parentId': {
                                'type': ['string', 'null'],
                                'description': 'Parent row ID for expandable/hierarchical rows',
                            },
                        },
                        'required': ['id'],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['editedItems'],
            'additionalProperties': True,
        },
    ),
    'TagNetworkResources': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'TagNetworkResources Output',
            'description': 'Output schema for TagNetworkResources. Display-only component instructing the user to tag network resources in the MGN console before continuing. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
    'TargetVPCSubnetAndKMSKeySelection': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[
            {
                'result': [
                    {
                        'host': 'db-server-01.example.com',
                        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                        'status': 'SUCCESS',
                        'databases': ['orders'],
                        'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                        'dms_project_name': 'my-dms-project',
                        'instance_id': 'instance-01',
                        'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                        'instance_profile_name': 'my-profile',
                        'port': 1433,
                        'region': 'us-east-1',
                        'endpoint': None,
                        'failure_message': None,
                        'failure_step': None,
                        'security_groups': ['sg-12345678'],
                        'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                        'source_data_source_name': 'source-endpoint',
                        'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                        'target_data_source_name': 'target-endpoint',
                        'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                        'vpc': 'vpc-12345678',
                        'customer_s3_bucket_dms': 'my-dms-bucket',
                        'subnets': [
                            {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                        ],
                        'kms_key_aliases': [
                            {
                                'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                                'AliasName': 'alias/my-key',
                                'CreationDate': '2024-01-01T00:00:00Z',
                                'LastUpdatedDate': '2024-01-01T00:00:00Z',
                                'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                            }
                        ],
                        'selected_key_alias': {
                            'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                            'AliasName': 'alias/my-key',
                            'CreationDate': '2024-01-01T00:00:00Z',
                            'LastUpdatedDate': '2024-01-01T00:00:00Z',
                            'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                        },
                        'selected_target': 'Aurora',
                    }
                ]
            }
        ],
        json_schema={
            'title': 'TargetVPCSubnetAndKMSKeySelection Output',
            'description': "Output schema for TargetVPCSubnetAndKMSKeySelection. Emits the full result list with each item's selected_key_alias and selected_target (Aurora or RDS) updated based on user selections.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {
                    'result': [
                        {
                            'host': 'db-server-01.example.com',
                            'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dbsecret-ABCDEF',  # pragma: allowlist secret
                            'status': 'SUCCESS',
                            'databases': ['orders'],
                            'dms_project_arn': 'arn:aws:dms:us-east-1:123456789012:project:ABCDEF',
                            'dms_project_name': 'my-dms-project',
                            'instance_id': 'instance-01',
                            'instance_profile_arn': 'arn:aws:iam::123456789012:instance-profile/my-profile',
                            'instance_profile_name': 'my-profile',
                            'port': 1433,
                            'region': 'us-east-1',
                            'endpoint': None,
                            'failure_message': None,
                            'failure_step': None,
                            'security_groups': ['sg-12345678'],
                            'source_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE',
                            'source_data_source_name': 'source-endpoint',
                            'target_data_source_arn': 'arn:aws:dms:us-east-1:123456789012:endpoint:TARGET',
                            'target_data_source_name': 'target-endpoint',
                            'target_secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:targetsecret-ABCDEF',  # pragma: allowlist secret
                            'vpc': 'vpc-12345678',
                            'customer_s3_bucket_dms': 'my-dms-bucket',
                            'subnets': [
                                {'availability_zone': 'us-east-1a', 'subnet_id': 'subnet-12345678'}
                            ],
                            'kms_key_aliases': [
                                {
                                    'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                                    'AliasName': 'alias/my-key',
                                    'CreationDate': '2024-01-01T00:00:00Z',
                                    'LastUpdatedDate': '2024-01-01T00:00:00Z',
                                    'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                                }
                            ],
                            'selected_key_alias': {
                                'AliasArn': 'arn:aws:kms:us-east-1:123456789012:alias/my-key',
                                'AliasName': 'alias/my-key',
                                'CreationDate': '2024-01-01T00:00:00Z',
                                'LastUpdatedDate': '2024-01-01T00:00:00Z',
                                'TargetKeyId': '12345678-1234-1234-1234-123456789012',
                            },
                            'selected_target': 'Aurora',
                        }
                    ]
                }
            ],
            'properties': {
                'result': {
                    'type': 'array',
                    'description': "Full list of database connection results with the user's KMS key alias selection and target database engine (Aurora or RDS) applied.",
                    'items': {
                        'type': 'object',
                        'properties': {
                            'host': {'type': 'string'},
                            'secret_arn': {'type': 'string'},
                            'status': {'type': 'string'},
                            'databases': {'type': 'array', 'items': {'type': 'string'}},
                            'dms_project_arn': {'type': 'string'},
                            'dms_project_name': {'type': 'string'},
                            'instance_id': {'type': 'string'},
                            'instance_profile_arn': {'type': 'string'},
                            'instance_profile_name': {'type': 'string'},
                            'port': {'type': 'number'},
                            'region': {'type': ['string', 'null']},
                            'endpoint': {'type': ['string', 'null']},
                            'failure_message': {'type': ['string', 'null']},
                            'failure_step': {'type': ['string', 'null']},
                            'security_groups': {'type': 'array', 'items': {'type': 'string'}},
                            'source_data_source_arn': {'type': 'string'},
                            'source_data_source_name': {'type': 'string'},
                            'target_data_source_arn': {'type': 'string'},
                            'target_data_source_name': {'type': 'string'},
                            'target_secret_arn': {'type': 'string'},
                            'vpc': {'type': 'string'},
                            'customer_s3_bucket_dms': {'type': 'string'},
                            'subnets': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'availability_zone': {'type': 'string'},
                                        'subnet_id': {'type': 'string'},
                                    },
                                    'additionalProperties': False,
                                },
                            },
                            'kms_key_aliases': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'AliasArn': {'type': 'string'},
                                        'AliasName': {'type': 'string'},
                                        'CreationDate': {'type': 'string'},
                                        'LastUpdatedDate': {'type': 'string'},
                                        'TargetKeyId': {'type': 'string'},
                                    },
                                    'required': [
                                        'AliasArn',
                                        'AliasName',
                                        'CreationDate',
                                        'LastUpdatedDate',
                                        'TargetKeyId',
                                    ],
                                    'additionalProperties': False,
                                },
                            },
                            'selected_key_alias': {
                                'description': 'The KMS key alias selected by the user, or null if none selected.',
                                'oneOf': [
                                    {
                                        'type': 'object',
                                        'properties': {
                                            'AliasArn': {'type': 'string'},
                                            'AliasName': {'type': 'string'},
                                            'CreationDate': {'type': 'string'},
                                            'LastUpdatedDate': {'type': 'string'},
                                            'TargetKeyId': {'type': 'string'},
                                        },
                                        'required': [
                                            'AliasArn',
                                            'AliasName',
                                            'CreationDate',
                                            'LastUpdatedDate',
                                            'TargetKeyId',
                                        ],
                                        'additionalProperties': False,
                                    },
                                    {'type': 'null'},
                                ],
                            },
                            'selected_target': {
                                'type': 'string',
                                'description': 'Target database engine selected by the user. Defaults to Aurora.',
                                'enum': ['Aurora', 'RDS'],
                            },
                        },
                        'required': [
                            'host',
                            'secret_arn',
                            'status',
                            'kms_key_aliases',
                            'selected_key_alias',
                            'selected_target',
                        ],
                        'additionalProperties': True,
                    },
                }
            },
            'required': ['result'],
            'additionalProperties': True,
        },
    ),
    'TextInput': OutputSchemaMeta(
        display_only=False,
        merge_with_artifact=False,
        examples=[{'data': 'User entered text here', 'enableFeatures': ['featureA', 'featureB']}],
        json_schema={
            'title': 'TextInput Output',
            'description': "Output schema for TextInput. Emits the user's text input along with enabled feature flags.",
            'displayOnly': False,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [
                {'data': 'User entered text here', 'enableFeatures': ['featureA', 'featureB']}
            ],
            'properties': {
                'data': {'type': 'string', 'description': 'The text string entered by the user'},
                'enableFeatures': {
                    'type': 'array',
                    'description': 'Array of enabled feature flag names, returned by getEnabledFeatures().',
                    'items': {'type': 'string'},
                },
            },
            'required': ['data', 'enableFeatures'],
            'additionalProperties': True,
        },
    ),
    'UpdateServiceQuota': OutputSchemaMeta(
        display_only=True,
        merge_with_artifact=False,
        examples=[{}],
        json_schema={
            'title': 'UpdateServiceQuota Output',
            'description': 'Output schema for UpdateServiceQuota. Display-only component that instructs the user to increase an AWS service quota (e.g. VPCs per region, EC2 VPC Elastic IPs) before continuing. No user input is collected via onInputChange.',
            'displayOnly': True,
            'mergeWithArtifact': False,
            'type': 'object',
            'examples': [{}],
            'properties': {},
            'required': [],
            'additionalProperties': True,
        },
    ),
}
