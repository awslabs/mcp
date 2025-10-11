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

"""Constants for AWS Security Hub MCP Server."""

# Security Hub service constants
SERVICE_NAME = 'securityhub'
DEFAULT_REGION = 'us-east-1'

# Finding states
FINDING_WORKFLOW_STATES = ['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED']

FINDING_RECORD_STATES = ['ACTIVE', 'ARCHIVED']

# Compliance statuses
COMPLIANCE_STATUSES = ['PASSED', 'WARNING', 'FAILED', 'NOT_AVAILABLE']

# Severity labels
SEVERITY_LABELS = ['INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

# Control workflow statuses
CONTROL_WORKFLOW_STATUSES = ['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED']

# Standard ARNs for common security standards
AWS_FOUNDATIONAL_SECURITY_STANDARD = (
    'arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0'
)
CIS_AWS_FOUNDATIONS_BENCHMARK = (
    'arn:aws:securityhub:::standard/cis-aws-foundations-benchmark/v/1.2.0'
)
PCI_DSS = 'arn:aws:securityhub:::standard/pci-dss/v/3.2.1'
NIST_CYBERSECURITY_FRAMEWORK = 'arn:aws:securityhub:::standard/nist-csf/v/1.0.0'

# Default pagination limits
DEFAULT_MAX_RESULTS = 100
MAX_RESULTS_LIMIT = 100

# Resource types commonly found in Security Hub
COMMON_RESOURCE_TYPES = [
    'AwsEc2Instance',
    'AwsS3Bucket',
    'AwsIamRole',
    'AwsIamUser',
    'AwsIamPolicy',
    'AwsRdsDbInstance',
    'AwsLambdaFunction',
    'AwsCloudTrailTrail',
    'AwsKmsKey',
    'AwsElbLoadBalancer',
    'AwsElbv2LoadBalancer',
    'AwsCloudFrontDistribution',
    'AwsApiGatewayRestApi',
    'AwsEksCluster',
]
