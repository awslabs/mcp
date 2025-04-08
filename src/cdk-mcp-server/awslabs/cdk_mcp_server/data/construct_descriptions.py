# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

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
