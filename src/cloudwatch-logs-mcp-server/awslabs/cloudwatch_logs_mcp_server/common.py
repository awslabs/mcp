from typing import Dict, Set


def remove_null_values(d: Dict):
    """Return a new dictionary with the key-value pair of any null value removed."""
    return {k: v for k, v in d.items() if v}


def filter_by_prefixes(strings: Set[str], prefixes: Set[str]) -> Set[str]:
    """Return strings filtered down to only those that start with any of the prefixes."""
    return {s for s in strings if any(s.startswith(p) for p in prefixes)}
