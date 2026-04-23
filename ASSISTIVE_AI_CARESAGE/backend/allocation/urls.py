from django.urls import path
from allocation.views import (
    SuggestDoctorView, ConfirmAllocationView, RespondAllocationView, ReferDoctorView,
    CandidatesListView, AcceptCaseView
)


urlpatterns = [
    path("allocation/suggest/<uuid:encounter_id>/", SuggestDoctorView.as_view()),
    path("allocation/candidates/<uuid:encounter_id>/", CandidatesListView.as_view()),
    path("allocation/confirm/", ConfirmAllocationView.as_view()),
    path("allocation/respond/", RespondAllocationView.as_view()),
    path("allocation/refer/", ReferDoctorView.as_view()),
    path("doctor/accept-case/", AcceptCaseView.as_view()),
]

