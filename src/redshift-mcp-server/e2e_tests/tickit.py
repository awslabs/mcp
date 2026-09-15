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

"""Seeds the TICKIT sample schema into a warehouse, by COPY from a public S3 bucket.

`s3://redshift-downloads/tickit/` is readable by any AWS principal, so the data is never
copied locally and the row counts below are fixed for every account. Both warehouse types
are seeded the same way: `redshift:CreateCluster` does advertise a `LoadSampleData`
parameter, but it is refused on current node types, and Serverless has no equivalent.
"""

import time
from typing import Any


S3_PREFIX = 's3://redshift-downloads/tickit/'

# Row count per table once loaded, measured on both a provisioned cluster and a Serverless
# workgroup. A deviation means the seed did not finish.
EXPECTED_ROWS = {
    'users': 49990,
    'venue': 202,
    'category': 11,
    'date': 365,
    'event': 8798,
    'listing': 192497,
    'sales': 172456,
}

_DDL = (
    'CREATE SCHEMA IF NOT EXISTS {schema}',
    """CREATE TABLE IF NOT EXISTS {schema}.users (
        userid integer not null distkey sortkey, username char(8), firstname varchar(30),
        lastname varchar(30), city varchar(30), state char(2), email varchar(100),
        phone char(14), likesports boolean, liketheatre boolean, likeconcerts boolean,
        likejazz boolean, likeclassical boolean, likeopera boolean, likerock boolean,
        likevegas boolean, likebroadway boolean, likemusicals boolean)""",
    """CREATE TABLE IF NOT EXISTS {schema}.venue (
        venueid smallint not null distkey sortkey, venuename varchar(100),
        venuecity varchar(30), venuestate char(2), venueseats integer)""",
    """CREATE TABLE IF NOT EXISTS {schema}.category (
        catid smallint not null distkey sortkey, catgroup varchar(10),
        catname varchar(10), catdesc varchar(50))""",
    """CREATE TABLE IF NOT EXISTS {schema}.date (
        dateid smallint not null distkey sortkey, caldate date not null,
        day character(3) not null, week smallint not null, month character(5) not null,
        qtr character(5) not null, year smallint not null, holiday boolean default('N'))""",
    """CREATE TABLE IF NOT EXISTS {schema}.event (
        eventid integer not null distkey, venueid smallint not null, catid smallint not null,
        dateid smallint not null sortkey, eventname varchar(200), starttime timestamp)""",
    """CREATE TABLE IF NOT EXISTS {schema}.listing (
        listid integer not null distkey, sellerid integer not null, eventid integer not null,
        dateid smallint not null sortkey, numtickets smallint not null,
        priceperticket decimal(8,2), totalprice decimal(8,2), listtime timestamp)""",
    """CREATE TABLE IF NOT EXISTS {schema}.sales (
        salesid integer not null, listid integer not null distkey, sellerid integer not null,
        buyerid integer not null, eventid integer not null, dateid smallint not null sortkey,
        qtysold smallint not null, pricepaid decimal(8,2), commission decimal(8,2),
        saletime timestamp)""",
)

# Object name and COPY options per table. sales is tab-delimited where the rest are
# pipe-delimited, and the two timestamp columns need explicit formats.
_LOADS = (
    ('users', 'allusers_pipe.txt', "DELIMITER '|'"),
    ('venue', 'venue_pipe.txt', "DELIMITER '|'"),
    ('category', 'category_pipe.txt', "DELIMITER '|'"),
    ('date', 'date2008_pipe.txt', "DELIMITER '|'"),
    ('event', 'allevents_pipe.txt', "DELIMITER '|' TIMEFORMAT 'YYYY-MM-DD HH:MI:SS'"),
    ('listing', 'listings_pipe.txt', "DELIMITER '|'"),
    ('sales', 'sales_tab.txt', "DELIMITER '\\t' TIMEFORMAT 'MM/DD/YYYY HH:MI:SS'"),
)


class SeedError(RuntimeError):
    """A statement failed, or the loaded row counts do not match EXPECTED_ROWS."""


def _run(data_client, target: dict, sql: str, timeout: float = 900.0) -> str:
    """Run one statement and wait for it to settle.

    Args:
        data_client: A redshift-data client.
        target: Addressing and authentication keys, from a `Warehouse` property.
        sql: The statement to run.
        timeout: Seconds to wait before giving up.

    Returns:
        The statement id, for fetching results.

    Raises:
        SeedError: If the statement fails or does not settle in time.
    """
    statement_id = data_client.execute_statement(Sql=sql, **target)['Id']
    deadline = time.monotonic() + timeout

    while True:
        described = data_client.describe_statement(Id=statement_id)
        status = described['Status']
        if status == 'FINISHED':
            return statement_id
        if status in ('FAILED', 'ABORTED'):
            raise SeedError(f'{status}: {described.get("Error", "unknown")}\n  {sql[:120]}')
        if time.monotonic() >= deadline:
            raise SeedError(f'did not settle in {timeout}s: {sql[:120]}')
        time.sleep(2)


def row_counts(data_client, target: dict, schema: str) -> dict[str, int]:
    """Count the rows in every seeded table.

    Args:
        data_client: A redshift-data client.
        target: Addressing and authentication keys.
        schema: The schema holding the tables.

    Returns:
        Table name to row count.
    """
    sql = ' UNION ALL '.join(
        f"SELECT '{table}' AS t, count(*) AS n FROM {schema}.{table}" for table in EXPECTED_ROWS
    )
    statement_id = _run(data_client, target, sql)
    records = data_client.get_statement_result(Id=statement_id)['Records']
    return {row[0]['stringValue']: row[1]['longValue'] for row in records}


def is_seeded(data_client, target: dict, schema: str) -> bool:
    """Report whether the schema already holds the full sample data.

    Lets a second run skip the load, which is what makes a paused-and-resumed warehouse
    cheaper than a fresh one.

    Args:
        data_client: A redshift-data client.
        target: Addressing and authentication keys.
        schema: The schema to inspect.

    Returns:
        True when every table is present with its expected row count.
    """
    try:
        return row_counts(data_client, target, schema) == EXPECTED_ROWS
    except SeedError:
        return False


def seed(data_client, target: dict, schema: str, role_arn: str, region: str) -> dict[str, int]:
    """Create the schema and load every table, then verify the row counts.

    Args:
        data_client: A redshift-data client.
        target: Addressing and authentication keys. Must authenticate as an identity that may
            create a schema, which on a provisioned cluster means the master user.
        schema: The schema to create and load into.
        role_arn: Role Redshift assumes to read the sample-data bucket.
        region: Region of the bucket, passed to COPY so it is not inferred.

    Returns:
        Table name to row count, matching EXPECTED_ROWS.

    Raises:
        SeedError: If any statement fails, or the counts do not match.
    """
    for statement in _DDL:
        _run(data_client, target, statement.format(schema=schema))

    for table, obj, options in _LOADS:
        _run(
            data_client,
            target,
            f"COPY {schema}.{table} FROM '{S3_PREFIX}{obj}' IAM_ROLE '{role_arn}' "
            f"{options} REGION '{region}'",
        )

    counts = row_counts(data_client, target, schema)
    if counts != EXPECTED_ROWS:
        raise SeedError(f'row counts do not match: got {counts}, want {EXPECTED_ROWS}')

    return counts


def grant_read(data_client, target: dict, schema: str, database: str, identity: str) -> None:
    """Give the identity the server under test authenticates as what it needs.

    A fresh provisioned cluster grants an IAM identity nothing, so without this the server
    cannot read the seeded schema, create the scratch tables the read-write scenarios use, or
    read the system views `review_cluster` depends on. Serverless is more permissive, but the
    grants are idempotent, so both are treated alike.

    Args:
        data_client: A redshift-data client.
        target: Addressing and authentication keys, authenticated as the master user.
        schema: The seeded schema.
        database: The database holding it.
        identity: Result of `SELECT current_user` under the server's own credentials.
    """
    for statement in (
        f'GRANT USAGE ON SCHEMA {schema} TO "{identity}"',
        f'GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO "{identity}"',
        f'GRANT ALL ON SCHEMA public TO "{identity}"',
        f'GRANT CREATE ON DATABASE {database} TO "{identity}"',
        f'GRANT ROLE sys:monitor TO "{identity}"',
    ):
        _run(data_client, target, statement)


def current_identity(data_client, target: dict) -> Any:
    """Return `SELECT current_user` for the given credentials.

    Args:
        data_client: A redshift-data client.
        target: Addressing and authentication keys.

    Returns:
        The database identity, such as `IAMR:<role>`.
    """
    statement_id = _run(data_client, target, 'SELECT current_user')
    return data_client.get_statement_result(Id=statement_id)['Records'][0][0]['stringValue']
