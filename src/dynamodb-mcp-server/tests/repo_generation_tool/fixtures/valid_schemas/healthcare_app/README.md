# Healthcare Medical Records Multi-Table Schema Example

This example demonstrates a comprehensive healthcare management system using multiple DynamoDB tables with complex medical data relationships and HIPAA-compliant access patterns.

## Architecture Overview

The schema is designed around three main tables representing the healthcare ecosystem:
- **PatientTable**: Manages patient profiles, medical history, and allergies
- **ProviderTable**: Handles healthcare providers, specialties, and schedules
- **AppointmentTable**: Manages appointments, notes, and scheduling relationships

## Tables and Entities

### PatientTable
- **Patient**: Core patient demographics and insurance information
- **PatientMedicalHistory**: Comprehensive medical records sorted by date
- **PatientAllergy**: Allergy records with severity and reaction details

### ProviderTable
- **Provider**: Healthcare provider profiles with credentials and specialties
- **ProviderSpecialty**: Specialty-based provider directory for patient search
- **ProviderSchedule**: Available appointment slots and scheduling

### AppointmentTable
- **Appointment**: Appointment details with patient and provider references
- **PatientAppointment**: Patient's appointment history sorted by date/time
- **ProviderAppointment**: Provider's daily schedule sorted by time
- **AppointmentNote**: Clinical notes with diagnosis and treatment plans

## Key Features Demonstrated

### Healthcare-Specific Patterns
- **Medical record chronology**: History sorted by date for timeline view
- **Provider directory**: Search providers by specialty and availability
- **Appointment scheduling**: Complex scheduling with time slot management
- **Clinical documentation**: Structured notes with medical codes

### Cross-Table Relationships
- Appointments link Patients and Providers across tables
- Medical records reference treating Providers
- Appointment notes maintain Provider authorship
- Scheduling considers both Patient and Provider availability

### Complex Access Patterns
- **Patient care**: Complete medical history, allergies, appointments
- **Provider workflow**: Daily schedule, patient list, clinical notes
- **Appointment management**: Scheduling, check-in, completion tracking
- **Medical search**: Find providers by specialty, available appointments

### Advanced DynamoDB Patterns
- **Time-based partitioning**: Medical records and appointments by date
- **Composite sort keys**: Enable date range queries and chronological sorting
- **Denormalization**: Patient/provider names duplicated for performance
- **Status-based indexing**: Appointments and schedules by status

## Sample Use Cases

1. **Patient Registration**: Create patient profile, add insurance, record allergies
2. **Provider Directory**: Search providers by specialty, check availability
3. **Appointment Scheduling**: Book appointments, manage schedules
4. **Clinical Workflow**: Check-in patients, add clinical notes, prescribe medications
5. **Medical History**: View patient timeline, track treatments, monitor allergies
6. **Practice Management**: Provider schedules, patient lists, appointment tracking

## Cross-Table Entity References

The schema includes extensive cross-table references for healthcare workflows:
- `add_medical_record`: References provider_id for treating physician
- `create_appointment`: References both Patient and Provider entities
- `add_appointment_to_provider`: References Patient and Appointment entities
- `add_appointment_note`: References Provider entity for clinical authorship

## Healthcare Compliance Considerations

This design demonstrates key healthcare data management patterns:
- **Patient privacy**: Data partitioned by patient for access control
- **Audit trails**: Comprehensive timestamps and provider attribution
- **Medical coding**: Support for ICD-10, CPT, and other standard codes
- **Clinical workflow**: Structured data for EMR integration
- **Appointment management**: Complex scheduling with provider availability

## Medical Data Structures

The schema includes healthcare-specific data structures:
- **Vital signs**: Structured objects for blood pressure, temperature, etc.
- **Diagnosis codes**: Arrays of ICD-10 codes for medical conditions
- **Procedure codes**: CPT codes for medical procedures and treatments
- **Medication records**: Prescription tracking with dosage and frequency
- **Insurance information**: Coverage details and authorization tracking

This schema showcases how to build a comprehensive healthcare management system with proper medical data relationships while maintaining efficient query patterns and supporting clinical workflows across multiple DynamoDB tables.