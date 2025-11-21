# Aurora DSQL MCP Server - Tool Testing Guide

## Documentation Tools (No Database Required)

### 1. dsql_search_documentation
**Purpose:** Search Aurora DSQL documentation

**Test Command:**
```
Search for "getting started with Aurora DSQL"
```

**Expected Result:** Should return relevant documentation links about getting started

---

### 2. dsql_read_documentation
**Purpose:** Read specific DSQL documentation pages

**Test Command:**
```
Read the documentation at https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html
```

**Expected Result:** Should return the content of the getting started page

---

### 3. dsql_recommend
**Purpose:** Get recommendations for DSQL best practices

**Test Command:**
```
Get recommendations for https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html
```

**Expected Result:** Should return related documentation recommendations

---

## Database Tools (Requires DSQL Cluster)

### 4. get_schema
**Purpose:** Retrieve table schema information

**Prerequisites:**
- DSQL cluster endpoint configured
- AWS credentials with access
- Database user configured

**Test Command:**
```
Get the schema for all tables in my database
```

**Expected Result:** Should return table names and their schemas

---

### 5. readonly_query
**Purpose:** Execute read-only SQL queries

**Prerequisites:**
- DSQL cluster endpoint configured
- AWS credentials with access
- Database user configured
- At least one table exists

**Test Command:**
```
Execute this query: SELECT version();
```

**Expected Result:** Should return the PostgreSQL version

---

### 6. transact
**Purpose:** Execute write operations in a transaction

**Prerequisites:**
- DSQL cluster endpoint configured
- AWS credentials with access
- Database user configured
- `--allow-writes` flag enabled in MCP configuration

**Test Command:**
```
Create a test table: CREATE TABLE test_table (id SERIAL PRIMARY KEY, name TEXT);
```

**Expected Result:** Should create the table (or fail if --allow-writes not enabled)

---

## Quick Test Prompts

Copy and paste these into the chat to test each tool:

1. **Documentation Search:**
   ```
   Search Aurora DSQL documentation for "connection pooling"
   ```

2. **Read Documentation:**
   ```
   Read the Aurora DSQL documentation page about IAM authentication
   ```

3. **Get Recommendations:**
   ```
   Get Aurora DSQL best practice recommendations
   ```

4. **Get Schema:**
   ```
   Show me the schema of all tables in my DSQL database
   ```

5. **Read-only Query:**
   ```
   Run this query on my DSQL database: SELECT current_database(), current_user;
   ```

6. **Write Transaction (if enabled):**
   ```
   Create a simple test table in my DSQL database
   ```

---

## Troubleshooting

### Tools show "not trusted"
- This is normal - you'll be prompted to approve each tool on first use
- You can add tools to `autoApprove` in your MCP configuration to skip prompts

### Database tools fail
- Check your MCP configuration has correct:
  - `--cluster_endpoint`
  - `--region`
  - `--database_user`
  - `--profile` (or AWS credentials)

### Transact tool blocked
- Verify `--allow-writes` is in your MCP configuration args
- By default, the server is read-only for safety
