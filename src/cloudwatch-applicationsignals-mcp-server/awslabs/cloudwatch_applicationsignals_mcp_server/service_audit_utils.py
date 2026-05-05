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

"""Service-specific utilities for service audit tool."""

from datetime import datetime, timezone
from loguru import logger
from typing import Any, List, Optional


def _ci_get(d: dict, *names) -> Optional[Any]:
    """Case-insensitive dictionary getter."""
    for n in names:
        if n in d:
            return d[n]
    lower = {k.lower(): v for k, v in d.items()}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def _need(d: dict, *names):
    """Get required field from dictionary."""
    v = _ci_get(d, *names)
    if v is None:
        raise ValueError(f'Missing required field: one of {", ".join(names)}')
    return v


def coerce_service_target(t: dict) -> dict:
    """Convert common shorthand inputs into canonical service target.

    Emits: {"Type":"service","Data":{"Service":{"Type":"Service","Name":...,"Environment":...,"AwsAccountId?":...}}}

    Shorthands accepted:
      {"Type":"service","Service":"<name>"}
      {"Type":"service","Data":{"Service":"<name>"}}
      {"Type":"service","Data":{"Service":{"Name":"<name>"}}}
      {"target_type":"service","service":"<name>"}
    """
    ttype = (_ci_get(t, 'Type', 'type', 'target_type') or '').lower()
    if ttype != 'service':
        raise ValueError('not a service target')

    data = _ci_get(t, 'Data', 'data') or {}
    service = _ci_get(data, 'Service', 'service') or _ci_get(t, 'Service', 'service')

    if isinstance(service, str):
        entity = {'Name': service}
    elif isinstance(service, dict):
        entity = dict(service)
    elif isinstance(data, dict) and _ci_get(data, 'Name', 'name'):
        entity = {'Name': _ci_get(data, 'Name', 'name')}
    else:
        raise ValueError("service target missing 'Service' payload")

    if 'Type' not in entity and 'type' not in entity:
        entity['Type'] = 'Service'

    name = _ci_get(entity, 'Name', 'name')
    env = _ci_get(entity, 'Environment', 'environment')
    acct = _ci_get(entity, 'AwsAccountId', 'awsAccountId', 'aws_account_id')

    out = {'Type': 'Service'}
    if name:
        out['Name'] = name
    if env:
        out['Environment'] = env
    if acct:
        out['AwsAccountId'] = acct

    return {'Type': 'service', 'Data': {'Service': out}}


def normalize_service_entity(entity: dict) -> dict:
    """Normalize service entity structure."""
    out = {
        'Type': _ci_get(entity, 'Type', 'type') or 'Service',
        'Name': _need(entity, 'Name', 'name'),
        'Environment': _ci_get(entity, 'Environment', 'environment'),
    }
    acct = _ci_get(entity, 'AwsAccountId', 'awsAccountId', 'aws_account_id')
    if acct:
        out['AwsAccountId'] = acct
    return out


def normalize_service_target(item: dict) -> dict:
    """Normalize service target structure."""
    data = _need(item, 'Data', 'data')
    svc = _ci_get(data, 'Service', 'service')
    svc_entity = normalize_service_entity(svc if isinstance(svc, dict) else data)
    return {'Type': 'service', 'Data': {'Service': svc_entity}}


def normalize_service_targets(raw: List[dict]) -> List[dict]:
    """Normalize and validate service targets."""
    if not isinstance(raw, list):
        raise ValueError('`service_targets` must be a JSON array')
    if len(raw) == 0:
        raise ValueError('`service_targets` must contain at least 1 item')

    out = []
    for i, t in enumerate(raw, 1):
        if not isinstance(t, dict):
            raise ValueError(f'service_targets[{i}] must be an object')

        maybe_type = (_ci_get(t, 'Type', 'type', 'target_type') or '').lower()
        if maybe_type == 'service':
            try:
                t = coerce_service_target(t)  # tolerant upgrade
            except ValueError as e:
                raise ValueError(f'service_targets[{i}] invalid service target: {e}')

        ttype = (_ci_get(t, 'Type', 'type') or '').lower()
        if ttype == 'service':
            out.append(normalize_service_target(t))
        else:
            raise ValueError(
                f"service_targets[{i}].type must be 'service' (this tool only handles service targets)"
            )

    return out


def validate_and_enrich_service_targets(
    normalized_targets: List[dict], applicationsignals_client, unix_start: int, unix_end: int
) -> List[dict]:
    """If a service target exists without Environment, fetch from the API.

    NOTE: This function should only be called AFTER wildcard expansion has been completed.
    Wildcard patterns should be expanded before calling this function.
    """
    enriched_targets = []

    for idx, t in enumerate(normalized_targets, 1):
        target_type = (t.get('Type') or '').lower()

        if target_type == 'service':
            svc = (t.get('Data') or {}).get('Service') or {}
            service_name = svc.get('Name')

            # Check if this is still a wildcard pattern - this should not happen after proper expansion
            if service_name and '*' in service_name:
                raise ValueError(
                    f"service_targets[{idx}]: Wildcard pattern '{service_name}' found in validation phase. "
                    f'Wildcard expansion should have been completed before validation. '
                    f'This indicates an internal processing error.'
                )

            if not svc.get('Environment') and service_name:
                # Fetch service details from API to get environment
                logger.debug(f'Fetching environment for service: {service_name}')
                try:
                    # Get all services to find the one we want
                    services_response = applicationsignals_client.list_services(
                        StartTime=datetime.fromtimestamp(unix_start, tz=timezone.utc),
                        EndTime=datetime.fromtimestamp(unix_end, tz=timezone.utc),
                        MaxResults=100,
                    )

                    # Find the service with matching name
                    target_service = None
                    for service in services_response.get('ServiceSummaries', []):
                        key_attrs = service.get('KeyAttributes', {})
                        if key_attrs.get('Name') == service_name:
                            target_service = service
                            break

                    if target_service:
                        key_attrs = target_service.get('KeyAttributes', {})
                        environment = key_attrs.get('Environment')
                        if environment:
                            # Enrich the service target with the found environment
                            enriched_svc = dict(svc)
                            enriched_svc['Environment'] = environment
                            enriched_target = {
                                'Type': 'service',
                                'Data': {'Service': enriched_svc},
                            }
                            enriched_targets.append(enriched_target)
                            logger.debug(
                                f'Enriched service {service_name} with environment: {environment}'
                            )
                            continue
                        else:
                            raise ValueError(
                                f"service_targets[{idx}]: Service '{service_name}' found but has no Environment. "
                                f'This service may not be properly configured in Application Signals.'
                            )
                    else:
                        raise ValueError(
                            f"service_targets[{idx}]: Service '{service_name}' not found in Application Signals. "
                            f'Use list_monitored_services() to see available services.'
                        )
                except Exception as e:
                    if 'not found' in str(e) or 'Service' in str(e):
                        raise e  # Re-raise our custom error messages
                    else:
                        raise ValueError(
                            f'service_targets[{idx}].Data.Service.Environment is required for service targets. '
                            f"Provide Environment (e.g., 'eks:top-observations/default') or ensure the service exists in Application Signals. "
                            f'API error: {str(e)}'
                        )
            elif not svc.get('Environment'):
                raise ValueError(
                    f'service_targets[{idx}].Data.Service.Environment is required for service targets. '
                    f"Provide Environment (e.g., 'eks:top-observations/default')."
                )
        else:
            # Non-service targets should not be here since this tool only handles services
            logger.warning(
                f"Unexpected target type '{target_type}' in service audit tool - ignoring"
            )

        # Add the target as-is if it doesn't need enrichment
        enriched_targets.append(t)

    return enriched_targets
