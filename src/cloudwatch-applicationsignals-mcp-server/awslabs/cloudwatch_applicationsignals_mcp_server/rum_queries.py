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
    return f"""fields @timestamp, event_type, metadata.pageId, metadata.browserName, metadata.countryCode,
  event_details.type, event_details.message, event_details.filename,
  event_details.request.url, event_details.response.status
| filter event_type in ["com.amazon.rum.js_error_event", "com.amazon.rum.http_event"]{extra_filter}
| stats count(*) as error_count by coalesce(event_details.message, event_details.request.url) as error_key, event_type, metadata.pageId{gb}
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



# --- Time series ---


def errors_timeseries_query(bucket: str = '1h', page_url: str | None = None) -> str:
    """Error count over time."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields event_type
| filter event_type in ["com.amazon.rum.js_error_event", "com.amazon.rum.http_event"]{extra_filter}
| stats count(*) as error_count by bin({bucket}) as time_bucket, event_type
| sort time_bucket asc"""


def performance_timeseries_query(bucket: str = '1h', page_url: str | None = None) -> str:
    """Page load time over time."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields event_details.duration
| filter event_type = "com.amazon.rum.performance_navigation_event"{extra_filter}
| stats pct(event_details.duration, 50) as p50_ms, pct(event_details.duration, 90) as p90_ms, count(*) as loads by bin({bucket}) as time_bucket
| sort time_bucket asc"""


def sessions_timeseries_query(bucket: str = '1h') -> str:
    """Session count over time."""
    return f"""fields user_details.sessionId
| filter event_type = "com.amazon.rum.session_start_event"
| stats count(*) as session_count by bin({bucket}) as time_bucket
| sort time_bucket asc"""


# --- Geo / Locations ---


def geo_sessions_query(page_url: str | None = None) -> str:
    """Session and error counts by country."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields metadata.countryCode, metadata.subdivisionCode, event_type
| filter metadata.countryCode != ""{extra_filter}
| stats count(*) as event_count,
  count_distinct(user_details.sessionId) as sessions,
  sum(event_type = "com.amazon.rum.js_error_event" or event_type = "com.amazon.rum.http_event") as errors
  by metadata.countryCode
| sort sessions desc
| limit 50"""


def geo_performance_query(page_url: str | None = None) -> str:
    """Page load time by country."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields metadata.countryCode, event_details.duration
| filter event_type = "com.amazon.rum.performance_navigation_event" and metadata.countryCode != ""{extra_filter}
| stats pct(event_details.duration, 50) as p50_ms, pct(event_details.duration, 90) as p90_ms, count(*) as loads by metadata.countryCode
| sort p90_ms desc
| limit 50"""


# --- HTTP Requests ---


def http_requests_query(page_url: str | None = None) -> str:
    """Top HTTP requests by URL with latency and status."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields event_details.request.url, event_details.request.method,
  event_details.response.status, event_details.duration
| filter event_type = "com.amazon.rum.http_event"{extra_filter}
| stats count(*) as request_count,
  pct(event_details.duration, 50) as p50_ms,
  pct(event_details.duration, 90) as p90_ms,
  sum(event_details.response.status >= 400 and event_details.response.status < 500) as http_4xx,
  sum(event_details.response.status >= 500) as http_5xx
  by event_details.request.url
| sort request_count desc
| limit 50"""


# --- Session detail ---


def session_detail_query(session_id: str) -> str:
    """All events for a single session in chronological order."""
    return f"""fields @timestamp, event_type, metadata.pageId,
  event_details.type, event_details.message, event_details.duration,
  event_details.request.url, event_details.response.status, event_details.value
| filter user_details.sessionId = "{session_id}"
| sort @timestamp asc
| limit 1000"""


# --- Resource requests ---


def resource_requests_query(page_url: str | None = None) -> str:
    """Top resource requests by duration and size."""
    extra_filter = _optional_filter('metadata.pageId', page_url)
    return f"""fields event_details.targetUrl, event_details.fileType,
  event_details.duration, event_details.transferSize
| filter event_type = "com.amazon.rum.performance_resource_event"{extra_filter}
| stats count(*) as request_count,
  pct(event_details.duration, 50) as p50_ms,
  pct(event_details.duration, 90) as p90_ms,
  avg(event_details.transferSize) as avg_bytes
  by event_details.targetUrl, event_details.fileType
| sort p90_ms desc
| limit 50"""


# --- ANRs (Android) ---

MOBILE_ANRS_ANDROID = """fields @timestamp, scope.name,
  attributes.exception.type, attributes.exception.message, attributes.exception.stacktrace,
  attributes.session.id, attributes.screen.name, attributes.thread.name,
  resource.attributes.device.model.name, resource.attributes.os.version
| filter scope.name = "io.opentelemetry.anr"
| stats count(*) as anr_count by attributes.exception.type, attributes.exception.message
| sort anr_count desc
| limit 25"""


# --- Page flows ---

PAGE_FLOWS_QUERY = """fields metadata.pageId, metadata.parentPageId
| filter event_type = "com.amazon.rum.page_view_event" and metadata.parentPageId != ""
| stats count(*) as navigation_count by metadata.parentPageId, metadata.pageId
| sort navigation_count desc
| limit 50"""

# --- Correlation ---

def trace_ids_for_page_query(page_url: str) -> str:
    """Find X-Ray trace IDs from slow pages."""
    return f"""fields event_details.trace_id, metadata.pageId, event_details.duration
| filter event_type = "com.amazon.rum.xray_trace_event" and metadata.pageId = "{page_url}"
| sort event_details.duration desc
| limit 20"""
