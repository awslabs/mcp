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

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class DocumentBase(BaseModel):
    """Base model for document data."""

    title: str = Field(..., min_length=1, max_length=255)
    tags: list[str] = Field(default_factory=list)


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""

    pass


class DocumentUpdate(BaseModel):
    """Model for updating an existing document."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    tags: Optional[list[str]] = None


class Document(DocumentBase):
    """Complete document model with metadata."""

    document_id: str
    filename: str
    s3_key: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            'example': {
                'document_id': '550e8400-e29b-41d4-a716-446655440000',
                'title': 'Project Proposal',
                'filename': 'proposal.pdf',
                's3_key': 'documents/550e8400-e29b-41d4-a716-446655440000/proposal.pdf',
                'content_type': 'application/pdf',
                'size_bytes': 2048576,
                'tags': ['project', 'proposal', '2024'],
                'uploaded_at': '2024-01-15T10:30:00Z',
                'updated_at': '2024-01-15T10:30:00Z',
            }
        }


class DocumentList(BaseModel):
    """Model for a list of documents."""

    documents: list[Document]
    total: int


class DownloadURL(BaseModel):
    """Model for document download URL."""

    download_url: str
    expires_in: int
    document_id: str
