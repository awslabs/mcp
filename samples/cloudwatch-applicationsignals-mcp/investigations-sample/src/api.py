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

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from src.config import settings
from src.database import document_service
from src.models import Document, DocumentList, DownloadURL
from src.scanner_client import scan_file
from src.storage import storage_service
from typing import Optional


router = APIRouter(prefix='/documents', tags=['documents'])


@router.post('', response_model=Document, status_code=201)
async def upload_document(
    file: UploadFile = File(...), title: str = Form(...), tags: str = Form(default='')
):
    """Upload a document with metadata."""
    file_content = await file.read()

    # Run security scan - we cannot upload dangerous documents, all files must be scanned before upload.
    try:
        scan_result = scan_file(file.filename, file_content)
        if scan_result.status != 'safe':
            raise HTTPException(
                status_code=400, detail=f'Security scan failed: {scan_result.message}'
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Validate content type - only a handful of content types supported in v1, filter out the rest
    if file.content_type not in settings.allowed_content_types:
        raise HTTPException(
            status_code=415, detail=f'Content type {file.content_type} not allowed'
        )

    # Validate file size - document-manager is meant for relatively small documents in v1
    if len(file_content) > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=f'File size exceeds maximum allowed size of {settings.max_upload_size} bytes',
        )

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

    try:
        # Create document record first to get document_id
        doc = document_service.create_document(
            title=title,
            filename=file.filename,
            s3_key='',  # Will update after S3 upload
            content_type=file.content_type,
            size_bytes=len(file_content),
            tags=tag_list,
        )

        # Generate S3 key
        s3_key = f'documents/{doc.document_id}/{file.filename}'

        # Upload to S3
        storage_service.upload_file(file_content, s3_key, file.content_type)

        # Update document with S3 key
        updated_doc = document_service.update_document(
            document_id=doc.document_id, title=title, tags=tag_list
        )

        # Manually set s3_key since update doesn't handle it
        updated_doc.s3_key = s3_key

        return updated_doc
    except Exception as e:
        # Cleanup on failure
        if doc:
            try:
                document_service.delete_document(doc.document_id)
                if s3_key:
                    storage_service.delete_file(s3_key)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{document_id}', response_model=Document)
async def get_document(document_id: str):
    """Get document metadata by ID."""
    document = document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail='Document not found')
    return document


@router.get('', response_model=DocumentList)
async def list_documents(
    tags: Optional[list[str]] = Query(None, description='Filter by tags (can specify multiple)'),
    start_date: Optional[str] = Query(None, description='Filter by start date (ISO format)'),
    end_date: Optional[str] = Query(None, description='Filter by end date (ISO format)'),
):
    """List all documents with optional filters."""
    try:
        documents = document_service.list_documents(
            tags=tags, start_date=start_date, end_date=end_date
        )
        return DocumentList(documents=documents, total=len(documents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{document_id}/download', response_model=DownloadURL)
async def get_download_url(document_id: str):
    """Generate presigned URL for document download."""
    # Get document metadata
    document = document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail='Document not found')

    # Check if file exists in S3
    if not storage_service.file_exists(document.s3_key):
        raise HTTPException(status_code=404, detail='Document file not found in storage')

    try:
        # Generate presigned URL
        url = storage_service.generate_presigned_url(
            document.s3_key, expiration=settings.presigned_url_expiration
        )

        return DownloadURL(
            download_url=url, expires_in=settings.presigned_url_expiration, document_id=document_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
