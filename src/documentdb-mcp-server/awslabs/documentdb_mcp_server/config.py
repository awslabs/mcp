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

"""Configuration settings for DocumentDB MCP Server."""

from awslabs.documentdb_mcp_server.errors import SafeToolError
from fnmatch import fnmatchcase
from loguru import logger
from typing import Any, Dict, List, Optional, Set, Tuple


# Upper bound on documents returned by find/aggregate and sampled by analyzeSchema.
MAX_RESULTS = 1000

# Aggregation stages that write to the database.
WRITE_STAGES = ('$out', '$merge')


class ServerConfig:
    """Configuration class for DocumentDB MCP Server.

    This class contains configuration options that control the server's behavior.
    """

    def __init__(self):
        """Initialize server configuration with default values.

        By default, the server starts in read-only mode for safety.
        """
        self.read_only_mode = True
        self.connection_string: Optional[str] = None
        # Namespace patterns from --allowed-namespaces; None allows every namespace.
        self.allowed_namespaces: Optional[List[str]] = None


# Singleton instance
serverConfig = ServerConfig()


def assert_pipeline_readonly(pipeline: List[Dict[str, Any]]) -> None:
    """Reject aggregation write stages while the server is in read-only mode.

    Every tool that accepts an aggregation pipeline must call this before the
    pipeline reaches the database.

    Args:
        pipeline: The aggregation pipeline supplied by the client.

    Raises:
        SafeToolError: If read-only mode is on and the pipeline contains $out or $merge.
    """
    if not serverConfig.read_only_mode:
        return

    for stage in pipeline:
        denied = next((s for s in WRITE_STAGES if s in stage), None)
        if denied:
            logger.warning(f'Pipeline denied: contains write stage ({denied}) in read-only mode')
            raise SafeToolError(
                'Operation not permitted: Server is configured in read-only mode. '
                'Aggregation pipeline contains write stages ($out or $merge) which are not allowed.'
            )


def bounded_limit(limit: int) -> int:
    """Clamp a client-supplied result limit to the range [1, MAX_RESULTS]."""
    return max(1, min(limit, MAX_RESULTS))


def parse_allowed_namespaces(value: Optional[str]) -> Optional[List[str]]:
    """Parse the --allowed-namespaces value into a list of patterns.

    The value is a comma-separated list of `db` or `db.collection` patterns, with
    shell-style wildcards (`*`, `?`, `[...]`). `db` alone allows every collection in
    that database. An empty or missing value returns None, which allows everything.

    Raises:
        ValueError: If a pattern has an empty database part.
    """
    if value is None or not value.strip():
        return None
    patterns = [p.strip() for p in value.split(',') if p.strip()]
    for pattern in patterns:
        if not pattern.split('.', 1)[0]:
            raise ValueError(f"Invalid namespace pattern '{pattern}': the database part is empty")
    return patterns


def _split_pattern(pattern: str) -> Tuple[str, str]:
    # Database names cannot contain '.', so the first '.' separates the collection.
    db_pattern, _, coll_pattern = pattern.partition('.')
    return db_pattern, coll_pattern or '*'


def is_database_allowed(database: str) -> bool:
    """Whether any allowed pattern covers at least part of this database."""
    if serverConfig.allowed_namespaces is None:
        return True
    return any(
        fnmatchcase(database, _split_pattern(p)[0]) for p in serverConfig.allowed_namespaces
    )


def is_namespace_allowed(database: str, collection: str) -> bool:
    """Whether database.collection matches an allowed pattern."""
    if serverConfig.allowed_namespaces is None:
        return True
    for pattern in serverConfig.allowed_namespaces:
        db_pattern, coll_pattern = _split_pattern(pattern)
        if fnmatchcase(database, db_pattern) and fnmatchcase(collection, coll_pattern):
            return True
    return False


def _namespace_denied(namespace: str) -> SafeToolError:
    logger.warning(f'Operation denied: namespace {namespace!r} is not in --allowed-namespaces')
    return SafeToolError(
        f"Operation not permitted: namespace '{namespace}' is not in the server's allowed namespaces."
    )


def assert_database_allowed(database: str) -> None:
    """Reject a database that no --allowed-namespaces pattern covers."""
    if not is_database_allowed(database):
        raise _namespace_denied(database)


def assert_namespace_allowed(database: str, collection: str) -> None:
    """Reject database.collection unless an --allowed-namespaces pattern matches it."""
    if not is_namespace_allowed(database, collection):
        raise _namespace_denied(f'{database}.{collection}')


def _target_namespace(database: str, target: Any, coll_key: str = 'coll') -> Tuple[str, str]:
    """Resolve a stage target that is either a collection name or {db, coll}."""
    if isinstance(target, str):
        return database, target
    if isinstance(target, dict) and isinstance(target.get(coll_key), str):
        target_db = target.get('db', database)
        if isinstance(target_db, str):
            return target_db, target[coll_key]
    raise SafeToolError(
        'Operation not permitted: the pipeline names a collection in a form the server cannot check '
        'against its allowed namespaces.'
    )


def pipeline_namespaces(database: str, pipeline: Any) -> Set[Tuple[str, str]]:
    """Every (database, collection) that an aggregation pipeline reads from or writes to.

    Covers $lookup, $graphLookup, $unionWith, $out and $merge, and the sub-pipelines
    of $lookup, $unionWith and $facet.
    """
    found: Set[Tuple[str, str]] = set()
    if not isinstance(pipeline, list):
        return found
    for stage in pipeline:
        if not isinstance(stage, dict):
            continue
        for op, spec in stage.items():
            if op == '$lookup' and isinstance(spec, dict):
                if 'from' in spec:
                    found.add(_target_namespace(database, spec['from']))
                found |= pipeline_namespaces(database, spec.get('pipeline'))
            elif op == '$graphLookup' and isinstance(spec, dict):
                found.add(_target_namespace(database, spec.get('from')))
            elif op == '$unionWith':
                if isinstance(spec, dict):
                    if 'coll' in spec:
                        found.add(_target_namespace(database, spec['coll']))
                    found |= pipeline_namespaces(database, spec.get('pipeline'))
                else:
                    found.add(_target_namespace(database, spec))
            elif op == '$out':
                found.add(_target_namespace(database, spec))
            elif op == '$merge':
                into = spec.get('into') if isinstance(spec, dict) else spec
                found.add(_target_namespace(database, into))
            elif op == '$facet' and isinstance(spec, dict):
                for sub_pipeline in spec.values():
                    found |= pipeline_namespaces(database, sub_pipeline)
    return found


def assert_pipeline_namespaces_allowed(database: str, collection: str, pipeline: Any) -> None:
    """Reject a pipeline whose source or any referenced collection is not allowed."""
    if serverConfig.allowed_namespaces is None:
        return
    assert_namespace_allowed(database, collection)
    for target_db, target_coll in sorted(pipeline_namespaces(database, pipeline)):
        assert_namespace_allowed(target_db, target_coll)
