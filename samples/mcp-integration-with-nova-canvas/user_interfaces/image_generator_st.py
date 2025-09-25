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

import os
import random
import requests
import streamlit as st
from PIL import Image
from typing import List, Optional


# Set page configuration
st.set_page_config(
    page_title='Nova Canvas Image Generator',
    layout='wide',
    initial_sidebar_state='expanded',
)
st.title('Nova Canvas Image Generator')

# API configuration
API_URL = 'http://localhost:8000'

# Initialize session state for generated images
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []

if 'improved_prompt' not in st.session_state:
    st.session_state.improved_prompt = None

if 'generation_mode' not in st.session_state:
    st.session_state.generation_mode = 'text'  # 'text' or 'color'

if 'colors' not in st.session_state:
    st.session_state.colors = []


def add_color(color: str):
    """Add a color to the color palette."""
    if len(st.session_state.colors) < 10:  # Nova Canvas supports up to 10 colors
        st.session_state.colors.append(color)


def remove_color(index: int):
    """Remove a color from the color palette."""
    if 0 <= index < len(st.session_state.colors):
        st.session_state.colors.pop(index)


def clear_colors():
    """Clear all colors from the color palette."""
    st.session_state.colors = []


def generate_image(
    prompt: str,
    negative_prompt: str,
    width: int = 1024,
    height: int = 1024,
    quality: str = 'standard',
    cfg_scale: float = 6.5,
    seed: Optional[int] = None,
    number_of_images: int = 1,
    colors: Optional[List[str]] = None,
    use_improved_prompt: bool = False,
):
    """Send a request to the FastAPI server to generate an image."""
    try:
        payload = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': width,
            'height': height,
            'quality': quality,
            'cfg_scale': cfg_scale,
            'seed': seed,
            'number_of_images': number_of_images,
            'use_improved_prompt': use_improved_prompt,
        }
        if colors:
            payload['colors'] = colors

        response = requests.post(
            f'{API_URL}/generate',
            json=payload,
            timeout=120,  # Longer timeout for image generation
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f'API Error: {str(e)}')
        return {
            'status': 'error',
            'message': f'Error communicating with the API: {str(e)}',
            'image_paths': [],
        }


# Sidebar for generation settings
with st.sidebar:
    st.title('Image Generation Settings')

    # Generation mode selection
    st.subheader('Generation Mode')
    generation_mode = st.radio(
        'Select generation mode:',
        options=['Text-to-Image', 'Color-Guided Generation'],
        index=0 if st.session_state.generation_mode == 'text' else 1,
    )
    st.session_state.generation_mode = 'text' if generation_mode == 'Text-to-Image' else 'color'

    # Image dimensions
    st.subheader('Image Dimensions')
    width_options = [512, 768, 1024, 1536, 2048]
    height_options = [512, 768, 1024, 1536, 2048]

    col1, col2 = st.columns(2)
    with col1:
        width = st.selectbox('Width', options=width_options, index=2)  # Default to 1024
    with col2:
        height = st.selectbox('Height', options=height_options, index=2)  # Default to 1024

    # Quality settings
    st.subheader('Quality')
    quality = st.radio('Image quality:', options=['standard', 'premium'], index=0)

    # Advanced settings
    st.subheader('Advanced Settings')
    cfg_scale = st.slider(
        'CFG Scale',
        min_value=1.1,
        max_value=10.0,
        value=6.5,
        step=0.1,
        help='How strongly the image adheres to the prompt',
    )

    use_seed = st.checkbox('Use specific seed', value=False)
    if use_seed:
        seed = st.number_input(
            'Seed', min_value=0, max_value=858993459, value=random.randint(0, 858993459)
        )
    else:
        seed = None

    number_of_images = st.slider('Number of images', min_value=1, max_value=5, value=1)

# Main content area
st.header('Create Your Image')

# Prompt input
prompt = st.text_area(
    'Image Description',
    placeholder='Describe the image you want to generate...',
    help='Be specific and detailed about what you want to see in the image',
)

# Negative prompt input
negative_prompt = st.text_area(
    'Negative Prompt',
    placeholder="Describe what you DON'T want to see in the image...",
    help='Specify elements you want to exclude from the image.',
)

# Default negative prompt suggestion
if not negative_prompt:
    st.info(
        'Tip: Consider adding "people, anatomy, hands, low quality, low resolution, low detail" to your negative prompt for better results.'
    )

# Color palette section (only shown in color-guided mode)
if st.session_state.generation_mode == 'color':
    st.header('Color Palette')
    st.write('Select up to 10 colors to guide the image generation')

    # Display current color palette
    if st.session_state.colors:
        cols = st.columns(10)  # Up to 10 colors
        for i, color in enumerate(st.session_state.colors):
            with cols[i % 10]:
                st.color_picker(f'Color {i + 1}', color, key=f'color_display_{i}', disabled=True)
                if st.button('Remove', key=f'remove_{i}'):
                    remove_color(i)
                    st.rerun()

    # Add new color
    if len(st.session_state.colors) < 10:
        new_color = st.color_picker('Add a color', '#FF4B4B')
        if st.button('Add to Palette'):
            add_color(new_color)
            st.rerun()

    # Clear all colors
    if st.session_state.colors and st.button('Clear All Colors'):
        clear_colors()
        st.rerun()

# Checkbox for improved prompt
use_improved_prompt = bool(
    st.checkbox(
        'Use Improved Prompt',
        value=True,
        help='Improve the prompt using Amazon Nova Micro Model for image generation',
    )
)

# Generate button
if st.button('Generate Image', type='primary', disabled=not prompt or not negative_prompt):
    st.session_state.improved_prompt = None
    with st.spinner('Generating your image... This may take a minute.'):
        # Prepare colors if in color-guided mode
        colors = st.session_state.colors if st.session_state.generation_mode == 'color' else None

        # Call the API
        result = generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            quality=quality,
            cfg_scale=cfg_scale,
            seed=seed,
            number_of_images=number_of_images,
            use_improved_prompt=use_improved_prompt,
            colors=colors,
        )

        # Store generated images
        st.session_state.generated_images = result['image_paths']

        if use_improved_prompt:
            improved_prompt = result['improved_prompt']
            if improved_prompt:
                st.session_state.improved_prompt = improved_prompt

        # Display success message or error
        if result['status'] == 'success':
            st.success(result['message'])
        else:
            st.error(f'Failed to generate image: {result["message"]}')

# Display the improved prompt
if st.session_state.improved_prompt:
    with st.expander('Improved Prompt', expanded=True):
        st.markdown(st.session_state.improved_prompt)

# Display generated images
if st.session_state.generated_images:
    st.header('Generated Images')

    # Create columns based on number of images
    num_cols = min(3, len(st.session_state.generated_images))
    if num_cols > 0:
        cols = st.columns(num_cols)

        for i, image_path in enumerate(st.session_state.generated_images):
            with cols[i % num_cols]:
                try:
                    # Display the image
                    img = Image.open(image_path)
                    st.image(img, caption=f'Image {i + 1}', use_container_width=True)

                    # Add download button
                    with open(image_path, 'rb') as file:
                        btn = st.download_button(
                            label=f'Download Image {i + 1}',
                            data=file,
                            file_name=os.path.basename(image_path),
                            mime='image/png',
                        )
                except Exception as e:
                    st.error(f'Error displaying image {i + 1}: {str(e)}')

# Display prompt best practices
with st.expander('Prompt Best Practices'):
    st.markdown("""
    ## Effective Prompt Structure

    An effective prompt often includes short descriptions of:

    1. The subject
    2. The environment
    3. (optional) The position or pose of the subject
    4. (optional) Lighting description
    5. (optional) Camera position/framing
    6. (optional) The visual style or medium ("photo", "illustration", "painting", etc.)

    ## Example Prompts

    - "realistic editorial photo of female teacher standing at a blackboard with a warm smile"
    - "whimsical and ethereal soft-shaded story illustration: A woman in a large hat stands at the ship's railing looking out across the ocean"
    - "drone view of a dark river winding through a stark Iceland landscape, cinematic quality"

    ## Using Negative Prompts

    Negative prompts can be surprisingly useful. Use them to exclude objects or style characteristics that might otherwise naturally occur as a result of your main prompt.

    For example, adding "waves, clouds" as a negative prompt to a ship scene will result in a cleaner, more minimal composition.

    Always include "people, anatomy, hands, low quality, low resolution, low detail" in your negative prompt for better results.
    """)
