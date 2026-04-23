
from core.models import User, Department
from django.contrib.auth.hashers import make_password

dept = Department.objects.get(name='General Emergency')
users_to_create = [
    ('doc1', 'doctor'), ('doc2', 'doctor'), ('doc3', 'doctor'),
    ('nurse1', 'nurse'), ('nurse2', 'nurse'), ('nurse3', 'nurse')
]

for uname, role in users_to_create:
    user, created = User.objects.get_or_create(
        username=uname,
        defaults={
            'full_name': f'{role.capitalize()} {uname[-1]}',
            'role': role,
            'department': dept,
            'is_active': True
        }
    )
    user.set_password('testpass')
    user.save()
    print(f"User {uname} ({role}) - {'Created' if created else 'Updated'}")
