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

"""Tests for the Amazon Rekognition MCP Server."""

import pytest
from awslabs.amazon_rekognition_mcp_server.server import (
    compare_faces,
    detect_labels,
    detect_moderation_labels,
    detect_text,
    index_faces,
    list_collections,
    recognize_celebrities,
    search_faces_by_image,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_list_collections():
    """Test list_collections tool."""
    mock_client = MagicMock()
    # Mock first call with NextToken
    mock_client.list_collections.side_effect = [
        {
            'CollectionIds': ['collection1', 'collection2'],
            'NextToken': 'token123',
        },
        {
            'CollectionIds': ['collection3', 'collection4'],
        },
    ]

    with patch(
        'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
        return_value=mock_client,
    ):
        result = await list_collections()

        # Check that list_collections was called twice (for pagination)
        assert mock_client.list_collections.call_count == 2
        # Check first call
        mock_client.list_collections.assert_any_call(MaxResults=100)
        # Check second call with token
        mock_client.list_collections.assert_any_call(MaxResults=100, NextToken='token123')

        # Check result
        assert result['CollectionIds'] == [
            'collection1',
            'collection2',
            'collection3',
            'collection4',
        ]


@pytest.mark.asyncio
async def test_index_faces():
    """Test index_faces tool."""
    mock_client = MagicMock()
    mock_response = {
        'FaceRecords': [{'Face': {'FaceId': 'face123'}}],
        'UnindexedFaces': [],
    }
    mock_client.index_faces.return_value = mock_response

    mock_image = {'Bytes': b'test image data'}

    with (
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_image_bytes', return_value=mock_image
        ),
    ):
        result = await index_faces(
            collection_id='test-collection', image_path='/path/to/image.jpg'
        )

        # Check that index_faces was called with correct parameters
        mock_client.index_faces.assert_called_once_with(
            CollectionId='test-collection',
            Image=mock_image,
            MaxFaces=1,
            QualityFilter='AUTO',
            DetectionAttributes=['ALL'],
        )

        # Check result
        assert result == mock_response


@pytest.mark.asyncio
async def test_search_faces_by_image():
    """Test search_faces_by_image tool."""
    mock_client = MagicMock()
    mock_response = {
        'FaceMatches': [{'Face': {'FaceId': 'face123'}, 'Similarity': 99.9}],
        'SearchedFaceBoundingBox': {'Width': 0.5, 'Height': 0.5, 'Left': 0.25, 'Top': 0.25},
        'SearchedFaceConfidence': 99.9,
    }
    mock_client.search_faces_by_image.return_value = mock_response

    mock_image = {'Bytes': b'test image data'}

    with (
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_image_bytes', return_value=mock_image
        ),
    ):
        result = await search_faces_by_image(
            collection_id='test-collection', image_path='/path/to/image.jpg'
        )

        # Check that search_faces_by_image was called with correct parameters
        mock_client.search_faces_by_image.assert_called_once_with(
            CollectionId='test-collection',
            Image=mock_image,
            MaxFaces=10,
            FaceMatchThreshold=80,
        )

        # Check result
        assert result == mock_response


@pytest.mark.asyncio
async def test_detect_labels():
    """Test detect_labels tool."""
    mock_client = MagicMock()
    mock_response = {
        'Labels': [{'Name': 'Person', 'Confidence': 99.9}, {'Name': 'Car', 'Confidence': 95.2}],
    }
    mock_client.detect_labels.return_value = mock_response

    mock_image = {'Bytes': b'test image data'}

    with (
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_image_bytes', return_value=mock_image
        ),
    ):
        result = await detect_labels(image_path='/path/to/image.jpg')

        # Check that detect_labels was called with correct parameters
        mock_client.detect_labels.assert_called_once_with(
            Image=mock_image,
            MaxLabels=100,
            MinConfidence=50,
        )

        # Check result
        assert result == mock_response


@pytest.mark.asyncio
async def test_detect_moderation_labels():
    """Test detect_moderation_labels tool."""
    mock_client = MagicMock()
    mock_response = {
        'ModerationLabels': [
            {'Name': 'Violence', 'Confidence': 99.9},
        ],
    }
    mock_client.detect_moderation_labels.return_value = mock_response

    mock_image = {'Bytes': b'test image data'}

    with (
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_image_bytes', return_value=mock_image
        ),
    ):
        result = await detect_moderation_labels(image_path='/path/to/image.jpg')

        # Check that detect_moderation_labels was called with correct parameters
        mock_client.detect_moderation_labels.assert_called_once_with(
            Image=mock_image,
            MinConfidence=50,
        )

        # Check result
        assert result == mock_response


@pytest.mark.asyncio
async def test_recognize_celebrities():
    """Test recognize_celebrities tool."""
    mock_client = MagicMock()
    mock_response = {
        'CelebrityFaces': [
            {'Name': 'Celebrity Name', 'Id': 'celeb123', 'MatchConfidence': 98.7},
        ],
        'UnrecognizedFaces': [],
    }
    mock_client.recognize_celebrities.return_value = mock_response

    mock_image = {'Bytes': b'test image data'}

    with (
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_image_bytes', return_value=mock_image
        ),
    ):
        result = await recognize_celebrities(image_path='/path/to/image.jpg')

        # Check that recognize_celebrities was called with correct parameters
        mock_client.recognize_celebrities.assert_called_once_with(
            Image=mock_image,
        )

        # Check result
        assert result == mock_response


@pytest.mark.asyncio
async def test_compare_faces():
    """Test compare_faces tool."""
    mock_client = MagicMock()
    mock_response = {
        'FaceMatches': [
            {
                'Face': {'BoundingBox': {'Width': 0.5, 'Height': 0.5, 'Left': 0.25, 'Top': 0.25}},
                'Similarity': 99.9,
            },
        ],
        'UnmatchedFaces': [],
        'SourceImageFace': {
            'BoundingBox': {'Width': 0.5, 'Height': 0.5, 'Left': 0.25, 'Top': 0.25}
        },
    }
    mock_client.compare_faces.return_value = mock_response

    mock_source_image = {'Bytes': b'test source image data'}
    mock_target_image = {'Bytes': b'test target image data'}

    with (
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_image_bytes',
            side_effect=[mock_source_image, mock_target_image],
        ),
    ):
        result = await compare_faces(
            source_image_path='/path/to/source.jpg', target_image_path='/path/to/target.jpg'
        )

        # Check that compare_faces was called with correct parameters
        mock_client.compare_faces.assert_called_once_with(
            SourceImage=mock_source_image,
            TargetImage=mock_target_image,
            SimilarityThreshold=80,
        )

        # Check result
        assert result == mock_response


@pytest.mark.asyncio
async def test_detect_text():
    """Test detect_text tool."""
    mock_client = MagicMock()
    mock_response = {
        'TextDetections': [
            {
                'DetectedText': 'Hello World',
                'Type': 'LINE',
                'Id': 0,
                'Confidence': 99.8,
                'Geometry': {
                    'BoundingBox': {'Width': 0.5, 'Height': 0.1, 'Left': 0.25, 'Top': 0.4},
                    'Polygon': [
                        {'X': 0.25, 'Y': 0.4},
                        {'X': 0.75, 'Y': 0.4},
                        {'X': 0.75, 'Y': 0.5},
                        {'X': 0.25, 'Y': 0.5},
                    ],
                },
            },
            {
                'DetectedText': 'Hello',
                'Type': 'WORD',
                'Id': 1,
                'ParentId': 0,
                'Confidence': 99.9,
                'Geometry': {
                    'BoundingBox': {'Width': 0.25, 'Height': 0.1, 'Left': 0.25, 'Top': 0.4},
                    'Polygon': [
                        {'X': 0.25, 'Y': 0.4},
                        {'X': 0.5, 'Y': 0.4},
                        {'X': 0.5, 'Y': 0.5},
                        {'X': 0.25, 'Y': 0.5},
                    ],
                },
            },
            {
                'DetectedText': 'World',
                'Type': 'WORD',
                'Id': 2,
                'ParentId': 0,
                'Confidence': 99.7,
                'Geometry': {
                    'BoundingBox': {'Width': 0.25, 'Height': 0.1, 'Left': 0.5, 'Top': 0.4},
                    'Polygon': [
                        {'X': 0.5, 'Y': 0.4},
                        {'X': 0.75, 'Y': 0.4},
                        {'X': 0.75, 'Y': 0.5},
                        {'X': 0.5, 'Y': 0.5},
                    ],
                },
            },
        ],
        'TextModelVersion': '3.0',
    }
    mock_client.detect_text.return_value = mock_response

    # Expected filtered response
    expected_result = {
        'TextDetections': [
            {
                'DetectedText': 'Hello World',
                'Type': 'LINE',
                'Confidence': 99.8,
            },
            {
                'DetectedText': 'Hello',
                'Type': 'WORD',
                'Confidence': 99.9,
            },
            {
                'DetectedText': 'World',
                'Type': 'WORD',
                'Confidence': 99.7,
            },
        ],
    }

    mock_image = {'Bytes': b'test image data'}

    with (
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_rekognition_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.amazon_rekognition_mcp_server.server.get_image_bytes', return_value=mock_image
        ),
    ):
        result = await detect_text(image_path='/path/to/image.jpg')

        # Check that detect_text was called with correct parameters
        mock_client.detect_text.assert_called_once_with(
            Image=mock_image,
        )

        # Check result contains only the filtered fields
        assert result == expected_result
