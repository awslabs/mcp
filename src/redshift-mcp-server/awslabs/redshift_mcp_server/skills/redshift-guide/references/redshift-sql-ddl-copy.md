# Redshift DDL, COPY & UNLOAD

## CREATE TABLE — distribution + sort are the highest-impact choices

```sql
CREATE TABLE <schema, identifier, no quotes>.<table, identifier, no quotes> (
    view_id         BIGINT IDENTITY(1,1),
    user_id         INT NOT NULL,
    page_url        VARCHAR(2048) ENCODE ZSTD,
    view_ts         TIMESTAMP NOT NULL DEFAULT SYSDATE,
    device_type     VARCHAR(50) ENCODE BYTEDICT
)
DISTSTYLE KEY DISTKEY (user_id)
COMPOUND SORTKEY (view_ts, user_id);
```

`AUTO` is the default for both DISTSTYLE and SORTKEY, and is the documented
recommendation for most tables — omit the clauses and let Redshift choose. Specify
them deliberately (as above) when the join/filter pattern is known.

**Distribution:** `AUTO` (default — Redshift chooses and can change it as the table
grows), `KEY` (large table joined on one column), `ALL` (small dim table), `EVEN`
(no clear join key).
**Sort key:** `AUTO` (default), `COMPOUND` (range scans on leading columns, e.g.
time series), `INTERLEAVED` (equal-weight multi-column filters).
**Encoding:** `AZ64` (numeric/date), `ZSTD` (VARCHAR), `BYTEDICT` (low-cardinality
strings). First sort-key column should be `RAW` (unspecified).

- No `CREATE INDEX` — use SORTKEY. No `SERIAL` — use `IDENTITY(seed, step)`.
- `ALTER COLUMN TYPE` only supports resizing VARCHAR columns — for other type changes, recreate the table.
- `ALTER TABLE ... ALTER DISTKEY`, `ALTER DISTSTYLE`, `ALTER SORTKEY` ARE supported.
- One `ADD COLUMN` per `ALTER TABLE`.

## Late-binding views (`WITH NO SCHEMA BINDING`)

Required for views over external/Spectrum or datashare tables — otherwise CREATE
fails schema validation. Column types resolve at query time.

```sql
CREATE VIEW <schema, identifier, no quotes>.daily_events AS
SELECT event_date, COUNT(*) AS n
FROM <external_schema, identifier, no quotes>.events
GROUP BY 1
WITH NO SCHEMA BINDING;
```

## COPY — load from S3 (Redshift-specific, not standard SQL)

```sql
COPY <schema, identifier, no quotes>.<table, identifier, no quotes>
FROM 's3://<bucket, string, no quotes>/<prefix, string, no quotes>/'
IAM_ROLE '<role_arn, string, single quotes>'
FORMAT AS PARQUET;
```

```sql
-- CSV with header; gzipped JSON; error tolerance
COPY t FROM 's3://<bucket>/data.csv' IAM_ROLE '<role_arn>'
CSV IGNOREHEADER 1 DELIMITER ',' DATEFORMAT 'auto';
COPY t FROM 's3://<bucket>/data/' IAM_ROLE '<role_arn>' JSON 'auto' GZIP;
COPY t FROM 's3://<bucket>/data/' IAM_ROLE '<role_arn>' CSV MAXERROR 100 ACCEPTINVCHARS '?';
```

- `IAM_ROLE` is the role attached to the **cluster** (provisioned) or **namespace**
  (Serverless), not the caller role. "S3ServiceException: Access Denied" → that
  role lacks `s3:GetObject`.
  Scope that role to the specific bucket and prefix it needs — `s3:GetObject` on
  `arn:aws:s3:::<bucket>/<prefix>/*` (plus `s3:ListBucket` on the bucket when loading a
  prefix) — rather than `s3:*` or a managed full-access policy. Because Redshift assumes
  this role, condition its **trust** policy on the calling resource so another cluster or
  workgroup in the account cannot use it:

  ```json
  "Condition": {"StringEquals": {"aws:SourceArn": "<cluster-or-namespace-arn>",
                                 "aws:SourceAccount": "<account-id>"}}
  ```

- Debug loads: `SYS_LOAD_ERROR_DETAIL` (all deployment types); `STL_LOAD_ERRORS` is provisioned single-AZ only — use `SYS_LOAD_ERROR_DETAIL` instead.

## UNLOAD — export to S3

```sql
UNLOAD ('SELECT * FROM <schema>.<table> WHERE view_ts > ''2024-01-01''')
TO 's3://<bucket, string, no quotes>/export/'
IAM_ROLE '<role_arn, string, single quotes>'
PARQUET PARTITION BY (region) ALLOWOVERWRITE
ENCRYPTED KMS_KEY_ID '<kms_key_arn>';
```

Single quotes inside the UNLOAD query string must be doubled (`''`).

`ENCRYPTED KMS_KEY_ID` writes the export with SSE-KMS; the role needs
`kms:GenerateDataKey` on the key. Include it by default — `UNLOAD` writes query results
to S3, where Redshift's own encryption no longer applies. It can be omitted when the
destination bucket already enforces default encryption.

## Iceberg tables (`USING ICEBERG`)

```sql
CREATE TABLE <external_schema, identifier, no quotes>.<table, identifier, no quotes> (
    event_id   INT,
    user_name  VARCHAR,
    event_time TIMESTAMP,
    amount     DOUBLE PRECISION
)
USING ICEBERG
LOCATION 's3://<bucket, string, no quotes>/<prefix, string, no quotes>/';
```

- Syntax is `USING ICEBERG` — NOT `STORED AS ICEBERG`, NOT `TABLE_FORMAT=ICEBERG`.
- Iceberg tables must be registered with the AWS Glue Data Catalog — reference them
  through an external schema (as above) or, for auto-mounted catalogs, three-part
  notation (`"catalog".database.table`).
- String columns use `VARCHAR` with no length — Iceberg maps them to `string`.
- `LOCATION` is required for external-schema and `awsdatacatalog` tables — the S3 path
  for Iceberg data and metadata. It cannot be specified for S3 table buckets
  (`s3tablescatalog`), where the catalog determines the location.
