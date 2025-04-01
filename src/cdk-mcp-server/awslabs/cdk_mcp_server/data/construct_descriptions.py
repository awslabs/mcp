"""GenAI CDK construct descriptions."""

from typing import Dict


def get_construct_descriptions() -> Dict[str, str]:
    """Get a dictionary mapping construct names to their descriptions."""
    return {
        # Agent-related constructs
        'Agent_creation': 'Create and configure Bedrock Agents with foundation models, instructions, and optional features',
        'Agent_actiongroups': 'Define custom functions for Bedrock Agents to call via Lambda and OpenAPI schemas',
        'Agent_alias': 'Create versioned aliases for Bedrock Agents to manage deployment and integration',
        'Agent_collaboration': 'Configure multiple Bedrock Agents to work together on complex tasks',
        'Agent_custom_orchestration': 'Override default agent orchestration flow with custom Lambda functions',
        'Agent_prompt_override': 'Customize prompts and LLM configurations for different agent processing steps',
        # Knowledge Base constructs
        'Knowledgebases_kendra': 'Create knowledge bases from Amazon Kendra GenAI indexes for RAG applications',
        'Knowledgebases_datasources': 'Configure data sources for Bedrock Knowledge Bases including S3, web crawlers, and more',
        'Knowledgebases_parsing': 'Define strategies for processing and interpreting document contents in knowledge bases',
        'Knowledgebases_transformation': 'Apply custom processing steps to documents during knowledge base ingestion',
        'Knowledgebases_chunking': 'Configure document chunking strategies for optimal knowledge base performance',
        'Knowledgebases_vector_opensearch': 'Use OpenSearch Serverless as a vector store (vector database) for Bedrock Knowledge Bases',
        'Knowledgebases_vector_aurora': 'Use Amazon RDS Aurora PostgreSQL as a vector store (vector database) for Bedrock Knowledge Bases',
        'Knowledgebases_vector_pinecone': 'Use Pinecone as a vector store (vector database) for Bedrock Knowledge Bases',
        'Knowledgebases_vector_creation': 'Create and configure vector stores (vector databases) for Bedrock Knowledge Bases',
        # Other Bedrock constructs
        'Bedrockguardrails': 'Configure content filtering and safety guardrails for Bedrock foundation models',
        'Profiles': 'Create and manage inference profiles for tracking usage and costs across regions',
        # OpenSearch constructs
        'Opensearchserverless_overview': 'Create and configure Amazon OpenSearch Serverless for vector search applications',
        'Opensearch_vectorindex_overview': 'Configure vector indexes in Amazon OpenSearch for semantic search',
    }
