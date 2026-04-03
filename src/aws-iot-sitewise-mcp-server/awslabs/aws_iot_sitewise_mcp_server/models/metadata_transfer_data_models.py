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

"""AWS IoT SiteWise Data Models and Schema Definitions."""

import re
from ..validation_utils import (
    validate_control_characters,
    validate_expression_variable_name,
    validate_external_id,
    validate_string_length,
    validate_uuid_format,
)
from dataclasses import field
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal, Optional


CONTROL_CHAR_PATTERN = re.compile(r'^[^\u0000-\u001F\u007F]+$')


class Name(BaseModel):
    """Name field for AWS IoT SiteWise entities."""

    value: str

    @field_validator('value')
    def validate_name(cls, v):
        """Validate name field constraints."""
        validate_string_length(v, 1, 256, 'Name')
        validate_control_characters(v, 'Name')
        return v


class Description(BaseModel):
    """Description field for AWS IoT SiteWise entities."""

    value: str

    @field_validator('value')
    def validate_description(cls, v):
        """Validate description field constraints."""
        validate_string_length(v, 1, 2048, 'Description')
        validate_control_characters(v, 'Description')
        return v


class Tag(BaseModel):
    """Tag key-value pair for AWS IoT SiteWise entities."""

    key: str
    value: str

    @field_validator('key')
    def validate_key(cls, v):
        """Validate tag key constraints."""
        if not isinstance(v, str) or not v:
            raise ValueError('key must be a non-empty string.')
        return v

    @field_validator('value')
    def validate_value(cls, v):
        """Validate tag value constraints."""
        return v


class ID(BaseModel):
    """UUID identifier for AWS IoT SiteWise entities."""

    value: str

    @field_validator('value')
    def validate_uuid(cls, v):
        """Validate UUID format constraints."""
        return validate_uuid_format(v, 'UUID')


class ExternalId(BaseModel):
    """External identifier for AWS IoT SiteWise entities."""

    value: str

    @field_validator('value')
    def validate_external_id(cls, v):
        """Validate external ID format and length constraints."""
        return validate_external_id(v)


class AttributeValue(BaseModel):
    """Attribute value for AWS IoT SiteWise properties."""

    value: str

    @field_validator('value')
    def validate_attribute_value(cls, v):
        """Validate attribute value constraints."""
        validate_control_characters(v, 'AttributeValue')
        return v


class PropertyUnit(BaseModel):
    """Unit of measurement for AWS IoT SiteWise properties."""

    value: str

    @field_validator('value')
    def validate_unit(cls, v):
        """Validate property unit constraints."""
        validate_string_length(v, 1, 256, 'PropertyUnit')
        validate_control_characters(v, 'PropertyUnit')
        return v


class PropertyAlias(BaseModel):
    """Alias for AWS IoT SiteWise properties."""

    value: str

    @field_validator('value')
    def validate_alias(cls, v):
        """Validate property alias constraints."""
        validate_string_length(v, 1, 1000, 'PropertyAlias')
        validate_control_characters(v, 'PropertyAlias')
        return v


class AssetModelType(BaseModel):
    """Type of AWS IoT SiteWise asset model."""

    value: Optional[Literal['ASSET_MODEL', 'COMPONENT_MODEL']] = None


class DataType(BaseModel):
    """Data type for AWS IoT SiteWise properties."""

    value: Literal['STRING', 'INTEGER', 'DOUBLE', 'BOOLEAN', 'STRUCT']


class ComputeLocation(BaseModel):
    """Compute location for AWS IoT SiteWise processing."""

    value: Literal['EDGE', 'CLOUD']


class ForwardingConfig(BaseModel):
    """Forwarding configuration for AWS IoT SiteWise processing."""

    state: Literal['ENABLED', 'DISABLED']


class MeasurementProcessingConfig(BaseModel):
    """Processing configuration for measurement properties."""

    forwardingConfig: ForwardingConfig


class TransformProcessingConfig(BaseModel):
    """Processing configuration for transform properties."""

    computeLocation: ComputeLocation
    forwardingConfig: Optional[ForwardingConfig] = None


class MetricProcessingConfig(BaseModel):
    """Processing configuration for metric properties."""

    computeLocation: ComputeLocation


class TumblingWindow(BaseModel):
    """Tumbling window configuration for metrics."""

    interval: str
    offset: Optional[str] = None

    @field_validator('interval')
    def validate_interval(cls, v):
        """Validate tumbling window interval constraints."""
        validate_string_length(v, 2, 23, 'TumblingWindow.interval')
        return v

    @field_validator('offset')
    def validate_offset(cls, v):
        """Validate tumbling window offset constraints."""
        if v:
            validate_string_length(v, 2, 25, 'TumblingWindow.offset')
        return v


class MetricWindow(BaseModel):
    """Window configuration for metrics."""

    tumbling: Optional[TumblingWindow] = None


class VariableValue(BaseModel):
    """Variable value reference for expressions."""

    propertyId: Optional[ID] = None
    propertyExternalId: Optional[ExternalId] = None
    hierarchyId: Optional[ID] = None
    hierarchyExternalId: Optional[ExternalId] = None

    @model_validator(mode='after')
    def validate_variable(cls, values):
        """Validate variable value constraints."""
        if not (values.propertyId or values.propertyExternalId):
            raise ValueError(
                "VariableValue must include either 'propertyId' or 'propertyExternalId'."
            )
        return values


class ExpressionVariable(BaseModel):
    """Variable definition for expressions."""

    name: str
    value: VariableValue

    @field_validator('name')
    def validate_name(cls, v):
        """Validate expression variable name constraints."""
        return validate_expression_variable_name(v)


class Attribute(BaseModel):
    """Attribute property definition."""

    defaultValue: Optional[str] = None

    @field_validator('defaultValue')
    def validate_default_value(cls, v):
        """Validate attribute default value constraints."""
        if v:
            validate_control_characters(v, 'Attribute.defaultValue')
        return v


class Transform(BaseModel):
    """Transform property definition."""

    expression: str
    variables: List[ExpressionVariable]
    processingConfig: Optional[TransformProcessingConfig] = None

    @field_validator('expression')
    def validate_expr(cls, v):
        """Validate transform expression constraints."""
        validate_string_length(v, 1, 1024, 'Transform.expression')
        return v


class Measurement(BaseModel):
    """Measurement property definition."""

    processingConfig: Optional[MeasurementProcessingConfig] = None


class Metric(BaseModel):
    """Metric property definition."""

    expression: str
    variables: List[ExpressionVariable]
    window: MetricWindow
    processingConfig: Optional[MetricProcessingConfig] = None

    @field_validator('expression')
    def validate_expr(cls, v):
        """Validate metric expression constraints."""
        validate_string_length(v, 1, 1024, 'Metric.expression')
        return v


class PropertyType(BaseModel):
    """Property type definition for asset model properties."""

    attribute: Optional[Attribute] = None
    transform: Optional[Transform] = None
    metric: Optional[Metric] = None
    measurement: Optional[Measurement] = None

    @model_validator(mode='after')
    def validate_property_type(cls, values):
        """Validate property type constraints."""
        defined = [
            v
            for v in [values.attribute, values.transform, values.metric, values.measurement]
            if v is not None
        ]
        if len(defined) != 1:
            raise ValueError(
                'PropertyType must define exactly one of attribute, transform, metric, or measurement.'
            )
        return values


class AssetModelHierarchy(BaseModel):
    """Asset model hierarchy definition."""

    name: Name
    id: Optional[ID] = None
    externalId: Optional[ExternalId] = None
    childAssetModelId: Optional[ID] = None
    childAssetModelExternalId: Optional[ExternalId] = None

    @model_validator(mode='after')
    def validate_hierarchy(cls, values):
        """Validate asset model hierarchy constraints."""
        combos = [
            (values.id, values.childAssetModelId),
            (values.id, values.childAssetModelExternalId),
            (values.externalId, values.childAssetModelId),
            (values.externalId, values.childAssetModelExternalId),
        ]
        if not any(all(pair) for pair in combos):
            raise ValueError('AssetModelHierarchy must include one valid field combination.')
        return values


class AssetModelProperty(BaseModel):
    """Asset model property definition."""

    name: Name
    dataType: DataType
    type: PropertyType
    id: Optional[ID] = None
    externalId: Optional[ExternalId] = None
    dataTypeSpec: Optional[Name] = None
    unit: Optional[str] = None

    @model_validator(mode='after')
    def validate_property(cls, values):
        """Validate asset model property constraints."""
        if not (values.id or values.externalId):
            raise ValueError('AssetModelProperty must have id or externalId.')
        if values.unit:
            validate_string_length(values.unit, 1, 256, 'Unit')
            validate_control_characters(values.unit, 'Unit')
        return values


class AssetModelCompositeModel(BaseModel):
    """Asset model composite model definition."""

    name: Name
    type: Name
    id: Optional[ID] = None
    externalId: Optional[ExternalId] = None
    parentId: Optional[ID] = None
    parentExternalId: Optional[ExternalId] = None
    composedAssetModelId: Optional[ID] = None
    composedAssetModelExternalId: Optional[ExternalId] = None
    description: Optional[Description] = None
    properties: Optional[List[AssetModelProperty]] = field(default_factory=list)

    @model_validator(mode='after')
    def validate_composite(cls, values):
        """Validate composite model constraints."""
        if not (values.id or values.externalId):
            raise ValueError('CompositeModel must have id or externalId.')
        return values


class AssetModel(BaseModel):
    """Asset model definition."""

    assetModelName: Name
    assetModelId: Optional[ID] = None
    assetModelExternalId: Optional[ExternalId] = None
    assetModelDescription: Optional[Description] = None
    assetModelType: Optional[AssetModelType] = None
    assetModelProperties: Optional[List[AssetModelProperty]] = field(default_factory=list)
    assetModelCompositeModels: Optional[List[AssetModelCompositeModel]] = field(
        default_factory=list
    )
    assetModelHierarchies: Optional[List[AssetModelHierarchy]] = field(default_factory=list)
    tags: Optional[List[Tag]] = field(default_factory=list)

    @model_validator(mode='after')
    def validate_model(cls, values):
        """Validate asset model constraints."""
        if not (values.assetModelId or values.assetModelExternalId):
            raise ValueError('AssetModel must include assetModelId or assetModelExternalId.')
        return values


class AssetProperty(BaseModel):
    """Asset property definition."""

    id: Optional[ID] = None
    externalId: Optional[ExternalId] = None
    alias: Optional[PropertyAlias] = None
    unit: Optional[PropertyUnit] = None
    attributeValue: Optional[AttributeValue] = None
    retainDataOnAliasChange: Literal['TRUE', 'FALSE'] = Field(default='TRUE')
    propertyNotificationState: Optional[Literal['ENABLED', 'DISABLED']] = None

    @model_validator(mode='after')
    def validate_asset_property(cls, values):
        """Validate asset property constraints."""
        # --- anyOf: must have id or externalId ---
        if not (values.id or values.externalId):
            raise ValueError("AssetProperty must include either 'id' or 'externalId'.")
        return values


class AssetHierarchy(BaseModel):
    """Asset hierarchy definition."""

    id: Optional[ID] = None
    externalId: Optional[ExternalId] = None
    childAssetId: Optional[ID] = None
    childAssetExternalId: Optional[ExternalId] = None

    @model_validator(mode='after')
    def validate_asset_hierarchy(cls, values):
        """Validate asset hierarchy constraints."""
        # --- anyOf validation: one of four valid required combinations ---
        valid_combinations = [
            (values.id and values.childAssetId),
            (values.externalId and values.childAssetId),
            (values.id and values.childAssetExternalId),
            (values.externalId and values.childAssetExternalId),
        ]

        if not any(valid_combinations):
            raise ValueError(
                'AssetHierarchy must include one of the valid required combinations: '
                '(id + childAssetId), (externalId + childAssetId), '
                '(id + childAssetExternalId), or (externalId + childAssetExternalId).'
            )

        return values


class Asset(BaseModel):
    """Asset definition."""

    assetName: Name
    assetId: Optional[ID] = None
    assetExternalId: Optional[ExternalId] = None
    assetModelId: Optional[ID] = None
    assetModelExternalId: Optional[ExternalId] = None
    assetDescription: Optional[Description] = None
    assetProperties: Optional[List[AssetProperty]] = field(default_factory=list)
    assetHierarchies: Optional[List[AssetHierarchy]] = field(default_factory=list)
    tags: Optional[List[Tag]] = field(default_factory=list)

    @model_validator(mode='after')
    def validate_asset(cls, values):
        """Validate asset constraints."""
        # --- anyOf validation: one of four valid required combinations ---
        valid_combinations = [
            (values.assetId and values.assetModelId),
            (values.assetExternalId and values.assetModelId),
            (values.assetId and values.assetModelExternalId),
            (values.assetExternalId and values.assetModelExternalId),
        ]

        if not any(valid_combinations):
            raise ValueError(
                'Asset must include one of the valid required combinations: '
                '(assetId + assetModelId), (assetExternalId + assetModelId), '
                '(assetId + assetModelExternalId), or (assetExternalId + assetModelExternalId).'
            )

        return values


class BulkImportSchema(BaseModel):
    """BulkImportSchema.

    Represents the top-level metadata transfer job resource schema for AWS IoT SiteWise.

    Fields:
        assetModels: List of AssetModel objects defining reusable model templates.
        assets: List of Asset objects instantiated from asset models.
    """

    assetModels: Optional[List['AssetModel']] = field(default_factory=list)
    assets: Optional[List['Asset']] = field(default_factory=list)

    @model_validator(mode='after')
    def validate_bulk_import_schema(cls, values):
        """Validate bulk import schema constraints."""
        # Cross-check: ensure all assets reference valid model external IDs
        if not values.assets or not values.assetModels:
            return values

        model_ids = {
            m.assetModelExternalId.value
            for m in values.assetModels
            if getattr(m, 'assetModelExternalId', None)
        }

        for asset in values.assets:
            asset_model_ext = (
                asset.assetModelExternalId.value
                if getattr(asset, 'assetModelExternalId', None)
                else None
            )
            if asset_model_ext and asset_model_ext not in model_ids:
                raise ValueError(
                    f"Asset '{asset.assetExternalId.value if asset.assetExternalId else asset.assetName.value}' "
                    f"references unknown AssetModelExternalId '{asset_model_ext}'."
                )
        return values
