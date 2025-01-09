from rest_framework import routers
from .order_views import *

from django.urls import include, path
router = routers.DefaultRouter()
urlpatterns = [
    path('', include(router.urls)),
    path("ManualOrderCreate", CreateManualOrder.as_view(), name='ManualOrderCreate'
         ),
    path("OrderListView", AdminOrderListView.as_view(), name='OrderListView'),
    path("RiderOrderListView", RiderOrderListView.as_view(),
         name='RiderOrderListView'),
    path("complete_order/<int:order_id>",
         complete_order, name='complete_order'),
    path("OrderListView", ManualOrderListView.as_view(), name='OrderList'),
    path("OrderDetailView/<int:order_id>",
         OrderDetailView.as_view(), name='OrderList')
]
