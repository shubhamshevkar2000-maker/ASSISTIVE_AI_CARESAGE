from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from core.exceptions import ok, err
from core.models import Patient, Encounter
from bed_management.models import Bed, Ambulance, BedWaitingQueue, HandoffSummary
from bed_management.serializers import BedSerializer, AmbulanceSerializer, BedWaitingQueueSerializer
from core.serializers import EncounterSerializer
from core.permissions import IsAuthenticatedViaJWT

def generate_handoff_internal(enc):
    """Internal helper to generate a handoff summary based on encounter data."""
    patient = enc.patient
    doctor = enc.assigned_doctor
    triage = getattr(enc, 'triage_data', None)
    vitals = triage.vitals_json if triage else {}
    
    # Find bed
    bed = Bed.objects.filter(current_encounter=enc).first()
    bed_info = f"{bed.id} ({bed.type})" if bed else "Unassigned"
    
    # Structured Risk Detection
    risks = []
    if vitals.get("spo2", 100) < 90:
        risks.append({"type": "Low SpO2", "severity": "high", "detail": f"SpO2 at {vitals.get('spo2')}%"})
    if vitals.get("hr", 80) > 120:
        risks.append({"type": "Tachycardia", "severity": "medium", "detail": f"HR at {vitals.get('hr')} bpm"})
    if enc.priority == "critical":
        risks.append({"type": "Critical Condition", "severity": "high", "detail": "Immediate monitoring required"})
        
    if not risks:
        risks.append({"type": "Stable", "severity": "low", "detail": "Standard monitoring"})
        
    # Full System Data Summary
    summary_lines = [
        f"Patient: {patient.name}",
        f"Priority: {enc.priority.upper()}",
        f"Status: {enc.status.replace('_', ' ').capitalize()}",
        f"Assigned Bed: {bed_info}",
        f"Assigned Doctor: {doctor.full_name if doctor else 'Unassigned'}",
    ]
    
    # Queue wait time
    wait_mins = int((timezone.now() - enc.created_at).total_seconds() / 60)
    summary_lines.append(f"Wait Time: {wait_mins} mins")
    
    # Ambulance usage
    amb = Ambulance.objects.filter(current_encounter=enc).first()
    if amb:
        summary_lines.append(f"Resource: Ambulance {amb.id} utilized for transport")
        
    # Vitals string
    summary_lines.append(f"Vitals: HR {vitals.get('hr', '--')}, SpO2 {vitals.get('spo2', '--')}%, BP {vitals.get('bp_systolic', '--')}/{vitals.get('bp_diastolic', '--')}")
    
    summary_text = "\n".join(summary_lines)
    
    # Prevent Duplicate Summaries
    latest = HandoffSummary.objects.filter(encounter=enc).first()
    if latest and latest.summary_text == summary_text:
        return latest
        
    return HandoffSummary.objects.create(
        encounter=enc,
        patient=patient,
        summary_text=summary_text,
        risks_json=risks
    )

class AdmitPatientView(APIView):
    """POST /api/bed-management/admit-patient/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def post(self, request):
        encounter_id = request.data.get("encounter_id")
        if not encounter_id:
            return err("encounter_id is required.", 400)

        try:
            enc = Encounter.objects.select_related("patient").get(pk=encounter_id, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        # Map encounter priority to bed type requirement
        # critical/high -> ICU, moderate/low -> General
        bed_type = "ICU" if enc.priority in ("critical", "high") else "General"

        with transaction.atomic():
            # Try to find an available bed of the required type
            bed = Bed.objects.select_for_update().filter(type=bed_type, status="free").first()

            if bed:
                # Assign bed immediately
                bed.status = "occupied"
                bed.current_patient = enc.patient
                bed.current_encounter = enc
                bed.save()
                
                # Update encounter status to admitted
                enc.status = "admitted"
                enc.save()

                # Generate initial handoff summary
                generate_handoff_internal(enc)

                return ok({
                    "message": f"Patient admitted to {bed_type} bed {bed.id}.",
                    "bed_id": bed.id,
                    "status": "admitted"
                })
            else:
                # No bed available -> Add to queue
                enc.status = "waiting"
                enc.save()

                priority_val = 10 if enc.priority == "critical" else 0
                q_entry, created = BedWaitingQueue.objects.get_or_create(
                    encounter=enc,
                    defaults={
                        "patient": enc.patient,
                        "type": bed_type,
                        "priority_level": priority_val
                    }
                )
                
                response_data = {
                    "message": f"No {bed_type} beds available. Patient added to waiting queue.",
                    "status": "waiting",
                    "queue_position": BedWaitingQueue.objects.filter(type=bed_type, created_at__lt=q_entry.created_at).count() + 1
                }

                # If critical, trigger ambulance dispatch (only if critical)
                if enc.priority == "critical":
                    ambulance = Ambulance.objects.filter(status="available").first()
                    if ambulance:
                        ambulance.status = "busy"
                        ambulance.current_patient = enc.patient
                        ambulance.current_encounter = enc
                        ambulance.save()
                        response_data["ambulance_dispatched"] = ambulance.id
                        response_data["message"] += f" Ambulance {ambulance.id} dispatched."
                
                return ok(response_data)

class DischargePatientView(APIView):
    """POST /api/bed-management/discharge-patient/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def post(self, request):
        encounter_id = request.data.get("encounter_id")
        if not encounter_id:
            return err("encounter_id is required.", 400)

        with transaction.atomic():
            try:
                bed = Bed.objects.select_for_update().get(current_encounter_id=encounter_id)
            except Bed.DoesNotExist:
                return err("No active bed assignment found for this encounter.", 404)

            # Free any ambulance associated with this encounter
            ambulance = Ambulance.objects.filter(current_encounter_id=encounter_id).first()
            if ambulance:
                ambulance.status = "available"
                ambulance.current_patient = None
                ambulance.current_encounter = None
                ambulance.save()

            # Free the bed
            bed.status = "free"
            bed.current_patient = None
            bed.current_encounter = None
            bed.save()

            # Update encounter status
            try:
                enc = Encounter.objects.get(pk=encounter_id)
                enc.status = "completed"
                enc.save()
            except Encounter.DoesNotExist:
                pass

            # Immediately check queue for next patient
            next_in_queue = BedWaitingQueue.objects.filter(type=bed.type).first()
            if next_in_queue:
                # Auto assign to next patient
                bed.status = "occupied"
                bed.current_patient = next_in_queue.patient
                bed.current_encounter = next_in_queue.encounter
                bed.save()
                
                # Update next patient's encounter
                next_enc = next_in_queue.encounter
                next_enc.status = "admitted"
                next_enc.save()
 
                # If it was a critical patient on an ambulance, free the ambulance
                # Robustly find any ambulance linked to this encounter
                amb_new = Ambulance.objects.filter(current_encounter_id=next_enc.id).first()
                if amb_new:
                    amb_new.status = "available"
                    amb_new.current_patient = None
                    amb_new.current_encounter = None
                    amb_new.save()

                # Generate handoff summary for the newly admitted patient
                # Call after ambulance is released so it reflects in summary
                generate_handoff_internal(next_enc)

                # Remove from queue
                next_in_queue.delete()
                
                return ok({
                    "message": f"Patient discharged. Bed {bed.id} auto-assigned to next in queue ({next_enc.patient.name}).",
                    "next_patient_admitted": True
                })

            return ok({"message": f"Patient discharged. Bed {bed.id} is now free."})

class BedListView(APIView):
    """GET /api/bed-management/beds/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        beds = Bed.objects.all().order_by("id")
        return ok(BedSerializer(beds, many=True).data)

class BedDashboardView(APIView):
    """GET /api/bed-management/dashboard/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        total_beds = Bed.objects.count()
        free_beds = Bed.objects.filter(status="free").count()
        occupied_beds = total_beds - free_beds
        
        icu_total = Bed.objects.filter(type="ICU").count()
        icu_free = Bed.objects.filter(type="ICU", status="free").count()
        icu_occupied = icu_total - icu_free
        
        gen_total = Bed.objects.filter(type="General").count()
        gen_free = Bed.objects.filter(type="General", status="free").count()
        gen_occupied = gen_total - gen_free
        
        waiting_icu = BedWaitingQueue.objects.filter(type="ICU").count()
        waiting_gen = BedWaitingQueue.objects.filter(type="General").count()
        
        amb_available = Ambulance.objects.filter(status="available").count()
        amb_total = Ambulance.objects.count()

        return ok({
            "total_beds": total_beds,
            "free_beds": free_beds,
            "occupied_beds": occupied_beds,
            "icu": {"total": icu_total, "free": icu_free, "occupied": icu_occupied},
            "general": {"total": gen_total, "free": gen_free, "occupied": gen_occupied},
            "waiting": {"icu": waiting_icu, "general": waiting_gen, "total": waiting_icu + waiting_gen},
            "ambulance": {"available": amb_available, "total": amb_total}
        })

class QueueListView(APIView):
    """GET /api/bed-management/queue/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        queue = BedWaitingQueue.objects.all()
        return ok(BedWaitingQueueSerializer(queue, many=True).data)

class AmbulanceStatusView(APIView):
    """GET /api/bed-management/ambulance-status/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        ambs = Ambulance.objects.all()
        return ok(AmbulanceSerializer(ambs, many=True).data)

class SeedBedsView(APIView):
    """POST /api/bed-management/seed/ — Dev helper to create some beds/ambs."""
    permission_classes = [IsAuthenticatedViaJWT]

    def post(self, request):
        # Create 5 ICU beds
        for i in range(1, 6):
            Bed.objects.get_or_create(id=f"ICU-{i:02d}", defaults={"type": "ICU"})
        # Create 10 General beds
        for i in range(1, 11):
            Bed.objects.get_or_create(id=f"GEN-{i:02d}", defaults={"type": "General"})
        # Create 3 Ambulances
        for i in range(1, 4):
            Ambulance.objects.get_or_create(id=f"AMB-{i:02d}")
        
        return ok("Beds and Ambulances seeded.")
class GenerateHandoffView(APIView):
    """
    POST /api/bed-management/generate-handoff/ -> Trigger fresh generation
    GET /api/bed-management/generate-handoff/?encounter_id=... -> Fetch history
    """
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        encounter_id = request.query_params.get("encounter_id")
        if not encounter_id:
            return err("encounter_id is required.", 400)
            
        summaries = HandoffSummary.objects.filter(encounter_id=encounter_id)
        data = [{
            "id": s.id,
            "summary_text": s.summary_text,
            "risks_json": s.risks_json,
            "created_at": s.created_at
        } for s in summaries]
        
        return ok(data)

    def post(self, request):
        encounter_id = request.data.get("encounter_id")
        if not encounter_id:
            return err("encounter_id is required.", 400)
            
        try:
            enc = Encounter.objects.select_related("patient", "assigned_doctor", "triage_data").get(pk=encounter_id)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)
            
        summary = generate_handoff_internal(enc)
        return ok({
            "id": summary.id,
            "summary_text": summary.summary_text,
            "risks_json": summary.risks_json,
            "created_at": summary.created_at
        })

class HospitalStatusView(APIView):
    """
    GET /api/bed-management/hospital-status/
    Atomic snapshot of all hospital resources.
    """
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        with transaction.atomic():
            # 1. Beds
            beds = Bed.objects.all().order_by("id")
            
            # 2. Counts
            icu_free = Bed.objects.filter(type="ICU", status="free").count()
            general_free = Bed.objects.filter(type="General", status="free").count()
            
            # 3. Queues
            icu_queue = BedWaitingQueue.objects.filter(type="ICU").select_related("encounter__patient")
            gen_queue = BedWaitingQueue.objects.filter(type="General").select_related("encounter__patient")
            
            # 4. Ambulances
            ambulances = Ambulance.objects.all().select_related("current_encounter__patient")
            
            # 5. Active Patients (Waiting, Assigned, Admitted, In Progress, Escalated)
            active_encs = Encounter.objects.filter(
                status__in=["waiting", "assigned", "admitted", "in_progress", "escalated"]
            ).select_related("patient", "assigned_doctor").order_by("-risk_score", "-created_at")

            return ok({
                "counts": {
                    "icu_free": icu_free,
                    "general_free": general_free
                },
                "beds": BedSerializer(beds, many=True).data,
                "queue": {
                    "icu": BedWaitingQueueSerializer(icu_queue, many=True).data,
                    "general": BedWaitingQueueSerializer(gen_queue, many=True).data
                },
                "ambulances": AmbulanceSerializer(ambulances, many=True).data,
                "patients": EncounterSerializer(active_encs, many=True).data
            })
