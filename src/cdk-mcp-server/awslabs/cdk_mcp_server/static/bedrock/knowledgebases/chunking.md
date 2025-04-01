# Vector Knowledge Base - Chunking Strategies

## Available Strategies

### Default Chunking

Applies Fixed Chunking with the default chunk size of 300 tokens and 20% overlap.

#### TypeScript

```ts
ChunkingStrategy.DEFAULT;
```

#### Python

```python
ChunkingStrategy.DEFAULT
```

### Fixed Size Chunking

This method divides the data into fixed-size chunks, with each chunk
containing a predetermined number of tokens. This strategy is useful when the data is uniform
in size and structure.

#### TypeScript

```ts
// Fixed Size Chunking with sane defaults.
ChunkingStrategy.FIXED_SIZE;

// Fixed Size Chunking with custom values.
ChunkingStrategy.fixedSize({ maxTokens: 200, overlapPercentage: 25 });
```

#### Python

```python
# Fixed Size Chunking with sane defaults.
ChunkingStrategy.FIXED_SIZE

# Fixed Size Chunking with custom values.
ChunkingStrategy.fixed_size(
  max_tokens= 200,
  overlap_percentage= 25
)
```

### Hierarchical Chunking

This strategy organizes data into layers of chunks, with the first
layer containing large chunks and the second layer containing smaller chunks derived from the first.
It is ideal for data with inherent hierarchies or nested structures.

#### TypeScript

```ts
// Hierarchical Chunking with the default for Cohere Models.
ChunkingStrategy.HIERARCHICAL_COHERE;

// Hierarchical Chunking with the default for Titan Models.
ChunkingStrategy.HIERARCHICAL_TITAN;

// Hierarchical Chunking with custom values. Tthe maximum chunk size depends on the model.
// Amazon Titan Text Embeddings: 8192. Cohere Embed models: 512
ChunkingStrategy.hierarchical({
  overlapTokens: 60,
  maxParentTokenSize: 1500,
  maxChildTokenSize: 300,
});
```

#### Python

```python
# Hierarchical Chunking with the default for Cohere Models.
ChunkingStrategy.HIERARCHICAL_COHERE

# Hierarchical Chunking with the default for Titan Models.
ChunkingStrategy.HIERARCHICAL_TITAN

# Hierarchical Chunking with custom values. Tthe maximum chunk size depends on the model.
# Amazon Titan Text Embeddings: 8192. Cohere Embed models: 512
chunking_strategy= ChunkingStrategy.hierarchical(
    overlap_tokens=60,
    max_parent_token_size=1500,
    max_child_token_size=300
)
```

### Semantic Chunking

This method splits data into smaller documents based on groups of similar
content derived from the text using natural language processing. It helps preserve contextual
relationships and ensures accurate and contextually appropriate results.

#### TypeScript

```ts
// Semantic Chunking with sane defaults.
ChunkingStrategy.SEMANTIC;

// Semantic Chunking with custom values.
ChunkingStrategy.semantic({ bufferSize: 0, breakpointPercentileThreshold: 95, maxTokens: 300 });
```

#### Python

```python
# Semantic Chunking with sane defaults.
ChunkingStrategy.SEMANTIC

# Semantic Chunking with custom values.
ChunkingStrategy.semantic(
  buffer_size=0,
  breakpoint_percentile_threshold=95,
  max_tokens=300
)
```

### No Chunking

This strategy treats each file as one chunk. If you choose this option,
you may want to pre-process your documents by splitting them into separate files.

#### TypeScript

```ts
ChunkingStrategy.NONE;
```

#### Python

```python
ChunkingStrategy.NONE
```
