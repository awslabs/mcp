from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, Optional


class TerraformExecutionRequest(BaseModel):
    """Request model for Terraform command execution with parameters.

    Attributes:
        command: The Terraform command to execute (init, plan, validate, apply, destroy).
        directory: Directory containing Terraform configuration files.
        variables: Optional dictionary of Terraform variables to pass.
        aws_region: Optional AWS region to use.
        strip_ansi: Whether to strip ANSI color codes from command output.
    """

    command: Literal['init', 'plan', 'validate', 'apply', 'destroy'] = Field(
        ..., description='Terraform command to execute'
    )
    working_directory: str = Field(..., description='Directory containing Terraform files')
    variables: Optional[Dict[str, str]] = Field(None, description='Terraform variables to pass')
    aws_region: Optional[str] = Field(None, description='AWS region to use')
    strip_ansi: bool = Field(True, description='Whether to strip ANSI color codes from output')


class SubmoduleInfo(BaseModel):
    """Model representing a Terraform submodule.

    Attributes:
        name: The name of the submodule.
        path: Path to the submodule within the parent module.
        description: Brief description of the submodule purpose.
        readme_content: The README content of the submodule, when available.
    """

    name: str
    path: str
    description: Optional[str] = 'No description available'
    readme_content: Optional[str] = None


class ModuleSearchResult(BaseModel):
    """Model representing search results from Terraform module registry.

    Attributes:
        name: The name of the Terraform module.
        namespace: The module's namespace/organization.
        provider: The provider (aws).
        version: Latest version of the module.
        url: URL to the module in the Terraform registry.
        description: Brief description of the module's purpose.
        readme_content: The README content of the module, when available.
        input_count: Number of input variables defined by the module.
        output_count: Number of outputs provided by the module.
        version_details: Detailed information about the version from GitHub releases.
        submodules: List of submodules contained in this module.
        has_submodules: Whether this module contains submodules.
    """

    name: str
    namespace: str
    provider: str = 'aws'
    version: str
    url: str
    description: str
    readme_content: Optional[str] = None
    input_count: Optional[int] = None
    output_count: Optional[int] = None
    version_details: Optional[Dict[str, Any]] = None
    submodules: Optional[list[SubmoduleInfo]] = None

    @property
    def has_submodules(self) -> bool:
        """Check if the module has any submodules."""
        return self.submodules is not None and len(self.submodules) > 0


class ProviderDocsResult(BaseModel):
    """Model representing documentation results for Terraform AWS provider resources.

    Attributes:
        resource_name: Name of the AWS resource type.
        url: URL to the documentation for this resource.
        description: Brief description of the resource.
        attributes: Key attributes available for this resource.
    """

    resource_name: str
    url: str
    description: str
    example_snippet: Optional[str] = None


class TerraformExecutionResult(BaseModel):
    """Result model for Terraform command execution.

    Attributes:
        command: The Terraform command that was executed.
        status: Execution status (success/error).
        return_code: The command's return code (0 for success).
        stdout: Standard output from the Terraform command.
        stderr: Standard error output from the Terraform command.
        working_directory: Directory where the command was executed.
        error_message: Optional error message if execution failed.
        outputs: Dictionary of output values from Terraform (for apply command).
    """

    command: str
    status: Literal['success', 'error']
    return_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: str = ''
    working_directory: str
    error_message: Optional[str] = None
    outputs: Optional[Dict[str, Any]] = Field(
        None, description='Terraform outputs (for apply command)'
    )
