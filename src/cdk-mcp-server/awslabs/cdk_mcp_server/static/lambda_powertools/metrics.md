# Metrics

Collect quantitative data about your application's behavior:

```python
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="payment-service")
tracer = Tracer(service="payment-service")
metrics = Metrics(namespace="PaymentService", service="payment-service")

@metrics.log_metrics  # Automatically emits metrics at the end of the function
def lambda_handler(event, context: LambdaContext):
    payment_id = event.get("payment_id")
    amount = event.get("amount", 0)

    try:
        # Record business metrics
        metrics.add_metric(name="PaymentProcessed", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="PaymentAmount", unit=MetricUnit.Dollars, value=amount)

        # Add dimensions for filtering
        metrics.add_dimension(name="PaymentMethod", value="credit_card")

        # Your business logic here
        result = process_payment(payment_id, amount)

        # Record successful outcome
        metrics.add_metric(name="SuccessfulPayment", unit=MetricUnit.Count, value=1)

        return result
    except Exception:
        # Record failed outcome
        metrics.add_metric(name="FailedPayment", unit=MetricUnit.Count, value=1)
        logger.exception("Payment processing failed")
        raise
```

## Key Benefits

- **Business-relevant metrics**: Track metrics that matter to your business
- **Automatic cold start metrics**: Monitor cold start frequency
- **Dimensional metrics**: Filter metrics by business dimensions
- **Efficient batching**: Metrics are batched and emitted in a single call
- **Standard units**: Use predefined units for consistent measurement

## Best Practices

1. **Initialize the metrics once**: Create the metrics object as a global variable
2. **Use the @metrics.log_metrics decorator**: This automatically emits metrics at the end of the function
3. **Add business dimensions**: Use add_dimension to enable filtering by business context
4. **Use appropriate metric units**: Choose from the predefined MetricUnit enum values
5. **Track both success and failure metrics**: Record metrics for both outcomes
6. **Use consistent naming**: Follow a consistent naming convention for metrics

## CDK Integration

> **REMINDER**: Lambda Powertools requires a Lambda layer. See `lambda-powertools://cdk` for CDK integration details.

For CloudWatch dashboard integration and other CDK-specific guidance, refer to `lambda-powertools://cdk`.
