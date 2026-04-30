# DSQL Examples: Connection & Ad-Hoc Queries

Part of [Aurora DSQL Implementation Examples](../dsql-examples.md).

---

## Ad-Hoc Queries with psql

PREFER connecting with a scoped database role using `generate-db-connect-auth-token`.
Reserve `admin` for role and schema setup only. See [access-control.md](../access-control.md).

```bash
# PREFERRED: Execute queries with a scoped role
PGPASSWORD="$(aws dsql generate-db-connect-auth-token \
  --hostname ${CLUSTER}.dsql.${REGION}.on.aws \
  --region ${REGION})" \
psql -h ${CLUSTER}.dsql.${REGION}.on.aws -U app_readwrite -d postgres \
  -c "SELECT COUNT(*) FROM objectives WHERE tenant_id = 'tenant-123';"

# Admin only — for role/schema setup
PGPASSWORD="$(aws dsql generate-db-connect-admin-auth-token \
  --hostname ${CLUSTER}.dsql.${REGION}.on.aws \
  --region ${REGION})" \
PGAPPNAME="<app-name>/<model-id>" \
psql -h ${CLUSTER}.dsql.${REGION}.on.aws -U admin -d postgres
```

---

## Connection Management

### RECOMMENDED: DSQL Connector

Source: [aurora-dsql-samples/javascript](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript)

```javascript
import { AuroraDSQLPool } from "@aws/aurora-dsql-node-postgres-connector";

function createPool(clusterEndpoint, user) {
  return new AuroraDSQLPool({
    host: clusterEndpoint,
    user: user,
    application_name: "<app-name>/<model-id>",
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 10000,
  });
}

async function example() {
  const pool = createPool(process.env.CLUSTER_ENDPOINT, process.env.CLUSTER_USER);

  try {
    const result = await pool.query("SELECT $1::int as value", [42]);
    console.log(`Result: ${result.rows[0].value}`);
  } finally {
    await pool.end();
  }
}
```

### Token Generation for Custom Implementations

For custom drivers or languages without DSQL Connector. Source: [aurora-dsql-samples/javascript/authentication](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/authentication)

```javascript
import { DsqlSigner } from "@aws-sdk/dsql-signer";

// PREFERRED: Generate token for scoped role (uses dsql:DbConnect)
async function generateToken(clusterEndpoint, region) {
  const signer = new DsqlSigner({ hostname: clusterEndpoint, region });
  return await signer.getDbConnectAuthToken();
}

// Admin only — for role/schema setup (uses dsql:DbConnectAdmin)
async function generateAdminToken(clusterEndpoint, region) {
  const signer = new DsqlSigner({ hostname: clusterEndpoint, region });
  return await signer.getDbConnectAdminAuthToken();
}
```
