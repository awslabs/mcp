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

"""Shared utilities for audit tools."""

import json
import os
import tempfile
from datetime import datetime, timezone
from loguru import logger
from typing import Any, Dict, List, Optional, Union


# Constants
DEFAULT_BATCH_SIZE = 5
FUZZY_MATCH_THRESHOLD = 30  # Minimum similarity score for fuzzy matching
HIGH_CONFIDENCE_MATCH_THRESHOLD = 85  # High confidence threshold for exact fuzzy matches


async def execute_audit_api(input_obj: Dict[str, Any], region: str, banner: str) -> str:
    """Execute the Application Signals audit API call with the given input object."""
    from .aws_clients import applicationsignals_client

    # File log path
    desired_log_path = os.environ.get('AUDITOR_LOG_PATH', tempfile.gettempdir())
    try:
        if desired_log_path.endswith(os.sep) or os.path.isdir(desired_log_path):
            os.makedirs(desired_log_path, exist_ok=True)
            log_path = os.path.join(desired_log_path, 'aws_api.log')
        else:
            os.makedirs(os.path.dirname(desired_log_path) or '.', exist_ok=True)
            log_path = desired_log_path
    except Exception:
        temp_dir = tempfile.gettempdir()
        os.makedirs(temp_dir, exist_ok=True)
        log_path = os.path.join(temp_dir, 'aws_api.log')

    # Process targets in batches if needed
    targets = input_obj.get('AuditTargets', [])
    batch_size = DEFAULT_BATCH_SIZE
    target_batches = []

    if len(targets) > batch_size:
        logger.info(f'Processing {len(targets)} targets in batches of {batch_size}')
        for i in range(0, len(targets), batch_size):
            batch = targets[i : i + batch_size]
            target_batches.append(batch)
    else:
        target_batches.append(targets)

    all_batch_results = []

    for batch_idx, batch_targets in enumerate(target_batches, 1):
        logger.info(
            f'Processing batch {batch_idx}/{len(target_batches)} with {len(batch_targets)} targets'
        )

        # Build API input for this batch
        batch_input_obj = {
            'StartTime': datetime.fromtimestamp(input_obj['StartTime'], tz=timezone.utc),
            'EndTime': datetime.fromtimestamp(input_obj['EndTime'], tz=timezone.utc),
            'AuditTargets': batch_targets,
        }
        if 'Auditors' in input_obj:
            batch_input_obj['Auditors'] = input_obj['Auditors']

        # Log API invocation details
        api_pretty_input = json.dumps(
            {
                'StartTime': input_obj['StartTime'],
                'EndTime': input_obj['EndTime'],
                'AuditTargets': batch_targets,
                'Auditors': input_obj.get('Auditors', []),
            },
            indent=2,
        )

        # Also log the actual batch_input_obj that will be sent to AWS API
        batch_input_for_logging = {
            'StartTime': batch_input_obj['StartTime'].isoformat(),
            'EndTime': batch_input_obj['EndTime'].isoformat(),
            'AuditTargets': batch_input_obj['AuditTargets'],
        }
        if 'Auditors' in batch_input_obj:
            batch_input_for_logging['Auditors'] = batch_input_obj['Auditors']

        batch_payload_json = json.dumps(batch_input_for_logging, indent=2)

        logger.info('═' * 80)
        logger.info(
            f'BATCH {batch_idx}/{len(target_batches)} - {datetime.now(timezone.utc).isoformat()}'
        )
        logger.info(banner.strip())
        logger.info('---- API INVOCATION ----')
        logger.info('applicationsignals_client.list_audit_findings()')
        logger.info('---- API PARAMETERS (JSON) ----')
        logger.info(api_pretty_input)
        logger.info('---- ACTUAL AWS API PAYLOAD ----')
        logger.info(batch_payload_json)
        logger.info('---- END PARAMETERS ----')

        # Write detailed payload to log file
        try:
            with open(log_path, 'a') as f:
                f.write('═' * 80 + '\n')
                f.write(
                    f'BATCH {batch_idx}/{len(target_batches)} - {datetime.now(timezone.utc).isoformat()}\n'
                )
                f.write(banner.strip() + '\n')
                f.write('---- API INVOCATION ----\n')
                f.write('applicationsignals_client.list_audit_findings()\n')
                f.write('---- API PARAMETERS (JSON) ----\n')
                f.write(api_pretty_input + '\n')
                f.write('---- ACTUAL AWS API PAYLOAD ----\n')
                f.write(batch_payload_json + '\n')
                f.write('---- END PARAMETERS ----\n\n')
        except Exception as log_error:
            logger.warning(f'Failed to write audit log to {log_path}: {log_error}')

        # Call the Application Signals API for this batch
        try:
            response = applicationsignals_client.list_audit_findings(**batch_input_obj)  # type: ignore[attr-defined]

            # Format and log output for this batch
            observation_text = json.dumps(response, indent=2, default=str)
            all_batch_results.append(response)

            if not response.get('AuditFindings'):
                try:
                    with open(log_path, 'a') as f:
                        f.write(f'📭 Batch {batch_idx}: No findings returned.\n')
                        f.write('---- END RESPONSE ----\n\n')
                except Exception as log_error:
                    logger.warning(f'Failed to write audit log to {log_path}: {log_error}')
                logger.info(f'📭 Batch {batch_idx}: No findings returned.\n---- END RESPONSE ----')
            else:
                try:
                    with open(log_path, 'a') as f:
                        f.write(f'---- BATCH {batch_idx} API RESPONSE (JSON) ----\n')
                        f.write(observation_text + '\n')
                        f.write('---- END RESPONSE ----\n\n')
                except Exception as log_error:
                    logger.warning(f'Failed to write audit log to {log_path}: {log_error}')
                logger.info(
                    f'---- BATCH {batch_idx} API RESPONSE (JSON) ----\n'
                    + observation_text
                    + '\n---- END RESPONSE ----'
                )

        except Exception as e:
            error_msg = str(e)
            try:
                with open(log_path, 'a') as f:
                    f.write(f'---- BATCH {batch_idx} API ERROR ----\n')
                    f.write(error_msg + '\n')
                    f.write('---- END ERROR ----\n\n')
            except Exception as log_error:
                logger.warning(f'Failed to write audit log to {log_path}: {log_error}')
            logger.error(
                f'---- BATCH {batch_idx} API ERROR ----\n' + error_msg + '\n---- END ERROR ----'
            )

            batch_error_result = {
                'batch_index': batch_idx,
                'error': f'API call failed: {error_msg}',
                'targets_count': len(batch_targets),
            }
            all_batch_results.append(batch_error_result)
            continue

    # Aggregate results from all batches
    if not all_batch_results:
        return banner + 'Result: No findings from any batch.'

    # Aggregate the findings from all successful batches
    aggregated_findings = []
    total_targets_processed = 0
    failed_batches = 0

    for batch_result in all_batch_results:
        if isinstance(batch_result, dict):
            if 'error' in batch_result:
                failed_batches += 1
                continue

            batch_findings = batch_result.get('AuditFindings', [])
            aggregated_findings.extend(batch_findings)

            # Count targets processed (this batch)
            # Get the batch size from the original targets list
            current_batch_size = min(
                DEFAULT_BATCH_SIZE,
                len(targets)
                - (len(aggregated_findings) // DEFAULT_BATCH_SIZE) * DEFAULT_BATCH_SIZE,
            )
            total_targets_processed += current_batch_size

    # Create final aggregated response
    final_result = {
        'AuditFindings': aggregated_findings,
        'BatchSummary': {
            'TotalBatches': len(target_batches),
            'SuccessfulBatches': len(target_batches) - failed_batches,
            'FailedBatches': failed_batches,
            'TotalTargetsProcessed': total_targets_processed,
            'TotalFindingsCount': len(aggregated_findings),
        },
    }

    # Add any error information if there were failed batches
    if failed_batches > 0:
        error_details = []
        for batch_result in all_batch_results:
            if isinstance(batch_result, dict) and 'error' in batch_result:
                error_details.append(
                    {
                        'batch': batch_result['batch_index'],
                        'error': batch_result['error'],
                        'targets_count': batch_result['targets_count'],
                    }
                )
        final_result['BatchErrors'] = error_details

    final_observation_text = json.dumps(final_result, indent=2, default=str)
    return banner + final_observation_text


def _create_service_target(
    service_name: str, environment: str, aws_account_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized service target configuration."""
    service_config = {
        'Type': 'Service',
        'Name': service_name,
        'Environment': environment,
    }
    if aws_account_id:
        service_config['AwsAccountId'] = aws_account_id

    return {
        'Type': 'service',
        'Data': {'Service': service_config},
    }


def parse_auditors(
    auditors_value: Union[str, None, Any], default_auditors: List[str]
) -> List[str]:
    """Parse and validate auditors parameter."""
    # Handle Pydantic Field objects that may be passed instead of actual values
    if hasattr(auditors_value, 'default') and hasattr(auditors_value, 'description'):
        # This is a Pydantic Field object, use its default value
        auditors_value = getattr(auditors_value, 'default', None)

    if auditors_value is None:
        user_prompt_text = os.environ.get('MCP_USER_PROMPT', '') or ''
        wants_root_cause = 'root cause' in user_prompt_text.lower()
        raw_a = default_auditors if not wants_root_cause else []
    elif str(auditors_value).lower() == 'all':
        raw_a = []  # Empty list means use all auditors
    else:
        raw_a = [a.strip() for a in str(auditors_value).split(',') if a.strip()]

    # Validate auditors
    if len(raw_a) == 0:
        return []  # Empty list means use all auditors
    else:
        allowed = {
            'slo',
            'operation_metric',
            'trace',
            'log',
            'dependency_metric',
            'top_contributor',
            'service_quota',
        }
        invalid = [a for a in raw_a if a not in allowed]
        if invalid:
            raise ValueError(
                f'Invalid auditor(s): {", ".join(invalid)}. Allowed: {", ".join(sorted(allowed))}'
            )
        return raw_a


def expand_service_wildcard_patterns(
    targets: List[dict], unix_start: int, unix_end: int, applicationsignals_client=None
) -> List[dict]:
    """Expand wildcard patterns for service targets only."""
    from .utils import calculate_name_similarity

    if applicationsignals_client is None:
        from .aws_clients import applicationsignals_client

    expanded_targets = []
    service_patterns = []
    service_fuzzy_matches = []

    logger.debug(f'expand_service_wildcard_patterns: Processing {len(targets)} targets')

    # First pass: identify patterns and collect non-wildcard targets
    for i, target in enumerate(targets):
        logger.debug(f'Target {i}: {target}')

        if not isinstance(target, dict):
            expanded_targets.append(target)
            continue

        target_type = target.get('Type', '').lower()
        logger.debug(f'Target {i} type: {target_type}')

        if target_type == 'service':
            # Check multiple possible locations for service name
            service_name = None

            # Check Data.Service.Name (full format)
            service_data = target.get('Data', {})
            if isinstance(service_data, dict):
                service_info = service_data.get('Service', {})
                if isinstance(service_info, dict):
                    service_name = service_info.get('Name', '')

            # Check shorthand Service field
            if not service_name:
                service_name = target.get('Service', '')

            logger.debug(f"Target {i} service name: '{service_name}'")

            if isinstance(service_name, str) and service_name:
                if '*' in service_name:
                    logger.debug(f"Target {i} identified as wildcard pattern: '{service_name}'")
                    service_patterns.append((target, service_name))
                else:
                    # Check if this might be a fuzzy match candidate
                    service_fuzzy_matches.append((target, service_name))
            else:
                logger.debug(f'Target {i} has no valid service name, passing through')
                expanded_targets.append(target)
        else:
            # Non-service targets pass through unchanged
            logger.debug(f'Target {i} is not a service target, passing through')
            expanded_targets.append(target)

    # Expand service patterns and fuzzy matches
    if service_patterns or service_fuzzy_matches:
        logger.debug(
            f'Expanding {len(service_patterns)} service wildcard patterns and {len(service_fuzzy_matches)} fuzzy matches'
        )
        try:
            services_response = applicationsignals_client.list_services(
                StartTime=datetime.fromtimestamp(unix_start, tz=timezone.utc),
                EndTime=datetime.fromtimestamp(unix_end, tz=timezone.utc),
                MaxResults=100,
            )
            all_services = services_response.get('ServiceSummaries', [])

            # Handle wildcard patterns
            for original_target, pattern in service_patterns:
                search_term = pattern.strip('*').lower() if pattern != '*' else ''
                matches_found = 0

                for service in all_services:
                    service_attrs = service.get('KeyAttributes', {})
                    service_name = service_attrs.get('Name', '')
                    service_type = service_attrs.get('Type', '')
                    environment = service_attrs.get('Environment', '')

                    # Filter out services without proper names or that are not actual services
                    if not service_name or service_name == 'Unknown' or service_type != 'Service':
                        logger.debug(
                            f"Skipping service: Name='{service_name}', Type='{service_type}', Environment='{environment}'"
                        )
                        continue

                    # Apply search filter
                    if search_term == '' or search_term in service_name.lower():
                        expanded_targets.append(_create_service_target(service_name, environment))
                        matches_found += 1
                        logger.debug(
                            f"Added service: Name='{service_name}', Environment='{environment}'"
                        )

                logger.debug(f"Service pattern '{pattern}' expanded to {matches_found} targets")

            # Handle fuzzy matches for inexact service names
            for original_target, inexact_name in service_fuzzy_matches:
                best_matches = []

                # Calculate similarity scores for all services
                for service in all_services:
                    service_attrs = service.get('KeyAttributes', {})
                    service_name = service_attrs.get('Name', '')
                    if not service_name:
                        continue

                    score = calculate_name_similarity(inexact_name, service_name, 'service')

                    if score >= FUZZY_MATCH_THRESHOLD:  # Minimum threshold for consideration
                        best_matches.append(
                            (service_name, service_attrs.get('Environment'), score)
                        )

                # Sort by score and take the best matches
                best_matches.sort(key=lambda x: x[2], reverse=True)

                if best_matches:
                    # If we have a very high score match, use only that
                    if best_matches[0][2] >= HIGH_CONFIDENCE_MATCH_THRESHOLD:
                        matched_services = [best_matches[0]]
                    else:
                        # Otherwise, take top 3 matches above threshold
                        matched_services = best_matches[:3]

                    logger.info(
                        f"Fuzzy matching service '{inexact_name}' found {len(matched_services)} candidates:"
                    )
                    for service_name, environment, score in matched_services:
                        logger.info(f"  - '{service_name}' in '{environment}' (score: {score})")
                        expanded_targets.append(_create_service_target(service_name, environment))
                else:
                    logger.warning(
                        f"No fuzzy matches found for service name '{inexact_name}' (no candidates above threshold)"
                    )
                    # Keep the original target - let the API handle the error
                    expanded_targets.append(original_target)

        except Exception as e:
            logger.warning(f'Failed to expand service patterns and fuzzy matches: {e}')
            # When expansion fails, we need to return an error rather than passing wildcards to validation
            # This prevents the validation phase from seeing wildcard patterns
            if service_patterns or service_fuzzy_matches:
                pattern_names = [pattern for _, pattern in service_patterns] + [
                    name for _, name in service_fuzzy_matches
                ]
                raise ValueError(
                    f'Failed to expand service wildcard patterns {pattern_names}. '
                    f'This may be due to AWS API access issues or missing services. '
                    f'Error: {str(e)}'
                )

    return expanded_targets


def expand_slo_wildcard_patterns(
    targets: List[dict], applicationsignals_client=None
) -> List[dict]:
    """Expand wildcard patterns for SLO targets only."""
    if applicationsignals_client is None:
        from .aws_clients import applicationsignals_client

    expanded_targets = []
    wildcard_patterns = []

    for target in targets:
        if isinstance(target, dict):
            ttype = target.get('Type', '').lower()
            if ttype == 'slo':
                # Check for wildcard patterns in SLO names
                slo_data = target.get('Data', {}).get('Slo', {})

                # BUG FIX: Handle case where Slo is a string instead of dict
                if isinstance(slo_data, str):
                    # Malformed input - Slo should be a dict with SloName key
                    raise ValueError(
                        f"Invalid SLO target format. Expected {{'Type':'slo','Data':{{'Slo':{{'SloName':'name'}}}}}} "
                        f"but got {{'Slo':'{slo_data}'}}. The 'Slo' field must be a dictionary with 'SloName' key."
                    )
                elif isinstance(slo_data, dict):
                    slo_name = slo_data.get('SloName', '')
                else:
                    # Handle other unexpected types
                    raise ValueError(
                        f"Invalid SLO target format. The 'Slo' field must be a dictionary with 'SloName' key, "
                        f'but got {type(slo_data).__name__}: {slo_data}'
                    )

                if '*' in slo_name:
                    wildcard_patterns.append((target, slo_name))
                else:
                    expanded_targets.append(target)
            else:
                expanded_targets.append(target)
        else:
            expanded_targets.append(target)

    # Expand wildcard patterns for SLOs
    if wildcard_patterns:
        logger.debug(f'Expanding {len(wildcard_patterns)} SLO wildcard patterns')
        try:
            # Get all SLOs to expand patterns
            slos_response = applicationsignals_client.list_service_level_objectives(
                MaxResults=50, IncludeLinkedAccounts=True
            )
            all_slos = slos_response.get('SloSummaries', [])

            for original_target, pattern in wildcard_patterns:
                search_term = pattern.strip('*').lower() if pattern != '*' else ''
                matches_found = 0

                for slo in all_slos:
                    slo_name = slo.get('Name', '')
                    if search_term == '' or search_term in slo_name.lower():
                        expanded_targets.append(
                            {
                                'Type': 'slo',
                                'Data': {
                                    'Slo': {'SloName': slo_name, 'SloArn': slo.get('Arn', '')}
                                },
                            }
                        )
                        matches_found += 1

                logger.debug(f"SLO pattern '{pattern}' expanded to {matches_found} targets")

        except Exception as e:
            logger.warning(f'Failed to expand SLO patterns: {e}')
            raise ValueError(f'Failed to expand SLO wildcard patterns. {str(e)}')

    return expanded_targets


def expand_service_operation_wildcard_patterns(
    targets: List[dict], unix_start: int, unix_end: int, applicationsignals_client=None
) -> List[dict]:
    """Expand wildcard patterns for service operation targets only."""
    if applicationsignals_client is None:
        from .aws_clients import applicationsignals_client

    expanded_targets = []
    wildcard_patterns = []

    for target in targets:
        if isinstance(target, dict):
            ttype = target.get('Type', '').lower()
            if ttype == 'service_operation':
                # Check for wildcard patterns in service names OR operation names
                service_op_data = target.get('Data', {}).get('ServiceOperation', {})
                service_data = service_op_data.get('Service', {})
                service_name = service_data.get('Name', '')
                operation = service_op_data.get('Operation', '')

                # Check if either service name or operation has wildcards
                if '*' in service_name or '*' in operation:
                    wildcard_patterns.append((target, service_name, operation))
                else:
                    expanded_targets.append(target)
            else:
                expanded_targets.append(target)
        else:
            expanded_targets.append(target)

    # Expand wildcard patterns for service operations
    if wildcard_patterns:
        logger.debug(f'Expanding {len(wildcard_patterns)} service operation wildcard patterns')
        try:
            # Get all services to expand patterns
            services_response = applicationsignals_client.list_services(
                StartTime=datetime.fromtimestamp(unix_start, tz=timezone.utc),
                EndTime=datetime.fromtimestamp(unix_end, tz=timezone.utc),
                MaxResults=100,
            )
            all_services = services_response.get('ServiceSummaries', [])

            for original_target, service_pattern, operation_pattern in wildcard_patterns:
                service_search_term = (
                    service_pattern.strip('*').lower() if service_pattern != '*' else ''
                )
                operation_search_term = (
                    operation_pattern.strip('*').lower() if operation_pattern != '*' else ''
                )
                matches_found = 0

                # Get the original metric type from the pattern
                service_op_data = original_target.get('Data', {}).get('ServiceOperation', {})
                metric_type = service_op_data.get('MetricType', 'Latency')

                # Find matching services
                matching_services = []
                for service in all_services:
                    service_attrs = service.get('KeyAttributes', {})
                    service_name = service_attrs.get('Name', '')
                    service_type = service_attrs.get('Type', '')

                    # Filter out services without proper names or that are not actual services
                    if not service_name or service_name == 'Unknown' or service_type != 'Service':
                        continue

                    # Check if service matches the pattern
                    if '*' not in service_pattern:
                        # Exact service name match
                        if service_name == service_pattern:
                            matching_services.append(service)
                    else:
                        # Wildcard service name match
                        if (
                            service_search_term == ''
                            or service_search_term in service_name.lower()
                        ):
                            matching_services.append(service)

                logger.debug(
                    f"Found {len(matching_services)} services matching pattern '{service_pattern}'"
                )

                # For each matching service, get operations and expand operation patterns
                for service in matching_services:
                    service_attrs = service.get('KeyAttributes', {})
                    service_name = service_attrs.get('Name', '')
                    environment = service_attrs.get('Environment', '')

                    try:
                        # Get operations for this service
                        operations_response = applicationsignals_client.list_service_operations(
                            StartTime=datetime.fromtimestamp(unix_start, tz=timezone.utc),
                            EndTime=datetime.fromtimestamp(unix_end, tz=timezone.utc),
                            KeyAttributes=service_attrs,
                            MaxResults=100,
                        )

                        operations = operations_response.get('Operations', [])
                        logger.debug(
                            f"Found {len(operations)} operations for service '{service_name}'"
                        )

                        # Filter operations based on operation pattern
                        for operation in operations:
                            operation_name = operation.get('Name', '')

                            # Check if operation matches the pattern
                            operation_matches = False
                            if '*' not in operation_pattern:
                                # Exact operation name match
                                operation_matches = operation_name == operation_pattern
                            else:
                                # Wildcard operation name match
                                if operation_search_term == '':
                                    # Match all operations
                                    operation_matches = True
                                else:
                                    # Check if operation contains the search term
                                    operation_matches = (
                                        operation_search_term in operation_name.lower()
                                    )

                            if operation_matches:
                                # Check if this operation has the required metric type
                                metric_refs = operation.get('MetricReferences', [])
                                has_metric_type = any(
                                    ref.get('MetricType', '') == metric_type
                                    or (
                                        metric_type == 'Availability'
                                        and ref.get('MetricType', '') == 'Fault'
                                    )
                                    for ref in metric_refs
                                )

                                if has_metric_type:
                                    service_target = _create_service_target(
                                        service_name, environment
                                    )
                                    expanded_targets.append(
                                        {
                                            'Type': 'service_operation',
                                            'Data': {
                                                'ServiceOperation': {
                                                    'Service': service_target['Data']['Service'],
                                                    'Operation': operation_name,
                                                    'MetricType': metric_type,
                                                }
                                            },
                                        }
                                    )
                                    matches_found += 1
                                    logger.debug(
                                        f'Added operation: {service_name} -> {operation_name} ({metric_type})'
                                    )
                                else:
                                    logger.debug(
                                        f'Skipping operation {operation_name} - no {metric_type} metric available'
                                    )

                    except Exception as e:
                        logger.warning(
                            f"Failed to get operations for service '{service_name}': {e}"
                        )
                        continue

                logger.debug(
                    f"Service operation pattern '{service_pattern}' + '{operation_pattern}' expanded to {matches_found} targets"
                )

        except Exception as e:
            logger.warning(f'Failed to expand service operation patterns: {e}')
            raise ValueError(f'Failed to expand service operation wildcard patterns. {str(e)}')

    return expanded_targets
