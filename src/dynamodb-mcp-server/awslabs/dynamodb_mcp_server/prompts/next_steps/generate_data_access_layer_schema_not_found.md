Error: Schema file not found at {schema_path}

The data model must be converted to schema.json before generating code. I will now:
1. Convert dynamodb_data_model.md to schema.json using the `dynamodb_data_model_schema_converter` tool
2. Validate the generated schema using the `dynamodb_data_model_schema_validator` tool
3. Generate the Python data access layer using the `generate_data_access_layer` tool

Starting conversion...
