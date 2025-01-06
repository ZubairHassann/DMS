from rest_framework import status, generics
from delivery.serializers import (
    RiderSignupSerializer,
    CustomerSignupSerializer,
    CustomerWalletSerializer,
)
from delivery.models import CustomerWallet,Customer
from .auth_serializers import (
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from delivery.permissions import IsSuperUser

User = get_user_model()


class RiderSignupView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        serializer = RiderSignupSerializer(data=request.data)
        if serializer.is_valid():
            rider = serializer.save()

            if hasattr(rider, "rider_wallet"):
                wallet_status = "Wallet created successfully."
            else:
                wallet_status = "Failed to create wallet."

            return Response(
                {
                    "message": "Rider account created successfully",
                    "rider_id": rider.id,
                    "wallet_status": wallet_status,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerSignupView(generics.CreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSignupSerializer

    def post(self, request):
        serializer = CustomerSignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Customer account created successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerWalletView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            customer = Customer.objects.get(user=request.user)
            wallet = CustomerWallet.objects.get(customer=customer)
            serializer = CustomerWalletSerializer(wallet)
            return Response(serializer.data)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except CustomerWallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": "Invalid token or logout failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password changed successfully."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"https://smms-app-ec48c9-7ad1bc-65-108-245-140.traefik.me/auth/forgot-password?uid={
                uid}&token={token}"

            send_mail(
                "Password Reset Request",
                f"Click the link to reset your password: {reset_link}",
                "no-reply@example.com",
                [email],
            )
            return Response(
                {"message": "Password reset link sent."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password has been reset successfully."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
