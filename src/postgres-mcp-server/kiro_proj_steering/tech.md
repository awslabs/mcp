# Technology Stack

## AWS Services

### Aurora PostgreSQL

**Cluster Creation:**
- Region: `us-east-2`
- DB cluster can take several minutes to create (5 to 7 minutes). Use get_job_status every  minute, instead of every few seconds.

**Database Connection:**
- **PREFERRED**: Use RDS Data API (no network connectivity required, works through AWS API)
- **ALTERNATIVE**: Use IAM authentication with `pgwire` connection method (requires network access to cluster)

**RDS Data API Connection (Recommended):**
- Use `@aws-sdk/client-rds-data` for database operations
- Use `@aws-sdk/credential-providers` with `fromNodeProviderChain()` for credentials
- **CRITICAL**: `fromNodeProviderChain()` requires AWS credentials as environment variables
- **Preferred**: Use `.env` file with `dotenv` package for credentials: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
- Add `dotenv` to dependencies and load at top of server: `import 'dotenv/config';`
- Create `.env.example` template for users to copy
- Store cluster ARN and secret ARN in `.env` file

**Environment Variables for RDS Data API:**
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token
CLUSTER_ARN=arn:aws:rds:us-east-2:account-id:cluster:cluster-name
SECRET_ARN=arn:aws:secretsmanager:us-east-2:account-id:secret:secret-name
DATABASE=postgres
AWS_REGION=us-east-2
```

**Node.js RDS Data API Pattern:**
```javascript
import 'dotenv/config';
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data';
import { fromNodeProviderChain } from '@aws-sdk/credential-providers';

const rdsClient = new RDSDataClient({
  region: process.env.AWS_REGION,
  credentials: fromNodeProviderChain()
});

const dbConfig = {
  resourceArn: process.env.CLUSTER_ARN,
  secretArn: process.env.SECRET_ARN,
  database: process.env.DATABASE
};

async function executeQuery(sql, parameters = []) {
  const command = new ExecuteStatementCommand({
    ...dbConfig,
    sql,
    parameters,
    includeResultMetadata: true  // CRITICAL: Required to get column names
  });
  return await rdsClient.send(command);
}

function formatRecords(records, columnMetadata) {
  if (!records || !records.length || !columnMetadata) return [];
  return records.map(record => {
    const row = {};
    record.forEach((field, index) => {
      if (!columnMetadata[index]) return;
      const columnName = columnMetadata[index].name;
      if (field.stringValue !== undefined) row[columnName] = field.stringValue;
      else if (field.longValue !== undefined) row[columnName] = field.longValue;
      else if (field.doubleValue !== undefined) row[columnName] = field.doubleValue;
      else if (field.booleanValue !== undefined) row[columnName] = field.booleanValue;
      else if (field.isNull) row[columnName] = null;
      else row[columnName] = null;
    });
    return row;
  });
}

// Example query
const result = await executeQuery('SELECT * FROM meals');
const rows = formatRecords(result.records, result.columnMetadata);
```

**RDS Data API Important Notes:**
- Always set `includeResultMetadata: true` to get column names
- Parameters use named placeholders: `:param_name`
- Parameter format: `{ name: 'param_name', value: { stringValue: 'value' } }`
- Value types: `stringValue`, `longValue`, `doubleValue`, `booleanValue`
- Date columns need explicit casting: `CAST(:date_param AS DATE)`
- JSON aggregations return as strings - parse with `JSON.parse()`
- No connection pooling needed - serverless API

**Error Handling:**
- Always wrap queries in try-catch
- Add console.error logging to all API endpoints for debugging
- Handle empty result sets gracefully

**Required Dependencies:**
- `@aws-sdk/client-rds-data`, `@aws-sdk/credential-providers`
- `express`, `cors`, `dotenv` for backend

**Alternative: pgwire Connection (if network access available):**
- Use `@aws-sdk/rds-signer` to generate IAM auth tokens
- Use `pg` package for PostgreSQL client
- Requires network connectivity to cluster endpoint
- See previous pattern for implementation details

## Frontend Stack

### React + Vite

**Project Creation:**
- Non-interactive: `echo "n" | npm create vite@latest client -- --template react`
- Answer "No" to rolldown-vite prompt

**Configuration:**
- Configure proxy in `vite.config.js`:
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true
      }
    }
  }
})
```

**Error Handling:**
- Always wrap fetch calls in try-catch
- Ensure state arrays default to empty arrays: `setMeals(Array.isArray(data) ? data : [])`
- Prevents "undefined.map is not a function" errors

**Dependencies:**
- `react`, `react-dom`, `vite`, `@vitejs/plugin-react`

## Full Stack App Pattern

1. **Assume `.env` file already exists** with AWS credentials (ACCESS_KEY, SECRET_KEY, SESSION_TOKEN, AWS_REGION)
2. Create Aurora cluster with MCP tools
3. Wait for cluster creation to complete (check with `get_job_status` every minute)
4. **Get Secret ARN automatically** using AWS CLI:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier CLUSTER_NAME --region us-east-2 --query 'DBClusters[0].MasterUserSecret.SecretArn' --output text
   ```
5. **Construct Cluster ARN** from cluster identifier and account ID:
   - Format: `arn:aws:rds:us-east-2:ACCOUNT_ID:cluster:CLUSTER_NAME`
   - Extract account ID from Secret ARN returned in step 4
6. **Update `.env` file** by appending:
   - `CLUSTER_ARN=arn:aws:rds:us-east-2:ACCOUNT_ID:cluster:CLUSTER_NAME`
   - `SECRET_ARN=<value from step 4>`
   - `DATABASE=postgres`
7. Create database schema using RDS Data API (one table at a time to avoid injection warnings)
8. Create Express backend with RDS Data API connection
9. Create React frontend with Vite
10. Add sample data to database using RDS Data API
11. Install dependencies: `npm install` in root and `npm install` in client
12. Start backend with `controlBashProcess`: `npm run server`
13. Start frontend with `controlBashProcess` in client directory: `npm run dev`

**Key Points:**
- User already has `.env` with AWS credentials - don't ask for them
- Secret ARN is automatically retrieved from `describe-db-clusters` API call
- The `MasterUserSecret.SecretArn` field contains the Secrets Manager ARN for database credentials
