# Troubleshooting

Common, cross-cutting issues when working with Amazon Timestream for InfluxDB. For
version- or topic-specific problems, use the cross-references below rather than
duplicating them here. Use the directory matching the user's engine — `influxdb3/`
or `influxdb2/`.

## Where to look for specific issues

| Symptom / area | See |
|---|---|
| Errors specific to InfluxDB 3 (clusters, SQL, processing engine) | [`influxdb3/troubleshooting.md`](./influxdb3/troubleshooting.md), [`influxdb3/gotchas.md`](./influxdb3/gotchas.md) |
| Errors specific to InfluxDB 2 (instances, Flux, read replicas) | [`influxdb2/troubleshooting.md`](./influxdb2/troubleshooting.md), [`influxdb2/gotchas.md`](./influxdb2/gotchas.md) |
| Query fails, returns no data, or is slow | [`influxdb3/query-guide.md`](./influxdb3/query-guide.md), [`influxdb2/query-guide.md`](./influxdb2/query-guide.md) (v2 has a **Query Performance** section) |
| Writes/ingest rejected, dropped points, type conflicts, replica lag | [`influxdb3/ingestion.md`](./influxdb3/ingestion.md), [`influxdb2/ingestion.md`](./influxdb2/ingestion.md) — see **Write Error Handling** (HTTP status codes) and **Batching** |
| Schema / cardinality problems (high memory, slow compaction, 10K-table limit) | [`influxdb3/schema-design.md`](./influxdb3/schema-design.md), [`influxdb2/schema-design.md`](./influxdb2/schema-design.md), plus the relevant `gotchas.md` |
| Parameter changes not taking effect, or tuning (V3) | [`influxdb3/parameters.md`](./influxdb3/parameters.md), plus `gotchas.md` |
| Token retrieval / which token to use | [influxdb-2-vs-3.md](./influxdb-2-vs-3.md) ("Retrieving tokens"), plus the relevant `onboarding.md` |
| Which version am I on / version-specific behavior | [influxdb-2-vs-3.md](./influxdb-2-vs-3.md) |
| Line protocol formatting errors | [line-protocol.md](./line-protocol.md) |

## Bad connection / authorization

The most common first-contact failures. Check, in order:

1. **Wrong port.** By default, V2 listens on **8086**, V3 on **8181**. Hitting the wrong port looks
   like a connection timeout or refused connection, not an auth error.
2. **Wrong, expired, or wrong-type token.** Retrieve or create the correct token — V2 via
   the influx CLI (`influx auth create --operator`); V3 from the cluster's Secrets
   Manager secret (`READONLY-InfluxDB-auth-parameters-<cluster ID>`). Full steps:
   [influxdb-2-vs-3.md](./influxdb-2-vs-3.md) → "Retrieving tokens".
3. **IAM does not gate the data plane.** The control plane uses SigV4/IAM, but
   data-plane reads/writes are authorized only by the engine token — an IAM ReadOnly
   policy will **not** block data-plane access (see the relevant `gotchas.md`).
4. **Network reachability.** Private instances/clusters require in-VPC access (or a
   bastion/port-forward), and the security group must allow inbound on the configured
   port.
5. **Namespace mismatch.** V2 requires the correct `org` + `bucket`; V3 requires the
   correct `db`. A missing or incorrect namespace often surfaces as `404`/empty results
   rather than an auth error.

### Quick isolation: health check

Both engines expose a `GET /health`. Use it to separate
"endpoint/network is down" from "auth, namespace, or payload is wrong":

```shell
curl https://<endpoint>:<port>/health
```

A healthy response (`OK`) means the engine is reachable, so the problem is most likely
auth (steps 2–3), networking to a private resource (step 5), or the namespace/payload —
not the endpoint itself.
