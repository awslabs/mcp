from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


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


class TerraformVariable(BaseModel):
    """Model representing a Terraform variable definition.

    Attributes:
        name: The name of the variable.
        type: The data type of the variable (string, number, bool, etc.).
        description: Description of the variable's purpose.
        default: Default value of the variable, if any.
        required: Whether the variable is required (no default value).
    """

    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    default: Optional[Any] = None
    required: bool = True


class TerraformOutput(BaseModel):
    """Model representing a Terraform output definition.

    Attributes:
        name: The name of the output.
        description: Description of the output's purpose.
    """

    name: str
    description: Optional[str] = None


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
        variables: List of variables defined in the module's variables.tf file.
        variables_content: Raw content of the variables.tf file.
        outputs: List of outputs defined in the module's README file.
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
    variables: Optional[List[TerraformVariable]] = None
    variables_content: Optional[str] = None
    outputs: Optional[List[TerraformOutput]] = None

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
        example_snippets: List of example code snippets with titles.
        arguments: Optional list of arguments with descriptions (specific to AWS provider).
        attributes: Optional list of attributes with descriptions (specific to AWS provider).
        schema: Optional schema structure with sections (specific to AWSCC provider).
               For AWSCC provider, this is a structured dictionary with sections.
        kind: Type of the item - resource or data source.
    """

    resource_name: str
    url: str
    description: str
    example_snippets: Optional[List[Dict[str, str]]] = Field(
        None, description='List of example snippets with titles'
    )
    arguments: Optional[List[Dict[str, str]]] = Field(
        None, description='List of arguments with descriptions (specific to AWS provider)'
    )
    attributes: Optional[List[Dict[str, str]]] = Field(
        None, description='List of attributes with descriptions (specific to AWS provider)'
    )
    schema: Optional[Any] = Field(
        None,
        description='Schema structure that can be a structured dictionary with sections (AWSCC provider)',
    )
    kind: str = Field('resource', description="Type of the item - 'resource' or 'data_source'")


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


class CheckovVulnerability(BaseModel):
    """Model representing a security vulnerability found by Checkov.

    Attributes:
        id: The Checkov check ID (e.g., CKV_AWS_1).
        type: The type of check (e.g., terraform_aws).
        resource: The resource identifier where the vulnerability was found.
        file_path: Path to the file containing the vulnerability.
        line: Line number where the vulnerability was found.
        description: Description of the vulnerability.
        guideline: Recommended fix or security guideline.
        severity: Severity level of the vulnerability.
        fixed: Whether the vulnerability has been fixed.
        fix_details: Details about how the vulnerability was fixed (if applicable).
    """

    id: str = Field(..., description='Checkov check ID')
    type: str = Field(..., description='Type of security check')
    resource: str = Field(..., description='Resource identifier')
    file_path: str = Field(..., description='Path to the file with the vulnerability')
    line: int = Field(..., description='Line number of the vulnerability')
    description: str = Field(..., description='Description of the vulnerability')
    guideline: Optional[str] = Field(None, description='Recommended fix or guideline')
    severity: str = Field('MEDIUM', description='Severity level (HIGH, MEDIUM, LOW)')
    fixed: bool = Field(False, description='Whether the vulnerability has been fixed')
    fix_details: Optional[str] = Field(None, description='Details about the fix applied')


class CheckovScanRequest(BaseModel):
    """Request model for Checkov scan execution.

    Attributes:
        working_directory: Directory containing Terraform files to scan.
        framework: Framework to scan (default: terraform).
        check_ids: Optional list of specific check IDs to run.
        skip_check_ids: Optional list of check IDs to skip.
        output_format: Format for the scan results output.
        auto_fix: Whether to attempt automatic fixes for found vulnerabilities.
    """

    working_directory: str = Field(..., description='Directory containing Terraform files')
    framework: str = Field(
        'terraform', description='Framework to scan (terraform, cloudformation, etc.)'
    )
    check_ids: Optional[List[str]] = Field(None, description='Specific check IDs to run')
    skip_check_ids: Optional[List[str]] = Field(None, description='Check IDs to skip')
    output_format: str = Field('json', description='Output format (json, cli, etc.)')
    auto_fix: bool = Field(False, description='Whether to attempt automatic fixes')


class CheckovScanResult(BaseModel):
    """Result model for Checkov scan execution.

    Attributes:
        status: Execution status (success/error).
        return_code: The command's return code (0 for success).
        working_directory: Directory where the scan was executed.
        error_message: Optional error message if execution failed.
        vulnerabilities: List of vulnerabilities found by the scan.
        summary: Summary of the scan results.
        raw_output: Raw output from the Checkov command.
    """

    status: Literal['success', 'error']
    return_code: Optional[int] = None
    working_directory: str
    error_message: Optional[str] = None
    vulnerabilities: List[CheckovVulnerability] = Field(
        [], description='List of found vulnerabilities'
    )
    summary: Dict[str, Any] = Field({}, description='Summary of scan results')
    raw_output: Optional[str] = Field(None, description='Raw output from Checkov')


class CheckovFixRequest(BaseModel):
    """Request model for fixing Checkov vulnerabilities.

    Attributes:
        working_directory: Directory containing Terraform files to fix.
        vulnerability_ids: List of vulnerability IDs to fix.
        backup_files: Whether to create backup files before fixing.
    """

    working_directory: str = Field(..., description='Directory containing Terraform files')
    vulnerability_ids: List[str] = Field(..., description='List of vulnerability IDs to fix')
    backup_files: bool = Field(True, description='Whether to create backup files before fixing')


class CheckovFixResult(BaseModel):
    """Result model for Checkov fix execution.

    Attributes:
        status: Execution status (success/error).
        return_code: The command's return code (0 for success).
        working_directory: Directory where the fix was executed.
        error_message: Optional error message if execution failed.
        fixed_vulnerabilities: List of vulnerabilities that were fixed.
        unfixed_vulnerabilities: List of vulnerabilities that could not be fixed.
        summary: Summary of the fix results.
    """

    status: Literal['success', 'error']
    return_code: Optional[int] = None
    working_directory: str
    error_message: Optional[str] = None
    fixed_vulnerabilities: List[CheckovVulnerability] = Field(
        [], description='List of fixed vulnerabilities'
    )
    unfixed_vulnerabilities: List[CheckovVulnerability] = Field(
        [], description='List of unfixed vulnerabilities'
    )
    summary: Dict[str, Any] = Field({}, description='Summary of fix results')
