# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig


# TenantCertificate Entity Configuration
TENANTCERTIFICATE_CONFIG = EntityConfig(
    entity_type='CERTIFICATE',
    pk_builder=lambda entity: f'TENANT#{entity.tenant_id}#USER#{entity.user_id}',
    pk_lookup_builder=lambda tenant_id, user_id: f'TENANT#{tenant_id}#USER#{user_id}',
    sk_builder=lambda entity: f'CERT#{entity.course_id}#{entity.issued_date}',
    sk_lookup_builder=lambda course_id, issued_date: f'CERT#{course_id}#{issued_date}',
    prefix_builder=lambda **kwargs: 'CERT#',
)


class TenantCertificate(ConfigurableEntity):
    tenant_id: str
    user_id: str
    course_id: str
    certificate_id: str
    course_title: str
    user_name: str
    instructor_name: str
    issued_date: int
    completion_date: int
    final_grade: str
    certificate_url: str = None
    verification_code: str
    expiry_date: int = None
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TENANTCERTIFICATE_CONFIG


# TenantCourse Entity Configuration
TENANTCOURSE_CONFIG = EntityConfig(
    entity_type='COURSE',
    pk_builder=lambda entity: f'TENANT#{entity.tenant_id}#COURSE#{entity.course_id}',
    pk_lookup_builder=lambda tenant_id, course_id: f'TENANT#{tenant_id}#COURSE#{course_id}',
    sk_builder=lambda entity: 'COURSE#DETAILS',
    sk_lookup_builder=lambda: 'COURSE#DETAILS',
    prefix_builder=lambda **kwargs: 'COURSE#',
)


class TenantCourse(ConfigurableEntity):
    tenant_id: str
    course_id: str
    title: str
    description: str
    instructor_id: str
    instructor_name: str
    category: str
    difficulty_level: str
    duration_hours: int
    max_enrollments: int = None
    prerequisites: list[str] = None
    tags: list[str] = None
    created_at: int
    updated_at: int
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TENANTCOURSE_CONFIG


# TenantEnrollment Entity Configuration
TENANTENROLLMENT_CONFIG = EntityConfig(
    entity_type='ENROLLMENT',
    pk_builder=lambda entity: f'TENANT#{entity.tenant_id}#USER#{entity.user_id}',
    pk_lookup_builder=lambda tenant_id, user_id: f'TENANT#{tenant_id}#USER#{user_id}',
    sk_builder=lambda entity: f'ENROLLMENT#{entity.course_id}#{entity.enrollment_date}',
    sk_lookup_builder=lambda course_id,
    enrollment_date: f'ENROLLMENT#{course_id}#{enrollment_date}',
    prefix_builder=lambda **kwargs: 'ENROLLMENT#',
)


class TenantEnrollment(ConfigurableEntity):
    tenant_id: str
    user_id: str
    course_id: str
    course_title: str
    instructor_name: str
    enrollment_date: int
    completion_date: int = None
    progress_percentage: int
    current_lesson: str = None
    grade: str = None
    certificate_issued: bool
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TENANTENROLLMENT_CONFIG


# TenantLesson Entity Configuration
TENANTLESSON_CONFIG = EntityConfig(
    entity_type='LESSON',
    pk_builder=lambda entity: f'TENANT#{entity.tenant_id}#COURSE#{entity.course_id}',
    pk_lookup_builder=lambda tenant_id, course_id: f'TENANT#{tenant_id}#COURSE#{course_id}',
    sk_builder=lambda entity: f'LESSON#{entity.lesson_order}#{entity.lesson_id}',
    sk_lookup_builder=lambda lesson_order, lesson_id: f'LESSON#{lesson_order}#{lesson_id}',
    prefix_builder=lambda **kwargs: 'LESSON#',
)


class TenantLesson(ConfigurableEntity):
    tenant_id: str
    course_id: str
    lesson_id: str
    lesson_order: int
    title: str
    description: str
    content_type: str
    content_url: str = None
    duration_minutes: int
    is_mandatory: bool
    quiz_required: bool
    passing_score: int = None
    created_at: int
    updated_at: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TENANTLESSON_CONFIG


# TenantOrganization Entity Configuration
TENANTORGANIZATION_CONFIG = EntityConfig(
    entity_type='ORG',
    pk_builder=lambda entity: f'TENANT#{entity.tenant_id}',
    pk_lookup_builder=lambda tenant_id: f'TENANT#{tenant_id}',
    sk_builder=lambda entity: 'ORG#PROFILE',
    sk_lookup_builder=lambda: 'ORG#PROFILE',
    prefix_builder=lambda **kwargs: 'ORG#',
)


class TenantOrganization(ConfigurableEntity):
    tenant_id: str
    organization_name: str
    domain: str
    subscription_plan: str
    max_users: int
    max_courses: int
    admin_email: str
    created_at: int
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TENANTORGANIZATION_CONFIG


# TenantProgress Entity Configuration
TENANTPROGRESS_CONFIG = EntityConfig(
    entity_type='PROGRESS',
    pk_builder=lambda entity: f'TENANT#{entity.tenant_id}#USER#{entity.user_id}#COURSE#{entity.course_id}',
    pk_lookup_builder=lambda tenant_id,
    user_id,
    course_id: f'TENANT#{tenant_id}#USER#{user_id}#COURSE#{course_id}',
    sk_builder=lambda entity: f'PROGRESS#{entity.lesson_id}#{entity.attempt_date}',
    sk_lookup_builder=lambda lesson_id, attempt_date: f'PROGRESS#{lesson_id}#{attempt_date}',
    prefix_builder=lambda **kwargs: 'PROGRESS#',
)


class TenantProgress(ConfigurableEntity):
    tenant_id: str
    user_id: str
    course_id: str
    lesson_id: str
    attempt_date: int
    completion_status: str
    time_spent_minutes: int
    quiz_score: int = None
    quiz_passed: bool = None
    notes: str = None
    last_accessed: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TENANTPROGRESS_CONFIG


# TenantUser Entity Configuration
TENANTUSER_CONFIG = EntityConfig(
    entity_type='USER',
    pk_builder=lambda entity: f'TENANT#{entity.tenant_id}#USER#{entity.user_id}',
    pk_lookup_builder=lambda tenant_id, user_id: f'TENANT#{tenant_id}#USER#{user_id}',
    sk_builder=lambda entity: 'USER#PROFILE',
    sk_lookup_builder=lambda: 'USER#PROFILE',
    prefix_builder=lambda **kwargs: 'USER#',
)


class TenantUser(ConfigurableEntity):
    tenant_id: str
    user_id: str
    email: str
    first_name: str
    last_name: str
    role: str
    department: str = None
    job_title: str = None
    enrollment_date: int
    last_login: int = None
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TENANTUSER_CONFIG
