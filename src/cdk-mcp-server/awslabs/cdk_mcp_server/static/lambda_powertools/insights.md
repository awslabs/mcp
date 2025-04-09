# Lambda Insights

Enhanced monitoring and observability for AWS Lambda functions:

## Overview

Lambda Insights is an extension of CloudWatch that provides system-level metrics, custom dashboards, and enhanced logging for Lambda functions. It complements Lambda Powertools by focusing on infrastructure-level monitoring rather than application-level metrics.

## Key Benefits

- **Zero-Code Instrumentation**: No code changes required to get system-level metrics
- **Memory Utilization Tracking**: Monitor memory usage patterns to optimize function configuration
- **CPU Utilization**: Identify CPU-bound functions that might benefit from more memory allocation
- **Network Usage**: Track network I/O for functions that communicate with external services
- **Cold Start Analysis**: Detailed metrics on initialization times to optimize performance
- **Automatic Dashboards**: Pre-built dashboards for quick analysis

## CDK Integration

> **REMINDER**: Lambda Powertools requires a Lambda layer. See `lambda-powertools://cdk` for details.

```typescript
import { LambdaInsightsVersion } from 'aws-cdk-lib/aws-lambda';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Runtime, Tracing } from 'aws-cdk-lib/aws-lambda';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import * as path from 'path';

// Create Lambda function with both Lambda Insights and Powertools
const myFunction = new PythonFunction(this, 'MyFunction', {
  entry: path.join(__dirname, '../src/my_function'),
  runtime: Runtime.PYTHON_3_13,

  // Attach Lambda layer (see lambda-powertools://cdk)
  layers: [powertoolsLayer],

  // Enable Lambda Insights
  insightsVersion: LambdaInsightsVersion.VERSION_1_0_119_0,

  // Enable X-Ray tracing
  tracing: Tracing.ACTIVE,

  // Configure Powertools environment variables
  environment: {
    POWERTOOLS_SERVICE_NAME: "my-service",
    POWERTOOLS_METRICS_NAMESPACE: "MyService",
    LOG_LEVEL: "INFO",
  },
});
```

## Observability Strategy

For a comprehensive observability strategy:

1. **System-Level Metrics** (Lambda Insights):
   - Memory utilization
   - CPU utilization
   - Network I/O
   - Cold start duration
   - Initialization times

2. **Business-Level Metrics** (Lambda Powertools):
   - Business transactions
   - User actions
   - Domain-specific events
   - Custom application metrics

## Cost Considerations

Lambda Insights incurs additional costs:
- $0.20 per function per month (prorated hourly)
- Additional CloudWatch costs for metrics and logs

For cost optimization:
- Enable Lambda Insights selectively on critical functions
- Consider using different CloudWatch log retention periods
- Monitor usage and adjust as needed

## Best Practices

1. **Enable on Critical Functions**: Start by enabling Lambda Insights on your most critical functions
2. **Review Dashboards Regularly**: Check the Lambda Insights dashboards to identify optimization opportunities
3. **Right-Size Memory**: Use memory utilization data to adjust function memory configuration
4. **Analyze Cold Starts**: Identify functions with high cold start times for optimization
5. **Combine with Powertools**: Use both solutions for complete observability
