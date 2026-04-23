
from core.models import User, Department
print('Departments:')
for d in Department.objects.all():
    print(f'- {d.name} ({d.id})')
print('\nUsers:')
for u in User.objects.all():
    print(f'- {u.username}: role={u.role}, dept={u.department.name if u.department else "None"}, active={u.is_active}')
