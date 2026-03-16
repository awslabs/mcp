---
name: agentcore-investigation
description: Investigate Bedrock AgentCore runtime sessions via CloudWatch Logs Insights — resolve session/trace IDs, query OTEL spans, filter noise, build timelines. Use when debugging AgentCore agent sessions, tracing tool calls, or analyzing latency.
---

# AgentCore Runtime Session Investigation

Investigate AgentCore runtime sessions by querying CloudWatch Logs Insights, filtering OpenTelemetry noise, and producing structured investigation output.

**Key capabilities:**
- Session-to-trace resolution via OTEL span correlation
- Structured and glob-style parse queries for both dedicated and combined log groups
- OpenTelemetry noise filtering with AgentCore-specific heuristics
- Timeline construction with T+offset format
- Error, tool invocation, token usage, and latency analysis

---

## Reference Files

Load these files as needed for detailed guidance:

### MCP:
#### [mcp-setup.md](mcp/mcp-setup.md)
**When:** ALWAYS load before starting an investigation — ensures CloudWatch and Application Signals MCP servers are configured
**Contains:** MCP server configuration for CloudWatch Logs and Application Signals, with setup instructions for Claude Code, Gemini, Codex, and Kiro CLI

#### [.mcp.json](mcp/.mcp.json)
**When:** Load when setting up MCP servers for the first time
**Contains:** Sample MCP configuration with both CloudWatch and Application Signals servers

### [otel-span-schema.md](references/otel-span-schema.md)
**When:** ALWAYS load before querying or filtering OTEL spans
**Contains:** Field extraction priorities, known instrumentation scopes, noise filtering heuristics (DROP/KEEP patterns)

---

## Phase 0: SessionId-to-TraceId Resolution

When the user provides a sessionId, resolve it to traceId(s) first. If user provides traceId directly, skip this phase.

### Discovery Query (structured fields)

```
fields traceId, @timestamp
| filter attributes.session.id = "SESSION_ID"
| stats count(*) as spanCount, min(@timestamp) as firstSeen, max(@timestamp) as lastSeen by traceId
| sort firstSeen asc
```

### Discovery Query (combined log group — glob-style parse)

```
fields @timestamp, @message
| parse @message '"traceId":"*"' as traceId
| parse @message '"session.id":"*"' as sessionId
| filter sessionId = "SESSION_ID" or @message like "SESSION_ID"
| stats earliest(@timestamp) as firstSeen, latest(@timestamp) as lastSeen, count(*) as spanCount by traceId
| sort firstSeen asc
| limit 50
```

### Latest Interaction Only

```
fields traceId
| filter attributes.session.id = "SESSION_ID"
| sort @timestamp desc
| limit 1
```

Store discovered traceId(s) and use them in ALL subsequent queries.

## Phase 1: Discover Log Groups

Use `describe_log_groups` with logGroupNamePrefix `/aws/bedrock-agentcore/runtimes` to find all runtime log groups.

```
Log group naming patterns (in priority order):
- /aws/bedrock-agentcore/runtimes/<agent_id>-<endpoint_name>/otel-rt-logs (structured OTEL spans)
- /aws/bedrock-agentcore/runtimes/<agent_id>-<endpoint_name>/[runtime-logs] (stdout/stderr)
- /aws/bedrock-agentcore/runtimes/<agent_id>-<endpoint_name>-DEFAULT (single combined group)
```

### Log Group Layouts

AgentCore runtimes always emit OTEL spans. Some deployments split logs into a dedicated `otel-rt-logs` sub-group; others write everything into a single combined log group. Both are normal.

| Log Group Layout | Query Strategy |
|-----------------|----------------|
| Dedicated `otel-rt-logs` exists | Use structured field queries (`traceId`, `attributes.session.id`, etc.) |
| Single combined log group | Try structured fields first — if they return 0 results, use glob-style `parse @message` |

If a dedicated `otel-rt-logs` group exists, prefer it for structured queries.

### Parse Syntax Guidance

When using `parse @message` on combined log groups, prefer glob-style parse — it is simpler and avoids escaping issues:

```
| parse @message '"name":"*"' as spanName
| parse @message '"traceId":"*"' as traceId
| parse @message '"startTimeUnixNano":"*"' as startNano
```

Regex parse (`/pattern/`) is valid CloudWatch Logs Insights syntax but requires careful escaping of quotes and special characters inside JSON. If glob-style parse extracts the field you need, use it.

## Phase 2: Query CloudWatch Logs Insights

Run all 6 query types for a complete investigation. Each query has a structured version (for dedicated `otel-rt-logs`) and a glob-style parse version (for combined log groups).

### Query Size Limits

Every query MUST include `| limit` to prevent context window overflow:
- Session overview: `| limit 50`
- Span details: `| limit 100`
- Errors: `| limit 50`
- Tool invocations: `| limit 100`
- Token usage: `| limit 50`
- Latency outliers: `| limit 20`

### Query 1: Session Overview

**Structured:**
```
fields @timestamp, traceId, spanId, parentSpanId, name, scope.name,
       attributes.session.id, attributes.gen_ai.operation.name, attributes.gen_ai.agent.name,
       startTimeUnixNano, endTimeUnixNano
| filter traceId = "TRACE_ID"
| sort startTimeUnixNano asc
| limit 50
```

**Combined log group:**
```
fields @timestamp, @message
| filter @message like "TRACE_ID"
| parse @message '"name":"*"' as spanName
| parse @message '"traceId":"*"' as traceId
| parse @message '"spanId":"*"' as spanId
| parse @message '"startTimeUnixNano":"*"' as startNano
| parse @message '"endTimeUnixNano":"*"' as endNano
| sort @timestamp asc
| limit 50
```

### Query 2: Span Details with Duration

**Structured:**
```
fields @timestamp, traceId, spanId, parentSpanId, name, scope.name,
       startTimeUnixNano, endTimeUnixNano,
       (endTimeUnixNano - startTimeUnixNano) / 1000000 as durationMs,
       status.code, attributes.gen_ai.operation.name
| filter traceId = "TRACE_ID"
| filter ispresent(startTimeUnixNano)
| sort startTimeUnixNano asc
| limit 100
```

**Combined log group:**
```
fields @timestamp, @message
| filter @message like "TRACE_ID"
| parse @message '"name":"*"' as spanName
| parse @message '"spanId":"*"' as spanId
| parse @message '"parentSpanId":"*"' as parentSpanId
| parse @message '"startTimeUnixNano":"*"' as startNano
| parse @message '"endTimeUnixNano":"*"' as endNano
| parse @message '"statusCode":"*"' as statusCode
| sort @timestamp asc
| limit 100
```

### Query 3: Errors

**Structured:**
```
fields @timestamp, traceId, spanId, name, status.code, status.message,
       attributes.error.message, attributes.exception.message, attributes.exception.type
| filter traceId = "TRACE_ID"
| filter status.code = 2 OR ispresent(attributes.error.message) OR ispresent(attributes.exception.message)
| sort @timestamp asc
| limit 50
```

**Combined log group:**
```
fields @timestamp, @message
| filter @message like "TRACE_ID"
| filter @message like /ERROR|exception|Exception|fault|STATUS_CODE_ERROR/
| parse @message '"name":"*"' as spanName
| parse @message '"statusCode":"*"' as statusCode
| parse @message '"startTimeUnixNano":"*"' as startNano
| sort @timestamp asc
| limit 50
```

### Query 4: Tool Invocations

**Structured:**
```
fields @timestamp, traceId, spanId, name, scope.name,
       attributes.gen_ai.operation.name, attributes.tool.name,
       startTimeUnixNano, endTimeUnixNano,
       (endTimeUnixNano - startTimeUnixNano) / 1000000 as durationMs
| filter traceId = "TRACE_ID"
| filter attributes.gen_ai.operation.name = "execute_tool" OR ispresent(attributes.tool.name) OR name like /tool/
| sort startTimeUnixNano asc
| limit 100
```

**Combined log group:**
```
fields @timestamp, @message
| filter @message like "TRACE_ID"
| filter @message like /tool|execute_tool|function_call/
| parse @message '"name":"*"' as spanName
| parse @message '"startTimeUnixNano":"*"' as startNano
| parse @message '"endTimeUnixNano":"*"' as endNano
| parse @message '"statusCode":"*"' as statusCode
| sort @timestamp asc
| limit 100
```

### Query 5: Token Usage

**Structured:**
```
fields @timestamp, traceId, spanId, name,
       attributes.gen_ai.usage.input_tokens, attributes.gen_ai.usage.output_tokens,
       attributes.gen_ai.usage.total_tokens, attributes.gen_ai.agent.name
| filter traceId = "TRACE_ID"
| filter ispresent(attributes.gen_ai.usage.total_tokens)
| sort @timestamp asc
| limit 50
```

**Combined log group:**
```
fields @timestamp, @message
| filter @message like "TRACE_ID"
| filter @message like /input_tokens|output_tokens|usage/
| parse @message '"name":"*"' as spanName
| parse @message '"gen_ai.usage.input_tokens"' as hasTokens
| sort @timestamp asc
| limit 50
```

### Query 6: Latency Outliers

**Structured:**
```
fields @timestamp, traceId, spanId, name,
       (endTimeUnixNano - startTimeUnixNano) / 1000000 as durationMs
| filter traceId = "TRACE_ID"
| filter ispresent(endTimeUnixNano)
| sort durationMs desc
| limit 20
```

**Combined log group:**
```
fields @timestamp, @message
| filter @message like "TRACE_ID"
| parse @message '"name":"*"' as spanName
| parse @message '"startTimeUnixNano":"*"' as startNano
| parse @message '"endTimeUnixNano":"*"' as endNano
| sort @timestamp asc
| limit 50
```

Queries are async — use `get_logs_insight_query_results` to poll until status is `Complete`.

## Phase 3: Filter OTEL Noise

See [otel-span-schema.md](references/otel-span-schema.md) for extraction rules, known scopes, and DROP/KEEP heuristics.

After retrieving query results:
1. Count total results received
2. Remove entries matching DROP patterns (count removed)
3. Keep entries matching KEEP patterns
4. Log: "Filtered: {total} → {kept} spans ({removed} noise entries dropped)"

## Phase 4: Build Timeline

Compute relative offsets from the earliest span's `startTimeUnixNano`:

```
[T+0ms]     Session started — traceId: abc123
[T+45ms]    LLM inference — model: anthropic.claude-v3 — 1,200ms
[T+1,250ms] Tool call: search_documents — 340ms
[T+1,600ms] Tool result: 3 documents found
[T+1,650ms] LLM inference — model: anthropic.claude-v3 — 890ms
[T+2,550ms] Response generated — 200 OK
[T+2,600ms] Session ended — total: 2,600ms
```

## Error Handling

| Situation | Action |
|-----------|--------|
| No log groups found | Ask user for log group name or AWS region |
| Query returns 0 results | Widen time range to ±24h, retry. If still empty, try alternate ID fields |
| Session ID not found | Try filtering by requestId, invocationId, traceId variants |
| Query timeout | Use `cancel_logs_insight_query`, reduce time range, retry |
| Partial results | Note in output, suggest narrower time window |
| Structured field queries return 0 results | Switch to glob-style `parse @message` queries (see Parse Syntax Guidance) |
