# SaaS Project Management Multi-Table Schema Example

This example demonstrates a comprehensive multi-tenant SaaS project management application using multiple DynamoDB tables with complex hierarchical relationships and cross-table references.

## Architecture Overview

The schema is designed around three main tables representing the organizational hierarchy:
- **OrganizationTable**: Manages organizations, members, and invitations
- **ProjectTable**: Handles projects, milestones, and organization-project relationships
- **TaskTable**: Manages tasks, assignments, comments, and user-task relationships

## Tables and Entities

### OrganizationTable
- **Organization**: Company/team profiles with subscription plans
- **OrganizationMember**: Team members with roles and permissions
- **OrganizationInvite**: Pending invitations to join organizations

### ProjectTable
- **Project**: Project details with team assignments and budgets
- **ProjectMilestone**: Project milestones with completion tracking
- **OrganizationProject**: Organization's project index sorted by creation date

### TaskTable
- **Task**: Individual tasks with assignments and dependencies
- **ProjectTask**: Project's task index sorted by status and priority
- **UserTask**: User's assigned tasks sorted by status and due date
- **TaskComment**: Task comments with mentions and attachments

## Key Features Demonstrated

### Multi-Tenant Architecture
- Organizations as top-level tenants
- Member-based access control with roles and permissions
- Invitation system for team growth

### Hierarchical Relationships
- Organizations → Projects → Tasks
- Cross-references maintained at each level
- Efficient querying at any hierarchy level

### Complex Access Patterns
- **Organization management**: Members, projects, invitations
- **Project tracking**: Tasks, milestones, team assignments
- **User workload**: Personal task lists across projects
- **Time-based queries**: Tasks by due date, projects by creation date

### Advanced DynamoDB Patterns
- **Composite sort keys**: Enable complex sorting (status + priority + date)
- **Multiple access patterns**: Same data accessible via different indexes
- **Denormalization**: User/project names duplicated for performance
- **Time-series data**: Comments and history sorted by timestamp

## Sample Use Cases

1. **Organization Setup**: Create org, invite members, assign roles
2. **Project Management**: Create projects, set milestones, assign teams
3. **Task Tracking**: Create tasks, assign to users, track progress
4. **User Dashboard**: View assigned tasks across all projects
5. **Team Collaboration**: Comment on tasks, mention team members
6. **Reporting**: Project status, user workload, milestone tracking

## Cross-Table Entity References

The schema extensively uses cross-table entity references to maintain relationships:
- `create_project`: References Organization entity
- `create_organization_invite`: References OrganizationMember (inviter)
- `create_task`: References Project entity
- `assign_task_to_user`: References Task and OrganizationMember entities
- `add_task_comment`: References OrganizationMember (author)
- `add_project_to_organization`: References both Organization and Project

## Multi-Tenant Considerations

This design demonstrates key multi-tenant SaaS patterns:
- **Data isolation**: Each organization's data is partitioned
- **Scalable user management**: Role-based access control
- **Flexible project structures**: Projects can have different team compositions
- **Cross-project visibility**: Users can see tasks across all their projects

This schema showcases how to build a scalable SaaS application with complex organizational hierarchies while maintaining efficient query patterns and data consistency across multiple DynamoDB tables.
