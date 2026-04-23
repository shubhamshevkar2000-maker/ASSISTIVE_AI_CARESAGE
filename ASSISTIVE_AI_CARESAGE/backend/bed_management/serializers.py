from rest_framework import serializers
from bed_management.models import Bed, Ambulance, BedWaitingQueue
from core.serializers import PatientSerializer, EncounterSerializer

class BedSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="current_patient", read_only=True)
    encounter_detail = EncounterSerializer(source="current_encounter", read_only=True)

    class Meta:
        model = Bed
        fields = ["id", "type", "status", "current_patient", "patient_detail", "current_encounter", "encounter_detail"]

class AmbulanceSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="current_patient", read_only=True)

    class Meta:
        model = Ambulance
        fields = ["id", "status", "current_patient", "patient_detail"]

class BedWaitingQueueSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="patient", read_only=True)

    class Meta:
        model = BedWaitingQueue
        fields = ["id", "patient", "patient_detail", "encounter", "type", "priority_level", "created_at"]
