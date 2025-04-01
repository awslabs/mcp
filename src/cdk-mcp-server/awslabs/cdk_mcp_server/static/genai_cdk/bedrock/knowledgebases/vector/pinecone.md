#### Example of `Pinecone` (manual, you must have Pinecone vector store created):

##### TypeScript

```ts
import * as s3 from 'aws-cdk-lib/aws-s3';
import { pinecone, bedrock } from '@cdklabs/generative-ai-cdk-constructs';

const pineconeds = new pinecone.PineconeVectorStore({
  connectionString: 'https://your-index-1234567.svc.gcp-starter.pinecone.io',
  credentialsSecretArn: 'arn:aws:secretsmanager:your-region:123456789876:secret:your-key-name',
  textField: 'question',
  metadataField: 'metadata',
});

const kb = new bedrock.VectorKnowledgeBase(this, 'KnowledgeBase', {
  vectorStore: pineconeds,
  embeddingsModel: bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1,
  instruction: 'Use this knowledge base to answer questions about books. ' + 'It contains the full text of novels.',
});

const docBucket = new s3.Bucket(this, 'DocBucket');

new bedrock.S3DataSource(this, 'DataSource', {
  bucket: docBucket,
  knowledgeBase: kb,
  dataSourceName: 'books',
  chunkingStrategy: bedrock.ChunkingStrategy.FIXED_SIZE,
});
```

##### Python

```python

from aws_cdk import (
    aws_s3 as s3,
)
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    pinecone,
)

pineconevs = pinecone.PineconeVectorStore(
            connection_string='https://your-index-1234567.svc.gcp-starter.pinecone.io',
            credentials_secret_arn='arn:aws:secretsmanager:your-region:123456789876:secret:your-key-name',
            text_field='question',
            metadata_field='metadata'
        )

kb = bedrock.VectorKnowledgeBase(self, 'KnowledgeBase',
            vector_store= pineconevs,
            embeddings_model= bedrock.BedrockFoundationModel.COHERE_EMBED_ENGLISH_V3,
            instruction=  'Use this knowledge base to answer questions about books. ' +
    'It contains the full text of novels.'
        )

docBucket = s3.Bucket(self, 'DockBucket')

bedrock.S3DataSource(self, 'DataSource',
    bucket= docBucket,
    knowledge_base=kb,
    data_source_name='books',
    chunking_strategy= bedrock.ChunkingStrategy.FIXED_SIZE,
)
```
