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

from ...common.errors import (
    OperationIsNotSupportedInTheRegionError,
)
from typing import Optional


# See https://docs.aws.amazon.com/AmazonS3/latest/userguide/endpoint-directory-buckets-AZ.html
SUPPORTED_REGIONS = [
    'us-east-1',
    'us-east-2',
    'us-west-2',
    'ap-south-1',
    'ap-northeast-1',
    'eu-west-1',
    'eu-north-1',
]


# This is a fix for Boto 3 regions support issue https://github.com/boto/boto3/issues/4684
def validate_s3_express_one_region(service: str, operation: str, region: Optional[str]):
    """Validates whether an S3 Express one region is supported by AWS API."""
    if operation == 'list-directory-buckets':
        if region and region not in SUPPORTED_REGIONS:
            raise OperationIsNotSupportedInTheRegionError(service, operation, region)
