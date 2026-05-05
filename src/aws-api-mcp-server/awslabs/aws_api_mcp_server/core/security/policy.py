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
import re
from ...core.common.config import READ_OPERATIONS_ONLY_MODE, REQUIRE_MUTATION_CONSENT
from enum import Enum
from loguru import logger
from pathlib import Path
from typing import Dict, List, Optional, Set


class PolicyDecision(Enum):
    """Class to list the policy decisions."""

    DENY = 'deny'
    ELICIT = 'elicit'
    ALLOW = 'allow'


def check_elicitation_support(ctx) -> bool:
    """Check if the context supports elicitation."""
    if ctx is None:
        return False
    try:
        return hasattr(ctx, 'elicit')
    except Exception:
        return False


class SecurityPolicy:
    """Class to determine if the command is in he security policy or not."""

    def __init__(self, ctx=None):
        """Initialize the policy lists."""
        self.denylist: Set[str] = set()
        self.elicit_list: Set[str] = set()
        self.customizations: Dict[str, List[str]] = {}

        # Determine elicitation support once during initialization
        self.supports_elicitation = check_elicitation_support(ctx)

        self._load_policy()

    def _load_policy(self):
        """Load security policy from user directory."""
        policy_path = Path.home() / '.aws' / 'aws-api-mcp' / 'mcp-security-policy.json'

        if not policy_path.exists():
            logger.warning(
                'No security policy file found at {}, not applying any additional security policies',
                policy_path,
            )
            return

        try:
            # Read and parse the file
            with open(policy_path, 'r') as policy_file:
                policy_data = json.load(policy_file)

            policy = policy_data.get('policy', {})

            # Load denylist
            if 'denyList' in policy:
                self.denylist = set(policy['denyList'])
                logger.info('Loaded {} commands in denylist', len(self.denylist))

            # Load elicit list (consent list)
            if 'elicitList' in policy:
                self.elicit_list = set(policy['elicitList'])
                logger.info('Loaded {} commands in elicit list', len(self.elicit_list))

        except Exception as e:
            logger.error('Failed to load security policy from {}: {}', policy_path, e)

        self._load_customizations()

    def _load_customizations(self):
        """Load customizations from separate file."""
        customization_path = Path(__file__).parent / 'aws_api_customization.json'

        try:
            with open(customization_path, 'r') as f:
                data = json.load(f)

            customizations = data.get('customizations', {})

            for cmd, config in customizations.items():
                api_calls = config.get('api_calls', [])
                self.customizations[cmd] = api_calls

            logger.info('Loaded {} customizations', len(self.customizations))

        except Exception as e:
            logger.error('Failed to load customizations from {}: {}', customization_path, e)
            raise

    def determine_policy_effect(
        self, service: str, operation: str, is_read_only: bool
    ) -> PolicyDecision:
        """Get policy decision for a service/operation combination.

        Priority: deny > elicit > default behavior
        """
        operation_kebab = operation.replace('_', '-')
        operation_kebab = re.sub('([A-Z])', r'-\1', operation_kebab).lower().lstrip('-')

        api_call = f'aws {service} {operation_kebab}'

        # Check denylist first
        if api_call in self.denylist:
            return PolicyDecision.DENY

        # Check elicit list
        if api_call in self.elicit_list:
            # If client doesn't support elicitation, treat the elicit list as deny
            if not self.supports_elicitation:
                return PolicyDecision.DENY
            return PolicyDecision.ELICIT

        if READ_OPERATIONS_ONLY_MODE and not is_read_only:
            return PolicyDecision.DENY

        if REQUIRE_MUTATION_CONSENT and not is_read_only:
            return PolicyDecision.ELICIT

        # Default behavior: allow all operations
        return PolicyDecision.ALLOW

    def check_customization(self, ir, is_read_only_func) -> Optional[PolicyDecision]:
        """Check if command matches a customization and return the highest priority decision.

        Returns None if no customization matches.
        """
        # Check if IR has the required metadata
        if (
            not ir.command_metadata
            or not getattr(ir.command_metadata, 'service_sdk_name', None)
            or not getattr(ir.command_metadata, 'operation_sdk_name', None)
        ):
            return None

        # Extract base command from IR (e.g., "s3 cp")
        service = ir.command_metadata.service_sdk_name
        operation = ir.command_metadata.operation_sdk_name

        # Convert operation to kebab-case if needed
        operation_kebab = operation.replace('_', '-')
        operation_kebab = re.sub('([A-Z])', r'-\1', operation_kebab).lower().lstrip('-')

        base_cmd = f'{service} {operation_kebab}'

        if base_cmd not in self.customizations:
            return None

        api_calls = self.customizations[base_cmd]
        decisions = []

        # Check the parent command itself
        parent_api_call = f'aws {base_cmd}'
        if parent_api_call in self.denylist:
            return PolicyDecision.DENY
        elif parent_api_call in self.elicit_list:
            if not self.supports_elicitation:
                return PolicyDecision.DENY
            decisions.append(PolicyDecision.ELICIT)

        # Check all underlying API calls
        for api_call in api_calls:
            # Parse service and operation from api_call
            api_parts = api_call.strip().split()
            # This should never happen now due to validation at load time
            if len(api_parts) < 3 or api_parts[0] != 'aws':
                logger.error('Unexpected invalid API call format: {}', api_call)
                continue

            service = api_parts[1]
            operation = api_parts[2].replace('-', '_')

            # Check against denylist/elicitlist first
            if api_call in self.denylist:
                return PolicyDecision.DENY
            elif api_call in self.elicit_list:
                if not self.supports_elicitation:
                    return PolicyDecision.DENY
                decisions.append(PolicyDecision.ELICIT)
            else:
                # Check default behavior based on read-only status
                is_read_only = is_read_only_func(service, operation)
                decision = self.determine_policy_effect(service, operation, is_read_only)
                decisions.append(decision)

        # Return highest priority decision: DENY > ELICIT > ALLOW

        if PolicyDecision.DENY in decisions:
            return PolicyDecision.DENY
        elif PolicyDecision.ELICIT in decisions:
            return PolicyDecision.ELICIT
        else:
            return PolicyDecision.ALLOW
