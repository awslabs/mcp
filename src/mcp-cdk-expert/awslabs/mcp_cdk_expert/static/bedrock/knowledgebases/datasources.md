# Knowledge Base Data Sources

## Overview

This document provides examples of adding various data sources to a Knowledge Base in Amazon Bedrock.

## Example

### TypeScript

```ts
const app = new cdk.App();
const stack = new cdk.Stack(app, 'aws-cdk-bedrock-data-sources-integ-test');

const kb = new VectorKnowledgeBase(stack, 'MyKnowledgeBase', {
  name: 'MyKnowledgeBase',
  embeddingsModel: BedrockFoundationModel.COHERE_EMBED_MULTILINGUAL_V3,
});

const bucket = new Bucket(stack, 'Bucket', {});
const lambdaFunction = new Function(stack, 'MyFunction', {
  runtime: cdk.aws_lambda.Runtime.PYTHON_3_9,
  handler: 'index.handler',
  code: cdk.aws_lambda.Code.fromInline('print("Hello, World!")'),
});

const secret = new Secret(stack, 'Secret');
const key = new Key(stack, 'Key');

kb.addWebCrawlerDataSource({
  sourceUrls: ['https://docs.aws.amazon.com/'],
  chunkingStrategy: ChunkingStrategy.HIERARCHICAL_COHERE,
  customTransformation: CustomTransformation.lambda({
    lambdaFunction: lambdaFunction,
    s3BucketUri: `s3://${bucket.bucketName}/chunk-processor/`,
  }),
});

kb.addS3DataSource({
  bucket,
  chunkingStrategy: ChunkingStrategy.SEMANTIC,
  parsingStrategy: ParsingStategy.foundationModel({
    model: BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0,
  }),
});

kb.addConfluenceDataSource({
  dataSourceName: 'TestDataSource',
  authSecret: secret,
  kmsKey: key,
  confluenceUrl: 'https://example.atlassian.net',
  filters: [
    {
      objectType: ConfluenceObjectType.ATTACHMENT,
      includePatterns: ['.*\\.pdf'],
      excludePatterns: ['.*private.*\\.pdf'],
    },
    {
      objectType: ConfluenceObjectType.PAGE,
      includePatterns: ['.*public.*\\.pdf'],
      excludePatterns: ['.*confidential.*\\.pdf'],
    },
  ],
});

kb.addSalesforceDataSource({
  authSecret: secret,
  endpoint: 'https://your-instance.my.salesforce.com',
  kmsKey: key,
  filters: [
    {
      objectType: SalesforceObjectType.ATTACHMENT,
      includePatterns: ['.*\\.pdf'],
      excludePatterns: ['.*private.*\\.pdf'],
    },
    {
      objectType: SalesforceObjectType.CONTRACT,
      includePatterns: ['.*public.*\\.pdf'],
      excludePatterns: ['.*confidential.*\\.pdf'],
    },
  ],
});

kb.addSharePointDataSource({
  dataSourceName: 'SharepointDataSource',
  authSecret: secret,
  kmsKey: key,
  domain: 'yourdomain',
  siteUrls: ['https://yourdomain.sharepoint.com/sites/mysite'],
  tenantId: '888d0b57-69f1-4fb8-957f-e1f0bedf64de',
  filters: [
    {
      objectType: SharePointObjectType.PAGE,
      includePatterns: ['.*\\.pdf'],
      excludePatterns: ['.*private.*\\.pdf'],
    },
    {
      objectType: SharePointObjectType.FILE,
      includePatterns: ['.*public.*\\.pdf'],
      excludePatterns: ['.*confidential.*\\.pdf'],
    },
  ],
});

kb.addCustomDataSource({
  dataSourceName: 'CustomDataSource',
  chunkingStrategy: ChunkingStrategy.FIXED_SIZE,
});
```

### Python

```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_kms as kms
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock
)

class PythonTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        kb = bedrock.VectorKnowledgeBase(self, 'MyKnowledgeBase',
                    embeddings_model= bedrock.BedrockFoundationModel.COHERE_EMBED_MULTILINGUAL_V3,
                )

        docBucket = s3.Bucket(self, 'Bucket')

        function = _lambda.Function(self, 'MyFunction',
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler='index.handler',
            code=_lambda.Code.from_inline('print("Hello, World!")'),
        )

        kb.add_web_crawler_data_source(
            source_urls= ['https://docs.aws.amazon.com/'],
            chunking_strategy= bedrock.ChunkingStrategy.HIERARCHICAL_COHERE,
            custom_transformation= bedrock.CustomTransformation.lambda_(
                lambda_function= function,
                s3_bucket_uri= f's3://{docBucket.bucket_name}/chunk-processor/'
            )
        )

        kb.add_s3_data_source(
            bucket= docBucket,
            chunking_strategy= bedrock.ChunkingStrategy.SEMANTIC,
            parsing_strategy= bedrock.ParsingStategy.foundation_model(
                parsing_model= bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0.as_i_model(self)
            )
        )

        secret = secretsmanager.Secret(self, 'Secret')
        key = kms.Key(self, 'Key')

        kb.add_confluence_data_source(
            data_source_name='TestDataSource',
            auth_secret=secret,
            kms_key=key,
            confluence_url='https://example.atlassian.net',
            filters=[
                bedrock.ConfluenceCrawlingFilters(
                    object_type=bedrock.ConfluenceObjectType.ATTACHMENT,
                    include_patterns= [".*\\.pdf"],
                    exclude_patterns= [".*private.*\\.pdf"],
                ),
                bedrock.ConfluenceCrawlingFilters(
                    object_type=bedrock.ConfluenceObjectType.PAGE,
                    include_patterns= [".*public.*\\.pdf"],
                    exclude_patterns= [".*confidential.*\\.pdf"],
                ),
            ]
        )

        kb.add_salesforce_data_source(
            auth_secret=secret,
            endpoint='https://your-instance.my.salesforce.com',
            kms_key=key,
            filters=[
                bedrock.SalesforceCrawlingFilters(
                    object_type=bedrock.SalesforceObjectType.ATTACHMENT,
                    include_patterns= [".*\\.pdf"],
                    exclude_patterns= [".*private.*\\.pdf"],
                ),
                bedrock.SalesforceCrawlingFilters(
                    object_type=bedrock.SalesforceObjectType.CONTRACT,
                    include_patterns= [".*public.*\\.pdf"],
                    exclude_patterns= [".*confidential.*\\.pdf"],
                ),
            ]
        )

        kb.add_share_point_data_source(
            data_source_name='SharepointDataSource',
            auth_secret=secret,
            kms_key=key,
            domain='yourDomain',
            site_urls= ['https://yourdomain.sharepoint.com/sites/mysite'],
            tenant_id='888d0b57-69f1-4fb8-957f-e1f0bedf64de',
            filters=[
                bedrock.SharePointCrawlingFilters(
                    object_type=bedrock.SharePointObjectType.PAGE,
                    include_patterns= [".*\\.pdf"],
                    exclude_patterns= [".*private.*\\.pdf"],
                ),
                bedrock.SharePointCrawlingFilters(
                    object_type=bedrock.SharePointObjectType.FILE,
                    include_patterns= [".*public.*\\.pdf"],
                    exclude_patterns= [".*confidential.*\\.pdf"],
                ),
            ]
        )

        kb.add_custom_data_source(
            data_source_name='CustomDataSource',
            chunking_strategy=bedrock.ChunkingStrategy.FIXED_SIZE,
        )
```
