from django.urls import include, path, re_path
from rest_framework import routers
from .auth_views import CustomerSignupView, RiderSignupView, LogoutView, ChangePasswordView, ForgotPasswordView, ResetPasswordView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.generic import TemplateView
router = routers.DefaultRouter()


urlpatterns = [

    path("logout/", LogoutView.as_view(), name="logout"),
    path('customer-signup/', CustomerSignupView.as_view(), name='customer-signup'),
    path('rider-signup/', RiderSignupView.as_view(), name='rider-signup'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    re_path(r"^docs/(?P<path>.*)$",
            TemplateView.as_view(template_name="docs.html")),
    path('', include(router.urls)),
]
