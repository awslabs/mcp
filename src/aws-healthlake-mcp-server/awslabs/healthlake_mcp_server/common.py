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

import os
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Union

from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from pydantic import BaseModel, Field


class DatastoreStatus(str, Enum):
    """HealthLake datastore status enumeration."""
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    DELETING = "DELETING"
    DELETED = "DELETED"


class FHIRVersion(str, Enum):
    """FHIR version enumeration."""
    R4 = "R4"


class JobStatus(str, Enum):
    """Job status enumeration."""
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOP_REQUESTED = "STOP_REQUESTED"
    STOPPED = "STOPPED"


class JobType(str, Enum):
    """Job type enumeration."""
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"


class PreloadDataType(str, Enum):
    """Preload data type enumeration."""
    SYNTHEA = "SYNTHEA"


class AuthorizationStrategy(str, Enum):
    """Authorization strategy enumeration."""
    SMART_ON_FHIR_V1 = "SMART_ON_FHIR_V1"
    AWS_AUTH = "AWS_AUTH"


class EncryptionKeyType(str, Enum):
    """Encryption key type enumeration."""
    KMS = "KMS"


class Tag(BaseModel):
    """Tag model for HealthLake resources."""
    key: str = Field(..., description="The tag key", alias="Key")
    value: str = Field(..., description="The tag value", alias="Value")


class SseConfiguration(BaseModel):
    """Server-side encryption configuration."""
    kms_encryption_config: Dict[str, Any] = Field(
        ..., description="KMS encryption configuration", alias="KmsEncryptionConfig"
    )


class IdentityProviderConfiguration(BaseModel):
    """Identity provider configuration for SMART on FHIR."""
    authorization_strategy: AuthorizationStrategy = Field(
        ..., description="The authorization strategy", alias="AuthorizationStrategy"
    )
    fine_grained_authorization_enabled: Optional[bool] = Field(
        None, description="Whether fine-grained authorization is enabled", alias="FineGrainedAuthorizationEnabled"
    )
    metadata: Optional[str] = Field(
        None, description="The JSON metadata elements for identity provider", alias="Metadata"
    )
    idp_lambda_arn: Optional[str] = Field(
        None, description="The Amazon Resource Name (ARN) of the Lambda function", alias="IdpLambdaArn"
    )


class CreateDatastoreInput(BaseModel):
    """Input model for creating a HealthLake datastore."""
    datastore_name: Optional[str] = Field(None, description="The user-generated name for the datastore", alias="DatastoreName")
    datastore_type_version: FHIRVersion = Field(..., description="The FHIR version of the datastore", alias="DatastoreTypeVersion")
    sse_configuration: Optional[SseConfiguration] = Field(
        None, description="The server-side encryption key configuration", alias="SseConfiguration"
    )
    preload_data_config: Optional[Dict[str, Any]] = Field(
        None, description="Optional parameter to preload data upon creation", alias="PreloadDataConfig"
    )
    client_token: Optional[str] = Field(
        None, description="Optional user provided token used for ensuring idempotency", alias="ClientToken"
    )
    tags: Optional[List[Tag]] = Field(None, description="Resource tags", alias="Tags")
    identity_provider_configuration: Optional[IdentityProviderConfiguration] = Field(
        None, description="The configuration of the identity provider", alias="IdentityProviderConfiguration"
    )


class StartFHIRImportJobInput(BaseModel):
    """Input model for starting a FHIR import job."""
    job_name: Optional[str] = Field(None, description="The name of the FHIR Import job", alias="JobName")
    input_data_config: Dict[str, Any] = Field(..., description="The input properties of the FHIR Import job", alias="InputDataConfig")
    job_output_data_config: Dict[str, Any] = Field(..., description="The output data configuration", alias="JobOutputDataConfig")
    datastore_id: str = Field(..., description="The AWS-generated datastore ID", alias="DatastoreId")
    data_access_role_arn: str = Field(..., description="The Amazon Resource Name (ARN) that gives HealthLake access permission", alias="DataAccessRoleArn")
    client_token: Optional[str] = Field(None, description="Optional user provided token", alias="ClientToken")


class StartFHIRExportJobInput(BaseModel):
    """Input model for starting a FHIR export job."""
    job_name: Optional[str] = Field(None, description="The user generated name for an export job", alias="JobName")
    output_data_config: Dict[str, Any] = Field(..., description="The output data configuration", alias="OutputDataConfig")
    datastore_id: str = Field(..., description="The AWS generated ID for the datastore", alias="DatastoreId")
    data_access_role_arn: str = Field(..., description="The Amazon Resource Name (ARN) that gives HealthLake access permission", alias="DataAccessRoleArn")
    client_token: Optional[str] = Field(None, description="Optional user provided token", alias="ClientToken")


def handle_exceptions(func):
    """Decorator to handle AWS exceptions consistently."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS ClientError in {func.__name__}: {error_code} - {error_message}")
            raise Exception(f"AWS Error ({error_code}): {error_message}")
        except BotoCoreError as e:
            logger.error(f"BotoCoreError in {func.__name__}: {str(e)}")
            raise Exception(f"AWS Connection Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise
    return wrapper


def mutation_check():
    """Check if mutations are allowed based on environment variable."""
    readonly_mode = os.getenv('HEALTHLAKE_MCP_READONLY', 'false').lower() == 'true'
    if readonly_mode:
        raise Exception(
            "This operation is not allowed in read-only mode. "
            "Set HEALTHLAKE_MCP_READONLY=false to enable write operations."
        )
