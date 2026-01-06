# CloudWatch Application Signals MCP Server

An MCP (Model Context Protocol) server that provides comprehensive tools for monitoring and analyzing AWS services using [AWS Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html).

This server enables AI assistants like Kiro, Claude, and GitHub Copilot to help you monitor service health, analyze performance metrics, track SLO compliance, and investigate issues using distributed tracing with advanced audit capabilities and root cause analysis.

## Key Features

1. **Comprehensive Service Auditing** - Monitor overall service health, diagnose root causes, and recommend actionable fixes with built-in APM expertise
2. **Advanced SLO Compliance Monitoring** - Track Service Level Objectives with breach detection and root cause analysis
3. **Operation-Level Performance Analysis** - Deep dive into specific API endpoints and operations
4. **100% Trace Visibility** - Query OpenTelemetry spans data via Transaction Search for complete observability
5. **Multi-Service Analysis** - Audit multiple services simultaneously with automatic batching
6. **Natural Language Insights** - Generate business insights from telemetry data through natural language queries

## Prerequisites

1. [Sign-Up for an AWS account](https://aws.amazon.com/free/?trk=78b916d7-7c94-4cab-98d9-0ce5e648dd5f&sc_channel=ps&ef_id=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB:G:s&s_kwcid=AL!4422!3!432339156162!e!!g!!aws%20sign%20up!9572385111!102212379327&gad_campaignid=9572385111&gbraid=0AAAAADjHtp99c5A9DUyUaUQVhVEoi8of3&gclid=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB)
2. [Enable Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html) for your applications
3. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
4. Install Python using `uv python install 3.10`

## Available Tools

### Enablement & Setup Tools

#### 1. **`get_enablement_guide`** - Application Signals Enablement Assistant
**Enable observability through AI-guided autonomous code modifications**

Use this tool to enable AWS Application Signals through agentic enablement. The tool returns a curated guide that the AI agent follows to autonomously make necessary code changes to your IaC, Dockerfiles, and dependency files. The guide is customized for your service platform (EC2, ECS, Lambda, EKS) and programming language (Python, Node.js, Java).

**Prerequisites:**
- **Enable Start Discovery** in your AWS account and region before using this tool
  - This is a one-time setup that creates the **AWSServiceRoleForCloudWatchApplicationSignals** service-linked role
  - Navigate to CloudWatch console → Services → "Start discovering your Services" → Enable Application Signals
  - See the [enablement guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html) for detailed steps

**How it works:**
- Returns a curated enablement guide as a prompt for the AI agent
- The AI agent follows the guide to autonomously modify your code
- The guide also serves as knowledge you can ask follow-up questions about
- Supports interactive Q&A throughout the enablement process

**When to use this tool:**
- Enable observability, monitoring, or Application Signals for your AWS service
- Set up automatic instrumentation for your application on AWS
- Instrument your service running on EC2, ECS, Lambda, or EKS
- Add tracing, metrics, or telemetry to your AWS application

**Requirements:**
- Write permissions to IaC files, Dockerfiles, and dependency files
- Platform must be one of: `ec2`, `ecs`, `lambda`, `eks`
- Language must be one of: `python`, `nodejs`, `java`

**Recommendations:**
- Use absolute paths for both IaC and application directories (less ambiguous for AI agents)
- Provide both directory paths in your initial prompt for faster enablement

**Best Practice Prompts:**

Good prompts (specific and complete):
```
"Enable Application Signals for my Python service running on ECS.
My app code is in /home/user/myapp and IaC is in /home/user/myapp/infrastructure"

"I want to add observability to my Node.js Lambda function.
The Lambda code is at /Users/dev/checkout-service and
the CDK infrastructure is at /Users/dev/checkout-service/cdk"

"Help me instrument my Java application on EC2 with Application Signals.
Application directory: /opt/apps/payment-api
Terraform code: /opt/apps/payment-api/terraform"
```

Less effective prompts:
```
"Enable monitoring for my app"
→ Missing: platform, language, paths

"Enable Application Signals. My code is in ./src and IaC is in ./infrastructure"
→ Problem: Relative paths instead of absolute paths

"Enable Application Signals for my ECS service at /home/user/myapp"
→ Missing: programming language
```

Quick template:
```
"Enable Application Signals for my [LANGUAGE] service on [PLATFORM].
App code: [ABSOLUTE_PATH_TO_APP]
IaC code: [ABSOLUTE_PATH_TO_IAC]"
```

### 🥇 Primary Audit Tools (Use These First)

#### 1. **`audit_services`** ⭐ **PRIMARY SERVICE AUDIT TOOL**
**The #1 tool for comprehensive AWS service health auditing and monitoring**

- **USE THIS FIRST** for all service-level auditing tasks
- Comprehensive health assessment with actionable insights and recommendations
- Multi-service analysis with automatic batching (audit 1-100+ services simultaneously)
- SLO compliance monitoring with automatic breach detection
- Root cause analysis with traces, logs, and metrics correlation
- Issue prioritization by severity (critical, warning, info findings)
- **Wildcard Pattern Support**: Use `*payment*` for automatic service discovery
- Performance optimized for fast execution across multiple targets

**Key Use Cases:**
- `audit_services(service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]')` - Audit all services
- `audit_services(service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]')` - Audit payment services
- `audit_services(..., auditors="all")` - Comprehensive root cause analysis with all auditors

#### 2. **`audit_slos`** ⭐ **PRIMARY SLO AUDIT TOOL**
**The #1 tool for comprehensive SLO compliance monitoring and breach analysis**

- **PREFERRED TOOL** for SLO root cause analysis after using `get_slo()`
- Much more comprehensive than individual trace tools - provides integrated analysis
- Combines traces, logs, metrics, and dependencies in a single audit
- Automatic SLO breach detection with prioritized findings
- **Wildcard Pattern Support**: Use `*payment*` for automatic SLO discovery
- Actionable recommendations based on multi-dimensional analysis

**Key Use Cases:**
- `audit_slos(slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]')` - Audit all SLOs
- `audit_slos(..., auditors="all")` - Comprehensive root cause analysis for SLO breaches

#### 3. **`audit_service_operations`** 🥇 **PRIMARY OPERATION AUDIT TOOL**
**The #1 RECOMMENDED tool for operation-specific analysis and performance investigation**

- **PREFERRED OVER audit_services()** for operation-level auditing
- Precision targeting of exact operation behavior vs. service-wide averages
- Actionable insights with specific error traces and dependency failures
- Code-level detail with exact stack traces and timeout locations
- **Wildcard Pattern Support**: Use `*GET*` for specific operation types
- Focused analysis that eliminates noise from other operations

**Key Use Cases:**
- `audit_service_operations(operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]')` - Audit GET operations in payment services
- `audit_service_operations(..., auditors="all")` - Root cause analysis for specific operations

### 📊 Service Discovery & Information Tools

#### 4. **`list_monitored_services`** - Service Discovery Tool
**OPTIONAL TOOL** - `audit_services()` can automatically discover services using wildcard patterns

- Get detailed overview of all monitored services in your environment
- Discover specific service names and environments for manual audit target construction
- **RECOMMENDED**: Use `audit_services()` with wildcard patterns instead for comprehensive discovery AND analysis

#### 5. **`get_service_detail`** - Service Metadata Tool
**For basic service metadata and configuration details**

- Service metadata and configuration (platform information, key attributes)
- Service-level metrics (Latency, Error, Fault aggregates)
- Log groups associated with the service
- **IMPORTANT**: This tool does NOT provide operation names - use `audit_services()` for operation discovery

#### 6. **`list_service_operations`** - Operation Discovery Tool
**CRITICAL LIMITATION**: Only discovers operations that have been ACTIVELY INVOKED in the specified time window

- Basic operation inventory for RECENTLY ACTIVE operations only (max 24 hours)
- Empty results ≠ no operations exist, just no recent invocations
- **RECOMMENDED**: Use `audit_services()` FIRST for comprehensive operation discovery and analysis

### 🎯 SLO Management Tools

#### 7. **`get_slo`** - SLO Configuration Details
**Essential for understanding SLO configuration before deep investigation**

- Comprehensive SLO configuration details (metrics, thresholds, goals)
- Operation names and key attributes for further investigation
- Metric type (LATENCY or AVAILABILITY) and comparison operators
- **NEXT STEP**: Use `audit_slos()` with `auditors="all"` for root cause analysis

#### 8. **`list_slos`** - SLO Discovery
**List all Service Level Objectives in Application Signals**

- Complete list of all SLOs in your account with names and ARNs
- Filter SLOs by service attributes
- Basic SLO information including creation time and operation names
- Useful for SLO discovery and finding SLO names for use with other tools

### 📈 Metrics & Performance Tools

#### 9. **`query_service_metrics`** - CloudWatch Metrics Analysis
**Get CloudWatch metrics for specific Application Signals services**

- Analyze service performance (latency, throughput, error rates)
- View trends over time with both standard statistics and percentiles
- Automatic granularity adjustment based on time range
- Summary statistics with recent data points and timestamps

### 🔍 Advanced Trace & Log Analysis Tools

#### 10. **`search_transaction_spans`** - 100% Trace Visibility
**Query OpenTelemetry Spans data via Transaction Search (100% sampled data)**

- **100% sampled data** vs X-Ray's 5% sampling for more accurate results
- Query "aws/spans" log group with CloudWatch Logs Insights
- Generate business performance insights and summaries
- **IMPORTANT**: Always include a limit in queries to prevent overwhelming context

**Example Query:**
```
FILTER attributes.aws.local.service = "payment-service" and attributes.aws.local.environment = "eks:production"
| STATS avg(duration) as avg_latency by attributes.aws.local.operation
| LIMIT 50
```

#### 11. **`query_sampled_traces`** - X-Ray Trace Analysis (Secondary Tool)
**Query AWS X-Ray traces (5% sampled data) for trace investigation**

- **⚠️ IMPORTANT**: Consider using `audit_slos()` with `auditors="all"` instead for comprehensive root cause analysis
- Uses X-Ray's 5% sampled trace data - may miss critical errors
- Limited context compared to comprehensive audit tools
- **RECOMMENDATION**: Use `get_service_detail()` for operation discovery and `audit_slos()` for root cause analysis

**Common Filter Expressions:**
- `service("service-name"){fault = true}` - Find traces with faults (5xx errors)
- `duration > 5` - Find slow requests (over 5 seconds)
- `annotation[aws.local.operation]="GET /api/orders"` - Filter by specific operation

#### 12. **`analyze_canary_failures`** - Comprehensive Canary Failure Analysis
**Deep dive into CloudWatch Synthetics canary failures with root cause identification**

- Comprehensive canary failure analysis with deep dive into issues
- Analyze historical patterns and specific incident details
- Get comprehensive artifact analysis including logs, screenshots, and HAR files
- Receive actionable recommendations based on AWS debugging methodology
- Correlate canary failures with Application Signals telemetry data
- Identify performance degradation and availability issues across service dependencies

**Key Features:**
- **Failure Pattern Analysis**: Identifies recurring failure modes and temporal patterns
- **Artifact Deep Dive**: Analyzes canary logs, screenshots, and network traces for root causes
- **Service Correlation**: Links canary failures to upstream/downstream service issues using Application Signals
- **Performance Insights**: Detects latency spikes, fault rates, and connection issues
- **Actionable Remediation**: Provides specific steps based on AWS operational best practices
- **IAM Analysis**: Validates IAM roles and permissions for common canary access issues
- **Backend Service Integration**: Correlates canary failures with backend service errors and exceptions

**Common Use Cases:**
- Incident Response: Rapid diagnosis of canary failures during outages
- Performance Investigation: Understanding latency and availability degradation
- Dependency Analysis: Identifying which services are causing canary failures
- Historical Trending: Analyzing failure patterns over time for proactive improvements
- Root Cause Analysis: Deep dive into specific failure scenarios with full context
- Infrastructure Issues: Diagnose S3 access, VPC connectivity, and browser target problems
- Backend Service Debugging: Identify application code issues affecting canary success

#### 13. **`list_change_events`** - AWS Application Signals Change Event Query
**Query AWS Application Signals change events to correlate infrastructure and application changes with service performance issues**

This tool provides access to AWS Application Signals' change detection capabilities through two complementary APIs:
- **ListEntityEvents**: Comprehensive change history for incident investigation and root cause analysis
- **ListServiceStates**: Current service state information for status monitoring

**Key Capabilities:**
- **Change Correlation**: Link deployments, configuration changes, and infrastructure modifications to performance issues
- **Timeline Analysis**: Build accurate timelines of events leading to incidents, alarms, or SLO breaches
- **Service-Specific Filtering**: Focus on changes to specific services using Application Signals service attributes
- **Multi-Change Type Tracking**: Monitor deployment events, configuration updates, infrastructure scaling, and other modifications
- **Incident Investigation**: Essential for root cause analysis when services experience performance degradation

**API Selection Guide:**
- **comprehensive_history=True (default)**: Uses ListEntityEvents API
  - **Question it answers**: "What are the changes in my service?" - Comprehensive change history
  - **Best for**: Incident investigation, change correlation, root cause analysis, timeline reconstruction
  - **Returns**: Complete chronological list of all change events (deployments, configurations, scaling) within time range
  - **Use when**: You need to see all changes that happened and correlate them with performance issues

- **comprehensive_history=False**: Uses ListServiceStates API
  - **Question it answers**: "Has anything changed in my service?" - Current change status
  - **Best for**: Service status monitoring, checking if recent changes occurred, troubleshooting current state
  - **Returns**: Information about the last deployment and other change states of services, providing visibility into recent changes that may have affected service performance
  - **Use when**: You want to quickly check if there were recent changes without needing the full history

**Common Use Cases:**
1. **Alarm-Triggered Investigation**: "My checkout-service alarm is firing. What changed recently?"
2. **Canary Failure Analysis**: "My checkout-canary is failing. Show me recent changes that might be related."
3. **Log-Based Error Investigation**: "I'm seeing errors in payment-service logs. What deployments happened before these errors?"
4. **Service Change History**: "Show me all changes to user-authentication-service in the last 24 hours."
5. **SLO Breach Timeline**: "I had an SLO breach at 3 PM. What changes led up to it?"
6. **Deployment Impact Analysis**: "Did the 2 PM deployment cause the performance degradation?"

**Integration with Other Tools:**
- **Enhances audit_services()**: Provides change context for service health issues
- **Correlates with audit_slos()**: Links changes to SLO breach analysis
- **Supports audit_service_operations()**: Adds timeline context for operation performance investigations
- **Complements analyze_canary_failures()**: Provides deployment correlation for canary issues

#### 14. **`list_slis`** - Legacy SLI Status Report (Specialized Tool)
**Use `audit_services()` as the PRIMARY tool for service auditing**

- Basic report showing summary counts (total, healthy, breached, insufficient data)
- Simple list of breached services with SLO names
- **IMPORTANT**: `audit_services()` is the PRIMARY and PREFERRED tool for all service auditing tasks
- Only use this tool for legacy SLI status report format specifically

## Installation

### One-Click Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=applicationsignals&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-applicationsignals-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22AWS_REGION%22%3A%22%5BThe%20AWS%20region%20to%20run%20in%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=applicationsignals&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwidGltZW91dCI6NjAsImNvbW1hbmQiOiJ1dnggYXdzbGFicy5jbG91ZHdhdGNoLWFwcGxpY2F0aW9uc2lnbmFscy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6IltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwiQVdTX1JFR0lPTiI6IltUaGUgQVdTIHJlZ2lvbiB0byBydW4gaW5dIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8ifQ) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=applicationsignals&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22timeout%22%3A60%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-applicationsignals-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22AWS_REGION%22%3A%22%5BThe%20AWS%20region%20to%20run%20in%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

### Installing via `uv`

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *awslabs.cloudwatch-applicationsignals-mcp-server*.

### Installing via Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  When installing a development or unpublished server, add the `--directory` flag:

  ```json
  {
    "mcpServers": {
      "applicationsignals": {
        "command": "uvx",
        "args": ["--from", "/absolute/path/to/cloudwatch-applicationsignals-mcp-server", "awslabs.cloudwatch-applicationsignals-mcp-server"],
        "env": {
          "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
          "AWS_REGION": "[AWS Region]",
          "FASTMCP_LOG_LEVEL": "ERROR"
        }
      }
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>

  ```json
  {
    "mcpServers": {
      "applicationsignals": {
        "command": "uvx",
        "args": ["awslabs.cloudwatch-applicationsignals-mcp-server@latest"],
        "env": {
          "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
          "AWS_REGION": "[AWS Region]",
          "FASTMCP_LOG_LEVEL": "ERROR"
        }
      }
    }
  }
  ```
</details>

### Installing for Kiro

See the [Kiro IDE documentation](https://kiro.dev/docs/mcp/configuration/) or the [Kiro CLI documentation](https://kiro.dev/docs/cli/mcp/configuration/) for details.

For global configuration, edit `~/.kiro/settings/mcp.json`. For project-specific configuration, edit `.kiro/settings/mcp.json` in your project directory.

Add the following configuration to your Kiro MCP settings file:

```json
{
    "mcpServers": {
        "applicationsignals": {
            "command": "uvx",
            "args": [
                "awslabs.cloudwatch-applicationsignals-mcp-server@latest"
            ],
            "env": {
                "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
                "AWS_REGION": "[AWS Region]",
                "FASTMCP_LOG_LEVEL": "ERROR"
            },
            "disabled": false,
            "autoApprove": []
        }
    }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "applicationsignals": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.cloudwatch-applicationsignals-mcp-server@latest",
        "awslabs.cloudwatch-applicationsignals-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
        "AWS_REGION": "[AWS Region]",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Build and install docker image locally on the same host of your LLM client

1. `git clone https://github.com/awslabs/mcp.git`
2. Go to sub-directory 'src/cloudwatch-applicationsignals-mcp-server/'
3. Run 'docker build -t awslabs/cloudwatch-applicationsignals-mcp-server:latest .'

### Add or update your LLM client's config with following:
```json
{
  "mcpServers": {
    "applicationsignals": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", "${HOME}/.aws:/root/.aws:ro",
        "-e", "AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
        "-e", "AWS_REGION=[AWS Region]",
        "awslabs/cloudwatch-applicationsignals-mcp-server:latest"
      ]
    }
  }
}
```

### Debugging

You can use the MCP inspector to debug the server. For `uvx` installations:

```bash
npx @modelcontextprotocol/inspector uvx awslabs.cloudwatch-applicationsignals-mcp-server
```

Or if you've installed the package in a specific directory:

```bash
cd /path/to/cloudwatch-applicationsignals-mcp-server
npx @modelcontextprotocol/inspector uv run awslabs.cloudwatch-applicationsignals-mcp-server
```

## Usage Examples

### Example 1: Comprehensive Service Health Audit (Recommended Workflow)
```
User: "Audit the health of all my payment services"
Assistant: I'll perform a comprehensive health audit of all your payment services using the primary audit tool.

[Uses audit_services with wildcard pattern]

audit_services(
  service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]',
  auditors="slo,operation_metric"
)

Results: Found 3 payment services with the following findings:

🔴 CRITICAL FINDINGS:
• payment-api-service: SLO breach detected - Latency SLO violated (p99: 2.1s > 1.5s threshold)
• payment-processor: High error rate detected (8.2% > 5% threshold)

⚠️ WARNING FINDINGS:
• payment-gateway: Dependency timeout issues with external payment provider

✅ HEALTHY:
• payment-validator: All metrics within normal ranges

Recommendations:
1. Investigate payment-api-service latency issues - check database connection pool
2. Review payment-processor error logs for root cause analysis
3. Consider circuit breaker pattern for payment-gateway external dependencies
```

### Example 2: SLO Breach Root Cause Analysis
```
User: "I have an SLO breach for my checkout service. Can you help me investigate?"
Assistant: I'll help you investigate the SLO breach. Let me first get the SLO configuration and then perform a comprehensive root cause analysis.

[Uses get_slo to understand configuration]
[Then uses audit_slos with auditors="all" for comprehensive analysis]

audit_slos(
  slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"checkout-service-latency-slo"}}}]',
  auditors="all"
)

Root Cause Analysis Results:

🔴 SLO BREACH CONFIRMED:
• checkout-service-latency-slo: 87.3% attainment (< 95% goal)
• Breach duration: 2.5 hours
• Impact: 1,247 requests affected

🔍 ROOT CAUSE IDENTIFIED:
• Database connection pool exhaustion detected
• Trace analysis shows 95% of slow requests waiting for DB connections
• Dependency on payment-service also showing elevated latency

📊 SUPPORTING EVIDENCE:
• P99 latency: 3.2s (threshold: 2.0s)
• Error rate spike: 12% during breach period
• 15 error traces with "connection timeout" messages

🛠️ RECOMMENDED ACTIONS:
1. Increase database connection pool size from 10 to 25
2. Implement connection pool monitoring alerts
3. Review payment-service dependency performance
4. Consider implementing request queuing for high load periods
```

### Example 3: Operation-Level Performance Investigation
```
User: "The GET operations in my payment services are slow. Can you investigate?"
Assistant: I'll investigate the performance of GET operations specifically in your payment services using operation-level analysis.

[Uses audit_service_operations for precise operation targeting]

audit_service_operations(
  operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]',
  auditors="operation_metric,trace"
)

Operation Performance Analysis Results:

🎯 GET OPERATIONS ANALYZED:
• payment-api: GET /api/payments/{id} - P99: 1.8s
• payment-api: GET /api/payments/history - P99: 3.2s ⚠️
• payment-processor: GET /api/process/status - P99: 0.8s ✅

🔴 PERFORMANCE ISSUES IDENTIFIED:
• GET /api/payments/history: Consistently slow (3.2s avg)
  - Root cause: Full table scan on payments table
  - 89% of requests show database query time > 2.5s
  - Missing index on user_id + created_date columns

📈 PERFORMANCE RECOMMENDATIONS:
1. Add composite index: CREATE INDEX idx_payments_user_date ON payments(user_id, created_date)
2. Implement pagination for history endpoint (limit 50 records)
3. Consider caching for frequently accessed payment histories
4. Add query timeout protection (max 5s)

🚀 EXPECTED IMPROVEMENT:
• Estimated latency reduction: 3.2s → 0.4s (87% improvement)
• Database load reduction: ~75%
```

### Example 4: Transaction Search for 100% Trace Visibility
```
User: "I want to analyze all the errors in my checkout service from the last hour"
Assistant: I'll use Transaction Search to analyze all errors with 100% trace visibility (no sampling).

[Uses search_transaction_spans for complete trace data]

search_transaction_spans(
  log_group_name="aws/spans",
  query_string='FILTER attributes.aws.local.service = "checkout-service" and attributes.http.status_code >= 400 | STATS count() as error_count by attributes.http.status_code, attributes.aws.local.operation | SORT error_count DESC | LIMIT 20',
  start_time="2024-01-15T10:00:00Z",
  end_time="2024-01-15T11:00:00Z"
)

✅ Transaction Search Results (100% sampled data):

ERROR BREAKDOWN (Last Hour):
• HTTP 500 errors: 47 occurrences
  - POST /api/checkout/complete: 31 errors
  - POST /api/checkout/validate: 16 errors

• HTTP 404 errors: 23 occurrences
  - GET /api/checkout/{id}: 23 errors

• HTTP 503 errors: 12 occurrences
  - POST /api/checkout/payment: 12 errors

🔍 KEY INSIGHTS:
• 82 total errors out of 1,247 requests (6.6% error rate)
• Most errors (66%) in checkout completion flow
• Service unavailable errors correlate with payment service dependency

🛠️ IMMEDIATE ACTIONS NEEDED:
1. Investigate checkout completion logic for 500 errors
2. Add validation for checkout ID existence (404s)
3. Implement circuit breaker for payment service calls (503s)
```

### Example 5: Service Discovery and Overview
```
User: "What services are being monitored and what's their current health status?"
Assistant: I'll get an overview of all monitored services and their health status.

[Uses list_monitored_services for discovery, then audit_services for health analysis]

Found 8 services being monitored:

📊 SERVICE INVENTORY:
• api-gateway-service (AWS::ApiGateway::RestApi) - Production
• checkout-service (AWS::ECS::Service) - Production
• payment-api-service (AWS::ECS::Service) - Production
• payment-processor (AWS::Lambda::Function) - Production
• user-service (AWS::EKS::Service) - Production
• inventory-service (AWS::EKS::Service) - Production
• notification-lambda (AWS::Lambda::Function) - Production
• analytics-service (AWS::ECS::Service) - Production

[Then performs health audit]

🏥 HEALTH STATUS SUMMARY:
✅ HEALTHY (5 services):
• api-gateway-service: All SLOs met, low latency
• user-service: Excellent performance metrics
• inventory-service: All operations within thresholds
• notification-lambda: Fast execution, no errors
• analytics-service: Stable performance

⚠️ NEEDS ATTENTION (2 services):
• checkout-service: Elevated latency on completion operations
• payment-api-service: Intermittent timeout issues

🔴 CRITICAL (1 service):
• payment-processor: SLO breach - error rate 8.2% (threshold: 5%)

💡 RECOMMENDATIONS:
1. Focus immediate attention on payment-processor error investigation
2. Monitor checkout-service latency trends
3. Review payment-api-service timeout configurations
```

### Example 6: Canary Failure Analysis and Root Cause Investigation
```
User: "My Pet Clinic canaries are failing. Can you help me diagnose the issues?"
Assistant: I'll analyze your Pet Clinic canaries to identify the root causes of failures.

[Uses analyze_canary_failures for comprehensive canary analysis]

analyze_canary_failures(canary_name="pc-visit-vet")
analyze_canary_failures(canary_name="pc-add-visit")
analyze_canary_failures(canary_name="webapp-erorrpagecanary")

🔍 CANARY FAILURE ANALYSIS RESULTS:

🔴 CRITICAL ISSUES IDENTIFIED:

**pc-visit-vet canary:**
• Root Cause: S3 bucket access issue
• Error Pattern: Exit status 127, "No such file or directory"
• Failure Count: 5 consecutive failures
• IAM Analysis: ✅ Role exists but S3 bucket ARN patterns incorrect in policies

**pc-add-visit canary:**
• Root Cause: Selector timeout + backend service errors
• Error Pattern: 30000ms timeout waiting for UI element + MissingFormatArgumentException
• Backend Issue: Format specifier '% o' error in BedrockRuntimeV1Service.invokeTitanModel()
• Performance: 34 second average response time, 0% success rate

**webapp-erorrpagecanary:**
• Root Cause: Browser target close during selector wait
• Error Pattern: "Target closed" waiting for `#jsError` selector
• Failure Count: 5 consecutive failures with 60000ms connection timeouts

🔍 BACKEND SERVICE CORRELATION:
• MissingFormatArgumentException detected in Pet Clinic backend
• Location: org.springframework.samples.petclinic.customers.aws.BedrockRuntimeV1Service.invokeTitanModel (line 75)
• Impact: Affects multiple canaries testing Pet Clinic functionality
• 20% fault rate on GET /api/customer/diagnose/owners/{ownerId}/pets/{petId}

🛠️ RECOMMENDED ACTIONS:

**Immediate (Critical):**
1. Fix S3 bucket ARN patterns in pc-visit-vet IAM policy
2. Fix format string bug in BedrockRuntimeV1Service: change '% o' to '%s' or correct format
3. Add VPC permissions to canary IAM roles if Lambda runs in VPC

**Infrastructure (High Priority):**
4. Investigate browser target stability issues (webapp-erorrpagecanary)
5. Review canary timeout configurations - consider increasing from 30s to 60s
6. Implement circuit breaker pattern for external service dependencies

**Monitoring (Medium Priority):**
7. Add Application Signals monitoring for canary success rates
8. Set up alerts for consecutive canary failures (>3 failures)
9. Implement canary health dashboard with real-time status

🎯 EXPECTED OUTCOMES:
• S3 access fix: Immediate resolution of pc-visit-vet failures
• Backend service fix: 80%+ improvement in Pet Clinic canary success rates
• Infrastructure improvements: Reduced browser target close errors
• Enhanced monitoring: Proactive failure detection and faster resolution
```

### Example 7: Change Events Timeline Analysis
```
User: "My checkout-service alarm is firing. What changed recently?"
Assistant: I'll investigate recent changes to your checkout-service that might have triggered the alarm.

[Uses list_change_events to correlate alarm timing with recent changes]

list_change_events(
  start_time="2024-01-15T12:00:00Z",  # 6 hours before alarm
  end_time="2024-01-15T18:00:00Z",   # Current time
  service_key_attributes='{"Name": "checkout-service", "Environment": "eks:production"}'
)

🚨 **ALARM CORRELATION ANALYSIS:**

**Alarm Details:**
• Trigger Time: 15:30 UTC
• Metric: ErrorRate > 5%
• Current Value: 12.3%

**RECENT CHANGES DETECTED:**
• 14:45 UTC: DEPLOYMENT - UpdateService (checkout-service v2.1.4)
• 15:15 UTC: CONFIGURATION - UpdateTaskDefinition (memory limit increased)
• 15:25 UTC: DEPLOYMENT - UpdateService (rollback attempted)

🎯 **TIMELINE CORRELATION:**
• Deployment at 14:45 UTC
• Alarm triggered 45 minutes later (15:30 UTC)
• Rollback attempt 5 minutes before alarm (15:25 UTC)
• Suggests deployment introduced errors, rollback may be incomplete

💡 **IMMEDIATE ACTIONS:**
1. Verify rollback completion status
2. Check if v2.1.4 introduced breaking changes
3. Monitor error logs from 14:45 UTC onwards
4. Consider full rollback to previous stable version
```

### Example 8: Multi-Service Change Pattern Analysis
```
User: "Multiple services are having issues. Show me all recent changes across my environment."
Assistant: I'll analyze recent changes across your environment. Since you want to see all changes without filtering to specific services, I'll use the ListServiceStates API which provides current service state information.

[Uses list_change_events with comprehensive_history=False for environment-wide analysis]

list_change_events(
  start_time="2024-01-15T06:00:00Z",  # Last 12 hours
  end_time="2024-01-15T18:00:00Z",
  comprehensive_history=False,  # Uses ListServiceStates API - no service filtering required
  max_results=100
)

🌐 **ENVIRONMENT-WIDE CHANGE ANALYSIS:**

**SERVICE STATE SUMMARY:**
• payment-service: Recent deployment detected (v2.1.4)
• checkout-service: Configuration change detected (memory limits updated)
• user-service: Stable - no recent changes
• api-gateway: Recent scaling event detected

**RECENT CHANGE INDICATORS:**
• Services with recent deployments: 3
• Services with configuration changes: 2
• Services with scaling events: 1
• Stable services: 2

🔍 **CHANGE CORRELATION ANALYSIS:**

**Services Requiring Investigation:**
• payment-service: Last deployment may correlate with reported issues
• checkout-service: Configuration changes might be reactive to problems
• api-gateway: Scaling events suggest increased load or performance issues

💡 **RECOMMENDED NEXT STEPS:**

For detailed change history of specific problematic services, I can investigate further:
1. Get service details first: get_service_detail("payment-service")
2. Then query comprehensive change history: list_change_events() with service_key_attributes
3. Correlate specific change timing with issue onset

Would you like me to investigate the change history for any specific service in detail?
```

## Recommended Workflows

### 🎯 Primary Audit Workflow (Most Common)
1. **Start with `audit_services()`** - Use wildcard patterns for automatic service discovery
2. **Review findings summary** - Let user choose which issues to investigate further
3. **Deep dive with `auditors="all"`** - For selected services needing root cause analysis

### 🔍 SLO Investigation Workflow
1. **Use `get_slo()`** - Understand SLO configuration and thresholds
2. **Use `audit_slos()` with `auditors="all"`** - Comprehensive root cause analysis
3. **Follow actionable recommendations** - Implement suggested fixes

### ⚡ Operation Performance Workflow
1. **Use `audit_service_operations()`** - Target specific operations with precision
2. **Apply wildcard patterns** - e.g., `*GET*` for all GET operations
3. **Root cause analysis** - Use `auditors="all"` for detailed investigation

### 🔄 Change Correlation Workflow
1. **Incident Detection** - Identify when issues started (alarms, logs, canary failures)
2. **Change Timeline** - Use `list_change_events()` to identify recent changes
3. **Correlation Analysis** - Match change timing with issue onset
4. **Root Cause Validation** - Use audit tools to confirm change impact
5. **Remediation** - Rollback problematic changes or implement fixes

### 📊 Complete Observability Workflow
1. **Service Discovery** - `audit_services()` with wildcard patterns
2. **SLO Compliance** - `audit_slos()` for breach detection
3. **Operation Analysis** - `audit_service_operations()` for endpoint-specific issues
4. **Change Correlation** - `list_change_events()` for timeline analysis
5. **Trace Investigation** - `search_transaction_spans()` for 100% trace visibility

## Configuration

### Required AWS Permissions

The server requires the following AWS IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "application-signals:ListServices",
        "application-signals:GetService",
        "application-signals:ListServiceOperations",
        "application-signals:ListServiceLevelObjectives",
        "application-signals:GetServiceLevelObjective",
        "application-signals:BatchGetServiceLevelObjectiveBudgetReport",
        "application-signals:ListAuditFindings",
        "application-signals:ListEntityEvents",
        "application-signals:ListServiceStates",
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "logs:GetQueryResults",
        "logs:StartQuery",
        "logs:StopQuery",
        "logs:FilterLogEvents",
        "xray:GetTraceSummaries",
        "xray:BatchGetTraces",
        "xray:GetTraceSegmentDestination",
        "synthetics:GetCanary",
        "synthetics:GetCanaryRuns",
        "s3:GetObject",
        "s3:ListBucket",
        "iam:GetRole",
        "iam:ListAttachedRolePolicies",
        "iam:GetPolicy",
        "iam:GetPolicyVersion"
      ],
      "Resource": "*"
    }
  ]
}
```

### Environment Variables

- `AWS_PROFILE` - AWS profile name to use for authentication (defaults to `default` profile)
- `AWS_REGION` - AWS region (defaults to us-east-1)
- `MCP_CLOUDWATCH_APPLICATION_SIGNALS_LOG_LEVEL` - Logging level (defaults to INFO)
- `AUDITOR_LOG_PATH` - Path for audit log files (defaults to /tmp)

### AWS Credentials

This server uses AWS profiles for authentication. Set the `AWS_PROFILE` environment variable to use a specific profile from your `~/.aws/credentials` file.

The server will use the standard AWS credential chain via boto3, which includes:
- AWS Profile specified by `AWS_PROFILE` environment variable
- Default profile from AWS credentials file
- IAM roles when running on EC2, ECS, Lambda, etc.

### Transaction Search Configuration

For 100% trace visibility, enable AWS X-Ray Transaction Search:
1. Configure X-Ray to send traces to CloudWatch Logs
2. Set destination to 'CloudWatchLogs' with status 'ACTIVE'
3. This enables the `search_transaction_spans()` tool for complete observability

Without Transaction Search, you'll only have access to 5% sampled trace data through X-Ray.

## Development

This server is part of the AWS Labs MCP collection. For development and contribution guidelines, please see the main repository documentation.

### Running Tests

To run the comprehensive test suite that validates all use case examples and tool functionality:

```bash
cd src/cloudwatch-applicationsignals-mcp-server
python -m pytest tests/test_use_case_examples.py -v
```

This test file verifies that all use case examples in the tool documentation call the correct tools with the right parameters and target formats. It includes tests for:

- All documented use cases for `audit_services()`, `audit_slos()`, and `audit_service_operations()`
- Target format validation (service, SLO, and operation targets)
- Wildcard pattern expansion functionality
- Auditor selection for different scenarios
- JSON format validation for all documentation examples

The tests use mocked AWS clients to prevent real API calls while validating the tool logic and parameter handling.

## License

This project is licensed under the Apache License, Version 2.0. See the LICENSE file for details.
