---
id: "GENCOST04-BP01"
title: "Reduce vector length on embedded tokens"
pillar: "Cost Optimization"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gencost04-bp01.html"
---

# GENCOST04-BP01 Reduce vector length on embedded tokens

Using a smaller vector size for data embeddings results in a reduced
response length for data-driven generative AI workflows. By keeping
vector lengths small, we can save on model output as well as vector
database computation requirements.

**Desired outcome:** A reduced total
cost of ownership for embeddings and data-driven generative AI
workflows.

**Benefits of establishing this best
practice:**

- [Measure
overall efficiency](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - Vector stores introduce a new
component for cost optimization into a generative AI
application. By increasing the efficiency of a vector store, you
also optimize the cost of running your application.
- [Analyze
and attribute expenditure](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - Reducing vector length can
help to lower the costs attributed to a vector store.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Consider using a smaller vector when embedding documents into a
vector store. The vector size hyperparameter specifies the size of
the resulting vector when embedding unstructured data. A smaller
resulting vector implies the embedding model will generate fewer
tokens on output, thus resulting in a reduced cost to embed
documents. This approach may result in less performant data
retrieval, so using a smaller vector should be done deliberately
with the cost-performance trade-off in mind.

Alternatively, some embedding models feature compressed vector
types. Compressed vector types are smaller than uncompressed
vectors, further reducing the cost of inference for search and
embedding tasks. Consider this element when selecting an embedding
model, as not all embedding models support compressed vectors.

### Implementation steps

- Identify the smallest vector length supported by the
selected embedding foundation model.
- Embed data using the smallest vector length.

You may have to modify the chunk size of the document or
introduce overlapping chunks to maintain high relevance
on output.

- Perform latency and load testing on your data retrieval workloads to verify that model response quality is still sufficient.
- Re-test with increased vector size or modified document chunking strategy to improve model response quality.

In some cases, changing the search algorithm may improve model response quality as well.

## Resources

**Related best practices:**

- COST08-BP01
- COST08-BP02
- COST08-BP03

**Related documents:**

- [AWS re:Invent 2023
- Prompt Engineering Best Practices for LLMs on Amazon Bedrock
(AIM377)](https://www.youtube.com/watch?v=jlqgGkh1wzY)

**Related examples:**

- [Amazon Bedrock Prompt Management is now Available in GA](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-prompt-management-is-now-available-in-ga/)
