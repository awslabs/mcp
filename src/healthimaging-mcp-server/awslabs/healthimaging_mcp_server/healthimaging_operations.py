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

"""AWS HealthImaging client for medical imaging operations."""

# Standard library imports
# Third-party imports
import boto3
import json
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)

# HealthImaging API limits
MAX_SEARCH_COUNT = 100  # Maximum number of resources per search request
DATASTORE_ID_LENGTH = 32  # AWS HealthImaging datastore ID length


def validate_datastore_id(datastore_id: str) -> str:
    """Validate AWS HealthImaging datastore ID format."""
    if not datastore_id or len(datastore_id) != DATASTORE_ID_LENGTH:
        raise ValueError(f'Datastore ID must be {DATASTORE_ID_LENGTH} characters')
    return datastore_id


class HealthImagingSearchError(Exception):
    """Exception raised for HealthImaging search parameter errors."""

    def __init__(self, message: str, invalid_params: Optional[list[str]] = None):
        """Initialize HealthImaging search error with message and optional invalid parameters."""
        self.invalid_params = invalid_params or []
        super().__init__(message)


class HealthImagingClient:
    """Client for AWS HealthImaging operations."""

    def __init__(self, region_name: Optional[str] = None):
        """Initialize the HealthImaging client."""
        try:
            self.session = boto3.Session()
            self.healthimaging_client = self.session.client(
                'medical-imaging', region_name=region_name
            )
            self.region = region_name or self.session.region_name or 'us-east-1'

        except NoCredentialsError:
            logger.error('AWS credentials not found. Please configure your credentials.')
            raise

    async def list_datastores(self, filter_status: Optional[str] = None) -> Dict[str, Any]:
        """List HealthImaging datastores."""
        try:
            params = {'maxResults': 50}
            if filter_status:
                params['datastoreStatus'] = filter_status

            response = self.healthimaging_client.list_datastores(**params)
            return response

        except ClientError as e:
            logger.error(f'Error listing datastores: {e}')
            raise

    async def get_datastore_details(self, datastore_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific datastore."""
        try:
            response = self.healthimaging_client.get_datastore(datastoreId=datastore_id)
            return response

        except ClientError as e:
            logger.error(f'Error getting datastore {datastore_id}: {e}')
            raise

    async def search_image_sets(
        self,
        datastore_id: str,
        search_criteria: Optional[Dict[str, Any]] = None,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        """Search for image sets in a datastore."""
        try:
            params = {
                'datastoreId': datastore_id,
                'maxResults': min(max_results, MAX_SEARCH_COUNT),
            }

            if search_criteria:
                params['searchCriteria'] = search_criteria

            response = self.healthimaging_client.search_image_sets(**params)
            return response

        except ClientError as e:
            logger.error(f'Error searching image sets: {e}')
            raise

    async def get_image_set(self, datastore_id: str, image_set_id: str) -> Dict[str, Any]:
        """Get metadata for a specific image set."""
        try:
            response = self.healthimaging_client.get_image_set(
                datastoreId=datastore_id, imageSetId=image_set_id
            )
            return response

        except ClientError as e:
            logger.error(f'Error getting image set {image_set_id}: {e}')
            raise

    async def get_image_set_metadata(
        self, datastore_id: str, image_set_id: str, version_id: Optional[str] = None
    ) -> str:
        """Get detailed DICOM metadata for an image set."""
        try:
            params = {'datastoreId': datastore_id, 'imageSetId': image_set_id}

            if version_id:
                params['versionId'] = version_id

            response = self.healthimaging_client.get_image_set_metadata(**params)

            # Read the streaming body
            metadata = response['imageSetMetadataBlob'].read().decode('utf-8')
            return metadata

        except ClientError as e:
            logger.error(f'Error getting image set metadata: {e}')
            raise

    async def get_image_frame(
        self, datastore_id: str, image_set_id: str, image_frame_id: str
    ) -> Dict[str, Any]:
        """Get information about retrieving a specific image frame."""
        try:
            response = self.healthimaging_client.get_image_frame(
                datastoreId=datastore_id,
                imageSetId=image_set_id,
                imageFrameInformation={'imageFrameId': image_frame_id},
            )

            # Return metadata about the frame (not the binary data)
            return {
                'datastoreId': datastore_id,
                'imageSetId': image_set_id,
                'imageFrameId': image_frame_id,
                'contentType': response.get('contentType'),
                'message': 'Frame data available (binary data not shown)',
            }

        except ClientError as e:
            logger.error(f'Error getting image frame: {e}')
            raise

    async def list_image_set_versions(
        self, datastore_id: str, image_set_id: str, max_results: int = 50
    ) -> Dict[str, Any]:
        """List all versions of an image set."""
        try:
            response = self.healthimaging_client.list_image_set_versions(
                datastoreId=datastore_id,
                imageSetId=image_set_id,
                maxResults=min(max_results, MAX_SEARCH_COUNT),
            )
            return response

        except ClientError as e:
            logger.error(f'Error listing image set versions: {e}')
            raise

    # DELETE OPERATIONS

    async def delete_image_set(self, datastore_id: str, image_set_id: str) -> Dict[str, Any]:
        """Delete an image set."""
        try:
            response = self.healthimaging_client.delete_image_set(
                datastoreId=datastore_id, imageSetId=image_set_id
            )
            return response

        except ClientError as e:
            logger.error(f'Error deleting image set {image_set_id}: {e}')
            raise

    async def delete_patient_studies(self, datastore_id: str, patient_id: str) -> Dict[str, Any]:
        """Delete all studies for a specific patient."""
        try:
            # First, search for all image sets for this patient
            search_response = await self.search_image_sets(
                datastore_id=datastore_id,
                search_criteria={
                    'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
                },
                max_results=MAX_SEARCH_COUNT,
            )

            deleted_image_sets = []

            if 'imageSetsMetadataSummaries' in search_response:
                for image_set in search_response['imageSetsMetadataSummaries']:
                    try:
                        delete_response = await self.delete_image_set(
                            datastore_id=datastore_id, image_set_id=image_set['imageSetId']
                        )
                        deleted_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'deleted',
                                'response': delete_response,
                            }
                        )
                    except ClientError as e:
                        deleted_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'error',
                                'error': str(e),
                            }
                        )

            return {
                'patientId': patient_id,
                'deletedImageSets': deleted_image_sets,
                'totalDeleted': len(
                    [img for img in deleted_image_sets if img['status'] == 'deleted']
                ),
            }

        except ClientError as e:
            logger.error(f'Error deleting patient studies: {e}')
            raise

    async def delete_study(self, datastore_id: str, study_instance_uid: str) -> Dict[str, Any]:
        """Delete all image sets for a specific study."""
        try:
            # Search for all image sets for this study
            search_response = await self.search_image_sets(
                datastore_id=datastore_id,
                search_criteria={
                    'filters': [
                        {
                            'values': [{'DICOMStudyInstanceUID': study_instance_uid}],
                            'operator': 'EQUAL',
                        }
                    ]
                },
                max_results=MAX_SEARCH_COUNT,
            )

            deleted_image_sets = []

            if 'imageSetsMetadataSummaries' in search_response:
                for image_set in search_response['imageSetsMetadataSummaries']:
                    try:
                        delete_response = await self.delete_image_set(
                            datastore_id=datastore_id, image_set_id=image_set['imageSetId']
                        )
                        deleted_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'deleted',
                                'response': delete_response,
                            }
                        )
                    except ClientError as e:
                        deleted_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'error',
                                'error': str(e),
                            }
                        )

            return {
                'studyInstanceUID': study_instance_uid,
                'deletedImageSets': deleted_image_sets,
                'totalDeleted': len(
                    [img for img in deleted_image_sets if img['status'] == 'deleted']
                ),
            }

        except ClientError as e:
            logger.error(f'Error deleting study {study_instance_uid}: {e}')
            raise

    # METADATA UPDATE OPERATIONS

    async def update_image_set_metadata(
        self, datastore_id: str, image_set_id: str, version_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update DICOM metadata for an image set."""
        try:
            response = self.healthimaging_client.update_image_set_metadata(
                datastoreId=datastore_id,
                imageSetId=image_set_id,
                latestVersionId=version_id,
                updateImageSetMetadataUpdates=updates,
            )
            return response

        except ClientError as e:
            logger.error(f'Error updating image set metadata: {e}')
            raise

    async def remove_series_from_image_set(
        self, datastore_id: str, image_set_id: str, series_instance_uid: str
    ) -> Dict[str, Any]:
        """Remove a specific series from an image set."""
        try:
            # Get current metadata to find the version
            image_set_info = await self.get_image_set(datastore_id, image_set_id)
            version_id = image_set_info['versionId']

            # Create update to remove the series
            updates = {
                'DICOMUpdates': {
                    'removableAttributes': json.dumps(
                        {'SchemaVersion': '1.1', 'Series': {series_instance_uid: {}}}
                    ).encode()
                }
            }

            response = await self.update_image_set_metadata(
                datastore_id=datastore_id,
                image_set_id=image_set_id,
                version_id=version_id,
                updates=updates,
            )
            return response

        except ClientError as e:
            logger.error(f'Error removing series {series_instance_uid}: {e}')
            raise

    async def remove_instance_from_image_set(
        self,
        datastore_id: str,
        image_set_id: str,
        sop_instance_uid: str,
        series_instance_uid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Remove a specific instance from an image set."""
        try:
            # Get current metadata
            image_set_info = await self.get_image_set(datastore_id, image_set_id)
            version_id = image_set_info['versionId']

            if not series_instance_uid:
                # Need to find the series containing this instance
                metadata = await self.get_image_set_metadata(datastore_id, image_set_id)
                metadata_json = json.loads(metadata)

                # Find the series containing this SOP instance
                for study in (
                    metadata_json.get('Study', {})
                    .get('DICOM', {})
                    .get('StudyInstanceUID', {})
                    .values()
                ):
                    for series_uid, series_data in study.get('Series', {}).items():
                        if sop_instance_uid in series_data.get('Instances', {}):
                            series_instance_uid = series_uid
                            break
                    if series_instance_uid:
                        break

            if not series_instance_uid:
                raise ValueError(f'Could not find series containing instance {sop_instance_uid}')

            # Create update to remove the instance
            updates = {
                'DICOMUpdates': {
                    'removableAttributes': json.dumps(
                        {
                            'SchemaVersion': '1.1',
                            'Study': {
                                # We need the study UID - get from metadata
                                'PLACEHOLDER_STUDY_UID': {
                                    'Series': {
                                        series_instance_uid: {'Instances': {sop_instance_uid: {}}}
                                    }
                                }
                            },
                        }
                    ).encode()
                }
            }

            response = await self.update_image_set_metadata(
                datastore_id=datastore_id,
                image_set_id=image_set_id,
                version_id=version_id,
                updates=updates,
            )
            return response

        except ClientError as e:
            logger.error(f'Error removing instance {sop_instance_uid}: {e}')
            raise

    # ENHANCED SEARCH OPERATIONS

    async def search_by_patient_id(
        self, datastore_id: str, patient_id: str, include_primary_only: bool = False
    ) -> Dict[str, Any]:
        """Enhanced search for all data related to a patient."""
        try:
            search_response = await self.search_image_sets(
                datastore_id=datastore_id,
                search_criteria={
                    'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
                },
                max_results=MAX_SEARCH_COUNT,
            )

            if include_primary_only and 'imageSetsMetadataSummaries' in search_response:
                search_response['imageSetsMetadataSummaries'] = [
                    img
                    for img in search_response['imageSetsMetadataSummaries']
                    if img.get('isPrimary', False)
                ]

            # Extract unique study and series UIDs
            study_uids = set()
            series_uids = set()

            if 'imageSetsMetadataSummaries' in search_response:
                for img_set in search_response['imageSetsMetadataSummaries']:
                    dicom_tags = img_set.get('DICOMTags', {})
                    if 'DICOMStudyInstanceUID' in dicom_tags:
                        study_uids.add(dicom_tags['DICOMStudyInstanceUID'])
                    if 'DICOMSeriesInstanceUID' in dicom_tags:
                        series_uids.add(dicom_tags['DICOMSeriesInstanceUID'])

            search_response['uniqueStudyUIDs'] = list(study_uids)
            search_response['uniqueSeriesUIDs'] = list(series_uids)
            search_response['patientId'] = patient_id

            return search_response

        except ClientError as e:
            logger.error(f'Error searching by patient ID: {e}')
            raise

    async def search_by_study_uid(
        self, datastore_id: str, study_instance_uid: str, include_primary_only: bool = False
    ) -> Dict[str, Any]:
        """Enhanced search for all image sets in a study."""
        try:
            search_response = await self.search_image_sets(
                datastore_id=datastore_id,
                search_criteria={
                    'filters': [
                        {
                            'values': [{'DICOMStudyInstanceUID': study_instance_uid}],
                            'operator': 'EQUAL',
                        }
                    ]
                },
                max_results=MAX_SEARCH_COUNT,
            )

            if include_primary_only and 'imageSetsMetadataSummaries' in search_response:
                search_response['imageSetsMetadataSummaries'] = [
                    img
                    for img in search_response['imageSetsMetadataSummaries']
                    if img.get('isPrimary', False)
                ]

            search_response['studyInstanceUID'] = study_instance_uid
            return search_response

        except ClientError as e:
            logger.error(f'Error searching by study UID {study_instance_uid}: {e}')
            raise

    async def search_by_series_uid(
        self, datastore_id: str, series_instance_uid: str
    ) -> Dict[str, Any]:
        """Enhanced search for image sets containing a specific series."""
        try:
            search_response = await self.search_image_sets(
                datastore_id=datastore_id,
                search_criteria={
                    'filters': [
                        {
                            'values': [{'DICOMSeriesInstanceUID': series_instance_uid}],
                            'operator': 'EQUAL',
                        }
                    ]
                },
                max_results=MAX_SEARCH_COUNT,
            )

            search_response['seriesInstanceUID'] = series_instance_uid
            return search_response

        except ClientError as e:
            logger.error(f'Error searching by series UID {series_instance_uid}: {e}')
            raise

    # DATA ANALYSIS OPERATIONS

    async def get_patient_studies(self, datastore_id: str, patient_id: str) -> Dict[str, Any]:
        """Get all studies for a patient with study-level DICOM metadata."""
        try:
            # Get all primary image sets for the patient
            search_response = await self.search_by_patient_id(
                datastore_id=datastore_id, patient_id=patient_id, include_primary_only=True
            )

            studies = []
            study_uids = set()

            if 'imageSetsMetadataSummaries' in search_response:
                for img_set in search_response['imageSetsMetadataSummaries']:
                    dicom_tags = img_set.get('DICOMTags', {})
                    study_uid = dicom_tags.get('DICOMStudyInstanceUID')

                    if study_uid and study_uid not in study_uids:
                        study_uids.add(study_uid)

                        # Get detailed metadata for this study
                        try:
                            metadata = await self.get_image_set_metadata(
                                datastore_id=datastore_id, image_set_id=img_set['imageSetId']
                            )
                            metadata_json = json.loads(metadata)

                            # Extract study-level information
                            study_info = {
                                'studyInstanceUID': study_uid,
                                'imageSetId': img_set['imageSetId'],
                                'patientMetadata': metadata_json.get('Patient', {}),
                                'studyMetadata': metadata_json.get('Study', {}),
                                'createdAt': img_set.get('createdAt'),
                                'updatedAt': img_set.get('updatedAt'),
                            }
                            studies.append(study_info)

                        except Exception as e:
                            logger.warning(
                                f'Could not get metadata for image set {img_set["imageSetId"]}: {e}'
                            )

            return {'patientId': patient_id, 'studies': studies, 'totalStudies': len(studies)}

        except ClientError as e:
            logger.error(f'Error getting patient studies: {e}')
            raise

    async def get_patient_series(self, datastore_id: str, patient_id: str) -> Dict[str, Any]:
        """Get all series UIDs for a patient."""
        try:
            search_response = await self.search_by_patient_id(
                datastore_id=datastore_id, patient_id=patient_id
            )

            return {
                'patientId': patient_id,
                'seriesUIDs': search_response.get('uniqueSeriesUIDs', []),
                'totalSeries': len(search_response.get('uniqueSeriesUIDs', [])),
            }

        except ClientError as e:
            logger.error(f'Error getting patient series: {e}')
            raise

    async def get_study_primary_image_sets(
        self, datastore_id: str, study_instance_uid: str
    ) -> Dict[str, Any]:
        """Get primary image sets for a study."""
        try:
            search_response = await self.search_by_study_uid(
                datastore_id=datastore_id,
                study_instance_uid=study_instance_uid,
                include_primary_only=True,
            )

            return search_response

        except ClientError as e:
            logger.error(f'Error getting primary image sets for study {study_instance_uid}: {e}')
            raise

    # BULK OPERATIONS

    async def bulk_update_patient_metadata(
        self, datastore_id: str, patient_id: str, new_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update patient metadata across all studies for a patient."""
        try:
            # Get all image sets for the patient
            search_response = await self.search_by_patient_id(
                datastore_id=datastore_id, patient_id=patient_id
            )

            updated_image_sets = []

            if 'imageSetsMetadataSummaries' in search_response:
                for img_set in search_response['imageSetsMetadataSummaries']:
                    try:
                        # Create update for patient metadata
                        updates = {
                            'DICOMUpdates': {
                                'updatableAttributes': json.dumps(
                                    {'SchemaVersion': '1.1', 'Patient': {'DICOM': new_metadata}}
                                ).encode()
                            }
                        }

                        # Get current version
                        image_set_info = await self.get_image_set(
                            datastore_id, img_set['imageSetId']
                        )
                        version_id = image_set_info['versionId']

                        update_response = await self.update_image_set_metadata(
                            datastore_id=datastore_id,
                            image_set_id=img_set['imageSetId'],
                            version_id=version_id,
                            updates=updates,
                        )

                        updated_image_sets.append(
                            {
                                'imageSetId': img_set['imageSetId'],
                                'status': 'updated',
                                'response': update_response,
                            }
                        )

                    except ClientError as e:
                        updated_image_sets.append(
                            {
                                'imageSetId': img_set['imageSetId'],
                                'status': 'error',
                                'error': str(e),
                            }
                        )

            return {
                'patientId': patient_id,
                'updatedImageSets': updated_image_sets,
                'totalUpdated': len(
                    [img for img in updated_image_sets if img['status'] == 'updated']
                ),
            }

        except ClientError as e:
            logger.error(f'Error bulk updating patient metadata: {e}')
            raise

    async def bulk_delete_by_criteria(
        self, datastore_id: str, search_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delete multiple image sets matching search criteria."""
        try:
            # Search for image sets matching criteria
            search_response = await self.search_image_sets(
                datastore_id=datastore_id,
                search_criteria=search_criteria,
                max_results=MAX_SEARCH_COUNT,
            )

            deleted_image_sets = []

            if 'imageSetsMetadataSummaries' in search_response:
                for img_set in search_response['imageSetsMetadataSummaries']:
                    try:
                        delete_response = await self.delete_image_set(
                            datastore_id=datastore_id, image_set_id=img_set['imageSetId']
                        )
                        deleted_image_sets.append(
                            {
                                'imageSetId': img_set['imageSetId'],
                                'status': 'deleted',
                                'response': delete_response,
                            }
                        )
                    except ClientError as e:
                        deleted_image_sets.append(
                            {
                                'imageSetId': img_set['imageSetId'],
                                'status': 'error',
                                'error': str(e),
                            }
                        )

            return {
                'searchCriteria': search_criteria,
                'deletedImageSets': deleted_image_sets,
                'totalDeleted': len(
                    [img for img in deleted_image_sets if img['status'] == 'deleted']
                ),
            }

        except ClientError as e:
            logger.error(f'Error bulk deleting by criteria: {e}')
            raise
