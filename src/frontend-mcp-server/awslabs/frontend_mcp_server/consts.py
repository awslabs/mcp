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

"""Constants for the AWS Amplify Gen2 MCP Server."""

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
AMPLIFY_DOCS_BASE = "https://docs.amplify.aws"

# Documentation and sample repositories
DOCUMENTATION_REPO = "aws-amplify/docs"
SAMPLE_REPOSITORIES = {
    "next": "aws-samples/amplify-next-template",
    "react": "aws-samples/amplify-vite-react-template",
    "angular": "aws-samples/amplify-angular-template",
    "vue": "aws-samples/amplify-vue-template",
    "ai": "aws-samples/amplify-ai-examples"
}

# Common project template files to check
PROJECT_TEMPLATE_FILES = {
    "package.json": "Project configuration and dependencies",
    "README.md": "Project documentation and setup instructions",
    "amplify/backend.ts": "Amplify backend configuration",
    "amplify/auth/resource.ts": "Authentication configuration",
    "amplify/data/resource.ts": "Data/API configuration",
    "amplify/storage/resource.ts": "Storage configuration",
    "src/main.tsx": "React main entry point",
    "src/main.ts": "Vue/Angular main entry point",
    "src/app/app.component.ts": "Angular app component",
    "pages/_app.tsx": "Next.js app component",
    "app/layout.tsx": "Next.js app router layout"
}

# Default search limits
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50

# Default content length limits
DEFAULT_CONTENT_LENGTH = 5000
MAX_CONTENT_LENGTH = 50000

# Framework mappings
SUPPORTED_FRAMEWORKS = ["react", "vue", "angular", "next", "ai"]

# Common Amplify Gen2 topics for guidance
AMPLIFY_TOPICS = [
    "authentication",
    "data",
    "storage",
    "functions",
    "ai",
    "analytics",
    "deployment",
    "hosting",
    "monitoring"
]
