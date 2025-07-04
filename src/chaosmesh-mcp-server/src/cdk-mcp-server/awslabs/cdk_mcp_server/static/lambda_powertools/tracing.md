# Tracing

Gain visibility into request flows across distributed services:

> **IMPORTANT**: When using Tracer, install Powertools with the tracer extra: `aws-lambda-powertools[tracer]`. This ensures the required aws_xray_sdk dependency is included.

```python
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="payment-service")
tracer = Tracer(service="payment-service")

@tracer.capture_method
def process_payment(payment_id: str):
    # This function is automatically traced
    # Add business-relevant annotations
    tracer.put_annotation(key="PaymentId", value=payment_id)
    tracer.put_metadata(key="PaymentMethod", value="credit_card")

    # Your business logic here
    return {"status": "processed"}

@logger.inject_lambda_context
@tracer.capture_lambda_handler  # Automatically traces Lambda invocations
def lambda_handler(event, context: LambdaContext):
    payment_id = event.get("payment_id")
    logger.info("Processing payment", extra={"payment_id": payment_id})

    result = process_payment(payment_id)
    return result
```

## Key Benefits

- **End-to-end request visibility**: Track requests as they flow through your distributed system
- **Automatic instrumentation**: AWS SDK calls are automatically traced
- **Business-relevant annotations**: Add searchable annotations for business context
- **Performance metrics**: Identify bottlenecks and optimize performance
- **Error tracking**: Automatically capture and visualize errors in the trace

## Best Practices

1. **Install with the tracer extra**: Use `pip install "aws-lambda-powertools[tracer]"` to ensure aws_xray_sdk is included
2. **Initialize the tracer once**: Create the tracer as a global variable
3. **Use the @tracer.capture_lambda_handler decorator**: This automatically traces the Lambda invocation
4. **Use @tracer.capture_method for internal functions**: This provides more granular tracing
5. **Add business context with annotations**: Use put_annotation for searchable fields
6. **Add additional context with metadata**: Use put_metadata for non-searchable details
7. **Enable X-Ray tracing in your Lambda function**: Set the tracing mode to Active in your Lambda configuration

## CDK Configuration

When using CDK, ensure X-Ray tracing is enabled:

```typescript
import { Tracing } from "aws-cdk-lib/aws-lambda";

const function = new Function(this, 'MyFunction', {
  // ... other properties
  tracing: Tracing.ACTIVE,  // Enable X-Ray tracing
});
```
