---
slug: /
title: Welcome to AWS MCP Servers
---

import styles from '@site/src/components/ServerCards/styles.module.css';

# Welcome to AWS MCP Servers

Get started with AWS MCP Servers and learn core features.

The AWS MCP Servers are a suite of specialized MCP servers that help you get the most out of AWS, wherever you use MCP.

## What is the Model Context Protocol (MCP) and how does it work with AWS MCP Servers?

> The Model Context Protocol (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. Whether you're building an AI-powered IDE, enhancing a chat interface, or creating custom AI workflows, MCP provides a standardized way to connect LLMs with the context they need.
>
> &mdash; [Model Context Protocol README](https://github.com/modelcontextprotocol#:~:text=The%20Model%20Context,context%20they%20need.)

An MCP Server is a lightweight program that exposes specific capabilities through the standardized Model Context Protocol. Host applications (such as chatbots, IDEs, and other AI tools) have MCP clients that maintain 1:1 connections with MCP servers. Common MCP clients include agentic AI coding assistants (like Q Developer, Cline, Cursor, Windsurf) as well as chatbot applications like Claude Desktop, with more clients coming soon. MCP servers can access local data sources and remote services to provide additional context that improves the generated outputs from the models.

AWS MCP Servers use this protocol to provide AI applications access to AWS documentation, contextual guidance, and best practices. Through the standardized MCP client-server architecture, AWS capabilities become an intelligent extension of your development environment or AI application.

AWS MCP servers enable enhanced cloud-native development, infrastructure management, and development workflows—making AI-assisted cloud computing more accessible and efficient.

The Model Context Protocol is an open source project run by Anthropic, PBC. and open to contributions from the entire community. For more information on MCP, you can find further documentation [here](https://modelcontextprotocol.io/introduction)

## Why AWS MCP Servers?

MCP servers enhance the capabilities of foundation models (FMs) in several key ways:

- **Improved Output Quality**: By providing relevant information directly in the model's context, MCP servers significantly improve model responses for specialized domains like AWS services. This approach reduces hallucinations, provides more accurate technical details, enables more precise code generation, and ensures recommendations align with current AWS best practices and service capabilities.

- **Access to Latest Documentation**: FMs may not have knowledge of recent releases, APIs, or SDKs. MCP servers bridge this gap by pulling in up-to-date documentation, ensuring your AI assistant always works with the latest AWS capabilities.

- **Workflow Automation**: MCP servers convert common workflows into tools that foundation models can use directly. Whether it's CDK, Terraform, or other AWS-specific workflows, these tools enable AI assistants to perform complex tasks with greater accuracy and efficiency.

- **Specialized Domain Knowledge**: MCP servers provide deep, contextual knowledge about AWS services that might not be fully represented in foundation models' training data, enabling more accurate and helpful responses for cloud development tasks.

## Getting Started Essentials

<div style={{
  background: '#F9FAFB',
  border: '1px solid #E5E7EB',
  borderLeft: '4px solid #0078D4',
  padding: '1.25rem',
  marginBottom: '2rem',
  borderRadius: '4px',
  display: 'flex',
  alignItems: 'center',
  gap: '1rem'
}}>

  <div>
    <div style={{ fontWeight: 600, color: '#111827', marginBottom: '0.25rem' }}>New from AWS New York Summit 2025!</div>
    <div style={{ color: '#6B7280', fontSize: '0.875rem' }}>Essential MCP servers for AWS resource management</div>
  </div>
</div>

Before diving into specific AWS services, set up these fundamental MCP servers for working with AWS resources:

<div className={styles.cardGrid}>
  <a href="/mcp/servers/aws-api-mcp-server" className={styles.serverCardLink}>
    <div className={styles.serverCard} style={{ minHeight: '200px' }}>
    <div className={styles.serverCardHeader}>
      <div className={styles.serverCardIcon}>
        <img src="/mcp/assets/icons/key.svg" alt="API icon" style={{ width: '22px', height: '22px' }} />
      </div>
      <div className={styles.serverCardTitleSection}>
        <h3 className={styles.serverCardTitle}>AWS API MCP</h3>
        <div className={styles.serverCardTags}>
          <span className={styles.serverCardCategory}>Essential Setup</span>
        </div>
      </div>
    </div>
    <div className={styles.serverCardContent}>
      <p className={styles.serverCardDescription} style={{ height: 'auto', overflow: 'visible', WebkitLineClamp: 'unset' }}>
        Set up secure programmatic access to AWS services with credential management and authentication handling. Manage infrastructure, explore resources, and execute AWS operations through natural language.
      </p>
    </div>
  </div>
  </a>

  <a href="/mcp/servers/aws-knowledge-mcp-server" className={styles.serverCardLink}>
    <div className={styles.serverCard} style={{ minHeight: '200px' }}>
    <div className={styles.serverCardHeader}>
      <div className={styles.serverCardIcon}>
        <img src="/mcp/assets/icons/book-open.svg" alt="Documentation icon" style={{ width: '22px', height: '22px' }} />
      </div>
      <div className={styles.serverCardTitleSection}>
        <h3 className={styles.serverCardTitle}>AWS Knowledge MCP</h3>
        <div className={styles.serverCardTags}>
          <span className={styles.serverCardCategory}>Essential Setup</span>
        </div>
      </div>
    </div>
    <div className={styles.serverCardContent}>
      <p className={styles.serverCardDescription} style={{ height: 'auto', overflow: 'visible', WebkitLineClamp: 'unset' }}>
        An AWS-managed remote MCP server that provides instant access to up-to-date AWS docs, API references, What's New posts, Getting Started information, Builder Library, blog posts, architectural references, and contextual guidance.
      </p>
    </div>
  </div>
  </a>
</div>

## Available AWS MCP Servers

The servers are organized into these main categories:

- **📚 Documentation**: Real-time access to official AWS documentation
- **🏗️ Infrastructure & Deployment**: Build, deploy, and manage cloud infrastructure
- **🤖 AI & Machine Learning**: Enhance AI applications with knowledge retrieval and ML capabilities
- **📊 Data & Analytics**: Work with databases, caching systems, and data processing
- **🛠️ Developer Tools & Support**: Accelerate development with code analysis and testing utilities
- **📡 Integration & Messaging**: Connect systems with messaging, workflows, and location services
- **💰 Cost & Operations**: Monitor, optimize, and manage your AWS infrastructure and costs
- **🧬 Healthcare & Lifesciences**: Interact with AWS HealthAI services.

import ServerCards from '@site/src/components/ServerCards';

<ServerCards />

## When to use local vs remote MCP servers?

AWS MCP servers can be run either locally on your development machine or remotely on the cloud. Here's when to use each approach:

### Local MCP Servers
- **Development & Testing**: Perfect for local development, testing, and debugging
- **Offline Work**: Continue working when internet connectivity is limited
- **Data Privacy**: Keep sensitive data and credentials on your local machine
- **Low Latency**: Minimal network overhead for faster response times
- **Resource Control**: Direct control over server resources and configuration

### Remote MCP Servers
- **Team Collaboration**: Share consistent server configurations across your team
- **Resource Intensive Tasks**: Offload heavy processing to dedicated cloud resources
- **Always Available**: Access your MCP servers from anywhere, any device
- **Automatic Updates**: Get the latest features and security patches automatically
- **Scalability**: Easily handle varying workloads without local resource constraints

> **Note**: Some MCP servers, like AWS Knowledge MCP, are provided as fully managed services by AWS. These AWS-managed remote servers require no setup or infrastructure management on your part - just connect and start using them.

## Workflows

Each server is designed for specific use cases:

- **👨‍💻 Vibe Coding & Development**: AI coding assistants helping you build faster
- **💬 Conversational Assistants**: Customer-facing chatbots and interactive Q&A systems
- **🤖 Autonomous Background Agents**: Headless automation, ETL pipelines, and operational systems

## Use Cases for the Servers

You can use the **AWS Documentation MCP Server** to help your AI assistant research and generate up-to-date code for any AWS service, like Amazon Bedrock Inline agents. Alternatively, you could use the **CDK MCP Server** or the **Terraform MCP Server** to have your AI assistant create infrastructure-as-code implementations that use the latest APIs and follow AWS best practices. With the **Cost Analysis MCP Server**, you could ask "What would be the estimated monthly cost for this CDK project before I deploy it?" or "Can you help me understand the potential AWS service expenses for this infrastructure design?" and receive detailed cost estimations and budget planning insights. The **Valkey MCP Server** enables natural language interaction with Valkey data stores, allowing AI assistants to efficiently manage data operations through a simple conversational interface.

## Additional Resources

- [Introducing AWS MCP Servers for code assistants](https://aws.amazon.com/blogs/machine-learning/introducing-aws-mcp-servers-for-code-assistants-part-1/)
- [Vibe coding with AWS MCP Servers | AWS Show & Tell](https://www.youtube.com/watch?v=qXGQQRMrcz0)
- [Terraform MCP Server Vibe Coding](https://youtu.be/i2nBD65md0Y)
- [How to Generate AWS Architecture Diagrams Using Amazon Q CLI and MCP](https://community.aws/content/2vPiiPiBSdRalaEax2rVDtshpf3/how-to-generate-aws-architecture-diagrams-using-amazon-q-cli-and-mcp)
- [Harness the power of MCP servers with Amazon Bedrock Agents](https://aws.amazon.com/blogs/machine-learning/harness-the-power-of-mcp-servers-with-amazon-bedrock-agents/)
- [Unlocking the power of Model Context Protocol (MCP) on AWS](https://aws.amazon.com/blogs/machine-learning/unlocking-the-power-of-model-context-protocol-mcp-on-aws/)
- [Introducing AWS Serverless MCP Server: AI-powered development for modern applications](https://aws.amazon.com/blogs/compute/introducing-aws-serverless-mcp-server-ai-powered-development-for-modern-applications/)
