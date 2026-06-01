---
id: "GENPERF04-BP01"
title: "Test vector store features for latency and relevant performance"
pillar: "Performance Efficiency"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genperf04-bp01.html"
---

# GENPERF04-BP01 Test vector store features for latency and relevant performance

Optimizing a data retrieval system for generative AI may have
more to do with data architecture and meta-data than the
foundation model selected. This best practice encourages high
data quality and data architecture to accelerate data-driven
generative AI workloads.

**Desired outcome:** When
implemented, this best practice facilitates expedient data
storage and access, with accurate and relevant data retrieval.

**Benefits of establishing this best
practice:**
[Consider
mechanical sympathy](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf-dp.html) - Optimizing a data storage system
for a generative AI workload can be as simple as changing vector
indexes or modifying the chunking strategy. Familiarize yourself
with how the system performs data storage and retrieval to best
optimize the database.

**Level of risk exposed if this best
practice is not established:** Medium

## Implementation guidance

Optimizing vector store features for generative AI requires a
holistic approach to search architecture. Begin with effective
chunking and embedding strategies, as these have greater
effects on performance and can only be addressed before data
enters the data store. There are several popular chunking
strategies to select from, including fixed-size, hierarchical,
or semantic. Some vector base solutions like Amazon Bedrock
allow for custom chunking strategies that can be defined with
an AWS Lambda function. There are several factors to consider
when selecting a chunking strategy, including the data being
chunked and how that data is to be retrieved. Evaluate the
available options when configuring a vector store, testing
document retrieval performance against each chunking strategy.

Search algorithms form the backbone of how vectors are
retrieved from vector stores. When selecting an approximate
nearest neighbor (ANN) algorithm, consider the trade-offs
between accuracy, speed, memory usage, and scalability. Common
options include locality-sensitive hashing (LSH) for fast
indexing, hierarchical navigable small world (HNSW) for high
accuracy, inverted file index (IVF) for balance, and product
quantization (PQ) for compact storage. Benchmark multiple
algorithms with your specific dataset to find the optimal
balance based on your prioritized performance metrics.

Organize indices hierarchically, with top-level indices for
general information and lower-level indices for detailed data.
This approach generally outperforms single indices.

For search optimization in AI-driven queries, focus on
machine-to-machine interactions. Implement query expansion
using AI-generated context, and shift fuzzy matching towards
semantic similarity. Leverage hybrid search approaches that
combine semantic understanding with traditional retrieval
techniques to enhance result relevance.

Continually monitor performance across all system components,
including embedding generation, index construction, query
processing, and result retrieval. Track latency, throughput,
and resource utilization. Prepare for scenarios where
performance bottlenecks may shift between layers as your
system scales and usage patterns change. You may have to
re-architect elements of your data storage solution based on
shifting usage patterns. Develop operational runbooks to
facilitate such changes.

Maintain data quality through regular assessments of
freshness, accuracy, and representativeness. Monitor for data
drift and implement processes for continuous data ingestion
and periodic re-embedding. Use automated checks, human review,
and AI output analysis to maintain data quality. Establish
clear governance policies, and maintain version control of
your vector store.

Remember that optimizations in one area can affect the entire
system. Stay adaptable to new techniques and algorithms to
maintain a high-performing, efficient knowledge retrieval
system that delivers accurate, contextually relevant
information for your generative AI application.

### Implementation steps

- Identify the most important performance KPI for this
workload (for example, accuracy, speed, memory usage, or
scalability). Consider implementing a custom search
algorithm that supports this KPI.
- Organize indices based on a hierarchy, where more detail
is introduced towards the bottom of the hierarchy.
- Establish query latency monitoring on the data retrieval
system to verify the database latency is consistently
monitored and alerted upon.
- Perform regular data quality checks, verifying that data
is assessed for quality before being placed into a
database.
- Develop an operational runbook to facilitate rapid
architecture changes to accommodate shifting usage
patterns.
- Develop an operational runbook to facilitate rapid
architecture changes to accommodate shifting usage
patterns.

## Resources

**Related best practices:**

- PERF05-BP02
- PERF05-BP03

**Related documents:**

- [Working
with vector search collections](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-vector-search.html)
- [Vector
search features and limits](https://docs.aws.amazon.com/memorydb/latest/devguide/vector-search-limits.html)

**Related examples:**

- [Accelerate
performance using a custom chunking mechanism with Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/accelerate-performance-using-a-custom-chunking-mechanism-with-amazon-bedrock/)
- [Amazon Bedrock Knowledge Bases now supports advanced parsing, chunking, and query reformulation giving greater control of accuracy in RAG based applications](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-knowledge-bases-now-supports-advanced-parsing-chunking-and-query-reformulation-giving-greater-control-of-accuracy-in-rag-based-applications/)
- [Amazon OpenSearch Service's vector database capabilities
explained](https://aws.amazon.com/blogs/big-data/amazon-opensearch-services-vector-database-capabilities-explained/)
- [Building
scalable, secure, and reliable RAG applications using Amazon Bedrock Knowledge Bases](https://aws.amazon.com/blogs/machine-learning/building-scalable-secure-and-reliable-rag-applications-using-amazon-bedrock-knowledge-bases/)
- [Dive
deep into vector data stores using Amazon Bedrock Knowledge
Bases](https://aws.amazon.com/blogs/machine-learning/dive-deep-into-vector-data-stores-using-amazon-bedrock-knowledge-bases/)
