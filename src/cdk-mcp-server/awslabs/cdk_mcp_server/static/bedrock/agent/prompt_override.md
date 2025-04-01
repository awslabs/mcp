# Prompt Overrides

## Overview

Bedrock Agents allows you to customize the prompts and LLM configuration for its different steps. You can disable steps or create a new prompt template. Prompt templates can be inserted from plain text files.

## Example

### TypeScript

```ts
import { readFileSync } from 'fs';

const file = readFileSync(prompt_path, 'utf-8');

const agent = new bedrock.Agent(this, 'Agent', {
      foundationModel: bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
      instruction: 'You are a helpful and friendly agent that answers questions about literature.',
      userInputEnabled: true,
      codeInterpreterEnabled: false,
      shouldPrepareAgent:true,
      promptOverrideConfiguration: bedrock.PromptOverrideConfiguration.fromSteps(
        [
          {
            stepType: bedrock.AgentStepType.PRE_PROCESSING,
            stepEnabled: true,
            customPromptTemplate: file,
            inferenceConfig: {
              temperature: 0.0,
              topP: 1,
              topK: 250,
              maximumLength: 1,
              stopSequences: ["\n\nHuman:"],
            },
            foundationModel: bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1
          }
        ]
      )
    });
```

### Python

```python
orchestration = open('prompts/orchestration.txt', encoding="utf-8").read()
agent = bedrock.Agent(self, "Agent",
            foundation_model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_V2_1,
            instruction="You are a helpful and friendly agent that answers questions about insurance claims.",
            user_input_enabled=True,
            code_interpreter_enabled=False,
            should_prepare_agent=True,
            prompt_override_configuration= bedrock.PromptOverrideConfiguration.from_steps(
                steps=[
                    bedrock.PromptStepConfiguration(
                        step_type=bedrock.AgentStepType.PRE_PROCESSING,
                        step_enabled= True,
                        custom_prompt_template= file,
                        inference_config=bedrock.InferenceConfiguration(
                            temperature=0.0,
                            top_k=250,
                            top_p=1,
                            maximum_length=1,
                            stop_sequences=['\n\nHuman:'],
                        ),
                        foundationModel: bedrock.BedrockFoundationModel.AMAZON_NOVA_LITE_V1
                    ),
                ]
            ),
        )
```
