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

from boto3 import Session, client
from os import getenv


def get_aws_client(
    service_name: str,
    region_name: str | None = None,
    profile_name: str | None = None,
):
    """AWS Client handler."""
    if region_name is None:
        region_name = getenv('AWS_REGION', 'us-east-1')

    if profile_name is None:
        profile_name = getenv('AWS_PROFILE', None)

    if profile_name:
        session = Session(profile_name=profile_name)
        return session.client(service_name, region_name=region_name)
    else:
        return client(service_name, region_name=region_name)


def get_account_id(profile_name: str | None = None) -> str:
    """AWS Account ID handler."""
    if profile_name:
        session = Session(profile_name=profile_name)
        return session.client('sts').get_caller_identity()['Account']
    else:
        return client('sts').get_caller_identity()['Account']
