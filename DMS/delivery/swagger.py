from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import serializers

class PermissionSerializer(serializers.Serializer):
    user_permissions = serializers.CharField()
    can_create = serializers.BooleanField()
    can_read = serializers.BooleanField()
    can_update = serializers.BooleanField()
    can_delete = serializers.BooleanField()

class GetPermissionSerializer(serializers.Serializer):
    user_group = serializers.IntegerField()
    permissions = serializers.ListField(child=PermissionSerializer())

    class Meta:
        example = {
            "user_group": 0,
            "permissions": [
                {
                    "user_permissions": "Dashboard",
                    "can_create": True,
                    "can_read": True,
                    "can_update": True,
                    "can_delete": True
                }
            ]
        }


urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]