---
description: Standard format for Agent scripts
globs: **/*.script.md
---
# Agent Script Format Specification

## Overview

This document defines the standard format for Agent scripts. Scripts are markdown files that provide structured guidance for agents to follow when performing specific tasks, making complex workflows repeatable and consistent.

## File Naming and Location

1. All script files MUST use the `.script.md` file extension.
2. Script files SHOULD have descriptive names using kebab-case (e.g., `idea-honing.script.md`).

## Script Structure

Each script MUST include the following sections:

### 1. Front Matter

```markdown
---
description: [A concise description of what the script does and when to use it]
---
```

**Constraints:**
- You MUST include front matter at the beginning of every script file
- You MUST include a `description` field in the front matter
- The description MUST be concise and clearly explain the script's purpose
- The front matter MUST be enclosed in triple dashes (`---`)

### 2. Title and Overview

```markdown
# [Script Name]

## Overview

[A concise description of what the script does and when to use it]
```

### 3. Parameters

```markdown
## Parameters

- **required_param** (required): [Description of the required parameter]
- **another_required** (required): [Description of another required parameter]
- **optional_param** (optional): [Description of the optional parameter]
- **optional_with_default** (optional, default: "default_value"): [Description]
```

Parameter names MUST:
- Use lowercase letters
- Use underscores for spaces (snake_case)
- Be descriptive of their purpose

For parameters with flexible input methods:

```markdown
## Parameters

- **input_data** (required): The data to be processed.

**Constraints for parameter acquisition:**
- You MUST ask for all required parameters upfront in a single prompt rather than one at a time
- You MUST support multiple input methods including:
  - Direct input: Text provided directly in the conversation
  - File path: Path to a local file
  - URL: Link to an internal resource
  - Other methods: You SHOULD be open to other ways the user might want to provide the data
- You MUST use appropriate tools to access content based on the input method
- You MUST confirm successful acquisition of all parameters before proceeding
- You SHOULD save any acquired data to a consistent location for use in subsequent steps
```

### 4. Steps

```markdown
## Steps

### 1. Verify Dependencies

Check for required tools and warn the user if any are missing.

**Constraints:**
- You MUST verify the following tools are available in your context:
  - tool_name_one
  - tool_name_two
- You MUST inform the user about any missing tools
- You MUST ask if the user wants to proceed anyway despite missing tools
- You MUST respect the user's decision to proceed or abort

### 2. [Step Name]

[Natural language description of what happens in this step]

**Constraints:**
- You MUST [specific requirement using RFC2119 keyword]
- You SHOULD [recommended behavior using RFC2119 keyword]
- You MAY [optional behavior using RFC2119 keyword]

### 3. [Next Step]

[Description]

**Constraints:**
- [List of constraints]
```

For steps with conditional logic:

```markdown
### 4. [Conditional Step]

If [condition], proceed with [specific action]. Otherwise, [alternative action].

**Constraints:**
- You MUST check [condition] before proceeding
- If [condition] is true, You MUST [action]
- If [condition] is false, You MUST [alternative action]
```

### 5. Examples (Optional but Recommended)

```markdown
## Examples

### Example Input
```
[Example input]
```

### Example Output
```
[Example output]
```
```

### 6. Troubleshooting (Optional)

```markdown
## Troubleshooting

### [Common Issue]
If [issue description], you should [resolution steps].

### [Another Issue]
[Description and resolution]
```

## RFC2119 Keywords

Scripts MUST use the following keywords as defined in RFC2119 to indicate requirement levels:

- **MUST** (or **REQUIRED**): Absolute requirement
- **MUST NOT** (or **SHALL NOT**): Absolute prohibition
- **SHOULD** (or **RECOMMENDED**): There may be valid reasons to ignore this item, but the full implications must be understood and carefully weighed
- **SHOULD NOT** (or **NOT RECOMMENDED**): There may be valid reasons when this behavior is acceptable, but the full implications should be understood
- **MAY** (or **OPTIONAL**): Truly optional item

## Negative Constraints and Context

When using negative constraints (MUST NOT, SHOULD NOT, SHALL NOT, NEVER, etc.), you MUST provide context explaining why the restriction exists. This helps users understand the reasoning and avoid similar issues.

**Format for negative constraints:**
```markdown
- You MUST NOT [action] because [reason/context]
- You SHOULD NEVER [action] since [explanation of consequences]
- You SHALL NOT [action] as [technical limitation or risk]
```

**Examples:**

Good constraint with context:
```markdown
- You MUST NOT use ellipses (...) in responses because your output will be read aloud by a text-to-speech engine, and the engine cannot properly pronounce ellipses
- You SHOULD NEVER delete Git history files since this could corrupt the repository and make recovery impossible
- You MUST NOT run `git push` because this could publish unreviewed code to shared repositories where others depend on it
```

Bad constraint without context:
```markdown
- You MUST NOT use ellipses
- You SHOULD NEVER delete Git files
- You MUST NOT run git push
```

**Common contexts for negative constraints:**
- **Technical limitations**: "because the system cannot handle..."
- **Security risks**: "since this could expose sensitive data..."
- **Data integrity**: "as this could corrupt or lose important information..."
- **User experience**: "because users will be confused by..."
- **Compatibility issues**: "since this breaks integration with..."
- **Performance concerns**: "as this could cause significant slowdowns..."
- **Workflow disruption**: "because this interferes with established processes..."

## Tool Dependency Verification

For scripts that require specific tools:

1. The first step MUST be "Verify Dependencies"
2. This step MUST check for all required tools that the script will use
3. The model already knows what tools are available in its context and does not need to run a command to check
4. The verification MUST ONLY check that tools exist in context and MUST NOT attempt to actually run the tools
5. If any tools are missing, the script MUST warn the user
6. The script MUST allow the user to proceed anyway if they choose to

Example:

```markdown
### 1. Verify Dependencies

Check for required tools and warn the user if any are missing.

**Constraints:**
- You MUST verify the following tools are available in your context:
  - santos_slack_mcp_server___get_conversation_history
  - santos_slack_mcp_server___get_thread_replies
- You MUST ONLY check for tool existence and MUST NOT attempt to run the tools because running tools during verification could cause unintended side effects, consume resources unnecessarily, or trigger actions before the user is ready
- You MUST inform the user about any missing tools with a clear message
- You MUST ask if the user wants to proceed anyway despite missing tools
- You MUST respect the user's decision to proceed or abort
```

## Interactive Scripts

For scripts with interactive elements:

1. The natural language description SHOULD clearly indicate when user interaction is expected
2. Constraints MUST specify how to handle user responses
3. The script SHOULD specify where to save interaction records

Example:

```markdown
### 2. Requirements Clarification

Guide the user through a series of questions to refine their initial idea.

**Constraints:**
- You MUST ask one question at a time
- You MUST append each question and answer to "idea-honing.md"
- You SHOULD adapt follow-up questions based on previous answers
- You MUST continue asking questions until sufficient detail is gathered
```

## Best Practices

1. Keep steps focused and concise
2. Use clear, specific constraints
3. Include examples for complex outputs
4. Use natural language descriptions that are easy to understand
5. Minimize complex conditional logic
6. Specify file paths for all artifacts created
7. Include troubleshooting guidance for common issues
8. Test scripts thoroughly before sharing
9. Always list required parameters before optional parameters
10. Use "You" instead of "The model" in constraints for more concise scripts
11. Remember that the model already knows what tools are available in its context
