import os
import sys
import django
from django.utils import timezone

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acuvera.settings')
django.setup()

from core.models import Patient, Encounter, User, TriageData, Department
from bed_management.models import Bed, HandoffSummary
from bed_management.views import generate_handoff_internal

def verify_handoff():
    print("--- Starting Handoff Verification ---")
    
    # 1. Setup Patient and Encounter
    patient, _ = Patient.objects.get_or_create(name="Handoff Test Patient", defaults={"age": 45, "gender": "M"})
    dept, _ = Department.objects.get_or_create(name="Emergency")
    enc = Encounter.objects.create(
        patient=patient,
        department=dept,
        priority="critical",
        status="in_progress"
    )
    
    # 2. Add Vitals
    vitals_json = {"hr": 130, "spo2": 85, "bp_systolic": 90, "bp_diastolic": 60}
    TriageData.objects.create(encounter=enc, vitals_json=vitals_json)
    
    # 3. Assign Bed
    bed, _ = Bed.objects.get_or_create(id="TEST-01", defaults={"type": "ICU", "status": "free"})
    bed.status = "occupied"
    bed.current_patient = patient
    bed.current_encounter = enc
    bed.save()
    
    print(f"Created patient {patient.name}, encounter {enc.id}, vitals SpO2: {vitals_json['spo2']}")
    
    # 4. Generate Handoff
    print("Generating handoff summary...")
    summary = generate_handoff_internal(enc)
    
    # 5. Verify Results
    print(f"Summary ID: {summary.id}")
    print(f"Summary Text:\n{summary.summary_text}")
    print(f"Risks Detected: {summary.risks_json}")
    
    assert "Low SpO2" in str(summary.risks_json), "Low SpO2 risk not detected!"
    assert "Tachycardia" in str(summary.risks_json), "Tachycardia risk not detected!"
    assert "CRITICAL" in summary.summary_text, "Priority not reflected in summary!"
    
    # 6. Test Duplicate Prevention
    print("Attempting to generate duplicate summary...")
    summary2 = generate_handoff_internal(enc)
    assert summary.id == summary2.id, "Duplicate summary created!"
    print("Duplicate prevention verified (IDs match).")
    
    # 7. Test History retrieval via model
    history = HandoffSummary.objects.filter(encounter=enc)
    assert history.count() == 1, "History count incorrect!"
    
    print("--- Handoff Verification Successful! ---")

if __name__ == "__main__":
    verify_handoff()
