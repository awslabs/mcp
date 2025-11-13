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

import io
import requests
from pydantic import BaseModel


SCANNER_URL = 'http://localhost:8001'


class ScanResult(BaseModel):
    """Scanner service response."""

    status: str
    message: str
    scan_time_ms: float
    size_kb: float


def scan_file(filename: str, file_content: bytes) -> ScanResult:
    """Send file to scanner service for security scanning.

    Args:
        filename: Name of the file
        file_content: File content as bytes

    Returns:
        ScanResult object with scan details

    Raises:
        Exception if scan fails
    """
    try:
        response = requests.post(
            f'{SCANNER_URL}/scan', files={'file': (filename, io.BytesIO(file_content))}, timeout=30
        )

        if response.status_code == 200:
            return ScanResult(**response.json())
        else:
            raise Exception(f'Scanner service returned {response.status_code}: {response.text}')

    except requests.exceptions.ConnectionError:
        raise Exception('Could not connect to scanner service - is it running?')
    except requests.exceptions.Timeout:
        raise Exception('Scanner service timed out')
    except Exception as e:
        raise Exception(f'Scanner service error: {str(e)}')
