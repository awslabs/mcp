# Structured Logging

Transform text logs into JSON objects with consistent fields:

```python
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize once as a global variable
logger = Logger(service="payment-service")

@logger.inject_lambda_context  # Automatically captures request_id, cold start, etc.
def lambda_handler(event, context: LambdaContext):
    try:
        # Log with structured context
        logger.info("Processing request", extra={"event_type": event.get("type")})

        # Process request
        result = process_data(event)

        logger.info("Request processed successfully")
        return result
    except Exception:
        # Automatically captures exception details and stack trace
        logger.exception("Error processing request")
        raise
```

## Key Benefits

- **Automatic correlation IDs**: Track requests across services with consistent IDs
- **Consistent log structure**: All logs follow the same JSON structure for easier filtering
- **Cold start detection**: Automatically logs when a function is experiencing a cold start
- **Simplified exception logging**: Captures full stack traces and exception details
- **Context enrichment**: Easily add business context to your logs

## Best Practices

1. **Initialize the logger once**: Create the logger as a global variable
2. **Use the @logger.inject_lambda_context decorator**: This automatically adds request IDs and other context
3. **Add business context with extra**: Use the extra parameter to add business-relevant information
4. **Use appropriate log levels**: INFO for normal operations, WARNING for concerning events, ERROR for failures
5. **Use logger.exception for exceptions**: This automatically captures the stack trace
