from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import *
from rest_framework.authtoken.models import Token
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status, viewsets
from .serializers import LoginSerializer, RiderSerializer, CustomerSerializer, CustomerWalletSerializer, RiderWalletSerializer, CompanyWalletSerializer
from .models import CustomUser, Rider, Customer, CustomerWallet, CompanyWallet, RiderWallet
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import RiderSerializer

# class AdminRegisterRiderView(viewsets.ModelViewSet):
#     queryset = CustomUser.objects.all()
#     permission_classes = [permissions.IsAuthenticated]
#     # authentication_classes = [TokenAuthentication, SessionAuthentication]

#     def post(self, request):
#         serializer = RiderRegistrationSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "Rider account created successfully."}, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def create(self, request):
#         serializer = RiderRegistrationSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "User account created successfully."}, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class CustomerRegisterViewSet(viewsets.ModelViewSet):
#     queryset = CustomUser.objects.all()
#     serializer_class = CustomerRegistrationSerializer

#     def create(self, request):
#         serializer = CustomerRegistrationSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "User account created successfully."}, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# def update(self, request, pk):
#     user = self.get_object()
#     serializer = CustomerRegistrationSerializer(user, data=request.data)
#     if serializer.is_valid():
#         serializer.save()
#         return Response({"message": "User account updated successfully."}, status=status.HTTP_200_OK)
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class UpdateRiderLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        rider = Rider.objects.get(user=request.user)
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude or not longitude:
            return Response({"error": "Latitude and Longitude are required."}, status=status.HTTP_400_BAD_REQUEST)

        rider.current_latitude = latitude
        rider.current_longitude = longitude
        rider.save()

        return Response({"message": "Location updated successfully."})


class GetCustomerLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id):
        from django.shortcuts import get_object_or_404

        customer = get_object_or_404(Customer, id=customer_id)
        data = {
            "latitude": customer.latitude,
            "longitude": customer.longitude,
            "address": customer.address,
        }
        return Response(data)


class LoginViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            token, created = Token.objects.update_or_create(user=user)

            return Response({
                'access': access_token,
                'refresh': str(refresh),
                'token': token.key
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RiderViewSet(viewsets.ModelViewSet):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RiderWalletView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get(self, request):
        # Assuming the authenticated user is a rider
        try:
            # Get the Rider object linked to the authenticated user
            rider = Rider.objects.get(user=request.user)
            # Query wallet using the Rider instance
            wallet = RiderWallet.objects.get(rider=rider)
            serializer = RiderWalletSerializer(wallet)
            return Response(serializer.data)
        except Rider.DoesNotExist:
            return Response({"message": "Rider profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except RiderWallet.DoesNotExist:
            return Response({"message": "Rider wallet not found."}, status=status.HTTP_404_NOT_FOUND)


class CustomerWalletView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            # Get the Customer object linked to the authenticated user
            customer = Customer.objects.get(user=request.user)
            # Query wallet using the Customer instance
            wallet = CustomerWallet.objects.get(customer=customer)
            serializer = CustomerWalletSerializer(wallet)
            return Response(serializer.data)
        except Customer.DoesNotExist:
            return Response({"message": "Customer profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except CustomerWallet.DoesNotExist:
            return Response({"message": "Customer wallet not found."}, status=status.HTTP_404_NOT_FOUND)


class CompanyWalletView(APIView):
    permission_classes = [IsSuperUser]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get(self, request):
        wallet = CompanyWallet.objects.first()  # Assuming a single wallet instance
        serializer = CompanyWalletSerializer(wallet)
        return Response(serializer.data)
