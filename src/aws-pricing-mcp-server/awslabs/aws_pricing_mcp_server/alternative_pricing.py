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

"""Alternative pricing plan mappings and hint generation.

This module manages mappings between AWS services and alternative pricing models
like fixed-rate subscriptions and savings plans.
"""

from typing import Any, Dict, List, Optional


ALTERNATIVE_PRICING_MAPPINGS: Dict[str, Dict[str, Any]] = {
    'CloudFrontPlans': {
        'services': ['AmazonCloudFront'],
        'bundled_services': [
            'AmazonCloudFront',
            'AmazonS3',
            'AmazonRoute53',
            'AWSWAF',
            'AWSShield',
        ],
        'keywords': ['fixed rate', 'flat rate', 'monthly subscription', 'plans'],
        'description': 'Fixed monthly plans bundling CDN, storage, DNS, and security',
    },
}


def get_pricing_alternatives(service_code: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve alternatives for all alternative pricing plans that include this service.

    Args:
        service_code: AWS service code (e.g., 'AmazonCloudFront', 'AmazonS3')

    Returns:
        List of hint dictionaries with service_code, type, description, relevance, and guidance,
        or None if no alternatives exist.
    """
    alternatives: List[Dict[str, Any]] = []

    for alt_service_code, alt_info in ALTERNATIVE_PRICING_MAPPINGS.items():
        if service_code in alt_info['services']:
            hint = {
                'service_code': alt_service_code,
                'keywords': alt_info['keywords'],
                'bundled_services': alt_info['bundled_services'],
                'description': alt_info['description'],
            }

            alternatives.append(hint)

    return alternatives if alternatives else None
