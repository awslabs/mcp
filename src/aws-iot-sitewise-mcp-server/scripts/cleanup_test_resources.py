#!/usr/bin/env python3
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

#!/usr/bin/env python3
"""Standalone script to clean up orphaned AWS IoT SiteWise test resources.

This script can be run independently to clean up any test resources that may
have been left behind from failed tests.

Usage:
    python scripts/cleanup_test_resources.py [--dry-run] [--prefix PREFIX] [--region REGION]
"""

import argparse
import logging
import os
import sys
from test_cleanup_utils import SiteWiseResourceTracker


# Add the test directory to the path so we can import test utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'test'))


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(
        description='Clean up orphaned AWS IoT SiteWise test resources'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be cleaned up without actually deleting resources',
    )
    parser.add_argument(
        '--prefix',
        default='mcp-test',
        help='Test resource prefix to search for (default: mcp-test)',
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region to clean up (default: us-east-1)',
    )
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    logger.info('Starting cleanup for region: {}, prefix: {}'.format(args.region, args.prefix))

    try:
        tracker = SiteWiseResourceTracker(region=args.region, test_prefix=args.prefix)

        if not tracker.is_aws_available():
            logger.error('AWS credentials not available or invalid')
            return 1

        # Find orphaned resources
        logger.info('Scanning for orphaned test resources...')

        # Scan for orphaned resources
        tracker.find_and_cleanup_test_resources()

        # Count resources found
        found_counts = {
            'assets': len(tracker.created_assets),
            'asset_models': len(tracker.created_asset_models),
            'gateways': len(tracker.created_gateways),
            'access_policies': len(tracker.created_access_policies),
        }

        total_found = sum(found_counts.values())

        if total_found == 0:
            logger.info('No orphaned test resources found')
            return 0

        logger.info('Found {} orphaned test resources:'.format(total_found))
        for resource_type, count in found_counts.items():
            if count > 0:
                logger.info('  - {}: {}'.format(resource_type, count))

        if args.dry_run:
            logger.info('Dry run mode - no resources will be deleted')
            return 0

        if not args.force:
            response = input('Delete {} orphaned test resources? (y/N): '.format(total_found))
            if response.lower() not in ['y', 'yes']:
                logger.info('Cleanup cancelled')
                return 0

        # Perform cleanup
        logger.info('Starting resource cleanup...')
        tracker.cleanup_all()
        logger.info('Cleanup completed successfully')

        return 0

    except KeyboardInterrupt:
        logger.warning('Cleanup interrupted by user')
        return 1
    except Exception as e:
        logger.error('Cleanup failed: {}'.format(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())
