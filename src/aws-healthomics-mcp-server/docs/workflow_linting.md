# Workflow Linting

The AWS HealthOmics MCP Server includes built-in workflow linting capabilities for validating WDL and CWL workflow definitions before deployment to AWS HealthOmics.

## Overview

Workflow linting helps catch common issues early in the development process:
- Syntax errors and parsing issues
- Missing required components (inputs, outputs, steps)
- Runtime requirement validation
- Best practice recommendations

## Supported Formats

### WDL (Workflow Description Language)
- Uses **miniwdl** for comprehensive validation
- Validates syntax, structure, and semantics
- Checks for missing runtime requirements
- Identifies unused inputs and outputs

### CWL (Common Workflow Language)
- Uses **cwltool** for standards-compliant validation
- Validates against CWL specifications
- Checks workflow structure and step definitions
- Ensures proper input/output connections

## Available Tools

### LintAHOWorkflowDefinition

Validates single workflow files and returns detailed findings.

**Parameters:**
- `workflow_content` (string): The workflow definition content
- `workflow_format` (string): Either "wdl" or "cwl"
- `filename` (string, optional): Filename for context in error messages

**Returns:**
- `status`: "success", "validation_failed", or "error"
- `format`: The workflow format that was linted
- `valid`: Boolean indicating if the workflow is valid
- `findings`: List of errors found during linting
- `warnings`: List of warnings found during linting
- `summary`: Summary statistics of issues found
- `linter`: Name of the linting tool used

### LintAHOWorkflowBundle

Validates multi-file workflow bundles with proper import/dependency resolution.

**Parameters:**
- `workflow_files` (dict): Dictionary mapping file paths to their content
- `workflow_format` (string): Either "wdl" or "cwl"
- `main_workflow_file` (string): Path to the main workflow file within the bundle

**Returns:**
- `status`: "success", "validation_failed", or "error"
- `format`: The workflow format that was linted
- `main_file`: The main workflow file that was processed
- `files_processed`: List of all files that were processed
- `valid`: Boolean indicating if the workflow bundle is valid
- `findings`: List of errors found during linting
- `warnings`: List of warnings found during linting
- `summary`: Summary statistics including file count and issues found
- `linter`: Name of the linting tool used

### CheckAHOLintingDependencies

Reports the status and versions of linting dependencies.

**Returns:**
- `status`: "success" or "error"
- `dependencies`: Information about miniwdl and cwltool
- `summary`: Summary of dependency availability

## Usage Examples

### Validating a WDL Workflow

```python
# Example WDL content with potential issues
wdl_content = """
version 1.0

workflow MyWorkflow {
    input {
        String sample_name
    }

    call ProcessSample { input: name = sample_name }

    output {
        File result = ProcessSample.output_file
    }
}

task ProcessSample {
    input {
        String name
    }

    command <<<
        echo "Processing ${name}" > result.txt
    >>>

    output {
        File output_file = "result.txt"
    }
}
"""

# Lint the workflow
result = await lint_workflow_definition(
    ctx=ctx,
    workflow_content=wdl_content,
    workflow_format="wdl",
    filename="my_workflow.wdl"
)

if result['valid']:
    print("Workflow is valid!")
else:
    print("Workflow has issues:")
    for finding in result['findings']:
        print(f"  Error: {finding['message']}")
    for warning in result['warnings']:
        print(f"  Warning: {warning['message']}")
```

### Validating a CWL Workflow

```python
# Example CWL content
cwl_content = """
cwlVersion: v1.2
class: Workflow

inputs:
  input_file:
    type: File

outputs:
  processed_file:
    type: File
    outputSource: process_step/output

steps:
  process_step:
    run:
      class: CommandLineTool
      baseCommand: [cat]
      inputs:
        input:
          type: File
          inputBinding:
            position: 1
      outputs:
        output:
          type: stdout
      stdout: processed.txt
    in:
      input: input_file
    out: [output]
"""

# Lint the workflow
result = await lint_workflow_definition(
    ctx=ctx,
    workflow_content=cwl_content,
    workflow_format="cwl",
    filename="my_workflow.cwl"
)
```

### Validating a Multi-File WDL Workflow

```python
# Example multi-file WDL workflow bundle
workflow_files = {
    "main.wdl": """
version 1.0

import "tasks/alignment.wdl" as alignment

workflow GenomicsPipeline {
    input {
        File reference_genome
        Array[File] fastq_files
    }

    call alignment.AlignReads {
        input:
            reference = reference_genome,
            reads = fastq_files
    }

    output {
        File aligned_bam = AlignReads.aligned_bam
    }
}
""",
    "tasks/alignment.wdl": """
version 1.0

task AlignReads {
    input {
        File reference
        Array[File] reads
    }

    command <<<
        bwa mem ${reference} ${sep=' ' reads} | samtools sort -o aligned.bam -
    >>>

    runtime {
        docker: "biocontainers/bwa:v0.7.17_cv1"
        memory: "8 GB"
        cpu: 4
    }

    output {
        File aligned_bam = "aligned.bam"
    }
}
"""
}

# Lint the workflow bundle
result = await lint_workflow_bundle(
    ctx=ctx,
    workflow_files=workflow_files,
    workflow_format="wdl",
    main_workflow_file="main.wdl"
)

if result['valid']:
    print(f"Workflow bundle is valid! Processed {result['summary']['files_count']} files.")
else:
    print("Workflow bundle has issues:")
    for finding in result['findings']:
        print(f"  Error in {finding['file']}: {finding['message']}")
```

### Validating a Multi-File CWL Workflow

```python
# Example multi-file CWL workflow bundle
workflow_files = {
    "main.cwl": """
cwlVersion: v1.2
class: Workflow

inputs:
  reference_genome: File
  fastq_files: File[]

outputs:
  aligned_bam:
    type: File
    outputSource: alignment/aligned_bam

steps:
  alignment:
    run: tools/alignment.cwl
    in:
      reference: reference_genome
      reads: fastq_files
    out: [aligned_bam]
""",
    "tools/alignment.cwl": """
cwlVersion: v1.2
class: CommandLineTool

requirements:
  - class: DockerRequirement
    dockerPull: "biocontainers/bwa:v0.7.17_cv1"

baseCommand: [bwa, mem]

inputs:
  reference:
    type: File
    inputBinding:
      position: 1
  reads:
    type: File[]
    inputBinding:
      position: 2

outputs:
  aligned_bam:
    type: stdout

stdout: aligned.bam
"""
}

# Lint the workflow bundle
result = await lint_workflow_bundle(
    ctx=ctx,
    workflow_files=workflow_files,
    workflow_format="cwl",
    main_workflow_file="main.cwl"
)
```

## Common Issues Detected

### WDL Issues
- Missing runtime requirements in tasks
- Undefined variables in command sections
- Missing workflow inputs or outputs
- Syntax errors in WDL expressions
- Type mismatches between task inputs/outputs

### CWL Issues
- Missing required fields (run, in, out)
- Invalid step connections
- Incorrect input/output types
- Missing workflow inputs or outputs
- CWL version compatibility issues
- Import resolution failures

### Multi-File Workflow Issues
- Missing imported files
- Circular import dependencies
- Namespace conflicts between imported modules
- Incorrect relative path references
- Version mismatches between main and imported files

## Best Practices

1. **Always lint before deployment**: Catch issues early in development
2. **Fix errors first**: Address all errors before warnings
3. **Review warnings**: Many warnings indicate potential improvements
4. **Use descriptive filenames**: Helps with error context and debugging
5. **Test with sample data**: Linting validates structure, not runtime behavior

## Integration with HealthOmics

After successful linting, workflows can be:
1. Packaged using `PackageAHOWorkflow`
2. Created in HealthOmics using `CreateAHOWorkflow`
3. Executed using `StartAHORun`

The linting step helps ensure workflows will parse correctly in the HealthOmics service and reduces deployment failures.
