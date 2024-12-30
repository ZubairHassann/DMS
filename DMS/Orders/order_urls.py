from rest_framework import routers
from .order_views import *
from django.urls import include, path
router = routers.DefaultRouter()
router.register(r'Manual-Order', ManualOrderViewSet, basename='Manual-Order'),
urlpatterns = [
    path('', include(router.urls)),
]