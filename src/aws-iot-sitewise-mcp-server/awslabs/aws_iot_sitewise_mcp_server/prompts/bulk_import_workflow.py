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

"""AWS IoT SiteWise Bulk Import Workflow Helper Prompt."""

from mcp.server.fastmcp.prompts import Prompt


def bulk_import_workflow_helper() -> str:
    """Generate a comprehensive guide for bulk importing data into AWS IoT SiteWise.

    This prompt helps design and implement bulk data import strategies for historical
    and real-time industrial data, including CSV preparation, IAM setup, and job configuration.

    Returns:
        Comprehensive bulk import workflow guide
    """
    return """
You are an AWS IoT SiteWise bulk import expert helping to set up large-scale data ingestion from S3.

## 🎯 AWS IoT SiteWise Bulk Import Workflow

### **Initial Assessment Questions**

Before we begin, I need to understand your bulk import requirements:

**1. What is the age of your oldest data?**
- Last 7 days
- Last 30 days
- 1-6 months old
- 6+ months old
- Historical data from [specific year]

**2. What is the approximate size of your data?**
- Small job (< 100MB)
- Medium job (100MB - 1GB)
- Large job (1GB - 10GB)
- Very large job (> 10GB)

**3. What type of data ingestion do you need?**
- Real-time processing with computations and alerts (buffered ingestion)
- Historical data storage for analysis (historical ingestion)
- Mixed: both real-time and historical

Based on your answers, I'll recommend the optimal type of data ingestion strategy.

### **Step 1: Discovery & Assessment (CRITICAL FIRST STEPS)**

**🔍 Ask for Column Headers First**
- **Never assume column names** - they vary between users and CSV files
- **Ask explicitly**: "What are the exact column names in your CSV file?"
- Column headers determine the entire job configuration
- Each bulk import job requires exact column header specification

**Check Existing Jobs for Error Bucket (Recommended):**
```
list_bulk_import_jobs()
describe_bulk_import_job(job_id="previous-job-id")
```
- **Reuse existing error bucket** from previous jobs when possible
- Extract: `error_report_location.bucket` and `prefix`
- **Inform customer**: "I'm using the error bucket location from your previous jobs"
- **Fallback**: Ask customer for error bucket if no previous jobs exist

**Storage Configuration Check:**
```
describe_storage_configuration()
```
- Verify current storage type and retention settings
- **For data older than 30 days**: Check if warm tier or multi-layer storage is enabled
- **If historical ingestion needed but storage not configured**: Ask user to enable required storage options

### **Step 2: Data Preparation Requirements**

**CSV Column Mapping Process:**
1. **Get user's actual column headers** (never assume)
2. **Map to AWS required format** (UPPERCASE)

**Required AWS Column Names:**
- `ALIAS` or (`ASSET_ID` + `PROPERTY_ID`) - Asset identifier
- `TIMESTAMP_SECONDS` - Unix epoch timestamp
- `VALUE` - Numeric or string value
- `DATA_TYPE` - DOUBLE, INTEGER, BOOLEAN, STRING
- `QUALITY` - GOOD, BAD, UNCERTAIN

**Optional AWS Columns:**
- `TIMESTAMP_NANO_OFFSET` - Nanosecond precision

**Example Column Mapping:**
```
User CSV Headers: "alias, data type, timestamp seconds, quality, value"
AWS Format Array: ["ALIAS", "DATA_TYPE", "TIMESTAMP_SECONDS", "QUALITY", "VALUE"]
```

**File Constraints:**
- Buffered ingestion: 256MB per file maximum
- Historical ingestion: 10GB per file (CSV), 256MB (Parquet)
- UTF-8 encoding required

### **Step 3: Error Bucket Strategy**

**Option A: Reuse Existing (Recommended)**
1. Check previous jobs: `list_bulk_import_jobs()`
2. Get error bucket: `describe_bulk_import_job(job_id)`
3. Extract: `error_report_location.bucket` and `prefix`
4. **Inform customer**: "Using error bucket from your previous jobs: s3://bucket/prefix"

**Option B: Ask Customer (If No Previous Jobs)**
- Error bucket name
- Prefix (optional, defaults to "errors/")

### **Step 4: IAM Role Setup**

**Choose Your IAM Role Option:**

**Option A: Provide Existing Role ARN**
- Use if you already have an IAM role with proper S3 permissions
- Role must have trust relationship with `iotsitewise.amazonaws.com`
- Required permissions: s3:* on data bucket and error bucket

**Option B: Create New Role (Recommended)**
```
create_bulk_import_iam_role(
    role_name="IoTSiteWiseBulkImportRole-[BUCKET]",
    data_bucket_names=["user-data-bucket"],
    error_bucket_name="discovered-error-bucket"
)
```
- Automatically configures all required S3 permissions
- Sets up proper trust policy for IoT SiteWise service
- Uses s3:* permissions for maximum compatibility

**Ask user**: "Do you want to provide an existing IAM role ARN, or should I create a new role for you?"

### **Step 5: Job Configuration**

**Required Information from User:**
1. **Data bucket name**
2. **File name/key**
3. **Exact column headers**

**Create Job with Discovered Settings:**
```
create_buffered_ingestion_job(
    job_name="buffered-ingestion-[DATE]",
    job_role_arn="arn:aws:iam::account:role/[ROLE-NAME]",
    files=[{{"bucket": "user-bucket", "key": "user-file.csv"}}],
    error_report_location={{"bucket": "discovered-error-bucket", "prefix": "errors/"}},
    job_configuration={{
        "fileFormat": {{
            "csv": {{
                "columnNames": ["MAPPED", "AWS", "COLUMN", "NAMES"]
            }}
        }}
    }}
)
```

### **Step 6: Post-Job Execution (CRITICAL TIMING)**

**⏰ Data Availability Timeline:**
- **Data ingestion**: Asynchronous - **Wait 15+ minutes**
- **Data available for queries**: ~15 minutes after job completion
- **Inform customer about this delay**

**Validation After 15+ Minutes:**
```
execute_query(
    query_statement="SELECT COUNT(*) FROM raw_time_series WHERE event_timestamp >= TIMESTAMP_SUB(DAY, 30, NOW())"
)
```

**Error Analysis:**
- Check S3 error bucket for detailed error reports
- Review job status messages
- Validate asset aliases exist in SiteWise

### **Step 7: Storage Configuration (For Historical Data)**

**If you answered that your data is older than 30 days, you'll need historical ingestion which requires storage configuration.**

**First, let me check your current storage configuration:**
```
describe_storage_configuration()
```

**If warm tier is DISABLED and storage type is SITEWISE_DEFAULT_STORAGE, I'll ask you:**

"Your data requires historical ingestion, but your current storage configuration doesn't support it. I can help you enable the required storage. Which option would you prefer?"

**Option A: Enable Warm Tier Only (Recommended - Simpler)**
- I'll run: `put_storage_configuration(storage_type="SITEWISE_DEFAULT_STORAGE", warm_tier="ENABLED", retention_period={"numberOfDays": 30})`

**Option B: Enable Multi-Layer Storage with Warm Tier (Advanced)**
- You'll need to provide: S3 bucket ARN and IAM role ARN
- I'll run: `put_storage_configuration(storage_type="MULTI_LAYER_STORAGE", ...)`

**Option C: Enable Both**
- Combination of the above options

**Tell me which option you prefer, and I'll configure it for you.**

### **Step 8: Ingestion Mode Selection**

**Buffered Ingestion (adaptive_ingestion=True)**
- **Use for**: Data within the last 30 days
- **Benefits**: Real-time computations, metrics, transforms, notifications
- **Storage**: No additional configuration required
- **File limit**: 256MB per file
- **Best for**: Recent operational data, real-time monitoring

**Historical Ingestion (adaptive_ingestion=False)**
- **Use for**: Older data, large datasets
- **Requirements**: Multilayer storage or warm tier must be enabled
- **File limit**: 10GB per file (CSV), 256MB (Parquet)
- **Best for**: Data migration, historical analysis

### **Step 9: Best Practices Checklist**

✅ **Always ask for column headers** - never assume format
✅ **Check previous jobs** for error bucket reuse
✅ **Inform customer** when reusing existing settings
✅ **Verify bucket permissions** before job creation
✅ **Map user headers to AWS format** correctly
✅ **Wait 15+ minutes** after job completion for data availability
✅ **Use buffered ingestion** for data within 30 days
✅ **Create bucket-specific IAM role** if existing role lacks access

### **Recommended Workflow Template:**

```
1. Ask: "What are the exact column names in your CSV file?"
2. Check existing jobs: list_bulk_import_jobs()
3. Get error bucket: describe_bulk_import_job(job_id)
4. Ask for: bucket name, file name
5. Create IAM role if needed: create_bulk_import_iam_role()
6. Create job with discovered error bucket location
7. Inform customer: "Job created. Data will be available in 15+ minutes"
8. Wait 15+ minutes, then validate data ingestion
```

Based on your answers above, I'll provide specific recommendations for:
- **Ingestion mode** (buffered vs historical)
- **File size limits** and optimization strategies
- **Storage configuration** requirements
- **Performance** considerations

**Next Steps:**
1. **Ask for your CSV column headers** (exact names)
2. **Check your previous jobs** for error bucket reuse
3. **Get your data bucket and file details**
4. **Create IAM role** if needed
5. **Configure and execute** bulk import job
6. **Wait 15 minutes**, then validate data ingestion

Would you like me to help you implement any specific part of this workflow?
"""


bulk_import_workflow_helper_prompt = Prompt.from_function(
    bulk_import_workflow_helper,
    name='bulk_import_workflow_helper_prompt',
    description='Comprehensive guide for AWS IoT SiteWise bulk data import workflows',
)
