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

"""Unit tests for AWS Security Hub MCP Server constants."""

from awslabs.security_hub_mcp_server.consts import (
    AWS_FOUNDATIONAL_SECURITY_STANDARD,
    CIS_AWS_FOUNDATIONS_BENCHMARK,
    COMMON_RESOURCE_TYPES,
    COMPLIANCE_STATUSES,
    CONTROL_WORKFLOW_STATUSES,
    DEFAULT_MAX_RESULTS,
    DEFAULT_REGION,
    FINDING_RECORD_STATES,
    FINDING_WORKFLOW_STATES,
    MAX_RESULTS_LIMIT,
    NIST_CYBERSECURITY_FRAMEWORK,
    PCI_DSS,
    SERVICE_NAME,
    SEVERITY_LABELS,
)


class TestSecurityHubConstants:
    """Test cases for Security Hub constants."""

    def test_service_name(self):
        """Test service name constant."""
        assert SERVICE_NAME == 'securityhub'

    def test_default_region(self):
        """Test default region constant."""
        assert DEFAULT_REGION == 'us-east-1'

    def test_finding_workflow_states(self):
        """Test finding workflow states."""
        expected_states = ['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED']
        assert FINDING_WORKFLOW_STATES == expected_states
        assert len(FINDING_WORKFLOW_STATES) == 4

    def test_finding_record_states(self):
        """Test finding record states."""
        expected_states = ['ACTIVE', 'ARCHIVED']
        assert FINDING_RECORD_STATES == expected_states
        assert len(FINDING_RECORD_STATES) == 2

    def test_compliance_statuses(self):
        """Test compliance statuses."""
        expected_statuses = ['PASSED', 'WARNING', 'FAILED', 'NOT_AVAILABLE']
        assert COMPLIANCE_STATUSES == expected_statuses
        assert len(COMPLIANCE_STATUSES) == 4

    def test_severity_labels(self):
        """Test severity labels."""
        expected_labels = ['INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        assert SEVERITY_LABELS == expected_labels
        assert len(SEVERITY_LABELS) == 5

    def test_control_workflow_statuses(self):
        """Test control workflow statuses."""
        expected_statuses = ['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED']
        assert CONTROL_WORKFLOW_STATUSES == expected_statuses
        assert len(CONTROL_WORKFLOW_STATUSES) == 4

    def test_security_standard_arns(self):
        """Test security standard ARNs."""
        assert 'aws-foundational-security-standard' in AWS_FOUNDATIONAL_SECURITY_STANDARD
        assert 'cis-aws-foundations-benchmark' in CIS_AWS_FOUNDATIONS_BENCHMARK
        assert 'pci-dss' in PCI_DSS
        assert 'nist-csf' in NIST_CYBERSECURITY_FRAMEWORK

        # Ensure all ARNs start with the correct prefix
        arn_prefix = 'arn:aws:securityhub:::standard/'
        assert AWS_FOUNDATIONAL_SECURITY_STANDARD.startswith(arn_prefix)
        assert CIS_AWS_FOUNDATIONS_BENCHMARK.startswith(arn_prefix)
        assert PCI_DSS.startswith(arn_prefix)
        assert NIST_CYBERSECURITY_FRAMEWORK.startswith(arn_prefix)

    def test_pagination_limits(self):
        """Test pagination limit constants."""
        assert DEFAULT_MAX_RESULTS == 100
        assert MAX_RESULTS_LIMIT == 100
        assert DEFAULT_MAX_RESULTS <= MAX_RESULTS_LIMIT

    def test_common_resource_types(self):
        """Test common resource types."""
        expected_types = [
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

        assert len(COMMON_RESOURCE_TYPES) == len(expected_types)

        # Check that all expected types are present
        for resource_type in expected_types:
            assert resource_type in COMMON_RESOURCE_TYPES

        # Check that all resource types follow AWS naming convention
        for resource_type in COMMON_RESOURCE_TYPES:
            assert resource_type.startswith('Aws')
            assert resource_type[3].isupper()  # Fourth character should be uppercase

    def test_constants_immutability(self):
        """Test that constants are properly defined as immutable types."""
        # Lists should be defined (though Python doesn't enforce immutability)
        assert isinstance(FINDING_WORKFLOW_STATES, list)
        assert isinstance(FINDING_RECORD_STATES, list)
        assert isinstance(COMPLIANCE_STATUSES, list)
        assert isinstance(SEVERITY_LABELS, list)
        assert isinstance(COMMON_RESOURCE_TYPES, list)

        # Strings should be strings
        assert isinstance(SERVICE_NAME, str)
        assert isinstance(DEFAULT_REGION, str)
        assert isinstance(AWS_FOUNDATIONAL_SECURITY_STANDARD, str)

        # Integers should be integers
        assert isinstance(DEFAULT_MAX_RESULTS, int)
        assert isinstance(MAX_RESULTS_LIMIT, int)

    def test_severity_labels_order(self):
        """Test that severity labels are in logical order from lowest to highest."""
        expected_order = ['INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        assert SEVERITY_LABELS == expected_order

    def test_workflow_states_consistency(self):
        """Test that workflow states are consistent between findings and controls."""
        assert FINDING_WORKFLOW_STATES == CONTROL_WORKFLOW_STATUSES
