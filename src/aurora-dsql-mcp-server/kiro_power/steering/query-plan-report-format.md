# Diagnostic Report Format

The diagnostic report is produced as Markdown, rendered inline in the agent's response. **Produce a full report for every explainability request**, even ones that feel simple — the structure is the deliverable, not a formality.

## Required Elements Checklist

Every report **MUST** contain all of these. Missing any one of them is a regression:

- [ ] `# SQL Query Explainability — Diagnostic Report` as the H1
- [ ] `Preview Only - not for distribution` on the line immediately below the H1
- [ ] `## Query Information` table with Query Identifier, Planning Time, Execution Time, DPU Estimate
- [ ] `## SQL Statement` section with the SQL in a fenced block
- [ ] `## Plan Overview` section with the plan tree in a fenced block
- [ ] `## Findings` section with numbered findings ordered by Node Duration (most expensive first)
- [ ] Each finding uses `#### What we observed`, `#### Why it happened`, `#### Recommendation` as H4 subheadings, verbatim
- [ ] Final `## Summary` table with columns `# | Finding | Severity | Recommendation | Expected Impact`
- [ ] Closing `## Next Steps` block inviting the user to say "reassess" (or equivalent) after applying any recommendation, so the skill can measure the actual impact against the predicted Expected Impact

### Conditional requirements

- **Execution Time >30s:** the report **MUST** include a section stating GUC experimentation was skipped due to the 30-second threshold, AND the verbatim manual GUC testing SQL (see the skipped-query block under [GUC Comparison Table](#guc-comparison-table)). Do **not** re-run the query for redundant predicate testing either.
- **Anomalous EXPLAIN values (e.g., trillion-row counts on small tables):** the report **MUST** explicitly confirm to the user that **query results are correct** despite the anomalous EXPLAIN output, flag the anomaly as a potential DSQL reporting bug, and include a [Support Request Template](#support-request-template) with Query ID, table statistics (reltuples, actual COUNT), and full plan output — no raw customer data values.

## Table of Contents

1. [Report Structure](#report-structure)
2. [Finding Format](#finding-format)
3. [Severity Levels](#severity-levels)
4. [Summary Table](#summary-table)
5. [GUC Comparison Table](#guc-comparison-table)
6. [Support Request Template](#support-request-template)

---

## Report Structure

Produce the report using this exact structure:

```markdown
# SQL Query Explainability — Diagnostic Report

Preview Only - not for distribution

## Query Information

| Field            | Value                                                            |
| ---------------- | ---------------------------------------------------------------- |
| Query Identifier | {query_id}                                                       |
| Planning Time    | {planning_time} ms                                               |
| Execution Time   | {execution_time} ms                                              |
| DPU Estimate     | Compute: {compute}, Read: {read}, Write: {write}, Total: {total} |

## SQL Statement

\`\`\`sql
{sql_statement}
\`\`\`

## Plan Overview

\`\`\`
{formatted_plan_tree}
\`\`\`

## Findings

Each finding is presented with three H4 subsections, verbatim: "What we observed" → "Why it happened" → "Recommendation".
Findings are ordered by duration impact, starting from the most expensive.

{findings}

## Summary

{summary_table}
```

## Finding Format

Each finding follows this structure:

```markdown
### Finding N: {Title} ({Severity} — {duration_or_context})

**Applies to:** {query_variant_tag}

#### What we observed

{Specific problem identified. Include a metrics table when quantitative evidence is available:}

| Metric   | Estimated | Actual | Error    |
| -------- | --------- | ------ | -------- |
| {metric} | {est}     | {act}  | {ratio}x |

#### Why it happened

{Root cause analysis with evidence from the plan, optimizer statistics, and actual cardinalities.
Show the optimizer's calculation when relevant (selectivity math, independence assumption).}

#### Recommendation

{Specific, actionable recommendation.}

{When the recommendation involves SQL, include the exact statement:}

\`\`\`sql
{recommended_sql}
\`\`\`

**Expected impact:** {What improvement the customer should expect. Ground the prediction in the
evidence you gathered — actual-vs-estimated row counts, Node Duration math, filter selectivity,
DPU breakdown. When the evidence supports a concrete prediction, state it that way (e.g.,
"Storage Lookup drops from 50 rows per loop × 2000 loops to 1 per loop ≈ 50× less read DPU;
execution should go from ~4s to ~80ms"). When the evidence is insufficient for a numeric
prediction, **do not fabricate one** — name the missing evidence explicitly (e.g., "Cannot
predict magnitude without `most_common_freqs` on this column; expected qualitative direction
is a reduction in Node Duration"). Honesty about what you don't know is always preferable to
a plausible-sounding number with no data behind it.}
```

### Query Variant Tags

Tag each finding with which query variant it applies to:

| Tag                            | Meaning                                     |
| ------------------------------ | ------------------------------------------- |
| Original Query                 | Finding from the original SQL execution     |
| GUC Experiment                 | Finding from GUC-based plan experimentation |
| Redundant Predicate Experiment | Finding from redundant predicate testing    |

### Linking Cascading Findings

When one finding's root cause is another finding:

```markdown
#### Recommendation

This finding is a consequence of Finding N — resolving that finding addresses this one.
No separate action needed.
```

## Severity Levels

| Severity   | Criteria                                                     |
| ---------- | ------------------------------------------------------------ |
| CRITICAL   | >50% of execution time; primary bottleneck                   |
| HIGH       | Root cause of a CRITICAL finding or 20–50% of execution time |
| MODERATE   | Measurable impact; worth fixing independently                |
| LOW        | Minor overhead; fix if convenient                            |
| BUG REPORT | Anomalous behavior indicating a potential DSQL bug           |

## Summary Table

Conclude the report with a summary table:

```markdown
## Summary

| # | Finding | Severity   | Recommendation            | Expected Impact   |
| - | ------- | ---------- | ------------------------- | ----------------- |
| 1 | {title} | {severity} | {one-line recommendation} | {one-line impact} |
| 2 | {title} | {severity} | {one-line recommendation} | {one-line impact} |
```

## GUC Comparison Table

When GUC experiments were performed, include a comparison:

```markdown
## GUC Experiment Results

| Metric                        | Default    | Merge Join Only |
| ----------------------------- | ---------- | --------------- |
| Plan structure                | {describe} | {describe}      |
| Execution time                | {X}ms      | {Y}ms           |
| DPU (Total)                   | {N}        | {M}             |
| Key differences               | {describe} | {describe}      |
| Disabled strategy still used? | N/A        | {Yes/No}        |
```

When GUC experiments were skipped (query >30s):

```markdown
## GUC Experiment Results

GUC experimentation skipped — original query execution time ({X}s) exceeds 30-second threshold.
Recommend testing alternative strategies manually:

\`\`\`sql
SET enable_hashjoin = off;
SET enable_nestloop = off;
SET enable_mergejoin = on;
EXPLAIN ANALYZE VERBOSE {original_sql};
\`\`\`
```

## Support Request Template

Produce when a potential DSQL bug is identified:

```markdown
## Support Request Template

**Subject:** {one-line description of the anomaly}

**Query Identifier:** {query_id}

**Description:**
{2-3 sentences explaining what was observed, why it is anomalous, and that the query
results are correct but diagnostic output appears affected.}

**Table Statistics:**

- {table}: reltuples={N}, relpages={M}, actual COUNT(*)={X}
- Index used: {index_name} ({index_columns})
- {additional context specific to the anomaly}

**DPU Estimate:** Compute={N}, Read={M}, Write={W}, Total={T}

**Full EXPLAIN ANALYZE VERBOSE output:**
\`\`\`
{full_plan_output}
\`\`\`
```

**Rules for the support template:**

- **MUST** include Query ID, full plan output, optimizer statistics, actual cardinalities, index definitions, DPU estimate
- **MUST NOT** include actual customer data values from tables
- Include only metadata, statistics, cardinalities, and plan output

## Next Steps (closing block of every report)

End the report with this block so the user knows to come back for a reassessment:

```markdown
## Next Steps

1. Apply the recommendations in order — Finding 1 first, then re-measure before deciding whether the subsequent findings still matter.
2. When any recommendation is in place, say **"reassess"** (or "I added the index" / "re-run the analysis"). I'll re-capture the plan, compare against the numbers above, and append an "Addendum: After-Change Performance" section to this report — so you can see the actual impact against the Expected Impact column.
3. If the observed change diverges significantly from the Expected Impact, I'll investigate the gap as a new finding rather than closing it out.
```

## Addendum: After-Change Performance (Phase 5)

When the user signals a reassessment, append a new H2 section to the **same** report — do not produce a separate report. The addendum has:

```markdown
## Addendum: After-Change Performance

**Change applied:** {one-line description of what the user did, e.g., "Added composite index (clientid, _transactionstartdatetime) on associate"}

**Re-captured plan:** Query Identifier {new_query_id}, Execution Time {new_ms} ms, DPU {new_total}

| Metric                 | Before        | After        | Improvement      |
| ---------------------- | ------------- | ------------ | ---------------- |
| Total Query Cost       | {before_cost} | {after_cost} | {pct}% ↓         |
| Scan Type (main node)  | {before_scan} | {after_scan} | {status}         |
| Estimated Rows Scanned | {before_est}  | {after_est}  | {pct}% ↓         |
| Execution Time         | {before_ms}   | {after_ms}   | {pct}% ↓         |
| DPU (Total)            | {before_dpu}  | {after_dpu}  | {pct}% ↓         |
| Result Set             | {before_rows} | {after_rows} | Unchanged / Diff |

**Match against Expected Impact:** {Yes — matches the N% latency reduction predicted in Finding 1 / No — only X% observed, investigating}.

**Remaining findings status:** {Finding 2 still applies / Findings 2–3 now trivial given this change}.
```

If the Result Set row count changed, flag that prominently — the change should be performance-neutral semantically, and any row-count drift means the recommendation altered query correctness (which should never happen for an index addition, and indicates something else is wrong).
