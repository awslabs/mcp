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

"""Test fixtures for storage_lens_tools unit tests."""

# Sample manifest data for testing
CSV_MANIFEST = {
    'sourceAccountId': '123456789012',
    'configId': 'my-dashboard-configuration-id',
    'destinationBucket': 'arn:aws:s3:::amzn-s3-demo-destination-bucket',
    'reportVersion': 'V_1',
    'reportDate': '2020-11-03',
    'reportFormat': 'CSV',
    'reportSchema': 'version_number,configuration_id,report_date,aws_account_number,aws_region,storage_class,record_type,record_value,bucket_name,metric_name,metric_value',
    'reportFiles': [
        {
            'key': 'DestinationPrefix/StorageLens/123456789012/my-dashboard-configuration-id/V_1/reports/dt=2020-11-03/a38f6bc4-2e3d-4355-ac8a-e2fdcf3de158.csv',
            'size': 1603959,
            'md5Checksum': '2177e775870def72b8d84febe1ad3574',  # pragma: allowlist secret
        }
    ],
}

PARQUET_MANIFEST = {
    'sourceAccountId': '123456789012',
    'configId': 'my-dashboard-configuration-id',
    'destinationBucket': 'arn:aws:s3:::amzn-s3-demo-destination-bucket',
    'reportVersion': 'V_1',
    'reportDate': '2020-11-03',
    'reportFormat': 'Parquet',
    'reportSchema': 'message s3.storage.lens { required string version_number; required string configuration_id; required string report_date; required string aws_account_number; required string aws_region; required string storage_class; required string record_type; required string record_value; required string bucket_name; required string metric_name; required long metric_value; }',
    'reportFiles': [
        {
            'key': 'DestinationPrefix/StorageLens/123456789012/my-dashboard-configuration-id/V_1/reports/dt=2020-11-03/bd23de7c-b46a-4cf4-bcc5-b21aac5be0f5.par',
            'size': 14714,
            'md5Checksum': 'b5c741ee0251cd99b90b3e8eff50b944',  # pragma: allowlist secret
        }
    ],
}
