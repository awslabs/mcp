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

"""Vendored botocore C2J service model for ElasticGumbyFrontEndService.

Call ``create_session()`` to get a boto3 Session that can create
``elasticgumbyfrontendservice`` clients.
"""

import functools
from pathlib import Path

import boto3
import botocore.session

_MODEL_DIR = str(Path(__file__).parent)


@functools.lru_cache(maxsize=1)
def create_session() -> boto3.Session:
    """Return a boto3 Session with the vendored FES model registered (cached)."""
    botocore_session = botocore.session.get_session()
    loader = botocore_session.get_component('data_loader')
    if _MODEL_DIR not in loader.search_paths:
        loader.search_paths.insert(0, _MODEL_DIR)
    return boto3.Session(botocore_session=botocore_session)
