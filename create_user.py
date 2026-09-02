import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()

from django.contrib.auth.models import User
from siniestros.models import UsuarioCustom

try:
    user, created = User.objects.get_or_create(username='testadmin', email='test@example.com')
    if created:
        user.set_password('testpass')
        user.save()
    
    UsuarioCustom.objects.get_or_create(username='testadmin', defaults={'rol': 'ADMIN', 'factor_ajuste': 1.0})
    print("User testadmin created successfully")
except Exception as e:
    print(f"Error: {e}")
