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

import json
import os
import re
import requests
import shutil
import tempfile
import time
import zipfile
from .config import EMBEDDING_MODEL_DIR
from botocore.response import StreamingBody
from contextlib import contextmanager
from datetime import datetime
from loguru import logger
from pathlib import Path
from typing import Any


@contextmanager
def operation_timer(service: str, operation: str, region: str):
    """Context manager for timing interpretation calls.

    :param service: The service name.
    :param operation: The operation name.
    :param region: The region where the call is being made
    """
    start = time.perf_counter()
    logger.info('Interpreting operation {}.{} for region {}', service, operation, region)
    yield
    end = time.perf_counter()
    elapsed_time = end - start
    logger.info('Operation {}.{} interpreted in {} seconds', service, operation, elapsed_time)


class Boto3Encoder(json.JSONEncoder):
    """Custom JSON encoder for boto3 objects."""

    def default(self, o):
        """Return a JSON-serializable version of the object."""
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, StreamingBody):
            return o.read().decode('utf-8')

        return super().default(o)


def as_json(boto_response: dict[str, Any]) -> str:
    """Convert a boto3 response dictionary to a JSON string."""
    return json.dumps(boto_response, cls=Boto3Encoder)


def expand_user_home_directory(args: list[str]) -> list[str]:
    """Expand paths beginning with '~' or '~user'."""
    return [os.path.expanduser(arg) for arg in args]


def validate_aws_region(region: str):
    """Checks if provided region is a valid AWS Region."""
    aws_region_pattern = '^(\\w{1,10})-(\\w{1,10}-)?(\\w{1,10})-\\d{1,2}$'

    if not re.match(aws_region_pattern, region):
        error_message = f'{region} is not a valid AWS Region'
        logger.error(error_message)
        raise ValueError(error_message)


def download_embedding_model(model_name: str):
    """Download embedding model from AWS."""
    download_url = f'https://models.knowledge-mcp.global.api.aws/{model_name}.zip'

    with tempfile.TemporaryDirectory() as tmp_dir:
        logger.debug('Dowloading embedding model {} to {}', model_name, tmp_dir)
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        zip_path = os.path.join(tmp_dir, f'{model_name}.zip')
        Path(
            zip_path
        ).parent.mkdir()  # HF models are structured as '<org_name>/<model>' so we have to create the parent folder

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        extract_dir = os.path.join(EMBEDDING_MODEL_DIR, model_name)
        logger.debug(
            'Extracting embedding model from {} to {}', zip_path, os.path.abspath(extract_dir)
        )
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        except Exception as e:
            logger.error('Failed to extract embedding model: {}', str(e))
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            raise
