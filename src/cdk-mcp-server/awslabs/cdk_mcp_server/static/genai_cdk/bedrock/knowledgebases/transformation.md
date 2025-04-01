# Knowledge Base - Custom Transformation

## Overview

Custom Transformation in Amazon Bedrock is a feature that allows you to create and apply
custom processing steps to documents moving through a data source ingestion pipeline.

Custom Transformation uses AWS Lambda functions to process documents, enabling you to
perform custom operations such as data extraction, normalization, or enrichment. To
create a custom transformation, set the `customTransformation` in a data source as below.

## Example

### TypeScript

```ts
CustomTransformation.lambda({
  lambdaFunction: lambdaFunction,
  s3BucketUri: `s3://${bucket.bucketName}/chunk-processor/`,
}),
```

### Python

```python
CustomTransformation.lambda_(
  lambda_function= function,
  s3_bucket_uri= f's3://{docBucket.bucket_name}/chunk-processor/'
)
```
