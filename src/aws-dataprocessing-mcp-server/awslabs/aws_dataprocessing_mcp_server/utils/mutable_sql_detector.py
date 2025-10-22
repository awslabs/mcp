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

import re


# -- Mutating keyword set for quick string matching --
MUTATING_KEYWORDS = {
    'INSERT',
    'UPDATE',
    'DELETE',
    'REPLACE',
    'TRUNCATE',
    'CREATE',
    'DROP',
    'ALTER',
    'RENAME',
    'GRANT',
    'REVOKE',
    'LOAD DATA',
    'LOAD XML',
    'INSTALL PLUGIN',
    'UNINSTALL PLUGIN',
}

MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(re.escape(k) for k in MUTATING_KEYWORDS) + r')\b'
)

# -- Regex for DDL statements --
DDL_REGEX = re.compile(
    r"""
    ^\s*(
        CREATE\s+(TABLE|VIEW|INDEX|TRIGGER|PROCEDURE|FUNCTION|EVENT)|
        DROP\s+(TABLE|VIEW|INDEX|TRIGGER|PROCEDURE|FUNCTION|EVENT)|
        ALTER\s+(TABLE|VIEW|TRIGGER|PROCEDURE|FUNCTION|EVENT)|
        RENAME\s+(TABLE)|
        TRUNCATE
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def detect_mutating_keywords(sql: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments)."""
    matched = []

    if DDL_REGEX.search(sql):
        matched.append('DDL')

    # Match individual keywords from MUTATING_KEYWORDS
    keyword_matches = MUTATING_PATTERN.findall(sql)
    if keyword_matches:
        # Deduplicate and normalize casing
        matched.extend(sorted({k.upper() for k in keyword_matches}))

    return matched
