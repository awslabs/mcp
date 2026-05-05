# AgentCore Investigation — OTEL Span Schema

## Field Extraction Priority

Extract these fields from AgentCore OTEL spans in priority order:

| Priority | Field Path | What It Contains |
|----------|-----------|------------------|
| 1 | `name` | Span/operation name |
| 2 | `attributes.gen_ai.operation.name` | GenAI operation type |
| 3 | `attributes.session.id` | Session identifier |
| 4 | `traceId` / `spanId` / `parentSpanId` | Trace correlation |
| 5 | `startTimeUnixNano` / `endTimeUnixNano` | Timing (compute durationMs) |
| 6 | `status.code` | OTel status (0=UNSET, 1=OK, 2=ERROR) |
| 7 | `attributes.gen_ai.usage.*` | Token counts (input_tokens, output_tokens, total_tokens) |
| 8 | `attributes.tool.name` | Tool name |
| 9 | `attributes.gen_ai.agent.name` | Agent name |
| 10 | `scope.name` | Instrumentation scope |
| 11 | `body` | Event body (for log events) |

## Known Instrumentation Scopes

| Scope | Framework |
|-------|-----------|
| `strands.telemetry.tracer` | Strands Agents SDK |
| `opentelemetry.instrumentation.langchain` | LangChain |
| `openinference.instrumentation.langchain` | LangChain (alternative) |

## Noise Filtering — DROP These Patterns

| Pattern | Why |
|---------|-----|
| `resourceSpans` wrapper with only metadata | OTel envelope, no signal |
| `scopeSpans` with empty `spans[]` | Empty instrumentation scope |
| `InstrumentationScope` lines with only library name/version | SDK metadata |
| Repeated `schemaUrl` entries | Schema boilerplate |
| `resource.attributes` containing only `service.name`, `telemetry.sdk.*` | Resource metadata, not signal |
| Heartbeat/keepalive messages | Infrastructure noise |
| `@ptr` fields from CW Insights | Internal CW pointers |

## Noise Filtering — KEEP These Patterns

| Pattern | Why |
|---------|-----|
| Any message with `error`, `exception`, `fault` | Errors always matter |
| Messages with `duration` > 0 | Actual span completions |
| Messages with `tool_use`, `toolUse`, `function_call` | Tool invocations |
| Messages with `statusCode` != 0 | Non-OK spans |
| Messages with `model_id` or `modelId` | Model inference calls |
| First and last message per `traceId` | Session boundaries |
