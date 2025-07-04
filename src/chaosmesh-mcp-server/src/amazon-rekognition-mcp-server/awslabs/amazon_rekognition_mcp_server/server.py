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

"""awslabs amazon-rekognition MCP Server implementation."""

from awslabs.amazon_rekognition_mcp_server.helpers import (
    get_image_bytes,
    get_rekognition_client,
    handle_exceptions,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Dict


mcp = FastMCP(
    'awslabs.amazon-rekognition-mcp-server',
    instructions="""
    Amazon Rekognition MCP Server provides tools to interact with Amazon Rekognition image analysis services.

    This server enables you to:
    - Manage face collections for storing and organizing face data
    - Index and search for faces across your image library
    - Detect objects, scenes, and activities in images
    - Identify inappropriate or unsafe content in images
    - Recognize celebrities in images
    - Compare faces between images for identity verification
    - Detect and extract text from images

    All image paths should be local file paths accessible to the server. If you've set the BASE_DIR
    environment variable, paths will be resolved relative to that directory.

    For more information about Amazon Rekognition, visit:
    https://aws.amazon.com/rekognition/
    """,
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)


@mcp.tool()
@handle_exceptions
async def list_collections() -> Dict:
    """Returns a list of collection IDs in your AWS account.

    Collections are containers for persisting faces that you index. You can create multiple
    collections to organize your face data. For example, you might create separate collections
    for different use cases or different sets of users.

    This tool handles pagination internally and returns all collections in a single response.

    Returns:
        A dictionary containing a list of collection IDs and other metadata.

    Example response:
        {
            "CollectionIds": ["my-collection-1", "my-collection-2"]
        }
    """
    client = get_rekognition_client()
    collections = []
    next_token = None

    # Handle pagination internally
    while True:
        params = {'MaxResults': 100}
        if next_token:
            params['NextToken'] = next_token

        response = client.list_collections(**params)
        collections.extend(response.get('CollectionIds', []))

        next_token = response.get('NextToken')
        if not next_token:
            break

    return {
        'CollectionIds': collections,
    }


@mcp.tool()
@handle_exceptions
async def index_faces(
    collection_id: str = Field(description='ID of the collection to add the face to'),
    image_path: str = Field(description='Path to the image file'),
) -> Dict:
    """Detects faces in an image and adds them to the specified collection.

    This operation detects faces in the input image, extracts facial features, and stores
    the face data in the specified collection. The face data persists until you explicitly
    delete it. The operation uses these default settings:

    - MaxFaces: 1 (only the largest face in the image is indexed)
    - QualityFilter: AUTO (automatically filters low-quality detected faces)
    - DetectionAttributes: ALL (returns all facial attributes)

    The operation returns face details, including:
    - Bounding box coordinates of the detected face
    - Confidence score for the face detection
    - Face ID assigned to the indexed face
    - Image ID assigned to the input image

    Args:
        collection_id: ID of the collection to add the face to. The collection must already exist.
        image_path: Path to the image file containing faces to index.

    Returns:
        A dictionary containing information about the indexed faces, including:
        - FaceRecords: List of face records, each containing Face and FaceDetail objects
        - UnindexedFaces: List of faces that couldn't be indexed and the reasons why

    Example response:
        {
            "FaceRecords": [
                {
                    "Face": {
                        "FaceId": "11fb64c9-39b6-4555-a7c7-4d646d393c85",
                        "BoundingBox": {...},
                        "ImageId": "a6d70cf1-3cf5-5058-9b21-3c84adb71933",
                        "Confidence": 99.98
                    },
                    "FaceDetail": {...}
                }
            ],
            "UnindexedFaces": []
        }
    """
    client = get_rekognition_client()
    image = get_image_bytes(image_path)

    response = client.index_faces(
        CollectionId=collection_id,
        Image=image,
        MaxFaces=1,
        QualityFilter='AUTO',
        DetectionAttributes=['ALL'],
    )

    return {
        'FaceRecords': response.get('FaceRecords', []),
        'UnindexedFaces': response.get('UnindexedFaces', []),
    }


@mcp.tool()
@handle_exceptions
async def search_faces_by_image(
    collection_id: str = Field(description='ID of the collection to search'),
    image_path: str = Field(description='Path to the image file'),
) -> Dict:
    """Searches for faces in a collection that match a face in the supplied image.

    This operation detects the largest face in the input image, extracts facial features,
    and searches the specified collection for matching faces. The operation returns an array
    of faces that match, ordered by similarity score with the highest similarity first.

    The operation uses these default settings:
    - MaxFaces: 10 (returns up to 10 matching faces)
    - FaceMatchThreshold: 80 (minimum similarity score of 80%)

    A face match is based on the similarity of facial features, not exact matching of the
    entire face or specific attributes like age or gender.

    Args:
        collection_id: ID of the collection to search.
        image_path: Path to the image file containing the face to search for.

    Returns:
        A dictionary containing information about the matching faces, including:
        - FaceMatches: List of matching faces with similarity scores
        - SearchedFaceBoundingBox: Bounding box of the face used for the search
        - SearchedFaceConfidence: Confidence that the searched face was actually a face

    Example response:
        {
            "FaceMatches": [
                {
                    "Similarity": 99.97,
                    "Face": {
                        "FaceId": "11fb64c9-39b6-4555-a7c7-4d646d393c85",
                        "BoundingBox": {...},
                        "ImageId": "a6d70cf1-3cf5-5058-9b21-3c84adb71933",
                        "Confidence": 99.98
                    }
                }
            ],
            "SearchedFaceBoundingBox": {...},
            "SearchedFaceConfidence": 99.98
        }
    """
    client = get_rekognition_client()
    image = get_image_bytes(image_path)

    response = client.search_faces_by_image(
        CollectionId=collection_id,
        Image=image,
        MaxFaces=10,
        FaceMatchThreshold=80,
    )

    return {
        'FaceMatches': response.get('FaceMatches', []),
        'SearchedFaceBoundingBox': response.get('SearchedFaceBoundingBox'),
        'SearchedFaceConfidence': response.get('SearchedFaceConfidence'),
    }


@mcp.tool()
@handle_exceptions
async def detect_labels(
    image_path: str = Field(description='Path to the image file'),
) -> Dict:
    """Detects objects, scenes, concepts, and activities in an image.

    This operation identifies objects (like "car" or "flower"), scenes (like "beach" or "city"),
    concepts (like "evening" or "nature"), and activities (like "running" or "playing soccer")
    within an image. For each label, the operation returns a confidence score and, where applicable,
    bounding boxes for detected objects.

    The operation uses these default settings:
    - MaxLabels: 100 (returns up to 100 labels)
    - MinConfidence: 50 (minimum confidence score of 50%)

    Args:
        image_path: Path to the image file to analyze.

    Returns:
        A dictionary containing detected labels and other metadata, including:
        - Labels: List of detected labels with confidence scores and locations

    Example response:
        {
            "Labels": [
                {
                    "Name": "Person",
                    "Confidence": 99.8,
                    "Instances": [
                        {
                            "BoundingBox": {...},
                            "Confidence": 99.8
                        }
                    ],
                    "Parents": []
                },
                {
                    "Name": "Beach",
                    "Confidence": 95.2,
                    "Instances": [],
                    "Parents": ["Outdoors", "Nature"]
                }
            ]
        }
    """
    client = get_rekognition_client()
    image = get_image_bytes(image_path)

    response = client.detect_labels(
        Image=image,
        MaxLabels=100,
        MinConfidence=50,
    )

    return {
        'Labels': response.get('Labels', []),
    }


@mcp.tool()
@handle_exceptions
async def detect_moderation_labels(
    image_path: str = Field(description='Path to the image file'),
) -> Dict:
    """Detects unsafe or inappropriate content in an image.

    This operation detects potentially unsafe, unwanted, or inappropriate content in images.
    It can identify content in categories such as:

    - Explicit Nudity
    - Suggestive Content
    - Violence
    - Visually Disturbing Content
    - Rude Gestures
    - Drugs & Tobacco
    - Alcohol
    - Gambling
    - Hate Symbols

    The operation uses a minimum confidence threshold of 50% by default.

    For each detected category, the operation returns a confidence score and hierarchical
    taxonomy (e.g., "Violence" might have a child category of "Weapon Violence").

    Args:
        image_path: Path to the image file to analyze for unsafe content.

    Returns:
        A dictionary containing detected moderation labels and other metadata, including:
        - ModerationLabels: List of detected moderation labels with confidence scores

    Example response:
        {
            "ModerationLabels": [
                {
                    "Confidence": 98.4,
                    "Name": "Violence",
                    "ParentName": ""
                },
                {
                    "Confidence": 98.0,
                    "Name": "Weapon Violence",
                    "ParentName": "Violence"
                }
            ]
        }
    """
    client = get_rekognition_client()
    image = get_image_bytes(image_path)

    response = client.detect_moderation_labels(
        Image=image,
        MinConfidence=50,
    )

    return {
        'ModerationLabels': response.get('ModerationLabels', []),
    }


@mcp.tool()
@handle_exceptions
async def recognize_celebrities(
    image_path: str = Field(description='Path to the image file'),
) -> Dict:
    """Recognizes celebrities in an image.

    This operation identifies celebrities (actors, musicians, athletes, etc.) in an image.
    For each detected celebrity, the operation returns:

    - Name of the celebrity
    - ID for the celebrity (that can be used to get additional information)
    - URLs pointing to additional information
    - Match confidence score
    - Bounding box coordinates of the face
    - Face landmarks and pose information

    The operation also returns information about faces that were detected but not
    recognized as celebrities.

    Args:
        image_path: Path to the image file containing potential celebrities.

    Returns:
        A dictionary containing recognized celebrities and other metadata, including:
        - CelebrityFaces: List of recognized celebrities with details
        - UnrecognizedFaces: List of faces that were detected but not recognized as celebrities

    Example response:
        {
            "CelebrityFaces": [
                {
                    "Name": "Celebrity Name",
                    "Id": "f9a1d78a-cc28-5c22-9b89-8adb82e3625f",
                    "MatchConfidence": 98.7,
                    "Urls": [
                        "https://www.imdb.com/name/nm0000123/"
                    ],
                    "Face": {...}
                }
            ],
            "UnrecognizedFaces": [
                {
                    "BoundingBox": {...},
                    "Landmarks": [...],
                    "Pose": {...},
                    "Quality": {...}
                }
            ]
        }
    """
    client = get_rekognition_client()
    image = get_image_bytes(image_path)

    response = client.recognize_celebrities(
        Image=image,
    )

    return {
        'CelebrityFaces': response.get('CelebrityFaces', []),
        'UnrecognizedFaces': response.get('UnrecognizedFaces', []),
    }


@mcp.tool()
@handle_exceptions
async def compare_faces(
    source_image_path: str = Field(description='Path to the source image file'),
    target_image_path: str = Field(description='Path to the target image file'),
) -> Dict:
    """Compares a face in the source image with faces in the target image.

    This operation compares the largest face detected in the source image with each face
    detected in the target image. The operation uses a similarity threshold of 80% by default,
    meaning that only faces with a similarity score of 80% or higher are considered matches.

    For each face in the target image, the operation returns:

    - Whether the face matches the largest face in the source image
    - A similarity score (0-100) indicating how closely the faces match
    - Bounding box coordinates for both the source and target faces

    This is useful for identity verification, finding specific people in photos,
    or comparing faces for similarity.

    Args:
        source_image_path: Path to the source image file containing the reference face.
        target_image_path: Path to the target image file containing faces to compare against.

    Returns:
        A dictionary containing information about the face matches, including:
        - FaceMatches: List of matching faces with similarity scores
        - UnmatchedFaces: List of faces in the target image that didn't match
        - SourceImageFace: Information about the face in the source image

    Example response:
        {
            "FaceMatches": [
                {
                    "Similarity": 98.2,
                    "Face": {
                        "BoundingBox": {...},
                        "Confidence": 99.98
                    }
                }
            ],
            "UnmatchedFaces": [...],
            "SourceImageFace": {
                "BoundingBox": {...},
                "Confidence": 99.97
            }
        }
    """
    client = get_rekognition_client()
    source_image = get_image_bytes(source_image_path)
    target_image = get_image_bytes(target_image_path)

    response = client.compare_faces(
        SourceImage=source_image,
        TargetImage=target_image,
        SimilarityThreshold=80,
    )

    return {
        'FaceMatches': response.get('FaceMatches', []),
        'UnmatchedFaces': response.get('UnmatchedFaces', []),
        'SourceImageFace': response.get('SourceImageFace'),
    }


@mcp.tool()
@handle_exceptions
async def detect_text(
    image_path: str = Field(description='Path to the image file'),
) -> Dict:
    """Detects text in an image.

    This operation identifies text in an image and converts it into machine-readable text.
    It can detect both printed text (such as books, posters, and documents) and handwritten text.

    The operation returns:

    - Detected text strings
    - Location of the text in the image (bounding boxes)
    - Confidence scores for the detection
    - Type of text (LINE or WORD)
    - Parent-child relationships between text elements (words within lines)

    This is useful for digitizing printed materials, extracting information from images,
    reading text in natural scenes, or processing documents.

    Args:
        image_path: Path to the image file containing text to detect.

    Returns:
        A dictionary containing detected text and metadata, including:
        - TextDetections: List of detected text elements with details

    Example response:
        {
            "TextDetections": [
                {
                    "DetectedText": "Hello World",
                    "Type": "LINE",
                    "Confidence": 99.8
                },
                {
                    "DetectedText": "Hello",
                    "Type": "WORD",
                    "Confidence": 99.9
                },
                {
                    "DetectedText": "World",
                    "Type": "WORD",
                    "Confidence": 99.7
                }
            ]
        }
    """
    client = get_rekognition_client()
    image = get_image_bytes(image_path)

    response = client.detect_text(
        Image=image,
    )

    # Filter the response to keep only essential fields
    filtered_detections = []
    for detection in response.get('TextDetections', []):
        filtered_detections.append(
            {
                'DetectedText': detection.get('DetectedText'),
                'Type': detection.get('Type'),
                'Confidence': detection.get('Confidence'),
            }
        )

    return {
        'TextDetections': filtered_detections,
    }


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting Amazon Rekognition MCP Server.')
    mcp.run()


if __name__ == '__main__':
    main()
