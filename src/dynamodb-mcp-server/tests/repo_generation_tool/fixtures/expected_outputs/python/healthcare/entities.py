# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig
from decimal import Decimal
from pydantic import BaseModel
from typing import Any


# Patient Entity Configuration
PATIENT_CONFIG = EntityConfig(
    entity_type='PATIENT',
    pk_builder=lambda entity: f'PATIENT#{entity.patient_id}',
    pk_lookup_builder=lambda patient_id: f'PATIENT#{patient_id}',
    sk_builder=lambda entity: 'PROFILE',
    sk_lookup_builder=lambda: 'PROFILE',
    prefix_builder=lambda **kwargs: 'PATIENT#',
)


class Patient(ConfigurableEntity):
    patient_id: str
    medical_record_number: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: str
    email: str = None
    address: dict[str, Any]
    emergency_contact: dict[str, Any]
    insurance_info: dict[str, Any] = None
    primary_care_provider_id: str = None
    created_at: str
    updated_at: str
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PATIENT_CONFIG


# PatientMedicalHistory Entity Configuration
PATIENTMEDICALHISTORY_CONFIG = EntityConfig(
    entity_type='MEDICAL_HISTORY',
    pk_builder=lambda entity: f'PATIENT#{entity.patient_id}',
    pk_lookup_builder=lambda patient_id: f'PATIENT#{patient_id}',
    sk_builder=lambda entity: f'HISTORY#{entity.record_date}#{entity.record_id}',
    sk_lookup_builder=lambda record_date, record_id: f'HISTORY#{record_date}#{record_id}',
    prefix_builder=lambda **kwargs: 'HISTORY#',
)


class PatientMedicalHistory(ConfigurableEntity):
    patient_id: str
    record_id: str
    record_date: str
    record_type: str
    provider_id: str
    diagnosis_codes: list[str] = None
    procedure_codes: list[str] = None
    medications: list[str] = None
    allergies: list[str] = None
    vital_signs: dict[str, Any] = None
    notes: str = None
    attachments: list[str] = None
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PATIENTMEDICALHISTORY_CONFIG


# PatientAllergy Entity Configuration
PATIENTALLERGY_CONFIG = EntityConfig(
    entity_type='ALLERGY',
    pk_builder=lambda entity: f'PATIENT#{entity.patient_id}',
    pk_lookup_builder=lambda patient_id: f'PATIENT#{patient_id}',
    sk_builder=lambda entity: f'ALLERGY#{entity.allergy_id}',
    sk_lookup_builder=lambda allergy_id: f'ALLERGY#{allergy_id}',
    prefix_builder=lambda **kwargs: 'ALLERGY#',
)


class PatientAllergy(ConfigurableEntity):
    patient_id: str
    allergy_id: str
    allergen: str
    allergy_type: str
    severity: str
    reaction: str = None
    onset_date: str = None
    notes: str = None
    status: str
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PATIENTALLERGY_CONFIG


# Provider Entity Configuration
PROVIDER_CONFIG = EntityConfig(
    entity_type='PROVIDER',
    pk_builder=lambda entity: f'PROVIDER#{entity.provider_id}',
    pk_lookup_builder=lambda provider_id: f'PROVIDER#{provider_id}',
    sk_builder=lambda entity: 'PROFILE',
    sk_lookup_builder=lambda: 'PROFILE',
    prefix_builder=lambda **kwargs: 'PROVIDER#',
)


class Provider(ConfigurableEntity):
    provider_id: str
    npi_number: str
    first_name: str
    last_name: str
    title: str
    specialties: list[str]
    license_number: str
    license_state: str
    phone: str
    email: str
    practice_address: dict[str, Any]
    hospital_affiliations: list[str] = None
    languages: list[str] = None
    accepting_new_patients: bool
    created_at: str
    updated_at: str
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PROVIDER_CONFIG


# ProviderSpecialty Entity Configuration
PROVIDERSPECIALTY_CONFIG = EntityConfig(
    entity_type='SPECIALTY',
    pk_builder=lambda entity: f'SPECIALTY#{entity.specialty_name}',
    pk_lookup_builder=lambda specialty_name: f'SPECIALTY#{specialty_name}',
    sk_builder=lambda entity: f'PROVIDER#{entity.provider_id}',
    sk_lookup_builder=lambda provider_id: f'PROVIDER#{provider_id}',
    prefix_builder=lambda **kwargs: 'PROVIDER#',
)


class ProviderSpecialty(ConfigurableEntity):
    specialty_name: str
    provider_id: str
    provider_name: str
    years_experience: int = None
    board_certified: bool
    accepting_new_patients: bool
    practice_location: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PROVIDERSPECIALTY_CONFIG


# ProviderSchedule Entity Configuration
PROVIDERSCHEDULE_CONFIG = EntityConfig(
    entity_type='SCHEDULE',
    pk_builder=lambda entity: f'PROVIDER#{entity.provider_id}',
    pk_lookup_builder=lambda provider_id: f'PROVIDER#{provider_id}',
    sk_builder=lambda entity: f'SCHEDULE#{entity.date}#{entity.time_slot}',
    sk_lookup_builder=lambda date, time_slot: f'SCHEDULE#{date}#{time_slot}',
    prefix_builder=lambda **kwargs: 'SCHEDULE#',
)


class ProviderSchedule(ConfigurableEntity):
    provider_id: str
    date: str
    time_slot: str
    duration_minutes: int
    appointment_type: str
    status: str
    location: str
    notes: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PROVIDERSCHEDULE_CONFIG


# Appointment Entity Configuration
APPOINTMENT_CONFIG = EntityConfig(
    entity_type='APPOINTMENT',
    pk_builder=lambda entity: f'APPOINTMENT#{entity.appointment_id}',
    pk_lookup_builder=lambda appointment_id: f'APPOINTMENT#{appointment_id}',
    sk_builder=lambda entity: 'DETAILS',
    sk_lookup_builder=lambda: 'DETAILS',
    prefix_builder=lambda **kwargs: 'APPOINTMENT#',
)


class Appointment(ConfigurableEntity):
    appointment_id: str
    patient_id: str
    provider_id: str
    appointment_date: str
    appointment_time: str
    duration_minutes: int
    appointment_type: str
    reason: str
    status: str
    location: str
    notes: str = None
    insurance_authorization: str = None
    copay_amount: Decimal = None
    created_at: str
    updated_at: str
    checked_in_at: str = None
    completed_at: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return APPOINTMENT_CONFIG


# PatientAppointment Entity Configuration
PATIENTAPPOINTMENT_CONFIG = EntityConfig(
    entity_type='PATIENT_APPOINTMENT',
    pk_builder=lambda entity: f'PATIENT#{entity.patient_id}',
    pk_lookup_builder=lambda patient_id: f'PATIENT#{patient_id}',
    sk_builder=lambda entity: f'APPOINTMENT#{entity.appointment_date}#{entity.appointment_time}#{entity.appointment_id}',
    sk_lookup_builder=lambda appointment_date,
    appointment_time,
    appointment_id: f'APPOINTMENT#{appointment_date}#{appointment_time}#{appointment_id}',
    prefix_builder=lambda **kwargs: 'APPOINTMENT#',
)


class PatientAppointment(ConfigurableEntity):
    patient_id: str
    appointment_id: str
    provider_id: str
    provider_name: str
    appointment_date: str
    appointment_time: str
    appointment_type: str
    reason: str
    status: str
    location: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PATIENTAPPOINTMENT_CONFIG


# ProviderAppointment Entity Configuration
PROVIDERAPPOINTMENT_CONFIG = EntityConfig(
    entity_type='PROVIDER_APPOINTMENT',
    pk_builder=lambda entity: f'PROVIDER#{entity.provider_id}',
    pk_lookup_builder=lambda provider_id: f'PROVIDER#{provider_id}',
    sk_builder=lambda entity: f'APPOINTMENT#{entity.appointment_date}#{entity.appointment_time}#{entity.appointment_id}',
    sk_lookup_builder=lambda appointment_date,
    appointment_time,
    appointment_id: f'APPOINTMENT#{appointment_date}#{appointment_time}#{appointment_id}',
    prefix_builder=lambda **kwargs: 'APPOINTMENT#',
)


class ProviderAppointment(ConfigurableEntity):
    provider_id: str
    appointment_id: str
    patient_id: str
    patient_name: str
    appointment_date: str
    appointment_time: str
    duration_minutes: int
    appointment_type: str
    reason: str
    status: str
    location: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PROVIDERAPPOINTMENT_CONFIG


# AppointmentNote Entity Configuration
APPOINTMENTNOTE_CONFIG = EntityConfig(
    entity_type='APPOINTMENT_NOTE',
    pk_builder=lambda entity: f'APPOINTMENT#{entity.appointment_id}',
    pk_lookup_builder=lambda appointment_id: f'APPOINTMENT#{appointment_id}',
    sk_builder=lambda entity: f'NOTE#{entity.created_at}#{entity.note_id}',
    sk_lookup_builder=lambda created_at, note_id: f'NOTE#{created_at}#{note_id}',
    prefix_builder=lambda **kwargs: 'NOTE#',
)


class AppointmentNote(ConfigurableEntity):
    appointment_id: str
    note_id: str
    provider_id: str
    note_type: str
    content: str
    diagnosis_codes: list[str] = None
    procedure_codes: list[str] = None
    medications_prescribed: list[str] = None
    follow_up_required: bool
    follow_up_date: str = None
    created_at: str
    updated_at: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return APPOINTMENTNOTE_CONFIG
