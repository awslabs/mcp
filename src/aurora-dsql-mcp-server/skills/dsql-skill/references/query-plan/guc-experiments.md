# GUC Experiments and Redundant Predicate Testing

## Table of Contents

1. [GUC Experiment Procedure](#guc-experiment-procedure)
2. [Transaction Isolation](#transaction-isolation)
3. [Interpreting GUC Results](#interpreting-guc-results)
4. [Redundant Predicate Testing](#redundant-predicate-testing)
5. [Handling Regressions](#handling-regressions)

---

## GUC Experiment Procedure

GUC (Grand Unified Configuration) experiments temporarily disable specific planner strategies to test whether viable alternatives exist.

### Experiments to Run

Per SKILL.md Phase 1, the `{original_sql}` reaching this phase is always a **SELECT** (DML is rewritten to SELECT before plan capture, INSERT and pl/pgsql are rejected). Execute two variants against that SELECT:

**Experiment 1 — Default baseline** (read-only, use `readonly_query`):

```python
readonly_query("EXPLAIN ANALYZE VERBOSE {original_sql}")
```

**Experiment 2 — Merge join only.** Needs `SET LOCAL` to scope GUC changes to a single transaction. `readonly_query` rejects the multi-statement form (semicolon guard), so this path requires `transact`. **Safety rules the caller MUST apply before invoking `transact`:**

- `{original_sql}` **MUST** be a SELECT — verify by reading the first non-comment token. Reject and abort otherwise.
- **MUST NOT** interpolate the `{original_sql}` through any prompt-derived path that could carry an additional statement. Pass it as a single list element, not concatenated into another string.
- **MUST NOT** pass `--allow-writes` SQL in the list. This list may only contain the four `SET LOCAL` + `EXPLAIN ANALYZE VERBOSE SELECT` statements shown below.
- If any statement fails (e.g., MCP server rejects it, the `EXPLAIN` errors), halt and report; do not chain additional recovery SQL.

```python
transact([
    "SET LOCAL enable_hashjoin = off",
    "SET LOCAL enable_nestloop = off",
    "SET LOCAL enable_mergejoin = on",
    "EXPLAIN ANALYZE VERBOSE {original_sql}",
])
```

`SET LOCAL` confines the GUC change to the transaction `transact` opens; the change is automatically discarded at commit.

### Execution Gate

| Original query time | Action                                                         |
| ------------------- | -------------------------------------------------------------- |
| ≤30 seconds         | Perform both experiments                                       |
| >30 seconds         | Skip experimentation; note in report; recommend manual testing |

**When original query ran >30 seconds**, the report **MUST** include a section explicitly stating that GUC experimentation was skipped due to execution time exceeding the 30-second threshold, and **MUST** provide the manual testing SQL verbatim so the customer can run it themselves in psql (session scope — no `BEGIN`/`COMMIT` needed when run interactively):

```sql
SET enable_hashjoin = off;
SET enable_nestloop = off;
SET enable_mergejoin = on;
EXPLAIN ANALYZE VERBOSE {original_sql};
```

Do not re-run the original query for redundant predicate testing either when execution exceeded 30s — recommend rewrites and explain expected impact from statistics.

## Transaction Isolation

**Each experiment MUST execute in a fresh `transact` call.** `transact` auto-wraps its statement list in its own `BEGIN/COMMIT`, and `SET LOCAL` confines the GUC to that transaction, so the settings MUST NOT carry into the next experiment. Execute experiments as separate `transact` calls.

## Handling experiment failures

If a `transact` call returns an error mid-batch (e.g., a `SET` is rejected, or the EXPLAIN fails), record the error under a "GUC experiment failed" finding in the report and **do not** compare partial results against the default baseline. `transact` auto-rolls back on any error, so session state is clean — but the missing plan means you cannot claim the planner chose suboptimally; surface the error verbatim instead.

## Interpreting GUC Results

### Plan Structure Changed

When the disabled strategy is replaced by a different one:

- Compare execution time between variants
- Compare DPU estimates
- Compare rows scanned and memory usage
- If the alternative is faster: the planner's cost model chose suboptimally
- If the alternative is slower: the planner's original choice was correct despite the estimation error

### Disabled Strategy Still Used (Inflated Cost)

When the planner uses the disabled strategy anyway, it adds ~10 billion to the node cost as a penalty. This indicates:

- No viable alternative join strategy exists for that node
- The bottleneck is the data access pattern (full scan, missing index), not the join choice
- Focus recommendations on improving the scan/index layer rather than join strategy

### Comparison Table Format

Present results as:

| Metric               | Default    | Merge Join Only |
| -------------------- | ---------- | --------------- |
| Plan structure       | [describe] | [describe]      |
| Execution time       | Xms        | Yms             |
| DPU (Total)          | N          | M               |
| Key node differences | [describe] | [describe]      |
| Strategy inflated?   | N/A        | Yes/No          |

## Redundant Predicate Testing

A redundant predicate is a join or filter predicate that is semantically true given business rules but not logically derivable from the existing join chain alone.

### When to Identify Redundant Predicates

Look for this pattern:

1. A table is accessed via a full scan or unselective scan
2. No direct filter predicate matches a leading index column
3. A business-rule relationship exists between columns across tables in the join chain
4. Adding an explicit predicate would match an existing composite index's leading column

### How Aurora DSQL Handles Predicate Inference

Aurora DSQL's optimizer performs transitive closure on equality predicates via EquivalenceClasses:

- Given `A = B` and `B = C`, it infers `A = C`
- Given `A = B` and `B = 42`, it propagates the constant: `A = 42`

The optimizer **cannot** infer business-rule relationships (e.g., "all orders for a user belong to the same tenant as the user"). These require explicit predicates.

### Testing Procedure

**When original query ran ≤30s:**

1. Identify all redundant predicates
2. Add all simultaneously to the SQL statement
3. Execute EXPLAIN ANALYZE VERBOSE with all predicates using `readonly_query`
4. Compare against original: execution time, plan structure, rows scanned, DPU estimate

**When original query ran >30s:**

Skip automatic testing. Recommend the rewrites and explain expected impact from index statistics.

### Before/After Comparison Format

```markdown
### Redundant Predicate Test Results

**Predicates added:**

- `table.column = value` (derived from: business rule explanation)

| Metric              | Original   | With Redundant Predicates |
| ------------------- | ---------- | ------------------------- |
| Execution time      | Xms        | Yms                       |
| DPU (Total)         | N          | M                         |
| Plan structure      | [describe] | [describe]                |
| Rows scanned (node) | A          | B                         |
```

## Handling Regressions

When adding all redundant predicates simultaneously causes a regression (higher execution time or DPU):

1. Analyze which predicate(s) caused the regression by comparing plan structure changes
2. Identify the mechanism (e.g., planner changed a targeted Nested Loop to a broad Merge Join scan)
3. Recommend applying only the beneficial predicates
4. Explain why the regressing predicate caused a worse plan

Present as a separate finding in the diagnostic report with the tag "Redundant Predicate Experiment".
