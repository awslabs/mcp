# CDK Integration

Integrate Lambda Powertools with CDK:

> **IMPORTANT**: When using Tracer functionality with CDK, ensure your dependency management includes the tracer extras. For Python, your package specification should use `aws-lambda-powertools[tracer]` or `aws-lambda-powertools[all]` rather than just `aws-lambda-powertools`.

```typescript
import * as path from "path";
import { Duration } from 'aws-cdk-lib';
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import { Runtime, Tracing } from "aws-cdk-lib/aws-lambda";
import { RetentionDays } from 'aws-cdk-lib/aws-logs';

// Create Lambda function with Powertools
const paymentFunction = new PythonFunction(this, 'PaymentFunction', {
  entry: path.join(__dirname, '../src/payment_function'),  // Directory containing requirements.txt
  runtime: Runtime.PYTHON_3_13,  // Always use the latest available runtime

  // Enable X-Ray tracing
  tracing: Tracing.ACTIVE,

  // Configure Powertools environment variables
  environment: {
    POWERTOOLS_SERVICE_NAME: "payment-service",
    POWERTOOLS_METRICS_NAMESPACE: "PaymentService",
    LOG_LEVEL: "INFO",
    POWERTOOLS_LOGGER_LOG_EVENT: "true",  // Log event for debugging
  },

  // Set appropriate log retention
  logRetention: RetentionDays.ONE_WEEK,
});
```

## Best Practices

- **Always use language-specific function constructs** instead of the generic Function construct
- **Enable X-Ray tracing** by setting `tracing: Tracing.ACTIVE`
- **Configure Powertools environment variables** for consistent naming
- **Set appropriate log retention** to manage CloudWatch Logs costs
- **Ensure requirements.txt includes the correct extras** (e.g., `aws-lambda-powertools[tracer]`)

## Language-Specific Function Constructs

When implementing Lambda functions with CDK, it's recommended to use language-specific constructs instead of the generic Function construct:

### PythonFunction Benefits

- **Automatic Dependency Management**: Bundles Python dependencies from requirements.txt without manual packaging
- **Proper Python Runtime Configuration**: Sets up the correct Python runtime environment with appropriate file permissions
- **Simplified Asset Bundling**: Handles asset bundling with appropriate exclusions for Python-specific files
- **Poetry/Pipenv Support**: Works with modern Python dependency management tools
- **Layer Management**: Simplifies the creation and attachment of Lambda layers

### NodeJSFunction Benefits

- **TypeScript Support**: Automatically transpiles TypeScript to JavaScript
- **Dependency Bundling**: Uses esbuild to bundle only required dependencies for smaller packages
- **Source Map Support**: Maintains source maps for easier debugging
- **Minification Options**: Provides options for code minification
- **Tree Shaking**: Eliminates unused code from the final bundle

## Example requirements.txt

For a Python Lambda function using Powertools with tracing:

```
aws-lambda-powertools[tracer]>=2.0.0
```

Or for all Powertools features:

```
aws-lambda-powertools[all]>=2.0.0
```

## Combining with Lambda Insights

For comprehensive observability, combine Lambda Powertools with Lambda Insights:

```typescript
import { LambdaInsightsVersion } from 'aws-cdk-lib/aws-lambda';

const function = new PythonFunction(this, 'MyFunction', {
  // ... other configuration

  // Enable Lambda Insights
  insightsVersion: LambdaInsightsVersion.VERSION_1_0_119_0,

  // Configure Powertools
  environment: {
    POWERTOOLS_SERVICE_NAME: "my-service",
    POWERTOOLS_METRICS_NAMESPACE: "MyService",
    // ... other environment variables
  },
});
```

This approach provides both system-level metrics (Lambda Insights) and business-level metrics (Powertools) for complete observability. See the [Lambda Insights](lambda-powertools://insights) section for more details.
