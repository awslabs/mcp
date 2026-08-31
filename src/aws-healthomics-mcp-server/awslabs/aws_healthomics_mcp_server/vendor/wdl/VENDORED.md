# Vendored: miniwdl (WDL parsing + static lint)

- **Upstream**: https://github.com/chanzuckerberg/miniwdl
- **Vendored at**: tag `v1.13.0`, commit `7f3068ff31de3d16d398ab5693a8dd8f21c5c807`
- **Date vendored**: 2026-08-27
- **License**: MIT (Copyright (c) 2018 Chan Zuckerberg Initiative) — see `LICENSE` in this directory, copied verbatim from upstream.

## Why

The `miniwdl` PyPI package declares a hard dependency on `pygtail` (GPL-licensed), used only by
`WDL.runtime` for streaming task stderr into logs during actual workflow execution. AWS
HealthOmics MCP server only needs WDL *parsing and static lint checks* (`LintAHOWorkflowDefinition`
/ `LintAHOWorkflowBundle`), never task execution, so depending on the `miniwdl` package pulls in a
GPL dependency for functionality that is never used. This vendors only the parsing/lint subtree so
the server never depends on `miniwdl` or `pygtail` at all.

## Files included (13, + LICENSE + py.typed)

Copied verbatim from `WDL/` at the tag above, with one exception noted below:

- `__init__.py` — top-level API (`load`, `load_async`, `parse_document`, etc.); attribution header
  added as a prepended comment block, code otherwise unmodified. Note: upstream's own
  `WDL/__init__.py` already does not import `WDL.runtime`, so no trimming of its imports was
  needed.
- `Error.py`, `Type.py`, `Env.py`, `Expr.py`, `Value.py`, `Tree.py`, `StdLib.py`, `Walker.py`,
  `_parser.py`, `_grammar.py` — AST, type system, and parser, unmodified.
- `Lint.py` — the static lint checks (`WDL.Lint.lint()` / `WDL.Lint.collect()`), unmodified.
- `_util.py` — **one function removed**: `PygtailLogger` (a `pygtail`-based task-stderr-streaming
  helper, lines ~453-499 in the original) was the only reference to `pygtail` anywhere in this
  entire vendored closure, and it is a lazy/deferred import inside that one function — never
  triggered by parsing or linting. It was removed (not just left as dead code) so no vendored file
  contains any textual reference to `pygtail`, keeping this tree clean for automated license/
  dependency scanning. This is the only content deviation from verbatim upstream source in the
  whole vendored tree. Everything else in `_util.py` is unmodified.
- `py.typed` — empty PEP 561 marker, copied as-is.

## Explicitly excluded

- `WDL/runtime/` (the entire task-execution engine) — not vendored, not imported, not needed.
  This is the sole source of the `pygtail` dependency upstream.
- `WDL/CLI.py`, `WDL/Zip.py` — not needed for library-level parse+lint usage; not vendored.

## Third-party (non-stdlib) dependencies required by this vendored code

Taken from upstream's own `pyproject.toml` version constraints at this tag:

- `regex>=2020.4.4`
- `lark~=1.2`
- `python-json-logger>=2,<4` (imported as `pythonjsonlogger` in `_util.py`)

None of these are GPL/MPL licensed. `pygtail` and `docker`/`xdg`/`psutil`/`bullet`/`ruamel.yaml`/
`argcomplete`/`coloredlogs`/`importlib-metadata` (upstream's other runtime/CLI dependencies) are
**not** required by this vendored subtree and must not be added as dependencies here.

## Verification

- `grep -rn pygtail .` in this directory returns zero matches.
- All `.py` files parse as valid Python (`ast.parse`).

## Public API for integration

```python
from awslabs.aws_healthomics_mcp_server.vendor import wdl

doc = wdl.parse_document(wdl_source_text)          # syntax-only parse, no typecheck/imports
# or, for full load with typechecking + import resolution (sync; wraps load_async internally):
doc = wdl.load(path_to_main_wdl_file, path=[dir_containing_bundle_files])

from awslabs.aws_healthomics_mcp_server.vendor.wdl import Lint
findings = Lint.collect(Lint.lint(doc, descend_imports=False))
# findings: List[Tuple[pos: wdl.SourcePosition, lint_class: str, message: str, suppressed: bool]]
```

`wdl.load()` raises `wdl.Error.SyntaxError` / `wdl.Error.ValidationError` /
`wdl.Error.MultipleValidationErrors` / `wdl.Error.ImportError` on invalid documents — catch these
to build error-style lint responses, same as `miniwdl check`'s own CLI does internally.

## Updating this vendored snapshot

There is no automated re-sync. To pick up upstream fixes or new lint rules, a person must manually
re-run this vendoring process against a newer miniwdl tag, re-verify the `pygtail` exclusion still
holds (upstream's module boundaries could change), and re-apply the `PygtailLogger` removal if it
still exists in `_util.py`.
