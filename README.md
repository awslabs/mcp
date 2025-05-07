# AWS MCP Servers

A suite of specialized MCP servers that help you get the most out of AWS, wherever you use MCP.

[![GitHub](https://img.shields.io/badge/github-awslabs/mcp-blue.svg?style=flat&logo=github)](https://github.com/awslabs/mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Codecov](https://img.shields.io/codecov/c/github/awslabs/mcp)](https://app.codecov.io/gh/awslabs/mcp)
[![OSSF-Scorecard Score](https://img.shields.io/ossf-scorecard/github.com/awslabs/mcp)](https://scorecard.dev/viewer/?uri=github.com/awslabs/mcp)

## Table of Contents

- [What is the Model Context Protocol (MCP) and how does it work with AWS MCP Servers?](#what-is-the-model-context-protocol-mcp-and-how-does-it-work-with-aws-mcp-servers)
  - [Why MCP Servers?](#why-mcp-servers)
- [Available Servers](#available-servers)
  - [Core MCP Server](#core-mcp-server)
  - [AWS Documentation MCP Server](#aws-documentation-mcp-server)
  - [Amazon Bedrock Knowledge Bases Retrieval MCP Server](#amazon-bedrock-knowledge-bases-retrieval-mcp-server)
  - [AWS CDK MCP Server](#aws-cdk-mcp-server)
  - [Cost Analysis MCP Server](#cost-analysis-mcp-server)
  - [Amazon Nova Canvas MCP Server](#amazon-nova-canvas-mcp-server)
  - [AWS Diagram MCP Server](#aws-diagram-mcp-server)
  - [AWS Lambda MCP Server](#aws-lambda-mcp-server)
  - [AWS Terraform MCP Server](#aws-terraform-mcp-server)
  - [Git Repo Research MCP Server](#git-repo-research-mcp-server)
  - [Use Cases for the Servers](#use-cases-for-the-servers)
- [Installation and Setup](#installation-and-setup)
  - [Getting Started with Cline and Amazon Bedrock](#getting-started-with-cline-and-amazon-bedrock)
  - [Getting Started with Cursor](#getting-started-with-cursor)
  - [Getting Started with Windsurf](#getting-started-with-windsurf)
  - Getting Started with Q Developer - Coming Soon
- [Samples](#samples)
- [Documentation](#documentation)
- [Vibe coding](#vibe-coding)
- [Additional Resources](#additional-resources)
- [Security](#security)
- [Contributing](#contributing)
- [Developer guide](#developer-guide)
- [License](#license)
- [Disclaimer](#disclaimer)

## What is the Model Context Protocol (MCP) and how does it work with AWS MCP Servers?

> The Model Context Protocol (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. Whether you're building an AI-powered IDE, enhancing a chat interface, or creating custom AI workflows, MCP provides a standardized way to connect LLMs with the context they need.
>
> &mdash; [Model Context Protocol README](https://github.com/modelcontextprotocol#:~:text=The%20Model%20Context,context%20they%20need.)

An MCP Server is a lightweight program that exposes specific capabilities through the standardized Model Context Protocol. Host applications (such as chatbots, IDEs, and other AI tools) have MCP clients that maintain 1:1 connections with MCP servers. Common MCP clients includ agentic AI coding assistants (like Q Developer, Cline, Cursor, Windsurf) as well as chatbot applications like Claude Desktop, with more clients coming soon. MCP servers can access local data sources and remote services to provide additional context that improves the generated outputs from the models.

AWS MCP Servers use this protocol to provide AI applications access to AWS documentation, contextual guidance, and best practices. Through the standardized MCP client-server architecture, AWS capabilities become an intelligent extension of your development environment or AI application.

AWS MCP servers enable enhanced cloud-native development, infrastructure management, and development workflows—making AI-assisted cloud computing more accessible and efficient.

The Model Context Protocol is an open source project run by Anthropic, PBC. and open to contributions from the entire community. For more information on MCP, you can find further documentation [here](https://modelcontextprotocol.io/introduction)

### Why MCP Servers?

MCP servers enhance the capabilities of foundation models (FMs) in several key ways:

- **Improved Output Quality**: By providing relevant information directly in the model's context, MCP servers significantly improve model responses for specialized domains like AWS services. This approach reduces hallucinations, provides more accurate technical details, enables more precise code generation, and ensures recommendations align with current AWS best practices and service capabilities.

- **Access to Latest Documentation**: FMs may not have knowledge of recent releases, APIs, or SDKs. MCP servers bridge this gap by pulling in up-to-date documentation, ensuring your AI assistant always works with the latest AWS capabilities.

- **Workflow Automation**: MCP servers convert common workflows into tools that foundation models can use directly. Whether it's CDK, Terraform, or other AWS-specific workflows, these tools enable AI assistants to perform complex tasks with greater accuracy and efficiency.

- **Specialized Domain Knowledge**: MCP servers provide deep, contextual knowledge about AWS services that might not be fully represented in foundation models' training data, enabling more accurate and helpful responses for cloud development tasks.

## Available Servers

This monorepo contains the following MCP servers:

### Core MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.core-mcp-server.svg)](https://pypi.org/project/awslabs.core-mcp-server/)

A server for managing and coordinating other AWS Labs MCP servers.

- Automatic MCP Server Management
- Planning and guidance to orchestrate AWS Labs MCP Servers
- UVX Installation Support
- Centralized Configuration

[Learn more](src/core-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/core-mcp-server/)

### AWS Documentation MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.aws-documentation-mcp-server.svg)](https://pypi.org/project/awslabs.aws-documentation-mcp-server/)

A server for accessing AWS documentation and best practices.

- Search Documentation using the official AWS search API
- Get content recommendations for AWS documentation pages
- Convert documentation to markdown format

[Learn more](src/aws-documentation-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/)

### Amazon Bedrock Knowledge Bases Retrieval MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.bedrock-kb-retrieval-mcp-server.svg)](https://pypi.org/project/awslabs.bedrock-kb-retrieval-mcp-server/)

A server for accessing Amazon Bedrock Knowledge Bases.

- Discover knowledge bases and their data sources
- Query knowledge bases with natural language
- Filter results by data source
- Rerank results

[Learn more](src/bedrock-kb-retrieval-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/bedrock-kb-retrieval-mcp-server/)

### AWS CDK MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.cdk-mcp-server.svg)](https://pypi.org/project/awslabs.cdk-mcp-server/)

A server for AWS CDK best practices.

- AWS CDK project analysis and assistance
- CDK construct recommendations
- Infrastructure as Code best practices

[Learn more](src/cdk-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/cdk-mcp-server/)

### Cost Analysis MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.cost-analysis-mcp-server.svg)](https://pypi.org/project/awslabs.cost-analysis-mcp-server/)

A server for AWS Cost Analysis.

- Analyze and visualize AWS costs
- Query cost data with natural language
- Generate cost reports and insights

[Learn more](src/cost-analysis-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/cost-analysis-mcp-server/)

### Amazon Nova Canvas MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.nova-canvas-mcp-server.svg)](https://pypi.org/project/awslabs.nova-canvas-mcp-server/)

A server for generating images using Amazon Nova Canvas.

- Text-based image generation with customizable parameters
- Color-guided image generation with specific palettes
- Workspace integration for saving generated images
- AWS authentication through profiles

[Learn more](src/nova-canvas-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/nova-canvas-mcp-server/)

### AWS Diagram MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.aws-diagram-mcp-server.svg)](https://pypi.org/project/awslabs.aws-diagram-mcp-server/)

A server for seamlessly creating diagrams using the Python diagrams package DSL.

- Generate professional diagrams using Python code
- Support for AWS architecture, sequence diagrams, flow charts, and class diagrams
- Customize diagram appearance, layout, and styling
- Code scanning to ensure secure diagram generation

[Learn more](src/aws-diagram-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/aws-diagram-mcp-server/)

### AWS Lambda MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.lambda-mcp-server.svg)](https://pypi.org/project/awslabs.lambda-mcp-server/)

A server to select and run AWS Lambda function as MCP tools without code changes.

- This server acts as a bridge between MCP clients and AWS Lambda functions, allowing foundation models (FMs) to access and run Lambda functions as tools.
- This can be used, for example, to access private resources such as internal applications and databases without the need to provide public network access.
- This approach allows an MCP client to use other AWS services, private networks, and the public internet.
- The Lambda function description is used by MCP to describe the tool and should guide the FMs on when (what does the function provide?) and how (which parameters it needs? which syntax?) to use it.

[Learn more](src/lambda-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/lambda-mcp-server/)

### AWS Terraform MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.terraform-mcp-server.svg)](https://pypi.org/project/awslabs.terraform-mcp-server/)

A server for AWS Terraform best practices.

- Security-First Development Workflow
- Checkov Integration
- AWS and AWSCC Provider Documentation
- AWS-IA GenAI Modules
- Terraform Workflow Execution

[Learn more](src/terraform-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/terraform-mcp-server/)

### Git Repo Research MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.git-repo-research-mcp-server.svg)](https://pypi.org/project/awslabs.git-repo-research-mcp-server/)

A server for researching Git repositories using semantic search.

- Repository Indexing with FAISS and Amazon Bedrock embeddings
- Semantic Search within repositories
- Repository Structure Analysis
- GitHub Repository Search in AWS organizations
- File Access with text and binary support

[Learn more](src/git-repo-research-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/git-repo-research-mcp-server/)

### Use Cases for the Servers

For example, you can use the **AWS Documentation MCP Server** to help your AI assistant research and generate up-to-date code for any AWS service, like Amazon Bedrock Inline agents. Alternatively, you could use the **CDK MCP Server** or the **Terraform MCP Server** to have your AI assistant create infrastructure-as-code implementations that use the latest APIs and follow AWS best practices. With the **Cost Analysis MCP Server**, you could ask "What would be the estimated monthly cost for this CDK project before I deploy it?" or "Can you help me understand the potential AWS service expenses for this infrastructure design?" and receive detailed cost estimations and budget planning insights.

## Installation and Setup

Each server has specific installation instructions. Generally, you can:

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python using `uv python install 3.10`
3. Configure AWS credentials with access to required services
4. Add the server to your MCP client configuration

Example configuration for Amazon Q CLI MCP (`~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MCP_SETTINGS_PATH": "path to your mcp settings file"
      }
    },
    "awslabs.nova-canvas-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.nova-canvas-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cost-analysis-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-analysis-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cdk-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.lambda-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.lambda-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FUNCTION_PREFIX": "your-function-prefix",
        "FUNCTION_LIST": "your-first-function, your-second-function",
        "FUNCTION_TAG_KEY": "your-tag-key",
        "FUNCTION_TAG_VALUE": "your-tag-value"
      }
    },
    "awslabs.terraform-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.terraform-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
    },
    "awslabs.git-repo-research-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.git-repo-research-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "GITHUB_TOKEN": "your-github-token"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

See individual server READMEs for specific requirements and configuration options.

**Note about performance when using `uvx` _"@latest"_ suffix:**

Using the _"@latest"_ suffix checks and downloads the latest MCP server package from pypi every time you start your MCP clients, but it comes with a cost of increased initial load times. If you want to minimize the initial load time, remove _"@latest"_ and manage your uv cache yourself using one of these approaches:

 - `uv cache clean <tool>`: where {tool} is the mcp server you want to delete from cache and install again (e.g.: "awslabs.lambda-mcp-server") (remember to remove the '<>').
 - `uvx <tool>@latest`: this will refresh the tool with the latest version and add it to the uv cache.

### Running MCP servers in containers

_This example uses docker with the "awslabs.nova-canvas-mcp-server and can be repeated for each MCP server_

- Build and tag the image

  ```base
  cd src/nova-canvas-mcp-server
  docker build -t awslabs/nova-canvas-mcp-server .
  ```

- Optionally save sensitive environmental variables in a file:

  ```.env
  # contents of a .env file with ficticious AWS temporary credentials
  AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
  ```

- Use the docker options: `--env`, `--env-file`, and `--volume` as needed because the `"env": {}` are not available within the container.

  ```json
  {
    "mcpServers": {
      "awslabs.nova-canvas-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "AWS_REGION=us-east-1",
          "--env-file",
          "/full/path/to/.env",
          "--volume",
          "/full/path/to/.aws:/app/.aws",
          "awslabs/nova-canvas-mcp-server:latest"
        ],
        "env": {}
      }
    }
  }
  ```

### Getting Started with Cline and Amazon Bedrock
<details>
<summary>Getting Started with Cline and Amazon Bedrock</summary>

**IMPORTANT:** Following these instructions may incur costs and are subject to the [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/). You are responsible for any associated costs. In addition to selecting the desired model in the Cline settings, ensure you have your selected model (e.g. `anthropic.claude-3-7-sonnet`) also enabled in Amazon Bedrock. For more information on this, see [these AWS docs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) on enabling model access to Amazon Bedrock Foundation Models (FMs).


1. Follow the steps above in the **Installation and Setup** section to install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/), install Python, and configure AWS credentials with the required services.

2. If using Visual Studio Code, install the [Cline VS Code Extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev) (or equivalent extension for your preferred IDE). Once installed, click the extension to open it. When prompted, select the tier that you wish. In this case, we will be using Amazon Bedrock, so the free tier of Cline is fine as we will be sending requests using the Amazon Bedrock API instead of the Cline API.

<p align="center">
  <img src="./docs/images/root-readme/install-cline-extension.png" width="800" height="400"  />
<p>


3. Select the **MCP Servers** button.

<p align="center">
  <img src="./docs/images/root-readme/select-mcp-servers.png" width="500" height="800"  />
<p>

4. Select the **Installed** tab, then click **Configure MCP Servers** to open the `cline_mcp_settings.json` file.

 <p align="center">
   <img src="./docs/images/root-readme/configure-mcp-servers.png" width="500" height="800"  />
 <p>

 5. In the `cline_mcp_settings.json` file, add your desired MCP servers in the `mcpServers` object. See the following example that will use some of the current AWS MCP servers that are available in this repository. Ensure you save the file to install the MCP servers.

 #### `cline_mcp_settings.json`
 ```json
 {
   "mcpServers": {
     "awslabs.core-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.core-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     },
     "awslabs.nova-canvas-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.nova-canvas-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     },
     "awslabs.terraform-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.terraform-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
     },
    }
  }
 ```

6. Once installed, you should see a list of your MCP Servers under the MCP Server Installed tab, and they should have a green slider to show that they are enabled. See the following for an example with two of the possible AWS MCP Servers. Click **Done** when finished. You should now see the Cline chat interface.

<p align="center">
  <img src="./docs/images/root-readme/mcp-servers-installed.png" width="500" height="800"  />
<p>

<p align="center">
  <img src="./docs/images/root-readme/cline-chat-interface.png" width="500" height="800"  />
<p>


7. By default, Cline will be set as the API provider, which has limits for the free tier. Next, let’s update the API provider to be AWS Bedrock, so we can use the LLMs through Bedrock, which would have billing go through your connected AWS account.


8. Click the settings gear to open up the Cline settings. Then under **API Provider**, switch this from `Cline` to `AWS Bedrock` and select `AWS Profile` for the authentication type. As a note, the `AWS Credentials` option works as well, however it uses a static credentials (Access Key ID and Secret Access Key) instead of temporary credentials that are automatically redistributed when the token expires, so the temporary credentials with an AWS Profile is the more secure and recommended method.

<p align="center">
  <img src="./docs/images/root-readme/cline-select-bedrock.png" width="500" height="800"  />
<p>


9. Fill out the configuration based on the existing AWS Profile you wish to use, select the desired AWS Region, and enable cross-region inference.

<p align="center">
  <img src="./docs/images/root-readme/cline-select-aws-profile.png" width="500" height="800"  />
<p>


<p align="center">
  <img src="./docs/images/root-readme/cline-api-provider-filled.png" width="500" height="800"  />
<p>

10. Next, scroll down on the settings page until you reach the text box that says Custom Instructions. Paste in the following snippet to ensure the `mcp-core` server is used as the starting point for every prompt:

```
For every new project, always look at your MCP servers and use mcp-core as the starting point every time. Also after a task completion include the list of MCP servers used in the operation.
```

<p align="center">
  <img src="./docs/images/root-readme/cline-custom-instructions.png" width="500" height="800"  />
<p>


11. Once the custom prompt is pasted in, click **Done** to return to the chat interface.

12. Now you can begin asking questions and testing out the functionality of your installed AWS MCP Servers. The default option in the chat interface is is `Plan` which will provide the output for you to take manual action on (e.g. providing you a sample configuration that you copy and paste into a file). However, you can optionally toggle this to `Act` which will allow Cline to act on your behalf (e.g. searching for content using a web browser, cloning a repository, executing code, etc). You can optionally toggle on the “Auto-approve” section to avoid having to click to approve the suggestions, however we recommend leaving this off during testing, especially if you have the Act toggle selected.

**Note:** For the best results, please prompt Cline to use the desired AWS MCP Server you wish to use. For example, `Using the Terraform MCP Server, do...`
</details>

### Getting Started with Cursor
<details>
<summary>Getting Started with Cursor</summary>

1. Follow the steps above in the **Installation and Setup** section to install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/), install Python, and configure AWS credentials with the required services.

2. You can place MCP configuration in two locations, depending on your use case:

  A. **Project Configuration**
    - For tools specific to a project, create a `.cursor/mcp.json` file in your project directory.
    - This allows you to define MCP servers that are only available within that specific project.

  B. **Global Configuration**
    - For tools that you want to use across all projects, create a `~/.cursor/mcp.json` file in your home directory.
    - This makes MCP servers available in all your Cursor workspaces.

#### `.cursor/mcp.json`
 ```json
 {
   "mcpServers": {
     "awslabs.core-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.core-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     },
     "awslabs.nova-canvas-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.nova-canvas-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     },
     "awslabs.terraform-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.terraform-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
     },
    }
  }
 ```

3. **Using MCP in Chat** The Composer Agent will automatically use any MCP tools that are listed under Available Tools on the MCP settings page if it determines them to be relevant. To prompt tool usage intentionally, please prompt Cursor to use the desired AWS MCP Server you wish to use. For example, `Using the Terraform MCP Server, do...`

4. **Tool Approval** By default, when Agent wants to use an MCP tool, it will display a message asking for your approval. You can use the arrow next to the tool name to expand the message and see what arguments the Agent is calling the tool with.

</details>

### Getting Started with Windsurf
<details>
<summary>Getting Started with Windsurf</summary>

1. Follow the steps above in the **Installation and Setup** section to install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/), install Python, and configure AWS credentials with the required services.

2. **Access MCP Settings**
   - Navigate to Windsurf - Settings > Advanced Settings or use the Command Palette > Open Windsurf Settings Page
   - Look for the "Model Context Protocol (MCP) Servers" section

3. **Add MCP Servers**
   - Click "Add Server" to add a new MCP server
   - You can choose from available templates like GitHub, Puppeteer, PostgreSQL, etc.
   - Alternatively, click "Add custom server" to configure your own server

4. **Manual Configuration**
   - You can also manually edit the MCP configuration file located at `~/.codeium/windsurf/mcp_config.json`

#### `~/.codeium/windsurf/mcp_config.json`
 ```json
 {
   "mcpServers": {
     "awslabs.core-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.core-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     },
     "awslabs.nova-canvas-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.nova-canvas-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     },
     "awslabs.terraform-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.terraform-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
     },
    }
  }
 ```
</details>

## Samples

Ready-to-use examples of AWS MCP Servers in action are available in the [samples](samples/) directory. These samples provide working code and step-by-step guides to help you get started with each MCP server.

## Documentation

Comprehensive documentation for all servers is available on our [documentation website](https://awslabs.github.io/mcp/).

Documentation for each server:

- [Core MCP Server](https://awslabs.github.io/mcp/servers/core-mcp-server/)
- [Amazon Bedrock Knowledge Bases Retrieval MCP Server](https://awslabs.github.io/mcp/servers/bedrock-kb-retrieval-mcp-server/)
- [AWS CDK MCP Server](https://awslabs.github.io/mcp/servers/cdk-mcp-server/)
- [Cost Analysis MCP Server](https://awslabs.github.io/mcp/servers/cost-analysis-mcp-server/)
- [Amazon Nova Canvas MCP Server](https://awslabs.github.io/mcp/servers/nova-canvas-mcp-server/)
- [AWS Diagram MCP Server](https://awslabs.github.io/mcp/servers/aws-diagram-mcp-server/)
- [Git Repo Research MCP Server](https://awslabs.github.io/mcp/servers/git-repo-research-mcp-server/)

Documentation includes:

- Detailed guides for each server
- Installation and configuration instructions
- API references
- Usage examples

## Vibe coding

You can use these MCP servers with your AI coding assistant to [vibe code](https://en.wikipedia.org/wiki/Vibe_coding). For tips and tricks on how to improve your vibe coding experience, please refer to our [guide](./VIBE_CODING_TIPS_TRICKS.md).

## Additional Resources

- [Introducing AWS MCP Servers for code assistants](https://aws.amazon.com/blogs/machine-learning/introducing-aws-mcp-servers-for-code-assistants-part-1/)
- [Vibe coding with AWS MCP Servers | AWS Show & Tell](https://www.youtube.com/watch?v=qXGQQRMrcz0)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## Contributing

Big shout out to our awesome contributors! Thank you for making this project better!

[![contributors](https://contrib.rocks/image?repo=awslabs/mcp&max=2000)](https://github.com/awslabs/mcp/graphs/contributors)

Contributions of all kinds are welcome! Check out our [contributor guide](CONTRIBUTING.md) for more information.

## Developer guide

If you want to add a new MCP Server to the library, check out our [development guide](DEVELOPER_GUIDE.md) and be sure to follow our [design guidelines](DESIGN_GUIDELINES.md).

## License

This project is licensed under the Apache-2.0 License.

## Disclaimer

Before using an MCP Server, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the laws, rules, and regulations that govern you and your content.
