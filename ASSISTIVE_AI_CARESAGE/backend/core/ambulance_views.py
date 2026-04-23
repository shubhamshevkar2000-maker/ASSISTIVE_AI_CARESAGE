"""
Ambulance Pre-Triage system.
POST /api/encounters/ambulance/   — Paramedic pre-registers incoming patient
GET  /api/encounters/incoming/    — Nurse fetches all incoming ambulances

Secured with X-Ambulance-Key: <AMBULANCE_TOKEN> header.
"""
import logging
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.models import Patient, Encounter, Department
from core.serializers import EncounterSerializer

logger = logging.getLogger("acuvera.ambulance")

AMBULANCE_TOKEN = getattr(settings, "AMBULANCE_TOKEN", "acuvera-demo-ambulance")


def _check_ambulance_auth(request):
    key = request.headers.get("X-Ambulance-Key", "")
    return key == AMBULANCE_TOKEN


class AmbulancePreRegisterView(APIView):
    """POST /api/encounters/ambulance/ — Paramedic submits patient en-route."""
    permission_classes = []  # Custom token auth below

    def post(self, request):
        if not _check_ambulance_auth(request):
            return err(
                "Ambulance authentication required. Pass X-Ambulance-Key header.",
                401
            )

        data = request.data
        eta_minutes = int(data.get("eta_minutes", 5))
        if eta_minutes < 1 or eta_minutes > 120:
            return err("eta_minutes must be between 1 and 120.", 400)

        dept_id = data.get("department_id")
        if dept_id:
            dept = Department.objects.filter(id=dept_id, is_active=True).first()
        else:
            dept = Department.objects.filter(is_active=True).first()
            
        if not dept:
            return err("No active departments available to receive ambulances.", 400)

        # Create patient — name optional (may be unknown in emergency)
        patient = Patient.objects.create(
            name=data.get("patient_name") or "Unknown (Ambulance)",
            age=data.get("age"),
            gender=data.get("gender", "unknown"),
        )

        # Create encounter in 'incoming' status
        enc = Encounter.objects.create(
            patient=patient,
            department=dept,
            status="incoming",
            eta_minutes=eta_minutes,
            eta_set_at=timezone.now(),
            notes=data.get("chief_complaint", "Ambulance pre-registration"),
            triage_stage="rapid",
        )

        # Run preliminary triage if vitals provided
        vitals = data.get("vitals", {})
        symptoms = data.get("symptoms", [])
        if vitals or symptoms:
            try:
                from triage.engine import compute_triage
                compute_triage(
                    encounter_id=str(enc.id),
                    vitals=vitals,
                    symptoms=symptoms,
                    red_flags=data.get("red_flags", {}),
                    patient_age=patient.age,
                )
                logger.info("Pre-triage complete for ambulance encounter %s", enc.id)
            except Exception as e:
                logger.warning("Ambulance pre-triage failed: %s", e)

        logger.info(
            "Ambulance pre-registration: encounter=%s eta=%dmin patient=%s",
            enc.id, eta_minutes, patient.name
        )

        return ok({
            "encounter_id": str(enc.id),
            "patient_name": patient.name,
            "eta_minutes": eta_minutes,
            "eta_set_at": enc.eta_set_at.isoformat(),
            "department": dept.name,
            "message": f"Patient pre-registered. Preparing bay. ETA: {eta_minutes} minutes.",
        }, status=201)


class IncomingAmbulanceListView(APIView):
    """GET /api/encounters/incoming/ — Nurse sees all incoming ambulances with ETA countdown."""
    permission_classes = []  # Accessible to authenticated users — use IsAuthenticatedViaJWT if needed

    def get(self, request):
        from core.permissions import IsAuthenticatedViaJWT
        # Lightweight auth check
        perm = IsAuthenticatedViaJWT()
        if not perm.has_permission(request, self):
            return err("Authentication required.", 401)

        now = timezone.now()
        incoming = Encounter.objects.filter(
            status="incoming", is_deleted=False
        ).select_related("patient", "department", "triage_data").order_by("eta_set_at")

        serializer = EncounterSerializer(incoming, many=True)
        return ok(serializer.data)
