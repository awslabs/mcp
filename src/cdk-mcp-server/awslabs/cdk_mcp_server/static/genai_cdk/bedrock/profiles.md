# Bedrock Inference Profiles

## System Defined Inference Profiles

You can build a CrossRegionInferenceProfile using a system defined inference profile. The inference profile will route requests to the Regions defined in the cross region (system-defined) inference profile that you choose. You can find the system defined inference profiles by navigating to your console (Amazon Bedrock -> Cross-region inference) or programmatically, for instance using [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock/client/list_inference_profiles.html).

Before using creating a CrossRegionInferenceProfile, ensure that you have access to the models and regions defined in the inference profiles. For instance, if you see the system defined inference profile "us.anthropic.claude-3-5-sonnet-20241022-v2:0" defined in your region, the table mentions that inference requests will be routed to US East (Virginia) us-east-1, US East (Ohio) us-east-2 and US West (Oregon) us-west-2. Thus, you need to have model access enabled in those regions for the model `anthropic.claude-3-5-sonnet-20241022-v2:0`. You can then create the CrossRegionInferenceProfile as follows:

### Examples

#### TypeScript

```ts
const cris = bedrock.CrossRegionInferenceProfile.fromConfig({
  geoRegion: bedrock.CrossRegionInferenceProfileRegion.US,
  model: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
});
```

#### Python

```python
cris = bedrock.CrossRegionInferenceProfile.from_config(
  geo_region= bedrock.CrossRegionInferenceProfileRegion.US,
  model= bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0
)
```

[View full documentation](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/cdk-lib/bedrock#system-defined-inference-profiles)

## Application Inference Profile

You can create an application inference profile with one or more Regions to track usage and costs when invoking a model.

To create an application inference profile for one Region, specify a foundation model. Usage and costs for requests made to that Region with that model will be tracked.

To create an application inference profile for multiple Regions, specify a cross region (system-defined) inference profile. The inference profile will route requests to the Regions defined in the cross region (system-defined) inference profile that you choose. Usage and costs for requests made to the Regions in the inference profile will be tracked. You can find the system defined inference profiles by navigating to your console (Amazon Bedrock -> Cross-region inference) or programmatically, for instance using [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock/client/list_inference_profiles.html):

```
bedrock = session.client("bedrock", region_name="us-east-1")
bedrock.list_inference_profiles(typeEquals='SYSTEM_DEFINED')
```

Before using application inference profiles, ensure that:

- You have appropriate IAM permissions
- You have access to the models and regions defined in the inference profiles
- Ensure proper configuration of the required API permissions for inference profile-related actions

Specifically the role you are assuming needs to have permissions for following actions in the IAM policy

```
"Action": [
      "bedrock:GetInferenceProfile",
      "bedrock:ListInferenceProfiles",
      "bedrock:DeleteInferenceProfile"
      "bedrock:TagResource",
      "bedrock:UntagResource",
      "bedrock:ListTagsForResource"
  ]
```

You can restrict to specific resources by applying "Resources" tag in the IAM policy.

```
"Resource": ["arn:aws:bedrock:*:*:application-inference-profile/*"]
```

### Examples

#### TypeScript

```ts
// Create an application inference profile for one Region
// You can use the 'bedrock.BedrockFoundationModel' or pass the arn as a string
const appInfProfile1 = new ApplicationInferenceProfile(this, 'myapplicationprofile', {
  inferenceProfileName: 'claude 3 sonnet v1',
  modelSource: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0,
  tags: [{ key: 'test', value: 'test' }],
});

// To create an application inference profile across regions, specify the cross region inference profile
const cris = bedrock.CrossRegionInferenceProfile.fromConfig({
  geoRegion: bedrock.CrossRegionInferenceProfileRegion.US,
  model: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
});

const appInfProfile2 = new ApplicationInferenceProfile(this, 'myapplicationprofile2', {
  inferenceProfileName: 'claude 3 sonnet v1',
  modelSource: cris,
});

// Import a Cfn L1 construct created application inference profile
const cfnapp = new CfnApplicationInferenceProfile(this, 'mytestaip3', {
  inferenceProfileName: 'mytest',
  modelSource: {
    copyFrom: 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
  },
});

const appInfProfile3 = bedrock.ApplicationInferenceProfile.fromCfnApplicationInferenceProfile(cfnapp);

// Import an inference profile through attributes
const appInfProfile4 = bedrock.ApplicationInferenceProfile.fromApplicationInferenceProfileAttributes(this, 'TestAIP', {
  inferenceProfileArn: 'arn:aws:bedrock:us-east-1:XXXXX:application-inference-profile/ID',
  inferenceProfileIdentifier: 'arn:aws:bedrock:us-east-1:XXXXXXX:application-inference-profile/ID',
});
```

#### Python

```python

# Create an application inference profile for one Region
# You can use the 'bedrock.BedrockFoundationModel' or pass the arn as a string
appInfProfile1 = bedrock.ApplicationInferenceProfile(self, 'myapplicationprofile',
  inference_profile_name='claude 3 sonnet v1',
  model_source=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0,
  tags=[CfnTag(
    key="key",
    value="value"
  )]
)

# To create an application inference profile across regions, specify the cross region inference profile
cris = bedrock.CrossRegionInferenceProfile.from_config(
  geo_region= bedrock.CrossRegionInferenceProfileRegion.US,
  model= bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0
)

appInfProfile2 = bedrock.ApplicationInferenceProfile(self, 'myapplicationprofile2',
  inference_profile_name='claude 35 sonnet v2',
  model_source=cris
)

# Import an inference profile through attributes
appInfProfile3 = bedrock.ApplicationInferenceProfile.from_application_inference_profile_attributes(self, 'TestAIP',
  inference_profile_arn='arn:aws:bedrock:us-east-1:XXXXX:application-inference-profile/ID',
  inference_profile_identifier='arn:aws:bedrock:us-east-1:XXXXXXX:application-inference-profile/ID',
)

# Import a Cfn L1 construct created application inference profile
cfnaip = CfnApplicationInferenceProfile(this, 'mytestaip4',
  inference_profile_name='mytest',
  model_source= CfnApplicationInferenceProfile.InferenceProfileModelSourceProperty(
    copy_from='arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
  ),
)

appInfProfile4 = bedrock.ApplicationInferenceProfile.from_cfn_application_inference_profile(cfnaip);
```

[View full documentation](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/cdk-lib/bedrock#application-inference-profile)
