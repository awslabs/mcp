# Bundled preview service model

> **Remove this entire `aws_data/` directory once the public AWS SDK ships the
> dynamic instrumentation operations.**

`application-signals/2024-04-15/service-2.json` is a bundled botocore service
model that exposes the dynamic-instrumentation operations
(`CreateInstrumentationConfiguration`, `ListInstrumentationConfigurations`,
`GetInstrumentationConfiguration`, `DeleteInstrumentationConfiguration`,
`BatchDeleteInstrumentationConfigurations`,
`GetInstrumentationConfigurationStatus`,
`ReportInstrumentationConfigurationStatus`) before they are available in the
public `botocore` release. The dynamic instrumentation feature is in preview;
these operations are not yet part of the public `application-signals` API.

The model is generated from the service team's source-of-truth Smithy model and
trimmed to only the seven dynamic-instrumentation operations the MCP tools call.

It is loaded by `dynamic_instrumentation/aws_clients.py` through a *session-scoped*
botocore data loader (no `AWS_DATA_PATH` env mutation) with the API version pinned
to `2024-04-15`. This isolation means the bundled model is invisible to the
existing awslabs `application-signals` client.

## Removal (one-shot cleanup PR)

When the public SDK ships these operations:

1. Bump the `boto3` floor in `pyproject.toml` to the version that includes them.
2. Rewrite `dynamic_instrumentation/aws_clients.py` to re-export the parent
   `applicationsignals_client` (snapshot Logs queries already use the parent
   `logs_client` directly).
3. Delete this `aws_data/` directory.

While the feature is in preview, this directory is shipped so the tools work
against the preview API; it is removed in a follow-up once the operations are
generally available in `botocore`.
