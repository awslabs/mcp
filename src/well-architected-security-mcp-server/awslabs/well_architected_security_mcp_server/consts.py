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

"""Constants for the AWS Security Pillar MCP Server."""

# Default AWS regions to use if none are specified
DEFAULT_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]

# Instructions for the MCP server
INSTRUCTIONS = """AWS Security Pillar MCP Server for analyzing AWS environments against Well-Architected Framework security principles.

This server dynamically adapts to your AWS environment, without requiring pre-defined services or rules.

## Key Capabilities
- Security services integration (Security Hub, GuardDuty, etc.)
- Dynamic resource discovery and security scanning
- Well-Architected Framework security analysis
- Detailed remediation planning with dry run analysis

## Available Tools

### CheckSecurityServices
Verifies if selected AWS security services are enabled in the specified region and account.
This consolidated tool checks the status of multiple AWS security services in a single call,
providing a comprehensive overview of your security posture.

### GetSecurityFindings
Retrieves security findings from various AWS security services including GuardDuty, Security Hub,
Inspector, IAM Access Analyzer, Trusted Advisor, and Macie with filtering options by severity.

### CheckStorageEncryption
Identifies storage resources using Resource Explorer and checks if they are properly configured
for data protection at rest according to AWS Well-Architected Framework Security Pillar best practices.

### CheckNetworkSecurity
Identifies network resources using Resource Explorer and checks if they are properly configured
for data protection in transit according to AWS Well-Architected Framework Security Pillar best practices.
This tool helps ensure your network configurations follow security best practices for protecting data in transit.

### GetStoredSecurityContext
Retrieves security services data that was stored in context from a previous CheckSecurityServices call
without making additional AWS API calls.

### GetResourceComplianceStatus
Checks the compliance status of specific AWS resources against AWS Config rules, providing
detailed compliance information and configuration history.

### ExploreAwsResources
Provides a comprehensive inventory of AWS resources within a specified region across multiple services.
This tool is useful for understanding what resources are deployed in your environment before conducting
a security assessment.

## Usage Guidelines
1. Start by exploring your AWS resources to understand your environment:
   - Use ExploreAwsResources to get a comprehensive inventory of resources
   - Review what services and resources are deployed in your target region

2. Check if key security services are enabled:
   - Use CheckSecurityServices to verify which security services are enabled
   - Review the summary to identify which services need to be enabled

3. Assess your data protection posture:
   - Use CheckStorageEncryption to verify encryption at rest
   - Use CheckNetworkSecurity to verify encryption in transit
   - Review the recommendations for improving your data protection

4. Analyze security findings:
   - Use GetSecurityFindings to retrieve findings from enabled security services
   - Focus on high-severity findings first

5. Apply recommended remediation steps to improve your security posture

## AWS Security Pillar
This server aligns with the Security Pillar of the AWS Well-Architected Framework, which focuses on:
- Identity and Access Management
- Detection Controls
- Infrastructure Protection
- Data Protection
- Incident Response

For more information, see: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html
"""


# Security domains from Well-Architected Framework
SECURITY_DOMAINS = [
    "identity_and_access_management",
    "detection",
    "infrastructure_protection",
    "data_protection",
    "incident_response",
    "application_security",
]

# Severity levels for security findings
SEVERITY_LEVELS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFORMATIONAL": 0,
}
