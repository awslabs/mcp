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

"""Auto-generated Pydantic models from botocore service model.

Re-exports all model classes and rebuilds Pydantic models so that
cross-file forward references resolve correctly.

DO NOT EDIT — this file is auto-generated from the botocore service model.
Generated from: MediaLive 2017-10-14
Botocore version: 1.40.49
"""

from pydantic import BaseModel

from awslabs.amazon_medialive_mcp_server.models.channel import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.common import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.encoding import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.infrastructure import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.input import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.monitoring import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.multiplex import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.output import *  # noqa: F401, F403
from awslabs.amazon_medialive_mcp_server.models.schedule import *  # noqa: F401, F403


def _rebuild_all_models() -> None:  # pragma: no cover
    """Rebuild Pydantic models with the combined namespace.

    Each domain module uses ``from __future__ import annotations`` so type
    annotations are strings at parse time. When a class in one domain file
    references a type from another, Pydantic needs all names in scope to resolve
    them. This function passes the fully-populated globals() of this module to
    each model's rebuild call.
    """
    ns = {k: v for k, v in globals().items() if not k.startswith('_')}
    for obj in list(ns.values()):
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
            try:
                obj.model_rebuild(_types_namespace=ns)
            except Exception:
                pass


_rebuild_all_models()  # pragma: no cover
