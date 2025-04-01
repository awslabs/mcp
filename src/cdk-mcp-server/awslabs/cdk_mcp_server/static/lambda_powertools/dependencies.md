# Dependencies

When using Lambda Powertools features, use the appropriate extras syntax to ensure all required dependencies are included:

```bash
# For tracing only
pip install "aws-lambda-powertools[tracer]"

# For validation and parser features
pip install "aws-lambda-powertools[validation]"

# For all features
pip install "aws-lambda-powertools[all]"
```

This approach ensures that all required dependencies (like aws_xray_sdk for tracing) are automatically included without having to specify them individually.

## Why Extras Are Important

Since version 2.0.0 of Lambda Powertools, the package has been optimized to reduce its size by making certain dependencies optional. This means:

1. The base package (`aws-lambda-powertools`) does not include all dependencies
2. Features like Tracer require additional dependencies (e.g., `aws_xray_sdk`)
3. Using extras ensures you get the right dependencies for the features you use

## Available Extras

| Extra | Description | Key Dependencies |
|-------|-------------|-----------------|
| `tracer` | For X-Ray tracing | `aws_xray_sdk` |
| `validation` | For event validation | `pydantic` |
| `parser` | For event parsing | `pydantic` |
| `all` | All features | All dependencies |

## In requirements.txt

For CDK deployments, make sure your dependency management system uses these extras specifications rather than just the base package:

```
# For specific features
aws-lambda-powertools[tracer]>=2.0.0

# OR for all features
aws-lambda-powertools[all]>=2.0.0
```
