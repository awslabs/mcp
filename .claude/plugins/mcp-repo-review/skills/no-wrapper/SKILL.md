---
name: mcp-no-wrapper
description: Use when reviewing a new MCP server PR to determine if it is a "boto3 wrapper" per the awslabs/mcp wrapper policy. Activates for PRs adding new servers, or when asked to evaluate whether an MCP server qualifies as non-wrapper.
---

# MCP Wrapper Policy Review

When a PR adds a new MCP server to the repository, evaluate whether it qualifies as a wrapper under the current policy. Wrappers are not accepted — only servers with demonstrable non-wrapper value are merged.

## Workflow

1. **Inventory tools:** Parse all `tools.py` files in the server directory. Find tool registrations (`@mcp.tool`, `mcp.tool(name=...)(...)`) and list every MCP tool with its function name and docstring.
2. **Map AWS clients:** For each tool, search for `get_aws_client('service')`, `boto3.client('service')`, or `Session().client('service')` calls — both in the tool function and in any helper functions it calls.
3. **Classify each tool:** Apply the classification criteria from [references/wrapper-policy.md](references/wrapper-policy.md).
4. **Produce verdict:** Generate a structured report with tool-by-tool classification, non-wrapper highlights, wrapper concerns, and an overall verdict.

## Classification Quick Reference

| Signal | Classification |
|--------|---------------|
| Calls exactly 1 boto3 method, returns result | **1:1 wrapper** ❌ |
| Chains multiple calls from same service | **Multi-step** ⚠️ (borderline) |
| Calls multiple different AWS services | **Cross-service non-wrapper** ✅ (Category 1) |
| Adds custom logic (dependency graphs, polling, report generation) | **Domain-specific non-wrapper** ✅ (Category 1) |
| Accesses data planes not in AWS APIs (RunCommand, DB connections) | **Data-plane non-wrapper** ✅ (Category 3) |
| Uses no AWS APIs | **Non-AWS non-wrapper** ✅ (Category 4) |

## Verdict Format

- ✅ **Not a Wrapper** — clear non-wrapper value across multiple tools
- ⚠️ **Mixed** — some non-wrapper value but significant wrapper-like tools
- ❌ **Wrapper** — predominantly 1:1 API mappings

## Reference Files

### [wrapper-policy.md](references/wrapper-policy.md)
**When:** ALWAYS load when evaluating a server for wrapper status
**Contains:** Full wrapper policy definitions, non-wrapper categories, and evaluation tips
