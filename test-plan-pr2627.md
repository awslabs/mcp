# Test Plan: Neptune Analytics endpoint_url support (PR #2627)

## Unit Tests (automated, 71 passing)

### Endpoint URI Parsing (test_neptune.py)
| Test | URI | Expected graphId | Expected endpoint_url |
|------|-----|-----------------|----------------------|
| test_init_neptune_analytics | `neptune-graph://g-1234567890` | `g-1234567890` | `None` |
| test_init_neptune_analytics_with_full_endpoint | `neptune-graph://g-1234567890.us-east-1.neptune-graph.amazonaws.com` | `g-1234567890` | `https://us-east-1.neptune-graph.amazonaws.com` |
| test_init_neptune_analytics_local_container | `neptune-graph://localhost:9100/g-1234567890` | `g-1234567890` | `http://localhost:9100` |

### Existing Tests (unchanged, all passing)
- Neptune Database initialization, status, schema, query (openCypher + Gremlin)
- Server tools: get_status, get_schema, run_opencypher_query, run_gremlin_query
- Graph initialization: missing endpoint, HTTPS config
- Analytics: schema refresh, query execution, error handling
- Database: connection, schema, query execution

## Manual Integration Tests

### Test 1: Managed Neptune Analytics (default endpoint)
```bash
export NEPTUNE_ENDPOINT="neptune-graph://g-1234567890"
# Start MCP server, verify connection to managed NA instance
# Run: RETURN 1 query via MCP tool
# Expected: successful query execution
```

### Test 2: Local Neptune Analytics Container
```bash
# Start local NA container
docker run -p 9100:9100 neptune-analytics-standalone

export NEPTUNE_ENDPOINT="neptune-graph://localhost:9100/local"
# Start MCP server, verify connection to local container
# Run: RETURN 1 query via MCP tool
# Expected: successful query execution without SigV4 errors
# Verify: boto3 does NOT prepend graph ID to hostname
```

### Test 3: Full Endpoint URI (VPC/custom)
```bash
export NEPTUNE_ENDPOINT="neptune-graph://g-1234567890.us-east-1.neptune-graph.amazonaws.com"
# Start MCP server
# Verify: graphId extracted as g-1234567890
# Verify: endpoint_url set to https://us-east-1.neptune-graph.amazonaws.com
```

### Test 4: Backward Compatibility
```bash
export NEPTUNE_ENDPOINT="neptune-graph://g-1234567890"
# No endpoint_url, no env var — should work exactly as before
# Verify: NeptuneAnalytics called with endpoint_url=None
```

### Test 5: Neptune Database (no regression)
```bash
export NEPTUNE_ENDPOINT="neptune-db://my-cluster.us-east-1.neptune.amazonaws.com"
# Verify: NeptuneDatabase path unchanged
# Verify: no endpoint_url parameter passed
```

## Verification Checklist
- [ ] All 71 unit tests pass
- [ ] Local NA container connects successfully with `neptune-graph://localhost:9100/graphId`
- [ ] Managed NA connects with `neptune-graph://g-xxxxxxxxxx`
- [ ] Full endpoint URI parses correctly
- [ ] No regression for Neptune Database endpoints
- [ ] `inject_host_prefix` disabled for custom endpoints (boto3 doesn't prepend graphId)
- [ ] NEPTUNE_ANALYTICS_ENDPOINT_URL env var removed (no longer needed)
