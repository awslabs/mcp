# Bedrock Guardrails

Amazon Bedrock's Guardrails feature enables you to implement robust governance and control mechanisms for your generative AI applications, ensuring alignment with your specific use cases and responsible AI policies. Guardrails empowers you to create multiple tailored policy configurations, each designed to address the unique requirements and constraints of different use cases. These policy configurations can then be seamlessly applied across multiple foundation models (FMs) and Agents, ensuring a consistent user experience and standardizing safety, security, and privacy controls throughout your generative AI ecosystem.

With Guardrails, you can define and enforce granular, customizable policies to precisely govern the behavior of your generative AI applications. You can configure the following policies in a guardrail to avoid undesirable and harmful content and remove sensitive information for privacy protection.

- Content filters – Adjust filter strengths to block input prompts or model responses containing harmful content.

- Denied topics – Define a set of topics that are undesirable in the context of your application. These topics will be blocked if detected in user queries or model responses.

- Word filters – Configure filters to block undesirable words, phrases, and profanity. Such words can include offensive terms, competitor names etc.

- Sensitive information filters – Block or mask sensitive information such as personally identifiable information (PII) or custom regex in user inputs and model responses.

You can create a Guardrail with a minimum blockedInputMessaging ,blockedOutputsMessaging and default content filter policy.

## Examples

### TypeScript

```ts
const guardrails = new bedrock.Guardrail(this, 'bedrockGuardrails', {
  name: 'my-BedrockGuardrails',
  description: 'Legal ethical guardrails.',
});

// Optional - Add Sensitive information filters

guardrails.addPIIFilter({
  type: PIIType.General.ADDRESS,
  action: GuardrailAction.ANONYMIZE,
});

guardrails.addRegexFilter({
  name: 'TestRegexFilter',
  description: 'This is a test regex filter',
  pattern: '/^[A-Z]{2}d{6}$/',
  action: bedrock.GuardrailAction.ANONYMIZE,
});

// Optional - Add contextual grounding

guardrails.addContextualGroundingFilter({
  type: ContextualGroundingFilterType.GROUNDING,
  threshold: 0.95,
});

guardrails.addContextualGroundingFilter({
  type: ContextualGroundingFilterType.RELEVANCE,
  threshold: 0.95,
});

// Optional - Add Denied topics . You can use a Topic or create your custom Topic

guardrails.addDeniedTopicFilter(Topic.FINANCIAL_ADVICE);
guardrails.addDeniedTopicFilter(
  Topic.custom({
    name: 'Legal_Advice',
    definition:
      'Offering guidance or suggestions on legal matters, legal actions, interpretation of laws, or legal rights and responsibilities.',
    examples: [
      'Can I sue someone for this?',
      'What are my legal rights in this situation?',
      'Is this action against the law?',
      'What should I do to file a legal complaint?',
      'Can you explain this law to me?',
    ],
  })
);

// Optional - Add Word filters. You can upload words from a file with addWordFilterFromFile function.
guardrails.addWordFilter('drugs');
guardrails.addManagedWordListFilter(ManagedWordFilterType.PROFANITY);
guardrails.addWordFilterFromFile('./scripts/wordsPolicy.csv');

// versioning - if you change any guardrail configuration, a new version will be created
guardrails.createVersion('testversion');

// Importing existing guardrail
const importedGuardrail = bedrock.Guardrail.fromGuardrailAttributes(stack, 'TestGuardrail', {
  guardrailArn: 'arn:aws:bedrock:us-east-1:123456789012:guardrail/oygh3o8g7rtl',
  guardrailVersion: '1', //optional
  kmsKey: kmsKey, //optional
});

// Importing Guardrails created through the L1 CDK CfnGuardrail construct
const cfnGuardrail = new CfnGuardrail(this, 'MyCfnGuardrail', {
  blockedInputMessaging: 'blockedInputMessaging',
  blockedOutputsMessaging: 'blockedOutputsMessaging',
  name: 'namemycfnguardrails',
  wordPolicyConfig: {
    wordsConfig: [
      {
        text: 'drugs',
      },
    ],
  },
});

const importedGuardrail = bedrock.Guardrail.fromCfnGuardrail(cfnGuardrail);
```

### Python

```python
    guardrail = bedrock.Guardrail(self, 'myGuardrails',
        name='my-BedrockGuardrails',
        description= "Legal ethical guardrails.")

    # Optional - Add Sensitive information filters

    guardrail.add_pii_filter(
        type= bedrock.pii_type.General.ADDRESS,
        action= bedrock.GuardrailAction.ANONYMIZE,
    )

    guardrail.add_regex_filter(
        name= "TestRegexFilter",
        description= "This is a test regex filter",
        pattern= "/^[A-Z]{2}d{6}$/",
        action= bedrock.GuardrailAction.ANONYMIZE,
    )

    # Optional - Add contextual grounding

    guardrail.add_contextual_grounding_filter(
        type= bedrock.ContextualGroundingFilterType.GROUNDING,
        threshold= 0.95,
    )

    # Optional - Add Denied topics . You can use default Topic or create your custom Topic with createTopic function. The default Topics can also be overwritten.

    guardrail.add_contextual_grounding_filter(
        type= bedrock.ContextualGroundingFilterType.RELEVANCE,
        threshold= 0.95,
    )

    guardrail.add_denied_topic_filter(bedrock.Topic.FINANCIAL_ADVICE)

    guardrail.add_denied_topic_filter(
      bedrock.Topic.custom(
        name= "Legal_Advice",
        definition=
            "Offering guidance or suggestions on legal matters, legal actions, interpretation of laws, or legal rights and responsibilities.",
        examples= [
            "Can I sue someone for this?",
            "What are my legal rights in this situation?",
            "Is this action against the law?",
            "What should I do to file a legal complaint?",
            "Can you explain this law to me?",
        ]
      )
    )

    # Optional - Add Word filters. You can upload words from a file with addWordFilterFromFile function.
    guardrail.add_word_filter("drugs")
    guardrail.add_managed_word_list_filter(bedrock.ManagedWordFilterType.PROFANITY)
    guardrail.add_word_filter_from_file("./scripts/wordsPolicy.csv")

    # versioning - if you change any guardrail configuration, a new version will be created
    guardrail.create_version("testversion")

    # Importing existing guardrail
    imported_guardrail = bedrock.Guardrail.from_guardrail_attributes(self, "TestGuardrail",
      guardrail_arn="arn:aws:bedrock:us-east-1:123456789012:guardrail/oygh3o8g7rtl",
      guardrail_version="1",
      kms_key=kms_key
    )

    # Importing Guardrails created through the L1 CDK CfnGuardrail construct
    cfn_guardrail = cfnbedrock.CfnGuardrail(self, "MyCfnGuardrail",
        blocked_input_messaging="blockedInputMessaging",
        blocked_outputs_messaging="blockedOutputsMessaging",
        name="name",

        # the properties below are optional
        word_policy_config=cfnbedrock.CfnGuardrail.WordPolicyConfigProperty(
            words_config=[cfnbedrock.CfnGuardrail.WordConfigProperty(
                text="drugs"
            )]
        )
    )

    imported_guardrail = bedrock.Guardrail.from_cfn_guardrail(cfn_guardrail)
```


[View full documentation](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/cdk-lib/bedrock#bedrock-guardrails)
