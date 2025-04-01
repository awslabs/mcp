# Vector Knowledge Base - Parsing Strategy

## Overview

A parsing strategy in Amazon Bedrock is a configuration that determines how the service
processes and interprets the contents of a document. It involves converting the document's
contents into text and splitting it into smaller chunks for analysis. Amazon Bedrock offers
two parsing strategies:

### Default Parsing Strategy

This strategy converts the document's contents into text
and splits it into chunks using a predefined approach. It is suitable for most use cases
but may not be optimal for specific document types or requirements.

### Foundation Model Parsing Strategy

This strategy uses a foundation model to describe
the contents of the document. It is particularly useful for improved processing of PDF files
with tables and images. To use this strategy, set the `parsingStrategy` in a data source as below.

#### TypeScript

```ts
bedrock.ParsingStategy.foundationModel({
  model: BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0,
});
```

#### Python

```python
bedrock.ParsingStategy.foundation_model(
    parsing_model=BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0
)
```
