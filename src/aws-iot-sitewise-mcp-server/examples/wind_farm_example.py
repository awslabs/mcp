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

#!/usr/bin/env python3
"""Example script demonstrating AWS IoT SiteWise MCP server usage.

This example shows how to:
1. Create asset models for wind turbines
2. Create assets from the models
3. Set up asset hierarchies
4. Ingest sample data

Prerequisites:
- AWS credentials configured
- IoT SiteWise permissions
- MCP server running
"""

from datetime import datetime, timezone
from typing import Any, Dict


def create_wind_turbine_model() -> Dict[str, Any]:
    """Create an asset model for wind turbines."""
    # Define properties for the wind turbine model
    # This would be used in the actual MCP server call (see commented code
    # below)
    # Example properties structure:
    # properties = [
    #     {
    #         "name": "WindSpeed",
    #         "dataType": "DOUBLE",
    #         "unit": "m/s",
    #         "type": {"measurement": {}},
    #     },
    #     {
    #         "name": "PowerOutput",
    #         "dataType": "DOUBLE",
    #         "unit": "kW",
    #         "type": {"measurement": {}},
    #     },
    #     {
    #         "name": "RotorSpeed",
    #         "dataType": "DOUBLE",
    #         "unit": "rpm",
    #         "type": {"measurement": {}},
    #     },
    #     {
    #         "name": "Temperature",
    #         "dataType": "DOUBLE",
    #         "unit": "Celsius",
    #         "type": {"measurement": {}},
    #     },
    #     {
    #         "name": "Efficiency",
    #         "dataType": "DOUBLE",
    #         "unit": "Percent",
    #         "type": {
    #             "transform": {
    #                 "expression": "PowerOutput / (WindSpeed * 100)",
    #                 "variables": [
    #                     {"name": "PowerOutput", "value": {"propertyId": "PowerOutput"}},
    #                     {"name": "WindSpeed", "value": {"propertyId": "WindSpeed"}},
    #                 ],
    #             }
    #         },
    #     },
    #     {
    #         "name": "Status",
    #         "dataType": "STRING",
    #         "type": {"attribute": {"defaultValue": "OPERATIONAL"}},
    #     },
    # ]

    # Create the asset model
    print('Creating wind turbine asset model...')
    # This would be called through the MCP server
    # result = sitewise_create_asset_model(
    #     asset_model_name="WindTurbineModel",
    #     asset_model_description="Asset model for wind turbine monitoring",
    #     asset_model_properties=properties
    # )

    # Simulated response for demonstration
    result = {
        'success': True,
        'asset_model_id': 'wind-turbine-model-123',
        'asset_model_arn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/wind-turbine-model-123',
    }

    print(f'✓ Created asset model: {result["asset_model_id"]}')
    return result


def create_wind_farm_model() -> Dict[str, Any]:
    """Create an asset model for wind farms."""
    # Define hierarchies for the wind farm
    # This would be used in the actual MCP server call (see commented code
    # below)
    # hierarchies = [{"name": "Turbines", "childAssetModelId": "wind-turbine-model-123"}]

    # Define aggregate properties for the wind farm
    # This would be used in the actual MCP server call (see commented code
    # below)
    # properties = [
    #     {
    #         "name": "TotalPowerOutput",
    #         "dataType": "DOUBLE",
    #         "unit": "MW",
    #         "type": {
    #             "metric": {
    #                 "expression": "sum(PowerOutput) / 1000",
    #                 "variables": [
    #                     {
    #                         "name": "PowerOutput",
    #                         "value": {
    #                             "hierarchyId": "Turbines",
    #                             "propertyId": "PowerOutput",
    #                         },
    #                     }
    #                 ],
    #                 "window": {"tumbling": {"interval": "1m"}},
    #             }
    #         },
    #     },
    #     {
    #         "name": "AverageWindSpeed",
    #         "dataType": "DOUBLE",
    #         "unit": "m/s",
    #         "type": {
    #             "metric": {
    #                 "expression": "avg(WindSpeed)",
    #                 "variables": [
    #                     {
    #                         "name": "WindSpeed",
    #                         "value": {
    #                             "hierarchyId": "Turbines",
    #                             "propertyId": "WindSpeed",
    #                         },
    #                     }
    #                 ],
    #                 "window": {"tumbling": {"interval": "5m"}},
    #             }
    #         },
    #     },
    # ]

    print('Creating wind farm asset model...')
    # This would be called through the MCP server
    # result = sitewise_create_asset_model(
    #     asset_model_name="WindFarmModel",
    #     asset_model_description="Asset model for wind farm management",
    #     asset_model_properties=properties,
    #     asset_model_hierarchies=hierarchies
    # )

    # Simulated response for demonstration
    result = {
        'success': True,
        'asset_model_id': 'wind-farm-model-456',
        'asset_model_arn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/wind-farm-model-456',
    }

    print(f'✓ Created wind farm model: {result["asset_model_id"]}')
    return result


def create_assets() -> Dict[str, Any]:
    """Create wind farm and turbine assets."""
    assets = {}

    # Create wind farm asset
    print('Creating wind farm asset...')
    # wind_farm = sitewise_create_asset(
    #     asset_name="North Field Wind Farm",
    #     asset_model_id="wind-farm-model-456",
    #     asset_description="Primary wind farm in the north field"
    # )

    wind_farm = {
        'success': True,
        'asset_id': 'wind-farm-001',
        'asset_arn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset/wind-farm-001',
    }
    assets['wind_farm'] = wind_farm
    print(f'✓ Created wind farm: {wind_farm["asset_id"]}')

    # Create turbine assets
    turbines = []
    for i in range(1, 6):  # Create 5 turbines
        print(f'Creating wind turbine {i}...')
        # turbine = sitewise_create_asset(
        #     asset_name=f"WindTurbine{i:03d}",
        #     asset_model_id="wind-turbine-model-123",
        #     asset_description=f"Wind turbine #{i} in the north field"
        # )

        turbine = {
            'success': True,
            'asset_id': f'turbine-{i:03d}',
            'asset_arn': f'arn:aws:iotsitewise:us-east-1:123456789012:asset/turbine-{i:03d}',
        }
        turbines.append(turbine)
        print(f'✓ Created turbine: {turbine["asset_id"]}')

        # Associate turbine with wind farm
        print(f'Associating turbine {i} with wind farm...')
        # association = sitewise_associate_assets(
        #     asset_id=wind_farm["asset_id"],
        #     hierarchy_id="Turbines",
        #     child_asset_id=turbine["asset_id"]
        # )
        print(f'✓ Associated turbine {i} with wind farm')

    assets['turbines'] = turbines
    return assets


def ingest_sample_data(assets: Dict[str, Any]) -> None:
    """Ingest sample data for the wind turbines."""
    print('Ingesting sample data...')

    # Generate sample data entries
    entries = []
    current_time = int(datetime.now(timezone.utc).timestamp())

    for i, turbine in enumerate(assets['turbines'], 1):
        # Simulate different operating conditions for each turbine
        wind_speed = 8.5 + (i * 0.5)  # 9.0 to 11.0 m/s
        power_output = wind_speed * 150  # Simplified power calculation
        rotor_speed = wind_speed * 12  # RPM
        temperature = 25 + (i * 2)  # 27 to 35°C

        # Create entries for each property
        turbine_entries = [
            {
                'entryId': f'turbine-{i}-wind-speed',
                'assetId': turbine['asset_id'],
                'propertyAlias': f'/windfarm/turbine{i}/windspeed',
                'propertyValues': [
                    {
                        'value': {'doubleValue': wind_speed},
                        'timestamp': {'timeInSeconds': current_time},
                        'quality': 'GOOD',
                    }
                ],
            },
            {
                'entryId': f'turbine-{i}-power-output',
                'assetId': turbine['asset_id'],
                'propertyAlias': f'/windfarm/turbine{i}/power',
                'propertyValues': [
                    {
                        'value': {'doubleValue': power_output},
                        'timestamp': {'timeInSeconds': current_time},
                        'quality': 'GOOD',
                    }
                ],
            },
            {
                'entryId': f'turbine-{i}-rotor-speed',
                'assetId': turbine['asset_id'],
                'propertyAlias': f'/windfarm/turbine{i}/rotor',
                'propertyValues': [
                    {
                        'value': {'doubleValue': rotor_speed},
                        'timestamp': {'timeInSeconds': current_time},
                        'quality': 'GOOD',
                    }
                ],
            },
            {
                'entryId': f'turbine-{i}-temperature',
                'assetId': turbine['asset_id'],
                'propertyAlias': f'/windfarm/turbine{i}/temp',
                'propertyValues': [
                    {
                        'value': {'doubleValue': temperature},
                        'timestamp': {'timeInSeconds': current_time},
                        'quality': 'GOOD',
                    }
                ],
            },
        ]
        entries.extend(turbine_entries)

    # Batch put the data
    # result = sitewise_batch_put_asset_property_value(entries=entries)

    print(f'✓ Ingested data for {len(assets["turbines"])} turbines')
    print(f'  - Total data points: {len(entries)}')


def main():
    """Main example execution."""
    print('🌪️  Wind Farm IoT SiteWise Setup Example')
    print('=' * 50)

    try:
        # Step 1: Create asset models
        print('\n📋 Step 1: Creating Asset Models')
        create_wind_turbine_model()  # Used for demonstration
        create_wind_farm_model()  # Used for demonstration

        # Step 2: Create assets and hierarchies
        print('\n🏗️  Step 2: Creating Assets and Hierarchies')
        assets = create_assets()

        # Step 3: Ingest sample data
        print('\n📊 Step 3: Ingesting Sample Data')
        ingest_sample_data(assets)

        # Summary
        print('\n✅ Setup Complete!')
        print('=' * 50)
        print(f'Wind Farm Asset ID: {assets["wind_farm"]["asset_id"]}')
        print(f'Number of Turbines: {len(assets["turbines"])}')

        print('\n🎯 Next Steps:')
        print('1. Configure property aliases for data ingestion')
        print('2. Set up alarms and notifications')
        print('3. Configure access policies for team members')
        print('4. Set up data retention and storage policies')
        print('5. Query and analyze the ingested data')

    except Exception as e:
        print(f'❌ Error during setup: {str(e)}')
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
