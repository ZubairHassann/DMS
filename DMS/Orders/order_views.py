from delivery.models import *
from rest_framework import viewsets, status
from .order_serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from delivery.permissions import IsSuperUser
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError, NotFound
from delivery.views import GetCustomerLocationView
from django.db import transaction
import requests


class ManualOrderViewSet(viewsets.ModelViewSet):
    queryset = ManualOrder.objects.all()
    serializer_class = ManualOrderSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def list(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_superuser:
            completed_orders = ManualOrder.objects.filter(status='delivered')
            active_orders = ManualOrder.objects.exclude(
                Q(status='delivered') | Q(rider__isnull=True))
            unassigned_orders = ManualOrder.objects.filter(
                Q(rider=user) | Q(rider__isnull=True))
        elif user.is_staff:
            completed_orders = ManualOrder.objects.filter(
                rider=user, status='delivered')
            active_orders = ManualOrder.objects.filter(
                rider=user).exclude(status='delivered')
            unassigned_orders = None
        else:
            completed_orders = ManualOrder.objects.filter(
                user=user, status='delivered')
            active_orders = ManualOrder.objects.filter(
                user=user).exclude(status='delivered')
            unassigned_orders = None
        completed_orders = self.get_serializer(
            completed_orders, many=True).data
        active_orders = self.get_serializer(active_orders, many=True).data
        unassigned_orders = self.get_serializer(
            unassigned_orders, many=True).data if unassigned_orders else []

        return Response({
            "completed_orders": completed_orders,
            "active_orders": active_orders,
            'unassigned_orders': unassigned_orders,
        })

    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_superuser:
            order_address = serializer.validated_data.get('address')

            rider = User.objects.filter(
                Q(is_superuser=False) & Q(is_staff=True))
            rider = rider.filter(profile__address=order_address).first()

            if rider:
                serializer.save(user=user, rider=rider)
            else:
                rider = User.objects.filter(
                    Q(is_superuser=True) & Q(is_staff=False)).first()
                if rider:
                    serializer.save(user=user, rider=rider)
                else:
                    return Response(
                        {'detail': 'No available riders for the specified address, Order has been shifted to unassigned orders'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        else:
            serializer.save(user=user)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance

        if user.is_staff and not user.is_superuser:

            serializer.save(
                total_price=serializer.validated_data.get(
                    'total_price', instance.total_price),
                status=serializer.validated_data.get(
                    'status', instance.status),
                invoice=serializer.validated_data.get(
                    'invoice', instance.invoice),
                rider=instance.rider,
                user=instance.user
            )
        elif user.is_superuser:
            serializer.save()
        else:
            return Response(
                {'detail': 'You do not have permission to update this order.'},
                status=status.HTTP_403_FORBIDDEN
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def complete_order(request, order_id):
    if not request.user.is_staff:
        return Response({"error": "Only admin and rider users can complete orders."}, status=status.HTTP_403_FORBIDDEN)
    try:
        order = ManualOrder.objects.get(id=order_id)
        ride_charges = Decimal(order.ride_charges)
        paid_amount = Decimal(order.paid_amount)
        total_price = Decimal(order.total_price)

        total_required = total_price + ride_charges

        if paid_amount > total_required:
            excess_amount = paid_amount - total_required
            customer_wallet, _ = CustomerWallet.objects.get_or_create(
                customer=order.user)
            customer_wallet.add_funds(excess_amount)

        elif paid_amount < total_required:
            deficit_amount = total_required - paid_amount
            customer_wallet, _ = CustomerWallet.objects.get_or_create(
                customer=order.user)

            if customer_wallet.balance >= deficit_amount:
                customer_wallet.deduct_funds(deficit_amount)
            else:
                return Response({"error": "Insufficient funds in customer's wallet to cover the deficit."},
                                status=status.HTTP_400_BAD_REQUEST)

        company_share_percentage = Decimal('0.07')
        company_share = order.ride_charges * company_share_percentage
        rider_share = order.ride_charges - company_share

        company_wallet, created = CompanyWallet.objects.get_or_create(id=1)
        company_wallet.add_funds(company_share)

        rider_wallet, _ = RiderWallet.objects.get_or_create(rider=order.rider)
        rider_wallet.add_funds(rider_share)

        order.status = 'delivered'
        order.save()

        return Response({"message": "Order completed and wallets updated successfully."}, status=status.HTTP_200_OK)
    except ManualOrder.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateManualOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise ValidationError(
                "Authentication is required to create an order.")

        request_data = request.data
        request_data['user'] = request.user.id

        try:
            valid_customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            raise NotFound("Customer matching query does not exist.")

        customer_lat = valid_customer.address_latitude
        customer_lon = valid_customer.address_longitude
        customer_address = valid_customer.address

        if not customer_lat or not customer_lon or not customer_address:

            location_response = GetCustomerLocationView().get(request)
            if location_response.status_code == 200:
                location_data = location_response.data
                customer_lat = location_data.get('latitude')
                customer_lon = location_data.get('longitude')
                customer_address = location_data.get(
                    'address', 'Unknown Address')

                valid_customer.address_latitude = customer_lat
                valid_customer.address_longitude = customer_lon
                valid_customer.address = customer_address
                valid_customer.save()
            else:
                raise ValidationError(
                    "Customer must have a valid address with latitude and longitude. "
                    "Please update your location details."
                )

        if not customer_lat or not customer_lon or not customer_address:
            raise ValidationError(
                "Customer must have a valid address with latitude, longitude, and address. "
                "Please update your location details."
            )

        request_data['address'] = customer_address

        nearest_rider = None
        min_distance = float('inf')

        riders = Rider.objects.filter(
            latitude__isnull=False, longitude__isnull=False)
        customer_coordinates = (float(customer_lat), float(customer_lon))

        for rider in riders:
            rider_coordinates = (float(rider.latitude), float(rider.longitude))
            distance = calculate_distance(
                *customer_coordinates, *rider_coordinates)
            if distance < min_distance:
                min_distance = distance
                nearest_rider = rider

        if not nearest_rider:
            raise NotFound("No available riders.")

        request_data['rider'] = nearest_rider.id

        serializer = ManualOrderSerializer(
            data=request_data, context={'request': request})

        if serializer.is_valid():
            manual_order = serializer.save(
                customer=valid_customer, rider=nearest_rider)

            return Response(
                {"message": "Order created successfully.", "order": serializer.data},
                status=200,
            )

        return Response(serializer.errors, status=400)

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
                return data.get("display_name", "Unknown Address")
            return "Unknown Address"
        except Exception as e:
            print(f"Error: {e}")
            return "Error fetching address"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def complete_order(request, order_id):
    if not request.user.is_staff:
        return Response({"error": "Only admin and rider users can complete orders."}, status=status.HTTP_403_FORBIDDEN)
    try:
        with transaction.atomic():
            # Fetch the order
            order = ManualOrder.objects.get(id=order_id)

            # Ensure all numeric fields are converted to Decimal
            ride_charges = Decimal(str(order.ride_charges))
            paid_amount = Decimal(str(order.paid_amount))
            total_price = Decimal(str(order.total_price))

            total_required = total_price + ride_charges

            # Debugging logs
            print(f"Order ID: {order_id}")
            print(f"Ride Charges: {ride_charges}, Paid Amount: {
                  paid_amount}, Total Price: {total_price}")
            print(f"Total Required: {total_required}")

            # Handle excess or deficit payment by the customer
            if paid_amount > total_required:
                excess_amount = paid_amount - total_required
                customer_wallet, _ = CustomerWallet.objects.get_or_create(
                    customer=order.customer)
                customer_wallet.add_funds(excess_amount)
                print(f"Excess Amount: {
                      excess_amount} added to Customer Wallet.")
            elif paid_amount < total_required:
                deficit_amount = total_required - paid_amount
                customer_wallet, _ = CustomerWallet.objects.get_or_create(
                    customer=order.customer)
                if customer_wallet.balance >= deficit_amount:
                    customer_wallet.deduct_funds(deficit_amount)
                    print(f"Deficit Amount: {
                          deficit_amount} deducted from Customer Wallet.")
                else:
                    return Response({"error": "Insufficient funds in customer's wallet to cover the deficit."},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Calculate shares for company and rider
            company_share_percentage = Decimal('0.07')
            company_share = ride_charges * company_share_percentage
            rider_share = ride_charges - company_share

            print(f"Company Share: {
                  company_share}, Rider Share: {rider_share}")

            # Update the company wallet
            company_wallet, _ = CompanyWallet.objects.get_or_create(
                id=1)  # Assuming single wallet for company
            company_wallet.add_funds(company_share)
            print("Company Wallet updated.")

            # Update the rider wallet
            rider_wallet, _ = RiderWallet.objects.get_or_create(
                rider=order.rider)
            rider_wallet.add_funds(rider_share)
            print("Rider Wallet updated.")

            # Mark the order as delivered
            order.status = 'delivered'
            order.save()
            print(f"Order {order_id} marked as delivered.")

            return Response({"message": "Order completed and wallets updated successfully."}, status=status.HTTP_200_OK)
    except ManualOrder.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error completing order: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminOrderListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        orders = ManualOrder.objects.all()
        serializer = ManualOrderSerializer(orders, many=True)
        return Response(serializer.data)


class RiderOrderListView(ListAPIView):
    serializer_class = ManualOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            rider = Rider.objects.get(user=user)
            print(rider)
        except Rider.DoesNotExist:
            return ManualOrder.objects.all()
        return ManualOrder.objects.all()
