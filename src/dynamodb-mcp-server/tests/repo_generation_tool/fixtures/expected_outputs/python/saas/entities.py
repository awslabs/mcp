# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig
from decimal import Decimal
from typing import Any


# Organization Entity Configuration
ORGANIZATION_CONFIG = EntityConfig(
    entity_type='ORGANIZATION',
    pk_builder=lambda entity: f'ORG#{entity.org_id}',
    pk_lookup_builder=lambda org_id: f'ORG#{org_id}',
    sk_builder=lambda entity: 'DETAILS',
    sk_lookup_builder=lambda: 'DETAILS',
    prefix_builder=lambda **kwargs: 'ORGANIZATION#',
)


class Organization(ConfigurableEntity):
    org_id: str
    name: str
    domain: str
    plan_type: str
    max_users: int
    max_projects: int
    created_at: str
    updated_at: str
    status: str
    billing_email: str
    settings: dict[str, Any] = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return ORGANIZATION_CONFIG


# OrganizationInvite Entity Configuration
ORGANIZATIONINVITE_CONFIG = EntityConfig(
    entity_type='INVITE',
    pk_builder=lambda entity: f'ORG#{entity.org_id}',
    pk_lookup_builder=lambda org_id: f'ORG#{org_id}',
    sk_builder=lambda entity: f'INVITE#{entity.invite_id}',
    sk_lookup_builder=lambda invite_id: f'INVITE#{invite_id}',
    prefix_builder=lambda **kwargs: 'INVITE#',
)


class OrganizationInvite(ConfigurableEntity):
    org_id: str
    invite_id: str
    email: str
    role: str
    invited_by: str
    created_at: str
    expires_at: str
    status: str
    accepted_at: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return ORGANIZATIONINVITE_CONFIG


# OrganizationMember Entity Configuration
ORGANIZATIONMEMBER_CONFIG = EntityConfig(
    entity_type='MEMBER',
    pk_builder=lambda entity: f'ORG#{entity.org_id}',
    pk_lookup_builder=lambda org_id: f'ORG#{org_id}',
    sk_builder=lambda entity: f'MEMBER#{entity.user_id}',
    sk_lookup_builder=lambda user_id: f'MEMBER#{user_id}',
    prefix_builder=lambda **kwargs: 'MEMBER#',
)


class OrganizationMember(ConfigurableEntity):
    org_id: str
    user_id: str
    email: str
    first_name: str
    last_name: str
    role: str
    permissions: list[str]
    joined_at: str
    last_active: str = None
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return ORGANIZATIONMEMBER_CONFIG


# OrganizationProject Entity Configuration
ORGANIZATIONPROJECT_CONFIG = EntityConfig(
    entity_type='ORG_PROJECT',
    pk_builder=lambda entity: f'ORG#{entity.org_id}',
    pk_lookup_builder=lambda org_id: f'ORG#{org_id}',
    sk_builder=lambda entity: f'PROJECT#{entity.created_at}#{entity.project_id}',
    sk_lookup_builder=lambda created_at, project_id: f'PROJECT#{created_at}#{project_id}',
    prefix_builder=lambda **kwargs: 'PROJECT#',
)


class OrganizationProject(ConfigurableEntity):
    org_id: str
    project_id: str
    project_name: str
    status: str
    priority: str
    owner_id: str
    team_size: int
    created_at: str
    due_date: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return ORGANIZATIONPROJECT_CONFIG


# Project Entity Configuration
PROJECT_CONFIG = EntityConfig(
    entity_type='PROJECT',
    pk_builder=lambda entity: f'PROJECT#{entity.project_id}',
    pk_lookup_builder=lambda project_id: f'PROJECT#{project_id}',
    sk_builder=lambda entity: 'DETAILS',
    sk_lookup_builder=lambda: 'DETAILS',
    prefix_builder=lambda **kwargs: 'PROJECT#',
)


class Project(ConfigurableEntity):
    project_id: str
    org_id: str
    name: str
    description: str = None
    status: str
    priority: str
    owner_id: str
    team_members: list[str]
    start_date: str = None
    due_date: str = None
    budget: Decimal = None
    currency: str = None
    tags: list[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PROJECT_CONFIG


# ProjectMilestone Entity Configuration
PROJECTMILESTONE_CONFIG = EntityConfig(
    entity_type='MILESTONE',
    pk_builder=lambda entity: f'PROJECT#{entity.project_id}',
    pk_lookup_builder=lambda project_id: f'PROJECT#{project_id}',
    sk_builder=lambda entity: f'MILESTONE#{entity.milestone_id}',
    sk_lookup_builder=lambda milestone_id: f'MILESTONE#{milestone_id}',
    prefix_builder=lambda **kwargs: 'MILESTONE#',
)


class ProjectMilestone(ConfigurableEntity):
    project_id: str
    milestone_id: str
    title: str
    description: str = None
    due_date: str
    status: str
    completion_percentage: int
    created_at: str
    completed_at: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PROJECTMILESTONE_CONFIG


# ProjectTask Entity Configuration
PROJECTTASK_CONFIG = EntityConfig(
    entity_type='PROJECT_TASK',
    pk_builder=lambda entity: f'PROJECT#{entity.project_id}',
    pk_lookup_builder=lambda project_id: f'PROJECT#{project_id}',
    sk_builder=lambda entity: f'TASK#{entity.status}#{entity.priority}#{entity.task_id}',
    sk_lookup_builder=lambda status, priority, task_id: f'TASK#{status}#{priority}#{task_id}',
    prefix_builder=lambda **kwargs: 'TASK#',
)


class ProjectTask(ConfigurableEntity):
    project_id: str
    task_id: str
    title: str
    status: str
    priority: str
    assignee_id: str = None
    due_date: str = None
    estimated_hours: Decimal = None
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PROJECTTASK_CONFIG


# Task Entity Configuration
TASK_CONFIG = EntityConfig(
    entity_type='TASK',
    pk_builder=lambda entity: f'TASK#{entity.task_id}',
    pk_lookup_builder=lambda task_id: f'TASK#{task_id}',
    sk_builder=lambda entity: 'DETAILS',
    sk_lookup_builder=lambda: 'DETAILS',
    prefix_builder=lambda **kwargs: 'TASK#',
)


class Task(ConfigurableEntity):
    task_id: str
    project_id: str
    title: str
    description: str = None
    status: str
    priority: str
    assignee_id: str = None
    reporter_id: str
    estimated_hours: Decimal = None
    actual_hours: Decimal = None
    due_date: str = None
    labels: list[str] = None
    dependencies: list[str] = None
    created_at: str
    updated_at: str
    completed_at: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TASK_CONFIG


# TaskComment Entity Configuration
TASKCOMMENT_CONFIG = EntityConfig(
    entity_type='COMMENT',
    pk_builder=lambda entity: f'TASK#{entity.task_id}',
    pk_lookup_builder=lambda task_id: f'TASK#{task_id}',
    sk_builder=lambda entity: f'COMMENT#{entity.created_at}#{entity.comment_id}',
    sk_lookup_builder=lambda created_at, comment_id: f'COMMENT#{created_at}#{comment_id}',
    prefix_builder=lambda **kwargs: 'COMMENT#',
)


class TaskComment(ConfigurableEntity):
    task_id: str
    comment_id: str
    author_id: str
    content: str
    comment_type: str
    created_at: str
    updated_at: str = None
    mentions: list[str] = None
    attachments: list[str] = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TASKCOMMENT_CONFIG


# UserTask Entity Configuration
USERTASK_CONFIG = EntityConfig(
    entity_type='USER_TASK',
    pk_builder=lambda entity: f'USER#{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'USER#{user_id}',
    sk_builder=lambda entity: f'TASK#{entity.status}#{entity.due_date}#{entity.task_id}',
    sk_lookup_builder=lambda status, due_date, task_id: f'TASK#{status}#{due_date}#{task_id}',
    prefix_builder=lambda **kwargs: 'TASK#',
)


class UserTask(ConfigurableEntity):
    user_id: str
    task_id: str
    project_id: str
    title: str
    status: str
    priority: str
    due_date: str = None
    estimated_hours: Decimal = None
    assigned_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USERTASK_CONFIG
