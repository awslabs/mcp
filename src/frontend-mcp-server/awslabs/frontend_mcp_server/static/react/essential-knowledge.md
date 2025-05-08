# Reference UI Application Development Guide

## Introduction
This document provides guidance for an LLM assistant helping users create custom web applications based on the reference UI template at https://github.com/sanjusunny/reference-ui. The template uses React, Tailwind CSS, React Router v7, shadcn UI components, AWS Amplify, and Zustand for state management. As the assisting LLM, you should use this information to analyze user requirements, suggest appropriate approaches, and provide implementation steps for customizing the reference template to meet their specific needs. Follow the structured approach outlined below to deliver high-quality applications efficiently while maintaining consistency with the existing architecture and best practices.

## Important
- Authentication, basic routing, and private/public layouts are already implemented
- Sample dashboard and settings pages exist as reference
- AWS backend integration will be handled separately
- If you run into issues, you MUST seek guidance from the AWSLabs Frontend MCP server under the "Troubleshooting" topic.

## Project Implementation Flow

### 0. Requirements Analysis
- Generate a modern app name and description
- Identify the primary color for the app if provided by the user, if not use shadcn defaults (usually #171717)
- Identify target users and primary purpose
- List and prioritize core features
- Map features to existing template structure
- Identify new pages and components needed
- Reuse the current authentication layouts and flow
- Reuse the current private page layout, with the application sidebar on the left and page content on the right
- Always include a dashboard page as the start page, and incorporate charts and lists based on the functional needs of the application
- Incorporate an AI Chat assistant to the application if helpful
- Make the UI design contemporary, clean and minimal.

### 1. Document your plan

Once you have completed your analysis, you MUST create a CHECKLIST.md in the root folder of the project with two clearly defined sections:

**Section 1: Application Analysis**
- Application name and description
- Target users and primary purpose
- Core features (prioritized list)
  - Be specific and detailed for each feature
  - Include success criteria for each feature
  - Identify which features require backend integration
- Complete page list with brief descriptions for each page
  - Detail EVERY page needed for the application
  - Include purpose, key components, and data needs for each page
  - Map pages to features they support
- Data models/entities needed
- UI components required for implementation
  - List shadcn components to be used for each page
  - Identify any custom components needed

**Example: Task Tracking App**
```markdown
# TaskFlow Application Analysis

## Application Overview
- **Name**: TaskFlow
- **Description**: A collaborative task tracking application for small teams
- **Target Users**: Small teams (5-15 people), project managers, freelancers
- **Primary Purpose**: Simplify task management and improve team coordination

## Core Features (Prioritized)
1. **Task Management**
   - Create, edit, delete tasks with title, description, due date, priority
   - Assign tasks to team members
   - Success criteria: Users can perform all CRUD operations on tasks
   - Backend integration: Required for persistent storage

2. **Task Board Views**
   - Kanban board with customizable columns (Todo, In Progress, Done)
   - List view with sorting and filtering options
   - Success criteria: Users can switch between views and drag-drop tasks
   - Backend integration: Required for state persistence

3. **Team Collaboration**
   - Comment on tasks
   - @mention team members
   - Success criteria: Users receive notifications when mentioned
   - Backend integration: Required for notifications

## Page List
1. **Dashboard**
   - Purpose: Overview of tasks, recent activity, and team performance
   - Components: Task summary cards, activity feed, progress charts
   - Data: Task counts by status, recent activities, completion rates

2. **Task Board**
   - Purpose: Visual kanban-style task management
   - Components: Drag-drop columns, task cards, filtering controls
   - Data: All tasks with status, assignee, priority information

3. **Task Details**
   - Purpose: View and edit detailed task information
   - Components: Form fields, comments section, activity log
   - Data: Single task with full details and comment history

4. **Team Members**
   - Purpose: Manage team members and view their tasks
   - Components: User list, user profile cards, assigned tasks
   - Data: User profiles and task assignments

5. **Settings**
   - Purpose: Configure application preferences
   - Components: Form fields for notification settings, theme options
   - Data: User preferences

## Data Models
1. **Task**
   - id, title, description, status, priority, dueDate, assigneeId, createdAt

2. **User**
   - id, name, email, avatar, role

3. **Comment**
   - id, taskId, userId, content, createdAt

## UI Components
1. **Dashboard Page**
   - shadcn: Card, Tabs, Avatar, Button, Select
   - Custom: TaskSummaryCard, ActivityFeed

2. **Task Board Page**
   - shadcn: Card, Badge, Avatar, Button, DropdownMenu
   - Custom: DraggableTaskCard, KanbanColumn

3. **Task Details Page**
   - shadcn: Form, Input, Textarea, Select, Button, Tabs, ScrollArea
   - Custom: CommentThread, TaskActivityLog

4. **Team Members Page**
   - shadcn: Card, Avatar, Table, Dialog, Badge
   - Custom: UserProfileCard, TaskAssignmentList

5. **Settings Page**
   - shadcn: Form, Switch, RadioGroup, Separator, Button
   - Custom: NotificationPreferences
```

**Section 2: Implementation Checklist**
- [ ] Generate modern app name/description
- [ ] Clone repo to "frontend" folder and install dependencies
- [ ] Update the README.md based on your analysis of the codebase and frontend stack
- [ ] Update package.json name and app name references
- [ ] Update app name and description on the login page
- [ ] Generate favicon.png and splash.png images using nova canvas MCP server
- [ ] Create mock amplify_outputs.json file
- [ ] Add/update pages and required components, using shadcn components
- [ ] Extend routing structure
- [ ] Add sample data to Zustand store
- [ ] Update navigation
- [ ] Ensure all required pages are created and wired up

As you go through the implementation, keep updating the checklist to ensure that you have completely created all the pages and features necessary to meet the functional needs of the application. The analysis section should be completed BEFORE beginning any implementation tasks.

### 2. Setup & Configuration
```bash
# Clone repository to frontend folder
git clone -b starterkits/frontend-react18-shadcn https://github.com/awslabs/mcp.git
cd mcp/frontend
npm install
```

Analyze this code base after cloning to understand how it is structured and the key architectural patterns and frontend stack.

Based on your analysis, update the README.md with an overview of the functional goal of the application and the frontend stack, including specific versions (e.g. React 18 instead of just React)

**PHASE VERIFICATION**: Ensure repository is cloned successfully and all dependencies are installed without errors. Confirm README.md is updated with accurate information.

### 3. Application Branding & Identity
- Update package.json with new application name
- Update app name references in components (e.g., app-sidebar.tsx)
- Update the app name and description on the login page
- Update document title and metadata in index.html
- Customize the primary color for the application using Tailwind if the user has provided a custom primary color for the app
- When setting primary color, you MUST update both the Tailwind and Amplify theme to keep them in sync
- Use Nova Canvas MCP Server to create the following 2 images:
  - **favicon.png (320x320)**
    - Create a minimal abstract icon that represents the app concept
    - Use monochromatic shades of the primary color
    - Design should be simple enough to be recognizable at small sizes
    - Avoid text or complex details that won't scale down well
  - **splash.png (1024x1024)**
    - Create a compelling minimal abstract conceptual editorial illustration relevant to the concept of the app
    - Use primarily dark shades of the primary color with subtle accent colors if appropriate
    - Design should convey the app's purpose through abstract visual elements
    - Can include subtle patterns, gradients, or geometric shapes
- You MUST use 'mv' to move the generated image and overwrite the existing image, as users can be on Windows or Unix systems and the 'move' command might not be available.

```bash
mv source-folder/file destination-folder/file
```

- Replace existing app icon references with generated favicon.png

**PHASE VERIFICATION**: Confirm all branding elements are consistently updated throughout the application. Verify both favicon.png and splash.png are properly generated and placed in the public folder.

### 4. UI Development
- Add new pages following existing patterns
- Reuse existing pages, layouts, components where possible
- Install or use shadcn components vs. creating custom components where possible
- Add required shadcn components: `npx shadcn add [component-name]`
- Keep component organization flat and simple
- Extend routing using react-router v7 as configured
- Update navigation components
- Add sample data to the Zustand store

**PHASE VERIFICATION**: Ensure all pages in the application analysis document are implemented. Verify routing works correctly between all pages. Confirm components use shadcn UI where appropriate.

### 5. Backend Configuration
- Create a mock `amplify_outputs.json` file for development
- Structure it to match expected backend resources
- This file will later be updated by an external build process

**PHASE VERIFICATION**: Confirm the mock amplify_outputs.json file is correctly formatted and contains all necessary configuration for local development.

**Example: Task App Mock Backend Configuration**
```json
{
  "auth": {
    "userPoolId": "mock-user-pool-id",
    "userPoolWebClientId": "mock-client-id",
    "region": "us-east-1",
    "identityPoolId": "mock-identity-pool-id"
  },
  "api": {
    "endpoints": [
      {
        "name": "TasksAPI",
        "endpoint": "https://example.com/api/tasks",
        "region": "us-east-1"
      }
    ]
  }
}
```

## Technical Guidelines

### State Management
- Always use central Zustand store instead of component state
- Avoid prop drilling completely
- Components should access store directly via hooks
- Only use component state for temporary UI states (form inputs while typing)

### Component Organization
- Keep component organization flat
- Place new components in appropriate existing folders
- Don't group by features unless app is complex
- Follow existing naming conventions
- Always use shadcn components if available

## Final check

Conduct a final check to make sure that all items in the CHECKLIST.md are completed with a high level of quality and there are no errors or missing functionality.
