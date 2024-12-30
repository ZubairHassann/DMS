from django.urls import include, path
from rest_framework import routers
from .views import  RiderViewSet, CustomerViewSet, CustomerWalletView, CompanyWalletView, RiderWalletView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = routers.DefaultRouter()
# router.register(r'Admin', AdminRegisterRiderView,
#                 basename='Admin')
# router.register(r'Customer-register', CustomerRegisterViewSet,
#                 basename='Customer-register')
# router.register(r'customer/signup', CustomerSignupView.as_view(),
#                 basename='Customer/signup')
# router.register(r'rider/signup', RiderSignupView.as_view(),
#                 basename='rider/signup')


router.register(r'rider', RiderViewSet, basename='rider')
router.register(r'customer', CustomerViewSet, basename='Customer')


urlpatterns = [
    path('', include(router.urls)),
    path("Comapany-Wallet", CompanyWalletView.as_view(), name='comapany-wallet'),
    path("Customer-Wallet", CustomerWalletView.as_view(), name='customer-wallet'),
    path("Rider-Wallet", RiderWalletView.as_view(), name='rider-wallet'),
]
