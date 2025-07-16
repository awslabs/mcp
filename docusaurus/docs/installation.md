# Installation

Each server has specific installation instructions with one-click installs for Cursor and VSCode. Generally, you can:

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python using `uv python install 3.10`
3. Configure AWS credentials with access to required services
4. Add the server to your MCP client configuration

Example configuration for Amazon Q CLI MCP (`~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-pricing-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.cdk-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-documentation-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.terraform-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.terraform-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

See individual servers under ***Available AWS MCP Servers*** for specific requirements and configuration options.

If you have problems with MCP configuration or want to check if the appropriate parameters are in place, you can try the following:

```shell
# Run MCP server manually with timeout 15s
$ timeout 15s uv tool run [MCP Name] [args] 2>&1 || echo "Command completed or timed out"

# Example (Aurora MySQL MCP Server)
$ timeout 15s uv tool run awslabs.mysql-mcp-server --resource_arn [Your Resource ARN] --secret_arn [Your Secret ARN] ... 2>&1 || echo "Command completed or timed out"

# If the arguments are not set appropriately, you may see the following message:
usage: awslabs.mysql-mcp-server [-h] --resource_arn RESOURCE_ARN --secret_arn SECRET_ARN --database DATABASE
                                --region REGION --readonly READONLY
awslabs.mysql-mcp-server: error: the following arguments are required: --resource_arn, --secret_arn, --database, --region, --readonly
```

**Note about performance when using `uvx` *"@latest"* suffix:**

Using the *"@latest"* suffix checks and downloads the latest MCP server package from pypi every time you start your MCP clients, but it comes with a cost of increased initial load times. If you want to minimize the initial load time, remove *"@latest"* and manage your uv cache yourself using one of these approaches:

- `uv cache clean [tool]`: where `[tool]` is the mcp server you want to delete from cache and install again (e.g.: "awslabs.lambda-tool-mcp-server") (remember to remove the square brackets).
- `uvx [tool]@latest`: this will refresh the tool with the latest version and add it to the uv cache.

### Running MCP servers in containers

*This example uses docker with the `awslabs.nova-canvas-mcp-server` and can be repeated for each MCP server*

- Build and tag the image

  ```base
  cd src/nova-canvas-mcp-server
  docker build -t awslabs/nova-canvas-mcp-server .
  ```

- Optionally save sensitive environmental variables in a file:

  ```.env
  # contents of a .env file with fictitious AWS temporary credentials
  AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
  ```

- Use the docker options: `--env`, `--env-file`, and `--volume` as needed because the `"env": `{}`` are not available within the container.

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

### Getting Started with Amazon Q Developer CLI

See [Amazon Q Developer CLI documentation](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-config-CLI.html) for details.

1. **Access MCP Settings**
   - Open the Q Developer panel and open the **Chat** panel.
   - Choose the tools icon to access to MCP configuration.

2. **Add MCP Servers**
   - Choose the plus (+) symbol.
   - Select the scope: global or local.
    If you select global scope, the MCP server configuration is stored in ~/.aws/amazonq/mcp.json and available across all your projects. If you select local scope, the configuration is stored in .amazonq/mcp.json within your current project.
   - Fill in values as applicable.

3. **Manual Configuration**
   - You can also manually edit the MCP configuration file located at `~/.aws/amazonq/mcp.json` globally or `.amazonq/mcp.json` locally.

#### `~/.aws/amazonq/mcp.json`

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Getting Started with Kiro

See [Kiro Model Context Protocol Documentation](https://kiro.dev/docs/mcp/configuration/) for details.

1. Navigate `Kiro` > `MCP Servers`
2. Add a new MCP server by clicking the `+ Add` button.
3. Paste the configuration given below:

#### `kiro_mcp_settings.json`

For macOS/Linux:

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

For Windows:

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Getting Started with Cline and Amazon Bedrock

**IMPORTANT:** Following these instructions may incur costs and are subject to the [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/). You are responsible for any associated costs. In addition to selecting the desired model in the Cline settings, ensure you have your selected model (e.g. `anthropic.claude-3-7-sonnet`) also enabled in Amazon Bedrock. For more information on this, see [these AWS docs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) on enabling model access to Amazon Bedrock Foundation Models (FMs).

1. Follow the steps above in the **Installation and Setup** section to install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/), install Python, and configure AWS credentials with the required services.
2. If using Visual Studio Code, install the [Cline VS Code Extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev) (or equivalent extension for your preferred IDE). Once installed, click the extension to open it. When prompted, select the tier that you wish. In this case, we will be using Amazon Bedrock, so the free tier of Cline is fine as we will be sending requests using the Amazon Bedrock API instead of the Cline API.
3. Select the **MCP Servers** button.
4. Select the **Installed** tab, then click **Configure MCP Servers** to open the `cline_mcp_settings.json` file
5. In the `cline_mcp_settings.json` file, add your desired MCP servers in the `mcpServers` object. See the following example that will use one of the current AWS MCP servers that is available in this repository. Ensure you save the file to install the MCP servers.

#### `cline_mcp_settings.json`

 ```json
  {
   "mcpServers": {
     "awslabs.nova-canvas-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.nova-canvas-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     }
    }
  }
 ```

6. Once installed, you should see a list of your MCP Servers under the MCP Server Installed tab, and they should have a green slider to show that they are enabled. Click **Done** when finished. You should now see the Cline chat interface.
7. By default, Cline will be set as the API provider, which has limits for the free tier. Next, let's update the API provider to be AWS Bedrock, so we can use the LLMs through Bedrock, which would have billing go through your connected AWS account.
8. Click the settings gear to open up the Cline settings. Then under **API Provider**, switch this from `Cline` to `AWS Bedrock` and select `AWS Profile` for the authentication type. As a note, the `AWS Credentials` option works as well, however it uses a static credentials (Access Key ID and Secret Access Key) instead of temporary credentials that are automatically redistributed when the token expires, so the temporary credentials with an AWS Profile is the more secure and recommended method.
9. Fill out the configuration based on the existing AWS Profile you wish to use, select the desired AWS Region, and enable cross-region inference. Click **Done** to return to the chat interface.
10. Now you can begin asking questions and testing out the functionality of your installed AWS MCP Servers. The default option in the chat interface is is `Plan` which will provide the output for you to take manual action on (e.g. providing you a sample configuration that you copy and paste into a file). However, you can optionally toggle this to `Act` which will allow Cline to act on your behalf (e.g. searching for content using a web browser, cloning a repository, executing code, etc). You can optionally toggle on the "Auto-approve" section to avoid having to click to approve the suggestions, however we recommend leaving this off during testing, especially if you have the Act toggle selected.

**Note:** For the best results, please prompt Cline to use the desired AWS MCP Server you wish to use. For example, `Using the Terraform MCP Server, do...`


### Getting Started with Cursor

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
    "awslabs.nova-canvas-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.nova-canvas-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     }
  }
}
```

3. **Using MCP in Chat** The Composer Agent will automatically use any MCP tools that are listed under Available Tools on the MCP settings page if it determines them to be relevant. To prompt tool usage intentionally, please prompt Cursor to use the desired AWS MCP Server you wish to use. For example, `Using the Terraform MCP Server, do...`

4. **Tool Approval** By default, when Agent wants to use an MCP tool, it will display a message asking for your approval. You can use the arrow next to the tool name to expand the message and see what arguments the Agent is calling the tool with.

### Getting Started with Windsurf


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
     }
    }
  }
 ```

### Getting Started with VS Code


Configure MCP servers in VS Code settings or in `.vscode/mcp.json` (see [VS Code MCP docs](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) for more info.):

#### `.vscode/mcp.json`

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```
