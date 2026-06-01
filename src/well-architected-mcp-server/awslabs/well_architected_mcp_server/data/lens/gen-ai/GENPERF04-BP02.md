---
id: "GENPERF04-BP02"
title: "Optimize vector sizes for your use case"
pillar: "Performance Efficiency"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genperf04-bp02.html"
---

# GENPERF04-BP02 Optimize vector sizes for your use case

Embedding models may offer support for different sizes of vectors
when embedding data. Optimizing the vector size for an embedding may
introduce long-term performance gains.

**Desired outcome:** When
implemented, this best practice helps verify that vector sizes are
optimized for a specific use case, which can lead to improved
performance over time.

**Benefits of establishing this best
practice:**
[Consider
mechanical sympathy](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf-dp.html) - Optimizing vector sizes for supported
vector embedding models may improve performance of your application.
Familiarize yourself with how your selected embedding model performs
embeddings and retrievals when optimizing.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

When embedding unstructured data into a vector database, it's
important to test multiple embedding models with various
vector sizes to optimize data retrieval and identify
performance trade-offs. While there's a general relationship
between vector size and accuracy within a model family, this
correlation isn't universal across all embedding models. The
performance of your embeddings depends on several factors: the
specific data you're encoding, the chosen embedding model, and
the vector size used within that model. Consider checking
popular leaderboards like
[HuggingFace's
Massive Text Embedding Benchmark (MTEB) Leaderboard](https://huggingface.co/mteb/leaderboard)
when selecting an embedding model.

Start with a more compact encoding, and increase the vector
size if warranted by your use cases to improve accuracy or
minimize loss. Consider the nature of your dataset and how
focused the topics or language are. The more narrow and deep
the content, the more likely fine-tuning is to improve
accuracy while potentially reducing vector size.

For use cases where higher latency is acceptable, larger
vector sizes within a given model may offer more accuracy and
response nuance. Conversely, for low-latency requirements,
smaller vector sizes typically result in faster retrieval.
However, it's crucial to note that a well-tuned model with
smaller dimensions (like 256) can sometimes outperform a more
generic model with larger dimensions (1024 or greater) in both
accuracy and speed.

Keep in mind that some models offer a limited range of
permissible vector dimensions. This is particularly true for
managed embedding model access through Amazon Bedrock. A wider
variety of embedding models can be incorporated into a
generative AI workflow using Amazon SageMaker AI model endpoints
or SageMaker AI JumpStart. Always test and evaluate the
performance of different models and vector sizes with your
specific dataset to find the optimal balance between accuracy
and latency for your use case.

### Implementation steps

- Identify the most important performance KPI for this
workload (like accuracy, speed, memory usage, or
scalability).
- Determine the number of vector options supported by your
selected embedding model and design experiments meant to
test each option.

Experiment on a variety of data to get a clear
determination of which embedding size is best for this
workload.
- Consider self-hosting an open-source embedding model
using Amazon SageMaker AI model endpoints if available
embedding options are not sufficient.

- Run the experiment and determine the most performant
embedding model for this scenario.

## Resources

**Related best practices:**

- [PERF03-BP01](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_data_use_purpose_built_data_store.html)
- [PERF03-BP02](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_data_evaluate_configuration_options_data_store.html)
- [PERF03-BP03](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_data_collect_record_data_store_performance_metrics.html)
- [PERF03-BP04](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_data_implement_strategies_to_improve_query_performance.html)

**Related documents:**

- [Customizing
your knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-customization.html)
- [Working
with vector search collections](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-vector-search.html)
- [Vector
search features and limits](https://docs.aws.amazon.com/memorydb/latest/devguide/vector-search-limits.html)

**Related examples:**

- [Amazon OpenSearch Service's vector database capabilities
explained](https://aws.amazon.com/blogs/big-data/amazon-opensearch-services-vector-database-capabilities-explained/)
- [Building
scalable, secure, and reliable RAG applications using Amazon Bedrock Knowledge Bases](https://aws.amazon.com/blogs/machine-learning/building-scalable-secure-and-reliable-rag-applications-using-amazon-bedrock-knowledge-bases/)
- [Dive
deep into vector data stores using Amazon Bedrock Knowledge
Bases](https://aws.amazon.com/blogs/machine-learning/dive-deep-into-vector-data-stores-using-amazon-bedrock-knowledge-bases/)

**Related tools:**

- [HuggingFace's
MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
