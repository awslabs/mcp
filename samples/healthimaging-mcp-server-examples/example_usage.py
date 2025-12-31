#!/usr/bin/env python3
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

"""Example usage of HealthImaging MCP Server tools.

This script demonstrates how to use the 39 available tools programmatically.

Prerequisites:
- MCP server configured and running
- AWS credentials with HealthImaging permissions
- Access to a HealthImaging datastore
"""

import asyncio


# Example configuration - update with your values
DATASTORE_ID = 'example-datastore-id-12345'  # Replace with your datastore ID
IMAGE_SET_ID = 'example-image-set-id-67890'  # Replace with your image set ID
PATIENT_ID = 'EXAMPLE_PATIENT_ID'  # Replace with actual patient ID
STUDY_UID = 'example.study.uid.1.2.3.4.5'  # Replace with actual study UID
SERIES_UID = 'example.series.uid.1.2.3.4.5.6'  # Replace with actual series UID


class HealthImagingExamples:
    """Examples demonstrating all 39 HealthImaging MCP tools."""

    def __init__(self):
        """Initialize the examples class."""
        self.results = {}

    async def run_datastore_examples(self):
        """Demonstrate datastore management tools (4 tools)."""
        print('🏥 Datastore Management Examples')
        print('=' * 50)

        # 1. List datastores
        print('1. Listing all datastores...')
        # In MCP client: "List my HealthImaging datastores"

        # 2. Get datastore details
        print('2. Getting datastore details...')
        # In MCP client: f"Get details for datastore {DATASTORE_ID}"

        # 3. Create datastore (requires permissions)
        print('3. Creating new datastore...')
        # In MCP client: "Create a new HealthImaging datastore named 'example-datastore'"

        # 4. Delete datastore (requires permissions)
        print('4. Deleting datastore...')
        # In MCP client: f"Delete HealthImaging datastore {DATASTORE_ID}"

    async def run_image_set_examples(self):
        """Demonstrate image set operations (7 tools)."""
        print('\n🖼️  Image Set Operations Examples')
        print('=' * 50)

        # 1. Search image sets
        print('1. Searching image sets...')
        # In MCP client: f"Search for image sets in datastore {DATASTORE_ID} where patient ID is '{PATIENT_ID}'"

        # 2. Get image set
        print('2. Getting image set details...')
        # In MCP client: f"Get image set {IMAGE_SET_ID} from datastore {DATASTORE_ID}"

        # 3. Get image set metadata
        print('3. Getting DICOM metadata...')
        # In MCP client: f"Get metadata for image set {IMAGE_SET_ID} in datastore {DATASTORE_ID}"

        # 4. List image set versions
        print('4. Listing image set versions...')
        # In MCP client: f"List versions for image set {IMAGE_SET_ID} in datastore {DATASTORE_ID}"

        # 5. Update image set metadata
        print('5. Updating image set metadata...')
        # In MCP client: f"Update metadata for image set {IMAGE_SET_ID} in datastore {DATASTORE_ID}"

        # 6. Copy image set
        print('6. Copying image set...')
        # In MCP client: f"Copy image set {IMAGE_SET_ID} from datastore {DATASTORE_ID} to destination datastore"

        # 7. Delete image set
        print('7. Deleting image set...')
        # In MCP client: f"Delete image set {IMAGE_SET_ID} from datastore {DATASTORE_ID}"

    async def run_advanced_dicom_examples(self):
        """Demonstrate advanced DICOM operations (18 tools)."""
        print('\n🔬 Advanced DICOM Operations Examples')
        print('=' * 50)

        # Enhanced Search Operations (3 tools)
        print('Enhanced Search Operations:')
        print('- Search by patient ID: Search for all data for a specific patient in datastore')
        print('- Search by study UID: Search for study with specific UID in datastore')
        print('- Search by series UID: Search for series with specific UID in datastore')

        # Data Analysis Operations (3 tools)
        print('\nData Analysis Operations:')
        print('- Get patient studies: Get all studies for a specific patient in datastore')
        print('- Get patient series: Get all series for a specific patient in datastore')
        print(
            '- Get study primary image sets: Get primary image sets for a specific study in datastore'
        )

        # Delete Operations (5 tools)
        print('\nDelete Operations (GDPR Compliance):')
        print('- Delete patient studies: Delete all studies for a specific patient in datastore')
        print('- Delete study: Delete study with specific UID in datastore')
        print('- Delete series by UID: Delete series with specific UID in datastore')
        print('- Delete instance in study: Delete instance from specific study in datastore')
        print('- Delete instance in series: Delete instance from specific series in datastore')

        # Metadata Update Operations (3 tools)
        print('\nMetadata Update Operations:')
        print(
            '- Get series primary image set: Get primary image set for specific series in datastore'
        )
        print(
            '- Get patient DICOMweb studies: Get DICOMweb studies for specific patient in datastore'
        )
        print(
            '- Update patient study metadata: Update patient and study metadata for specific patient in datastore'
        )

        # Bulk Operations (2 tools)
        print('\nBulk Operations:')
        print(
            '- Bulk update patient metadata: Bulk update metadata for specific patient in datastore'
        )
        print(
            "- Bulk delete by criteria: Bulk delete image sets in datastore where modality is 'CR'"
        )

        # DICOM Hierarchy Operations (2 tools)
        print('\nDICOM Hierarchy Operations:')
        print('- Remove series from image set: Remove specific series from image set in datastore')
        print('- Remove instance from image set: Remove instance from image set in datastore')

    async def run_import_export_examples(self):
        """Demonstrate DICOM import/export jobs (6 tools)."""
        print('\n📥📤 Import/Export Job Examples')
        print('=' * 50)

        # Import operations
        print('Import Operations:')
        print('- Start DICOM import job: Start import from S3 bucket')
        print('- Get DICOM import job: Monitor import job status')
        print('- List DICOM import jobs: List all import jobs')

        # Export operations
        print('\nExport Operations:')
        print('- Start DICOM export job: Start export to S3 bucket')
        print('- Get DICOM export job: Monitor export job status')
        print('- List DICOM export jobs: List all export jobs')

    async def run_tagging_examples(self):
        """Demonstrate resource tagging (3 tools)."""
        print('\n🏷️  Resource Tagging Examples')
        print('=' * 50)

        print('Tagging Operations:')
        print('- List tags: List tags for datastore resource')
        print('- Tag resource: Add Environment=Production tag to resource')
        print('- Untag resource: Remove Environment tag from resource')

    async def run_workflow_examples(self):
        """Demonstrate common medical imaging workflows."""
        print('\n🔄 Common Workflow Examples')
        print('=' * 50)

        print('Medical Research Workflow:')
        print('1. Discovery: List datastores to find available data')
        print('2. Search: Search by patient ID to find specific data')
        print('3. Analysis: Get patient studies for comprehensive overview')
        print('4. Access: Get image set metadata to extract DICOM data')
        print('5. Processing: Get image frames for analysis')

        print('\nData Management Workflow:')
        print('1. Import: Start DICOM import job from S3')
        print('2. Monitor: Check import job status')
        print('3. Organize: Tag resources with metadata')
        print('4. Update: Update image set metadata as needed')
        print('5. Archive: Export data for long-term storage')

        print('\nGDPR Compliance Workflow:')
        print('1. Identify: Search by patient ID to find all data')
        print('2. Analyze: Get patient studies to understand scope')
        print('3. Remove: Delete patient studies for complete removal')
        print('4. Verify: Search again to confirm deletion')

    async def run_all_examples(self):
        """Run all example demonstrations."""
        print('🏥 HealthImaging MCP Server - All 39 Tools Examples')
        print('=' * 60)
        print('This script demonstrates all available tools and common workflows.')
        print('Note: These are example commands for MCP client usage.\n')

        await self.run_datastore_examples()
        await self.run_image_set_examples()
        await self.run_advanced_dicom_examples()
        await self.run_import_export_examples()
        await self.run_tagging_examples()
        await self.run_workflow_examples()

        print('\n✅ All examples completed!')
        print('\nTo use these examples:')
        print('1. Configure the HealthImaging MCP server in your MCP client')
        print('2. Update the configuration variables at the top of this script')
        print('3. Use the example commands in your MCP client interface')
        print('4. Refer to the README.md for detailed usage instructions')


def main():
    """Main function to run all examples."""
    examples = HealthImagingExamples()
    asyncio.run(examples.run_all_examples())


if __name__ == '__main__':
    main()
