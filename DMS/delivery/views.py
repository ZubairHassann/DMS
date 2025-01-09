from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import *
from rest_framework.authtoken.models import Token
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status, viewsets
from .serializers import LoginSerializer, RiderSerializer, CustomerSerializer, CustomerWalletSerializer, RiderWalletSerializer, CompanyWalletSerializer
from .models import Rider, Customer, CustomerWallet, CompanyWallet, RiderWallet, Customer
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import RiderSerializer
import requests
from django.http import JsonResponse


class GetRiderLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            print(f"Logged-in user: {request.user}")
            rider = request.user.rider
            data = {
                "latitude": rider.latitude,
                "longitude": rider.longitude,
                "address": rider.address,
            }
            return Response(data)
        except AttributeError:
            print("Rider object not found for the logged-in user.")
            return Response({"error": "Rider details not found for the logged-in user."}, status=404)

    def post(self, request):
        """Update the location of the logged-in rider."""
        try:
            rider = request.user.rider
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')

            if latitude is None or longitude is None:
                return Response(
                    {"error": "Latitude and longitude are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            address = self.get_address_from_coordinates(latitude, longitude)
            rider.latitude = latitude
            rider.longitude = longitude
            rider.address = address
            rider.save()

            return Response(
                {"success": "Location updated successfully."},
                status=status.HTTP_200_OK
            )
        except AttributeError:
            return Response({"error": "Rider details not found for the logged-in user."}, status=status.HTTP_404_NOT_FOUND)

    def get_address_from_coordinates(self, latitude, longitude):
        """Fetch address from latitude and longitude using LocationIQ API."""
        try:
            api_url = "https://us1.locationiq.com/v1/reverse.php"
            api_key = "pk.8dcc4459a73a29fa7b1d8c7f011d1d7f"
            params = {
                "key": api_key,
                "lat": latitude,
                "lon": longitude,
                "format": "json",
            }
            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("display_name", "Address not found")
            return "Address not found"
        except Exception as e:
            print(f"Error: {e}")
            return "Error fetching address"


def get_rider_location(request):
    latitude = 24.8607
    longitude = 67.0011
    if latitude and longitude:
        address = GetRiderLocationView().get_address_from_coordinates(latitude, longitude)
        return JsonResponse({"address": address})
    return JsonResponse({"error": "Latitude and Longitude are required"}, status=400)


class GetCustomerLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get the location of the logged-in customer."""
        try:
            customer = request.user.customer_profile
            if not customer:
                return Response({"error": "No customer profile found for the logged-in user."}, status=404)
            data = {
                "latitude": customer.address_latitude,
                "longitude": customer.address_longitude,
                "address": customer.address,
            }
            return Response(data)
        except AttributeError:
            return Response({"error": "Customer details not found for the logged-in user."}, status=404)

    def post(self, request):
        """Update the location of the logged-in customer."""
        try:
            customer = request.user.customer_profile
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            if latitude is None or longitude is None:
                return Response(
                    {"error": "Latitude and longitude are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            address = self.get_address_from_coordinates(latitude, longitude)
            customer.address_latitude = latitude
            customer.address_longitude = longitude
            customer.address = address
            customer.save()

            return Response(
                {"success": "Location updated successfully."},
                status=status.HTTP_200_OK
            )
        except AttributeError:
            return Response({"error": "Customer details not found for the logged-in user."}, status=status.HTTP_404_NOT_FOUND)

    def get_address_from_coordinates(self, latitude, longitude):
        """Fetch address from latitude and longitude using LocationIQ API."""
        try:
            api_url = "https://us1.locationiq.com/v1/reverse.php"
            api_key = "pk.8dcc4459a73a29fa7b1d8c7f011d1d7f"
            params = {
                "key": api_key,
                "lat": latitude,
                "lon": longitude,
                "format": "json",
            }

            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("display_name", "Address not found")
            return "Address not found"
        except Exception as e:
            print(f"Error: {e}")
            return "Error fetching address"


def get_location(request):
    """Fetch address using latitude and longitude from the request."""
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')

    if latitude and longitude:
        address = GetCustomerLocationView().get_address_from_coordinates(latitude, longitude)
        return JsonResponse({"address": address})
    return JsonResponse({"error": "Latitude and Longitude are required"}, status=400)


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
        try:
            rider = Rider.objects.get(user=request.user)
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
            customer = Customer.objects.get(user=request.user)
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
        wallet = CompanyWallet.objects.first()
        serializer = CompanyWalletSerializer(wallet)
        return Response(serializer.data)
