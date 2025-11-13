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

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    aws_region: str
    s3_bucket_name: str
    dynamodb_table_name: str
    app_name: str = 'Document Manager API'
    app_version: str = '1.0.0'
    max_upload_size: int = 51200  # 50kB
    allowed_content_types: list[str] = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]
    presigned_url_expiration: int = 3600


settings = Settings()
