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

import functools
import os
from botocore.exceptions import ClientError
from loguru import logger
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Tag(BaseModel):
    """Tag model for HealthLake resources."""

    key: str = Field(alias='Key')
    value: str = Field(alias='Value')


class CreateDatastoreInput(BaseModel):
    """Input model for creating a HealthLake datastore."""

    datastore_type_version: str
    datastore_name: Optional[str] = None
    sse_configuration: Optional[Dict[str, Any]] = None
    preload_data_config: Optional[Dict[str, Any]] = None
    client_token: Optional[str] = None
    tags: Optional[List[Tag]] = None
    identity_provider_configuration: Optional[Dict[str, Any]] = None


class StartFHIRImportJobInput(BaseModel):
    """Input model for starting a FHIR import job."""

    input_data_config: Dict[str, Any]
    job_output_data_config: Dict[str, Any]
    datastore_id: str
    data_access_role_arn: str
    job_name: Optional[str] = None
    client_token: Optional[str] = None


class StartFHIRExportJobInput(BaseModel):
    """Input model for starting a FHIR export job."""

    output_data_config: Dict[str, Any]
    datastore_id: str
    data_access_role_arn: str
    job_name: Optional[str] = None
    client_token: Optional[str] = None


def handle_exceptions(func):
    """Decorator to handle exceptions in HealthLake MCP server functions."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f'AWS ClientError: {error_code} - {error_message}')

            # Re-raise with more context
            raise Exception(f'AWS HealthLake Error ({error_code}): {error_message}') from e
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {str(e)}')
            raise

    return wrapper


def mutation_check():
    """Check if mutations are allowed based on environment variable."""
    if os.getenv('HEALTHLAKE_MCP_READONLY', 'false').lower() == 'true':
        raise Exception('Operation not permitted: HealthLake MCP server is in read-only mode')
