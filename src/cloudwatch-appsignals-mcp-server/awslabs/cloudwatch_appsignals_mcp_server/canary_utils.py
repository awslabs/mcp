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

"""Utility functions for CloudWatch Synthetics canary analysis and debugging."""

import asyncio
import json
import gzip
import io
import zipfile
import subprocess
import tempfile
import os
import re
import urllib.request
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse
from botocore.exceptions import ClientError
from loguru import logger
from .aws_clients import logs_client, synthetics_client, s3_client, iam_client, lambda_client, sts_client
from .utils import parse_timestamp

async def check_iam_exists_for_canary(canary: dict, iam_client) -> dict:
    """Check if IAM role exists for the canary."""
    execution_role_arn = canary.get('ExecutionRoleArn', '')
    if not execution_role_arn:
        return {"exists": False, "error": "No execution role configured"}
    
    role_name = execution_role_arn.split('/')[-1]
    
    try:
        iam_client.get_role(RoleName=role_name)
        return {"exists": True, "role_name": role_name}
    except ClientError as e:
        logger.warning(f"Failed to check IAM role {role_name}: {str(e)}")
        if e.response['Error']['Code'] == 'NoSuchEntity':
            return {"exists": False, "error": f"Role '{role_name}' does not exist"}
        else:
            return {"exists": False, "error": f"Cannot check role: {e.response.get('Error', {}).get('Message', str(e))}"}


async def check_lambda_permissions(canary: dict, iam_client) -> dict:
    """Check if IAM role has proper Lambda execution permissions."""
    execution_role_arn = canary.get('ExecutionRoleArn', '')
    if not execution_role_arn:
        return {"has_basic_execution": False, "has_vpc_permissions": False, "needs_vpc_check": False, "error": "No execution role configured"}
    
    role_name = execution_role_arn.split('/')[-1]
    
    try:
        policies_response = iam_client.list_attached_role_policies(RoleName=role_name)
        attached_policies = policies_response['AttachedPolicies']
        
        has_basic_execution = False
        has_vpc_permissions = False
        
        lambda_basic_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        lambda_vpc_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
        
        for policy in attached_policies:
            if policy['PolicyArn'] == lambda_basic_arn:
                has_basic_execution = True
            elif policy['PolicyArn'] == lambda_vpc_arn:
                has_vpc_permissions = True
                has_basic_execution = True
        
        if not has_basic_execution:
            for policy in attached_policies:
                if not policy['PolicyArn'].startswith('arn:aws:iam::aws:'):
                    try:
                        policy_response = iam_client.get_policy(PolicyArn=policy['PolicyArn'])
                        policy_version = iam_client.get_policy_version(
                            PolicyArn=policy['PolicyArn'],
                            VersionId=policy_response['Policy']['DefaultVersionId']
                        )
                        
                        policy_doc = policy_version['PolicyVersion']['Document']
                        
                        for statement in policy_doc.get('Statement', []):
                            actions = statement.get('Action', [])
                            if isinstance(actions, str):
                                actions = [actions]
                            
                            has_logs = any('logs:CreateLogGroup' in action or 'logs:CreateLogStream' in action or 'logs:PutLogEvents' in action for action in actions)
                            if has_logs and statement.get('Effect') == 'Allow':
                                has_basic_execution = True
                                break
                    
                    except Exception as e:
                        logger.warning(f"Failed to parse policy document: {str(e)}")
                        continue
        
        return {
            "has_basic_execution": has_basic_execution,
            "has_managed_basic_execution": any(p['PolicyArn'] == lambda_basic_arn for p in attached_policies),
            "has_vpc_permissions": has_vpc_permissions,
            "needs_vpc_check": not has_vpc_permissions,
            "attached_policies": [p['PolicyArn'] for p in attached_policies]
        }
        
    except Exception as e:
        return {"has_basic_execution": False, "has_vpc_permissions": False, "needs_vpc_check": False, "error": str(e)}


async def analyze_iam_role_and_policies(canary: dict, iam_client, region: str) -> dict:
    """Analyze IAM Role and Policies."""
    analysis = {
        "status": "analyzing",
        "checks": {},
        "issues_found": [],
        "recommendations": []
    }
    
    iam_check = await check_iam_exists_for_canary(canary, iam_client)
    if not iam_check["exists"]:
        analysis["checks"]["iam_exists"] = f"❌ IAM role does not exist: {iam_check['error']}"
        analysis["issues_found"].append(iam_check["error"])
    else:
        role_name = iam_check["role_name"]
        analysis["checks"]["iam_exists"] = f"✅ IAM role `{role_name}` exists"
    
    lambda_check = await check_lambda_permissions(canary, iam_client)
    if "error" in lambda_check:
        analysis["checks"]["lambda_execution"] = f"❌ IAM role check failed: {lambda_check['error']}"
        analysis["issues_found"].append(f"Cannot verify IAM permissions: {lambda_check['error']}")
        analysis["recommendations"].append("Verify the canary's execution role exists and has proper permissions")
    elif lambda_check.get("has_managed_basic_execution", False):
        analysis["checks"]["lambda_execution"] = "✅ Has Lambda basic execution permissions"
    elif lambda_check.get("has_basic_execution", False):
        analysis["checks"]["lambda_execution"] = "✅ Has custom Lambda execution permissions (sufficient)"
    else:
        analysis["checks"]["lambda_execution"] = "❌ Missing Lambda basic execution permissions"
        analysis["issues_found"].append("IAM role lacks Lambda execution permissions")
        analysis["recommendations"].append("Add Lambda execution permissions (logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents)")
    
    if lambda_check["has_vpc_permissions"]:
        analysis["checks"]["lambda_vpc"] = "✅ Has Lambda VPC permissions"
    elif lambda_check["needs_vpc_check"]:
        analysis["checks"]["lambda_vpc"] = "⚠️ No VPC permissions (may be needed if Lambda is in VPC)"
    
    analysis["status"] = "completed"
    return analysis


async def analyze_har_file(s3_client, bucket_name, har_files, is_failed_run=True) -> dict:
    """Analyze HAR files from canary runs."""
    har_analysis = {"status": "no_har_files", "insights": []}
    
    if not har_files:
        return har_analysis
    
    try:
        har_key = har_files[0]['Key']  # Fix: use 'Key' not 'key'
        har_obj = s3_client.get_object(Bucket=bucket_name, Key=har_key)
        har_content = har_obj['Body'].read()
        
        if har_key.endswith('.gz'):
            har_content = gzip.decompress(har_content)
        
        content_str = har_content.decode('utf-8')
        
        # Handle .har.html format
        if har_key.endswith('.har.html'):
            # Extract JSON from HTML wrapper - find matching braces
            import re
            start_match = re.search(r'var harOutput\s*=\s*({)', content_str)
            if start_match:
                json_start = start_match.start(1)
                brace_count = 0
                json_end = -1
                
                # Find matching closing brace
                for i, char in enumerate(content_str[json_start:], json_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > 0:
                    content_str = content_str[json_start:json_end]
                else:
                    return {"status": "error", "insights": ["Could not find end of HAR JSON data"]}
            else:
                return {"status": "error", "insights": ["Could not find harOutput variable in HTML"]}
        
        har_data = json.loads(content_str)
        
        entries = har_data.get('log', {}).get('entries', [])
        if not entries:
            return {"status": "empty_har", "insights": ["HAR file contains no network entries"]}
        
        insights = []
        failed_requests = []
        request_details = []
        
        for entry in entries:
            request = entry.get('request', {})
            response = entry.get('response', {})
            timings = entry.get('timings', {})
            
            url = request.get('url', 'unknown')
            status = response.get('status', 0)
            
            # Extract all timing components
            blocked = timings.get('blocked', 0) if timings.get('blocked', 0) > 0 else 0
            dns = timings.get('dns', 0) if timings.get('dns', 0) > 0 else 0
            connect = timings.get('connect', 0) if timings.get('connect', 0) > 0 else 0
            send = timings.get('send', 0) if timings.get('send', 0) > 0 else 0
            wait = timings.get('wait', 0) if timings.get('wait', 0) > 0 else 0
            receive = timings.get('receive', 0) if timings.get('receive', 0) > 0 else 0
            ssl = timings.get('ssl', 0) if timings.get('ssl', 0) > 0 else 0
            
            total_time = sum([v for v in timings.values() if isinstance(v, (int, float)) and v > 0])
            
            if total_time > 0:
                request_details.append({
                    'url': url,
                    'status': status,
                    'total': total_time,
                    'blocked': blocked,
                    'dns': dns,
                    'connect': connect,
                    'ssl': ssl,
                    'send': send,
                    'wait': wait,
                    'receive': receive
                })
            
            if is_failed_run and int(status) >= 400:
                failed_requests.append({
                    'url': url,
                    'status': status,
                    'statusText': response.get('statusText', ''),
                    'total': total_time,
                    'blocked': blocked,
                    'wait': wait
                })
        
        # Sort by total time to find slowest requests
        request_details.sort(key=lambda x: x['total'], reverse=True)
        
        if failed_requests:
            insights.append(f"🚨 Found {len(failed_requests)} failed HTTP requests:")
            for req in failed_requests[:3]:
                insights.append(f"  • {req['status']} {req['statusText']}: {req['url'][:100]}...")
        
        # Show top slowest requests with timing breakdown
        if request_details:
            insights.append(f"🐌 Top 5 slowest requests (timing breakdown):")
            for i, req in enumerate(request_details[:5]):
                insights.append(f"  {i+1}. {req['total']:.0f}ms total - {req['url'][:80]}")
                
                # Show timing breakdown
                breakdown = []
                if req['blocked'] > 0:
                    breakdown.append(f"Blocked: {req['blocked']:.0f}ms")
                if req['dns'] > 0:
                    breakdown.append(f"DNS: {req['dns']:.0f}ms")
                if req['connect'] > 0:
                    breakdown.append(f"Connect: {req['connect']:.0f}ms")
                if req['ssl'] > 0:
                    breakdown.append(f"SSL: {req['ssl']:.0f}ms")
                if req['send'] > 0:
                    breakdown.append(f"Send: {req['send']:.0f}ms")
                if req['wait'] > 0:
                    breakdown.append(f"Wait: {req['wait']:.0f}ms")
                if req['receive'] > 0:
                    breakdown.append(f"Receive: {req['receive']:.0f}ms")
                
                if breakdown:
                    insights.append(f"     {' | '.join(breakdown)}")
        
        # Identify specific issues
        blocking_issues = [r for r in request_details if r['blocked'] > 500]
        if blocking_issues:
            insights.append(f"🔒 {len(blocking_issues)} requests with high blocking time (connection limits):")
            for req in blocking_issues[:3]:
                insights.append(f"  • {req['blocked']:.0f}ms blocked: {req['url'][:80]}")
        
        waiting_issues = [r for r in request_details if r['wait'] > 1000]
        if waiting_issues:
            insights.append(f"⏳ {len(waiting_issues)} requests with high server wait time:")
            for req in waiting_issues[:3]:
                insights.append(f"  • {req['wait']:.0f}ms waiting: {req['url'][:80]}")
        
        
        har_analysis = {
            "status": "analyzed",
            "total_requests": len(entries),
            "failed_requests": len(failed_requests),
            "insights": insights[:10]
        }
        
    except Exception as e:
        har_analysis = {
            "status": "error",
            "insights": [f"HAR analysis failed: {str(e)[:200]}"]
        }
    
    return har_analysis


async def analyze_screenshots(s3_client, bucket_name, screenshots, is_failed_run=True) -> dict:
    """Analyze screenshots from canary runs."""
    screenshot_analysis = {"status": "no_screenshots", "insights": []}
    
    if not screenshots:
        return screenshot_analysis
    
    try:
        insights = []
        screenshot_types = {}
        
        for screenshot in screenshots:
            filename = screenshot['Key'].split('/')[-1]
            if 'error' in filename.lower() or 'failure' in filename.lower():
                screenshot_types['error'] = screenshot
            elif 'loaded' in filename.lower() or 'success' in filename.lower():
                screenshot_types['success'] = screenshot
            elif 'timeout' in filename.lower():
                screenshot_types['timeout'] = screenshot
        
        if is_failed_run:
            if 'error' in screenshot_types:
                insights.append("📸 Error screenshot captured - check for visible error messages")
                insights.append(f"   Screenshot: {screenshot_types['error']['Key']}")
            
            if 'timeout' in screenshot_types:
                insights.append("⏰ Timeout screenshot available - page may not have loaded completely")
            
            if not screenshot_types:
                insights.append("📸 Basic screenshots available - check for unexpected page content")
        
        insights.append(f"📊 Total screenshots: {len(screenshots)}")
        
        if screenshot_types:
            types_found = list(screenshot_types.keys())
            insights.append(f"📋 Screenshot types: {', '.join(types_found)}")
        
        screenshot_analysis = {
            "status": "analyzed",
            "total_screenshots": len(screenshots),
            "screenshot_types": list(screenshot_types.keys()),
            "insights": insights
        }
        
    except Exception as e:
        screenshot_analysis = {
            "status": "error",
            "insights": [f"Screenshot analysis failed: {str(e)[:200]}"]
        }
    
    return screenshot_analysis


async def analyze_log_files(s3_client, bucket_name, logs, is_failed_run=True) -> dict:
    """Analyze log files from canary runs"""
    log_analysis = {"status": "no_logs", "insights": []}
    
    if not logs:
        return log_analysis
    
    try:
        insights = []
        error_patterns = []
        
        for log_file in logs[:3]:  # Limit to 3 log files
            log_key = log_file['Key']
            
            try:
                log_obj = s3_client.get_object(Bucket=bucket_name, Key=log_key)
                log_content = log_obj['Body'].read()
                
                if log_key.endswith('.gz'):
                    log_content = gzip.decompress(log_content)
                
                log_text = log_content.decode('utf-8', errors='ignore')
                
                if is_failed_run:
                    error_keywords = [
                        'ERROR', 'FAILED', 'Exception', 'timeout', 'refused',
                        'not found', '404', '500', '502', '503', '504',
                        'DNS_PROBE', 'CONNECTION_REFUSED', 'SSL_ERROR', 'ERR_'
                    ]
                    
                    found_errors = []
                    for line in log_text.split('\n'):
                        line_lower = line.lower()
                        # Skip INFO and DEBUG lines unless they contain actual errors
                        if any(level in line for level in [' INFO:', ' DEBUG:']) and not any(err in line_lower for err in ['error', 'failed', 'exception', 'err_']):
                            continue
                            
                        for keyword in error_keywords:
                            if keyword.lower() in line_lower:
                                found_errors.append(line.strip()[:150])
                                break
                    
                    if found_errors:
                        error_patterns.extend(found_errors[:5])
                
            except Exception as log_error:
                insights.append(f"⚠️ Could not read log {log_key}: {str(log_error)[:100]}")
        
        if error_patterns:
            insights.append(f"🚨 Found {len(error_patterns)} error patterns in logs:")
            for i, error in enumerate(error_patterns[:5], 1):
                insights.append(f"  {i}. {error}")
        elif is_failed_run:
            insights.append("📋 No obvious error patterns found in log files")
            insights.append("💡 Check CloudWatch Logs for more detailed error information")
        
        insights.append(f"📊 Analyzed {min(len(logs), 3)} log files")
        
        log_analysis = {
            "status": "analyzed",
            "total_log_files": len(logs),
            "error_patterns_found": len(error_patterns),
            "insights": insights
        }
        
    except Exception as e:
        log_analysis = {
            "status": "error",
            "insights": [f"Log analysis failed: {str(e)[:200]}"]
        }
    
    return log_analysis


def check_resource_arns_correct(canary: dict, iam_client) -> dict:
    """Check if all resource ARNs in IAM policies are correct."""
    execution_role_arn = canary.get('ExecutionRoleArn', '')
    if not execution_role_arn:
        return {"correct": False, "error": "No execution role configured"}
    
    role_name = execution_role_arn.split('/')[-1]
    
    try:
        policies_response = iam_client.list_attached_role_policies(RoleName=role_name)
        attached_policies = policies_response['AttachedPolicies']
        
        canary_bucket = canary.get('ArtifactS3Location', '')
        
        if not canary_bucket.startswith('s3://'):
            if canary_bucket:
                canary_bucket = f's3://{canary_bucket}'
            else:
                return {"correct": False, "error": "No S3 artifact location configured"}
        
        actual_bucket_name = canary_bucket.replace('s3://', '').split('/')[0]
        has_mismatch = False
        
        for policy in attached_policies:
            if not policy['PolicyArn'].startswith('arn:aws:iam::aws:'):
                try:
                    policy_response = iam_client.get_policy(PolicyArn=policy['PolicyArn'])
                    policy_version = iam_client.get_policy_version(
                        PolicyArn=policy['PolicyArn'],
                        VersionId=policy_response['Policy']['DefaultVersionId']
                    )
                    
                    policy_doc = policy_version['PolicyVersion']['Document']
                    
                    for statement in policy_doc.get('Statement', []):
                        resources = statement.get('Resource', [])
                        if isinstance(resources, str):
                            resources = [resources]
                        
                        for resource in resources:
                            if 's3:::' in resource:
                                s3_part = resource.split('s3:::')[1]
                                bucket_pattern = s3_part.split('/')[0]
                                
                                if not _matches_bucket_pattern(actual_bucket_name, bucket_pattern):
                                    has_mismatch = True
                                    break
                        
                        if has_mismatch:
                            break
                    
                    if has_mismatch:
                        break
                
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    if error_code in ['NoSuchEntity', 'InvalidPolicyDocument']:
                        has_mismatch = True
                        break
                except Exception as e:
                    logger.error(f"Error: {str(e)}")
                    continue
        
        return {
            "correct": not has_mismatch,
            "actual_bucket": actual_bucket_name
        }
        
    except Exception as e:
        return {"correct": False, "error": str(e)}


def _matches_bucket_pattern(actual_bucket: str, pattern: str) -> bool:
    """Check if actual bucket matches the pattern (including wildcards)"""
    if pattern == actual_bucket:
        return True
    
    if '*' in pattern:
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(f'^{regex_pattern}$', actual_bucket))
    
    return False


async def analyze_canary_logs_with_time_window(canary_name: str, failure_time, canary: dict, window_minutes: int = 3, region: str = "us-east-1") -> dict:
    """Analyze canary logs within a specific time window around failure."""
    try:
        
        # Calculate time window around failure
        if isinstance(failure_time, str):
            failure_time = datetime.fromisoformat(failure_time.replace('Z', '+00:00'))
        
        start_time = failure_time - timedelta(minutes=window_minutes//2)
        end_time = failure_time + timedelta(minutes=window_minutes//2)
        
        # Convert to milliseconds since epoch
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        # Get actual Lambda function name from EngineArn
        engine_arn = canary.get('EngineArn', '')
        function_name = engine_arn.split(':function:')[1].split(':')[0]
        log_group_name = f"/aws/lambda/{function_name}"
        
        # Get log events in the time window
        try:
            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_timestamp,
                endTime=end_timestamp,
                limit=10
            )
            
            events = response.get('events', [])
            
            # Analyze log events for errors and patterns
            error_events = []
            warning_events = []
            info_events = []
            
            for event in events:
                message = event.get('message', '').lower()
                if any(keyword in message for keyword in ['error', 'failed', 'exception', 'timeout']):
                    error_events.append({
                        'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                        'message': event['message'][:300]
                    })
                elif any(keyword in message for keyword in ['warn', 'warning']):
                    warning_events.append({
                        'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                        'message': event['message'][:300]
                    })
                else:
                    info_events.append({
                        'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                        'message': event['message'][:200]
                    })
            
            return {
                'status': 'success',
                'time_window': f"{start_time.isoformat()} to {end_time.isoformat()}",
                'total_events': len(events),
                'error_events': error_events[:5],  # Limit to top 5
                'warning_events': warning_events[:5],  # Limit to top 5
                'info_events': info_events[:5],  # Limit to top 5
                'insights': [
                    f"Found {len(error_events)} error events",
                    f"Found {len(warning_events)} warning events",
                    f"Analyzed {window_minutes}-minute window around failure"
                ]
            }
            
        except ClientError as log_error:
            if log_error.response['Error']['Code'] == 'ResourceNotFoundException':
                return {
                    'status': 'no_logs',
                    'insights': [f"No CloudWatch logs found for canary: {canary_name}"]
                }
            else:
                return {
                    'status': 'error',
                    'insights': [f"CloudWatch logs access error: {log_error.response.get('Error', {}).get('Message', str(log_error))}"]
                }
        
    except Exception as e:
        return {
            'status': 'error',
            'insights': [f"Log analysis failed: {str(e)[:200]}"]
        }

async def extract_disk_memory_usage_metrics(canary_name: str, region: str = "us-east-1") -> dict:
    """Extract disk and memory usage metrics from canary log group."""
    try:
        # Get canary details to find the Lambda function name
        canary_response = synthetics_client.get_canary(Name=canary_name)
        canary = canary_response['Canary']
        
        # Extract Lambda function name from EngineArn
        engine_arn = canary.get('EngineArn', '')
        if not engine_arn:
            return {"error": "No EngineArn found for canary"}
        
        function_name = engine_arn.split(':function:')[1].split(':')[0]
        log_group_name = f"/aws/lambda/{function_name}"
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        query = '''
        fields @timestamp, message.Result.telemetry.maxEphemeralStorageUsageInMb, message.Result.telemetry.maxEphemeralStorageUsagePercent, message.Result.telemetry.maxSyntheticsMemoryUsageInMB
        | filter ispresent(message.Result.telemetry.maxEphemeralStorageUsageInMb)
        | sort @timestamp desc
        | limit 20
        '''
        
        response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query
        )
        
        query_id = response['queryId']
        
        # Wait for completion
        max_wait = 30
        wait_time = 0
        while wait_time < max_wait:
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            await asyncio.sleep(2)
            wait_time += 2
        
        if not result.get('results'):
            return {"error": "No telemetry data found in canary logs"}
        
        telemetry_data = []
        for row in result['results']:
            if len(row) >= 4:
                telemetry_data.append({
                    "timestamp": row[0]['value'],
                    "maxEphemeralStorageUsageInMb": float(row[1]['value']) if row[1]['value'] else 0,
                    "maxEphemeralStorageUsagePercent": float(row[2]['value']) if row[2]['value'] else 0,
                    "maxSyntheticsMemoryUsageInMB": float(row[3]['value']) if row[3]['value'] else 0
                })
        
        if not telemetry_data:
            return {"error": "No valid telemetry metrics found"}
        
        return {
            "maxEphemeralStorageUsageInMb": max(t['maxEphemeralStorageUsageInMb'] for t in telemetry_data),
            "maxEphemeralStorageUsagePercent": max(t['maxEphemeralStorageUsagePercent'] for t in telemetry_data),
            "maxSyntheticsMemoryUsageInMB": max(t['maxSyntheticsMemoryUsageInMB'] for t in telemetry_data)
        }
        
    except Exception as e:
        return {"error": f"Resource analysis failed: {str(e)[:200]}"}


async def get_canary_code(canary: dict, region: str = "us-east-1") -> dict:
    """Extract and analyze canary code from Lambda layers."""
    try:
        engine_arn = canary.get('EngineArn', '')
        if not engine_arn:
            return {"error": "No EngineArn found for canary"}
        
        function_name = engine_arn.split(':function:')[1].split(':')[0]
        
        # Get function configuration
        function_response = lambda_client.get_function(FunctionName=function_name)
        config = function_response['Configuration']
        
        result = {
            "function_name": function_name,
            "memory_size": config['MemorySize'],
            "timeout": config['Timeout'],
            "ephemeral_storage": config.get('EphemeralStorage', {}).get('Size', 512),
            "layers_count": len(config.get('Layers', [])),
            "code_content": ""
        }
        
        # Get layer code
        layers = config.get('Layers', [])
        custom_layers = [l for l in layers if not l['Arn'].startswith('arn:aws:lambda:us-east-1:378653112637:layer:Synthetics')]
        
        if custom_layers:
            import urllib.request
            import zipfile
            import tempfile
            import os
            import ssl
            
            layer_arn = custom_layers[0]['Arn']
            layer_response = lambda_client.get_layer_version_by_arn(Arn=layer_arn)
            
            if 'Location' in layer_response['Content']:
                layer_url = layer_response['Content']['Location']
                
                ssl_context = ssl._create_unverified_context()
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                    with urllib.request.urlopen(layer_url, context=ssl_context) as response:
                        tmp_file.write(response.read())
                    tmp_file.flush()
                    
                    with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                        js_files = [f for f in zip_ref.namelist() if f.endswith('.js')]
                        
                        if js_files:
                            main_js = next((f for f in js_files if 'index.js' in f), js_files[0])
                            with zip_ref.open(main_js) as f:
                                code_content = f.read().decode('utf-8')
                                lines = code_content.split('\n')
                                result["code_content"] = '\n'.join(f"{i+1}: {line}" for i, line in enumerate(lines))
                    
                    os.unlink(tmp_file.name)
        
        return result
        
    except Exception as e:
        return {"error": f"Canary code analysis failed: {str(e)}"}


async def get_canary_metrics_and_service_insights(canary_name: str, region: str) -> str:
    """Get canary metrics and service insights using Application Signals audit API."""
    import time
    import subprocess
    import json
    
    try:
        # Get caller identity for account ID
        caller_identity = sts_client.get_caller_identity()
        account_id = caller_identity['Account']

        # Note: Will use execute_audit_api once canary changes are released
        # from .audit_utils import execute_audit_api
        # audit_input = {
        #     'StartTime': int(time.time()) - 900,
        #     'EndTime': int(time.time()),
        #     'AuditTargets': [{
        #         "Type": "canary", 
        #         "Data": {
        #             "Canary": {
        #                 "CanaryName": canary_name
        #             }
        #         }
        #     }],
        #     'Auditors': ['canary', 'operation_metric', 'trace']
        # }
        # return await execute_audit_api(audit_input, region, f"Canary Analysis for {canary_name}\n")

        cmd = [
            'aws', 'application-signals-demo', 'list-audit-findings',
            '--region', region,
            '--endpoint-url', 'https://application-signals-gamma.us-west-2.api.aws',
            '--start-time', str(int(time.time()) - 900),
            '--end-time', str(int(time.time())),
            '--audit-targets', f'[{{"Type": "canary", "Data": {{"Canary": {{"CanaryName": "{canary_name}"}}}}}}]',
            '--auditors', 'canary', 'operation_metric', 'trace'
        ]

        telemetry_result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if telemetry_result.returncode != 0:
            return f"Error: {telemetry_result.stderr}"
            
        # Parse and format the JSON response
        try:
            response = json.loads(telemetry_result.stdout)
            findings = response.get('AuditFindings', [])
            
            if not findings:
                return "No telemetry findings available for this canary."
            
            formatted_output = []
            for finding in findings:
                key_attrs = finding.get('KeyAttributes', {})
                service_name = key_attrs.get('Name', 'Unknown Service')
                operation = finding.get('Operation', 'N/A')
                finding_type = finding.get('Type', 'Unknown')
                
                formatted_output.append(f"\n**Service**: {service_name}")
                formatted_output.append(f"**Operation**: {operation}")
                formatted_output.append(f"**Type**: {finding_type}")
                
                auditor_results = finding.get('AuditorResults', [])
                for result in auditor_results:
                    auditor = result.get('Auditor', 'Unknown')
                    severity = result.get('Severity', 'Unknown')
                    description = result.get('Description', 'No description')
                    
                    formatted_output.append(f"\n🔍 **{auditor} Analysis** (Severity: {severity})")
                    formatted_output.append(description)
                
                formatted_output.append("\n" + "─" * 50)
            
            return "\n".join(formatted_output)
            
        except json.JSONDecodeError:
            return telemetry_result.stdout
        
    except Exception as e:
        return f"Telemetry API unavailable: {str(e)}"
