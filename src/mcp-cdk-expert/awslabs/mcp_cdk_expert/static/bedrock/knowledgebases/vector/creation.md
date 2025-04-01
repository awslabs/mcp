# Vector Knowledge Base Properties

| Name | Type | Required | Description |
|---|---|---|---|
| embeddingsModel | BedrockFoundationModel | Yes | The embeddings model for the knowledge base |
| name | string | No | The name of the knowledge base |
| vectorType | VectorType | No | The vector type to store vector embeddings |
| description | string | No | The description of the knowledge base |
| instruction | string | No | Instructions for agents based on the design and type of information of the Knowledge Base that will impact how Agents interact with the Knowledge Base |
| existingRole | iam.IRole | No | Existing IAM role with a policy statement granting permission to invoke the specific embeddings model |
| indexName | string | No | The name of the vector index (only applicable if vectorStore is of type VectorCollection) |
| vectorField | string | No | The name of the field in the vector index (only applicable if vectorStore is of type VectorCollection) |
| vectorStore | VectorCollection \| PineconeVectorStore \| AmazonAuroraVectorStore \| ExistingAmazonAuroraVectorStore | No | The vector store for the knowledge base |
| vectorIndex | VectorIndex | No | The vector index for the OpenSearch Serverless backed knowledge base |
| knowledgeBaseState | string | No | Specifies whether to use the knowledge base or not when sending an InvokeAgent request |
| tags | Record<string, string> | No | Tag (KEY-VALUE) bedrock agent resource |


### Vector Knowledge Base - Vector Type

The data type for the vectors when using a model to convert text into vector embeddings. Embeddings type may impact the availability of some embeddings models and vector stores. The following vector types are available:

- Floating point: More precise vector representation of the text, but more costly in storage.
- Binary: Not as precise vector representation of the text, but not as costly in storage as a standard floating-point (float32). Not all embedding models and vector stores support binary embeddings

See [Supported embeddings models](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-supported.html) for information on the available models and their vector data types.

#### Example

##### Typescript

```ts
const app = new cdk.App();
const stack = new cdk.Stack(app, 'aws-cdk-bedrock-data-sources-integ-test');

const kb = new VectorKnowledgeBase(stack, 'MyKnowledgeBase', {
  name: 'MyKnowledgeBase',
  vectorType: bedrock.VectorType.BINARY,
  embeddingsModel: BedrockFoundationModel.COHERE_EMBED_MULTILINGUAL_V3,
});
```

##### Python

```python

from aws_cdk import (
    aws_s3 as s3,
)
from cdklabs.generative_ai_cdk_constructs import (
    bedrock
)

kb = bedrock.VectorKnowledgeBase(self, 'KnowledgeBase',
    name= 'MyKnowledgeBase',
    vector_type= bedrock.VectorType.BINARY,
    embeddings_model= bedrock.BedrockFoundationModel.COHERE_EMBED_MULTILINGUAL_V3,
)
```

### Vector Knowledge Base - Data Sources

Data sources are the various repositories or systems from which information is extracted and ingested into the
knowledge base. These sources provide the raw content that will be processed, indexed, and made available for
querying within the knowledge base system. Data sources can include various types of systems such as document
management systems, databases, file storage systems, and content management platforms. Suuported Data Sources
include Amazon S3 buckets, Web Crawlers, SharePoint sites, Salesforce instances, and Confluence spaces.

- **Amazon S3**. You can either create a new data source using the `bedrock.S3DataSource(..)` class, or using the
  `kb.addS3DataSource(..)`.
- **Web Crawler**. You can either create a new data source using the `bedrock.WebCrawlerDataSource(..)` class, or using the
  `kb.addWebCrawlerDataSource(..)`.
- **Confluence**. You can either create a new data source using the `bedrock.ConfluenceDataSource(..)` class, or using the
  `kb.addConfluenceDataSource(..)`.
- **SharePoint**. You can either create a new data source using the `bedrock.SharePointDataSource(..)` class, or using the
  `kb.addSharePointDataSource(..)`.
- **Salesforce**. You can either create a new data source using the `bedrock.SalesforceDataSource(..)` class, or using the
  `kb.addSalesforceDataSource(..)`.
- **Custom**. You can either create a new data source using the `bedrock.CustomDataSource(..)` class, or using the
  `kb.addCustomDataSource(..)`. This allows you to add your own custom data source to the knowledge base.
