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


def cloudformation_pre_deploy_validation() -> str:
    """Get pre-deployment validation instructions using CloudFormation change sets.

    Returns:
        JSON string with validation workflow instructions.
    """
    instructions = {
        'overview': 'Pre-deployment validation is enabled by default when creating change sets. Validates templates against common failure scenarios before resource provisioning.',
        'validation_types': {
            'property_syntax': {
                'description': 'Validates resource properties against AWS resource schemas',
                'checks': [
                    'Required properties',
                    'Valid property values',
                    'Deprecated properties',
                ],
                'failure_mode': 'FAIL - prevents change set execution',
                'example_error': '#/NotificationConfiguration/QueueConfigurations/0: required key [Event] not found',
            },
            'resource_name_conflict': {
                'description': 'Checks for naming conflicts with existing AWS resources',
                'checks': [
                    'Resource names meet AWS naming requirements',
                    'No conflicts with existing resources',
                ],
                'failure_mode': 'FAIL - prevents change set execution',
            },
            's3_bucket_emptiness': {
                'description': 'Warns when deleting S3 buckets that contain objects',
                'checks': ['Object presence in buckets being deleted'],
                'failure_mode': 'WARN - allows execution with warning',
                'note': 'Only checks object presence, not bucket policies or other constraints',
            },
        },
        'workflow': {
            'step_1_create_changeset': {
                'description': 'Create change set (validation runs automatically)',
                'command': 'aws cloudformation create-change-set --stack-name <name> --template-body file://<path> --change-set-name <name> --change-set-type CREATE|UPDATE --region <region>',
                'notes': [
                    'Validation runs automatically during creation',
                    'Add --capabilities CAPABILITY_IAM if template creates IAM resources',
                    'For S3 validation, ensure s3:ListBucket permission',
                ],
            },
            'step_2_check_validation': {
                'description': 'Check validation results using describe-events',
                'command': 'aws cloudformation describe-events --change-set-id <arn> --region <region>',
                'key_fields': {
                    'EventType': 'VALIDATION_ERROR indicates validation failure',
                    'ValidationName': 'PROPERTY_VALIDATION | RESOURCE_NAME_CONFLICT | S3_BUCKET_EMPTINESS',
                    'ValidationStatus': 'FAILED or PASSED',
                    'ValidationStatusReason': 'Detailed error message',
                    'ValidationPath': 'Property path in template where error occurred',
                    'ValidationFailureMode': 'FAIL or WARN',
                },
            },
            'step_3_fix_and_retry': {
                'description': 'Fix issues and create new change set',
                'notes': [
                    'Validation results are tied to specific change set',
                    'Modify template and create new change set to re-validate',
                ],
            },
        },
        'example': 'aws cloudformation create-change-set --stack-name my-stack --template-body file://template.yaml --change-set-name validation-$(date +%s) --change-set-type CREATE --region us-west-2 && aws cloudformation describe-events --change-set-id <arn> --region us-west-2',
        'key_considerations': [
            'Validation is automatic - no opt-in required',
            "Focuses on 3 common failure scenarios - doesn't guarantee deployment success",
            'Runtime errors (invalid AMI IDs, resource limits, permissions) still caught during execution',
            'Validation results tied to specific change set - modify template requires new change set',
        ],
    }
    return json.dumps(instructions, indent=2)
