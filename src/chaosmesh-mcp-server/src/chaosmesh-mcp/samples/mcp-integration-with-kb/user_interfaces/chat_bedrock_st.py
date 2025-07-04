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

import json
import requests
import streamlit as st
import time


# Set page configuration
st.set_page_config(
    page_title='MCP integration with KB',
    layout='wide',
    initial_sidebar_state='expanded',
)
st.title('MCP integration with KB')

# Initialize session state for knowledge base IDs
if 'kb_ids' not in st.session_state:
    st.session_state.kb_ids = []

if 'current_kb_id' not in st.session_state:
    st.session_state.current_kb_id = None

# Sidebar for Knowledge Base configuration
with st.sidebar:
    st.title('Knowledge Base Settings')

    # Knowledge Base selection
    st.subheader('Current Knowledge Base')
    if st.session_state.kb_ids:
        current_kb = st.selectbox(
            'Select Knowledge Base',
            options=st.session_state.kb_ids,
            index=0
            if st.session_state.current_kb_id is None
            else st.session_state.kb_ids.index(st.session_state.current_kb_id),
        )
        st.session_state.current_kb_id = current_kb
    else:
        st.info('No Knowledge Bases added yet')

    # Add new Knowledge Base
    st.subheader('Add Knowledge Base')
    new_kb_id = st.text_input('Knowledge Base ID')

    if st.button('Add Knowledge Base'):
        if new_kb_id and new_kb_id not in st.session_state.kb_ids:
            st.session_state.kb_ids.append(new_kb_id)
            st.session_state.current_kb_id = new_kb_id
            st.success(f'Added Knowledge Base: {new_kb_id}')
            st.rerun()
        elif not new_kb_id:
            st.error('Please enter a Knowledge Base ID')
        else:
            st.warning('This Knowledge Base ID already exists')

    # Remove Knowledge Base
    if st.session_state.kb_ids and st.button('Remove Selected Knowledge Base'):
        st.session_state.kb_ids.remove(st.session_state.current_kb_id)
        if st.session_state.kb_ids:
            st.session_state.current_kb_id = st.session_state.kb_ids[0]
        else:
            st.session_state.current_kb_id = None
        st.rerun()

# Display current Knowledge Base info in main area
if st.session_state.current_kb_id:
    st.info(f'Using Knowledge Base: {st.session_state.current_kb_id}')
else:
    st.warning('Please add a Knowledge Base ID in the sidebar')

# API configuration
API_URL = 'http://localhost:8000'


def query_api(prompt, kb_id):
    """Send a query to the FastAPI server and get the response."""
    try:
        response = requests.post(
            f'{API_URL}/query', json={'query': prompt, 'kb_id': kb_id}, timeout=30
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()['messages']
    except requests.exceptions.RequestException as e:
        st.error(f'API Error: {str(e)}')
        return [{'content': f'Error communicating with the API: {str(e)}'}]


if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

if prompt := st.chat_input('What would you like to ask your Bedrock Knowledge Base?'):
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)

    with st.chat_message('assistant'):
        message_placeholder = st.empty()
        full_response = ''

        # Check if KB ID is set before processing
        if not st.session_state.current_kb_id:
            full_response = 'Please add a Knowledge Base ID in the sidebar to continue.'
        else:
            try:
                # Call our API with the KB integration
                with st.spinner('Processing your query...'):
                    messages = query_api(prompt, st.session_state.current_kb_id)

                # Process the response
                for message in messages:
                    content = message.get('content', '')

                    # Check if content is JSON and extract relevant parts
                    try:
                        json_content = json.loads(content)
                        if isinstance(json_content, dict) and 'content' in json_content:
                            content = json_content['content']
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON or not the expected format, use as is
                        pass

                    # Simulate stream of response with milliseconds delay
                    for chunk in content.split(' '):
                        full_response += chunk + ' '
                        if chunk.endswith('\n'):
                            full_response += ' '
                        time.sleep(0.05)

                        # Add a blinking cursor to simulate typing
                        message_placeholder.markdown(full_response + '▌')
            except Exception as e:
                full_response = f'Error: {str(e)}'

        message_placeholder.markdown(full_response)

    st.session_state.messages.append({'role': 'assistant', 'content': full_response})
