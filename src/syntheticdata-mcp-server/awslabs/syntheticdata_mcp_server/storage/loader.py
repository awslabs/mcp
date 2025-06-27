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


"""Unified data loader implementation."""

from .s3 import S3Target
from typing import Any, Dict, List


class UnifiedDataLoader:
    """Loader that supports multiple storage targets."""

    def __init__(self):
        """Initialize with supported storage targets."""
        self.targets = {'s3': S3Target()}

    async def load_data(
        self, data: Dict[str, List[Dict]], targets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Load data to multiple storage targets.

        Args:
            data: Dictionary mapping table names to lists of records
            targets: List of target configurations, each containing:
                - type: Target type (e.g., 's3')
                - config: Target-specific configuration

        Returns:
            Dictionary containing results for each target
        """
        results = {}

        for target_config in targets:
            # Validate target config structure
            if not isinstance(target_config, dict):
                results['unknown'] = {
                    'success': False,
                    'error': 'Invalid target configuration format',
                }
                continue

            target_type = target_config.get('type')
            if not target_type:
                results['unknown'] = {'success': False, 'error': 'Missing target type'}
                continue

            if target_type not in self.targets:
                results[target_type] = {
                    'success': False,
                    'error': f'Unsupported target type: {target_type}',
                }
                continue

            target = self.targets[target_type]
            config = target_config.get('config', {})

            # Validate configuration
            try:
                is_valid = await target.validate(data, config)
                if not is_valid:
                    results[target_type] = {
                        'success': False,
                        'error': 'Invalid configuration or data',
                    }
                    continue
            except Exception as e:
                results[target_type] = {'success': False, 'error': str(e)}
                continue

            # Load data
            try:
                result = await target.load(data, config)
                results[target_type] = result
            except Exception as e:
                results[target_type] = {'success': False, 'error': str(e)}

        return {'success': all(r['success'] for r in results.values()), 'results': results}
