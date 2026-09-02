import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()

from django.contrib.auth.models import User
from siniestros.models import UsuarioCustom

user, created = User.objects.get_or_create(username='testajustador', email='test2@example.com')
if created:
    user.set_password('testpass')
    user.save()

UsuarioCustom.objects.get_or_create(username='testajustador', defaults={'rol': 'AJUSTADOR', 'factor_ajuste': 1.0})
print("User testajustador created successfully")
