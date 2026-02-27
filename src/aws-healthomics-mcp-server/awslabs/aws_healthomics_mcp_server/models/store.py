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

"""Store management data models for HealthOmics sequence stores and reference stores."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional


# --- Enums ---


class ReadSetFileType(str, Enum):
    """Supported read set file types."""

    FASTQ = 'FASTQ'
    BAM = 'BAM'
    CRAM = 'CRAM'
    UBAM = 'UBAM'


class ReadSetStatus(str, Enum):
    """Read set statuses."""

    ARCHIVED = 'ARCHIVED'
    ACTIVATING = 'ACTIVATING'
    ACTIVE = 'ACTIVE'
    DELETING = 'DELETING'
    DELETED = 'DELETED'
    PROCESSING_UPLOAD = 'PROCESSING_UPLOAD'
    UPLOAD_FAILED = 'UPLOAD_FAILED'


class ImportJobStatus(str, Enum):
    """Import/export job statuses."""

    SUBMITTED = 'SUBMITTED'
    IN_PROGRESS = 'IN_PROGRESS'
    CANCELLING = 'CANCELLING'
    CANCELLED = 'CANCELLED'
    FAILED = 'FAILED'
    COMPLETED = 'COMPLETED'
    COMPLETED_WITH_FAILURES = 'COMPLETED_WITH_FAILURES'


class ReferenceStatus(str, Enum):
    """Reference statuses."""

    ACTIVE = 'ACTIVE'
    DELETING = 'DELETING'
    DELETED = 'DELETED'


# --- Sequence Store Models ---


class SequenceStoreSummary(BaseModel):
    """Summary of a sequence store."""

    id: str
    arn: str
    name: str
    description: Optional[str] = None
    creationTime: datetime
    fallbackLocation: Optional[str] = None


class SequenceStoreDetail(SequenceStoreSummary):
    """Detailed sequence store information."""

    sseConfig: Optional[Dict] = None
    eTag: Optional[str] = None


class ReadSetSummary(BaseModel):
    """Summary of a read set."""

    id: str
    arn: str
    sequenceStoreId: str
    name: Optional[str] = None
    status: str
    fileType: str
    subjectId: Optional[str] = None
    sampleId: Optional[str] = None
    referenceArn: Optional[str] = None
    creationTime: datetime


class ReadSetImportSource(BaseModel):
    """Source configuration for a read set import."""

    sourceFileType: str
    sourceFiles: Dict[str, str]
    referenceArn: Optional[str] = None
    sampleId: Optional[str] = None
    subjectId: Optional[str] = None
    name: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


# --- Reference Store Models ---


class ReferenceStoreSummary(BaseModel):
    """Summary of a reference store."""

    id: str
    arn: str
    name: str
    description: Optional[str] = None
    creationTime: datetime


class ReferenceStoreDetail(ReferenceStoreSummary):
    """Detailed reference store information."""

    sseConfig: Optional[Dict] = None
    eTag: Optional[str] = None


class ReferenceSummary(BaseModel):
    """Summary of a reference."""

    id: str
    arn: str
    referenceStoreId: str
    name: Optional[str] = None
    status: str
    description: Optional[str] = None
    md5: Optional[str] = None
    creationTime: datetime


class ReferenceImportSource(BaseModel):
    """Source configuration for a reference import."""

    sourceFile: str
    name: str
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
