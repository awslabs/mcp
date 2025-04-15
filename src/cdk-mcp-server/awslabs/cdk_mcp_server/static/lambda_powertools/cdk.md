# CDK Integration

## Lambda Layer Requirement

> **CRITICAL**: Lambda Powertools libraries are NOT included in the default Lambda runtime. You MUST create a Lambda layer to include these dependencies. Use the **LambdaLayerDocumentationProvider** tool for comprehensive guidance:
>
> ```
> LambdaLayerDocumentationProvider(layer_type="python")
> ```

## Basic Implementation

```typescript
import * as path from "path";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import { Runtime, Tracing } from "aws-cdk-lib/aws-lambda";
import { PythonLayerVersion } from "@aws-cdk/aws-lambda-python-alpha";

// Create Lambda layer for Powertools
const powertoolsLayer = new PythonLayerVersion(this, "PowertoolsLayer", {
  entry: path.join(__dirname, '../layers/powertools'),  // Directory with requirements.txt
  compatibleRuntimes: [Runtime.PYTHON_3_13],
  description: "Lambda Powertools for Python",
});

// Create Lambda function with Powertools
const myFunction = new PythonFunction(this, 'MyFunction', {
  entry: path.join(__dirname, '../src/my_function'),
  runtime: Runtime.PYTHON_3_13,
  layers: [powertoolsLayer],  // Attach the Powertools layer
  tracing: Tracing.ACTIVE,    // Enable X-Ray tracing
  environment: {
    POWERTOOLS_SERVICE_NAME: "my-service",
    POWERTOOLS_METRICS_NAMESPACE: "MyService",
    LOG_LEVEL: "INFO",
  },
});
```

## Best Practices

- **Always use language-specific function constructs** instead of the generic Function construct
- **Create a dedicated Lambda layer** for Powertools dependencies
- **Enable X-Ray tracing** by setting `tracing: Tracing.ACTIVE`
- **Configure Powertools environment variables** for consistent naming

## Feature-Specific Resources

For implementation details of specific features, refer to:
- `lambda-powertools://logging`
- `lambda-powertools://metrics`
- `lambda-powertools://tracing`
- `lambda-powertools://bedrock`
