# Kendra Knowledge Base

## Overview

With Amazon Bedrock Knowledge Bases, you can build a knowledge base from an Amazon Kendra GenAI index to create more sophisticated and accurate Retrieval Augmented Generation (RAG)-powered digital assistants. By combining an Amazon Kendra GenAI index with Amazon Bedrock Knowledge Bases, you can:

- Reuse your indexed content across multiple Amazon Bedrock applications without rebuilding indexes or re-ingesting data.
- Leverage the advanced GenAI capabilities of Amazon Bedrock while benefiting from the high-accuracy information retrieval of Amazon Kendra.
- Customize your digital assistant's behavior using the tools of Amazon Bedrock while maintaining the semantic accuracy of an Amazon Kendra GenAI index.

## Kendra Knowledge Base Properties

| Name | Type | Required | Description |
|------|------|----------|-------------|
| kendraIndex | IKendraGenAiIndex | Yes | The Kendra Index to use for the knowledge base. |
| name | string | No | The name of the knowledge base. If not provided, a name will be auto-generated. |
| description | string | No | Description of the knowledge base. |
| instruction | string | No | Instructions for the knowledge base. |
| existingRole | iam.IRole | No | An existing IAM role to use for the knowledge base. If not provided, a new role will be created. |

## Example

### TypeScript

```ts
import * as s3 from 'aws-cdk-lib/aws-s3';
import { bedrock, kendra } from '@cdklabs/generative-ai-cdk-constructs';

const cmk = new kms.Key(stack, 'cmk', {});

// you can create a new index using the api below
const index = new kendra.KendraGenAiIndex(this, 'index', {
  name: 'kendra-index-cdk',
  kmsKey: cmk,
  documentCapacityUnits: 1, // 40K documents
  queryCapacityUnits: 1,    // 0.2 QPS
});

// or import an existing one
const index = kendra.KendraGenAiIndex.fromAttrs(this, 'myindex', {
  indexId: 'myindex',
  role: myRole
});

new bedrock.KendraKnowledgeBase(this, 'kb', {
  name: 'kendra-kb-cdk',
  kendraIndex: index,
});
```

### Python

```py
from aws_cdk import aws_kms as kms
from cdklabs.generative_ai_cdk_constructs import bedrock, kendra

# Create a KMS key
cmk = kms.Key(stack, 'cmk')

# Create a new Kendra index
index = kendra.KendraGenAiIndex(self, 'index',
    name='kendra-index-cdk',
    kms_key=cmk,
    document_capacity_units=1,  # 40K documents
    query_capacity_units=1      # 0.2 QPS
)

# Or import an existing index
index = kendra.KendraGenAiIndex.from_attrs(self, 'myindex',
    index_id='myindex',
    role=my_role
)

# Create a Kendra Knowledge Base
kb = bedrock.KendraKnowledgeBase(self, 'kb',
    name='kendra-kb-cdk',
    kendra_index=index
)
```

[View full documentation](https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/cdk-lib/bedrock/README.md)
