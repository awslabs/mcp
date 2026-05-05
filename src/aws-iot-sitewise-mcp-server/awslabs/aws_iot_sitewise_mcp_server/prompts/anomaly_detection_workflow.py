# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS IoT SiteWise Anomaly Detection Workflow Helper Prompt."""

from mcp.server.fastmcp.prompts import Prompt


def anomaly_detection_workflow_helper() -> str:
    """Generate a comprehensive guide for setting up anomaly detection in AWS IoT SiteWise.

    This prompt helps design and implement anomaly detection workflows for industrial
    assets, including model creation, training, inference, and monitoring.

    Returns:
        Comprehensive anomaly detection workflow guide
    """
    return """
You are an AWS IoT SiteWise anomaly detection expert helping to set up intelligent monitoring for industrial assets.

## 🎯 AWS IoT SiteWise Anomaly Detection Workflow

### **Step 1: Choose Your Computation Model Approach**

**First, let's determine how you want to define your anomaly detection model:**

**Option A: Asset Model Level**
- **Choose this if**: You want to create a reusable computation model template that can be applied to multiple assets
- **How it works**:
  - Define the model using `assetModelProperty` references
  - Apply to specific assets by calling ExecuteAction API with an `assetId`
  - Same model definition can be reused across multiple assets
- **Benefits**:
  - Reusable across multiple assets of the same type
  - Consistent detection logic
  - Easier to manage at scale
- **Example**: Create a "Pump Anomaly Detection" model that can be applied to Pump-001, Pump-002, etc.

**Option B: Asset Level**
- **Choose this if**: You want to create a computation model with properties from different assets or need asset-specific property combinations
- **How it works**:
  - Define the model using `assetProperty` references with specific asset IDs
  - Call ExecuteAction API without needing to specify `assetId` (already defined in model)
  - Model is bound to specific assets and properties at creation time
- **Benefits**:
  - Can combine properties from different assets
  - Direct binding to specific assets and properties
  - Flexible property selection across your asset hierarchy
- **Example**: Create a model that uses temperature from Asset-A, pressure from Asset-B, and vibration from Asset-C

**Which approach fits your needs better?**
- **Asset Model Level**: Reusable template applied to multiple assets via ExecuteAction with assetId
- **Asset Level**: Specific asset/property combinations defined at model creation time

Please let me know which option you prefer, and I'll guide you through the appropriate setup process.

### **Step 2: Select Your Assets and Properties**

Based on your choice from Step 1, let's identify the specific assets and properties for your anomaly detection model:

**If you chose Asset Model Level:**
Let's discover your available asset models and their properties:

```
# First, let's see what asset models you have
list_asset_models()

# Then examine the specific asset model you want to use
describe_asset_model(asset_model_id="your-selected-asset-model-id")
```

**Questions for Asset Model Level:**
1. **Which asset model** do you want to create the anomaly detection template for?
2. **Input properties**: Which properties from this asset model should be used as inputs for anomaly detection? (2-10 properties recommended)
3. **Result property**: Which property should store the anomaly scores? (This should be a measurement property with STRING data type)

**If you chose Asset Level:**
Let's discover your available assets and their properties:

```
# First, let's see what assets you have
list_assets()

# Then examine the specific assets you want to use
describe_asset(asset_id="your-selected-asset-id")
```

**Questions for Asset Level:**
1. **Which assets** do you want to include in your anomaly detection model? (Can be multiple assets)
2. **Input properties**: Which specific properties from which assets should be used as inputs? (2-10 properties total recommended)
3. **Result property**: Which asset and property should store the anomaly scores? (This should be a measurement property with STRING data type)

**Property Selection Guidelines:**
- **Input Properties**: Choose sensor measurements that are relevant to the anomalies you want to detect (temperature, pressure, vibration, flow rate, etc.)
- **Result Property**: Must be a measurement property with STRING data type to store anomaly scores
- **Data Quality**: Ensure selected properties have consistent, good quality data
- **Correlation**: Choose properties that are likely to show patterns when anomalies occur

**Example Selections:**

*Asset Model Level Example:*
- Asset Model: "Pump Model" (ID: abc-123-def)
- Input Properties: Temperature, Pressure, Vibration (Property IDs: temp-456, press-789, vib-012)
- Result Property: Anomaly Score (Property ID: anom-345)

*Asset Level Example:*
- Assets: Pump-001 (ID: pump1-uuid), Sensor-Hub-A (ID: hub-uuid)
- Input Properties:
  - Temperature from Pump-001 (Property ID: temp-456)
  - Pressure from Pump-001 (Property ID: press-789)
  - Ambient Temperature from Sensor-Hub-A (Property ID: ambient-123)
- Result Property: Anomaly Score in Pump-001 (Property ID: anom-345)

Please provide:
1. Your selected asset model(s) or asset(s)
2. The specific input properties you want to use
3. The result property for storing anomaly scores

I'll help you discover and validate these selections using the SiteWise APIs.


### **Step 3: Create Anomaly Detection Computation Model**

Now that you've selected your approach and identified your assets and properties, let's create the anomaly detection computation model:

**Required Information from Steps 1 & 2:**
- ✅ Computation model approach (Asset Model Level or Asset Level)
- ✅ Selected asset model(s) or asset(s) with their UUIDs
- ✅ Input properties (2-10 properties with their UUIDs)
- ✅ Result property (STRING data type property with UUID)

**Model Creation Parameters:**
1. **Model Name**: Choose a descriptive name for your anomaly detection model
2. **Description**: Explain the purpose and scope of the anomaly detection
3. **Property Bindings**: Configure input and result properties based on your Step 1 choice

**If you chose Asset Model Level in Step 1:**

Use the asset model and properties you identified in Step 2 to create a reusable template:

```python
create_anomaly_detection_model(
    computation_model_name="Pump-Anomaly-Detection-Model",
    input_properties=[
        {"assetModelProperty": {"assetModelId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "propertyId": "12345678-abcd-ef12-3456-789012345678"}},
        {"assetModelProperty": {"assetModelId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "propertyId": "87654321-dcba-21fe-6543-210987654321"}},
        {"assetModelProperty": {"assetModelId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "propertyId": "11223344-5566-7788-99aa-bbccddeeff00"}}
    ],
    result_property={
        "assetModelProperty": {"assetModelId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "propertyId": "aabbccdd-eeff-1122-3344-556677889900"}
    },
    computation_model_description="Detects operational anomalies in industrial pumps using temperature, pressure, and vibration sensor data"
)
```

**If you chose Asset Level in Step 1:**

Use the specific assets and properties you identified in Step 2:

```python
create_anomaly_detection_model(
    computation_model_name="Multi-Asset-Anomaly-Detection",
    input_properties=[
        {"assetProperty": {"assetId": "f1e2d3c4-b5a6-9807-1234-567890abcdef", "propertyId": "12345678-abcd-ef12-3456-789012345678"}},
        {"assetProperty": {"assetId": "f1e2d3c4-b5a6-9807-1234-567890abcdef", "propertyId": "87654321-dcba-21fe-6543-210987654321"}},
        {"assetProperty": {"assetId": "9876543a-bcde-f012-3456-789abcdef012", "propertyId": "11223344-5566-7788-99aa-bbccddeeff00"}}
    ],
    result_property={
        "assetProperty": {"assetId": "f1e2d3c4-b5a6-9807-1234-567890abcdef", "propertyId": "aabbccdd-eeff-1122-3344-556677889900"}
    },
    computation_model_description="Detects anomalies across multiple assets by analyzing pump performance, environmental conditions, and equipment operations"
)
```

**Template with Your Actual UUIDs:**

Replace the example UUIDs below with the actual UUIDs from your Step 2 discovery:

*Asset Model Level Template:*
```python
create_anomaly_detection_model(
    computation_model_name="[Your-Model-Name]",
    input_properties=[
        {"assetModelProperty": {"assetModelId": "12345678-1234-1234-1234-123456789012", "propertyId": "abcdef12-3456-7890-abcd-ef1234567890"}},
        {"assetModelProperty": {"assetModelId": "12345678-1234-1234-1234-123456789012", "propertyId": "fedcba09-8765-4321-fedc-ba0987654321"}},
        # Add more input properties as needed
    ],
    result_property={
        "assetModelProperty": {"assetModelId": "12345678-1234-1234-1234-123456789012", "propertyId": "99887766-5544-3322-1100-ffeeddccbbaa"}
    },
    computation_model_description="[Your description]"
)
```

*Asset Level Template:*
```python
create_anomaly_detection_model(
    computation_model_name="[Your-Model-Name]",
    input_properties=[
        {"assetProperty": {"assetId": "87654321-4321-4321-4321-210987654321", "propertyId": "abcdef12-3456-7890-abcd-ef1234567890"}},
        {"assetProperty": {"assetId": "87654321-4321-4321-4321-210987654321", "propertyId": "fedcba09-8765-4321-fedc-ba0987654321"}},
        {"assetProperty": {"assetId": "13579bdf-2468-ace0-1357-9bdf2468ace0", "propertyId": "24681357-9bdf-ace0-2468-1357ace09bdf"}},
        # Can mix properties from different assets
    ],
    result_property={
        "assetProperty": {"assetId": "87654321-4321-4321-4321-210987654321", "propertyId": "99887766-5544-3322-1100-ffeeddccbbaa"}
    },
    computation_model_description="[Your description]"
)
```

**After Model Creation:**
- The API will return a `computation_model_id` (UUID format like: `550e8400-e29b-41d4-a716-446655440000`)
- Save this computation_model_id - you'll need it for all subsequent operations
- The model is now created but not yet trained or active

**Next Steps After Creation:**
- **Asset Model Level**: Bind the model to specific assets using the computation_model_id (Step 4)
- **Asset Level**: Ready for training using the computation_model_id (Skip to Step 5)

Please provide your actual UUIDs from Step 2, and I'll help you create the anomaly detection computation model with the correct format.

### **Step 4: Execute Training Action**

Now that your computation model is created, you need to train it before you can start inference. Training teaches the model to recognize normal vs. anomalous patterns in your data.

**Required Information from Step 3:**
- ✅ `computation_model_id` (UUID returned from model creation)

**First, get the training action definition ID:**
```python
describe_computation_model(computation_model_id="550e8400-e29b-41d4-a716-446655440000")
# Extract actionDefinitions where actionType is "AWS/ANOMALY_DETECTION_TRAINING"
# Save the actionDefinitionId for training
```

**Training Configuration Questions:**

**1. Training Data Time Range (REQUIRED):**
- **Start Time**: When should the training data begin? (Unix timestamp)
- **End Time**: When should the training data end? (Unix timestamp)
- **Recommendation**: Use 90+ days of historical data for robust models
- **Example**: 90 days ago to recent data

**2. Data Sampling Rate (OPTIONAL):**
- **Target Sampling Rate**: How frequently should data be sampled for training?
- **Options**: PT1S (1 second) to PT1H (1 hour)
- **Examples**: PT5M (5 minutes), PT15M (15 minutes), PT1H (1 hour)
- **Note**: Higher rates provide more detail but increase training cost

**3. Supervised Learning with Labels (OPTIONAL):**
If you have labeled anomaly data for supervised learning:
- **Label S3 Bucket**: S3 bucket containing your labeled training data CSV
- **Label S3 Prefix**: S3 prefix/path to your Labels.csv file
- **Note**: Both bucket and prefix must be provided together

**4. Model Evaluation Configuration (OPTIONAL):**
For pointwise diagnostics and model performance evaluation:
- **Evaluation Start Time**: Unix timestamp for evaluation data start
- **Evaluation End Time**: Unix timestamp for evaluation data end
- **Evaluation S3 Bucket**: S3 bucket for storing evaluation results
- **Evaluation S3 Prefix**: S3 prefix for evaluation results
- **Note**: All four evaluation parameters must be provided together

**5. Training Metrics (OPTIONAL):**
For comprehensive training insights:
- **Metrics S3 Bucket**: S3 bucket for storing training metrics JSON
- **Metrics S3 Prefix**: S3 prefix for metrics files
- **Note**: Both metrics bucket and prefix must be provided together

**6. Asset Binding (Asset Model Level Only):**
If you created an Asset Model Level computation model:
- **Resolve To Asset ID**: UUID of the specific asset to bind this training to

**Training Execution Examples:**

**Basic Training (Minimum Required Parameters):**
```python
execute_training_action(
    training_action_definition_id="12345678-abcd-ef12-3456-789012345678",
    training_mode="TRAIN_MODEL",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    export_data_start_time=1717225200,  # Unix timestamp - 90 days ago
    export_data_end_time=1722789360     # Unix timestamp - recent
)
```

**Training with Sampling Rate:**
```python
execute_training_action(
    training_action_definition_id="12345678-abcd-ef12-3456-789012345678",
    training_mode="TRAIN_MODEL",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    export_data_start_time=1717225200,
    export_data_end_time=1722789360,
    target_sampling_rate="PT1M"  # 1-minute intervals
)
```

**Complete Training with All Optional Configurations:**
```python
execute_training_action(
    training_action_definition_id="12345678-abcd-ef12-3456-789012345678",
    training_mode="TRAIN_MODEL",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    export_data_start_time=1717225200,
    export_data_end_time=1722789360,
    target_sampling_rate="PT15M",
    label_bucket_name="anomaly-detection-data-bucket",
    label_s3_prefix="Labels/pump-model/Labels.csv",
    evaluation_start_time=1719817200,
    evaluation_end_time=1720422000,
    evaluation_bucket_name="anomaly-detection-eval-bucket",
    evaluation_s3_prefix="Evaluations/pump-model/",
    metrics_bucket_name="anomaly-detection-metrics-bucket",
    metrics_s3_prefix="ModelMetrics/pump-model/",
    resolve_to={"assetId": "87654321-4321-4321-4321-210987654321"}  # Asset Model Level only
)
```

**Monitor Training Progress:**
```python
# List training executions
list_executions(
    target_resource_id="550e8400-e29b-41d4-a716-446655440000",
    target_resource_type="COMPUTATION_MODEL",
    action_type="AWS/ANOMALY_DETECTION_TRAINING"
)

# Check specific training execution status
describe_execution(execution_id="training-execution-uuid")
```

**Training Data Requirements:**
- **Minimum**: 14 days of historical data
- **Recommended**: 90+ days for robust models
- **Optimal**: 6+ months for complex pattern recognition
- **Data Quality**: Ensure consistent, good quality data during the training period
- **Seasonal Patterns**: Include full seasonal cycles if applicable

**After Training Completion:**
- Training will return an execution ID for monitoring progress
- Training typically takes several hours to complete
- Once training is successful, the model is ready for inference
- You can proceed to Step 5 (Inference Configuration) after training completes

**Next Steps:**
1. Gather your training data time range (start and end timestamps)
2. Decide on optional configurations (sampling rate, labels, evaluation, metrics)
3. Execute the training action with your parameters
4. Monitor training progress using list_executions and describe_execution
5. Proceed to inference configuration once training completes successfully

Please provide your training configuration details, and I'll help you execute the training action.

### **Step 5: Start Inference (Real-time Anomaly Detection)**

Once your model training is complete and successful, you can start real-time inference to detect anomalies in your live data.

**Required Information from Step 4:**
- ✅ `computation_model_id` (UUID from Step 3)
- ✅ Training completed successfully (verified via `describe_execution`)

**First, get the inference action definition ID:**
```python
describe_computation_model(computation_model_id="550e8400-e29b-41d4-a716-446655440000")
# Extract actionDefinitions where actionType is "AWS/ANOMALY_DETECTION_INFERENCE"
# Save the actionDefinitionId for inference
```

**Inference Configuration Questions:**

**1. Data Upload Frequency (REQUIRED for START mode):**
- **How often should the model process new data for anomaly detection?**
- **Options**: PT5M, PT10M, PT15M, PT30M, PT1H, PT2H, PT3H, PT4H, PT5H, PT6H, PT7H, PT8H, PT9H, PT10H, PT11H, PT12H, PT1D
- **Examples**: PT15M (15 minutes), PT1H (1 hour), PT6H (6 hours)
- **Note**: Higher frequencies provide faster detection but increase processing costs

**2. Data Delay Offset (OPTIONAL):**
- **How many minutes should we wait for data completeness before processing?**
- **Range**: 0-60 minutes
- **Default**: Usually 0-2 minutes to ensure all sensor data has arrived
- **Example**: 2 minutes delay to account for network latency

**3. Target Model Version (OPTIONAL):**
- **Which trained model version should be used for inference?**
- **Default**: Uses the last active trained model version, if none then latest successfully trained model version
- **Use Case**: Specify a particular version if you want to use a specific trained model

**4. Weekly Operating Window (OPTIONAL):**
- **When should anomaly detection run during the week?**
- **Format**: Day names (monday-sunday) with time ranges in 24-hour format
- **Example**: Business hours only, or 24/7 monitoring
- **Use Case**: Save costs by running only during operational hours

**5. Inference Time Zone (OPTIONAL):**
- **What timezone should be used for scheduling inference?**
- **Format**: IANA timezone identifier (e.g., "America/Chicago", "Europe/London", "UTC")
- **Use Case**: Align inference with local working hours and operational schedules

**6. Asset Binding (Asset Model Level Only):**
If you created an Asset Model Level computation model:
- **Resolve To Asset ID**: UUID of the specific asset to run inference on

**Inference Execution Examples:**

**Basic Inference (Minimum Required Parameters):**
```python
execute_inference_action(
    inference_action_definition_id="87654321-dcba-21fe-6543-210987654321",
    inference_mode="START",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    data_upload_frequency="PT15M"  # Process data every 15 minutes
)
```

**Inference with Data Delay and Model Version:**
```python
execute_inference_action(
    inference_action_definition_id="87654321-dcba-21fe-6543-210987654321",
    inference_mode="START",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    data_upload_frequency="PT15M",
    data_delay_offset_in_minutes=2,  # 5-minute delay for data completeness
    target_model_version=1           # Use specific model version
)
```

**Complete Inference with Operating Window:**
```python
execute_inference_action(
    inference_action_definition_id="87654321-dcba-21fe-6543-210987654321",
    inference_mode="START",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    data_upload_frequency="PT15M",
    data_delay_offset_in_minutes=2,
    target_model_version=1,
    weekly_operating_window={
        "monday": ["08:00-17:00"],     # Business hours only
        "tuesday": ["08:00-17:00"],
        "wednesday": ["08:00-17:00"],
        "thursday": ["08:00-17:00"],
        "friday": ["08:00-17:00"]
    },
    inference_time_zone="America/Chicago",
    resolve_to={"assetId": "87654321-4321-4321-4321-210987654321"}  # Asset Model Level only
)
```

**Monitor Inference Status:**
```python
# List inference executions
list_executions(
    target_resource_id="550e8400-e29b-41d4-a716-446655440000",
    target_resource_type="COMPUTATION_MODEL",
    action_type="AWS/ANOMALY_DETECTION_INFERENCE"
)

# Check specific inference execution status
describe_execution(execution_id="inference-execution-uuid")
```

**Stop Inference (when needed):**
```python
execute_inference_action(
    inference_action_definition_id="87654321-dcba-21fe-6543-210987654321",
    inference_mode="STOP",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"}
)
```

**Inference Configuration Guidelines:**
- **Frequency Selection**: Balance detection speed vs. cost (PT15M is often a good starting point)
- **Operating Windows**: Use business hours to reduce costs if 24/7 monitoring isn't required
- **Data Delay**: Allow 5-10 minutes for data completeness in most industrial scenarios
- **Timezone**: Set to match your operational timezone for proper scheduling

**After Starting Inference:**
- Inference will return an execution ID for monitoring progress
- The model will start processing live data at the specified frequency
- Anomaly scores will be written to your configured result property
- You can monitor anomaly scores using queries or dashboards

**Next Steps:**
1. Verify your training completed successfully
2. Configure your inference parameters (frequency, delay, operating window)
3. Start inference with your configuration
4. Monitor inference execution status
5. Begin monitoring anomaly scores in your result property

Please provide your inference configuration details, and I'll help you start real-time anomaly detection.

### **Step 6: Monitor Anomaly Scores**

Once inference is running, you can monitor the anomaly detection results that are published to your configured result property. The results contain detailed anomaly information in JSON format.

**Required Information from Step 5:**
- ✅ Inference is running successfully (verified via `describe_execution`)
- ✅ Result property UUID (from Step 2/3 configuration)
- ✅ Asset ID (for the result property location)

**Anomaly Score Result Format:**

The anomaly detection results are published as JSON strings to your result property with the following structure:

```json
{
    "timestamp": "2025-10-30T15:44:17.000000",
    "prediction": 1,
    "prediction_reason": "ANOMALY_DETECTED",
    "anomaly_score": 0.95928,
    "diagnostics": [{
        "name": "81ce7bb7-6694-4c4c-981f-9686110c538d\\25597e2e-9fe8-42ab-9d16-5cbe44de2c01",
        "value": 0.31411
    }, {
        "name": "81ce7bb7-6694-4c4c-981f-9686110c538d\\0946de06-c5f4-4c9e-b8b6-fe014d1a9cc2",
        "value": 0.68589
    }]
}
```

**Result Field Explanations:**
- **timestamp**: When the anomaly detection was performed (ISO 8601 format)
- **prediction**: Binary result (0 = normal, 1 = anomaly detected)
- **prediction_reason**: Text explanation ("NORMAL" or "ANOMALY_DETECTED")
- **anomaly_score**: Confidence score (0.0 = normal, 1.0 = highly anomalous)
- **diagnostics**: Property-level contributions to the anomaly score
  - **name**: Property identifier (assetId\\propertyId format)
  - **value**: Individual property's contribution to the overall anomaly score

**Retrieve Anomaly Scores:**

**Get Latest Anomaly Score:**
```python
get_asset_property_value(
    asset_id="87654321-4321-4321-4321-210987654321",
    property_id="aabbccdd-eeff-1122-3344-556677889900"  # Your result property UUID
)
```

**Get Historical Anomaly Scores:**
```python
get_asset_property_value_history(
    asset_id="87654321-4321-4321-4321-210987654321",
    property_id="aabbccdd-eeff-1122-3344-556677889900",  # Your result property UUID
    start_date="2024-11-01T00:00:00Z",  # ISO 8601 format
    end_date="2024-11-04T23:59:59Z",    # ISO 8601 format
    time_ordering="DESCENDING",         # Latest first
    max_results=100                     # Limit results
)
```

**Next Steps:**
1. Start monitoring your result property for anomaly scores
2. Parse the JSON results to extract anomaly information
3. Set up appropriate thresholds for your operational needs
4. Implement alerting based on anomaly confidence levels
5. Use diagnostics to understand which properties are contributing to anomalies

Please provide your result property details, and I'll help you set up anomaly score monitoring.

### **Step 7: Automated Retraining Setup (Optional)**

To keep your anomaly detection model accurate over time, you can set up automated retraining that runs on a schedule. This creates a retraining scheduler that automatically trains your model with fresh data at regular intervals.

**Required Information from Previous Steps:**
- ✅ `computation_model_id` (UUID from Step 3)
- ✅ `training_action_definition_id` (from Step 4)
- ✅ Model has been successfully trained at least once

**Retraining Configuration Questions:**

**1. Lookback Window (REQUIRED for retraining scheduler):**
- **How much historical data should be used for each retraining?**
- **Options**: P180D (180 days), P360D (360 days), P540D (540 days), P720D (720 days)
- **Recommendation**: P360D (1 year) provides good balance of data richness and relevance
- **Example**: P360D uses the last 360 days of data for each retraining

**2. Retraining Frequency (REQUIRED for retraining scheduler):**
- **How often should the model be retrained?**
- **Range**: P30D (30 days) to P1Y (1 year)
- **Common Options**: P30D (monthly), P90D (quarterly), P180D (semi-annually)
- **Note**: First execution starts after the specified frequency period from scheduler start

**3. Model Promotion (OPTIONAL):**
- **How should newly trained models be promoted to active use?**
- **SERVICE_MANAGED** (default): AWS automatically promotes successful models
- **CUSTOMER_MANAGED**: You manually control which models become active
- **Recommendation**: SERVICE_MANAGED for automated operations

**4. Retraining Start Date (OPTIONAL):**
- **When should the retraining scheduler begin?**
- **Format**: Unix timestamp
- **Default**: Starts immediately if not specified
- **Use Case**: Align with maintenance windows or operational schedules

**5. Model Metrics Configuration (OPTIONAL):**
For comprehensive retraining insights and performance tracking:
- **Metrics S3 Bucket**: S3 bucket for storing retraining metrics JSON
- **Metrics S3 Prefix**: S3 prefix for retraining metrics files
- **Note**: Both metrics bucket and prefix must be provided together
- **Use Case**: Track model performance trends across retraining cycles

**6. Asset Binding (Asset Model Level Only):**
If you created an Asset Model Level computation model:
- **Resolve To Asset ID**: UUID of the specific asset for retraining

**Retraining Execution Examples:**

**Basic Retraining Scheduler (Minimum Required Parameters):**
```python
execute_training_action(
    training_action_definition_id="12345678-abcd-ef12-3456-789012345678",
    training_mode="START_RETRAINING_SCHEDULER",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    lookback_window="P360D",        # Use 360 days of historical data
    retraining_frequency="P30D"     # Retrain every 30 days
)
```

**Retraining Scheduler with Model Metrics:**
```python
execute_training_action(
    training_action_definition_id="12345678-abcd-ef12-3456-789012345678",
    training_mode="START_RETRAINING_SCHEDULER",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    lookback_window="P360D",                    # Use 360 days of data
    retraining_frequency="P30D",                # Retrain every 30 days
    promotion="SERVICE_MANAGED",                # Auto-promote successful models
    metrics_bucket_name="anomaly-retraining-metrics-bucket",
    metrics_s3_prefix="RetrainingMetrics/pump-model/"
)
```

**Complete Retraining Scheduler Configuration:**
```python
execute_training_action(
    training_action_definition_id="12345678-abcd-ef12-3456-789012345678",
    training_mode="START_RETRAINING_SCHEDULER",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"},
    lookback_window="P360D",                    # Use 360 days of data
    retraining_frequency="P30D",                # Retrain every 30 days
    promotion="SERVICE_MANAGED",                # Auto-promote successful models
    retraining_start_date=1730332800,          # Unix timestamp for start date
    metrics_bucket_name="anomaly-retraining-metrics-bucket",
    metrics_s3_prefix="RetrainingMetrics/pump-model/",
    resolve_to={"assetId": "87654321-4321-4321-4321-210987654321"}  # Asset Model Level only
)
```

**Stop Retraining Scheduler (when needed):**
```python
execute_training_action(
    training_action_definition_id="12345678-abcd-ef12-3456-789012345678",
    training_mode="STOP_RETRAINING_SCHEDULER",
    target_resource={"computationModelId": "550e8400-e29b-41d4-a716-446655440000"}
)
```

**Monitor Retraining Scheduler:**
```python
# List retraining executions
list_executions(
    target_resource_id="550e8400-e29b-41d4-a716-446655440000",
    target_resource_type="COMPUTATION_MODEL",
    action_type="AWS/ANOMALY_DETECTION_TRAINING"
)

# Check specific retraining execution status
describe_execution(execution_id="retraining-execution-uuid")
```

**Retraining Schedule Behavior:**
- **First Execution**: Occurs after the specified `retraining_frequency` period from scheduler start
- **Subsequent Executions**: Continue at the specified frequency interval
- **Data Window**: Each retraining uses the `lookback_window` period of most recent data
- **Model Versions**: Each successful retraining creates a new model version
- **Promotion**: SERVICE_MANAGED automatically activates successful models for inference
- **Metrics**: If configured, comprehensive training metrics are saved to S3 for each retraining cycle

**Example Timeline:**
If you start a retraining scheduler on January 1st with `retraining_frequency="P30D"`:
- **January 1st**: Scheduler starts
- **January 31st**: First retraining execution (30 days later)
- **March 2nd**: Second retraining execution (30 days after first)
- **April 1st**: Third retraining execution (30 days after second)
- And so on...

**Model Metrics Benefits:**
- **Performance Tracking**: Monitor model accuracy trends over time
- **Comparison**: Compare performance across different retraining cycles
- **Optimization**: Identify optimal retraining frequency and parameters
- **Troubleshooting**: Diagnose model performance issues
- **Compliance**: Maintain audit trail of model performance

**Retraining Best Practices:**
- **Frequency Selection**: Balance model freshness with computational cost
  - **P30D**: Good for rapidly changing environments
  - **P90D**: Suitable for most industrial applications
  - **P180D**: Appropriate for stable, slow-changing processes
- **Lookback Window**: Use enough data to capture patterns
  - **P360D**: Recommended for seasonal patterns
  - **P180D**: Minimum for stable patterns
- **Promotion Strategy**: SERVICE_MANAGED reduces operational overhead
- **Metrics Collection**: Enable metrics for performance monitoring and optimization
- **Monitoring**: Regularly check retraining execution status and model performance

**When to Use Retraining:**
- **Data Drift**: When operational conditions change over time
- **Seasonal Patterns**: To adapt to seasonal variations in equipment behavior
- **Equipment Aging**: As equipment characteristics change with age
- **Process Changes**: When operational procedures or setpoints are modified
- **Performance Degradation**: When anomaly detection accuracy decreases

**Next Steps:**
1. Decide if automated retraining is needed for your use case
2. Choose appropriate lookback window and retraining frequency
3. Configure model metrics collection if needed for performance tracking
4. Configure and start the retraining scheduler
5. Monitor retraining executions and model performance
6. Adjust frequency or parameters based on operational feedback

Please provide your retraining configuration preferences, and I'll help you set up automated model retraining.

### **Best Practices Checklist**

✅ **Always discover assets first** - never assume structure
✅ **Use UUIDs for all IDs** - names are not accepted
✅ **Choose appropriate configuration level** - asset vs asset model
✅ **Provide sufficient training data** - minimum 14 days, recommended 90+
✅ **Monitor training progress** - check execution status regularly
✅ **Set appropriate inference frequency** - balance cost vs responsiveness
✅ **Configure operating windows** - avoid unnecessary processing
✅ **Plan for model maintenance** - regular retraining and optimization

### **Troubleshooting Guide**

**Common Issues:**
- **Training Fails**: Check data availability, property bindings, time ranges
- **No Anomaly Scores**: Verify inference is running, check property aliases
- **High False Positives**: Adjust thresholds, add more normal data to training
- **Model Not Learning**: Increase training data period, check input property quality
- **Binding Errors**: Verify UUIDs are correct, check asset model relationships

### **Recommended Workflow Template:**

```
1. Discover: list_asset_models() and list_assets()
2. Identify: Input properties and result property for anomaly scores
3. Create: Anomaly detection model (asset or asset model level)
4. Bind: Model to specific assets (asset model level only)
5. Train: Execute training with historical data
6. Monitor: Training progress and model performance
7. Infer: Start real-time anomaly detection
8. Alert: Set up monitoring and notification systems
9. Optimize: Retrain as needed
10. Maintain: Regular model updates and performance reviews
```

### **Next Steps:**
1. **Identify your assets and properties** for anomaly monitoring
2. **Choose configuration strategy** (asset vs asset model level)
3. **Create anomaly detection model** with appropriate bindings
4. **Train the model** with historical data
5. **Start inference** for real-time monitoring

Would you like me to help you implement any specific part of this anomaly detection workflow?
"""


anomaly_detection_workflow_helper_prompt = Prompt.from_function(
    anomaly_detection_workflow_helper,
    name='anomaly_detection_workflow_helper_prompt',
    description='Comprehensive guide for AWS IoT SiteWise anomaly detection workflows and intelligent asset monitoring',
)
