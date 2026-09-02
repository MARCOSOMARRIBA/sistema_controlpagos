from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView, TokenBlacklistView
from siniestros.serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # BUG-001: endpoint para invalidar el refresh token en el servidor al hacer logout
    path('api/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/', include('siniestros.urls')),
    path('api/facturacion/', include('facturacion.urls')),
]

