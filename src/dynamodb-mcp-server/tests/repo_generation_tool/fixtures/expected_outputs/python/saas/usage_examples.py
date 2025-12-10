"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
import time
from decimal import Decimal

# Import generated entities and repositories
from entities import (
    Organization,
    OrganizationInvite,
    OrganizationMember,
    OrganizationProject,
    Project,
    ProjectMilestone,
    ProjectTask,
    Task,
    TaskComment,
    UserTask,
)
from repositories import (
    OrganizationInviteRepository,
    OrganizationMemberRepository,
    OrganizationProjectRepository,
    OrganizationRepository,
    ProjectMilestoneRepository,
    ProjectRepository,
    ProjectTaskRepository,
    TaskCommentRepository,
    TaskRepository,
    UserTaskRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # OrganizationTable table repositories
        self.organization_repo = OrganizationRepository('OrganizationTable')
        self.organizationmember_repo = OrganizationMemberRepository('OrganizationTable')
        self.organizationinvite_repo = OrganizationInviteRepository('OrganizationTable')
        # ProjectTable table repositories
        self.project_repo = ProjectRepository('ProjectTable')
        self.projectmilestone_repo = ProjectMilestoneRepository('ProjectTable')
        self.organizationproject_repo = OrganizationProjectRepository('ProjectTable')
        # TaskTable table repositories
        self.task_repo = TaskRepository('TaskTable')
        self.projecttask_repo = ProjectTaskRepository('TaskTable')
        self.usertask_repo = UserTaskRepository('TaskTable')
        self.taskcomment_repo = TaskCommentRepository('TaskTable')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== OrganizationTable Table Operations ===')

        # Organization example
        print('\n--- Organization ---')

        # 1. CREATE - Create sample organization
        sample_organization = Organization(
            org_id='org_id123',
            name='sample_name',
            domain='sample_domain',
            plan_type='sample_plan_type',
            max_users=42,
            max_projects=42,
            created_at='sample_created_at',
            updated_at='sample_updated_at',
            status='active',
            billing_email='sample_billing_email',
            settings={'key': 'value'},
        )

        print('📝 Creating organization...')
        print(f'📝 PK: {sample_organization.pk()}, SK: {sample_organization.sk()}')

        created_organization = self.organization_repo.create_organization(sample_organization)
        print(f'✅ Created: {created_organization}')

        # Store created entity for access pattern testing
        created_entities['Organization'] = created_organization
        # 2. UPDATE - Update non-key field (name)
        print('\n🔄 Updating name field...')
        original_value = created_organization.name
        created_organization.name = 'updated_name'

        updated_organization = self.organization_repo.update_organization(created_organization)
        print(f'✅ Updated name: {original_value} → {updated_organization.name}')

        # Update stored entity with updated values
        created_entities['Organization'] = updated_organization

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving organization...')
        retrieved_organization = self.organization_repo.get_organization(
            created_organization.org_id
        )

        if retrieved_organization:
            print(f'✅ Retrieved: {retrieved_organization}')
        else:
            print('❌ Failed to retrieve organization')

        print('🎯 Organization CRUD cycle completed successfully!')

        # OrganizationMember example
        print('\n--- OrganizationMember ---')

        # 1. CREATE - Create sample organizationmember
        sample_organizationmember = OrganizationMember(
            org_id='org_id123',
            user_id='user_id123',
            email='sample_email',
            first_name='sample_first_name',
            last_name='sample_last_name',
            role='sample_role',
            permissions=['sample1', 'sample2'],
            joined_at='sample_joined_at',
            last_active='sample_last_active',
            status='active',
        )

        print('📝 Creating organizationmember...')
        print(f'📝 PK: {sample_organizationmember.pk()}, SK: {sample_organizationmember.sk()}')

        created_organizationmember = self.organizationmember_repo.create_organization_member(
            sample_organizationmember
        )
        print(f'✅ Created: {created_organizationmember}')

        # Store created entity for access pattern testing
        created_entities['OrganizationMember'] = created_organizationmember
        # 2. UPDATE - Update non-key field (email)
        print('\n🔄 Updating email field...')
        original_value = created_organizationmember.email
        created_organizationmember.email = 'updated_email'

        updated_organizationmember = self.organizationmember_repo.update_organization_member(
            created_organizationmember
        )
        print(f'✅ Updated email: {original_value} → {updated_organizationmember.email}')

        # Update stored entity with updated values
        created_entities['OrganizationMember'] = updated_organizationmember

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving organizationmember...')
        retrieved_organizationmember = self.organizationmember_repo.get_organization_member(
            created_organizationmember.org_id, created_organizationmember.user_id
        )

        if retrieved_organizationmember:
            print(f'✅ Retrieved: {retrieved_organizationmember}')
        else:
            print('❌ Failed to retrieve organizationmember')

        print('🎯 OrganizationMember CRUD cycle completed successfully!')

        # OrganizationInvite example
        print('\n--- OrganizationInvite ---')

        # 1. CREATE - Create sample organizationinvite
        sample_organizationinvite = OrganizationInvite(
            org_id='org_id123',
            invite_id='invite_id123',
            email='sample_email',
            role='sample_role',
            invited_by='sample_invited_by',
            created_at='sample_created_at',
            expires_at='sample_expires_at',
            status='active',
            accepted_at='sample_accepted_at',
        )

        print('📝 Creating organizationinvite...')
        print(f'📝 PK: {sample_organizationinvite.pk()}, SK: {sample_organizationinvite.sk()}')

        created_organizationinvite = self.organizationinvite_repo.create_organization_invite(
            sample_organizationinvite
        )
        print(f'✅ Created: {created_organizationinvite}')

        # Store created entity for access pattern testing
        created_entities['OrganizationInvite'] = created_organizationinvite
        # 2. UPDATE - Update non-key field (email)
        print('\n🔄 Updating email field...')
        original_value = created_organizationinvite.email
        created_organizationinvite.email = 'updated_email'

        updated_organizationinvite = self.organizationinvite_repo.update_organization_invite(
            created_organizationinvite
        )
        print(f'✅ Updated email: {original_value} → {updated_organizationinvite.email}')

        # Update stored entity with updated values
        created_entities['OrganizationInvite'] = updated_organizationinvite

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving organizationinvite...')
        retrieved_organizationinvite = self.organizationinvite_repo.get_organization_invite(
            created_organizationinvite.org_id, created_organizationinvite.invite_id
        )

        if retrieved_organizationinvite:
            print(f'✅ Retrieved: {retrieved_organizationinvite}')
        else:
            print('❌ Failed to retrieve organizationinvite')

        print('🎯 OrganizationInvite CRUD cycle completed successfully!')
        print('\n=== ProjectTable Table Operations ===')

        # Project example
        print('\n--- Project ---')

        # 1. CREATE - Create sample project
        sample_project = Project(
            project_id='project_id123',
            org_id='org_id123',
            name='sample_name',
            description='sample_description',
            status='active',
            priority='sample_priority',
            owner_id='owner_id123',
            team_members=['sample1', 'sample2'],
            start_date='sample_start_date',
            due_date='sample_due_date',
            budget=Decimal('3.14'),
            currency='sample_currency',
            tags=['sample1', 'sample2'],
            created_at='sample_created_at',
            updated_at='sample_updated_at',
        )

        print('📝 Creating project...')
        print(f'📝 PK: {sample_project.pk()}, SK: {sample_project.sk()}')

        created_project = self.project_repo.create_project(sample_project)
        print(f'✅ Created: {created_project}')

        # Store created entity for access pattern testing
        created_entities['Project'] = created_project
        # 2. UPDATE - Update non-key field (org_id)
        print('\n🔄 Updating org_id field...')
        original_value = created_project.org_id
        created_project.org_id = 'updated_org_id'

        updated_project = self.project_repo.update_project(created_project)
        print(f'✅ Updated org_id: {original_value} → {updated_project.org_id}')

        # Update stored entity with updated values
        created_entities['Project'] = updated_project

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving project...')
        retrieved_project = self.project_repo.get_project(created_project.project_id)

        if retrieved_project:
            print(f'✅ Retrieved: {retrieved_project}')
        else:
            print('❌ Failed to retrieve project')

        print('🎯 Project CRUD cycle completed successfully!')

        # ProjectMilestone example
        print('\n--- ProjectMilestone ---')

        # 1. CREATE - Create sample projectmilestone
        sample_projectmilestone = ProjectMilestone(
            project_id='project_id123',
            milestone_id='milestone_id123',
            title='sample_title',
            description='sample_description',
            due_date='sample_due_date',
            status='active',
            completion_percentage=42,
            created_at='sample_created_at',
            completed_at='sample_completed_at',
        )

        print('📝 Creating projectmilestone...')
        print(f'📝 PK: {sample_projectmilestone.pk()}, SK: {sample_projectmilestone.sk()}')

        created_projectmilestone = self.projectmilestone_repo.create_project_milestone(
            sample_projectmilestone
        )
        print(f'✅ Created: {created_projectmilestone}')

        # Store created entity for access pattern testing
        created_entities['ProjectMilestone'] = created_projectmilestone
        # 2. UPDATE - Update non-key field (title)
        print('\n🔄 Updating title field...')
        original_value = created_projectmilestone.title
        created_projectmilestone.title = 'updated_title'

        updated_projectmilestone = self.projectmilestone_repo.update_project_milestone(
            created_projectmilestone
        )
        print(f'✅ Updated title: {original_value} → {updated_projectmilestone.title}')

        # Update stored entity with updated values
        created_entities['ProjectMilestone'] = updated_projectmilestone

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving projectmilestone...')
        retrieved_projectmilestone = self.projectmilestone_repo.get_project_milestone(
            created_projectmilestone.project_id, created_projectmilestone.milestone_id
        )

        if retrieved_projectmilestone:
            print(f'✅ Retrieved: {retrieved_projectmilestone}')
        else:
            print('❌ Failed to retrieve projectmilestone')

        print('🎯 ProjectMilestone CRUD cycle completed successfully!')

        # OrganizationProject example
        print('\n--- OrganizationProject ---')

        # 1. CREATE - Create sample organizationproject
        sample_organizationproject = OrganizationProject(
            org_id='org_id123',
            project_id='project_id123',
            project_name='sample_project_name',
            status='active',
            priority='sample_priority',
            owner_id='owner_id123',
            team_size=42,
            created_at='sample_created_at',
            due_date='sample_due_date',
        )

        print('📝 Creating organizationproject...')
        print(f'📝 PK: {sample_organizationproject.pk()}, SK: {sample_organizationproject.sk()}')

        created_organizationproject = self.organizationproject_repo.create_organization_project(
            sample_organizationproject
        )
        print(f'✅ Created: {created_organizationproject}')

        # Store created entity for access pattern testing
        created_entities['OrganizationProject'] = created_organizationproject
        # 2. UPDATE - Update non-key field (project_name)
        print('\n🔄 Updating project_name field...')
        original_value = created_organizationproject.project_name
        created_organizationproject.project_name = 'updated_project_name'

        updated_organizationproject = self.organizationproject_repo.update_organization_project(
            created_organizationproject
        )
        print(
            f'✅ Updated project_name: {original_value} → {updated_organizationproject.project_name}'
        )

        # Update stored entity with updated values
        created_entities['OrganizationProject'] = updated_organizationproject

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving organizationproject...')
        retrieved_organizationproject = self.organizationproject_repo.get_organization_project(
            created_organizationproject.org_id,
            created_organizationproject.created_at,
            created_organizationproject.project_id,
        )

        if retrieved_organizationproject:
            print(f'✅ Retrieved: {retrieved_organizationproject}')
        else:
            print('❌ Failed to retrieve organizationproject')

        print('🎯 OrganizationProject CRUD cycle completed successfully!')
        print('\n=== TaskTable Table Operations ===')

        # Task example
        print('\n--- Task ---')

        # 1. CREATE - Create sample task
        sample_task = Task(
            task_id='task_id123',
            project_id='project_id123',
            title='sample_title',
            description='sample_description',
            status='active',
            priority='sample_priority',
            assignee_id='assignee_id123',
            reporter_id='reporter_id123',
            estimated_hours=Decimal('3.14'),
            actual_hours=Decimal('3.14'),
            due_date='sample_due_date',
            labels=['sample1', 'sample2'],
            dependencies=['sample1', 'sample2'],
            created_at='sample_created_at',
            updated_at='sample_updated_at',
            completed_at='sample_completed_at',
        )

        print('📝 Creating task...')
        print(f'📝 PK: {sample_task.pk()}, SK: {sample_task.sk()}')

        created_task = self.task_repo.create_task(sample_task)
        print(f'✅ Created: {created_task}')

        # Store created entity for access pattern testing
        created_entities['Task'] = created_task
        # 2. UPDATE - Update non-key field (project_id)
        print('\n🔄 Updating project_id field...')
        original_value = created_task.project_id
        created_task.project_id = 'updated_project_id'

        updated_task = self.task_repo.update_task(created_task)
        print(f'✅ Updated project_id: {original_value} → {updated_task.project_id}')

        # Update stored entity with updated values
        created_entities['Task'] = updated_task

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving task...')
        retrieved_task = self.task_repo.get_task(created_task.task_id)

        if retrieved_task:
            print(f'✅ Retrieved: {retrieved_task}')
        else:
            print('❌ Failed to retrieve task')

        print('🎯 Task CRUD cycle completed successfully!')

        # ProjectTask example
        print('\n--- ProjectTask ---')

        # 1. CREATE - Create sample projecttask
        sample_projecttask = ProjectTask(
            project_id='project_id123',
            task_id='task_id123',
            title='sample_title',
            status='active',
            priority='sample_priority',
            assignee_id='assignee_id123',
            due_date='sample_due_date',
            estimated_hours=Decimal('3.14'),
            created_at='sample_created_at',
        )

        print('📝 Creating projecttask...')
        print(f'📝 PK: {sample_projecttask.pk()}, SK: {sample_projecttask.sk()}')

        created_projecttask = self.projecttask_repo.create_project_task(sample_projecttask)
        print(f'✅ Created: {created_projecttask}')

        # Store created entity for access pattern testing
        created_entities['ProjectTask'] = created_projecttask
        # 2. UPDATE - Update non-key field (title)
        print('\n🔄 Updating title field...')
        original_value = created_projecttask.title
        created_projecttask.title = 'updated_title'

        updated_projecttask = self.projecttask_repo.update_project_task(created_projecttask)
        print(f'✅ Updated title: {original_value} → {updated_projecttask.title}')

        # Update stored entity with updated values
        created_entities['ProjectTask'] = updated_projecttask

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving projecttask...')
        retrieved_projecttask = self.projecttask_repo.get_project_task(
            created_projecttask.project_id,
            created_projecttask.status,
            created_projecttask.priority,
            created_projecttask.task_id,
        )

        if retrieved_projecttask:
            print(f'✅ Retrieved: {retrieved_projecttask}')
        else:
            print('❌ Failed to retrieve projecttask')

        print('🎯 ProjectTask CRUD cycle completed successfully!')

        # UserTask example
        print('\n--- UserTask ---')

        # 1. CREATE - Create sample usertask
        sample_usertask = UserTask(
            user_id='user_id123',
            task_id='task_id123',
            project_id='project_id123',
            title='sample_title',
            status='active',
            priority='sample_priority',
            due_date='sample_due_date',
            estimated_hours=Decimal('3.14'),
            assigned_at='sample_assigned_at',
        )

        print('📝 Creating usertask...')
        print(f'📝 PK: {sample_usertask.pk()}, SK: {sample_usertask.sk()}')

        created_usertask = self.usertask_repo.create_user_task(sample_usertask)
        print(f'✅ Created: {created_usertask}')

        # Store created entity for access pattern testing
        created_entities['UserTask'] = created_usertask
        # 2. UPDATE - Update non-key field (project_id)
        print('\n🔄 Updating project_id field...')
        original_value = created_usertask.project_id
        created_usertask.project_id = 'updated_project_id'

        updated_usertask = self.usertask_repo.update_user_task(created_usertask)
        print(f'✅ Updated project_id: {original_value} → {updated_usertask.project_id}')

        # Update stored entity with updated values
        created_entities['UserTask'] = updated_usertask

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving usertask...')
        retrieved_usertask = self.usertask_repo.get_user_task(
            created_usertask.user_id,
            created_usertask.status,
            created_usertask.due_date,
            created_usertask.task_id,
        )

        if retrieved_usertask:
            print(f'✅ Retrieved: {retrieved_usertask}')
        else:
            print('❌ Failed to retrieve usertask')

        print('🎯 UserTask CRUD cycle completed successfully!')

        # TaskComment example
        print('\n--- TaskComment ---')

        # 1. CREATE - Create sample taskcomment
        sample_taskcomment = TaskComment(
            task_id='task_id123',
            comment_id='comment_id123',
            author_id='author_id123',
            content='sample_content',
            comment_type='sample_comment_type',
            created_at='sample_created_at',
            updated_at='sample_updated_at',
            mentions=['sample1', 'sample2'],
            attachments=['sample1', 'sample2'],
        )

        print('📝 Creating taskcomment...')
        print(f'📝 PK: {sample_taskcomment.pk()}, SK: {sample_taskcomment.sk()}')

        created_taskcomment = self.taskcomment_repo.create_task_comment(sample_taskcomment)
        print(f'✅ Created: {created_taskcomment}')

        # Store created entity for access pattern testing
        created_entities['TaskComment'] = created_taskcomment
        # 2. UPDATE - Update non-key field (author_id)
        print('\n🔄 Updating author_id field...')
        original_value = created_taskcomment.author_id
        created_taskcomment.author_id = 'updated_author_id'

        updated_taskcomment = self.taskcomment_repo.update_task_comment(created_taskcomment)
        print(f'✅ Updated author_id: {original_value} → {updated_taskcomment.author_id}')

        # Update stored entity with updated values
        created_entities['TaskComment'] = updated_taskcomment

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving taskcomment...')
        retrieved_taskcomment = self.taskcomment_repo.get_task_comment(
            created_taskcomment.task_id,
            created_taskcomment.created_at,
            created_taskcomment.comment_id,
        )

        if retrieved_taskcomment:
            print(f'✅ Retrieved: {retrieved_taskcomment}')
        else:
            print('❌ Failed to retrieve taskcomment')

        print('🎯 TaskComment CRUD cycle completed successfully!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed successfully!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete Organization
        if 'Organization' in created_entities:
            print('\n🗑️  Deleting organization...')
            deleted = self.organization_repo.delete_organization(
                created_entities['Organization'].org_id
            )

            if deleted:
                print('✅ Deleted organization successfully')
            else:
                print('❌ Failed to delete organization')

        # Delete OrganizationMember
        if 'OrganizationMember' in created_entities:
            print('\n🗑️  Deleting organizationmember...')
            deleted = self.organizationmember_repo.delete_organization_member(
                created_entities['OrganizationMember'].org_id,
                created_entities['OrganizationMember'].user_id,
            )

            if deleted:
                print('✅ Deleted organizationmember successfully')
            else:
                print('❌ Failed to delete organizationmember')

        # Delete OrganizationInvite
        if 'OrganizationInvite' in created_entities:
            print('\n🗑️  Deleting organizationinvite...')
            deleted = self.organizationinvite_repo.delete_organization_invite(
                created_entities['OrganizationInvite'].org_id,
                created_entities['OrganizationInvite'].invite_id,
            )

            if deleted:
                print('✅ Deleted organizationinvite successfully')
            else:
                print('❌ Failed to delete organizationinvite')

        # Delete Project
        if 'Project' in created_entities:
            print('\n🗑️  Deleting project...')
            deleted = self.project_repo.delete_project(created_entities['Project'].project_id)

            if deleted:
                print('✅ Deleted project successfully')
            else:
                print('❌ Failed to delete project')

        # Delete ProjectMilestone
        if 'ProjectMilestone' in created_entities:
            print('\n🗑️  Deleting projectmilestone...')
            deleted = self.projectmilestone_repo.delete_project_milestone(
                created_entities['ProjectMilestone'].project_id,
                created_entities['ProjectMilestone'].milestone_id,
            )

            if deleted:
                print('✅ Deleted projectmilestone successfully')
            else:
                print('❌ Failed to delete projectmilestone')

        # Delete OrganizationProject
        if 'OrganizationProject' in created_entities:
            print('\n🗑️  Deleting organizationproject...')
            deleted = self.organizationproject_repo.delete_organization_project(
                created_entities['OrganizationProject'].org_id,
                created_entities['OrganizationProject'].created_at,
                created_entities['OrganizationProject'].project_id,
            )

            if deleted:
                print('✅ Deleted organizationproject successfully')
            else:
                print('❌ Failed to delete organizationproject')

        # Delete Task
        if 'Task' in created_entities:
            print('\n🗑️  Deleting task...')
            deleted = self.task_repo.delete_task(created_entities['Task'].task_id)

            if deleted:
                print('✅ Deleted task successfully')
            else:
                print('❌ Failed to delete task')

        # Delete ProjectTask
        if 'ProjectTask' in created_entities:
            print('\n🗑️  Deleting projecttask...')
            deleted = self.projecttask_repo.delete_project_task(
                created_entities['ProjectTask'].project_id,
                created_entities['ProjectTask'].status,
                created_entities['ProjectTask'].priority,
                created_entities['ProjectTask'].task_id,
            )

            if deleted:
                print('✅ Deleted projecttask successfully')
            else:
                print('❌ Failed to delete projecttask')

        # Delete UserTask
        if 'UserTask' in created_entities:
            print('\n🗑️  Deleting usertask...')
            deleted = self.usertask_repo.delete_user_task(
                created_entities['UserTask'].user_id,
                created_entities['UserTask'].status,
                created_entities['UserTask'].due_date,
                created_entities['UserTask'].task_id,
            )

            if deleted:
                print('✅ Deleted usertask successfully')
            else:
                print('❌ Failed to delete usertask')

        # Delete TaskComment
        if 'TaskComment' in created_entities:
            print('\n🗑️  Deleting taskcomment...')
            deleted = self.taskcomment_repo.delete_task_comment(
                created_entities['TaskComment'].task_id,
                created_entities['TaskComment'].created_at,
                created_entities['TaskComment'].comment_id,
            )

            if deleted:
                print('✅ Deleted taskcomment successfully')
            else:
                print('❌ Failed to delete taskcomment')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'OrganizationTable' must exist")
        print("   - DynamoDB table 'ProjectTable' must exist")
        print("   - DynamoDB table 'TaskTable' must exist")
        print('   - AWS credentials configured')
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # Organization
        # Access Pattern #1: Get organization details by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: Get organization details by ID")
        #     print("   Using Main Table")
        #     org_id = created_entities["Organization"].org_id
        #     self.organization_repo.get_organization(
        #         org_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #2: Create new organization
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: Create new organization")
        #     print("   Using Main Table")
        #     organization = created_entities["Organization"]
        #     self.organization_repo.create_organization(
        #         organization,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # Access Pattern #3: Update organization subscription plan
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Update organization subscription plan")
        #     print("   Using Main Table")
        #     org_id = created_entities["Organization"].org_id
        #     plan_type = created_entities["Organization"].plan_type
        #     max_users = created_entities["Organization"].max_users
        #     max_projects = created_entities["Organization"].max_projects
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_org_id"
        #     self.organization_repo.update_organization_plan(
        #         org_id,
        #         plan_type,
        #         max_users,
        #         max_projects,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # OrganizationMember
        # Access Pattern #4: Get all members of an organization
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Get all members of an organization")
        #     print("   Using Main Table")
        #     org_id = created_entities["OrganizationMember"].org_id
        #     self.organizationmember_repo.get_organization_members(
        #         org_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #5: Add member to organization
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Add member to organization")
        #     print("   Using Main Table")
        #     member = created_entities["OrganizationMember"]
        #     self.organizationmember_repo.add_organization_member(
        #         member,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

        # Access Pattern #6: Update member role and permissions
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: Update member role and permissions")
        #     print("   Using Main Table")
        #     org_id = created_entities["OrganizationMember"].org_id
        #     user_id = created_entities["OrganizationMember"].user_id
        #     role = created_entities["OrganizationMember"].role
        #     permissions = created_entities["OrganizationMember"].permissions
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_org_id"
        #     self.organizationmember_repo.update_member_role(
        #         org_id,
        #         user_id,
        #         role,
        #         permissions,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        # OrganizationInvite
        # Access Pattern #7: Get pending invites for organization
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Get pending invites for organization")
        #     print("   Using Main Table")
        #     org_id = created_entities["OrganizationInvite"].org_id
        #     self.organizationinvite_repo.get_organization_invites(
        #         org_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Access Pattern #8: Create organization invite with member reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Create organization invite with member reference")
        #     print("   Using Main Table")
        #     invite = created_entities["OrganizationInvite"]
        #     inviter = created_entities["OrganizationMember"]
        #     self.organizationinvite_repo.create_organization_invite_with_refs(
        #         invite,
        #         inviter,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # Project
        # Access Pattern #9: Get project details by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Get project details by ID")
        #     print("   Using Main Table")
        #     project_id = created_entities["Project"].project_id
        #     self.project_repo.get_project(
        #         project_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # Access Pattern #10: Create new project with organization reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Create new project with organization reference")
        #     print("   Using Main Table")
        #     project = created_entities["Project"]
        #     organization = created_entities["Organization"]
        #     self.project_repo.create_project_with_refs(
        #         project,
        #         organization,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

        # Access Pattern #11: Update project status and progress
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #11: Update project status and progress")
        #     print("   Using Main Table")
        #     project_id = created_entities["Project"].project_id
        #     status = created_entities["Project"].status
        #     updated_at = created_entities["Project"].updated_at
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_project_id"
        #     self.project_repo.update_project_status(
        #         project_id,
        #         status,
        #         updated_at,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #11: {e}")

        # ProjectMilestone
        # Access Pattern #12: Get all milestones for a project
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #12: Get all milestones for a project")
        #     print("   Using Main Table")
        #     project_id = created_entities["ProjectMilestone"].project_id
        #     self.projectmilestone_repo.get_project_milestones(
        #         project_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #12: {e}")

        # Access Pattern #13: Create milestone for project
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #13: Create milestone for project")
        #     print("   Using Main Table")
        #     milestone = created_entities["ProjectMilestone"]
        #     self.projectmilestone_repo.create_project_milestone(
        #         milestone,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #13: {e}")

        # OrganizationProject
        # Access Pattern #14: Get all projects for an organization (sorted by creation date)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #14: Get all projects for an organization (sorted by creation date)")
        #     print("   Using Main Table")
        #     org_id = created_entities["OrganizationProject"].org_id
        #     self.organizationproject_repo.get_organization_projects(
        #         org_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #14: {e}")

        # Access Pattern #15: Add project to organization index with cross-table references
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #15: Add project to organization index with cross-table references")
        #     print("   Using Main Table")
        #     org_project = created_entities["OrganizationProject"]
        #     organization = created_entities["Organization"]
        #     project = created_entities["Project"]
        #     self.organizationproject_repo.add_project_to_organization(
        #         org_project,
        #         organization,
        #         project,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #15: {e}")

        # Task
        # Access Pattern #16: Get task details by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #16: Get task details by ID")
        #     print("   Using Main Table")
        #     task_id = created_entities["Task"].task_id
        #     self.task_repo.get_task(
        #         task_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #16: {e}")

        # Access Pattern #17: Create new task with project reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #17: Create new task with project reference")
        #     print("   Using Main Table")
        #     task = created_entities["Task"]
        #     project = created_entities["Project"]
        #     self.task_repo.create_task_with_refs(
        #         task,
        #         project,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #17: {e}")

        # Access Pattern #18: Update task status and completion
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #18: Update task status and completion")
        #     print("   Using Main Table")
        #     task_id = created_entities["Task"].task_id
        #     status = created_entities["Task"].status
        #     actual_hours = created_entities["Task"].actual_hours
        #     completed_at = created_entities["Task"].completed_at
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_task_id"
        #     self.task_repo.update_task_status(
        #         task_id,
        #         status,
        #         actual_hours,
        #         completed_at,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #18: {e}")

        # ProjectTask
        # Access Pattern #19: Get all tasks for a project (sorted by status and priority)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #19: Get all tasks for a project (sorted by status and priority)")
        #     print("   Using Main Table")
        #     project_id = created_entities["ProjectTask"].project_id
        #     self.projecttask_repo.get_project_tasks(
        #         project_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #19: {e}")

        # Access Pattern #20: Get tasks for a project filtered by status
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #20: Get tasks for a project filtered by status")
        #     print("   Using Main Table")
        #     project_id = created_entities["ProjectTask"].project_id
        #     status = created_entities["ProjectTask"].status
        #     self.projecttask_repo.get_project_tasks_by_status(
        #         project_id,
        #         status,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #20: {e}")

        # Access Pattern #21: Add task to project index
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #21: Add task to project index")
        #     print("   Using Main Table")
        #     project_task = created_entities["ProjectTask"]
        #     self.projecttask_repo.add_task_to_project(
        #         project_task,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #21: {e}")

        # UserTask
        # Access Pattern #22: Get all tasks assigned to a user (sorted by status and due date)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #22: Get all tasks assigned to a user (sorted by status and due date)")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserTask"].user_id
        #     self.usertask_repo.get_user_tasks(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #22: {e}")

        # Access Pattern #23: Get active tasks for a user
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #23: Get active tasks for a user")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserTask"].user_id
        #     status = created_entities["UserTask"].status
        #     self.usertask_repo.get_user_active_tasks(
        #         user_id,
        #         status,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #23: {e}")

        # Access Pattern #24: Assign task to user with cross-table references
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #24: Assign task to user with cross-table references")
        #     print("   Using Main Table")
        #     user_task = created_entities["UserTask"]
        #     task = created_entities["Task"]
        #     member = created_entities["OrganizationMember"]
        #     self.usertask_repo.assign_task_to_user(
        #         user_task,
        #         task,
        #         member,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #24: {e}")

        # TaskComment
        # Access Pattern #25: Get all comments for a task (sorted by creation time)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #25: Get all comments for a task (sorted by creation time)")
        #     print("   Using Main Table")
        #     task_id = created_entities["TaskComment"].task_id
        #     self.taskcomment_repo.get_task_comments(
        #         task_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #25: {e}")

        # Access Pattern #26: Add comment to task with author reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #26: Add comment to task with author reference")
        #     print("   Using Main Table")
        #     comment = created_entities["TaskComment"]
        #     author = created_entities["OrganizationMember"]
        #     self.taskcomment_repo.add_task_comment(
        #         comment,
        #         author,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #26: {e}")

        print('\n💡 Access Pattern Implementation Notes:')
        print('   - Main Table queries use partition key and sort key')
        print('   - GSI queries use different key structures and may have range conditions')
        print(
            '   - Range conditions (begins_with, between, >, <, >=, <=) require additional parameters'
        )
        print('   - Implement the access pattern methods in your repository classes')


def main():
    """Main function to run examples"""
    # Parse command line arguments
    include_additional_access_patterns = '--all' in sys.argv

    # Check if we're running against DynamoDB Local
    endpoint_url = os.getenv('AWS_ENDPOINT_URL_DYNAMODB')
    if endpoint_url:
        print(f'🔗 Using DynamoDB endpoint: {endpoint_url}')
        print(f'🌍 Using region: {os.getenv("AWS_DEFAULT_REGION", "us-east-1")}')
    else:
        print('🌐 Using AWS DynamoDB (no local endpoint specified)')

    print('📊 Using multiple tables:')
    print('   - OrganizationTable')
    print('   - ProjectTable')
    print('   - TaskTable')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
