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
"""Gateway to the AWS application-signals API.

The single seam where dynamic-instrumentation tools touch botocore. Each
operation here issues one boto3 call, wraps any raised exception in a
``GatewayError``, and lets the caller render the failure through
``render_error``. Tool functions never import ``botocore.exceptions`` — that
contract belongs to this module.
"""

from .aws_clients import get_application_signals_client
from .error_translation import render_client_error, translate_aws_error
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, Dict, Mapping, Optional, Sequence


class GatewayError(Exception):
    """Wraps any exception raised by an application-signals call.

    The original exception is preserved on ``original_exc`` so callers can
    pass the gateway error through ``render_error`` without losing the
    botocore-specific data ``render_client_error`` needs.
    """

    def __init__(self, original_exc: BaseException):
        """Wrap ``original_exc``, preserving it for later rendering."""
        super().__init__(str(original_exc))
        self.original_exc = original_exc


def _call(method_name: str, **kwargs: Any) -> Dict[str, Any]:
    client = get_application_signals_client()
    method = getattr(client, method_name)
    try:
        return method(**kwargs)
    except (BotoCoreError, ClientError) as exc:
        # Narrow on purpose: these two cover the full botocore exception
        # surface (``ClientError`` for service-side errors, ``BotoCoreError``
        # for credentials/connection/timeout failures). Programming errors
        # (``AttributeError`` from a typo, ``TypeError`` from a bad kwarg)
        # propagate unwrapped so they surface as themselves in tracebacks
        # instead of masquerading as AWS failures.
        raise GatewayError(exc) from exc


def create_instrumentation_configuration(**kwargs: Any) -> Dict[str, Any]:
    """Call ``CreateInstrumentationConfiguration`` through the gateway."""
    return _call('create_instrumentation_configuration', **kwargs)


def list_instrumentation_configurations(**kwargs: Any) -> Dict[str, Any]:
    """Call ``ListInstrumentationConfigurations`` through the gateway."""
    return _call('list_instrumentation_configurations', **kwargs)


def get_instrumentation_configuration(**kwargs: Any) -> Dict[str, Any]:
    """Call ``GetInstrumentationConfiguration`` through the gateway."""
    return _call('get_instrumentation_configuration', **kwargs)


def delete_instrumentation_configuration(**kwargs: Any) -> Dict[str, Any]:
    """Call ``DeleteInstrumentationConfiguration`` through the gateway."""
    return _call('delete_instrumentation_configuration', **kwargs)


def batch_delete_instrumentation_configurations(**kwargs: Any) -> Dict[str, Any]:
    """Call ``BatchDeleteInstrumentationConfigurations`` through the gateway."""
    return _call('batch_delete_instrumentation_configurations', **kwargs)


def get_instrumentation_configuration_status(**kwargs: Any) -> Dict[str, Any]:
    """Call ``GetInstrumentationConfigurationStatus`` through the gateway."""
    return _call('get_instrumentation_configuration_status', **kwargs)


def render_error(
    err: GatewayError,
    *,
    action: str,
    attempted_label: str = 'ATTEMPTED PARAMETERS:',
    attempted: Optional[Mapping[str, object]] = None,
    possible_causes: Optional[Sequence[str]] = None,
    troubleshooting: Optional[Sequence[str]] = None,
    trailer: Optional[str] = None,
) -> str:
    """Render a ``GatewayError`` using the appropriate error template.

    Callers that want tailored prose for a ``ClientError`` pass
    ``possible_causes`` / ``troubleshooting`` / ``trailer``; those flow
    through ``render_client_error``. Callers that pass none of those — and
    every non-``ClientError`` exception regardless — fall through to
    ``translate_aws_error``, which carries its own canned bullets per
    exception type. This preserves the per-tool rendering contract that
    existed before tools were routed through the gateway.
    """
    exc = err.original_exc
    has_tailored_prose = bool(possible_causes or troubleshooting or trailer)
    if isinstance(exc, ClientError) and has_tailored_prose:
        return render_client_error(
            exc,
            action=action,
            attempted_label=attempted_label,
            attempted=attempted,
            possible_causes=possible_causes,
            troubleshooting=troubleshooting,
            trailer=trailer,
        )
    return translate_aws_error(exc, action=action, context=attempted)
