# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Sorted Set operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import Any, Dict, Optional
from valkey.exceptions import ValkeyError


@mcp.tool()
async def sorted_set_add(key: str, mapping: Dict[Any, float]) -> str:
    """Add member-score pairs to sorted set.

    Args:
        key: The name of the key
        mapping: Dictionary of member-score pairs

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.zadd(key, mapping)
        return f"Successfully added {result} new member(s) to sorted set '{key}'"
    except ValkeyError as e:
        return f"Error adding to sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_add_incr(key: str, member: Any, score: float) -> str:
    """Add member to sorted set or increment its score.

    Args:
        key: The name of the key
        member: The member to add/update
        score: Score to add to existing score (or initial score)

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.zincrby(key, score, member)
        return f"Successfully set score for member in sorted set '{key}' to {result}"
    except ValkeyError as e:
        return f"Error incrementing score in sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_remove(key: str, *members: Any) -> str:
    """Remove member(s) from sorted set.

    Args:
        key: The name of the key
        *members: Members to remove

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.zrem(key, *members)
        return f"Successfully removed {result} member(s) from sorted set '{key}'"
    except ValkeyError as e:
        return f"Error removing from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_remove_by_rank(key: str, start: int, stop: int) -> str:
    """Remove members by rank range.

    Args:
        key: The name of the key
        start: Start rank (inclusive)
        stop: Stop rank (inclusive)

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.zremrangebyrank(key, start, stop)
        return f"Successfully removed {result} member(s) by rank from sorted set '{key}'"
    except ValkeyError as e:
        return f"Error removing by rank from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_remove_by_score(key: str, min_score: float, max_score: float) -> str:
    """Remove members by score range.

    Args:
        key: The name of the key
        min_score: Minimum score (inclusive)
        max_score: Maximum score (inclusive)

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.zremrangebyscore(key, min_score, max_score)
        return f"Successfully removed {result} member(s) by score from sorted set '{key}'"
    except ValkeyError as e:
        return f"Error removing by score from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_remove_by_lex(key: str, min_lex: str, max_lex: str) -> str:
    """Remove members by lexicographical range.

    Args:
        key: The name of the key
        min_lex: Minimum value (inclusive)
        max_lex: Maximum value (inclusive)

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.zremrangebylex(key, min_lex, max_lex)
        return f"Successfully removed {result} member(s) by lex range from sorted set '{key}'"
    except ValkeyError as e:
        return f"Error removing by lex range from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_cardinality(
    key: str, min_score: Optional[float] = None, max_score: Optional[float] = None
) -> str:
    """Get number of members in sorted set.

    Args:
        key: The name of the key
        min_score: Minimum score (optional)
        max_score: Maximum score (optional)

    Returns:
        Number of members or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if min_score is not None and max_score is not None:
            result = r.zcount(key, min_score, max_score)
        else:
            result = r.zcard(key)
        return str(result)
    except ValkeyError as e:
        return f"Error getting sorted set cardinality for '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_score(key: str, member: Any) -> str:
    """Get score of member in sorted set.

    Args:
        key: The name of the key
        member: The member to get score for

    Returns:
        Score or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.zscore(key, member)
        if result is None:
            return f"Member not found in sorted set '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting score from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_rank(key: str, member: Any, reverse: bool = False) -> str:
    """Get rank of member in sorted set.

    Args:
        key: The name of the key
        member: The member to get rank for
        reverse: If True, get rank in reverse order (highest first)

    Returns:
        Rank or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if reverse:
            result = r.zrevrank(key, member)
        else:
            result = r.zrank(key, member)
        if result is None:
            return f"Member not found in sorted set '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting rank from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_range(
    key: str, start: int = 0, stop: int = -1, withscores: bool = False, reverse: bool = False
) -> str:
    """Get range of members from sorted set.

    Args:
        key: The name of the key
        start: Start index (inclusive)
        stop: Stop index (inclusive)
        withscores: Include scores in result
        reverse: Return results in reverse order

    Returns:
        List of members (with scores if requested) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if reverse:
            result = r.zrevrange(key, start, stop, withscores=withscores)
        else:
            result = r.zrange(key, start, stop, withscores=withscores)
        if not result:
            return f"No members found in range for sorted set '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting range from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_range_by_score(
    key: str,
    min_score: float,
    max_score: float,
    withscores: bool = False,
    reverse: bool = False,
    offset: Optional[int] = None,
    count: Optional[int] = None,
) -> str:
    """Get range of members by score.

    Args:
        key: The name of the key
        min_score: Minimum score (inclusive)
        max_score: Maximum score (inclusive)
        withscores: Include scores in result
        reverse: Return results in reverse order
        offset: Number of members to skip
        count: Maximum number of members to return

    Returns:
        List of members (with scores if requested) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if reverse:
            result = r.zrevrangebyscore(
                key, max_score, min_score, withscores=withscores, start=offset, num=count
            )
        else:
            result = r.zrangebyscore(
                key, min_score, max_score, withscores=withscores, start=offset, num=count
            )
        if not result:
            return f"No members found in score range for sorted set '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting score range from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_range_by_lex(
    key: str,
    min_lex: str,
    max_lex: str,
    reverse: bool = False,
    offset: Optional[int] = None,
    count: Optional[int] = None,
) -> str:
    """Get range of members by lexicographical order.

    Args:
        key: The name of the key
        min_lex: Minimum value (inclusive)
        max_lex: Maximum value (inclusive)
        reverse: Return results in reverse order
        offset: Number of members to skip
        count: Maximum number of members to return

    Returns:
        List of members or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if reverse:
            result = r.zrevrangebylex(key, max_lex, min_lex, start=offset, num=count)
        else:
            result = r.zrangebylex(key, min_lex, max_lex, start=offset, num=count)
        if not result:
            return f"No members found in lex range for sorted set '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting lex range from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_popmin(key: str, count: Optional[int] = None) -> str:
    """Remove and return members with lowest scores.

    Args:
        key: The name of the key
        count: Number of members to pop (optional)

    Returns:
        Popped members with scores or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if count:
            result = r.zpopmin(key, count)
        else:
            result = r.zpopmin(key)
        if not result:
            return f"Sorted set '{key}' is empty"
        return str(result)
    except ValkeyError as e:
        return f"Error popping min from sorted set '{key}': {str(e)}"


@mcp.tool()
async def sorted_set_popmax(key: str, count: Optional[int] = None) -> str:
    """Remove and return members with highest scores.

    Args:
        key: The name of the key
        count: Number of members to pop (optional)

    Returns:
        Popped members with scores or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if count:
            result = r.zpopmax(key, count)
        else:
            result = r.zpopmax(key)
        if not result:
            return f"Sorted set '{key}' is empty"
        return str(result)
    except ValkeyError as e:
        return f"Error popping max from sorted set '{key}': {str(e)}"
