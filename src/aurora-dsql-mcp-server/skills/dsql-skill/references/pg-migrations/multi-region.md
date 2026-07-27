# Multi-Region DSQL Design

Aurora DSQL supports active-active multi-region with strong consistency.

Sources:

- [What is Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)
- [Multi-Region Clusters](https://awslabs.github.io/aurora-dsql-starter-kit/multi-region-clusters.html)
- [Multi-Region Endpoint Routing](https://aws.amazon.com/blogs/database/implement-multi-region-endpoint-routing-for-amazon-aurora-dsql/)

---

## Overview

| Configuration | Availability | Regions                                                                                         |
| ------------- | ------------ | ----------------------------------------------------------------------------------------------- |
| Single-Region | 99.99%       | 1                                                                                               |
| Multi-Region  | 99.999%      | Two peered clusters in two Regions plus one shared witness Region (the witness has no endpoint) |

**Key properties:**

- Active-active: both regions handle reads AND writes
- Strongly consistent: all reads/writes to any endpoint are consistent
- Synchronous replication (not eventual)
- Same schema automatically in both regions — deploy DDL once
- Zero data loss failover

---

## Schema Deployment

Schema DDL MUST be executed against only ONE region — it propagates automatically:

```sql
-- Connect to Region 1 endpoint
CREATE TABLE orders (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), ...);
-- Table is immediately available in Region 2
```

---

## Application Design

### Geographic Partitioning (Minimize Cross-Region Conflicts)

```sql
CREATE TABLE user_sessions (
  region varchar(20),
  session_id uuid DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  PRIMARY KEY (region, session_id)
);
-- Region 1 writes with region='us-east-1'
-- Region 2 writes with region='us-east-2'
```

### Connection Routing

- **Latency-based (Route 53):** Route to nearest region
- **Failover:** Primary/secondary with health checks
- **Application-level:** Connection string per region

### OCC in Multi-Region

Cross-region write conflicts use the same SQLSTATE 40001 mechanism. Design for low
contention across regions — partition data by geography where possible.

---

## Quotas

| Quota                             | Value                                                                                     |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| Multi-region clusters per account | 5 (increasable)                                                                           |
| Cluster topology                  | Two peered clusters in two endpoint Regions, plus one shared witness Region (no endpoint) |
| Storage per cluster               | 10 TiB (up to 256 TiB)                                                                    |
