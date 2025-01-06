from django.urls import include, path
from rest_framework import routers
from .views import get_location, RiderViewSet, CustomerViewSet, CustomerWalletView, CompanyWalletView, RiderWalletView, GetRiderLocationView, GetCustomerLocationView

router = routers.DefaultRouter()
router.register(r'riderProfile', RiderViewSet, basename='rider')
router.register(r'customerProfile', CustomerViewSet, basename='Customer')


urlpatterns = [
    path('', include(router.urls)),
    path("Comapany-Wallet", CompanyWalletView.as_view(), name='comapany-wallet'),
    path("Customer-Wallet", CustomerWalletView.as_view(), name='customer-wallet'),
    path("Rider-Wallet", RiderWalletView.as_view(), name='rider-wallet'),
    path('CustomerLocations/',
         GetCustomerLocationView.as_view(), name='customer_location'),
    path("RiderLocation", GetRiderLocationView.as_view(), name='RiderLocation'),
    path("get-location/", get_location, name="get_location")
]
