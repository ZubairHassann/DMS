from rest_framework import routers
from .order_views import *
from django.urls import include, path
router = routers.DefaultRouter()
router.register(r'Manual-Order', ManualOrderViewSet, basename='Manual-Order'),
urlpatterns = [
    path('', include(router.urls)),
    path("ManualOrderCreate", CreateManualOrder.as_view(), name='ManualOrderCreate'
         ),
    path("OrderListView", AdminOrderListView.as_view(), name='OrderListView'),
    path("RiderOrderListView", RiderOrderListView.as_view(),
         name='RiderOrderListView')
]
