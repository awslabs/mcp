"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
import time

# Import generated entities and repositories
from entities import (
    TenantCertificate,
    TenantCourse,
    TenantEnrollment,
    TenantLesson,
    TenantOrganization,
    TenantProgress,
    TenantUser,
)
from repositories import (
    TenantCertificateRepository,
    TenantCourseRepository,
    TenantEnrollmentRepository,
    TenantLessonRepository,
    TenantOrganizationRepository,
    TenantProgressRepository,
    TenantUserRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # ELearningPlatform table repositories
        self.tenantcertificate_repo = TenantCertificateRepository('ELearningPlatform')
        self.tenantcourse_repo = TenantCourseRepository('ELearningPlatform')
        self.tenantenrollment_repo = TenantEnrollmentRepository('ELearningPlatform')
        self.tenantlesson_repo = TenantLessonRepository('ELearningPlatform')
        self.tenantorganization_repo = TenantOrganizationRepository('ELearningPlatform')
        self.tenantprogress_repo = TenantProgressRepository('ELearningPlatform')
        self.tenantuser_repo = TenantUserRepository('ELearningPlatform')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== ELearningPlatform Table Operations ===')

        # TenantCertificate example
        print('\n--- TenantCertificate ---')

        # 1. CREATE - Create sample tenantcertificate
        sample_tenantcertificate = TenantCertificate(
            tenant_id='tenant_id123',
            user_id='user_id123',
            course_id='course_id123',
            certificate_id='certificate_id123',
            course_title='sample_course_title',
            user_name='sample_user_name',
            instructor_name='sample_instructor_name',
            issued_date=42,
            completion_date=42,
            final_grade='sample_final_grade',
            certificate_url='sample_certificate_url',
            verification_code='sample_verification_code',
            expiry_date=42,
            status='active',
        )

        print('📝 Creating tenantcertificate...')
        print(f'📝 PK: {sample_tenantcertificate.pk()}, SK: {sample_tenantcertificate.sk()}')

        created_tenantcertificate = self.tenantcertificate_repo.create_tenant_certificate(
            sample_tenantcertificate
        )
        print(f'✅ Created: {created_tenantcertificate}')

        # Store created entity for access pattern testing
        created_entities['TenantCertificate'] = created_tenantcertificate
        # 2. UPDATE - Update non-key field (certificate_id)
        print('\n🔄 Updating certificate_id field...')
        original_value = created_tenantcertificate.certificate_id
        created_tenantcertificate.certificate_id = 'updated_certificate_id'

        updated_tenantcertificate = self.tenantcertificate_repo.update_tenant_certificate(
            created_tenantcertificate
        )
        print(
            f'✅ Updated certificate_id: {original_value} → {updated_tenantcertificate.certificate_id}'
        )

        # Update stored entity with updated values
        created_entities['TenantCertificate'] = updated_tenantcertificate

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tenantcertificate...')
        retrieved_tenantcertificate = self.tenantcertificate_repo.get_tenant_certificate(
            created_tenantcertificate.tenant_id,
            created_tenantcertificate.user_id,
            created_tenantcertificate.course_id,
            created_tenantcertificate.issued_date,
        )

        if retrieved_tenantcertificate:
            print(f'✅ Retrieved: {retrieved_tenantcertificate}')
        else:
            print('❌ Failed to retrieve tenantcertificate')

        print('🎯 TenantCertificate CRUD cycle completed successfully!')

        # TenantCourse example
        print('\n--- TenantCourse ---')

        # 1. CREATE - Create sample tenantcourse
        sample_tenantcourse = TenantCourse(
            tenant_id='tenant_id123',
            course_id='course_id123',
            title='sample_title',
            description='sample_description',
            instructor_id='instructor_id123',
            instructor_name='sample_instructor_name',
            category='electronics',
            difficulty_level='sample_difficulty_level',
            duration_hours=42,
            max_enrollments=42,
            prerequisites=['sample1', 'sample2'],
            tags=['sample1', 'sample2'],
            created_at=42,
            updated_at=42,
            status='active',
        )

        print('📝 Creating tenantcourse...')
        print(f'📝 PK: {sample_tenantcourse.pk()}, SK: {sample_tenantcourse.sk()}')

        created_tenantcourse = self.tenantcourse_repo.create_tenant_course(sample_tenantcourse)
        print(f'✅ Created: {created_tenantcourse}')

        # Store created entity for access pattern testing
        created_entities['TenantCourse'] = created_tenantcourse
        # 2. UPDATE - Update non-key field (title)
        print('\n🔄 Updating title field...')
        original_value = created_tenantcourse.title
        created_tenantcourse.title = 'updated_title'

        updated_tenantcourse = self.tenantcourse_repo.update_tenant_course(created_tenantcourse)
        print(f'✅ Updated title: {original_value} → {updated_tenantcourse.title}')

        # Update stored entity with updated values
        created_entities['TenantCourse'] = updated_tenantcourse

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tenantcourse...')
        retrieved_tenantcourse = self.tenantcourse_repo.get_tenant_course(
            created_tenantcourse.tenant_id, created_tenantcourse.course_id
        )

        if retrieved_tenantcourse:
            print(f'✅ Retrieved: {retrieved_tenantcourse}')
        else:
            print('❌ Failed to retrieve tenantcourse')

        print('🎯 TenantCourse CRUD cycle completed successfully!')

        # TenantEnrollment example
        print('\n--- TenantEnrollment ---')

        # 1. CREATE - Create sample tenantenrollment
        sample_tenantenrollment = TenantEnrollment(
            tenant_id='tenant_id123',
            user_id='user_id123',
            course_id='course_id123',
            course_title='sample_course_title',
            instructor_name='sample_instructor_name',
            enrollment_date=42,
            completion_date=42,
            progress_percentage=42,
            current_lesson='sample_current_lesson',
            grade='sample_grade',
            certificate_issued=True,
            status='active',
        )

        print('📝 Creating tenantenrollment...')
        print(f'📝 PK: {sample_tenantenrollment.pk()}, SK: {sample_tenantenrollment.sk()}')

        created_tenantenrollment = self.tenantenrollment_repo.create_tenant_enrollment(
            sample_tenantenrollment
        )
        print(f'✅ Created: {created_tenantenrollment}')

        # Store created entity for access pattern testing
        created_entities['TenantEnrollment'] = created_tenantenrollment
        # 2. UPDATE - Update non-key field (course_title)
        print('\n🔄 Updating course_title field...')
        original_value = created_tenantenrollment.course_title
        created_tenantenrollment.course_title = 'updated_course_title'

        updated_tenantenrollment = self.tenantenrollment_repo.update_tenant_enrollment(
            created_tenantenrollment
        )
        print(
            f'✅ Updated course_title: {original_value} → {updated_tenantenrollment.course_title}'
        )

        # Update stored entity with updated values
        created_entities['TenantEnrollment'] = updated_tenantenrollment

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tenantenrollment...')
        retrieved_tenantenrollment = self.tenantenrollment_repo.get_tenant_enrollment(
            created_tenantenrollment.tenant_id,
            created_tenantenrollment.user_id,
            created_tenantenrollment.course_id,
            created_tenantenrollment.enrollment_date,
        )

        if retrieved_tenantenrollment:
            print(f'✅ Retrieved: {retrieved_tenantenrollment}')
        else:
            print('❌ Failed to retrieve tenantenrollment')

        print('🎯 TenantEnrollment CRUD cycle completed successfully!')

        # TenantLesson example
        print('\n--- TenantLesson ---')

        # 1. CREATE - Create sample tenantlesson
        sample_tenantlesson = TenantLesson(
            tenant_id='tenant_id123',
            course_id='course_id123',
            lesson_id='lesson_id123',
            lesson_order=42,
            title='sample_title',
            description='sample_description',
            content_type='sample_content_type',
            content_url='sample_content_url',
            duration_minutes=42,
            is_mandatory=True,
            quiz_required=True,
            passing_score=42,
            created_at=42,
            updated_at=42,
        )

        print('📝 Creating tenantlesson...')
        print(f'📝 PK: {sample_tenantlesson.pk()}, SK: {sample_tenantlesson.sk()}')

        created_tenantlesson = self.tenantlesson_repo.create_tenant_lesson(sample_tenantlesson)
        print(f'✅ Created: {created_tenantlesson}')

        # Store created entity for access pattern testing
        created_entities['TenantLesson'] = created_tenantlesson
        # 2. UPDATE - Update non-key field (title)
        print('\n🔄 Updating title field...')
        original_value = created_tenantlesson.title
        created_tenantlesson.title = 'updated_title'

        updated_tenantlesson = self.tenantlesson_repo.update_tenant_lesson(created_tenantlesson)
        print(f'✅ Updated title: {original_value} → {updated_tenantlesson.title}')

        # Update stored entity with updated values
        created_entities['TenantLesson'] = updated_tenantlesson

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tenantlesson...')
        retrieved_tenantlesson = self.tenantlesson_repo.get_tenant_lesson(
            created_tenantlesson.tenant_id,
            created_tenantlesson.course_id,
            created_tenantlesson.lesson_order,
            created_tenantlesson.lesson_id,
        )

        if retrieved_tenantlesson:
            print(f'✅ Retrieved: {retrieved_tenantlesson}')
        else:
            print('❌ Failed to retrieve tenantlesson')

        print('🎯 TenantLesson CRUD cycle completed successfully!')

        # TenantOrganization example
        print('\n--- TenantOrganization ---')

        # 1. CREATE - Create sample tenantorganization
        sample_tenantorganization = TenantOrganization(
            tenant_id='tenant_id123',
            organization_name='sample_organization_name',
            domain='sample_domain',
            subscription_plan='sample_subscription_plan',
            max_users=42,
            max_courses=42,
            admin_email='sample_admin_email',
            created_at=42,
            status='active',
        )

        print('📝 Creating tenantorganization...')
        print(f'📝 PK: {sample_tenantorganization.pk()}, SK: {sample_tenantorganization.sk()}')

        created_tenantorganization = self.tenantorganization_repo.create_tenant_organization(
            sample_tenantorganization
        )
        print(f'✅ Created: {created_tenantorganization}')

        # Store created entity for access pattern testing
        created_entities['TenantOrganization'] = created_tenantorganization
        # 2. UPDATE - Update non-key field (organization_name)
        print('\n🔄 Updating organization_name field...')
        original_value = created_tenantorganization.organization_name
        created_tenantorganization.organization_name = 'updated_organization_name'

        updated_tenantorganization = self.tenantorganization_repo.update_tenant_organization(
            created_tenantorganization
        )
        print(
            f'✅ Updated organization_name: {original_value} → {updated_tenantorganization.organization_name}'
        )

        # Update stored entity with updated values
        created_entities['TenantOrganization'] = updated_tenantorganization

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tenantorganization...')
        retrieved_tenantorganization = self.tenantorganization_repo.get_tenant_organization(
            created_tenantorganization.tenant_id
        )

        if retrieved_tenantorganization:
            print(f'✅ Retrieved: {retrieved_tenantorganization}')
        else:
            print('❌ Failed to retrieve tenantorganization')

        print('🎯 TenantOrganization CRUD cycle completed successfully!')

        # TenantProgress example
        print('\n--- TenantProgress ---')

        # 1. CREATE - Create sample tenantprogress
        sample_tenantprogress = TenantProgress(
            tenant_id='tenant_id123',
            user_id='user_id123',
            course_id='course_id123',
            lesson_id='lesson_id123',
            attempt_date=42,
            completion_status='active',
            time_spent_minutes=int(time.time()),
            quiz_score=42,
            quiz_passed=True,
            notes='sample_notes',
            last_accessed=42,
        )

        print('📝 Creating tenantprogress...')
        print(f'📝 PK: {sample_tenantprogress.pk()}, SK: {sample_tenantprogress.sk()}')

        created_tenantprogress = self.tenantprogress_repo.create_tenant_progress(
            sample_tenantprogress
        )
        print(f'✅ Created: {created_tenantprogress}')

        # Store created entity for access pattern testing
        created_entities['TenantProgress'] = created_tenantprogress
        # 2. UPDATE - Update non-key field (completion_status)
        print('\n🔄 Updating completion_status field...')
        original_value = created_tenantprogress.completion_status
        created_tenantprogress.completion_status = 'updated_completion_status'

        updated_tenantprogress = self.tenantprogress_repo.update_tenant_progress(
            created_tenantprogress
        )
        print(
            f'✅ Updated completion_status: {original_value} → {updated_tenantprogress.completion_status}'
        )

        # Update stored entity with updated values
        created_entities['TenantProgress'] = updated_tenantprogress

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tenantprogress...')
        retrieved_tenantprogress = self.tenantprogress_repo.get_tenant_progress(
            created_tenantprogress.tenant_id,
            created_tenantprogress.user_id,
            created_tenantprogress.course_id,
            created_tenantprogress.lesson_id,
            created_tenantprogress.attempt_date,
        )

        if retrieved_tenantprogress:
            print(f'✅ Retrieved: {retrieved_tenantprogress}')
        else:
            print('❌ Failed to retrieve tenantprogress')

        print('🎯 TenantProgress CRUD cycle completed successfully!')

        # TenantUser example
        print('\n--- TenantUser ---')

        # 1. CREATE - Create sample tenantuser
        sample_tenantuser = TenantUser(
            tenant_id='tenant_id123',
            user_id='user_id123',
            email='sample_email',
            first_name='sample_first_name',
            last_name='sample_last_name',
            role='sample_role',
            department='sample_department',
            job_title='sample_job_title',
            enrollment_date=42,
            last_login=42,
            status='active',
        )

        print('📝 Creating tenantuser...')
        print(f'📝 PK: {sample_tenantuser.pk()}, SK: {sample_tenantuser.sk()}')

        created_tenantuser = self.tenantuser_repo.create_tenant_user(sample_tenantuser)
        print(f'✅ Created: {created_tenantuser}')

        # Store created entity for access pattern testing
        created_entities['TenantUser'] = created_tenantuser
        # 2. UPDATE - Update non-key field (email)
        print('\n🔄 Updating email field...')
        original_value = created_tenantuser.email
        created_tenantuser.email = 'updated_email'

        updated_tenantuser = self.tenantuser_repo.update_tenant_user(created_tenantuser)
        print(f'✅ Updated email: {original_value} → {updated_tenantuser.email}')

        # Update stored entity with updated values
        created_entities['TenantUser'] = updated_tenantuser

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tenantuser...')
        retrieved_tenantuser = self.tenantuser_repo.get_tenant_user(
            created_tenantuser.tenant_id, created_tenantuser.user_id
        )

        if retrieved_tenantuser:
            print(f'✅ Retrieved: {retrieved_tenantuser}')
        else:
            print('❌ Failed to retrieve tenantuser')

        print('🎯 TenantUser CRUD cycle completed successfully!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed successfully!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete TenantCertificate
        if 'TenantCertificate' in created_entities:
            print('\n🗑️  Deleting tenantcertificate...')
            deleted = self.tenantcertificate_repo.delete_tenant_certificate(
                created_entities['TenantCertificate'].tenant_id,
                created_entities['TenantCertificate'].user_id,
                created_entities['TenantCertificate'].course_id,
                created_entities['TenantCertificate'].issued_date,
            )

            if deleted:
                print('✅ Deleted tenantcertificate successfully')
            else:
                print('❌ Failed to delete tenantcertificate')

        # Delete TenantCourse
        if 'TenantCourse' in created_entities:
            print('\n🗑️  Deleting tenantcourse...')
            deleted = self.tenantcourse_repo.delete_tenant_course(
                created_entities['TenantCourse'].tenant_id,
                created_entities['TenantCourse'].course_id,
            )

            if deleted:
                print('✅ Deleted tenantcourse successfully')
            else:
                print('❌ Failed to delete tenantcourse')

        # Delete TenantEnrollment
        if 'TenantEnrollment' in created_entities:
            print('\n🗑️  Deleting tenantenrollment...')
            deleted = self.tenantenrollment_repo.delete_tenant_enrollment(
                created_entities['TenantEnrollment'].tenant_id,
                created_entities['TenantEnrollment'].user_id,
                created_entities['TenantEnrollment'].course_id,
                created_entities['TenantEnrollment'].enrollment_date,
            )

            if deleted:
                print('✅ Deleted tenantenrollment successfully')
            else:
                print('❌ Failed to delete tenantenrollment')

        # Delete TenantLesson
        if 'TenantLesson' in created_entities:
            print('\n🗑️  Deleting tenantlesson...')
            deleted = self.tenantlesson_repo.delete_tenant_lesson(
                created_entities['TenantLesson'].tenant_id,
                created_entities['TenantLesson'].course_id,
                created_entities['TenantLesson'].lesson_order,
                created_entities['TenantLesson'].lesson_id,
            )

            if deleted:
                print('✅ Deleted tenantlesson successfully')
            else:
                print('❌ Failed to delete tenantlesson')

        # Delete TenantOrganization
        if 'TenantOrganization' in created_entities:
            print('\n🗑️  Deleting tenantorganization...')
            deleted = self.tenantorganization_repo.delete_tenant_organization(
                created_entities['TenantOrganization'].tenant_id
            )

            if deleted:
                print('✅ Deleted tenantorganization successfully')
            else:
                print('❌ Failed to delete tenantorganization')

        # Delete TenantProgress
        if 'TenantProgress' in created_entities:
            print('\n🗑️  Deleting tenantprogress...')
            deleted = self.tenantprogress_repo.delete_tenant_progress(
                created_entities['TenantProgress'].tenant_id,
                created_entities['TenantProgress'].user_id,
                created_entities['TenantProgress'].course_id,
                created_entities['TenantProgress'].lesson_id,
                created_entities['TenantProgress'].attempt_date,
            )

            if deleted:
                print('✅ Deleted tenantprogress successfully')
            else:
                print('❌ Failed to delete tenantprogress')

        # Delete TenantUser
        if 'TenantUser' in created_entities:
            print('\n🗑️  Deleting tenantuser...')
            deleted = self.tenantuser_repo.delete_tenant_user(
                created_entities['TenantUser'].tenant_id, created_entities['TenantUser'].user_id
            )

            if deleted:
                print('✅ Deleted tenantuser successfully')
            else:
                print('❌ Failed to delete tenantuser')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'ELearningPlatform' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # TenantCertificate
        # Access Pattern #18: Get all certificates earned by user in tenant
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #18: Get all certificates earned by user in tenant")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantCertificate"].tenant_id
        #     user_id = created_entities["TenantCertificate"].user_id
        #     self.tenantcertificate_repo.get_user_certificates(
        #         tenant_id,
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #18: {e}")

        # Access Pattern #19: Issue certificate for course completion
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #19: Issue certificate for course completion")
        #     print("   Using Main Table")
        #     certificate = created_entities["TenantCertificate"]
        #     self.tenantcertificate_repo.issue_course_certificate(
        #         certificate,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #19: {e}")

        # Access Pattern #20: Verify certificate by verification code
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #20: Verify certificate by verification code")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantCertificate"].tenant_id
        #     user_id = created_entities["TenantCertificate"].user_id
        #     course_id = created_entities["TenantCertificate"].course_id
        #     issued_date = created_entities["TenantCertificate"].issued_date
        #     self.tenantcertificate_repo.verify_certificate(
        #         tenant_id,
        #         user_id,
        #         course_id,
        #         issued_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #20: {e}")

        # TenantCourse
        # Access Pattern #6: Get course details within tenant
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: Get course details within tenant")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantCourse"].tenant_id
        #     course_id = created_entities["TenantCourse"].course_id
        #     self.tenantcourse_repo.get_tenant_course(
        #         tenant_id,
        #         course_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        # Access Pattern #7: Create new course in tenant
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Create new course in tenant")
        #     print("   Using Main Table")
        #     course = created_entities["TenantCourse"]
        #     self.tenantcourse_repo.create_tenant_course(
        #         course,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Access Pattern #8: Update course information
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Update course information")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantCourse"].tenant_id
        #     course_id = created_entities["TenantCourse"].course_id
        #     updates = created_entities["TenantCourse"]
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_tenant_id"
        #     self.tenantcourse_repo.update_course_details(
        #         tenant_id,
        #         course_id,
        #         updates,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # TenantEnrollment
        # Access Pattern #9: Get all course enrollments for a user in tenant
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Get all course enrollments for a user in tenant")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantEnrollment"].tenant_id
        #     user_id = created_entities["TenantEnrollment"].user_id
        #     self.tenantenrollment_repo.get_user_enrollments(
        #         tenant_id,
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # Access Pattern #10: Enroll user in a course
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Enroll user in a course")
        #     print("   Using Main Table")
        #     enrollment = created_entities["TenantEnrollment"]
        #     self.tenantenrollment_repo.enroll_user_in_course(
        #         enrollment,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

        # Access Pattern #11: Update user's progress in course
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #11: Update user's progress in course")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantEnrollment"].tenant_id
        #     user_id = created_entities["TenantEnrollment"].user_id
        #     course_id = created_entities["TenantEnrollment"].course_id
        #     enrollment_date = created_entities["TenantEnrollment"].enrollment_date
        #     progress_percentage = created_entities["TenantEnrollment"].progress_percentage
        #     current_lesson = created_entities["TenantEnrollment"].current_lesson
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_tenant_id"
        #     self.tenantenrollment_repo.update_enrollment_progress(
        #         tenant_id,
        #         user_id,
        #         course_id,
        #         enrollment_date,
        #         progress_percentage,
        #         current_lesson,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #11: {e}")

        # TenantLesson
        # Access Pattern #12: Get all lessons for a course in tenant (ordered)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #12: Get all lessons for a course in tenant (ordered)")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantLesson"].tenant_id
        #     course_id = created_entities["TenantLesson"].course_id
        #     self.tenantlesson_repo.get_course_lessons(
        #         tenant_id,
        #         course_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #12: {e}")

        # Access Pattern #13: Get specific lesson details
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #13: Get specific lesson details")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantLesson"].tenant_id
        #     course_id = created_entities["TenantLesson"].course_id
        #     lesson_order = created_entities["TenantLesson"].lesson_order
        #     lesson_id = created_entities["TenantLesson"].lesson_id
        #     self.tenantlesson_repo.get_specific_lesson(
        #         tenant_id,
        #         course_id,
        #         lesson_order,
        #         lesson_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #13: {e}")

        # Access Pattern #14: Create new lesson in course
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #14: Create new lesson in course")
        #     print("   Using Main Table")
        #     lesson = created_entities["TenantLesson"]
        #     self.tenantlesson_repo.create_course_lesson(
        #         lesson,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #14: {e}")

        # TenantOrganization
        # Access Pattern #1: Get organization details for a tenant
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: Get organization details for a tenant")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantOrganization"].tenant_id
        #     self.tenantorganization_repo.get_tenant_organization(
        #         tenant_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #2: Create new tenant organization
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: Create new tenant organization")
        #     print("   Using Main Table")
        #     organization = created_entities["TenantOrganization"]
        #     self.tenantorganization_repo.create_tenant_organization(
        #         organization,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # TenantProgress
        # Access Pattern #15: Get user's progress for all lessons in a course
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #15: Get user's progress for all lessons in a course")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantProgress"].tenant_id
        #     user_id = created_entities["TenantProgress"].user_id
        #     course_id = created_entities["TenantProgress"].course_id
        #     self.tenantprogress_repo.get_user_course_progress(
        #         tenant_id,
        #         user_id,
        #         course_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #15: {e}")

        # Access Pattern #16: Record user's progress on a lesson
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #16: Record user's progress on a lesson")
        #     print("   Using Main Table")
        #     progress = created_entities["TenantProgress"]
        #     self.tenantprogress_repo.record_lesson_progress(
        #         progress,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #16: {e}")

        # Access Pattern #17: Update user's lesson progress
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #17: Update user's lesson progress")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantProgress"].tenant_id
        #     user_id = created_entities["TenantProgress"].user_id
        #     course_id = created_entities["TenantProgress"].course_id
        #     lesson_id = created_entities["TenantProgress"].lesson_id
        #     attempt_date = created_entities["TenantProgress"].attempt_date
        #     completion_status = created_entities["TenantProgress"].completion_status
        #     time_spent_minutes = created_entities["TenantProgress"].time_spent_minutes
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_tenant_id"
        #     self.tenantprogress_repo.update_lesson_progress(
        #         tenant_id,
        #         user_id,
        #         course_id,
        #         lesson_id,
        #         attempt_date,
        #         completion_status,
        #         time_spent_minutes,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #17: {e}")

        # TenantUser
        # Access Pattern #3: Get user profile within tenant
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Get user profile within tenant")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantUser"].tenant_id
        #     user_id = created_entities["TenantUser"].user_id
        #     self.tenantuser_repo.get_tenant_user(
        #         tenant_id,
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # Access Pattern #4: Create new user in tenant
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Create new user in tenant")
        #     print("   Using Main Table")
        #     user = created_entities["TenantUser"]
        #     self.tenantuser_repo.create_tenant_user(
        #         user,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #5: Update user profile information
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Update user profile information")
        #     print("   Using Main Table")
        #     tenant_id = created_entities["TenantUser"].tenant_id
        #     user_id = created_entities["TenantUser"].user_id
        #     updates = created_entities["TenantUser"]
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_tenant_id"
        #     self.tenantuser_repo.update_user_profile(
        #         tenant_id,
        #         user_id,
        #         updates,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

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
    print('   - ELearningPlatform')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
