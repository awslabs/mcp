"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys

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
        try:
            self.tenantcertificate_repo = TenantCertificateRepository('ELearningPlatform')
            print("✅ Initialized TenantCertificateRepository for table 'ELearningPlatform'")
        except Exception as e:
            print(f'❌ Failed to initialize TenantCertificateRepository: {e}')
            self.tenantcertificate_repo = None
        try:
            self.tenantcourse_repo = TenantCourseRepository('ELearningPlatform')
            print("✅ Initialized TenantCourseRepository for table 'ELearningPlatform'")
        except Exception as e:
            print(f'❌ Failed to initialize TenantCourseRepository: {e}')
            self.tenantcourse_repo = None
        try:
            self.tenantenrollment_repo = TenantEnrollmentRepository('ELearningPlatform')
            print("✅ Initialized TenantEnrollmentRepository for table 'ELearningPlatform'")
        except Exception as e:
            print(f'❌ Failed to initialize TenantEnrollmentRepository: {e}')
            self.tenantenrollment_repo = None
        try:
            self.tenantlesson_repo = TenantLessonRepository('ELearningPlatform')
            print("✅ Initialized TenantLessonRepository for table 'ELearningPlatform'")
        except Exception as e:
            print(f'❌ Failed to initialize TenantLessonRepository: {e}')
            self.tenantlesson_repo = None
        try:
            self.tenantorganization_repo = TenantOrganizationRepository('ELearningPlatform')
            print("✅ Initialized TenantOrganizationRepository for table 'ELearningPlatform'")
        except Exception as e:
            print(f'❌ Failed to initialize TenantOrganizationRepository: {e}')
            self.tenantorganization_repo = None
        try:
            self.tenantprogress_repo = TenantProgressRepository('ELearningPlatform')
            print("✅ Initialized TenantProgressRepository for table 'ELearningPlatform'")
        except Exception as e:
            print(f'❌ Failed to initialize TenantProgressRepository: {e}')
            self.tenantprogress_repo = None
        try:
            self.tenantuser_repo = TenantUserRepository('ELearningPlatform')
            print("✅ Initialized TenantUserRepository for table 'ELearningPlatform'")
        except Exception as e:
            print(f'❌ Failed to initialize TenantUserRepository: {e}')
            self.tenantuser_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete TenantCertificate (tenant_id, user_id, course_id, issued_date)
        try:
            sample_tenantcertificate = TenantCertificate(
                tenant_id='tenant-12345',
                user_id='user-67890',
                course_id='course-11111',
                certificate_id='cert-22222',
                course_title='JavaScript Fundamentals',
                user_name='John Doe',
                instructor_name='Jane Smith',
                issued_date=1705737600,
                completion_date=1705651200,
                final_grade='A',
                certificate_url='https://example.com/certificates/cert-22222.pdf',
                verification_code='VERIFY-12345',
                expiry_date=1737273600,
                status='active',
            )
            self.tenantcertificate_repo.delete_tenant_certificate(
                sample_tenantcertificate.tenant_id,
                sample_tenantcertificate.user_id,
                sample_tenantcertificate.course_id,
                sample_tenantcertificate.issued_date,
            )
            print('   🗑️  Deleted leftover tenantcertificate (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TenantCourse (tenant_id, course_id)
        try:
            sample_tenantcourse = TenantCourse(
                tenant_id='tenant-12345',
                course_id='course-11111',
                title='JavaScript Fundamentals',
                description='Learn the basics of JavaScript programming language',
                instructor_id='instructor-001',
                instructor_name='John Smith',
                category='Programming',
                difficulty_level='beginner',
                duration_hours=40,
                max_enrollments=100,
                prerequisites=['Basic Computer Skills'],
                tags=['javascript', 'programming', 'web-development'],
                created_at=1704067200,
                updated_at=1705737600,
                status='active',
            )
            self.tenantcourse_repo.delete_tenant_course(
                sample_tenantcourse.tenant_id, sample_tenantcourse.course_id
            )
            print('   🗑️  Deleted leftover tenantcourse (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TenantEnrollment (tenant_id, user_id, course_id, enrollment_date)
        try:
            sample_tenantenrollment = TenantEnrollment(
                tenant_id='tenant-12345',
                user_id='user-67890',
                course_id='course-11111',
                course_title='JavaScript Fundamentals',
                instructor_name='John Smith',
                enrollment_date=1705305600,
                completion_date=42,
                progress_percentage=75,
                current_lesson='lesson-33333',
                grade='None',
                certificate_issued=False,
                status='active',
            )
            self.tenantenrollment_repo.delete_tenant_enrollment(
                sample_tenantenrollment.tenant_id,
                sample_tenantenrollment.user_id,
                sample_tenantenrollment.course_id,
                sample_tenantenrollment.enrollment_date,
            )
            print('   🗑️  Deleted leftover tenantenrollment (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TenantLesson (tenant_id, course_id, lesson_order, lesson_id)
        try:
            sample_tenantlesson = TenantLesson(
                tenant_id='tenant-12345',
                course_id='course-11111',
                lesson_id='lesson-33333',
                lesson_order=1,
                title='Introduction to Variables',
                description='Learn about JavaScript variables and data types',
                content_type='video',
                content_url='https://example.com/videos/lesson-33333.mp4',
                duration_minutes=25,
                is_mandatory=True,
                quiz_required=True,
                passing_score=80,
                created_at=1704067200,
                updated_at=1705737600,
            )
            self.tenantlesson_repo.delete_tenant_lesson(
                sample_tenantlesson.tenant_id,
                sample_tenantlesson.course_id,
                sample_tenantlesson.lesson_order,
                sample_tenantlesson.lesson_id,
            )
            print('   🗑️  Deleted leftover tenantlesson (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TenantOrganization (tenant_id)
        try:
            sample_tenantorganization = TenantOrganization(
                tenant_id='tenant-12345',
                organization_name='TechCorp Learning',
                domain='techcorp.com',
                subscription_plan='enterprise',
                max_users=500,
                max_courses=100,
                admin_email='admin@techcorp.com',
                created_at=1704067200,
                status='active',
            )
            self.tenantorganization_repo.delete_tenant_organization(
                sample_tenantorganization.tenant_id
            )
            print('   🗑️  Deleted leftover tenantorganization (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TenantProgress (tenant_id, user_id, course_id, lesson_id, attempt_date)
        try:
            sample_tenantprogress = TenantProgress(
                tenant_id='tenant-12345',
                user_id='user-67890',
                course_id='course-11111',
                lesson_id='lesson-33333',
                attempt_date=1705737600,
                completion_status='completed',
                time_spent_minutes=30,
                quiz_score=92,
                quiz_passed=True,
                notes='Great progress on variables concept',
                last_accessed=1705824000,
            )
            self.tenantprogress_repo.delete_tenant_progress(
                sample_tenantprogress.tenant_id,
                sample_tenantprogress.user_id,
                sample_tenantprogress.course_id,
                sample_tenantprogress.lesson_id,
                sample_tenantprogress.attempt_date,
            )
            print('   🗑️  Deleted leftover tenantprogress (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TenantUser (tenant_id, user_id)
        try:
            sample_tenantuser = TenantUser(
                tenant_id='tenant-12345',
                user_id='user-67890',
                email='john.doe@techcorp.com',
                first_name='John',
                last_name='Doe',
                role='learner',
                department='Engineering',
                job_title='Software Developer',
                enrollment_date=1704931200,
                last_login=1705737600,
                status='active',
            )
            self.tenantuser_repo.delete_tenant_user(
                sample_tenantuser.tenant_id, sample_tenantuser.user_id
            )
            print('   🗑️  Deleted leftover tenantuser (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== ELearningPlatform Table Operations ===')

        # TenantCertificate example
        print('\n--- TenantCertificate ---')

        # 1. CREATE - Create sample tenantcertificate
        sample_tenantcertificate = TenantCertificate(
            tenant_id='tenant-12345',
            user_id='user-67890',
            course_id='course-11111',
            certificate_id='cert-22222',
            course_title='JavaScript Fundamentals',
            user_name='John Doe',
            instructor_name='Jane Smith',
            issued_date=1705737600,
            completion_date=1705651200,
            final_grade='A',
            certificate_url='https://example.com/certificates/cert-22222.pdf',
            verification_code='VERIFY-12345',
            expiry_date=1737273600,
            status='active',
        )

        print('📝 Creating tenantcertificate...')
        print(f'📝 PK: {sample_tenantcertificate.pk()}, SK: {sample_tenantcertificate.sk()}')

        try:
            created_tenantcertificate = self.tenantcertificate_repo.create_tenant_certificate(
                sample_tenantcertificate
            )
            print(f'✅ Created: {created_tenantcertificate}')
            # Store created entity for access pattern testing
            created_entities['TenantCertificate'] = created_tenantcertificate
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tenantcertificate already exists, retrieving existing entity...')
                try:
                    existing_tenantcertificate = (
                        self.tenantcertificate_repo.get_tenant_certificate(
                            sample_tenantcertificate.tenant_id,
                            sample_tenantcertificate.user_id,
                            sample_tenantcertificate.course_id,
                            sample_tenantcertificate.issued_date,
                        )
                    )

                    if existing_tenantcertificate:
                        print(f'✅ Retrieved existing: {existing_tenantcertificate}')
                        # Store existing entity for access pattern testing
                        created_entities['TenantCertificate'] = existing_tenantcertificate
                    else:
                        print('❌ Failed to retrieve existing tenantcertificate')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tenantcertificate: {get_error}')
            else:
                print(f'❌ Failed to create tenantcertificate: {e}')
        # 2. UPDATE - Update non-key field (course_title)
        if 'TenantCertificate' in created_entities:
            print('\n🔄 Updating course_title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TenantCertificate']
                refreshed_entity = self.tenantcertificate_repo.get_tenant_certificate(
                    entity_for_refresh.tenant_id,
                    entity_for_refresh.user_id,
                    entity_for_refresh.course_id,
                    entity_for_refresh.issued_date,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.course_title
                    refreshed_entity.course_title = 'Advanced JavaScript Fundamentals'

                    updated_tenantcertificate = (
                        self.tenantcertificate_repo.update_tenant_certificate(refreshed_entity)
                    )
                    print(
                        f'✅ Updated course_title: {original_value} → {updated_tenantcertificate.course_title}'
                    )

                    # Update stored entity with updated values
                    created_entities['TenantCertificate'] = updated_tenantcertificate
                else:
                    print('❌ Could not refresh tenantcertificate for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tenantcertificate was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tenantcertificate: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TenantCertificate' in created_entities:
            print('\n🔍 Retrieving tenantcertificate...')
            try:
                entity_for_get = created_entities['TenantCertificate']
                retrieved_tenantcertificate = self.tenantcertificate_repo.get_tenant_certificate(
                    entity_for_get.tenant_id,
                    entity_for_get.user_id,
                    entity_for_get.course_id,
                    entity_for_get.issued_date,
                )

                if retrieved_tenantcertificate:
                    print(f'✅ Retrieved: {retrieved_tenantcertificate}')
                else:
                    print('❌ Failed to retrieve tenantcertificate')
            except Exception as e:
                print(f'❌ Failed to retrieve tenantcertificate: {e}')

        print('🎯 TenantCertificate CRUD cycle completed!')

        # TenantCourse example
        print('\n--- TenantCourse ---')

        # 1. CREATE - Create sample tenantcourse
        sample_tenantcourse = TenantCourse(
            tenant_id='tenant-12345',
            course_id='course-11111',
            title='JavaScript Fundamentals',
            description='Learn the basics of JavaScript programming language',
            instructor_id='instructor-001',
            instructor_name='John Smith',
            category='Programming',
            difficulty_level='beginner',
            duration_hours=40,
            max_enrollments=100,
            prerequisites=['Basic Computer Skills'],
            tags=['javascript', 'programming', 'web-development'],
            created_at=1704067200,
            updated_at=1705737600,
            status='active',
        )

        print('📝 Creating tenantcourse...')
        print(f'📝 PK: {sample_tenantcourse.pk()}, SK: {sample_tenantcourse.sk()}')

        try:
            created_tenantcourse = self.tenantcourse_repo.create_tenant_course(sample_tenantcourse)
            print(f'✅ Created: {created_tenantcourse}')
            # Store created entity for access pattern testing
            created_entities['TenantCourse'] = created_tenantcourse
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tenantcourse already exists, retrieving existing entity...')
                try:
                    existing_tenantcourse = self.tenantcourse_repo.get_tenant_course(
                        sample_tenantcourse.tenant_id, sample_tenantcourse.course_id
                    )

                    if existing_tenantcourse:
                        print(f'✅ Retrieved existing: {existing_tenantcourse}')
                        # Store existing entity for access pattern testing
                        created_entities['TenantCourse'] = existing_tenantcourse
                    else:
                        print('❌ Failed to retrieve existing tenantcourse')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tenantcourse: {get_error}')
            else:
                print(f'❌ Failed to create tenantcourse: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'TenantCourse' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TenantCourse']
                refreshed_entity = self.tenantcourse_repo.get_tenant_course(
                    entity_for_refresh.tenant_id, entity_for_refresh.course_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = 'Advanced JavaScript Fundamentals'

                    updated_tenantcourse = self.tenantcourse_repo.update_tenant_course(
                        refreshed_entity
                    )
                    print(f'✅ Updated title: {original_value} → {updated_tenantcourse.title}')

                    # Update stored entity with updated values
                    created_entities['TenantCourse'] = updated_tenantcourse
                else:
                    print('❌ Could not refresh tenantcourse for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tenantcourse was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tenantcourse: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TenantCourse' in created_entities:
            print('\n🔍 Retrieving tenantcourse...')
            try:
                entity_for_get = created_entities['TenantCourse']
                retrieved_tenantcourse = self.tenantcourse_repo.get_tenant_course(
                    entity_for_get.tenant_id, entity_for_get.course_id
                )

                if retrieved_tenantcourse:
                    print(f'✅ Retrieved: {retrieved_tenantcourse}')
                else:
                    print('❌ Failed to retrieve tenantcourse')
            except Exception as e:
                print(f'❌ Failed to retrieve tenantcourse: {e}')

        print('🎯 TenantCourse CRUD cycle completed!')

        # TenantEnrollment example
        print('\n--- TenantEnrollment ---')

        # 1. CREATE - Create sample tenantenrollment
        sample_tenantenrollment = TenantEnrollment(
            tenant_id='tenant-12345',
            user_id='user-67890',
            course_id='course-11111',
            course_title='JavaScript Fundamentals',
            instructor_name='John Smith',
            enrollment_date=1705305600,
            completion_date=42,
            progress_percentage=75,
            current_lesson='lesson-33333',
            grade='None',
            certificate_issued=False,
            status='active',
        )

        print('📝 Creating tenantenrollment...')
        print(f'📝 PK: {sample_tenantenrollment.pk()}, SK: {sample_tenantenrollment.sk()}')

        try:
            created_tenantenrollment = self.tenantenrollment_repo.create_tenant_enrollment(
                sample_tenantenrollment
            )
            print(f'✅ Created: {created_tenantenrollment}')
            # Store created entity for access pattern testing
            created_entities['TenantEnrollment'] = created_tenantenrollment
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tenantenrollment already exists, retrieving existing entity...')
                try:
                    existing_tenantenrollment = self.tenantenrollment_repo.get_tenant_enrollment(
                        sample_tenantenrollment.tenant_id,
                        sample_tenantenrollment.user_id,
                        sample_tenantenrollment.course_id,
                        sample_tenantenrollment.enrollment_date,
                    )

                    if existing_tenantenrollment:
                        print(f'✅ Retrieved existing: {existing_tenantenrollment}')
                        # Store existing entity for access pattern testing
                        created_entities['TenantEnrollment'] = existing_tenantenrollment
                    else:
                        print('❌ Failed to retrieve existing tenantenrollment')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tenantenrollment: {get_error}')
            else:
                print(f'❌ Failed to create tenantenrollment: {e}')
        # 2. UPDATE - Update non-key field (completion_date)
        if 'TenantEnrollment' in created_entities:
            print('\n🔄 Updating completion_date field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TenantEnrollment']
                refreshed_entity = self.tenantenrollment_repo.get_tenant_enrollment(
                    entity_for_refresh.tenant_id,
                    entity_for_refresh.user_id,
                    entity_for_refresh.course_id,
                    entity_for_refresh.enrollment_date,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.completion_date
                    refreshed_entity.completion_date = 1705824000

                    updated_tenantenrollment = self.tenantenrollment_repo.update_tenant_enrollment(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated completion_date: {original_value} → {updated_tenantenrollment.completion_date}'
                    )

                    # Update stored entity with updated values
                    created_entities['TenantEnrollment'] = updated_tenantenrollment
                else:
                    print('❌ Could not refresh tenantenrollment for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tenantenrollment was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tenantenrollment: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TenantEnrollment' in created_entities:
            print('\n🔍 Retrieving tenantenrollment...')
            try:
                entity_for_get = created_entities['TenantEnrollment']
                retrieved_tenantenrollment = self.tenantenrollment_repo.get_tenant_enrollment(
                    entity_for_get.tenant_id,
                    entity_for_get.user_id,
                    entity_for_get.course_id,
                    entity_for_get.enrollment_date,
                )

                if retrieved_tenantenrollment:
                    print(f'✅ Retrieved: {retrieved_tenantenrollment}')
                else:
                    print('❌ Failed to retrieve tenantenrollment')
            except Exception as e:
                print(f'❌ Failed to retrieve tenantenrollment: {e}')

        print('🎯 TenantEnrollment CRUD cycle completed!')

        # TenantLesson example
        print('\n--- TenantLesson ---')

        # 1. CREATE - Create sample tenantlesson
        sample_tenantlesson = TenantLesson(
            tenant_id='tenant-12345',
            course_id='course-11111',
            lesson_id='lesson-33333',
            lesson_order=1,
            title='Introduction to Variables',
            description='Learn about JavaScript variables and data types',
            content_type='video',
            content_url='https://example.com/videos/lesson-33333.mp4',
            duration_minutes=25,
            is_mandatory=True,
            quiz_required=True,
            passing_score=80,
            created_at=1704067200,
            updated_at=1705737600,
        )

        print('📝 Creating tenantlesson...')
        print(f'📝 PK: {sample_tenantlesson.pk()}, SK: {sample_tenantlesson.sk()}')

        try:
            created_tenantlesson = self.tenantlesson_repo.create_tenant_lesson(sample_tenantlesson)
            print(f'✅ Created: {created_tenantlesson}')
            # Store created entity for access pattern testing
            created_entities['TenantLesson'] = created_tenantlesson
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tenantlesson already exists, retrieving existing entity...')
                try:
                    existing_tenantlesson = self.tenantlesson_repo.get_tenant_lesson(
                        sample_tenantlesson.tenant_id,
                        sample_tenantlesson.course_id,
                        sample_tenantlesson.lesson_order,
                        sample_tenantlesson.lesson_id,
                    )

                    if existing_tenantlesson:
                        print(f'✅ Retrieved existing: {existing_tenantlesson}')
                        # Store existing entity for access pattern testing
                        created_entities['TenantLesson'] = existing_tenantlesson
                    else:
                        print('❌ Failed to retrieve existing tenantlesson')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tenantlesson: {get_error}')
            else:
                print(f'❌ Failed to create tenantlesson: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'TenantLesson' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TenantLesson']
                refreshed_entity = self.tenantlesson_repo.get_tenant_lesson(
                    entity_for_refresh.tenant_id,
                    entity_for_refresh.course_id,
                    entity_for_refresh.lesson_order,
                    entity_for_refresh.lesson_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = 'Introduction to Variables and Data Types'

                    updated_tenantlesson = self.tenantlesson_repo.update_tenant_lesson(
                        refreshed_entity
                    )
                    print(f'✅ Updated title: {original_value} → {updated_tenantlesson.title}')

                    # Update stored entity with updated values
                    created_entities['TenantLesson'] = updated_tenantlesson
                else:
                    print('❌ Could not refresh tenantlesson for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tenantlesson was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tenantlesson: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TenantLesson' in created_entities:
            print('\n🔍 Retrieving tenantlesson...')
            try:
                entity_for_get = created_entities['TenantLesson']
                retrieved_tenantlesson = self.tenantlesson_repo.get_tenant_lesson(
                    entity_for_get.tenant_id,
                    entity_for_get.course_id,
                    entity_for_get.lesson_order,
                    entity_for_get.lesson_id,
                )

                if retrieved_tenantlesson:
                    print(f'✅ Retrieved: {retrieved_tenantlesson}')
                else:
                    print('❌ Failed to retrieve tenantlesson')
            except Exception as e:
                print(f'❌ Failed to retrieve tenantlesson: {e}')

        print('🎯 TenantLesson CRUD cycle completed!')

        # TenantOrganization example
        print('\n--- TenantOrganization ---')

        # 1. CREATE - Create sample tenantorganization
        sample_tenantorganization = TenantOrganization(
            tenant_id='tenant-12345',
            organization_name='TechCorp Learning',
            domain='techcorp.com',
            subscription_plan='enterprise',
            max_users=500,
            max_courses=100,
            admin_email='admin@techcorp.com',
            created_at=1704067200,
            status='active',
        )

        print('📝 Creating tenantorganization...')
        print(f'📝 PK: {sample_tenantorganization.pk()}, SK: {sample_tenantorganization.sk()}')

        try:
            created_tenantorganization = self.tenantorganization_repo.create_tenant_organization(
                sample_tenantorganization
            )
            print(f'✅ Created: {created_tenantorganization}')
            # Store created entity for access pattern testing
            created_entities['TenantOrganization'] = created_tenantorganization
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tenantorganization already exists, retrieving existing entity...')
                try:
                    existing_tenantorganization = (
                        self.tenantorganization_repo.get_tenant_organization(
                            sample_tenantorganization.tenant_id
                        )
                    )

                    if existing_tenantorganization:
                        print(f'✅ Retrieved existing: {existing_tenantorganization}')
                        # Store existing entity for access pattern testing
                        created_entities['TenantOrganization'] = existing_tenantorganization
                    else:
                        print('❌ Failed to retrieve existing tenantorganization')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tenantorganization: {get_error}')
            else:
                print(f'❌ Failed to create tenantorganization: {e}')
        # 2. UPDATE - Update non-key field (organization_name)
        if 'TenantOrganization' in created_entities:
            print('\n🔄 Updating organization_name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TenantOrganization']
                refreshed_entity = self.tenantorganization_repo.get_tenant_organization(
                    entity_for_refresh.tenant_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.organization_name
                    refreshed_entity.organization_name = 'TechCorp Learning Solutions'

                    updated_tenantorganization = (
                        self.tenantorganization_repo.update_tenant_organization(refreshed_entity)
                    )
                    print(
                        f'✅ Updated organization_name: {original_value} → {updated_tenantorganization.organization_name}'
                    )

                    # Update stored entity with updated values
                    created_entities['TenantOrganization'] = updated_tenantorganization
                else:
                    print('❌ Could not refresh tenantorganization for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tenantorganization was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tenantorganization: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TenantOrganization' in created_entities:
            print('\n🔍 Retrieving tenantorganization...')
            try:
                entity_for_get = created_entities['TenantOrganization']
                retrieved_tenantorganization = (
                    self.tenantorganization_repo.get_tenant_organization(entity_for_get.tenant_id)
                )

                if retrieved_tenantorganization:
                    print(f'✅ Retrieved: {retrieved_tenantorganization}')
                else:
                    print('❌ Failed to retrieve tenantorganization')
            except Exception as e:
                print(f'❌ Failed to retrieve tenantorganization: {e}')

        print('🎯 TenantOrganization CRUD cycle completed!')

        # TenantProgress example
        print('\n--- TenantProgress ---')

        # 1. CREATE - Create sample tenantprogress
        sample_tenantprogress = TenantProgress(
            tenant_id='tenant-12345',
            user_id='user-67890',
            course_id='course-11111',
            lesson_id='lesson-33333',
            attempt_date=1705737600,
            completion_status='completed',
            time_spent_minutes=30,
            quiz_score=92,
            quiz_passed=True,
            notes='Great progress on variables concept',
            last_accessed=1705824000,
        )

        print('📝 Creating tenantprogress...')
        print(f'📝 PK: {sample_tenantprogress.pk()}, SK: {sample_tenantprogress.sk()}')

        try:
            created_tenantprogress = self.tenantprogress_repo.create_tenant_progress(
                sample_tenantprogress
            )
            print(f'✅ Created: {created_tenantprogress}')
            # Store created entity for access pattern testing
            created_entities['TenantProgress'] = created_tenantprogress
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tenantprogress already exists, retrieving existing entity...')
                try:
                    existing_tenantprogress = self.tenantprogress_repo.get_tenant_progress(
                        sample_tenantprogress.tenant_id,
                        sample_tenantprogress.user_id,
                        sample_tenantprogress.course_id,
                        sample_tenantprogress.lesson_id,
                        sample_tenantprogress.attempt_date,
                    )

                    if existing_tenantprogress:
                        print(f'✅ Retrieved existing: {existing_tenantprogress}')
                        # Store existing entity for access pattern testing
                        created_entities['TenantProgress'] = existing_tenantprogress
                    else:
                        print('❌ Failed to retrieve existing tenantprogress')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tenantprogress: {get_error}')
            else:
                print(f'❌ Failed to create tenantprogress: {e}')
        # 2. UPDATE - Update non-key field (completion_status)
        if 'TenantProgress' in created_entities:
            print('\n🔄 Updating completion_status field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TenantProgress']
                refreshed_entity = self.tenantprogress_repo.get_tenant_progress(
                    entity_for_refresh.tenant_id,
                    entity_for_refresh.user_id,
                    entity_for_refresh.course_id,
                    entity_for_refresh.lesson_id,
                    entity_for_refresh.attempt_date,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.completion_status
                    refreshed_entity.completion_status = 'mastered'

                    updated_tenantprogress = self.tenantprogress_repo.update_tenant_progress(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated completion_status: {original_value} → {updated_tenantprogress.completion_status}'
                    )

                    # Update stored entity with updated values
                    created_entities['TenantProgress'] = updated_tenantprogress
                else:
                    print('❌ Could not refresh tenantprogress for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tenantprogress was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tenantprogress: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TenantProgress' in created_entities:
            print('\n🔍 Retrieving tenantprogress...')
            try:
                entity_for_get = created_entities['TenantProgress']
                retrieved_tenantprogress = self.tenantprogress_repo.get_tenant_progress(
                    entity_for_get.tenant_id,
                    entity_for_get.user_id,
                    entity_for_get.course_id,
                    entity_for_get.lesson_id,
                    entity_for_get.attempt_date,
                )

                if retrieved_tenantprogress:
                    print(f'✅ Retrieved: {retrieved_tenantprogress}')
                else:
                    print('❌ Failed to retrieve tenantprogress')
            except Exception as e:
                print(f'❌ Failed to retrieve tenantprogress: {e}')

        print('🎯 TenantProgress CRUD cycle completed!')

        # TenantUser example
        print('\n--- TenantUser ---')

        # 1. CREATE - Create sample tenantuser
        sample_tenantuser = TenantUser(
            tenant_id='tenant-12345',
            user_id='user-67890',
            email='john.doe@techcorp.com',
            first_name='John',
            last_name='Doe',
            role='learner',
            department='Engineering',
            job_title='Software Developer',
            enrollment_date=1704931200,
            last_login=1705737600,
            status='active',
        )

        print('📝 Creating tenantuser...')
        print(f'📝 PK: {sample_tenantuser.pk()}, SK: {sample_tenantuser.sk()}')

        try:
            created_tenantuser = self.tenantuser_repo.create_tenant_user(sample_tenantuser)
            print(f'✅ Created: {created_tenantuser}')
            # Store created entity for access pattern testing
            created_entities['TenantUser'] = created_tenantuser
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tenantuser already exists, retrieving existing entity...')
                try:
                    existing_tenantuser = self.tenantuser_repo.get_tenant_user(
                        sample_tenantuser.tenant_id, sample_tenantuser.user_id
                    )

                    if existing_tenantuser:
                        print(f'✅ Retrieved existing: {existing_tenantuser}')
                        # Store existing entity for access pattern testing
                        created_entities['TenantUser'] = existing_tenantuser
                    else:
                        print('❌ Failed to retrieve existing tenantuser')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tenantuser: {get_error}')
            else:
                print(f'❌ Failed to create tenantuser: {e}')
        # 2. UPDATE - Update non-key field (role)
        if 'TenantUser' in created_entities:
            print('\n🔄 Updating role field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TenantUser']
                refreshed_entity = self.tenantuser_repo.get_tenant_user(
                    entity_for_refresh.tenant_id, entity_for_refresh.user_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.role
                    refreshed_entity.role = 'instructor'

                    updated_tenantuser = self.tenantuser_repo.update_tenant_user(refreshed_entity)
                    print(f'✅ Updated role: {original_value} → {updated_tenantuser.role}')

                    # Update stored entity with updated values
                    created_entities['TenantUser'] = updated_tenantuser
                else:
                    print('❌ Could not refresh tenantuser for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tenantuser was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tenantuser: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TenantUser' in created_entities:
            print('\n🔍 Retrieving tenantuser...')
            try:
                entity_for_get = created_entities['TenantUser']
                retrieved_tenantuser = self.tenantuser_repo.get_tenant_user(
                    entity_for_get.tenant_id, entity_for_get.user_id
                )

                if retrieved_tenantuser:
                    print(f'✅ Retrieved: {retrieved_tenantuser}')
                else:
                    print('❌ Failed to retrieve tenantuser')
            except Exception as e:
                print(f'❌ Failed to retrieve tenantuser: {e}')

        print('🎯 TenantUser CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

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
            try:
                deleted = self.tenantcertificate_repo.delete_tenant_certificate(
                    created_entities['TenantCertificate'].tenant_id,
                    created_entities['TenantCertificate'].user_id,
                    created_entities['TenantCertificate'].course_id,
                    created_entities['TenantCertificate'].issued_date,
                )

                if deleted:
                    print('✅ Deleted tenantcertificate successfully')
                else:
                    print('❌ Failed to delete tenantcertificate (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tenantcertificate: {e}')

        # Delete TenantCourse
        if 'TenantCourse' in created_entities:
            print('\n🗑️  Deleting tenantcourse...')
            try:
                deleted = self.tenantcourse_repo.delete_tenant_course(
                    created_entities['TenantCourse'].tenant_id,
                    created_entities['TenantCourse'].course_id,
                )

                if deleted:
                    print('✅ Deleted tenantcourse successfully')
                else:
                    print('❌ Failed to delete tenantcourse (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tenantcourse: {e}')

        # Delete TenantEnrollment
        if 'TenantEnrollment' in created_entities:
            print('\n🗑️  Deleting tenantenrollment...')
            try:
                deleted = self.tenantenrollment_repo.delete_tenant_enrollment(
                    created_entities['TenantEnrollment'].tenant_id,
                    created_entities['TenantEnrollment'].user_id,
                    created_entities['TenantEnrollment'].course_id,
                    created_entities['TenantEnrollment'].enrollment_date,
                )

                if deleted:
                    print('✅ Deleted tenantenrollment successfully')
                else:
                    print('❌ Failed to delete tenantenrollment (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tenantenrollment: {e}')

        # Delete TenantLesson
        if 'TenantLesson' in created_entities:
            print('\n🗑️  Deleting tenantlesson...')
            try:
                deleted = self.tenantlesson_repo.delete_tenant_lesson(
                    created_entities['TenantLesson'].tenant_id,
                    created_entities['TenantLesson'].course_id,
                    created_entities['TenantLesson'].lesson_order,
                    created_entities['TenantLesson'].lesson_id,
                )

                if deleted:
                    print('✅ Deleted tenantlesson successfully')
                else:
                    print('❌ Failed to delete tenantlesson (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tenantlesson: {e}')

        # Delete TenantOrganization
        if 'TenantOrganization' in created_entities:
            print('\n🗑️  Deleting tenantorganization...')
            try:
                deleted = self.tenantorganization_repo.delete_tenant_organization(
                    created_entities['TenantOrganization'].tenant_id
                )

                if deleted:
                    print('✅ Deleted tenantorganization successfully')
                else:
                    print('❌ Failed to delete tenantorganization (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tenantorganization: {e}')

        # Delete TenantProgress
        if 'TenantProgress' in created_entities:
            print('\n🗑️  Deleting tenantprogress...')
            try:
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
                    print('❌ Failed to delete tenantprogress (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tenantprogress: {e}')

        # Delete TenantUser
        if 'TenantUser' in created_entities:
            print('\n🗑️  Deleting tenantuser...')
            try:
                deleted = self.tenantuser_repo.delete_tenant_user(
                    created_entities['TenantUser'].tenant_id,
                    created_entities['TenantUser'].user_id,
                )

                if deleted:
                    print('✅ Deleted tenantuser successfully')
                else:
                    print('❌ Failed to delete tenantuser (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tenantuser: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'ELearningPlatform' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # TenantCertificate
        # Access Pattern #18: Get all certificates earned by user in tenant
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #18: Get all certificates earned by user in tenant')
            print('   Using Main Table')
            result = self.tenantcertificate_repo.get_user_certificates(
                created_entities['TenantCertificate'].tenant_id,
                created_entities['TenantCertificate'].user_id,
            )
            print('   ✅ Get all certificates earned by user in tenant completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #18: {e}')

        # Access Pattern #19: Issue certificate for course completion
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #19: Issue certificate for course completion')
            print('   Using Main Table')
            test_entity = TenantCertificate(
                tenant_id='sample_tenant_id',
                user_id='sample_user_id',
                course_id='sample_course_id',
                certificate_id='sample_certificate_id',
                course_title='sample_course_title',
                user_name='sample_user_name',
                instructor_name='sample_instructor_name',
                issued_date=0,
                completion_date=0,
                final_grade='sample_final_grade',
                certificate_url='sample_certificate_url',
                verification_code='sample_verification_code',
                expiry_date=0,
                status='sample_status',
            )
            result = self.tenantcertificate_repo.issue_course_certificate(test_entity)
            print('   ✅ Issue certificate for course completion completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #19: {e}')

        # Access Pattern #20: Verify certificate by verification code
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #20: Verify certificate by verification code')
            print('   Using Main Table')
            result = self.tenantcertificate_repo.verify_certificate(
                created_entities['TenantCertificate'].tenant_id,
                created_entities['TenantCertificate'].user_id,
                created_entities['TenantCertificate'].course_id,
                created_entities['TenantCertificate'].issued_date,
            )
            print('   ✅ Verify certificate by verification code completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #20: {e}')

        # TenantCourse
        # Access Pattern #6: Get course details within tenant
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #6: Get course details within tenant')
            print('   Using Main Table')
            result = self.tenantcourse_repo.get_tenant_course(
                created_entities['TenantCourse'].tenant_id,
                created_entities['TenantCourse'].course_id,
            )
            print('   ✅ Get course details within tenant completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # Access Pattern #7: Create new course in tenant
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #7: Create new course in tenant')
            print('   Using Main Table')
            test_entity = TenantCourse(
                tenant_id='sample_tenant_id',
                course_id='sample_course_id',
                title='sample_title',
                description='sample_description',
                instructor_id='sample_instructor_id',
                instructor_name='sample_instructor_name',
                category='sample_category',
                difficulty_level='sample_difficulty_level',
                duration_hours=0,
                max_enrollments=0,
                prerequisites=['sample_prerequisite'],
                tags=['sample_tag'],
                created_at=0,
                updated_at=0,
                status='sample_status',
            )
            result = self.tenantcourse_repo.put_tenant_course(test_entity)
            print('   ✅ Create new course in tenant completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #8: Update course information
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #8: Update course information')
            print('   Using Main Table')
            result = self.tenantcourse_repo.update_course_details(
                created_entities['TenantCourse'].tenant_id,
                created_entities['TenantCourse'].course_id,
                created_entities['TenantCourse'],
            )
            print('   ✅ Update course information completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # TenantEnrollment
        # Access Pattern #9: Get all course enrollments for a user in tenant
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Get all course enrollments for a user in tenant')
            print('   Using Main Table')
            result = self.tenantenrollment_repo.get_user_enrollments(
                created_entities['TenantEnrollment'].tenant_id,
                created_entities['TenantEnrollment'].user_id,
            )
            print('   ✅ Get all course enrollments for a user in tenant completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # Access Pattern #10: Enroll user in a course
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #10: Enroll user in a course')
            print('   Using Main Table')
            test_entity = TenantEnrollment(
                tenant_id='sample_tenant_id',
                user_id='sample_user_id',
                course_id='sample_course_id',
                course_title='sample_course_title',
                instructor_name='sample_instructor_name',
                enrollment_date=0,
                completion_date=42,
                progress_percentage=0,
                current_lesson='sample_current_lesson',
                grade='sample_grade',
                certificate_issued=False,
                status='sample_status',
            )
            result = self.tenantenrollment_repo.enroll_user_in_course(test_entity)
            print('   ✅ Enroll user in a course completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

        # Access Pattern #11: Update user's progress in course
        # Index: Main Table
        try:
            print("🔍 Testing Access Pattern #11: Update user's progress in course")
            print('   Using Main Table')
            result = self.tenantenrollment_repo.update_enrollment_progress(
                created_entities['TenantEnrollment'].tenant_id,
                created_entities['TenantEnrollment'].user_id,
                created_entities['TenantEnrollment'].course_id,
                created_entities['TenantEnrollment'].enrollment_date,
                created_entities['TenantEnrollment'].progress_percentage,
                created_entities['TenantEnrollment'].current_lesson,
            )
            print("   ✅ Update user's progress in course completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # TenantLesson
        # Access Pattern #12: Get all lessons for a course in tenant (ordered)
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #12: Get all lessons for a course in tenant (ordered)'
            )
            print('   Using Main Table')
            result = self.tenantlesson_repo.get_course_lessons(
                created_entities['TenantLesson'].tenant_id,
                created_entities['TenantLesson'].course_id,
            )
            print('   ✅ Get all lessons for a course in tenant (ordered) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # Access Pattern #13: Get specific lesson details
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #13: Get specific lesson details')
            print('   Using Main Table')
            result = self.tenantlesson_repo.get_specific_lesson(
                created_entities['TenantLesson'].tenant_id,
                created_entities['TenantLesson'].course_id,
                created_entities['TenantLesson'].lesson_order,
                created_entities['TenantLesson'].lesson_id,
            )
            print('   ✅ Get specific lesson details completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #13: {e}')

        # Access Pattern #14: Create new lesson in course
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #14: Create new lesson in course')
            print('   Using Main Table')
            test_entity = TenantLesson(
                tenant_id='sample_tenant_id',
                course_id='sample_course_id',
                lesson_id='sample_lesson_id',
                lesson_order=0,
                title='sample_title',
                description='sample_description',
                content_type='sample_content_type',
                content_url='sample_content_url',
                duration_minutes=0,
                is_mandatory=False,
                quiz_required=False,
                passing_score=0,
                created_at=0,
                updated_at=0,
            )
            result = self.tenantlesson_repo.create_course_lesson(test_entity)
            print('   ✅ Create new lesson in course completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #14: {e}')

        # TenantOrganization
        # Access Pattern #1: Get organization details for a tenant
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #1: Get organization details for a tenant')
            print('   Using Main Table')
            result = self.tenantorganization_repo.get_tenant_organization(
                created_entities['TenantOrganization'].tenant_id
            )
            print('   ✅ Get organization details for a tenant completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #2: Create new tenant organization
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #2: Create new tenant organization')
            print('   Using Main Table')
            test_entity = TenantOrganization(
                tenant_id='sample_tenant_id',
                organization_name='sample_organization_name',
                domain='sample_domain',
                subscription_plan='sample_subscription_plan',
                max_users=0,
                max_courses=0,
                admin_email='sample_admin_email',
                created_at=0,
                status='sample_status',
            )
            result = self.tenantorganization_repo.put_tenant_organization(test_entity)
            print('   ✅ Create new tenant organization completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # TenantProgress
        # Access Pattern #15: Get user's progress for all lessons in a course
        # Index: Main Table
        try:
            print("🔍 Testing Access Pattern #15: Get user's progress for all lessons in a course")
            print('   Using Main Table')
            result = self.tenantprogress_repo.get_user_course_progress(
                created_entities['TenantProgress'].tenant_id,
                created_entities['TenantProgress'].user_id,
                created_entities['TenantProgress'].course_id,
            )
            print("   ✅ Get user's progress for all lessons in a course completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #15: {e}')

        # Access Pattern #16: Record user's progress on a lesson
        # Index: Main Table
        try:
            print("🔍 Testing Access Pattern #16: Record user's progress on a lesson")
            print('   Using Main Table')
            test_entity = TenantProgress(
                tenant_id='sample_tenant_id',
                user_id='sample_user_id',
                course_id='sample_course_id',
                lesson_id='sample_lesson_id',
                attempt_date=0,
                completion_status='sample_completion_status',
                time_spent_minutes=0,
                quiz_score=0,
                quiz_passed=False,
                notes='sample_notes',
                last_accessed=0,
            )
            result = self.tenantprogress_repo.record_lesson_progress(test_entity)
            print("   ✅ Record user's progress on a lesson completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #16: {e}')

        # Access Pattern #17: Update user's lesson progress
        # Index: Main Table
        try:
            print("🔍 Testing Access Pattern #17: Update user's lesson progress")
            print('   Using Main Table')
            result = self.tenantprogress_repo.update_lesson_progress(
                created_entities['TenantProgress'].tenant_id,
                created_entities['TenantProgress'].user_id,
                created_entities['TenantProgress'].course_id,
                created_entities['TenantProgress'].lesson_id,
                created_entities['TenantProgress'].attempt_date,
                created_entities['TenantProgress'].completion_status,
                created_entities['TenantProgress'].time_spent_minutes,
            )
            print("   ✅ Update user's lesson progress completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #17: {e}')

        # TenantUser
        # Access Pattern #3: Get user profile within tenant
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #3: Get user profile within tenant')
            print('   Using Main Table')
            result = self.tenantuser_repo.get_tenant_user(
                created_entities['TenantUser'].tenant_id, created_entities['TenantUser'].user_id
            )
            print('   ✅ Get user profile within tenant completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # Access Pattern #4: Create new user in tenant
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #4: Create new user in tenant')
            print('   Using Main Table')
            test_entity = TenantUser(
                tenant_id='sample_tenant_id',
                user_id='sample_user_id',
                email='sample_email',
                first_name='sample_first_name',
                last_name='sample_last_name',
                role='sample_role',
                department='sample_department',
                job_title='sample_job_title',
                enrollment_date=0,
                last_login=0,
                status='sample_status',
            )
            result = self.tenantuser_repo.put_tenant_user(test_entity)
            print('   ✅ Create new user in tenant completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: Update user profile information
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #5: Update user profile information')
            print('   Using Main Table')
            result = self.tenantuser_repo.update_user_profile(
                created_entities['TenantUser'].tenant_id,
                created_entities['TenantUser'].user_id,
                created_entities['TenantUser'],
            )
            print('   ✅ Update user profile information completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

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
    print('   - ELearningPlatform')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
