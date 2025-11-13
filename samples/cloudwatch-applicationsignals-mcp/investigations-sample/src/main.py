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

from fastapi import FastAPI
from src.api import router
from src.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description='Document management API with S3 storage and DynamoDB metadata',
)

app.include_router(router)


@app.get('/')
async def root():
    """Root endpoint returning API information."""
    return {'name': settings.app_name, 'version': settings.app_version, 'docs': '/docs'}


@app.get('/health')
async def health_check():
    """Health check endpoint."""
    return {'status': 'healthy'}
