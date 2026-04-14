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

"""CloudWatch RUM MCP Server - Pre-built Logs Insights query templates."""


def _optional_filter(field: str, value: str | None) -> str:
    """Build an optional filter clause."""
    if value:
        return f' and {field} = "{value}"'
    return ''


def _group_by_clause(group_by: str | None) -> str:
    """Build optional group-by suffix for geo/browser/device breakdowns."""
    valid = {
        'country': 'metadata.countryCode',
        'browser': 'metadata.browserName',
        'device': 'metadata.deviceType',
        'os': 'metadata.osName',
        'page': 'metadata.pageId',
    }
    if group_by and group_by.lower() in valid:
        return f', {valid[group_by.lower()]}'
    return ''


# --- Health audit (parallel queries) ---

HEALTH_ERROR_RATE = """fields event_type
| filter event_type in ["com.amazon.rum.js_error_event", "com.amazon.rum.http_event"]
| stats count(*) as error_count by metadata.countryCode, metadata.browserName
| sort error_count desc
| limit 10"""

HEALTH_SLOWEST_PAGES = """fields metadata.pageId, event_details.duration
| filter event_type = "com.amazon.rum.performance_navigation_event"
| stats pct(event_details.duration, 90) as p90_load_ms, count(*) as loads by metadata.pageId
| sort p90_load_ms desc
| limit 10"""

HEALTH_SESSION_ERRORS = """fields user_details.sessionId
| filter event_type in ["com.amazon.rum.js_error_event", "com.amazon.rum.http_event"]
| stats count(*) as errors by user_details.sessionId
| sort errors desc
| limit 10"""


# --- Errors ---

def errors_query(page_url: str | None = None, group_by: str | None = None) -> str:
    """Build error analysis query."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    gb = _group_by_clause(group_by)
    return f"""fields @timestamp, event_type, event_details.error_type, event_details.error_message,
  event_details.stack_trace, metadata.pageId, metadata.browserName, metadata.countryCode
| filter event_type in ["com.amazon.rum.js_error_event", "com.amazon.rum.http_event"]{extra_filter}
| stats count(*) as error_count by event_details.error_message, metadata.pageId{gb}
| sort error_count desc
| limit 50"""


# --- Performance ---

def performance_navigation_query(page_url: str | None = None) -> str:
    """Build page load performance query."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields metadata.pageId, event_details.duration
| filter event_type = "com.amazon.rum.performance_navigation_event"{extra_filter}
| stats
  pct(event_details.duration, 50) as p50_load_ms,
  pct(event_details.duration, 90) as p90_load_ms,
  pct(event_details.duration, 99) as p99_load_ms,
  count(*) as page_loads
  by metadata.pageId
| sort p90_load_ms desc
| limit 25"""


def performance_web_vitals_query(page_url: str | None = None) -> str:
    """Build Web Vitals query (LCP, FID, CLS, INP)."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields event_type, event_details.value, metadata.pageId
| filter event_type in [
    "com.amazon.rum.largest_contentful_paint_event",
    "com.amazon.rum.first_input_delay_event",
    "com.amazon.rum.cumulative_layout_shift_event",
    "com.amazon.rum.interaction_to_next_paint_event"
  ]{extra_filter}
| stats
  pct(event_details.value, 50) as p50,
  pct(event_details.value, 90) as p90,
  pct(event_details.value, 99) as p99,
  count(*) as samples
  by event_type, metadata.pageId
| sort event_type, p90 desc"""


# --- Sessions ---

SESSIONS_QUERY = """fields user_details.sessionId, metadata.browserName, metadata.osName,
  metadata.deviceType, metadata.countryCode
| stats
  min(@timestamp) as session_start,
  max(@timestamp) as session_end,
  count(*) as event_count
  by user_details.sessionId, metadata.browserName, metadata.osName, metadata.deviceType
| sort session_start desc
| limit 50"""


# --- Page views ---

PAGE_VIEWS_QUERY = """fields metadata.pageId, metadata.title
| filter event_type = "com.amazon.rum.page_view_event"
| stats count(*) as view_count by metadata.pageId, metadata.title
| sort view_count desc
| limit 25"""


# --- Anomaly / patterns ---

TOP_PATTERNS_QUERY = """pattern @message
| sort @sampleCount desc
| limit 5"""

ERROR_PATTERNS_QUERY = """fields @timestamp, @message
| filter @message like /(?i)(error|exception|fail|timeout|fatal)/
| pattern @message
| limit 5"""


# --- Mobile (validated against 194722437489 rum-mobile-datagen-android) ---

MOBILE_CRASHES_ANDROID = """fields @timestamp, eventName, scope.name,
  attributes.exception.type, attributes.exception.message, attributes.exception.stacktrace,
  attributes.session.id, attributes.screen.name, attributes.thread.name,
  resource.attributes.device.model.name, resource.attributes.os.version
| filter scope.name = "io.opentelemetry.crash"
| stats count(*) as crash_count by attributes.exception.type, attributes.exception.message
| sort crash_count desc
| limit 25"""

MOBILE_CRASHES_IOS = """fields @timestamp, scope.name,
  attributes.type, attributes.message, attributes.stacktrace,
  attributes.session.id, attributes.screen.name
| filter scope.name like /software.amazon.opentelemetry.(crash|hang)/
| stats count(*) as crash_count by attributes.type, attributes.message
| sort crash_count desc
| limit 25"""

MOBILE_APP_LAUNCHES_ANDROID = """fields @timestamp, name, attributes.start.type, durationNano,
  attributes.activity.name, attributes.session.id,
  resource.attributes.device.model.name, resource.attributes.os.version
| filter name = "AppStart"
| stats
  pct(durationNano / 1000000, 50) as p50_ms,
  pct(durationNano / 1000000, 90) as p90_ms,
  pct(durationNano / 1000000, 99) as p99_ms,
  count(*) as launches
  by attributes.start.type
| sort attributes.start.type"""

MOBILE_APP_LAUNCHES_IOS = """fields @timestamp, name, attributes.launch.type, durationNano,
  attributes.session.id
| filter name = "AppStart" and scope.name = "software.amazon.opentelemetry.AppStart"
| stats
  pct(durationNano / 1000000, 50) as p50_ms,
  pct(durationNano / 1000000, 90) as p90_ms,
  pct(durationNano / 1000000, 99) as p99_ms,
  count(*) as launches
  by attributes.launch.type
| sort attributes.launch.type"""


# --- Correlation ---

def trace_ids_for_page_query(page_url: str) -> str:
    """Find X-Ray trace IDs from slow pages."""
    return f"""fields event_details.trace_id, metadata.pageId, event_details.duration
| filter event_type = "com.amazon.rum.xray_trace_event" and metadata.pageId = "{page_url}"
| sort event_details.duration desc
| limit 20"""
