# Developer guide

At the moment, there is no dedicated development container, thus you need to configure your local development environment following the steps described below.

## Pre-requisites

- [pre-commit](https://pre-commit.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Python](Python) 3.10. You can install it through uv using `uv python install 3.10`
- [Git](https://git-scm.com/) (if using code repository)
- (optional) [AWS CLI](https://aws.amazon.com/cli/). Some servers will require to use your AWS credentials to interact with your AWS account. Configure your credentials:

```shell
aws configure --profile [your-profile]
AWS Access Key ID [None]: xxxxxx
AWS Secret Access Key [None]:yyyyyyyyyy
Default region name [None]: us-east-1
Default output format [None]: json
```

## Preparing your Build Environment

| Action                                                                                                               | Explanation                                                                                                                                                                                                                                 |
| :--------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Open the [repository](https://github.com/awslabs/mcp). | As you are reading this file from the repo, you are probably already there.                                                                                                                       |
| Using the [fork](https://github.com/awslabs/mcp/fork) button in the upper right, fork the repo into your GitHub account.                                    | Some git/GitHub expertise is assumed.                                                                            |
| Clone the forked repo to your local development environment.                                                              | If you wish to work off a branch in your repository, create and clone that branch. You will create a PR back to `main` in the awslabs/mcp repository eventually, you can do that from fork/main or fork/*branch* |
| `cd mcp`                                                                        | This is the home directory of the repo and where you will open your text editor, run builds, etc.                                                                                                                           |
| `code .`                                                                                                             | Opens the project in VSCode. You can use the editor of your choice, just adapt this step to your specific use case.                                                                                                              |
| `pre-commit install`                                                                                                             | Install the pre-commit hooks. Pre-commit checks are crucial for a fast feedback loop while ensuring security practices at the individual change level. To prevent scenarios where these checks are accidentally omitted at the client side, we run it at [CI level](https://github.com/awslabs/mcp/tree/main/.github) too.                                                                                                             |

## Working on your server

| Action                                            | Explanation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| :-------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| (optional)<br/>`git checkout -b your-branch-name` | If you're working in a different branch than main in your forked repo and haven't changed your local branch, now is a good time to do so. |
| (optional) `uvx cookiecutter https://github.com/awslabs/mcp.git --checkout cookiecutters --output-dir ./src --directory python`                                                                                                         | If you want to add a new server to the repository. This command will run [cookiecutter](https://cookiecutter.readthedocs.io/en/stable/index.html) to generate a new project using a template.                                                                                                                      |
| Answer the CLI prompted questions                                                                                                         | In case you created a new server using the previous command. Once you answer the different questions, your new server files will be generated under src/<SERVER_NAME>-mcp-server                                                                                                                      |
| `cd src/example-mcp-server`                                                                                                       | This is the directory containing your server files.                                                                                                                      |
| `uv add {your dependencies}` or directly update ```pyproject.toml``` to add your MCP server's dependencies, under `dependencies =[]`                                                                                                     | Add dependencies required for your server.                                                                                                                      |
| ```uv venv && uv sync --all-groups```                                                                                                    | Create a Python virtual environment and install the dependencies.                                                                                                                      |
| (optional) Relative imports checks                                                                                                    | (Optional) If you are migrating your existing MCP server from another path, open two editors, one in the fork, one in your current MCP Server. Ensure your relative imports are correct.                                                                                                                      |
| *Do all your code editing*                        | Open your code editor and edit the files for your server or perform your edits on an existing server. Your server code must be located in the src folder. Use an existing server as an example of the structure that is expected.                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Create your MCP Server's documentation                       | Ensure your README conforms to the style of other READMEs, as these will be used for GitHub Pages. Add a new page for your MCP server under `docs/servers`. Edit `mkdocs.yml` and a your new page to the navigation list. Finally, you can run `mkdocs serve` to locally build and view the site.                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `git commit -m 'chore(doc): update main README.md'`                                                                                                             | Commit to your fork using clear commit messages. We highly recommend using [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) semantic. We do not enforce conventional commits on contributors to lower the entry bar. Pre-commit will run automatically before each commit. You can also run pre-commit manually on all files using `pre-commit run --all-files`. If any hook fails, the commit will be aborted, and you will need to fix the issues before committing again.                                                                                                           |

## Testing

### Testing with a Local Development MCP Server

You can modify the settings of your MCP client to run your local server. Open the your client json settings file and update it as needed. For instance, :

```
"awslabs.aws-documentation-mcp-server": {
    "command": "uv",
    "args": [
    "--directory",
    "<absolute path to your server code>",
    "run",
    "server.py"
    ],
    "env": {
    "FASTMCP_LOG_LEVEL": "ERROR"
    },
    "disabled": false,
    "autoApprove": []
},
```

where `<absolute path to your server code>` is the absolute path to the server code, for instance `/Users/myuser/mcp/src/aws-documentation-mcp-server/awslabs/aws_documentation_mcp_server`.

Also, the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) provides [Inspector](https://github.com/modelcontextprotocol/inspector), a developer tool for testing and debugging MCP servers. More information on Inspector can be found in the [documentation](https://modelcontextprotocol.io/docs/tools/inspector).

The Inspector runs directly through npx without requiring installation:

```shell
   $ npx @modelcontextprotocol/inspector <command> <args>
```

For instance, to inspect your locally developed server, you can run:

```
npx @modelcontextprotocol/inspector \
  uv \
  --directory <absolute path to your server code> \
  run \
  server.py
```
where `<absolute path to your server code>` is the absolute path to the server code, for instance `/Users/myuser/mcp/src/aws-documentation-mcp-server/awslabs/aws_documentation_mcp_server`.

Inspector will run your server on locahost (for instance: http://127.0.0.1:6274). You can then open your browser and connect to the server. For up to date instructions on how to use Inspector, please refer to the [official documentation](https://modelcontextprotocol.io/docs/tools/inspector).

### Unit tests

Each MCP server is expected to have a `tests` folder containing unit tests. For instance, you can refer to an existing server like [AWS Documentation Server](src/aws-documentation-mcp-server/tests/).

| Action            | Explanation                                |
| :------------------ | :------------------------------------------- |
| `cd src/example-mcp-server` | This is the directory containing your server files. |
| `uv run --frozen pytest` | This will run all unit tests for the server. |

## Opening your Pull Request

| Action                                            | Explanation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| :-------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Open your Pull Request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) | Once all your local tests and branch CI passes, send us a pull request with a conventional semantic title, and answer any default questions in the pull request interface. |
| Fix issues | Pay attention to any automated CI failures reported in the pull request, and stay involved in the conversation. |
| Merge ! | Once your PR is merged, the changes will be available on the main branch. If you created a new MCP server, the team will take care of the necessary steps to publish the server to the correct package manager. |
