
from core.models import User, Department
from django.contrib.auth.hashers import make_password

def setup():
    depts = list(Department.objects.all())
    if not depts:
        print("No departments found. Seed data first.")
        return
        
    for dept in depts:
        # Create 2 doctors and 1 nurse per department
        users_to_create = [
            (f'doc_{dept.name.lower().replace(" ", "_")}_1', 'doctor'),
            (f'doc_{dept.name.lower().replace(" ", "_")}_2', 'doctor'),
            (f'nurse_{dept.name.lower().replace(" ", "_")}_1', 'nurse'),
        ]
        
        for uname, role in users_to_create:
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'full_name': f'{role.capitalize()} {uname.split("_")[-1]}',
                    'role': role,
                    'department': dept,
                    'is_active': True
                }
            )
            user.set_password('testpass')
            user.save()
            print(f"User {uname} ({role}) in {dept.name} - {'Created' if created else 'Updated'}")

if __name__ == "__main__":
    setup()

