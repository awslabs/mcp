# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.


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
            target_type = target_config['type']
            if target_type not in self.targets:
                results[target_type] = {
                    'success': False,
                    'error': f'Unsupported target type: {target_type}',
                }
                continue

            target = self.targets[target_type]

            # Validate configuration
            is_valid = await target.validate(data, target_config['config'])
            if not is_valid:
                results[target_type] = {'success': False, 'error': 'Invalid configuration or data'}
                continue

            # Load data
            try:
                result = await target.load(data, target_config['config'])
                results[target_type] = result
            except Exception as e:
                results[target_type] = {'success': False, 'error': str(e)}

        return {'success': all(r['success'] for r in results.values()), 'results': results}
