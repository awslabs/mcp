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

# Hand-written Tier 2 cross-reference validation checks for MediaLive operations.
# These catch known gotchas where the AWS API returns cryptic error messages,
# providing clear guidance before the API call is made.

from typing import Callable


def validate_create_channel(config: dict) -> list[str]:
    """Validate cross-references in a CreateChannel request.

    Checks that VideoDescriptionName and AudioDescriptionNames referenced
    in outputs actually exist in the encoder_settings definitions.
    Returns a list of error strings (empty means valid).
    """
    errors: list[str] = []

    encoder_settings = config.get('EncoderSettings') or config.get('encoder_settings')
    if not encoder_settings:
        return errors

    # Collect defined video description names
    video_descriptions = (
        encoder_settings.get('VideoDescriptions')
        or encoder_settings.get('video_descriptions')
        or []
    )
    defined_video_names: set[str] = set()
    for vd in video_descriptions:
        name = vd.get('Name') or vd.get('name')
        if name:
            defined_video_names.add(name)

    # Collect defined audio description names
    audio_descriptions = (
        encoder_settings.get('AudioDescriptions')
        or encoder_settings.get('audio_descriptions')
        or []
    )
    defined_audio_names: set[str] = set()
    for ad in audio_descriptions:
        name = ad.get('Name') or ad.get('name')
        if name:
            defined_audio_names.add(name)

    # Check cross-references in output groups
    output_groups = (
        encoder_settings.get('OutputGroups') or encoder_settings.get('output_groups') or []
    )
    for og in output_groups:
        outputs = og.get('Outputs') or og.get('outputs') or []
        for output in outputs:
            # Check VideoDescriptionName reference
            video_desc_name = output.get('VideoDescriptionName') or output.get(
                'video_description_name'
            )
            if video_desc_name and video_desc_name not in defined_video_names:
                errors.append(
                    f"VideoDescriptionName '{video_desc_name}' not found in "
                    f'VideoDescriptions. Valid: {defined_video_names}'
                )

            # Check AudioDescriptionNames references
            audio_desc_names = output.get('AudioDescriptionNames') or output.get(
                'audio_description_names', []
            )
            for adn in audio_desc_names:
                if adn not in defined_audio_names:
                    errors.append(
                        f"AudioDescriptionName '{adn}' not found in "
                        f'AudioDescriptions. Valid: {defined_audio_names}'
                    )

    return errors


VALIDATORS: dict[str, Callable[[dict], list[str]]] = {
    'CreateChannel': validate_create_channel,
}
