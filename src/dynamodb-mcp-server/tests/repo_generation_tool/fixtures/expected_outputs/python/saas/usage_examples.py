"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
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
        try:
            self.organization_repo = OrganizationRepository('OrganizationTable')
            print("✅ Initialized OrganizationRepository for table 'OrganizationTable'")
        except Exception as e:
            print(f'❌ Failed to initialize OrganizationRepository: {e}')
            self.organization_repo = None
        try:
            self.organizationinvite_repo = OrganizationInviteRepository('OrganizationTable')
            print("✅ Initialized OrganizationInviteRepository for table 'OrganizationTable'")
        except Exception as e:
            print(f'❌ Failed to initialize OrganizationInviteRepository: {e}')
            self.organizationinvite_repo = None
        try:
            self.organizationmember_repo = OrganizationMemberRepository('OrganizationTable')
            print("✅ Initialized OrganizationMemberRepository for table 'OrganizationTable'")
        except Exception as e:
            print(f'❌ Failed to initialize OrganizationMemberRepository: {e}')
            self.organizationmember_repo = None
        # ProjectTable table repositories
        try:
            self.organizationproject_repo = OrganizationProjectRepository('ProjectTable')
            print("✅ Initialized OrganizationProjectRepository for table 'ProjectTable'")
        except Exception as e:
            print(f'❌ Failed to initialize OrganizationProjectRepository: {e}')
            self.organizationproject_repo = None
        try:
            self.project_repo = ProjectRepository('ProjectTable')
            print("✅ Initialized ProjectRepository for table 'ProjectTable'")
        except Exception as e:
            print(f'❌ Failed to initialize ProjectRepository: {e}')
            self.project_repo = None
        try:
            self.projectmilestone_repo = ProjectMilestoneRepository('ProjectTable')
            print("✅ Initialized ProjectMilestoneRepository for table 'ProjectTable'")
        except Exception as e:
            print(f'❌ Failed to initialize ProjectMilestoneRepository: {e}')
            self.projectmilestone_repo = None
        # TaskTable table repositories
        try:
            self.projecttask_repo = ProjectTaskRepository('TaskTable')
            print("✅ Initialized ProjectTaskRepository for table 'TaskTable'")
        except Exception as e:
            print(f'❌ Failed to initialize ProjectTaskRepository: {e}')
            self.projecttask_repo = None
        try:
            self.task_repo = TaskRepository('TaskTable')
            print("✅ Initialized TaskRepository for table 'TaskTable'")
        except Exception as e:
            print(f'❌ Failed to initialize TaskRepository: {e}')
            self.task_repo = None
        try:
            self.taskcomment_repo = TaskCommentRepository('TaskTable')
            print("✅ Initialized TaskCommentRepository for table 'TaskTable'")
        except Exception as e:
            print(f'❌ Failed to initialize TaskCommentRepository: {e}')
            self.taskcomment_repo = None
        try:
            self.usertask_repo = UserTaskRepository('TaskTable')
            print("✅ Initialized UserTaskRepository for table 'TaskTable'")
        except Exception as e:
            print(f'❌ Failed to initialize UserTaskRepository: {e}')
            self.usertask_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete Organization (org_id)
        try:
            sample_organization = Organization(
                org_id='org-12345',
                name='TechCorp Solutions',
                domain='techcorp.com',
                plan_type='premium',
                max_users=50,
                max_projects=25,
                created_at='2024-01-01T00:00:00Z',
                updated_at='2024-01-01T00:00:00Z',
                status='active',
                billing_email='billing@techcorp.com',
                settings={'notifications': True, 'theme': 'light'},
            )
            self.organization_repo.delete_organization(sample_organization.org_id)
            print('   🗑️  Deleted leftover organization (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete OrganizationInvite (org_id, invite_id)
        try:
            sample_organizationinvite = OrganizationInvite(
                org_id='org-12345',
                invite_id='invite-67890',
                email='newuser@example.com',
                role='member',
                invited_by='user-11111',
                created_at='2024-01-15T10:00:00Z',
                expires_at='2024-01-22T10:00:00Z',
                status='pending',
                accepted_at='None',
            )
            self.organizationinvite_repo.delete_organization_invite(
                sample_organizationinvite.org_id, sample_organizationinvite.invite_id
            )
            print('   🗑️  Deleted leftover organizationinvite (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete OrganizationMember (org_id, user_id)
        try:
            sample_organizationmember = OrganizationMember(
                org_id='org-12345',
                user_id='user-11111',
                email='john.doe@techcorp.com',
                first_name='John',
                last_name='Doe',
                role='admin',
                permissions=['read', 'write', 'admin'],
                joined_at='2024-01-01T00:00:00Z',
                last_active='2024-01-20T16:30:00Z',
                status='active',
            )
            self.organizationmember_repo.delete_organization_member(
                sample_organizationmember.org_id, sample_organizationmember.user_id
            )
            print('   🗑️  Deleted leftover organizationmember (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete OrganizationProject (org_id, created_at, project_id)
        try:
            sample_organizationproject = OrganizationProject(
                org_id='org-12345',
                project_id='project-22222',
                project_name='Mobile App Development',
                status='active',
                priority='high',
                owner_id='user-11111',
                team_size=5,
                created_at='2024-01-10T08:00:00Z',
                due_date='2024-03-15T23:59:59Z',
            )
            self.organizationproject_repo.delete_organization_project(
                sample_organizationproject.org_id,
                sample_organizationproject.created_at,
                sample_organizationproject.project_id,
            )
            print('   🗑️  Deleted leftover organizationproject (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Project (project_id)
        try:
            sample_project = Project(
                project_id='project-22222',
                org_id='org-12345',
                name='Mobile App Development',
                description='Developing a cross-platform mobile application for customer engagement',
                status='active',
                priority='high',
                owner_id='user-11111',
                team_members=['user-11111', 'user-22222', 'user-33333'],
                start_date='2024-01-10T08:00:00Z',
                due_date='2024-03-15T23:59:59Z',
                budget=Decimal('50000.0'),
                currency='USD',
                tags=['mobile', 'cross-platform', 'customer-engagement'],
                created_at='2024-01-10T08:00:00Z',
                updated_at='2024-01-10T08:00:00Z',
            )
            self.project_repo.delete_project(sample_project.project_id)
            print('   🗑️  Deleted leftover project (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete ProjectMilestone (project_id, milestone_id)
        try:
            sample_projectmilestone = ProjectMilestone(
                project_id='project-22222',
                milestone_id='milestone-33333',
                title='UI/UX Design Complete',
                description='Complete all user interface and user experience designs',
                due_date='2024-02-01T23:59:59Z',
                status='completed',
                completion_percentage=100,
                created_at='2024-01-12T09:00:00Z',
                completed_at='2024-01-30T17:00:00Z',
            )
            self.projectmilestone_repo.delete_project_milestone(
                sample_projectmilestone.project_id, sample_projectmilestone.milestone_id
            )
            print('   🗑️  Deleted leftover projectmilestone (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete ProjectTask (project_id, status, priority, task_id)
        try:
            sample_projecttask = ProjectTask(
                project_id='project-22222',
                task_id='task-44444',
                title='Implement user authentication',
                status='in_progress',
                priority='high',
                assignee_id='user-11111',
                due_date='2024-01-25T17:00:00Z',
                estimated_hours=Decimal('16.0'),
                created_at='2024-01-12T09:00:00Z',
            )
            self.projecttask_repo.delete_project_task(
                sample_projecttask.project_id,
                sample_projecttask.status,
                sample_projecttask.priority,
                sample_projecttask.task_id,
            )
            print('   🗑️  Deleted leftover projecttask (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Task (task_id)
        try:
            sample_task = Task(
                task_id='task-44444',
                project_id='project-22222',
                title='Implement user authentication',
                description='Create secure login and registration system with JWT tokens',
                status='in_progress',
                priority='high',
                assignee_id='user-11111',
                reporter_id='user-22222',
                estimated_hours=Decimal('16.0'),
                actual_hours=Decimal('3.14'),
                due_date='2024-01-25T17:00:00Z',
                labels=['authentication', 'security', 'backend'],
                dependencies=['task-33333'],
                created_at='2024-01-12T09:00:00Z',
                updated_at='2024-01-12T09:00:00Z',
                completed_at='None',
            )
            self.task_repo.delete_task(sample_task.task_id)
            print('   🗑️  Deleted leftover task (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TaskComment (task_id, created_at, comment_id)
        try:
            sample_taskcomment = TaskComment(
                task_id='task-44444',
                comment_id='comment-55555',
                author_id='user-11111',
                content='Started working on the authentication flow. JWT implementation is in progress.',
                comment_type='update',
                created_at='2024-01-15T14:30:00Z',
                updated_at='None',
                mentions=['user-22222'],
                attachments=['auth-diagram.png'],
            )
            self.taskcomment_repo.delete_task_comment(
                sample_taskcomment.task_id,
                sample_taskcomment.created_at,
                sample_taskcomment.comment_id,
            )
            print('   🗑️  Deleted leftover taskcomment (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete UserTask (user_id, status, due_date, task_id)
        try:
            sample_usertask = UserTask(
                user_id='user-11111',
                task_id='task-44444',
                project_id='project-22222',
                title='Implement user authentication',
                status='in_progress',
                priority='high',
                due_date='2024-01-25T17:00:00Z',
                estimated_hours=Decimal('16.0'),
                assigned_at='2024-01-12T09:00:00Z',
            )
            self.usertask_repo.delete_user_task(
                sample_usertask.user_id,
                sample_usertask.status,
                sample_usertask.due_date,
                sample_usertask.task_id,
            )
            print('   🗑️  Deleted leftover usertask (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== OrganizationTable Table Operations ===')

        # Organization example
        print('\n--- Organization ---')

        # 1. CREATE - Create sample organization
        sample_organization = Organization(
            org_id='org-12345',
            name='TechCorp Solutions',
            domain='techcorp.com',
            plan_type='premium',
            max_users=50,
            max_projects=25,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z',
            status='active',
            billing_email='billing@techcorp.com',
            settings={'notifications': True, 'theme': 'light'},
        )

        print('📝 Creating organization...')
        print(f'📝 PK: {sample_organization.pk()}, SK: {sample_organization.sk()}')

        try:
            created_organization = self.organization_repo.create_organization(sample_organization)
            print(f'✅ Created: {created_organization}')
            # Store created entity for access pattern testing
            created_entities['Organization'] = created_organization
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  organization already exists, retrieving existing entity...')
                try:
                    existing_organization = self.organization_repo.get_organization(
                        sample_organization.org_id
                    )

                    if existing_organization:
                        print(f'✅ Retrieved existing: {existing_organization}')
                        # Store existing entity for access pattern testing
                        created_entities['Organization'] = existing_organization
                    else:
                        print('❌ Failed to retrieve existing organization')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing organization: {get_error}')
            else:
                print(f'❌ Failed to create organization: {e}')
        # 2. UPDATE - Update non-key field (name)
        if 'Organization' in created_entities:
            print('\n🔄 Updating name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Organization']
                refreshed_entity = self.organization_repo.get_organization(
                    entity_for_refresh.org_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.name
                    refreshed_entity.name = 'TechCorp Solutions Inc.'

                    updated_organization = self.organization_repo.update_organization(
                        refreshed_entity
                    )
                    print(f'✅ Updated name: {original_value} → {updated_organization.name}')

                    # Update stored entity with updated values
                    created_entities['Organization'] = updated_organization
                else:
                    print('❌ Could not refresh organization for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  organization was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update organization: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Organization' in created_entities:
            print('\n🔍 Retrieving organization...')
            try:
                entity_for_get = created_entities['Organization']
                retrieved_organization = self.organization_repo.get_organization(
                    entity_for_get.org_id
                )

                if retrieved_organization:
                    print(f'✅ Retrieved: {retrieved_organization}')
                else:
                    print('❌ Failed to retrieve organization')
            except Exception as e:
                print(f'❌ Failed to retrieve organization: {e}')

        print('🎯 Organization CRUD cycle completed!')

        # OrganizationInvite example
        print('\n--- OrganizationInvite ---')

        # 1. CREATE - Create sample organizationinvite
        sample_organizationinvite = OrganizationInvite(
            org_id='org-12345',
            invite_id='invite-67890',
            email='newuser@example.com',
            role='member',
            invited_by='user-11111',
            created_at='2024-01-15T10:00:00Z',
            expires_at='2024-01-22T10:00:00Z',
            status='pending',
            accepted_at='None',
        )

        print('📝 Creating organizationinvite...')
        print(f'📝 PK: {sample_organizationinvite.pk()}, SK: {sample_organizationinvite.sk()}')

        try:
            created_organizationinvite = self.organizationinvite_repo.create_organization_invite(
                sample_organizationinvite
            )
            print(f'✅ Created: {created_organizationinvite}')
            # Store created entity for access pattern testing
            created_entities['OrganizationInvite'] = created_organizationinvite
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  organizationinvite already exists, retrieving existing entity...')
                try:
                    existing_organizationinvite = (
                        self.organizationinvite_repo.get_organization_invite(
                            sample_organizationinvite.org_id, sample_organizationinvite.invite_id
                        )
                    )

                    if existing_organizationinvite:
                        print(f'✅ Retrieved existing: {existing_organizationinvite}')
                        # Store existing entity for access pattern testing
                        created_entities['OrganizationInvite'] = existing_organizationinvite
                    else:
                        print('❌ Failed to retrieve existing organizationinvite')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing organizationinvite: {get_error}')
            else:
                print(f'❌ Failed to create organizationinvite: {e}')
        # 2. UPDATE - Update non-key field (role)
        if 'OrganizationInvite' in created_entities:
            print('\n🔄 Updating role field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['OrganizationInvite']
                refreshed_entity = self.organizationinvite_repo.get_organization_invite(
                    entity_for_refresh.org_id, entity_for_refresh.invite_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.role
                    refreshed_entity.role = 'admin'

                    updated_organizationinvite = (
                        self.organizationinvite_repo.update_organization_invite(refreshed_entity)
                    )
                    print(f'✅ Updated role: {original_value} → {updated_organizationinvite.role}')

                    # Update stored entity with updated values
                    created_entities['OrganizationInvite'] = updated_organizationinvite
                else:
                    print('❌ Could not refresh organizationinvite for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  organizationinvite was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update organizationinvite: {e}')

        # 3. GET - Retrieve and print the entity
        if 'OrganizationInvite' in created_entities:
            print('\n🔍 Retrieving organizationinvite...')
            try:
                entity_for_get = created_entities['OrganizationInvite']
                retrieved_organizationinvite = (
                    self.organizationinvite_repo.get_organization_invite(
                        entity_for_get.org_id, entity_for_get.invite_id
                    )
                )

                if retrieved_organizationinvite:
                    print(f'✅ Retrieved: {retrieved_organizationinvite}')
                else:
                    print('❌ Failed to retrieve organizationinvite')
            except Exception as e:
                print(f'❌ Failed to retrieve organizationinvite: {e}')

        print('🎯 OrganizationInvite CRUD cycle completed!')

        # OrganizationMember example
        print('\n--- OrganizationMember ---')

        # 1. CREATE - Create sample organizationmember
        sample_organizationmember = OrganizationMember(
            org_id='org-12345',
            user_id='user-11111',
            email='john.doe@techcorp.com',
            first_name='John',
            last_name='Doe',
            role='admin',
            permissions=['read', 'write', 'admin'],
            joined_at='2024-01-01T00:00:00Z',
            last_active='2024-01-20T16:30:00Z',
            status='active',
        )

        print('📝 Creating organizationmember...')
        print(f'📝 PK: {sample_organizationmember.pk()}, SK: {sample_organizationmember.sk()}')

        try:
            created_organizationmember = self.organizationmember_repo.create_organization_member(
                sample_organizationmember
            )
            print(f'✅ Created: {created_organizationmember}')
            # Store created entity for access pattern testing
            created_entities['OrganizationMember'] = created_organizationmember
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  organizationmember already exists, retrieving existing entity...')
                try:
                    existing_organizationmember = (
                        self.organizationmember_repo.get_organization_member(
                            sample_organizationmember.org_id, sample_organizationmember.user_id
                        )
                    )

                    if existing_organizationmember:
                        print(f'✅ Retrieved existing: {existing_organizationmember}')
                        # Store existing entity for access pattern testing
                        created_entities['OrganizationMember'] = existing_organizationmember
                    else:
                        print('❌ Failed to retrieve existing organizationmember')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing organizationmember: {get_error}')
            else:
                print(f'❌ Failed to create organizationmember: {e}')
        # 2. UPDATE - Update non-key field (role)
        if 'OrganizationMember' in created_entities:
            print('\n🔄 Updating role field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['OrganizationMember']
                refreshed_entity = self.organizationmember_repo.get_organization_member(
                    entity_for_refresh.org_id, entity_for_refresh.user_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.role
                    refreshed_entity.role = 'owner'

                    updated_organizationmember = (
                        self.organizationmember_repo.update_organization_member(refreshed_entity)
                    )
                    print(f'✅ Updated role: {original_value} → {updated_organizationmember.role}')

                    # Update stored entity with updated values
                    created_entities['OrganizationMember'] = updated_organizationmember
                else:
                    print('❌ Could not refresh organizationmember for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  organizationmember was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update organizationmember: {e}')

        # 3. GET - Retrieve and print the entity
        if 'OrganizationMember' in created_entities:
            print('\n🔍 Retrieving organizationmember...')
            try:
                entity_for_get = created_entities['OrganizationMember']
                retrieved_organizationmember = (
                    self.organizationmember_repo.get_organization_member(
                        entity_for_get.org_id, entity_for_get.user_id
                    )
                )

                if retrieved_organizationmember:
                    print(f'✅ Retrieved: {retrieved_organizationmember}')
                else:
                    print('❌ Failed to retrieve organizationmember')
            except Exception as e:
                print(f'❌ Failed to retrieve organizationmember: {e}')

        print('🎯 OrganizationMember CRUD cycle completed!')
        print('\n=== ProjectTable Table Operations ===')

        # OrganizationProject example
        print('\n--- OrganizationProject ---')

        # 1. CREATE - Create sample organizationproject
        sample_organizationproject = OrganizationProject(
            org_id='org-12345',
            project_id='project-22222',
            project_name='Mobile App Development',
            status='active',
            priority='high',
            owner_id='user-11111',
            team_size=5,
            created_at='2024-01-10T08:00:00Z',
            due_date='2024-03-15T23:59:59Z',
        )

        print('📝 Creating organizationproject...')
        print(f'📝 PK: {sample_organizationproject.pk()}, SK: {sample_organizationproject.sk()}')

        try:
            created_organizationproject = (
                self.organizationproject_repo.create_organization_project(
                    sample_organizationproject
                )
            )
            print(f'✅ Created: {created_organizationproject}')
            # Store created entity for access pattern testing
            created_entities['OrganizationProject'] = created_organizationproject
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  organizationproject already exists, retrieving existing entity...')
                try:
                    existing_organizationproject = (
                        self.organizationproject_repo.get_organization_project(
                            sample_organizationproject.org_id,
                            sample_organizationproject.created_at,
                            sample_organizationproject.project_id,
                        )
                    )

                    if existing_organizationproject:
                        print(f'✅ Retrieved existing: {existing_organizationproject}')
                        # Store existing entity for access pattern testing
                        created_entities['OrganizationProject'] = existing_organizationproject
                    else:
                        print('❌ Failed to retrieve existing organizationproject')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing organizationproject: {get_error}')
            else:
                print(f'❌ Failed to create organizationproject: {e}')
        # 2. UPDATE - Update non-key field (project_name)
        if 'OrganizationProject' in created_entities:
            print('\n🔄 Updating project_name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['OrganizationProject']
                refreshed_entity = self.organizationproject_repo.get_organization_project(
                    entity_for_refresh.org_id,
                    entity_for_refresh.created_at,
                    entity_for_refresh.project_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.project_name
                    refreshed_entity.project_name = 'Mobile App Development v2.0'

                    updated_organizationproject = (
                        self.organizationproject_repo.update_organization_project(refreshed_entity)
                    )
                    print(
                        f'✅ Updated project_name: {original_value} → {updated_organizationproject.project_name}'
                    )

                    # Update stored entity with updated values
                    created_entities['OrganizationProject'] = updated_organizationproject
                else:
                    print('❌ Could not refresh organizationproject for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  organizationproject was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update organizationproject: {e}')

        # 3. GET - Retrieve and print the entity
        if 'OrganizationProject' in created_entities:
            print('\n🔍 Retrieving organizationproject...')
            try:
                entity_for_get = created_entities['OrganizationProject']
                retrieved_organizationproject = (
                    self.organizationproject_repo.get_organization_project(
                        entity_for_get.org_id, entity_for_get.created_at, entity_for_get.project_id
                    )
                )

                if retrieved_organizationproject:
                    print(f'✅ Retrieved: {retrieved_organizationproject}')
                else:
                    print('❌ Failed to retrieve organizationproject')
            except Exception as e:
                print(f'❌ Failed to retrieve organizationproject: {e}')

        print('🎯 OrganizationProject CRUD cycle completed!')

        # Project example
        print('\n--- Project ---')

        # 1. CREATE - Create sample project
        sample_project = Project(
            project_id='project-22222',
            org_id='org-12345',
            name='Mobile App Development',
            description='Developing a cross-platform mobile application for customer engagement',
            status='active',
            priority='high',
            owner_id='user-11111',
            team_members=['user-11111', 'user-22222', 'user-33333'],
            start_date='2024-01-10T08:00:00Z',
            due_date='2024-03-15T23:59:59Z',
            budget=Decimal('50000.0'),
            currency='USD',
            tags=['mobile', 'cross-platform', 'customer-engagement'],
            created_at='2024-01-10T08:00:00Z',
            updated_at='2024-01-10T08:00:00Z',
        )

        print('📝 Creating project...')
        print(f'📝 PK: {sample_project.pk()}, SK: {sample_project.sk()}')

        try:
            created_project = self.project_repo.create_project(sample_project)
            print(f'✅ Created: {created_project}')
            # Store created entity for access pattern testing
            created_entities['Project'] = created_project
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  project already exists, retrieving existing entity...')
                try:
                    existing_project = self.project_repo.get_project(sample_project.project_id)

                    if existing_project:
                        print(f'✅ Retrieved existing: {existing_project}')
                        # Store existing entity for access pattern testing
                        created_entities['Project'] = existing_project
                    else:
                        print('❌ Failed to retrieve existing project')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing project: {get_error}')
            else:
                print(f'❌ Failed to create project: {e}')
        # 2. UPDATE - Update non-key field (name)
        if 'Project' in created_entities:
            print('\n🔄 Updating name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Project']
                refreshed_entity = self.project_repo.get_project(entity_for_refresh.project_id)

                if refreshed_entity:
                    original_value = refreshed_entity.name
                    refreshed_entity.name = 'Mobile App Development v2.0'

                    updated_project = self.project_repo.update_project(refreshed_entity)
                    print(f'✅ Updated name: {original_value} → {updated_project.name}')

                    # Update stored entity with updated values
                    created_entities['Project'] = updated_project
                else:
                    print('❌ Could not refresh project for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  project was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update project: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Project' in created_entities:
            print('\n🔍 Retrieving project...')
            try:
                entity_for_get = created_entities['Project']
                retrieved_project = self.project_repo.get_project(entity_for_get.project_id)

                if retrieved_project:
                    print(f'✅ Retrieved: {retrieved_project}')
                else:
                    print('❌ Failed to retrieve project')
            except Exception as e:
                print(f'❌ Failed to retrieve project: {e}')

        print('🎯 Project CRUD cycle completed!')

        # ProjectMilestone example
        print('\n--- ProjectMilestone ---')

        # 1. CREATE - Create sample projectmilestone
        sample_projectmilestone = ProjectMilestone(
            project_id='project-22222',
            milestone_id='milestone-33333',
            title='UI/UX Design Complete',
            description='Complete all user interface and user experience designs',
            due_date='2024-02-01T23:59:59Z',
            status='completed',
            completion_percentage=100,
            created_at='2024-01-12T09:00:00Z',
            completed_at='2024-01-30T17:00:00Z',
        )

        print('📝 Creating projectmilestone...')
        print(f'📝 PK: {sample_projectmilestone.pk()}, SK: {sample_projectmilestone.sk()}')

        try:
            created_projectmilestone = self.projectmilestone_repo.create_project_milestone(
                sample_projectmilestone
            )
            print(f'✅ Created: {created_projectmilestone}')
            # Store created entity for access pattern testing
            created_entities['ProjectMilestone'] = created_projectmilestone
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  projectmilestone already exists, retrieving existing entity...')
                try:
                    existing_projectmilestone = self.projectmilestone_repo.get_project_milestone(
                        sample_projectmilestone.project_id, sample_projectmilestone.milestone_id
                    )

                    if existing_projectmilestone:
                        print(f'✅ Retrieved existing: {existing_projectmilestone}')
                        # Store existing entity for access pattern testing
                        created_entities['ProjectMilestone'] = existing_projectmilestone
                    else:
                        print('❌ Failed to retrieve existing projectmilestone')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing projectmilestone: {get_error}')
            else:
                print(f'❌ Failed to create projectmilestone: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'ProjectMilestone' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['ProjectMilestone']
                refreshed_entity = self.projectmilestone_repo.get_project_milestone(
                    entity_for_refresh.project_id, entity_for_refresh.milestone_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = 'UI/UX Design Complete - Revised'

                    updated_projectmilestone = self.projectmilestone_repo.update_project_milestone(
                        refreshed_entity
                    )
                    print(f'✅ Updated title: {original_value} → {updated_projectmilestone.title}')

                    # Update stored entity with updated values
                    created_entities['ProjectMilestone'] = updated_projectmilestone
                else:
                    print('❌ Could not refresh projectmilestone for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  projectmilestone was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update projectmilestone: {e}')

        # 3. GET - Retrieve and print the entity
        if 'ProjectMilestone' in created_entities:
            print('\n🔍 Retrieving projectmilestone...')
            try:
                entity_for_get = created_entities['ProjectMilestone']
                retrieved_projectmilestone = self.projectmilestone_repo.get_project_milestone(
                    entity_for_get.project_id, entity_for_get.milestone_id
                )

                if retrieved_projectmilestone:
                    print(f'✅ Retrieved: {retrieved_projectmilestone}')
                else:
                    print('❌ Failed to retrieve projectmilestone')
            except Exception as e:
                print(f'❌ Failed to retrieve projectmilestone: {e}')

        print('🎯 ProjectMilestone CRUD cycle completed!')
        print('\n=== TaskTable Table Operations ===')

        # ProjectTask example
        print('\n--- ProjectTask ---')

        # 1. CREATE - Create sample projecttask
        sample_projecttask = ProjectTask(
            project_id='project-22222',
            task_id='task-44444',
            title='Implement user authentication',
            status='in_progress',
            priority='high',
            assignee_id='user-11111',
            due_date='2024-01-25T17:00:00Z',
            estimated_hours=Decimal('16.0'),
            created_at='2024-01-12T09:00:00Z',
        )

        print('📝 Creating projecttask...')
        print(f'📝 PK: {sample_projecttask.pk()}, SK: {sample_projecttask.sk()}')

        try:
            created_projecttask = self.projecttask_repo.create_project_task(sample_projecttask)
            print(f'✅ Created: {created_projecttask}')
            # Store created entity for access pattern testing
            created_entities['ProjectTask'] = created_projecttask
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  projecttask already exists, retrieving existing entity...')
                try:
                    existing_projecttask = self.projecttask_repo.get_project_task(
                        sample_projecttask.project_id,
                        sample_projecttask.status,
                        sample_projecttask.priority,
                        sample_projecttask.task_id,
                    )

                    if existing_projecttask:
                        print(f'✅ Retrieved existing: {existing_projecttask}')
                        # Store existing entity for access pattern testing
                        created_entities['ProjectTask'] = existing_projecttask
                    else:
                        print('❌ Failed to retrieve existing projecttask')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing projecttask: {get_error}')
            else:
                print(f'❌ Failed to create projecttask: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'ProjectTask' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['ProjectTask']
                refreshed_entity = self.projecttask_repo.get_project_task(
                    entity_for_refresh.project_id,
                    entity_for_refresh.status,
                    entity_for_refresh.priority,
                    entity_for_refresh.task_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = 'Implement secure user authentication system'

                    updated_projecttask = self.projecttask_repo.update_project_task(
                        refreshed_entity
                    )
                    print(f'✅ Updated title: {original_value} → {updated_projecttask.title}')

                    # Update stored entity with updated values
                    created_entities['ProjectTask'] = updated_projecttask
                else:
                    print('❌ Could not refresh projecttask for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  projecttask was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update projecttask: {e}')

        # 3. GET - Retrieve and print the entity
        if 'ProjectTask' in created_entities:
            print('\n🔍 Retrieving projecttask...')
            try:
                entity_for_get = created_entities['ProjectTask']
                retrieved_projecttask = self.projecttask_repo.get_project_task(
                    entity_for_get.project_id,
                    entity_for_get.status,
                    entity_for_get.priority,
                    entity_for_get.task_id,
                )

                if retrieved_projecttask:
                    print(f'✅ Retrieved: {retrieved_projecttask}')
                else:
                    print('❌ Failed to retrieve projecttask')
            except Exception as e:
                print(f'❌ Failed to retrieve projecttask: {e}')

        print('🎯 ProjectTask CRUD cycle completed!')

        # Task example
        print('\n--- Task ---')

        # 1. CREATE - Create sample task
        sample_task = Task(
            task_id='task-44444',
            project_id='project-22222',
            title='Implement user authentication',
            description='Create secure login and registration system with JWT tokens',
            status='in_progress',
            priority='high',
            assignee_id='user-11111',
            reporter_id='user-22222',
            estimated_hours=Decimal('16.0'),
            actual_hours=Decimal('3.14'),
            due_date='2024-01-25T17:00:00Z',
            labels=['authentication', 'security', 'backend'],
            dependencies=['task-33333'],
            created_at='2024-01-12T09:00:00Z',
            updated_at='2024-01-12T09:00:00Z',
            completed_at='None',
        )

        print('📝 Creating task...')
        print(f'📝 PK: {sample_task.pk()}, SK: {sample_task.sk()}')

        try:
            created_task = self.task_repo.create_task(sample_task)
            print(f'✅ Created: {created_task}')
            # Store created entity for access pattern testing
            created_entities['Task'] = created_task
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  task already exists, retrieving existing entity...')
                try:
                    existing_task = self.task_repo.get_task(sample_task.task_id)

                    if existing_task:
                        print(f'✅ Retrieved existing: {existing_task}')
                        # Store existing entity for access pattern testing
                        created_entities['Task'] = existing_task
                    else:
                        print('❌ Failed to retrieve existing task')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing task: {get_error}')
            else:
                print(f'❌ Failed to create task: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'Task' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Task']
                refreshed_entity = self.task_repo.get_task(entity_for_refresh.task_id)

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = 'Implement secure user authentication system'

                    updated_task = self.task_repo.update_task(refreshed_entity)
                    print(f'✅ Updated title: {original_value} → {updated_task.title}')

                    # Update stored entity with updated values
                    created_entities['Task'] = updated_task
                else:
                    print('❌ Could not refresh task for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  task was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update task: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Task' in created_entities:
            print('\n🔍 Retrieving task...')
            try:
                entity_for_get = created_entities['Task']
                retrieved_task = self.task_repo.get_task(entity_for_get.task_id)

                if retrieved_task:
                    print(f'✅ Retrieved: {retrieved_task}')
                else:
                    print('❌ Failed to retrieve task')
            except Exception as e:
                print(f'❌ Failed to retrieve task: {e}')

        print('🎯 Task CRUD cycle completed!')

        # TaskComment example
        print('\n--- TaskComment ---')

        # 1. CREATE - Create sample taskcomment
        sample_taskcomment = TaskComment(
            task_id='task-44444',
            comment_id='comment-55555',
            author_id='user-11111',
            content='Started working on the authentication flow. JWT implementation is in progress.',
            comment_type='update',
            created_at='2024-01-15T14:30:00Z',
            updated_at='None',
            mentions=['user-22222'],
            attachments=['auth-diagram.png'],
        )

        print('📝 Creating taskcomment...')
        print(f'📝 PK: {sample_taskcomment.pk()}, SK: {sample_taskcomment.sk()}')

        try:
            created_taskcomment = self.taskcomment_repo.create_task_comment(sample_taskcomment)
            print(f'✅ Created: {created_taskcomment}')
            # Store created entity for access pattern testing
            created_entities['TaskComment'] = created_taskcomment
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  taskcomment already exists, retrieving existing entity...')
                try:
                    existing_taskcomment = self.taskcomment_repo.get_task_comment(
                        sample_taskcomment.task_id,
                        sample_taskcomment.created_at,
                        sample_taskcomment.comment_id,
                    )

                    if existing_taskcomment:
                        print(f'✅ Retrieved existing: {existing_taskcomment}')
                        # Store existing entity for access pattern testing
                        created_entities['TaskComment'] = existing_taskcomment
                    else:
                        print('❌ Failed to retrieve existing taskcomment')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing taskcomment: {get_error}')
            else:
                print(f'❌ Failed to create taskcomment: {e}')
        # 2. UPDATE - Update non-key field (content)
        if 'TaskComment' in created_entities:
            print('\n🔄 Updating content field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TaskComment']
                refreshed_entity = self.taskcomment_repo.get_task_comment(
                    entity_for_refresh.task_id,
                    entity_for_refresh.created_at,
                    entity_for_refresh.comment_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.content
                    refreshed_entity.content = 'Completed the authentication flow. JWT implementation is done and tested. Ready for review.'

                    updated_taskcomment = self.taskcomment_repo.update_task_comment(
                        refreshed_entity
                    )
                    print(f'✅ Updated content: {original_value} → {updated_taskcomment.content}')

                    # Update stored entity with updated values
                    created_entities['TaskComment'] = updated_taskcomment
                else:
                    print('❌ Could not refresh taskcomment for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  taskcomment was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update taskcomment: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TaskComment' in created_entities:
            print('\n🔍 Retrieving taskcomment...')
            try:
                entity_for_get = created_entities['TaskComment']
                retrieved_taskcomment = self.taskcomment_repo.get_task_comment(
                    entity_for_get.task_id, entity_for_get.created_at, entity_for_get.comment_id
                )

                if retrieved_taskcomment:
                    print(f'✅ Retrieved: {retrieved_taskcomment}')
                else:
                    print('❌ Failed to retrieve taskcomment')
            except Exception as e:
                print(f'❌ Failed to retrieve taskcomment: {e}')

        print('🎯 TaskComment CRUD cycle completed!')

        # UserTask example
        print('\n--- UserTask ---')

        # 1. CREATE - Create sample usertask
        sample_usertask = UserTask(
            user_id='user-11111',
            task_id='task-44444',
            project_id='project-22222',
            title='Implement user authentication',
            status='in_progress',
            priority='high',
            due_date='2024-01-25T17:00:00Z',
            estimated_hours=Decimal('16.0'),
            assigned_at='2024-01-12T09:00:00Z',
        )

        print('📝 Creating usertask...')
        print(f'📝 PK: {sample_usertask.pk()}, SK: {sample_usertask.sk()}')

        try:
            created_usertask = self.usertask_repo.create_user_task(sample_usertask)
            print(f'✅ Created: {created_usertask}')
            # Store created entity for access pattern testing
            created_entities['UserTask'] = created_usertask
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  usertask already exists, retrieving existing entity...')
                try:
                    existing_usertask = self.usertask_repo.get_user_task(
                        sample_usertask.user_id,
                        sample_usertask.status,
                        sample_usertask.due_date,
                        sample_usertask.task_id,
                    )

                    if existing_usertask:
                        print(f'✅ Retrieved existing: {existing_usertask}')
                        # Store existing entity for access pattern testing
                        created_entities['UserTask'] = existing_usertask
                    else:
                        print('❌ Failed to retrieve existing usertask')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing usertask: {get_error}')
            else:
                print(f'❌ Failed to create usertask: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'UserTask' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['UserTask']
                refreshed_entity = self.usertask_repo.get_user_task(
                    entity_for_refresh.user_id,
                    entity_for_refresh.status,
                    entity_for_refresh.due_date,
                    entity_for_refresh.task_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = 'Implement secure user authentication system'

                    updated_usertask = self.usertask_repo.update_user_task(refreshed_entity)
                    print(f'✅ Updated title: {original_value} → {updated_usertask.title}')

                    # Update stored entity with updated values
                    created_entities['UserTask'] = updated_usertask
                else:
                    print('❌ Could not refresh usertask for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  usertask was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update usertask: {e}')

        # 3. GET - Retrieve and print the entity
        if 'UserTask' in created_entities:
            print('\n🔍 Retrieving usertask...')
            try:
                entity_for_get = created_entities['UserTask']
                retrieved_usertask = self.usertask_repo.get_user_task(
                    entity_for_get.user_id,
                    entity_for_get.status,
                    entity_for_get.due_date,
                    entity_for_get.task_id,
                )

                if retrieved_usertask:
                    print(f'✅ Retrieved: {retrieved_usertask}')
                else:
                    print('❌ Failed to retrieve usertask')
            except Exception as e:
                print(f'❌ Failed to retrieve usertask: {e}')

        print('🎯 UserTask CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

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
            try:
                deleted = self.organization_repo.delete_organization(
                    created_entities['Organization'].org_id
                )

                if deleted:
                    print('✅ Deleted organization successfully')
                else:
                    print('❌ Failed to delete organization (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete organization: {e}')

        # Delete OrganizationInvite
        if 'OrganizationInvite' in created_entities:
            print('\n🗑️  Deleting organizationinvite...')
            try:
                deleted = self.organizationinvite_repo.delete_organization_invite(
                    created_entities['OrganizationInvite'].org_id,
                    created_entities['OrganizationInvite'].invite_id,
                )

                if deleted:
                    print('✅ Deleted organizationinvite successfully')
                else:
                    print('❌ Failed to delete organizationinvite (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete organizationinvite: {e}')

        # Delete OrganizationMember
        if 'OrganizationMember' in created_entities:
            print('\n🗑️  Deleting organizationmember...')
            try:
                deleted = self.organizationmember_repo.delete_organization_member(
                    created_entities['OrganizationMember'].org_id,
                    created_entities['OrganizationMember'].user_id,
                )

                if deleted:
                    print('✅ Deleted organizationmember successfully')
                else:
                    print('❌ Failed to delete organizationmember (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete organizationmember: {e}')

        # Delete OrganizationProject
        if 'OrganizationProject' in created_entities:
            print('\n🗑️  Deleting organizationproject...')
            try:
                deleted = self.organizationproject_repo.delete_organization_project(
                    created_entities['OrganizationProject'].org_id,
                    created_entities['OrganizationProject'].created_at,
                    created_entities['OrganizationProject'].project_id,
                )

                if deleted:
                    print('✅ Deleted organizationproject successfully')
                else:
                    print('❌ Failed to delete organizationproject (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete organizationproject: {e}')

        # Delete Project
        if 'Project' in created_entities:
            print('\n🗑️  Deleting project...')
            try:
                deleted = self.project_repo.delete_project(created_entities['Project'].project_id)

                if deleted:
                    print('✅ Deleted project successfully')
                else:
                    print('❌ Failed to delete project (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete project: {e}')

        # Delete ProjectMilestone
        if 'ProjectMilestone' in created_entities:
            print('\n🗑️  Deleting projectmilestone...')
            try:
                deleted = self.projectmilestone_repo.delete_project_milestone(
                    created_entities['ProjectMilestone'].project_id,
                    created_entities['ProjectMilestone'].milestone_id,
                )

                if deleted:
                    print('✅ Deleted projectmilestone successfully')
                else:
                    print('❌ Failed to delete projectmilestone (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete projectmilestone: {e}')

        # Delete ProjectTask
        if 'ProjectTask' in created_entities:
            print('\n🗑️  Deleting projecttask...')
            try:
                deleted = self.projecttask_repo.delete_project_task(
                    created_entities['ProjectTask'].project_id,
                    created_entities['ProjectTask'].status,
                    created_entities['ProjectTask'].priority,
                    created_entities['ProjectTask'].task_id,
                )

                if deleted:
                    print('✅ Deleted projecttask successfully')
                else:
                    print('❌ Failed to delete projecttask (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete projecttask: {e}')

        # Delete Task
        if 'Task' in created_entities:
            print('\n🗑️  Deleting task...')
            try:
                deleted = self.task_repo.delete_task(created_entities['Task'].task_id)

                if deleted:
                    print('✅ Deleted task successfully')
                else:
                    print('❌ Failed to delete task (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete task: {e}')

        # Delete TaskComment
        if 'TaskComment' in created_entities:
            print('\n🗑️  Deleting taskcomment...')
            try:
                deleted = self.taskcomment_repo.delete_task_comment(
                    created_entities['TaskComment'].task_id,
                    created_entities['TaskComment'].created_at,
                    created_entities['TaskComment'].comment_id,
                )

                if deleted:
                    print('✅ Deleted taskcomment successfully')
                else:
                    print('❌ Failed to delete taskcomment (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete taskcomment: {e}')

        # Delete UserTask
        if 'UserTask' in created_entities:
            print('\n🗑️  Deleting usertask...')
            try:
                deleted = self.usertask_repo.delete_user_task(
                    created_entities['UserTask'].user_id,
                    created_entities['UserTask'].status,
                    created_entities['UserTask'].due_date,
                    created_entities['UserTask'].task_id,
                )

                if deleted:
                    print('✅ Deleted usertask successfully')
                else:
                    print('❌ Failed to delete usertask (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete usertask: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'OrganizationTable' must exist")
        print("   - DynamoDB table 'ProjectTable' must exist")
        print("   - DynamoDB table 'TaskTable' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # Organization
        # Access Pattern #1: Get organization details by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #1: Get organization details by ID')
            print('   Using Main Table')
            result = self.organization_repo.get_organization(
                created_entities['Organization'].org_id
            )
            print('   ✅ Get organization details by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #2: Create new organization
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #2: Create new organization')
            print('   Using Main Table')
            test_entity = Organization(
                org_id='sample_org_id',
                name='sample_name',
                domain='sample_domain',
                plan_type='sample_plan_type',
                max_users=0,
                max_projects=0,
                created_at='sample_created_at',
                updated_at='sample_updated_at',
                status='sample_status',
                billing_email='sample_billing_email',
                settings={},
            )
            result = self.organization_repo.put_organization(test_entity)
            print('   ✅ Create new organization completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Access Pattern #3: Update organization subscription plan
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #3: Update organization subscription plan')
            print('   Using Main Table')
            result = self.organization_repo.update_organization_plan(
                created_entities['Organization'].org_id,
                created_entities['Organization'].plan_type,
                created_entities['Organization'].max_users,
                created_entities['Organization'].max_projects,
            )
            print('   ✅ Update organization subscription plan completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # OrganizationInvite
        # Access Pattern #7: Get pending invites for organization
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #7: Get pending invites for organization')
            print('   Using Main Table')
            result = self.organizationinvite_repo.get_organization_invites(
                created_entities['OrganizationInvite'].org_id
            )
            print('   ✅ Get pending invites for organization completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #8: Create organization invite with member reference
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #8: Create organization invite with member reference')
            print('   Using Main Table')
            test_entity = OrganizationInvite(
                org_id='sample_org_id',
                invite_id='sample_invite_id',
                email='sample_email',
                role='sample_role',
                invited_by='sample_invited_by',
                created_at='sample_created_at',
                expires_at='sample_expires_at',
                status='sample_status',
                accepted_at='sample_accepted_at',
            )
            result = self.organizationinvite_repo.put_organization_invite(test_entity)
            print('   ✅ Create organization invite with member reference completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # OrganizationMember
        # Access Pattern #4: Get all members of an organization
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #4: Get all members of an organization')
            print('   Using Main Table')
            result = self.organizationmember_repo.get_organization_members(
                created_entities['OrganizationMember'].org_id
            )
            print('   ✅ Get all members of an organization completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: Add member to organization
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #5: Add member to organization')
            print('   Using Main Table')
            test_entity = OrganizationMember(
                org_id='sample_org_id',
                user_id='sample_user_id',
                email='sample_email',
                first_name='sample_first_name',
                last_name='sample_last_name',
                role='sample_role',
                permissions=['sample_permission'],
                joined_at='sample_joined_at',
                last_active='sample_last_active',
                status='sample_status',
            )
            result = self.organizationmember_repo.add_organization_member(test_entity)
            print('   ✅ Add member to organization completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # Access Pattern #6: Update member role and permissions
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #6: Update member role and permissions')
            print('   Using Main Table')
            result = self.organizationmember_repo.update_member_role(
                created_entities['OrganizationMember'].org_id,
                created_entities['OrganizationMember'].user_id,
                created_entities['OrganizationMember'].role,
                [],
            )
            print('   ✅ Update member role and permissions completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # OrganizationProject
        # Access Pattern #14: Get all projects for an organization (sorted by creation date)
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #14: Get all projects for an organization (sorted by creation date)'
            )
            print('   Using Main Table')
            result = self.organizationproject_repo.get_organization_projects(
                created_entities['OrganizationProject'].org_id
            )
            print('   ✅ Get all projects for an organization (sorted by creation date) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #14: {e}')

        # Access Pattern #15: Add project to organization index with cross-table references
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #15: Add project to organization index with cross-table references'
            )
            print('   Using Main Table')
            test_entity = OrganizationProject(
                org_id='sample_org_id',
                project_id='sample_project_id',
                project_name='sample_project_name',
                status='sample_status',
                priority='sample_priority',
                owner_id='sample_owner_id',
                team_size=0,
                created_at='sample_created_at',
                due_date='sample_due_date',
            )
            result = self.organizationproject_repo.add_project_to_organization(test_entity)
            print('   ✅ Add project to organization index with cross-table references completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #15: {e}')

        # Project
        # Access Pattern #9: Get project details by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Get project details by ID')
            print('   Using Main Table')
            result = self.project_repo.get_project(created_entities['Project'].project_id)
            print('   ✅ Get project details by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # Access Pattern #10: Create new project with organization reference
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #10: Create new project with organization reference')
            print('   Using Main Table')
            test_entity = Project(
                project_id='sample_project_id',
                org_id='sample_org_id',
                name='sample_name',
                description='sample_description',
                status='sample_status',
                priority='sample_priority',
                owner_id='sample_owner_id',
                team_members=['sample_team_member'],
                start_date='sample_start_date',
                due_date='sample_due_date',
                budget=Decimal('0.0'),
                currency='sample_currency',
                tags=['sample_tag'],
                created_at='sample_created_at',
                updated_at='sample_updated_at',
            )
            result = self.project_repo.put_project(test_entity)
            print('   ✅ Create new project with organization reference completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

        # Access Pattern #11: Update project status and progress
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #11: Update project status and progress')
            print('   Using Main Table')
            result = self.project_repo.update_project_status(
                created_entities['Project'].project_id,
                created_entities['Project'].status,
                created_entities['Project'].updated_at,
            )
            print('   ✅ Update project status and progress completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # ProjectMilestone
        # Access Pattern #12: Get all milestones for a project
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #12: Get all milestones for a project')
            print('   Using Main Table')
            result = self.projectmilestone_repo.get_project_milestones(
                created_entities['ProjectMilestone'].project_id
            )
            print('   ✅ Get all milestones for a project completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # Access Pattern #13: Create milestone for project
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #13: Create milestone for project')
            print('   Using Main Table')
            test_entity = ProjectMilestone(
                project_id='sample_project_id',
                milestone_id='sample_milestone_id',
                title='sample_title',
                description='sample_description',
                due_date='sample_due_date',
                status='sample_status',
                completion_percentage=0,
                created_at='sample_created_at',
                completed_at='sample_completed_at',
            )
            result = self.projectmilestone_repo.put_project_milestone(test_entity)
            print('   ✅ Create milestone for project completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #13: {e}')

        # ProjectTask
        # Access Pattern #19: Get all tasks for a project (sorted by status and priority)
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #19: Get all tasks for a project (sorted by status and priority)'
            )
            print('   Using Main Table')
            result = self.projecttask_repo.get_project_tasks(
                created_entities['ProjectTask'].project_id
            )
            print('   ✅ Get all tasks for a project (sorted by status and priority) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #19: {e}')

        # Access Pattern #20: Get tasks for a project filtered by status
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #20: Get tasks for a project filtered by status')
            print('   Using Main Table')
            result = self.projecttask_repo.get_project_tasks_by_status(
                created_entities['ProjectTask'].project_id, created_entities['ProjectTask'].status
            )
            print('   ✅ Get tasks for a project filtered by status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #20: {e}')

        # Access Pattern #21: Add task to project index
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #21: Add task to project index')
            print('   Using Main Table')
            test_entity = ProjectTask(
                project_id='sample_project_id',
                task_id='sample_task_id',
                title='sample_title',
                status='sample_status',
                priority='sample_priority',
                assignee_id='sample_assignee_id',
                due_date='sample_due_date',
                estimated_hours=Decimal('0.0'),
                created_at='sample_created_at',
            )
            result = self.projecttask_repo.add_task_to_project(test_entity)
            print('   ✅ Add task to project index completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #21: {e}')

        # Task
        # Access Pattern #16: Get task details by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #16: Get task details by ID')
            print('   Using Main Table')
            result = self.task_repo.get_task(created_entities['Task'].task_id)
            print('   ✅ Get task details by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #16: {e}')

        # Access Pattern #17: Create new task with project reference
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #17: Create new task with project reference')
            print('   Using Main Table')
            test_entity = Task(
                task_id='sample_task_id',
                project_id='sample_project_id',
                title='sample_title',
                description='sample_description',
                status='sample_status',
                priority='sample_priority',
                assignee_id='sample_assignee_id',
                reporter_id='sample_reporter_id',
                estimated_hours=Decimal('0.0'),
                actual_hours=Decimal('0.0'),
                due_date='sample_due_date',
                labels=['sample_label'],
                dependencies=['sample_dependency'],
                created_at='sample_created_at',
                updated_at='sample_updated_at',
                completed_at='sample_completed_at',
            )
            result = self.task_repo.put_task(test_entity)
            print('   ✅ Create new task with project reference completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #17: {e}')

        # Access Pattern #18: Update task status and completion
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #18: Update task status and completion')
            print('   Using Main Table')
            result = self.task_repo.update_task_status(
                created_entities['Task'].task_id,
                created_entities['Task'].status,
                created_entities['Task'].actual_hours,
                created_entities['Task'].completed_at,
            )
            print('   ✅ Update task status and completion completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #18: {e}')

        # TaskComment
        # Access Pattern #25: Get all comments for a task (sorted by creation time)
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #25: Get all comments for a task (sorted by creation time)'
            )
            print('   Using Main Table')
            result = self.taskcomment_repo.get_task_comments(
                created_entities['TaskComment'].task_id
            )
            print('   ✅ Get all comments for a task (sorted by creation time) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #25: {e}')

        # Access Pattern #26: Add comment to task with author reference
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #26: Add comment to task with author reference')
            print('   Using Main Table')
            test_entity = TaskComment(
                task_id='sample_task_id',
                comment_id='sample_comment_id',
                author_id='sample_author_id',
                content='sample_content',
                comment_type='sample_comment_type',
                created_at='sample_created_at',
                updated_at='sample_updated_at',
                mentions=['sample_mention'],
                attachments=['sample_attachment'],
            )
            result = self.taskcomment_repo.add_task_comment(test_entity)
            print('   ✅ Add comment to task with author reference completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #26: {e}')

        # UserTask
        # Access Pattern #22: Get all tasks assigned to a user (sorted by status and due date)
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #22: Get all tasks assigned to a user (sorted by status and due date)'
            )
            print('   Using Main Table')
            result = self.usertask_repo.get_user_tasks(created_entities['UserTask'].user_id)
            print(
                '   ✅ Get all tasks assigned to a user (sorted by status and due date) completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #22: {e}')

        # Access Pattern #23: Get active tasks for a user
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #23: Get active tasks for a user')
            print('   Using Main Table')
            result = self.usertask_repo.get_user_active_tasks(
                created_entities['UserTask'].user_id, created_entities['UserTask'].status
            )
            print('   ✅ Get active tasks for a user completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #23: {e}')

        # Access Pattern #24: Assign task to user with cross-table references
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #24: Assign task to user with cross-table references')
            print('   Using Main Table')
            test_entity = UserTask(
                user_id='sample_user_id',
                task_id='sample_task_id',
                project_id='sample_project_id',
                title='sample_title',
                status='sample_status',
                priority='sample_priority',
                due_date='sample_due_date',
                estimated_hours=Decimal('0.0'),
                assigned_at='sample_assigned_at',
            )
            result = self.usertask_repo.assign_task_to_user(test_entity)
            print('   ✅ Assign task to user with cross-table references completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #24: {e}')

        print('\n💡 Access Pattern Implementation Notes:')
        print('   - Main Table queries use partition key and sort key')
        print('   - GSI queries use different key structures and may have range conditions')
        print(
            '   - Range conditions (begins_with, between, >, <, >=, <=) require additional parameters'
        )
        print('   - Implement the access pattern methods in your repository classes')


def main():
    """Main function to run examples"""
    # 🚨 SAFETY CHECK: Prevent accidental execution against production DynamoDB
    endpoint_url = os.getenv('AWS_ENDPOINT_URL_DYNAMODB', '')

    # Check if running against DynamoDB Local
    is_local = 'localhost' in endpoint_url.lower() or '127.0.0.1' in endpoint_url

    if not is_local:
        print('=' * 80)
        print('🚨 SAFETY WARNING: NOT RUNNING AGAINST DYNAMODB LOCAL')
        print('=' * 80)
        print()
        print(f'Current endpoint: {endpoint_url or "AWS DynamoDB (production)"}')
        print()
        print('⚠️  This script performs CREATE, UPDATE, and DELETE operations that could')
        print('   affect your production data!')
        print()
        print('To run against production DynamoDB:')
        print('  1. Review the code carefully to understand what data will be modified')
        print("  2. Search for 'SAFETY CHECK' in this file")
        print("  3. Comment out the 'raise RuntimeError' line below the safety check")
        print('  4. Understand the risks before proceeding')
        print()
        print('To run safely against DynamoDB Local:')
        print('  export AWS_ENDPOINT_URL_DYNAMODB=http://localhost:8000')
        print()
        print('=' * 80)

        # 🛑 SAFETY CHECK: Comment out this line to run against production
        raise RuntimeError(
            'Safety check: Refusing to run against production DynamoDB. See warning above.'
        )

    # Parse command line arguments
    include_additional_access_patterns = '--all' in sys.argv

    # Check if we're running against DynamoDB Local
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
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
