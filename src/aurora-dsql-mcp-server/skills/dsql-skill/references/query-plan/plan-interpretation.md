# Plan Interpretation Reference

## Table of Contents

1. [DSQL Node Types](#dsql-node-types)
2. [Layered Plan Structure](#layered-plan-structure)
3. [Calculating Node Duration](#calculating-node-duration)
4. [Detecting Estimation Errors](#detecting-estimation-errors)
5. [Nested Loop Amplification](#nested-loop-amplification)
6. [Post-Scan Filter Selectivity](#post-scan-filter-selectivity)
7. [Hash Table Resizing](#hash-table-resizing)
8. [High-Loop Storage Lookups](#high-loop-storage-lookups)
9. [Anomalous Values](#anomalous-values)
10. [Projections and Row Width](#projections-and-row-width)

---

## DSQL Node Types

DSQL stores all table data in B-Tree structures. Secondary indexes are also B-Tree, and contain the primary table keys for the secondary index values that make up the tree. DSQL extends standard PostgreSQL with storage-layer node types:

### DSQL-Specific Nodes

| Node Type               | Description                                                                     |
| ----------------------- | ------------------------------------------------------------------------------- |
| Full Scan (btree-table) | Full table scan                                                                 |
| Storage Scan            | Physical read of >1 rows of data from storage layer via Pushdown Compute Engine |
| B-Tree Scan             | Physical read of rows from storage                                              |
| Storage Lookup          | Point lookup of a row by internal row pointer (follows index scan)              |
| B-Tree Lookup           | Point lookup of a table entry by key                                            |

### Standard PostgreSQL Nodes

| Node Type       | Description                                            |
| --------------- | ------------------------------------------------------ |
| Nested Loop     | Iterates inner side once per outer row                 |
| Hash Join       | Builds hash table from one side, probes with the other |
| Merge Join      | Merges two pre-sorted inputs                           |
| Index Scan      | Scans an index and fetches matching rows               |
| Index Only Scan | Retrieves all data from index access (no table access) |
| Seq Scan        | Sequential full table scan                             |
| Sort            | Sorts rows for Merge Join or ORDER BY                  |
| Aggregate       | Computes GROUP BY / aggregate functions                |

## Layered Plan Structure

A logical scan decomposes into a Storage Scan, which itself has a B-Tree Scan child — not two siblings. Index Scan adds a **second, parallel** Storage Lookup branch (its own B-Tree Lookup child) for columns the index does not cover.

**Full Scan (single branch):**

```
Full Scan (btree-table) on tablename
  Filter: col_a = 'v'              ← query processor filter (post-transfer)
  -> Storage Scan on tablename
       Filters: col_b = 'v'        ← storage filter (pre-transfer)
       -> B-Tree Scan on tablename
```

**Index Scan (two parallel branches; Storage Lookup is a sibling of Storage Scan, not a child):**

```
Index Scan using idx on tablename
  Index Cond: col_a = 'v'
  -> Storage Scan on idx
       -> B-Tree Scan on tablename
  -> Storage Lookup on tablename   ← separate branch for non-covered columns
       -> B-Tree Lookup on tablename
```

A child's timing and row counts roll up into its parent's totals — not into a sibling branch.

## Calculating Node Duration

DSQL follows the standard PostgreSQL EXPLAIN convention: `actual time` is reported **per iteration**, not cumulative. The node's total wall-clock time is:

```
Node Duration = actual_time_end × loops
```

Where:

- `actual_time_end` is the per-iteration time reported for the node (in ms)
- `loops` is the number of times the node executed (always 1 at the top level; >1 for the inner side of a Nested Loop)

Rank all nodes by total duration descending. Begin analysis from the most expensive node.

## Detecting Estimation Errors

An estimation error exists when estimated rows diverge significantly from actual rows:

| Error Magnitude | Classification                                            |
| --------------- | --------------------------------------------------------- |
| 2x–5x           | Minor — note but low priority                             |
| 5x–50x          | Significant — investigate statistics                      |
| 50x+            | Severe — likely correlated predicates or stale statistics |

Calculate error ratio: `actual_rows / estimated_rows` (or inverse if estimate is higher).

For each significant error, record:

- The node type and table
- The estimated vs actual row count
- The index or scan method used
- Any filter predicates applied

## Nested Loop Amplification

Flag when a Nested Loop's outer input has a significant estimation error:

**Pattern:**

```
Nested Loop (est: N rows, actual: M rows)
├── [Outer] Hash Join / Scan (est: X, actual: Y where Y >> X)
└── [Inner] Index Scan (per-loop cost × Y loops)
```

**Explanation:** The planner chose Nested Loop expecting X iterations on the inner side. With Y actual iterations (where Y >> X), total inner-side cost = per-loop cost × Y. A Hash Join or Merge Join would have been more efficient at this cardinality.

**Quantify:**

- Expected total inner time: per-loop time × estimated outer rows
- Actual total inner time: per-loop time × actual outer rows
- Amplification factor: actual / estimated

## Post-Scan Filter Selectivity

Calculate filter waste when a node applies a post-scan filter:

```
Filter Selectivity = Rows Removed by Filter / (Rows Removed by Filter + Actual Rows)
```

| Selectivity | Interpretation                                   |
| ----------- | ------------------------------------------------ |
| <10%        | Minimal waste — filter removes few rows          |
| 10%–50%     | Moderate — consider composite index              |
| >50%        | High waste — strong candidate for index pushdown |

For nodes inside loops, calculate total filter waste:

```
Total rows scanned = (Actual Rows + Rows Removed) × loops
Total rows filtered = Rows Removed × loops
```

## Hash Table Resizing

When a Hash Join reports `Buckets: originally N, now M` (where M > N):

- The planner underestimated the build-side cardinality
- The hash table was dynamically resized during execution
- This adds memory pressure and execution overhead

Flag the build-side estimation error and trace it to the source scan node.

## High-Loop Storage Lookups

When a Storage Lookup has a high loop count:

```
Total I/O operations = actual_rows × loops
```

Flag when total I/O operations exceed 10,000. Each Storage Lookup involves a point read from the storage layer — high loop counts with even modest per-loop rows create significant cumulative I/O.

## Anomalous Values

Detect physically impossible row counts in DSQL plan nodes:

**Detection criteria:**

- A node reports `actual rows` exceeding the table's known total row count by 10x or more
- Particularly common on Storage Lookup nodes under high loop counts

**Example:** Storage Lookup reporting 7.7 trillion actual rows for a table with 379,484 rows.

**Action:**

- Flag as a potential DSQL reporting bug
- Verify query results are correct (they typically are — only EXPLAIN output is affected)
- Include in support request template

These anomalous values do not affect query correctness — only diagnostic output accuracy.

## Projections and Row Width

Capture Projections lists from Storage Scan and Storage Lookup nodes:

```
Projections: [col1, col2, col3, ...]
```

Assess row width overhead:

- Count projected columns per node
- Note when `SELECT *` pulls all columns from wide tables
- Flag tables with 50+ columns or estimated row width >5,000 bytes

Wide projections increase I/O on Storage Lookups and memory usage in Hash Joins. Impact scales with result set size.
