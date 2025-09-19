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

"""Unit tests for AWS Security Hub MCP Server models."""

import pytest
from awslabs.security_hub_mcp_server.models import (
    ComplianceCheck,
    Finding,
    FindingFilter,
    Insight,
    SecurityStandard,
)
from datetime import datetime
from pydantic import ValidationError


class TestSecurityHubModels:
    """Test cases for Security Hub Pydantic models."""

    def test_finding_model_valid(self):
        """Test Finding model with valid data."""
        finding_data = {
            'id': 'finding-123',
            'product_arn': 'arn:aws:securityhub:us-east-1::product/aws/securityhub',
            'generator_id': 'security-control/EC2.1',
            'aws_account_id': '123456789012',
            'title': 'EC2 instances should not have a public IP address',
            'description': 'This control checks whether EC2 instances have a public IP address.',
            'severity': {'Label': 'HIGH', 'Normalized': 70},
            'workflow_state': 'NEW',
            'record_state': 'ACTIVE',
            'created_at': datetime(2024, 1, 1, 0, 0, 0),
            'updated_at': datetime(2024, 1, 1, 0, 0, 0),
            'resources': [{'Type': 'AwsEc2Instance', 'Id': 'i-1234567890abcdef0'}],
        }

        finding = Finding(**finding_data)

        assert finding.id == 'finding-123'
        assert finding.title == 'EC2 instances should not have a public IP address'
        assert finding.severity['Label'] == 'HIGH'
        assert finding.workflow_state == 'NEW'
        assert len(finding.resources) == 1

    def test_finding_model_with_compliance(self):
        """Test Finding model with compliance data."""
        finding_data = {
            'id': 'finding-456',
            'product_arn': 'arn:aws:securityhub:us-east-1::product/aws/securityhub',
            'generator_id': 'security-control/S3.1',
            'aws_account_id': '123456789012',
            'title': 'S3 buckets should prohibit public read access',
            'description': 'This control checks whether S3 buckets allow public read access.',
            'severity': {'Label': 'CRITICAL', 'Normalized': 90},
            'compliance': {'Status': 'FAILED'},
            'workflow_state': 'NEW',
            'record_state': 'ACTIVE',
            'created_at': datetime(2024, 1, 1, 0, 0, 0),
            'updated_at': datetime(2024, 1, 1, 0, 0, 0),
            'resources': [],
        }

        finding = Finding(**finding_data)

        assert finding.compliance is not None
        assert finding.compliance['Status'] == 'FAILED'

    def test_finding_model_missing_required_field(self):
        """Test Finding model validation with missing required field."""
        finding_data = {
            'product_arn': 'arn:aws:securityhub:us-east-1::product/aws/securityhub',
            'generator_id': 'security-control/EC2.1',
            'aws_account_id': '123456789012',
            'title': 'EC2 instances should not have a public IP address',
            'description': 'This control checks whether EC2 instances have a public IP address.',
            'severity': {'Label': 'HIGH', 'Normalized': 70},
            'workflow_state': 'NEW',
            'record_state': 'ACTIVE',
            'created_at': datetime(2024, 1, 1, 0, 0, 0),
            'updated_at': datetime(2024, 1, 1, 0, 0, 0),
            'resources': [],
            # Missing 'id' field
        }

        with pytest.raises(ValidationError) as exc_info:
            Finding(**finding_data)

        assert 'id' in str(exc_info.value)

    def test_compliance_check_model_valid(self):
        """Test ComplianceCheck model with valid data."""
        compliance_data = {
            'control_id': 'EC2.1',
            'title': 'EC2 instances should not have a public IP address',
            'description': 'This control checks whether EC2 instances have a public IP address.',
            'compliance_status': 'FAILED',
            'severity_rating': 'HIGH',
            'workflow_status': 'NEW',
            'updated_at': datetime(2024, 1, 1, 0, 0, 0),
        }

        compliance_check = ComplianceCheck(**compliance_data)

        assert compliance_check.control_id == 'EC2.1'
        assert compliance_check.compliance_status == 'FAILED'
        assert compliance_check.severity_rating == 'HIGH'

    def test_security_standard_model_valid(self):
        """Test SecurityStandard model with valid data."""
        standard_data = {
            'standards_arn': 'arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0',
            'name': 'AWS Foundational Security Standard',
            'description': 'The AWS Foundational Security Standard is a set of controls that detect when your deployed AWS resources do not align to security best practices.',
            'enabled_by_default': True,
        }

        standard = SecurityStandard(**standard_data)

        assert 'aws-foundational-security-standard' in standard.standards_arn
        assert standard.name == 'AWS Foundational Security Standard'
        assert standard.enabled_by_default is True

    def test_insight_model_valid(self):
        """Test Insight model with valid data."""
        insight_data = {
            'insight_arn': 'arn:aws:securityhub:us-east-1:123456789012:insight/123456789012/custom/insight-1',
            'name': 'High severity findings by resource type',
            'filters': {'SeverityLabel': [{'Value': 'HIGH', 'Comparison': 'EQUALS'}]},
            'group_by_attribute': 'ResourceType',
        }

        insight = Insight(**insight_data)

        assert 'insight-1' in insight.insight_arn
        assert insight.name == 'High severity findings by resource type'
        assert insight.group_by_attribute == 'ResourceType'
        assert 'SeverityLabel' in insight.filters

    def test_finding_filter_model_empty(self):
        """Test FindingFilter model with no filters."""
        filter_data = {}

        finding_filter = FindingFilter(**filter_data)

        assert finding_filter.product_arn is None
        assert finding_filter.aws_account_id is None
        assert finding_filter.severity_label is None

    def test_finding_filter_model_with_filters(self):
        """Test FindingFilter model with various filters."""
        filter_data = {
            'product_arn': ['arn:aws:securityhub:us-east-1::product/aws/securityhub'],
            'aws_account_id': ['123456789012'],
            'severity_label': ['HIGH', 'CRITICAL'],
            'compliance_status': ['FAILED'],
            'workflow_state': ['NEW', 'NOTIFIED'],
            'record_state': ['ACTIVE'],
            'resource_type': ['AwsEc2Instance'],
            'resource_id': ['i-1234567890abcdef0'],
            'title': ['EC2 instances should not have a public IP address'],
            'created_at_start': datetime(2024, 1, 1, 0, 0, 0),
            'created_at_end': datetime(2024, 1, 31, 23, 59, 59),
            'updated_at_start': datetime(2024, 1, 1, 0, 0, 0),
            'updated_at_end': datetime(2024, 1, 31, 23, 59, 59),
        }

        finding_filter = FindingFilter(**filter_data)

        assert len(finding_filter.product_arn) == 1
        assert len(finding_filter.severity_label) == 2
        assert 'HIGH' in finding_filter.severity_label
        assert 'CRITICAL' in finding_filter.severity_label
        assert finding_filter.created_at_start.year == 2024
        assert finding_filter.updated_at_end.day == 31

    def test_finding_filter_model_datetime_validation(self):
        """Test FindingFilter model datetime field validation."""
        filter_data = {
            'created_at_start': datetime(2024, 1, 1, 0, 0, 0),
            'created_at_end': datetime(2024, 1, 31, 23, 59, 59),
        }

        finding_filter = FindingFilter(**filter_data)

        assert isinstance(finding_filter.created_at_start, datetime)
        assert isinstance(finding_filter.created_at_end, datetime)
        assert finding_filter.created_at_start < finding_filter.created_at_end

    def test_model_serialization(self):
        """Test model serialization to dict."""
        finding_data = {
            'id': 'finding-789',
            'product_arn': 'arn:aws:securityhub:us-east-1::product/aws/securityhub',
            'generator_id': 'security-control/IAM.1',
            'aws_account_id': '123456789012',
            'title': 'IAM policies should not allow full administrative privileges',
            'description': 'This control checks whether IAM policies grant full administrative privileges.',
            'severity': {'Label': 'MEDIUM', 'Normalized': 40},
            'workflow_state': 'RESOLVED',
            'record_state': 'ACTIVE',
            'created_at': datetime(2024, 1, 1, 0, 0, 0),
            'updated_at': datetime(2024, 1, 2, 0, 0, 0),
            'resources': [
                {'Type': 'AwsIamPolicy', 'Id': 'arn:aws:iam::123456789012:policy/AdminPolicy'}
            ],
        }

        finding = Finding(**finding_data)
        finding_dict = finding.model_dump()

        assert finding_dict['id'] == 'finding-789'
        assert finding_dict['workflow_state'] == 'RESOLVED'
        assert len(finding_dict['resources']) == 1
        assert isinstance(finding_dict['created_at'], datetime)

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        standard_data = {
            'standards_arn': 'arn:aws:securityhub:::standard/cis-aws-foundations-benchmark/v/1.2.0',
            'name': 'CIS AWS Foundations Benchmark',
            'description': 'The Center for Internet Security (CIS) AWS Foundations Benchmark',
            'enabled_by_default': False,
        }

        standard = SecurityStandard(**standard_data)
        json_str = standard.model_dump_json()

        assert 'cis-aws-foundations-benchmark' in json_str
        assert 'CIS AWS Foundations Benchmark' in json_str
        assert 'false' in json_str  # JSON boolean representation
