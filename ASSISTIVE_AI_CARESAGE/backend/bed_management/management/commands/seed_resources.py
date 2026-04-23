from django.core.management.base import BaseCommand
from bed_management.models import Bed, Ambulance

class Command(BaseCommand):
    help = "Seeds the hospital with beds and ambulances."

    def handle(self, *args, **options):
        # 2 ICU beds
        for i in range(1, 3):
            Bed.objects.get_or_create(
                id=f"ICU-{i:02d}",
                defaults={"type": "ICU", "status": "free"}
            )
        
        # 2 General beds
        for i in range(1, 3):
            Bed.objects.get_or_create(
                id=f"GEN-{i:02d}",
                defaults={"type": "General", "status": "free"}
            )
            
        # 2 Ambulances
        for i in range(1, 3):
            Ambulance.objects.get_or_create(
                id=f"AMB-{i:02d}",
                defaults={"status": "available"}
            )
            
        self.stdout.write(self.style.SUCCESS("Successfully seeded beds and ambulances."))
