# Contributing Guidelines

Thank you for your interest in contributing to our project. Whether it's a bug report, new feature, correction, or additional
documentation, we greatly value feedback and contributions from our community.

Please read through this document before submitting any issues or pull requests to ensure we have all the necessary
information to effectively respond to your bug report or contribution.

## Reporting Bugs/Feature Requests

We welcome you to use the GitHub issue tracker to report bugs or suggest features.

When filing an issue, please check existing open, or recently closed, issues to make sure somebody else hasn't already
reported the issue. Please try to include as much information as you can. Details like these are incredibly useful:

* A reproducible test case or series of steps
* The version of our code being used
* Any modifications you've made relevant to the bug
* Anything unusual about your environment or deployment

## Contributing via Pull Requests

Contributions via pull requests are much appreciated. Before sending us a pull request, please ensure that:

1. You are working against the latest source on the *main* branch.
2. You check existing open, and recently merged, pull requests to make sure someone else hasn't addressed the problem already.
3. You open an issue to discuss any significant work - we would hate for your time to be wasted.

To send us a pull request, please:

1. Fork the repository.
2. Modify the source; please focus on the specific change you are contributing. If you also reformat all the code, it will be hard for us to focus on your change.
3. Ensure local tests pass before submitting your PR:
   - `uvx ruff check .` (runs the linter to catch code quality issues)
   - `uvx ruff format .` (formats code according to project standards)
   - `uvx run —frozen pyright` (runs static type checking)

   These checks will automatically run in CI when you submit your PR, so running them locally first will save time and iterations.
4. Commit to your fork using clear commit messages.
5. Send us a pull request, answering any default questions in the pull request interface.
6. Pay attention to any automated CI failures reported in the pull request, and stay involved in the conversation.

GitHub provides additional document on [forking a repository](https://help.github.com/articles/fork-a-repo/) and
[creating a pull request](https://help.github.com/articles/creating-a-pull-request/).

### Adding a new MCP Server

Thank you for your interest in adding more functionality to AWS MCP Servers. To add a new one, we highly recommend using [Python cookiecutter](https://cookiecutter.readthedocs.io/en/stable/index.html), as it provides templates and boilerplates that you can quickly start from.

1. Fork the repository.
2. Run cookiecutter.

   ```cli
   uvx cookiecutter https://github.com/awslabs/mcp.git --checkout cookiecutters --output-dir ./src --directory python
   ```

3. Answer the cli prompted questions:

    ```cli
    [1/12] project_namespace (awslabs): # Keep default (awslabs)
    [2/12] hyphen_namespace (awslabs): # Keep default (awslabs)
    [3/12] underscore_namespace (awslabs): # Keep default (awslabs)
    [4/12] project_domain (Short Domain): example # Your new MCP server name (e.g., "example")
    [5/12] hyphen_domain (example): # Press Enter (will create "example-mcp-server")
    [6/12] underscore_domain (example): # Press Enter (will create "example_mcp_server")
    [7/12] description: # Brief description of your MCP server's purpose
    [8/12] instructions: # How to use your MCP server (will help LLMs understand it)
    [9/12] author_name: # Your name
    [10/12] author_email: # Your email
    [11/12] python_version (>=3.13): # Keep default (>=3.13)
    [12/12] version (0.0.0): # Starting version
    ```

4. Check the generated boilerplate files and start building from there.
5. Go to your MCP Server directory and add your dependencies.

   ```cli
   cd src/example-mcp-server
   uv add {your dependencies}
   ```

6. Or, directly update `pyproject.toml` to add your MCP server's dependency.

   ```toml
   dependencies = [
       "mcp[cli]>=1.6.0",
       "pydantic>=2.10.6",
       # add your dependencies here
   ]
   ```

7. Create Python virtual environment and install the dependencies.

   ```cli
   uv venv
   source .venv/bin/activate
   uv sync --all-group
   ```

8. (Optional) If you are migrating your existing MCP server from another path, open two editors, one in the fork, one in your current MCP Server. Ensure your relative imports are correct.

9. Ensure local tests pass. If your code doesn't pass the tests, the PR checks will fail.
   - `uvx ruff check .` (linting)
   - `uvx ruff format .` (code formatting)
   - `uvx run —frozen pyright` (type checking)

10. Take a moment to conform to the other READMEs as those will be transposed into GitHub pages.

11. Commit to your fork using clear commit messages.
12. Send us a pull request, answering any default questions in the pull request interface.
13. Pay attention to any automated CI failures reported in the pull request, and stay involved in the conversation.

## Finding contributions to work on

Looking at the existing issues is a great way to find something to contribute on. As our projects, by default, use the default GitHub issue labels (enhancement/bug/duplicate/help wanted/invalid/question/wontfix), looking at any 'help wanted' issues is a great place to start.

## Code of Conduct

This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
opensource-codeofconduct@amazon.com with any additional questions or comments.

## Security issue notifications

If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public github issue.

## Licensing

See the [LICENSE](LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.
