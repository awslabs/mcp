# Multi-Tenant E-Learning Platform Single Table Design Example

This example demonstrates a comprehensive multi-tenant e-learning platform using DynamoDB's single table design with complex hierarchical partition keys for tenant isolation and data organization.

## Architecture Overview

The schema is designed around a single DynamoDB table representing the multi-tenant e-learning ecosystem:
- **ELearningPlatform**: Manages all tenant organizations, users, courses, enrollments, lessons, progress tracking, and certificates in one table

## Tables and Entities

### ELearningPlatform Table
- **TenantOrganization**: Organization profiles with subscription plans and limits
- **TenantUser**: User profiles within tenant organizations with roles and departments
- **TenantCourse**: Course catalog with instructor assignments and metadata
- **TenantEnrollment**: User course enrollments with progress tracking
- **TenantLesson**: Course lessons with ordered content and requirements
- **TenantProgress**: Detailed lesson-level progress tracking and quiz results
- **TenantCertificate**: Course completion certificates with verification

## Key Features Demonstrated

### Multi-Tenant Architecture
- **Tenant isolation**: All data partitioned by tenant_id for complete separation
- **Hierarchical partition keys**: Complex PK patterns like `TENANT#{tenant_id}#USER#{user_id}`
- **Scalable user management**: Role-based access within tenant boundaries
- **Subscription-based limits**: Max users and courses per tenant organization

### Complex Partition Key Patterns
- **Single tenant**: `TENANT#{tenant_id}` for organization data
- **Tenant + User**: `TENANT#{tenant_id}#USER#{user_id}` for user-specific data
- **Tenant + Course**: `TENANT#{tenant_id}#COURSE#{course_id}` for course content
- **Triple hierarchy**: `TENANT#{tenant_id}#USER#{user_id}#COURSE#{course_id}` for progress tracking

### Educational Workflow Patterns
- **Course management**: Create courses, lessons, and learning paths
- **Enrollment tracking**: User course enrollments with progress monitoring
- **Progress analytics**: Detailed lesson completion and quiz performance
- **Certification system**: Automated certificate issuance with verification
- **Learning paths**: Ordered lessons with prerequisites and dependencies

### Advanced DynamoDB Patterns
- **Hierarchical sort keys**: Enable ordered lesson retrieval and progress tracking
- **Strategic denormalization**: Course titles and instructor names duplicated for performance
- **Time-based sorting**: Enrollments and progress sorted by dates
- **Composite key queries**: Efficient retrieval of related educational data

## Sample Use Cases

1. **Tenant Onboarding**: Create organization, set subscription limits, add admin users
2. **Course Creation**: Build courses with ordered lessons, quizzes, and prerequisites
3. **User Enrollment**: Enroll users in courses, track progress, issue certificates
4. **Learning Analytics**: Monitor user progress, completion rates, quiz performance
5. **Certification Management**: Issue, verify, and manage course completion certificates
6. **Multi-Tenant Reporting**: Generate tenant-specific learning analytics and reports

## Cross-Table Entity References

The schema uses entity references within access patterns for data consistency:
- `create_tenant_organization`: References TenantOrganization entity
- `create_tenant_user`: References TenantUser entity for user management
- `create_tenant_course`: References TenantCourse entity for course creation
- `enroll_user_in_course`: References TenantEnrollment entity
- `create_course_lesson`: References TenantLesson entity
- `record_lesson_progress`: References TenantProgress entity
- `issue_course_certificate`: References TenantCertificate entity

## Multi-Tenant Design Considerations

This design demonstrates key multi-tenant e-learning patterns:
- **Complete tenant isolation**: Each tenant's data is fully separated by partition keys
- **Hierarchical data organization**: Users, courses, and progress logically grouped
- **Scalable content delivery**: Lessons and progress tracking optimized for performance
- **Subscription management**: Built-in limits and usage tracking per tenant
- **Educational compliance**: Progress tracking and certification for regulatory requirements
- **Cross-tenant security**: Partition key design prevents data leakage between tenants

This schema showcases how to build a scalable multi-tenant e-learning platform using DynamoDB's single table design while maintaining strict tenant isolation, supporting complex educational workflows, and enabling efficient learning analytics across the entire platform.
