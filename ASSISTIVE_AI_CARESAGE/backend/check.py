
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acuvera.settings')
django.setup()
from core.models import User, Department
print('Departments:')
for d in Department.objects.all():
    print(f'- {d.name} ({d.id})')
print('\nUsers:')
for u in User.objects.all():
    dept_name = u.department.name if u.department else "None"
    print(f'- {u.username}: role={u.role}, dept={dept_name}, active={u.is_active}')
