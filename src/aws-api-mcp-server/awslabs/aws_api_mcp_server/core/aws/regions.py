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

import boto3
from ..common.errors import AwsRegionResolutionError
from botocore.exceptions import ClientError


# These global services don't have regionalized endpoints
NON_REGIONALIZED_SERVICES = ('iam', 'route53')

# These global services have fixed regionalized endpoints
GLOBAL_SERVICE_REGIONS = {
    'devicefarm': 'us-west-2',
    'ecr-public': 'us-east-1',
    'globalaccelerator': 'us-west-2',
    'marketplace-catalog': 'us-east-1',
    'route53-recovery-control-config': 'us-west-2',
    'route53-recovery-readiness': 'us-west-2',
    'route53domains': 'us-east-1',
    'sagemaker-geospatial': 'us-west-2',
}


def get_active_regions(profile_name: str | None = None) -> list[str]:
    """Return a list of active regions for the given profile."""
    session = boto3.Session(profile_name=profile_name)
    account_client = session.client('account')
    try:
        paginator = account_client.get_paginator('list_regions')
        active_regions = []
        for page in paginator.paginate():
            page_regions = page.get('Regions', [])
            active_regions.extend(
                region['RegionName']
                for region in page_regions
                if region.get('RegionOptStatus') in ['ENABLED', 'ENABLED_BY_DEFAULT']
            )
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'AccessDenied':
            raise AwsRegionResolutionError(
                reason=(
                    f'The IAM principal lacks the "account:ListRegions" permission. '
                    f'Grant this permission to enable multi-region command expansion. '
                    f'Details: {e}'
                ),
                profile_name=profile_name,
            )
        raise AwsRegionResolutionError(
            reason=f'Unexpected AWS API error while listing regions. Details: {e}',
            profile_name=profile_name,
        )
    except Exception as e:
        raise AwsRegionResolutionError(
            reason=f'Unexpected error while retrieving active AWS regions. Details: {e}',
            profile_name=profile_name,
        )

    return active_regions
