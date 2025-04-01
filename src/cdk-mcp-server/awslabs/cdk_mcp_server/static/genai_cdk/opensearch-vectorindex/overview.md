# Amazon OpenSearch Vector Index Construct Library

## Table of contents

- [Amazon OpenSearch Vector Index Construct Library](#amazon-opensearch-vector-index-construct-library)
  - [Table of contents](#table-of-contents)
  - [API](#api)
  - [Vector Index](#vector-index)
  - [Example](#example)
    - [TypeScript](#typescript)
    - [Python](#python)
  - [Default values](#default-values)

## API

See the [API documentation](../../../apidocs/namespaces/opensearch_vectorindex/README.md).

## Vector Index

The `VectorIndex` resource connects to OpenSearch and creates an index suitable for use with Amazon Bedrock Knowledge Bases.

## Example

### TypeScript

```ts
import {
  opensearchserverless,
  opensearch_vectorindex,
} from '@cdklabs/generative-ai-cdk-constructs';

const vectorStore = new opensearchserverless.VectorCollection(
  this,
  'VectorCollection'
);

new opensearch_vectorindex.VectorIndex(this, 'VectorIndex', {
  collection: vectorStore,
  indexName: 'bedrock-knowledge-base-default-index',
  vectorField: 'bedrock-knowledge-base-default-vector',
  vectorDimensions: 1536,
  precision: 'float',
  distanceType: 'l2',
  mappings: [
    {
      mappingField: 'AMAZON_BEDROCK_TEXT_CHUNK',
      dataType: 'text',
      filterable: true,
    },
    {
      mappingField: 'AMAZON_BEDROCK_METADATA',
      dataType: 'text',
      filterable: false,
    },
  ],
  analyzer: {
    characterFilters: [opensearchserverless.CharacterFilterType.ICU_NORMALIZER],
    tokenizer: opensearchserverless.TokenizerType.KUROMOJI_TOKENIZER,
    tokenFilters: [
      opensearchserverless.TokenFilterType.KUROMOJI_BASEFORM,
      opensearchserverless.TokenFilterType.JA_STOP,
    ],
  },
});
```

### Python

```python
from cdklabs.generative_ai_cdk_constructs import (
    opensearchserverless,
    opensearch_vectorindex,
)

vectorCollection = opensearchserverless.VectorCollection(self, "VectorCollection")

vectorIndex = opensearch_vectorindex.VectorIndex(self, "VectorIndex",
    vector_dimensions= 1536,
    collection=vectorCollection,
    index_name='bedrock-knowledge-base-default-index',
    vector_field='bedrock-knowledge-base-default-vector',
    precision='float',
    distance_type='l2',
    mappings= [
        opensearch_vectorindex.MetadataManagementFieldProps(
            mapping_field='AMAZON_BEDROCK_TEXT_CHUNK',
            data_type='text',
            filterable=True
        ),
        opensearch_vectorindex.MetadataManagementFieldProps(
            mapping_field='AMAZON_BEDROCK_METADATA',
            data_type='text',
            filterable=False
        )
    ],
    analyzer=opensearchserverless.AnalyzerProps(
        character_filters=[opensearchserverless.CharacterFilterType.ICU_NORMALIZER],
        tokenizer=opensearchserverless.TokenizerType.KUROMOJI_TOKENIZER,
        token_filters=[
            opensearchserverless.TokenFilterType.KUROMOJI_BASEFORM,
            opensearchserverless.TokenFilterType.JA_STOP,
        ],
    )
)
```

## Default values

Behind the scenes, the custom resource creates a k-NN vector in the OpenSearch index, allowing to perform different kinds of k-NN search. The knn_vector field is highly configurable and can serve many different k-NN workloads. It is created as follows:

Python

```py
"properties": {
            vector_field: {
                "type": "knn_vector",
                "dimension": dimensions,
                "data_type": precision,
                "method": {
                    "engine": "faiss",
                    "space_type": distance_type,
                    "name": "hnsw",
                    "parameters": {},
                },
            },
            "id": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
        },
```

Users can currently configure the ```vector_field```, ```dimension```, ```data_type```, and ```distance_type``` fields through the construct interface.

For details on the different settings, you can refer to the [Knn plugin documentation](https://opensearch.org/docs/latest/search-plugins/knn/knn-index/).
