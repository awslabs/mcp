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

"""Tests for audit_presentation_utils module."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.audit_presentation_utils import (
    create_targeted_audit_request,
    extract_findings_summary,
    format_detailed_finding_analysis,
    format_findings_summary,
)


class TestExtractFindingsSummary:
    """Test extract_findings_summary function."""

    def test_extract_findings_from_valid_json(self):
        """Test extracting findings from valid JSON audit result."""
        audit_result = """Some text before
        {
            "AuditFindings": [
                {
                    "FindingId": "finding-1",
                    "Severity": "CRITICAL",
                    "Description": "High error rate detected"
                }
            ]
        }"""

        findings, original = extract_findings_summary(audit_result)

        assert len(findings) == 1
        assert findings[0]['FindingId'] == 'finding-1'
        assert findings[0]['Severity'] == 'CRITICAL'
        assert original == audit_result

    def test_extract_findings_no_json(self):
        """Test handling audit result with no JSON."""
        audit_result = 'No JSON content here'

        findings, original = extract_findings_summary(audit_result)

        assert findings == []
        assert original == audit_result

    def test_extract_findings_invalid_json(self):
        """Test handling audit result with invalid JSON."""
        audit_result = 'Some text { invalid json }'

        findings, original = extract_findings_summary(audit_result)

        assert findings == []
        assert original == audit_result

    def test_extract_findings_no_audit_findings_key(self):
        """Test handling JSON without AuditFindings key."""
        audit_result = '{"SomeOtherKey": "value"}'

        findings, original = extract_findings_summary(audit_result)

        assert findings == []
        assert original == audit_result

    def test_extract_findings_empty_findings(self):
        """Test handling JSON with empty AuditFindings."""
        audit_result = '{"AuditFindings": []}'

        findings, original = extract_findings_summary(audit_result)

        assert findings == []
        assert original == audit_result


class TestFormatFindingsSummary:
    """Test format_findings_summary function."""

    def test_format_no_findings(self):
        """Test formatting when no findings are present."""
        result = format_findings_summary([], 'service')

        assert '✅ No issues found in service audit' in result
        assert 'All targets appear healthy' in result

    def test_format_single_critical_finding(self):
        """Test formatting with a single critical finding."""
        findings = [
            {'FindingId': 'critical-1', 'Severity': 'CRITICAL', 'Description': 'Service is down'}
        ]

        result = format_findings_summary(findings, 'service')

        assert '🚨 **1 Critical Issues**' in result
        assert 'critical-1' in result
        assert 'Service is down' in result
        assert '**1.**' in result

    def test_format_mixed_severity_findings(self):
        """Test formatting with mixed severity findings."""
        findings = [
            {'FindingId': 'critical-1', 'Severity': 'CRITICAL', 'Description': 'Critical issue'},
            {'FindingId': 'warning-1', 'Severity': 'WARNING', 'Description': 'Warning issue'},
            {'FindingId': 'info-1', 'Severity': 'INFO', 'Description': 'Info issue'},
        ]

        result = format_findings_summary(findings, 'slo')

        assert '🚨 **1 Critical Issues**' in result
        assert '⚠️  **1 Warning Issues**' in result
        assert 'ℹ️  **1 Info Issues**' in result
        assert '**1.**' in result
        assert '**2.**' in result
        assert '**3.**' in result

    def test_format_findings_without_description(self):
        """Test formatting findings without description."""
        findings = [{'FindingId': 'test-1', 'Severity': 'WARNING'}]

        result = format_findings_summary(findings, 'operation')

        assert 'test-1' in result
        assert 'No description available' in result

    def test_format_findings_case_insensitive_severity(self):
        """Test formatting with different case severities."""
        findings = [
            {'FindingId': 'test-1', 'Severity': 'critical', 'Description': 'Lower case critical'},
            {'FindingId': 'test-2', 'Severity': 'Warning', 'Description': 'Mixed case warning'},
        ]

        result = format_findings_summary(findings, 'service')

        assert '🚨 **CRITICAL ISSUES:**' in result
        assert '⚠️  **WARNING ISSUES:**' in result

    def test_format_findings_default_severity(self):
        """Test formatting findings with missing severity (defaults to INFO)."""
        findings = [{'FindingId': 'test-1', 'Description': 'No severity specified'}]

        result = format_findings_summary(findings, 'service')

        assert 'ℹ️  **INFORMATIONAL:**' in result


class TestCreateTargetedAuditRequest:
    """Test create_targeted_audit_request function."""

    def test_create_service_audit_request(self):
        """Test creating targeted audit request for service."""
        original_targets = [
            {
                'Type': 'service',
                'Data': {
                    'Service': {'Type': 'Service', 'Name': 'test-service', 'Environment': 'prod'}
                },
            }
        ]

        findings = [
            {'FindingId': 'finding-1', 'TargetName': 'test-service', 'Severity': 'CRITICAL'}
        ]

        result = create_targeted_audit_request(original_targets, findings, 1, 'service')

        assert len(result['targets']) == 1
        assert result['targets'][0]['Type'] == 'service'
        assert result['targets'][0]['Data']['Service']['Name'] == 'test-service'
        assert result['finding']['FindingId'] == 'finding-1'
        assert result['auditors'] == 'all'

    def test_create_slo_audit_request(self):
        """Test creating targeted audit request for SLO."""
        original_targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo'}}}]

        findings = [
            {'FindingId': 'slo-finding-1', 'TargetName': 'test-slo', 'Severity': 'WARNING'}
        ]

        result = create_targeted_audit_request(original_targets, findings, 1, 'slo')

        assert len(result['targets']) == 1
        assert result['targets'][0]['Type'] == 'slo'
        assert result['targets'][0]['Data']['Slo']['SloName'] == 'test-slo'
        assert result['finding']['FindingId'] == 'slo-finding-1'

    def test_create_operation_audit_request(self):
        """Test creating targeted audit request for operation."""
        original_targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {
                            'Type': 'Service',
                            'Name': 'api-service',
                            'Environment': 'prod',
                        },
                        'Operation': 'GET /users',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        findings = [
            {
                'FindingId': 'op-finding-1',
                'TargetName': 'api-service:GET /users',
                'Severity': 'CRITICAL',
            }
        ]

        result = create_targeted_audit_request(original_targets, findings, 1, 'operation')

        assert len(result['targets']) == 1
        assert result['targets'][0]['Type'] == 'service_operation'
        assert result['targets'][0]['Data']['ServiceOperation']['Service']['Name'] == 'api-service'
        assert result['targets'][0]['Data']['ServiceOperation']['Operation'] == 'GET /users'

    def test_create_audit_request_invalid_index(self):
        """Test creating audit request with invalid finding index."""
        original_targets = []
        findings = [{'FindingId': 'test-1'}]

        with pytest.raises(ValueError, match='Invalid finding index 2'):
            create_targeted_audit_request(original_targets, findings, 2, 'service')

        with pytest.raises(ValueError, match='Invalid finding index 0'):
            create_targeted_audit_request(original_targets, findings, 0, 'service')

    def test_create_audit_request_no_matching_target(self):
        """Test creating audit request when no matching target is found."""
        original_targets = [
            {'Type': 'service', 'Data': {'Service': {'Name': 'different-service'}}}
        ]

        findings = [
            {'FindingId': 'finding-1', 'TargetName': 'missing-service', 'Severity': 'CRITICAL'}
        ]

        result = create_targeted_audit_request(original_targets, findings, 1, 'service')

        # Should create a new target based on the finding
        assert len(result['targets']) == 1
        assert result['targets'][0]['Data']['Service']['Name'] == 'missing-service'

    def test_create_audit_request_operation_service_name_match(self):
        """Test operation audit request matching by service name only."""
        original_targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'api-service'},
                        'Operation': 'GET /users',
                    }
                },
            }
        ]

        findings = [
            {
                'FindingId': 'op-finding-1',
                'TargetName': 'api-service',  # Just service name, not full operation
                'Severity': 'WARNING',
            }
        ]

        result = create_targeted_audit_request(original_targets, findings, 1, 'operation')

        assert len(result['targets']) == 1
        assert result['targets'][0]['Data']['ServiceOperation']['Service']['Name'] == 'api-service'


class TestFormatDetailedFindingAnalysis:
    """Test format_detailed_finding_analysis function."""

    def test_format_detailed_analysis_complete(self):
        """Test formatting detailed analysis with complete finding data."""
        finding = {
            'TargetName': 'test-service',
            'FindingType': 'HighErrorRate',
            'Title': 'High Error Rate Detected',
            'Severity': 'CRITICAL',
            'Description': 'Service experiencing 50% error rate',
        }

        detailed_result = 'Detailed analysis shows database connection issues'

        result = format_detailed_finding_analysis(finding, detailed_result)

        assert '🚨 **DETAILED ROOT CAUSE ANALYSIS**' in result
        assert '**Target:** test-service' in result
        assert '**Issue Type:** HighErrorRate' in result
        assert '**Severity:** CRITICAL' in result
        assert '**Title:** High Error Rate Detected' in result
        assert '**Issue Description:**' in result
        assert 'Service experiencing 50% error rate' in result
        assert '**COMPREHENSIVE ANALYSIS RESULTS:**' in result
        assert 'Detailed analysis shows database connection issues' in result

    def test_format_detailed_analysis_minimal(self):
        """Test formatting detailed analysis with minimal finding data."""
        finding = {}
        detailed_result = 'Basic analysis result'

        result = format_detailed_finding_analysis(finding, detailed_result)

        assert '**Target:** Unknown Target' in result
        assert '**Issue Type:** Unknown' in result
        assert '**Severity:** INFO' in result
        assert '**Title:** No title' in result
        assert '**Issue Description:**' not in result  # No description section
        assert 'Basic analysis result' in result

    def test_format_detailed_analysis_warning_severity(self):
        """Test formatting with WARNING severity."""
        finding = {'Severity': 'WARNING', 'TargetName': 'warning-service'}

        result = format_detailed_finding_analysis(finding, 'Warning analysis')

        assert '⚠️ **DETAILED ROOT CAUSE ANALYSIS**' in result
        assert '**Severity:** WARNING' in result

    def test_format_detailed_analysis_info_severity(self):
        """Test formatting with INFO severity."""
        finding = {'Severity': 'INFO', 'TargetName': 'info-service'}

        result = format_detailed_finding_analysis(finding, 'Info analysis')

        assert 'ℹ️ **DETAILED ROOT CAUSE ANALYSIS**' in result
        assert '**Severity:** INFO' in result

    def test_format_detailed_analysis_unknown_severity(self):
        """Test formatting with unknown severity (defaults to INFO emoji)."""
        finding = {'Severity': 'UNKNOWN', 'TargetName': 'unknown-service'}

        result = format_detailed_finding_analysis(finding, 'Unknown analysis')

        assert 'ℹ️ **DETAILED ROOT CAUSE ANALYSIS**' in result
        assert '**Severity:** UNKNOWN' in result

    def test_format_detailed_analysis_empty_description(self):
        """Test formatting with empty description."""
        finding = {'TargetName': 'test-service', 'Description': ''}

        result = format_detailed_finding_analysis(finding, 'Analysis result')

        # Empty description should not create description section
        assert '**Issue Description:**' not in result
