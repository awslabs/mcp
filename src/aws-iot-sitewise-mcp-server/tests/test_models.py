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

"""Tests for AWS IoT SiteWise Models."""

import pytest
from awslabs.aws_iot_sitewise_mcp_server.models import (
    ID,
    Asset,
    AssetHierarchy,
    AssetModel,
    AssetModelCompositeModel,
    AssetModelHierarchy,
    AssetModelProperty,
    AssetModelType,
    AssetProperty,
    Attribute,
    AttributeValue,
    BulkImportSchema,
    ComputeLocation,
    DataType,
    Description,
    ExpressionVariable,
    ExternalId,
    ForwardingConfig,
    Measurement,
    MeasurementProcessingConfig,
    Metric,
    MetricProcessingConfig,
    MetricWindow,
    Name,
    PropertyAlias,
    PropertyType,
    PropertyUnit,
    Tag,
    Transform,
    TransformProcessingConfig,
    TumblingWindow,
    VariableValue,
)
from pydantic import ValidationError


class TestBasicModels:
    """Test cases for basic model validation."""

    def test_name_validation(self):
        """Test Name model validation."""
        # Valid name
        name = Name(value='ValidName')
        assert name.value == 'ValidName'

        # Invalid empty name
        with pytest.raises(ValidationError):
            Name(value='')

        # Invalid long name
        with pytest.raises(ValidationError):
            Name(value='A' * 300)

        # Invalid control characters
        with pytest.raises(ValidationError):
            Name(value='Invalid\x00Name')

    def test_external_id_validation(self):
        """Test ExternalId model validation."""
        # Valid external ID
        ext_id = ExternalId(value='valid-external-id')
        assert ext_id.value == 'valid-external-id'

        # Invalid empty external ID
        with pytest.raises(ValidationError):
            ExternalId(value='')

        # Invalid short external ID
        with pytest.raises(ValidationError):
            ExternalId(value='a')

    def test_external_id_pattern_validation(self):
        """Test ExternalId pattern validation."""
        # Invalid pattern - starts with number but ends with hyphen
        with pytest.raises(ValidationError):
            ExternalId(value='1invalid-')

        # Invalid pattern - contains invalid characters
        with pytest.raises(ValidationError):
            ExternalId(value='invalid@id')

        # Invalid long external ID
        with pytest.raises(ValidationError):
            ExternalId(value='A' * 150)

    def test_id_validation(self):
        """Test ID model validation."""
        # Valid UUID
        valid_uuid = '12345678-1234-1234-1234-123456789012'
        id_obj = ID(value=valid_uuid)
        assert id_obj.value == valid_uuid

        # Invalid UUID
        with pytest.raises(ValidationError):
            ID(value='invalid-uuid')

    def test_data_type_validation(self):
        """Test DataType model validation."""
        # Valid data types
        valid_types = ['STRING', 'INTEGER', 'DOUBLE', 'BOOLEAN', 'STRUCT']
        for dtype in valid_types:
            data_type = DataType(value=dtype)  # type: ignore
            assert data_type.value == dtype

    def test_description_validation(self):
        """Test Description model validation."""
        # Valid description
        desc = Description(value='Valid description')
        assert desc.value == 'Valid description'

        # Invalid empty description
        with pytest.raises(ValidationError):
            Description(value='')

        # Invalid long description
        with pytest.raises(ValidationError):
            Description(value='A' * 3000)

    def test_description_control_characters(self):
        """Test Description validation with control characters."""
        with pytest.raises(ValidationError):
            Description(value='Invalid\x01Description')

    def test_property_alias_validation(self):
        """Test PropertyAlias model validation."""
        # Valid alias
        alias = PropertyAlias(value='/factory/line1/temperature')
        assert alias.value == '/factory/line1/temperature'

        # Invalid empty alias
        with pytest.raises(ValidationError):
            PropertyAlias(value='')

    def test_property_alias_control_characters(self):
        """Test PropertyAlias validation with control characters."""
        with pytest.raises(ValidationError):
            PropertyAlias(value='/factory/line1\x00/temperature')

        # Invalid long alias
        with pytest.raises(ValidationError):
            PropertyAlias(value='A' * 1100)

    def test_tag_validation(self):
        """Test Tag model validation."""
        # Valid tag
        tag = Tag(key='Environment', value='Production')
        assert tag.key == 'Environment'
        assert tag.value == 'Production'

        # Invalid empty key
        with pytest.raises(ValidationError):
            Tag(key='', value='Production')

        # Invalid non-string key (covers the isinstance check in validate_key)
        with pytest.raises(ValidationError, match='Input should be a valid string'):
            Tag(key=123, value='Production')  # type: ignore

        # Invalid non-string value (covers line 63)
        with pytest.raises(ValidationError, match='Input should be a valid string'):
            Tag(key='Environment', value=123)  # type: ignore

    def test_attribute_value_validation(self):
        """Test AttributeValue model validation."""
        # Valid attribute value
        attr_val = AttributeValue(value='ValidValue')
        assert attr_val.value == 'ValidValue'

        # Invalid control characters
        with pytest.raises(ValidationError):
            AttributeValue(value='Invalid\x00Value')

    def test_property_unit_validation(self):
        """Test PropertyUnit model validation."""
        # Valid unit
        unit = PropertyUnit(value='Celsius')
        assert unit.value == 'Celsius'

        # Invalid empty unit
        with pytest.raises(ValidationError):
            PropertyUnit(value='')

        # Invalid long unit
        with pytest.raises(ValidationError):
            PropertyUnit(value='A' * 300)

        # Invalid control characters
        with pytest.raises(ValidationError):
            PropertyUnit(value='Invalid\x00Unit')


class TestPropertyTypes:
    """Test cases for property type models."""

    def test_measurement_property_type(self):
        """Test creating a measurement property type."""
        measurement = Measurement()
        prop_type = PropertyType(measurement=measurement)
        assert prop_type.measurement is not None
        assert prop_type.attribute is None
        assert prop_type.transform is None
        assert prop_type.metric is None

    def test_attribute_property_type(self):
        """Test creating an attribute property type."""
        attribute = Attribute(defaultValue='test-value')
        prop_type = PropertyType(attribute=attribute)
        assert prop_type.attribute is not None
        assert prop_type.attribute.defaultValue == 'test-value'
        assert prop_type.measurement is None

    def test_transform_property_type(self):
        """Test creating a transform property type."""
        variable = ExpressionVariable(
            name='temp',
            value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
        )
        transform = Transform(expression='avg(temp)', variables=[variable])
        prop_type = PropertyType(transform=transform)
        assert prop_type.transform is not None
        assert prop_type.transform.expression == 'avg(temp)'

    def test_metric_property_type(self):
        """Test creating a metric property type."""
        variable = ExpressionVariable(
            name='temp',
            value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
        )
        window = MetricWindow(tumbling=TumblingWindow(interval='1d'))
        metric = Metric(expression='avg(temp)', variables=[variable], window=window)
        prop_type = PropertyType(metric=metric)
        assert prop_type.metric is not None
        assert prop_type.metric.expression == 'avg(temp)'

    def test_property_type_validation(self):
        """Test PropertyType validation."""
        # Invalid - no property type defined
        with pytest.raises(ValidationError):
            PropertyType()

        # Invalid - multiple property types defined
        with pytest.raises(ValidationError):
            PropertyType(measurement=Measurement(), attribute=Attribute())

        # Valid - exactly one property type defined (test all combinations)
        # Test with attribute only
        prop_type_attr = PropertyType(attribute=Attribute(defaultValue='test'))
        assert prop_type_attr.attribute is not None
        assert prop_type_attr.measurement is None
        assert prop_type_attr.transform is None
        assert prop_type_attr.metric is None

        # Test with transform only
        variable = ExpressionVariable(
            name='temp',
            value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
        )
        prop_type_transform = PropertyType(
            transform=Transform(expression='avg(temp)', variables=[variable])
        )
        assert prop_type_transform.transform is not None
        assert prop_type_transform.attribute is None
        assert prop_type_transform.measurement is None
        assert prop_type_transform.metric is None

        # Test with metric only
        window = MetricWindow(tumbling=TumblingWindow(interval='1d'))
        prop_type_metric = PropertyType(
            metric=Metric(expression='avg(temp)', variables=[variable], window=window)
        )
        assert prop_type_metric.metric is not None
        assert prop_type_metric.attribute is None
        assert prop_type_metric.measurement is None
        assert prop_type_metric.transform is None

    def test_attribute_default_value_validation(self):
        """Test Attribute defaultValue validation."""
        # Valid attribute with no default
        attr = Attribute()
        assert attr.defaultValue is None

        # Invalid control characters in default value
        with pytest.raises(ValidationError):
            Attribute(defaultValue='Invalid\x00Value')

    def test_transform_expression_validation(self):
        """Test Transform expression validation."""
        variable = ExpressionVariable(
            name='temp',
            value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
        )

        # Invalid empty expression
        with pytest.raises(ValidationError):
            Transform(expression='', variables=[variable])

        # Invalid long expression
        with pytest.raises(ValidationError):
            Transform(expression='A' * 1100, variables=[variable])

    def test_metric_expression_validation(self):
        """Test Metric expression validation."""
        variable = ExpressionVariable(
            name='temp',
            value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
        )
        window = MetricWindow(tumbling=TumblingWindow(interval='1d'))

        # Invalid empty expression
        with pytest.raises(ValidationError):
            Metric(expression='', variables=[variable], window=window)

        # Invalid long expression
        with pytest.raises(ValidationError):
            Metric(expression='A' * 1100, variables=[variable], window=window)


class TestAssetModelProperty:
    """Test cases for AssetModelProperty model."""

    def test_valid_measurement_property(self):
        """Test creating a valid measurement property."""
        prop = AssetModelProperty(
            name=Name(value='Temperature'),
            externalId=ExternalId(value='temp-sensor-1'),
            dataType=DataType(value='DOUBLE'),
            type=PropertyType(measurement=Measurement()),
        )

        assert prop.name.value == 'Temperature'
        assert prop.externalId is not None
        assert prop.externalId.value == 'temp-sensor-1'
        assert prop.dataType.value == 'DOUBLE'
        assert prop.type.measurement is not None

    def test_valid_attribute_property(self):
        """Test creating a valid attribute property."""
        prop = AssetModelProperty(
            name=Name(value='SerialNumber'),
            externalId=ExternalId(value='serial-attr'),
            dataType=DataType(value='STRING'),
            type=PropertyType(attribute=Attribute(defaultValue='SN-12345')),
        )

        assert prop.name.value == 'SerialNumber'
        assert prop.type.attribute and prop.type.attribute.defaultValue == 'SN-12345'

    def test_asset_model_property_validation(self):
        """Test AssetModelProperty validation."""
        # Invalid - missing id and externalId
        with pytest.raises(ValidationError):
            AssetModelProperty(
                name=Name(value='TestProperty'),
                dataType=DataType(value='STRING'),
                type=PropertyType(measurement=Measurement()),
            )

        # Valid with unit
        prop = AssetModelProperty(
            name=Name(value='Temperature'),
            externalId=ExternalId(value='temp-sensor'),
            dataType=DataType(value='DOUBLE'),
            type=PropertyType(measurement=Measurement()),
            unit='Celsius',
        )
        assert prop.unit == 'Celsius'

        # Invalid unit - too long
        with pytest.raises(ValidationError):
            AssetModelProperty(
                name=Name(value='Temperature'),
                externalId=ExternalId(value='temp-sensor'),
                dataType=DataType(value='DOUBLE'),
                type=PropertyType(measurement=Measurement()),
                unit='A' * 300,
            )

        # Invalid unit - control characters
        with pytest.raises(ValidationError):
            AssetModelProperty(
                name=Name(value='Temperature'),
                externalId=ExternalId(value='temp-sensor'),
                dataType=DataType(value='DOUBLE'),
                type=PropertyType(measurement=Measurement()),
                unit='Invalid\x00Unit',
            )


class TestAssetProperty:
    """Test cases for AssetProperty model."""

    def test_valid_asset_property(self):
        """Test creating a valid asset property."""
        prop = AssetProperty(
            externalId=ExternalId(value='temp-prop'),
            alias=PropertyAlias(value='/factory/line1/temperature'),
        )

        assert prop.externalId and prop.externalId.value == 'temp-prop'
        assert prop.alias and prop.alias.value == '/factory/line1/temperature'

    def test_asset_property_validation(self):
        """Test asset property validation requirements."""
        # Must have either id or externalId
        with pytest.raises(ValidationError):
            AssetProperty()


class TestAssetHierarchy:
    """Test cases for AssetHierarchy model."""

    def test_valid_asset_hierarchy(self):
        """Test creating a valid asset hierarchy."""
        hierarchy = AssetHierarchy(
            externalId=ExternalId(value='children-hierarchy'),
            childAssetExternalId=ExternalId(value='child-asset-1'),
        )

        assert hierarchy.externalId and hierarchy.externalId.value == 'children-hierarchy'
        assert (
            hierarchy.childAssetExternalId
            and hierarchy.childAssetExternalId.value == 'child-asset-1'
        )

    def test_asset_hierarchy_validation(self):
        """Test AssetHierarchy validation."""
        # Invalid - missing required field combinations
        with pytest.raises(ValidationError):
            AssetHierarchy()

        # Valid combination: id + childAssetId
        hierarchy = AssetHierarchy(
            id=ID(value='12345678-1234-1234-1234-123456789012'),
            childAssetId=ID(value='87654321-4321-4321-4321-210987654321'),
        )
        assert hierarchy.id is not None
        assert hierarchy.childAssetId is not None


class TestAssetModelHierarchy:
    """Test cases for AssetModelHierarchy model."""

    def test_asset_model_hierarchy_validation(self):
        """Test AssetModelHierarchy validation."""
        # Invalid - missing required field combinations
        with pytest.raises(ValidationError):
            AssetModelHierarchy(name=Name(value='TestHierarchy'))

        # Valid - has id and childAssetModelId
        hierarchy = AssetModelHierarchy(
            name=Name(value='TestHierarchy'),
            id=ID(value='12345678-1234-1234-1234-123456789012'),
            childAssetModelId=ID(value='87654321-4321-4321-4321-210987654321'),
        )
        assert hierarchy.name.value == 'TestHierarchy'


class TestAssetModelCompositeModel:
    """Test cases for AssetModelCompositeModel model."""

    def test_asset_model_composite_model_validation(self):
        """Test AssetModelCompositeModel validation."""
        # Invalid - missing id and externalId
        with pytest.raises(ValidationError):
            AssetModelCompositeModel(name=Name(value='TestComposite'), type=Name(value='TestType'))

        # Valid - has id
        composite = AssetModelCompositeModel(
            name=Name(value='TestComposite'),
            type=Name(value='TestType'),
            id=ID(value='12345678-1234-1234-1234-123456789012'),
        )
        assert composite.name.value == 'TestComposite'


class TestAssetModel:
    """Test cases for AssetModel model."""

    def test_asset_model_validation(self):
        """Test AssetModel validation."""
        # Invalid - missing assetModelId and assetModelExternalId
        with pytest.raises(ValidationError):
            AssetModel(assetModelName=Name(value='TestModel'))


class TestAsset:
    """Test cases for Asset model."""

    def test_asset_validation(self):
        """Test Asset validation."""
        # Invalid - missing required field combinations
        with pytest.raises(ValidationError):
            Asset(assetName=Name(value='TestAsset'))

        # Invalid - missing assetName (covers line 362)
        with pytest.raises(
            ValidationError, match='Input should be a valid dictionary or instance of Name'
        ):
            Asset(
                assetName=None,  # type: ignore
                assetId=ID(value='12345678-1234-1234-1234-123456789012'),
                assetModelId=ID(value='87654321-4321-4321-4321-210987654321'),
            )

        # Valid combination: assetId + assetModelId
        asset = Asset(
            assetName=Name(value='TestAsset'),
            assetId=ID(value='12345678-1234-1234-1234-123456789012'),
            assetModelId=ID(value='87654321-4321-4321-4321-210987654321'),
        )
        assert asset.assetName.value == 'TestAsset'


class TestBulkImportSchema:
    """Test cases for BulkImportSchema model."""

    def test_empty_bulk_import_schema(self):
        """Test creating an empty bulk import schema."""
        schema = BulkImportSchema()
        assert schema.assetModels == []
        assert schema.assets == []

    def test_bulk_import_schema_with_lists(self):
        """Test creating schema with empty lists."""
        schema = BulkImportSchema(assetModels=[], assets=[])
        assert schema.assetModels == []
        assert schema.assets == []

    def test_schema_model_dump(self):
        """Test schema serialization."""
        schema = BulkImportSchema()
        dumped = schema.model_dump(exclude_none=True)

        # Should have the basic structure
        assert 'assetModels' in dumped
        assert 'assets' in dumped

    def test_bulk_import_schema_cross_validation(self):
        """Test BulkImportSchema cross-validation."""
        # Test with assets referencing unknown model external IDs
        asset_model = AssetModel(
            assetModelName=Name(value='TestModel'),
            assetModelExternalId=ExternalId(value='test-model'),
        )

        asset = Asset(
            assetName=Name(value='TestAsset'),
            assetExternalId=ExternalId(value='test-asset'),
            assetModelExternalId=ExternalId(value='unknown-model'),  # References unknown model
        )

        with pytest.raises(ValidationError):
            BulkImportSchema(assetModels=[asset_model], assets=[asset])

        # Valid case - asset references existing model
        valid_asset = Asset(
            assetName=Name(value='TestAsset'),
            assetExternalId=ExternalId(value='test-asset'),
            assetModelExternalId=ExternalId(value='test-model'),  # References existing model
        )

        schema = BulkImportSchema(assetModels=[asset_model], assets=[valid_asset])
        assert schema.assetModels is not None and len(schema.assetModels) == 1
        assert schema.assets is not None and len(schema.assets) == 1


class TestExpressionVariable:
    """Test cases for ExpressionVariable model."""

    def test_valid_expression_variable(self):
        """Test creating a valid expression variable."""
        variable = ExpressionVariable(
            name='temp',
            value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
        )

        assert variable.name == 'temp'
        assert variable.value.propertyId is not None
        assert variable.value.propertyId.value == '12345678-1234-1234-1234-123456789012'

    def test_invalid_variable_name(self):
        """Test validation of variable names."""
        # Invalid name pattern
        with pytest.raises(ValidationError):
            ExpressionVariable(
                name='InvalidName',  # Should start with lowercase
                value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
            )

    def test_expression_variable_name_validation(self):
        """Test ExpressionVariable name validation."""
        # Invalid empty name
        with pytest.raises(ValidationError):
            ExpressionVariable(
                name='',
                value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
            )

        # Invalid long name
        with pytest.raises(ValidationError):
            ExpressionVariable(
                name='a' * 70,
                value=VariableValue(propertyId=ID(value='12345678-1234-1234-1234-123456789012')),
            )

    def test_variable_value_validation(self):
        """Test VariableValue validation."""
        # Valid with propertyExternalId
        var_val = VariableValue(propertyExternalId=ExternalId(value='temp-sensor'))
        assert var_val.propertyExternalId is not None

        # Invalid - missing both propertyId and propertyExternalId
        with pytest.raises(ValidationError):
            VariableValue()


class TestTumblingWindow:
    """Test cases for TumblingWindow model."""

    def test_valid_tumbling_window(self):
        """Test creating a valid tumbling window."""
        window = TumblingWindow(interval='1d')
        assert window.interval == '1d'

    def test_tumbling_window_with_offset(self):
        """Test creating a tumbling window with offset."""
        window = TumblingWindow(interval='1h', offset='30m')
        assert window.interval == '1h'
        assert window.offset == '30m'

    def test_tumbling_window_validation(self):
        """Test TumblingWindow validation."""
        # Invalid short interval
        with pytest.raises(ValidationError):
            TumblingWindow(interval='1')

        # Invalid long interval
        with pytest.raises(ValidationError):
            TumblingWindow(interval='A' * 30)

        # Invalid short offset
        with pytest.raises(ValidationError):
            TumblingWindow(interval='1h', offset='1')

        # Invalid long offset
        with pytest.raises(ValidationError):
            TumblingWindow(interval='1h', offset='A' * 30)


class TestProcessingConfigs:
    """Test cases for processing configuration models."""

    def test_forwarding_config(self):
        """Test ForwardingConfig model."""
        config = ForwardingConfig(state='ENABLED')
        assert config.state == 'ENABLED'

    def test_compute_location(self):
        """Test ComputeLocation model."""
        location = ComputeLocation(value='EDGE')
        assert location.value == 'EDGE'

    def test_measurement_processing_config(self):
        """Test MeasurementProcessingConfig model."""
        config = MeasurementProcessingConfig(forwardingConfig=ForwardingConfig(state='ENABLED'))
        assert config.forwardingConfig.state == 'ENABLED'

    def test_measurement_model(self):
        """Test Measurement model directly."""
        # Test creating a Measurement instance directly
        measurement = Measurement()
        assert measurement.processingConfig is None

        # Test with processing config
        measurement_with_config = Measurement(
            processingConfig=MeasurementProcessingConfig(
                forwardingConfig=ForwardingConfig(state='ENABLED')
            )
        )
        assert measurement_with_config.processingConfig is not None
        assert measurement_with_config.processingConfig.forwardingConfig.state == 'ENABLED'

    def test_transform_processing_config(self):
        """Test TransformProcessingConfig model."""
        config = TransformProcessingConfig(
            computeLocation=ComputeLocation(value='CLOUD'),
            forwardingConfig=ForwardingConfig(state='DISABLED'),
        )
        assert config.computeLocation.value == 'CLOUD'
        assert config.forwardingConfig is not None
        assert config.forwardingConfig.state == 'DISABLED'

    def test_metric_processing_config(self):
        """Test MetricProcessingConfig model."""
        config = MetricProcessingConfig(computeLocation=ComputeLocation(value='EDGE'))
        assert config.computeLocation.value == 'EDGE'

    def test_asset_model_type(self):
        """Test AssetModelType model."""
        model_type = AssetModelType(value='COMPONENT_MODEL')
        assert model_type.value == 'COMPONENT_MODEL'

        # Test with None value
        model_type_none = AssetModelType()
        assert model_type_none.value is None


if __name__ == '__main__':
    pytest.main([__file__])
