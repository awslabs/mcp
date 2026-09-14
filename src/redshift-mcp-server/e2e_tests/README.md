# End-to-end tests

The tests are not in this directory. They are written by an agent, at run time, against live
Redshift warehouses.

The harness provisions the AWS resources, generates an agent config that hands the agent the
server built from this working tree, gives it a scenario in prose, and records what it did and
concluded in a report per scenario. A scenario names the surface to cover and points at the unit
tests for the cases; it never says what should happen, because an agent told the answer reports
it back instead of finding it out.

Nothing here runs under `pytest`. `uv run pytest` collects the unit suite only.

## Prerequisites

- An AWS profile with permission to create Redshift clusters, Serverless workgroups, IAM roles
  and Secrets Manager secrets. Use a sandbox account: the harness creates and deletes real
  infrastructure.
- `kiro-cli` on PATH, signed in.
- `uv` on PATH. The harness runs the server through it, in this package's own environment.

## Setup

```bash
cp config.toml.example config.toml
# fill in [aws].profile and [aws].region
```

`config.toml` is git-ignored: it names an account. Every account-specific value lives there, and
a missing or unfilled setting fails the run rather than falling back to a default that might
reach the wrong account.

## Commands

Run from the package root, so that `e2e_tests` is importable:

```bash
uv run python -m e2e_tests.run status   # what exists, changing nothing
uv run python -m e2e_tests.run up       # create, resume, seed, grant
uv run python -m e2e_tests.run test     # the above, then the scenarios, then teardown
uv run python -m e2e_tests.run pause    # stop compute billing
uv run python -m e2e_tests.run down     # delete everything the harness owns
```

`test` takes a scenario name — `branch` for the current branch's changes, `tools` for every
tool against both warehouse types — and defaults to running both. `--keep-up` skips teardown,
so an iteration does not pay to resume.

Every operation is idempotent. `up` against warehouses that are already seeded costs a few
describe calls.

## What a run costs

| | |
|---|---|
| Provisioned cluster | `ra3.large` x2. Create ~4 min, pause ~5.5 min, resume ~4 min |
| Serverless workgroup | 8 RPU. Create ~1 min |
| Seeding | ~424k rows by COPY from `s3://redshift-downloads/tickit/`, a few minutes |
| A scenario | 20-40 min of agent time |

Teardown pauses the cluster rather than deleting it, so between runs it bills storage only and
the next run resumes instead of creating. Set `destroy_after_run = true` to delete both
warehouses instead; the next run then pays full creation. Serverless has no pause operation and
bills nothing while idle, so it is always left alone.

## The five configurations

Access mode and write confirmation are read once at server start, so one server cannot show more
than one configuration. The generated agent therefore carries five, and a scenario can compare
them within a single conversation:

| Prefix | Configuration | Batch action |
|---|---|---|
| `ro_*` | default: read-only | allowed |
| `rw_*` | `ACCESS_MODE=read-write`, writes confirmed | allowed |
| `rwu_*` | `ACCESS_MODE=read-write` with `UNSAFE_SKIP_WRITE_CONFIRMATION=true` | allowed |
| `nb_*` | default: read-only | denied |
| `nbw_*` | `ACCESS_MODE=read-write` with `UNSAFE_SKIP_WRITE_CONFIRMATION=true` | denied |

The prefixes are not cosmetic. All five servers register the same seven tool names, and an agent
offered five `execute_query` tools sees one, with no say in which server answers it. Each
server's tools are aliased to a distinct name so a scenario can tell the configurations apart.

The denied pair is what reaches the server's `no_batch` fallback. The server selects that path
from a real `AccessDeniedException`, so no setting reaches the code; the harness assumes a role
with a session policy denying exactly that one action, and refuses to start a run if the denial
is not in effect. Both the role's own database identity and the profile's are granted the sample
schema, so a fallback read is exercised against user tables rather than only the catalogue.

There are two of them because the fallback's refusals sit behind different gates. `nb_*` is the
default install, which is the compatibility case the fallback exists for. `nbw_*` skips write
confirmation, because confirmation is checked before the fallback is consulted: at any
configuration that confirms, a write is refused for want of a confirmation, and the fallback's
own explanation of why it cannot serve writes never surfaces.

## Watching a run

A run takes tens of minutes, so start it in the background and poll it. Poll in short
intervals — a minute is about right — rather than sleeping once for the whole expected
duration: a single long sleep cannot be interrupted, reports nothing while it holds, and
outlasts a run that failed in its first minute.

```bash
uv run python -u -m e2e_tests.run test --keep-up > /tmp/e2e.log 2>&1 &
while pgrep -f 'e2e_tests.run' >/dev/null; do tail -1 /tmp/e2e.log; sleep 60; done
```

`python -u` matters. Without it the harness's progress sits in a pipe buffer and the log stays
empty until the run ends.

## What a run cannot reach

`rw_*` never completes a confirmation round trip. The agent CLI does not advertise MCP
elicitation, so the server has nowhere to ask and refuses the write instead. That exercises the
fail-closed branch, which is the one that matters, but a confirm and a decline are only
observable from a client that can prompt. `rwu_*` covers what happens once a write is allowed
through.

## Reports

`report_branch.md` and `report_tools.md`, one per scenario, overwritten by each run and committed.
They are the evidence a commit or pull request points at, so they are worth reading before being
cited, and a change that alters behaviour wants them regenerated alongside it.

Undated, and overwritten rather than accumulated: a report belongs to the commit that carries it,
so git holds the history. `git log -p report_branch.md` shows how the answer changed and which
change moved it.

Each opens with the branch and commit under test, the warehouses and their sizes, and the exit
status and duration. Then three sections, in the order a reader wants them:

1. **Summary** — a table, one row per scenario or per tool, PASS or FAIL, and a comment only
   where there is something to say, followed by any notes. Written by the agent, which is asked
   for exactly this shape; the harness lifts it out of the reply and puts it first.
2. **Prompt** — what was actually asked, so a surprising row can be weighed against it.
3. **Transcript** — everything else the agent said and every tool it called.

A run whose agent produced no summary says so in place of the table, rather than leaving an empty
section that reads like a clean result.

## Not committed

- `config.toml` — names an account and a profile.
- `.kiro/agents/` — the generated agent config, which holds live session credentials for the
  denied-batch role and absolute paths true only on the machine that wrote it.
- `.logs/` — one server log per configuration, holding every statement a run sent. Useful right
  after a run, worthless a week later.

## Measured, and worth knowing

- `redshift:CreateCluster` advertises a `LoadSampleData` parameter, but it is refused on current
  node types, and Serverless has no equivalent. Both warehouses are seeded by COPY instead.
- A fresh provisioned cluster grants an IAM identity nothing, not even `CREATE SCHEMA`. Seeding
  runs as the managed master user, and the server's own identity is granted afterwards.
  Serverless is more permissive, but is treated the same way.
- The Data API resolves the target before it authorizes. A made-up cluster identifier answers
  `ValidationException` whatever the caller is allowed, so a denial can only be confirmed
  against a warehouse that is up.
