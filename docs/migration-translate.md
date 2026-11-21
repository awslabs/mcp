# Migration Guide: Amazon Translate MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.amazon-translate-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Amazon Translate MCP server registered 19 tools. Fourteen wrapped Amazon Translate API calls (`TranslateText`, `ListLanguages`, the terminology operations, and the batch translation job operations), some with Amazon S3 checks around them. One read a batch job's error files from Amazon S3. Three ran local logic only: a translation quality check and two tools that reported on workflows running inside the server process. One returned placeholder metrics without reading any. The AWS MCP Server covers every API call through a single `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It also reaches the parts of the Amazon Translate API the server never exposed, such as `DeleteTerminology`, `StopTextTranslationJob`, translation settings, and parallel data.

No Agent Skill in the Agent Toolkit for AWS covers Amazon Translate, so there's no skill to install for it.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws-cli@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "AWS_REGION=us-east-1"
      ]
    }
  }
}
```

Set `AWS_REGION` to the Region where you use Amazon Translate. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the permissions the old server used:

- `translate:TranslateText`, `translate:ListLanguages`, `translate:ImportTerminology`, `translate:ListTerminologies`, `translate:GetTerminology`, `translate:StartTextTranslationJob`, `translate:DescribeTextTranslationJob`, and `translate:ListTextTranslationJobs`
- `iam:PassRole` on the batch job's data access role
- `s3:ListBucket` and `s3:GetObject` on the batch output bucket, to read a job's error details

Add `comprehend:DetectDominantLanguage` to detect a language with Amazon Comprehend in place of `detect_language`. The AWS managed policy `TranslateFullAccess` grants it alongside `translate:*`, for automatic source language detection (`SourceLanguageCode="auto"`). Add `translate:DeleteTerminology`, `translate:StopTextTranslationJob`, or `cloudwatch:GetMetricData` if you use those operations. The batch data access role itself doesn't change: it still needs read access to the input prefix, write access to the output prefix, and a trust policy for `translate.amazonaws.com` (see [Prerequisites for batch translation jobs](https://docs.aws.amazon.com/translate/latest/dg/async-prereqs.html)).

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

With the AWS MCP Server, ask your agent to do the same job and it makes the equivalent call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. For example, the agent might run:

```python
resp = await call_boto3(
    service_name="translate",
    operation_name="TranslateText",
    region_name="us-east-1",
    params={
        "Text": "Bonjour tout le monde, nous traduisons des notes courtes chaque matin.",
        "SourceLanguageCode": "auto",
        "TargetLanguageCode": "es",
    },
)
result = {"detected_language": resp["SourceLanguageCode"], "translation": resp["TranslatedText"]}
result
```

`call_boto3` pages `ListTerminologies` automatically, so one call returns every terminology. `ListTextTranslationJobs` has no botocore paginator, so `call_boto3` returns one page and a `NextToken` when there are more; pass it back in the next call until a response comes without one.

### Text translation and language detection

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `translate_text(text, source_language, target_language, terminology_names)` | Called `TranslateText` with `Text`, `SourceLanguageCode`, `TargetLanguageCode` and `TerminologyNames`. Given `auto`, it first ran `detect_language` (a `TranslateText` call into English) and sent the detected code. Returned the translation, the two language codes and the names of the applied terminologies; dropped the applied term pairs, and `confidence_score` was always `null`. Never sent `Settings`. | `call_boto3(service_name="translate", operation_name="TranslateText", params={"Text": ..., "SourceLanguageCode": ..., "TargetLanguageCode": ..., "TerminologyNames": [...], "Settings": {...}})` |
| `detect_language(text)` | Translated the text into English with `TranslateText` (`SourceLanguageCode="auto"`, `TargetLanguageCode="en"`) and returned the `SourceLanguageCode` it reported, with a fixed `confidence_score` of 0.95 and an empty `alternative_languages` list | `call_boto3(service_name="comprehend", operation_name="DetectDominantLanguage", params={"Text": ...})`, which returns each detected language with its score and translates nothing |
| `validate_translation(original_text, translated_text, source_language, target_language)` | Local checks only, with no AWS call: started from a score of 1.0 and subtracted for a length ratio under 0.3 or over 3.0, a translation identical to the original, HTML entities (`&lt;`, `&gt;`, `&amp;`), extra whitespace, and a single word making up more than 30% of the translation. `is_valid` meant a score of at least 0.8 and no issues. | No API equivalent. Ask the agent to review the translation, or to translate it back with `TranslateText` and compare (see Summary of Gaps). |
| `smart_translate_workflow(text, target_language, quality_threshold, terminology_names, auto_detect_language)` | Ran `detect_language` (a `TranslateText` call into English), checked the pair against `ListLanguages`, called `TranslateText` again with the detected code, then ran `validate_translation`'s local checks. It detected the language even with `auto_detect_language=False`, and `quality_threshold` only wrote a log warning. | One `call_boto3(service_name="translate", operation_name="TranslateText", params={"Text": ..., "SourceLanguageCode": "auto", "TargetLanguageCode": ...})`; the response's `SourceLanguageCode` is the detected language |

### Languages and metrics

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `list_language_pairs()` | Called `ListLanguages` (`DisplayLanguageCode="en"`, `MaxResults=500`) and returned every ordered pair of the returned codes, plus `auto` to each code, each tagged with the same five document formats. `ListLanguages` includes `auto` as a language, so the 76 codes became 5,775 pairs, including 75 pairs that target `auto` and 75 `auto` pairs listed twice. | `call_boto3(service_name="translate", operation_name="ListLanguages", params={"DisplayLanguageCode": "en"})`. The old pair list was every combination of these codes, so the language list carries the same information. |
| `get_language_metrics(language_pair, time_range)` | Checked `time_range` (`1h`, `24h`, `7d` or `30d`) and the pair format, then returned a placeholder: `translation_count` and `character_count` of 0 and `average_response_time` and `error_rate` of `null`, whatever the account's usage. Creating its CloudWatch client called `ListMetrics` once as a connectivity check; no metric data was read. | `call_boto3(service_name="cloudwatch", operation_name="GetMetricData", ...)` on the `AWS/Translate` namespace: `SuccessfulRequestCount`, `UserErrorCount`, `ServerErrorCount` and `ThrottledCount` by `Operation`, and `CharacterCount` and `ResponseTime` by `Operation` and `LanguagePair` (for example `en-es`). See the example below. |

To read a day of usage for one language pair, the agent might run:

```python
from datetime import datetime, timedelta, timezone

end = datetime.now(timezone.utc)
resp = await call_boto3(
    service_name="cloudwatch",
    operation_name="GetMetricData",
    region_name="us-east-1",
    params={
        "StartTime": (end - timedelta(hours=24)).isoformat(),
        "EndTime": end.isoformat(),
        "MetricDataQueries": [
            {
                "Id": "characters",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Translate",
                        "MetricName": "CharacterCount",
                        "Dimensions": [
                            {"Name": "LanguagePair", "Value": "en-es"},
                            {"Name": "Operation", "Value": "TranslateText"},
                        ],
                    },
                    "Period": 86400,
                    "Stat": "Sum",
                },
            },
            {
                "Id": "requests",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Translate",
                        "MetricName": "SuccessfulRequestCount",
                        "Dimensions": [{"Name": "Operation", "Value": "TranslateText"}],
                    },
                    "Period": 86400,
                    "Stat": "Sum",
                },
            },
        ],
    },
)
result = {r["Id"]: r["Values"] for r in resp["MetricDataResults"]}
result
```

For the metric list, see [CloudWatch metrics and dimensions for Amazon Translate](https://docs.aws.amazon.com/translate/latest/dg/translate-cloudwatch.html).

### Custom terminology

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_terminology(name, description, source_language, target_languages, terms)` | Built a CSV file with the header row `source,target` from the term pairs, ignoring `source_language` and `target_languages`, and called `ImportTerminology` without the required `MergeStrategy`. botocore rejected every call before sending it, and the tool reported `ServiceUnavailableError`. The file would also fail on its own: Amazon Translate rejects a CSV whose first row isn't language codes. | `call_boto3(service_name="translate", operation_name="ImportTerminology", params={"Name": ..., "Description": ..., "MergeStrategy": "OVERWRITE", "TerminologyData": {"File": "en,es\nsource term,target term\n", "Format": "CSV", "Directionality": "UNI"}})` (see the example below) |
| `import_terminology(name, description, file_content, file_format, source_language, target_languages)` | Base64-decoded `file_content` into a temporary file, checked it locally (a CSV header and the first five rows, or the TMX structure; at most 10,000 terms and 10 MB), and called `ImportTerminology` with `Directionality="UNI"` and no `MergeStrategy`, so every call failed the same way as `create_terminology`. `source_language` and `target_languages` fed only the local check. | The same `ImportTerminology` call, with the file's text in `TerminologyData.File` and `Format` set to `CSV`, `TSV` or `TMX` |
| `list_terminologies()` | Called `ListTerminologies` (`MaxResults=50`, first page only). Once the account had a terminology, the tool failed with `AttributeError`: it read a `last_updated` field that its `TerminologySummary` model doesn't have. | `call_boto3(service_name="translate", operation_name="ListTerminologies")` |
| `get_terminology(name)` | Called `GetTerminology` with `TerminologyDataFormat="CSV"` and returned the name, description, languages, term count, dates, size and format. Dropped `Arn`, `Directionality`, and `TerminologyDataLocation`, the link to download the terms. | `call_boto3(service_name="translate", operation_name="GetTerminology", params={"Name": ..., "TerminologyDataFormat": "CSV"})` |

To create a terminology, the agent might run:

```python
resp = await call_boto3(
    service_name="translate",
    operation_name="ImportTerminology",
    region_name="us-east-1",
    params={
        "Name": "product-names",
        "Description": "Product names that stay in English",
        "MergeStrategy": "OVERWRITE",
        "TerminologyData": {
            "File": "en,es,fr\nAmazon Photos,Amazon Photos,Amazon Photos\n",
            "Format": "CSV",
            "Directionality": "UNI",
        },
    },
)
props = resp["TerminologyProperties"]
result = {k: props.get(k) for k in ("Name", "SourceLanguageCode", "TargetLanguageCodes", "TermCount")}
result
```

The first row of a CSV file holds the language codes: the source language first, then each target language (see [Creating a custom terminology](https://docs.aws.amazon.com/translate/latest/dg/creating-custom-terminology.html)).

### Batch translation jobs

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `start_batch_translation(input_s3_uri, output_s3_uri, data_access_role_arn, job_name, source_language, target_languages, terminology_names, parallel_data_names, client_token)` | Called `HeadBucket` on the input and output buckets and `ListObjectsV2` (`MaxKeys=1`) on the input prefix, then `StartTextTranslationJob` with `ContentType` fixed to `text/plain`. Accepted `parallel_data_names` and `client_token` but never sent them. Returned the job ID and a fixed status of `SUBMITTED`. | `call_boto3(service_name="translate", operation_name="StartTextTranslationJob", params={"JobName": ..., "InputDataConfig": {"S3Uri": ..., "ContentType": ...}, "OutputDataConfig": {"S3Uri": ...}, "DataAccessRoleArn": ..., "SourceLanguageCode": ..., "TargetLanguageCodes": [...], "TerminologyNames": [...], "ParallelDataNames": [...]})` |
| `trigger_batch_translation(input_s3_uri, output_s3_uri, data_access_role_arn, job_name, source_language, target_languages, terminology_names, content_type)` | Checked each language pair against `ListLanguages` and each terminology name against the first 50 from `ListTerminologies`, ran the same S3 checks, called `StartTextTranslationJob` with the given `content_type`, then `DescribeTextTranslationJob` for the first status | `run_script` combining `StartTextTranslationJob` and `DescribeTextTranslationJob`; add `ListLanguages`, `ListTerminologies` or `HeadBucket` calls first if you want the same checks |
| `get_translation_job(job_id)` | Called `DescribeTextTranslationJob` and returned the name, status, input and output S3 URIs, content type, submitted and end times, and the job's `Message` when it failed or completed with errors. `progress` was a guess from the status (0, 50 or 100), and the `JobDetails` document counts were dropped. | `call_boto3(service_name="translate", operation_name="DescribeTextTranslationJob", params={"JobId": ...})` |
| `list_translation_jobs(max_results, status_filter, next_token)` | Called `ListTextTranslationJobs` with `MaxResults`, one page only. A `status_filter` was sent as `Filter={"Status": ...}`, a key the API doesn't have (it's `JobStatus`), so botocore rejected every filtered call; `COMPLETED_WITH_ERROR` and `STOP_REQUESTED` were refused even before that. `next_token` was accepted but never sent, so asking for the next page returned the first page again. | `call_boto3(service_name="translate", operation_name="ListTextTranslationJobs", params={"Filter": {"JobStatus": ...}})`, passing each response's `NextToken` back until none is returned; `Filter` also takes `JobName`, `SubmittedAfterTime` and `SubmittedBeforeTime` |
| `monitor_batch_translation(job_id, output_s3_uri, monitor_interval, max_monitoring_duration)` | Called `DescribeTextTranslationJob` every `monitor_interval` seconds (default 30) inside one tool call until the job was `COMPLETED`, `FAILED` or `STOPPED`, or `max_monitoring_duration` (default 3,600 seconds) ran out, then ran `analyze_batch_translation_errors`' S3 reads if the job had failed. `COMPLETED_WITH_ERROR` isn't in that list: in testing, a job that ended that way after 11 minutes kept the call polling until the 25-minute limit the test set, 51 checks in all, and the error analysis didn't run. | `call_boto3(service_name="translate", operation_name="DescribeTextTranslationJob", params={"JobId": ...})` each time you want the status; ask the agent to check again later |
| `analyze_batch_translation_errors(job_id, output_s3_uri)` | Called `ListObjectsV2` with `Delimiter="/"` on the output prefix to find the folder whose name contains the job ID, `ListObjectsV2` on its `details/` folder, and `GetObject` on each `.json` file there. Returned the parsed files, plus fixed suggestions picked by matching words such as `utf-8`, `format`, `permission` and `language` anywhere in the file text. In testing, a UTF-8 error also drew three language suggestions, because the file's `sourceLanguageCode` key contains `language` and the message contains `invalid`. | `run_script` combining `ListObjectsV2` and `GetObject` on the job's `details/` folder, `<output prefix>/<account ID>-TranslateText-<job ID>/details/`; each document that failed has an `auxiliaryData.error` entry with its `errorCode` and `errorMessage` (see the example below) |
| `managed_batch_translation_workflow(input_s3_uri, output_s3_uri, data_access_role_arn, job_name, source_language, target_languages, terminology_names, content_type, monitor_interval, max_monitoring_duration)` | Ran `trigger_batch_translation`'s checks and start, `monitor_batch_translation`'s polling loop, and `get_language_metrics` for each pair (the placeholder zeros), all in one tool call that stayed open until the job finished: 11.5 minutes and 24 status checks for a one-document job in testing. It stops on the same three statuses as `monitor_batch_translation`. | `run_script` with `StartTextTranslationJob`, then `DescribeTextTranslationJob` in later calls, and the S3 details read above if the job reports errors |

To find out which documents in a batch job failed and why, the agent might run:

```python
import json

prefix = "translated/123456789012-TranslateText-<job-id>/details/"
listing = await call_boto3(
    service_name="s3",
    operation_name="ListObjectsV2",
    region_name="us-east-1",
    params={"Bucket": "amzn-s3-demo-bucket", "Prefix": prefix},
)
errors = []
for obj in listing.get("Contents", []):
    got = await call_boto3(
        service_name="s3",
        operation_name="GetObject",
        region_name="us-east-1",
        params={"Bucket": "amzn-s3-demo-bucket", "Key": obj["Key"]},
    )
    details = json.loads(got["Body"])
    for doc in details["details"]:
        if "error" in doc["auxiliaryData"]:
            errors.append({"file": doc["sourceFile"], **doc["auxiliaryData"]["error"]})
result = errors
result
```

Each target language gets a `<language code>.auxiliary-translation-details.json` file in that folder (see [Getting batch translation results](https://docs.aws.amazon.com/translate/latest/dg/async-results.html)).

### In-process workflow tracking

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `list_active_workflows()` | Listed the `smart_translate_workflow` and `managed_batch_translation_workflow` calls still running in the same server process, from memory. A workflow left the list when its tool call returned. | No equivalent, because nothing keeps running between `run_script` calls. For batch jobs, `call_boto3(service_name="translate", operation_name="ListTextTranslationJobs", params={"Filter": {"JobStatus": "IN_PROGRESS"}})`. |
| `get_workflow_status(workflow_id)` | Returned one running workflow's current step, completed steps and parameters; answered `not found` once the workflow's tool call had returned | No equivalent. For a batch job, `DescribeTextTranslationJob` reports its status. |

Because `run_script` exposes the full Amazon Translate API, operations the old server never had (for example `DeleteTerminology`, `StopTextTranslationJob`, `TranslateDocument`, or `CreateParallelData`) are also available.

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION`, `AWS_DEFAULT_REGION` | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | A profile through `AWS_MCP_PROXY_PROFILES`; the proxy signs requests with the standard AWS credential chain |
| `FASTMCP_LOG_LEVEL` | Not needed; it set the old server's log level |
| `TRANSLATE_MAX_TEXT_LENGTH`, `TRANSLATE_BATCH_TIMEOUT`, `ENABLE_AUDIT_LOGGING`, `ENABLE_TRANSLATION_CACHE`, `TRANSLATE_CACHE_TTL`, `TRANSLATE_MAX_FILE_SIZE`, `TRANSLATE_ALLOWED_EXTENSIONS`, `TRANSLATE_BLOCKED_PATTERNS` | Not needed. The server read and logged these at startup, but no tool used them: the services were built with fixed defaults, such as a 10,000-character text limit. |

## What Improves

- **Terminologies can be created.** `create_terminology` and `import_terminology` sent `ImportTerminology` without its required `MergeStrategy` parameter, so botocore rejected every call before it reached Amazon Translate. Through `call_boto3`, the same call with `MergeStrategy="OVERWRITE"` created the terminology, and a `TranslateText` call that named it applied the term.
- **Terminologies can be listed.** `list_terminologies` failed with `AttributeError` whenever the account had at least one terminology. `ListTerminologies` returns them, with `LastUpdatedAt`.
- **Filtered and paged job lists.** `list_translation_jobs` failed on every `status_filter` and returned the first page again when given `next_token`. `ListTextTranslationJobs` with `Filter={"JobStatus": "COMPLETED_WITH_ERROR"}` returned the matching jobs.
- **Service error messages reach the agent.** The old server's error handler looked for the `TranslateException` class in `exceptions.py`, but its services raised the separate classes of the same names in `models.py`. Every service error came back as `"An unexpected error occurred: <class name>"`, without the message: an unknown terminology, an invalid status filter, and the missing `MergeStrategy` all looked alike. `run_script` returns the error code and message, such as `InvalidParameterValueException: The provided terminology file contains an unsupported source language (line 1), or the file format is incorrect.`
- **Real detection scores.** `DetectDominantLanguage` scored French text at 0.985 and English text at 0.996, where `detect_language` always reported 0.95, and it doesn't translate the text into English to get the answer.
- **Real usage metrics.** CloudWatch `GetMetricData` on `AWS/Translate` returned the account's successful `TranslateText` requests, `en-es` characters, and average response time for the day, where `get_language_metrics` returned 0, 0, `null` and `null`.
- **Batch job document counts.** `DescribeTextTranslationJob` returns `JobDetails` with `InputDocumentsCount`, `TranslatedDocumentsCount` and `DocumentsWithErrorsCount`, where `get_translation_job` dropped them and reported a progress guess of 0, 50 or 100.
- **The rest of the Amazon Translate API.** Translation `Settings` (formality, profanity masking, brevity), which no tool sent; any `ContentType` for `StartTextTranslationJob`, where `start_batch_translation` always sent `text/plain`; `ParallelDataNames`, which `start_batch_translation` accepted and dropped; `TSV` terminology files and multi-directional terminologies; and operations the server never exposed, such as `DeleteTerminology` and `StopTextTranslationJob`.

## Workflow Change

### Before (Amazon Translate Server)

1. Set `AWS_REGION` and `AWS_PROFILE` before starting the server
2. Translate text, or start a batch job with `managed_batch_translation_workflow` or `monitor_batch_translation` and wait while one tool call polls the job (11.5 minutes for a one-document job in testing)
3. `create_terminology` and `import_terminology` return an error on every call, and `list_terminologies` returns one as soon as a terminology exists

### After (AWS MCP Server)

1. Give the agent your Region and, for batch jobs, the S3 locations and the data access role ARN
2. Ask for a translation, a terminology, or a batch job; the agent makes the calls through `run_script`
3. For a batch job, the agent starts it, checks its status when you ask, and reads the `details` files in the output folder if any documents failed

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Local translation quality checks (`validate_translation`, and the `quality_score` in `smart_translate_workflow`) | Not available | Ask the agent to review the translation, or to translate it back into the source language with `TranslateText` and compare |
| Precomputed language pairs, each tagged with five document formats and terminology support (`list_language_pairs`) | Changed | Call `ListLanguages`; the old list paired every returned code with every other, so any two codes form a pair as before |
| Checks before starting a batch job: each language pair against `ListLanguages`, each terminology name against `ListTerminologies`, `HeadBucket` on both buckets, and a warning for an empty input prefix (`trigger_batch_translation` and `managed_batch_translation_workflow`; `start_batch_translation` ran only the S3 checks) | Not available | Ask the agent to make the same calls in the `run_script` that starts the job |
| Waiting inside one tool call until a batch job ends, with a polling history (`monitor_batch_translation`, `managed_batch_translation_workflow`) | Not available | The job keeps running in Amazon Translate; ask the agent to check it with `DescribeTextTranslationJob` later |
| Suggestions picked by matching words in a job's error files (`analyze_batch_translation_errors`) | Not available | The agent reads the `details` files (example above) and explains each `errorMessage` |
| In-process workflow tracking (`list_active_workflows`, `get_workflow_status`) | Not available | For batch jobs, `ListTextTranslationJobs` with `Filter={"JobStatus": "IN_PROGRESS"}` |
| Input checks before calling AWS: a 10,000-character text limit, the `xx` or `xx-XX` language code format, different source and target languages, and terminology name characters | Not available | Amazon Translate validates each request, and `run_script` returns the service's error code and message |
| Three retries with backoff on throttling and service errors in `TranslationService`, on top of botocore's retries | Changed | If `run_script` reports a `ThrottlingException`, ask the agent to wait and run the call again |
| Errors returned as a JSON object in the tool result instead of raised | Changed | `run_script` reports API errors in its response |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.amazon-translate-mcp-server@latest` get that final release.
- The `src/amazon-translate-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.amazon-translate-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.amazon-translate-mcp-server`
