import datetime
import json
from typing import Dict, List, Set


def remove_null_values(d: Dict):
    """Return a new dictionary with the key-value pair of any null value removed."""
    return {k: v for k, v in d.items() if v}


def filter_by_prefixes(strings: Set[str], prefixes: Set[str]) -> Set[str]:
    """Return strings filtered down to only those that start with any of the prefixes."""
    return {s for s in strings if any(s.startswith(p) for p in prefixes)}


def epoch_ms_to_utc_iso(ms: int) -> str:
    """Convert milliseconds since epoch to an ISO 8601 timestamp string."""
    return datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc).isoformat()


def clean_up_pattern(pattern_result: List[Dict[str, str]]):
    """Clean up results from an @pattern query to remove extra fields and limit the log samples to 1.

    The main purpose of this is to keep the token usage down because of the potential for results to
    exceed the context window size.
    """
    for entry in pattern_result:
        entry.pop('@tokens', None)
        entry.pop('@visualization', None)
        # limit to 1 sample
        entry['@logSamples'] = json.loads(entry.get('@logSamples', '[]'))[:1]
