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
from enum import Enum
from loguru import logger
from pathlib import Path
from typing import Dict, List, Optional, Set


class PolicyDecision(Enum):
    """Class to list the policy decisions."""

    DENY = 'deny'
    ELICIT = 'elicit'
    ALLOW = 'allow'


class SecurityPolicy:
    """Class to determine if the command is in he security policy or not."""

    def __init__(self):
        """Initialize the policy lists."""
        self.denylist: Set[str] = set()
        self.elicit_list: Set[str] = set()
        self.customizations: Dict[str, List[str]] = {}
        self._load_policy()

    def _load_policy(self):
        """Load security policy from user directory."""
        policy_dir = Path.home() / '.aws' / 'aws-api-mcp'
        policy_dir.mkdir(parents=True, exist_ok=True)
        policy_path = policy_dir / 'mcp-security-policy.json'
        security_dir = Path(__file__).parent
        customization_path = security_dir / 'aws_api_customization.json'

        if not policy_path.exists():
            logger.info('No security policy file found at {}, using default behavior', policy_path)
        else:
            try:
                with open(policy_path, 'r') as f:
                    policy_data = json.load(f)

                # Load denylist
                if 'denylist' in policy_data:
                    self.denylist = set(policy_data['denylist'])
                    logger.info('Loaded {} commands in denylist', len(self.denylist))

                # Load elicit list (consent list)
                if 'elicitList' in policy_data:
                    self.elicit_list = set(policy_data['elicitList'])
                    logger.info('Loaded {} commands in elicit list', len(self.elicit_list))

            except Exception as e:
                logger.error('Failed to load security policy from {}: {}', policy_path, e)

        # Load customizations from separate file
        if customization_path.exists():
            try:
                with open(customization_path, 'r') as f:
                    customization_data = json.load(f)

                if 'customizations' in customization_data:
                    self.customizations = {}
                    for cmd, config in customization_data['customizations'].items():
                        if 'api_calls' in config:
                            self.customizations[cmd] = config['api_calls']
                    logger.info('Loaded {} customizations', len(self.customizations))

            except Exception as e:
                logger.error('Failed to load customizations from {}: {}', customization_path, e)

    def get_decision(
        self, service: str, operation: str, is_read_only: bool, supports_elicitation: bool
    ) -> PolicyDecision:
        """Get policy decision for a service/operation combination.

        Priority: deny > elicit > default behavior
        """
        operation_kebab = operation.replace('_', '-')
        operation_kebab = re.sub('([A-Z])', r'-\1', operation_kebab).lower().lstrip('-')

        api_call = f'aws {service} {operation_kebab}'

        # s3 service maps to s3api in CLI for some operations
        if service == 's3':
            # For s3 service, also check s3api variant
            api_call_s3api = f'aws s3api {operation_kebab}'

            # Check denylist first
            if api_call in self.denylist or api_call_s3api in self.denylist:
                return PolicyDecision.DENY

            # Check elicit list
            if api_call in self.elicit_list or api_call_s3api in self.elicit_list:
                if not supports_elicitation:
                    return PolicyDecision.DENY
                return PolicyDecision.ELICIT
        else:
            # Check denylist first
            if api_call in self.denylist:
                return PolicyDecision.DENY

            # Check elicit list
            if api_call in self.elicit_list:
                # If client doesn't support elicitation, treat the elicit list as deny
                if not supports_elicitation:
                    return PolicyDecision.DENY
                return PolicyDecision.ELICIT

        # Default behavior: allow all operations
        return PolicyDecision.ALLOW

    def check_customization(
        self, cli_command: str, is_read_only_func, supports_elicitation: bool
    ) -> Optional[PolicyDecision]:
        """Check if command matches a customization and return the highest priority decision.

        Returns None if no customization matches.
        """
        # Extract base command (e.g., "s3 ls" from "aws s3 ls bucket-name")
        parts = cli_command.strip().split()
        if len(parts) < 3 or parts[0] != 'aws':
            return None

        base_cmd = f'{parts[1]} {parts[2]}'

        if base_cmd not in self.customizations:
            return None

        api_calls = self.customizations[base_cmd]
        decisions = []

        # Check the parent command itself
        parent_api_call = f'aws {base_cmd}'
        if parent_api_call in self.denylist:
            return PolicyDecision.DENY
        elif parent_api_call in self.elicit_list:
            if not supports_elicitation:
                return PolicyDecision.DENY
            decisions.append(PolicyDecision.ELICIT)

        # Check all underlying API calls
        for api_call in api_calls:
            # Parse service and operation from api_call
            api_parts = api_call.strip().split()
            if len(api_parts) < 3 or api_parts[0] != 'aws':
                continue

            service = api_parts[1]
            operation = api_parts[2].replace('-', '_')

            # Check against denylist/elicitlist first
            if api_call in self.denylist:
                return PolicyDecision.DENY
            elif api_call in self.elicit_list:
                if not supports_elicitation:
                    return PolicyDecision.DENY
                decisions.append(PolicyDecision.ELICIT)
            else:
                # Check default behavior based on read-only status
                is_read_only = is_read_only_func(service, operation)
                decision = self.get_decision(
                    service, operation, is_read_only, supports_elicitation
                )
                decisions.append(decision)

        # Return highest priority decision: DENY > ELICIT > ALLOW

        if PolicyDecision.DENY in decisions:
            return PolicyDecision.DENY
        elif PolicyDecision.ELICIT in decisions:
            return PolicyDecision.ELICIT
        else:
            return PolicyDecision.ALLOW


security_policy = SecurityPolicy()
