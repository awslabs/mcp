# AEA-355: Refactor Valkey MCP Server — V2 Tool Surface (17 Tools)

**Created:** 2026-04-17
**Updated:** 2026-04-20
**Status:** In Progress
**Assignee:** Jonathan Neufeld
**Priority:** Highest
**Sprint:** AEA Sprint 5

---

## V2 Tool Surface Overview

Every tool touches a live Valkey instance. No syntax-teaching wrappers — that's what skills are for. 3-tier safety model: read (always safe) → write (mutations) → admin (opt-in destructive). Observability tools inspired by Valkey Admin.

**17 tools across 3 phases:**

| # | Tool | Phase | What It Does |
|---|------|-------|-------------|
| 1 | `manage_index` | 1 | FT.CREATE / DROP / INFO / _LIST with structured input. Defaults COSINE + HNSW. |
| 2 | `add_documents` | 1 | Text → embed → binary pack → HSET. Auto-creates index if missing. |
| 3 | `search` | 1 | Unified semantic, text, hybrid, find-similar. Auto-detects mode. |
| 4 | `aggregate` | 1 | FT.AGGREGATE structured pipeline builder. |
| 5 | `json_get` | 1 | Typed JSON.GET with path. +14% vs CLI. |
| 6 | `json_set` | 1 | Typed JSON.SET with path + optional TTL. +17% vs CLI. |
| 7 | `json_arrappend` | 1 | Append to JSON array at path. +17% vs CLI. |
| 8 | `json_arrpop` | 1 | Pop from JSON array at path. +33% vs CLI. |
| 9 | `json_arrtrim` | 1 | Trim JSON array to range. +33% vs CLI. |
| 10 | `valkey_read` | 2 | Read-only commands: GET, HGETALL, LRANGE, SCAN, TTL, EXISTS, TYPE, INFO, etc. |
| 11 | `valkey_write` | 2 | Mutating commands: SET, HSET, DEL, LPUSH, SADD, ZADD, XADD, EXPIRE, etc. Destructive blocked. |
| 12 | `valkey_admin` | 2 | Opt-in destructive: FLUSHALL, FLUSHDB, CONFIG SET, CLUSTER RESET, SHUTDOWN, DEBUG, EVAL. |
| 13 | `cluster_health` | 3 | One-shot cluster health: topology, memory, replication lag, slot coverage, latency. |
| 14 | `slow_queries` | 3 | Top slow commands with P50/P99 latency, LATENCY DOCTOR, recommendations. |
| 15 | `keyspace_scan` | 3 | Key distribution by prefix, type breakdown, TTL profile, encoding analysis. |
| 16 | `hot_keys` | 3 | Top-K keys by LFU frequency, command stats, risk assessment. |
| 17 | `memory_analysis` | 3 | MEMORY DOCTOR, top-K by size, fragmentation, encoding optimization tips. |

**PR scope:** This PR delivers tools 1–9 (Phase 1). Phase 2 (Command Runner) and Phase 3 (Observability) are future PRs.

**3-tier safety:** `valkey_read` (always safe) → `valkey_write` (mutations, no destructive) → `valkey_admin` (opt-in only, disabled by default). An agent cannot accidentally FLUSHALL a staging cluster.

**Client library:** Valkey-GLIDE. This is a greenfield rewrite — all tools and the connection layer are built fresh on GLIDE. Existing `valkey-py` code is reference only; salvage patterns and logic where applicable but do not retain old code.

---

## Summary

Replace the current ~40+ generic data-type tools. Phase 1 delivers **9 tools**: 4 AI Search (new) + 5 JSON Intelligence (retained, benchmark-justified at 14–33% above CLI). Phase 2 collapses the remaining ~96 removed tools down to **3 Command Runner tools** with 3-tier safety, giving agents access to the full Valkey command set through safe/write/destructive tiers instead of per-command wrappers.

---

## Current State → Target State

### Remove (all existing tools)

All existing tools are being replaced. Nothing is retained as-is.

| Module | Tools | Reason |
|--------|-------|--------|
| `tools/json.py` | 17 tools | Reimplemented as JSON Intelligence tools (Phase 1) |
| `tools/string.py` | 8 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/list.py` | 12 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/set.py` | 5 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/sorted_set.py` | 8 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/hash.py` | 7 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/stream.py` | 6 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/bitmap.py` | 4 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/hyperloglog.py` | 3 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/misc.py` | 3 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/server_management.py` | 2 tools | Replaced by `valkey_read`/`valkey_write` (Phase 2) |
| `tools/semantic_search.py` | 7 tools | Replaced by AI Search tools (Phase 1) |
| `tools/vss.py` | 1 tool | Replaced by AI Search tools (Phase 1) |
| `tools/index.py` | 1 tool | Replaced by `manage_index` (Phase 1) |

### Build (new — 17 tools total)

| Tool | Phase | APIs | Notes |
|------|-------|------|-------|
| `manage_index` | 1 | FT.CREATE / DROP / INFO / _LIST | Structured JSON input, defaults COSINE + HNSW |
| `add_documents` | 1 | Embed → binary pack → HSET | Auto-creates index if missing |
| `search` | 1 | Unified semantic/text/hybrid/find-similar | Auto-detects mode from params |
| `aggregate` | 1 | FT.AGGREGATE pipeline builder | Structured JSON prevents DSL syntax errors |
| `json_get` | 1 | JSON.GET | Reimplemented fresh. +14% vs CLI. |
| `json_set` | 1 | JSON.SET | Reimplemented fresh. +17% vs CLI. |
| `json_arrappend` | 1 | JSON.ARRAPPEND | Reimplemented fresh. +17% vs CLI. |
| `json_arrpop` | 1 | JSON.ARRPOP | Reimplemented fresh. +33% vs CLI. |
| `json_arrtrim` | 1 | JSON.ARRTRIM | Reimplemented fresh. +33% vs CLI. |
| `valkey_read` | 2 | Read-only commands | Safe tier — always available |
| `valkey_write` | 2 | Mutating commands | Write tier — destructive blocked |
| `valkey_admin` | 2 | Destructive commands | Admin tier — opt-in, disabled by default |
| `cluster_health` | 3 | INFO, CLUSTER INFO/NODES, LATENCY | Future PR |
| `slow_queries` | 3 | SLOWLOG, LATENCY DOCTOR | Future PR |
| `keyspace_scan` | 3 | SCAN + TYPE/TTL/OBJECT ENCODING | Future PR |
| `hot_keys` | 3 | OBJECT FREQ, commandstats | Future PR |
| `memory_analysis` | 3 | MEMORY DOCTOR/USAGE, INFO memory | Future PR |

---

## Implementation Plan

### Phase 0: Rewrite connection layer for Valkey-GLIDE (2–3 hr)

**Files:** `common/connection.py`, `common/config.py`

Replace the `valkey-py` connection layer with Valkey-GLIDE. This is the foundation — all tools depend on it.

- Replace `ValkeyConnectionManager` with a GLIDE-based connection manager
- GLIDE client: `GlideClient` (standalone) or `GlideClusterClient` (cluster mode)
- Update config to support GLIDE connection options (host, port, TLS, credentials, cluster mode)
- GLIDE uses async natively — aligns well with the MCP async tool pattern
- For FT.* (search) and JSON.* commands not yet in GLIDE's typed API, use `custom_command()`
- Remove all `valkey-py` imports across the codebase

### Phase A: Build `manage_index` tool (2–3 hr)

**File:** `tools/search_manage_index.py`

Wraps FT.CREATE, FT.DROP, FT.INFO, FT._LIST behind structured JSON input.

```python
async def manage_index(
    action: str,                    # "create" | "drop" | "info" | "list"
    index_name: str = None,         # Required for create/drop/info
    schema: List[Dict] = None,      # Field definitions for create
    prefix: List[str] = None,       # Key prefix filter
    index_type: str = "HASH",       # HASH or JSON
    structure_type: str = "HNSW",   # HNSW or FLAT (vector fields)
    distance_metric: str = "COSINE" # COSINE, L2, or IP (vector fields)
) -> Dict[str, Any]
```

Schema field format:
```json
[
  {"name": "title", "type": "TEXT", "sortable": true},
  {"name": "embedding", "type": "VECTOR", "dimensions": 768},
  {"name": "year", "type": "NUMERIC"},
  {"name": "category", "type": "TAG"}
]
```

Refactors logic from existing `tools/index.py`, extending it to support TEXT, NUMERIC, TAG, GEO field types alongside VECTOR.

### Phase B: Build `add_documents` tool (2–3 hr)

**File:** `tools/search_add_documents.py`

Full embed → binary pack → HSET pipeline.

```python
async def add_documents(
    index_name: str,
    documents: List[Dict[str, Any]],
    id_field: str = "id",
    prefix: str = None,
    embedding_field: str = None,
    text_fields: List[str] = None,
    embedding_dimensions: int = None
) -> Dict[str, Any]
```

- If `embedding_field` + `text_fields` provided: generates embeddings, binary-packs, stores via HSET
- If no `embedding_field`: stores as plain hashes (text-only search)
- Auto-creates index if missing
- Falls back to Ollama `nomic-embed-text` when no provider configured

Carries forward embed pipeline from existing `semantic_search.py`.

### Phase C: Build `search` tool (3–4 hr)

**File:** `tools/search_query.py`

Unified search with mode auto-detection.

```python
async def search(
    index_name: str,
    query_text: str = None,
    document_id: str = None,
    vector_field: str = "embedding",
    filter_expression: str = None,
    return_fields: List[str] = None,
    offset: int = 0,
    limit: int = 10,
    hybrid_weight: float = 0.5
) -> Dict[str, Any]
```

| `query_text` | `document_id` | Embedding provider | Mode |
|:---:|:---:|:---:|:---|
| ✓ | ✗ | configured | Semantic |
| ✓ | ✗ | not configured | Text |
| ✗ | ✓ | — | Find-similar |
| ✓ | ✗ | configured + weight | Hybrid |

Refactors from `vss.py` and `semantic_search.py`.

### Phase D: Build `aggregate` tool (3–4 hr)

**File:** `tools/search_aggregate.py`

Structured pipeline builder for FT.AGGREGATE. Entirely new code.

```python
async def aggregate(
    index_name: str,
    query: str = "*",
    pipeline: List[Dict] = None
) -> Dict[str, Any]
```

Pipeline stage format:
```json
[
  {"type": "GROUPBY", "fields": ["@category"], "reducers": [
    {"function": "COUNT", "alias": "count"},
    {"function": "AVG", "field": "@price", "alias": "avg_price"}
  ]},
  {"type": "SORTBY", "fields": [{"field": "@count", "order": "DESC"}]},
  {"type": "APPLY", "expression": "@avg_price * 1.1", "alias": "adjusted_price"},
  {"type": "LIMIT", "offset": 0, "count": 10}
]
```

Supported stages: GROUPBY, SORTBY, APPLY, FILTER, LIMIT.
Supported REDUCE functions: COUNT, COUNT_DISTINCT, COUNT_DISTINCTISH, SUM, MIN, MAX, AVG, STDDEV, QUANTILE, TOLIST, FIRST_VALUE, RANDOM_SAMPLE.

### Phase E: Strip all existing tools (1–2 hr)

All existing MCP tools are being replaced — nothing is retained as-is.

1. **Delete `tools/json.py`** entirely — JSON Intelligence tools (5–9) will be reimplemented fresh
2. **Delete tool modules:** `string.py`, `list.py`, `set.py`, `sorted_set.py`, `hash.py`, `stream.py`, `bitmap.py`, `hyperloglog.py`, `misc.py`, `server_management.py`, `semantic_search.py`, `vss.py`
3. **Delete `tools/index.py`** — logic now lives in `manage_index`
4. **Update `tools/__init__.py`** — import only the 4 search modules (+ new modules as they're built)
5. **Update `main.py`** — import only new modules
6. **Delete all corresponding test files** for removed tools
7. **Delete old plan docs**

### Phase F: Dependency cleanup (1 hr)

1. Replace `valkey` (valkey-py) with `valkey-glide` in `pyproject.toml`
2. Remove all other unused dependencies
3. Regenerate `uv.lock`
4. Keep: `valkey-glide`, `boto3` (Bedrock embeddings), `openai` (OpenAI embeddings), `httpx` (Ollama), `numpy` (if used by embeddings)
5. Remove: `valkey` (valkey-py), any deps only used by deleted tool modules

### Phase G: Tests (3–4 hr)

| File | Covers |
|------|--------|
| `tests/test_search_manage_index.py` | JSON → FT.CREATE/DROP/INFO/_LIST, defaults, validation |
| `tests/test_search_add_documents.py` | Embed pipeline, auto-index, plain hash, readonly |
| `tests/test_search_query.py` | Mode auto-detection, all four search paths |
| `tests/test_search_aggregate.py` | Pipeline translation, REDUCE functions, errors |
| `tests/test_json.py` | Reimplemented JSON Intelligence tools (5 tools) |

### Phase H: Documentation (1–2 hr)

1. Update README.md — remove all generic data-type docs, add search tool docs
2. Document each tool's JSON schema with examples
3. Update MCP config examples
4. Update example queries section

### Phase I: Build `valkey_read` tool (3–4 hr)

**File:** `tools/valkey_read.py`

Read-only command runner. Safe tier — readonly by design, safe to point at any cluster.

```python
async def valkey_read(
    command: str,           # e.g., "GET", "HGETALL", "LRANGE"
    args: List[str] = None, # Command arguments
) -> Dict[str, Any]
```

- Allowlisted read-only commands: GET, MGET, HGET, HGETALL, HMGET, HKEYS, HVALS, HLEN, HEXISTS, LRANGE, LLEN, LINDEX, SMEMBERS, SCARD, SISMEMBER, SRANDMEMBER, ZRANGE, ZRANGEBYSCORE, ZRANGEBYLEX, ZRANK, ZSCORE, ZCARD, XRANGE, XREVRANGE, XLEN, XINFO, SCAN, HSCAN, SSCAN, ZSCAN, TTL, PTTL, EXISTS, TYPE, DBSIZE, INFO, KEYS, RANDOMKEY, OBJECT, MEMORY USAGE, FT.INFO, FT.SEARCH, FT._LIST, JSON.GET, JSON.OBJKEYS, JSON.OBJLEN, JSON.ARRLEN, JSON.TYPE
- Rejects any command not on the allowlist
- Always available (no readonly mode check — it's inherently safe)
- Parses and returns structured results

### Phase J: Build `valkey_write` tool (3–4 hr)

**File:** `tools/valkey_write.py`

Mutating command runner. Write tier — allowlisted mutations only, destructive commands blocked.

```python
async def valkey_write(
    command: str,           # e.g., "SET", "HSET", "DEL"
    args: List[str] = None, # Command arguments
) -> Dict[str, Any]
```

- Allowlisted write commands: SET, MSET, SETNX, SETEX, PSETEX, APPEND, INCR, INCRBY, INCRBYFLOAT, DECR, DECRBY, GETSET, GETDEL, HSET, HMSET, HSETNX, HDEL, HINCRBY, HINCRBYFLOAT, LPUSH, RPUSH, LPOP, RPOP, LSET, LINSERT, LREM, LTRIM, SADD, SREM, SPOP, SMOVE, ZADD, ZREM, ZINCRBY, ZPOPMIN, ZPOPMAX, XADD, XDEL, XTRIM, XACK, DEL, UNLINK, EXPIRE, PEXPIRE, EXPIREAT, PEXPIREAT, PERSIST, RENAME, RENAMENX, COPY, PUBLISH, JSON.SET, JSON.DEL, JSON.ARRAPPEND, JSON.ARRPOP, JSON.ARRTRIM, JSON.NUMINCRBY, JSON.NUMMULTBY, JSON.STRAPPEND, JSON.TOGGLE, JSON.CLEAR, FT.CREATE, FT.DROPINDEX, FT.ALTER
- Explicitly blocks destructive commands (FLUSHALL, FLUSHDB, SHUTDOWN, CONFIG SET, CLUSTER RESET, DEBUG, EVAL, EVALSHA, SCRIPT)
- Disabled in readonly mode
- Returns structured results

### Phase K: Build `valkey_admin` tool (2–3 hr)

**File:** `tools/valkey_admin.py`

Destructive command runner. Opt-in only, disabled by default.

```python
async def valkey_admin(
    command: str,           # e.g., "FLUSHALL", "CONFIG SET"
    args: List[str] = None, # Command arguments
    confirm: bool = False,  # Must be True to execute destructive commands
) -> Dict[str, Any]
```

- Requires explicit opt-in via server config (e.g., `VALKEY_ADMIN_ENABLED=true`)
- Commands: FLUSHALL, FLUSHDB, CONFIG SET, CONFIG RESETSTAT, CLUSTER RESET, CLUSTER FAILOVER, SHUTDOWN, DEBUG, EVAL, EVALSHA, SCRIPT, CLIENT KILL, SWAPDB, MIGRATE
- `confirm` parameter must be `True` — double safety gate
- Disabled in readonly mode
- Returns structured results with warnings about destructive actions

### Phase L: Tests for Command Runner tools (3–4 hr)

| File | Covers |
|------|--------|
| `tests/test_valkey_read.py` | Allowlist enforcement, command parsing, structured results |
| `tests/test_valkey_write.py` | Allowlist enforcement, destructive command blocking, readonly mode |
| `tests/test_valkey_admin.py` | Opt-in config, confirm gate, destructive command execution |

---

## File Changes Summary

### Delete

| Category | Files |
|----------|-------|
| Tool modules | `json.py`, `string.py`, `list.py`, `set.py`, `sorted_set.py`, `hash.py`, `stream.py`, `bitmap.py`, `hyperloglog.py`, `misc.py`, `server_management.py`, `semantic_search.py`, `vss.py`, `index.py` |
| Test files | `test_json.py`, `test_json_additional.py`, `test_json_readonly.py`, `test_string.py`, `test_list.py`, `test_list_additional.py`, `test_list_readonly.py`, `test_set.py`, `test_set_readonly.py`, `test_sorted_set.py`, `test_sorted_set_additional.py`, `test_sorted_set_readonly.py`, `test_hash.py`, `test_stream.py`, `test_stream_additional.py`, `test_stream_readonly.py`, `test_bitmap.py`, `test_hyperloglog.py`, `test_misc.py`, `test_server_management.py`, `test_semantic_search.py`, `test_semantic_search_integration.py`, `test_embeddings.py`, `test_bedrock_embeddings.py`, `test_openai_embeddings.py`, `test_providers_coverage.py`, `test_vector_search_integration.py`, `test_vss.py`, `test_vss_live_integration.py`, `test_index.py` |
| Old plans | `SEMANTIC_SEARCH_REMOVAL_PLAN.md`, `SEMANTIC_SEARCH_REMOVAL_ESTIMATE.md`, `VALKEY_SEARCH_SKILL_ESTIMATE.md`, `VALKEY_SEARCH_SKILL_ESTIMATE_SUMMARY.md`, `COMBINED_WORK_ESTIMATE.md`, `SKILL_VECTOR_SEARCH_ESTIMATE.md`, `VSS_GLIDE_MIGRATION_ESTIMATE.md` |

### Create

| File | Description |
|------|-------------|
| `tools/search_manage_index.py` | `manage_index` tool |
| `tools/search_add_documents.py` | `add_documents` tool |
| `tools/search_query.py` | `search` tool |
| `tools/search_aggregate.py` | `aggregate` tool |
| `tools/json.py` | Reimplemented JSON Intelligence tools (5 tools) |
| `tools/valkey_read.py` | `valkey_read` — read-only command runner |
| `tools/valkey_write.py` | `valkey_write` — mutating command runner |
| `tools/valkey_admin.py` | `valkey_admin` — destructive command runner (opt-in) |
| `tests/test_search_manage_index.py` | Tests |
| `tests/test_search_add_documents.py` | Tests |
| `tests/test_search_query.py` | Tests |
| `tests/test_search_aggregate.py` | Tests |
| `tests/test_json.py` | Tests for reimplemented JSON tools |
| `tests/test_valkey_read.py` | Tests |
| `tests/test_valkey_write.py` | Tests |
| `tests/test_valkey_admin.py` | Tests |

### Modify

| File | Change |
|------|--------|
| `common/connection.py` | Full rewrite — replace valkey-py with Valkey-GLIDE |
| `common/config.py` | Remove `vec_index_type` from VALKEY_CFG, update for GLIDE connection options |
| `tools/__init__.py` | Import only new modules |
| `main.py` | Import only new modules |
| `pyproject.toml` | Replace `valkey` with `valkey-glide`, remove unused deps |
| `README.md` | Full rewrite of tools/config sections |
| `tests/test_config.py` | Remove embedding config tests if needed |
| `tests/test_connection.py` | Verify no broken refs |

### Regenerate

| File | Reason |
|------|--------|
| `uv.lock` | After dependency changes |

---

## Estimated Effort

| Phase | Hours |
|-------|-------|
| 0. GLIDE connection layer | 2–3 |
| A. `manage_index` | 2–3 |
| B. `add_documents` | 2–3 |
| C. `search` | 3–4 |
| D. `aggregate` | 3–4 |
| E. Strip removed tools | 1–2 |
| F. Dependency cleanup | 1 |
| G. Tests (Phase 1) | 3–4 |
| H. Documentation | 1–2 |
| I. `valkey_read` | 3–4 |
| J. `valkey_write` | 3–4 |
| K. `valkey_admin` | 2–3 |
| L. Tests (Phase 2) | 3–4 |
| **Total** | **29–41** |

---

## Risks

| Risk | Mitigation |
|------|-----------|
| GLIDE lacks typed API for FT.* and JSON.* commands | Use `custom_command()` for search and JSON operations; typed API for standard commands |
| GLIDE API differences from valkey-py | Greenfield rewrite — no porting, build fresh against GLIDE docs |
| Removing tools that downstream users depend on | This is a deliberate product decision backed by benchmark data |
| FT.AGGREGATE DSL coverage gaps | Start with core stages; add more in follow-up phases |
| Embedding provider fallback | Ollama + nomic-embed-text; document that Ollama must be running locally |
| JSON tool trimming breaks tests | Trim tests in same commit as tool removal |
| Command allowlist gaps in valkey_read/write | Start with core commands; extend allowlists based on usage feedback |
| valkey_admin accidentally enabled in production | Disabled by default, requires explicit config + confirm parameter — double safety gate |

---

## Acceptance Criteria

### Phase 1 — AI Search + JSON Intelligence (9 tools)
- [ ] Server exposes exactly 9 Phase 1 tools: `manage_index`, `add_documents`, `search`, `aggregate`, `json_get`, `json_set`, `json_arrappend`, `json_arrpop`, `json_arrtrim`
- [ ] All 9 tools are fresh implementations — no code retained from existing tools
- [ ] `manage_index` accepts structured JSON → FT.CREATE/DROP/INFO/_LIST, defaults COSINE + HNSW
- [ ] `add_documents` performs embed → binary pack → HSET, supports Bedrock/OpenAI/Ollama with fallback
- [ ] `search` auto-detects semantic/text/hybrid/find-similar from params
- [ ] `aggregate` accepts structured JSON pipeline → valid FT.AGGREGATE syntax
- [ ] All existing tools are deleted (including json.py — reimplemented fresh)

### Phase 2 — Command Runner (3 tools, 3-tier safety)
- [ ] `valkey_read` executes allowlisted read-only commands, rejects everything else
- [ ] `valkey_write` executes allowlisted mutating commands, blocks destructive commands, respects readonly mode
- [ ] `valkey_admin` is disabled by default, requires server config opt-in + `confirm=True` to execute
- [ ] Destructive commands (FLUSHALL, FLUSHDB, SHUTDOWN, etc.) are impossible without both config opt-in and confirm flag

### Both Phases
- [ ] All tests pass
- [ ] README updated to reflect 12-tool surface (Phase 1 + Phase 2)
