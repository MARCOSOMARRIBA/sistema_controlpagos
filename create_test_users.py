import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()

from django.contrib.auth.models import User
from siniestros.models import UsuarioCustom

def create_users():
    # 1. Crear Administrador
    admin_user, created = User.objects.get_or_create(username='admin')
    if created:
        admin_user.set_password('admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        print("✅ Credencial ADMIN creada: Usuario 'admin' / Contraseña 'admin123'")
    else:
        # Forzar password si ya existía
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ Credencial ADMIN actualizada: Usuario 'admin' / Contraseña 'admin123'")

    UsuarioCustom.objects.update_or_create(
        username='admin',
        defaults={'rol': 'ADMIN', 'factor_ajuste': 1.0}
    )

    # 2. Crear Ajustador de Prueba
    ajustador_user, created = User.objects.get_or_create(username='ajustador1')
    if created:
        ajustador_user.set_password('ajustador123')
        ajustador_user.save()
        print("✅ Credencial AJUSTADOR creada: Usuario 'ajustador1' / Contraseña 'ajustador123'")
    else:
        # Forzar password si ya existía
        ajustador_user.set_password('ajustador123')
        ajustador_user.save()
        print("✅ Credencial AJUSTADOR actualizada: Usuario 'ajustador1' / Contraseña 'ajustador123'")

    UsuarioCustom.objects.update_or_create(
        username='ajustador1',
        defaults={'rol': 'AJUSTADOR', 'factor_ajuste': 1.0}
    )

if __name__ == '__main__':
    create_users()
