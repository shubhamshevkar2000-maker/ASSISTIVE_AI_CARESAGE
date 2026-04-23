from django.urls import path
from bed_management.views import (
    AdmitPatientView, DischargePatientView, BedListView,
    BedDashboardView, QueueListView, AmbulanceStatusView,
    SeedBedsView, GenerateHandoffView, HospitalStatusView
)

urlpatterns = [
    path("bed-management/admit-patient/", AdmitPatientView.as_view()),
    path("bed-management/discharge-patient/", DischargePatientView.as_view()),
    path("bed-management/beds/", BedListView.as_view()),
    path("bed-management/dashboard/", BedDashboardView.as_view()),
    path("bed-management/queue/", QueueListView.as_view()),
    path("bed-management/ambulance-status/", AmbulanceStatusView.as_view()),
    path("bed-management/seed/", SeedBedsView.as_view()),
    path("bed-management/generate-handoff/", GenerateHandoffView.as_view(), name="generate-handoff"),
    path("bed-management/hospital-status/", HospitalStatusView.as_view(), name="hospital-status"),
]
