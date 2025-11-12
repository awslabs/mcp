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
import time
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from datetime import datetime
from src.config import settings
from src.models import Document
from typing import Optional
from uuid import uuid4


class DocumentService:
    """Service for managing document metadata in DynamoDB."""

    def __init__(self):
        """Initialize DocumentService with DynamoDB table connection."""
        dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.table = dynamodb.Table(settings.dynamodb_table_name)

    def create_document(
        self,
        title: str,
        filename: str,
        s3_key: str,
        content_type: str,
        size_bytes: int,
        tags: list[str],
    ) -> Document:
        """Create document metadata in DynamoDB."""
        document_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        item = {
            'document_id': document_id,
            'title': title,
            'filename': filename,
            's3_key': s3_key,
            'content_type': content_type,
            'size_bytes': size_bytes,
            'tags': tags,
            'uploaded_at': timestamp,
            'updated_at': timestamp,
        }

        try:
            self.table.put_item(Item=item)
            return Document(**item)
        except ClientError as e:
            raise Exception(f'Failed to create document in DynamoDB: {str(e)}')

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve document metadata from DynamoDB with retry logic."""
        max_retries = 4
        base_delay = 0.1

        for attempt in range(max_retries):
            try:
                response = self.table.get_item(Key={'document_id': document_id})
                if 'Item' in response:
                    return Document(**response['Item'])
                return None
            except ClientError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)
                else:
                    raise Exception(f'Failed to retrieve document: {str(e)}')

    def _fetch_tag_with_pagination(self, tag: str, date_filters=None):
        """Pagination handler for tag queries."""
        filter_expr = Attr('tags').contains(tag)
        if date_filters:
            filter_expr = filter_expr & date_filters

        items = []
        response = self.table.scan(FilterExpression=filter_expr)
        items.extend(response.get('Items', []))

        # Handle pagination per tag for accuracy
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                FilterExpression=filter_expr, ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        return items

    def _query_tags(self, tags: list[str], date_filters=None):
        all_results = []
        for tag in tags:
            results = self._fetch_tag_with_pagination(tag, date_filters)
            all_results.extend(results)
        return all_results

    def list_documents(
        self,
        tags: Optional[list[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[Document]:
        """List/search documents with optional filters."""
        print(f'[list_documents] tags={tags}, start_date={start_date}, end_date={end_date}')
        try:
            if tags:
                # Build date filters
                date_filters = None
                if start_date and end_date:
                    date_filters = Attr('uploaded_at').between(start_date, end_date)
                elif start_date:
                    date_filters = Attr('uploaded_at').gte(start_date)
                elif end_date:
                    date_filters = Attr('uploaded_at').lte(end_date)

                all_results = self._query_tags(tags, date_filters)

                # Deduplicate results by document_id
                unique_items = {item['document_id']: item for item in all_results}
                items = list(unique_items.values())
            else:
                filter_expression = None
                if start_date and end_date:
                    filter_expression = Attr('uploaded_at').between(start_date, end_date)
                elif start_date:
                    filter_expression = Attr('uploaded_at').gte(start_date)
                elif end_date:
                    filter_expression = Attr('uploaded_at').lte(end_date)

                if filter_expression:
                    response = self.table.scan(FilterExpression=filter_expression)
                else:
                    response = self.table.scan()

                items = response.get('Items', [])

                while 'LastEvaluatedKey' in response:
                    if filter_expression:
                        response = self.table.scan(
                            FilterExpression=filter_expression,
                            ExclusiveStartKey=response['LastEvaluatedKey'],
                        )
                    else:
                        response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                    items.extend(response.get('Items', []))

            return [Document(**item) for item in items]
        except ClientError as e:
            raise Exception(f'Failed to list documents from DynamoDB: {str(e)}')

    def delete_document(self, document_id: str) -> bool:
        """Delete document metadata from DynamoDB."""
        try:
            self.table.delete_item(Key={'document_id': document_id})
            return True
        except ClientError as e:
            raise Exception(f'Failed to delete document from DynamoDB: {str(e)}')

    def update_document(
        self, document_id: str, title: Optional[str] = None, tags: Optional[list[str]] = None
    ) -> Optional[Document]:
        """Update document metadata."""
        try:
            update_expression = 'SET updated_at = :updated_at'
            expression_values = {':updated_at': datetime.utcnow().isoformat()}

            if title:
                update_expression += ', title = :title'
                expression_values[':title'] = title

            if tags is not None:
                update_expression += ', tags = :tags'
                expression_values[':tags'] = tags

            response = self.table.update_item(
                Key={'document_id': document_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW',
            )

            return Document(**response['Attributes'])
        except ClientError as e:
            raise Exception(f'Failed to update document in DynamoDB: {str(e)}')


document_service = DocumentService()
