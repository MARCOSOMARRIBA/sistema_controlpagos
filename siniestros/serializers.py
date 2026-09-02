from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Aseguradora, Siniestro, CorteMensual, UsuarioCustom

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        try:
            custom_user = UsuarioCustom.objects.get(username=user.username)
            token['rol'] = custom_user.rol
        except UsuarioCustom.DoesNotExist:
            token['rol'] = None
        return token


class AseguradoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aseguradora
        fields = '__all__'

class SiniestroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Siniestro
        fields = '__all__'

class CorteMensualSerializer(serializers.ModelSerializer):
    ajustador_nombre = serializers.CharField(source='id_ajustador.username', read_only=True)
    
    class Meta:
        model = CorteMensual
        fields = '__all__'
