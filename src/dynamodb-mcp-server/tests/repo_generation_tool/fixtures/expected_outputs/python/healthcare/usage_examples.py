"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
import time
from decimal import Decimal

# Import generated entities and repositories
from entities import (
    Appointment,
    AppointmentNote,
    Patient,
    PatientAllergy,
    PatientAppointment,
    PatientMedicalHistory,
    Provider,
    ProviderAppointment,
    ProviderSchedule,
    ProviderSpecialty,
)
from repositories import (
    AppointmentNoteRepository,
    AppointmentRepository,
    PatientAllergyRepository,
    PatientAppointmentRepository,
    PatientMedicalHistoryRepository,
    PatientRepository,
    ProviderAppointmentRepository,
    ProviderRepository,
    ProviderScheduleRepository,
    ProviderSpecialtyRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # PatientTable table repositories
        self.patient_repo = PatientRepository('PatientTable')
        self.patientmedicalhistory_repo = PatientMedicalHistoryRepository('PatientTable')
        self.patientallergy_repo = PatientAllergyRepository('PatientTable')
        # ProviderTable table repositories
        self.provider_repo = ProviderRepository('ProviderTable')
        self.providerspecialty_repo = ProviderSpecialtyRepository('ProviderTable')
        self.providerschedule_repo = ProviderScheduleRepository('ProviderTable')
        # AppointmentTable table repositories
        self.appointment_repo = AppointmentRepository('AppointmentTable')
        self.patientappointment_repo = PatientAppointmentRepository('AppointmentTable')
        self.providerappointment_repo = ProviderAppointmentRepository('AppointmentTable')
        self.appointmentnote_repo = AppointmentNoteRepository('AppointmentTable')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== PatientTable Table Operations ===')

        # Patient example
        print('\n--- Patient ---')

        # 1. CREATE - Create sample patient
        sample_patient = Patient(
            patient_id='patient_id123',
            medical_record_number='sample_medical_record_number',
            first_name='sample_first_name',
            last_name='sample_last_name',
            date_of_birth='sample_date_of_birth',
            gender='sample_gender',
            phone='sample_phone',
            email='sample_email',
            address={'key': 'value'},
            emergency_contact={'key': 'value'},
            insurance_info={'key': 'value'},
            primary_care_provider_id='primary_care_provider_id123',
            created_at='sample_created_at',
            updated_at='sample_updated_at',
            status='active',
        )

        print('📝 Creating patient...')
        print(f'📝 PK: {sample_patient.pk()}, SK: {sample_patient.sk()}')

        created_patient = self.patient_repo.create_patient(sample_patient)
        print(f'✅ Created: {created_patient}')

        # Store created entity for access pattern testing
        created_entities['Patient'] = created_patient
        # 2. UPDATE - Update non-key field (medical_record_number)
        print('\n🔄 Updating medical_record_number field...')
        original_value = created_patient.medical_record_number
        created_patient.medical_record_number = 'updated_medical_record_number'

        updated_patient = self.patient_repo.update_patient(created_patient)
        print(
            f'✅ Updated medical_record_number: {original_value} → {updated_patient.medical_record_number}'
        )

        # Update stored entity with updated values
        created_entities['Patient'] = updated_patient

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving patient...')
        retrieved_patient = self.patient_repo.get_patient(created_patient.patient_id)

        if retrieved_patient:
            print(f'✅ Retrieved: {retrieved_patient}')
        else:
            print('❌ Failed to retrieve patient')

        print('🎯 Patient CRUD cycle completed successfully!')

        # PatientMedicalHistory example
        print('\n--- PatientMedicalHistory ---')

        # 1. CREATE - Create sample patientmedicalhistory
        sample_patientmedicalhistory = PatientMedicalHistory(
            patient_id='patient_id123',
            record_id='record_id123',
            record_date='sample_record_date',
            record_type='sample_record_type',
            provider_id='provider_id123',
            diagnosis_codes=['sample1', 'sample2'],
            procedure_codes=['sample1', 'sample2'],
            medications=['sample1', 'sample2'],
            allergies=['sample1', 'sample2'],
            vital_signs={'key': 'value'},
            notes='sample_notes',
            attachments=['sample1', 'sample2'],
            created_at='sample_created_at',
        )

        print('📝 Creating patientmedicalhistory...')
        print(
            f'📝 PK: {sample_patientmedicalhistory.pk()}, SK: {sample_patientmedicalhistory.sk()}'
        )

        created_patientmedicalhistory = (
            self.patientmedicalhistory_repo.create_patient_medical_history(
                sample_patientmedicalhistory
            )
        )
        print(f'✅ Created: {created_patientmedicalhistory}')

        # Store created entity for access pattern testing
        created_entities['PatientMedicalHistory'] = created_patientmedicalhistory
        # 2. UPDATE - Update non-key field (record_type)
        print('\n🔄 Updating record_type field...')
        original_value = created_patientmedicalhistory.record_type
        created_patientmedicalhistory.record_type = 'updated_record_type'

        updated_patientmedicalhistory = (
            self.patientmedicalhistory_repo.update_patient_medical_history(
                created_patientmedicalhistory
            )
        )
        print(
            f'✅ Updated record_type: {original_value} → {updated_patientmedicalhistory.record_type}'
        )

        # Update stored entity with updated values
        created_entities['PatientMedicalHistory'] = updated_patientmedicalhistory

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving patientmedicalhistory...')
        retrieved_patientmedicalhistory = (
            self.patientmedicalhistory_repo.get_patient_medical_history(
                created_patientmedicalhistory.patient_id,
                created_patientmedicalhistory.record_date,
                created_patientmedicalhistory.record_id,
            )
        )

        if retrieved_patientmedicalhistory:
            print(f'✅ Retrieved: {retrieved_patientmedicalhistory}')
        else:
            print('❌ Failed to retrieve patientmedicalhistory')

        print('🎯 PatientMedicalHistory CRUD cycle completed successfully!')

        # PatientAllergy example
        print('\n--- PatientAllergy ---')

        # 1. CREATE - Create sample patientallergy
        sample_patientallergy = PatientAllergy(
            patient_id='patient_id123',
            allergy_id='allergy_id123',
            allergen='sample_allergen',
            allergy_type='sample_allergy_type',
            severity='sample_severity',
            reaction='sample_reaction',
            onset_date='sample_onset_date',
            notes='sample_notes',
            status='active',
            created_at='sample_created_at',
        )

        print('📝 Creating patientallergy...')
        print(f'📝 PK: {sample_patientallergy.pk()}, SK: {sample_patientallergy.sk()}')

        created_patientallergy = self.patientallergy_repo.create_patient_allergy(
            sample_patientallergy
        )
        print(f'✅ Created: {created_patientallergy}')

        # Store created entity for access pattern testing
        created_entities['PatientAllergy'] = created_patientallergy
        # 2. UPDATE - Update non-key field (allergen)
        print('\n🔄 Updating allergen field...')
        original_value = created_patientallergy.allergen
        created_patientallergy.allergen = 'updated_allergen'

        updated_patientallergy = self.patientallergy_repo.update_patient_allergy(
            created_patientallergy
        )
        print(f'✅ Updated allergen: {original_value} → {updated_patientallergy.allergen}')

        # Update stored entity with updated values
        created_entities['PatientAllergy'] = updated_patientallergy

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving patientallergy...')
        retrieved_patientallergy = self.patientallergy_repo.get_patient_allergy(
            created_patientallergy.patient_id, created_patientallergy.allergy_id
        )

        if retrieved_patientallergy:
            print(f'✅ Retrieved: {retrieved_patientallergy}')
        else:
            print('❌ Failed to retrieve patientallergy')

        print('🎯 PatientAllergy CRUD cycle completed successfully!')
        print('\n=== ProviderTable Table Operations ===')

        # Provider example
        print('\n--- Provider ---')

        # 1. CREATE - Create sample provider
        sample_provider = Provider(
            provider_id='provider_id123',
            npi_number='sample_npi_number',
            first_name='sample_first_name',
            last_name='sample_last_name',
            title='sample_title',
            specialties=['sample1', 'sample2'],
            license_number='sample_license_number',
            license_state='sample_license_state',
            phone='sample_phone',
            email='sample_email',
            practice_address={'key': 'value'},
            hospital_affiliations=['sample1', 'sample2'],
            languages=['sample1', 'sample2'],
            accepting_new_patients=True,
            created_at='sample_created_at',
            updated_at='sample_updated_at',
            status='active',
        )

        print('📝 Creating provider...')
        print(f'📝 PK: {sample_provider.pk()}, SK: {sample_provider.sk()}')

        created_provider = self.provider_repo.create_provider(sample_provider)
        print(f'✅ Created: {created_provider}')

        # Store created entity for access pattern testing
        created_entities['Provider'] = created_provider
        # 2. UPDATE - Update non-key field (npi_number)
        print('\n🔄 Updating npi_number field...')
        original_value = created_provider.npi_number
        created_provider.npi_number = 'updated_npi_number'

        updated_provider = self.provider_repo.update_provider(created_provider)
        print(f'✅ Updated npi_number: {original_value} → {updated_provider.npi_number}')

        # Update stored entity with updated values
        created_entities['Provider'] = updated_provider

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving provider...')
        retrieved_provider = self.provider_repo.get_provider(created_provider.provider_id)

        if retrieved_provider:
            print(f'✅ Retrieved: {retrieved_provider}')
        else:
            print('❌ Failed to retrieve provider')

        print('🎯 Provider CRUD cycle completed successfully!')

        # ProviderSpecialty example
        print('\n--- ProviderSpecialty ---')

        # 1. CREATE - Create sample providerspecialty
        sample_providerspecialty = ProviderSpecialty(
            specialty_name='sample_specialty_name',
            provider_id='provider_id123',
            provider_name='provider_name123',
            years_experience=42,
            board_certified=True,
            accepting_new_patients=True,
            practice_location='sample_practice_location',
        )

        print('📝 Creating providerspecialty...')
        print(f'📝 PK: {sample_providerspecialty.pk()}, SK: {sample_providerspecialty.sk()}')

        created_providerspecialty = self.providerspecialty_repo.create_provider_specialty(
            sample_providerspecialty
        )
        print(f'✅ Created: {created_providerspecialty}')

        # Store created entity for access pattern testing
        created_entities['ProviderSpecialty'] = created_providerspecialty
        # 2. UPDATE - Update non-key field (provider_name)
        print('\n🔄 Updating provider_name field...')
        original_value = created_providerspecialty.provider_name
        created_providerspecialty.provider_name = 'updated_provider_name'

        updated_providerspecialty = self.providerspecialty_repo.update_provider_specialty(
            created_providerspecialty
        )
        print(
            f'✅ Updated provider_name: {original_value} → {updated_providerspecialty.provider_name}'
        )

        # Update stored entity with updated values
        created_entities['ProviderSpecialty'] = updated_providerspecialty

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving providerspecialty...')
        retrieved_providerspecialty = self.providerspecialty_repo.get_provider_specialty(
            created_providerspecialty.specialty_name, created_providerspecialty.provider_id
        )

        if retrieved_providerspecialty:
            print(f'✅ Retrieved: {retrieved_providerspecialty}')
        else:
            print('❌ Failed to retrieve providerspecialty')

        print('🎯 ProviderSpecialty CRUD cycle completed successfully!')

        # ProviderSchedule example
        print('\n--- ProviderSchedule ---')

        # 1. CREATE - Create sample providerschedule
        sample_providerschedule = ProviderSchedule(
            provider_id='provider_id123',
            date='sample_date',
            time_slot='sample_time_slot',
            duration_minutes=42,
            appointment_type='sample_appointment_type',
            status='active',
            location='sample_location',
            notes='sample_notes',
        )

        print('📝 Creating providerschedule...')
        print(f'📝 PK: {sample_providerschedule.pk()}, SK: {sample_providerschedule.sk()}')

        created_providerschedule = self.providerschedule_repo.create_provider_schedule(
            sample_providerschedule
        )
        print(f'✅ Created: {created_providerschedule}')

        # Store created entity for access pattern testing
        created_entities['ProviderSchedule'] = created_providerschedule
        # 2. UPDATE - Update non-key field (duration_minutes)
        print('\n🔄 Updating duration_minutes field...')
        original_value = created_providerschedule.duration_minutes
        created_providerschedule.duration_minutes = 99

        updated_providerschedule = self.providerschedule_repo.update_provider_schedule(
            created_providerschedule
        )
        print(
            f'✅ Updated duration_minutes: {original_value} → {updated_providerschedule.duration_minutes}'
        )

        # Update stored entity with updated values
        created_entities['ProviderSchedule'] = updated_providerschedule

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving providerschedule...')
        retrieved_providerschedule = self.providerschedule_repo.get_provider_schedule(
            created_providerschedule.provider_id,
            created_providerschedule.date,
            created_providerschedule.time_slot,
        )

        if retrieved_providerschedule:
            print(f'✅ Retrieved: {retrieved_providerschedule}')
        else:
            print('❌ Failed to retrieve providerschedule')

        print('🎯 ProviderSchedule CRUD cycle completed successfully!')
        print('\n=== AppointmentTable Table Operations ===')

        # Appointment example
        print('\n--- Appointment ---')

        # 1. CREATE - Create sample appointment
        sample_appointment = Appointment(
            appointment_id='appointment_id123',
            patient_id='patient_id123',
            provider_id='provider_id123',
            appointment_date='sample_appointment_date',
            appointment_time='sample_appointment_time',
            duration_minutes=42,
            appointment_type='sample_appointment_type',
            reason='sample_reason',
            status='active',
            location='sample_location',
            notes='sample_notes',
            insurance_authorization='sample_insurance_authorization',
            copay_amount=Decimal('3.14'),
            created_at='sample_created_at',
            updated_at='sample_updated_at',
            checked_in_at='sample_checked_in_at',
            completed_at='sample_completed_at',
        )

        print('📝 Creating appointment...')
        print(f'📝 PK: {sample_appointment.pk()}, SK: {sample_appointment.sk()}')

        created_appointment = self.appointment_repo.create_appointment(sample_appointment)
        print(f'✅ Created: {created_appointment}')

        # Store created entity for access pattern testing
        created_entities['Appointment'] = created_appointment
        # 2. UPDATE - Update non-key field (patient_id)
        print('\n🔄 Updating patient_id field...')
        original_value = created_appointment.patient_id
        created_appointment.patient_id = 'updated_patient_id'

        updated_appointment = self.appointment_repo.update_appointment(created_appointment)
        print(f'✅ Updated patient_id: {original_value} → {updated_appointment.patient_id}')

        # Update stored entity with updated values
        created_entities['Appointment'] = updated_appointment

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving appointment...')
        retrieved_appointment = self.appointment_repo.get_appointment(
            created_appointment.appointment_id
        )

        if retrieved_appointment:
            print(f'✅ Retrieved: {retrieved_appointment}')
        else:
            print('❌ Failed to retrieve appointment')

        print('🎯 Appointment CRUD cycle completed successfully!')

        # PatientAppointment example
        print('\n--- PatientAppointment ---')

        # 1. CREATE - Create sample patientappointment
        sample_patientappointment = PatientAppointment(
            patient_id='patient_id123',
            appointment_id='appointment_id123',
            provider_id='provider_id123',
            provider_name='provider_name123',
            appointment_date='sample_appointment_date',
            appointment_time='sample_appointment_time',
            appointment_type='sample_appointment_type',
            reason='sample_reason',
            status='active',
            location='sample_location',
        )

        print('📝 Creating patientappointment...')
        print(f'📝 PK: {sample_patientappointment.pk()}, SK: {sample_patientappointment.sk()}')

        created_patientappointment = self.patientappointment_repo.create_patient_appointment(
            sample_patientappointment
        )
        print(f'✅ Created: {created_patientappointment}')

        # Store created entity for access pattern testing
        created_entities['PatientAppointment'] = created_patientappointment
        # 2. UPDATE - Update non-key field (provider_id)
        print('\n🔄 Updating provider_id field...')
        original_value = created_patientappointment.provider_id
        created_patientappointment.provider_id = 'updated_provider_id'

        updated_patientappointment = self.patientappointment_repo.update_patient_appointment(
            created_patientappointment
        )
        print(
            f'✅ Updated provider_id: {original_value} → {updated_patientappointment.provider_id}'
        )

        # Update stored entity with updated values
        created_entities['PatientAppointment'] = updated_patientappointment

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving patientappointment...')
        retrieved_patientappointment = self.patientappointment_repo.get_patient_appointment(
            created_patientappointment.patient_id,
            created_patientappointment.appointment_date,
            created_patientappointment.appointment_time,
            created_patientappointment.appointment_id,
        )

        if retrieved_patientappointment:
            print(f'✅ Retrieved: {retrieved_patientappointment}')
        else:
            print('❌ Failed to retrieve patientappointment')

        print('🎯 PatientAppointment CRUD cycle completed successfully!')

        # ProviderAppointment example
        print('\n--- ProviderAppointment ---')

        # 1. CREATE - Create sample providerappointment
        sample_providerappointment = ProviderAppointment(
            provider_id='provider_id123',
            appointment_id='appointment_id123',
            patient_id='patient_id123',
            patient_name='sample_patient_name',
            appointment_date='sample_appointment_date',
            appointment_time='sample_appointment_time',
            duration_minutes=42,
            appointment_type='sample_appointment_type',
            reason='sample_reason',
            status='active',
            location='sample_location',
        )

        print('📝 Creating providerappointment...')
        print(f'📝 PK: {sample_providerappointment.pk()}, SK: {sample_providerappointment.sk()}')

        created_providerappointment = self.providerappointment_repo.create_provider_appointment(
            sample_providerappointment
        )
        print(f'✅ Created: {created_providerappointment}')

        # Store created entity for access pattern testing
        created_entities['ProviderAppointment'] = created_providerappointment
        # 2. UPDATE - Update non-key field (patient_id)
        print('\n🔄 Updating patient_id field...')
        original_value = created_providerappointment.patient_id
        created_providerappointment.patient_id = 'updated_patient_id'

        updated_providerappointment = self.providerappointment_repo.update_provider_appointment(
            created_providerappointment
        )
        print(
            f'✅ Updated patient_id: {original_value} → {updated_providerappointment.patient_id}'
        )

        # Update stored entity with updated values
        created_entities['ProviderAppointment'] = updated_providerappointment

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving providerappointment...')
        retrieved_providerappointment = self.providerappointment_repo.get_provider_appointment(
            created_providerappointment.provider_id,
            created_providerappointment.appointment_date,
            created_providerappointment.appointment_time,
            created_providerappointment.appointment_id,
        )

        if retrieved_providerappointment:
            print(f'✅ Retrieved: {retrieved_providerappointment}')
        else:
            print('❌ Failed to retrieve providerappointment')

        print('🎯 ProviderAppointment CRUD cycle completed successfully!')

        # AppointmentNote example
        print('\n--- AppointmentNote ---')

        # 1. CREATE - Create sample appointmentnote
        sample_appointmentnote = AppointmentNote(
            appointment_id='appointment_id123',
            note_id='note_id123',
            provider_id='provider_id123',
            note_type='sample_note_type',
            content='sample_content',
            diagnosis_codes=['sample1', 'sample2'],
            procedure_codes=['sample1', 'sample2'],
            medications_prescribed=['sample1', 'sample2'],
            follow_up_required=True,
            follow_up_date='sample_follow_up_date',
            created_at='sample_created_at',
            updated_at='sample_updated_at',
        )

        print('📝 Creating appointmentnote...')
        print(f'📝 PK: {sample_appointmentnote.pk()}, SK: {sample_appointmentnote.sk()}')

        created_appointmentnote = self.appointmentnote_repo.create_appointment_note(
            sample_appointmentnote
        )
        print(f'✅ Created: {created_appointmentnote}')

        # Store created entity for access pattern testing
        created_entities['AppointmentNote'] = created_appointmentnote
        # 2. UPDATE - Update non-key field (provider_id)
        print('\n🔄 Updating provider_id field...')
        original_value = created_appointmentnote.provider_id
        created_appointmentnote.provider_id = 'updated_provider_id'

        updated_appointmentnote = self.appointmentnote_repo.update_appointment_note(
            created_appointmentnote
        )
        print(f'✅ Updated provider_id: {original_value} → {updated_appointmentnote.provider_id}')

        # Update stored entity with updated values
        created_entities['AppointmentNote'] = updated_appointmentnote

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving appointmentnote...')
        retrieved_appointmentnote = self.appointmentnote_repo.get_appointment_note(
            created_appointmentnote.appointment_id,
            created_appointmentnote.created_at,
            created_appointmentnote.note_id,
        )

        if retrieved_appointmentnote:
            print(f'✅ Retrieved: {retrieved_appointmentnote}')
        else:
            print('❌ Failed to retrieve appointmentnote')

        print('🎯 AppointmentNote CRUD cycle completed successfully!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed successfully!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete Patient
        if 'Patient' in created_entities:
            print('\n🗑️  Deleting patient...')
            deleted = self.patient_repo.delete_patient(created_entities['Patient'].patient_id)

            if deleted:
                print('✅ Deleted patient successfully')
            else:
                print('❌ Failed to delete patient')

        # Delete PatientMedicalHistory
        if 'PatientMedicalHistory' in created_entities:
            print('\n🗑️  Deleting patientmedicalhistory...')
            deleted = self.patientmedicalhistory_repo.delete_patient_medical_history(
                created_entities['PatientMedicalHistory'].patient_id,
                created_entities['PatientMedicalHistory'].record_date,
                created_entities['PatientMedicalHistory'].record_id,
            )

            if deleted:
                print('✅ Deleted patientmedicalhistory successfully')
            else:
                print('❌ Failed to delete patientmedicalhistory')

        # Delete PatientAllergy
        if 'PatientAllergy' in created_entities:
            print('\n🗑️  Deleting patientallergy...')
            deleted = self.patientallergy_repo.delete_patient_allergy(
                created_entities['PatientAllergy'].patient_id,
                created_entities['PatientAllergy'].allergy_id,
            )

            if deleted:
                print('✅ Deleted patientallergy successfully')
            else:
                print('❌ Failed to delete patientallergy')

        # Delete Provider
        if 'Provider' in created_entities:
            print('\n🗑️  Deleting provider...')
            deleted = self.provider_repo.delete_provider(created_entities['Provider'].provider_id)

            if deleted:
                print('✅ Deleted provider successfully')
            else:
                print('❌ Failed to delete provider')

        # Delete ProviderSpecialty
        if 'ProviderSpecialty' in created_entities:
            print('\n🗑️  Deleting providerspecialty...')
            deleted = self.providerspecialty_repo.delete_provider_specialty(
                created_entities['ProviderSpecialty'].specialty_name,
                created_entities['ProviderSpecialty'].provider_id,
            )

            if deleted:
                print('✅ Deleted providerspecialty successfully')
            else:
                print('❌ Failed to delete providerspecialty')

        # Delete ProviderSchedule
        if 'ProviderSchedule' in created_entities:
            print('\n🗑️  Deleting providerschedule...')
            deleted = self.providerschedule_repo.delete_provider_schedule(
                created_entities['ProviderSchedule'].provider_id,
                created_entities['ProviderSchedule'].date,
                created_entities['ProviderSchedule'].time_slot,
            )

            if deleted:
                print('✅ Deleted providerschedule successfully')
            else:
                print('❌ Failed to delete providerschedule')

        # Delete Appointment
        if 'Appointment' in created_entities:
            print('\n🗑️  Deleting appointment...')
            deleted = self.appointment_repo.delete_appointment(
                created_entities['Appointment'].appointment_id
            )

            if deleted:
                print('✅ Deleted appointment successfully')
            else:
                print('❌ Failed to delete appointment')

        # Delete PatientAppointment
        if 'PatientAppointment' in created_entities:
            print('\n🗑️  Deleting patientappointment...')
            deleted = self.patientappointment_repo.delete_patient_appointment(
                created_entities['PatientAppointment'].patient_id,
                created_entities['PatientAppointment'].appointment_date,
                created_entities['PatientAppointment'].appointment_time,
                created_entities['PatientAppointment'].appointment_id,
            )

            if deleted:
                print('✅ Deleted patientappointment successfully')
            else:
                print('❌ Failed to delete patientappointment')

        # Delete ProviderAppointment
        if 'ProviderAppointment' in created_entities:
            print('\n🗑️  Deleting providerappointment...')
            deleted = self.providerappointment_repo.delete_provider_appointment(
                created_entities['ProviderAppointment'].provider_id,
                created_entities['ProviderAppointment'].appointment_date,
                created_entities['ProviderAppointment'].appointment_time,
                created_entities['ProviderAppointment'].appointment_id,
            )

            if deleted:
                print('✅ Deleted providerappointment successfully')
            else:
                print('❌ Failed to delete providerappointment')

        # Delete AppointmentNote
        if 'AppointmentNote' in created_entities:
            print('\n🗑️  Deleting appointmentnote...')
            deleted = self.appointmentnote_repo.delete_appointment_note(
                created_entities['AppointmentNote'].appointment_id,
                created_entities['AppointmentNote'].created_at,
                created_entities['AppointmentNote'].note_id,
            )

            if deleted:
                print('✅ Deleted appointmentnote successfully')
            else:
                print('❌ Failed to delete appointmentnote')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'PatientTable' must exist")
        print("   - DynamoDB table 'ProviderTable' must exist")
        print("   - DynamoDB table 'AppointmentTable' must exist")
        print('   - AWS credentials configured')
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # Patient
        # Access Pattern #1: Get patient profile by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: Get patient profile by ID")
        #     print("   Using Main Table")
        #     patient_id = created_entities["Patient"].patient_id
        #     self.patient_repo.get_patient(
        #         patient_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #2: Create new patient record
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: Create new patient record")
        #     print("   Using Main Table")
        #     patient = created_entities["Patient"]
        #     self.patient_repo.create_patient(
        #         patient,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # Access Pattern #3: Update patient contact and insurance information
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Update patient contact and insurance information")
        #     print("   Using Main Table")
        #     patient_id = created_entities["Patient"].patient_id
        #     updates = created_entities["Patient"]
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_patient_id"
        #     self.patient_repo.update_patient_info(
        #         patient_id,
        #         updates,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # PatientMedicalHistory
        # Access Pattern #4: Get medical history for patient (sorted by date)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Get medical history for patient (sorted by date)")
        #     print("   Using Main Table")
        #     patient_id = created_entities["PatientMedicalHistory"].patient_id
        #     self.patientmedicalhistory_repo.get_patient_medical_history_list(
        #         patient_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #5: Get patient medical history within date range
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Get patient medical history within date range")
        #     print("   Using Main Table")
        #     patient_id = created_entities["PatientMedicalHistory"].patient_id
        #     start_date = ""
        #     end_date = ""
        #     self.patientmedicalhistory_repo.get_patient_history_by_date_range(
        #         patient_id,
        #         start_date,
        #         end_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

        # Access Pattern #6: Add medical record with provider reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: Add medical record with provider reference")
        #     print("   Using Main Table")
        #     medical_record = created_entities["PatientMedicalHistory"]
        #     provider_id = created_entities["PatientMedicalHistory"].provider_id
        #     self.patientmedicalhistory_repo.add_medical_record(
        #         medical_record,
        #         provider_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        # PatientAllergy
        # Access Pattern #7: Get all active allergies for patient
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Get all active allergies for patient")
        #     print("   Using Main Table")
        #     patient_id = created_entities["PatientAllergy"].patient_id
        #     self.patientallergy_repo.get_patient_allergies(
        #         patient_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Access Pattern #8: Add allergy record for patient
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Add allergy record for patient")
        #     print("   Using Main Table")
        #     allergy = created_entities["PatientAllergy"]
        #     self.patientallergy_repo.add_patient_allergy(
        #         allergy,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # Provider
        # Access Pattern #9: Get provider profile by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Get provider profile by ID")
        #     print("   Using Main Table")
        #     provider_id = created_entities["Provider"].provider_id
        #     self.provider_repo.get_provider(
        #         provider_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # Access Pattern #10: Create new provider profile
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Create new provider profile")
        #     print("   Using Main Table")
        #     provider = created_entities["Provider"]
        #     self.provider_repo.create_provider(
        #         provider,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

        # Access Pattern #11: Update provider availability status
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #11: Update provider availability status")
        #     print("   Using Main Table")
        #     provider_id = created_entities["Provider"].provider_id
        #     accepting_new_patients = created_entities["Provider"].accepting_new_patients
        #     status = created_entities["Provider"].status
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_provider_id"
        #     self.provider_repo.update_provider_availability(
        #         provider_id,
        #         accepting_new_patients,
        #         status,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #11: {e}")

        # ProviderSpecialty
        # Access Pattern #12: Get all providers for a specific specialty
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #12: Get all providers for a specific specialty")
        #     print("   Using Main Table")
        #     specialty_name = created_entities["ProviderSpecialty"].specialty_name
        #     self.providerspecialty_repo.get_providers_by_specialty(
        #         specialty_name,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #12: {e}")

        # Access Pattern #13: Add provider to specialty index
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #13: Add provider to specialty index")
        #     print("   Using Main Table")
        #     specialty_item = created_entities["ProviderSpecialty"]
        #     self.providerspecialty_repo.add_provider_specialty(
        #         specialty_item,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #13: {e}")

        # ProviderSchedule
        # Access Pattern #14: Get provider schedule for date range
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #14: Get provider schedule for date range")
        #     print("   Using Main Table")
        #     provider_id = created_entities["ProviderSchedule"].provider_id
        #     start_date = ""
        #     end_date = ""
        #     self.providerschedule_repo.get_provider_schedule(
        #         provider_id,
        #         start_date,
        #         end_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #14: {e}")

        # Access Pattern #15: Get available appointment slots for provider
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #15: Get available appointment slots for provider")
        #     print("   Using Main Table")
        #     provider_id = created_entities["ProviderSchedule"].provider_id
        #     date = created_entities["ProviderSchedule"].date
        #     self.providerschedule_repo.get_available_slots(
        #         provider_id,
        #         date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #15: {e}")

        # Appointment
        # Access Pattern #16: Get appointment details by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #16: Get appointment details by ID")
        #     print("   Using Main Table")
        #     appointment_id = created_entities["Appointment"].appointment_id
        #     self.appointment_repo.get_appointment(
        #         appointment_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #16: {e}")

        # Access Pattern #17: Create new appointment with patient and provider references
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #17: Create new appointment with patient and provider references")
        #     print("   Using Main Table")
        #     appointment = created_entities["Appointment"]
        #     patient = created_entities["Patient"]
        #     provider = created_entities["Provider"]
        #     self.appointment_repo.create_appointment_with_refs(
        #         appointment,
        #         patient,
        #         provider,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #17: {e}")

        # Access Pattern #18: Update appointment status and check-in time
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #18: Update appointment status and check-in time")
        #     print("   Using Main Table")
        #     appointment_id = created_entities["Appointment"].appointment_id
        #     status = created_entities["Appointment"].status
        #     checked_in_at = created_entities["Appointment"].checked_in_at
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_appointment_id"
        #     self.appointment_repo.update_appointment_status(
        #         appointment_id,
        #         status,
        #         checked_in_at,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #18: {e}")

        # PatientAppointment
        # Access Pattern #19: Get all appointments for patient (sorted by date/time)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #19: Get all appointments for patient (sorted by date/time)")
        #     print("   Using Main Table")
        #     patient_id = created_entities["PatientAppointment"].patient_id
        #     self.patientappointment_repo.get_patient_appointments(
        #         patient_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #19: {e}")

        # Access Pattern #20: Get upcoming appointments for patient
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #20: Get upcoming appointments for patient")
        #     print("   Using Main Table")
        #     patient_id = created_entities["PatientAppointment"].patient_id
        #     start_date = ""
        #     self.patientappointment_repo.get_patient_upcoming_appointments(
        #         patient_id,
        #         start_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #20: {e}")

        # Access Pattern #21: Add appointment to patient's appointment history
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #21: Add appointment to patient's appointment history")
        #     print("   Using Main Table")
        #     patient_appointment = created_entities["PatientAppointment"]
        #     self.patientappointment_repo.add_appointment_to_patient(
        #         patient_appointment,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #21: {e}")

        # ProviderAppointment
        # Access Pattern #22: Get all appointments for provider (sorted by date/time)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #22: Get all appointments for provider (sorted by date/time)")
        #     print("   Using Main Table")
        #     provider_id = created_entities["ProviderAppointment"].provider_id
        #     self.providerappointment_repo.get_provider_appointments(
        #         provider_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #22: {e}")

        # Access Pattern #23: Get provider's appointments for specific date
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #23: Get provider's appointments for specific date")
        #     print("   Using Main Table")
        #     provider_id = created_entities["ProviderAppointment"].provider_id
        #     appointment_date = created_entities["ProviderAppointment"].appointment_date
        #     self.providerappointment_repo.get_provider_daily_schedule(
        #         provider_id,
        #         appointment_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #23: {e}")

        # Access Pattern #24: Add appointment to provider's schedule with cross-table references
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #24: Add appointment to provider's schedule with cross-table references")
        #     print("   Using Main Table")
        #     provider_appointment = created_entities["ProviderAppointment"]
        #     patient = created_entities["Patient"]
        #     appointment = created_entities["Appointment"]
        #     self.providerappointment_repo.add_appointment_to_provider(
        #         provider_appointment,
        #         patient,
        #         appointment,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #24: {e}")

        # AppointmentNote
        # Access Pattern #25: Get all notes for an appointment
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #25: Get all notes for an appointment")
        #     print("   Using Main Table")
        #     appointment_id = created_entities["AppointmentNote"].appointment_id
        #     self.appointmentnote_repo.get_appointment_notes(
        #         appointment_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #25: {e}")

        # Access Pattern #26: Add clinical note to appointment with provider reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #26: Add clinical note to appointment with provider reference")
        #     print("   Using Main Table")
        #     note = created_entities["AppointmentNote"]
        #     provider = created_entities["Provider"]
        #     self.appointmentnote_repo.add_appointment_note(
        #         note,
        #         provider,
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
    print('   - PatientTable')
    print('   - ProviderTable')
    print('   - AppointmentTable')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
