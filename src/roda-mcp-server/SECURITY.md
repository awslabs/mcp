# Security

This document covers security considerations for the design of this MCP server and for users consuming it.

## Encryption in Transit

All S3 operations use HTTPS/TLS 1.2+ for encryption in transit, enforced at the boto3 client level:

- `use_ssl=True` — HTTPS is required for every S3 API call; plain HTTP is never used.
- `verify=True` — TLS certificate validation is enabled on every connection, preventing man-in-the-middle attacks.
- `signature_version='s3v4'` — AWS Signature Version 4 is used for authenticated requests.

Similarly, all external API calls (such as downloading ndjson file from Github) require TLS 1.2 or higher with certificate validation enabled.

## Data Integrity

The server fetches registry metadata over HTTPS from `registry.opendata.aws`. A checksum validation mechanism is in place that activates if the registry publishes a SHA-256 sidecar file. This provides detection of corrupted or tampered downloads.

## Access Control

- **No credentials stored** — the server does not store, cache, or log AWS credentials.
- **Anonymous access only** — preview and sample operations use unsigned requests. No AWS account is required or used.
- **Controlled-access datasets** — datasets with controlled access are excluded from preview and sample operations. The server surfaces the access request URL instead.

## Data Handling

- **No data persistence** — downloaded file samples are held in memory only for the duration of the request and are not written to disk.
- **Limited preview** - preview of S3 structure performs LIST operations to 10 objects maximum per request.
- **Byte-range cap** — file sampling is capped at 100KB per request.
- **Registry cache** — dataset metadata is cached in memory for 24 hours. No sensitive data is included in the cache (metadata only: names, descriptions, tags, ARNs).
- **Text truncation** — text output from sampled files is truncated to 2000 characters before being returned.

## Input Validation

- Bucket ARNs are verified against the dataset's known public resources before any S3 operation is attempted.
- Controlled-access and requester-pays resources are filtered out before preview or sample operations — the server will not attempt access on restricted buckets.
- JSON parsing errors during registry ingestion are caught per-line and skipped gracefully without exposing internal state.

## Considerations for Users

- **Review dataset licenses** — always review the license for a dataset before using its data. The server surfaces license information but does not interpret its terms.
- **Requester-pays buckets** — some datasets incur data transfer costs. The server will flag these and share instructions on how to access.
- **No authentication for public data** — preview and sample use anonymous S3 access. If you need to access controlled or private datasets, use the AWS CLI with your own credentials outside this server.
- **Network exposure** — the server makes outbound HTTPS requests to `registry.opendata.aws` and AWS S3 endpoints. Ensure your network policy allows this.
- **Using AWS services** - if you are using AWS services to process the datasets you have discovered, please be mindful of the [shared responsibility model of security](https://aws.amazon.com/compliance/shared-responsibility-model/).
