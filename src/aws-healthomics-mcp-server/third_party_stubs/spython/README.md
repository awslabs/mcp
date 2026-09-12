# `spython` compatibility stub

This is **not** a copy of, or a substitute implementation for, the real
[`spython`](https://github.com/singularityhub/singularity-cli) package
(MPL-2.0 licensed). It contains no code from that project.

`cwltool` imports three names from `spython` at module load time
(`cwltool/singularity.py`):

```python
from spython.main import Client
from spython.main.parse.parsers.docker import DockerParser
from spython.main.parse.writers.singularity import SingularityWriter
```

All three are only *used* inside functions that build and run Singularity
containers — functionality this MCP server never invokes, since
`LintAHOWorkflowDefinition`/`LintAHOWorkflowBundle` only ever call
`cwltool --validate`, which parses and statically validates a CWL document
without executing it.

Because `spython` is an unconditional (non-extra) dependency of `cwltool`,
installing the real package would pull MPL-2.0-licensed code into this
Apache-2.0 project's dependency closure purely to satisfy an import that is
never exercised. This package provides the same three names as empty stubs
so `import cwltool` succeeds, without installing the real `spython`
distribution. Each stub raises `NotImplementedError` if actually called,
so any future code path that starts relying on real Singularity build/run
behavior fails loudly instead of silently misbehaving.

It is wired in via `[tool.uv.sources]` in the parent package's
`pyproject.toml`, which tells `uv` to satisfy `cwltool`'s `spython>=0.3.0`
requirement from this local path instead of PyPI.
