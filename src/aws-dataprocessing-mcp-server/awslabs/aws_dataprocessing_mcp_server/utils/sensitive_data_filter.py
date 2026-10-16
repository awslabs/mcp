# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Field-level filtering for responses that may carry customer content.

When the server runs without ``--allow-sensitive-data-access``, operations that
return records mixing operational metadata with customer content are answered
with the metadata only, rather than refused outright. The caller still learns
what exists and what state it is in; the fields that can carry job arguments,
customer rows, or error payloads are omitted.

Filtering is allowlist based on purpose. Each record type declares the fields it
returns, and anything not named is dropped. With a denylist, any field a future
AWS API version adds would be returned by default, which is the wrong default
for a control whose job is to withhold content.

Note that an allowlist is not a guarantee about content: several retained fields
(``Name``, ``Jar``) are customer-controlled strings. The allowlists below are a
reviewed judgement about which fields are worth returning, not a proof about
what the retained values can contain.
"""

from typing import Any, Dict, List, Mapping, Tuple, Union


# An allowlist maps a field name to either True (retain as-is) or a nested
# allowlist (recurse into the dict at that key).
FieldSpec = Mapping[str, Union[bool, Mapping[str, Any]]]


# EMR on EC2 Step / StepSummary.
# Omitted: Config.Args (the spark-submit command line, which commonly carries
# --conf settings and JDBC connection strings), Config.Properties (arbitrary
# customer key/values), Status.StateChangeReason.Message and
# Status.FailureDetails (failure text that can echo query values and rows).
EMR_STEP_FIELDS: FieldSpec = {
    'Id': True,
    'Name': True,
    'ActionOnFailure': True,
    'ExecutionRoleArn': True,
    'Config': {'Jar': True, 'MainClass': True},
    'Status': {
        'State': True,
        'StateChangeReason': {'Code': True},
        'Timeline': True,
    },
}


# Glue JobRun.
# Omitted: Arguments (job arguments, which include connection settings passed to
# the job), ErrorMessage and StateDetail (failure text).
GLUE_JOB_RUN_FIELDS: FieldSpec = {
    'Id': True,
    'Attempt': True,
    'PreviousRunId': True,
    'TriggerName': True,
    'JobName': True,
    'JobMode': True,
    'JobRunState': True,
    'StartedOn': True,
    'LastModifiedOn': True,
    'CompletedOn': True,
    'PredecessorRuns': True,
    'AllocatedCapacity': True,
    'ExecutionTime': True,
    'Timeout': True,
    'MaxCapacity': True,
    'WorkerType': True,
    'NumberOfWorkers': True,
    'SecurityConfiguration': True,
    'LogGroupName': True,
    'NotificationProperty': True,
    'GlueVersion': True,
    'DPUSeconds': True,
    'ExecutionClass': True,
    'MaintenanceWindow': True,
    'ProfileName': True,
}


# Glue Statement.
# Omitted: Code (the submitted statement text), Output.Data (the execution
# result), Output.ErrorValue and Output.Traceback (error payloads that can
# contain customer rows).
GLUE_STATEMENT_FIELDS: FieldSpec = {
    'Id': True,
    'State': True,
    'Progress': True,
    'StartedOn': True,
    'CompletedOn': True,
    'Output': {
        'ExecutionCount': True,
        'Status': True,
        'ErrorName': True,
    },
}


# EMR Serverless jobRun and jobRunSummary. The two shapes differ (the summary
# uses "id" where the full record uses "jobRunId"); listing both is harmless
# because absent keys are skipped.
# Omitted: stateDetails (failure text), jobDriver (entryPointArguments and
# sparkSubmitParameters, which carry job settings), configurationOverrides
# (arbitrary customer configuration), tags (customer-controlled values).
EMR_SERVERLESS_JOB_RUN_FIELDS: FieldSpec = {
    'applicationId': True,
    'jobRunId': True,
    'id': True,
    'name': True,
    'arn': True,
    'createdBy': True,
    'createdAt': True,
    'updatedAt': True,
    'executionRole': True,
    'state': True,
    'releaseLabel': True,
    'type': True,
    'mode': True,
    'attempt': True,
    'attemptCreatedAt': True,
    'attemptUpdatedAt': True,
    'startedAt': True,
    'endedAt': True,
    'executionTimeoutMinutes': True,
    'totalExecutionDurationSeconds': True,
    'queuedDurationMilliseconds': True,
    'totalResourceUtilization': True,
    'billedResourceUtilization': True,
    'networkConfiguration': True,
    'retryPolicy': True,
}


def filter_record(
    record: Dict[str, Any], allowed: FieldSpec, _prefix: str = ''
) -> Tuple[Dict[str, Any], List[str]]:
    """Return a copy of record holding only allowlisted fields, plus what was dropped.

    Args:
        record: An AWS API record. Passed through untouched if not a dict.
        allowed: The allowlist for this record type.
        _prefix: Internal, used to build dotted paths for nested fields.

    Returns:
        A (filtered_record, omitted_paths) tuple. omitted_paths holds the dotted
        path of every field that was present in the input but not retained, so
        callers can be told what is missing rather than left to guess whether a
        field was empty or omitted.
    """
    if not isinstance(record, dict):
        return record, []

    filtered: Dict[str, Any] = {}
    omitted: List[str] = []

    for key, value in record.items():
        path = f'{_prefix}{key}'
        spec = allowed.get(key)

        if spec is True:
            filtered[key] = value
        elif isinstance(spec, Mapping) and isinstance(value, dict):
            nested, nested_omitted = filter_record(value, spec, f'{path}.')
            omitted.extend(nested_omitted)
            # Drop a container that ends up empty, so the response does not
            # advertise a key with nothing behind it.
            if nested:
                filtered[key] = nested
        else:
            omitted.append(path)

    return filtered, omitted


def filter_records(records: List[Any], allowed: FieldSpec) -> Tuple[List[Any], List[str]]:
    """Apply filter_record across a list, returning the union of omitted paths.

    Args:
        records: A list of AWS API records.
        allowed: The allowlist for the record type.

    Returns:
        A (filtered_records, omitted_paths) tuple. omitted_paths is de-duplicated
        and sorted, since per-element paths are identical in practice and the
        caller reports them once for the whole response.
    """
    filtered: List[Any] = []
    omitted: set = set()

    for record in records:
        one, one_omitted = filter_record(record, allowed)
        filtered.append(one)
        omitted.update(one_omitted)

    return filtered, sorted(omitted)


def redaction_notice(operation: str, omitted: List[str]) -> str:
    """Build the message appended to a success response when fields were withheld.

    Args:
        operation: The operation name, for the message.
        omitted: Dotted paths of the omitted fields.

    Returns:
        A sentence naming the omitted fields and the flag that returns them, or
        an empty string when nothing was omitted.
    """
    if not omitted:
        return ''
    return (
        f'Note: {operation} omitted the following fields because '
        f'--allow-sensitive-data-access is not enabled: {", ".join(omitted)}. '
        f'Enable the flag to receive them.'
    )
