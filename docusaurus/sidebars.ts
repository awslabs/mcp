import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  mainSidebar: [
    {
      type: 'category',
      label: 'Get Started',
      collapsed: false,
      items: ['intro', 'installation', 'vibe_coding'],
    },
    {
      type: 'category',
      label: 'Available AWS MCP Servers',
      collapsed: false,
      items: [
        {
          type: 'category',
          label: 'Getting Started',
          items: [
            'servers/aws-api-mcp-server',
            'servers/aws-knowledge-mcp-server',
          ],
        },
        {
          type: 'category',
          label: 'Documentation',
          items: ['servers/aws-documentation-mcp-server'],
        },
        {
          type: 'category',
          label: 'Infrastructure & Deployment',
          items: [
            'servers/ccapi-mcp-server',
            'servers/cdk-mcp-server',
            'servers/cfn-mcp-server',
            'servers/terraform-mcp-server',
            'servers/eks-mcp-server',
            'servers/ecs-mcp-server',
            'servers/finch-mcp-server',
            'servers/lambda-tool-mcp-server',
            'servers/stepfunctions-tool-mcp-server',
            'servers/aws-serverless-mcp-server',
            'servers/aws-support-mcp-server',
          ],
        },
        {
          type: 'category',
          label: 'AI & Machine Learning',
          items: [
            'servers/bedrock-kb-retrieval-mcp-server',
            'servers/amazon-rekognition-mcp-server',
            'servers/amazon-qindex-mcp-server',
            'servers/amazon-qbusiness-anonymous-mcp-server',
            'servers/nova-canvas-mcp-server',
          ],
        },
        {
          type: 'category',
          label: 'Data & Analytics',
          items: [
            'servers/documentdb-mcp-server',
            'servers/dynamodb-mcp-server',
            'servers/elasticache-mcp-server',
            'servers/valkey-mcp-server',
            'servers/memcached-mcp-server',
            'servers/timestream-for-influxdb-mcp-server',
            'servers/amazon-keyspaces-mcp-server',
            'servers/amazon-neptune-mcp-server',
            'servers/aurora-dsql-mcp-server',
            'servers/mysql-mcp-server',
            'servers/postgres-mcp-server',
            'servers/aws-dataprocessing-mcp-server',
            'servers/redshift-mcp-server',
            'servers/s3-tables-mcp-server',
          ],
        },
        {
          type: 'category',
          label: 'Developer Tools & Support',
          items: [
            'servers/core-mcp-server',
            'servers/git-repo-research-mcp-server',
            'servers/openapi-mcp-server',
            'servers/aws-diagram-mcp-server',
            'servers/prometheus-mcp-server',
            'servers/code-doc-gen-mcp-server',
            'servers/frontend-mcp-server',
            'servers/iam-mcp-server',
            'servers/kendra-index-mcp-server',
            'servers/syntheticdata-mcp-server',
            'servers/aws-bedrock-data-automation-mcp-server',
            'servers/aws-location-mcp-server',
            'servers/aws-msk-mcp-server',
          ],
        },
        {
          type: 'category',
          label: 'Integration & Messaging',
          items: [
            'servers/amazon-mq-mcp-server',
            'servers/amazon-sns-sqs-mcp-server',
          ],
        },
        {
          type: 'category',
          label: 'Cost & Operations',
          items: [
            'servers/aws-pricing-mcp-server',
            'servers/cost-explorer-mcp-server',
            'servers/cloudwatch-mcp-server',
            'servers/cloudwatch-appsignals-mcp-server',
          ],
        },
        {
          type: 'category',
          label: 'Healthcare & Lifesciences',
          items: ['servers/aws-healthomics-mcp-server'],
        },
      ],
    },
    {
      type: 'category',
      label: 'Samples',
      collapsed: false,
      items: [
        'samples/mcp-integration-with-kb',
        'samples/mcp-integration-with-nova-canvas',
        'samples/stepfunctions-tool-mcp-server',
      ],
    },
  ],
};

export default sidebars;
