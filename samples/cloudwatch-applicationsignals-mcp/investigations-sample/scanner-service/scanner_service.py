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

#!/usr/bin/env python3
"""Document Scanner Service - Simulates malware/content scanning.

Intentionally slow to demonstrate performance issues.
"""

import time
import uvicorn
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel


app = FastAPI(title='Document Scanner Service', version='1.0.0')


class ScanResponse(BaseModel):
    """Response model for document scan results."""

    status: str
    message: str
    scan_time_ms: float
    size_kb: float


@app.post('/scan', response_model=ScanResponse)
async def scan_document(file: UploadFile = File(...)):
    """Scan document for threats.

    Simulates scanning by sleeping 1ms per KB.
    """
    start_time = time.time()

    # Read file content
    content = await file.read()
    size_kb = len(content) / 1024

    # Simulate scanning time: 1ms per KB
    scan_duration = size_kb * 0.001
    time.sleep(scan_duration)

    elapsed_ms = (time.time() - start_time) * 1000

    return ScanResponse(
        status='safe',
        message=f"Document '{file.filename}' passed security scan",
        scan_time_ms=round(elapsed_ms, 2),
        size_kb=round(size_kb, 2),
    )


@app.get('/health')
async def health_check():
    """Health check endpoint."""
    return {'status': 'healthy', 'service': 'scanner'}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8001)
