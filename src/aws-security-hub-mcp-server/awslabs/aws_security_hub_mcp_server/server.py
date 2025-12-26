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
"""AWS Security Hub MCP Server implementation."""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from awslabs.aws_security_hub_mcp_server.models import (
    ComplianceStatus,
    ComplianceSummary,
    FindingStatistics,
    RecordState,
    SecurityFinding,
    SecurityInsight,
    SecurityScore,
    SeverityLabel,
    StandardControl,
    UpdateFindingRequest,
    WorkflowStatus,
)

# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Configuration
AWS_PROFILE = os.getenv('AWS_PROFILE')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
MAX_RESULTS = int(os.getenv('SECURITY_HUB_MAX_RESULTS', '100'))

mcp = FastMCP(
    'awslabs.aws-security-hub-mcp-server',
    instructions="""
    # AWS Security Hub MCP Server

    This server provides tools to interact with AWS Security Hub for security findings analysis, 
    compliance reporting, and security posture management.

    ## Best Practices

    - Use specific filters when querying findings to get relevant results
    - For large result sets, use pagination with NextToken
    - Check compliance status regularly to maintain security posture
    - Update finding workflow status to track remediation progress
    - Use insights to identify security trends and patterns
    - Monitor security scores to track overall security improvements

    ## Tool Selection Guide

    - Use `get_security_findings` when: You need to retrieve and analyze specific security findings
    - Use `get_compliance_summary` when: You want to understand overall compliance status
    - Use `get_insights` when: You need to analyze security trends and patterns
    - Use `get_finding_statistics` when: You want aggregated data about security findings
    - Use `update_finding_workflow` when: You need to update the status of findings
    - Use `manage_standards` when: You want to enable/disable security standards
    - Use `get_security_score` when: You need to track overall security posture
    """,
    dependencies=[
        'boto3',
        'pydantic',
        'loguru',
    ],
)


def get_security_hub_client():
    """Get a configured Security Hub client."""
    try:
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        return session.client('securityhub')
    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure your credentials.")
        raise
    except Exception as e:
        logger.error(f"Error creating Security Hub client: {e}")
        raise


def parse_finding(finding_data: Dict[str, Any]) -> SecurityFinding:
    """Parse AWS Security Hub finding data into our model."""
    severity = finding_data.get('Severity', {})
    severity_label = severity.get('Label', 'INFORMATIONAL')
    severity_score = severity.get('Normalized')
    
    workflow = finding_data.get('Workflow', {})
    workflow_status = workflow.get('Status', 'NEW')
    
    compliance = finding_data.get('Compliance', {})
    compliance_status = compliance.get('Status') if compliance else None
    
    resources = finding_data.get('Resources', [])
    resource_type = resources[0].get('Type') if resources else None
    resource_id = resources[0].get('Id') if resources else None
    
    remediation = finding_data.get('Remediation', {})
    remediation_url = remediation.get('Recommendation', {}).get('Url') if remediation else None
    
    return SecurityFinding(
        id=finding_data['Id'],
        product_arn=finding_data['ProductArn'],
        generator_id=finding_data['GeneratorId'],
        aws_account_id=finding_data['AwsAccountId'],
        region=finding_data['Region'],
        title=finding_data['Title'],
        description=finding_data['Description'],
        severity_label=SeverityLabel(severity_label),
        severity_score=severity_score,
        workflow_status=WorkflowStatus(workflow_status),
        record_state=RecordState(finding_data.get('RecordState', 'ACTIVE')),
        compliance_status=ComplianceStatus(compliance_status) if compliance_status else None,
        created_at=finding_data['CreatedAt'],
        updated_at=finding_data['UpdatedAt'],
        resource_type=resource_type,
        resource_id=resource_id,
        remediation_url=remediation_url,
        source_url=finding_data.get('SourceUrl'),
    )


@mcp.tool()
async def get_security_findings(
    ctx: Context,
    severity_labels: Optional[List[SeverityLabel]] = None,
    workflow_status: Optional[List[WorkflowStatus]] = None,
    compliance_status: Optional[List[ComplianceStatus]] = None,
    record_state: Optional[List[RecordState]] = None,
    product_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    days_back: Optional[int] = 7,
    max_results: Optional[int] = 50,
) -> List[SecurityFinding]:
    """Retrieve security findings from AWS Security Hub with filtering options.
    
    This tool allows you to query Security Hub findings with various filters to focus on
    specific security issues. You can filter by severity, workflow status, compliance status,
    and other attributes.
    
    Args:
        ctx: MCP context for logging and error handling
        severity_labels: Filter by severity levels
        workflow_status: Filter by workflow status
        compliance_status: Filter by compliance status
        record_state: Filter by record state
        product_name: Filter by product name
        resource_type: Filter by AWS resource type
        days_back: Number of days back to search
        max_results: Maximum number of findings to return
        
    Returns:
        List of SecurityFinding objects matching the filters
    """
    try:
        client = get_security_hub_client()
        
        # Build filters
        filters = {}
        
        if severity_labels:
            filters['SeverityLabel'] = [{'Value': label.value, 'Comparison': 'EQUALS'} 
                                      for label in severity_labels]
        
        if workflow_status:
            filters['WorkflowStatus'] = [{'Value': status.value, 'Comparison': 'EQUALS'} 
                                       for status in workflow_status]
        
        if compliance_status:
            filters['ComplianceStatus'] = [{'Value': status.value, 'Comparison': 'EQUALS'} 
                                         for status in compliance_status]
        
        if record_state:
            filters['RecordState'] = [{'Value': state.value, 'Comparison': 'EQUALS'} 
                                    for state in record_state]
        
        if product_name:
            filters['ProductName'] = [{'Value': product_name, 'Comparison': 'EQUALS'}]
        
        if resource_type:
            filters['ResourceType'] = [{'Value': resource_type, 'Comparison': 'EQUALS'}]
        
        # Add time filter
        if days_back:
            start_date = datetime.utcnow() - timedelta(days=days_back)
            filters['UpdatedAt'] = [{
                'Start': start_date.isoformat() + 'Z',
                'Comparison': 'GREATER_THAN_OR_EQUAL'
            }]
        
        # Limit results
        max_results = min(max_results or 50, MAX_RESULTS)
        
        logger.info(f"Querying Security Hub findings with filters: {filters}")
        
        response = client.get_findings(
            Filters=filters,
            MaxResults=max_results
        )
        
        findings = []
        for finding_data in response.get('Findings', []):
            try:
                finding = parse_finding(finding_data)
                findings.append(finding)
            except Exception as e:
                logger.warning(f"Error parsing finding {finding_data.get('Id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Retrieved {len(findings)} security findings")
        return findings
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}")
    except Exception as e:
        logger.error(f"Error retrieving security findings: {e}")
        raise


@mcp.tool()
async def get_compliance_summary(
    ctx: Context,
    standard_name: Optional[str] = None,
) -> List[ComplianceSummary]:
    """Get compliance status summary across enabled security standards.
    
    This tool provides an overview of compliance status across all enabled security standards
    or a specific standard if specified.
    
    Args:
        ctx: MCP context for logging and error handling
        standard_name: Optional filter for specific standard
        
    Returns:
        List of ComplianceSummary objects with compliance statistics
    """
    try:
        client = get_security_hub_client()
        
        # Get enabled standards
        logger.info("Retrieving enabled security standards")
        standards_response = client.get_enabled_standards()
        
        compliance_summaries = []
        
        for standard in standards_response.get('StandardsSubscriptions', []):
            standard_arn = standard['StandardsArn']
            standard_subscription_arn = standard['StandardsSubscriptionArn']
            
            # Get standard details
            standards_details = client.describe_standards(StandardsArns=[standard_arn])
            standard_detail = standards_details['Standards'][0]
            std_name = standard_detail['Name']
            
            # Skip if filtering by standard name and this doesn't match
            if standard_name and standard_name.lower() not in std_name.lower():
                continue
            
            # Get controls for this standard
            controls_response = client.describe_standards_controls(
                StandardsSubscriptionArn=standard_subscription_arn
            )
            
            # Count compliance status
            passed = failed = warning = not_available = 0
            total = len(controls_response.get('Controls', []))
            
            for control in controls_response.get('Controls', []):
                # Get findings for this control
                control_filters = {
                    'GeneratorId': [{'Value': control['ControlId'], 'Comparison': 'EQUALS'}],
                    'RecordState': [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}]
                }
                
                try:
                    findings_response = client.get_findings(
                        Filters=control_filters,
                        MaxResults=1
                    )
                    
                    if findings_response.get('Findings'):
                        finding = findings_response['Findings'][0]
                        compliance = finding.get('Compliance', {})
                        status = compliance.get('Status', 'NOT_AVAILABLE')
                        
                        if status == 'PASSED':
                            passed += 1
                        elif status == 'FAILED':
                            failed += 1
                        elif status == 'WARNING':
                            warning += 1
                        else:
                            not_available += 1
                    else:
                        # No findings means control is likely passing
                        passed += 1
                        
                except Exception as e:
                    logger.warning(f"Error getting findings for control {control['ControlId']}: {e}")
                    not_available += 1
            
            # Calculate compliance percentage
            compliance_percentage = (passed / total * 100) if total > 0 else 0
            
            compliance_summary = ComplianceSummary(
                standard_name=std_name,
                standard_arn=standard_arn,
                enabled=standard['StandardsStatus'] == 'ENABLED',
                passed_controls=passed,
                failed_controls=failed,
                warning_controls=warning,
                not_available_controls=not_available,
                total_controls=total,
                compliance_percentage=compliance_percentage
            )
            
            compliance_summaries.append(compliance_summary)
        
        logger.info(f"Retrieved compliance summary for {len(compliance_summaries)} standards")
        return compliance_summaries
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}")
    except Exception as e:
        logger.error(f"Error retrieving compliance summary: {e}")
        raise


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()

@mcp.tool()
async def get_insights(
    ctx: Context,
    insight_name: Optional[str] = None,
    max_results: Optional[int] = 20,
) -> List[SecurityInsight]:
    """Retrieve Security Hub insights for analyzing security trends and patterns.
    
    Insights help identify security trends, patterns, and anomalies in your findings data.
    
    Args:
        ctx: MCP context for logging and error handling
        insight_name: Optional filter for specific insight name
        max_results: Maximum number of insights to return
        
    Returns:
        List of SecurityInsight objects
    """
    try:
        client = get_security_hub_client()
        
        logger.info("Retrieving Security Hub insights")
        
        response = client.get_insights(MaxResults=min(max_results or 20, 100))
        
        insights = []
        for insight_data in response.get('Insights', []):
            insight_name_value = insight_data.get('Name', '')
            
            # Filter by name if specified
            if insight_name and insight_name.lower() not in insight_name_value.lower():
                continue
            
            insight = SecurityInsight(
                insight_arn=insight_data['InsightArn'],
                name=insight_name_value,
                filters=insight_data.get('Filters', {}),
                group_by_attribute=insight_data.get('GroupByAttribute', '')
            )
            insights.append(insight)
        
        logger.info(f"Retrieved {len(insights)} insights")
        return insights
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}")
    except Exception as e:
        logger.error(f"Error retrieving insights: {e}")
        raise


@mcp.tool()
async def get_finding_statistics(
    ctx: Context,
    group_by: str = "SeverityLabel",
    days_back: Optional[int] = 30,
) -> List[FindingStatistics]:
    """Get aggregated statistics about security findings grouped by specified attribute.
    
    This tool provides statistical analysis of your security findings, helping you understand
    the distribution and trends in your security posture.
    
    Args:
        ctx: MCP context for logging and error handling
        group_by: Attribute to group findings by
        days_back: Number of days back to analyze
        
    Returns:
        List of FindingStatistics objects with aggregated data
    """
    try:
        client = get_security_hub_client()
        
        # Build time filter
        filters = {}
        if days_back:
            start_date = datetime.utcnow() - timedelta(days=days_back)
            filters['UpdatedAt'] = [{
                'Start': start_date.isoformat() + 'Z',
                'Comparison': 'GREATER_THAN_OR_EQUAL'
            }]
        
        # Add active record state filter
        filters['RecordState'] = [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}]
        
        logger.info(f"Getting finding statistics grouped by {group_by}")
        
        # Get all findings (we'll group them ourselves since Security Hub doesn't have a direct aggregation API)
        response = client.get_findings(
            Filters=filters,
            MaxResults=MAX_RESULTS
        )
        
        findings = response.get('Findings', [])
        
        # Group findings by the specified attribute
        groups = {}
        total_count = len(findings)
        
        for finding in findings:
            group_key = None
            
            if group_by == "SeverityLabel":
                group_key = finding.get('Severity', {}).get('Label', 'UNKNOWN')
            elif group_by == "WorkflowStatus":
                group_key = finding.get('Workflow', {}).get('Status', 'UNKNOWN')
            elif group_by == "ProductName":
                group_key = finding.get('ProductName', 'UNKNOWN')
            elif group_by == "ResourceType":
                resources = finding.get('Resources', [])
                group_key = resources[0].get('Type', 'UNKNOWN') if resources else 'UNKNOWN'
            else:
                group_key = 'UNKNOWN'
            
            groups[group_key] = groups.get(group_key, 0) + 1
        
        # Convert to statistics objects
        statistics = []
        for group_key, count in groups.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            stat = FindingStatistics(
                group_key=group_key,
                count=count,
                percentage=round(percentage, 2)
            )
            statistics.append(stat)
        
        # Sort by count descending
        statistics.sort(key=lambda x: x.count, reverse=True)
        
        logger.info(f"Generated statistics for {len(statistics)} groups from {total_count} findings")
        return statistics
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}")
    except Exception as e:
        logger.error(f"Error retrieving finding statistics: {e}")
        raise


@mcp.tool()
async def update_finding_workflow(
    ctx: Context,
    finding_ids: List[str],
    workflow_status: WorkflowStatus,
    note: Optional[str] = None,
) -> str:
    """Update the workflow status of security findings and optionally add notes.
    
    This tool allows you to update the workflow status of findings to track remediation
    progress and add notes for documentation.
    
    Args:
        ctx: MCP context for logging and error handling
        finding_ids: List of finding ARNs to update
        workflow_status: New workflow status to set
        note: Optional note to add to the findings
        
    Returns:
        Success message with number of updated findings
    """
    try:
        client = get_security_hub_client()
        
        # Prepare the update request
        finding_identifiers = []
        for finding_id in finding_ids:
            # Extract account ID and region from the finding ARN if it's a full ARN
            if finding_id.startswith('arn:aws:securityhub:'):
                parts = finding_id.split(':')
                if len(parts) >= 6:
                    region = parts[3]
                    account_id = parts[4]
                    finding_identifiers.append({
                        'Id': finding_id,
                        'ProductArn': f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default"
                    })
                else:
                    # Assume it's just the finding ID
                    finding_identifiers.append({
                        'Id': finding_id,
                        'ProductArn': f"arn:aws:securityhub:{AWS_REGION}::product/aws/securityhub"
                    })
            else:
                # Assume it's just the finding ID
                finding_identifiers.append({
                    'Id': finding_id,
                    'ProductArn': f"arn:aws:securityhub:{AWS_REGION}::product/aws/securityhub"
                })
        
        # Prepare the update data
        update_data = {
            'FindingIdentifiers': finding_identifiers,
            'Workflow': {'Status': workflow_status.value}
        }
        
        if note:
            update_data['Note'] = {
                'Text': note,
                'UpdatedBy': 'AWS Security Hub MCP Server'
            }
        
        logger.info(f"Updating workflow status for {len(finding_identifiers)} findings to {workflow_status.value}")
        
        response = client.batch_update_findings(**update_data)
        
        processed_findings = response.get('ProcessedFindings', [])
        unprocessed_findings = response.get('UnprocessedFindings', [])
        
        success_count = len(processed_findings)
        error_count = len(unprocessed_findings)
        
        result_message = f"Successfully updated {success_count} findings to {workflow_status.value}"
        
        if error_count > 0:
            result_message += f". Failed to update {error_count} findings."
            for unprocessed in unprocessed_findings:
                logger.warning(f"Failed to update finding {unprocessed.get('FindingIdentifier', {}).get('Id')}: {unprocessed.get('ErrorMessage')}")
        
        if note:
            result_message += f" Added note: '{note}'"
        
        logger.info(result_message)
        return result_message
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}")
    except Exception as e:
        logger.error(f"Error updating finding workflow: {e}")
        raise


@mcp.tool()
async def get_security_score(
    ctx: Context,
) -> SecurityScore:
    """Retrieve the overall security score and security posture information.
    
    This tool provides an overview of your overall security posture based on
    Security Hub's security score calculation.
    
    Args:
        ctx: MCP context for logging and error handling
        
    Returns:
        SecurityScore object with current score and metrics
    """
    try:
        client = get_security_hub_client()
        
        logger.info("Calculating security score from findings data")
        
        # Get all active findings
        filters = {
            'RecordState': [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}]
        }
        
        response = client.get_findings(
            Filters=filters,
            MaxResults=MAX_RESULTS
        )
        
        findings = response.get('Findings', [])
        total_findings = len(findings)
        
        # Count findings by severity
        severity_counts = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0,
            'INFORMATIONAL': 0
        }
        
        control_findings = 0
        
        for finding in findings:
            severity = finding.get('Severity', {}).get('Label', 'INFORMATIONAL')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count control findings (findings from security standards)
            generator_id = finding.get('GeneratorId', '')
            if any(std in generator_id for std in ['aws-foundational-security-standard', 'cis-aws-foundations-benchmark', 'pci-dss']):
                control_findings += 1
        
        # Calculate a simple security score based on severity weights
        # This is a simplified calculation - AWS Security Hub uses a more complex algorithm
        severity_weights = {
            'CRITICAL': 10,
            'HIGH': 7,
            'MEDIUM': 4,
            'LOW': 2,
            'INFORMATIONAL': 1
        }
        
        total_weight = sum(severity_counts[sev] * weight for sev, weight in severity_weights.items())
        max_possible_weight = total_findings * severity_weights['CRITICAL'] if total_findings > 0 else 1
        
        # Invert the score so higher is better (fewer high-severity findings = higher score)
        current_score = max(0, 100 - (total_weight / max_possible_weight * 100)) if total_findings > 0 else 100
        
        security_score = SecurityScore(
            current_score=round(current_score, 2),
            max_score=100.0,
            score_date=datetime.utcnow(),
            control_findings_count=control_findings,
            security_score_percentage=round(current_score, 2)
        )
        
        logger.info(f"Calculated security score: {current_score:.2f}/100 based on {total_findings} findings")
        return security_score
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Security Hub error ({error_code}): {error_message}")
        raise Exception(f"Security Hub API error: {error_message}")
    except Exception as e:
        logger.error(f"Error calculating security score: {e}")
        raise