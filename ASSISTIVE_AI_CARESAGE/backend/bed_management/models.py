import uuid
from django.db import models
from core.models import Patient, Encounter

class Bed(models.Model):
    TYPE_CHOICES = [("ICU", "ICU"), ("General", "General")]
    STATUS_CHOICES = [("free", "Free"), ("occupied", "Occupied")]

    id = models.CharField(primary_key=True, max_length=10) # e.g. B-01
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="free")
    current_patient = models.OneToOneField(
        Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_bed"
    )
    current_encounter = models.OneToOneField(
        Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name="bed_link"
    )

    def __str__(self):
        return f"{self.id} ({self.type}) - {self.status}"

class Ambulance(models.Model):
    STATUS_CHOICES = [("available", "Available"), ("busy", "Busy")]
    
    id = models.CharField(primary_key=True, max_length=10) # e.g. AMB-01
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="available")
    current_patient = models.ForeignKey(
        Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name="ambulance_dispatches"
    )
    current_encounter = models.ForeignKey(
        Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name="ambulance_links"
    )

    def __str__(self):
        return f"Ambulance {self.id} - {self.status}"

class BedWaitingQueue(models.Model):
    TYPE_CHOICES = [("ICU", "ICU"), ("General", "General")]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    priority_level = models.IntegerField(default=0) # Higher = more urgent
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-priority_level", "created_at"] # FIFO within priority

    def __str__(self):
        return f"Queue: {self.patient.name} for {self.type}"

class HandoffSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="handoff_summaries")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    summary_text = models.TextField()
    risks_json = models.JSONField(default=list) # List of {type, severity}
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "handoff_summaries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Handoff for {self.patient.name} at {self.created_at}"
