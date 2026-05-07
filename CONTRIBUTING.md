# Contributing Guidelines

Thank you for your interest in contributing to our project. Whether it's a bug report, new feature, correction, or additional
documentation, we greatly value feedback and contributions from our community.

Please read through this document before submitting any issues or pull requests to ensure we have all the necessary
information to effectively respond to your bug report or contribution.

## Reporting Bugs/Feature Requests

We welcome you to use the GitHub issue tracker to report bugs or suggest features.

When filing an issue, please check existing open, or recently closed, issues to make sure somebody else hasn't already
reported the issue. Please try to include as much information as you can. Details like these are incredibly useful:

* A reproducible test case or series of steps
* The version of our code being used
* Any modifications you've made relevant to the bug
* Anything unusual about your environment or deployment

## Contributing via Pull Requests

Contributions via pull requests are much appreciated. Before sending us a pull request, please ensure that:

1. You are working against the latest source on the *main* branch.
2. You check existing open, and recently merged, pull requests to make sure someone else hasn't addressed the problem already.
3. You open an issue to discuss any significant work - we would hate for your time to be wasted. For instance, if you want to propose a new MCP Server, you would need to first open a RFC issue.

The [Developer guide](DEVELOPER_GUIDE.md) provides the steps to set up your dev environment and make sure your code is ready before you submit your pull request.

### Reviewing your changes before opening a PR

This repository ships Claude Code slash commands in `.claude/commands/` to help you self-review and fix findings before opening a PR. They review your local branch against `origin/main` — the same surface the PR will expose.

| Command | Purpose |
|---|---|
| `/review` | Scans the diff against `origin/main` and writes findings (Blockers / Suggestions / Nits) to `/tmp/cr-review-<branch>.md`. |
| `/revise` | Reads the latest findings file and applies the fixes. Commits per severity tier. Accepts `--include-nits`, `--only <IDs>`, `--skip <IDs>`. |
| `/auto-revise` | Loops `/review` → `/revise` (up to 10 rounds) until no actionable findings remain. Pass `--include-nits` to also require Nits==0 before terminating. |

Recommended flow before opening a PR:

1. Commit your work locally.
2. Run `/auto-revise` (or `/auto-revise --include-nits` for the highest bar).
3. Inspect the final findings file and any round archives at `/tmp/cr-review-<branch>-round-<i>.md`.
4. Push and open the PR.

Both `/revise` and `/auto-revise` commit but never push — you push manually once you're satisfied.

### Running CI checks locally before you push

Some packages ship a local mirror of the CI workflows so you can catch what
CI would catch without waiting for GitHub Actions. Today this lives in
`src/cloudwatch-applicationsignals-mcp-server/` and covers the same steps
as `.github/workflows/python.yml`, `pre-commit.yml`, `scanners.yml`,
`semgrep.yml`, and `check-license-header.yml`.

From repo root:

```bash
./poe           # list available tasks
./poe ci        # full run — everything CI runs
./poe ci-fast   # core correctness gates only (~25s)
./poe test      # pytest with coverage
./poe lint      # ruff-format, ruff-check, pyright
./poe scan      # bandit, detect-secrets, semgrep, license-header
./poe ci --only pytest,ruff-check     # arbitrary ci-check.sh args pass through
```

The underlying driver is `scripts/ci-check.sh` in the package — run it
directly with `--list`, `--only`, `--skip`, or `--no-fail-fast` for
finer control. First-time setup provisions a hash-pinned tool venv
for `detect-secrets` and `semgrep` (cached afterwards); requires `uv`,
`python3`, and `jq` on `PATH`.

### Special `./README.md` considerations for new MCP servers

When adding a new MCP server, you must update the README.md to include your server in the appropriate categories under "Available MCP Servers". Add it to both the "Browse by What You're Building" and "Browse by How You're Working" sections with a brief description that clearly explains its purpose. Include a link to the server's directory using the pattern `src/your-server-name/`. Ensure your server's description is consistent with the style of existing entries.

GitHub provides additional document on [forking a repository](https://help.github.com/articles/fork-a-repo/) and
[creating a pull request](https://help.github.com/articles/creating-a-pull-request/).

## Finding contributions to work on

Looking at the existing issues is a great way to find something to contribute on. As our projects, by default, use the default GitHub issue labels (enhancement/bug/duplicate/help wanted/invalid/question/wontfix), looking at any 'help wanted' issues is a great place to start.

## Code of Conduct

This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
[opensource-codeofconduct@amazon.com](mailto:opensource-codeofconduct@amazon.com) with any additional questions or comments.

## Security issue notifications

If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public github issue.

## Licensing

See the [LICENSE](LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.
